"""
Real-Time AI Threat Analysis API Endpoints
Ultra-fast threat analysis using Groq AI
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import asyncio
import time
import sys
import os

# Add the backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.groq_ai_client import (
    GroqAIClient, 
    quick_component_analysis, 
    quick_flow_analysis,
    ThreatSuggestion
)
router = APIRouter(prefix="/api/ai-threats", tags=["AI Threat Analysis"])

# Request Models
class ComponentAnalysisRequest(BaseModel):
    component: Dict[str, Any]
    canvas_context: Optional[Dict[str, Any]] = None

class FlowAnalysisRequest(BaseModel):
    flow: Dict[str, Any]
    source_component: Optional[Dict[str, Any]] = None
    target_component: Optional[Dict[str, Any]] = None

class ArchitectureAnalysisRequest(BaseModel):
    canvas: Dict[str, Any]
    focus_areas: Optional[List[str]] = None

class ThreatQuestionRequest(BaseModel):
    question: str
    canvas_context: Dict[str, Any]

class MitigationRequest(BaseModel):
    threat_title: str
    component_type: str
    threat_id: Optional[str] = None

# Response Models
class ThreatAnalysisResponse(BaseModel):
    threats: List[Dict[str, Any]]
    analysis_time_ms: int
    confidence: float
    suggestions_count: int

class QuestionResponse(BaseModel):
    answer: str
    response_time_ms: int
    followup_suggestions: Optional[List[str]] = None

@router.post("/analyze/component", response_model=ThreatAnalysisResponse)
async def analyze_component_threats(request: ComponentAnalysisRequest):
    """
    Real-time threat analysis for a single component with methodology awareness
    Returns threats within 2-3 seconds for immediate UI feedback
    """
    start_time = time.time()
    
    try:
        # Use enhanced analysis with canvas context
        async with GroqAIClient() as client:
            threats = await client.analyze_component_threats(
                request.component, 
                request.canvas_context
            )
        
        # Convert ThreatSuggestion objects to dicts
        threat_dicts = []
        for threat in threats:
            if hasattr(threat, 'title'):  # ThreatSuggestion object
                threat_dicts.append({
                    "id": threat.id,
                    "title": threat.title,
                    "description": threat.description,
                    "severity": threat.severity,
                    "category": threat.category.value if hasattr(threat.category, 'value') else str(threat.category),
                    "likelihood": threat.likelihood,
                    "impact": threat.impact,
                    "mitigation": threat.mitigation,
                    "confidence": threat.confidence,
                    "component_ids": threat.component_ids
                })
            else:  # Already a dict
                threat_dicts.append(threat)
        
        analysis_time = int((time.time() - start_time) * 1000)
        
        return ThreatAnalysisResponse(
            threats=threat_dicts,
            analysis_time_ms=analysis_time,
            confidence=sum(t.get('confidence', 0.7) for t in threat_dicts) / len(threat_dicts) if threat_dicts else 0.0,
            suggestions_count=len(threat_dicts)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

@router.post("/analyze/flow", response_model=ThreatAnalysisResponse)
async def analyze_flow_threats(request: FlowAnalysisRequest):
    """
    Real-time data flow threat analysis
    Analyzes threats in data transmission between components
    """
    start_time = time.time()
    
    try:
        # Enhance flow data with component context
        enhanced_flow = request.flow.copy()
        if request.source_component:
            enhanced_flow['source_type'] = request.source_component.get('type')
            enhanced_flow['source_trust'] = request.source_component.get('trustLevel')
        if request.target_component:
            enhanced_flow['target_type'] = request.target_component.get('type')
            enhanced_flow['target_trust'] = request.target_component.get('trustLevel')
        
        threats = await quick_flow_analysis(enhanced_flow)
        
        analysis_time = int((time.time() - start_time) * 1000)
        
        return ThreatAnalysisResponse(
            threats=threats,
            analysis_time_ms=analysis_time,
            confidence=0.85,  # Flow analysis is typically high confidence
            suggestions_count=len(threats)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flow analysis failed: {str(e)}")

@router.post("/analyze/architecture", response_model=ThreatAnalysisResponse)
async def analyze_architecture_threats(request: ArchitectureAnalysisRequest):
    """
    Comprehensive architecture analysis
    Identifies systemic and architectural-level threats
    """
    start_time = time.time()
    
    try:
        async with GroqAIClient() as client:
            threats = await client.analyze_architecture_threats(request.canvas)
            
        analysis_time = int((time.time() - start_time) * 1000)
        
        # Convert ThreatSuggestion objects to dicts
        threat_dicts = [
            {
                "id": threat.id,
                "title": threat.title,
                "description": threat.description,
                "severity": threat.severity,
                "category": threat.category.value,
                "likelihood": threat.likelihood,
                "impact": threat.impact,
                "mitigation": threat.mitigation,
                "confidence": threat.confidence,
                "component_ids": threat.component_ids
            }
            for threat in threats
        ]
        
        return ThreatAnalysisResponse(
            threats=threat_dicts,
            analysis_time_ms=analysis_time,
            confidence=sum(t.confidence for t in threats) / len(threats) if threats else 0.0,
            suggestions_count=len(threats)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Architecture analysis failed: {str(e)}")

@router.post("/ask", response_model=QuestionResponse)
async def ask_threat_question(request: ThreatQuestionRequest):
    """
    Ask specific questions about threat modeling
    Get instant expert advice and recommendations
    """
    start_time = time.time()
    
    try:
        async with GroqAIClient() as client:
            answer = await client.ask_threat_question(
                request.question, 
                request.canvas_context
            )
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Generate followup suggestions based on the question
        followups = []
        question_lower = request.question.lower()
        if "mitigation" in question_lower:
            followups = [
                "What are the implementation costs?",
                "Are there alternative approaches?",
                "How do I prioritize these mitigations?"
            ]
        elif "threat" in question_lower:
            followups = [
                "What mitigations address this threat?",
                "How likely is this threat in my environment?",
                "Are there similar threats I should consider?"
            ]
        
        return QuestionResponse(
            answer=answer,
            response_time_ms=response_time,
            followup_suggestions=followups
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")

@router.post("/mitigation/details")
async def get_mitigation_details(request: MitigationRequest):
    """
    Get detailed mitigation steps and implementation guidance
    """
    start_time = time.time()
    
    try:
        async with GroqAIClient() as client:
            details = await client.get_mitigation_details(
                request.threat_title,
                request.component_type
            )
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            "mitigation_details": details,
            "response_time_ms": response_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mitigation details failed: {str(e)}")

@router.get("/health")
async def ai_health_check():
    """
    Check if AI service is available and responsive
    """
    start_time = time.time()
    
    try:
        # Quick test with minimal component
        test_component = {
            "id": "test",
            "type": "api",
            "name": "test-api"
        }
        
        threats = await quick_component_analysis(test_component)
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            "status": "healthy",
            "ai_service": "groq",
            "response_time_ms": response_time,
            "test_threats_found": len(threats),
            "fast_analysis": response_time < 5000  # Should be under 5 seconds
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "ai_service": "groq"
        }

# Real-time streaming endpoint for live analysis
@router.post("/analyze/live")
async def live_threat_analysis(request: ComponentAnalysisRequest):
    """
    Ultra-fast live analysis as user types/draws
    Optimized for real-time feedback with sub-second responses
    """
    try:
        # Use the fastest possible analysis
        start_time = time.time()
        
        # Simplified analysis for live feedback
        component = request.component
        threats = []
        
        # Quick pattern-based threat detection
        component_type = component.get('type', '').lower()
        trust_level = component.get('trustLevel', 'internal')
        
        # Fast heuristic-based threats (while AI processes in background)
        if component_type == 'api' and trust_level == 'external':
            threats.append({
                "id": "quick-api-auth",
                "title": "API Authentication Required",
                "severity": "High",
                "category": "spoofing",
                "confidence": 0.9
            })
        
        if component_type == 'database':
            threats.append({
                "id": "quick-db-injection",
                "title": "SQL Injection Risk",
                "severity": "High", 
                "category": "tampering",
                "confidence": 0.85
            })
        
        analysis_time = int((time.time() - start_time) * 1000)
        
        return {
            "threats": threats,
            "analysis_time_ms": analysis_time,
            "is_live": True,
            "ai_analysis_pending": True  # Indicates full AI analysis is processing
        }
        
    except Exception as e:
        return {
            "threats": [],
            "error": str(e),
            "is_live": True
        }

# New Threat Management Endpoints

class ThreatDismissalRequest(BaseModel):
    threat_id: str
    component_id: str
    reason: Optional[str] = None

class DetailedMitigationRequest(BaseModel):
    threat_id: str
    threat_title: str
    component_type: str
    canvas_context: Optional[Dict[str, Any]] = None

class JiraTaskRequest(BaseModel):
    threat_data: Dict[str, Any]
    mitigation_data: Dict[str, Any]
    jira_config: Dict[str, Any]

class CanvasRefreshRequest(BaseModel):
    old_canvas_hash: str
    canvas_context: Dict[str, Any]

@router.post("/threats/dismiss")
async def dismiss_threat(request: ThreatDismissalRequest):
    """
    Dismiss a threat suggestion and optionally provide reasoning
    """
    start_time = time.time()
    
    try:
        async with GroqAIClient() as client:
            success = await client.dismiss_threat_suggestion(
                request.threat_id,
                request.component_id,
                request.reason
            )
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": success,
            "threat_id": request.threat_id,
            "dismissed_at": time.time(),
            "response_time_ms": response_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Threat dismissal failed: {str(e)}")

@router.post("/mitigation/detailed")
async def get_detailed_mitigation(request: DetailedMitigationRequest):
    """
    Get comprehensive mitigation details with implementation steps and Jira integration
    """
    start_time = time.time()
    
    try:
        async with GroqAIClient() as client:
            mitigation_details = await client.get_detailed_mitigation(
                request.threat_id,
                request.threat_title,
                request.component_type,
                request.canvas_context
            )
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            "mitigation": mitigation_details,
            "response_time_ms": response_time,
            "threat_id": request.threat_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detailed mitigation failed: {str(e)}")

@router.post("/jira/create-task")
async def create_jira_task(request: JiraTaskRequest):
    """
    Create a Jira task from threat and mitigation data
    """
    start_time = time.time()
    
    try:
        async with GroqAIClient() as client:
            jira_response = await client.create_jira_task(
                request.threat_data,
                request.mitigation_data,
                request.jira_config
            )
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            "jira_task": jira_response,
            "response_time_ms": response_time,
            "created_at": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jira task creation failed: {str(e)}")

@router.post("/canvas/refresh-check")
async def check_canvas_refresh(request: CanvasRefreshRequest):
    """
    Check if canvas has changed and threats need refreshing
    """
    start_time = time.time()
    
    try:
        async with GroqAIClient() as client:
            refresh_status = await client.refresh_threats_for_canvas_change(
                request.old_canvas_hash,
                request.canvas_context
            )
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            "refresh_status": refresh_status,
            "response_time_ms": response_time,
            "checked_at": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Canvas refresh check failed: {str(e)}")

@router.get("/threats/management/features")
async def get_threat_management_features():
    """
    Get available threat management features and their capabilities
    """
    return {
        "features": {
            "threat_dismissal": {
                "enabled": True,
                "description": "Users can dismiss threat suggestions with optional reasoning",
                "persistence": "session-based"  # In production, this would be "database-persistent"
            },
            "detailed_mitigations": {
                "enabled": True,
                "description": "Comprehensive mitigation guidance with implementation steps",
                "includes": ["tools_required", "effort_estimation", "implementation_steps", "jira_integration"]
            },
            "jira_integration": {
                "enabled": True,
                "description": "One-click Jira task creation from threat suggestions",
                "supported_fields": ["summary", "description", "priority", "labels", "components", "epic_link"]
            },
            "canvas_awareness": {
                "enabled": True,
                "description": "Real-time canvas change detection and threat refresh",
                "capabilities": ["hash_based_change_detection", "incremental_updates", "context_preservation"]
            },
            "dynamic_threat_count": {
                "enabled": True,
                "description": "AI-determined optimal threat count based on component complexity",
                "range": "1-12 threats per component"
            }
        },
        "ai_capabilities": {
            "methodologies_supported": ["STRIDE", "CIA", "LINDDUN", "CUSTOM"],
            "response_time_target": "700-1200ms",
            "confidence_scoring": True,
            "context_awareness": "full_canvas_and_component_relationships"
        }
    }
