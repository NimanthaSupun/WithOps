"""
Ensemble Trainer for Pipeline Prediction Service

Creates ensemble models by combining multiple algorithms.
Ensemble methods typically outperform individual models.

Ensemble Strategies:
1. Voting Ensemble (hard/soft voting)
2. Stacking (meta-learner combining base models)
3. Weighted Ensemble (weighted average predictions)
"""

import logging
import time
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

logger = logging.getLogger(__name__)


class EnsembleTrainer:
    """
    Creates and trains ensemble models.
    
    Combines Random Forest, XGBoost, and Gradient Boosting
    for improved prediction accuracy.
    """

    def __init__(self):
        self.ensemble_model = None
        self.base_models = {}

    async def train_voting_ensemble(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        voting: str = "soft",
        weights: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Train a voting ensemble combining multiple algorithms.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation features
            y_val: Optional validation labels
            voting: "hard" (majority vote) or "soft" (probability average)
            weights: Optional weights for each model [rf_weight, xgb_weight, gb_weight]
            
        Returns:
            {
                "model": trained ensemble,
                "accuracy": accuracy score,
                "precision": precision score,
                "recall": recall score,
                "f1": f1 score,
                "base_models": individual model scores,
                "training_time": time in seconds
            }
        """
        start_time = time.time()
        
        logger.info(f"🧬 Training voting ensemble ({voting} voting)...")
        
        # Define base models
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1,
        )
        
        gb = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42,
        )
        
        # Try to use XGBoost if available
        try:
            import xgboost as xgb
            xgb_model = xgb.XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=7,
                random_state=42,
                use_label_encoder=False,
                eval_metric="logloss",
            )
            base_estimators = [
                ("rf", rf),
                ("xgb", xgb_model),
                ("gb", gb),
            ]
            default_weights = [1, 1.2, 1]  # Slightly boost XGBoost
        except ImportError:
            logger.warning("⚠️ XGBoost not available, using RF + GB only")
            base_estimators = [
                ("rf", rf),
                ("gb", gb),
            ]
            default_weights = [1, 1]
        
        weights = weights or default_weights
        
        # Create voting ensemble
        ensemble = VotingClassifier(
            estimators=base_estimators,
            voting=voting,
            weights=weights,
            n_jobs=-1,
        )
        
        # Train ensemble
        ensemble.fit(X_train, y_train)
        
        elapsed = time.time() - start_time
        
        # Evaluate on training set
        y_pred = ensemble.predict(X_train)
        train_accuracy = accuracy_score(y_train, y_pred)
        train_precision = precision_score(y_train, y_pred, zero_division=0)
        train_recall = recall_score(y_train, y_pred, zero_division=0)
        train_f1 = f1_score(y_train, y_pred, zero_division=0)
        
        result = {
            "model": ensemble,
            "voting": voting,
            "weights": weights,
            "train_accuracy": train_accuracy,
            "train_precision": train_precision,
            "train_recall": train_recall,
            "train_f1": train_f1,
            "training_time": elapsed,
        }
        
        # Log base model performances
        base_scores = {}
        for name, model in base_estimators:
            base_pred = model.predict(X_train)
            base_acc = accuracy_score(y_train, base_pred)
            base_scores[name] = base_acc
            logger.info(f"   {name.upper()}: accuracy={base_acc:.4f}")
        
        result["base_models"] = base_scores
        result["ensemble_accuracy"] = train_accuracy
        
        logger.info(
            f"✅ Ensemble trained in {elapsed:.1f}s\n"
            f"   Ensemble accuracy: {train_accuracy:.4f}\n"
            f"   Precision: {train_precision:.4f}, Recall: {train_recall:.4f}, F1: {train_f1:.4f}"
        )
        
        # Validate on validation set if provided
        if X_val is not None and y_val is not None:
            y_val_pred = ensemble.predict(X_val)
            val_accuracy = accuracy_score(y_val, y_val_pred)
            val_precision = precision_score(y_val, y_val_pred, zero_division=0)
            val_recall = recall_score(y_val, y_val_pred, zero_division=0)
            val_f1 = f1_score(y_val, y_val_pred, zero_division=0)
            
            result.update({
                "val_accuracy": val_accuracy,
                "val_precision": val_precision,
                "val_recall": val_recall,
                "val_f1": val_f1,
            })
            
            logger.info(
                f"   Validation accuracy: {val_accuracy:.4f}\n"
                f"   Validation F1: {val_f1:.4f}"
            )
        
        self.ensemble_model = ensemble
        self.base_models = {name: model for name, model in base_estimators}
        
        return result

    async def compare_single_vs_ensemble(
        self,
        ensemble: Any,
        single_model: Any,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Compare ensemble performance vs single best model.
        
        Args:
            ensemble: Ensemble model
            single_model: Single best model to compare against
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Comparison results with improvement metrics
        """
        # Predict with both
        ensemble_pred = ensemble.predict(X_test)
        single_pred = single_model.predict(X_test)
        
        # Compute metrics
        ensemble_acc = accuracy_score(y_test, ensemble_pred)
        single_acc = accuracy_score(y_test, single_pred)
        
        ensemble_f1 = f1_score(y_test, ensemble_pred, zero_division=0)
        single_f1 = f1_score(y_test, single_pred, zero_division=0)
        
        improvement_acc = ensemble_acc - single_acc
        improvement_f1 = ensemble_f1 - single_f1
        
        result = {
            "ensemble_accuracy": ensemble_acc,
            "single_accuracy": single_acc,
            "accuracy_improvement": improvement_acc,
            "ensemble_f1": ensemble_f1,
            "single_f1": single_f1,
            "f1_improvement": improvement_f1,
            "ensemble_better": improvement_acc > 0,
        }
        
        logger.info(
            f"📊 Ensemble vs Single Model:\n"
            f"   Accuracy: Ensemble {ensemble_acc:.4f} vs Single {single_acc:.4f} "
            f"({improvement_acc:+.4f})\n"
            f"   F1-Score: Ensemble {ensemble_f1:.4f} vs Single {single_f1:.4f} "
            f"({improvement_f1:+.4f})"
        )
        
        return result

    def get_feature_importance_ensemble(self, feature_names: List[str]) -> Dict[str, float]:
        """
        Compute feature importance from ensemble base models.
        
        Averages feature importance across all base models.
        
        Args:
            feature_names: List of feature names
            
        Returns:
            Dictionary of feature -> average importance
        """
        if not self.base_models:
            logger.warning("⚠️ No base models trained yet")
            return {}
        
        importances = {}
        
        for feature in feature_names:
            importances[feature] = 0.0
        
        for name, model in self.base_models.items():
            if hasattr(model, "feature_importances_"):
                model_imp = model.feature_importances_
                for i, feature in enumerate(feature_names):
                    if i < len(model_imp):
                        importances[feature] += model_imp[i]
        
        # Average across models
        num_models = len(self.base_models)
        for feature in importances:
            importances[feature] /= num_models
        
        # Sort by importance
        sorted_imp = dict(sorted(
            importances.items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        logger.info("📊 Ensemble Feature Importance (Top 10):")
        for i, (feature, imp) in enumerate(list(sorted_imp.items())[:10], 1):
            logger.info(f"   {i:2d}. {feature:30s}: {imp:.4f}")
        
        return sorted_imp


# Global instance
ensemble_trainer = EnsembleTrainer()
