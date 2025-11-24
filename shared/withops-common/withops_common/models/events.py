"""
Event models for inter-service communication via message bus
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional


class BaseEvent(BaseModel):
    """Base event model for all events"""
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None  # For distributed tracing
    metadata: Optional[Dict[str, Any]] = None


class RepoSyncedEvent(BaseEvent):
    """Event published when a GitHub repository is synced"""
    event_type: str = "github.repo.synced"
    org_id: str
    repo_id: str
    repo_name: str
    workflow_count: int
    user_id: str


class AIAnalysisCompletedEvent(BaseEvent):
    """Event published when AI analysis completes"""
    event_type: str = "ai.analysis.completed"
    analysis_id: str
    analysis_type: str  # "pr_description", "threat_analysis", "workflow_scan"
    result: Dict[str, Any]
    user_id: str


class ThreatModelCreatedEvent(BaseEvent):
    """Event published when a threat model is created"""
    event_type: str = "threat.model.created"
    model_id: str
    model_name: str
    organization_id: str
    user_id: str


class SecurityScanCompletedEvent(BaseEvent):
    """Event published when security scan completes"""
    event_type: str = "security.scan.completed"
    scan_id: str
    org_id: str
    repo_id: Optional[str] = None
    vulnerability_count: int
    risk_score: float
    user_id: str
