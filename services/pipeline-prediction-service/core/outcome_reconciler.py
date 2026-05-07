"""
Outcome Reconciliation Service for Pipeline Prediction

Periodically syncs with GitHub API to fill in missing pipeline outcomes.
This is a fallback for when webhooks don't arrive for any reason.

Runs daily to reconcile predictions older than 24 hours without outcomes.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


class OutcomeReconciler:
    """
    Reconciles pending predictions with actual pipeline outcomes from GitHub API.
    
    Flow:
    1. Find all predictions older than 24h without outcomes
    2. For each, query GitHub API to get actual run status
    3. Update PredictionHistory with actual_conclusion
    4. Compute prediction_correct
    5. Store in database
    """
    
    async def reconcile_all_orgs(self) -> Dict[str, int]:
        """
        Reconcile all organizations' pending predictions.
        Returns: {org_name: num_reconciled}
        """
        from database.config import db_manager
        from database.models import PredictionHistory
        from sqlalchemy import select
        
        results = {}
        
        try:
            async with db_manager.get_session() as session:
                # Get distinct orgs with pending predictions
                result = await session.execute(
                    select(PredictionHistory.org_name).distinct().where(
                        (PredictionHistory.actual_conclusion == None) &
                        (PredictionHistory.predicted_at < datetime.utcnow() - timedelta(hours=24))
                    )
                )
                
                orgs = result.scalars().all()
                
                for org in orgs:
                    count = await self.reconcile_org(org)
                    results[org] = count
                    logger.info(f"  {org}: Reconciled {count} predictions")
            
            total = sum(results.values())
            logger.info(f"✅ Reconciliation complete: {total} predictions updated across {len(results)} orgs")
            return results
        
        except Exception as e:
            logger.error(f"❌ Reconciliation error: {e}", exc_info=True)
            return results
    
    async def reconcile_org(self, org_name: str) -> int:
        """
        Reconcile all pending predictions for a specific organization.
        """
        from database.config import db_manager
        from database.models import PredictionHistory
        from sqlalchemy import select
        
        try:
            async with db_manager.get_session() as session:
                # Get pending predictions older than 24 hours
                result = await session.execute(
                    select(PredictionHistory).where(
                        (PredictionHistory.org_name == org_name) &
                        (PredictionHistory.actual_conclusion == None) &
                        (PredictionHistory.predicted_at < datetime.utcnow() - timedelta(hours=24))
                    ).limit(100)  # Process in batches
                )
                
                predictions = result.scalars().all()
                reconciled = 0
                
                for pred in predictions:
                    if pred.commit_sha:
                        success = await self._update_prediction_from_api(pred)
                        if success:
                            reconciled += 1
                
                if reconciled > 0:
                    await session.commit()
                
                return reconciled
        
        except Exception as e:
            logger.error(f"❌ Org reconciliation error for {org_name}: {e}", exc_info=True)
            return 0
    
    async def _update_prediction_from_api(self, pred: Any) -> bool:
        """
        Query GitHub API to get actual outcome for a prediction.
        Update the prediction record if found.
        """
        from core.data_collector import data_collector
        
        try:
            # Query GitHub API for this commit's workflow runs
            runs = await data_collector.fetch_workflow_runs_by_commit(
                org_name=pred.org_name,
                repo_name=pred.repo_name,
                commit_sha=pred.commit_sha
            )
            
            if not runs:
                logger.debug(f"No runs found for {pred.commit_sha}")
                return False
            
            # Get the most recent completed run
            completed_runs = [r for r in runs if r.get("status") == "completed"]
            
            if not completed_runs:
                logger.debug(f"No completed runs yet for {pred.commit_sha}")
                return False
            
            latest_run = sorted(
                completed_runs,
                key=lambda x: x.get("updated_at", ""),
                reverse=True
            )[0]
            
            conclusion = latest_run.get("conclusion")
            
            if not conclusion:
                logger.debug(f"No conclusion for run {latest_run.get('id')}")
                return False
            
            # Update prediction
            predicted_failure = pred.failure_probability > 0.5
            actual_failure = conclusion in ("failure", "timed_out")
            
            pred.actual_conclusion = conclusion
            pred.actual_completed_at = datetime.fromisoformat(
                latest_run.get("updated_at", "").replace("Z", "+00:00")
            ) if latest_run.get("updated_at") else datetime.utcnow()
            pred.prediction_correct = (predicted_failure == actual_failure)
            
            logger.debug(
                f"✅ Reconciled {pred.id}: "
                f"predicted={'FAIL' if predicted_failure else 'PASS'} "
                f"actual={'FAIL' if actual_failure else 'PASS'} "
                f"correct={pred.prediction_correct}"
            )
            
            return True
        
        except Exception as e:
            logger.warning(f"Could not reconcile prediction {pred.id}: {e}")
            return False


# Global instance
reconciler = OutcomeReconciler()


# ============================================================================
# STANDALONE RECONCILIATION SCHEDULER
# ============================================================================

async def schedule_reconciliation():
    """
    Run reconciliation periodically.
    Can be called from APScheduler or manually.
    """
    logger.info("🔄 Starting outcome reconciliation...")
    await reconciler.reconcile_all_orgs()
    logger.info("✅ Outcome reconciliation complete")
