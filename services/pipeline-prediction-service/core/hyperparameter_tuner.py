"""
Hyperparameter Tuning for Pipeline Prediction Service

Performs grid search optimization for Random Forest and XGBoost models.
Finds optimal hyperparameters based on cross-validation performance.

Tested algorithms:
- Random Forest (fast, interpretable)
- XGBoost (higher performance, tunable)
- Gradient Boosting (sklearn baseline)
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import make_scorer, f1_score

logger = logging.getLogger(__name__)


class HyperparameterTuner:
    """
    Optimizes ML model hyperparameters using grid search.
    
    Hyperparameter Spaces:
    - Random Forest: n_estimators, max_depth, min_samples_split, min_samples_leaf
    - XGBoost: learning_rate, max_depth, subsample, colsample_bytree
    - Gradient Boosting: n_estimators, learning_rate, max_depth
    """

    def __init__(self, cv_folds: int = 5, scoring: str = "f1"):
        """
        Args:
            cv_folds: Number of cross-validation folds (default 5)
            scoring: Scoring metric for grid search (f1, accuracy, roc_auc)
        """
        self.cv_folds = cv_folds
        self.scoring = scoring

    async def tune_random_forest(
        self, X_train, y_train, X_val=None, y_val=None, quick: bool = False
    ) -> Dict[str, Any]:
        """
        Tune Random Forest hyperparameters using grid search.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation set for final evaluation
            y_val: Optional validation labels
            quick: If True, use smaller parameter space for faster search
            
        Returns:
            {
                "best_model": fitted model,
                "best_params": optimal hyperparameters,
                "best_score": cross-val score,
                "grid_scores": all tested scores,
                "time": tuning time in seconds
            }
        """
        start_time = time.time()
        
        logger.info("🔍 Tuning Random Forest hyperparameters...")
        
        # Define parameter grid
        if quick:
            param_grid = {
                "n_estimators": [50, 100],
                "max_depth": [10, 15],
                "min_samples_split": [5, 10],
            }
        else:
            param_grid = {
                "n_estimators": [50, 100, 200],
                "max_depth": [10, 15, 20],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
                "max_features": ["sqrt", "log2"],
            }
        
        base_model = RandomForestClassifier(random_state=42, n_jobs=-1)
        
        grid_search = GridSearchCV(
            base_model,
            param_grid,
            cv=self.cv_folds,
            scoring=self.scoring,
            n_jobs=-1,
            verbose=1,
        )
        
        grid_search.fit(X_train, y_train)
        
        elapsed = time.time() - start_time
        
        result = {
            "algorithm": "random_forest",
            "best_model": grid_search.best_estimator_,
            "best_params": grid_search.best_params_,
            "best_score": grid_search.best_score_,
            "cv_results": grid_search.cv_results_,
            "time": elapsed,
        }
        
        logger.info(
            f"✅ Random Forest tuning complete in {elapsed:.1f}s\n"
            f"   Best params: {grid_search.best_params_}\n"
            f"   Best CV score: {grid_search.best_score_:.4f}"
        )
        
        # Evaluate on validation set if provided
        if X_val is not None and y_val is not None:
            val_score = grid_search.best_estimator_.score(X_val, y_val)
            result["validation_score"] = val_score
            logger.info(f"   Validation accuracy: {val_score:.4f}")
        
        return result

    async def tune_xgboost(
        self, X_train, y_train, X_val=None, y_val=None, quick: bool = False
    ) -> Dict[str, Any]:
        """
        Tune XGBoost hyperparameters using grid search.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation set
            y_val: Optional validation labels
            quick: If True, use smaller parameter space
            
        Returns:
            Tuning results dictionary
        """
        start_time = time.time()
        
        logger.info("🔍 Tuning XGBoost hyperparameters...")
        
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("❌ XGBoost not installed. Install with: pip install xgboost")
            return {
                "algorithm": "xgboost",
                "status": "failed",
                "error": "XGBoost not installed",
            }
        
        if quick:
            param_grid = {
                "learning_rate": [0.05, 0.1],
                "max_depth": [5, 7],
                "subsample": [0.8, 1.0],
            }
        else:
            param_grid = {
                "learning_rate": [0.01, 0.05, 0.1],
                "max_depth": [3, 5, 7],
                "subsample": [0.7, 0.8, 1.0],
                "colsample_bytree": [0.7, 0.8, 1.0],
                "n_estimators": [50, 100],
            }
        
        base_model = xgb.XGBClassifier(
            random_state=42,
            n_jobs=-1,
            use_label_encoder=False,
            eval_metric="logloss",
        )
        
        grid_search = GridSearchCV(
            base_model,
            param_grid,
            cv=self.cv_folds,
            scoring=self.scoring,
            n_jobs=-1,
            verbose=1,
        )
        
        grid_search.fit(X_train, y_train)
        
        elapsed = time.time() - start_time
        
        result = {
            "algorithm": "xgboost",
            "best_model": grid_search.best_estimator_,
            "best_params": grid_search.best_params_,
            "best_score": grid_search.best_score_,
            "cv_results": grid_search.cv_results_,
            "time": elapsed,
        }
        
        logger.info(
            f"✅ XGBoost tuning complete in {elapsed:.1f}s\n"
            f"   Best params: {grid_search.best_params_}\n"
            f"   Best CV score: {grid_search.best_score_:.4f}"
        )
        
        if X_val is not None and y_val is not None:
            val_score = grid_search.best_estimator_.score(X_val, y_val)
            result["validation_score"] = val_score
            logger.info(f"   Validation accuracy: {val_score:.4f}")
        
        return result

    async def tune_gradient_boosting(
        self, X_train, y_train, X_val=None, y_val=None, quick: bool = False
    ) -> Dict[str, Any]:
        """
        Tune Gradient Boosting hyperparameters.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation set
            y_val: Optional validation labels
            quick: If True, use smaller parameter space
            
        Returns:
            Tuning results dictionary
        """
        start_time = time.time()
        
        logger.info("🔍 Tuning Gradient Boosting hyperparameters...")
        
        if quick:
            param_grid = {
                "n_estimators": [50, 100],
                "learning_rate": [0.05, 0.1],
                "max_depth": [3, 5],
            }
        else:
            param_grid = {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.05, 0.1],
                "max_depth": [3, 5, 7],
                "min_samples_split": [2, 5],
                "subsample": [0.8, 1.0],
            }
        
        base_model = GradientBoostingClassifier(random_state=42)
        
        grid_search = GridSearchCV(
            base_model,
            param_grid,
            cv=self.cv_folds,
            scoring=self.scoring,
            n_jobs=-1,
            verbose=1,
        )
        
        grid_search.fit(X_train, y_train)
        
        elapsed = time.time() - start_time
        
        result = {
            "algorithm": "gradient_boosting",
            "best_model": grid_search.best_estimator_,
            "best_params": grid_search.best_params_,
            "best_score": grid_search.best_score_,
            "cv_results": grid_search.cv_results_,
            "time": elapsed,
        }
        
        logger.info(
            f"✅ Gradient Boosting tuning complete in {elapsed:.1f}s\n"
            f"   Best params: {grid_search.best_params_}\n"
            f"   Best CV score: {grid_search.best_score_:.4f}"
        )
        
        if X_val is not None and y_val is not None:
            val_score = grid_search.best_estimator_.score(X_val, y_val)
            result["validation_score"] = val_score
            logger.info(f"   Validation accuracy: {val_score:.4f}")
        
        return result

    async def compare_algorithms(
        self, X_train, y_train, X_val=None, y_val=None, quick: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Tune all three algorithms and compare results.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation set
            y_val: Optional validation labels
            quick: Use quick parameter space for faster comparison
            
        Returns:
            {
                "random_forest": {...},
                "xgboost": {...},
                "gradient_boosting": {...},
                "winner": algorithm with best score
            }
        """
        logger.info("🏆 Comparing all three algorithms...")
        
        results = {}
        
        # Tune Random Forest
        rf_result = await self.tune_random_forest(X_train, y_train, X_val, y_val, quick)
        results["random_forest"] = rf_result
        
        # Tune XGBoost
        xgb_result = await self.tune_xgboost(X_train, y_train, X_val, y_val, quick)
        results["xgboost"] = xgb_result
        
        # Tune Gradient Boosting
        gb_result = await self.tune_gradient_boosting(X_train, y_train, X_val, y_val, quick)
        results["gradient_boosting"] = gb_result
        
        # Determine winner
        scores = {
            name: result.get("best_score", 0)
            for name, result in results.items()
        }
        winner = max(scores, key=scores.get)
        results["winner"] = winner
        results["scores"] = scores
        
        logger.info(
            f"🏆 Winner: {winner.upper()}\n"
            f"   Scores: RF={scores.get('random_forest', 0):.4f}, "
            f"XGB={scores.get('xgboost', 0):.4f}, GB={scores.get('gradient_boosting', 0):.4f}"
        )
        
        return results


# Global instance
hyperparameter_tuner = HyperparameterTuner(cv_folds=5, scoring="f1")
