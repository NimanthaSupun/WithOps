"""
Organization models shared across services
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrganizationBase(BaseModel):
    """Base organization model"""
    github_org_id: int
    login: str
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    """Organization response model"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
