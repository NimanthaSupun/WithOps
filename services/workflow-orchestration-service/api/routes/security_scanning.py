"""
Security Scanning API Routes
Handles workflow security analysis and vulnerability detection
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
import logging
import httpx

from core.security_scanner import SecurityScanner
from database.operations import SecurityScanRepository
from database.config import db_manager
from database.models import ScanRiskLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security", tags=["security-scanning"])


class ScanWorkflowRequest(BaseModel):
    """Request model for scanning workflow"""
    workflow_content: str
    workflow_name: Optional[str] = None


class ScanResponse(BaseModel):
    """Response model for scan results"""
    scan_id: str
    workflow_name: str
    risk_level: str
    risk_score: float
    total_issues: int
    critical: int
    high: int
    medium: int
    low: int
    info: int
    recommendations: List[str]


@router.post("/scan/workflow")
async def scan_workflow(
    request: ScanWorkflowRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Scan a single workflow for security vulnerabilities
    
    Args:
        request: Workflow content and name
        x_user_id: User ID from header
    
    Returns:
        Scan results with issues and recommendations
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        # Perform security scan
        scan_result = SecurityScanner.scan_workflow(
            workflow_content=request.workflow_content,
            workflow_name=request.workflow_name or "Unknown"
        )
        
        # Save to database
        async with db_manager.get_session() as session:
            scan_repo = SecurityScanRepository(session)
            scan = await scan_repo.create_scan(
                user_id=x_user_id,
                org_name="",  # Not applicable for direct content scan
                repo_name="",
                workflow_id=request.workflow_name or "adhoc-scan",
                scan_type="workflow",
                risk_level=ScanRiskLevel(scan_result['risk_level']),
                risk_score=scan_result['risk_score'],
                findings=scan_result['issues'],
                recommendations=scan_result['recommendations']
            )
            
            return ScanResponse(
                scan_id=str(scan.id),
                workflow_name=scan_result['workflow_name'],
                risk_level=scan_result['risk_level'],
                risk_score=scan_result['risk_score'],
                total_issues=scan_result['summary']['total_issues'],
                critical=scan_result['summary']['critical'],
                high=scan_result['summary']['high'],
                medium=scan_result['summary']['medium'],
                low=scan_result['summary']['low'],
                info=scan_result['summary']['info'],
                recommendations=scan_result['recommendations']
            )
    
    except Exception as e:
        logger.error(f"Error scanning workflow: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to scan workflow: {str(e)}")


@router.post("/scan/repository/{org_name}/{repo_name}")
async def scan_repository(
    org_name: str,
    repo_name: str,
    ref: str = 'main',
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Scan all workflows in a repository
    
    Args:
        org_name: GitHub organization/owner
        repo_name: Repository name
        ref: Git ref (branch/tag)
        x_user_id: User ID from header
    
    Returns:
        Aggregate scan results for all workflows
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        import os
        github_service_url = os.getenv('GITHUB_SERVICE_URL', 'http://github-service:8002')
        
        # Get all workflows from repository via GitHub Service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{github_service_url}/api/repos/{org_name}/{repo_name}/workflows",
                headers={'X-User-Id': x_user_id}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch workflows")
            
            workflows = response.json().get('workflows', [])
        
        scan_results = []
        total_issues = 0
        highest_risk_score = 0.0
        highest_risk_level = "minimal"
        
        # Scan each workflow
        for workflow in workflows:
            try:
                # Fetch workflow content
                async with httpx.AsyncClient(timeout=30.0) as client:
                    content_response = await client.get(
                        f"{github_service_url}/api/repos/{org_name}/{repo_name}/contents/.github/workflows/{workflow['path']}",
                        headers={'X-User-Id': x_user_id},
                        params={'ref': ref}
                    )
                    
                    if content_response.status_code != 200:
                        continue
                    
                    workflow_content = content_response.text
                
                # Scan workflow
                scan_result = SecurityScanner.scan_workflow(
                    workflow_content=workflow_content,
                    workflow_name=workflow['name']
                )
                
                # Save to database
                async with db_manager.get_session() as session:
                    scan_repo = SecurityScanRepository(session)
                    scan = await scan_repo.create_scan(
                        user_id=x_user_id,
                        org_name=org_name,
                        repo_name=repo_name,
                        workflow_id=workflow['path'],
                        scan_type="repository",
                        risk_level=ScanRiskLevel(scan_result['risk_level']),
                        risk_score=scan_result['risk_score'],
                        findings=scan_result['issues'],
                        recommendations=scan_result['recommendations']
                    )
                
                scan_results.append({
                    'scan_id': str(scan.id),
                    'workflow_name': scan_result['workflow_name'],
                    'risk_level': scan_result['risk_level'],
                    'risk_score': scan_result['risk_score'],
                    'total_issues': scan_result['summary']['total_issues']
                })
                
                total_issues += scan_result['summary']['total_issues']
                if scan_result['risk_score'] > highest_risk_score:
                    highest_risk_score = scan_result['risk_score']
                    highest_risk_level = scan_result['risk_level']
            
            except Exception as e:
                logger.error(f"Error scanning workflow {workflow['name']}: {str(e)}")
                continue
        
        return {
            'org_name': org_name,
            'repo_name': repo_name,
            'total_workflows_scanned': len(scan_results),
            'total_issues': total_issues,
            'highest_risk_score': highest_risk_score,
            'highest_risk_level': highest_risk_level,
            'scans': scan_results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning repository: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to scan repository: {str(e)}")


@router.post("/scan/organization/{org_name}")
async def scan_organization(
    org_name: str,
    ref: str = 'main',
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Scan all workflows across all repositories in an organization
    
    Args:
        org_name: GitHub organization name
        ref: Git ref (branch/tag)
        x_user_id: User ID from header
    
    Returns:
        Organization-wide scan results
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        import os
        github_service_url = os.getenv('GITHUB_SERVICE_URL', 'http://github-service:8002')
        
        # Get all repositories in organization
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{github_service_url}/api/orgs/{org_name}/repos",
                headers={'X-User-Id': x_user_id}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch repositories")
            
            repositories = response.json().get('repositories', [])
        
        org_scan_results = []
        total_workflows = 0
        total_issues = 0
        highest_risk_score = 0.0
        
        # Scan each repository
        for repo in repositories:
            try:
                # Use scan_repository for each repo
                repo_result = await scan_repository(
                    org_name=org_name,
                    repo_name=repo['name'],
                    ref=ref,
                    x_user_id=x_user_id
                )
                
                org_scan_results.append(repo_result)
                total_workflows += repo_result['total_workflows_scanned']
                total_issues += repo_result['total_issues']
                
                if repo_result['highest_risk_score'] > highest_risk_score:
                    highest_risk_score = repo_result['highest_risk_score']
            
            except Exception as e:
                logger.error(f"Error scanning repository {repo['name']}: {str(e)}")
                continue
        
        # Determine overall risk level
        if highest_risk_score >= 75:
            overall_risk_level = 'critical'
        elif highest_risk_score >= 50:
            overall_risk_level = 'high'
        elif highest_risk_score >= 25:
            overall_risk_level = 'medium'
        elif highest_risk_score >= 10:
            overall_risk_level = 'low'
        else:
            overall_risk_level = 'minimal'
        
        return {
            'org_name': org_name,
            'total_repositories_scanned': len(org_scan_results),
            'total_workflows_scanned': total_workflows,
            'total_issues': total_issues,
            'highest_risk_score': highest_risk_score,
            'overall_risk_level': overall_risk_level,
            'repositories': org_scan_results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning organization: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to scan organization: {str(e)}")


@router.get("/scans/{org_name}")
async def get_scan_history(
    org_name: str,
    scan_type: Optional[str] = None,
    limit: int = 10,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get security scan history for organization
    
    Args:
        org_name: GitHub organization/owner
        scan_type: Filter by scan type (workflow, repository, organization)
        limit: Number of scans to return
        x_user_id: User ID from header
    
    Returns:
        List of recent scans
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            scan_repo = SecurityScanRepository(session)
            scans = await scan_repo.get_latest_scans(
                org_name=org_name,
                scan_type=scan_type,
                limit=limit
            )
            
            return {
                'org_name': org_name,
                'scans': [
                    {
                        'scan_id': str(scan.id),
                        'repo_name': scan.repo_name,
                        'workflow_id': scan.workflow_id,
                        'scan_type': scan.scan_type,
                        'risk_level': scan.risk_level,
                        'risk_score': scan.risk_score,
                        'total_findings': len(scan.findings),
                        'secrets_found': scan.secrets_found,
                        'unsafe_actions_found': scan.unsafe_actions_found,
                        'permission_issues_found': scan.permission_issues_found,
                        'injection_risks_found': scan.injection_risks_found,
                        'scanned_at': scan.created_at.isoformat()
                    }
                    for scan in scans
                ]
            }
    
    except Exception as e:
        logger.error(f"Error getting scan history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get scan history: {str(e)}")


@router.get("/scans/{scan_id}/details")
async def get_scan_details(
    scan_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get detailed scan results including all findings
    
    Args:
        scan_id: Scan ID
        x_user_id: User ID from header
    
    Returns:
        Detailed scan results
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            scan_repo = SecurityScanRepository(session)
            scan = await scan_repo.get_scan_by_id(scan_id)
            
            if not scan:
                raise HTTPException(status_code=404, detail="Scan not found")
            
            return {
                'scan_id': str(scan.id),
                'org_name': scan.org_name,
                'repo_name': scan.repo_name,
                'workflow_id': scan.workflow_id,
                'scan_type': scan.scan_type,
                'risk_level': scan.risk_level,
                'risk_score': scan.risk_score,
                'findings': scan.findings,
                'recommendations': scan.recommendations,
                'secrets_found': scan.secrets_found,
                'unsafe_actions_found': scan.unsafe_actions_found,
                'permission_issues_found': scan.permission_issues_found,
                'injection_risks_found': scan.injection_risks_found,
                'scanned_at': scan.created_at.isoformat()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scan details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get scan details: {str(e)}")


@router.get("/overview/{org_name}")
async def get_security_overview(
    org_name: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get security overview with aggregate metrics
    
    Args:
        org_name: GitHub organization/owner
        x_user_id: User ID from header
    
    Returns:
        Security metrics and overview
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            scan_repo = SecurityScanRepository(session)
            scans = await scan_repo.get_latest_scans(org_name=org_name, limit=100)
            
            if not scans:
                return {
                    'org_name': org_name,
                    'total_scans': 0,
                    'risk_distribution': {},
                    'total_issues': 0,
                    'last_scan': None
                }
            
            # Calculate metrics
            risk_distribution = {
                'critical': sum(1 for s in scans if s.risk_level == ScanRiskLevel.CRITICAL),
                'high': sum(1 for s in scans if s.risk_level == ScanRiskLevel.HIGH),
                'medium': sum(1 for s in scans if s.risk_level == ScanRiskLevel.MEDIUM),
                'low': sum(1 for s in scans if s.risk_level == ScanRiskLevel.LOW),
                'minimal': sum(1 for s in scans if s.risk_level == ScanRiskLevel.MINIMAL),
            }
            
            total_issues = sum(len(s.findings) for s in scans)
            total_secrets = sum(s.secrets_found for s in scans)
            total_unsafe_actions = sum(s.unsafe_actions_found for s in scans)
            
            return {
                'org_name': org_name,
                'total_scans': len(scans),
                'risk_distribution': risk_distribution,
                'total_issues': total_issues,
                'total_secrets_found': total_secrets,
                'total_unsafe_actions_found': total_unsafe_actions,
                'last_scan': scans[0].created_at.isoformat() if scans else None
            }
    
    except Exception as e:
        logger.error(f"Error getting security overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get security overview: {str(e)}")
