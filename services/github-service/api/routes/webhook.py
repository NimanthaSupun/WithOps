"""
GitHub Webhook Handler — Real-time App Installation Lifecycle Events

This endpoint receives GitHub App webhook events and keeps our database
in sync when users install, uninstall, or suspend our app.

Webhook URL configured in GitHub App settings:
  https://api.withops.com/webhooks/github

Supported events:
  - installation (action: created, deleted, suspend, unsuspend)
  - installation_repositories (action: added, removed)
  - workflow_run (action: completed → forwarded to pipeline-prediction-service)
  - ping

Security: Every request is verified using HMAC-SHA256 with the shared
GITHUB_WEBHOOK_SECRET before any database operation is performed.
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header
from sqlalchemy import select

from database import db_manager, OrganizationInstallation
from core.event_bus import event_bus
from core.redis_cache import cache
from core.github_client import github_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["GitHub Webhooks"])

# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def _verify_github_signature(payload_body: bytes, signature_header: Optional[str]) -> bool:
    """
    Verify the GitHub webhook HMAC-SHA256 signature.

    GitHub sends the signature in the header:
        X-Hub-Signature-256: sha256=<hex_digest>

    We compute the expected digest from the raw request body using our
    GITHUB_WEBHOOK_SECRET and compare them with a constant-time comparison
    to prevent timing attacks.

    Returns:
        True  — signature is valid
        False — signature is missing or does not match
    """
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.error("❌ GITHUB_WEBHOOK_SECRET is not configured — rejecting all webhooks")
        return False

    if not signature_header:
        logger.warning("⚠️ Webhook received without X-Hub-Signature-256 header")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning(f"⚠️ Unexpected signature format: {signature_header[:20]}")
        return False

    received_digest = signature_header[len("sha256="):]

    # Compute expected HMAC-SHA256
    expected_digest = hmac.new(
        webhook_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_digest, received_digest)


# ---------------------------------------------------------------------------
# Main webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/github")
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
):
    """
    Receive and process GitHub App webhook events.

    GitHub App webhook URL (configured in GitHub App settings):
        https://api.withops.com/webhooks/github

    This endpoint:
    1. Verifies the HMAC-SHA256 signature
    2. Dispatches to the correct event handler
    3. Always returns 200 OK quickly (GitHub retries on non-2xx)
    """
    # Read raw bytes BEFORE parsing — signature is over the raw body
    raw_body = await request.body()

    # --- Security gate: verify HMAC signature first ---
    if not _verify_github_signature(raw_body, x_hub_signature_256):
        logger.warning(
            f"⚠️ Webhook signature verification FAILED "
            f"| event={x_github_event} | delivery={x_github_delivery}"
        )
        # Return 401 so GitHub knows we rejected it (it won't retry on 4xx)
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse the JSON payload
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = x_github_event or "unknown"
    action = payload.get("action", "")
    delivery_id = x_github_delivery or "unknown"

    logger.info(
        f"📩 Webhook received | event={event_type} | action={action} "
        f"| delivery={delivery_id}"
    )

    # --- Dispatch by event type ---
    try:
        if event_type == "ping":
            await _handle_ping(payload)

        elif event_type == "installation":
            await _handle_installation_event(payload, action)

        elif event_type == "installation_repositories":
            await _handle_installation_repositories_event(payload, action)

        elif event_type == "workflow_run":
            await _handle_workflow_run_event(payload, action, raw_body, x_hub_signature_256)

        else:
            logger.info(f"ℹ️ Ignoring unhandled event type: {event_type}")

    except Exception as e:
        # Log the error but still return 200 so GitHub does not retry
        # (retries would cause duplicate processing)
        logger.error(
            f"❌ Error processing webhook event={event_type} action={action}: {e}",
            exc_info=True,
        )

    # GitHub expects a 2xx response quickly; return 200 always
    return {"status": "ok", "event": event_type, "action": action, "delivery": delivery_id}


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

async def _handle_ping(payload: dict):
    """Handle the ping event GitHub sends when you first configure a webhook."""
    zen = payload.get("zen", "")
    hook_id = payload.get("hook_id", "")
    logger.info(f"🏓 GitHub webhook PING received | hook_id={hook_id} | zen='{zen}'")


async def _handle_installation_event(payload: dict, action: str):
    """
    Handle GitHub App installation lifecycle events.

    Actions handled:
        deleted    — User removed our app from their org/account
        suspend    — User temporarily disabled our app
        unsuspend  — User re-enabled our app
        created    — (informational — real record is created via installation callback)
    """
    installation = payload.get("installation", {})
    installation_id = installation.get("id")
    account = installation.get("account", {})
    org_login = account.get("login")
    account_type = account.get("type", "")  # "Organization" or "User"

    if not installation_id:
        logger.warning("⚠️ Webhook payload missing installation.id — skipping")
        return

    logger.info(
        f"🔔 Installation event | action={action} | installation_id={installation_id} "
        f"| account={org_login} ({account_type})"
    )

    if action == "deleted":
        await _process_installation_deleted(installation_id, org_login, payload)

    elif action == "suspend":
        await _process_installation_status_change(installation_id, org_login, "suspended")

    elif action == "unsuspend":
        await _process_installation_status_change(installation_id, org_login, "active")

    elif action == "created":
        # The installation was created via GitHub UI (not through our callback).
        # Our /installation/callback handles the DB write, but if somehow a
        # user installs directly, we log it. A sync can pick it up later.
        logger.info(
            f"ℹ️ Installation created via webhook (not callback). "
            f"installation_id={installation_id}, org={org_login}. "
            f"DB record will be created by /installation/callback or /sync-installations."
        )

    else:
        logger.info(f"ℹ️ Unhandled installation action: {action}")


async def _process_installation_deleted(
    installation_id: int,
    org_login: Optional[str],
    payload: dict,
):
    """
    Core handler — called when a user removes our GitHub App from their org.

    Steps:
    1. Find OrganizationInstallation row by github_installation_id
    2. Mark it as 'deleted' (soft delete) and set uninstalled_at timestamp
    3. Invalidate Redis + in-memory caches for fresh data on next request
    4. Publish a Redis event so Events Hub can notify connected UI clients
    """
    logger.info(
        f"🗑️ Processing installation DELETED | installation_id={installation_id} | org={org_login}"
    )

    async with db_manager.get_session() as session:
        # Fetch the installation record
        result = await session.execute(
            select(OrganizationInstallation).where(
                OrganizationInstallation.github_installation_id == installation_id
            )
        )
        db_installation = result.scalar_one_or_none()

        if not db_installation:
            logger.warning(
                f"⚠️ No DB record found for installation_id={installation_id} "
                f"(org={org_login}). It may have already been removed."
            )
            # Still try to invalidate caches in case of stale data
            if org_login:
                await _invalidate_all_caches(org_login)
            return

        # Soft-delete: update status and timestamps
        previous_status = db_installation.status
        db_installation.status = "deleted"
        db_installation.uninstalled_at = datetime.utcnow()
        db_installation.updated_at = datetime.utcnow()

        await session.commit()

        logger.info(
            f"✅ Installation marked as DELETED in DB "
            f"| github_installation_id={installation_id} "
            f"| org={org_login} "
            f"| previous_status={previous_status}"
        )

        # Get the org login from DB if not provided by GitHub payload
        if not org_login and db_installation.organization:
            org_login = db_installation.organization.login

    # Invalidate caches so stale "app_installed=True" data is gone immediately
    if org_login:
        await _invalidate_all_caches(org_login)

    # Publish event so the Events Hub can push a real-time notification
    # to any connected frontend clients (dashboard will update automatically)
    await event_bus.publish({
        "type": "github.installation.deleted",
        "org_name": org_login,
        "data": {
            "installation_id": installation_id,
            "organization_login": org_login,
            "action": "deleted",
            "message": "GitHub App was uninstalled. Access revoked.",
        },
        "source": "github-service-webhook",
    })

    logger.info(
        f"📤 Published github.installation.deleted event for org={org_login}"
    )


async def _process_installation_status_change(
    installation_id: int,
    org_login: Optional[str],
    new_status: str,
):
    """
    Handle suspend / unsuspend actions.

    When suspended, the installation still exists but GitHub won't accept
    API calls using the installation access token. We reflect this in DB.
    """
    logger.info(
        f"🔄 Updating installation status | installation_id={installation_id} "
        f"| org={org_login} | new_status={new_status}"
    )

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(OrganizationInstallation).where(
                OrganizationInstallation.github_installation_id == installation_id
            )
        )
        db_installation = result.scalar_one_or_none()

        if not db_installation:
            logger.warning(
                f"⚠️ No DB record found for installation_id={installation_id} — cannot update status"
            )
            return

        db_installation.status = new_status
        db_installation.updated_at = datetime.utcnow()
        await session.commit()

        logger.info(
            f"✅ Installation status updated to '{new_status}' "
            f"| github_installation_id={installation_id}"
        )

    # Invalidate caches so UI reflects the new state immediately
    if org_login:
        await _invalidate_all_caches(org_login)

    # Broadcast real-time notification
    event_label = "suspended" if new_status == "suspended" else "unsuspended"
    await event_bus.publish({
        "type": f"github.installation.{event_label}",
        "org_name": org_login,
        "data": {
            "installation_id": installation_id,
            "organization_login": org_login,
            "status": new_status,
        },
        "source": "github-service-webhook",
    })


async def _handle_installation_repositories_event(payload: dict, action: str):
    """
    Handle installation_repositories events.

    GitHub fires this when repos are added to / removed from an installation.
    We log and invalidate cache so the workspace view refreshes.
    """
    installation = payload.get("installation", {})
    installation_id = installation.get("id")
    org_login = installation.get("account", {}).get("login")

    repos_added = [r.get("full_name") for r in payload.get("repositories_added", [])]
    repos_removed = [r.get("full_name") for r in payload.get("repositories_removed", [])]

    logger.info(
        f"📦 installation_repositories | action={action} | org={org_login} "
        f"| added={repos_added} | removed={repos_removed}"
    )

    # Invalidate workspace cache so next load picks up repo changes
    if org_login:
        await _invalidate_all_caches(org_login)

    # Publish event for real-time dashboard refresh
    await event_bus.publish({
        "type": "github.installation_repositories.changed",
        "org_name": org_login,
        "data": {
            "installation_id": installation_id,
            "action": action,
            "repositories_added": repos_added,
            "repositories_removed": repos_removed,
        },
        "source": "github-service-webhook",
    })


# ---------------------------------------------------------------------------
# Workflow Run handler — forwards to Pipeline Prediction Service
# ---------------------------------------------------------------------------

async def _handle_workflow_run_event(
    payload: dict,
    action: str,
    raw_body: bytes,
    signature: Optional[str],
):
    """
    Handle workflow_run events from GitHub Actions.

    When a workflow run completes, we:
    1. Forward the payload to the pipeline-prediction-service so it can
       update prediction outcomes (close the ML feedback loop)
    2. Publish a Redis event so the Events Hub can push real-time
       notifications to the predictor dashboard

    Actions:
        completed  — Workflow finished (success, failure, cancelled, etc.)
        requested  — New workflow run was requested
        in_progress — Workflow run started executing
    """
    workflow_run = payload.get("workflow_run", {})
    conclusion = workflow_run.get("conclusion", "")
    repo_full_name = workflow_run.get("repository", {}).get("full_name", "")
    run_id = workflow_run.get("id")
    workflow_name = workflow_run.get("name", "")

    logger.info(
        f"⚡ workflow_run event | action={action} | repo={repo_full_name} "
        f"| run_id={run_id} | conclusion={conclusion} | workflow={workflow_name}"
    )

    # Only forward completed runs to the prediction service
    if action != "completed":
        logger.debug(f"Skipping workflow_run action={action} (not completed)")
        return

    # ── 1. Forward to pipeline-prediction-service ──
    prediction_service_url = os.getenv(
        "PIPELINE_PREDICTION_SERVICE_URL",
        "http://pipeline-prediction-service:8009"
    )

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{prediction_service_url}/webhook/github/workflow-complete",
                content=raw_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature or "",
                    "X-GitHub-Event": "workflow_run",
                },
            )

            if response.status_code == 200:
                result = response.json()
                predictions_updated = result.get("predictions_updated", 0)
                logger.info(
                    f"✅ Pipeline prediction service notified | "
                    f"run_id={run_id} | predictions_updated={predictions_updated}"
                )
            else:
                logger.warning(
                    f"⚠️ Pipeline prediction service returned {response.status_code}: "
                    f"{response.text[:200]}"
                )

    except ImportError:
        logger.warning(
            "⚠️ httpx not installed — cannot forward to pipeline-prediction-service. "
            "Install with: pip install httpx"
        )
    except Exception as e:
        logger.warning(
            f"⚠️ Failed to forward workflow_run to pipeline-prediction-service: {e}"
        )

    # ── 2. Publish Redis event for real-time UI updates ──
    org_name = repo_full_name.split("/")[0] if "/" in repo_full_name else ""
    repo_name = repo_full_name.split("/")[1] if "/" in repo_full_name else ""

    await event_bus.publish({
        "type": "github.workflow_run.completed",
        "org_name": org_name,
        "data": {
            "run_id": run_id,
            "repo_name": repo_name,
            "repo_full_name": repo_full_name,
            "workflow_name": workflow_name,
            "conclusion": conclusion,
            "head_branch": workflow_run.get("head_branch", ""),
            "head_sha": workflow_run.get("head_commit", {}).get("sha", ""),
            "actor": workflow_run.get("actor", {}).get("login", ""),
            "event": workflow_run.get("event", ""),
            "run_number": workflow_run.get("run_number"),
            "created_at": workflow_run.get("created_at"),
            "updated_at": workflow_run.get("updated_at"),
        },
        "source": "github-service-webhook",
    })


# ---------------------------------------------------------------------------
# Cache invalidation helper
# ---------------------------------------------------------------------------

async def _invalidate_all_caches(org_login: str):
    """
    Purge all cached data for an org so the next request fetches fresh data.

    Clears:
      - Redis cache (persistent across service restarts)
      - In-memory cache inside GitHubClient (fast, per-process)
    """
    try:
        await cache.invalidate_organization_cache(org_login)
        logger.info(f"🗑️ Redis cache invalidated for org: {org_login}")
    except Exception as e:
        logger.warning(f"⚠️ Redis cache invalidation failed for {org_login}: {e}")

    try:
        github_client._clear_installation_cache(org_login)
        logger.info(f"🗑️ In-memory cache cleared for org: {org_login}")
    except Exception as e:
        logger.warning(f"⚠️ In-memory cache clear failed for {org_login}: {e}")
