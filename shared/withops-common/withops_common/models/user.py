"""
User models shared across services
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user model"""
    auth_user_id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    github_username: Optional[str] = None


class UserResponse(UserBase):
    """User response model with additional fields"""
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True
