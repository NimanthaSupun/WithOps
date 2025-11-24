"""
GitHub Routes - Proxy to GitHub Service
This file proxies requests to the GitHub microservice
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from core.security import get_current_user
from core.github_service_client import github_service_client
from core.user_storage_db import (
    record_organization_installation,
    get_user_installed_organizations,
    is_user_authorized_for_organization
)
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# ORGANIZATION DISCOVERY & INSTALLATION
# ============================================================================

@router.get("/organizations/discover")
async def start_organization_discovery(current_user: str = Depends(get_current_user)):
    """
    Start GitHub organization discovery process
    Proxies to GitHub Service
    """
    try:
        logger.info(f"Organization discovery requested by user: {current_user}")
        result = await github_service_client.start_organization_discovery()
        return result
    except Exception as e:
        logger.error(f"Error in organization discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizations/callback")
@router.post("/organizations/callback")
async def handle_organization_callback(
    code: str = Query(...),
    state: str = Query(None),
    current_user: str = Depends(get_current_user)
):
    """
    Handle OAuth callback from organization discovery
    Proxies to GitHub Service
    """
    try:
        logger.info(f"Organization callback for user: {current_user}")
        result = await github_service_client.handle_organization_callback(code, state)
        return result
    except Exception as e:
        logger.error(f"Error in organization callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organizations/{org_name}/install")
async def start_app_installation(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Generate GitHub App installation URL with user state
    """
    try:
        logger.info(f"App installation requested for {org_name} by {current_user}")
        
        # Create state parameter with user_id|org_name and base64 encode it
        import base64
        state_data = f"{current_user}|{org_name}"
        encoded_state = base64.urlsafe_b64encode(state_data.encode()).decode()
        
        # Pass state to GitHub Service
        result = await github_service_client.start_app_installation(org_name, encoded_state)
        return result
    except Exception as e:
        logger.error(f"Error generating installation URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organizations/{org_name}/sync-realtime")
async def sync_organization_realtime(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Real-time sync organization data and push updates via WebSocket
    """
    try:
        # Quick auth check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Proxy to GitHub service
        result = await github_service_client._make_request(
            "POST",
            f"/api/github/organizations/{org_name}/sync-realtime"
        )
        
        # Send WebSocket updates if there are changes
        if result.get("has_changes"):
            from core.websocket_manager import websocket_manager
            await websocket_manager.send_to_user(current_user, {
                "type": "workspace_changes",
                "organization": org_name,
                "changes": result.get("changes"),
                "total_changes": (
                    len(result.get("changes", {}).get("repositories", {}).get("added", [])) +
                    len(result.get("changes", {}).get("repositories", {}).get("removed", [])) +
                    len(result.get("changes", {}).get("workflows", {}).get("added", [])) +
                    len(result.get("changes", {}).get("workflows", {}).get("removed", []))
                )
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Real-time sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Real-time sync failed: {str(e)}")


@router.get("/installation/callback")
@router.post("/installation/callback")
async def handle_installation_callback(
    installation_id: int = Query(..., description="Installation ID from GitHub"),
    setup_action: str = Query(..., description="Setup action from GitHub"),
    state: str = Query(None, description="State parameter"),
    request: Request = None,
):
    """
    Handle GitHub App installation callback
    Proxies to GitHub Service and records installation in database
    """
    try:
        logger.info(f"Installation callback received: installation_id={installation_id}, setup_action={setup_action}, state={state}")
        
        # Extract user from state
        user_id = None
        org_name_from_state = None
        
        if state:
            try:
                import base64
                decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
                if '|' in decoded_state:
                    parts = decoded_state.rsplit('|', 1)
                    user_id = parts[0]
                    if len(parts) > 1:
                        org_name_from_state = parts[1]
                    logger.info(f"✅ Decoded state: user={user_id}, org={org_name_from_state}")
                else:
                    user_id = decoded_state
                    logger.info(f"✅ Decoded state (old format): user={user_id}")
            except Exception as decode_error:
                logger.warning(f"⚠️ Base64 decode failed: {decode_error}")
                if state.startswith('install_'):
                    org_name_from_state = state.replace('install_', '')
                    logger.info(f"✅ Extracted org from old format state: {org_name_from_state}")
        
        if not user_id:
            logger.error("❌ Cannot determine user from state parameter")
            raise HTTPException(status_code=400, detail="Invalid state parameter - cannot determine user")
        
        # Call GitHub Service to process the callback
        result = await github_service_client.handle_installation_callback(
            installation_id, setup_action, state
        )
        
        # Extract org from result
        org_name = result.get("organization", {}).get("login")
        if not org_name:
            org_name = org_name_from_state
        
        # Record installation in database
        if user_id and org_name:
            installation_data = {
                "installation_id": installation_id,
                "organization": result.get("organization", {}),
                "permissions": result.get("permissions", {}),
                "events": result.get("events", []),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at")
            }
            
            try:
                await record_organization_installation(user_id, org_name, installation_data)
                logger.info(f"✅ Installation recorded in database for {org_name} by user {user_id}")
            except Exception as db_error:
                logger.error(f"❌ Database recording failed: {db_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to record installation in database: {db_error}"
                )
        else:
            logger.warning(f"⚠️ Cannot record installation - user_id={user_id}, org_name={org_name}")
            raise HTTPException(status_code=400, detail="Missing user or organization information")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Installation callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-organizations")
async def get_my_organizations(
    request: Request,
    current_user: str = Depends(get_current_user),
    cleanup: bool = False
):
    """
    Get organizations that the current user has installed and can access
    Proxies to GitHub Service with authentication
    """
    try:
        logger.info(f"✅ Proxying /my-organizations request for user: {current_user}")
        
        # Forward Authorization header to github-service
        auth_header = request.headers.get("Authorization")
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        
        # Proxy request to github-service
        result = await github_service_client.get_my_organizations(
            cleanup=cleanup,
            headers=headers
        )
        
        logger.info(f"✅ Returned {result.get('total_count', 0)} organizations for user {current_user}")
        return result
        
    except Exception as e:
        logger.error(f"Error proxying my-organizations request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GITHUB WEBHOOKS
# ============================================================================

@router.post("/webhooks")
async def handle_github_webhook(
    request: Request
):
    """
    Handle GitHub App webhooks (installation events)
    
    Setup Instructions:
    1. Go to: https://github.com/settings/apps/YOUR_APP/advanced
    2. Set Webhook URL: https://YOUR_DOMAIN/api/github/webhooks
    3. Enable events: Installation (created, deleted, suspend, unsuspend)
    4. For local testing, use ngrok: ngrok http 8000
       Then set webhook URL: https://YOUR-NGROK-URL/api/github/webhooks
    """
    try:
        payload = await request.json()
        event_type = request.headers.get("X-GitHub-Event")
        delivery_id = request.headers.get("X-GitHub-Delivery")
        
        logger.info(f"📥 Webhook received: {event_type} (delivery: {delivery_id})")
        
        if event_type == "ping":
            # GitHub sends this to test the webhook
            logger.info("✅ Webhook ping successful")
            return {"status": "success", "message": "Pong! Webhook is configured correctly"}
        
        if event_type == "installation":
            action = payload.get("action")
            installation = payload.get("installation", {})
            installation_id = installation.get("id")
            repositories = payload.get("repositories", [])
            sender = payload.get("sender", {})
            
            logger.info(f"📦 Installation event: {action} | ID: {installation_id} | Repos: {len(repositories)} | Sender: {sender.get('login')}")
            
            if action == "deleted":
                # Handle app uninstallation
                from database.config import db_manager
                from database.operations import installation_repo
                
                async with db_manager.get_session() as session:
                    success = await installation_repo.mark_installation_deleted(session, installation_id)
                    await session.commit()
                
                if success:
                    logger.info(f"✅ Marked installation {installation_id} as deleted in database")
                    return {
                        "status": "success", 
                        "message": f"Installation {installation_id} marked as deleted",
                        "action": "deleted"
                    }
                else:
                    logger.warning(f"⚠️ Installation {installation_id} not found in database")
                    return {
                        "status": "not_found", 
                        "message": "Installation not found, may have been already removed"
                    }
            
            elif action == "created":
                # Handle new installation - log it
                logger.info(f"✅ New installation created: {installation_id}")
                return {
                    "status": "success", 
                    "message": "New installation detected, will be recorded on first access"
                }
            
            elif action == "suspend":
                # Handle app suspension
                from database.config import db_manager
                from database.operations import installation_repo
                
                async with db_manager.get_session() as session:
                    success = await installation_repo.suspend_installation(session, installation_id)
                    await session.commit()
                
                logger.info(f"✅ Suspended installation {installation_id}")
                return {"status": "success", "message": "Installation suspended"}
            
            elif action == "unsuspend":
                # Handle app unsuspension
                from database.config import db_manager
                from database.operations import installation_repo
                
                async with db_manager.get_session() as session:
                    success = await installation_repo.unsuspend_installation(session, installation_id)
                    await session.commit()
                
                logger.info(f"✅ Unsuspended installation {installation_id}")
                return {"status": "success", "message": "Installation unsuspended"}
            
            else:
                logger.info(f"ℹ️ Unhandled installation action: {action}")
                return {"status": "success", "message": f"Action '{action}' acknowledged but not processed"}
        
        # Handle other event types
        logger.info(f"ℹ️ Unhandled webhook event type: {event_type}")
        return {"status": "success", "message": f"Event '{event_type}' received"}
        
    except Exception as e:
        logger.error(f"❌ Error handling webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============================================================================
# WORKSPACE OPERATIONS
# ============================================================================

@router.get("/workspace/{org_name}")
async def get_organization_workspace(
    org_name: str,
    force_fresh: bool = Query(False),
    current_user: str = Depends(get_current_user)
):
    """
    Get organization workspace data with security checks
    *** SECURITY: Only allows access to organizations installed by the current user ***
    """
    try:
        # Validate organization name
        if not org_name or org_name.strip() == '' or org_name == 'undefined' or org_name == 'null':
            logger.error(f"❌ Invalid organization name provided: '{org_name}' (user: {current_user})")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid organization name: '{org_name}'. Organization name cannot be empty, 'undefined', or 'null'."
            )
        
        org_name = org_name.strip()
        logger.info(f"🌐 Getting workspace for {org_name} (user: {current_user})")
        
        # CRITICAL SECURITY CHECK: Verify user has permission to access this organization
        from core.user_storage_db import is_user_authorized_for_organization
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        
        if not user_authorized:
            logger.error(f"❌ SECURITY VIOLATION: User {current_user} denied access to {org_name}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'. This organization may have been installed by another user or the app may not be installed."
            )
        
        # User is authorized, proceed with workspace fetch
        logger.info(f"✅ User {current_user} authorized for {org_name}")
        result = await github_service_client.get_organization_workspace(org_name, force_fresh)
        
        # Add authorization info to response
        result["access_authorized"] = True
        result["authorized_user"] = current_user
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/installations")
async def get_installations(current_user: str = Depends(get_current_user)):
    """
    Get all GitHub App installations
    Proxies to GitHub Service
    """
    try:
        result = await github_service_client.get_installations()
        return result
    except Exception as e:
        logger.error(f"Error getting installations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizations/{org_name}/stats")
async def get_organization_stats(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get organization statistics
    Proxies to GitHub Service
    """
    try:
        result = await github_service_client.get_organization_stats(org_name)
        return result
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WORKFLOW OPERATIONS
# ============================================================================

@router.get("/workspace/{org_name}/workflow/{repo_name}/{workflow_path:path}")
async def get_workflow_content(
    org_name: str,
    repo_name: str,
    workflow_path: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get workflow file content
    Proxies to GitHub Service
    """
    try:
        result = await github_service_client.get_workflow_content(org_name, repo_name, workflow_path)
        return result
    except Exception as e:
        logger.error(f"Error getting workflow content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{org_name}/workflows/detailed")
async def get_detailed_workflows(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get detailed workflow information - Proxies to GitHub Service
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Proxy to GitHub service
        result = await github_service_client.get_organization_workflows_detailed(org_name)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detailed workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{org_name}/actions/paginated")
async def get_actions_paginated(
    org_name: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    current_user: str = Depends(get_current_user)
):
    """
    Get paginated GitHub Actions - Proxies to GitHub Service
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Proxy to GitHub service
        result = await github_service_client.get_organization_actions_paginated(
            org_name, page=page, per_page=per_page, search=search
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paginated actions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{org_name}/actions/detailed")
async def get_organization_actions(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get all GitHub Actions from organization workflows
    Proxies to GitHub Service
    """
    try:
        result = await github_service_client.get_organization_actions(org_name)
        return result
    except Exception as e:
        logger.error(f"Error getting actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace/{org_name}/actions/create-pr")
async def create_action_update_pr(
    org_name: str,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """
    Create a pull request to update a single outdated GitHub Action
    """
    try:
        # Check user authorization
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"User {current_user} is not authorized to access organization {org_name}"
            )
        
        # Proxy to GitHub service
        result = await github_service_client._make_request(
            "POST",
            f"/api/github/workspace/{org_name}/actions/create-pr",
            json=request
        )
        return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating action update PR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create pull request: {str(e)}")


@router.post("/workspace/{org_name}/actions/create-bulk-pr")
async def create_bulk_action_update_pr(
    org_name: str,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """
    Create a pull request to update multiple outdated GitHub Actions in a single workflow
    """
    try:
        # Check user authorization
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"User {current_user} is not authorized to access organization {org_name}"
            )
        
        # Proxy to GitHub service
        result = await github_service_client._make_request(
            "POST",
            f"/api/github/workspace/{org_name}/actions/create-bulk-pr",
            json=request
        )
        return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bulk action update PR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create bulk pull request: {str(e)}")


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

@router.delete("/workspace/{org_name}/cache")
async def clear_organization_cache(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Clear cache for organization
    Proxies to GitHub Service
    """
    try:
        result = await github_service_client.clear_organization_cache(org_name)
        return result
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def github_service_health():
    """Check GitHub Service health"""
    try:
        result = await github_service_client.health_check()
        return {
            "status": "healthy",
            "github_service": result
        }
    except Exception as e:
        logger.error(f"GitHub Service health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
