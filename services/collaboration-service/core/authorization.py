"""
Authorization helpers for collaboration service
"""
import logging
from sqlalchemy import select, and_
from database.models import User, Organization, OrganizationInstallation
from database.config import db_manager

logger = logging.getLogger(__name__)


async def is_user_authorized_for_organization(user_id: str, org_name: str) -> bool:
    """
    Check if user has access to organization based on GitHub App installation
    
    Args:
        user_id: Auth0 user ID
        org_name: GitHub organization login name
    
    Returns:
        True if user is authorized, False otherwise
    """
    try:
        async with db_manager.get_session() as session:
            # Query to check if user has active installation for this organization
            stmt = (
                select(OrganizationInstallation)
                .join(Organization, OrganizationInstallation.organization_id == Organization.id)
                .join(User, OrganizationInstallation.user_id == User.id)
                .where(
                    and_(
                        User.auth_user_id == user_id,
                        Organization.login == org_name,
                        OrganizationInstallation.status == "active"
                    )
                )
            )
            
            result = await session.execute(stmt)
            installation = result.scalar_one_or_none()
            
            is_authorized = installation is not None
            logger.info(f"Authorization check for user {user_id} in org {org_name}: {is_authorized}")
            return is_authorized
            
    except Exception as e:
        logger.error(f"Error checking authorization: {e}")
        return False


async def get_user_by_auth_id(auth_user_id: str):
    """Get user by Auth0 user ID"""
    try:
        async with db_manager.get_session() as session:
            stmt = select(User).where(User.auth_user_id == auth_user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return None


async def get_organization_by_name(org_name: str):
    """Get organization by login name"""
    try:
        async with db_manager.get_session() as session:
            stmt = select(Organization).where(Organization.login == org_name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error fetching organization: {e}")
        return None
