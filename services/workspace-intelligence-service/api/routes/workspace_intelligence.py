"""
API Routes for Workspace Intelligence & DevSecOps Maturity Analysis
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging

from database.config import db_manager
from core.workspace_analyzer import WorkspaceAnalyzer
from core.workspace_intelligence_db import WorkspaceIntelligenceDB
from core.github_service_client import github_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace-intelligence", tags=["Workspace Intelligence"])


@router.get("/health")
async def health_check():
    """Health check endpoint for workspace intelligence service"""
    return {
        "status": "healthy",
        "service": "workspace-intelligence-service"
    }


# Request/Response Models
class AnalyzeWorkspaceRequest(BaseModel):
    """Request to analyze workspace"""
    organization_name: str
    tree_data: List[Dict]
    repository_tree_id: str
    fetch_github_data: bool = False


class AnalyzeProjectRequest(BaseModel):
    """Request to analyze a specific project"""
    organization_name: str
    repository_tree_id: str
    project_id: str
    project_data: Dict
    fetch_github_data: bool = False


class GetAnalysisResponse(BaseModel):
    """Response with analysis results"""
    success: bool
    analysis: Optional[Dict] = None
    error: Optional[str] = None


@router.post("/analyze-workspace")
async def analyze_workspace(
    request: AnalyzeWorkspaceRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger organization-wide workspace analysis
    
    Analyzes all projects, detects centralized workflows,
    maps dependencies, and provides intelligence
    """
    try:
        logger.info(f"🚀 Workspace analysis request for org: {request.organization_name}")
        
        # Create analyzer with GitHub service client
        analyzer = WorkspaceAnalyzer(github_service_client)
        
        # Run analysis in background
        background_tasks.add_task(
            _run_workspace_analysis,
            analyzer,
            request.organization_name,
            request.tree_data,
            request.repository_tree_id,
            "system",  # No user context in microservice
            request.fetch_github_data
        )
        
        return {
            "success": True,
            "message": "Workspace analysis started",
            "status": "analyzing"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start workspace analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-project")
async def analyze_project(
    request: AnalyzeProjectRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger analysis for a specific project/folder
    """
    try:
        logger.info(f"📁 Project analysis request: {request.project_id}")
        
        analyzer = WorkspaceAnalyzer(github_service_client)
        
        background_tasks.add_task(
            _run_project_analysis,
            analyzer,
            request.organization_name,
            request.repository_tree_id,
            request.project_id,
            request.project_data,
            "system",  # No user context in microservice
            request.fetch_github_data
        )
        
        return {
            "success": True,
            "message": "Project analysis started",
            "project_id": request.project_id,
            "status": "analyzing"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start project analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{analysis_id}")
async def get_analysis(
    analysis_id: str
):
    """
    Get detailed analysis results by ID
    """
    try:
        async with db_manager.get_session() as session:
            result = await WorkspaceIntelligenceDB.get_analysis_with_details(session, analysis_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Convert SQLAlchemy model to dict
        analysis_dict = {
            'id': result.id,
            'project_name': result.project_name,
            'organization_name': result.organization_name,
            'status': result.status,
            'overall_maturity_score': result.overall_maturity_score,
            'maturity_level': result.maturity_level,
            'implementation_score': result.implementation_score,
            'build_deployment_score': result.build_deployment_score,
            'verification_score': result.verification_score,
            'information_gathering_score': result.information_gathering_score,
            'total_repositories': result.total_repositories,
            'total_workflows': result.total_workflows,
            'critical_findings': result.critical_findings,
            'high_findings': result.high_findings,
            'medium_findings': result.medium_findings,
            'low_findings': result.low_findings,
            'detected_practices': result.detected_practices or {},
            'analysis_config': result.analysis_config or {},
            'created_at': result.created_at.isoformat() if result.created_at else None,
            'completed_at': result.completed_at.isoformat() if result.completed_at else None
        }
        
        # For now, return simplified structure
        repositories = []
        
        return {
            "success": True,
            "analysis": analysis_dict,
            "repositories": repositories,
            "maturity_scores": {
                'overall': analysis_dict['overall_maturity_score'],
                'implementation': analysis_dict['implementation_score'],
                'build_deployment': analysis_dict['build_deployment_score'],
                'verification': analysis_dict['verification_score'],
                'information_gathering': analysis_dict['information_gathering_score']
            },
            "findings_summary": {
                'critical': analysis_dict['critical_findings'] or 0,
                'high': analysis_dict['high_findings'] or 0,
                'medium': analysis_dict['medium_findings'] or 0,
                'low': analysis_dict['low_findings'] or 0
            }
        }
        
        return {
            "success": True,
            "analysis": {
                "id": analysis_dict['id'],
                "project_name": analysis_dict['project_name'],
                "organization": analysis_dict['organization_name'],
                "status": analysis_dict['status'],
                "completed_at": analysis_dict['completed_at'],
                "maturity": {
                    "overall_score": analysis_dict['overall_maturity_score'],
                    "level": analysis_dict['maturity_level'],
                    "implementation_score": analysis_dict['implementation_score'],
                    "build_deployment_score": analysis_dict['build_deployment_score'],
                    "verification_score": analysis_dict['verification_score'],
                    "information_gathering_score": analysis_dict['information_gathering_score']
                },
                "statistics": {
                    "total_repositories": analysis_dict['total_repositories'],
                    "total_workflows": analysis_dict['total_workflows'],
                    "critical_findings": analysis_dict['critical_findings'],
                    "high_findings": analysis_dict['high_findings'],
                    "medium_findings": analysis_dict['medium_findings'],
                    "low_findings": analysis_dict['low_findings'],
                },
                "detected_practices": analysis_dict['detected_practices'],
                "findings_count": {
                    "critical": analysis_dict['critical_findings'] or 0,
                    "high": analysis_dict['high_findings'] or 0,
                    "medium": analysis_dict['medium_findings'] or 0,
                    "low": analysis_dict['low_findings'] or 0
                }
            },
            "repositories": repositories,
            "maturity_scores": {
                'overall': analysis_dict['overall_maturity_score'],
                'implementation': analysis_dict['implementation_score'],
                'build_deployment': analysis_dict['build_deployment_score'],
                'verification': analysis_dict['verification_score'],
                'information_gathering': analysis_dict['information_gathering_score']
            },
            "findings_summary": {
                'critical': analysis_dict['critical_findings'] or 0,
                'high': analysis_dict['high_findings'] or 0,
                'medium': analysis_dict['medium_findings'] or 0,
                'low': analysis_dict['low_findings'] or 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/latest")
async def get_latest_project_analysis(
    project_id: str
):
    """
    Get the latest analysis for a specific project
    """
    try:
        async with db_manager.get_session() as session:
            analysis = await WorkspaceIntelligenceDB.get_latest_analysis(session, project_id)
        
        if not analysis:
            return {
                "success": True,
                "analysis": None,
                "message": "No analysis found for this project"
            }
        
        return {
            "success": True,
            "analysis": {
                "id": analysis.id,
                "project_name": analysis.project_name,
                "status": analysis.status,
                "overall_maturity_score": analysis.overall_maturity_score,
                "maturity_level": analysis.maturity_level,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                "findings_summary": {
                    "critical": analysis.critical_findings,
                    "high": analysis.high_findings,
                    "medium": analysis.medium_findings,
                    "low": analysis.low_findings,
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get latest analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organization/{organization_name}")
async def get_organization_analyses(
    organization_name: str
):
    """
    Get all analyses for an organization
    """
    try:
        async with db_manager.get_session() as session:
            # Query all analyses for this organization
            from database.models import ProjectAnalysis
            stmt = select(ProjectAnalysis).where(
                ProjectAnalysis.organization_name == organization_name
            ).order_by(ProjectAnalysis.created_at.desc())
            
            result = await session.execute(stmt)
            analyses = result.scalars().all()
        
        if not analyses:
            return {
                "success": True,
                "analyses": [],
                "message": "No analyses found for this organization"
            }
        
        return {
            "success": True,
            "analyses": [
                {
                    "id": analysis.id,
                    "project_name": analysis.project_name,
                    "status": analysis.status,
                    "overall_maturity_score": analysis.overall_maturity_score,
                    "maturity_level": analysis.maturity_level,
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                    "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                }
                for analysis in analyses
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get organization analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/finding/{finding_id}")
async def update_finding_status(
    finding_id: str,
    status: str
):
    """
    Update finding status (acknowledge, mark as false positive, resolve, etc.)
    """
    try:
        from database.models import RepositoryFinding
        from datetime import datetime
        from sqlalchemy import select
        
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(RepositoryFinding).filter(RepositoryFinding.id == finding_id)
            )
            finding = result.scalar_one_or_none()
            
            if not finding:
                raise HTTPException(status_code=404, detail="Finding not found")
            
            # Update status
            finding.status = status
            finding.acknowledged_by = current_user
            finding.acknowledged_at = datetime.utcnow()
            
            if status == 'resolved':
                finding.resolved_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "success": True,
                "message": f"Finding status updated to: {status}",
                "finding_id": finding_id
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update finding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task functions
async def _run_workspace_analysis(
    analyzer: WorkspaceAnalyzer,
    org_name: str,
    tree_data: List[Dict],
    tree_id: str,
    user_id: str,
    fetch_github_data: bool
):
    """Background task to run workspace analysis"""
    from core.event_bus import event_bus
    import time
    
    analysis_id = None
    start_time = time.time()
    
    try:
        # Publish analysis started event
        await event_bus.publish_workspace_analysis_started(
            analysis_id=None,  # Will be assigned after save
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id
        )
        
        # Run analysis
        result = await analyzer.analyze_workspace(
            org_name,
            tree_data,
            fetch_github_data
        )
        
        # Save results for each project
        async with db_manager.get_session() as session:
            for project_analysis in result.get('project_analyses', []):
                saved_analysis = await WorkspaceIntelligenceDB.save_project_analysis(
                    session,
                    tree_id,
                    project_analysis['project_id'],
                    project_analysis['project_name'],
                    org_name,
                    user_id,
                    project_analysis
                )
                
                if not analysis_id:
                    analysis_id = saved_analysis.id
                
                # Publish project analysis completed event
                await event_bus.publish_project_analysis_completed(
                    analysis_id=saved_analysis.id,
                    project_id=project_analysis['project_id'],
                    project_name=project_analysis['project_name'],
                    organization_name=org_name,
                    maturity_scores={
                        'overall': saved_analysis.overall_maturity_score or 0,
                        'implementation': saved_analysis.implementation_score or 0,
                        'build_deployment': saved_analysis.build_deployment_score or 0,
                        'verification': saved_analysis.verification_score or 0,
                        'information_gathering': saved_analysis.information_gathering_score or 0
                    }
                )
        
        duration = time.time() - start_time
        
        # Publish analysis completed event
        await event_bus.publish_workspace_analysis_completed(
            analysis_id=analysis_id,
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id,
            duration_seconds=duration,
            maturity_score=result.get('organization_metrics', {}).get('overall_maturity', 0),
            total_repositories=result.get('summary', {}).get('total_repositories', 0),
            total_workflows=result.get('summary', {}).get('total_workflows', 0),
            findings_count=result.get('summary', {}).get('findings_count', {})
        )
        
        logger.info(f"✅ Workspace analysis completed for {org_name}")
        
    except Exception as e:
        logger.error(f"❌ Background workspace analysis failed: {str(e)}", exc_info=True)
        
        # Publish analysis failed event
        await event_bus.publish_workspace_analysis_failed(
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id,
            error_message=str(e)
        )


async def _run_project_analysis(
    analyzer: WorkspaceAnalyzer,
    org_name: str,
    tree_id: str,
    project_id: str,
    project_data: Dict,
    user_id: str,
    fetch_github_data: bool
):
    """Background task to run project analysis"""
    from core.event_bus import event_bus
    import time
    
    project_name = project_data.get('name', project_id)
    start_time = time.time()
    
    try:
        # Publish analysis started event
        await event_bus.publish_workspace_analysis_started(
            analysis_id=None,
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id
        )
        
        # Wrap project in a list for analyze_workspace
        tree_data = [project_data]
        
        result = await analyzer.analyze_workspace(
            org_name,
            tree_data,
            fetch_github_data
        )
        
        # Save results
        async with db_manager.get_session() as session:
            if result.get('project_analyses'):
                project_analysis = result['project_analyses'][0]
                
                saved_analysis = await WorkspaceIntelligenceDB.save_project_analysis(
                    session,
                    tree_id,
                    project_id,
                    project_analysis['project_name'],
                    org_name,
                    user_id,
                    project_analysis
                )
                
                # Publish project analysis completed event
                await event_bus.publish_project_analysis_completed(
                    analysis_id=saved_analysis.id,
                    project_id=project_id,
                    project_name=project_analysis['project_name'],
                    organization_name=org_name,
                    maturity_scores={
                        'overall': saved_analysis.overall_maturity_score or 0,
                        'implementation': saved_analysis.implementation_score or 0,
                        'build_deployment': saved_analysis.build_deployment_score or 0,
                        'verification': saved_analysis.verification_score or 0,
                        'information_gathering': saved_analysis.information_gathering_score or 0
                    }
                )
        
        duration = time.time() - start_time
        
        # Publish analysis completed event
        await event_bus.publish_workspace_analysis_completed(
            analysis_id=saved_analysis.id if result.get('project_analyses') else None,
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id,
            duration_seconds=duration,
            maturity_score=result.get('organization_metrics', {}).get('overall_maturity', 0),
            total_repositories=1,
            total_workflows=result.get('summary', {}).get('total_workflows', 0),
            findings_count=result.get('summary', {}).get('findings_count', {})
        )
        
        logger.info(f"✅ Project analysis completed for {project_id}")
        
    except Exception as e:
        logger.error(f"❌ Background project analysis failed: {str(e)}", exc_info=True)
        
        # Publish analysis failed event
        await event_bus.publish_workspace_analysis_failed(
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id,
            error_message=str(e)
        )

