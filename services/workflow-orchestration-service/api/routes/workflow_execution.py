"""
Workflow Execution API Routes
Handles workflow triggering, status monitoring, and execution history
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging
import os

from core.execution_engine import ExecutionEngine
from core.workflow_parser import WorkflowParser
from core.stream_manager import stream_manager
from database.operations import WorkflowExecutionRepository
from database.config import db_manager
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflow-execution"])


@router.get("/health")
async def health_check():
    """Health check endpoint accessible through Kong Gateway"""
    return {
        "status": "healthy",
        "service": "workflow-orchestration-service",
        "version": "1.0.0"
    }


# Initialize execution engine
github_service_url = os.getenv('GITHUB_SERVICE_URL', 'http://github-service:8002')
auth_service_url = os.getenv('AUTH_SERVICE_URL', 'http://auth-service:8001')
execution_engine = ExecutionEngine(github_service_url, auth_service_url)


class TriggerWorkflowRequest(BaseModel):
    """Request model for triggering workflow"""
    ref: str = 'main'
    inputs: Optional[Dict[str, Any]] = None


class ExecutionResponse(BaseModel):
    """Response model for execution"""
    execution_id: str
    workflow_id: str
    status: str
    github_run_id: Optional[int]
    message: str


@router.post("/{org_name}/{repo_name}/{workflow_id}/trigger")
async def trigger_workflow(
    org_name: str,
    repo_name: str,
    workflow_id: str,
    request: TriggerWorkflowRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Trigger a GitHub Actions workflow
    
    Args:
        org_name: GitHub organization/owner
        repo_name: Repository name
        workflow_id: Workflow file name or ID
        request: Trigger parameters (ref, inputs)
        x_user_id: User ID from header
    
    Returns:
        Execution information
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        result = await execution_engine.trigger_workflow(
            user_id=x_user_id,
            org_name=org_name,
            repo_name=repo_name,
            workflow_id=workflow_id,
            ref=request.ref,
            inputs=request.inputs
        )
        
        if result['status'] == 'failed':
            raise HTTPException(status_code=500, detail=result['message'])
        
        return ExecutionResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering workflow: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {str(e)}")


@router.get("/{org_name}/{repo_name}/{workflow_id}/history")
async def get_execution_history(
    org_name: str,
    repo_name: str,
    workflow_id: str,
    limit: int = 10,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get execution history for a workflow
    
    Args:
        org_name: GitHub organization/owner
        repo_name: Repository name
        workflow_id: Workflow file name or ID
        limit: Number of executions to return
        x_user_id: User ID from header
    
    Returns:
        List of executions
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            exec_repo = WorkflowExecutionRepository(session)
            executions = await exec_repo.get_execution_history(
                org_name=org_name,
                repo_name=repo_name,
                workflow_id=workflow_id,
                limit=limit
            )
            
            return {
                'org_name': org_name,
                'repo_name': repo_name,
                'workflow_id': workflow_id,
                'executions': [
                    {
                        'execution_id': str(exec.id),
                        'execution_number': exec.execution_number,
                        'status': exec.status,
                        'github_run_id': exec.github_run_id,
                        'ref': exec.ref,
                        'triggered_by': exec.triggered_by,
                        'started_at': exec.started_at.isoformat() if exec.started_at else None,
                        'completed_at': exec.completed_at.isoformat() if exec.completed_at else None,
                        'duration_seconds': exec.duration_seconds,
                        'created_at': exec.created_at.isoformat()
                    }
                    for exec in executions
                ]
            }
    
    except Exception as e:
        logger.error(f"Error getting execution history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get execution history: {str(e)}")


@router.get("/{execution_id}/status")
async def get_execution_status(
    execution_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get detailed status of a specific execution
    
    Args:
        execution_id: Execution ID
        x_user_id: User ID from header
    
    Returns:
        Detailed execution status
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            exec_repo = WorkflowExecutionRepository(session)
            execution = await exec_repo.get_execution_by_id(execution_id)
            
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")
            
            # Get live status from GitHub if still running
            if execution.status in ['pending', 'running'] and execution.github_run_id:
                live_status = await execution_engine.get_execution_status(
                    org_name=execution.org_name,
                    repo_name=execution.repo_name,
                    run_id=execution.github_run_id,
                    user_id=x_user_id
                )
                
                return {
                    'execution_id': str(execution.id),
                    'workflow_id': execution.workflow_id,
                    'status': live_status['status'],
                    'conclusion': live_status['conclusion'],
                    'github_run_id': execution.github_run_id,
                    'ref': execution.ref,
                    'started_at': live_status['started_at'],
                    'completed_at': live_status['completed_at'],
                    'duration_seconds': live_status['duration_seconds'],
                    'jobs': live_status['jobs']
                }
            
            # Return stored data for completed executions
            return {
                'execution_id': str(execution.id),
                'workflow_id': execution.workflow_id,
                'status': execution.status,
                'github_run_id': execution.github_run_id,
                'ref': execution.ref,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration_seconds': execution.duration_seconds,
                'steps': execution.steps
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    SSE stream for real-time execution updates
    
    Args:
        execution_id: Execution ID to stream
        x_user_id: User ID from header
    
    Returns:
        SSE event stream
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        # Verify execution exists
        async with db_manager.get_session() as session:
            exec_repo = WorkflowExecutionRepository(session)
            execution = await exec_repo.get_execution_by_id(execution_id)
            
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")
        
        # Return SSE stream
        return EventSourceResponse(stream_manager.sse_stream(execution_id))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stream execution: {str(e)}")


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Cancel a running workflow execution
    
    Args:
        execution_id: Execution ID to cancel
        x_user_id: User ID from header
    
    Returns:
        Cancellation status
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        async with db_manager.get_session() as session:
            exec_repo = WorkflowExecutionRepository(session)
            execution = await exec_repo.get_execution_by_id(execution_id)
            
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")
            
            if not execution.github_run_id:
                raise HTTPException(status_code=400, detail="Cannot cancel - no GitHub run ID")
            
            if execution.status not in ['pending', 'running']:
                raise HTTPException(status_code=400, detail=f"Cannot cancel execution with status: {execution.status}")
            
            # Cancel via GitHub Service
            success = await execution_engine.cancel_execution(
                org_name=execution.org_name,
                repo_name=execution.repo_name,
                run_id=execution.github_run_id,
                user_id=x_user_id
            )
            
            if success:
                # Update database
                from database.models import ExecutionStatus
                await exec_repo.update_execution_status(
                    execution_id=execution_id,
                    status=ExecutionStatus.CANCELLED
                )
                
                return {"message": "Execution cancelled successfully", "execution_id": execution_id}
            else:
                raise HTTPException(status_code=500, detail="Failed to cancel execution")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel execution: {str(e)}")


@router.get("/{org_name}/{repo_name}/{workflow_id}/content")
async def get_workflow_content(
    org_name: str,
    repo_name: str,
    workflow_id: str,
    ref: str = 'main',
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Get workflow YAML content from GitHub
    
    Args:
        org_name: GitHub organization/owner
        repo_name: Repository name
        workflow_id: Workflow file name
        ref: Git ref (branch/tag)
        x_user_id: User ID from header
    
    Returns:
        Workflow content and parsed data
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        import httpx
        
        # Fetch from GitHub Service
        url = f"{github_service_url}/api/repos/{org_name}/{repo_name}/contents/.github/workflows/{workflow_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={'X-User-Id': x_user_id},
                params={'ref': ref}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch workflow content")
            
            content = response.text
            
            # Parse workflow
            parsed = WorkflowParser.parse_workflow(content)
            
            return {
                'org_name': org_name,
                'repo_name': repo_name,
                'workflow_id': workflow_id,
                'ref': ref,
                'content': content,
                'parsed': parsed
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow content: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflow content: {str(e)}")


@router.get("/{org_name}/{repo_name}/{workflow_id}/parameters")
async def get_workflow_parameters(
    org_name: str,
    repo_name: str,
    workflow_id: str,
    ref: str = 'main',
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Extract workflow input parameters
    
    Args:
        org_name: GitHub organization/owner
        repo_name: Repository name
        workflow_id: Workflow file name
        ref: Git ref (branch/tag)
        x_user_id: User ID from header
    
    Returns:
        Workflow input parameters
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        import httpx
        import yaml
        
        # Fetch workflow content
        url = f"{github_service_url}/api/repos/{org_name}/{repo_name}/contents/.github/workflows/{workflow_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={'X-User-Id': x_user_id},
                params={'ref': ref}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch workflow")
            
            content = response.text
            workflow_data = yaml.safe_load(content)
            
            # Extract inputs from workflow_dispatch trigger
            triggers = workflow_data.get('on', {})
            inputs = {}
            
            if isinstance(triggers, dict):
                workflow_dispatch = triggers.get('workflow_dispatch', {})
                if isinstance(workflow_dispatch, dict):
                    inputs = workflow_dispatch.get('inputs', {})
            
            return {
                'workflow_id': workflow_id,
                'inputs': inputs
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow parameters: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflow parameters: {str(e)}")
