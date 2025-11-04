"""
Database models for DevSecOps application using Supabase
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
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    auth_user_id = Column(String, unique=True, nullable=False, index=True)  # Auth0 user ID
    email = Column(String, nullable=False)
    name = Column(String)
    avatar_url = Column(String)
    github_username = Column(String)
    github_user_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    github_tokens = relationship("GitHubToken", back_populates="user", cascade="all, delete-orphan")
    organization_installations = relationship("OrganizationInstallation", back_populates="user", cascade="all, delete-orphan")


class GitHubToken(Base):
    """Store GitHub tokens for users"""
    __tablename__ = "github_tokens"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    access_token = Column(String, nullable=False)  # Should be encrypted in production
    token_type = Column(String, default="oauth")  # oauth, app_installation
    scope = Column(String)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # GitHub user info (snapshot)
    github_user_info = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="github_tokens")


class Organization(Base):
    """GitHub organizations"""
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_org_id = Column(Integer, unique=True, nullable=False, index=True)
    login = Column(String, unique=True, nullable=False, index=True)  # org name
    name = Column(String)
    description = Column(Text)
    avatar_url = Column(String)
    html_url = Column(String)
    type = Column(String)  # Organization, User
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Organization metadata from GitHub
    github_metadata = Column(JSON)
    
    # Relationships
    installations = relationship("OrganizationInstallation", back_populates="organization", cascade="all, delete-orphan")
    security_scans = relationship("SecurityScan", back_populates="organization", cascade="all, delete-orphan")
    security_metrics = relationship("SecurityMetric", back_populates="organization", cascade="all, delete-orphan")
    security_reports = relationship("SecurityReport", back_populates="organization", cascade="all, delete-orphan")


class OrganizationInstallation(Base):
    """Track GitHub App installations in organizations"""
    __tablename__ = "organization_installations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    github_installation_id = Column(Integer, unique=True, nullable=False, index=True)
    
    # Installation status
    status = Column(String, default="active")  # active, suspended, deleted
    installed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uninstalled_at = Column(DateTime)
    last_verified = Column(DateTime)  # Last time we verified installation exists on GitHub
    
    # Installation metadata from GitHub
    permissions = Column(JSON)
    events = Column(JSON)
    installation_metadata = Column(JSON)
    
    # App configuration
    repository_selection = Column(String)  # all, selected
    selected_repositories = Column(JSON)  # list of repo IDs if selected
    
    # Relationships
    user = relationship("User", back_populates="organization_installations")
    organization = relationship("Organization", back_populates="installations")
    repositories = relationship("Repository", back_populates="installation", cascade="all, delete-orphan")


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
    
    # Repository statistics
    stargazers_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0)
    forks_count = Column(Integer, default=0)
    size = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    github_created_at = Column(DateTime)
    github_updated_at = Column(DateTime)
    github_pushed_at = Column(DateTime)
    
    # Repository metadata from GitHub
    github_metadata = Column(JSON)
    
    # Relationships
    installation = relationship("OrganizationInstallation", back_populates="repositories")
    workflows = relationship("Workflow", back_populates="repository", cascade="all, delete-orphan")
    security_scans = relationship("SecurityScan", back_populates="repository", cascade="all, delete-orphan")
    security_metrics = relationship("SecurityMetric", back_populates="repository", cascade="all, delete-orphan")
    security_reports = relationship("SecurityReport", back_populates="repository", cascade="all, delete-orphan")


class Workflow(Base):
    """GitHub Actions workflows"""
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    github_workflow_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    state = Column(String)  # active, deleted, disabled_fork, disabled_inactivity, disabled_manually
    
    # Workflow content and metadata
    content = Column(Text)  # YAML content (cached)
    content_hash = Column(String)  # Hash to detect changes
    
    # URLs
    html_url = Column(String)
    badge_url = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    github_created_at = Column(DateTime)
    github_updated_at = Column(DateTime)
    
    # Workflow metadata from GitHub
    github_metadata = Column(JSON)
    
    # Relationships
    repository = relationship("Repository", back_populates="workflows")
    security_scans = relationship("SecurityScan", back_populates="workflow", cascade="all, delete-orphan")


class UserSession(Base):
    """Track user sessions and current organization context"""
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_token = Column(String, unique=True, nullable=False, index=True)
    current_organization_id = Column(String, ForeignKey("organizations.id"))
    
    # Session metadata
    ip_address = Column(String)
    user_agent = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User")
    current_organization = relationship("Organization")


class AuditLog(Base):
    """Audit trail for security and compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    action = Column(String, nullable=False)  # login, install_app, access_org, view_workflow, etc.
    resource_type = Column(String)  # organization, repository, workflow
    resource_id = Column(String)
    
    # Event details
    event_data = Column(JSON)
    ip_address = Column(String)
    user_agent = Column(String)
    status = Column(String)  # success, failed, denied
    error_message = Column(String)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


class ProjectTree(Base):
    """Project tree structure for organizations"""
    __tablename__ = "project_trees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)  # User who created/owns the tree
    
    # Tree structure (JSON format)
    tree_data = Column(JSON, nullable=False, default=list)
    
    # Metadata
    name = Column(String, default="Project Structure")
    description = Column(String)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")


class RepositoryTree(Base):
    """Repository tree structure for workspace analysis and DevSecOps intelligence"""
    __tablename__ = "repository_trees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)  # User who created/owns the tree
    
    # Tree structure (JSON format) - stores folders and repositories
    tree_data = Column(JSON, nullable=False, default=list)
    
    # Metadata
    name = Column(String, default="Repository Structure")
    description = Column(String)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Future workspace analysis metadata
    analysis_status = Column(String, default="pending")  # pending, analyzing, completed, failed
    last_analyzed_at = Column(DateTime)
    maturity_score = Column(Float)  # Overall DevSecOps maturity score (0-100)
    analysis_metadata = Column(JSON)  # Store analysis results, AI findings, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")


# =============================================================================
# 🛡️ THREAT MODELING MODELS
# =============================================================================

class ThreatModel(Base):
    """Threat models for organizations/repositories"""
    __tablename__ = "threat_models"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=True)  # Optional - can be org-wide
    user_id = Column(String, ForeignKey("users.id"), nullable=False)  # Creator
    
    # Model metadata
    name = Column(String, nullable=False)
    description = Column(Text)
    methodology = Column(String, default="STRIDE")  # STRIDE, LINDDUN, CIA, CUSTOM
    status = Column(String, default="draft")  # draft, review, approved, archived
    version = Column(Integer, default=1)
    
    # Canvas data (JSON format for D3.js/Konva.js)
    canvas_data = Column(JSON, default=dict)  # Stores nodes, edges, positions, etc.
    
    # Metadata for collaboration
    last_editor_id = Column(String, ForeignKey("users.id"))
    is_collaborative = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # Public within organization
    
    # AI analysis results
    ai_analysis = Column(JSON, default=dict)  # Store AI-generated suggestions
    last_ai_analysis = Column(DateTime)
    
    # Document analysis for enhanced AI context
    document_analysis = Column(JSON, default=dict)  # Processed document insights
    document_status = Column(String, default="none")  # none, uploading, processing, completed, failed
    document_file_name = Column(String)  # Original uploaded filename
    document_processed_at = Column(DateTime)  # When document was processed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    repository = relationship("Repository")
    creator = relationship("User", foreign_keys=[user_id])
    last_editor = relationship("User", foreign_keys=[last_editor_id])
    elements = relationship("ThreatModelElement", back_populates="threat_model", cascade="all, delete-orphan")
    assessments = relationship("ThreatAssessment", back_populates="threat_model", cascade="all, delete-orphan")
    collaborators = relationship("ThreatModelCollaborator", back_populates="threat_model", cascade="all, delete-orphan")
    versions = relationship("ThreatModelVersion", back_populates="threat_model", cascade="all, delete-orphan")


class ThreatModelElement(Base):
    """Individual elements in a threat model (processes, data stores, etc.)"""
    __tablename__ = "threat_model_elements"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False)
    
    # Element properties
    element_type = Column(String, nullable=False)  # process, datastore, external_entity, trust_boundary
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Canvas positioning
    x_position = Column(Integer, default=0)
    y_position = Column(Integer, default=0)
    width = Column(Integer, default=100)
    height = Column(Integer, default=60)
    
    # Element metadata
    properties = Column(JSON, default=dict)  # Custom properties (encryption, auth, etc.)
    style = Column(JSON, default=dict)  # Visual styling
    
    # AI analysis for this element
    identified_threats = Column(JSON, default=list)  # AI-identified threats
    risk_score = Column(Integer, default=0)  # 0-10 risk score
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    threat_model = relationship("ThreatModel", back_populates="elements")
    assessments = relationship("ThreatAssessment", back_populates="element")


class ThreatAssessment(Base):
    """STRIDE/LINDDUN assessments for model elements"""
    __tablename__ = "threat_assessments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False)
    element_id = Column(String, ForeignKey("threat_model_elements.id"), nullable=True)  # Can be model-wide
    
    # Threat details
    threat_category = Column(String, nullable=False)  # S, T, R, I, D, E for STRIDE
    threat_title = Column(String, nullable=False)
    threat_description = Column(Text)
    
    # Risk assessment
    impact_level = Column(String, default="medium")  # low, medium, high, critical
    likelihood = Column(String, default="medium")  # low, medium, high
    risk_level = Column(String, default="medium")  # Calculated from impact + likelihood
    
    # Mitigation
    mitigation_status = Column(String, default="identified")  # identified, planned, implemented, verified
    mitigation_description = Column(Text)
    mitigation_notes = Column(Text)
    
    # AI generated data
    ai_generated = Column(Boolean, default=False)
    ai_confidence = Column(Integer, default=0)  # 0-100 confidence score
    ai_model_used = Column(String)  # groq, huggingface, ollama
    
    # Assignment and tracking
    assigned_to = Column(String)  # User ID or team name
    due_date = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    threat_model = relationship("ThreatModel", back_populates="assessments")
    element = relationship("ThreatModelElement", back_populates="assessments")


class ThreatModelCollaborator(Base):
    """Users who can collaborate on a threat model"""
    __tablename__ = "threat_model_collaborators"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Permissions
    role = Column(String, default="viewer")  # owner, editor, reviewer, viewer
    can_edit = Column(Boolean, default=False)
    can_approve = Column(Boolean, default=False)
    can_comment = Column(Boolean, default=True)
    
    # Status
    invitation_status = Column(String, default="active")  # pending, active, declined
    invited_at = Column(DateTime, default=datetime.utcnow)
    invited_by = Column(String, ForeignKey("users.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    threat_model = relationship("ThreatModel", back_populates="collaborators")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])


class ThreatModelVersion(Base):
    """Version history for threat models"""
    __tablename__ = "threat_model_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Version metadata
    version_number = Column(Integer, nullable=False)
    version_name = Column(String)  # Optional custom name
    change_description = Column(Text)
    
    # Snapshot of model data
    canvas_data_snapshot = Column(JSON)
    elements_snapshot = Column(JSON)
    assessments_snapshot = Column(JSON)
    
    # Version status
    is_current = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    threat_model = relationship("ThreatModel", back_populates="versions")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])


class AIAnalysisHistory(Base):
    """Store all AI analysis results for threat models"""
    __tablename__ = "ai_analysis_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)  # User who requested the analysis
    
    # Analysis metadata
    analysis_type = Column(String, default="comprehensive")  # comprehensive, quick, focused
    methodology = Column(String, default="STRIDE")  # STRIDE, LINDDUN, CIA
    
    # Analysis results (full JSON data)
    analysis_data = Column(JSON, nullable=False)  # Complete analysis result
    structured_analysis = Column(JSON)  # Parsed structured data
    
    # Context at time of analysis
    diagram_elements_count = Column(Integer, default=0)
    diagram_connections_count = Column(Integer, default=0)
    had_document = Column(Boolean, default=False)
    had_diagram = Column(Boolean, default=False)
    
    # Status
    status = Column(String, default="completed")  # pending, processing, completed, failed
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    analysis_duration_ms = Column(Integer)  # How long the analysis took
    
    # Relationships
    threat_model = relationship("ThreatModel")
    user = relationship("User")


class ThreatLibrary(Base):
    """Predefined threat library for different methodologies"""
    __tablename__ = "threat_library"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Threat details
    methodology = Column(String, nullable=False)  # STRIDE, LINDDUN, CIA, CUSTOM
    category = Column(String, nullable=False)  # S, T, R, I, D, E for STRIDE
    threat_name = Column(String, nullable=False)
    threat_description = Column(Text)
    
    # Context
    applicable_elements = Column(JSON, default=list)  # Which element types this applies to
    example_scenarios = Column(JSON, default=list)
    
    # Default risk assessment
    default_impact = Column(String, default="medium")
    default_likelihood = Column(String, default="medium")
    
    # Mitigation guidance
    common_mitigations = Column(JSON, default=list)
    mitigation_examples = Column(JSON, default=list)
    
    # Metadata
    is_built_in = Column(Boolean, default=True)  # Built-in vs custom
    organization_id = Column(String, ForeignKey("organizations.id"))  # For custom threats
    created_by = Column(String, ForeignKey("users.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    creator = relationship("User")


# =============== SECURITY SCANNING MODELS ===============

class SecurityScan(Base):
    """Security scans performed on workflows and repositories"""
    __tablename__ = "security_scans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Scan target information
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    repository_id = Column(String, ForeignKey("repositories.id"))  # Optional for org-wide scans
    workflow_id = Column(String, ForeignKey("workflows.id"))  # Optional for repo-wide scans
    
    # Scan metadata
    scan_type = Column(String, nullable=False)  # workflow, repository, organization
    scan_initiator = Column(String, ForeignKey("users.id"), nullable=False)
    scan_id = Column(String, nullable=False, index=True)  # External scan ID from ML service
    
    # Scan results
    status = Column(String, nullable=False)  # running, completed, failed, error
    risk_score = Column(Float, default=0.0)  # 0-100 risk score
    risk_level = Column(String)  # minimal, low, medium, high
    vulnerability_count = Column(Integer, default=0)
    
    # ML model information
    models_used = Column(JSON, default=list)  # List of ML models used
    scanner_version = Column(String, default="1.0.0")
    scan_duration_seconds = Column(Float, default=0.0)
    
    # Detailed results
    scan_result_data = Column(JSON)  # Full scan result from ML service
    features_analyzed = Column(Integer, default=0)
    model_predictions = Column(JSON)  # Individual model predictions
    model_probabilities = Column(JSON)  # Model probability scores
    
    # Timestamps
    scan_started_at = Column(DateTime, default=datetime.utcnow)
    scan_completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    repository = relationship("Repository")
    workflow = relationship("Workflow")
    initiator = relationship("User")
    vulnerabilities = relationship("SecurityVulnerability", back_populates="scan", cascade="all, delete-orphan")


class SecurityVulnerability(Base):
    """Individual vulnerabilities found during security scans"""
    __tablename__ = "security_vulnerabilities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("security_scans.id"), nullable=False)
    
    # Vulnerability details
    vulnerability_type = Column(String, nullable=False)  # hardcoded_secrets, excessive_permissions, etc.
    severity = Column(String, nullable=False)  # low, medium, high, critical
    title = Column(String, nullable=False)
    description = Column(Text)
    message = Column(Text)  # Specific message for this instance
    
    # Location information
    file_path = Column(String)  # Workflow file path
    line_number = Column(Integer)  # Line number where vulnerability found
    pattern_matched = Column(String)  # Regex pattern that matched
    
    # Remediation guidance
    recommendation = Column(Text)
    fix_suggestion = Column(Text)
    external_references = Column(JSON, default=list)  # Links to security guides
    
    # Vulnerability status
    status = Column(String, default="open")  # open, acknowledged, fixed, false_positive
    acknowledged_by = Column(String, ForeignKey("users.id"))
    acknowledged_at = Column(DateTime)
    fixed_by = Column(String, ForeignKey("users.id"))
    fixed_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scan = relationship("SecurityScan", back_populates="vulnerabilities")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])
    fixer = relationship("User", foreign_keys=[fixed_by])


class SecurityMetric(Base):
    """Aggregated security metrics for tracking trends"""
    __tablename__ = "security_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Metric target
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    repository_id = Column(String, ForeignKey("repositories.id"))  # Optional for org-wide metrics
    metric_date = Column(DateTime, nullable=False, index=True)  # Date this metric represents
    
    # Security metrics
    total_workflows = Column(Integer, default=0)
    workflows_scanned = Column(Integer, default=0)
    average_risk_score = Column(Float, default=0.0)
    high_risk_workflows = Column(Integer, default=0)
    medium_risk_workflows = Column(Integer, default=0)
    low_risk_workflows = Column(Integer, default=0)
    minimal_risk_workflows = Column(Integer, default=0)
    
    # Vulnerability metrics
    total_vulnerabilities = Column(Integer, default=0)
    new_vulnerabilities = Column(Integer, default=0)
    fixed_vulnerabilities = Column(Integer, default=0)
    open_vulnerabilities = Column(Integer, default=0)
    critical_vulnerabilities = Column(Integer, default=0)
    high_vulnerabilities = Column(Integer, default=0)
    medium_vulnerabilities = Column(Integer, default=0)
    low_vulnerabilities = Column(Integer, default=0)
    
    # Coverage metrics
    scan_coverage_percentage = Column(Float, default=0.0)  # % of workflows scanned
    repository_coverage_percentage = Column(Float, default=0.0)  # % of repos scanned
    
    # Trend information
    risk_trend = Column(String)  # improving, stable, degrading
    vulnerability_trend = Column(String)  # improving, stable, degrading
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    repository = relationship("Repository")


class SecurityReport(Base):
    """Generated security reports for organizations and repositories"""
    __tablename__ = "security_reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Report metadata
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    repository_id = Column(String, ForeignKey("repositories.id"))  # Optional for org-wide reports
    report_type = Column(String, nullable=False)  # daily, weekly, monthly, on_demand
    generated_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Report content
    title = Column(String, nullable=False)
    summary = Column(Text)
    report_data = Column(JSON)  # Structured report content
    recommendations = Column(JSON, default=list)  # List of recommendations
    
    # Report statistics
    total_scans = Column(Integer, default=0)
    total_vulnerabilities = Column(Integer, default=0)
    average_risk_score = Column(Float, default=0.0)
    highest_risk_workflow = Column(String)
    
    # Report period
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    
    # Report status
    status = Column(String, default="generated")  # generated, sent, archived
    sent_to = Column(JSON, default=list)  # List of email addresses report was sent to
    sent_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    repository = relationship("Repository")
    generator = relationship("User")


# ============================================================================
# WORKSPACE INTELLIGENCE & DEVSECOPS MATURITY MODELS
# ============================================================================

class ProjectAnalysis(Base):
    """Analysis results for a project (folder) in the repository tree"""
    __tablename__ = "project_analyses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_tree_id = Column(String, ForeignKey("repository_trees.id"), nullable=False)
    project_id = Column(String, nullable=False)  # ID of the project/folder in tree_data
    project_name = Column(String, nullable=False)
    organization_name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Optional - allows analysis without user
    
    # Analysis status
    status = Column(String, default="pending")  # pending, analyzing, completed, failed, stale
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Overall scores
    overall_maturity_score = Column(Float)  # 0-100
    maturity_level = Column(String)  # Level 0-4 based on OWASP DSOMM
    
    # Dimension scores (OWASP DSOMM dimensions)
    implementation_score = Column(Float)
    build_deployment_score = Column(Float)
    verification_score = Column(Float)
    information_gathering_score = Column(Float)
    
    # Statistics
    total_repositories = Column(Integer, default=0)
    repositories_analyzed = Column(Integer, default=0)
    total_workflows = Column(Integer, default=0)
    
    # Summary findings
    critical_findings = Column(Integer, default=0)
    high_findings = Column(Integer, default=0)
    medium_findings = Column(Integer, default=0)
    low_findings = Column(Integer, default=0)
    
    # Detected security practices (aggregated from all repos)
    detected_practices = Column(JSON)  # Stores tools, policies, workflows info
    
    # Analysis metadata
    analysis_config = Column(JSON)  # Configuration used for analysis
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    repository_tree = relationship("RepositoryTree")
    user = relationship("User")
    repository_findings = relationship("RepositoryFinding", back_populates="project_analysis", cascade="all, delete-orphan")
    maturity_scores = relationship("MaturityScore", back_populates="project_analysis", cascade="all, delete-orphan")


class RepositoryFinding(Base):
    """Individual security/DevSecOps findings for repositories"""
    __tablename__ = "repository_findings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String, ForeignKey("project_analyses.id"), nullable=False)
    
    # Repository information
    repository_name = Column(String, nullable=False)
    repository_full_name = Column(String)
    repository_url = Column(String)
    
    # Finding details
    finding_type = Column(String, nullable=False)  # missing_sast, missing_dast, no_branch_protection, etc.
    category = Column(String)  # tools, policies, architecture, configuration
    severity = Column(String)  # critical, high, medium, low, info
    title = Column(String, nullable=False)
    description = Column(Text)
    
    # Detection details
    detected_by = Column(String)  # rule_name or detector that found this
    confidence = Column(Float)  # 0-1 confidence score
    
    # Remediation
    recommendation = Column(Text)
    remediation_effort = Column(String)  # low, medium, high
    priority = Column(Integer)  # 1-5, higher is more important
    
    # Status tracking
    status = Column(String, default="open")  # open, acknowledged, false_positive, resolved, ignored
    acknowledged_by = Column(String, ForeignKey("users.id"))
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    # Additional context
    finding_metadata = Column(JSON)  # Store additional context, affected files, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project_analysis = relationship("ProjectAnalysis", back_populates="repository_findings")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])


class MaturityScore(Base):
    """Detailed maturity scores by dimension and category"""
    __tablename__ = "maturity_scores"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String, ForeignKey("project_analyses.id"), nullable=False)
    
    # Dimension info (based on OWASP DSOMM)
    dimension = Column(String, nullable=False)  # Implementation, Build&Deployment, Verification, Information
    sub_dimension = Column(String)  # e.g., "Static Analysis", "Dynamic Analysis", etc.
    
    # Scoring
    score = Column(Float, nullable=False)  # 0-100
    max_score = Column(Float, default=100)
    level = Column(Integer)  # 0-4 maturity level
    
    # Details
    practices_found = Column(JSON)  # List of practices detected
    practices_missing = Column(JSON)  # List of missing practices
    recommendations = Column(JSON)  # List of recommendations to improve
    
    # Weights and calculations
    weight = Column(Float, default=1.0)  # Weight in overall score calculation
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project_analysis = relationship("ProjectAnalysis", back_populates="maturity_scores")


class WorkflowEmbedding(Base):
    """Vector embeddings of workflow files for RAG queries"""
    __tablename__ = "workflow_embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Repository and workflow info
    organization_name = Column(String, nullable=False, index=True)
    repository_name = Column(String, nullable=False, index=True)
    workflow_path = Column(String, nullable=False)
    workflow_name = Column(String)
    
    # Content
    content = Column(Text, nullable=False)  # Original YAML content
    content_hash = Column(String, index=True)  # Hash to detect changes
    
    # Embedding (stored as JSON array, will use pgvector in production)
    embedding = Column(JSON)  # Vector embedding from Ollama
    embedding_model = Column(String)  # Model used for embedding
    
    # Extracted metadata
    detected_tools = Column(JSON)  # List of security tools detected
    triggers = Column(JSON)  # Workflow triggers
    jobs_summary = Column(JSON)  # Summary of jobs
    security_practices = Column(JSON)  # Detected security practices
    
    # Analysis context
    chunk_index = Column(Integer, default=0)  # For chunked content
    total_chunks = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_embedded_at = Column(DateTime)


class QueryHistory(Base):
    """History of RAG queries for workspace intelligence"""
    __tablename__ = "query_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    organization_name = Column(String, nullable=False)
    
    # Query details
    query_text = Column(Text, nullable=False)
    query_type = Column(String)  # security_check, tool_detection, compliance, general
    scope = Column(String)  # all_projects, specific_project, repository
    scope_id = Column(String)  # ID of project or repository if scoped
    
    # Response
    response_text = Column(Text)
    response_sources = Column(JSON)  # List of sources used in response
    context_used = Column(JSON)  # Embedding chunks retrieved
    
    # Performance metrics
    processing_time_ms = Column(Integer)
    embeddings_retrieved = Column(Integer)
    tokens_used = Column(Integer)
    
    # Feedback
    user_rating = Column(Integer)  # 1-5 stars
    user_feedback = Column(Text)
    was_helpful = Column(Boolean)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
