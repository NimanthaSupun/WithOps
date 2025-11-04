"""
Organization-based collaboration API routes
Secure collaboration based on GitHub organization membership
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from core.user_storage_db import (
    is_user_authorized_for_organization,
    get_user_installed_organizations
)
from core.security import get_current_user
from database.config import get_db_session
from database.models import User, Organization, OrganizationInstallation
from database.operations import OrganizationInstallationRepository
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])

# Pydantic Models
class OrganizationMemberResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    github_username: Optional[str] = None
    last_login: Optional[datetime] = None
    is_online: bool = False

class CollaborationInviteRequest(BaseModel):
    organization: str = Field(..., description="GitHub organization name")
    model_id: str = Field(..., description="Threat model ID")
    invited_user_ids: List[str] = Field(..., description="List of user IDs to invite")
    message: Optional[str] = Field(None, description="Optional invitation message")

class CollaborationSessionResponse(BaseModel):
    session_id: str
    model_id: str
    organization: str
    created_by: str
    invited_users: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None

class CollaborationInviteResponse(BaseModel):
    invite_id: str
    session_id: str
    invited_by: str
    organization: str
    model_id: str
    message: Optional[str] = None
    created_at: datetime
    status: str = "pending"  # pending, accepted, declined, expired

@router.get("/organization/{org_name}/members", response_model=List[OrganizationMemberResponse])
async def get_organization_members(
    org_name: str,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get list of users who have installed the app in the specified organization
    Only authorized organization members can see this list
    """
    
    # Check if current user is authorized for this organization
    if not await is_user_authorized_for_organization(current_user, org_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this organization"
        )
    
    # Get all users who have installed the app in this organization
    try:
        stmt = (
            select(User)
            .join(OrganizationInstallation, User.id == OrganizationInstallation.user_id)
            .join(Organization, OrganizationInstallation.organization_id == Organization.id)
            .where(
                and_(
                    Organization.login == org_name,
                    OrganizationInstallation.status == "active"
                )
            )
        )
        
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        # Convert to response format
        members = []
        for user in users:
            members.append(OrganizationMemberResponse(
                user_id=user.auth_user_id,  # Use Auth0 user ID, not database ID
                email=user.email,
                name=user.name or "Unknown User",  # Provide fallback for missing names
                avatar_url=user.avatar_url,
                github_username=user.github_username,
                last_login=user.last_login,
                is_online=False  # TODO: Implement real-time presence
            ))
        
        return members
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch organization members: {str(e)}"
        )

@router.post("/invite", response_model=CollaborationSessionResponse)
async def create_collaboration_invite(
    invite_request: CollaborationInviteRequest,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create a collaboration invitation for organization members
    Only authorized organization members can create invitations
    """
    
    # Check if current user is authorized for this organization
    if not await is_user_authorized_for_organization(current_user, invite_request.organization):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create invitations for this organization"
        )
    
    # Verify all invited users are authorized for this organization
    for user_id in invite_request.invited_user_ids:
        if not await is_user_authorized_for_organization(user_id, invite_request.organization):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {user_id} is not authorized for organization {invite_request.organization}"
            )
    
    # Create collaboration session
    # TODO: Store this in database with proper session management
    import uuid
    session_id = str(uuid.uuid4())
    
    collaboration_session = CollaborationSessionResponse(
        session_id=session_id,
        model_id=invite_request.model_id,
        organization=invite_request.organization,
        created_by=current_user,
        invited_users=invite_request.invited_user_ids,
        created_at=datetime.utcnow()
    )
    
    # TODO: Send real-time notifications to invited users
    # TODO: Store invitation records in database
    
    return collaboration_session

@router.get("/organization/{org_name}/sessions", response_model=List[CollaborationSessionResponse])
async def get_organization_collaboration_sessions(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get active collaboration sessions for the organization
    """
    
    # Check if current user is authorized for this organization
    if not await is_user_authorized_for_organization(current_user, org_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this organization"
        )
    
    # TODO: Implement database storage for collaboration sessions
    # For now, return empty list
    return []

@router.get("/invites/pending", response_model=List[CollaborationInviteResponse])
async def get_pending_invitations(
    current_user: str = Depends(get_current_user)
):
    """
    Get pending collaboration invitations for the current user
    """
    
    # TODO: Implement database storage for invitations
    # For now, return empty list
    return []

@router.post("/invites/{invite_id}/accept")
async def accept_collaboration_invite(
    invite_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Accept a collaboration invitation
    """
    
    # TODO: Implement invitation acceptance logic
    # 1. Verify invitation exists and is pending
    # 2. Verify current user is the invited user
    # 3. Update invitation status
    # 4. Add user to collaboration session
    
    return {"message": "Invitation accepted", "invite_id": invite_id}

@router.post("/invites/{invite_id}/decline")
async def decline_collaboration_invite(
    invite_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Decline a collaboration invitation
    """
    
    # TODO: Implement invitation decline logic
    return {"message": "Invitation declined", "invite_id": invite_id}

@router.get("/session/{session_id}/status")
async def get_collaboration_session_status(
    session_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get collaboration session status and participant list
    """
    
    # TODO: Implement session status retrieval
    # 1. Verify user has access to this session
    # 2. Return session details, active participants, etc.
    
    return {
        "session_id": session_id,
        "status": "active",
        "participants": [],
        "created_at": datetime.utcnow().isoformat()
    }
