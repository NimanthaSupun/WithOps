# api/routes/threat_modeling.py

import asyncio
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from core.security import get_current_user
from core.redis_cache import cache
from database.config import db_manager
from database.models import (
    ThreatModel, ThreatModelElement, ThreatAssessment, 
    ThreatModelCollaborator, ThreatModelVersion, ThreatLibrary,
    User, Organization, Repository
)
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
 # =============================================================================
# 🔧 THREAT LIBRARY ENDPOINTS
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

# (Removed invalid decorator and misplaced code)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# =============================================================================
# 📊 PYDANTIC MODELS FOR REQUEST/RESPONSE
# =============================================================================

class ThreatModelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    methodology: str = "STRIDE"  # STRIDE, LINDDUN, CIA, CUSTOM
    repository_id: Optional[str] = None  # If tied to specific repo
    is_public: bool = False

class ThreatModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    canvas_data: Optional[Dict] = None

class ThreatElementCreate(BaseModel):
    element_type: str  # process, datastore, external_entity, trust_boundary
    name: str
    description: Optional[str] = None
    x_position: int = 0
    y_position: int = 0
    width: int = 100
    height: int = 60
    properties: Optional[Dict] = {}

class ThreatAssessmentCreate(BaseModel):
    element_id: Optional[str] = None
    threat_category: str  # S, T, R, I, D, E for STRIDE
    threat_title: str
    threat_description: Optional[str] = None
    impact_level: str = "medium"
    likelihood: str = "medium"
    mitigation_description: Optional[str] = None

class AIAnalysisRequest(BaseModel):
    threat_model_id: str
    analysis_type: str = "full"  # full, element, pattern_recognition
    context: Optional[Dict] = {}

# =============================================================================
# 🛡️ THREAT MODEL CRUD OPERATIONS
# =============================================================================

@router.get("/models/{org_name}")
async def get_threat_models(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """Get all threat models for an organization"""
    try:
        # Check cache first for performance
        cache_key = f"threat_models_{org_name}_{current_user}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"🚀 Returning cached threat models for {org_name}")
            return json.loads(cached_result)
        
        async with db_manager.get_session() as session:
            # Get organization
            org_query = select(Organization).where(Organization.login == org_name)
            org_result = await session.execute(org_query)
            organization = org_result.scalar_one_or_none()
            
            if not organization:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            # Get user
            user_query = select(User).where(User.auth_user_id == current_user)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get threat models (user can see models they created or are collaborators on)
            models_query = select(ThreatModel).options(
                selectinload(ThreatModel.creator),
                selectinload(ThreatModel.repository),
                selectinload(ThreatModel.collaborators)
            ).where(
                and_(
                    ThreatModel.organization_id == organization.id,
                    or_(
                        ThreatModel.user_id == user.id,
                        ThreatModel.is_public == True,
                        ThreatModel.collaborators.any(ThreatModelCollaborator.user_id == user.id)
                    )
                )
            ).order_by(ThreatModel.updated_at.desc())
            
            models_result = await session.execute(models_query)
            threat_models = models_result.scalars().all()
            
            # Format response
            models_data = []
            for model in threat_models:
                # Get element count
                element_count_query = select(func.count(ThreatModelElement.id)).where(
                    ThreatModelElement.threat_model_id == model.id
                )
                element_count_result = await session.execute(element_count_query)
                element_count = element_count_result.scalar() or 0
                
                # Get assessment count
                assessment_count_query = select(func.count(ThreatAssessment.id)).where(
                    ThreatAssessment.threat_model_id == model.id
                )
                assessment_count_result = await session.execute(assessment_count_query)
                assessment_count = assessment_count_result.scalar() or 0
                
                models_data.append({
                    "id": model.id,
                    "name": model.name,
                    "description": model.description,
                    "methodology": model.methodology,
                    "status": model.status,
                    "version": model.version,
                    "is_public": model.is_public,
                    "element_count": element_count,
                    "assessment_count": assessment_count,
                    "creator": {
                        "id": model.creator.id if model.creator else None,
                        "name": model.creator.name if model.creator else "Unknown",
                        "email": model.creator.email if model.creator else None
                    },
                    "repository": {
                        "id": model.repository.id if model.repository else None,
                        "name": model.repository.name if model.repository else None,
                        "full_name": model.repository.full_name if model.repository else None
                    } if model.repository else None,
                    "last_ai_analysis": model.last_ai_analysis.isoformat() if model.last_ai_analysis else None,
                    "created_at": model.created_at.isoformat(),
                    "updated_at": model.updated_at.isoformat()
                })
            
            result = {
                "success": True,
                "models": models_data,
                "total_count": len(models_data),
                "organization": {
                    "id": organization.id,
                    "login": organization.login,
                    "name": organization.name
                }
            }
            
            # Cache for 5 minutes for performance
            await cache.set(cache_key, json.dumps(result, default=str), expire=300)
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting threat models for {org_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get threat models: {str(e)}")


@router.post("/models/{org_name}")
async def create_threat_model(
    org_name: str,
    request: ThreatModelCreate,
    current_user: str = Depends(get_current_user)
):
    """Create a new threat model"""
    try:
        async with db_manager.get_session() as session:
            # Get organization
            org_query = select(Organization).where(Organization.login == org_name)
            org_result = await session.execute(org_query)
            organization = org_result.scalar_one_or_none()
            
            if not organization:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            # Get user
            user_query = select(User).where(User.auth_user_id == current_user)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Validate repository if provided
            repository = None
            if request.repository_id:
                repo_query = select(Repository).where(Repository.id == request.repository_id)
                repo_result = await session.execute(repo_query)
                repository = repo_result.scalar_one_or_none()
                
                if not repository:
                    raise HTTPException(status_code=404, detail="Repository not found")
            
            # Create threat model
            threat_model = ThreatModel(
                organization_id=organization.id,
                repository_id=repository.id if repository else None,
                user_id=user.id,
                name=request.name,
                description=request.description,
                methodology=request.methodology,
                is_public=request.is_public,
                canvas_data={
                    "nodes": [],
                    "edges": [],
                    "metadata": {
                        "version": "1.0",
                        "created_with": "WithOps Threat Modeling"
                    }
                }
            )
            
            session.add(threat_model)
            await session.commit()
            await session.refresh(threat_model)
            
            # Clear cache
            cache_key = f"threat_models_{org_name}_{current_user}"
            await cache.delete(cache_key)
            
            logger.info(f"✅ Created threat model '{request.name}' for {org_name} by user {current_user}")
            
            return {
                "success": True,
                "message": "Threat model created successfully",
                "threat_model": {
                    "id": threat_model.id,
                    "name": threat_model.name,
                    "description": threat_model.description,
                    "methodology": threat_model.methodology,
                    "status": threat_model.status,
                    "created_at": threat_model.created_at.isoformat()
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating threat model for {org_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create threat model: {str(e)}")


@router.get("/models/{org_name}/{model_id}")
async def get_threat_model_details(
    org_name: str,
    model_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get detailed information about a specific threat model"""
    try:
        # Check cache first
        cache_key = f"threat_model_details_{model_id}_{current_user}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"🚀 Returning cached threat model details for {model_id}")
            return json.loads(cached_result)
        
        async with db_manager.get_session() as session:
            # Get threat model with all relationships
            model_query = select(ThreatModel).options(
                selectinload(ThreatModel.creator),
                selectinload(ThreatModel.repository),
                selectinload(ThreatModel.elements),
                selectinload(ThreatModel.assessments),
                selectinload(ThreatModel.collaborators).selectinload(ThreatModelCollaborator.user)
            ).where(ThreatModel.id == model_id)
            
            model_result = await session.execute(model_query)
            threat_model = model_result.scalar_one_or_none()
            
            if not threat_model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            # Check user access
            user_query = select(User).where(User.auth_user_id == current_user)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Verify access permissions
            has_access = (
                threat_model.user_id == user.id or 
                threat_model.is_public or
                any(collab.user_id == user.id for collab in threat_model.collaborators)
            )
            
            if not has_access:
                raise HTTPException(status_code=403, detail="Access denied to this threat model")
            
            # Format detailed response
            result = {
                "success": True,
                "threat_model": {
                    "id": threat_model.id,
                    "name": threat_model.name,
                    "description": threat_model.description,
                    "methodology": threat_model.methodology,
                    "status": threat_model.status,
                    "version": threat_model.version,
                    "is_public": threat_model.is_public,
                    "canvas_data": threat_model.canvas_data,
                    "ai_analysis": threat_model.ai_analysis,
                    "last_ai_analysis": threat_model.last_ai_analysis.isoformat() if threat_model.last_ai_analysis else None,
                    "creator": {
                        "id": threat_model.creator.id,
                        "name": threat_model.creator.name,
                        "email": threat_model.creator.email
                    },
                    "repository": {
                        "id": threat_model.repository.id,
                        "name": threat_model.repository.name,
                        "full_name": threat_model.repository.full_name
                    } if threat_model.repository else None,
                    "elements": [{
                        "id": element.id,
                        "element_type": element.element_type,
                        "name": element.name,
                        "description": element.description,
                        "x_position": element.x_position,
                        "y_position": element.y_position,
                        "width": element.width,
                        "height": element.height,
                        "properties": element.properties,
                        "identified_threats": element.identified_threats,
                        "risk_score": element.risk_score,
                        "created_at": element.created_at.isoformat(),
                        "updated_at": element.updated_at.isoformat()
                    } for element in threat_model.elements],
                    "assessments": [{
                        "id": assessment.id,
                        "element_id": assessment.element_id,
                        "threat_category": assessment.threat_category,
                        "threat_title": assessment.threat_title,
                        "threat_description": assessment.threat_description,
                        "impact_level": assessment.impact_level,
                        "likelihood": assessment.likelihood,
                        "risk_level": assessment.risk_level,
                        "mitigation_status": assessment.mitigation_status,
                        "mitigation_description": assessment.mitigation_description,
                        "ai_generated": assessment.ai_generated,
                        "ai_confidence": assessment.ai_confidence,
                        "created_at": assessment.created_at.isoformat(),
                        "updated_at": assessment.updated_at.isoformat()
                    } for assessment in threat_model.assessments],
                    "collaborators": [{
                        "id": collab.id,
                        "user": {
                            "id": collab.user.id,
                            "name": collab.user.name,
                            "email": collab.user.email
                        },
                        "role": collab.role,
                        "can_edit": collab.can_edit,
                        "can_approve": collab.can_approve,
                        "invitation_status": collab.invitation_status,
                        "invited_at": collab.invited_at.isoformat()
                    } for collab in threat_model.collaborators],
                    "created_at": threat_model.created_at.isoformat(),
                    "updated_at": threat_model.updated_at.isoformat()
                }
            }
            
            # Cache for 2 minutes (shorter since this data changes more frequently)
            await cache.set(cache_key, json.dumps(result, default=str), expire=120)
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting threat model details for {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get threat model: {str(e)}")


# =============================================================================
# 🤖 AI INTEGRATION ENDPOINTS (We'll implement AI here)
# =============================================================================

@router.post("/ai/analyze")
async def analyze_threat_model_with_ai(
    request: AIAnalysisRequest,
    current_user: str = Depends(get_current_user)
):
    """
    🤖 AI-powered threat analysis using Groq/HuggingFace
    THIS IS WHERE WE'LL INTEGRATE AI SERVICES
    """
    try:
        # TODO: This is where we'll integrate AI services
        # For now, return a placeholder response
        
        logger.info(f"🤖 AI analysis requested for model {request.threat_model_id} by user {current_user}")
        
        # Placeholder response - we'll implement AI integration next
        return {
            "success": True,
            "message": "AI analysis endpoint ready - AI integration will be implemented next",
            "analysis_type": request.analysis_type,
            "threat_model_id": request.threat_model_id,
            "note": "This endpoint is prepared for AI integration with Groq/HuggingFace"
        }
        
    except Exception as e:
        logger.error(f"Error in AI analysis: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


# =============================================================================
# 📚 THREAT LIBRARY ENDPOINTS
# =============================================================================

@router.get("/library/{methodology}")
async def get_threat_library(
    methodology: str = "STRIDE",
    current_user: str = Depends(get_current_user)
):
    """Get predefined threats for a methodology"""
    try:
        # Check cache first
        cache_key = f"threat_library_{methodology}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"🚀 Returning cached threat library for {methodology}")
            return json.loads(cached_result)
        
        async with db_manager.get_session() as session:
            # Get built-in threats for methodology
            library_query = select(ThreatLibrary).where(
                and_(
                    ThreatLibrary.methodology == methodology,
                    ThreatLibrary.is_built_in == True
                )
            ).order_by(ThreatLibrary.category, ThreatLibrary.threat_name)
            
            library_result = await session.execute(library_query)
            threats = library_result.scalars().all()
            
            # Group by category
            threats_by_category = {}
            for threat in threats:
                if threat.category not in threats_by_category:
                    threats_by_category[threat.category] = []
                
                threats_by_category[threat.category].append({
                    "id": threat.id,
                    "threat_name": threat.threat_name,
                    "threat_description": threat.threat_description,
                    "applicable_elements": threat.applicable_elements,
                    "example_scenarios": threat.example_scenarios,
                    "default_impact": threat.default_impact,
                    "default_likelihood": threat.default_likelihood,
                    "common_mitigations": threat.common_mitigations
                })
            
            result = {
                "success": True,
                "methodology": methodology,
                "threats_by_category": threats_by_category,
                "total_threats": len(threats)
            }
            
            # Cache for 1 hour (threat library doesn't change often)
            await cache.set(cache_key, json.dumps(result, default=str), expire=3600)
            
            return result
            
    except Exception as e:
        logger.error(f"Error getting threat library for {methodology}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get threat library: {str(e)}")


# =============================================================================
# 🔄 REAL-TIME COLLABORATION ENDPOINTS (For Liveblocks integration)
# =============================================================================

@router.get("/collaborate/{model_id}/auth")
async def get_collaboration_auth(
    model_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get authentication token for real-time collaboration"""
    try:
        # TODO: Integrate with Liveblocks authentication
        # For now, return a placeholder
        
        return {
            "success": True,
            "collaboration_token": "placeholder_token",
            "model_id": model_id,
            "user_id": current_user,
            "note": "Liveblocks integration will be implemented in Phase 3"
        }
        
    except Exception as e:
        logger.error(f"Error getting collaboration auth for {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get collaboration auth: {str(e)}")


# =============================================================================
# 📊 DASHBOARD & ANALYTICS
# =============================================================================

@router.get("/dashboard/{org_name}")
async def get_threat_modeling_dashboard(
    org_name: str,
    current_user: str = Depends(get_current_user)
):
    """Get threat modeling dashboard data for organization"""
    try:
        # Check cache first
        cache_key = f"threat_dashboard_{org_name}_{current_user}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"🚀 Returning cached threat dashboard for {org_name}")
            return json.loads(cached_result)
        
        async with db_manager.get_session() as session:
            # Get organization
            org_query = select(Organization).where(Organization.login == org_name)
            org_result = await session.execute(org_query)
            organization = org_result.scalar_one_or_none()
            
            if not organization:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            # Get user
            user_query = select(User).where(User.auth_user_id == current_user)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get dashboard statistics
            total_models_query = select(func.count(ThreatModel.id)).where(
                ThreatModel.organization_id == organization.id
            )
            total_models_result = await session.execute(total_models_query)
            total_models = total_models_result.scalar() or 0
            
            user_models_query = select(func.count(ThreatModel.id)).where(
                and_(
                    ThreatModel.organization_id == organization.id,
                    ThreatModel.user_id == user.id
                )
            )
            user_models_result = await session.execute(user_models_query)
            user_models = user_models_result.scalar() or 0
            
            total_assessments_query = select(func.count(ThreatAssessment.id)).join(
                ThreatModel, ThreatAssessment.threat_model_id == ThreatModel.id
            ).where(ThreatModel.organization_id == organization.id)
            total_assessments_result = await session.execute(total_assessments_query)
            total_assessments = total_assessments_result.scalar() or 0
            
            # Recent activity (last 7 days)
            recent_date = datetime.utcnow() - timedelta(days=7)
            recent_models_query = select(func.count(ThreatModel.id)).where(
                and_(
                    ThreatModel.organization_id == organization.id,
                    ThreatModel.created_at >= recent_date
                )
            )
            recent_models_result = await session.execute(recent_models_query)
            recent_models = recent_models_result.scalar() or 0
            
            result = {
                "success": True,
                "dashboard": {
                    "organization": {
                        "id": organization.id,
                        "login": organization.login,
                        "name": organization.name
                    },
                    "statistics": {
                        "total_threat_models": total_models,
                        "user_threat_models": user_models,
                        "total_assessments": total_assessments,
                        "recent_models": recent_models
                    },
                    "quick_actions": [
                        {
                            "title": "Create New Threat Model",
                            "description": "Start a new threat modeling session",
                            "action": "create_model",
                            "icon": "🛡️"
                        },
                        {
                            "title": "Browse Threat Library",
                            "description": "Explore STRIDE/LINDDUN threats",
                            "action": "browse_library",
                            "icon": "📚"
                        },
                        {
                            "title": "AI Analysis",
                            "description": "Get AI-powered threat suggestions",
                            "action": "ai_analysis",
                            "icon": "🤖"
                        }
                    ]
                }
            }
            
            # Cache for 5 minutes
            await cache.set(cache_key, json.dumps(result, default=str), expire=300)
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting threat dashboard for {org_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")
