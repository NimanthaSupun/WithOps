"""
GitHub Webhook Routes for Pipeline Prediction Service

Handles GitHub Actions workflow completion events and updates prediction outcomes.

Webhook Setup:
  1. GitHub Org Settings → Webhooks → Add Webhook
  2. Payload URL: https://withops.com/webhook/github/workflow-complete
  3. Content type: application/json
  4. Events: Workflow runs
  5. Active: ✓
"""

import logging
import hashlib
import hmac
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks"])


# ============================================================================
# WEBHOOK SIGNATURE VERIFICATION
# ============================================================================

def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature using HMAC-SHA256.
    
    GitHub sends: X-Hub-Signature-256: sha256=<hash>
    We compute:   sha256=hmac.new(secret, payload, sha256).hexdigest()
    
    If they match, the webhook is authentic.
    """
    expected_signature = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


# ============================================================================
# WEBHOOK ENDPOINT
# ============================================================================

@router.post("/webhook/github/workflow-complete")
async def handle_workflow_completion(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
):
    """
    GitHub webhook handler for workflow_run events.
    
    GitHub sends:
    ```json
    {
      "action": "completed",
      "workflow_run": {
        "id": 12345678,
        "name": "CI/CD Pipeline",
        "conclusion": "success" | "failure" | "cancelled" | "timed_out" | "neutral",
        "repository": {
          "full_name": "NimanthaSupun/WithOps",
          "name": "WithOps"
        },
        "head_branch": "main",
        "head_commit": {
          "id": "abc123def456...",
          "sha": "abc123def456...",
          "message": "feat: add new feature"
        },
        "created_at": "2026-04-10T15:30:00Z",
        "updated_at": "2026-04-10T15:35:00Z",
        "run_number": 42,
        "event": "push" | "pull_request" | "schedule",
        "status": "completed",
        "conclusion": "success" | "failure" | ...,
        "run_attempt": 1,
        "actor": {
          "login": "supun",
          "id": 1001
        }
      }
    }
    ```
    """
    import os
    from database.config import db_manager
    from database.models import WorkflowRunHistory, PredictionHistory
    from sqlalchemy import select
    
    try:
        # 1. Verify webhook signature
        payload = await request.body()
        webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
        
        if webhook_secret and not verify_github_signature(payload, x_hub_signature_256 or "", webhook_secret):
            logger.warning("❌ Invalid GitHub webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        data = await request.json()
        
        # 2. Extract relevant fields
        action = data.get("action")
        workflow_run = data.get("workflow_run", {})
        
        # Only process completed workflows
        if action != "completed":
            logger.debug(f"Skipping webhook action: {action}")
            return {"status": "skipped", "reason": f"action is {action}, waiting for completed"}
        
        run_id = workflow_run.get("id")
        conclusion = workflow_run.get("conclusion")  # success, failure, cancelled, timed_out, neutral
        repo_full_name = workflow_run.get("repository", {}).get("full_name", "")
        org_name, repo_name = repo_full_name.split("/") if "/" in repo_full_name else (None, None)
        head_sha = workflow_run.get("head_sha", "") or workflow_run.get("head_commit", {}).get("id", "")
        
        if not all([run_id, conclusion, org_name, repo_name, head_sha]):
            logger.warning(f"❌ Missing required fields in webhook: {data}")
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        logger.info(f"📡 Webhook received: {org_name}/{repo_name} run #{run_id} conclusion={conclusion}")
        
        # ────────────────────────────────────────────────────────────────
        # 3. Update WorkflowRunHistory with actual conclusion
        # ────────────────────────────────────────────────────────────────
        async with db_manager.get_session() as session:
            # Update or create workflow run record
            result = await session.execute(
                select(WorkflowRunHistory).where(WorkflowRunHistory.github_run_id == run_id)
            )
            run_record = result.scalar_one_or_none()
            
            if run_record:
                run_record.conclusion = conclusion
                run_record.status = "completed"
                run_record.updated_at = datetime.utcnow()
                run_record.completed_at = datetime.fromisoformat(
                    workflow_run.get("updated_at", "").replace("Z", "+00:00")
                ) if workflow_run.get("updated_at") else datetime.utcnow()
            else:
                # Create new record if doesn't exist (webhook arrived before data collection)
                run_record = WorkflowRunHistory(
                    organization_id=org_name,
                    org_name=org_name,
                    repo_name=repo_name,
                    repo_full_name=repo_full_name,
                    github_run_id=run_id,
                    workflow_name=workflow_run.get("name", ""),
                    workflow_path=workflow_run.get("path", ""),
                    run_number=workflow_run.get("run_number"),
                    event=workflow_run.get("event", ""),
                    status="completed",
                    conclusion=conclusion,
                    created_at=datetime.fromisoformat(
                        workflow_run.get("created_at", "").replace("Z", "+00:00")
                    ) if workflow_run.get("created_at") else datetime.utcnow(),
                    head_branch=workflow_run.get("head_branch", ""),
                    head_sha=head_sha,
                    commit_message=workflow_run.get("head_commit", {}).get("message", ""),
                    actor_login=workflow_run.get("actor", {}).get("login", ""),
                    actor_id=workflow_run.get("actor", {}).get("id"),
                )
                session.add(run_record)
            
            await session.flush()
            
            # ────────────────────────────────────────────────────────────────
            # 4. Update PredictionHistory records with actual outcome
            # ────────────────────────────────────────────────────────────────
            predictions = await session.execute(
                select(PredictionHistory).where(
                    (PredictionHistory.org_name == org_name) &
                    (PredictionHistory.repo_name == repo_name) &
                    (PredictionHistory.commit_sha == head_sha) &
                    (PredictionHistory.actual_conclusion == None)  # Only pending predictions
                )
            )
            
            prediction_records = predictions.scalars().all()
            
            for pred in prediction_records:
                # Determine if prediction was correct
                predicted_failure = pred.failure_probability > 0.5
                actual_failure = conclusion in ("failure", "timed_out")
                
                pred.actual_conclusion = conclusion
                pred.actual_completed_at = datetime.utcnow()
                pred.prediction_correct = (predicted_failure == actual_failure)
                
                logger.info(
                    f"  ✅ Updated prediction {pred.id}: "
                    f"predicted={'FAIL' if predicted_failure else 'PASS'} "
                    f"actual={'FAIL' if actual_failure else 'PASS'} "
                    f"correct={pred.prediction_correct}"
                )
            
            await session.commit()
            
            # ────────────────────────────────────────────────────────────────
            # 5. Publish event to event bus (for real-time updates)
            # ────────────────────────────────────────────────────────────────
            try:
                import redis
                r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), 
                               port=int(os.getenv("REDIS_PORT", 6379)))
                
                event_data = {
                    "org_name": org_name,
                    "repo_name": repo_name,
                    "run_id": run_id,
                    "conclusion": conclusion,
                    "predictions_updated": len(prediction_records),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                r.publish("pipeline.workflow_completed", str(event_data))
                logger.debug(f"Published workflow completion event: {event_data}")
            except Exception as e:
                logger.warning(f"⚠️ Could not publish event: {e}")
        
        logger.info(f"✅ Webhook processed: Updated {len(prediction_records)} predictions")
        
        return {
            "status": "success",
            "run_id": run_id,
            "conclusion": conclusion,
            "predictions_updated": len(prediction_records),
            "org_name": org_name,
            "repo_name": repo_name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK FOR WEBHOOK
# ============================================================================

@router.post("/webhook/github/ping")
async def webhook_ping():
    """GitHub sends this to test webhook connectivity."""
    logger.info("🏓 GitHub webhook ping received")
    return {"status": "webhook_ready", "service": "pipeline-prediction-service"}
