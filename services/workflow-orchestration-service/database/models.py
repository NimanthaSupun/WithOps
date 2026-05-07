"""
Database models for Workflow Orchestration Service
Handles workflow trees, executions, security scans, and canvas designs
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()


class ProjectTree(Base):
    """Map to existing project_trees table in main schema"""
    __tablename__ = "project_trees"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False, index=True)
    
    # Tree structure stored as JSON
    tree_data = Column(JSON, nullable=False, default=list)
    
    # Metadata
    name = Column(String, default="Project Structure")
    description = Column(String)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowTreeType(str, enum.Enum):
    """Types of tree nodes"""
    FOLDER = "folder"
    WORKFLOW = "workflow"
    FILE = "file"


class ExecutionStatus(str, enum.Enum):
    """Workflow execution statuses"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ScanRiskLevel(str, enum.Enum):
    """Security scan risk levels"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowTree(Base):
    """User-customized workflow tree organization"""
    __tablename__ = "workflow_trees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    org_name = Column(String, nullable=False, index=True)
    
    # Tree structure stored as JSON
    tree_data = Column(JSON, nullable=False)
    
    # Metadata
    node_count = Column(Integer, default=0)
    workflow_count = Column(Integer, default=0)
    folder_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Version control
    version = Column(Integer, default=1)
    
    # Unique constraint
    __table_args__ = (
        {'schema': 'workflow_orchestration'},
    )


class WorkflowExecution(Base):
    """Workflow execution history with detailed steps"""
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, nullable=False, index=True)
    execution_number = Column(Integer, nullable=False)
    
    # Organization and repository info
    org_name = Column(String, nullable=False, index=True)
    repo_name = Column(String, nullable=False)
    workflow_name = Column(String, nullable=False)
    workflow_path = Column(String, nullable=False)
    
    # Execution details
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, index=True)
    triggered_by = Column(String, nullable=False)  # user_id
    trigger_type = Column(String, default="manual")  # manual, webhook, scheduled
    
    # Parameters and inputs
    parameters = Column(JSON)  # Build parameters
    inputs = Column(JSON)  # Workflow inputs
    
    # Execution timeline
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration = Column(Integer)  # Duration in seconds
    
    # Detailed execution data
    steps = Column(JSON)  # Step-by-step execution details
    jobs = Column(JSON)  # GitHub Actions jobs data
    logs_url = Column(String)  # URL to full logs
    artifacts_url = Column(String)  # URL to artifacts
    
    # GitHub Actions specific
    github_run_id = Column(String, index=True)  # GitHub Actions run ID
    github_run_number = Column(Integer)
    github_run_url = Column(String)
    
    # Results
    conclusion = Column(String)  # success, failure, cancelled, etc.
    exit_code = Column(Integer)
    error_message = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        {'schema': 'workflow_orchestration'},
    )


class WorkflowSecurityScan(Base):
    """Security scan results for workflows"""
    __tablename__ = "workflow_security_scans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_type = Column(String, nullable=False, index=True)  # workflow, repository, organization
    
    # Target identification
    org_name = Column(String, nullable=False, index=True)
    repo_name = Column(String)
    workflow_id = Column(String)
    workflow_name = Column(String)
    workflow_path = Column(String)
    
    # Scan results
    risk_level = Column(Enum(ScanRiskLevel), index=True)
    risk_score = Column(Float)  # 0-100
    
    # Detailed findings
    findings = Column(JSON, nullable=False)  # Array of security issues
    recommendations = Column(JSON)  # Array of recommendations
    
    # Finding categories
    secrets_found = Column(Integer, default=0)
    unsafe_actions = Column(Integer, default=0)
    permission_issues = Column(Integer, default=0)
    script_injection_risks = Column(Integer, default=0)
    
    # Scan metadata
    scanned_by = Column(String, nullable=False)  # user_id
    scan_duration = Column(Integer)  # Duration in seconds
    scanner_version = Column(String)
    
    # Timestamps
    scanned_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        {'schema': 'workflow_orchestration'},
    )


class WorkflowCanvasDesign(Base):
    """Visual workflow editor canvas designs"""
    __tablename__ = "workflow_canvas_designs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, nullable=False, index=True)
    
    # Organization info
    org_name = Column(String, nullable=False, index=True)
    repo_name = Column(String)
    
    # Canvas design data
    design_data = Column(JSON, nullable=False)  # Nodes, positions, connections
    relationships = Column(JSON)  # Workflow dependencies graph
    
    # Canvas metadata
    canvas_width = Column(Integer)
    canvas_height = Column(Integer)
    zoom_level = Column(Float, default=1.0)
    
    # Version control
    version = Column(Integer, default=1)
    
    # User info
    created_by = Column(String, nullable=False)
    updated_by = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    saved_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        {'schema': 'workflow_orchestration'},
    )


class WorkflowMetric(Base):
    """Analytics and performance metrics for workflows"""
    __tablename__ = "workflow_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, nullable=False, unique=True, index=True)
    
    # Organization and repository info
    org_name = Column(String, nullable=False, index=True)
    repo_name = Column(String, nullable=False)
    workflow_name = Column(String, nullable=False)
    
    # Execution metrics
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    cancelled_runs = Column(Integer, default=0)
    
    # Performance metrics
    avg_duration = Column(Integer)  # Average duration in seconds
    min_duration = Column(Integer)
    max_duration = Column(Integer)
    
    # Success rate
    success_rate = Column(Float)  # Percentage
    
    # Recent activity
    last_run_at = Column(DateTime)
    last_success_at = Column(DateTime)
    last_failure_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        {'schema': 'workflow_orchestration'},
    )
