"""
API routes for GitHub Service
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import logging
import base64
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import core modules
from core.github_client import github_client
from core.redis_cache import cache
from core.queue_config import RefreshChannel, RefreshJobType
from core.security import get_current_user
from core.job_queue import verification_queue
from database import db_manager, User, Organization, OrganizationInstallation
from database.config import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["GitHub"])
security = HTTPBearer()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def resolve_user_uuid(auth_user_id: str, session) -> str:
    """
    Resolve Auth0 user ID to internal UUID
    
    Args:
        auth_user_id: Auth0 user ID (e.g., "google-oauth2|123456")
        session: Database session
        
    Returns:
        User UUID from database
        
    Raises:
        HTTPException: If user not found
    """
    result = await session.execute(
        select(User.id).where(User.auth_user_id == auth_user_id)
    )
    user_uuid = result.scalar()
    
    if not user_uuid:
        logger.warning(f"⚠️ No UUID found for auth_user_id: {auth_user_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"User not found in database. Please login to backend first."
        )
    
    logger.info(f"✅ Resolved {auth_user_id} → {user_uuid}")
    return user_uuid


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class OrganizationDiscoveryResponse(BaseModel):
    oauth_url: str
    state: str


class OrganizationListResponse(BaseModel):
    organizations: List[Dict]
    total_count: int


class WorkspaceResponse(BaseModel):
    organization: str
    status: str
    installation_id: int
    repository_count: int
    repositories: List[Dict]
    total_workflows: int
    workflows: List[Dict]
    last_updated: str


# ============================================================================
# ORGANIZATION DISCOVERY & INSTALLATION
# ============================================================================

@router.get("/orgs")
async def list_organizations(
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get list of organizations accessible to the current user
    Alias for /my-organizations endpoint for convenience
    """
    try:
        logger.info(f"📋 Listing organizations for user: {current_user}")
        
        # Resolve user UUID from Auth0 ID
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Get user's organizations from database
        result = await session.execute(
            select(Organization, OrganizationInstallation)
            .join(OrganizationInstallation, Organization.id == OrganizationInstallation.organization_id)
            .where(OrganizationInstallation.user_id == user_uuid)
        )
        
        orgs_data = []
        for org, installation in result.all():
            orgs_data.append({
                "id": str(org.id),
                "login": org.login,
                "name": org.name,
                "installation_id": installation.installation_id,
                "created_at": org.created_at.isoformat() if org.created_at else None
            })
        
        logger.info(f"✅ Found {len(orgs_data)} organizations for user {user_uuid}")
        
        return {
            "success": True,
            "organizations": orgs_data,
            "total_count": len(orgs_data)
        }
    except Exception as e:
        logger.error(f"❌ Error listing organizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GITHUB ACCOUNT CONNECTION (For users who logged in with non-GitHub methods)
# ============================================================================

@router.get("/connect/start")
async def start_github_connection(
    current_user: str = Depends(get_current_user)
):
    """
    Start GitHub account connection for users who logged in with non-GitHub methods.
    Returns OAuth URL to connect their GitHub account.
    """
    try:
        logger.info(f"🔗 Starting GitHub connection for user: {current_user}")
        
        # Use the same OAuth URL but with different state
        oauth_url = github_client.get_organization_discovery_oauth_url(state="connect_github")
        
        return {
            "success": True,
            "oauth_url": oauth_url,
            "state": "connect_github",
            "message": "Redirect user to oauth_url to connect their GitHub account"
        }
    except Exception as e:
        logger.error(f"Error starting GitHub connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connect/callback")
@router.post("/connect/callback")
async def handle_github_connection_callback(
    code: str,
    state: str = None,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Handle callback after user authorizes GitHub connection.
    Stores GitHub token and auto-links user to existing org installations.
    """
    try:
        logger.info(f"🔗 GitHub connection callback for user: {current_user}")
        
        # Resolve user UUID from Auth0 ID
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Exchange code for GitHub access token
        access_token = await github_client.exchange_code_for_token(code)
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get GitHub access token")
        
        # Get GitHub user info
        github_user_response = await github_client.http_client.get(
            f"{github_client.base_url}/user",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        
        github_user_info = None
        github_username = None
        if github_user_response.status_code == 200:
            github_user_info = github_user_response.json()
            github_username = github_user_info.get("login")
            logger.info(f"✅ Got GitHub user info: {github_username}")
        
        # Store the GitHub token in database
        from database import GitHubToken
        
        # Check if token already exists for this user
        existing_token_query = select(GitHubToken).where(
            GitHubToken.user_id == user_uuid,
            GitHubToken.is_active == True
        )
        existing_result = await session.execute(existing_token_query)
        existing_token = existing_result.scalar()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = access_token
            existing_token.updated_at = datetime.utcnow()
            existing_token.last_used = datetime.utcnow()
            existing_token.github_user_info = github_user_info
            logger.info(f"🔄 Updated existing GitHub token for user {user_uuid}")
        else:
            # Create new token
            new_token = GitHubToken(
                user_id=user_uuid,
                access_token=access_token,
                token_type="oauth",
                scope="read:org,read:user",
                github_user_info=github_user_info,
                is_active=True
            )
            session.add(new_token)
            logger.info(f"✅ Created new GitHub token for user {user_uuid}")
        
        # Also update user's github_username if we got it
        if github_username:
            user_query = select(User).where(User.id == user_uuid)
            user_result = await session.execute(user_query)
            user = user_result.scalar()
            if user:
                user.github_username = github_username
                if github_user_info:
                    user.github_user_id = github_user_info.get("id")
        
        await session.commit()
        
        # === AUTO-LINK TO EXISTING INSTALLATIONS ===
        # Get user's GitHub organizations
        user_orgs_response = await github_client.http_client.get(
            f"{github_client.base_url}/user/orgs",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        
        linked_orgs = []
        if user_orgs_response.status_code == 200:
            user_github_orgs = {org['login'] for org in user_orgs_response.json()}
            logger.info(f"🔗 User is member of {len(user_github_orgs)} GitHub orgs: {user_github_orgs}")
            
            # Find existing installations in these orgs
            if user_github_orgs:
                existing_installations_query = (
                    select(OrganizationInstallation, Organization)
                    .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                    .where(Organization.login.in_(user_github_orgs))
                    .where(OrganizationInstallation.status == "active")
                )
                
                result = await session.execute(existing_installations_query)
                existing_installations = result.all()
                
                for installation, org in existing_installations:
                    linked_users = installation.linked_users or []
                    if installation.user_id != user_uuid and str(user_uuid) not in linked_users:
                        # Auto-link this user
                        linked_users.append(str(user_uuid))
                        installation.linked_users = linked_users
                        installation.updated_at = datetime.utcnow()
                        linked_orgs.append(org.login)
                        logger.info(f"🔗 Auto-linked user {user_uuid} to installation for {org.login}")
                
                if linked_orgs:
                    await session.commit()
                    logger.info(f"✅ Auto-linked user to {len(linked_orgs)} organizations: {linked_orgs}")
        
        return {
            "success": True,
            "github_username": github_username,
            "github_connected": True,
            "linked_organizations": linked_orgs,
            "message": f"GitHub account connected successfully. Auto-linked to {len(linked_orgs)} organizations."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in GitHub connection callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connect/status")
async def get_github_connection_status(
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Check if current user has a GitHub account connected.
    """
    try:
        user_uuid = await resolve_user_uuid(current_user, session)
        
        from database import GitHubToken
        token_query = select(GitHubToken).where(
            GitHubToken.user_id == user_uuid,
            GitHubToken.is_active == True
        )
        result = await session.execute(token_query)
        token = result.scalar()
        
        if token:
            github_username = None
            if token.github_user_info:
                github_username = token.github_user_info.get("login")
            
            return {
                "success": True,
                "github_connected": True,
                "github_username": github_username,
                "connected_at": token.created_at.isoformat() if token.created_at else None
            }
        else:
            return {
                "success": True,
                "github_connected": False,
                "github_username": None,
                "message": "No GitHub account connected. Use /connect/start to connect."
            }
            
    except Exception as e:
        logger.error(f"Error checking GitHub connection status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizations/discover")
async def start_organization_discovery():
    """
    Step 1: Start GitHub organization discovery process
    Returns OAuth URL for user to discover organizations they can install the app into
    """
    try:
        oauth_url = github_client.get_organization_discovery_oauth_url()
        
        return {
            "success": True,
            "oauth_url": oauth_url,
            "state": "discover_orgs"
        }
    except Exception as e:
        logger.error(f"Error in organization discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizations/callback")
@router.post("/organizations/callback")
async def handle_organization_callback(
    code: str, 
    state: str = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Step 2: Handle OAuth callback for organization discovery
    Requires authentication to determine which orgs already have app installed by this user
    *** MULTI-USER: Auto-links users to existing installations in their GitHub orgs ***
    """
    try:
        logger.info(f"🔍 Organization callback for user: {current_user}")
        
        # Resolve user UUID from Auth0 ID
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Exchange code for token
        access_token = await github_client.exchange_code_for_token(code)
        
        # ===== SAVE GITHUB TOKEN TO DATABASE =====
        # This enables auto-link feature in /my-organizations
        try:
            from database import GitHubToken
            
            # Get GitHub user info
            user_info_response = await github_client.http_client.get(
                f"{github_client.base_url}/user",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            github_user_info = {}
            if user_info_response.status_code == 200:
                github_user_info = user_info_response.json()
                logger.info(f"🔍 GitHub user: {github_user_info.get('login')}")
            
            # Check for existing token
            existing_token_query = select(GitHubToken).where(
                GitHubToken.user_id == user_uuid,
                GitHubToken.is_active == True
            )
            existing_result = await session.execute(existing_token_query)
            existing_token = existing_result.scalar()
            
            if existing_token:
                # Update existing token
                existing_token.access_token = access_token
                existing_token.github_user_info = github_user_info
                existing_token.updated_at = datetime.utcnow()
                logger.info(f"🔄 Updated existing GitHub token for user {user_uuid}")
            else:
                # Create new token
                new_token = GitHubToken(
                    user_id=user_uuid,
                    access_token=access_token,
                    token_type="bearer",
                    scope="read:org",
                    github_user_info=github_user_info,
                    is_active=True
                )
                session.add(new_token)
                logger.info(f"✅ Saved new GitHub token for user {user_uuid}")
            
            await session.commit()
        except Exception as token_error:
            logger.warning(f"⚠️ Failed to save GitHub token (non-critical): {token_error}")
        
        # ===== AUTO-LINK TO EXISTING INSTALLATIONS =====
        # Check which GitHub orgs this user belongs to and auto-link to existing installations
        auto_linked_orgs = []
        try:
            # Get user's GitHub orgs using their OAuth token
            user_orgs_response = await github_client.http_client.get(
                f"{github_client.base_url}/user/orgs",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if user_orgs_response.status_code == 200:
                user_github_orgs = {org['login'] for org in user_orgs_response.json()}
                logger.info(f"🔗 User {current_user} is member of {len(user_github_orgs)} GitHub orgs: {user_github_orgs}")
                
                # Find existing installations in these orgs that user is NOT already linked to
                existing_installations_query = (
                    select(OrganizationInstallation, Organization)
                    .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                    .where(Organization.login.in_(user_github_orgs))
                    .where(OrganizationInstallation.status == "active")
                )
                
                result = await session.execute(existing_installations_query)
                existing_installations = result.all()
                
                for installation, org in existing_installations:
                    # Check if user is NOT the owner and NOT in linked_users
                    linked_users = installation.linked_users or []
                    if installation.user_id != user_uuid and str(user_uuid) not in linked_users:
                        # Auto-link this user to the installation
                        linked_users.append(str(user_uuid))
                        installation.linked_users = linked_users
                        installation.updated_at = datetime.utcnow()
                        auto_linked_orgs.append(org.login)
                        logger.info(f"🔗 Auto-linked user {user_uuid} to installation for {org.login}")
                
                if auto_linked_orgs:
                    await session.commit()
                    logger.info(f"✅ Auto-linked user to {len(auto_linked_orgs)} existing installations: {auto_linked_orgs}")
            else:
                logger.warning(f"⚠️ Could not fetch user's GitHub orgs for auto-link: {user_orgs_response.status_code}")
                
        except Exception as link_error:
            logger.warning(f"⚠️ Auto-link failed (non-critical): {link_error}")
        # ===== END AUTO-LINK =====
        
        # Get user's organizations with installation status (now includes auto-linked orgs)
        organizations = await github_client.get_user_organizations(access_token, str(user_uuid))
        
        logger.info(f"📋 Retrieved {len(organizations)} organizations for user {user_uuid}")
        
        return {
            "success": True,
            "organizations": organizations,
            "total_count": len(organizations),
            "auto_linked_count": len(auto_linked_orgs),
            "auto_linked_orgs": auto_linked_orgs,
            "message": f"Found {len(organizations)} organizations" + (f" (auto-linked to {len(auto_linked_orgs)} existing installations)" if auto_linked_orgs else "")
        }
    except Exception as e:
        logger.error(f"Error in organization callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organizations/{org_name}/install")
async def start_app_installation(
    org_name: str,
    current_user: str = Depends(get_current_user),
    state: str = Query(None)
):
    """
    Step 3: Generate GitHub App installation URL for specific organization
    Requires authentication to track who installed the app
    """
    try:
        # Encode user ID and org name in state parameter
        # Format: base64(user_id|org_name)
        state_data = f"{current_user}|{org_name}"
        encoded_state = base64.urlsafe_b64encode(state_data.encode()).decode()
        
        logger.info(f"🔐 Generating install URL for {org_name}, user: {current_user}")
        installation_url = github_client.generate_app_installation_url(org_name, encoded_state)
        
        return {
            "success": True,
            "installation_url": installation_url,
            "organization": org_name,
            "state": encoded_state
        }
    except Exception as e:
        logger.error(f"Error generating installation URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/installation/callback")
@router.post("/installation/callback")
async def handle_installation_callback(
    installation_id: int = Query(..., description="Installation ID from GitHub"),
    setup_action: str = Query(..., description="Setup action from GitHub"),
    state: str = Query(None, description="State parameter"),
    request: Request = None,
):
    """
    Step 4: Handle GitHub App installation callback
    Process the callback after user installs the GitHub App into an organization
    Includes background prefetching for instant workspace access
    """
    try:
        # Extract current user from state (now properly decoded)
        current_user = None
        org_name_from_state = None
        
        if state:
            try:
                # Decode base64-encoded state parameter
                decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
                
                if '|' in decoded_state:
                    # New format: user_id|org_name
                    # Split from RIGHT to handle Auth0 user IDs like "google-oauth2|123456789"
                    parts = decoded_state.rsplit('|', 1)
                    current_user = parts[0]
                    if len(parts) > 1:
                        org_name_from_state = parts[1]
                    logger.info(f"✅ Decoded state: user={current_user}, org={org_name_from_state}")
                else:
                    # Fallback: might be old format
                    current_user = decoded_state
                    logger.info(f"✅ Decoded state (old format): user={current_user}")
            except Exception as decode_error:
                # Fallback to old parsing method if base64 decode fails
                logger.warning(f"⚠️ Base64 decode failed, trying old format: {decode_error}")
                if '_' in state:
                    current_user = state.split('_')[0]
                    logger.info(f"✅ Extracted user from old format: {current_user}")
        
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
            
            # Use org from state as fallback if not in installation details
            if not org_login and org_name_from_state:
                org_login = org_name_from_state
                logger.info(f"Using organization from decoded state: {org_login}")
        except Exception as installation_error:
            logger.error(f"Installation callback error: {str(installation_error)}")
            # If we have org from state, continue with minimal data
            if org_name_from_state:
                logger.warning(f"⚠️ Using fallback org from state: {org_name_from_state}")
                org_login = org_name_from_state
                org_info = {"login": org_login, "id": 0}
                installation_details = {"permissions": {}, "events": []}
            else:
                raise HTTPException(status_code=500, detail=f"Failed to get installation details: {str(installation_error)}")
        
        logger.info(f"GitHub App successfully installed in organization: {org_login}")
        
        # Prepare installation data
        installation_data = {
            "installation_id": installation_id,
            "organization": org_info,
            "permissions": installation_details.get("permissions", {}),
            "events": installation_details.get("events", []),
            "created_at": installation_details.get("created_at"),
            "updated_at": installation_details.get("updated_at")
        }
        
        # Record installation in database
        if current_user:
            try:
                async with db_manager.get_session() as session:
                    # Resolve user UUID
                    user_uuid = await resolve_user_uuid(current_user, session)
                    
                    # Check if organization exists, create if not
                    org_result = await session.execute(
                        select(Organization).where(Organization.login == org_login)
                    )
                    organization = org_result.scalar_one_or_none()
                    
                    if not organization:
                        logger.info(f"📝 Creating new organization record: {org_login}")
                        organization = Organization(
                            github_org_id=org_info.get("id", 0),
                            login=org_login,
                            name=org_info.get("name"),
                            description=org_info.get("description"),
                            avatar_url=org_info.get("avatar_url"),
                            html_url=org_info.get("html_url"),
                            type=org_info.get("type", "Organization"),
                            github_metadata=org_info
                        )
                        session.add(organization)
                        await session.flush()  # Get the ID
                    
                    # Check if installation already exists
                    install_result = await session.execute(
                        select(OrganizationInstallation).where(
                            OrganizationInstallation.github_installation_id == installation_id
                        )
                    )
                    existing_install = install_result.scalar_one_or_none()
                    
                    if existing_install:
                        logger.info(f"📝 Updating existing installation record: {installation_id}")
                        existing_install.status = "active"
                        existing_install.updated_at = datetime.utcnow()
                        existing_install.permissions = installation_details.get("permissions", {})
                        existing_install.events = installation_details.get("events", [])
                    else:
                        logger.info(f"📝 Creating new installation record: {installation_id}")
                        new_installation = OrganizationInstallation(
                            user_id=user_uuid,
                            organization_id=organization.id,
                            github_installation_id=installation_id,
                            status="active",
                            permissions=installation_details.get("permissions", {}),
                            events=installation_details.get("events", []),
                            installation_metadata=installation_details
                        )
                        session.add(new_installation)
                    
                    await session.commit()
                    logger.info(f"✅ Installation recorded in database for user {user_uuid}")
                    
                    # Invalidate ALL caches after installation change
                    # This is CRITICAL - the all_installations cache must be cleared
                    # otherwise /my-organizations will use stale data and mark new installations as deleted
                    await cache.invalidate_organization_cache(org_login)
                    github_client._clear_installation_cache(org_login)  # Clear internal cache including all_installations
                    logger.info(f"🗑️ Invalidated all caches for {org_login} after installation")
                    
                    # Publish installation created event
                    from core.event_bus import event_bus
                    await event_bus.publish_installation_created(
                        installation_id=installation_id,
                        org_login=org_login,
                        org_id=org_info.get("id", 0),
                        user_id=current_user
                    )
                    logger.info(f"📤 Published installation.created event for {org_login}")
                    
            except Exception as db_error:
                logger.error(f"❌ Failed to record installation in database: {db_error}", exc_info=True)
                # Don't fail the whole request if database recording fails
        else:
            logger.warning(f"⚠️ No user context for installation {installation_id}, skipping database record")
        
        # Background prefetch workspace data for instant access
        async def prefetch_workspace():
            try:
                logger.info(f"🚀 Background prefetching workspace data for {org_login}")
                await github_client.get_organization_workspace_detailed(installation_id, org_login)
                logger.info(f"✅ Workspace data prefetched for {org_login}")
            except Exception as e:
                logger.warning(f"⚠️ Background prefetch failed for {org_login}: {e}")
        
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
            "prefetch_status": "Workspace data is being prefetched in the background for instant access",
            "user_id": current_user,  # Include for backend to record
            "org_name": org_login      # Include for backend to record
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Installation callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process installation: {str(e)}")


# ============================================================================
# USER ORGANIZATIONS
# ============================================================================

@router.get("/my-organizations")
async def get_my_organizations(
    current_user: str = Depends(get_current_user),
    force_verify: bool = Query(False, description="Force immediate verification (blocks response)")
):
    """
    Get organizations that the current user has installed and can access
    *** MULTI-USER: Auto-links users to existing installations in their GitHub orgs ***
    *** PERFORMANCE: Returns cached data immediately, verifies in background ***
    
    Args:
        current_user: Auth0 user ID from JWT token
        force_verify: If True, verify synchronously (slower but guaranteed fresh)
        
    Returns:
        List of organizations with installation details and last_verified timestamp
    """
    try:
        logger.info(f"✅ Getting organizations for user: {current_user}")
        
        async with db_manager.get_session() as session:
            # Resolve Auth0 ID to database UUID
            user_uuid = await resolve_user_uuid(current_user, session)
            logger.info(f"🔍 Resolved user {current_user} to UUID: {user_uuid}")
            
            # ===== CHECK GITHUB CONNECTION =====
            # Track if user has a GitHub token connected
            has_github_token = False
            github_username = None
            
            # ===== AUTO-LINK FEATURE =====
            # Check GitHub API for user's org memberships and auto-link to existing installations
            try:
                # Get user's GitHub token from database
                from database import GitHubToken
                token_query = select(GitHubToken).where(
                    GitHubToken.user_id == user_uuid,
                    GitHubToken.is_active == True
                ).order_by(GitHubToken.created_at.desc())
                
                token_result = await session.execute(token_query)
                github_token = token_result.scalar()
                
                if github_token and github_token.access_token:
                    # Extract GitHub username from stored info
                    if github_token.github_user_info:
                        github_username = github_token.github_user_info.get("login")
                    
                    # Get user's GitHub orgs using their OAuth token
                    user_orgs_response = await github_client.http_client.get(
                        f"{github_client.base_url}/user/orgs",
                        headers={
                            "Authorization": f"token {github_token.access_token}",
                            "Accept": "application/vnd.github.v3+json"
                        }
                    )
                    
                    if user_orgs_response.status_code == 200:
                        # Token is valid
                        has_github_token = True
                        user_github_orgs = {org['login'] for org in user_orgs_response.json()}
                        logger.info(f"🔗 User {current_user} is member of {len(user_github_orgs)} GitHub orgs: {user_github_orgs}")
                        
                        # Find existing installations in these orgs that user is NOT already linked to
                        existing_installations_query = (
                            select(OrganizationInstallation, Organization)
                            .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                            .where(Organization.login.in_(user_github_orgs))
                            .where(OrganizationInstallation.status == "active")
                        )
                        
                        result = await session.execute(existing_installations_query)
                        existing_installations = result.all()
                        
                        auto_linked_count = 0
                        for installation, org in existing_installations:
                            # Check if user is NOT the owner and NOT in linked_users
                            linked_users = installation.linked_users or []
                            if installation.user_id != user_uuid and str(user_uuid) not in linked_users:
                                # Auto-link this user to the installation
                                linked_users.append(str(user_uuid))
                                installation.linked_users = linked_users
                                installation.updated_at = datetime.utcnow()
                                auto_linked_count += 1
                                logger.info(f"🔗 Auto-linked user {user_uuid} to installation for {org.login}")
                        
                        if auto_linked_count > 0:
                            await session.commit()
                            logger.info(f"✅ Auto-linked user to {auto_linked_count} existing installations")
                    elif user_orgs_response.status_code == 401:
                        # Token is expired or revoked - mark it as inactive
                        logger.warning(f"⚠️ GitHub token expired/invalid for user {user_uuid} (401) - marking as inactive")
                        github_token.is_active = False
                        github_token.updated_at = datetime.utcnow()
                        await session.commit()
                        has_github_token = False
                        github_username = None
                    else:
                        logger.warning(f"⚠️ Could not fetch user's GitHub orgs: {user_orgs_response.status_code}")
                        # Keep has_github_token = False for other errors
                else:
                    logger.warning(f"⚠️ No GitHub token found for user {user_uuid} - skipping auto-link")
                    
            except Exception as e:
                logger.error(f"⚠️ Auto-link failed (non-critical): {e}")
            # ===== END AUTO-LINK =====
            
            # Query organizations where user is owner OR in linked_users
            from sqlalchemy import or_, cast, String, func
            from sqlalchemy.dialects.postgresql import JSONB
            
            query = (
                select(OrganizationInstallation, Organization)
                .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                .where(
                    or_(
                        OrganizationInstallation.user_id == user_uuid,  # User is owner
                        cast(OrganizationInstallation.linked_users, JSONB).contains(cast([str(user_uuid)], JSONB))  # User is in linked_users
                    )
                )
                .where(OrganizationInstallation.status == "active")
                .order_by(OrganizationInstallation.installed_at.desc())  # Most recent first
            )
            
            result = await session.execute(query)
            installations = result.all()
            
            logger.info(f"📊 Found {len(installations)} installations for user {user_uuid}")
            
            # ===== DEDUPLICATE AND VERIFY INSTALLATIONS =====
            # Group by org login to handle duplicates
            seen_orgs = {}  # org_login -> (installation, org) - keep the most recent valid one
            stale_installations = []
            
            for installation, org in installations:
                org_login = org.login
                
                # Check if we already have this org
                if org_login in seen_orgs:
                    # This is a duplicate - mark the older one for cleanup
                    existing_install, _ = seen_orgs[org_login]
                    # Keep the one with higher installation_id (more recent from GitHub)
                    if installation.github_installation_id > existing_install.github_installation_id:
                        stale_installations.append(existing_install)
                        seen_orgs[org_login] = (installation, org)
                    else:
                        stale_installations.append(installation)
                    logger.warning(f"⚠️ Found duplicate installation for {org_login}, keeping most recent")
                else:
                    seen_orgs[org_login] = (installation, org)
            
            # Clean up stale/duplicate installations
            if stale_installations:
                logger.info(f"🧹 Cleaning up {len(stale_installations)} stale/duplicate installations")
                for stale_install in stale_installations:
                    stale_install.status = "deleted"
                    stale_install.uninstalled_at = datetime.utcnow()
                await session.commit()
            
            # Convert to deduplicated list
            installations = list(seen_orgs.values())
            logger.info(f"📊 After deduplication: {len(installations)} unique organizations")
            
            # ===== VERIFY INSTALLATIONS ON GITHUB (if force_verify or no recent verification) =====
            # Get all app installations from GitHub to cross-check
            valid_installation_ids = set()
            try:
                all_github_installations = await github_client._get_all_installations_cached()
                valid_installation_ids = {inst['id'] for inst in all_github_installations}
                logger.info(f"🔍 GitHub has {len(valid_installation_ids)} active installations")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch GitHub installations for verification: {e}")
            
            if len(installations) == 0:
                logger.warning(f"⚠️ No installations found for user {user_uuid} (Auth0 ID: {current_user})")
                
                # Try to find orphaned installations (no user_id) and link them to this user
                orphaned_query = (
                    select(OrganizationInstallation, Organization)
                    .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                    .where(OrganizationInstallation.user_id == None)
                    .where(OrganizationInstallation.status == "active")
                )
                orphaned_result = await session.execute(orphaned_query)
                orphaned_installations = orphaned_result.all()
                
                if orphaned_installations:
                    logger.info(f"🔧 Found {len(orphaned_installations)} orphaned installations, attempting to link to user {user_uuid}")
                    for orphaned_install, orphaned_org in orphaned_installations:
                        # Verify this installation is still valid on GitHub
                        try:
                            await github_client.get_installation_details(orphaned_install.github_installation_id)
                            orphaned_install.user_id = user_uuid
                            orphaned_install.updated_at = datetime.utcnow()
                            logger.info(f"✅ Linked orphaned installation {orphaned_install.github_installation_id} ({orphaned_org.login}) to user {user_uuid}")
                        except Exception as verify_error:
                            logger.warning(f"⚠️ Orphaned installation {orphaned_install.github_installation_id} is no longer valid: {verify_error}")
                    
                    await session.commit()
                    
                    # Re-query after linking
                    result = await session.execute(query)
                    installations_raw = result.all()
                    # Deduplicate again
                    seen_orgs = {}
                    for inst, o in installations_raw:
                        if o.login not in seen_orgs:
                            seen_orgs[o.login] = (inst, o)
                    installations = list(seen_orgs.values())
                    logger.info(f"📊 After linking: Found {len(installations)} installations for user {user_uuid}")
            
            organizations = []
            verification_jobs_enqueued = 0
            installations_to_delete = []
            
            for installation, org in installations:
                # ===== VERIFY INSTALLATION EXISTS ON GITHUB =====
                # If we have valid_installation_ids, check if this installation still exists
                if valid_installation_ids and installation.github_installation_id not in valid_installation_ids:
                    logger.warning(f"⚠️ Installation {installation.github_installation_id} for {org.login} no longer exists on GitHub - marking as deleted")
                    installations_to_delete.append(installation)
                    continue  # Skip this org
                
                # Determine user's relationship to this installation
                is_owner = installation.user_id == user_uuid
                linked_users = installation.linked_users or []
                is_linked = str(user_uuid) in linked_users
                
                org_data = {
                    "id": org.github_org_id,
                    "login": org.login,
                    "name": org.name or org.login,
                    "description": org.description,
                    "avatar_url": org.avatar_url,
                    "html_url": org.html_url,
                    "type": org.type or "Organization",
                    "github_org_id": org.github_org_id,
                    
                    # Frontend expects these fields for access control
                    "app_installed": True,
                    "can_access": True,
                    "installed_by_you": is_owner,  # True only if user is the installer
                    "auto_linked": is_linked,  # True if user was auto-linked
                    "verified": True,
                    
                    # Installation details
                    "installation_id": installation.github_installation_id,
                    "created_at": installation.installed_at.isoformat() if installation.installed_at else None,
                    "updated_at": installation.updated_at.isoformat() if installation.updated_at else None,
                    "last_verified": installation.last_verified.isoformat() if installation.last_verified else None,
                    
                    # Additional installation metadata
                    "installation": {
                        "id": installation.id,
                        "github_installation_id": installation.github_installation_id,
                        "status": installation.status,
                        "installed_at": installation.installed_at.isoformat() if installation.installed_at else None,
                        "last_verified": installation.last_verified.isoformat() if installation.last_verified else None,
                        "permissions": installation.permissions,
                        "events": installation.events,
                        "is_owner": is_owner,
                        "linked_user_count": len(linked_users)
                    }
                }
                
                # Update last_verified since we just checked
                installation.last_verified = datetime.utcnow()
                
                # Check if verification is stale (>10 minutes old) or never verified
                verification_stale = (
                    installation.last_verified is None or
                    (datetime.utcnow() - installation.last_verified).total_seconds() > 600  # 10 minutes
                )
                
                if force_verify:
                    # Synchronous verification (blocks response)
                    try:
                        await github_client.get_installation_details(installation.github_installation_id)
                        logger.info(f"✅ Verified installation for {org.login}")
                        
                        # Update last_verified timestamp
                        installation.last_verified = datetime.utcnow()
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Installation {installation.github_installation_id} no longer valid for {org.login}: {e}")
                        installations_to_delete.append(installation)
                        continue  # Skip this org
                
                elif verification_stale:
                    # Background verification (non-blocking)
                    await verification_queue.enqueue_verification(
                        org_name=org.login,
                        installation_id=installation.github_installation_id,
                        user_id=str(user_uuid),
                        priority="normal"
                    )
                    verification_jobs_enqueued += 1
                    logger.info(f"📤 Enqueued background verification for {org.login}")
                
                organizations.append(org_data)
            
            # ===== CLEANUP STALE INSTALLATIONS =====
            if installations_to_delete:
                logger.info(f"🧹 Marking {len(installations_to_delete)} installations as deleted")
                for install_to_delete in installations_to_delete:
                    install_to_delete.status = "deleted"
                    install_to_delete.uninstalled_at = datetime.utcnow()
                await session.commit()
                logger.info(f"✅ Cleaned up {len(installations_to_delete)} stale installations")
            
            # Commit any pending changes (like last_verified updates)
            await session.commit()
            
            if verification_jobs_enqueued > 0:
                logger.info(f"📊 Enqueued {verification_jobs_enqueued} background verification jobs")
            
            # Determine if user needs to connect GitHub
            # User needs GitHub connection if:
            # 1. They don't have a GitHub token, AND
            # 2. They have no organizations (neither owned nor linked)
            needs_github_connection = not has_github_token
            
            if needs_github_connection and len(organizations) == 0:
                logger.info(f"⚠️ User {user_uuid} needs to connect GitHub account - no token and no orgs")
            elif needs_github_connection:
                logger.info(f"⚠️ User {user_uuid} has {len(organizations)} orgs but no GitHub token - recommend connecting for auto-link")
            
            return {
                "organizations": organizations,
                "total_count": len(organizations),
                "user_id": user_uuid,
                "background_verification": verification_jobs_enqueued > 0,
                "jobs_enqueued": verification_jobs_enqueued,
                # GitHub connection status for frontend
                "github_connected": has_github_token,
                "github_username": github_username,
                "needs_github_connection": needs_github_connection,
                "message": "Connect your GitHub account to access your team's organizations" if (needs_github_connection and len(organizations) == 0) else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user organizations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get organizations: {str(e)}")


@router.get("/organizations/{org_name}/verify-installation")
async def verify_installation(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Verify if the GitHub App is still installed in the organization
    Returns installation status for the current user
    Also updates database if installation is deleted on GitHub
    """
    try:
        logger.info(f"🔍 Verifying installation for {org_name}, user: {current_user}")
        
        async with db_manager.get_session() as session:
            # Resolve user UUID
            user_uuid = await resolve_user_uuid(current_user, session)
            
            # Check if organization exists and has active installation for this user
            query = (
                select(OrganizationInstallation, Organization)
                .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                .where(Organization.login == org_name)
                .where(OrganizationInstallation.user_id == user_uuid)
                .where(OrganizationInstallation.status == 'active')
            )
            
            result = await session.execute(query)
            installation_data = result.first()
            
            if installation_data:
                installation, org = installation_data
                
                # Verify with GitHub API that installation still exists
                try:
                    await github_client.get_installation_details(installation.github_installation_id)
                    logger.info(f"✅ Installation verified on GitHub for {org_name}")
                    
                    # Update last_verified timestamp
                    installation.last_verified = datetime.utcnow()
                    await session.commit()
                    
                    return {
                        "app_installed": True,
                        "installation_id": installation.github_installation_id,
                        "organization": {
                            "login": org.login,
                            "id": org.github_org_id,
                            "avatar_url": org.avatar_url
                        },
                        "status": "active"
                    }
                except Exception as github_error:
                    # Installation deleted on GitHub - update database
                    logger.warning(f"⚠️ Installation {installation.github_installation_id} deleted on GitHub for {org_name}: {github_error}")
                    installation.status = "deleted"
                    installation.uninstalled_at = datetime.utcnow()
                    await session.commit()
                    
                    # Invalidate cache
                    await cache.invalidate_organization_cache(org_name)
                    
                    logger.info(f"🗑️ Marked installation as deleted in database for {org_name}")
                    
                    return {
                        "app_installed": False,
                        "installation_id": None,
                        "status": "deleted",
                        "message": f"Installation was deleted on GitHub"
                    }
            else:
                logger.warning(f"⚠️ No active installation found for {org_name} by user {user_uuid}")
                return {
                    "app_installed": False,
                    "installation_id": None,
                    "status": "not_installed"
                }
                
    except Exception as e:
        logger.error(f"Error verifying installation for {org_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify installation: {str(e)}")


# ============================================================================
# ORGANIZATION INVITATIONS
# ============================================================================

class InvitationCreate(BaseModel):
    """Request model for creating an invitation"""
    email: str
    role: str = "member"  # member or owner


class InvitationResponse(BaseModel):
    """Response model for invitation"""
    id: str
    organization_login: str
    organization_name: str
    organization_avatar_url: str
    invited_email: str
    invited_by_name: str
    invited_by_email: str
    status: str
    role: str
    created_at: str
    expires_at: str


@router.post("/organizations/{org_name}/invitations")
async def create_invitation(
    org_name: str,
    invitation_data: InvitationCreate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create an invitation to join an organization.
    Only the organization owner can send invitations.
    """
    import secrets
    from datetime import timedelta
    from database import OrganizationInvitation
    
    try:
        logger.info(f"📨 Creating invitation for {invitation_data.email} to org {org_name}")
        
        # Resolve current user
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Get the user's email for the response
        user_result = await session.execute(
            select(User).where(User.id == user_uuid)
        )
        current_user_obj = user_result.scalar()
        
        if not current_user_obj:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user is the owner of this organization's installation
        query = (
            select(OrganizationInstallation, Organization)
            .join(Organization, OrganizationInstallation.organization_id == Organization.id)
            .where(Organization.login == org_name)
            .where(OrganizationInstallation.user_id == user_uuid)
            .where(OrganizationInstallation.status == "active")
        )
        
        result = await session.execute(query)
        installation_data = result.first()
        
        if not installation_data:
            raise HTTPException(
                status_code=403, 
                detail="You are not the owner of this organization's installation"
            )
        
        installation, organization = installation_data
        
        # Check if email is already invited (pending)
        existing_invite = await session.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.organization_id == organization.id,
                OrganizationInvitation.invited_email == invitation_data.email.lower(),
                OrganizationInvitation.status == "pending"
            )
        )
        if existing_invite.scalar():
            raise HTTPException(
                status_code=400, 
                detail=f"An invitation for {invitation_data.email} is already pending"
            )
        
        # Check if user is already a member (owner or linked)
        linked_users = installation.linked_users or []
        
        # Check if invited email matches any existing user
        existing_user = await session.execute(
            select(User).where(User.email == invitation_data.email.lower())
        )
        existing_user_obj = existing_user.scalar()
        
        if existing_user_obj:
            if str(existing_user_obj.id) == str(installation.user_id):
                raise HTTPException(
                    status_code=400, 
                    detail="This user is already the owner of this organization"
                )
            if str(existing_user_obj.id) in linked_users:
                raise HTTPException(
                    status_code=400, 
                    detail="This user is already a member of this organization"
                )
        
        # Create invitation
        invite_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        new_invitation = OrganizationInvitation(
            organization_id=organization.id,
            invited_by_user_id=user_uuid,
            invited_email=invitation_data.email.lower(),
            invite_token=invite_token,
            status="pending",
            role=invitation_data.role,
            expires_at=expires_at
        )
        
        session.add(new_invitation)
        await session.commit()
        await session.refresh(new_invitation)
        
        logger.info(f"✅ Created invitation {new_invitation.id} for {invitation_data.email} to {org_name}")
        
        return {
            "success": True,
            "invitation": {
                "id": new_invitation.id,
                "organization_login": organization.login,
                "organization_name": organization.name or organization.login,
                "invited_email": new_invitation.invited_email,
                "invited_by": current_user_obj.name or current_user_obj.email,
                "status": new_invitation.status,
                "role": new_invitation.role,
                "created_at": new_invitation.created_at.isoformat(),
                "expires_at": new_invitation.expires_at.isoformat(),
                "invite_token": invite_token  # Only returned on creation for potential email link
            },
            "message": f"Invitation sent to {invitation_data.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating invitation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create invitation: {str(e)}")


@router.get("/organizations/{org_name}/invitations")
async def list_organization_invitations(
    org_name: str,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List all invitations for an organization.
    Only the organization owner can view invitations.
    """
    from database import OrganizationInvitation
    
    try:
        # Resolve current user
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Check if user is the owner of this organization's installation
        query = (
            select(OrganizationInstallation, Organization)
            .join(Organization, OrganizationInstallation.organization_id == Organization.id)
            .where(Organization.login == org_name)
            .where(OrganizationInstallation.user_id == user_uuid)
            .where(OrganizationInstallation.status == "active")
        )
        
        result = await session.execute(query)
        installation_data = result.first()
        
        if not installation_data:
            raise HTTPException(
                status_code=403, 
                detail="You are not the owner of this organization's installation"
            )
        
        installation, organization = installation_data
        
        # Get all invitations for this organization
        invitations_result = await session.execute(
            select(OrganizationInvitation, User)
            .join(User, OrganizationInvitation.invited_by_user_id == User.id)
            .where(OrganizationInvitation.organization_id == organization.id)
            .order_by(OrganizationInvitation.created_at.desc())
        )
        
        invitations = []
        for invitation, invited_by_user in invitations_result.all():
            # Check if expired and update status
            if invitation.status == "pending" and invitation.expires_at < datetime.utcnow():
                invitation.status = "expired"
                await session.commit()
            
            invitations.append({
                "id": invitation.id,
                "invited_email": invitation.invited_email,
                "invited_by_name": invited_by_user.name or invited_by_user.email,
                "status": invitation.status,
                "role": invitation.role,
                "created_at": invitation.created_at.isoformat(),
                "expires_at": invitation.expires_at.isoformat(),
                "accepted_at": invitation.accepted_at.isoformat() if invitation.accepted_at else None
            })
        
        # Also get current team members
        linked_users = installation.linked_users or []
        members = []
        
        # Add owner
        owner_result = await session.execute(
            select(User).where(User.id == installation.user_id)
        )
        owner = owner_result.scalar()
        if owner:
            members.append({
                "id": owner.id,
                "email": owner.email,
                "name": owner.name,
                "avatar_url": owner.avatar_url,
                "role": "owner",
                "joined_at": installation.installed_at.isoformat() if installation.installed_at else None
            })
        
        # Add linked members
        if linked_users:
            linked_result = await session.execute(
                select(User).where(User.id.in_(linked_users))
            )
            for user in linked_result.scalars().all():
                members.append({
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "avatar_url": user.avatar_url,
                    "role": "member",
                    "joined_at": None  # Could track this in a separate table
                })
        
        return {
            "organization": {
                "login": organization.login,
                "name": organization.name or organization.login,
                "avatar_url": organization.avatar_url
            },
            "invitations": invitations,
            "members": members,
            "total_invitations": len(invitations),
            "total_members": len(members)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing invitations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list invitations: {str(e)}")


@router.delete("/organizations/{org_name}/invitations/{invitation_id}")
async def cancel_invitation(
    org_name: str,
    invitation_id: str,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Cancel a pending invitation.
    Only the organization owner can cancel invitations.
    """
    from database import OrganizationInvitation
    
    try:
        # Resolve current user
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Check if user is the owner of this organization's installation
        query = (
            select(OrganizationInstallation, Organization)
            .join(Organization, OrganizationInstallation.organization_id == Organization.id)
            .where(Organization.login == org_name)
            .where(OrganizationInstallation.user_id == user_uuid)
            .where(OrganizationInstallation.status == "active")
        )
        
        result = await session.execute(query)
        installation_data = result.first()
        
        if not installation_data:
            raise HTTPException(
                status_code=403, 
                detail="You are not the owner of this organization's installation"
            )
        
        installation, organization = installation_data
        
        # Find and cancel the invitation
        invitation_result = await session.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.id == invitation_id,
                OrganizationInvitation.organization_id == organization.id
            )
        )
        invitation = invitation_result.scalar()
        
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        if invitation.status != "pending":
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel invitation with status: {invitation.status}"
            )
        
        invitation.status = "cancelled"
        invitation.updated_at = datetime.utcnow()
        await session.commit()
        
        logger.info(f"🗑️ Cancelled invitation {invitation_id} for {invitation.invited_email}")
        
        return {
            "success": True,
            "message": f"Invitation for {invitation.invited_email} has been cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling invitation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel invitation: {str(e)}")


@router.get("/my-invitations")
async def get_my_pending_invitations(
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get all pending invitations for the current user's email.
    This is called when user logs in to check if they have pending invitations.
    """
    from database import OrganizationInvitation
    
    try:
        # Resolve current user
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Get user's email
        user_result = await session.execute(
            select(User).where(User.id == user_uuid)
        )
        user = user_result.scalar()
        
        if not user or not user.email:
            return {"invitations": [], "total_count": 0}
        
        logger.info(f"🔍 Checking pending invitations for {user.email}")
        
        # Find pending invitations for this email
        invitations_query = (
            select(OrganizationInvitation, Organization, User)
            .join(Organization, OrganizationInvitation.organization_id == Organization.id)
            .join(User, OrganizationInvitation.invited_by_user_id == User.id)
            .where(OrganizationInvitation.invited_email == user.email.lower())
            .where(OrganizationInvitation.status == "pending")
            .where(OrganizationInvitation.expires_at > datetime.utcnow())
        )
        
        result = await session.execute(invitations_query)
        
        invitations = []
        for invitation, organization, invited_by in result.all():
            invitations.append({
                "id": invitation.id,
                "invite_token": invitation.invite_token,
                "organization": {
                    "login": organization.login,
                    "name": organization.name or organization.login,
                    "avatar_url": organization.avatar_url
                },
                "invited_by": {
                    "name": invited_by.name or invited_by.email,
                    "email": invited_by.email,
                    "avatar_url": invited_by.avatar_url
                },
                "role": invitation.role,
                "created_at": invitation.created_at.isoformat(),
                "expires_at": invitation.expires_at.isoformat()
            })
        
        logger.info(f"📨 Found {len(invitations)} pending invitations for {user.email}")
        
        return {
            "invitations": invitations,
            "total_count": len(invitations)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending invitations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get invitations: {str(e)}")


@router.post("/invitations/{invite_token}/accept")
async def accept_invitation(
    invite_token: str,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Accept an invitation to join an organization.
    The user must be logged in with the email that was invited.
    """
    from database import OrganizationInvitation
    
    try:
        # Resolve current user
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Get user's email
        user_result = await session.execute(
            select(User).where(User.id == user_uuid)
        )
        user = user_result.scalar()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find the invitation
        invitation_query = (
            select(OrganizationInvitation, Organization, OrganizationInstallation)
            .join(Organization, OrganizationInvitation.organization_id == Organization.id)
            .join(OrganizationInstallation, OrganizationInstallation.organization_id == Organization.id)
            .where(OrganizationInvitation.invite_token == invite_token)
        )
        
        result = await session.execute(invitation_query)
        invitation_data = result.first()
        
        if not invitation_data:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        invitation, organization, installation = invitation_data
        
        # Verify the invitation
        if invitation.status != "pending":
            raise HTTPException(
                status_code=400, 
                detail=f"Invitation is no longer valid (status: {invitation.status})"
            )
        
        if invitation.expires_at < datetime.utcnow():
            invitation.status = "expired"
            await session.commit()
            raise HTTPException(status_code=400, detail="Invitation has expired")
        
        # Verify email matches
        if invitation.invited_email.lower() != user.email.lower():
            raise HTTPException(
                status_code=403, 
                detail=f"This invitation was sent to {invitation.invited_email}, not {user.email}"
            )
        
        # Add user to linked_users
        linked_users = installation.linked_users or []
        if str(user_uuid) not in linked_users:
            linked_users.append(str(user_uuid))
            installation.linked_users = linked_users
            installation.updated_at = datetime.utcnow()
        
        # Update invitation status
        invitation.status = "accepted"
        invitation.accepted_at = datetime.utcnow()
        invitation.accepted_by_user_id = user_uuid
        
        await session.commit()
        
        logger.info(f"✅ User {user.email} accepted invitation to {organization.login}")
        
        # Invalidate cache for this organization
        await cache.invalidate_organization_cache(organization.login)
        
        return {
            "success": True,
            "message": f"You have joined {organization.name or organization.login}",
            "organization": {
                "login": organization.login,
                "name": organization.name or organization.login,
                "avatar_url": organization.avatar_url,
                "installation_id": installation.github_installation_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to accept invitation: {str(e)}")


@router.post("/invitations/{invite_token}/decline")
async def decline_invitation(
    invite_token: str,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Decline an invitation to join an organization.
    """
    from database import OrganizationInvitation
    
    try:
        # Resolve current user
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Get user's email
        user_result = await session.execute(
            select(User).where(User.id == user_uuid)
        )
        user = user_result.scalar()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find the invitation
        invitation_result = await session.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.invite_token == invite_token
            )
        )
        invitation = invitation_result.scalar()
        
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        if invitation.status != "pending":
            raise HTTPException(
                status_code=400, 
                detail=f"Invitation is no longer valid (status: {invitation.status})"
            )
        
        # Verify email matches
        if invitation.invited_email.lower() != user.email.lower():
            raise HTTPException(
                status_code=403, 
                detail="This invitation was not sent to you"
            )
        
        # Update invitation status
        invitation.status = "declined"
        invitation.updated_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(f"❌ User {user.email} declined invitation {invitation.id}")
        
        return {
            "success": True,
            "message": "Invitation declined"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error declining invitation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to decline invitation: {str(e)}")


@router.delete("/organizations/{org_name}/members/{member_id}")
async def remove_member(
    org_name: str,
    member_id: str,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Remove a member from the organization.
    Only the organization owner can remove members.
    """
    try:
        # Resolve current user
        user_uuid = await resolve_user_uuid(current_user, session)
        
        # Check if user is the owner of this organization's installation
        query = (
            select(OrganizationInstallation, Organization)
            .join(Organization, OrganizationInstallation.organization_id == Organization.id)
            .where(Organization.login == org_name)
            .where(OrganizationInstallation.user_id == user_uuid)
            .where(OrganizationInstallation.status == "active")
        )
        
        result = await session.execute(query)
        installation_data = result.first()
        
        if not installation_data:
            raise HTTPException(
                status_code=403, 
                detail="You are not the owner of this organization's installation"
            )
        
        installation, organization = installation_data
        
        # Cannot remove yourself (owner)
        if str(member_id) == str(user_uuid):
            raise HTTPException(
                status_code=400, 
                detail="You cannot remove yourself as the owner"
            )
        
        # Remove from linked_users
        linked_users = installation.linked_users or []
        if str(member_id) not in linked_users:
            raise HTTPException(status_code=404, detail="Member not found in this organization")
        
        linked_users.remove(str(member_id))
        installation.linked_users = linked_users
        installation.updated_at = datetime.utcnow()
        
        await session.commit()
        
        # Get removed user info for response
        removed_user_result = await session.execute(
            select(User).where(User.id == member_id)
        )
        removed_user = removed_user_result.scalar()
        
        logger.info(f"🗑️ Removed member {member_id} from {org_name}")
        
        # Invalidate cache
        await cache.invalidate_organization_cache(org_name)
        
        return {
            "success": True,
            "message": f"Removed {removed_user.name or removed_user.email if removed_user else 'member'} from {organization.login}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to remove member: {str(e)}")


# ============================================================================
# WORKSPACE DATA
# ============================================================================

@router.get("/workspace/{org_name}")
async def get_organization_workspace(
    org_name: str,
    force_fresh: bool = Query(False, description="Force fresh data fetch bypassing cache")
):
    """
    Get comprehensive workspace data for an organization
    Uses redis cache with TTL-based invalidation
    """
    try:
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        
        if not installation_id:
            raise HTTPException(
                status_code=404,
                detail=f"GitHub App not installed in organization: {org_name}"
            )
        
        # Get the organization's database ID for threat modeling and other services
        organization_db_id = None
        async with db_manager.get_session() as session:
            from sqlalchemy import select
            org_result = await session.execute(
                select(Organization).where(Organization.login == org_name)
            )
            org = org_result.scalar_one_or_none()
            if org:
                organization_db_id = org.id
                logger.info(f"📋 Organization DB ID for {org_name}: {organization_db_id}")
        
        # If not forcing fresh, try cache first
        if not force_fresh:
            cached_data = await cache.get_cached_workspace_data(org_name, installation_id)
            
            if cached_data:
                cache_age = cached_data.get('cache_age', 0)
                is_stale = cache_age > 3600  # Stale if > 1 hour
                should_refresh = cache_age > 300  # Refresh if > 5 minutes
                
                logger.info(f"✅ Cache hit for workspace {org_name} (age: {cache_age:.0f}s)")
                
                # Queue background refresh if cache is getting old
                if should_refresh:
                    asyncio.create_task(
                        cache.publish_refresh_job(
                            RefreshChannel.WORKSPACE_REFRESH,
                            {
                                "type": RefreshJobType.WORKSPACE_FULL,
                                "org_name": org_name,
                                "user_id": None,
                                "timestamp": datetime.now().isoformat(),
                                "params": {}
                            }
                        )
                    )
                
                return {
                    **cached_data,
                    "organization": {
                        "id": organization_db_id,
                        "login": org_name
                    },
                    "from_cache": True,
                    "is_stale": is_stale,
                    "refreshing_in_background": should_refresh
                }
        
        # Force fresh or no cache - fetch synchronously
        logger.info(f"⚠️ Fetching fresh workspace for {org_name}")
        workspace_data = await github_client.get_organization_workspace_detailed(
            installation_id,
            org_name,
            force_fresh=force_fresh
        )
        
        # Cache the fresh data
        await cache.cache_workspace_data(org_name, installation_id, workspace_data, ttl=900)
        
        return {
            **workspace_data,
            "organization": {
                "id": organization_db_id,
                "login": org_name
            },
            "from_cache": False,
            "refreshing_in_background": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace for {org_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace/{org_name}/refresh")
async def force_refresh_organization(
    org_name: str
):
    """
    Force refresh organization workspace data
    Clears all caches and fetches fresh data from GitHub
    """
    try:
        logger.info(f"🔄 Force refresh requested for {org_name}")
        
        # Get installation ID
        installation_id = await github_client._get_installation_id(org_name)
        
        if not installation_id:
            raise HTTPException(
                status_code=404,
                detail=f"GitHub App not installed in organization: {org_name}"
            )
        
        # Clear all caches for this organization
        await cache.clear_organization_cache(org_name, installation_id)
        logger.info(f"🗑️ Cleared all caches for {org_name}")
        
        # Fetch fresh data from GitHub
        workspace_data = await github_client.get_organization_workspace_detailed(
            installation_id,
            org_name,
            force_fresh=True
        )
        
        # Cache the fresh data
        await cache.cache_workspace_data(org_name, installation_id, workspace_data, ttl=900)
        
        logger.info(f"✅ Successfully refreshed workspace data for {org_name}")
        
        return {
            **workspace_data,
            "success": True,
            "refreshed": True,
            "from_cache": False,
            "message": f"Successfully refreshed data for {org_name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error force refreshing workspace for {org_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh organization data: {str(e)}")


@router.get("/installations")
async def get_user_installations():
    """
    Get all GitHub App installations
    """
    try:
        installations = await github_client.get_all_user_installations()
        
        return {
            "success": True,
            "installations": installations,
            "total_count": len(installations)
        }
    except Exception as e:
        logger.error(f"Error getting installations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WORKFLOW OPERATIONS
# ============================================================================

@router.get("/workspace/{org_name}/workflow/{repo_name}/{workflow_path:path}")
async def get_workflow_content(org_name: str, repo_name: str, workflow_path: str):
    """
    Get content of a specific workflow file
    """
    try:
        installation_id = await github_client._get_installation_id(org_name)
        
        if not installation_id:
            raise HTTPException(
                status_code=404,
                detail=f"GitHub App not installed: {org_name}"
            )
        
        content = await github_client.get_workflow_content(
            installation_id,
            org_name,
            repo_name,
            workflow_path
        )
        
        return {
            "success": True,
            "content": content,
            "workflow_path": workflow_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{org_name}/actions/detailed")
async def get_organization_actions(org_name: str):
    """
    Get all GitHub Actions from all workflows in an organization
    """
    try:
        installation_id = await github_client._get_installation_id(org_name)
        
        if not installation_id:
            raise HTTPException(
                status_code=404,
                detail=f"GitHub App not installed: {org_name}"
            )
        
        actions = await github_client.get_organization_actions_detailed(
            installation_id,
            org_name
        )
        
        return {
            "success": True,
            "actions": actions,
            "total_count": len(actions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/organizations/{org_name}/stats")
async def get_organization_stats(org_name: str):
    """
    Get organization statistics (repository and workflow counts)
    Async pattern: Returns cached data immediately and refreshes in background
    """
    try:
        installation_id = await github_client._get_installation_id(org_name)
        
        if not installation_id:
            raise HTTPException(
                status_code=404,
                detail=f"GitHub App not installed: {org_name}"
            )
        
        # Try cache first
        cache_key = github_client._get_cache_key('stats', installation_id, org_name)
        cached_stats, cache_age = github_client._get_cached_with_age(cache_key)
        
        if cached_stats:
            from core.queue_config import REFRESH_THRESHOLD
            
            should_refresh = cache_age and cache_age > REFRESH_THRESHOLD
            is_stale = cache_age and cache_age > 3600
            
            logger.info(f"✅ Returning cached stats for {org_name} (age: {cache_age:.0f}s, stale: {is_stale})")
            
            # Queue refresh only if cache is getting old
            if should_refresh:
                asyncio.create_task(
                    cache.publish_refresh_job(
                        RefreshChannel.WORKSPACE_REFRESH,
                        {
                            "type": RefreshJobType.WORKSPACE_FULL,
                            "org_name": org_name,
                            "user_id": None,
                            "timestamp": datetime.now().isoformat(),
                            "params": {"stats_only": True}
                        }
                    )
                )
            
            return {
                "success": True,
                "organization": org_name,
                **cached_stats,
                "from_cache": True,
                "cache_age": cache_age,
                "is_stale": is_stale,
                "refreshing_in_background": should_refresh
            }
        
        # No cache - fetch fresh stats
        logger.info(f"⚠️ Fetching fresh stats for {org_name}")
        stats = await github_client.get_organization_stats(installation_id, org_name)
        
        return {
            "success": True,
            "organization": org_name,
            **stats,
            "from_cache": False,
            "refreshing_in_background": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WORKFLOW OPERATIONS
# ============================================================================

@router.get("/workspace/{org_name}/workflows/detailed")
async def get_detailed_workflows(org_name: str):
    """
    Get detailed workflow information including triggers, runs, and author data
    Always returns enhanced workflow data with detailed information
    """
    try:
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Try to get cached DETAILED workflows first
        detailed_cache_key = github_client._get_cache_key('workflow_detailed', installation_id, org_name)
        cached_detailed = github_client._get_cached(detailed_cache_key)
        
        if cached_detailed:
            # Return cached detailed workflows immediately
            logger.info(f"✅ Returning cached detailed workflows for {org_name}: {len(cached_detailed)} workflows")
            
            # Queue background refresh job (fire and forget)
            asyncio.create_task(
                cache.publish_refresh_job(
                    RefreshChannel.WORKFLOWS_REFRESH,
                    {
                        "type": RefreshJobType.WORKFLOWS_DETAILED,
                        "org_name": org_name,
                        "user_id": None,
                        "timestamp": datetime.now().isoformat(),
                        "params": {}
                    }
                )
            )
            
            return {
                "message": f"Detailed workflow data for {org_name} (cached)",
                "organization": org_name,
                "total_workflows": len(cached_detailed),
                "workflows": cached_detailed,
                "last_updated": datetime.now().isoformat(),
                "from_cache": True,
                "refreshing_in_background": True
            }
        
        # No detailed cache - fetch and enhance workflows
        logger.info(f"⚠️ No detailed workflow cache for {org_name}, fetching and enhancing...")
        
        # Get basic workspace data (may be cached)
        cache_key = github_client._get_cache_key('workspace', installation_id, org_name)
        cached_workspace = github_client._get_cached(cache_key)
        
        if cached_workspace:
            workflows = cached_workspace.get("workflows", [])
        else:
            workspace_data = await github_client.get_organization_workspace_detailed(installation_id, org_name)
            workflows = workspace_data.get("workflows", [])
        
        # Enhance workflow data with detailed information
        detailed_workflows = []
        
        # Process workflows in batches
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
            
            if batch_tasks:
                tasks = [task for _, task in batch_tasks]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for (workflow, _), enhanced_data in zip(batch_tasks, results):
                    if isinstance(enhanced_data, Exception):
                        logger.error(f"Error enhancing workflow {workflow.get('name')}: {enhanced_data}")
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
        
        logger.info(f"Enhanced {len(detailed_workflows)} workflows with detailed information")
        
        # Cache the detailed workflows for future requests (1 hour TTL)
        github_client._set_cached(detailed_cache_key, detailed_workflows, 'workflow_detailed')
        logger.info(f"💾 Cached detailed workflows for {org_name}")
        
        return {
            "message": f"Detailed workflow data for {org_name}",
            "organization": org_name,
            "total_workflows": len(detailed_workflows),
            "workflows": detailed_workflows,
            "last_updated": datetime.now().isoformat(),
            "from_cache": False,
            "refreshing_in_background": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detailed workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get detailed workflows: {str(e)}")


@router.get("/workspace/{org_name}/workflows/{workflow_name}/actions/history")
async def get_workflow_actions_history(
    org_name: str,
    workflow_name: str,
    repo_name: str = Query(..., description="Repository name")
):
    """
    Get GitHub Actions run history for a specific workflow
    Returns list of workflow runs with status, duration, and metadata
    """
    try:
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Get workflow runs from GitHub API
        token = await github_client.get_installation_access_token(installation_id)
        
        # Try to find the workflow file
        # The workflow name might be URL encoded, so decode it
        from urllib.parse import unquote
        decoded_workflow_name = unquote(workflow_name)
        
        logger.info(f"📋 Fetching workflow history for: {decoded_workflow_name} in {org_name}/{repo_name}")
        
        # Try common workflow file patterns
        possible_filenames = [
            f"{decoded_workflow_name}.yml",
            f"{decoded_workflow_name}.yaml",
            decoded_workflow_name if decoded_workflow_name.endswith(('.yml', '.yaml')) else None
        ]
        
        workflow_runs = []
        workflow_id = None
        
        # Try to get workflow runs using workflow filename
        for filename in filter(None, possible_filenames):
            try:
                logger.info(f"🔍 Trying workflow filename: {filename}")
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://api.github.com/repos/{org_name}/{repo_name}/actions/workflows/{filename}/runs",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28"
                        },
                        params={"per_page": 20},
                        timeout=30.0
                    )
                    
                    logger.info(f"📊 Response status for {filename}: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        workflow_runs = data.get("workflow_runs", [])
                        logger.info(f"✅ Found {len(workflow_runs)} runs for {filename}")
                        if workflow_runs:
                            workflow_id = workflow_runs[0].get("workflow_id")
                            break
                    elif response.status_code == 404:
                        logger.info(f"❌ Workflow file not found: {filename}")
                    
            except Exception as e:
                logger.warning(f"Error fetching runs for {filename}: {str(e)}")
                continue
        
        # Format the response and fetch job details for each run IN PARALLEL
        async def fetch_job_details(run, client):
            """Fetch job details for a single run"""
            try:
                jobs_response = await client.get(
                    f"https://api.github.com/repos/{org_name}/{repo_name}/actions/runs/{run.get('id')}/jobs",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28"
                    },
                    timeout=30.0
                )
                
                if jobs_response.status_code == 200:
                    jobs_data = jobs_response.json()
                    return jobs_data.get("jobs", [])
            except Exception as e:
                logger.warning(f"Error fetching jobs for run {run.get('id')}: {str(e)}")
            return []
        
        # Fetch all job details in parallel for better performance
        formatted_runs = []
        if workflow_runs:
            async with httpx.AsyncClient() as client:
                # Create tasks for parallel execution
                job_fetch_tasks = [fetch_job_details(run, client) for run in workflow_runs]
                
                # Execute all job fetches in parallel
                logger.info(f"🚀 Fetching job details for {len(workflow_runs)} runs in parallel...")
                all_jobs = await asyncio.gather(*job_fetch_tasks)
                
                # Combine runs with their job details
                for run, jobs in zip(workflow_runs, all_jobs):
                    formatted_runs.append({
                        "id": run.get("id"),
                        "name": run.get("name"),
                        "run_number": run.get("run_number"),
                        "status": run.get("status"),
                        "conclusion": run.get("conclusion"),
                        "created_at": run.get("created_at"),
                        "updated_at": run.get("updated_at"),
                        "html_url": run.get("html_url"),
                        "event": run.get("event"),
                        "head_branch": run.get("head_branch"),
                        "head_sha": run.get("head_sha")[:7] if run.get("head_sha") else None,
                        "actor": run.get("actor", {}).get("login") if run.get("actor") else None,
                        "run_started_at": run.get("run_started_at"),
                        "jobs": jobs,
                        "head_commit": run.get("head_commit"),
                        "triggering_actor": run.get("triggering_actor"),
                        "logs_url": run.get("logs_url")
                    })
        
        logger.info(f"✅ Returning {len(formatted_runs)} workflow runs with job details")
        
        return {
            "success": True,
            "workflow_name": decoded_workflow_name,
            "repository": repo_name,
            "organization": org_name,
            "total_runs": len(formatted_runs),
            "total_count": len(formatted_runs),
            "runs": formatted_runs,
            "workflow_id": workflow_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow history: {str(e)}")


@router.get("/workspace/{org_name}/actions/paginated")
async def get_actions_paginated(
    org_name: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query("")
):
    """
    Get paginated and searchable GitHub Actions information
    Async pattern: Returns cached data immediately and refreshes in background
    """
    try:
        # Try cache first - check paginated cache
        cached_data = await cache.get_cached_paginated_actions(org_name, page, per_page, search)
        if cached_data:
            logger.info(f"✅ Returning cached paginated data for {org_name} (page {page})")
            
            # Queue background refresh job (fire and forget)
            asyncio.create_task(
                cache.publish_refresh_job(
                    RefreshChannel.ACTIONS_REFRESH,
                    {
                        "type": RefreshJobType.ACTIONS_PAGINATED,
                        "org_name": org_name,
                        "user_id": None,
                        "timestamp": datetime.now().isoformat(),
                        "params": {"page": page, "per_page": per_page, "search": search}
                    }
                )
            )
            
            return {
                "message": f"GitHub Actions analysis for {org_name} (cached)",
                "organization": org_name,
                "page": page,
                "per_page": per_page,
                "search_query": search,
                "from_cache": True,
                "refreshing_in_background": True,
                **cached_data
            }
        
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in {org_name}")
        
        # Get actions data
        cached_actions = await cache.get_cached_actions(org_name)
        if cached_actions:
            logger.info(f"Using cached actions data for {org_name}")
            actions_data = cached_actions['actions']
        else:
            logger.info(f"Fetching fresh actions data for {org_name}")
            actions_data = await github_client.get_organization_actions_detailed(installation_id, org_name)
            await cache.cache_actions_data(org_name, actions_data)
        
        # Apply search filter
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
        
        # Transform data for table
        table_data = []
        for action in paginated_actions:
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
        
        # Calculate statistics
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
            "from_cache": False,
            "refreshing_in_background": False,
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
        
        await cache.cache_paginated_actions(org_name, page, per_page, search, result)
        
        logger.info(f"Analyzed {total_items} actions from {org_name} (page {page}/{total_pages})")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paginated organization actions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organizations/{org_name}/sync-realtime")
async def sync_organization_realtime(org_name: str):
    """
    Real-time sync organization data and detect changes
    Async pattern: Returns cached data immediately and triggers background refresh
    """
    try:
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail="Installation not found")
        
        # Get current cached data
        cache_key = github_client._get_cache_key('workspace', installation_id, org_name)
        cached_data = github_client._get_cached(cache_key)
        
        if cached_data:
            # Return cached status immediately and queue refresh
            logger.info(f"✅ Returning cached sync status for {org_name}")
            
            # Queue background refresh job (fire and forget)
            asyncio.create_task(
                cache.publish_refresh_job(
                    RefreshChannel.WORKSPACE_REFRESH,
                    {
                        "type": RefreshJobType.WORKSPACE_FULL,
                        "org_name": org_name,
                        "user_id": None,
                        "timestamp": datetime.now().isoformat(),
                        "params": {}
                    }
                )
            )
            
            return {
                "message": "Sync initiated (processing in background)",
                "organization": org_name,
                "total_repositories": cached_data.get("repository_count", 0),
                "total_workflows": len(cached_data.get("workflows", [])),
                "from_cache": True,
                "refreshing_in_background": True,
                "last_updated": cached_data.get("last_updated", datetime.now().isoformat())
            }
        
        # No cache - force fresh data synchronously (first time only)
        logger.info(f"⚠️ No cache for {org_name}, fetching fresh data...")
        fresh_data = await github_client.get_organization_workspace_detailed(installation_id, org_name, force_fresh=True)
        
        # Compare and detect changes
        changes = {
            "repositories": {"added": [], "removed": [], "updated": []},
            "workflows": {"added": [], "removed": [], "updated": []}
        }
        
        if cached_data:
            # Compare repositories
            old_repos = {repo["name"]: repo for repo in cached_data.get("repositories", [])}
            new_repos = {repo["name"]: repo for repo in fresh_data.get("repositories", [])}
            
            for repo_name, repo_data in new_repos.items():
                if repo_name not in old_repos:
                    changes["repositories"]["added"].append(repo_data)
            
            for repo_name, repo_data in old_repos.items():
                if repo_name not in new_repos:
                    changes["repositories"]["removed"].append(repo_data)
            
            # Compare workflows
            old_workflows = {f"{wf['repository']}/{wf['name']}": wf for wf in cached_data.get("workflows", [])}
            new_workflows = {f"{wf['repository']}/{wf['name']}": wf for wf in fresh_data.get("workflows", [])}
            
            for wf_key, wf_data in new_workflows.items():
                if wf_key not in old_workflows:
                    changes["workflows"]["added"].append(wf_data)
            
            for wf_key, wf_data in old_workflows.items():
                if wf_key not in new_workflows:
                    changes["workflows"]["removed"].append(wf_data)
        
        return {
            "message": "Real-time sync completed",
            "organization": org_name,
            "changes": changes,
            "processing_time": fresh_data.get("processing_time", "unknown"),
            "total_repositories": fresh_data.get("repository_count", 0),
            "total_workflows": fresh_data.get("total_workflows", 0),
            "has_changes": any(changes["repositories"].values()) or any(changes["workflows"].values()),
            "from_cache": False,
            "refreshing_in_background": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Real-time sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Real-time sync failed: {str(e)}")


@router.post("/workspace/{org_name}/actions/create-pr")
async def create_action_update_pr(org_name: str, request: Request):
    """
    Create a pull request to update a single outdated GitHub Action
    """
    try:
        from core.pr_creator import PRCreator
        
        body = await request.json()
        repo = body.get("repo")
        workflow_path = body.get("workflow_path")
        action_name = body.get("action_name")
        current_version = body.get("current_version")
        latest_version = body.get("latest_version")
        
        if not all([repo, workflow_path, action_name, current_version, latest_version]):
            missing_fields = []
            if not repo: missing_fields.append("repo")
            if not workflow_path: missing_fields.append("workflow_path")
            if not action_name: missing_fields.append("action_name")
            if not current_version: missing_fields.append("current_version")
            if not latest_version: missing_fields.append("latest_version")
            
            raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}")
        
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in organization {org_name}")
        
        pr_creator = PRCreator(github_client, installation_id)
        
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
            raise HTTPException(status_code=500, detail=f"Failed to create pull request: {result.get('error', 'Unknown error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating action update PR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create pull request: {str(e)}")


@router.post("/workspace/{org_name}/actions/create-bulk-pr")
async def create_bulk_action_update_pr(org_name: str, request: Request):
    """
    Create a pull request to update multiple outdated GitHub Actions
    """
    try:
        from core.pr_creator import PRCreator
        
        body = await request.json()
        repo = body.get("repo")
        workflow_path = body.get("workflow_path")
        actions = body.get("actions", [])
        
        if not all([repo, workflow_path, actions]):
            raise HTTPException(status_code=400, detail="Missing required fields: repo, workflow_path, actions")
        
        if not isinstance(actions, list) or len(actions) == 0:
            raise HTTPException(status_code=400, detail="Actions must be a non-empty list")
        
        for action in actions:
            if not all([action.get("action_name"), action.get("current_version"), action.get("latest_version")]):
                raise HTTPException(status_code=400, detail="Each action must have action_name, current_version, and latest_version")
        
        installation_id = await github_client._get_installation_id(org_name)
        if not installation_id:
            raise HTTPException(status_code=404, detail=f"GitHub App not installed in organization {org_name}")
        
        pr_creator = PRCreator(github_client, installation_id)
        
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
            raise HTTPException(status_code=500, detail=f"Failed to create bulk pull request: {result.get('error', 'Unknown error')}")
            
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
    Clear all cache entries for a specific organization
    Requires authentication
    """
    try:
        # Invalidate all organization cache (workspace, stats, etc.)
        cleared_count = await cache.invalidate_organization_cache(org_name)
        
        logger.info(f"🗑️ Cleared {cleared_count} cache entries for {org_name} by user {current_user}")
        
        return {
            "success": True,
            "message": f"Cleared cache for {org_name}",
            "cleared_entries": cleared_count,
            "org_name": org_name
        }
    except Exception as e:
        logger.error(f"Error clearing cache for {org_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for GitHub service"""
    return {
        "status": "healthy",
        "service": "github-service",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# PROJECT TREE PROXY ENDPOINTS (Forward to Workflow Orchestration Service)
# ============================================================================

@router.get("/project-tree/{org_name}")
async def get_project_tree(
    org_name: str,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Get project tree from Workflow Orchestration Service
    """
    import httpx
    import os
    
    try:
        workflow_service_url = os.getenv("WORKFLOW_ORCHESTRATION_SERVICE_URL", "http://workflow-orchestration-service:8007")
        
        async with httpx.AsyncClient() as client:
            # Forward headers
            headers = {
                "X-User-Id": current_user,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{workflow_service_url}/api/project-tree/{org_name}",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 404:
                return {"tree_data": [], "organization": org_name, "success": True}
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Workflow orchestration service error: {e}")
        if e.response.status_code == 404:
            return {"tree_data": {}, "node_count": 0, "workflow_count": 0, "folder_count": 0}
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error proxying to workflow orchestration service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/project-tree/{org_name}")
async def save_project_tree(
    org_name: str,
    tree_data: Dict,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Save project tree to Workflow Orchestration Service
    Publishes event for async processing
    """
    import httpx
    import os
    from core.event_bus import event_bus
    
    try:
        workflow_service_url = os.getenv("WORKFLOW_ORCHESTRATION_SERVICE_URL", "http://workflow-orchestration-service:8007")
        
        async with httpx.AsyncClient() as client:
            # Forward headers
            headers = {
                "X-User-Id": current_user,
                "Content-Type": "application/json"
            }
            
            response = await client.post(
                f"{workflow_service_url}/api/project-tree/{org_name}",
                json=tree_data,
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Publish event asynchronously
            await event_bus.publish({
                "type": "workflow.project_tree.saved",
                "data": {
                    "organization": org_name,
                    "user_id": current_user,
                    "tree_data": tree_data.get("tree_data", [])
                },
                "source": "github-service"
            })
            
            return result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Workflow orchestration service error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error proxying to workflow orchestration service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/project-tree/{org_name}")
async def delete_project_tree(
    org_name: str,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Delete project tree from backend service (project_trees table)
    Publishes event for async processing
    """
    import httpx
    import os
    from core.event_bus import event_bus
    
    try:
        backend_service_url = os.getenv("BACKEND_SERVICE_URL", "http://backend:8001")
        
        async with httpx.AsyncClient() as client:
            # Forward headers
            headers = {
                "X-User-Id": current_user,
                "Content-Type": "application/json"
            }
            
            response = await client.delete(
                f"{backend_service_url}/api/project-tree/{org_name}",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Publish event asynchronously
            await event_bus.publish({
                "type": "workflow.project_tree.deleted",
                "data": {
                    "organization": org_name,
                    "user_id": current_user
                },
                "source": "github-service"
            })
            
            return result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Workflow orchestration service error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error proxying to workflow orchestration service: {e}")
        raise HTTPException(status_code=500, detail=str(e))
