"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class ThreatModelCreate(BaseModel):
    name: str
    description: str
    methodology: str = "STRIDE"
    repository_id: Optional[str] = None
    organization_id: str
    metadata: Optional[Dict] = None
    canvas_data: Optional[Dict] = None


class ThreatModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    canvas_data: Optional[Dict] = None
    ai_analysis: Optional[Dict] = None
    last_ai_analysis: Optional[str] = None


class ThreatModelResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    methodology: str
    status: str
    canvas_data: Optional[Dict]
    organization_id: str
    repository_id: Optional[str]
    user_id: str
    created_at: str
    updated_at: Optional[str]
    document_status: Optional[str] = None
    document_file_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ComprehensiveAnalysisRequest(BaseModel):
    canvas_data: Dict
    model_metadata: Dict
    document_context: Optional[Dict] = None


class AnalysisSaveRequest(BaseModel):
    analysis_data: Dict


class ThreatElementCreate(BaseModel):
    element_type: str  # "process", "datastore", "dataflow", "external_entity"
    name: str
    description: Optional[str] = None
    position: Dict  # Canvas position
    properties: Optional[Dict] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    database: Optional[str] = None
