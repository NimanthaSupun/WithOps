"""
Training API Routes for Pipeline Prediction Service

Endpoints:
  POST /generate-data     — Generate synthetic training data
  POST /train             — Trigger model training
  GET  /train/status      — Get last training result
  GET  /model/{org_name}  — Get model info for an organization
  GET  /feature-importance/{org_name} — Get feature importance data
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Training & Model Management"])


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================

class GenerateDataRequest(BaseModel):
    org_name: str = Field(default="NimanthaSupun", description="Organization name")
    num_runs: int = Field(default=1500, ge=50, le=5000, description="Number of synthetic runs")
    clear_existing: bool = Field(default=False, description="Clear existing data first")


class TrainRequest(BaseModel):
    org_name: str = Field(default="NimanthaSupun", description="Organization to train for")
    model_type: str = Field(
        default="random_forest",
        description="Model type: random_forest, xgboost, gradient_boosting"
    )


class GenerateDataResponse(BaseModel):
    status: str
    records_created: int
    org_name: str
    message: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/generate-data", response_model=GenerateDataResponse)
async def generate_synthetic_data(request: GenerateDataRequest):
    """
    Generate synthetic CI/CD workflow data for model training.

    This creates realistic workflow run records with embedded failure patterns
    that the ML model can learn. Use this when you don't have enough real
    historical data.

    Embedded patterns include:
    - Late-night commits fail more often
    - Large changesets (>15 files) have higher failure rates
    - Weekend commits are riskier
    - Some authors have higher failure rates
    - Failure cascades (recent failures increase next failure probability)
    """
    from core.synthetic_data import populate_database, clear_synthetic_data

    try:
        if request.clear_existing:
            deleted = await clear_synthetic_data(request.org_name)
            logger.info(f"🗑️ Cleared {deleted} existing records for {request.org_name}")

        records = await populate_database(
            num_runs=request.num_runs,
            org_name=request.org_name
        )

        return GenerateDataResponse(
            status="success",
            records_created=records,
            org_name=request.org_name,
            message=f"Generated {records} synthetic workflow runs for {request.org_name}. "
                    f"You can now train a model via POST /api/pipeline-prediction/train"
        )

    except Exception as e:
        logger.error(f"❌ Data generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train")
async def train_model(request: TrainRequest):
    """
    Train an ML model for pipeline failure prediction.

    This runs the full training pipeline:
    1. Loads workflow run data from the database
    2. Engineers 19 features per run
    3. Splits into 80% train / 20% test
    4. Trains a Random Forest or XGBoost classifier
    5. Evaluates with accuracy, precision, recall, F1, AUC-ROC
    6. Saves the model to disk and registers it in the database

    Prerequisites: You need at least 30 workflow runs in the database.
    Generate synthetic data first if needed.
    """
    if request.model_type not in ("random_forest", "xgboost", "gradient_boosting"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model_type: {request.model_type}. "
                   f"Choose from: random_forest, xgboost, gradient_boosting"
        )

    from core.trainer import trainer

    try:
        result = await trainer.train(
            org_name=request.org_name,
            model_type=request.model_type,
        )

        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result.get("error", "Training failed"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Training endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/train/status")
async def get_training_status():
    """Get the result of the last training run."""
    from core.trainer import trainer

    if trainer.last_training_result is None:
        return {
            "status": "no_training_run",
            "message": "No training has been performed yet. "
                       "Trigger training via POST /api/pipeline-prediction/train"
        }

    return trainer.last_training_result


@router.get("/model/{org_name}")
async def get_model_info(org_name: str):
    """
    Get information about the active model for an organization.
    Includes version, type, performance metrics, and training metadata.
    """
    from core.model_manager import model_manager

    metadata = model_manager.get_metadata(org_name)

    if metadata is None:
        # Try loading from database
        loaded = await model_manager.load_model_from_disk(org_name)
        if loaded:
            metadata = model_manager.get_metadata(org_name)

    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model found for organization '{org_name}'. "
                   f"Train a model first via POST /api/pipeline-prediction/train"
        )

    return {
        "org_name": org_name,
        "model_loaded": True,
        **metadata,
    }


@router.get("/feature-importance/{org_name}")
async def get_feature_importance(org_name: str):
    """
    Get feature importance data for the active model.
    Useful for understanding which factors most influence predictions.
    Returns features sorted by importance (descending).
    """
    from core.model_manager import model_manager

    metadata = model_manager.get_metadata(org_name)
    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail=f"No model found for '{org_name}'"
        )

    importance = metadata.get("feature_importance", {})
    sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

    return {
        "org_name": org_name,
        "model_version": metadata.get("version"),
        "feature_importance": [
            {"feature": name, "importance": score}
            for name, score in sorted_importance
        ],
    }


@router.get("/data/stats/{org_name}")
async def get_data_stats(org_name: str):
    """
    Get statistics about the training data available for an organization.
    """
    from database.config import db_manager
    from database.models import WorkflowRunHistory
    from sqlalchemy import select, func

    try:
        async with db_manager.get_session() as session:
            # Total records
            total_result = await session.execute(
                select(func.count())
                .select_from(WorkflowRunHistory)
                .where(WorkflowRunHistory.org_name == org_name)
            )
            total = total_result.scalar()

            if total == 0:
                return {
                    "org_name": org_name,
                    "total_runs": 0,
                    "message": "No data found. Generate synthetic data via "
                               "POST /api/pipeline-prediction/generate-data"
                }

            # Success/failure counts
            success_result = await session.execute(
                select(func.count())
                .select_from(WorkflowRunHistory)
                .where(WorkflowRunHistory.org_name == org_name)
                .where(WorkflowRunHistory.conclusion == "success")
            )
            successes = success_result.scalar()

            failure_result = await session.execute(
                select(func.count())
                .select_from(WorkflowRunHistory)
                .where(WorkflowRunHistory.org_name == org_name)
                .where(WorkflowRunHistory.conclusion.in_(["failure", "timed_out"]))
            )
            failures = failure_result.scalar()

            # Unique repos and authors
            repos_result = await session.execute(
                select(func.count(func.distinct(WorkflowRunHistory.repo_name)))
                .where(WorkflowRunHistory.org_name == org_name)
            )
            unique_repos = repos_result.scalar()

            authors_result = await session.execute(
                select(func.count(func.distinct(WorkflowRunHistory.actor_login)))
                .where(WorkflowRunHistory.org_name == org_name)
            )
            unique_authors = authors_result.scalar()

            # Date range
            date_range = await session.execute(
                select(
                    func.min(WorkflowRunHistory.created_at),
                    func.max(WorkflowRunHistory.created_at)
                ).where(WorkflowRunHistory.org_name == org_name)
            )
            min_date, max_date = date_range.one()

            return {
                "org_name": org_name,
                "total_runs": total,
                "successes": successes,
                "failures": failures,
                "failure_rate": round(failures / total * 100, 1) if total > 0 else 0,
                "unique_repos": unique_repos,
                "unique_authors": unique_authors,
                "date_range": {
                    "from": min_date.isoformat() if min_date else None,
                    "to": max_date.isoformat() if max_date else None,
                },
                "ready_for_training": total >= 30,
            }

    except Exception as e:
        logger.error(f"❌ Error getting data stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
