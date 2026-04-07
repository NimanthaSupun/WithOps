"""
Prediction API Routes for Pipeline Prediction Service

Endpoints:
  POST /predict                          — Predict pipeline failure probability
  GET  /history/{org_name}/{repo_name}   — Get prediction history for a repo
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Prediction"])


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================

class PredictRequest(BaseModel):
    org_name: str = Field(..., description="GitHub organization name")
    repo_name: str = Field(..., description="Repository name")
    branch: str = Field(default="main", description="Branch name")
    author: str = Field(default="unknown", description="Commit author username")
    commit_sha: str = Field(default="", description="Commit SHA (optional)")
    event_type: str = Field(default="push", description="Event: push, pull_request, schedule")
    files_changed: int = Field(default=0, ge=0, description="Number of files changed")
    additions: int = Field(default=0, ge=0, description="Lines added")
    deletions: int = Field(default=0, ge=0, description="Lines deleted")
    commit_message: str = Field(default="", description="Commit message text")


class PredictResponse(BaseModel):
    prediction: Dict[str, Any]
    risk_factors: List[Dict[str, Any]]
    recommendation: str
    context: Dict[str, Any]
    model_info: Optional[Dict[str, Any]]
    prediction_id: Optional[str]
    predicted_at: Optional[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/predict", response_model=PredictResponse)
async def predict_pipeline_failure(request: PredictRequest):
    """
    Predict whether a CI/CD pipeline run will pass or fail.

    Send commit context (repo, branch, author, files changed, etc.)
    and receive a failure probability with human-readable risk factors.

    **Example request:**
    ```json
    {
        "org_name": "NimanthaSupun",
        "repo_name": "WithOps",
        "branch": "feature/new-dashboard",
        "author": "supun",
        "event_type": "push",
        "files_changed": 15,
        "additions": 342,
        "deletions": 89,
        "commit_message": "feat: add new dashboard component"
    }
    ```
    """
    from core.predictor import predictor

    try:
        result = await predictor.predict(
            org_name=request.org_name,
            repo_name=request.repo_name,
            branch=request.branch,
            author=request.author,
            commit_sha=request.commit_sha,
            event_type=request.event_type,
            files_changed=request.files_changed,
            additions=request.additions,
            deletions=request.deletions,
            commit_message=request.commit_message,
        )

        return result

    except Exception as e:
        logger.error(f"❌ Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{org_name}/{repo_name}")
async def get_prediction_history(
    org_name: str,
    repo_name: str,
    limit: int = 50,
):
    """
    Get prediction history for a specific repository.
    Includes accuracy stats comparing predictions vs actual outcomes.
    """
    from database.config import db_manager
    from database.models import PredictionHistory
    from sqlalchemy import select, func

    try:
        async with db_manager.get_session() as session:
            # Get recent predictions
            result = await session.execute(
                select(PredictionHistory)
                .where(PredictionHistory.org_name == org_name)
                .where(PredictionHistory.repo_name == repo_name)
                .order_by(PredictionHistory.predicted_at.desc())
                .limit(limit)
            )
            records = result.scalars().all()

            predictions = []
            correct = 0
            total_with_outcome = 0

            for r in records:
                pred = {
                    "id": r.id,
                    "predicted_at": r.predicted_at.isoformat() if r.predicted_at else None,
                    "branch": r.branch,
                    "author": r.author,
                    "failure_probability": r.failure_probability,
                    "risk_level": r.risk_level,
                    "actual_conclusion": r.actual_conclusion,
                    "prediction_correct": r.prediction_correct,
                }
                predictions.append(pred)

                if r.prediction_correct is not None:
                    total_with_outcome += 1
                    if r.prediction_correct:
                        correct += 1

            # Compute stats
            total_count = await session.execute(
                select(func.count())
                .select_from(PredictionHistory)
                .where(PredictionHistory.org_name == org_name)
                .where(PredictionHistory.repo_name == repo_name)
            )

            stats = {
                "total_predictions": total_count.scalar(),
                "showing": len(predictions),
            }

            if total_with_outcome > 0:
                stats["verified_predictions"] = total_with_outcome
                stats["accuracy"] = round(correct / total_with_outcome, 4)

            return {
                "org_name": org_name,
                "repo_name": repo_name,
                "predictions": predictions,
                "stats": stats,
            }

    except Exception as e:
        logger.error(f"❌ Error fetching prediction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{org_name}")
async def get_org_prediction_history(org_name: str, limit: int = 50):
    """
    Get prediction history across all repos for an organization.
    """
    from database.config import db_manager
    from database.models import PredictionHistory
    from sqlalchemy import select

    try:
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(PredictionHistory)
                .where(PredictionHistory.org_name == org_name)
                .order_by(PredictionHistory.predicted_at.desc())
                .limit(limit)
            )
            records = result.scalars().all()

            predictions = [
                {
                    "id": r.id,
                    "repo_name": r.repo_name,
                    "predicted_at": r.predicted_at.isoformat() if r.predicted_at else None,
                    "branch": r.branch,
                    "author": r.author,
                    "failure_probability": r.failure_probability,
                    "risk_level": r.risk_level,
                    "risk_factors": r.risk_factors,
                    "recommendation": r.recommendation,
                }
                for r in records
            ]

            return {
                "org_name": org_name,
                "predictions": predictions,
                "total": len(predictions),
            }

    except Exception as e:
        logger.error(f"❌ Error fetching org prediction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
