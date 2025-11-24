"""
Organization-based collaboration API routes
Secure collaboration based on GitHub organization membership
"""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import logging

from core.authorization import is_user_authorized_for_organization, get_organization_by_name
from database.config import db_manager
from database.models import User, Organization, OrganizationInstallation, CollaborationSession, CollaborationInvite
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

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
    current_user: str  # Passed from Kong/gateway authentication
):
    """
    Get list of users who have installed the app in the specified organization
    Only authorized organization members can see this list
    
    NOTE: current_user should be passed from authentication gateway (Kong/Backend)
    """
    
    # Check if current user is authorized for this organization
    if not await is_user_authorized_for_organization(current_user, org_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this organization"
        )
    
    # Get all users who have installed the app in this organization
    try:
        async with db_manager.get_session() as session:
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
                    user_id=user.auth_user_id,  # Use Auth0 user ID
                    email=user.email,
                    name=user.name or "Unknown User",
                    avatar_url=user.avatar_url,
                    github_username=user.github_username,
                    last_login=user.last_login,
                    is_online=False  # TODO: Implement real-time presence
                ))
            
            logger.info(f"Found {len(members)} members in organization {org_name}")
            return members
            
    except Exception as e:
        logger.error(f"Failed to fetch organization members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch organization members: {str(e)}"
        )


@router.post("/invite", response_model=CollaborationSessionResponse)
async def create_collaboration_invite(
    invite_request: CollaborationInviteRequest,
    current_user: str  # Passed from authentication gateway
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
    
    try:
        # Get organization
        org = await get_organization_by_name(invite_request.organization)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {invite_request.organization} not found"
            )
        
        # Create collaboration session
        session_id = str(uuid.uuid4())
        
        async with db_manager.get_session() as session:
            # Create session record
            collab_session = CollaborationSession(
                session_id=session_id,
                model_id=invite_request.model_id,
                organization_id=org.id,
                created_by=current_user,
                participants=[current_user] + invite_request.invited_user_ids,
                status="active"
            )
            session.add(collab_session)
            await session.flush()
            
            # Create invite records for each invited user
            for user_id in invite_request.invited_user_ids:
                invite = CollaborationInvite(
                    session_id=collab_session.id,
                    invited_by=current_user,
                    invited_user_id=user_id,
                    message=invite_request.message,
                    status="pending"
                )
                session.add(invite)
            
            await session.commit()
            
            logger.info(f"Created collaboration session {session_id} for model {invite_request.model_id}")
            
            return CollaborationSessionResponse(
                session_id=session_id,
                model_id=invite_request.model_id,
                organization=invite_request.organization,
                created_by=current_user,
                invited_users=invite_request.invited_user_ids,
                created_at=collab_session.created_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create collaboration invite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collaboration invite: {str(e)}"
        )


@router.get("/organization/{org_name}/sessions", response_model=List[CollaborationSessionResponse])
async def get_organization_collaboration_sessions(
    org_name: str,
    current_user: str  # Passed from authentication gateway
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
    
    try:
        async with db_manager.get_session() as session:
            stmt = (
                select(CollaborationSession)
                .join(Organization, CollaborationSession.organization_id == Organization.id)
                .where(
                    and_(
                        Organization.login == org_name,
                        CollaborationSession.status == "active"
                    )
                )
            )
            
            result = await session.execute(stmt)
            sessions = result.scalars().all()
            
            # Convert to response format
            session_responses = []
            for s in sessions:
                session_responses.append(CollaborationSessionResponse(
                    session_id=s.session_id,
                    model_id=s.model_id,
                    organization=org_name,
                    created_by=s.created_by,
                    invited_users=s.participants or [],
                    created_at=s.created_at,
                    expires_at=s.expires_at
                ))
            
            return session_responses
            
    except Exception as e:
        logger.error(f"Failed to fetch collaboration sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch collaboration sessions: {str(e)}"
        )


@router.get("/invites/pending", response_model=List[CollaborationInviteResponse])
async def get_pending_invitations(
    current_user: str  # Passed from authentication gateway
):
    """
    Get pending collaboration invitations for the current user
    """
    
    try:
        async with db_manager.get_session() as session:
            stmt = (
                select(CollaborationInvite, CollaborationSession, Organization)
                .join(CollaborationSession, CollaborationInvite.session_id == CollaborationSession.id)
                .join(Organization, CollaborationSession.organization_id == Organization.id)
                .where(
                    and_(
                        CollaborationInvite.invited_user_id == current_user,
                        CollaborationInvite.status == "pending"
                    )
                )
            )
            
            result = await session.execute(stmt)
            invites_data = result.all()
            
            # Convert to response format
            invite_responses = []
            for invite, collab_session, org in invites_data:
                invite_responses.append(CollaborationInviteResponse(
                    invite_id=invite.id,
                    session_id=collab_session.session_id,
                    invited_by=invite.invited_by,
                    organization=org.login,
                    model_id=collab_session.model_id,
                    message=invite.message,
                    created_at=invite.created_at,
                    status=invite.status
                ))
            
            return invite_responses
            
    except Exception as e:
        logger.error(f"Failed to fetch pending invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending invitations: {str(e)}"
        )


@router.post("/invites/{invite_id}/accept")
async def accept_collaboration_invite(
    invite_id: str,
    current_user: str  # Passed from authentication gateway
):
    """
    Accept a collaboration invitation
    """
    
    try:
        async with db_manager.get_session() as session:
            # Get invite
            stmt = select(CollaborationInvite).where(CollaborationInvite.id == invite_id)
            result = await session.execute(stmt)
            invite = result.scalar_one_or_none()
            
            if not invite:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invitation not found"
                )
            
            # Verify current user is the invited user
            if invite.invited_user_id != current_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to accept this invitation"
                )
            
            # Update invitation status
            invite.status = "accepted"
            invite.responded_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"User {current_user} accepted invitation {invite_id}")
            return {"message": "Invitation accepted", "invite_id": invite_id}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to accept invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept invitation: {str(e)}"
        )


@router.post("/invites/{invite_id}/decline")
async def decline_collaboration_invite(
    invite_id: str,
    current_user: str  # Passed from authentication gateway
):
    """
    Decline a collaboration invitation
    """
    
    try:
        async with db_manager.get_session() as session:
            # Get invite
            stmt = select(CollaborationInvite).where(CollaborationInvite.id == invite_id)
            result = await session.execute(stmt)
            invite = result.scalar_one_or_none()
            
            if not invite:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invitation not found"
                )
            
            # Verify current user is the invited user
            if invite.invited_user_id != current_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to decline this invitation"
                )
            
            # Update invitation status
            invite.status = "declined"
            invite.responded_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"User {current_user} declined invitation {invite_id}")
            return {"message": "Invitation declined", "invite_id": invite_id}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to decline invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decline invitation: {str(e)}"
        )


@router.get("/session/{session_id}/status")
async def get_collaboration_session_status(
    session_id: str,
    current_user: str  # Passed from authentication gateway
):
    """
    Get collaboration session status and participant list
    """
    
    try:
        async with db_manager.get_session() as session:
            # Get session
            stmt = select(CollaborationSession).where(CollaborationSession.session_id == session_id)
            result = await session.execute(stmt)
            collab_session = result.scalar_one_or_none()
            
            if not collab_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            
            # Verify user has access to this session
            if current_user not in (collab_session.participants or []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this session"
                )
            
            return {
                "session_id": session_id,
                "status": collab_session.status,
                "participants": collab_session.participants or [],
                "created_at": collab_session.created_at.isoformat(),
                "model_id": collab_session.model_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}"
        )
