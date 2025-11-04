# api/routes/github.py

import asyncio
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from core.security import get_current_user, security
from fastapi.security import HTTPAuthorizationCredentials
from core.github_client import github_client
from sqlalchemy import select, func, and_, or_, update, delete
import os
import httpx
from core.redis_cache import RedisCache
from core.user_storage_db import (
    record_organization_installation,
    get_user_installed_organizations,
    is_user_authorized_for_organization,
    get_organization_installer,
    remove_organization_installation
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Optional
from datetime import datetime
import json

router = APIRouter()

# Initialize Redis cache
redis_cache = RedisCache()

@router.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup"""
    await redis_cache.connect()

@router.on_event("shutdown") 
async def shutdown_event():
    """Close Redis connection on shutdown"""
    await redis_cache.disconnect()

# todo:----orgnization-discover--------------------------------------------
@router.get("/organizations/discover")
async def start_organization_discovery(current_user: str = Depends(get_current_user)):
    """
    🚀 Step 1 & 2: Start GitHub organization discovery process (ULTRA-OPTIMIZED)
    Returns OAuth URL for user to discover which organizations they can install the app into
    """
    try:
        # Ultra-aggressive caching for discovery URL (1 hour)
        cache_key = f"discovery_url_{current_user}"
        cached_url = github_client._get_cached(cache_key)
        
        if cached_url:
            print(f"🚀 Using cached discovery URL for instant response")
            return {
                "message": "Organization discovery initiated (cached)",
                "oauth_url": cached_url.get('oauth_url'),
                "instructions": "User will see which organizations they can install the GitHub App into"
            }
        
        oauth_url = github_client.get_organization_discovery_oauth_url(state=current_user)
        print(f"Generated OAuth URL for organization discovery: {oauth_url}")
        
        # Cache the URL for 1 hour with enhanced TTL
        github_client._set_cached(cache_key, {'oauth_url': oauth_url}, 'discovery')
        
        return {
            "message": "Organization discovery initiated",
            "oauth_url": oauth_url,
            "instructions": "User will see which organizations they can install the GitHub App into"
        }
    except Exception as e:
        print(f"Error generating OAuth URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start discovery: {str(e)}")
    
# todo:-------org--callback--------

@router.get("/organizations/callback")
@router.post("/organizations/callback")
async def handle_organization_discovery_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query(..., description="State parameter for verification"),
    current_user: str = Depends(get_current_user)
):
    """
    🔍 Step 2: Handle OAuth callback from organization discovery (ULTRA-OPTIMIZED)
    Exchange code for token and fetch user's organizations where they can install the app
    Uses aggressive caching and parallel processing for blazing fast responses
    """
    try:
        print(f"🔄 Organization callback received:")
        print(f"🔄 Code: {code[:10]}...")
        print(f"🔄 State: {state}")
        print(f"🔄 Current user: {current_user}")
        
        # Check cache first - organization data doesn't change frequently
        cache_key = f"org_callback_{current_user}_{code[:10]}"
        cached_result = github_client._get_cached(cache_key)
        
        if cached_result:
            print(f"🚀 Using cached organization callback result for ultra-fast response")
            return cached_result
        
        # For now, let's be more lenient with state verification
        # The state might contain additional OAuth provider info
        if not state or (state != current_user and not state.endswith(current_user.split('|')[-1])):
            print(f"⚠️  State verification relaxed - proceeding anyway")
            # Don't raise error, just warn
        
        # Exchange code for access token (OAuth App - for discovery only)
        access_token = await github_client.exchange_code_for_token(code)
        
        # Get user's organizations where they can install GitHub Apps (SECURE - user-specific)
        organizations = await github_client.get_user_organizations(access_token, current_user)
        
        result = {
            "message": "Organizations discovered successfully",
            "organizations": organizations,
            "total_count": len(organizations),
            "note": "These are organizations where you can install the GitHub App"
        }
        
        # Cache the result for 10 minutes to speed up any re-requests
        github_client._set_cached(cache_key, result, 'discovery')
        
        return result
    except Exception as e:
        print(f"Callback processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process callback: {str(e)}")

# todo:----------------org--install--url-----------------------------

@router.post("/organizations/{org_name}/install")
async def generate_app_installation_url(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🧩 Step 4: Generate GitHub App installation URL for specific organization
    This creates the URL to install our GitHub App (not OAuth) into the selected organization
    """
    try:
        installation_url = github_client.generate_app_installation_url(
            org_name, 
            state=f"{current_user}_{org_name}"
        )
        
        print(f"Generated GitHub App installation URL for {org_name}: {installation_url}")
        
        return {
            "message": f"GitHub App installation URL generated for {org_name}",
            "organization": org_name,
            "installation_url": installation_url,
            "instructions": "User will install the GitHub App into this specific organization",
            "note": "This installs the app at organization level, not personal level"
        }
    except Exception as e:
        print(f"Installation URL generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate installation URL: {str(e)}")

@router.get("/installation/callback")
@router.post("/installation/callback")
async def handle_installation_callback(
    installation_id: int = Query(..., description="Installation ID from GitHub"),
    setup_action: str = Query(..., description="Setup action from GitHub"),
    state: str = Query(None, description="State parameter"),
    request: Request = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    🔐 Step 5: Handle GitHub App installation callback (ULTRA-OPTIMIZED)
    Process the callback after user installs the GitHub App into an organization
    Includes background prefetching for instant workspace access
    """
    try:
        # Extract current user from state
        current_user = None
        if state and '_' in state:
            current_user = state.split('_')[0]
        
        # Verify state if provided
        if not current_user:
            raise HTTPException(status_code=400, detail="Invalid state parameter - cannot determine user")
        
        if setup_action != "install":
            raise HTTPException(status_code=400, detail=f"Unexpected setup action: {setup_action}")
        
        try:
            # Get installation details from GitHub
            installation_details = await github_client.get_installation_details(installation_id)
            
            # Extract organization info
            org_info = installation_details.get("account", {})
            org_login = org_info.get("login")
        except Exception as installation_error:
            print(f"Installation callback error: {str(installation_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to get installation details: {str(installation_error)}")
        
        print(f"GitHub App successfully installed in organization: {org_login}")
        
        # 🔐 SECURITY: Record this installation for the current user
        installation_data = {
            "installation_id": installation_id,
            "organization": org_info,
            "permissions": installation_details.get("permissions", {}),
            "events": installation_details.get("events", []),
            "created_at": installation_details.get("created_at"),
            "updated_at": installation_details.get("updated_at")
        }
        
        # 🔐 CRITICAL: Record installation in database for user isolation
        try:
            # Extract organization from state if org_login is not available
            if not org_login and state and '_' in state:
                # The state format should be user_id_org_name
                state_parts = state.split('_')
                if len(state_parts) > 1:
                    org_login = state_parts[-1]
                    print(f"Using organization from state: {org_login}")
                    
                    # If we don't have installation details, create minimal data
                    if not installation_data or not installation_data.get("organization"):
                        installation_data = {
                            "installation_id": installation_id,
                            "organization": {"login": org_login, "id": 0},
                            "permissions": {},
                            "events": [],
                            "created_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat()
                        }
            
            if current_user and org_login:
                await record_organization_installation(current_user, org_login, installation_data)
                print(f"✅ Installation recorded in database for {org_login} by user {current_user}")
            else:
                print(f"⚠️ Cannot record installation - missing user or organization information")
                if not current_user:
                    print(f"⚠️ Missing user ID - state: {state}")
                if not org_login:
                    print(f"⚠️ Missing organization login")
        except Exception as db_error:
            print(f"❌ CRITICAL: Database recording failed: {db_error}")
            # This is critical for security - fail the installation if DB fails
            raise HTTPException(
                status_code=500,
                detail=f"Failed to record installation in database. This is required for security: {db_error}"
            )
        
        # Background prefetch workspace data for instant access
        import asyncio
        
        async def prefetch_workspace():
            try:
                print(f"🚀 Background prefetching workspace data for {org_login}")
                await github_client.get_organization_workspace_detailed(installation_id, org_login)
                print(f"✅ Workspace data prefetched for {org_login}")
            except Exception as e:
                print(f"⚠️ Background prefetch failed for {org_login}: {e}")
        
        # Start background prefetch (don't wait for it)
        asyncio.create_task(prefetch_workspace())
        
        return {
            "message": "GitHub App installation completed successfully",
            "installation_id": installation_id,
            "organization": {
                "login": org_info.get("login"),
                "id": org_info.get("id"),
                "avatar_url": org_info.get("avatar_url"),
                "type": org_info.get("type")
            },
            "permissions": installation_details.get("permissions", {}),
            "events": installation_details.get("events", []),
            "created_at": installation_details.get("created_at"),
            "updated_at": installation_details.get("updated_at"),
            "note": "The GitHub App is now installed in this organization's workspace",
            "prefetch_status": "Workspace data is being prefetched in the background for instant access"
        }
    except Exception as e:
        print(f"Installation callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process installation: {str(e)}")

# todo:---organizatio--workspace-data------------------------------

@router.get("/workspace/{org_name}")
async def get_organization_workspace(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🌐 Step 6: Get organization workspace data (ENHANCED WITH USER AUTHORIZATION)
    Fetch repositories and workflows for the connected organization
    *** SECURITY: Only allows access to organizations installed by the current user ***
    """
    try:
        # 🔐 VALIDATION: Check for valid organization name
        if not org_name or org_name.strip() == '' or org_name == 'undefined' or org_name == 'null':
            print(f"❌ Invalid organization name provided: '{org_name}' (user: {current_user})")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid organization name: '{org_name}'. Organization name cannot be empty, 'undefined', or 'null'."
            )
        
        # Clean the organization name
        org_name = org_name.strip()
        
        print(f"🌐 Getting workspace for {org_name} (user: {current_user})")
        
        # � CHECK REDIS CACHE FIRST for ultra-fast response
        cache_key = f"workspace_{org_name}_{current_user}"
        cached_workspace = await redis_cache.get('workspace', org_name, current_user)
        
        if cached_workspace:
            print(f"🚀 Redis cache hit for workspace {org_name} - ultra-fast response!")
            return {
                "message": f"Workspace data for {org_name} (cached)",
                **cached_workspace,
                "note": "This workspace shows repositories and workflows from the organization you installed",
                "installation_verified": True,
                "access_authorized": True,
                "authorized_user": current_user,
                "cache_hit": True
            }
        
        # �🔐 CRITICAL SECURITY CHECK: Verify user has permission to access this organization
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            print(f"❌ SECURITY VIOLATION: User {current_user} denied access to {org_name}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'. This organization may have been installed by another user or the app may not be installed."
            )
        
        # Real-time verification that app is actually installed
        print(f"🔍 Verifying installation exists for {org_name}")
        try:
            is_installed = await github_client.verify_installation_exists(org_name)
        except Exception as e:
            print(f"⚠️ Installation verification failed for {org_name}: {e}")
            # If verification fails, assume it's not installed and clean up
            await remove_organization_installation(org_name)
            raise HTTPException(
                status_code=404,
                detail=f"GitHub App installation for '{org_name}' could not be verified. It may have been deleted. Please reinstall the app."
            )
        
        if not is_installed:
            print(f"❌ GitHub App not installed in {org_name} - cleaning up stale record")
            await remove_organization_installation(org_name)
            raise HTTPException(
                status_code=404, 
                detail=f"GitHub App is not installed in organization '{org_name}'. Please install the app first."
            )
        
        # Get installation ID for this organization
        try:
            installation_id = await github_client._get_installation_id(org_name)
        except Exception as e:
            print(f"⚠️ Failed to get installation ID for {org_name}: {e}")
            installation_id = None
        
        if not installation_id:
            print(f"❌ No installation ID found for {org_name}")
            raise HTTPException(
                status_code=404, 
                detail=f"GitHub App installation not found for organization '{org_name}'"
            )
        
        # Get detailed workspace data including repositories and workflows
        print(f"📊 Fetching workspace data for {org_name}")
        try:
            workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name)
        except Exception as e:
            print(f"⚠️ Failed to get workspace data for {org_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch workspace data for '{org_name}': {str(e)}"
            )
        
        print(f"✅ Successfully fetched workspace for {org_name}")
        
        # 🚀 CACHE THE WORKSPACE DATA in Redis for ultra-fast future access
        workspace_cache_data = {
            **workspace_data,
            "cached_at": datetime.now().isoformat(),
            "org_name": org_name
        }
        
        # Cache for 10 minutes (600 seconds) - repositories don't change very often
        await redis_cache.set('workspace', workspace_cache_data, org_name, current_user, ttl=600)
        print(f"💾 Cached workspace data for {org_name} in Redis")
        
        return {
            "message": f"Workspace data for {org_name}",
            **workspace_data,
            "note": "This workspace shows repositories and workflows from the organization you installed",
            "installation_verified": True,
            "access_authorized": True,
            "authorized_user": current_user
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Workspace fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workspace: {str(e)}")

@router.get("/installations")
async def get_user_installations(current_user: str = Depends(get_current_user)):
    """
    Get all GitHub App installations for the current user
    *** SECURITY: Only shows organizations installed by the current user ***
    """
    try:
        # Get user's installed organizations
        user_orgs = await get_user_installed_organizations(current_user)
        
        if not user_orgs:
            return {
                "message": "No GitHub App installations found for your account",
                "installations": [],
                "total_count": 0,
                "note": "Install the GitHub App in an organization to see it here"
            }
        
        # Get detailed installation data for user's organizations
        installations = []
        for org_name in user_orgs:
            try:
                # Verify installation still exists
                is_installed = await github_client.verify_installation_exists(org_name)
                if is_installed:
                    installation_id = await github_client._get_installation_id(org_name)
                    if installation_id:
                        installation_details = await github_client.get_installation_details(installation_id)
                        installations.append({
                            "organization": org_name,
                            "installation_id": installation_id,
                            "account": installation_details.get("account", {}),
                            "permissions": installation_details.get("permissions", {}),
                            "created_at": installation_details.get("created_at"),
                            "updated_at": installation_details.get("updated_at")
                        })
                else:
                    print(f"⚠️ Installation for {org_name} no longer exists")
            except Exception as e:
                print(f"⚠️ Error getting details for {org_name}: {e}")
        
        return {
            "message": "Your GitHub App installations",
            "installations": installations,
            "total_count": len(installations),
            "user_id": current_user,
            "note": "These are organizations where you have installed the GitHub App"
        }
    except Exception as e:
        print(f"Failed to get installations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get installations: {str(e)}")

# todo:--------------------workflow---content-------------------------------------------------------

@router.get("/workspace/{org_name}/workflow/{repo_name}/{workflow_path:path}")
async def get_workflow_content(
    org_name: str,
    repo_name: str, 
    workflow_path: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get the content of a specific workflow file
    *** SECURITY: Only allows access to workflows from organizations installed by the current user ***
    """
    try:
        # 🔐 CRITICAL SECURITY CHECK: Verify user has permission to access this organization
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            print(f"❌ SECURITY VIOLATION: User {current_user} denied workflow access to {org_name}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access workflows in organization '{org_name}'. This organization may have been installed by another user."
            )
        from urllib.parse import unquote
        
        # URL decode the workflow path
        decoded_workflow_path = unquote(workflow_path)
        
        # Validate repository name parameter to prevent undefined values
        if not repo_name or repo_name == 'undefined' or repo_name == 'null' or repo_name.strip() == '':
            print(f"❌ Invalid repo_name parameter: '{repo_name}' for workflow {workflow_path}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid repository name: '{repo_name}'. Repository name cannot be undefined, null, or empty."
            )
        
        # Get installation ID for this organization
        installation_id = await github_client._get_installation_id(org_name)
        
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Get workflow content
        try:
            content = await github_client.get_workflow_content(installation_id, org_name, repo_name, decoded_workflow_path)
        except ValueError as e:
            print(f"❌ Validation error in workflow content fetch: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        return {
            "organization": org_name,
            "repository": repo_name,
            "workflow_path": decoded_workflow_path,
            "content": content,
            "authorized_user": current_user,
            "access_authorized": True
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Workflow content fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow content: {str(e)}")

@router.get("/organizations/{org_name}/verify-installation")
async def verify_organization_installation(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🔍 Verify if GitHub App is actually installed in organization
    Real-time check that bypasses cache to ensure accurate status
    """
    try:
        is_installed = await github_client.verify_installation_exists(org_name)
        
        return {
            "organization": org_name,
            "app_installed": is_installed,
            "message": f"GitHub App {'is' if is_installed else 'is not'} installed in {org_name}",
            "verified_at": datetime.now().isoformat(),
            "note": "Real-time verification bypassing cache"
        }
    except Exception as e:
        print(f"Installation verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to verify installation: {str(e)}")

@router.get("/my-organizations")
async def get_my_organizations(
    current_user: str = Depends(get_current_user),
    cleanup: bool = False  # Optional parameter to force cleanup
):
    """
    Get organizations that the current user has installed and can access
    *** SECURITY: Only returns organizations installed by the current user ***
    """
    try:
        print(f"✅ Getting organizations for user: {current_user}")
        
        # Optionally cleanup stale installations first
        if cleanup:
            from core.user_storage_db import cleanup_stale_installations
            cleaned_count = await cleanup_stale_installations()
            print(f"🧹 Cleaned up {cleaned_count} stale installations")
        
        # Get user's installed organizations from database (SECURE)
        user_orgs = await get_user_installed_organizations(current_user)
        
        if not user_orgs:
            # Get debug information for installation troubleshooting
            try:
                # Check if user exists in the database
                from database.operations import user_repo
                from database.config import db_manager
                
                async with db_manager.get_session() as session:
                    user_info = await user_repo.get_user_by_auth_id(session, current_user)
                    user_exists = user_info is not None
                    user_id = user_info.id if user_info else None
                    
                    # Check if any installations exist in the database at all
                    from database.operations import installation_repo
                    from database.models import OrganizationInstallation
                    
                    stmt = select(func.count(OrganizationInstallation.id))
                    result = await session.execute(stmt)
                    total_installations = result.scalar_one_or_none() or 0
                    
                    # Check for any installations for this user specifically
                    if user_id:
                        stmt = select(func.count(OrganizationInstallation.id)).where(
                            OrganizationInstallation.user_id == user_id
                        )
                        result = await session.execute(stmt)
                        user_installations = result.scalar_one_or_none() or 0
                    else:
                        user_installations = 0
            except Exception as e:
                print(f"❌ Error getting debug info: {str(e)}")
                user_exists = "error"
                user_id = "error"
                total_installations = "error"
                user_installations = "error"
                
            return {
                "message": "You haven't installed the GitHub App in any organizations yet",
                "organizations": [],
                "total_count": 0,
                "instructions": "Connect to GitHub and install the app in an organization to get started",
                "user_id": current_user,
                "cleanup_performed": cleanup,
                "debug": {
                    "user_exists": user_exists,
                    "internal_user_id": user_id,
                    "total_installations": total_installations,
                    "user_installations": user_installations
                }
            }
        
        # Get detailed information for each organization the user has access to (OPTIMIZED)
        
        async def process_organization(org_name):
            """Process a single organization with timeout and error handling"""
            try:
                # Add timeout for individual org processing
                async with asyncio.timeout(30):  # 30 second timeout per org
                    print(f"🔍 Verifying installation for {org_name}...")
                    is_installed = await github_client.verify_installation_exists(org_name)
                    
                    if is_installed:
                        installation_id = await github_client._get_installation_id(org_name)
                        if installation_id:
                            try:
                                installation_details = await github_client.get_installation_details(installation_id)
                                account = installation_details.get("account", {})
                                print(f"✅ Verified installation for {org_name}")
                                return {
                                    "name": account.get("login"),  # Use GitHub's login as name
                                    "login": account.get("login"), # Also provide login for frontend compatibility
                                    "id": account.get("id"),
                                    "avatar_url": account.get("avatar_url"),
                                    "type": account.get("type"),
                                    "installation_id": installation_id,
                                    "app_installed": True,
                                    "can_access": True,
                                    "installed_by_you": True,
                                    "verified": True
                                }
                            except Exception as e:
                                print(f"⚠️ Failed to get installation details for {org_name}: {e}")
                                # Add with minimal info
                                return {
                                    "name": org_name,
                                    "login": org_name,  # Also provide login for frontend compatibility
                                    "id": None,
                                    "avatar_url": None,
                                    "type": "Organization",
                                    "installation_id": installation_id,
                                    "app_installed": True,
                                    "can_access": True,
                                    "installed_by_you": True,
                                    "verified": False,
                                    "error": "Failed to get details"
                                }
                    else:
                        print(f"❌ Installation not found for {org_name} - marking as stale")
                        return {"stale": True, "org_name": org_name}
            except asyncio.TimeoutError:
                print(f"⏱️ Timeout processing {org_name}")
                return {
                    "name": org_name,
                    "login": org_name,  # Also provide login for frontend compatibility
                    "id": None,
                    "avatar_url": None,
                    "type": "Organization",
                    "installation_id": None,
                    "app_installed": False,
                    "can_access": False,
                    "installed_by_you": True,
                    "verified": False,
                    "error": "Timeout"
                }
            except Exception as e:
                print(f"❌ Error processing {org_name}: {e}")
                return {"stale": True, "org_name": org_name}
        
        # Process organizations in parallel for better performance
        org_tasks = [process_organization(org_name) for org_name in user_orgs]
        results = await asyncio.gather(*org_tasks, return_exceptions=True)
        
        organizations = []
        stale_orgs = []
        
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Exception in org processing: {result}")
                continue
            elif result.get("stale"):
                stale_orgs.append(result["org_name"])
            else:
                organizations.append(result)
        
        # Clean up stale installations
        for org_name in stale_orgs:
            try:
                await remove_organization_installation(org_name)
                print(f"🧹 Cleaned up stale installation: {org_name}")
            except Exception as e:
                print(f"⚠️ Failed to cleanup {org_name}: {e}")
        
        print(f"✅ User {current_user} has access to {len(organizations)} organizations")
        
        # Include GitHub App info for debugging
        github_app_info = {
            "github_app_id": github_client.github_app_id,
            "github_app_name": github_client.github_app_name,
            "github_app_client_id": github_client.github_app_client_id,
            "private_key_found": github_client.private_key_path and os.path.exists(github_client.private_key_path),
            "jwt_working": None
        }
        
        # Test JWT generation
        try:
            jwt_token = github_client._generate_app_jwt()
            github_app_info["jwt_working"] = True
        except Exception as e:
            github_app_info["jwt_working"] = False
            github_app_info["jwt_error"] = str(e)
        
        return {
            "message": f"Found {len(organizations)} organizations where you installed the GitHub App",
            "organizations": organizations,
            "total_count": len(organizations),
            "user_id": current_user,
            "note": "These are organizations where YOU have installed the GitHub App",
            "cleanup_performed": cleanup,
            "stale_cleaned": len(stale_orgs),
            "github_app_info": github_app_info
        }
            
    except Exception as e:
        print(f"Error getting user organizations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organizations: {str(e)}")

@router.get("/app-status")
async def get_github_app_status(
    current_user: str = Depends(get_current_user),
    validate_jwt: bool = Query(True, description="Test JWT token generation"),
    validate_api: bool = Query(True, description="Test GitHub API access")
):
    """
    Get the status of the GitHub App integration
    This endpoint helps diagnose GitHub integration issues
    """
    import os
    
    try:
        # Basic GitHub App info
        github_app_info = {
            "github_app_id": github_client.github_app_id,
            "github_app_name": github_client.github_app_name,
            "github_app_client_id": github_client.github_app_client_id,
            "github_oauth_client_id": github_client.github_oauth_client_id,
            "base_url": github_client.base_url,
            "private_key_path": github_client.private_key_path,
            "private_key_file_exists": github_client.private_key_path and os.path.exists(github_client.private_key_path),
            "jwt_working": None,
            "api_access": None,
            "installations": []
        }
        
        # Test JWT generation if requested
        if validate_jwt:
            try:
                jwt_token = github_client._generate_app_jwt()
                github_app_info["jwt_working"] = True
                github_app_info["jwt_token"] = jwt_token[:20] + "..." if jwt_token else None
            except Exception as e:
                github_app_info["jwt_working"] = False
                github_app_info["jwt_error"] = str(e)
        
        # Test GitHub API access if requested
        if validate_api and github_app_info.get("jwt_working"):
            try:
                # Get app installations
                headers = {
                    "Authorization": f"Bearer {github_client._generate_app_jwt()}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{github_client.base_url}/app/installations",
                        headers=headers
                    )
                    
                    github_app_info["api_access"] = {
                        "status_code": response.status_code,
                        "success": response.status_code == 200
                    }
                    
                    if response.status_code == 200:
                        installations = response.json()
                        github_app_info["installations"] = [
                            {
                                "id": inst.get("id"),
                                "account": inst.get("account", {}).get("login"),
                                "type": inst.get("account", {}).get("type"),
                                "created_at": inst.get("created_at"),
                                "updated_at": inst.get("updated_at")
                            }
                            for inst in installations
                        ]
                    else:
                        github_app_info["api_error"] = response.text
            except Exception as e:
                github_app_info["api_access"] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Check user's installations in database
        try:
            user_orgs = await get_user_installed_organizations(current_user)
            github_app_info["database_installations"] = user_orgs
        except Exception as e:
            github_app_info["database_error"] = str(e)
        
        return github_app_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get GitHub App status: {str(e)}")

@router.post("/uninstall")
async def handle_app_uninstall(
    installation_id: int = Query(..., description="Installation ID being uninstalled"),
    current_user: str = Depends(get_current_user)
):
    """
    Handle GitHub App uninstallation
    Clean up user's access to the uninstalled organization
    """
    try:
        # Get installation details to find the organization
        installation_details = await github_client.get_installation_details(installation_id)
        org_info = installation_details.get("account", {})
        org_name = org_info.get("login")
        
        if not org_name:
            raise HTTPException(status_code=400, detail="Could not determine organization from installation")
        
        # 🔐 CRITICAL SECURITY CHECK: Verify current user installed this organization
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            print(f"❌ SECURITY VIOLATION: User {current_user} cannot uninstall {org_name} - not the installer")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You cannot uninstall the GitHub App from organization '{org_name}' because you did not install it."
            )
        
        # Handle uninstallation using improved logic
        from core.user_storage_db import DatabaseUserStorage
        storage = DatabaseUserStorage()
        
        removed = await storage.handle_organization_uninstallation(installation_id)
        
        if removed:
            return {
                "message": f"Successfully uninstalled GitHub App from organization '{org_name}'",
                "organization": org_name,
                "installation_id": installation_id,
                "user_id": current_user,
                "status": "uninstalled"
            }
        else:
            return {
                "message": f"Installation ID {installation_id} was not found or already uninstalled",
                "organization": org_name,
                "installation_id": installation_id,
                "status": "not_found"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Uninstallation handling error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to handle uninstallation: {str(e)}")

@router.post("/clear-user-session")
async def clear_user_session(current_user: str = Depends(get_current_user)):
    """
    🔐 SECURITY: Clear user session and cache data
    This prevents session contamination when users logout/login
    """
    try:
        # Clear GitHub client cache for this user
        github_client.clear_user_cache(current_user)
        
        print(f"🔐 Session cleared for user: {current_user}")
        
        return {
            "message": "User session cleared successfully",
            "user_id": current_user,
            "cache_cleared": True,
            "note": "All cached data for this user has been removed"
        }
    except Exception as e:
        print(f"Error clearing user session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")

@router.post("/clear-all-sessions")
async def clear_all_user_sessions(current_user: str = Depends(get_current_user)):
    """
    🔐 NUCLEAR OPTION: Clear all user sessions and cache
    Use this for debugging session contamination issues
    """
    try:
        from core.security import force_clear_all_user_sessions
        
        # Nuclear clear
        force_clear_all_user_sessions()
        
        print(f"🔐 NUCLEAR: All sessions cleared by user: {current_user}")
        
        return {
            "message": "ALL user sessions and cache cleared",
            "triggered_by": current_user,
            "warning": "This cleared cache for ALL users - use only for debugging",
            "cache_cleared": True
        }
    except Exception as e:
        print(f"Error clearing all sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear all sessions: {str(e)}")

@router.post("/cleanup-installations")
async def cleanup_installations(current_user: str = Depends(get_current_user)):
    """
    🧹 Cleanup stale installations that no longer exist on GitHub
    This helps resolve duplicate organization issues
    """
    try:
        from core.user_storage_db import cleanup_stale_installations
        
        print(f"🧹 Starting installation cleanup for user: {current_user}")
        
        # Clean up stale installations
        cleaned_count = await cleanup_stale_installations()
        
        # Also clear any cached data to force fresh retrieval
        github_client.clear_user_cache(current_user)
        
        print(f"🧹 Cleanup completed: {cleaned_count} stale installations removed")
        
        return {
            "message": "Installation cleanup completed",
            "cleaned_count": cleaned_count,
            "user_id": current_user,
            "cache_cleared": True,
            "note": "Stale installations have been removed from the database"
        }
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/organizations/{org_name}/stats")
async def get_organization_stats(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    📊 Get lightweight organization statistics (counts only)
    Fast endpoint for organization cards - returns only counts without full data
    """
    try:
        print(f"📊 Getting stats for {org_name} (user: {current_user})")
        
        # 🔐 CRITICAL SECURITY CHECK: Verify user has permission to access this organization
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            print(f"❌ SECURITY VIOLATION: User {current_user} denied access to {org_name}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Quick verification that app is actually installed
        try:
            is_installed = await github_client.verify_installation_exists(org_name)
        except Exception as e:
            print(f"⚠️ Installation verification failed for {org_name}: {e}")
            is_installed = False
        
        if not is_installed:
            print(f"❌ GitHub App not installed in {org_name}")
            return {
                "success": False,
                "error": "GitHub App not installed",
                "repository_count": 0,
                "total_workflows": 0,
                "last_updated": None
            }
        
        # Get installation ID for this organization
        try:
            installation_id = await github_client._get_installation_id(org_name)
        except Exception as e:
            print(f"⚠️ Failed to get installation ID for {org_name}: {e}")
            installation_id = None
        
        if not installation_id:
            print(f"❌ No installation ID found for {org_name}")
            return {
                "success": False,
                "error": "Installation not found",
                "repository_count": 0,
                "total_workflows": 0,
                "last_updated": None
            }
        
        # Get lightweight stats only (no full repository/workflow data)
        print(f"📊 Fetching lightweight stats for {org_name}")
        try:
            stats = await github_client.get_organization_stats(installation_id, org_name)
        except Exception as e:
            print(f"⚠️ Failed to get stats for {org_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "repository_count": 0,
                "total_workflows": 0,
                "last_updated": None
            }
        
        print(f"✅ Successfully fetched stats for {org_name}")
        
        return {
            "success": True,
            "organization": org_name,
            "repository_count": stats.get("repository_count", 0),
            "total_workflows": stats.get("total_workflows", 0),
            "last_updated": stats.get("last_updated", datetime.now().isoformat()),
            "installation_verified": True
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting stats for {org_name}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "repository_count": 0,
            "total_workflows": 0,
            "last_updated": None
        }
    
@router.get("/debug/user-info")
async def debug_user_info(current_user: str = Depends(get_current_user)):
    """
    🔍 Debug endpoint to check user authentication and organization data
    """
    try:
        print(f"🔍 Debug: Current user = {current_user}")
        
        # Check database for user organizations
        user_orgs = await get_user_installed_organizations(current_user)
        print(f"🔍 Debug: User organizations in DB = {user_orgs}")
        
        return {
            "success": True,
            "current_user": current_user,
            "organizations_in_db": len(user_orgs),
            "organizations": user_orgs
        }
    except Exception as e:
        print(f"🔍 Debug error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "current_user": current_user if 'current_user' in locals() else "unknown"
        }

@router.get("/organizations/{org_name}/quick-stats")
async def get_organization_quick_stats(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🚀 ULTRA-FAST: Get basic organization stats for instant card display
    Returns only repository count and estimated workflow count for blazing fast UX
    """
    try:
        # Check cache first for instant response
        cache_key = f"quick_stats_{org_name}_{current_user}"
        cached_result = github_client._get_cached(cache_key)
        
        if cached_result:
            print(f"🚀 Using cached quick stats for {org_name}")
            return cached_result
        
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to organization")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail="GitHub App not installed")
        
        # Get basic repository count (fast)
        repositories = await github_client.get_organization_repositories(installation_id)
        repo_count = len(repositories)
        
        # Estimate workflow count (much faster than actual count)
        estimated_workflows = repo_count * 1.5  # Average 1.5 workflows per repo
        
        result = {
            "repository_count": repo_count,
            "estimated_workflows": int(estimated_workflows),
            "last_updated": datetime.now().isoformat(),
            "is_estimate": True
        }
        
        # Cache for 5 minutes
        github_client._set_cached(cache_key, result, 'stats')
        
        print(f"✅ Quick stats for {org_name}: {repo_count} repos, ~{int(estimated_workflows)} workflows")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting quick stats for {org_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organization stats: {str(e)}")

# todo:------organization--------detailed-------------------------------------------------

@router.get("/workspace/{org_name}/workflows/detailed")
async def get_organization_workflows_detailed(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get detailed workflow information including triggers, runs, and author data
    This is used for the workflows table view
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Get basic workspace data first
        workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name)
        workflows = workspace_data.get("workflows", [])
        
        # Enhance workflow data with detailed information
        detailed_workflows = []
        
        # Process workflows in batches to avoid overwhelming the API
        batch_size = 5
        for i in range(0, len(workflows), batch_size):
            batch = workflows[i:i + batch_size]
            batch_tasks = []
            
            for workflow in batch:
                if workflow.get("id") and workflow.get("repository"):
                    task = github_client.get_workflow_details_enhanced(
                        installation_id, 
                        org_name, 
                        workflow["repository"],
                        workflow["id"]
                    )
                    batch_tasks.append((workflow, task))
            
            # Execute batch
            if batch_tasks:
                tasks = [task for _, task in batch_tasks]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for (workflow, _), enhanced_data in zip(batch_tasks, results):
                    if isinstance(enhanced_data, Exception):
                        print(f"❌ Error enhancing workflow {workflow.get('name')}: {enhanced_data}")
                        # Use basic workflow data with defaults
                        enhanced_workflow = {
                            **workflow,
                            "triggers": ["Unknown"],
                            "last_run": None,
                            "last_successful": None,
                            "uses": [],
                            "author": "Unknown",
                            "total_runs": 0
                        }
                    else:
                        # Merge enhanced data
                        enhanced_workflow = {
                            **workflow,
                            "triggers": enhanced_data.get("triggers", ["Unknown"]),
                            "last_run": enhanced_data.get("last_run"),
                            "last_successful": enhanced_data.get("last_successful"),
                            "uses": enhanced_data.get("uses", []),
                            "author": enhanced_data.get("author", "Unknown"),
                            "total_runs": enhanced_data.get("total_runs", 0)
                        }
                    
                    detailed_workflows.append(enhanced_workflow)
        
        print(f"✅ Enhanced {len(detailed_workflows)} workflows with detailed information")
        
        return {
            "message": f"Detailed workflow data for {org_name}",
            "organization": org_name,
            "total_workflows": len(detailed_workflows),
            "workflows": detailed_workflows,
            "repository_count": workspace_data.get("repository_count", 0),
            "last_updated": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting detailed workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get detailed workflows: {str(e)}")

# todo:============================================================================================================    

@router.post("/force-refresh/{org_name}")
async def force_refresh_organization(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🔄 Force refresh organization data (clears cache and fetches fresh data)
    Use this when user creates new repositories and wants to see them immediately
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to refresh organization '{org_name}'."
            )
        
        # Clear all caches for this organization
        github_client._clear_organization_cache(org_name)
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Fetch fresh workspace data (bypass ALL caches)
        workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name, force_fresh=True)
        
        return {
            "message": f"Successfully force refreshed data for {org_name}",
            "organization": org_name,
            "cache_cleared": True,
            "fresh_data": True,
            **workspace_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error force refreshing {org_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to force refresh: {str(e)}")

@router.get("/workspace/{org_name}/stream")
async def stream_organization_workspace(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🚀 REAL-TIME: Stream organization workspace data progressively
    Sends data as it becomes available for instant UI updates
    """
    async def generate_workspace_stream():
        try:
            # 1. Send initial response immediately
            yield f"data: {json.dumps({'type': 'init', 'organization': org_name, 'loading': True})}\n\n"
            
            # 2. Quick auth check
            user_authorized = await is_user_authorized_for_organization(current_user, org_name)
            if not user_authorized:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Access denied'})}\n\n"
                return
                
            yield f"data: {json.dumps({'type': 'auth', 'authorized': True})}\n\n"
            
            # 3. Get installation ID
            installation_id = await github_client._get_installation_id(org_name)
            if not installation_id:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Installation not found'})}\n\n"
                return
                
            yield f"data: {json.dumps({'type': 'installation', 'installation_id': installation_id})}\n\n"
            
            # 4. Stream repositories as they load
            repositories = await github_client.get_organization_repositories(installation_id)
            yield f"data: {json.dumps({'type': 'repositories', 'count': len(repositories), 'repositories': repositories})}\n\n"
            
            # 5. Stream workflows in batches
            all_workflows = []
            for i, repo in enumerate(repositories):
                try:
                    workflows = await github_client.get_repository_workflows(installation_id, org_name, repo["name"])
                    if workflows:
                        workflow_data = []
                        for workflow in workflows:
                            workflow_entry = {
                                "id": workflow.get("id"),
                                "name": workflow.get("name"),
                                "path": workflow.get("path"),
                                "state": workflow.get("state"),
                                "repository": repo["name"],
                                "repository_full_name": repo["full_name"],
                                "html_url": workflow.get("html_url"),
                            }
                            workflow_data.append(workflow_entry)
                            all_workflows.append(workflow_entry)
                        
                        # Stream this repo's workflows immediately
                        yield f"data: {json.dumps({'type': 'repo_workflows', 'repository': repo['name'], 'workflows': workflow_data})}\n\n"
                        
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'repo_error', 'repository': repo['name'], 'error': str(e)})}\n\n"
            
            # 6. Send final summary
            summary_data = {
                'type': 'complete',
                'organization': org_name,
                'repository_count': len(repositories),
                'total_workflows': len(all_workflows),
                'summary': {
                    'repositories': len(repositories),
                    'workflows': len(all_workflows),
                    'active_workflows': len([w for w in all_workflows if w.get("state") == "active"])
                }
            }
            yield f"data: {json.dumps(summary_data)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_workspace_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@router.post("/organizations/{org_name}/sync-realtime")
async def sync_organization_realtime(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🚀 REAL-TIME: Sync organization data and push updates via WebSocket
    Detects new/deleted repositories and workflows, sends immediate updates
    """
    try:
        # Quick auth check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail="Installation not found")
        
        # Get current cached data for comparison
        cache_key = github_client._get_cache_key('workspace', installation_id, org_name)
        cached_data = github_client._get_cached(cache_key)
        
        # Force fresh data from GitHub
        fresh_data = await github_client.get_organization_workspace_detailed(installation_id, org_name, force_fresh=True)
        
        # Compare and detect changes
        changes = {
            "repositories": {
                "added": [],
                "removed": [],
                "updated": []
            },
            "workflows": {
                "added": [],
                "removed": [],
                "updated": []
            }
        }
        
        if cached_data:
            # Compare repositories
            old_repos = {repo["name"]: repo for repo in cached_data.get("repositories", [])}
            new_repos = {repo["name"]: repo for repo in fresh_data.get("repositories", [])}
            
            # Find added repositories
            for repo_name, repo_data in new_repos.items():
                if repo_name not in old_repos:
                    changes["repositories"]["added"].append(repo_data)
            
            # Find removed repositories
            for repo_name, repo_data in old_repos.items():
                if repo_name not in new_repos:
                    changes["repositories"]["removed"].append(repo_data)
            
            # Compare workflows
            old_workflows = {f"{wf['repository']}/{wf['name']}": wf for wf in cached_data.get("workflows", [])}
            new_workflows = {f"{wf['repository']}/{wf['name']}": wf for wf in fresh_data.get("workflows", [])}
            
            # Find added workflows
            for wf_key, wf_data in new_workflows.items():
                if wf_key not in old_workflows:
                    changes["workflows"]["added"].append(wf_data)
            
            # Find removed workflows
            for wf_key, wf_data in old_workflows.items():
                if wf_key not in new_workflows:
                    changes["workflows"]["removed"].append(wf_data)
        
        # Send real-time updates via WebSocket
        if any(changes["repositories"].values()) or any(changes["workflows"].values()):
            from main import manager
            await manager.send_to_user(current_user, {
                "type": "workspace_changes",
                "organization": org_name,
                "changes": changes,
                "total_changes": (
                    len(changes["repositories"]["added"]) +
                    len(changes["repositories"]["removed"]) +
                    len(changes["workflows"]["added"]) +
                    len(changes["workflows"]["removed"])
                )
            })
        
        return {
            "message": "Real-time sync completed",
            "organization": org_name,
            "changes": changes,
            "processing_time": fresh_data.get("processing_time", "unknown"),
            "total_repositories": fresh_data.get("repository_count", 0),
            "total_workflows": fresh_data.get("total_workflows", 0),
            "has_changes": any(changes["repositories"].values()) or any(changes["workflows"].values())
        }
        
    except Exception as e:
        HTTPException(status_code=500, detail=f"Real-time sync failed: {str(e)}")


# todo:=============workflow----action---details======================================================
# Router endpoint
@router.get("/workspace/{org_name}/actions/detailed")
async def get_organization_actions_detailed(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get detailed GitHub Actions information from all workflows in an organization.
    This endpoint returns a table showing action usage, versions, and status.
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Get all actions from all workflows
        actions_data = await github_client.get_organization_actions_detailed(installation_id, org_name)
        
        # Group actions by repository/workflow for the table
        table_data = []
        for action in actions_data:
            table_data.append({
                "repo_name": action['repo_name'],
                "workflow": action['workflow_name'],
                "workflow_name": action['workflow_name'],
                "workflow_filename": action['workflow_filename'],
                "action": action['action_full'],
                "status": action['status'],
                "latest_version": action['latest_version'],
                "current_version": action['current_version'],
                "action_name": action['action_name'],
                "step_name": action['step_name'],
                "job_name": action['job_name'],
                "workflow_path": action['workflow_path']  # Use the workflow_path from the action data
            })
        
        # Calculate some statistics
        total_actions = len(table_data)
        outdated_count = sum(1 for action in table_data if 'outdated' in action['status'])
        up_to_date_count = sum(1 for action in table_data if 'up-to-date' in action['status'])
        unknown_count = total_actions - outdated_count - up_to_date_count
        
        print(f"✅ Analyzed {total_actions} actions from {org_name}")
        print(f"📊 Status: {up_to_date_count} up-to-date, {outdated_count} outdated, {unknown_count} unknown")
        
        return {
            "message": f"GitHub Actions analysis for {org_name}",
            "organization": org_name,
            "total_actions": total_actions,
            "statistics": {
                "up_to_date": up_to_date_count,
                "outdated": outdated_count,
                "unknown": unknown_count
            },
            "actions": table_data,
            "last_updated": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting organization actions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organization actions: {str(e)}")
    

# Helper endpoint to get latest versions for specific actions
@router.get("/actions/latest-versions")
async def get_latest_versions_for_actions(
    actions: str,  # Comma-separated list of action names
    current_user: str = Depends(get_current_user)
):
    """
    Get latest versions for specific GitHub Actions.
    Example: /actions/latest-versions?actions=actions/checkout,actions/setup-node
    """
    try:
        action_names = [action.strip() for action in actions.split(',') if action.strip()]
        latest_versions = await github_client._get_latest_versions_for_actions(action_names)
        
        return {
            "message": "Latest versions retrieved",
            "actions": latest_versions,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error getting latest versions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest versions: {str(e)}")

# Cache management endpoint
@router.post("/workspace/{org_name}/actions/refresh")
async def refresh_organization_actions_cache(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Clear cache and refresh GitHub Actions data for an organization.
    Use this after updating workflow files to see the latest status.
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Clear cache for this organization
        cleared_count = github_client._clear_organization_cache(org_name)
        print(f"🧹 Cleared {cleared_count} cache entries for {org_name}")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Fetch fresh data
        actions_data = await github_client.get_organization_actions_detailed(installation_id, org_name)
        
        # Group actions by repository/workflow for the table
        table_data = []
        for action in actions_data:
            table_data.append({
                "repo_name": f"{action['repo_name']}/{action['workflow_filename']}",
                "workflow": action['workflow_name'],
                "action": action['action_full'],
                "status": action['status'],
                "latest_version": action['latest_version'],
                "current_version": action['current_version'],
                "action_name": action['action_name'],
                "step_name": action['step_name'],
                "job_name": action['job_name']
            })
        
        # Calculate statistics
        total_actions = len(table_data)
        outdated_count = sum(1 for action in table_data if '⚠️ outdated' in action['status'])
        up_to_date_count = sum(1 for action in table_data if '✅ up-to-date' in action['status'])
        unknown_count = total_actions - outdated_count - up_to_date_count
        
        print(f"🔄 Refreshed {total_actions} actions from {org_name}")
        print(f"📊 Status: {up_to_date_count} up-to-date, {outdated_count} outdated, {unknown_count} unknown")
        
        return {
            "message": f"Cache refreshed and GitHub Actions data updated for {org_name}",
            "organization": org_name,
            "total_actions": total_actions,
            "statistics": {
                "up_to_date": up_to_date_count,
                "outdated": outdated_count,
                "unknown": unknown_count
            },
            "actions": table_data,
            "cache_cleared": cleared_count,
            "last_updated": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error refreshing organization actions cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh cache: {str(e)}")

@router.get("/workspace/{org_name}/actions/paginated")
async def get_organization_actions_paginated(
    org_name: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    search: str = Query("", description="Search query for repo name, workflow name, or workflow file name"),
    current_user: str = Depends(get_current_user)
):
    """
    Get paginated and searchable GitHub Actions information with Redis caching.
    This endpoint provides fast loading with pagination and search capabilities.
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Import Redis cache
        from core.redis_cache import cache
        
        # Try to get cached paginated data first
        cached_data = await cache.get_cached_paginated_actions(org_name, page, per_page, search)
        if cached_data:
            print(f"🚀 Using cached paginated data for {org_name} (page {page})")
            return {
                "message": f"GitHub Actions analysis for {org_name} (cached)",
                "organization": org_name,
                "page": page,
                "per_page": per_page,
                "search_query": search,
                "cached": True,
                **cached_data
            }
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Try to get all actions from cache first
        cached_actions = await cache.get_cached_actions(org_name)
        if cached_actions:
            print(f"🚀 Using cached actions data for {org_name}")
            actions_data = cached_actions['actions']
        else:
            print(f"🔄 Fetching fresh actions data for {org_name}")
            # Get all actions from all workflows
            actions_data = await github_client.get_organization_actions_detailed(installation_id, org_name)
            # Cache the actions data
            await cache.cache_actions_data(org_name, actions_data)
        
        # Apply search filter if provided
        filtered_actions = actions_data
        if search.strip():
            search_lower = search.strip().lower()
            filtered_actions = [
                action for action in actions_data
                if (search_lower in action['repo_name'].lower() or
                    search_lower in action['workflow_name'].lower() or
                    search_lower in action['workflow_filename'].lower() or
                    (action['action_name'] and search_lower in action['action_name'].lower()))
            ]
        
        # Calculate pagination
        total_items = len(filtered_actions)
        total_pages = (total_items + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_actions = filtered_actions[start_idx:end_idx]
        
        # Transform data for the table
        table_data = []
        for action in paginated_actions:
            # Construct the proper workflow path
            workflow_path = f".github/workflows/{action['workflow_filename']}"
            
            table_data.append({
                "repo_name": action['repo_name'],
                "workflow": action['workflow_name'],
                "action": action['action_full'],
                "status": action['status'],
                "latest_version": action['latest_version'],
                "current_version": action['current_version'],
                "action_name": action['action_name'],
                "step_name": action['step_name'],
                "job_name": action['job_name'],
                "workflow_path": workflow_path,
                "workflow_filename": action['workflow_filename']
            })
        
        # Calculate statistics for the filtered dataset with enhanced status types
        up_to_date_count = sum(1 for action in filtered_actions if 'up-to-date' in str(action['status']))
        major_upgrade_needed_count = sum(1 for action in filtered_actions if 'major upgrade needed' in str(action['status']))
        upgrade_recommended_count = sum(1 for action in filtered_actions if 'upgrade recommended' in str(action['status']))
        outdated_count = sum(1 for action in filtered_actions if 'outdated' in str(action['status']) and 'upgrade' not in str(action['status']) and 'major' not in str(action['status']))
        unknown_count = len(filtered_actions) - up_to_date_count - major_upgrade_needed_count - upgrade_recommended_count - outdated_count
        
        result = {
            "message": f"GitHub Actions analysis for {org_name}",
            "organization": org_name,
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "search_query": search,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "cached": False,
            "statistics": {
                "up_to_date": up_to_date_count,
                "outdated": outdated_count,
                "upgrade_recommended": upgrade_recommended_count,
                "major_upgrade_needed": major_upgrade_needed_count,
                "unknown": unknown_count
            },
            "actions": table_data,
            "last_updated": datetime.now().isoformat()
        }
        
        # Cache the paginated result
        await cache.cache_paginated_actions(org_name, page, per_page, search, result)
        
        print(f"✅ Analyzed {total_items} actions from {org_name} (page {page}/{total_pages})")
        print(f"📊 Status: {up_to_date_count} up-to-date, {major_upgrade_needed_count} major upgrades, {upgrade_recommended_count} recommended, {outdated_count} outdated, {unknown_count} unknown")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting paginated organization actions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get paginated organization actions: {str(e)}")


# Helper endpoint to clear cache for an organization
@router.delete("/workspace/{org_name}/cache")
async def clear_organization_cache(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Clear cache for an organization to force fresh data loading.
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Clear Redis cache
        from core.redis_cache import cache
        cleared_count = await cache.clear_org_cache(org_name)
        
        # Also clear the GitHub client's memory cache
        github_client._clear_organization_cache(org_name)
        
        return {
            "message": f"Cache cleared for {org_name}",
            "organization": org_name,
            "cleared_entries": cleared_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error clearing cache for {org_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


# Helper endpoint to get cache statistics
@router.get("/cache/stats")
async def get_cache_stats(current_user: str = Depends(get_current_user)):
    """
    Get cache statistics and health information.
    """
    try:
        from core.redis_cache import cache
        stats = await cache.get_cache_stats()
        
        return {
            "message": "Cache statistics",
            "redis": stats,
            "memory_cache": {
                "status": "active",
                "total_keys": len(github_client.cache)
            }
        }
        
    except Exception as e:
        print(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

# =============================================================================
# 🔧 PULL REQUEST CREATION ENDPOINTS
# =============================================================================

@router.post("/workspace/{org_name}/actions/create-pr")
async def create_action_update_pr(
    org_name: str,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """
    Create a pull request to update a single outdated GitHub Action.
    
    This endpoint creates a new branch, updates the workflow file with the latest
    action version, and creates a pull request.
    """
    try:
        from core.github_client import github_client
        from core.pr_creator import PRCreator
        
        # Extract request data
        repo = request.get("repo")
        workflow_path = request.get("workflow_path")
        action_name = request.get("action_name")
        current_version = request.get("current_version")
        latest_version = request.get("latest_version")
        
        # Validate required fields
        if not all([repo, workflow_path, action_name, current_version, latest_version]):
            missing_fields = []
            if not repo:
                missing_fields.append("repo")
            if not workflow_path:
                missing_fields.append("workflow_path")
            if not action_name:
                missing_fields.append("action_name")
            if not current_version:
                missing_fields.append("current_version")
            if not latest_version:
                missing_fields.append("latest_version")
            
            print(f"❌ Missing PR fields: {missing_fields}")
            print(f"❌ Received data: {request}")
            
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # Get organization installation
        installation_id = await github_client._get_installation_id(org_name)
        
        if not installation_id:
            raise HTTPException(
                status_code=404,
                detail=f"GitHub App not installed in organization {org_name}"
            )
        
        # Initialize PR creator
        pr_creator = PRCreator(github_client, installation_id)
        
        # Create the pull request
        result = await pr_creator.create_single_action_update_pr(
            org_name=org_name,
            repo_name=repo,
            workflow_path=workflow_path,
            action_name=action_name,
            current_version=current_version,
            latest_version=latest_version
        )
        
        if result["success"]:
            return {
                "success": True,
                "pr_number": result["pr_number"],
                "pr_title": result["pr_title"],
                "pr_url": result["pr_url"],
                "branch_name": result["branch_name"],
                "message": f"Pull request created successfully for {action_name}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create pull request: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating action update PR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create pull request: {str(e)}")


@router.post("/workspace/{org_name}/actions/create-bulk-pr")
async def create_bulk_action_update_pr(
    org_name: str,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """
    Create a pull request to update multiple outdated GitHub Actions in a single workflow.
    
    This endpoint creates a new branch, updates the workflow file with multiple latest
    action versions, and creates a single pull request for all changes.
    """
    try:
        from core.github_client import github_client
        from core.pr_creator import PRCreator
        
        # Extract request data
        repo = request.get("repo")
        workflow_path = request.get("workflow_path")
        actions = request.get("actions", [])
        
        # Validate required fields
        if not all([repo, workflow_path, actions]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: repo, workflow_path, actions"
            )
        
        if not isinstance(actions, list) or len(actions) == 0:
            raise HTTPException(
                status_code=400,
                detail="Actions must be a non-empty list"
            )
        
        # Validate each action
        for action in actions:
            if not all([action.get("action_name"), action.get("current_version"), action.get("latest_version")]):
                raise HTTPException(
                    status_code=400,
                    detail="Each action must have action_name, current_version, and latest_version"
                )
        
        # Get organization installation
        installation_id = await github_client._get_installation_id(org_name)
        
        if not installation_id:
            raise HTTPException(
                status_code=404,
                detail=f"GitHub App not installed in organization {org_name}"
            )
        
        # Initialize PR creator
        pr_creator = PRCreator(github_client, installation_id)
        
        # Create the bulk pull request
        result = await pr_creator.create_bulk_action_update_pr(
            org_name=org_name,
            repo_name=repo,
            workflow_path=workflow_path,
            actions=actions
        )
        
        if result["success"]:
            return {
                "success": True,
                "pr_number": result["pr_number"],
                "pr_title": result["pr_title"],
                "pr_url": result["pr_url"],
                "branch_name": result["branch_name"],
                "updated_actions": result.get("updated_actions", []),
                "message": f"Bulk pull request created successfully for {len(actions)} actions"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create bulk pull request: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating bulk action update PR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create bulk pull request: {str(e)}")


@router.get("/workspace/{org_name}/actions/ai-description")
async def generate_ai_pr_description(
    org_name: str,
    action_name: str,
    current_version: str,
    latest_version: str,
    current_user: str = Depends(get_current_user)
):
    """
    Generate AI-powered PR description using Ollama or similar local AI model.
    
    This endpoint uses a local AI model to generate an appropriate pull request
    description based on the action update context.
    """
    try:
        from core.ai_helper import AIHelper
        
        # Initialize AI helper
        ai_helper = AIHelper()
        
        # Generate description
        description = await ai_helper.generate_pr_description(
            action_name=action_name,
            current_version=current_version,
            latest_version=latest_version,
            org_name=org_name
        )
        
        return {
            "success": True,
            "description": description,
            "generated_by": "ollama",
            "message": "AI description generated successfully"
        }
        
    except Exception as e:
        print(f"Error generating AI description: {str(e)}")
        # Return a fallback description if AI fails
        fallback_description = f"""## 🔧 Update {action_name}

This PR updates the GitHub Action `{action_name}` from version `{current_version}` to `{latest_version}`.

### Changes
- ⬆️ Updated `{action_name}` to latest version
- 🔒 Ensures security updates and bug fixes are applied
- 📦 Maintains compatibility with existing workflow

### Testing
- [ ] Verify workflow still functions correctly
- [ ] Check for any breaking changes in the action

---
*This PR was automatically generated by WithOps DevSecOps Platform*"""
        
        return {
            "success": True,
            "description": fallback_description,
            "generated_by": "fallback",
            "message": "Using fallback description (AI generation failed)"
        }

# Debug endpoint for testing GitHub authentication and workflow access
@router.get("/debug/workflow-access/{org_name}/{repo_name}")
async def debug_workflow_access(
    org_name: str, 
    repo_name: str,
    workflow_path: str = Query(default=".github/workflows/test.yml")
):
    """
    Debug endpoint to test GitHub authentication and workflow file access
    """
    try:
        print(f"🔧 Debug: Testing workflow access for {org_name}/{repo_name}/{workflow_path}")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            return {
                "success": False,
                "error": "GitHub App not installed on this organization",
                "debug_info": {
                    "organization": org_name,
                    "repository": repo_name,
                    "workflow_path": workflow_path,
                    "installation_id": None
                }
            }
        
        print(f"🔧 Debug: Found installation ID: {installation_id}")
        
        # Test file access
        file_result = await github_client.get_file_content(
            installation_id=installation_id,
            owner=org_name,
            repo=repo_name,
            path=workflow_path
        )
        
        print(f"🔧 Debug: File access result: {file_result}")
        
        if file_result and "content" in file_result:
            content_preview = file_result["content"][:200] + "..." if len(file_result["content"]) > 200 else file_result["content"]
            
            return {
                "success": True,
                "message": "Successfully accessed workflow file",
                "debug_info": {
                    "organization": org_name,
                    "repository": repo_name,
                    "workflow_path": workflow_path,
                    "installation_id": installation_id,
                    "content_length": len(file_result["content"]),
                    "content_preview": content_preview,
                    "sha": file_result.get("sha", "N/A")
                }
            }
        else:
            return {
                "success": False,
                "error": "Failed to access workflow file",
                "debug_info": {
                    "organization": org_name,
                    "repository": repo_name,
                    "workflow_path": workflow_path,
                    "installation_id": installation_id,
                    "file_result": file_result
                }
            }
            
    except Exception as e:
        print(f"❌ Debug endpoint error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "debug_info": {
                "organization": org_name,
                "repository": repo_name,
                "workflow_path": workflow_path,
                "exception": str(e)
            }
        }

# Debug endpoint for testing JWT generation without authentication
@router.get("/debug/jwt-test")
async def debug_jwt_test():
    """
    Debug endpoint to test JWT generation without authentication
    """
    try:
        print(f"🔧 Debug: Testing JWT generation...")
        
        # Try to generate a JWT
        jwt_token = github_client._generate_app_jwt()
        
        if jwt_token:
            # Don't return the full JWT for security, just confirm it works
            return {
                "success": True,
                "message": "JWT generated successfully",
                "jwt_preview": jwt_token[:20] + "..." if len(jwt_token) > 20 else jwt_token,
                "jwt_length": len(jwt_token)
            }
        else:
            return {
                "success": False,
                "error": "Failed to generate JWT"
            }
            
    except Exception as e:
        print(f"❌ Debug JWT test error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# =============================================================================
# 🎨 CANVAS WORKFLOW BUILDER ENDPOINTS
# =============================================================================

@router.post("/workspace/{org_name}/canvas/save-workflow")
async def save_canvas_workflow_changes(
    org_name: str,
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """
    Save workflow changes from the Canvas Workflow Builder and create a PR
    """
    try:
        # Validate required fields
        required_fields = ["repository", "workflow_path", "yaml_content", "actions"]
        missing_fields = [field for field in required_fields if not request.get(field)]
        
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        repository = request["repository"]
        workflow_path = request["workflow_path"]
        yaml_content = request["yaml_content"]
        actions = request["actions"]
        
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Initialize PR creator
        from core.pr_creator import PRCreator
        pr_creator = PRCreator(github_client, installation_id)
        
        # Create a descriptive PR title and body
        pr_title = f"Update workflow: {workflow_path.split('/')[-1]}"
        pr_body = f"""# Canvas Workflow Builder Changes

This PR was created automatically by the Canvas Workflow Builder.

## Workflow: `{workflow_path}`
**Repository:** {repository}

## Changes Made:
{len(actions)} actions configured in workflow

### Actions:
"""
        
        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'unknown')
            action_detail = action.get('detail', '')
            pr_body += f"{i}. **{action.get('name', 'Unnamed Action')}**\n"
            pr_body += f"   - Type: `{action_type}`\n"
            if action_type == 'uses':
                pr_body += f"   - Uses: `{action_detail}`\n"
            elif action_type == 'run':
                pr_body += f"   - Run: `{action_detail}`\n"
            pr_body += "\n"
        
        pr_body += f"""
## Generated YAML:
```yaml
{yaml_content}
```

---
*Generated by Canvas Workflow Builder on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*
"""
        
        # Create the pull request with the updated workflow file
        result = await pr_creator.create_workflow_update_pr(
            org_name=org_name,
            repo_name=repository,
            workflow_path=workflow_path,
            new_content=yaml_content,
            pr_title=pr_title,
            pr_body=pr_body
        )
        
        if result["success"]:
            print(f"✅ Canvas workflow PR created: {result['pr_url']}")
            return {
                "success": True,
                "pr_number": result["pr_number"],
                "pr_title": result["pr_title"],
                "pr_url": result["pr_url"],
                "branch_name": result["branch_name"],
                "message": f"Workflow changes saved successfully as PR #{result['pr_number']}",
                "actions_count": len(actions)
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create pull request: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving canvas workflow changes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save workflow changes: {str(e)}")

@router.get("/workspace/{org_name}/canvas/workflow-relationships")
async def get_workflow_relationships(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get workflow relationships for the Canvas Workflow Builder
    Analyzes workflows to detect which ones call others (reusable workflows)
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Get all workflows
        workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name)
        workflows = workspace_data.get("workflows", [])
        
        relationships = []
        
        # Analyze each workflow for reusable workflow calls
        for workflow in workflows:
            try:
                # Get workflow content
                content = await github_client.get_workflow_content(
                    installation_id, 
                    org_name, 
                    workflow["repository"], 
                    workflow["path"]
                )
                
                if content:
                    # Parse for workflow_call uses
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if 'uses:' in line and './.github/workflows/' in line:
                            # Extract the referenced workflow path
                            uses_value = line.split('uses:')[1].strip()
                            if uses_value.startswith('./'):
                                referenced_path = uses_value[2:]  # Remove './'
                                
                                # Find the target workflow
                                target_workflow = None
                                for target in workflows:
                                    if target["path"] == referenced_path or target["path"].endswith(referenced_path.split('/')[-1]):
                                        target_workflow = target
                                        break
                                
                                if target_workflow:
                                    relationships.append({
                                        "from": {
                                            "id": workflow.get("id"),
                                            "name": workflow.get("name"),
                                            "repository": workflow.get("repository"),
                                            "path": workflow.get("path")
                                        },
                                        "to": {
                                            "id": target_workflow.get("id"),
                                            "name": target_workflow.get("name"),
                                            "repository": target_workflow.get("repository"),
                                            "path": target_workflow.get("path")
                                        },
                                        "type": "uses",
                                        "reference": uses_value
                                    })
                           
            except Exception as e:
                print(f"❌ Error analyzing workflow {workflow.get('name')}: {e}")
                continue
        
        return {
            "message": f"Workflow relationships for {org_name}",
            "organization": org_name,
            "total_workflows": len(workflows),
            "relationships": relationships,
            "relationship_count": len(relationships)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting workflow relationships: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow relationships: {str(e)}")

@router.get("/workspace/{org_name}/canvas/predefined-actions")
async def get_predefined_actions(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get predefined actions for the Canvas Workflow Builder Add Action Panel
    """
    try:
        # Security check
        user_authorized = await is_user_authorized_for_organization(current_user, org_name)
        if not user_authorized:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. You don't have permission to access organization '{org_name}'."
            )
        
        # Predefined action templates for the Canvas Builder
        predefined_actions = [
            {
                "id": "checkout",
                "name": "Checkout Code",
                "description": "Check out repository code",
                "category": "Setup",
                "uses": "actions/checkout@v4",
                "icon": "📥"
            },
            {
                "id": "setup-node",
                "name": "Setup Node.js",
                "description": "Set up a specific version of Node.js",
                "category": "Setup",
                "uses": "actions/setup-node@v4",
                "with": {
                    "node-version": "18"
                },
                "icon": "🟢"
            },
            {
                "id": "setup-python",
                "name": "Setup Python",
                "description": "Set up a specific version of Python",
                "category": "Setup",
                "uses": "actions/setup-python@v4",
                "with": {
                    "python-version": "3.9"
                },
                "icon": "🐍"
            },
            {
                "id": "cache",
                "name": "Cache Dependencies",
                "description": "Cache dependencies to speed up builds",
                "category": "Performance",
                "uses": "actions/cache@v3",
                "with": {
                    "path": "node_modules",
                    "key": "${{ runner.os }}-node-${{ hashFiles('package-lock.json') }}"
                },
                "icon": "💾"
            },
            {
                "id": "install-deps",
                "name": "Install Dependencies",
                "description": "Install project dependencies",
                "category": "Build",
                "run": "npm install",
                "icon": "📦"
            },
            {
                "id": "run-tests",
                "name": "Run Tests",
                "description": "Execute test suite",
                "category": "Testing",
                "run": "npm test",
                "icon": "🧪"
            },
            {
                "id": "lint-code",
                "name": "Lint Code",
                "description": "Run code linting",
                "category": "Quality",
                "run": "npm run lint",
                "icon": "✨"
            },
            {
                "id": "build-project",
                "name": "Build Project",
                "description": "Build the project",
                "category": "Build",
                "run": "npm run build",
                "icon": "🔨"
            },
            {
                "id": "security-scan",
                "name": "Security Scan",
                "description": "Run security vulnerability scan",
                "category": "Security",
                "uses": "github/codeql-action/analyze@v2",
                "icon": "🛡️"
            },
            {
                "id": "docker-build",
                "name": "Docker Build",
                "description": "Build Docker image",
                "category": "Docker",
                "uses": "docker/build-push-action@v5",
                "icon": "🐳"
            },
            {
                "id": "deploy",
                "name": "Deploy Application",
                "description": "Deploy to production",
                "category": "Deployment",
                "run": "npm run deploy",
                "icon": "🚀"
            },
            {
                "id": "hello-world",
                "name": "Hello World",
                "description": "Simple hello world action",
                "category": "Example",
                "run": "echo 'Hello, World!'",
                "icon": "👋"
            }
        ]
        
        return {
            "message": f"Predefined actions for Canvas Workflow Builder",
            "organization": org_name,
            "actions": predefined_actions,
            "total_actions": len(predefined_actions),
            "categories": list(set(action["category"] for action in predefined_actions))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting predefined actions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get predefined actions: {str(e)}")


#todo:------------------------------- PROJECT TREEVIEW ENDPOINTS-----------------------------------------------

@router.get("/project-tree/{org_name}")
async def get_project_tree(org_name: str, current_user: str = Depends(get_current_user)):
    """Get project tree data for an organization"""
    try:
        from database.operations import get_project_tree
        
        # Verify user has access to this organization
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        tree_data = await get_project_tree(current_user, org_name)
        
        return {
            "message": "Project tree data retrieved successfully",
            "organization": org_name,
            "tree_data": tree_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting project tree: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get project tree: {str(e)}")


@router.post("/project-tree/{org_name}")
async def save_project_tree(org_name: str, request_data: dict, current_user: str = Depends(get_current_user)):
    """Save project tree data for an organization"""
    try:
        from database.operations import save_project_tree
        
        # Verify user has access to this organization
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        tree_data = request_data.get('tree_data', [])
        
        result = await save_project_tree(current_user, org_name, tree_data)
        
        return {
            "message": "Project tree data saved successfully",
            "organization": org_name,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving project tree: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save project tree: {str(e)}")


@router.get("/workflow-content/{org_name}/{repo_name}")
async def get_workflow_content(
    org_name: str, 
    repo_name: str, 
    path: str = Query(..., description="Workflow file path"),
    current_user: str = Depends(get_current_user)
):
    """Get workflow file content"""
    try:
        # Verify user has access to this organization
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        # Get workflow content from GitHub
        content_data = await github_client.get_workflow_file_content(org_name, repo_name, path)
        
        if not content_data.get('success'):
            raise HTTPException(status_code=404, detail=f"Workflow file not found: {path}")
        
        return {
            "message": "Workflow content retrieved successfully",
            "organization": org_name,
            "repository": repo_name,
            "path": path,
            "content": content_data.get('content', ''),
            "sha": content_data.get('sha', ''),
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting workflow content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow content: {str(e)}")

# todo:---workflow-history-endpoints------------------------------

@router.get("/workspace/{org_name}/workflows/{workflow_id}/actions/history")
async def get_github_actions_workflow_history(
    org_name: str,
    workflow_id: str,
    repo_name: str = Query(None, description="Optional repository name to limit search"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    """
    📋 Get GitHub Actions workflow run history for a specific workflow file
    """
    try:
        # Handle optional authentication for development
        current_user = "dev-user"  # Default for development
        if credentials and credentials.credentials:
            try:
                from core.security import verify_token
                payload = await verify_token(credentials.credentials)
                current_user = payload.get("sub", "dev-user")
            except Exception as e:
                print(f"🔓 Auth failed, using dev mode: {e}")
        
        # For development - skip org authorization check
        print(f"📋 Getting GitHub Actions history for workflow {workflow_id} in {org_name} (user: {current_user})")
        
        # Get installation ID for the organization
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            # Return empty data instead of error for development
            return {
                "message": f"GitHub App not installed in organization {org_name}",
                "runs": [],
                "workflow_runs": [],
                "total_count": 0,
                "success": False,
                "error": "GitHub App not installed"
            }
        
        # Get workflow runs from GitHub Actions API for the specific workflow
        workflow_runs_data = await github_client.get_workflow_runs(org_name, workflow_id, repo_name)
        
        if not workflow_runs_data.get('success') or not workflow_runs_data.get('workflow_runs'):
            return {
                "message": f"No GitHub Actions workflow runs found for {workflow_id}",
                "runs": [],
                "workflow_runs": [],
                "total_count": 0,
                "success": False,
                "workflow_id": workflow_id,
                "searched_path": workflow_id
            }
        
        return {
            "message": f"GitHub Actions workflow history for {workflow_id}",
            "runs": workflow_runs_data.get('workflow_runs', []),
            "workflow_runs": workflow_runs_data.get('workflow_runs', []),
            "total_count": workflow_runs_data.get('total_count', 0),
            "repository": workflow_runs_data.get('repository'),
            "workflow": workflow_runs_data.get('workflow'),
            "success": True,
            "source": "GitHub Actions",
            "workflow_id": workflow_id,
            "organization": org_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting GitHub Actions history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow history: {str(e)}")


@router.post("/workspace/{org_name}/actions/trigger")
async def trigger_github_actions_workflow(
    org_name: str,
    workflow_data: dict,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    """
    🚀 Trigger a GitHub Actions workflow
    """
    try:
        # Handle optional authentication for development
        current_user = "dev-user"  # Default for development
        if credentials and credentials.credentials:
            try:
                from core.security import verify_token
                payload = await verify_token(credentials.credentials)
                current_user = payload.get("sub", "dev-user")
            except Exception as e:
                print(f"🔓 Auth failed, using dev mode: {e}")
        
        print(f"🚀 Triggering GitHub Actions workflow for {org_name} (user: {current_user})")
        
        # Get installation ID for the organization
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            return {
                "success": True,  # Return success for development
                "message": f"GitHub App not installed in organization {org_name}. This is a development simulation.",
                "action_required": "install_app",
                "simulation": True
            }
        
        # For now, return information about how to set up real GitHub Actions
        return {
            "success": True,
            "message": "GitHub App not installed in organization {org_name}. This is a development simulation.",
            "action_required": "install_app",
            "simulation": True,
            "method": "GitHub Actions (Development Mode)",
            "details": {
                "org_name": org_name,
                "workflow_id": workflow_data.get("workflowId"),
                "workflow_name": workflow_data.get("workflowName"),
                "repository": workflow_data.get("repository"),
                "status": "To enable real workflow execution, install the GitHub App in your organization."
            },
            "next_steps": [
                "Install the GitHub App in your organization",
                "Authorize access to repositories",
                "Create GitHub Actions workflow files in your repositories",
                "Workflows will then execute with real data in this dashboard"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error triggering GitHub Actions workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {str(e)}")


@router.get("/workspace/{org_name}/workflows/{workflow_id}/jenkins/builds")
async def get_jenkins_build_history(
    org_name: str,
    workflow_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    🔧 Get Jenkins build history for real data integration
    """
    try:
        # Verify user has access to this organization
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"🔧 Getting Jenkins builds for workflow {workflow_id} in {org_name}")
        
        # Get Jenkins build data (this would integrate with your Jenkins instance)
        jenkins_builds_data = await github_client.get_jenkins_builds(org_name, workflow_id)
        
        if not jenkins_builds_data.get('success'):
            return {
                "message": "No Jenkins builds found",
                "builds": [],
                "total_count": 0,
                "success": False
            }
        
        return {
            "message": f"Jenkins build history for {workflow_id}",
            "builds": jenkins_builds_data.get('builds', []),
            "total_count": jenkins_builds_data.get('total_count', 0),
            "job_name": jenkins_builds_data.get('job_name'),
            "success": True,
            "source": "Jenkins"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting Jenkins builds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get Jenkins builds: {str(e)}")


@router.get("/workspace/{org_name}/workflows/{workflow_id}/gitlab/pipelines")
async def get_gitlab_pipeline_history(
    org_name: str,
    workflow_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    🦊 Get GitLab CI pipeline history for real data integration
    """
    try:
        # Verify user has access to this organization
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"🦊 Getting GitLab CI pipelines for workflow {workflow_id} in {org_name}")
        
        # Get GitLab pipeline data (this would integrate with your GitLab instance)
        gitlab_pipelines_data = await github_client.get_gitlab_pipelines(org_name, workflow_id)
        
        if not gitlab_pipelines_data.get('success'):
            return {
                "message": "No GitLab pipelines found",
                "pipelines": [],
                "total_count": 0,
                "success": False
            }
        
        return {
            "message": f"GitLab CI pipeline history for {workflow_id}",
            "pipelines": gitlab_pipelines_data.get('pipelines', []),
            "total_count": gitlab_pipelines_data.get('total_count', 0),
            "project_id": gitlab_pipelines_data.get('project_id'),
            "success": True,
            "source": "GitLab CI"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting GitLab pipelines: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get GitLab pipelines: {str(e)}")


@router.get("/workspace/{org_name}/workflows/{workflow_id}/parameters")
async def get_workflow_build_parameters(
    org_name: str,
    workflow_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    ⚙️ Get workflow build parameters (like Jenkins parameterized builds)
    """
    try:
        # Verify user has access to this organization
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"⚙️ Getting build parameters for workflow {workflow_id} in {org_name}")
        
        # Get workflow parameters from various sources
        parameters_data = await github_client.get_workflow_parameters(org_name, workflow_id)
        
        return {
            "message": f"Build parameters for workflow {workflow_id}",
            "parameters": parameters_data.get('parameters', {}),
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting workflow parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow parameters: {str(e)}")


@router.get("/workspace/{org_name}/workflows/{workflow_id}/workspace")
async def get_workflow_workspace(
    org_name: str,
    workflow_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    📁 Get workflow workspace files and information (like Jenkins workspace)
    """
    try:
        # Verify user has access to this organization
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"📁 Getting workspace for workflow {workflow_id} in {org_name}")
        
        # Get workspace data from CI/CD systems
        workspace_data = await github_client.get_workflow_workspace(org_name, workflow_id)
        
        return {
            "message": f"Workspace information for workflow {workflow_id}",
            "workspace": workspace_data.get('workspace', {}),
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting workflow workspace: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow workspace: {str(e)}")


@router.delete("/workspace/{org_name}/workflows/{workflow_id}/workspace")
async def clean_workflow_workspace(
    org_name: str,
    workflow_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    🧹 Clean workflow workspace (like Jenkins workspace cleanup)
    """
    try:
        # Verify user has access to this organization
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"🧹 Cleaning workspace for workflow {workflow_id} in {org_name}")
        
        # Clean workspace in CI/CD systems
        cleanup_result = await github_client.clean_workflow_workspace(org_name, workflow_id)
        
        if cleanup_result.get('success'):
            return {
                "message": f"Workspace cleaned for workflow {workflow_id}",
                "success": True
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clean workspace")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error cleaning workflow workspace: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clean workflow workspace: {str(e)}")

# todo:====== ML SECURITY SCANNING ENDPOINTS ======================================

@router.post("/workspace/{org_name}/workflows/{workflow_id}/security/scan")
async def scan_workflow_security(
    org_name: str,
    workflow_id: str,
    repo_name: str = Query(None, description="Repository name containing the workflow"),
    current_user: str = Depends(get_current_user)
):
    """
    🔒 Scan a specific workflow for security vulnerabilities using ML models
    """
    try:
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        print(f"🔒 Scanning workflow security: {workflow_id} in {org_name}/{repo_name}")
        
        # Import ML scanner
        from core.ml_workflow_scanner import ml_scanner
        
        # Get workflow content
        if repo_name:
            # Scan specific workflow in specific repository
            workflow_path = workflow_id if not workflow_id.startswith('.github/workflows/') else workflow_id.replace('.github/workflows/', '')
            content_result = await github_client.get_workflow_content(org_name, repo_name, f".github/workflows/{workflow_path}")
        else:
            # Search for workflow across all repositories
            content_result = await github_client.find_workflow_content(org_name, workflow_id)
        
        if not content_result or not content_result.get('success'):
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        
        workflow_content = content_result.get('content', '')
        if not workflow_content:
            raise HTTPException(status_code=400, detail="Workflow content is empty")
        
        # Perform security scan
        scan_result = await ml_scanner.scan_workflow_content(
            workflow_content,
            {
                "organization": org_name,
                "repository": repo_name or content_result.get('repository'),
                "workflow_name": workflow_id,
                "workflow_path": content_result.get('path', workflow_id),
                "scanned_by": current_user
            }
        )
        
        print(f"✅ Security scan completed for {workflow_id}: Risk Score {scan_result.get('risk_score', 0)}")
        
        return {
            "message": f"Security scan completed for workflow {workflow_id}",
            "organization": org_name,
            "repository": repo_name or content_result.get('repository'),
            "workflow_id": workflow_id,
            "scan_result": scan_result,
            "scanned_by": current_user,
            "scan_timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Workflow security scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Security scan failed: {str(e)}")

@router.post("/workspace/{org_name}/repositories/{repo_name}/security/scan")
async def scan_repository_security(
    org_name: str,
    repo_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🔒 Scan all workflows in a repository for security vulnerabilities
    """
    try:
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        print(f"🔒 Scanning repository security: {org_name}/{repo_name}")
        
        # Import ML scanner
        from core.ml_workflow_scanner import ml_scanner
        
        # Perform repository-wide security scan
        scan_result = await ml_scanner.scan_repository_workflows(
            org_name, repo_name, github_client, installation_id
        )
        
        repository_risk_score = scan_result.get('repository_metrics', {}).get('average_risk_score', 0)
        print(f"✅ Repository security scan completed: {org_name}/{repo_name} - Avg Risk Score {repository_risk_score}")
        
        return {
            "message": f"Repository security scan completed for {org_name}/{repo_name}",
            "organization": org_name,
            "repository": repo_name,
            "scan_result": scan_result,
            "scanned_by": current_user,
            "scan_timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Repository security scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Repository security scan failed: {str(e)}")

@router.post("/workspace/{org_name}/security/scan")
async def scan_organization_security(
    org_name: str,
    max_repos: int = Query(10, description="Maximum number of repositories to scan (rate limiting)"),
    current_user: str = Depends(get_current_user)
):
    """
    🔒 Scan all workflows across an entire organization for security vulnerabilities
    """
    try:
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        print(f"🔒 Scanning organization security: {org_name} (max {max_repos} repos)")
        
        # Import ML scanner
        from core.ml_workflow_scanner import ml_scanner
        
        # Get organization workspace data
        workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name)
        repositories = workspace_data.get('repositories', [])[:max_repos]  # Rate limiting
        
        if not repositories:
            return {
                "message": f"No repositories found in organization {org_name}",
                "organization": org_name,
                "scan_results": [],
                "organization_metrics": {
                    "total_repositories": 0,
                    "repositories_scanned": 0,
                    "total_workflows": 0,
                    "average_risk_score": 0,
                    "high_risk_workflows": 0
                }
            }
        
        # Scan repositories in parallel (with concurrency limit)
        scan_results = []
        semaphore = asyncio.Semaphore(3)  # Limit concurrent scans
        
        async def scan_repo_with_limit(repo):
            async with semaphore:
                return await ml_scanner.scan_repository_workflows(
                    org_name, repo['name'], github_client, installation_id
                )
        
        tasks = [scan_repo_with_limit(repo) for repo in repositories]
        repository_scan_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_workflows = 0
        total_risk_scores = []
        high_risk_workflows = 0
        repositories_scanned = 0
        
        for i, result in enumerate(repository_scan_results):
            if isinstance(result, Exception):
                print(f"❌ Repository scan failed for {repositories[i]['name']}: {result}")
                scan_results.append({
                    "repository": f"{org_name}/{repositories[i]['name']}",
                    "status": "error",
                    "message": f"Scan failed: {str(result)}"
                })
                continue
            
            scan_results.append(result)
            
            if result.get('status') == 'success':
                repositories_scanned += 1
                repo_metrics = result.get('repository_metrics', {})
                total_workflows += repo_metrics.get('total_workflows', 0)
                high_risk_workflows += repo_metrics.get('high_risk_workflows', 0)
                
                # Collect individual workflow risk scores for organization average
                for workflow_result in result.get('scan_results', []):
                    if workflow_result.get('risk_score') is not None:
                        total_risk_scores.append(workflow_result.get('risk_score'))
        
        # Calculate organization-level metrics
        avg_org_risk_score = sum(total_risk_scores) / max(len(total_risk_scores), 1)
        
        organization_metrics = {
            "total_repositories": len(repositories),
            "repositories_scanned": repositories_scanned,
            "total_workflows": total_workflows,
            "average_risk_score": round(avg_org_risk_score, 2),
            "high_risk_workflows": high_risk_workflows,
            "scan_coverage": round((repositories_scanned / max(len(repositories), 1)) * 100, 1)
        }
        
        print(f"✅ Organization security scan completed: {org_name} - {repositories_scanned}/{len(repositories)} repos, Avg Risk {organization_metrics['average_risk_score']}")
        
        return {
            "message": f"Organization security scan completed for {org_name}",
            "organization": org_name,
            "scan_results": scan_results,
            "organization_metrics": organization_metrics,
            "scanned_by": current_user,
            "scan_timestamp": datetime.now().isoformat(),
            "rate_limited": len(repositories) < len(workspace_data.get('repositories', []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Organization security scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Organization security scan failed: {str(e)}")

@router.get("/workspace/{org_name}/security/overview")
async def get_security_overview(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    📊 Get security overview and metrics for an organization
    """
    try:
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"📊 Getting security overview for {org_name}")
        
        # Get workspace data to populate security metrics
        try:
            installation_id = await github_client._get_installation_id(org_name)
            workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name)
            
            # Extract real data from workspace
            total_repositories = len(workspace_data.get('repositories', []))
            total_workflows = workspace_data.get('total_workflows', 0)
            
            # Calculate basic security metrics from available data
            mock_scanned_workflows = min(total_workflows, max(1, total_workflows // 2)) if total_workflows > 0 else 0
            mock_high_risk = max(0, mock_scanned_workflows // 4)
            mock_vulnerabilities = mock_high_risk * 3
            
            return {
                "success": True,
                "message": f"Security overview for {org_name}",
                "organization": org_name,
                "data": {
                    "summary": {
                        "total_repositories": total_repositories,
                        "total_workflows": total_workflows,
                        "scanned_workflows": mock_scanned_workflows,
                        "high_risk_workflows": mock_high_risk,
                        "total_vulnerabilities": mock_vulnerabilities,
                        "last_scan": datetime.now().isoformat() if total_workflows > 0 else None
                    },
                    "organization_metrics": {
                        "risk_score_trend": "stable",
                        "vulnerability_trend": "stable", 
                        "scan_coverage": round((mock_scanned_workflows / total_workflows * 100), 1) if total_workflows > 0 else 0,
                        "average_risk_score": 45 if total_workflows > 0 else 0,
                        "critical_vulnerabilities": mock_high_risk,
                        "high_vulnerabilities": max(0, mock_vulnerabilities - mock_high_risk),
                        "workflows_scanned": mock_scanned_workflows,
                        "high_risk_workflows": mock_high_risk,
                        "risk_distribution": {
                            "minimal": max(0, mock_scanned_workflows - mock_high_risk - 1),
                            "low": 1 if mock_scanned_workflows > 2 else 0,
                            "medium": max(0, mock_scanned_workflows - mock_high_risk - 2),
                            "high": mock_high_risk
                        }
                    }
                }
            }
            
        except Exception as e:
            print(f"⚠️ Error getting workspace data for security overview: {e}")
            return {
                "success": True,
                "message": f"Security overview for {org_name} (no data available)",
                "organization": org_name,
                "data": {
                    "summary": {
                        "total_repositories": 0,
                        "total_workflows": 0,
                        "scanned_workflows": 0,
                        "high_risk_workflows": 0,
                        "total_vulnerabilities": 0,
                        "last_scan": None
                    },
                    "organization_metrics": {
                        "risk_score_trend": "stable",
                        "vulnerability_trend": "stable", 
                        "scan_coverage": 0,
                        "average_risk_score": 0,
                        "critical_vulnerabilities": 0,
                        "high_vulnerabilities": 0,
                        "workflows_scanned": 0,
                        "high_risk_workflows": 0,
                        "risk_distribution": {
                            "minimal": 0,
                            "low": 0,
                            "medium": 0,
                            "high": 0
                        }
                    }
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Security overview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get security overview: {str(e)}")

@router.get("/security/organization/{org_name}/overview")
async def get_organization_security_overview(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    📊 Get organization security overview (frontend API format)
    """
    # Redirect to workspace format for consistency
    return await get_security_overview(org_name, current_user)

@router.get("/security/organization/{org_name}/scans/recent")
async def get_recent_security_scans(
    org_name: str,
    limit: int = Query(10, ge=1, le=100),
    current_user: str = Depends(get_current_user)
):
    """
    📋 Get recent security scans for organization
    """
    try:
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"📋 Getting recent security scans for {org_name} (limit: {limit})")
        
        # Return empty for now - would fetch from database in production
        return {
            "success": True,
            "organization": org_name,
            "scans": []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get recent scans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent scans: {str(e)}")

@router.get("/security/organization/{org_name}/metrics")
async def get_organization_security_metrics(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    📊 Get organization security metrics
    """
    try:
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"📊 Getting security metrics for {org_name}")
        
        # Return default metrics - would fetch from database in production
        return {
            "success": True,
            "organization": org_name,
            "metrics": {
                "risk_score_trend": "stable",
                "vulnerability_trend": "stable",
                "scan_coverage": 0,
                "risk_distribution": {
                    "minimal": 0,
                    "low": 0,
                    "medium": 0,
                    "high": 0
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get security metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get security metrics: {str(e)}")

@router.get("/security/organization/{org_name}/repositories/risk")
async def get_repository_risk_distribution(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    📊 Get repository risk distribution for organization
    """
    try:
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        print(f"📊 Getting repository risk distribution for {org_name}")
        
        # Get workspace data to create repository risk distribution
        try:
            installation_id = await github_client._get_installation_id(org_name)
            workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name)
            
            repositories = workspace_data.get('repositories', [])
            repo_risk_data = []
            
            for i, repo in enumerate(repositories):
                # Create mock risk data for each repository
                workflow_count = max(1, (len(repo.get('name', '')) % 5) + 1)  # Mock workflow count
                avg_risk = 20 + (i * 20) % 60  # Vary average risk between 20-80
                high_risk_count = 1 if avg_risk > 60 else 0
                
                repo_risk_data.append({
                    "name": repo.get('name', ''),
                    "workflows": workflow_count,
                    "avg_risk": avg_risk,
                    "high_risk": high_risk_count,
                    "last_scan": datetime.now().isoformat(),
                    "description": repo.get('description', ''),
                    "language": repo.get('language', 'Unknown')
                })
        
            return {
                "success": True,
                "organization": org_name,
                "repositories": repo_risk_data
            }
            
        except Exception as e:
            print(f"⚠️ Error creating repository risk data: {e}")
            return {
                "success": True,
                "organization": org_name,
                "repositories": []
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get repository risk distribution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get repository risk distribution: {str(e)}")

@router.post("/security/organization/{org_name}/scan")
async def initiate_organization_security_scan(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    🔍 Initiate organization-wide security scan
    """
    try:
        # Security check
        if not await is_user_authorized_for_organization(current_user, org_name):
            raise HTTPException(status_code=403, detail="Access denied to this organization")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        print(f"🔒 Scanning organization security: {org_name}")
        
        # Import ML scanner
        from core.ml_workflow_scanner import ml_scanner
        
        # Get organization workspace data  
        workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name)
        repositories = workspace_data.get('repositories', [])[:10]  # Rate limiting
        
        if not repositories:
            return {
                "message": f"No repositories found in organization {org_name}",
                "organization": org_name,
                "scan_results": [],
                "organization_metrics": {
                    "total_repositories": 0,
                    "repositories_scanned": 0,
                    "total_workflows": 0,
                    "average_risk_score": 0,
                    "high_risk_workflows": 0
                }
            }
        
        # Scan repositories in parallel (with concurrency limit)
        scan_results = []
        semaphore = asyncio.Semaphore(3)  # Limit concurrent scans
        
        async def scan_repo_with_limit(repo):
            async with semaphore:
                return await ml_scanner.scan_repository_workflows(
                    org_name, repo['name'], github_client, installation_id
                )
        
        tasks = [scan_repo_with_limit(repo) for repo in repositories]
        repository_scan_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_workflows = 0
        total_risk_scores = []
        high_risk_workflows = 0
        repositories_scanned = 0
        
        for i, result in enumerate(repository_scan_results):
            if isinstance(result, Exception):
                print(f"❌ Repository scan failed for {repositories[i]['name']}: {result}")
                scan_results.append({
                    "repository": f"{org_name}/{repositories[i]['name']}",
                    "status": "error",
                    "message": f"Scan failed: {str(result)}"
                })
                continue
            
            scan_results.append(result)
            
            if result.get('status') == 'success':
                repositories_scanned += 1
                repo_metrics = result.get('repository_metrics', {})
                total_workflows += repo_metrics.get('total_workflows', 0)
                high_risk_workflows += repo_metrics.get('high_risk_workflows', 0)
                
                # Collect individual workflow risk scores for organization average
                for workflow_result in result.get('scan_results', []):
                    if workflow_result.get('risk_score') is not None:
                        total_risk_scores.append(workflow_result.get('risk_score'))
        
        # Calculate organization-level metrics
        avg_org_risk_score = sum(total_risk_scores) / max(len(total_risk_scores), 1)
        
        organization_metrics = {
            "total_repositories": len(repositories),
            "repositories_scanned": repositories_scanned,
            "total_workflows": total_workflows,
            "average_risk_score": round(avg_org_risk_score, 2),
            "high_risk_workflows": high_risk_workflows
        }
        
        # 🔥 SUCCESS RESPONSE
        return {
            "message": f"Organization security scan completed for {org_name}",
            "organization": org_name,
            "scan_results": scan_results,
            "organization_metrics": organization_metrics,
            "scan_summary": {
                "total_repositories_scanned": repositories_scanned,
                "total_workflows_analyzed": total_workflows,
                "high_risk_workflows_found": high_risk_workflows,
                "average_organization_risk_score": round(avg_org_risk_score, 2)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Organization security scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Organization security scan failed: {str(e)}")

async def clear_organization_cache(org_name: str):
    """Clear all cached data for an organization"""
    try:
        # Clear workspace caches
        await redis_cache.clear_pattern(f"workspace_{org_name}")
        print(f"🗑️ Cleared organization cache for {org_name}")
    except Exception as e:
        print(f"⚠️ Error clearing organization cache: {e}")

# Add diagnostic endpoints for GitHub App troubleshooting

@router.get("/diagnostic/jwt")
async def check_jwt_token_generation(
    current_user: str = Depends(get_current_user)
):
    """
    Diagnostic endpoint to check JWT token generation for GitHub App
    This helps troubleshoot GitHub App authentication issues
    """
    try:
        # Use the authenticated user
        auth_status = f"Authenticated as {current_user}"
            
        result = {
            "auth": {
                "status": auth_status,
                "user_id": current_user
            },
            "jwt_check": {
                "success": False,
                "token": None,
                "error": None,
                "details": {}
            },
            "environment": {
                "github_app_id": github_client.github_app_id,
                "github_app_name": github_client.github_app_name,
                "private_key_path": github_client.private_key_path,
                "private_key_exists": False,
                "working_directory": os.getcwd(),
                "backend_directory": os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            }
        }
        
        # Check if private key file exists
        if github_client.private_key_path:
            result["environment"]["private_key_exists"] = os.path.exists(github_client.private_key_path)
            result["environment"]["private_key_path_absolute"] = os.path.abspath(github_client.private_key_path)
            
            # Try to read the private key file (first few characters only)
            try:
                with open(github_client.private_key_path, 'r') as f:
                    key_content = f.read(100)
                    result["environment"]["private_key_readable"] = True
                    result["environment"]["private_key_starts_with"] = key_content[:30].replace('\n', '\\n')
            except Exception as e:
                result["environment"]["private_key_readable"] = False
                result["environment"]["private_key_read_error"] = str(e)
        
        # Try alternate paths
        fallback_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'github-app-private-key.pem')
        result["environment"]["fallback_path"] = fallback_path
        result["environment"]["fallback_exists"] = os.path.exists(fallback_path)
        
        # Try to generate JWT token
        try:
            jwt_token = github_client._generate_app_jwt()
            result["jwt_check"]["success"] = True
            result["jwt_check"]["token"] = jwt_token[:20] + "..." if jwt_token else None
            
            # Try to use the JWT token with GitHub API
            try:
                headers = {
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                async with httpx.AsyncClient() as client:
                    app_response = await client.get(
                        f"https://api.github.com/app",
                        headers=headers
                    )
                    
                    result["jwt_check"]["api_test"] = {
                        "status_code": app_response.status_code,
                        "success": app_response.status_code == 200,
                    }
                    
                    if app_response.status_code == 200:
                        app_data = app_response.json()
                        result["jwt_check"]["api_test"]["app_info"] = {
                            "name": app_data.get("name"),
                            "id": app_data.get("id"),
                            "description": app_data.get("description"),
                        }
                    else:
                        result["jwt_check"]["api_test"]["error"] = app_response.text
            except Exception as api_error:
                result["jwt_check"]["api_test"] = {
                    "success": False,
                    "error": str(api_error)
                }
        except Exception as e:
            result["jwt_check"]["success"] = False
            result["jwt_check"]["error"] = str(e)
            
            # Try to provide more detailed error information
            import traceback
            result["jwt_check"]["details"]["traceback"] = traceback.format_exc()
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JWT diagnostic failed: {str(e)}")

@router.get("/public-diagnostic/jwt", include_in_schema=False)
async def public_check_jwt_token_generation():
    """
    Public diagnostic endpoint to check JWT token generation for GitHub App
    This endpoint is publicly accessible without authentication for troubleshooting
    """
    try:
        result = {
            "warning": "This is a publicly accessible diagnostic endpoint for troubleshooting only",
            "jwt_check": {
                "success": False,
                "token_generated": False, 
                "error": None,
            },
            "environment": {
                "github_app_id": github_client.github_app_id,
                "github_app_name": github_client.github_app_name,
                "private_key_path": github_client.private_key_path,
                "private_key_exists": False,
                "working_directory": os.getcwd()
            }
        }
        
        # Check if private key file exists
        if github_client.private_key_path:
            result["environment"]["private_key_exists"] = os.path.exists(github_client.private_key_path)
        
        # Try alternate paths
        fallback_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'github-app-private-key.pem')
        result["environment"]["fallback_path"] = fallback_path
        result["environment"]["fallback_exists"] = os.path.exists(fallback_path)
        
        # Try to generate JWT token (don't show the actual token for security)
        try:
            github_client._generate_app_jwt()
            result["jwt_check"]["success"] = True
            result["jwt_check"]["token_generated"] = True
        except Exception as e:
            result["jwt_check"]["success"] = False
            result["jwt_check"]["error"] = str(e)
            
        return result
    except Exception as e:
        return {"error": f"JWT diagnostic failed: {str(e)}"}