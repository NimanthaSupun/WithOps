"""
DORA Event Handler
Processes GitHub workflow_run.completed events published to Redis
and persists them as deployment events for DORA metrics computation.

The GitHub Service already publishes events with type 'github.workflow_run.completed'
to the 'github_events' Redis channel. This handler subscribes to those events
and records them in the deployment_events table.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from database import db_manager
from database.dora_models import DeploymentEvent

logger = logging.getLogger(__name__)


class DORAEventHandler:
    """Handles GitHub workflow_run events for DORA metrics tracking."""

    async def handle_workflow_run_completed(self, event_data: Dict[str, Any]):
        """
        Process a github.workflow_run.completed event from the Redis event bus.

        Expected event_data structure (published by github-service webhook.py):
        {
            "type": "github.workflow_run.completed",
            "org_name": "my-org",
            "data": {
                "run_id": 12345,
                "repo_name": "my-repo",
                "repo_full_name": "my-org/my-repo",
                "workflow_name": "CI",
                "conclusion": "success",
                "head_branch": "main",
                "head_sha": "abc123...",
                "actor": "developer",
                "event": "push",
                "run_number": 42,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:05:00Z"
            }
        }
        """
        try:
            org_name = event_data.get("org_name", "")
            data = event_data.get("data", {})

            run_id = data.get("run_id")
            conclusion = data.get("conclusion", "")
            repo_name = data.get("repo_name", "")
            repo_full_name = data.get("repo_full_name", "")
            head_branch = data.get("head_branch", "")

            if not run_id or not conclusion:
                logger.warning("⚠️ DORA: Skipping event with missing run_id or conclusion")
                return

            # Skip cancelled/skipped runs — they don't count as deployments
            if conclusion in ("cancelled", "skipped", "neutral"):
                logger.debug(f"DORA: Skipping {conclusion} run {run_id} for {repo_full_name}")
                return

            # Parse timestamps
            started_at = self._parse_timestamp(data.get("created_at"))
            completed_at = self._parse_timestamp(data.get("updated_at"))

            # Calculate duration
            duration_seconds = None
            if started_at and completed_at:
                duration_seconds = int((completed_at - started_at).total_seconds())

            # Create deployment event record
            deployment = DeploymentEvent(
                org_name=org_name,
                repo_name=repo_name,
                repo_full_name=repo_full_name,
                workflow_run_id=run_id,
                workflow_name=data.get("workflow_name", ""),
                run_number=data.get("run_number"),
                commit_sha=data.get("head_sha", ""),
                branch=head_branch,
                trigger_event=data.get("event", ""),
                actor=data.get("actor", ""),
                conclusion=conclusion,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
            )

            async with db_manager.get_session() as session:
                session.add(deployment)

            logger.info(
                f"📊 DORA: Recorded deployment event | "
                f"repo={repo_full_name} | conclusion={conclusion} | "
                f"run_id={run_id} | branch={head_branch}"
            )

        except Exception as e:
            logger.error(f"❌ DORA: Failed to process workflow_run event: {e}", exc_info=True)

    @staticmethod
    def _parse_timestamp(ts_string: str) -> datetime:
        """Parse GitHub ISO 8601 timestamp string to datetime object."""
        if not ts_string:
            return None
        try:
            # GitHub timestamps: "2026-01-01T00:00:00Z"
            cleaned = ts_string.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        except (ValueError, AttributeError):
            return None


# Global instance
dora_event_handler = DORAEventHandler()
