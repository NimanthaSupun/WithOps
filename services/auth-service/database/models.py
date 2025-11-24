"""
Database models for Auth Service
Minimal models needed for user authentication and management
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auth_user_id = Column(String(255), unique=True, nullable=False, index=True)  # Auth0 ID
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    avatar_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    organization_installations = relationship("OrganizationInstallation", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, auth_user_id={self.auth_user_id})>"


class Organization(Base):
    """GitHub organizations"""
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_org_id = Column(Integer, unique=True, nullable=False, index=True)
    login = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    description = Column(Text)
    avatar_url = Column(String)
    html_url = Column(String)
    type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    github_metadata = Column(JSON)
    
    # Relationships
    installations = relationship("OrganizationInstallation", back_populates="organization")


class OrganizationInstallation(Base):
    """Track GitHub App installations in organizations"""
    __tablename__ = "organization_installations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    github_installation_id = Column(Integer, unique=True, nullable=False, index=True)
    status = Column(String, default="active")
    installed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uninstalled_at = Column(DateTime)
    last_verified = Column(DateTime)
    permissions = Column(JSON)
    events = Column(JSON)
    installation_metadata = Column(JSON)
    repository_selection = Column(String)
    selected_repositories = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="organization_installations")
    organization = relationship("Organization", back_populates="installations")
    repositories = relationship("Repository", back_populates="installation")


class Repository(Base):
    """Repositories within installations"""
    __tablename__ = "repositories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    installation_id = Column(String, ForeignKey("organization_installations.id"), nullable=False)
    github_repo_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    description = Column(Text)
    private = Column(Boolean, default=False)
    html_url = Column(String)
    clone_url = Column(String)
    default_branch = Column(String)
    language = Column(String)
    stargazers_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0)
    forks_count = Column(Integer, default=0)
    size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    github_created_at = Column(DateTime)
    github_updated_at = Column(DateTime)
    github_pushed_at = Column(DateTime)
    github_metadata = Column(JSON)
    
    # Relationships
    installation = relationship("OrganizationInstallation", back_populates="repositories")
    workflows = relationship("Workflow", back_populates="repository")


class Workflow(Base):
    """GitHub Actions workflows"""
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    github_workflow_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    state = Column(String)
    content = Column(Text)
    content_hash = Column(String)
    html_url = Column(String)
    badge_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    github_created_at = Column(DateTime)
    github_updated_at = Column(DateTime)
    github_metadata = Column(JSON)
    
    # Relationships
    repository = relationship("Repository", back_populates="workflows")
