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
from core.github_client import GitHubClient
from core.security import get_current_user
from database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace-intelligence", tags=["Workspace Intelligence"])


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
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """
    Trigger organization-wide workspace analysis
    
    Analyzes all projects, detects centralized workflows,
    maps dependencies, and provides intelligence
    """
    try:
        logger.info(f"🚀 Workspace analysis request for org: {request.organization_name}")
        
        # Create analyzer (you'll need to pass github_client)
        github_client = GitHubClient()  # Initialize appropriately
        analyzer = WorkspaceAnalyzer(github_client)
        
        # Run analysis in background
        background_tasks.add_task(
            _run_workspace_analysis,
            analyzer,
            request.organization_name,
            request.tree_data,
            request.repository_tree_id,
            current_user,
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
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """
    Trigger analysis for a specific project/folder
    """
    try:
        logger.info(f"📁 Project analysis request: {request.project_id}")
        
        github_client = GitHubClient()
        analyzer = WorkspaceAnalyzer(github_client)
        
        background_tasks.add_task(
            _run_project_analysis,
            analyzer,
            request.organization_name,
            request.repository_tree_id,
            request.project_id,
            request.project_data,
            current_user,
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
    analysis_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get detailed analysis results by ID
    """
    try:
        async with db_manager.get_session() as session:
            result = await WorkspaceIntelligenceDB.get_analysis_with_details(session, analysis_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis = result['analysis']
        findings = result['findings']
        scores = result['maturity_scores']
        
        # Group findings by repository to construct repositories array
        repo_map = {}
        for f in findings:
            repo_name = f.repository_name
            if repo_name not in repo_map:
                repo_map[repo_name] = {
                    'repository_name': repo_name,
                    'has_workflows': f.finding_type != 'no_cicd_workflows',
                    'findings': [],
                    'findings_count': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
                }
            
            repo_map[repo_name]['findings'].append({
                "id": f.id,
                "type": f.finding_type,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "recommendation": f.recommendation,
                "status": f.status,
            })
            
            # Count by severity
            severity = f.severity.lower()
            if severity in repo_map[repo_name]['findings_count']:
                repo_map[repo_name]['findings_count'][severity] += 1
        
        repositories = list(repo_map.values())
        
        return {
            "success": True,
            "analysis": {
                "id": analysis.id,
                "project_name": analysis.project_name,
                "organization": analysis.organization_name,
                "status": analysis.status,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                "maturity": {
                    "overall_score": analysis.overall_maturity_score,
                    "level": analysis.maturity_level,
                    "implementation_score": analysis.implementation_score,
                    "build_deployment_score": analysis.build_deployment_score,
                    "verification_score": analysis.verification_score,
                },
                "statistics": {
                    "total_repositories": analysis.total_repositories,
                    "total_workflows": analysis.total_workflows,
                    "critical_findings": analysis.critical_findings,
                    "high_findings": analysis.high_findings,
                    "medium_findings": analysis.medium_findings,
                    "low_findings": analysis.low_findings,
                },
                "detected_practices": analysis.detected_practices or {},  # Include detected practices
                "findings_count": {  # Alias for easier UI access
                    "critical": analysis.critical_findings,
                    "high": analysis.high_findings,
                    "medium": analysis.medium_findings,
                    "low": analysis.low_findings,
                },
                "repositories": repositories,  # Grouped repository data
                "findings": [
                    {
                        "id": f.id,
                        "repository": f.repository_name,
                        "type": f.finding_type,
                        "severity": f.severity,
                        "title": f.title,
                        "description": f.description,
                        "recommendation": f.recommendation,
                        "status": f.status,
                    }
                    for f in findings
                ],
                "maturity_scores": [
                    {
                        "dimension": s.dimension,
                        "sub_dimension": s.sub_dimension,
                        "score": s.score,
                        "level": s.level,
                        "practices_found": s.practices_found,
                    }
                    for s in scores
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/latest")
async def get_latest_project_analysis(
    project_id: str,
    current_user: str = Depends(get_current_user)
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
    organization_name: str,
    current_user: str = Depends(get_current_user)
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
    status: str,
    current_user: str = Depends(get_current_user)
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
    try:
        # Run analysis
        result = await analyzer.analyze_workspace(
            org_name,
            tree_data,
            fetch_github_data
        )
        
        # Save results for each project
        async with db_manager.get_session() as session:
            for project_analysis in result.get('project_analyses', []):
                await WorkspaceIntelligenceDB.save_project_analysis(
                    session,
                    tree_id,
                    project_analysis['project_id'],
                    project_analysis['project_name'],
                    org_name,
                    user_id,
                    project_analysis
                )
        
        logger.info(f"✅ Workspace analysis completed for {org_name}")
        
    except Exception as e:
        logger.error(f"❌ Background workspace analysis failed: {str(e)}", exc_info=True)


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
    try:
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
                
                await WorkspaceIntelligenceDB.save_project_analysis(
                    session,
                    tree_id,
                    project_id,
                    project_analysis['project_name'],
                    org_name,
                    user_id,
                    project_analysis
                )
        
        logger.info(f"✅ Project analysis completed for {project_id}")
        
    except Exception as e:
        logger.error(f"❌ Background project analysis failed: {str(e)}", exc_info=True)
