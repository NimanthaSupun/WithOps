from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json
import logging

from .models import User, GitHubToken, Organization, OrganizationInstallation, Repository, Workflow, AuditLog
from .config import db_manager

logger = logging.getLogger(__name__)

class UserRepository:
    """User-related database operations"""
    
    @staticmethod
    async def create_or_update_user(
        session: AsyncSession,
        auth_user_id: str,
        email: str,
        name: str = None,
        avatar_url: str = None,
        github_username: str = None,
        github_user_id: int = None
    ) -> User:
        """Create or update user"""
        
        # Check if user exists
        stmt = select(User).where(User.auth_user_id == auth_user_id)
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate users
        user = result.scalars().first()
        
        if user:
            # Update existing user
            user.email = email
            user.name = name or user.name
            user.avatar_url = avatar_url or user.avatar_url
            user.github_username = github_username or user.github_username
            user.github_user_id = github_user_id or user.github_user_id
            user.updated_at = datetime.utcnow()
            user.last_login = datetime.utcnow()
            logger.info(f"Updated existing user: {auth_user_id}")
        else:
            # Create new user
            user = User(
                auth_user_id=auth_user_id,
                email=email,
                name=name,
                avatar_url=avatar_url,
                github_username=github_username,
                github_user_id=github_user_id,
                last_login=datetime.utcnow()
            )
            session.add(user)
            logger.info(f"Created new user: {auth_user_id}")
        
        await session.flush()
        return user
    
    @staticmethod
    async def get_user_by_auth_id(session: AsyncSession, auth_user_id: str) -> Optional[User]:
        """Get user by Auth0 user ID"""
        stmt = select(User).where(User.auth_user_id == auth_user_id)
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate users
        return result.scalars().first()
    
    @staticmethod
    async def get_user_with_tokens(session: AsyncSession, auth_user_id: str) -> Optional[User]:
        """Get user with GitHub tokens"""
        stmt = select(User).options(
            selectinload(User.github_tokens)
        ).where(User.auth_user_id == auth_user_id)
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate users
        return result.scalars().first()


class GitHubTokenRepository:
    """GitHub token management"""
    
    @staticmethod
    async def store_github_token(
        session: AsyncSession,
        user_id: str,
        access_token: str,
        token_type: str = "oauth",
        scope: str = None,
        expires_at: datetime = None,
        github_user_info: Dict = None
    ) -> GitHubToken:
        """Store GitHub access token for user"""
        
        # Remove existing tokens of the same type
        await session.execute(
            delete(GitHubToken).where(
                and_(GitHubToken.user_id == user_id, GitHubToken.token_type == token_type)
            )
        )
         
        # Create new token
        token = GitHubToken(
            user_id=user_id,
            access_token=access_token,  # TODO: Encrypt in production
            token_type=token_type,
            scope=scope,
            expires_at=expires_at,
            github_user_info=github_user_info,
            last_used=datetime.utcnow()
        )
        
        session.add(token)
        await session.flush()
        
        logger.info(f"Stored GitHub token for user: {user_id}")
        return token
    
    @staticmethod
    async def get_active_token(session: AsyncSession, user_id: str, token_type: str = "oauth") -> Optional[GitHubToken]:
        """Get active GitHub token for user"""
        stmt = select(GitHubToken).where(
            and_(
                GitHubToken.user_id == user_id,
                GitHubToken.token_type == token_type,
                GitHubToken.is_active == True,
                or_(GitHubToken.expires_at.is_(None), GitHubToken.expires_at > datetime.utcnow())
            )
        )
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate tokens
        token = result.scalars().first()
        
        if token:
            # Update last used
            token.last_used = datetime.utcnow()
            await session.flush()
        
        return token
    
    @staticmethod
    async def revoke_user_tokens(session: AsyncSession, user_id: str) -> int:
        """Revoke all tokens for a user"""
        stmt = update(GitHubToken).where(GitHubToken.user_id == user_id).values(is_active=False)
        result = await session.execute(stmt)
        return result.rowcount


class OrganizationRepository:
    """Organization management"""
    
    @staticmethod
    async def create_or_update_organization(
        session: AsyncSession,
        github_org_id: int,
        login: str,
        name: str = None,
        description: str = None,
        avatar_url: str = None,
        html_url: str = None,
        org_type: str = None,
        github_metadata: Dict = None
    ) -> Organization:
        """Create or update organization"""
        
        # Check if organization exists
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
            logger.info(f"Updated organization: {login}")
        else:
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
            logger.info(f"Created new organization: {login}")
        
        await session.flush()
        return org
    
    @staticmethod
    async def get_organization_by_login(session: AsyncSession, login: str) -> Optional[Organization]:
        """Get organization by login"""
        stmt = select(Organization).where(Organization.login == login)
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate organizations
        return result.scalars().first()


class OrganizationInstallationRepository:
    """Organization installation management (SECURE)"""
    
    @staticmethod
    async def create_installation(
        session: AsyncSession,
        user_id: str,
        organization_id: str,
        github_installation_id: int,
        permissions: Dict = None,
        events: List = None,
        installation_metadata: Dict = None,
        repository_selection: str = "all",
        selected_repositories: List = None
    ) -> OrganizationInstallation:
        """Create new installation record with improved duplicate handling"""
        
        # Check for existing installation by GitHub installation ID
        stmt = select(OrganizationInstallation).where(
            OrganizationInstallation.github_installation_id == github_installation_id
        )
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate installations
        existing_installation = result.scalars().first()
        
        if existing_installation:
            # Update existing installation instead of creating duplicate
            existing_installation.user_id = user_id
            existing_installation.organization_id = organization_id
            existing_installation.permissions = permissions
            existing_installation.events = events
            existing_installation.installation_metadata = installation_metadata
            existing_installation.repository_selection = repository_selection
            existing_installation.selected_repositories = selected_repositories
            existing_installation.status = "active"
            existing_installation.updated_at = datetime.utcnow()
            existing_installation.uninstalled_at = None
            
            logger.info(f"Updated existing installation: {github_installation_id} for user: {user_id}")
            return existing_installation
        
        # Check for any existing active installation for this user+org combination
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
            existing_user_org_installation.repository_selection = repository_selection
            existing_user_org_installation.selected_repositories = selected_repositories
            existing_user_org_installation.updated_at = datetime.utcnow()
            
            logger.info(f"Updated existing user-org installation: {github_installation_id} for user: {user_id}")
            return existing_user_org_installation
        
        # Create new installation
        installation = OrganizationInstallation(
            user_id=user_id,
            organization_id=organization_id,
            github_installation_id=github_installation_id,
            permissions=permissions,
            events=events,
            installation_metadata=installation_metadata,
            repository_selection=repository_selection,
            selected_repositories=selected_repositories
        )
        
        session.add(installation)
        await session.flush()
        
        logger.info(f"Created new installation: {github_installation_id} for user: {user_id}")
        return installation
    
    @staticmethod
    async def get_user_installations(session: AsyncSession, user_id: str) -> List[OrganizationInstallation]:
        """Get all installations for a user (SECURE)"""
        stmt = select(OrganizationInstallation).options(
            selectinload(OrganizationInstallation.organization)
        ).where(
            and_(
                OrganizationInstallation.user_id == user_id,
                OrganizationInstallation.status == "active"
            )
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def is_user_authorized_for_organization(
        session: AsyncSession, 
        user_id: str, 
        org_login: str
    ) -> bool:
        """Check if user is authorized to access organization (SECURE)"""
        stmt = select(OrganizationInstallation).join(Organization).where(
            and_(
                OrganizationInstallation.user_id == user_id,
                Organization.login == org_login,
                OrganizationInstallation.status == "active"
            )
        )
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle multiple installations
        return result.scalars().first() is not None
    
    @staticmethod
    async def get_organization_installer(session: AsyncSession, org_login: str) -> Optional[str]:
        """Get the user ID who installed the app in this organization"""
        stmt = select(OrganizationInstallation.user_id).join(Organization).where(
            and_(
                Organization.login == org_login,
                OrganizationInstallation.status == "active"
            )
        )
        result = await session.execute(stmt)
        # Use scalars().first() instead of scalar_one_or_none() to handle multiple installations
        return result.scalars().first()
    
    @staticmethod
    async def remove_installation(session: AsyncSession, github_installation_id: int) -> bool:
        """Remove installation (mark as deleted)"""
        stmt = update(OrganizationInstallation).where(
            OrganizationInstallation.github_installation_id == github_installation_id
        ).values(
            status="deleted",
            uninstalled_at=datetime.utcnow()
        )
        result = await session.execute(stmt)
        return result.rowcount > 0
    
    @staticmethod
    async def remove_installation_by_org_name(session: AsyncSession, org_login: str) -> bool:
        """Remove installation by organization name (mark as deleted)"""
        stmt = update(OrganizationInstallation).join(Organization).where(
            Organization.login == org_login
        ).values(
            status="deleted",
            uninstalled_at=datetime.utcnow()
        )
        result = await session.execute(stmt)
        return result.rowcount > 0
    
    @staticmethod
    async def cleanup_stale_installations(session: AsyncSession, github_client) -> int:
        """Clean up installations that no longer exist on GitHub"""
        # Get all active installations
        stmt = select(OrganizationInstallation).options(
            selectinload(OrganizationInstallation.organization)
        ).where(OrganizationInstallation.status == "active")
        
        result = await session.execute(stmt)
        installations = result.scalars().all()
        
        cleaned_count = 0
        
        for installation in installations:
            try:
                # Check if installation still exists on GitHub
                exists = await github_client.verify_installation_exists(
                    installation.organization.login
                )
                
                if not exists:
                    # Mark as deleted
                    installation.status = "deleted"
                    installation.uninstalled_at = datetime.utcnow()
                    cleaned_count += 1
                    logger.info(f"Cleaned up stale installation: {installation.organization.login}")
                    
            except Exception as e:
                logger.warning(f"Failed to verify installation {installation.organization.login}: {e}")
        
        return cleaned_count

    @staticmethod
    async def get_stale_installations(session: AsyncSession) -> List[OrganizationInstallation]:
        """Get installations that haven't been verified recently"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        stmt = select(OrganizationInstallation).options(
            selectinload(OrganizationInstallation.organization)
        ).where(
            and_(
                OrganizationInstallation.status == "active",
                or_(
                    OrganizationInstallation.last_verified.is_(None),
                    OrganizationInstallation.last_verified < cutoff_time
                )
            )
        )
        
        result = await session.execute(stmt)
        return result.scalars().all()


class AuditLogRepository:
    """Audit logging for security and compliance"""
    
    @staticmethod
    async def log_action(
        session: AsyncSession,
        user_id: str,
        action: str,
        resource_type: str = None,
        resource_id: str = None,
        event_data: Dict = None,
        ip_address: str = None,
        user_agent: str = None,
        status: str = "success",
        error_message: str = None
    ) -> AuditLog:
        """Log user action for audit trail"""
        
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            event_data=event_data,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        
        session.add(log_entry)
        await session.flush()
        
        logger.info(f"Logged action: {action} by user: {user_id} - {status}")
        return log_entry
    
    @staticmethod
    async def get_user_audit_logs(
        session: AsyncSession,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Get audit logs for a user"""
        stmt = select(AuditLog).where(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        return result.scalars().all()


# PROJECT TREE OPERATIONS
async def get_project_tree(user_id: str, org_name: str) -> list:
    """Get project tree data for a user and organization"""
    try:
        async with db_manager.get_session() as session:
            # First get the organization
            org_stmt = select(Organization).where(Organization.login == org_name)
            org_result = await session.execute(org_stmt)
            # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate organizations
            organization = org_result.scalars().first()
            
            if not organization:
                logger.warning(f"Organization not found: {org_name}")
                return []
            
            # Get user
            user_stmt = select(User).where(User.auth_user_id == user_id)
            user_result = await session.execute(user_stmt)
            # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate users
            user = user_result.scalars().first()
            
            if not user:
                logger.warning(f"User not found: {user_id}")
                return []
            
            # Get project tree
            from .models import ProjectTree
            tree_stmt = select(ProjectTree).where(
                and_(
                    ProjectTree.organization_id == organization.id,
                    ProjectTree.user_id == user.id,
                    ProjectTree.is_active == True
                )
            ).order_by(ProjectTree.updated_at.desc())
            
            tree_result = await session.execute(tree_stmt)
            # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate tree entries
            project_tree = tree_result.scalars().first()
            
            if project_tree:
                return project_tree.tree_data or []
            else:
                return []
                
    except Exception as e:
        logger.error(f"Error getting project tree for {user_id}/{org_name}: {str(e)}")
        return []


async def save_project_tree(user_id: str, org_name: str, tree_data: list) -> bool:
    """Save project tree data for a user and organization"""
    try:
        async with db_manager.get_session() as session:
            # First get the organization
            org_stmt = select(Organization).where(Organization.login == org_name)
            org_result = await session.execute(org_stmt)
            # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate organizations
            organization = org_result.scalars().first()
            
            if not organization:
                logger.error(f"Organization not found: {org_name}")
                return False
            
            # Get user
            user_stmt = select(User).where(User.auth_user_id == user_id)
            user_result = await session.execute(user_stmt)
            # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate users
            user = user_result.scalars().first()
            
            if not user:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Check if project tree exists
            from .models import ProjectTree
            tree_stmt = select(ProjectTree).where(
                and_(
                    ProjectTree.organization_id == organization.id,
                    ProjectTree.user_id == user.id,
                    ProjectTree.is_active == True
                )
            )
            
            tree_result = await session.execute(tree_stmt)
            # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicate tree entries
            project_tree = tree_result.scalars().first()
            
            if project_tree:
                # Update existing
                project_tree.tree_data = tree_data
                project_tree.updated_at = datetime.utcnow()
                project_tree.version += 1
                logger.info(f"Updated project tree for {user_id}/{org_name}")
            else:
                # Create new
                project_tree = ProjectTree(
                    organization_id=organization.id,
                    user_id=user.id,
                    tree_data=tree_data
                )
                session.add(project_tree)
                logger.info(f"Created new project tree for {user_id}/{org_name}")
            
            await session.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error saving project tree for {user_id}/{org_name}: {str(e)}")
        return False


# Repository instances for easy access
user_repo = UserRepository()
github_token_repo = GitHubTokenRepository()
organization_repo = OrganizationRepository()
installation_repo = OrganizationInstallationRepository()
audit_repo = AuditLogRepository()
