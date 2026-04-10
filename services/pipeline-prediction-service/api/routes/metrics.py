"""
Metrics & Accuracy Endpoints for Pipeline Prediction Service

Expose model accuracy, prediction correctness, and drift metrics.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Metrics & Monitoring"])


# ============================================================================
# ACCURACY METRICS
# ============================================================================

@router.get("/api/pipeline-prediction/metrics/{org_name}")
async def get_org_metrics(org_name: str, days: int = 7):
    """
    Get accuracy metrics for an organization over the last N days.
    
    Returns:
    - accuracy: Fraction of predictions that were correct (0-1)
    - total_predictions: Number of predictions made
    - correct_predictions: Number of correct predictions
    - incomplete_predictions: Still waiting for outcomes
    - by_risk_level: Accuracy broken down by risk level
    - by_date: Daily accuracy trends
    """
    from database.config import db_manager
    from database.models import PredictionHistory
    from sqlalchemy import select, func
    
    try:
        async with db_manager.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all predictions in time window with outcomes
            result = await session.execute(
                select(PredictionHistory).where(
                    (PredictionHistory.org_name == org_name) &
                    (PredictionHistory.predicted_at >= cutoff_date)
                )
            )
            
            predictions = result.scalars().all()
            
            if not predictions:
                return {
                    "org_name": org_name,
                    "status": "no_data",
                    "message": f"No predictions found for {org_name} in last {days} days"
                }
            
            # Build metrics
            total = len(predictions)
            with_outcomes = [p for p in predictions if p.prediction_correct is not None]
            correct = sum(1 for p in with_outcomes if p.prediction_correct)
            incomplete = len([p for p in predictions if p.prediction_correct is None])
            
            # Accuracy by risk level
            by_risk = {}
            for level in ["low", "medium", "high", "critical"]:
                level_preds = [p for p in with_outcomes if p.risk_level == level]
                if level_preds:
                    level_correct = sum(1 for p in level_preds if p.prediction_correct)
                    by_risk[level] = {
                        "total": len(level_preds),
                        "correct": level_correct,
                        "accuracy": round(level_correct / len(level_preds), 4)
                    }
            
            # Daily accuracy trends
            by_date = {}
            for pred in with_outcomes:
                date_key = pred.predicted_at.strftime("%Y-%m-%d")
                if date_key not in by_date:
                    by_date[date_key] = {"total": 0, "correct": 0}
                by_date[date_key]["total"] += 1
                if pred.prediction_correct:
                    by_date[date_key]["correct"] += 1
            
            for date_key in by_date:
                by_date[date_key]["accuracy"] = round(
                    by_date[date_key]["correct"] / by_date[date_key]["total"],
                    4
                )
            
            # Top models by accuracy
            active_model = await session.execute(
                select(PredictionHistory.model_version).where(
                    PredictionHistory.org_name == org_name
                ).order_by(PredictionHistory.predicted_at.desc()).limit(1)
            )
            current_version = active_model.scalar()
            
            return {
                "org_name": org_name,
                "time_period": {
                    "days": days,
                    "start": cutoff_date.isoformat(),
                    "end": datetime.utcnow().isoformat()
                },
                "overall": {
                    "total_predictions": total,
                    "predictions_with_outcomes": len(with_outcomes),
                    "incomplete_predictions": incomplete,
                    "correct_predictions": correct,
                    "accuracy": round(correct / len(with_outcomes), 4) if with_outcomes else 0.0
                },
                "by_risk_level": by_risk,
                "by_date": by_date,
                "current_model_version": current_version
            }
    
    except Exception as e:
        logger.error(f"❌ Error computing metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FALSE POSITIVES / FALSE NEGATIVES
# ============================================================================

@router.get("/api/pipeline-prediction/errors/{org_name}")
async def get_prediction_errors(org_name: str, limit: int = 50, repo_name: Optional[str] = None):
    """
    Get predictions that were incorrect (false positives and negatives).
    
    Helps identify systematic biases in the model.
    """
    from database.config import db_manager
    from database.models import PredictionHistory
    from sqlalchemy import select
    
    try:
        async with db_manager.get_session() as session:
            query = select(PredictionHistory).where(
                (PredictionHistory.org_name == org_name) &
                (PredictionHistory.prediction_correct == False)
            )
            
            if repo_name:
                query = query.where(PredictionHistory.repo_name == repo_name)
            
            result = await session.execute(
                query.order_by(PredictionHistory.predicted_at.desc()).limit(limit)
            )
            
            errors = result.scalars().all()
            
            false_positives = []  # Predicted fail, actually passed
            false_negatives = []  # Predicted pass, actually failed
            
            for err in errors:
                error_info = {
                    "prediction_id": err.id,
                    "repo_name": err.repo_name,
                    "branch": err.branch,
                    "author": err.author,
                    "predicted_at": err.predicted_at.isoformat(),
                    "failure_probability": err.failure_probability,
                    "risk_level": err.risk_level,
                    "actual_conclusion": err.actual_conclusion,
                    "risk_factors": err.risk_factors
                }
                
                if err.failure_probability > 0.5 and err.actual_conclusion == "success":
                    false_positives.append(error_info)
                elif err.failure_probability <= 0.5 and err.actual_conclusion == "failure":
                    false_negatives.append(error_info)
            
            return {
                "org_name": org_name,
                "repo_name": repo_name or "all",
                "false_positives": {
                    "count": len(false_positives),
                    "errors": false_positives
                },
                "false_negatives": {
                    "count": len(false_negatives),
                    "errors": false_negatives
                }
            }
    
    except Exception as e:
        logger.error(f"❌ Error getting errors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PREDICTION COMPLETION RATE
# ============================================================================

@router.get("/api/pipeline-prediction/completion-status/{org_name}")
async def get_completion_status(org_name: str):
    """
    Monitor how quickly predictions get outcomes.
    
    Returns:
    - total_predictions: Total predictions made
    - completed: Predictions with outcomes
    - pending: Still waiting for outcomes
    - avg_time_to_outcome: Average hours between prediction and outcome
    """
    from database.config import db_manager
    from database.models import PredictionHistory
    from sqlalchemy import select, func
    
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(PredictionHistory).where(
                    PredictionHistory.org_name == org_name
                ).order_by(PredictionHistory.predicted_at.desc()).limit(1000)
            )
            
            predictions = result.scalars().all()
            
            if not predictions:
                return {
                    "org_name": org_name,
                    "status": "no_data",
                    "message": "No predictions found"
                }
            
            completed = [p for p in predictions if p.prediction_correct is not None]
            pending = [p for p in predictions if p.prediction_correct is None]
            
            # Calculate average time to outcome
            times_to_outcome = []
            for p in completed:
                if p.actual_completed_at:
                    delta = (p.actual_completed_at - p.predicted_at).total_seconds() / 3600
                    times_to_outcome.append(delta)
            
            avg_time = sum(times_to_outcome) / len(times_to_outcome) if times_to_outcome else 0
            
            return {
                "org_name": org_name,
                "total_predictions": len(predictions),
                "completed": len(completed),
                "pending": len(pending),
                "completion_rate": round(len(completed) / len(predictions), 4),
                "avg_time_to_outcome_hours": round(avg_time, 2),
                "oldest_pending": {
                    "prediction_id": pending[0].id if pending else None,
                    "predicted_at": pending[0].predicted_at.isoformat() if pending else None,
                    "hours_pending": round((datetime.utcnow() - pending[0].predicted_at).total_seconds() / 3600, 2)
                    if pending else None
                }
            }
    
    except Exception as e:
        logger.error(f"❌ Error getting completion status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM HEALTH STATUS
# ============================================================================

@router.get("/api/pipeline-prediction/health")
async def get_system_health():
    """
    Get overall system health status.
    
    Returns:
    - model_status: Active models per org
    - accuracy_trends: Whether accuracy is improving or degrading
    - pending_predictions: Predictions awaiting outcomes
    - system_status: green / yellow / red
    """
    from database.config import db_manager
    from database.models import MLModelRegistry, PredictionHistory
    from sqlalchemy import select, func
    
    try:
        async with db_manager.get_session() as session:
            # Active models
            models = await session.execute(
                select(MLModelRegistry).where(MLModelRegistry.is_active == True)
            )
            active_models = models.scalars().all()
            
            # Pending predictions
            pending = await session.execute(
                select(func.count()).select_from(PredictionHistory).where(
                    PredictionHistory.prediction_correct == None
                )
            )
            pending_count = pending.scalar()
            
            # Recent accuracy (last 7 days)
            cutoff = datetime.utcnow() - timedelta(days=7)
            recent = await session.execute(
                select(PredictionHistory).where(
                    (PredictionHistory.predicted_at >= cutoff) &
                    (PredictionHistory.prediction_correct != None)
                )
            )
            recent_preds = recent.scalars().all()
            recent_accuracy = (
                sum(1 for p in recent_preds if p.prediction_correct) / len(recent_preds)
                if recent_preds else 0.0
            )
            
            # Determine system status
            if recent_accuracy < 0.70 or pending_count > 10000:
                status = "red"
            elif recent_accuracy < 0.75 or pending_count > 5000:
                status = "yellow"
            else:
                status = "green"
            
            return {
                "system_status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "models": {
                    "active_count": len(active_models),
                    "by_org": [
                        {
                            "org": m.org_name,
                            "version": m.model_version,
                            "accuracy": m.accuracy,
                            "type": m.model_type,
                            "trained_at": m.trained_at.isoformat() if m.trained_at else None
                        }
                        for m in active_models
                    ]
                },
                "predictions": {
                    "pending": pending_count,
                    "recent_accuracy": round(recent_accuracy, 4),
                    "time_window": "7 days"
                }
            }
    
    except Exception as e:
        logger.error(f"❌ Error getting health status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
