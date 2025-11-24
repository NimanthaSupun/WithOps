"""
Threat Analysis AI Routes
Provides AI-powered threat analysis using Claude
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from core.claude_ai_client import claude_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["Threat Analysis"])

class ThreatAnalysisRequest(BaseModel):
    code: str
    context: Optional[str] = ""
    model: Optional[str] = "claude-3-5-sonnet-20241022"

class ThreatAnalysisResponse(BaseModel):
    success: bool
    analysis: str
    model_used: str
    message: str

@router.post("/threat-analysis", response_model=ThreatAnalysisResponse)
async def analyze_threats(request: ThreatAnalysisRequest):
    """
    Analyze code for security threats using Claude AI
    """
    try:
        # Use Claude for threat analysis
        analysis = await claude_client.analyze_threats(
            code=request.code,
            context=request.context,
            model=request.model
        )
        
        return ThreatAnalysisResponse(
            success=True,
            analysis=analysis,
            model_used=request.model,
            message="Threat analysis completed successfully"
        )
    except Exception as e:
        logger.error(f"Threat analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Threat analysis failed: {str(e)}"
        )
