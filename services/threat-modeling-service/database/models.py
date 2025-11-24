"""
Database models for Threat Modeling Service
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model for auth_user_id to UUID mapping"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    auth_user_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String)
    name = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class ThreatModel(Base):
    """Threat models for organizations/repositories"""
    __tablename__ = "threat_models"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)  # Foreign key reference (not enforced in microservice)
    repository_id = Column(String, nullable=True, index=True)  # Optional - can be org-wide
    user_id = Column(String, nullable=False, index=True)  # Creator
    
    # Model metadata
    name = Column(String, nullable=False)
    description = Column(Text)
    methodology = Column(String, default="STRIDE")  # STRIDE, LINDDUN, CIA, CUSTOM
    status = Column(String, default="draft")  # draft, review, approved, archived
    version = Column(Integer, default=1)
    
    # Canvas data (JSON format for D3.js/Konva.js)
    canvas_data = Column(JSON, default=dict)  # Stores nodes, edges, positions, etc.
    
    # Metadata for collaboration
    last_editor_id = Column(String)
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
    elements = relationship("ThreatModelElement", back_populates="threat_model", cascade="all, delete-orphan")
    assessments = relationship("ThreatAssessment", back_populates="threat_model", cascade="all, delete-orphan")
    collaborators = relationship("ThreatModelCollaborator", back_populates="threat_model", cascade="all, delete-orphan")
    versions = relationship("ThreatModelVersion", back_populates="threat_model", cascade="all, delete-orphan")
    analyses = relationship("AIAnalysisHistory", back_populates="threat_model", cascade="all, delete-orphan")


class ThreatModelElement(Base):
    """Individual elements in a threat model (processes, data stores, etc.)"""
    __tablename__ = "threat_model_elements"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False, index=True)
    
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
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False, index=True)
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
    ai_model_used = Column(String)  # groq, claude, ollama
    
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
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Permissions
    role = Column(String, default="viewer")  # owner, editor, reviewer, viewer
    can_edit = Column(Boolean, default=False)
    can_approve = Column(Boolean, default=False)
    can_comment = Column(Boolean, default=True)
    
    # Status
    invitation_status = Column(String, default="active")  # pending, active, declined
    invited_at = Column(DateTime, default=datetime.utcnow)
    invited_by = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    threat_model = relationship("ThreatModel", back_populates="collaborators")


class ThreatModelVersion(Base):
    """Version history for threat models"""
    __tablename__ = "threat_model_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False)
    
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
    approved_by = Column(String)
    approved_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    threat_model = relationship("ThreatModel", back_populates="versions")


class AIAnalysisHistory(Base):
    """Store all AI analysis results for threat models"""
    __tablename__ = "ai_analysis_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_model_id = Column(String, ForeignKey("threat_models.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False)  # User who requested the analysis
    
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
    threat_model = relationship("ThreatModel", back_populates="analyses")


class ThreatLibrary(Base):
    """Predefined threat library for different methodologies"""
    __tablename__ = "threat_library"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Threat details
    methodology = Column(String, nullable=False, index=True)  # STRIDE, LINDDUN, CIA, CUSTOM
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
    organization_id = Column(String)  # For custom threats
    created_by = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
