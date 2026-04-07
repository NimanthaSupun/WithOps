"""
Predictor for Pipeline Prediction Service

Takes commit context, runs the trained model, and generates human-readable
risk factor explanations for why a pipeline might fail.
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


# Human-readable explanations for each feature
RISK_EXPLANATIONS = {
    "hour_of_day": {
        "check": lambda v: v >= 22 or v < 6,
        "message": lambda v: f"Late-night commit at {int(v)}:00 — failure rate is 3× higher after 10 PM",
    },
    "is_weekend": {
        "check": lambda v: v == 1,
        "message": lambda v: "Weekend commit — historically 2× more failures on weekends",
    },
    "is_business_hours": {
        "check": lambda v: v == 0,
        "message": lambda v: "Outside business hours — commits during 9-5 on weekdays are safer",
    },
    "files_changed": {
        "check": lambda v: v > 10,
        "message": lambda v: f"{int(v)} files changed — large changesets (>10 files) fail significantly more often",
    },
    "total_changes": {
        "check": lambda v: v > 300,
        "message": lambda v: f"{int(v)} total line changes — commits with >300 line changes have elevated risk",
    },
    "change_ratio": {
        "check": lambda v: v > 5,
        "message": lambda v: f"High addition-to-deletion ratio ({v:.1f}×) — mostly new code without cleanup",
    },
    "author_failure_rate": {
        "check": lambda v: v > 0.25,
        "message": lambda v: f"Author has {v:.0%} failure rate in recent history",
    },
    "repo_failure_rate_7d": {
        "check": lambda v: v > 0.20,
        "message": lambda v: f"Repository has {v:.0%} failure rate in the last 7 days",
    },
    "failures_last_24h": {
        "check": lambda v: v >= 2,
        "message": lambda v: f"{int(v)} failures in the last 24 hours — cascading instability detected",
    },
    "branch_type": {
        "check": lambda v: v == 3,  # hotfix
        "message": lambda v: "Hotfix branch — rushed fixes have higher failure rates",
    },
    "is_pull_request": {
        "check": lambda v: v == 0,
        "message": lambda v: "Direct push (no PR) — pull requests with code review reduce failures",
    },
}

RISK_LEVELS = {
    (0.0, 0.25): "low",
    (0.25, 0.50): "medium",
    (0.50, 0.75): "high",
    (0.75, 1.01): "critical",
}

RECOMMENDATIONS = {
    "low": "Low risk — this commit looks safe to push. Continue with confidence.",
    "medium": "Moderate risk — consider running tests locally before pushing.",
    "high": "High risk — strongly recommend running the full test suite locally. Review the risk factors below.",
    "critical": "Critical risk — this commit has multiple high-risk indicators. Consider breaking it into smaller changes and getting a code review.",
}


class Predictor:
    """
    Inference engine that:
    1. Loads the trained model from ModelManager
    2. Extracts features from the incoming request
    3. Runs model.predict_proba() to get failure probability
    4. Generates human-readable risk factor explanations
    5. Returns structured prediction with confidence and recommendations
    """

    def __init__(self):
        pass

    async def predict(
        self,
        org_name: str,
        repo_name: str,
        branch: str = "main",
        author: str = "unknown",
        commit_sha: str = "",
        event_type: str = "push",
        files_changed: int = 0,
        additions: int = 0,
        deletions: int = 0,
        commit_message: str = "",
    ) -> Dict[str, Any]:
        """
        Run a prediction for a given commit context.

        Returns a structured prediction with probability, risk level,
        risk factors, and recommendation.
        """
        from core.model_manager import model_manager
        from core.feature_engineer import feature_engineer

        # 1. Check if model is available
        model = model_manager.get_model(org_name)
        metadata = model_manager.get_metadata(org_name)

        if model is None:
            # Try loading from disk
            loaded = await model_manager.load_model_from_disk(org_name)
            if loaded:
                model = model_manager.get_model(org_name)
                metadata = model_manager.get_metadata(org_name)

        if model is None:
            return self._no_model_response(org_name)

        # 2. Build a run dict that matches what feature_engineer expects
        now = datetime.utcnow()
        run_data = {
            "org_name": org_name,
            "repo_name": repo_name,
            "head_branch": branch,
            "actor_login": author,
            "head_sha": commit_sha,
            "event": event_type,
            "files_changed": files_changed,
            "additions": additions,
            "deletions": deletions,
            "commit_message": commit_message,
            "created_at": now,
            "workflow_name": "CI/CD Pipeline",
            "status": "completed",
            "duration_seconds": None,
        }

        # 3. Get historical context from database
        history = await self._get_recent_history(org_name, repo_name)

        # 4. Extract features
        X = feature_engineer.transform_single(run_data, history)

        # 5. Run prediction
        failure_prob = float(model.predict_proba(X)[0][1])
        success_prob = 1.0 - failure_prob

        # 6. Determine risk level
        risk_level = self._get_risk_level(failure_prob)

        # 7. Generate risk factors
        feature_names = metadata.get("feature_names", [])
        feature_importance = metadata.get("feature_importance", {})
        risk_factors = self._generate_risk_factors(
            X[0], feature_names, feature_importance, failure_prob
        )

        # 8. Get recommendation
        recommendation = RECOMMENDATIONS.get(risk_level, RECOMMENDATIONS["medium"])

        # 9. Store prediction in history
        prediction_record = await self._save_prediction(
            org_name=org_name,
            repo_name=repo_name,
            branch=branch,
            commit_sha=commit_sha,
            author=author,
            failure_prob=failure_prob,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendation=recommendation,
            model_version=metadata.get("version"),
            model_type=metadata.get("model_type"),
        )

        return {
            "prediction": {
                "failure_probability": round(failure_prob, 4),
                "success_probability": round(success_prob, 4),
                "risk_level": risk_level,
                "confidence": self._calculate_confidence(failure_prob),
            },
            "risk_factors": risk_factors,
            "recommendation": recommendation,
            "context": {
                "org_name": org_name,
                "repo_name": repo_name,
                "branch": branch,
                "author": author,
                "files_changed": files_changed,
                "additions": additions,
                "deletions": deletions,
            },
            "model_info": {
                "version": metadata.get("version"),
                "type": metadata.get("model_type"),
                "accuracy": metadata.get("metrics", {}).get("accuracy"),
            },
            "prediction_id": prediction_record,
            "predicted_at": now.isoformat(),
        }

    # ════════════════════════════════════════════════════════════════════════
    # RISK FACTOR GENERATION
    # ════════════════════════════════════════════════════════════════════════

    def _generate_risk_factors(
        self,
        feature_vector: np.ndarray,
        feature_names: List[str],
        feature_importance: Dict[str, float],
        failure_prob: float,
    ) -> List[Dict[str, Any]]:
        """
        Generate human-readable risk factors by combining:
        - Feature values (what the model sees)
        - Feature importance (how much each feature matters)
        - Rule-based explanations (what it means in plain English)
        """
        factors = []

        for i, name in enumerate(feature_names):
            if i >= len(feature_vector):
                break

            value = feature_vector[i]
            importance = feature_importance.get(name, 0.0)

            # Check if this feature triggers a risk explanation
            if name in RISK_EXPLANATIONS:
                rule = RISK_EXPLANATIONS[name]
                if rule["check"](value):
                    factors.append({
                        "factor": name.replace("_", " ").title(),
                        "detail": rule["message"](value),
                        "importance": round(importance, 4),
                        "value": round(float(value), 2),
                    })

        # Sort by importance (most impactful first)
        factors.sort(key=lambda x: x["importance"], reverse=True)

        # Return top 5 most important factors
        return factors[:5]

    # ════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _get_risk_level(self, probability: float) -> str:
        """Map probability to risk level string."""
        for (low, high), level in RISK_LEVELS.items():
            if low <= probability < high:
                return level
        return "medium"

    def _calculate_confidence(self, probability: float) -> float:
        """
        Confidence is highest when probability is near 0 or 1,
        and lowest when near 0.5 (uncertain).
        """
        return round(abs(probability - 0.5) * 2, 4)

    def _no_model_response(self, org_name: str) -> Dict[str, Any]:
        """Return a response when no model is available."""
        from datetime import datetime
        return {
            "prediction": {
                "failure_probability": 0.5,
                "success_probability": 0.5,
                "risk_level": "unknown",
                "confidence": 0,
            },
            "risk_factors": [
                {
                    "factor": "No trained model",
                    "detail": f"No ML model has been trained for '{org_name}' yet. Generate synthetic data and train a model first.",
                    "importance": 1.0,
                }
            ],
            "recommendation": (
                f"No trained model available for '{org_name}'. "
                f"Generate data first: POST /api/pipeline-prediction/generate-data, "
                f"then train: POST /api/pipeline-prediction/train"
            ),
            "context": {
                "org_name": org_name,
                "model_status": "not_trained",
            },
            "model_info": {
                "version": "0.0.0",
                "type": "none",
            },
            "prediction_id": None,
            "predicted_at": datetime.utcnow().isoformat(),
        }

    async def _get_recent_history(
        self, org_name: str, repo_name: str, limit: int = 200
    ) -> List[Dict]:
        """Fetch recent workflow run history from DB for context features."""
        try:
            from database.config import db_manager
            from database.models import WorkflowRunHistory
            from sqlalchemy import select

            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(WorkflowRunHistory)
                    .where(WorkflowRunHistory.org_name == org_name)
                    .order_by(WorkflowRunHistory.created_at.desc())
                    .limit(limit)
                )
                records = result.scalars().all()

                return [
                    {
                        "repo_name": r.repo_name,
                        "actor_login": r.actor_login,
                        "conclusion": r.conclusion,
                        "created_at": r.created_at,
                        "duration_seconds": r.duration_seconds,
                        "status": r.status,
                    }
                    for r in records
                ]
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch history: {e}")
            return []

    async def _save_prediction(self, **kwargs) -> Optional[str]:
        """Save prediction to history table for auditing."""
        try:
            from database.config import db_manager
            from database.models import PredictionHistory

            record = PredictionHistory(
                org_name=kwargs["org_name"],
                repo_name=kwargs["repo_name"],
                branch=kwargs.get("branch"),
                commit_sha=kwargs.get("commit_sha"),
                author=kwargs.get("author"),
                failure_probability=kwargs["failure_prob"],
                risk_level=kwargs["risk_level"],
                risk_factors=kwargs.get("risk_factors"),
                recommendation=kwargs.get("recommendation"),
                model_version=kwargs.get("model_version"),
                model_type=kwargs.get("model_type"),
            )

            async with db_manager.get_session() as session:
                session.add(record)
                await session.commit()
                return record.id

        except Exception as e:
            logger.warning(f"⚠️ Could not save prediction history: {e}")
            return None


# Global instance
predictor = Predictor()
