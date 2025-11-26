"""
Threat Modeling API Routes
Main routes for threat model CRUD, analysis, and document processing
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from sqlalchemy import select, func
from typing import List
from datetime import datetime
import logging
import time

from database import db_manager, ThreatModel, AIAnalysisHistory, ThreatLibrary, User
from app.models import (
    ThreatModelCreate,
    ThreatModelUpdate,
    ThreatModelResponse,
    ComprehensiveAnalysisRequest,
    AnalysisSaveRequest,
    HealthResponse
)
from app.services import ThreatAnalysisService
from app.core import get_current_user, document_processor, event_bus

router = APIRouter(prefix="/api/v1", tags=["threat-modeling"])
logger = logging.getLogger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def resolve_user_uuid(auth_user_id: str, session) -> str:
    """Resolve Auth0 user ID to internal UUID"""
    result = await session.execute(
        select(User.id).where(User.auth_user_id == auth_user_id)
    )
    user_uuid = result.scalar()
    
    if not user_uuid:
        logger.warning(f"⚠️ No UUID found for auth_user_id: {auth_user_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"User not found in database. Please login to backend first."
        )
    
    logger.info(f"✅ Resolved {auth_user_id} → {user_uuid}")
    return user_uuid


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Service health check"""
    db_healthy = await db_manager.health_check()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "threat-modeling-service",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_healthy else "disconnected"
    }


@router.get("/methodologies")
async def get_methodologies():
    """
    Get available threat modeling methodologies
    Returns STRIDE, LINDDUN, and CIA Triad configurations
    """
    methodologies = {
        "STRIDE": {
            "name": "STRIDE",
            "description": "Microsoft STRIDE threat modeling methodology",
            "categories": ["Spoofing", "Tampering", "Repudiation", "Information Disclosure", "Denial of Service", "Elevation of Privilege"],
            "focus": "Security threats across identity, data, and access control"
        },
        "LINDDUN": {
            "name": "LINDDUN",
            "description": "LINDDUN privacy threat modeling methodology",
            "categories": ["Linkability", "Identifiability", "Non-repudiation", "Detectability", "Disclosure of Information", "Unawareness", "Non-compliance"],
            "focus": "Privacy threats and data protection concerns"
        },
        "CIA": {
            "name": "CIA Triad",
            "description": "Confidentiality, Integrity, Availability security model",
            "categories": ["Confidentiality Breach", "Integrity Violation", "Availability Disruption"],
            "focus": "Core information security principles"
        }
    }
    
    return {
        "success": True,
        "methodologies": methodologies,
        "default": "STRIDE"
    }


# =============================================================================
# THREAT MODELS CRUD
# =============================================================================

@router.post("/models", response_model=ThreatModelResponse)
async def create_threat_model(
    request: ThreatModelCreate,
    current_user: str = Depends(get_current_user)
):
    """Create new threat model"""
    try:
        async with db_manager.get_session() as session:
            # Resolve Auth0 ID to internal UUID
            user_uuid = await resolve_user_uuid(current_user, session)
            
            new_model = ThreatModel(
                name=request.name,
                description=request.description,
                methodology=request.methodology,
                status="draft",
                organization_id=request.organization_id,
                repository_id=request.repository_id,
                user_id=user_uuid,
                canvas_data=request.canvas_data or {
                    "elements": [],
                    "connections": [],
                    "metadata": {"zoom": 1.0, "panX": 0, "panY": 0}
                },
                created_at=datetime.utcnow()
            )
            
            session.add(new_model)
            await session.commit()
            await session.refresh(new_model)
            
            logger.info(f"✅ Created threat model: {new_model.id} for user UUID {user_uuid}")
            
            # Publish event
            await event_bus.publish_model_created(
                model_id=new_model.id,
                user_id=user_uuid,
                organization_id=new_model.organization_id,
                name=new_model.name
            )
            
            return ThreatModelResponse(
                id=new_model.id,
                name=new_model.name,
                description=new_model.description,
                methodology=new_model.methodology,
                status=new_model.status,
                canvas_data=new_model.canvas_data,
                organization_id=new_model.organization_id,
                repository_id=new_model.repository_id,
                user_id=new_model.user_id,
                created_at=new_model.created_at.isoformat(),
                updated_at=new_model.updated_at.isoformat() if new_model.updated_at else None,
                document_status=new_model.document_status,
                document_file_name=new_model.document_file_name
            )
    except Exception as e:
        logger.error(f"Error creating threat model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=List[ThreatModelResponse])
async def list_threat_models(
    current_user: str = Depends(get_current_user),
    organization_id: str = Query(None)
):
    """List threat models for user"""
    try:
        logger.info(f"🔍 Querying threat models for user: {current_user}, org: {organization_id}")
        
        async with db_manager.get_session() as session:
            # Resolve Auth0 ID to internal UUID
            user_uuid = await resolve_user_uuid(current_user, session)
            
            query = select(ThreatModel).where(ThreatModel.user_id == user_uuid)
            
            if organization_id:
                query = query.where(ThreatModel.organization_id == organization_id)
            
            query = query.order_by(ThreatModel.created_at.desc())
            
            result = await session.execute(query)
            models = result.scalars().all()
            
            logger.info(f"📊 Found {len(models)} threat models for user UUID {user_uuid}")
            
            # Debug: Log first model if exists
            if models:
                logger.info(f"🔍 First model: id={models[0].id}, name={models[0].name}, user_id={models[0].user_id}")
            
            return [
                ThreatModelResponse(
                    id=m.id,
                    name=m.name,
                    description=m.description,
                    methodology=m.methodology,
                    status=m.status,
                    canvas_data=m.canvas_data,
                    organization_id=m.organization_id,
                    repository_id=m.repository_id,
                    user_id=m.user_id,
                    created_at=m.created_at.isoformat(),
                    updated_at=m.updated_at.isoformat() if m.updated_at else None,
                    document_status=m.document_status,
                    document_file_name=m.document_file_name
                )
                for m in models
            ]
    except Exception as e:
        logger.error(f"Error listing threat models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_threat_model(model_id: str):
    """Get specific threat model"""
    try:
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
                    "metadata": {"zoom": 1.0, "panX": 0, "panY": 0}
                },
                "organization_id": model.organization_id,
                "repository_id": model.repository_id,
                "user_id": model.user_id,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None,
                "document_status": model.document_status,
                "document_file_name": model.document_file_name,
                "document_analysis": model.document_analysis
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching threat model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/models/{model_id}")
async def update_threat_model(model_id: str, request: ThreatModelUpdate):
    """Update threat model"""
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            # Update fields
            update_data = request.dict(exclude_unset=True)
            
            # Handle datetime conversion
            if 'last_ai_analysis' in update_data and update_data['last_ai_analysis']:
                if isinstance(update_data['last_ai_analysis'], str):
                    try:
                        dt = datetime.fromisoformat(
                            update_data['last_ai_analysis'].replace('Z', '+00:00')
                        )
                        update_data['last_ai_analysis'] = dt.replace(tzinfo=None)
                    except ValueError:
                        update_data['last_ai_analysis'] = datetime.utcnow()
            
            for field, value in update_data.items():
                setattr(model, field, value)
            
            model.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(model)
            
            # Publish event
            await event_bus.publish_model_updated(
                model_id=model.id,
                user_id=model.user_id,
                organization_id=model.organization_id,
                name=model.name
            )
            
            return {
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "methodology": model.methodology,
                "status": model.status,
                "canvas_data": model.canvas_data,
                "updated_at": model.updated_at.isoformat(),
                "ai_analysis": model.ai_analysis,
                "last_ai_analysis": model.last_ai_analysis.isoformat() if model.last_ai_analysis else None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating threat model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_id}")
async def delete_threat_model(model_id: str):
    """Delete threat model"""
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            # Store info before deletion
            model_info = {
                "id": model.id,
                "user_id": model.user_id,
                "organization_id": model.organization_id,
                "name": model.name
            }
            
            await session.delete(model)
            await session.commit()
            
            # Publish event
            await event_bus.publish_model_deleted(
                model_id=model_info["id"],
                user_id=model_info["user_id"],
                organization_id=model_info["organization_id"],
                name=model_info["name"]
            )
            
            return {"message": "Threat model deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting threat model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# THREAT ANALYSIS
# =============================================================================

@router.post("/models/{model_id}/comprehensive-analysis")
async def perform_comprehensive_analysis(
    model_id: str,
    request: ComprehensiveAnalysisRequest
):
    """Perform comprehensive AI analysis"""
    try:
        logger.info(f"🧠 Starting comprehensive analysis for model: {model_id}")
        
        # Get threat model
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            threat_model = result.scalars().first()
            
            if not threat_model:
                raise HTTPException(status_code=404, detail="Threat model not found")
        
        # Perform analysis
        analysis_result = await ThreatAnalysisService.analyze_comprehensive(
            model_id=model_id,
            canvas_data=request.canvas_data,
            metadata=request.model_metadata,
            document_context=request.document_context
        )
        
        logger.info(f"✅ Comprehensive analysis complete for model: {model_id}")
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}/analyses")
async def get_analysis_history(model_id: str):
    """Get analysis history"""
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(AIAnalysisHistory)
                .where(AIAnalysisHistory.threat_model_id == model_id)
                .order_by(AIAnalysisHistory.created_at.desc())
            )
            history_records = result.scalars().all()
            
            history = []
            for record in history_records:
                analysis_dict = record.analysis_data.copy() if record.analysis_data else {}
                analysis_dict.update({
                    "id": record.id,
                    "timestamp": record.created_at.isoformat() if record.created_at else datetime.utcnow().isoformat(),
                    "methodology": record.methodology,
                    "analysis_type": record.analysis_type,
                    "diagram_elements_count": record.diagram_elements_count,
                    "diagram_connections_count": record.diagram_connections_count,
                    "has_document": record.had_document,
                    "has_diagram": record.had_diagram,
                    "status": record.status
                })
                history.append(analysis_dict)
            
            logger.info(f"📚 Retrieved {len(history)} analyses for model {model_id}")
            return history
    except Exception as e:
        logger.error(f"Error getting analysis history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/analyses")
async def save_analysis(model_id: str, request: AnalysisSaveRequest):
    """Save analysis to history"""
    try:
        analysis_data = request.analysis_data
        
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            # Update model with latest analysis
            model.ai_analysis = analysis_data
            timestamp_str = analysis_data.get("timestamp", datetime.utcnow().isoformat())
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            model.last_ai_analysis = timestamp.replace(tzinfo=None)
            model.updated_at = datetime.utcnow()
            
            # Save to history
            history_record = AIAnalysisHistory(
                id=analysis_data.get("id", f"analysis-{int(time.time())}-{model_id[:8]}"),
                threat_model_id=model_id,
                user_id=model.user_id,
                analysis_type=analysis_data.get("analysis_type", "comprehensive"),
                methodology=analysis_data.get("methodology", "STRIDE"),
                analysis_data=analysis_data,
                structured_analysis=analysis_data.get("structured_analysis"),
                diagram_elements_count=analysis_data.get("diagram_elements_count", 0),
                diagram_connections_count=analysis_data.get("diagram_connections_count", 0),
                had_document=analysis_data.get("has_document", False),
                had_diagram=analysis_data.get("has_diagram", False),
                status="completed",
                created_at=timestamp.replace(tzinfo=None)
            )
            session.add(history_record)
            
            await session.commit()
            
            logger.info(f"✅ Saved analysis {analysis_data.get('id')} for model {model_id}")
            
            return {
                "success": True,
                "id": analysis_data.get("id"),
                "timestamp": analysis_data.get("timestamp"),
                "message": "Analysis saved successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_id}/analysis/{analysis_id}")
async def delete_analysis(model_id: str, analysis_id: str):
    """Delete specific analysis"""
    try:
        async with db_manager.get_session() as session:
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
            
            logger.info(f"✅ Deleted analysis {analysis_id}")
            return {"success": True, "message": "Analysis deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DOCUMENT PROCESSING
# =============================================================================

@router.post("/models/{model_id}/upload-document")
async def upload_document(model_id: str, file: UploadFile = File(...)):
    """Upload and process document for enhanced analysis"""
    try:
        logger.info(f"📄 Processing document upload: {file.filename}")
        
        # Update model status
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            if not model:
                raise HTTPException(status_code=404, detail="Threat model not found")
            
            model.document_status = "processing"
            await session.commit()
        
        # Process document
        file_content = await file.read()
        processing_result = await document_processor.process_document(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        if not processing_result["success"]:
            async with db_manager.get_session() as session:
                model.document_status = "failed"
                await session.commit()
            raise HTTPException(status_code=400, detail=processing_result["error"])
        
        # Update model with results
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatModel).where(ThreatModel.id == model_id)
            )
            model = result.scalars().first()
            
            model.document_analysis = {
                "processing_result": processing_result,
                "extracted_text": processing_result["text_content"],
                "analysis": processing_result["analysis"],
                "metadata": {
                    "word_count": processing_result["word_count"],
                    "file_format": processing_result["file_format"]
                }
            }
            model.document_status = "completed"
            model.document_file_name = file.filename
            model.document_processed_at = datetime.utcnow()
            
            await session.commit()
        
        logger.info(f"✅ Document processed: {file.filename}")
        
        return {
            "success": True,
            "message": "Document processed successfully",
            "document_info": {
                "filename": file.filename,
                "file_size": processing_result["file_size"],
                "word_count": processing_result["word_count"]
            },
            "analysis_preview": {
                "technologies_found": len(processing_result["analysis"]["technologies"]),
                "security_concerns": processing_result["analysis"]["security_concerns"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# THREAT LIBRARY
# =============================================================================

@router.get("/library")
async def get_threat_library():
    """Get threat library patterns"""
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ThreatLibrary).where(ThreatLibrary.is_built_in == True)
            )
            threats = result.scalars().all()
            
            return [
                {
                    "id": t.id,
                    "methodology": t.methodology,
                    "category": t.category,
                    "threat_name": t.threat_name,
                    "threat_description": t.threat_description,
                    "applicable_elements": t.applicable_elements,
                    "common_mitigations": t.common_mitigations
                }
                for t in threats
            ]
    except Exception as e:
        logger.error(f"Error fetching threat library: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard overview"""
    try:
        async with db_manager.get_session() as session:
            total_models = await session.execute(select(func.count(ThreatModel.id)))
            total_count = total_models.scalar() or 0
            
            recent_query = select(ThreatModel).order_by(ThreatModel.created_at.desc()).limit(5)
            recent_result = await session.execute(recent_query)
            recent_models = recent_result.scalars().all()
            
            recent_activity = [
                {
                    "id": m.id,
                    "name": m.name,
                    "status": m.status,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in recent_models
            ]
            
            return {
                "total_models": total_count,
                "recent_activity": recent_activity,
                "status": "success"
            }
    except Exception as e:
        logger.error(f"Error fetching dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
