# api/routes/threat_modeling.py

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel, validator
from fastapi.responses import StreamingResponse
from core.security import get_current_user
from core.redis_cache import cache
from core.document_processor import document_processor
from database.config import db_manager
from database.models import (
    ThreatModel, ThreatModelElement, ThreatAssessment, 
    ThreatModelCollaborator, ThreatModelVersion, ThreatLibrary,
    AIAnalysisHistory, User, Organization, Repository
)
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import logging
import hashlib
import PyPDF2
import docx
import io
import redis

router = APIRouter()
logger = logging.getLogger(__name__)

# =============================================================================
# 📊 PYDANTIC MODELS FOR REQUEST/RESPONSE
# =============================================================================

class ThreatModelCreate(BaseModel):
    name: str
    description: str
    methodology: str = "STRIDE"
    repository_id: Optional[int] = None
    metadata: Optional[Dict] = None
    canvas_data: Optional[Dict] = None

class ThreatModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    canvas_data: Optional[Dict] = None
    ai_analysis: Optional[Dict] = None
    last_ai_analysis: Optional[str] = None  # Will be converted to datetime in the endpoint

class ThreatElementCreate(BaseModel):
    element_type: str  # "process", "datastore", "dataflow", "external_entity"
    name: str

# =============================================================================
# 🧠 COMPREHENSIVE AI ANALYSIS
# =============================================================================

class ComprehensiveAnalysisRequest(BaseModel):
    canvas_data: Dict
    model_metadata: Dict
    document_context: Optional[Dict] = None

@router.post("/models/{model_id}/comprehensive-analysis")
async def perform_comprehensive_analysis(
    model_id: str, 
    request: ComprehensiveAnalysisRequest
):
    """
    Perform comprehensive AI analysis of threat model architecture.
    Combines canvas data, document context, and best practices.
    """
    try:
        logger.info(f"🧠 Starting comprehensive analysis for model: {model_id}")
        
        # Get the threat model from database
        async with db_manager.get_session() as session:
            model_query = select(ThreatModel).where(ThreatModel.id == model_id)
            model_result = await session.execute(model_query)
            threat_model = model_result.scalars().first()
            
            if not threat_model:
                raise HTTPException(status_code=404, detail="Threat model not found")
        
        # Extract analysis components
        canvas_data = request.canvas_data
        metadata = request.model_metadata
        document_analysis = request.document_context
        
        # Perform comprehensive analysis
        analysis_result = await analyze_threat_model_comprehensive(
            model_id=model_id,
            canvas_data=canvas_data,
            metadata=metadata,
            document_context=document_analysis,
            threat_model=threat_model
        )
        
        logger.info(f"✅ Comprehensive analysis complete for model: {model_id}")
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Comprehensive analysis failed for model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

async def analyze_threat_model_comprehensive(
    model_id: str,
    canvas_data: Dict,
    metadata: Dict,
    document_context: Optional[Dict],
    threat_model
) -> Dict:
    """
    Perform comprehensive threat model analysis combining multiple data sources.
    """
    
    # Extract canvas components
    elements = canvas_data.get("elements", [])
    connections = canvas_data.get("connections", [])
    existing_threats = canvas_data.get("threats", [])
    
    # Architecture Analysis
    architecture_analysis = {
        "component_count": len(elements),
        "connection_count": len(connections),
        "methodology": metadata.get("methodology", "STRIDE"),
        "complexity_score": calculate_complexity_score(elements, connections),
        "critical_components": identify_critical_components(elements, connections)
    }
    
    # Security Posture Analysis
    security_analysis = {
        "existing_threat_count": len(existing_threats),
        "coverage_analysis": analyze_threat_coverage(elements, existing_threats, metadata.get("methodology")),
        "risk_hotspots": identify_risk_hotspots(elements, connections, existing_threats),
        "security_gaps": identify_security_gaps(elements, connections, metadata.get("methodology"))
    }
    
    # Document Context Integration
    document_insights = {}
    if document_context:
        document_insights = {
            "document_available": True,
            "technologies_mentioned": document_context.get("technologies", []),
            "security_keywords": document_context.get("security_keywords", []),
            "compliance_requirements": extract_compliance_requirements(document_context),
            "document_driven_recommendations": generate_document_recommendations(document_context, elements)
        }
    else:
        document_insights = {"document_available": False}
    
    # Generate AI Recommendations
    recommendations = generate_comprehensive_recommendations(
        elements, connections, existing_threats, metadata, document_context
    )
    
    # Create comprehensive analysis response
    analysis_response = {
        "model_id": model_id,
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "analysis_version": "2.0-comprehensive",
        
        "executive_summary": generate_executive_summary(
            architecture_analysis, security_analysis, document_insights
        ),
        
        "architecture_analysis": architecture_analysis,
        "security_analysis": security_analysis,
        "document_insights": document_insights,
        
        "recommendations": recommendations,
        
        "action_items": generate_action_items(recommendations),
        
        "compliance_guidance": generate_compliance_guidance(
            metadata.get("methodology"), document_context
        ),
        
        "methodology_specific_insights": generate_methodology_insights(
            metadata.get("methodology"), elements, connections
        )
    }
    
    return analysis_response

def calculate_complexity_score(elements: List, connections: List) -> int:
    """Calculate architecture complexity score (1-10)"""
    base_score = min(len(elements) * 0.5 + len(connections) * 0.3, 8)
    
    # Increase complexity for multiple data stores, external entities
    datastore_count = len([e for e in elements if e.get("type") == "datastore"])
    external_count = len([e for e in elements if e.get("type") == "external_entity"])
    
    complexity_bonus = min(datastore_count * 0.5 + external_count * 0.3, 2)
    
    return min(int(base_score + complexity_bonus), 10)

def identify_critical_components(elements: List, connections: List) -> List:
    """Identify components with high connectivity or sensitive data"""
    critical = []
    
    # Count connections per element
    connection_counts = {}
    for conn in connections:
        source = conn.get("source")
        target = conn.get("target")
        connection_counts[source] = connection_counts.get(source, 0) + 1
        connection_counts[target] = connection_counts.get(target, 0) + 1
    
    for element in elements:
        element_id = element.get("id")
        connections_count = connection_counts.get(element_id, 0)
        
        # Critical if highly connected or sensitive type
        if connections_count >= 3 or element.get("type") in ["datastore", "process"]:
            critical.append({
                "id": element_id,
                "name": element.get("name", "Unnamed"),
                "type": element.get("type"),
                "connection_count": connections_count,
                "reason": "High connectivity" if connections_count >= 3 else "Sensitive component type"
            })
    
    return critical

def analyze_threat_coverage(elements: List, threats: List, methodology: str) -> Dict:
    """Analyze how well threats cover the architecture"""
    total_elements = len(elements)
    threatened_elements = set()
    
    for threat in threats:
        if threat.get("elementId"):
            threatened_elements.add(threat.get("elementId"))
    
    coverage_percentage = (len(threatened_elements) / max(total_elements, 1)) * 100
    
    return {
        "total_elements": total_elements,
        "threatened_elements": len(threatened_elements),
        "coverage_percentage": round(coverage_percentage, 1),
        "uncovered_elements": total_elements - len(threatened_elements),
        "methodology": methodology
    }

def identify_risk_hotspots(elements: List, connections: List, threats: List) -> List:
    """Identify components with highest risk concentration"""
    risk_scores = {}
    
    # Calculate risk per element based on threats
    for threat in threats:
        element_id = threat.get("elementId")
        if element_id:
            risk_score = threat.get("riskScore", 5)  # Default medium risk
            risk_scores[element_id] = risk_scores.get(element_id, 0) + risk_score
    
    # Sort by risk score
    hotspots = []
    for element in elements:
        element_id = element.get("id")
        total_risk = risk_scores.get(element_id, 0)
        
        if total_risk > 0:
            hotspots.append({
                "id": element_id,
                "name": element.get("name", "Unnamed"),
                "type": element.get("type"),
                "total_risk_score": total_risk,
                "threat_count": len([t for t in threats if t.get("elementId") == element_id])
            })
    
    # Return top 5 hotspots
    return sorted(hotspots, key=lambda x: x["total_risk_score"], reverse=True)[:5]

def identify_security_gaps(elements: List, connections: List, methodology: str) -> List:
    """Identify potential security gaps in the architecture"""
    gaps = []
    
    # Check for unprotected data stores
    datastores = [e for e in elements if e.get("type") == "datastore"]
    for ds in datastores:
        # Check if datastore has authentication/encryption connections
        ds_connections = [c for c in connections 
                         if c.get("source") == ds.get("id") or c.get("target") == ds.get("id")]
        
        if not any("auth" in c.get("label", "").lower() for c in ds_connections):
            gaps.append({
                "type": "authentication",
                "component": ds.get("name", "Unnamed Datastore"),
                "description": "Datastore may lack proper authentication controls",
                "severity": "High"
            })
    
    # Check for unencrypted external communications
    external_connections = []
    for conn in connections:
        source_el = next((e for e in elements if e.get("id") == conn.get("source")), None)
        target_el = next((e for e in elements if e.get("id") == conn.get("target")), None)
        
        if (source_el and source_el.get("type") == "external_entity") or \
           (target_el and target_el.get("type") == "external_entity"):
            if "encrypt" not in conn.get("label", "").lower() and "https" not in conn.get("label", "").lower():
                gaps.append({
                    "type": "encryption",
                    "component": f"Connection: {conn.get('label', 'Unnamed')}",
                    "description": "External communication may lack encryption",
                    "severity": "Medium"
                })
    
    return gaps

def extract_compliance_requirements(document_context: Dict) -> List:
    """Extract compliance requirements from document analysis"""
    compliance_terms = {
        "GDPR": ["gdpr", "general data protection regulation", "data protection"],
        "HIPAA": ["hipaa", "health insurance portability"],
        "SOX": ["sarbanes-oxley", "sox", "financial reporting"],
        "PCI DSS": ["pci", "payment card industry", "card data"],
        "ISO 27001": ["iso 27001", "information security management"]
    }
    
    requirements = []
    security_keywords = document_context.get("security_keywords", [])
    key_insights = document_context.get("key_insights", [])
    
    all_text = " ".join(security_keywords + key_insights).lower()
    
    for standard, keywords in compliance_terms.items():
        if any(keyword in all_text for keyword in keywords):
            requirements.append(standard)
    
    return requirements

def generate_document_recommendations(document_context: Dict, elements: List) -> List:
    """Generate recommendations based on document analysis"""
    recommendations = []
    
    technologies = document_context.get("technologies", [])
    security_keywords = document_context.get("security_keywords", [])
    
    # Technology-specific recommendations
    if "Database" in technologies:
        recommendations.append("Consider implementing database encryption at rest based on document requirements")
    
    if "Web Application" in technologies:
        recommendations.append("Implement web application security controls as mentioned in documentation")
    
    # Security keyword driven recommendations
    if "compliance" in security_keywords:
        recommendations.append("Ensure threat model addresses compliance requirements from documentation")
    
    if "monitoring" in security_keywords:
        recommendations.append("Add monitoring and logging components as specified in requirements")
    
    return recommendations

def generate_comprehensive_recommendations(
    elements: List, connections: List, threats: List, metadata: Dict, document_context: Optional[Dict]
) -> List:
    """Generate comprehensive AI-powered recommendations"""
    recommendations = []
    
    # Architecture recommendations
    if len(elements) > 10:
        recommendations.append({
            "category": "Architecture",
            "priority": "Medium",
            "title": "Consider Microservices Decomposition",
            "description": "Large monolithic architecture detected. Consider breaking into smaller services.",
            "rationale": "Improved security isolation and maintainability"
        })
    
    # Security recommendations based on methodology
    methodology = metadata.get("methodology", "STRIDE")
    
    if methodology == "STRIDE":
        # STRIDE-specific recommendations
        process_count = len([e for e in elements if e.get("type") == "process"])
        if process_count > 0 and len(threats) < process_count * 2:
            recommendations.append({
                "category": "Threat Coverage",
                "priority": "High", 
                "title": "Increase STRIDE Threat Coverage",
                "description": f"Only {len(threats)} threats identified for {process_count} processes. Consider all STRIDE categories.",
                "rationale": "Comprehensive threat coverage ensures no attack vectors are missed"
            })
    
    # Document-driven recommendations
    if document_context:
        technologies = document_context.get("technologies", [])
        if "API" in technologies:
            recommendations.append({
                "category": "API Security",
                "priority": "High",
                "title": "Implement API Security Controls", 
                "description": "Document mentions APIs. Ensure rate limiting, authentication, and input validation.",
                "rationale": "APIs are common attack vectors requiring specific security measures"
            })
    
    # Risk-based recommendations
    high_risk_threats = [t for t in threats if t.get("riskScore", 0) > 15]
    if high_risk_threats:
        recommendations.append({
            "category": "Risk Management",
            "priority": "Critical",
            "title": "Address Critical Risk Threats",
            "description": f"{len(high_risk_threats)} high-risk threats require immediate attention.",
            "rationale": "High-risk threats can lead to significant security incidents"
        })
    
    return recommendations

def generate_action_items(recommendations: List) -> List:
    """Convert recommendations into actionable items"""
    action_items = []
    
    for i, rec in enumerate(recommendations[:5]):  # Top 5 recommendations
        action_items.append({
            "id": f"action_{i+1}",
            "title": rec.get("title", ""),
            "priority": rec.get("priority", "Medium"),
            "category": rec.get("category", "General"),
            "estimated_effort": "Medium",  # Could be enhanced with ML
            "timeline": "Next Sprint" if rec.get("priority") == "Critical" else "Next Release"
        })
    
    return action_items

def generate_executive_summary(architecture_analysis: Dict, security_analysis: Dict, document_insights: Dict) -> str:
    """Generate executive summary of the analysis"""
    
    complexity = architecture_analysis.get("complexity_score", 0)
    threat_count = security_analysis.get("existing_threat_count", 0)
    coverage = security_analysis.get("coverage_analysis", {}).get("coverage_percentage", 0)
    
    summary_parts = []
    
    # Architecture overview
    summary_parts.append(f"Architecture contains {architecture_analysis.get('component_count', 0)} components with complexity score {complexity}/10.")
    
    # Security posture
    if coverage < 50:
        summary_parts.append(f"Security coverage at {coverage:.1f}% requires improvement.")
    else:
        summary_parts.append(f"Good security coverage at {coverage:.1f}%.")
    
    # Document integration
    if document_insights.get("document_available"):
        summary_parts.append("Analysis enhanced with uploaded documentation context.")
    
    # Risk assessment
    risk_hotspots = len(security_analysis.get("risk_hotspots", []))
    if risk_hotspots > 0:
        summary_parts.append(f"{risk_hotspots} high-risk components identified requiring attention.")
    
    return " ".join(summary_parts)

def generate_compliance_guidance(methodology: str, document_context: Optional[Dict]) -> Dict:
    """Generate compliance-specific guidance"""
    guidance = {
        "methodology_compliance": {},
        "document_driven": []
    }
    
    # Methodology-specific compliance
    if methodology == "STRIDE":
        guidance["methodology_compliance"] = {
            "framework": "STRIDE",
            "compliance_benefits": [
                "Comprehensive threat categorization",
                "Structured security analysis",
                "Industry-standard methodology"
            ]
        }
    
    # Document-driven compliance
    if document_context:
        requirements = extract_compliance_requirements(document_context)
        for req in requirements:
            guidance["document_driven"].append({
                "standard": req,
                "recommendation": f"Ensure threat model addresses {req} requirements"
            })
    
    return guidance

def generate_methodology_insights(methodology: str, elements: List, connections: List) -> Dict:
    """Generate methodology-specific insights and recommendations"""
    
    insights = {
        "methodology": methodology,
        "specific_recommendations": []
    }
    
    if methodology == "STRIDE":
        # STRIDE-specific analysis
        process_count = len([e for e in elements if e.get("type") == "process"])
        dataflow_count = len([e for e in elements if e.get("type") == "dataflow"])
        datastore_count = len([e for e in elements if e.get("type") == "datastore"])
        
        insights["component_breakdown"] = {
            "processes": process_count,
            "dataflows": dataflow_count, 
            "datastores": datastore_count
        }
        
        insights["specific_recommendations"] = [
            f"Analyze all {process_count} processes for Spoofing and Tampering threats",
            f"Review {datastore_count} datastores for Information Disclosure risks",
            f"Ensure {dataflow_count} dataflows have proper Elevation of Privilege controls"
        ]
    
    elif methodology == "CIA":
        # CIA Triad specific analysis
        insights["specific_recommendations"] = [
            "Verify Confidentiality controls for sensitive data elements",
            "Ensure Integrity mechanisms for all data modifications", 
            "Confirm Availability requirements for critical services"
        ]
    
    return insights

# =============================================================================
# � AI ANALYSIS HISTORY
# =============================================================================

@router.get("/models/{model_id}/analyses")
async def get_analysis_history(model_id: str):
    """Get all past AI analysis results for a threat model from ai_analysis_history table"""
    try:
        # Handle mock models
        if model_id.startswith("test-model-"):
            # Return mock analysis history
            return [
                {
                    "id": f"analysis-{i}",
                    "timestamp": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    "methodology": "STRIDE",
                    "analysis_type": "comprehensive" if i % 2 == 0 else "partial",
                    "diagram_elements_count": 5 - i,
                    "diagram_connections_count": 3 - i,
                    "analysis": f"Mock analysis result #{i+1} - This is a comprehensive STRIDE analysis...",
                    "success": True
                }
                for i in range(3)  # Return 3 mock analyses
            ]
        
        # Handle real database models - Query the NEW ai_analysis_history table
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(AIAnalysisHistory)
                .where(AIAnalysisHistory.threat_model_id == model_id)
                .order_by(AIAnalysisHistory.created_at.desc())  # Most recent first
            )
            history_records = result.scalars().all()
            
            # Convert to list of dictionaries matching the immediate AI result structure
            history = []
            for record in history_records:
                # Return the FULL analysis_data object to match immediate AI result format
                analysis_dict = record.analysis_data.copy() if record.analysis_data else {}
                
                # Debug logging
                logger.info(f"🔍 Record ID: {record.id}")
                logger.info(f"🔍 analysis_data keys: {list(analysis_dict.keys())}")
                logger.info(f"🔍 Has structured_analysis in analysis_data: {'structured_analysis' in analysis_dict}")
                
                # Ensure required fields are present
                analysis_dict.update({
                    "id": record.id,
                    "timestamp": record.created_at.isoformat() if record.created_at else datetime.utcnow().isoformat(),
                    "methodology": record.methodology,
                    "analysis_type": record.analysis_type,
                    "diagram_elements_count": record.diagram_elements_count,
                    "diagram_connections_count": record.diagram_connections_count,
                    "has_document": record.had_document,
                    "has_diagram": record.had_diagram,
                    "status": record.status,
                    "success": True
                })
                
                history.append(analysis_dict)
            
            logger.info(f"📚 Retrieved {len(history)} analyses from database history for model {model_id}")
            return history
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analysis history: {str(e)}")

@router.post("/models/{model_id}/analyses")
async def save_analysis(model_id: str, analysis_data: dict):
    """Save a new AI analysis result to the threat model history"""
    try:
        # Handle mock models
        if model_id.startswith("test-model-"):
            return {
                "success": True, 
                "message": f"Mock analysis saved for {model_id}",
                "id": analysis_data.get("id", f"mock-analysis-{int(time.time())}")
            }
        
        # For real models, update the threat model with the latest analysis
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            # Update the model with the new analysis (for quick access to latest)
            model.ai_analysis = analysis_data
            
            # Parse timestamp and remove timezone info (database uses timezone-naive datetimes)
            timestamp_str = analysis_data.get("timestamp", datetime.utcnow().isoformat())
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Remove timezone info to match database schema
            model.last_ai_analysis = timestamp.replace(tzinfo=None)
            model.updated_at = datetime.utcnow()
            
            # 🆕 SAVE TO HISTORY TABLE - Store EVERY analysis, not just the latest
            history_record = AIAnalysisHistory(
                id=analysis_data.get("id", f"analysis-{int(time.time())}-{model_id[:8]}"),
                threat_model_id=model_id,
                user_id=model.user_id,  # User who created the model (or could be current user)
                analysis_type=analysis_data.get("analysis_type", "comprehensive"),
                methodology=analysis_data.get("methodology", "STRIDE"),
                analysis_data=analysis_data,  # Store complete analysis
                structured_analysis=analysis_data.get("structured_analysis"),  # Store parsed data
                diagram_elements_count=analysis_data.get("diagram_elements_count", 0),
                diagram_connections_count=analysis_data.get("diagram_connections_count", 0),
                had_document=analysis_data.get("has_document", False),
                had_diagram=analysis_data.get("has_diagram", False),
                status="completed",
                created_at=timestamp.replace(tzinfo=None)
            )
            session.add(history_record)
            
            await session.commit()
            
            logger.info(f"✅ Saved analysis {analysis_data.get('id')} to BOTH main table and history table for model {model_id}")
            
            return {
                "success": True,
                "id": analysis_data.get("id"),
                "timestamp": analysis_data.get("timestamp"),
                "message": "Analysis saved successfully to database history"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save analysis: {str(e)}")

@router.delete("/models/{model_id}/analysis/{analysis_id}")
async def delete_analysis(model_id: str, analysis_id: str):
    """Delete a specific AI analysis record from history"""
    try:
        # Handle mock models
        if model_id.startswith("test-model-"):
            return {"success": True, "message": f"Mock analysis {analysis_id} deleted"}
        
        # Delete from ai_analysis_history table
        async with db_manager.get_session() as session:
            # First verify the threat model exists
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            # Delete the specific analysis from history table
            result = await session.execute(
                select(AIAnalysisHistory).where(
                    AIAnalysisHistory.id == analysis_id,
                    AIAnalysisHistory.threat_model_id == model_id
                )
            )
            analysis = result.scalars().first()
            
            if not analysis:
                raise HTTPException(status_code=404, detail="Analysis not found")
            
            await session.delete(analysis)
            await session.commit()
            
            logger.info(f"✅ Deleted analysis {analysis_id} from database")
            return {"success": True, "message": "Analysis deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete analysis: {str(e)}")

# =============================================================================
# �🔧 HEALTH CHECK
# =============================================================================

@router.get("/health")
async def threat_modeling_health():
    """Health check for threat modeling service"""
    return {
        "status": "healthy",
        "service": "threat-modeling",
        "timestamp": datetime.utcnow().isoformat()
    }
    description: Optional[str] = None
    position: Dict  # Canvas position
    properties: Optional[Dict] = None

# =============================================================================
# 🧪 SIMPLE TEST ENDPOINTS (NO AUTH FOR TESTING)
# =============================================================================

@router.get("/library")
async def get_all_threats():
    """Get all predefined threats from library (for testing)"""
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatLibrary).where(ThreatLibrary.is_built_in == True)
            )
            threats = result.scalars().all()
            
            threat_list = []
            for threat in threats:
                threat_data = {
                    "id": threat.id,
                    "methodology": threat.methodology,
                    "category": threat.category,
                    "threat_name": threat.threat_name,
                    "threat_description": threat.threat_description,
                    "applicable_elements": threat.applicable_elements,
                    "example_scenarios": threat.example_scenarios,
                    "default_impact": threat.default_impact,
                    "default_likelihood": threat.default_likelihood,
                    "common_mitigations": threat.common_mitigations
                }
                threat_list.append(threat_data)
            
            return threat_list
            
    except Exception as e:
        logger.error(f"Error fetching threat library: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching threats: {str(e)}")

@router.get("/dashboard")
async def get_dashboard_overview():
    """Get dashboard overview (for testing)"""
    try:
        async with db_manager.get_session() as session:
            # Get basic stats
            total_models = await session.execute(select(func.count(ThreatModel.id)))
            total_count = total_models.scalar() or 0
            
            # Get recent models
            recent_query = select(ThreatModel).order_by(ThreatModel.created_at.desc()).limit(5)
            recent_result = await session.execute(recent_query)
            recent_models = recent_result.scalars().all()
            
            recent_activity = []
            for model in recent_models:
                recent_activity.append({
                    "id": model.id,
                    "name": model.name,
                    "status": model.status,
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                    "updated_at": model.updated_at.isoformat() if model.updated_at else None
                })
            
            return {
                "total_models": total_count,
                "recent_activity": recent_activity,
                "status": "success"
            }
            
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard: {str(e)}")

@router.post("/models")
async def create_threat_model_simple(request: ThreatModelCreate, current_user: str = Depends(get_current_user)):
    """Create a threat model for the authenticated user"""
    try:
        async with db_manager.get_session() as session:
            # Get the authenticated user's internal ID
            from database.operations import UserRepository, OrganizationInstallationRepository
            user = await UserRepository.get_user_by_auth_id(session, current_user)
            if not user:
                logger.warning(f"⚠️ User not found: {current_user}")
                raise HTTPException(status_code=404, detail="User not found")
            
            logger.info(f"🔍 Creating threat model for user: {current_user} (ID: {user.id})")
            
            # Get user's installations to find their organizations
            user_installations = await OrganizationInstallationRepository.get_user_installations(session, user.id)
            
            if not user_installations:
                logger.warning(f"⚠️ User {current_user} has no organization installations")
                raise HTTPException(
                    status_code=400, 
                    detail="You must have at least one organization installed to create threat models"
                )
            
            # Use the first organization
            default_org_id = user_installations[0].organization_id
            
            # Create the threat model with authenticated user
            new_model = ThreatModel(
                name=request.name,
                description=request.description,
                methodology=request.methodology,
                status="draft",
                organization_id=default_org_id,
                user_id=user.id,  # Use authenticated user's ID
                canvas_data=request.canvas_data or {
                    "elements": [],
                    "connections": [],
                    "metadata": { "zoom": 1.0, "panX": 0, "panY": 0 }
                },
                created_at=datetime.utcnow()
            )
            
            session.add(new_model)
            await session.commit()
            await session.refresh(new_model)
            
            logger.info(f"✅ Created threat model in database: {new_model.id} for user: {current_user}")
            
            return {
                "id": new_model.id,
                "name": new_model.name,
                "description": new_model.description,
                "methodology": new_model.methodology,
                "status": new_model.status,
                "canvas_data": new_model.canvas_data,
                "created_at": new_model.created_at.isoformat(),
                "message": "Threat model created successfully and saved to database"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating threat model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating model: {str(e)}")

@router.get("/models")
async def list_threat_models_simple(current_user: str = Depends(get_current_user)):
    """List threat models for the authenticated user"""
    import time
    start_time = time.time()
    logger.info(f"🔍 Starting list_threat_models_simple endpoint for user: {current_user}")
    
    try:
        logger.info("🔍 Creating database session...")
        async with db_manager.get_session() as session:
            session_time = time.time()
            logger.info(f"🔍 Database session created in {session_time - start_time:.2f}s")
            
            # Get the user's internal ID from auth_user_id
            from database.operations import UserRepository
            user = await UserRepository.get_user_by_auth_id(session, current_user)
            if not user:
                logger.warning(f"⚠️ User not found: {current_user}")
                raise HTTPException(status_code=404, detail="User not found")
            
            logger.info(f"🔍 Executing ThreatModel query for user_id: {user.id} (auth_user_id: {current_user})...")
            
            # First, let's check ALL threat models to debug
            all_models_result = await session.execute(select(ThreatModel))
            all_models = all_models_result.scalars().all()
            logger.info(f"📊 DEBUG: Total threat models in database: {len(all_models)}")
            for m in all_models[:5]:  # Show first 5
                logger.info(f"📊 DEBUG: Model '{m.name}' - user_id: {m.user_id}")
            
            # Now get user's models
            result = await session.execute(
                select(ThreatModel)
                .where(ThreatModel.user_id == user.id)
                .order_by(ThreatModel.created_at.desc())
            )
            query_time = time.time()
            logger.info(f"🔍 Query executed in {query_time - session_time:.2f}s")
            
            models = result.scalars().all()
            fetch_time = time.time()
            logger.info(f"🔍 Models fetched ({len(models)} models) in {fetch_time - query_time:.2f}s")
            
            model_list = []
            for i, model in enumerate(models):
                if i % 10 == 0:  # Log every 10 models
                    logger.info(f"🔍 Processing model {i+1}/{len(models)}")
                    
                model_data = {
                    "id": model.id,
                    "name": model.name,
                    "description": model.description,
                    "methodology": model.methodology,
                    "status": model.status,
                    
                    # Document analysis fields
                    "document_status": getattr(model, 'document_status', 'none'),
                    "document_file_name": getattr(model, 'document_file_name', None),
                    "document_analysis": getattr(model, 'document_analysis', {}),
                    "document_processed_at": model.document_processed_at.isoformat() if getattr(model, 'document_processed_at', None) else None,
                    
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                    "updated_at": model.updated_at.isoformat() if model.updated_at else None
                }
                model_list.append(model_data)
            
            process_time = time.time()
            logger.info(f"🔍 Models processed in {process_time - fetch_time:.2f}s")
            logger.info(f"✅ Total endpoint time: {process_time - start_time:.2f}s")
            
            return model_list
            
    except Exception as e:
        logger.error(f"Error listing threat models: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")

@router.get("/models/{model_id}")
async def get_threat_model_simple(model_id: str):
    """Get a specific threat model (simplified for testing)"""
    try:
        # Handle mock models (test-model-* IDs)
        if model_id.startswith("test-model-"):
            return {
                "id": model_id,
                "name": f"Mock Model {model_id.split('-')[-1][:8]}",
                "description": "This is a mock threat model for testing the canvas",
                "methodology": "STRIDE",
                "status": "draft",
                "canvas_data": {
                    "elements": [],
                    "connections": [],
                    "metadata": { "zoom": 1.0, "panX": 0, "panY": 0 }
                },
                "created_at": "2025-07-28T13:29:05.670051",
                "updated_at": None,
                "is_mock": True
            }
        
        # Handle real database models
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            return {
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "methodology": model.methodology,
                "status": model.status,
                "canvas_data": model.canvas_data or {
                    "elements": [],
                    "connections": [],
                    "metadata": { "zoom": 1.0, "panX": 0, "panY": 0 }
                },
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None,
                "is_mock": False
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching threat model: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching model: {str(e)}")

@router.put("/models/{model_id}")
async def update_threat_model_simple(model_id: str, request: ThreatModelUpdate):
    """Update a threat model (simplified for testing)"""
    try:
        # Handle mock models - just return success for testing
        if model_id.startswith("test-model-"):
            return {
                "id": model_id,
                "name": f"Mock Model {model_id.split('-')[-1][:8]}",
                "description": "Updated mock model",
                "methodology": "STRIDE",
                "status": "draft",
                "updated_at": datetime.utcnow().isoformat(),
                "message": "Mock model updated successfully"
            }
        
        # Handle real database models
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            # Update fields if provided
            update_data = request.dict(exclude_unset=True)
            
            # Handle datetime conversion for last_ai_analysis
            if 'last_ai_analysis' in update_data and update_data['last_ai_analysis']:
                if isinstance(update_data['last_ai_analysis'], str):
                    try:
                        # Parse and convert to timezone-naive datetime
                        dt = datetime.fromisoformat(
                            update_data['last_ai_analysis'].replace('Z', '+00:00')
                        )
                        # Remove timezone info for database compatibility
                        update_data['last_ai_analysis'] = dt.replace(tzinfo=None)
                    except ValueError:
                        # If parsing fails, use current time
                        update_data['last_ai_analysis'] = datetime.utcnow()
            
            for field, value in update_data.items():
                setattr(model, field, value)
            
            model.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(model)
            
            return {
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "methodology": model.methodology,
                "status": model.status,
                "canvas_data": model.canvas_data,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None,
                "ai_analysis": model.ai_analysis,
                "last_ai_analysis": model.last_ai_analysis.isoformat() if model.last_ai_analysis else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating threat model: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating model: {str(e)}")

@router.delete("/models/{model_id}")
async def delete_threat_model_simple(model_id: str):
    """Delete a threat model (simplified for testing)"""
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            await session.delete(model)
            await session.commit()
            
            return {"message": "Threat model deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting threat model: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting model: {str(e)}")

# =============================================================================
# � DOCUMENT UPLOAD AND PROCESSING
# =============================================================================

@router.post("/models/{model_id}/upload-document")
async def upload_document(model_id: str, file: UploadFile = File(...)):
    """
    Upload and process a document for enhanced AI threat analysis context
    
    Supports: PDF, DOCX, DOC, TXT files up to 10MB
    Provides enhanced text extraction and analysis for better AI insights
    """
    try:
        logger.info(f"📄 Processing document upload for model {model_id}: {file.filename}")
        
        # Update model status to processing
        async with db_manager.get_session() as session:
            model_result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = model_result.scalar_one_or_none()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            # Set processing status
            model.document_status = "processing"
            model.updated_at = datetime.utcnow()
            await session.commit()
        
        # Read file content
        file_content = await file.read()
        
        # Process document using enhanced processor
        processing_result = await document_processor.process_document(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        if not processing_result["success"]:
            # Update model status to failed
            async with db_manager.get_session() as session:
                model.document_status = "failed"
                await session.commit()
            
            raise HTTPException(status_code=400, detail=processing_result["error"])
        
        # Update database with processing results
        async with db_manager.get_session() as session:
            model_result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = model_result.scalar_one_or_none()
            
            # Update model with enhanced document analysis
            model.document_analysis = {
                "processing_result": processing_result,
                "extracted_text": processing_result["text_content"],
                "analysis": processing_result["analysis"],
                "metadata": {
                    "word_count": processing_result["word_count"],
                    "character_count": processing_result["character_count"],
                    "file_format": processing_result["file_format"],
                    "processed_at": processing_result["processed_at"]
                }
            }
            model.document_status = "completed"
            model.document_file_name = file.filename
            model.document_processed_at = datetime.utcnow()
            model.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(model)
        
        # Cache for fast access during AI analysis
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            cache_key = f"doc_analysis:{model_id}"
            await asyncio.get_event_loop().run_in_executor(
                None, 
                redis_client.setex, 
                cache_key, 
                604800,  # 7 days
                json.dumps(model.document_analysis)
            )
        except Exception as cache_error:
            logger.warning(f"⚠️ Redis cache failed for model {model_id}: {cache_error}")
        
        logger.info(f"✅ Document processed successfully: {file.filename} ({processing_result['word_count']} words)")
        
        return {
            "success": True,
            "message": "Document uploaded and processed successfully",
            "document_info": {
                "filename": file.filename,
                "file_size": processing_result["file_size"],
                "file_format": processing_result["file_format"],
                "word_count": processing_result["word_count"],
                "character_count": processing_result["character_count"]
            },
            "document_analysis": {
                "extracted_text": processing_result["text_content"],
                "analysis": processing_result["analysis"],
                "metadata": {
                    "word_count": processing_result["word_count"],
                    "character_count": processing_result["character_count"],
                    "file_format": processing_result["file_format"],
                    "processed_at": processing_result["processed_at"]
                }
            },
            "analysis_preview": {
                "technologies_found": len(processing_result["analysis"]["technologies"]),
                "security_concerns": processing_result["analysis"]["security_concerns"],
                "has_architecture_info": processing_result["analysis"]["has_architecture_info"],
                "complexity_score": processing_result["analysis"]["complexity_score"]
            },
            "ai_ready": True  # Document is ready for AI analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing document upload: {e}")
        
        # Update model status to failed
        try:
            async with db_manager.get_session() as session:
                model_result = await session.execute(
                    select(ThreatModel).where(ThreatModel.id == model_id)
                )
                model = model_result.scalar_one_or_none()
                if model:
                    model.document_status = "failed"
                    await session.commit()
        except Exception:
            pass  # Don't let database errors mask the original error
        
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


async def analyze_document_content(text: str, filename: str) -> Dict:
    """Analyze document content and extract key insights"""
    try:
        # Basic text analysis (we'll enhance this with AI later)
        words = text.lower().split()
        word_count = len(words)
        
        # Technology detection
        tech_keywords = {
            'aws': ['aws', 'amazon web services', 'ec2', 'lambda', 'rds', 's3', 'cloudformation'],
            'kubernetes': ['kubernetes', 'k8s', 'kubectl', 'pods', 'services', 'ingress'],
            'docker': ['docker', 'container', 'dockerfile', 'image'],
            'database': ['database', 'mysql', 'postgresql', 'mongodb', 'redis'],
            'security': ['security', 'authentication', 'authorization', 'encryption', 'tls', 'ssl'],
            'microservices': ['microservice', 'microservices', 'api gateway', 'service mesh'],
            'cicd': ['ci/cd', 'jenkins', 'github actions', 'gitlab', 'pipeline']
        }
        
        detected_technologies = []
        for category, keywords in tech_keywords.items():
            if any(keyword in text.lower() for keyword in keywords):
                detected_technologies.append(category)
        
        # Security-related keyword extraction
        security_keywords = []
        security_terms = [
            'authentication', 'authorization', 'encryption', 'security', 'vulnerability', 
            'threat', 'risk', 'compliance', 'audit', 'monitoring', 'logging'
        ]
        
        for term in security_terms:
            if term in text.lower():
                security_keywords.append(term)
        
        # Key insights extraction (simple version - we'll enhance with AI)
        key_insights = []
        
        if 'architecture' in text.lower():
            key_insights.append("Document contains architectural information")
        if 'requirement' in text.lower():
            key_insights.append("Document contains requirements specification")
        if 'security' in text.lower():
            key_insights.append("Document contains security considerations")
        if 'compliance' in text.lower():
            key_insights.append("Document mentions compliance requirements")
        
        return {
            "filename": filename,
            "word_count": word_count,
            "technologies": detected_technologies,
            "security_keywords": security_keywords,
            "key_insights": key_insights,
            "extracted_at": datetime.utcnow().isoformat(),
            "analysis_version": "1.0"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing document content: {e}")
        return {
            "filename": filename,
            "error": str(e),
            "extracted_at": datetime.utcnow().isoformat()
        }

# =============================================================================
# �🔧 HEALTH CHECK
# =============================================================================

@router.get("/health")
async def threat_modeling_health():
    """Health check for threat modeling service"""
    return {
        "status": "healthy",
        "service": "threat-modeling",
        "timestamp": datetime.utcnow().isoformat()
    }
