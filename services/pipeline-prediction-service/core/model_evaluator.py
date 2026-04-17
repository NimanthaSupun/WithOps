"""
Model Evaluator for Pipeline Prediction Service

Evaluates model accuracy on real completed predictions.
Detects performance drift and triggers alerts if accuracy drops.

Weekly evaluation on last 500 completed predictions per organization.
Provides actionable insights for model retraining decisions.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    Evaluates model performance on real, completed pipeline predictions.
    
    Key responsibilities:
    - Compute accuracy metrics on last N completed predictions
    - Detect performance drift (accuracy drops >5%)
    - Track metrics over time for trending
    - Generate evaluation reports
    """

    def __init__(self, lookback_days: int = 7):
        """
        Args:
            lookback_days: Days of completed predictions to evaluate on
        """
        self.lookback_days = lookback_days

    async def evaluate_all_orgs(self) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate all organizations' models.
        
        Returns:
            {
                org_name: {
                    "accuracy": 0.75,
                    "precision": 0.80,
                    "recall": 0.70,
                    "f1": 0.75,
                    "total_predictions": 500,
                    "correct_predictions": 375,
                    "drift_detected": False,
                    "baseline_accuracy": 0.78,
                    "accuracy_change": -0.03,
                    "status": "healthy" | "warning" | "critical"
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
                    eval_result = await self.evaluate_org(org)
                    results[org] = eval_result
                    
                    # Log results
                    status = eval_result.get("status", "unknown")
                    accuracy = eval_result.get("accuracy", 0)
                    logger.info(
                        f"📊 Evaluation for {org}: accuracy={accuracy:.2%}, "
                        f"status={status}, drift={eval_result.get('drift_detected', False)}"
                    )
                    
                    # Alert on drift
                    if eval_result.get("drift_detected"):
                        logger.warning(
                            f"⚠️ DRIFT ALERT {org}: Accuracy dropped from "
                            f"{eval_result.get('baseline_accuracy', 0):.2%} to "
                            f"{accuracy:.2%} ({eval_result.get('accuracy_change', 0):.2%} change)"
                        )
        
        except Exception as e:
            logger.error(f"❌ Error evaluating all organizations: {e}", exc_info=True)
        
        return results

    async def evaluate_org(self, org_name: str) -> Dict[str, Any]:
        """
        Evaluate a single organization's model.
        
        Args:
            org_name: Organization to evaluate
            
        Returns:
            Evaluation metrics dictionary with status
        """
        from database.config import db_manager
        from database.models import PredictionHistory, MLModelRegistry

        result = {
            "org_name": org_name,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "total_predictions": 0,
            "correct_predictions": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_negatives": 0,
            "true_positives": 0,
            "drift_detected": False,
            "baseline_accuracy": None,
            "accuracy_change": 0.0,
            "status": "insufficient_data",
            "evaluated_at": datetime.utcnow().isoformat(),
        }

        try:
            async with db_manager.get_session() as session:
                # Get predictions completed in last N days
                cutoff_date = datetime.utcnow() - timedelta(days=self.lookback_days)
                
                pred_result = await session.execute(
                    select(PredictionHistory).where(
                        and_(
                            PredictionHistory.org_name == org_name,
                            PredictionHistory.actual_conclusion.isnot(None),  # Only completed
                            PredictionHistory.predicted_at >= cutoff_date,
                        )
                    ).order_by(desc(PredictionHistory.predicted_at)).limit(500)
                )
                predictions = pred_result.scalars().all()

                if not predictions:
                    logger.warning(f"⚠️ No completed predictions for {org_name} in last {self.lookback_days} days")
                    return result

                # Compute metrics
                total = len(predictions)
                correct = sum(1 for p in predictions if p.prediction_correct)
                
                # Breakdown: TP, FP, FN, TN
                # prediction_correct=True means prediction matched actual
                true_positives = sum(1 for p in predictions 
                                     if p.prediction_correct and p.risk_level == "critical")
                true_negatives = sum(1 for p in predictions 
                                     if p.prediction_correct and p.risk_level != "critical")
                false_positives = sum(1 for p in predictions 
                                      if not p.prediction_correct and p.risk_level == "critical")
                false_negatives = sum(1 for p in predictions 
                                      if not p.prediction_correct and p.risk_level != "critical")

                accuracy = correct / total if total > 0 else 0.0
                precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
                recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

                result.update({
                    "accuracy": accuracy,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "total_predictions": total,
                    "correct_predictions": correct,
                    "true_positives": true_positives,
                    "true_negatives": true_negatives,
                    "false_positives": false_positives,
                    "false_negatives": false_negatives,
                })

                # Get baseline accuracy from previous model
                baseline_result = await session.execute(
                    select(MLModelRegistry).where(
                        MLModelRegistry.org_name == org_name
                    ).order_by(desc(MLModelRegistry.trained_at)).limit(1)
                )
                latest_model = baseline_result.scalar()
                
                if latest_model and latest_model.accuracy:
                    baseline = latest_model.accuracy
                    result["baseline_accuracy"] = baseline
                    change = accuracy - baseline
                    result["accuracy_change"] = change
                    
                    # Drift detection: >5% drop
                    if change < -0.05:
                        result["drift_detected"] = True
                        result["status"] = "critical"
                    elif accuracy < 0.65:
                        result["status"] = "warning"
                    else:
                        result["status"] = "healthy"
                else:
                    result["status"] = "no_baseline"

        except Exception as e:
            logger.error(f"❌ Error evaluating {org_name}: {e}", exc_info=True)
            result["status"] = "error"

        return result

    async def get_evaluation_trends(self, org_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get evaluation trends over time for an organization.
        
        Args:
            org_name: Organization to analyze
            days: Number of days to look back
            
        Returns:
            List of daily evaluations with metrics
        """
        from database.config import db_manager
        from database.models import PredictionHistory

        trends = []
        
        try:
            async with db_manager.get_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                pred_result = await session.execute(
                    select(PredictionHistory).where(
                        and_(
                            PredictionHistory.org_name == org_name,
                            PredictionHistory.actual_conclusion.isnot(None),
                            PredictionHistory.predicted_at >= cutoff_date,
                        )
                    ).order_by(PredictionHistory.predicted_at)
                )
                predictions = pred_result.scalars().all()

                # Group by day
                by_day = {}
                for pred in predictions:
                    day = pred.predicted_at.date()
                    if day not in by_day:
                        by_day[day] = {
                            "date": day.isoformat(),
                            "total": 0,
                            "correct": 0,
                            "accuracy": 0.0,
                        }
                    
                    by_day[day]["total"] += 1
                    if pred.prediction_correct:
                        by_day[day]["correct"] += 1

                # Compute daily accuracy
                for day_data in by_day.values():
                    if day_data["total"] > 0:
                        day_data["accuracy"] = day_data["correct"] / day_data["total"]
                    trends.append(day_data)

        except Exception as e:
            logger.error(f"❌ Error getting trends for {org_name}: {e}", exc_info=True)

        return trends

    async def get_model_comparison(
        self, org_name: str, window_days: int = 7
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare current model vs previous model on recent predictions.
        
        Args:
            org_name: Organization to analyze
            window_days: Days of predictions to compare on
            
        Returns:
            {
                "current_model": {version, accuracy, ...},
                "previous_model": {version, accuracy, ...},
                "improvement": accuracy_change
            }
        """
        result = {
            "current_model": {},
            "previous_model": {},
            "improvement": 0.0,
            "recommendation": "monitor",
        }

        try:
            # Get current evaluation
            current_eval = await self.evaluate_org(org_name)
            result["current_model"] = {
                "accuracy": current_eval.get("accuracy"),
                "precision": current_eval.get("precision"),
                "recall": current_eval.get("recall"),
                "f1": current_eval.get("f1"),
                "total_predictions": current_eval.get("total_predictions"),
            }

            # Get baseline
            if current_eval.get("baseline_accuracy"):
                result["previous_model"]["accuracy"] = current_eval.get("baseline_accuracy")
                result["improvement"] = current_eval.get("accuracy_change", 0.0)

                # Recommendation
                if result["improvement"] > 0.01:
                    result["recommendation"] = "activate_new_model"
                elif result["improvement"] < -0.05:
                    result["recommendation"] = "rollback_model"
                else:
                    result["recommendation"] = "monitor"

        except Exception as e:
            logger.error(f"❌ Error comparing models for {org_name}: {e}", exc_info=True)
            result["error"] = str(e)

        return result


# Global instance
model_evaluator = ModelEvaluator(lookback_days=7)


async def schedule_evaluation():
    """
    Entry point for APScheduler.
    Called weekly to evaluate all models.
    """
    logger.info("🔍 Starting weekly model evaluation...")
    
    try:
        results = await model_evaluator.evaluate_all_orgs()
        
        success_count = sum(1 for r in results.values() if r.get("status") != "error")
        warning_count = sum(1 for r in results.values() if r.get("status") == "warning")
        critical_count = sum(1 for r in results.values() if r.get("status") == "critical")
        
        logger.info(
            f"✅ Weekly evaluation completed: {success_count} healthy, "
            f"{warning_count} warnings, {critical_count} critical"
        )
        
        return results
    
    except Exception as e:
        logger.error(f"❌ Weekly evaluation failed: {e}", exc_info=True)
        return {}
