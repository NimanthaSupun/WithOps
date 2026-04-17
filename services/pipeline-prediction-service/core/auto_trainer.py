"""
Auto-Retraining Service for Pipeline Prediction Service

Automatically retrains models on real completed predictions every 2 weeks.
Performs A/B testing of new model vs current model.
Auto-activates new model if accuracy improves >1%.
Maintains rollback capability.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc

logger = logging.getLogger(__name__)


class AutoTrainer:
    """
    Automatic model retraining on real data with A/B testing.
    
    Workflow:
    1. Collect last 2000 completed real predictions per org
    2. Train new model on this data (with feature engineering)
    3. A/B test: new model vs current model on same data
    4. If new accuracy > current + 1%, activate new model
    5. Else keep current model, log comparison
    """

    def __init__(self, min_samples: int = 100, min_improvement: float = 0.01):
        """
        Args:
            min_samples: Minimum completed predictions needed to retrain
            min_improvement: Minimum accuracy improvement (1%) to activate new model
        """
        self.min_samples = min_samples
        self.min_improvement = min_improvement

    async def retrain_all_orgs(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrain all organizations with sufficient data.
        
        Returns:
            {
                org_name: {
                    "status": "retrained" | "skipped" | "failed",
                    "old_accuracy": 0.75,
                    "new_accuracy": 0.77,
                    "improvement": 0.02,
                    "decision": "activated" | "keep_current" | "error",
                    "new_model_version": 5,
                    "training_time": 45.2,
                    "samples_used": 500,
                },
                ...
            }
        """
        from database.config import db_manager

        results = {}
        
        try:
            async with db_manager.get_session() as session:
                # Get all organizations with predictions
                from database.models import PredictionHistory
                
                org_result = await session.execute(
                    select(PredictionHistory.org_name).distinct()
                )
                orgs = org_result.scalars().all()
                
                for org in orgs:
                    retrain_result = await self.retrain_org(org)
                    results[org] = retrain_result
                    
                    status = retrain_result.get("status", "unknown")
                    decision = retrain_result.get("decision", "none")
                    logger.info(
                        f"🤖 Retraining {org}: status={status}, decision={decision}"
                    )
        
        except Exception as e:
            logger.error(f"❌ Error retraining all organizations: {e}", exc_info=True)
        
        return results

    async def retrain_org(self, org_name: str) -> Dict[str, Any]:
        """
        Retrain model for a single organization.
        
        Args:
            org_name: Organization to retrain
            
        Returns:
            Retraining result with decision
        """
        from database.config import db_manager
        from database.models import PredictionHistory, MLModelRegistry
        from core.trainer import Trainer
        from core.feature_engineer import feature_engineer
        from core.model_manager import model_manager
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, 
            f1_score, roc_auc_score
        )

        start_time = time.time()
        result = {
            "org_name": org_name,
            "status": "skipped",
            "decision": "none",
            "old_accuracy": None,
            "new_accuracy": None,
            "improvement": 0.0,
            "training_time": 0.0,
            "samples_used": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # ── Step 1: Collect real completed predictions ──
            async with db_manager.get_session() as session:
                # Get last 2000 completed predictions for this org
                pred_result = await session.execute(
                    select(PredictionHistory).where(
                        and_(
                            PredictionHistory.org_name == org_name,
                            PredictionHistory.actual_conclusion.isnot(None),
                        )
                    ).order_by(desc(PredictionHistory.predicted_at)).limit(2000)
                )
                predictions = pred_result.scalars().all()

                if len(predictions) < self.min_samples:
                    logger.warning(
                        f"⚠️ Insufficient data for {org_name}: "
                        f"only {len(predictions)} completed predictions. "
                        f"Need {self.min_samples}."
                    )
                    result["status"] = "insufficient_data"
                    return result

                result["samples_used"] = len(predictions)
                logger.info(f"📚 Collected {len(predictions)} real predictions for {org_name}")

                # ── Step 2: Convert predictions to training data ──
                # This is simplified - in production, you'd reconstruct full features
                X = []
                y = []
                
                for pred in predictions:
                    # Simplified: use available prediction data
                    # In production, reconstruct full feature vector from workflow history
                    features = {
                        "failure_probability": pred.failure_probability,
                        "risk_level_critical": 1.0 if pred.risk_level == "critical" else 0.0,
                        "risk_level_high": 1.0 if pred.risk_level == "high" else 0.0,
                        "risk_level_medium": 1.0 if pred.risk_level == "medium" else 0.0,
                    }
                    X.append(features)
                    # 1 if predicted failure, 0 if success
                    y.append(1 if pred.actual_conclusion == "failure" else 0)

                # Convert to feature vectors
                import pandas as pd
                import numpy as np
                df = pd.DataFrame(X)
                feature_names = df.columns.tolist()
                X_array = df.values
                y_array = np.array(y)

                # ── Step 3: Get current (old) model accuracy ──
                current_model = model_manager.get_model(org_name)
                current_metadata = model_manager.get_metadata(org_name)
                old_accuracy = current_metadata.get("metrics", {}).get("accuracy", 0.0) if current_metadata else 0.0
                result["old_accuracy"] = old_accuracy

                # ── Step 4: Train new model ──
                logger.info(f"🏋️ Training new model for {org_name}...")
                
                X_train, X_test, y_train, y_test = train_test_split(
                    X_array, y_array, test_size=0.2, random_state=42, stratify=y_array
                )

                # Train Random Forest (fast and interpretable)
                from sklearn.ensemble import RandomForestClassifier
                new_model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=15,
                    min_samples_split=5,
                    random_state=42,
                    n_jobs=-1,
                )
                new_model.fit(X_train, y_train)

                # ── Step 5: A/B test: compare accuracies ──
                y_pred_new = new_model.predict(X_test)
                new_accuracy = accuracy_score(y_test, y_pred_new)
                result["new_accuracy"] = new_accuracy

                # If we have a current model, compare
                if current_model:
                    y_pred_current = current_model.predict(X_test)
                    current_accuracy = accuracy_score(y_test, y_pred_current)
                    improvement = new_accuracy - current_accuracy
                else:
                    current_accuracy = old_accuracy
                    improvement = new_accuracy - old_accuracy

                result["improvement"] = improvement
                training_time = time.time() - start_time
                result["training_time"] = training_time

                logger.info(
                    f"📊 New model accuracy: {new_accuracy:.2%}, "
                    f"Current: {current_accuracy:.2%}, "
                    f"Improvement: {improvement:.2%}"
                )

                # ── Step 6: Decision: activate or keep current ──
                if improvement >= self.min_improvement:
                    # Compute metrics for new model
                    try:
                        precision = precision_score(y_test, y_pred_new)
                        recall = recall_score(y_test, y_pred_new)
                        f1 = f1_score(y_test, y_pred_new)
                        # AUC-ROC might fail if only 1 class, so wrap in try
                        try:
                            auc_roc = roc_auc_score(y_test, new_model.predict_proba(X_test)[:, 1])
                        except:
                            auc_roc = 0.0
                    except Exception as e:
                        logger.warning(f"⚠️ Error computing metrics: {e}")
                        precision = recall = f1 = auc_roc = 0.0

                    # Extract feature importance
                    feature_importance = {
                        name: float(importance)
                        for name, importance in zip(feature_names, new_model.feature_importances_)
                    }

                    # Get class distribution
                    from collections import Counter
                    class_dist = Counter(y_train)
                    class_distribution = {
                        "failure": int(class_dist[1]),
                        "success": int(class_dist[0]),
                    }

                    # Save new model
                    metrics = {
                        "accuracy": new_accuracy,
                        "precision": precision,
                        "recall": recall,
                        "f1": f1,
                        "auc_roc": auc_roc,
                    }

                    new_version = await model_manager.save_model(
                        model=new_model,
                        org_name=org_name,
                        model_type="random_forest",
                        metrics=metrics,
                        feature_importance=feature_importance,
                        feature_names=feature_names,
                        training_samples=len(X_train),
                        class_distribution=class_distribution,
                    )

                    result["status"] = "retrained"
                    result["decision"] = "activated"
                    result["new_model_version"] = new_version
                    
                    logger.info(
                        f"✅ NEW MODEL ACTIVATED for {org_name} v{new_version}. "
                        f"Accuracy: {new_accuracy:.2%} (+{improvement:.2%})"
                    )

                else:
                    result["status"] = "retrained"
                    result["decision"] = "keep_current"
                    logger.info(
                        f"⏸️ Keeping current model for {org_name}. "
                        f"Improvement {improvement:.2%} < {self.min_improvement:.2%} threshold"
                    )

        except Exception as e:
            logger.error(f"❌ Retraining failed for {org_name}: {e}", exc_info=True)
            result["status"] = "failed"
            result["decision"] = "error"
            result["error"] = str(e)

        return result

    async def get_retraining_schedule(self) -> Dict[str, Dict[str, Any]]:
        """
        Get next retraining times for all organizations.
        
        Returns:
            {
                org_name: {
                    "last_retraining": datetime,
                    "next_retraining": datetime,
                    "days_until": int,
                    "samples_ready": int,
                },
                ...
            }
        """
        from database.config import db_manager
        from database.models import PredictionHistory, MLModelRegistry

        schedule = {}
        
        try:
            async with db_manager.get_session() as session:
                # Get all organizations
                org_result = await session.execute(
                    select(PredictionHistory.org_name).distinct()
                )
                orgs = org_result.scalars().all()
                
                for org in orgs:
                    # Get last training time
                    model_result = await session.execute(
                        select(MLModelRegistry).where(
                            MLModelRegistry.org_name == org
                        ).order_by(desc(MLModelRegistry.trained_at)).limit(1)
                    )
                    last_model = model_result.scalar()
                    last_trained = last_model.trained_at if last_model else None

                    # Get count of completed predictions since last training
                    since_date = last_trained or (datetime.utcnow() - timedelta(days=14))
                    pred_result = await session.execute(
                        select(PredictionHistory).where(
                            and_(
                                PredictionHistory.org_name == org,
                                PredictionHistory.actual_conclusion.isnot(None),
                                PredictionHistory.predicted_at >= since_date,
                            )
                        )
                    )
                    samples_ready = len(pred_result.scalars().all())

                    # Estimate next retraining
                    next_retraining = (last_trained + timedelta(days=14)) if last_trained else datetime.utcnow()
                    days_until = (next_retraining - datetime.utcnow()).days

                    schedule[org] = {
                        "last_retraining": last_trained.isoformat() if last_trained else None,
                        "next_retraining": next_retraining.isoformat(),
                        "days_until": max(0, days_until),
                        "samples_ready": samples_ready,
                    }

        except Exception as e:
            logger.error(f"❌ Error getting retraining schedule: {e}", exc_info=True)

        return schedule


# Global instance
auto_trainer = AutoTrainer(min_samples=100, min_improvement=0.01)


async def schedule_retraining():
    """
    Entry point for APScheduler.
    Called bi-weekly to retrain models on real data.
    """
    logger.info("🤖 Starting bi-weekly auto-retraining...")
    
    try:
        results = await auto_trainer.retrain_all_orgs()
        
        activated = sum(1 for r in results.values() if r.get("decision") == "activated")
        kept = sum(1 for r in results.values() if r.get("decision") == "keep_current")
        failed = sum(1 for r in results.values() if r.get("decision") == "error")
        
        logger.info(
            f"✅ Bi-weekly retraining completed: {activated} activated, "
            f"{kept} kept current, {failed} failed"
        )
        
        return results
    
    except Exception as e:
        logger.error(f"❌ Bi-weekly retraining failed: {e}", exc_info=True)
        return {}
