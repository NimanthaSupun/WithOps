"""
Database models for Workspace Intelligence Service
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model for storing user information"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    auth_user_id = Column(String, unique=True, nullable=False, index=True)  # Auth0 user ID
    email = Column(String, nullable=False)
    name = Column(String)
    avatar_url = Column(String)
    github_username = Column(String)
    github_user_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)


class RepositoryTree(Base):
    """Repository tree structure for workspace visualization"""
    __tablename__ = "repository_trees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)  # Original column
    organization_name = Column(String, nullable=False, index=True)  # Added by migration
    user_id = Column(String, nullable=False, index=True)
    
    # Tree structure (JSON format) - stores folders and repositories
    tree_data = Column(JSON, nullable=False, default=list)
    
    # Metadata
    name = Column(String, default="Repository Structure")
    description = Column(String)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Workspace analysis metadata
    analysis_status = Column(String, default="pending")
    last_analyzed_at = Column(DateTime)
    maturity_score = Column(Float)
    analysis_metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkspaceAnalysis(Base):
    """Workspace analysis results and maturity scores"""
    __tablename__ = "workspace_analyses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    organization_name = Column(String, nullable=False, index=True)
    repository_tree_id = Column(String, ForeignKey("repository_trees.id"))
    
    # Analysis metadata
    analysis_type = Column(String, default="full_workspace")  # full_workspace, single_project
    project_id = Column(String)  # If single project analysis
    project_name = Column(String)
    
    # Analysis results
    analysis_data = Column(JSON, nullable=False)  # Complete analysis output
    maturity_score = Column(Float)
    maturity_level = Column(Integer)
    maturity_label = Column(String)
    
    # Summary metrics
    total_repositories = Column(Integer, default=0)
    total_workflows = Column(Integer, default=0)
    total_projects = Column(Integer, default=0)
    findings_count = Column(JSON)  # {critical: N, high: N, ...}
    
    # Detected practices
    detected_practices = Column(JSON)  # Aggregated security practices
    
    # Timestamps
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analysis_duration_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    status = Column(String, default="completed")  # pending, in_progress, completed, failed
    error_message = Column(Text)


class ProjectAnalysis(Base):
    """Individual project analysis (subset of workspace analysis)"""
    __tablename__ = "project_analyses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_tree_id = Column(String, nullable=False)
    project_id = Column(String, nullable=False)
    project_name = Column(String, nullable=False)
    organization_name = Column(String, nullable=False, index=True)
    user_id = Column(String, index=True)
    
    # Status
    status = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Maturity scores
    overall_maturity_score = Column(Float)
    maturity_level = Column(String)
    implementation_score = Column(Float)
    build_deployment_score = Column(Float)
    verification_score = Column(Float)
    information_gathering_score = Column(Float)
    
    # Metrics
    total_repositories = Column(Integer)
    repositories_analyzed = Column(Integer)
    total_workflows = Column(Integer)
    critical_findings = Column(Integer)
    high_findings = Column(Integer)
    medium_findings = Column(Integer)
    low_findings = Column(Integer)
    
    # Analysis configuration and detected practices
    analysis_config = Column(JSON)
    detected_practices = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
