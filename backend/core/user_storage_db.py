"""
Database-backed user storage system using Supabase
Replaces the in-memory storage with proper database operations
"""

from typing import Optional, Dict, List
import asyncio
from database.operations import (
    user_repo, github_token_repo, organization_repo, 
    installation_repo, audit_repo
)
from database.config import db_manager
from database.models import User, OrganizationInstallation, Organization
from sqlalchemy import select
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseUserStorage:
    """Database-backed user storage for secure multi-user support"""
    
    async def store_user_github_token(self, user_id: str, access_token: str, user_info: Dict) -> None:
        """Store GitHub access token for a user (DATABASE VERSION)"""
        async with db_manager.get_session() as session:
            # Get or create user
            user = await user_repo.create_or_update_user(
                session,
                auth_user_id=user_id,
                email=user_info.get('email', ''),
                name=user_info.get('name', user_info.get('login')),
                avatar_url=user_info.get('avatar_url'),
                github_username=user_info.get('login'),
                github_user_id=user_info.get('id')
            )
            
            # Store GitHub token
            await github_token_repo.store_github_token(
                session,
                user_id=user.id,
                access_token=access_token,
                token_type="oauth",
                github_user_info=user_info
            )
            
            # Log the action
            await audit_repo.log_action(
                session,
                user_id=user.id,
                action="store_github_token",
                event_data={"github_username": user_info.get('login')}
            )
            
            await session.commit()
        
        logger.info(f"✅ Stored GitHub token for user: {user_id}")

    async def get_user_github_token(self, user_id: str) -> Optional[str]:
        """Get GitHub access token for a user (DATABASE VERSION)"""
        async with db_manager.get_session() as session:
            # Get user
            user = await user_repo.get_user_by_auth_id(session, user_id)
            if not user:
                return None
            
            # Get active token
            token = await github_token_repo.get_active_token(session, user.id)
            return token.access_token if token else None

    async def get_user_github_info(self, user_id: str) -> Optional[Dict]:
        """Get stored GitHub user info (DATABASE VERSION)"""
        async with db_manager.get_session() as session:
            # Get user
            user = await user_repo.get_user_by_auth_id(session, user_id)
            if not user:
                return None
            
            # Get active token with user info
            token = await github_token_repo.get_active_token(session, user.id)
            return token.github_user_info if token else None

    async def user_has_github_token(self, user_id: str) -> bool:
        """Check if user has a GitHub token stored (DATABASE VERSION)"""
        token = await self.get_user_github_token(user_id)
        return token is not None

    async def remove_user_github_token(self, user_id: str) -> bool:
        """Remove user's GitHub token (DATABASE VERSION)"""
        async with db_manager.get_session() as session:
            # Get user
            user = await user_repo.get_user_by_auth_id(session, user_id)
            if not user:
                return False
            
            # Revoke all tokens
            revoked_count = await github_token_repo.revoke_user_tokens(session, user.id)
            
            # Log the action
            await audit_repo.log_action(
                session,
                user_id=user.id,
                action="remove_github_token",
                event_data={"revoked_tokens": revoked_count}
            )
            
            await session.commit()
            
            if revoked_count > 0:
                logger.info(f"🗑️ Removed GitHub token for user: {user_id}")
                return True
            return False

    async def record_organization_installation(self, user_id: str, org_name: str, installation_data: Dict) -> None:
        """Record that a user has installed the app in an organization (DATABASE VERSION - IMPROVED)"""
        async with db_manager.get_session() as session:
            # Get or create user
            user = await user_repo.get_user_by_auth_id(session, user_id)
            if not user:
                # Create user if they don't exist
                user = await user_repo.create_or_update_user(
                    session,
                    auth_user_id=user_id,
                    email=f"{user_id}@unknown.com",  # Placeholder email
                    name=f"User {user_id.split('|')[-1]}"  # Extract ID from auth user ID
                )
                logger.info(f"Created user: {user_id}")
            
            # Handle organization with improved duplicate prevention
            org_info = installation_data.get('organization', {})
            organization = await self._get_or_create_organization_safe(
                session,
                github_org_id=org_info.get('id'),
                login=org_name,
                name=org_info.get('name'),
                description=org_info.get('description'),
                avatar_url=org_info.get('avatar_url'),
                html_url=org_info.get('html_url'),
                org_type=org_info.get('type'),
                github_metadata=org_info
            )
            
            # Handle installation with improved duplicate prevention
            installation = await self._handle_installation_safe(
                session,
                user_id=user.id,
                organization_id=organization.id,
                github_installation_id=installation_data.get('installation_id'),
                permissions=installation_data.get('permissions'),
                events=installation_data.get('events'),
                installation_metadata=installation_data
            )
            
            # Log the action
            await audit_repo.log_action(
                session,
                user_id=user.id,
                action="install_github_app",
                resource_type="organization",
                resource_id=organization.id,
                event_data={"organization": org_name, "installation_id": installation_data.get('installation_id')}
            )
            
            await session.commit()
        
        logger.info(f"🔐 Recorded installation: {org_name} installed by {user_id}")

    async def get_user_installed_organizations(self, user_id: str) -> List[str]:
        """Get list of organizations that this user has installed (DATABASE VERSION)"""
        async with db_manager.get_session() as session:
            # Get user
            user = await user_repo.get_user_by_auth_id(session, user_id)
            if not user:
                return []
            
            # Get user's installations
            installations = await installation_repo.get_user_installations(session, user.id)
            return [installation.organization.login for installation in installations]

    async def is_user_authorized_for_organization(self, user_id: str, org_name: str) -> bool:
        """Check if user is authorized to access this organization (DATABASE VERSION)"""
        async with db_manager.get_session() as session:
            # Get user
            user = await user_repo.get_user_by_auth_id(session, user_id)
            if not user:
                return False
            
            # Check authorization
            authorized = await installation_repo.is_user_authorized_for_organization(
                session, user.id, org_name
            )
            
            # Log access attempt
            await audit_repo.log_action(
                session,
                user_id=user.id,
                action="check_organization_access",
                resource_type="organization",
                resource_id=org_name,
                event_data={"organization": org_name},
                status="success" if authorized else "denied"
            )
            
            await session.commit()
            return authorized

    async def get_organization_installer(self, org_name: str) -> Optional[str]:
        """Get the user ID who installed this organization (DATABASE VERSION)"""
        async with db_manager.get_session() as session:
            user_id = await installation_repo.get_organization_installer(session, org_name)
            if user_id:
                # Convert back to auth_user_id
                user = await session.get(User, user_id)
                return user.auth_user_id if user else None
            return None

    async def remove_organization_installation(self, org_name: str) -> bool:
        """Remove organization installation (DATABASE VERSION)"""
        async with db_manager.get_session() as session:
            # Get organization
            organization = await organization_repo.get_organization_by_login(session, org_name)
            if not organization:
                return False
            
            # Get installation
            stmt = select(OrganizationInstallation).where(
                OrganizationInstallation.organization_id == organization.id
            )
            result = await session.execute(stmt)
            # Use scalars().first() instead of scalar_one_or_none() to handle multiple installations
            installation = result.scalars().first()
            
            if installation:
                # Mark as deleted
                removed = await installation_repo.remove_installation(
                    session, installation.github_installation_id
                )
                
                # Log the action
                await audit_repo.log_action(
                    session,
                    user_id=installation.user_id,
                    action="uninstall_github_app",
                    resource_type="organization",
                    resource_id=organization.id,
                    event_data={"organization": org_name}
                )
                
                await session.commit()
                
                if removed:
                    logger.info(f"🗑️ Removed installation record for: {org_name}")
                    return True
            
            return False

    async def cleanup_stale_installations(self) -> int:
        """Clean up installations that no longer exist on GitHub"""
        async with db_manager.get_session() as session:
            from core.github_client import github_client
            cleaned_count = await installation_repo.cleanup_stale_installations(session, github_client)
            await session.commit()
            return cleaned_count
    
    async def remove_organization_installation_by_name(self, org_name: str) -> bool:
        """Remove organization installation by name"""
        async with db_manager.get_session() as session:
            removed = await installation_repo.remove_installation_by_org_name(session, org_name)
            await session.commit()
            return removed

    async def _get_or_create_organization_safe(
        self,
        session,
        github_org_id: int,
        login: str,
        name: str = None,
        description: str = None,
        avatar_url: str = None,
        html_url: str = None,
        org_type: str = None,
        github_metadata: Dict = None
    ) -> Organization:
        """
        Get or create organization with proper duplicate prevention
        """
        from database.models import Organization
        from sqlalchemy import select
        
        # First, try to find by GitHub org ID (most reliable)
        stmt = select(Organization).where(Organization.github_org_id == github_org_id)
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate organizations
        org = result.scalars().first()
        
        if org:
            # Update existing organization
            org.login = login
            org.name = name or org.name
            org.description = description or org.description
            org.avatar_url = avatar_url or org.avatar_url
            org.html_url = html_url or org.html_url
            org.type = org_type or org.type
            org.github_metadata = github_metadata or org.github_metadata
            org.updated_at = datetime.utcnow()
            logger.info(f"✅ Updated existing organization: {login}")
            return org
        
        # If not found by ID, check by login (handle edge case)
        stmt = select(Organization).where(Organization.login == login)
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate organizations
        org = result.scalars().first()
        
        if org:
            # Update the GitHub org ID if it was missing
            org.github_org_id = github_org_id
            org.name = name or org.name
            org.description = description or org.description
            org.avatar_url = avatar_url or org.avatar_url
            org.html_url = html_url or org.html_url
            org.type = org_type or org.type
            org.github_metadata = github_metadata or org.github_metadata
            org.updated_at = datetime.utcnow()
            logger.info(f"✅ Updated organization with GitHub ID: {login}")
            return org
        
        # Create new organization
        org = Organization(
            github_org_id=github_org_id,
            login=login,
            name=name,
            description=description,
            avatar_url=avatar_url,
            html_url=html_url,
            type=org_type,
            github_metadata=github_metadata
        )
        session.add(org)
        await session.flush()
        logger.info(f"✅ Created new organization: {login}")
        return org
    
    async def _handle_installation_safe(
        self,
        session,
        user_id: str,
        organization_id: str,
        github_installation_id: int,
        permissions: Dict = None,
        events: List = None,
        installation_metadata: Dict = None
    ) -> OrganizationInstallation:
        """
        Handle installation with proper duplicate prevention and reactivation
        """
        from database.models import OrganizationInstallation
        from sqlalchemy import select, and_
        
        # Check for existing installation by GitHub installation ID
        stmt = select(OrganizationInstallation).where(
            OrganizationInstallation.github_installation_id == github_installation_id
        )
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate installations
        existing_installation = result.scalars().first()
        
        if existing_installation:
            # Reactivate existing installation
            existing_installation.status = "active"
            existing_installation.user_id = user_id
            existing_installation.organization_id = organization_id
            existing_installation.permissions = permissions
            existing_installation.events = events
            existing_installation.installation_metadata = installation_metadata
            existing_installation.updated_at = datetime.utcnow()
            existing_installation.uninstalled_at = None
            logger.info(f"✅ Reactivated existing installation: {github_installation_id}")
            return existing_installation
        
        # Check for any existing installation for this user+org combination
        stmt = select(OrganizationInstallation).where(
            and_(
                OrganizationInstallation.user_id == user_id,
                OrganizationInstallation.organization_id == organization_id,
                OrganizationInstallation.status == "active"
            )
        )
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate user-org installations
        existing_user_org_installation = result.scalars().first()
        
        if existing_user_org_installation:
            # Update existing installation with new GitHub installation ID
            existing_user_org_installation.github_installation_id = github_installation_id
            existing_user_org_installation.permissions = permissions
            existing_user_org_installation.events = events
            existing_user_org_installation.installation_metadata = installation_metadata
            existing_user_org_installation.updated_at = datetime.utcnow()
            logger.info(f"✅ Updated existing user-org installation: {github_installation_id}")
            return existing_user_org_installation
        
        # Create new installation
        installation = OrganizationInstallation(
            user_id=user_id,
            organization_id=organization_id,
            github_installation_id=github_installation_id,
            permissions=permissions,
            events=events,
            installation_metadata=installation_metadata,
            status="active"
        )
        session.add(installation)
        await session.flush()
        logger.info(f"✅ Created new installation: {github_installation_id}")
        return installation

    async def handle_organization_uninstallation(self, github_installation_id: int) -> bool:
        """Handle GitHub App uninstallation"""
        async with db_manager.get_session() as session:
            try:
                # Find installation by GitHub installation ID
                stmt = select(OrganizationInstallation).where(
                    OrganizationInstallation.github_installation_id == github_installation_id
                )
                result = await session.execute(stmt)
                # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate installations
                installation = result.scalars().first()
                
                if installation:
                    # Mark as deleted instead of removing
                    installation.status = "deleted"
                    installation.uninstalled_at = datetime.utcnow()
                    installation.updated_at = datetime.utcnow()
                    
                    # Log the uninstallation
                    await audit_repo.log_action(
                        session,
                        user_id=installation.user_id,
                        action="uninstall_app",
                        resource_type="organization",
                        resource_id=str(installation.organization_id),
                        event_data={"github_installation_id": github_installation_id},
                        status="success"
                    )
                    
                    await session.commit()
                    logger.info(f"✅ Marked installation {github_installation_id} as uninstalled")
                    return True
                else:
                    logger.warning(f"⚠️ Installation {github_installation_id} not found for uninstallation")
                    return False
                    
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to handle uninstallation: {str(e)}")
                return False

# Global database storage instance
db_storage = DatabaseUserStorage()

# Legacy wrapper functions for backward compatibility
async def store_user_github_token(user_id: str, access_token: str, user_info: Dict) -> None:
    await db_storage.store_user_github_token(user_id, access_token, user_info)

async def get_user_github_token(user_id: str) -> Optional[str]:
    return await db_storage.get_user_github_token(user_id)

async def get_user_github_info(user_id: str) -> Optional[Dict]:
    return await db_storage.get_user_github_info(user_id)

async def user_has_github_token(user_id: str) -> bool:
    return await db_storage.user_has_github_token(user_id)

async def remove_user_github_token(user_id: str) -> bool:
    return await db_storage.remove_user_github_token(user_id)

async def record_organization_installation(user_id: str, org_name: str, installation_data: Dict) -> None:
    await db_storage.record_organization_installation(user_id, org_name, installation_data)

async def get_user_installed_organizations(user_id: str) -> List[str]:
    return await db_storage.get_user_installed_organizations(user_id)

async def is_user_authorized_for_organization(user_id: str, org_name: str) -> bool:
    return await db_storage.is_user_authorized_for_organization(user_id, org_name)

async def get_organization_installer(org_name: str) -> Optional[str]:
    return await db_storage.get_organization_installer(org_name)

async def remove_organization_installation(org_name: str) -> bool:
    return await db_storage.remove_organization_installation(org_name)

async def cleanup_stale_installations() -> int:
    """Clean up installations that no longer exist on GitHub"""
    return await db_storage.cleanup_stale_installations()

async def remove_organization_installation_by_name(org_name: str) -> bool:
    """Remove organization installation by name"""
    return await db_storage.remove_organization_installation_by_name(org_name)

# Legacy compatibility - these should not be used anymore
user_tokens: Dict[str, Dict] = {}
user_organizations: Dict[str, str] = {}
user_installed_organizations: Dict[str, List[str]] = {}
organization_installers: Dict[str, str] = {}
installation_metadata: Dict[str, Dict] = {}

# Legacy class for old code compatibility
class UserStorage:
    """Legacy UserStorage class - now uses database"""
    
    async def set_user_workspace(self, user_id: str, workspace_info: Dict) -> None:
        logger.warning("set_user_workspace is deprecated - workspace info is now stored in database")
    
    async def get_user_workspace(self, user_id: str) -> Optional[Dict]:
        logger.warning("get_user_workspace is deprecated - use database operations instead")
        return None
    
    async def clear_user_workspace(self, user_id: str) -> bool:
        logger.warning("clear_user_workspace is deprecated")
        return False
    
    async def has_user_workspace(self, user_id: str) -> bool:
        logger.warning("has_user_workspace is deprecated")
        return False
    
    async def store_discovered_organizations(self, user_id: str, organizations: List[Dict]) -> None:
        logger.warning("store_discovered_organizations is deprecated")
    
    async def get_discovered_organizations(self, user_id: str) -> List[Dict]:
        logger.warning("get_discovered_organizations is deprecated")
        return []

# Global instance for backward compatibility
user_storage = UserStorage()
