"""
Canvas API Routes
Handles visual workflow design and relationship management
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from database.operations import CanvasDesignRepository
from database.config import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/canvas", tags=["canvas"])


class SaveCanvasRequest(BaseModel):
    """Request model for saving canvas design"""
    org_name: str
    repo_name: str
    design_data: Dict[str, Any]
    relationships: Optional[List[Dict[str, Any]]] = None
    canvas_metadata: Optional[Dict[str, Any]] = None


class CanvasResponse(BaseModel):
    """Response model for canvas design"""
    canvas_id: str
    org_name: str
    repo_name: str
    design_data: Dict[str, Any]
    relationships: List[Dict[str, Any]]
    canvas_metadata: Dict[str, Any]
    version: int
    updated_at: str


@router.post("/save-workflow")
async def save_canvas_design(
    request: SaveCanvasRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Save workflow canvas design
    
    Args:
        request: Canvas design data
        x_user_id: User ID from header
    
    Returns:
        Saved canvas design
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            canvas_repo = CanvasDesignRepository(session)
            canvas = await canvas_repo.save_canvas(
                user_id=x_user_id,
                org_name=request.org_name,
                repo_name=request.repo_name,
                design_data=request.design_data,
                relationships=request.relationships or [],
                canvas_metadata=request.canvas_metadata or {}
            )
            
            return CanvasResponse(
                canvas_id=str(canvas.id),
                org_name=canvas.org_name,
                repo_name=canvas.repo_name,
                design_data=canvas.design_data,
                relationships=canvas.relationships,
                canvas_metadata=canvas.canvas_metadata,
                version=canvas.version,
                updated_at=canvas.updated_at.isoformat()
            )
    
    except Exception as e:
        logger.error(f"Error saving canvas design: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save canvas design: {str(e)}")


@router.get("/{org_name}/{repo_name}")
async def get_canvas_design(
    org_name: str,
    repo_name: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get canvas design for repository
    
    Args:
        org_name: GitHub organization/owner
        repo_name: Repository name
        x_user_id: User ID from header
    
    Returns:
        Canvas design data
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            canvas_repo = CanvasDesignRepository(session)
            canvas = await canvas_repo.get_canvas(
                org_name=org_name,
                repo_name=repo_name,
                user_id=x_user_id
            )
            
            if not canvas:
                raise HTTPException(status_code=404, detail="Canvas design not found")
            
            return CanvasResponse(
                canvas_id=str(canvas.id),
                org_name=canvas.org_name,
                repo_name=canvas.repo_name,
                design_data=canvas.design_data,
                relationships=canvas.relationships,
                canvas_metadata=canvas.canvas_metadata,
                version=canvas.version,
                updated_at=canvas.updated_at.isoformat()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting canvas design: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get canvas design: {str(e)}")


@router.get("/workflow-relationships/{org_name}/{repo_name}")
async def get_workflow_relationships(
    org_name: str,
    repo_name: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get workflow relationships and dependencies
    
    Args:
        org_name: GitHub organization/owner
        repo_name: Repository name
        x_user_id: User ID from header
    
    Returns:
        Workflow relationships
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            canvas_repo = CanvasDesignRepository(session)
            canvas = await canvas_repo.get_canvas(
                org_name=org_name,
                repo_name=repo_name,
                user_id=x_user_id
            )
            
            if not canvas:
                return {
                    'org_name': org_name,
                    'repo_name': repo_name,
                    'relationships': []
                }
            
            return {
                'org_name': org_name,
                'repo_name': repo_name,
                'relationships': canvas.relationships
            }
    
    except Exception as e:
        logger.error(f"Error getting workflow relationships: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflow relationships: {str(e)}")


@router.get("/predefined-actions")
async def get_predefined_actions(
    category: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get library of predefined GitHub Actions
    
    Args:
        category: Filter by category (ci, cd, security, etc.)
        x_user_id: User ID from header
    
    Returns:
        List of predefined actions
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    # Predefined popular GitHub Actions organized by category
    actions_library = {
        'ci': [
            {
                'name': 'Checkout',
                'action': 'actions/checkout@v4',
                'description': 'Check out repository code',
                'inputs': {'fetch-depth': '0', 'submodules': 'false'}
            },
            {
                'name': 'Setup Node.js',
                'action': 'actions/setup-node@v4',
                'description': 'Set up Node.js environment',
                'inputs': {'node-version': '20', 'cache': 'npm'}
            },
            {
                'name': 'Setup Python',
                'action': 'actions/setup-python@v5',
                'description': 'Set up Python environment',
                'inputs': {'python-version': '3.11', 'cache': 'pip'}
            },
        ],
        'testing': [
            {
                'name': 'Run Tests',
                'action': 'run',
                'description': 'Execute test suite',
                'command': 'npm test'
            },
            {
                'name': 'Code Coverage',
                'action': 'codecov/codecov-action@v4',
                'description': 'Upload coverage reports',
                'inputs': {'token': '${{ secrets.CODECOV_TOKEN }}'}
            },
        ],
        'security': [
            {
                'name': 'CodeQL Analysis',
                'action': 'github/codeql-action/analyze@v3',
                'description': 'Run CodeQL security analysis',
                'inputs': {'category': '/language:javascript'}
            },
            {
                'name': 'Dependency Review',
                'action': 'actions/dependency-review-action@v4',
                'description': 'Review dependencies for vulnerabilities',
                'inputs': {}
            },
            {
                'name': 'Trivy Security Scan',
                'action': 'aquasecurity/trivy-action@master',
                'description': 'Scan for vulnerabilities',
                'inputs': {'scan-type': 'fs', 'severity': 'CRITICAL,HIGH'}
            },
        ],
        'deployment': [
            {
                'name': 'Deploy to Azure',
                'action': 'azure/webapps-deploy@v2',
                'description': 'Deploy to Azure Web Apps',
                'inputs': {'app-name': '${{ secrets.AZURE_WEBAPP_NAME }}'}
            },
            {
                'name': 'Deploy to AWS',
                'action': 'aws-actions/configure-aws-credentials@v4',
                'description': 'Configure AWS credentials',
                'inputs': {'aws-region': 'us-east-1'}
            },
        ],
        'docker': [
            {
                'name': 'Docker Build & Push',
                'action': 'docker/build-push-action@v5',
                'description': 'Build and push Docker image',
                'inputs': {'push': 'true', 'tags': 'user/app:latest'}
            },
            {
                'name': 'Docker Login',
                'action': 'docker/login-action@v3',
                'description': 'Login to Docker registry',
                'inputs': {'username': '${{ secrets.DOCKER_USERNAME }}'}
            },
        ],
        'notifications': [
            {
                'name': 'Slack Notification',
                'action': 'slackapi/slack-github-action@v1',
                'description': 'Send Slack notification',
                'inputs': {'channel-id': 'C1234567890'}
            },
        ]
    }
    
    if category:
        if category not in actions_library:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        
        return {
            'category': category,
            'actions': actions_library[category]
        }
    
    return {
        'categories': list(actions_library.keys()),
        'actions': actions_library
    }


@router.delete("/{org_name}/{repo_name}")
async def delete_canvas_design(
    org_name: str,
    repo_name: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Delete canvas design for repository
    
    Args:
        org_name: GitHub organization/owner
        repo_name: Repository name
        x_user_id: User ID from header
    
    Returns:
        Success message
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            canvas_repo = CanvasDesignRepository(session)
            canvas = await canvas_repo.get_canvas(
                org_name=org_name,
                repo_name=repo_name,
                user_id=x_user_id
            )
            
            if not canvas:
                raise HTTPException(status_code=404, detail="Canvas design not found")
            
            await session.delete(canvas)
            await session.commit()
            
            return {
                'message': 'Canvas design deleted successfully',
                'org_name': org_name,
                'repo_name': repo_name
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting canvas design: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete canvas design: {str(e)}")
