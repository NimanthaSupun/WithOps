"""
Training Pipeline for Pipeline Prediction Service

Orchestrates the full ML training flow:
  1. Fetch data (synthetic or real) from database
  2. Engineer features
  3. Split into train/test
  4. Train model (Random Forest or XGBoost)
  5. Evaluate with precision, recall, F1, AUC-ROC
  6. Extract feature importance
  7. Save model + register in DB
"""

import logging
import time
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

logger = logging.getLogger(__name__)


class Trainer:
    """
    ML Training Pipeline.

    Supports:
    - Random Forest (default, fast, good explainability)
    - XGBoost (optional, better performance on some datasets)
    - Gradient Boosting (sklearn fallback if xgboost not available)
    """

    def __init__(self):
        self.last_training_result: Optional[Dict] = None

    async def train(
        self,
        org_name: str,
        model_type: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        Full training pipeline: data → features → train → evaluate → save.

        Args:
            org_name: Organization to train model for
            model_type: "random_forest", "xgboost", or "gradient_boosting"
            test_size: Fraction of data reserved for testing
            random_state: Random seed for reproducibility

        Returns:
            Dictionary with training results, metrics, and model info
        """
        start_time = time.time()
        logger.info(f"🏋️ Starting training pipeline for {org_name} (model: {model_type})")

        result = {
            "org_name": org_name,
            "model_type": model_type,
            "status": "in_progress",
            "progress": {},
        }

        try:
            # ── Step 1: Load data from database ──
            result["progress"]["data_collection"] = "in_progress"
            runs = await self._load_training_data(org_name)

            if len(runs) < 30:
                result["status"] = "failed"
                result["error"] = (
                    f"Insufficient data: only {len(runs)} runs found. "
                    f"Need at least 30 runs to train. "
                    f"Generate synthetic data first via POST /api/pipeline-prediction/generate-data"
                )
                return result

            result["progress"]["data_collection"] = f"completed ({len(runs)} runs loaded)"

            # ── Step 2: Feature engineering ──
            result["progress"]["feature_engineering"] = "in_progress"

            from core.feature_engineer import feature_engineer
            X, y, feature_names = feature_engineer.transform_dataset(runs)

            result["progress"]["feature_engineering"] = (
                f"completed ({X.shape[1]} features extracted)"
            )

            # ── Step 3: Train-test split ──
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=test_size,
                stratify=y,
                random_state=random_state,
            )

            logger.info(f"   Train set: {X_train.shape[0]} samples")
            logger.info(f"   Test set:  {X_test.shape[0]} samples")

            # ── Step 4: Train model ──
            result["progress"]["model_training"] = "in_progress"
            model = self._create_model(model_type, y_train, random_state)
            model.fit(X_train, y_train)
            result["progress"]["model_training"] = "completed"

            # ── Step 5: Evaluate ──
            result["progress"]["evaluation"] = "in_progress"
            metrics = self._evaluate(model, X_test, y_test)
            result["progress"]["evaluation"] = "completed"

            logger.info(f"   📊 Metrics:")
            logger.info(f"      Accuracy:  {metrics['accuracy']:.4f}")
            logger.info(f"      Precision: {metrics['precision']:.4f}")
            logger.info(f"      Recall:    {metrics['recall']:.4f}")
            logger.info(f"      F1 Score:  {metrics['f1']:.4f}")
            logger.info(f"      AUC-ROC:   {metrics['auc_roc']:.4f}")

            # ── Step 6: Feature importance ──
            importance = self._get_feature_importance(model, feature_names)

            logger.info(f"   🔍 Top 5 Features:")
            sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            for fname, imp in sorted_imp[:5]:
                logger.info(f"      {fname}: {imp:.4f}")

            # ── Step 7: Class distribution ──
            class_dist = {
                "success": int(np.sum(y == 0)),
                "failure": int(np.sum(y == 1)),
            }

            # ── Step 8: Save model ──
            from core.model_manager import model_manager

            version = await model_manager.save_model(
                model=model,
                org_name=org_name,
                model_type=model_type,
                metrics=metrics,
                feature_importance=importance,
                feature_names=feature_names,
                training_samples=len(X_train),
                class_distribution=class_dist,
            )

            # ── Build final result ──
            elapsed = time.time() - start_time
            result.update({
                "status": "completed",
                "model_version": version,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "total_samples": len(runs),
                "metrics": metrics,
                "feature_importance": importance,
                "class_distribution": class_dist,
                "feature_names": feature_names,
                "training_duration_seconds": round(elapsed, 2),
            })

            self.last_training_result = result
            logger.info(f"✅ Training completed in {elapsed:.1f}s — Model v{version}")

        except Exception as e:
            logger.error(f"❌ Training failed: {e}", exc_info=True)
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    # ════════════════════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ════════════════════════════════════════════════════════════════════════

    async def _load_training_data(self, org_name: str):
        """Load workflow run data from the database."""
        from database.config import db_manager
        from database.models import WorkflowRunHistory
        from sqlalchemy import select

        async with db_manager.get_session() as session:
            result = await session.execute(
                select(WorkflowRunHistory)
                .where(WorkflowRunHistory.org_name == org_name)
                .order_by(WorkflowRunHistory.created_at.asc())
            )
            records = result.scalars().all()

            # Convert ORM objects to dicts
            runs = []
            for r in records:
                runs.append({
                    "org_name": r.org_name,
                    "repo_name": r.repo_name,
                    "repo_full_name": r.repo_full_name,
                    "github_run_id": r.github_run_id,
                    "workflow_name": r.workflow_name,
                    "workflow_path": r.workflow_path,
                    "run_number": r.run_number,
                    "event": r.event,
                    "status": r.status,
                    "conclusion": r.conclusion,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "started_at": r.started_at,
                    "completed_at": r.completed_at,
                    "duration_seconds": r.duration_seconds,
                    "head_branch": r.head_branch,
                    "head_sha": r.head_sha,
                    "commit_message": r.commit_message,
                    "actor_login": r.actor_login,
                    "actor_id": r.actor_id,
                    "files_changed": r.files_changed,
                    "additions": r.additions,
                    "deletions": r.deletions,
                })

            logger.info(f"📦 Loaded {len(runs)} runs from database for {org_name}")
            return runs

    def _create_model(self, model_type: str, y_train: np.ndarray,
                       random_state: int):
        """Create and configure the ML model."""

        # Calculate class weight ratio for imbalanced data
        n_success = np.sum(y_train == 0)
        n_failure = np.sum(y_train == 1)
        scale_pos = n_success / max(n_failure, 1)

        if model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=random_state,
                n_jobs=-1,  # Use all CPU cores
            )

        elif model_type == "xgboost":
            try:
                from xgboost import XGBClassifier
                return XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    scale_pos_weight=scale_pos,
                    random_state=random_state,
                    use_label_encoder=False,
                    eval_metric="logloss",
                )
            except ImportError:
                logger.warning("⚠️ XGBoost not installed, falling back to GradientBoosting")
                return GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=random_state,
                )

        elif model_type == "gradient_boosting":
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=random_state,
            )

        else:
            raise ValueError(f"Unknown model type: {model_type}. "
                             f"Choose from: random_forest, xgboost, gradient_boosting")

    def _evaluate(self, model, X_test: np.ndarray,
                   y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate the trained model on test data."""

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        # Handle edge case where only one class is present in test set
        try:
            auc = roc_auc_score(y_test, y_proba)
        except ValueError:
            auc = 0.0
            logger.warning("⚠️ Could not compute AUC-ROC (single class in test set)")

        cm = confusion_matrix(y_test, y_pred).tolist()

        return {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
            "auc_roc": round(float(auc), 4),
            "confusion_matrix": cm,
        }

    def _get_feature_importance(self, model, feature_names) -> Dict[str, float]:
        """Extract feature importance from the trained model."""
        importances = model.feature_importances_
        return {
            name: round(float(imp), 4)
            for name, imp in zip(feature_names, importances)
        }


# Global instance
trainer = Trainer()
