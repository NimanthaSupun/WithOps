"""
API Routes for Workspace Intelligence & DevSecOps Maturity Analysis
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging

from database.config import db_manager
from core.workspace_analyzer import WorkspaceAnalyzer
from core.workspace_intelligence_db import WorkspaceIntelligenceDB
from core.github_service_client import github_service_client
from core.security import get_current_user, security

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


class AnalyzeFolderRequest(BaseModel):
    """Request to analyze a specific folder"""
    organization_name: str
    tree_data: List[Dict]
    repository_tree_id: str
    folder_id: str
    folder_path: str
    include_subfolders: bool = True
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
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
):
    """
    Trigger organization-wide workspace analysis
    
    Analyzes all projects, detects centralized workflows,
    maps dependencies, and provides intelligence
    """
    try:
        # Extract user_id from JWT token
        user_id = await get_current_user(credentials)
        if not user_id:
            user_id = "system"  # Fallback for backward compatibility
        
        logger.info(f"🚀 Workspace analysis request for org: {request.organization_name}, user: {user_id}")
        
        # Create analyzer with GitHub service client
        analyzer = WorkspaceAnalyzer(github_service_client)
        
        # Run analysis in background
        background_tasks.add_task(
            _run_workspace_analysis,
            analyzer,
            request.organization_name,
            request.tree_data,
            request.repository_tree_id,
            user_id,
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


@router.post("/analyze-workspace-unified")
async def analyze_workspace_unified(
    request: AnalyzeWorkspaceRequest,
    background_tasks: BackgroundTasks,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
):
    """
    Trigger unified workspace analysis - creates ONE analysis with project breakdowns
    
    This analyzes the entire organization structure and saves it as a single
    unified analysis record with embedded project breakdowns for drill-down.
    Recommended for executive dashboards and org-wide visibility.
    """
    try:
        # Extract user_id from JWT token
        user_id = await get_current_user(credentials)
        if not user_id:
            user_id = "system"  # Fallback for backward compatibility
        
        logger.info(f"🚀 Unified workspace analysis request for org: {request.organization_name}, user: {user_id}")
        
        # Create analyzer with GitHub service client
        analyzer = WorkspaceAnalyzer(github_service_client)
        
        # Run unified analysis in background
        background_tasks.add_task(
            _run_unified_workspace_analysis,
            analyzer,
            request.organization_name,
            request.tree_data,
            request.repository_tree_id,
            user_id,
            request.fetch_github_data
        )
        
        return {
            "success": True,
            "message": "Unified workspace analysis started",
            "analysis_mode": "unified",
            "status": "analyzing"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start unified workspace analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-folder")
async def analyze_folder(
    request: AnalyzeFolderRequest,
    background_tasks: BackgroundTasks,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
):
    """
    Trigger folder-specific analysis (subset of repositories)
    
    Analyzes only repositories within a specific folder,
    allowing team-level or product-level maturity assessment
    """
    try:
        # Extract user_id from JWT token
        user_id = await get_current_user(credentials)
        if not user_id:
            user_id = "system"  # Fallback for backward compatibility
        
        logger.info(f"📁 Folder analysis request for: {request.folder_path} in org: {request.organization_name}, user: {user_id}")
        
        # Filter tree_data to only include the specified folder
        filtered_tree_data = _filter_tree_by_folder(
            request.tree_data,
            request.folder_path,
            request.include_subfolders
        )
        
        if not filtered_tree_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Folder '{request.folder_path}' not found or contains no repositories"
            )
        
        # Count repositories in scope
        repo_count = _count_repositories_in_tree(filtered_tree_data)
        logger.info(f"📊 Found {repo_count} repositories in folder '{request.folder_path}'")
        
        # Create analyzer with GitHub service client
        analyzer = WorkspaceAnalyzer(github_service_client)
        
        # Run analysis in background with folder scope
        background_tasks.add_task(
            _run_folder_analysis,
            analyzer,
            request.organization_name,
            filtered_tree_data,
            request.repository_tree_id,
            request.folder_id,
            request.folder_path,
            user_id,
            request.fetch_github_data
        )
        
        return {
            "success": True,
            "message": f"Folder analysis started for '{request.folder_path}'",
            "status": "analyzing",
            "folder_path": request.folder_path,
            "repositories_count": repo_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to start folder analysis: {str(e)}")
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
        
        logger.info(f"🔍 Retrieved analysis {analysis_id} for project {result.project_name}")
        
        # Convert SQLAlchemy model to dict
        analysis_dict = {
            'id': result.id,
            'project_name': result.project_name,
            'organization_name': result.organization_name,
            'status': result.status,
            'analysis_scope': result.analysis_scope,  # unified, folder, or organization
            'folder_path': result.folder_path,
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
            'analysis_data': result.analysis_data or {},  # Include full analysis data for project_analyses
            'created_at': result.created_at.isoformat() if result.created_at else None,
            'completed_at': result.completed_at.isoformat() if result.completed_at else None
        }
        
        # Extract repositories and findings from analysis_data JSON field
        analysis_data = result.analysis_data or {}
        
        logger.info(f"📦 Analysis data keys: {list(analysis_data.keys()) if analysis_data else 'None'}")
        logger.info(f"📦 Analysis data type: {type(analysis_data)}")
        logger.info(f"📦 Analysis scope: {result.analysis_scope}")
        
        # Extract repositories and findings from project analysis structure
        repositories = []
        findings = []
        
        # Check if this is a unified analysis (contains project_analyses array)
        if result.analysis_scope == 'unified' and 'project_analyses' in analysis_data:
            logger.info(f"🌐 Processing unified analysis with {len(analysis_data['project_analyses'])} projects")
            
            # Collect all repositories from all projects
            for project in analysis_data['project_analyses']:
                project_repos = project.get('repositories', [])
                # Add project_name to each repository for grouping
                for repo in project_repos:
                    repo['project_name'] = project.get('project_name', 'Unknown')
                repositories.extend(project_repos)
                
                # Collect findings from all repositories in this project
                for repo in project_repos:
                    repo_findings = repo.get('findings', [])
                    findings.extend(repo_findings)
            
            logger.info(f"📊 Found {len(repositories)} total repositories across all projects")
            logger.info(f"🔍 Found {len(findings)} total findings across all repositories")
        
        # The analysis_data contains the project analysis with 'repositories' array
        elif 'repositories' in analysis_data:
            repositories = analysis_data['repositories']
            logger.info(f"📊 Found {len(repositories)} repositories in analysis_data")
            
            # Collect all findings from all repositories
            for repo in repositories:
                repo_findings = repo.get('findings', [])
                findings.extend(repo_findings)
                logger.info(f"📋 Repository '{repo.get('repository_name')}' has {len(repo_findings)} findings")
        else:
            logger.warning("⚠️ No 'repositories' key found in analysis_data")
        
        logger.info(f"✅ Returning {len(repositories)} repositories and {len(findings)} findings")
        
        return {
            "success": True,
            "analysis": analysis_dict,
            "repositories": repositories,
            "findings": findings,
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
                    "analysis_scope": analysis.analysis_scope,
                    "folder_path": analysis.folder_path,
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                    "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                    "total_repositories": analysis.total_repositories or 0,
                    "findings_count": (
                        (analysis.critical_findings or 0) +
                        (analysis.high_findings or 0) +
                        (analysis.medium_findings or 0) +
                        (analysis.low_findings or 0)
                    ),
                    "maturity_score": analysis.overall_maturity_score or 0
                }
                for analysis in analyses
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get organization analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folder/{folder_path:path}/analyses")
async def get_folder_analyses(
    folder_path: str
):
    """
    Get all analyses for a specific folder
    """
    try:
        async with db_manager.get_session() as session:
            from database.models import ProjectAnalysis
            stmt = select(ProjectAnalysis).where(
                ProjectAnalysis.folder_path == folder_path
            ).order_by(ProjectAnalysis.created_at.desc())
            
            result = await session.execute(stmt)
            analyses = result.scalars().all()
        
        if not analyses:
            return {
                "success": True,
                "analyses": [],
                "message": f"No analyses found for folder '{folder_path}'"
            }
        
        return {
            "success": True,
            "analyses": [
                {
                    "id": analysis.id,
                    "project_name": analysis.project_name,
                    "folder_path": analysis.folder_path,
                    "status": analysis.status,
                    "overall_maturity_score": analysis.overall_maturity_score,
                    "maturity_level": analysis.maturity_level,
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                    "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                    "total_repositories": analysis.total_repositories or 0,
                    "repositories_in_scope": analysis.repositories_in_scope or [],
                    "findings_count": (
                        (analysis.critical_findings or 0) +
                        (analysis.high_findings or 0) +
                        (analysis.medium_findings or 0) +
                        (analysis.low_findings or 0)
                    ),
                    "maturity_score": analysis.overall_maturity_score or 0
                }
                for analysis in analyses
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get folder analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folder/{folder_path:path}/latest")
async def get_latest_folder_analysis(
    folder_path: str
):
    """
    Get the latest analysis for a specific folder
    """
    try:
        async with db_manager.get_session() as session:
            from database.models import ProjectAnalysis
            stmt = select(ProjectAnalysis).where(
                ProjectAnalysis.folder_path == folder_path
            ).order_by(ProjectAnalysis.created_at.desc()).limit(1)
            
            result = await session.execute(stmt)
            analysis = result.scalar_one_or_none()
        
        if not analysis:
            return {
                "success": True,
                "analysis": None,
                "message": f"No analysis found for folder '{folder_path}'"
            }
        
        return {
            "success": True,
            "analysis": {
                "id": analysis.id,
                "project_name": analysis.project_name,
                "folder_path": analysis.folder_path,
                "status": analysis.status,
                "overall_maturity_score": analysis.overall_maturity_score,
                "maturity_level": analysis.maturity_level,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                "total_repositories": analysis.total_repositories or 0,
                "repositories_in_scope": analysis.repositories_in_scope or [],
                "findings_summary": {
                    "critical": analysis.critical_findings or 0,
                    "high": analysis.high_findings or 0,
                    "medium": analysis.medium_findings or 0,
                    "low": analysis.low_findings or 0
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get latest folder analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-folders")
async def compare_folders(
    folder_paths: List[str]
):
    """
    Compare maturity scores across multiple folders
    """
    try:
        if not folder_paths or len(folder_paths) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 folder paths required for comparison"
            )
        
        async with db_manager.get_session() as session:
            from database.models import ProjectAnalysis
            
            comparisons = []
            for folder_path in folder_paths:
                # Get latest analysis for each folder
                stmt = select(ProjectAnalysis).where(
                    ProjectAnalysis.folder_path == folder_path
                ).order_by(ProjectAnalysis.created_at.desc()).limit(1)
                
                result = await session.execute(stmt)
                analysis = result.scalar_one_or_none()
                
                if analysis:
                    comparisons.append({
                        "folder_path": folder_path,
                        "analysis_id": analysis.id,
                        "maturity_score": analysis.overall_maturity_score or 0,
                        "maturity_level": analysis.maturity_level,
                        "total_repositories": analysis.total_repositories or 0,
                        "total_findings": (
                            (analysis.critical_findings or 0) +
                            (analysis.high_findings or 0) +
                            (analysis.medium_findings or 0) +
                            (analysis.low_findings or 0)
                        ),
                        "critical_findings": analysis.critical_findings or 0,
                        "analyzed_at": analysis.created_at.isoformat() if analysis.created_at else None,
                        "dsomm_scores": {
                            "implementation": analysis.implementation_score or 0,
                            "build_deployment": analysis.build_deployment_score or 0,
                            "verification": analysis.verification_score or 0,
                            "information_gathering": analysis.information_gathering_score or 0
                        }
                    })
                else:
                    comparisons.append({
                        "folder_path": folder_path,
                        "analysis_id": None,
                        "maturity_score": 0,
                        "maturity_level": "Not Analyzed",
                        "total_repositories": 0,
                        "total_findings": 0,
                        "critical_findings": 0,
                        "analyzed_at": None,
                        "dsomm_scores": {}
                    })
        
        # Calculate averages and rankings
        analyzed_folders = [c for c in comparisons if c['analysis_id']]
        avg_maturity = sum(c['maturity_score'] for c in analyzed_folders) / len(analyzed_folders) if analyzed_folders else 0
        
        # Sort by maturity score
        ranked = sorted(comparisons, key=lambda x: x['maturity_score'], reverse=True)
        
        return {
            "success": True,
            "comparisons": comparisons,
            "ranked": ranked,
            "summary": {
                "average_maturity": round(avg_maturity, 2),
                "highest_maturity": ranked[0]['maturity_score'] if ranked else 0,
                "lowest_maturity": ranked[-1]['maturity_score'] if ranked else 0,
                "folders_analyzed": len(analyzed_folders),
                "folders_requested": len(folder_paths)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to compare folders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/analysis/{analysis_id}")
async def delete_analysis(
    analysis_id: str
):
    """
    Delete a specific analysis by ID
    """
    try:
        async with db_manager.get_session() as session:
            from database.models import ProjectAnalysis
            from sqlalchemy import select
            
            # Find the analysis
            stmt = select(ProjectAnalysis).where(ProjectAnalysis.id == analysis_id)
            result = await session.execute(stmt)
            analysis = result.scalar_one_or_none()
            
            if not analysis:
                raise HTTPException(status_code=404, detail="Analysis not found")
            
            # Delete the analysis (findings are stored in analysis_data JSON, not as separate records)
            await session.delete(analysis)
            await session.commit()
            
            logger.info(f"🗑️ Successfully deleted analysis {analysis_id}")
            
            return {
                "success": True,
                "message": "Analysis deleted successfully",
                "analysis_id": analysis_id
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete analysis: {str(e)}")
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
            finding.acknowledged_by = "system"  # No user context in microservice
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
                    },
                    user_id=user_id
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
            findings_count=result.get('summary', {}).get('findings_count', {}),
            analysis_scope="workspace"
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


async def _run_folder_analysis(
    analyzer: WorkspaceAnalyzer,
    org_name: str,
    filtered_tree_data: List[Dict],
    tree_id: str,
    folder_id: str,
    folder_path: str,
    user_id: str,
    fetch_github_data: bool
):
    """Background task to run folder-specific analysis"""
    from core.event_bus import event_bus
    import time
    
    start_time = time.time()
    analysis_id = None
    
    try:
        logger.info(f"📁 Starting folder analysis for: {folder_path}")
        
        # Extract repository names from filtered tree
        repo_names = _extract_repository_names(filtered_tree_data)
        
        # Publish analysis started event
        await event_bus.publish_workspace_analysis_started(
            analysis_id=None,
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id
        )
        
        # Run analysis on filtered tree data
        result = await analyzer.analyze_workspace(
            org_name,
            filtered_tree_data,
            fetch_github_data
        )
        
        # Save results with folder scope metadata
        async with db_manager.get_session() as session:
            for project_analysis in result.get('project_analyses', []):
                # Enhanced save with folder scope information
                saved_analysis = await WorkspaceIntelligenceDB.save_project_analysis(
                    session,
                    tree_id,
                    project_analysis['project_id'],
                    project_analysis['project_name'],
                    org_name,
                    user_id,
                    project_analysis,
                    analysis_scope='folder',
                    folder_id=folder_id,
                    folder_path=folder_path,
                    repositories_in_scope=repo_names
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
        
        # Publish analysis completed event with folder context
        await event_bus.publish_workspace_analysis_completed(
            analysis_id=analysis_id,
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id,
            duration_seconds=duration,
            maturity_score=result.get('organization_metrics', {}).get('overall_maturity', 0),
            total_repositories=result.get('summary', {}).get('total_repositories', 0),
            total_workflows=result.get('summary', {}).get('total_workflows', 0),
            findings_count=result.get('summary', {}).get('findings_count', {}),
            project_name=folder_path,  # Use folder path as project name for filtering
            folder_path=folder_path,
            analysis_scope="folder"
        )
        
        logger.info(f"✅ Folder analysis completed for {folder_path} ({len(repo_names)} repos)")
        
    except Exception as e:
        logger.error(f"❌ Background folder analysis failed: {str(e)}", exc_info=True)
        
        # Publish analysis failed event
        await event_bus.publish_workspace_analysis_failed(
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id,
            error_message=str(e)
        )


async def _run_unified_workspace_analysis(
    analyzer: WorkspaceAnalyzer,
    org_name: str,
    tree_data: List[Dict],
    tree_id: str,
    user_id: str,
    fetch_github_data: bool
):
    """
    Background task to run unified workspace analysis
    
    Analyzes entire organization and saves as ONE analysis record
    with embedded project breakdowns for drill-down capability
    """
    from core.event_bus import event_bus
    import time
    
    start_time = time.time()
    
    try:
        # Publish analysis started event
        await event_bus.publish_workspace_analysis_started(
            analysis_id=None,
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id
        )
        
        logger.info(f"🔍 Starting unified workspace analysis for {org_name}")
        
        # Run complete workspace analysis
        result = await analyzer.analyze_workspace(
            org_name,
            tree_data,
            fetch_github_data
        )
        
        logger.info("📊 Analysis complete. Saving unified analysis...")
        
        # Save as ONE unified analysis record
        async with db_manager.get_session() as session:
            unified_analysis = await WorkspaceIntelligenceDB.save_unified_analysis(
                session,
                tree_id,
                org_name,
                user_id,
                result
            )
            
            analysis_id = unified_analysis.id
        
        duration = time.time() - start_time
        
        # Publish analysis completed event with unified scope
        await event_bus.publish_workspace_analysis_completed(
            analysis_id=analysis_id,
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id,
            duration_seconds=duration,
            maturity_score=result.get('organization_metrics', {}).get('overall_maturity', 0),
            total_repositories=result.get('summary', {}).get('total_repositories', 0),
            total_workflows=result.get('summary', {}).get('total_workflows', 0),
            findings_count=result.get('summary', {}).get('findings_count', {}),
            analysis_scope="unified"
        )
        
        logger.info(f"✅ Unified workspace analysis completed for {org_name} (ID: {analysis_id})")
        
    except Exception as e:
        logger.error(f"❌ Background unified workspace analysis failed: {str(e)}", exc_info=True)
        
        # Publish analysis failed event
        await event_bus.publish_workspace_analysis_failed(
            organization_name=org_name,
            user_id=user_id,
            tree_id=tree_id,
            error_message=str(e)
        )


def _filter_tree_by_folder(tree_data: List[Dict], folder_path: str, include_subfolders: bool) -> List[Dict]:
    """
    Filter tree_data to only include items from specified folder path
    
    Args:
        tree_data: Complete repository tree structure
        folder_path: Path like "team-a/backend" or "infrastructure"
        include_subfolders: Whether to include nested subfolders
        
    Returns:
        Filtered tree_data containing only the specified folder
    """
    path_parts = folder_path.split('/')
    
    def find_folder_recursive(items: List[Dict], parts: List[str]) -> Optional[Dict]:
        """Recursively find folder in tree structure"""
        if not parts:
            return None
            
        current_name = parts[0]
        remaining_parts = parts[1:]
        
        for item in items:
            if item.get('type') == 'folder' and item.get('name') == current_name:
                if not remaining_parts:
                    # Found the target folder
                    return item
                else:
                    # Continue searching in children
                    children = item.get('children', [])
                    return find_folder_recursive(children, remaining_parts)
        
        return None
    
    # Find the target folder
    target_folder = find_folder_recursive(tree_data, path_parts)
    
    if not target_folder:
        return []
    
    # If include_subfolders, return the folder with all its children
    # Otherwise, filter out nested folders and keep only direct repos
    if include_subfolders:
        return [target_folder]
    else:
        # Create a copy with only direct repositories
        filtered_folder = target_folder.copy()
        filtered_folder['children'] = [
            child for child in target_folder.get('children', [])
            if child.get('type') != 'folder'
        ]
        return [filtered_folder]


def _count_repositories_in_tree(tree_data: List[Dict]) -> int:
    """Count total number of repositories in tree structure"""
    count = 0
    
    def count_recursive(items: List[Dict]):
        nonlocal count
        for item in items:
            if item.get('type') == 'repository':
                count += 1
            elif item.get('type') == 'folder':
                count_recursive(item.get('children', []))
    
    count_recursive(tree_data)
    return count


def _extract_repository_names(tree_data: List[Dict]) -> List[str]:
    """Extract all repository names from tree structure"""
    repo_names = []
    
    def extract_recursive(items: List[Dict]):
        for item in items:
            if item.get('type') == 'repository':
                repo_names.append(item.get('name', ''))
            elif item.get('type') == 'folder':
                extract_recursive(item.get('children', []))
    
    extract_recursive(tree_data)
    return repo_names
