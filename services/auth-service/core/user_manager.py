"""
User management utilities for Auth Service
Handles user creation, updates, and profile management
"""

import logging
import re
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User

logger = logging.getLogger(__name__)


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_email(email: str) -> Optional[str]:
    """
    Sanitize and fix common email issues
    
    Args:
        email: Email address to sanitize
        
    Returns:
        Sanitized email or None if invalid
    """
    if not email:
        return None
    
    # Remove whitespace and convert to lowercase
    email = email.strip().lower()
    
    # Fix common typos
    email = email.replace('gamil.com', 'gmail.com')
    email = email.replace('gmial.com', 'gmail.com')
    email = email.replace('yahooo.com', 'yahoo.com')
    email = email.replace('hotmial.com', 'hotmail.com')
    
    # Fix missing @ symbol
    if '@' not in email and '.' in email:
        parts = email.split('.')
        if len(parts) >= 2:
            domain_part = '.'.join(parts[-2:])
            if domain_part in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                username = '.'.join(parts[:-2]) if len(parts) > 2 else parts[0]
                email = f"{username}@{domain_part}"
    
    return email if validate_email(email) else None


async def get_or_create_user(
    session: AsyncSession,
    auth_user_id: str,
    user_info: dict
) -> User:
    """
    Get existing user or create new one from Auth0 user info
    
    Args:
        session: Database session
        auth_user_id: Auth0 user ID (sub claim)
        user_info: User info from Auth0 token
        
    Returns:
        User object
    """
    # Try to get existing user
    query = select(User).where(User.auth_user_id == auth_user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Upgrade placeholder email if we have a real one
        if user.email.endswith('@placeholder.local'):
            email = user_info.get('email')
            if email:
                email = sanitize_email(email)
                if email:
                    user.email = email
                    logger.info(f"Upgraded placeholder email for user {auth_user_id}")
        
        await session.commit()
        await session.refresh(user)
        
        # Publish user login event
        try:
            from core.event_bus import event_bus
            await event_bus.publish_user_login(
                user_id=user.id,
                auth_user_id=user.auth_user_id,
                email=user.email
            )
        except Exception as e:
            logger.error(f"Failed to publish user login event: {e}")
        
        return user
    
    # Create new user
    email = user_info.get('email')
    
    # Sanitize and validate email
    if email:
        email = sanitize_email(email)
        if not email:
            logger.warning(f"Invalid email in token for user {auth_user_id}: {user_info.get('email')}")
    
    # Generate placeholder email if needed
    if not email:
        user_id_part = auth_user_id.split('|')[-1]
        email = f"user-{user_id_part}@placeholder.local"
        logger.warning(f"Using placeholder email for user {auth_user_id}: {email}")
    else:
        logger.info(f"Creating user {auth_user_id} with email: {email}")
    
    # Create user
    user = User(
        auth_user_id=auth_user_id,
        email=email,
        name=user_info.get('name') or 'Unknown User',
        avatar_url=user_info.get('picture'),
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"Created new user: {auth_user_id}")
    
    # Publish user created event
    try:
        from core.event_bus import event_bus
        await event_bus.publish_user_created(
            user_id=user.id,
            auth_user_id=user.auth_user_id,
            email=user.email,
            name=user.name
        )
    except Exception as e:
        logger.error(f"Failed to publish user created event: {e}")
    
    return user


async def get_user_by_auth_id(
    session: AsyncSession,
    auth_user_id: str
) -> Optional[User]:
    """
    Get user by Auth0 ID
    
    Args:
        session: Database session
        auth_user_id: Auth0 user ID
        
    Returns:
        User object or None
    """
    query = select(User).where(User.auth_user_id == auth_user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def update_user_profile(
    session: AsyncSession,
    auth_user_id: str,
    **updates
) -> Optional[User]:
    """
    Update user profile
    
    Args:
        session: Database session
        auth_user_id: Auth0 user ID
        **updates: Fields to update
        
    Returns:
        Updated user or None if not found
    """
    user = await get_user_by_auth_id(session, auth_user_id)
    
    if not user:
        return None
    
    # Update allowed fields
    allowed_fields = ['name', 'email', 'avatar_url']
    updated_fields = {}
    
    for field, value in updates.items():
        if field in allowed_fields and value is not None:
            setattr(user, field, value)
            updated_fields[field] = value
    
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"Updated user profile: {auth_user_id}")
    
    # Publish user updated event if any fields were updated
    if updated_fields:
        try:
            from core.event_bus import event_bus
            await event_bus.publish_user_updated(
                user_id=user.id,
                auth_user_id=user.auth_user_id,
                updated_fields=updated_fields
            )
        except Exception as e:
            logger.error(f"Failed to publish user updated event: {e}")
    
    return user
