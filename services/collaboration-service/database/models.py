"""
Database models for Collaboration Service
"""
from sqlalchemy import Column, String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model - references existing users table"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    auth_user_id = Column(String, unique=True, nullable=False)  # Auth0 user ID
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    avatar_url = Column(String)
    github_username = Column(String)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Organization(Base):
    """Organization model - references existing organizations table"""
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    login = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    avatar_url = Column(String)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrganizationInstallation(Base):
    """Organization installation model - references existing table"""
    __tablename__ = "organization_installations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    installation_id = Column(Integer, unique=True, nullable=False)
    status = Column(String, default="active")  # active, suspended, deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CollaborationSession(Base):
    """Collaboration session for real-time collaboration"""
    __tablename__ = "collaboration_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, unique=True, nullable=False, index=True)
    model_id = Column(String, nullable=False)  # Threat model ID
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Session metadata
    status = Column(String, default="active")  # active, ended, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Session data
    participants = Column(JSON, default=list)  # List of user IDs
    session_metadata = Column(JSON)  # Renamed from 'metadata' to avoid SQLAlchemy conflict


class CollaborationInvite(Base):
    """Collaboration invitation"""
    __tablename__ = "collaboration_invites"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("collaboration_sessions.id"), nullable=False)
    invited_by = Column(String, ForeignKey("users.id"), nullable=False)
    invited_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Invitation details
    message = Column(String)
    status = Column(String, default="pending")  # pending, accepted, declined, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    responded_at = Column(DateTime)
