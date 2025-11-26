"""
Execution Engine - Orchestrate workflow executions via GitHub Service
Handles triggering, status polling, and state management
"""

import httpx
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from database.operations import WorkflowExecutionRepository, MetricsRepository
from database.models import ExecutionStatus

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Orchestrate GitHub Actions workflow executions"""
    
    def __init__(self, github_service_url: str, auth_service_url: str):
        """
        Initialize execution engine
        
        Args:
            github_service_url: Base URL for GitHub Service (e.g., http://github-service:8002)
            auth_service_url: Base URL for Auth Service (e.g., http://auth-service:8001)
        """
        self.github_service_url = github_service_url.rstrip('/')
        self.auth_service_url = auth_service_url.rstrip('/')
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def trigger_workflow(
        self,
        user_id: str,
        org_name: str,
        repo_name: str,
        workflow_id: str,
        ref: str = 'main',
        inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger a GitHub Actions workflow
        
        Args:
            user_id: User ID for tracking
            org_name: GitHub organization/owner
            repo_name: Repository name
            workflow_id: Workflow file name or ID
            ref: Git ref (branch/tag) to run workflow on
            inputs: Workflow inputs (for workflow_dispatch)
        
        Returns:
            {
                'execution_id': str,
                'workflow_id': str,
                'status': str,
                'github_run_id': int,
                'message': str
            }
        """
        try:
            # Call GitHub Service to trigger workflow
            url = f"{self.github_service_url}/api/workflows/{org_name}/{repo_name}/{workflow_id}/dispatches"
            
            payload = {
                'ref': ref,
                'inputs': inputs or {}
            }
            
            logger.info(f"Triggering workflow {workflow_id} for {org_name}/{repo_name} on ref {ref}")
            
            response = await self.http_client.post(
                url,
                json=payload,
                headers={'X-User-Id': user_id}
            )
            
            if response.status_code == 204:
                # Workflow triggered successfully
                # Create execution record in database
                from database.config import db_manager
                
                async with db_manager.get_session() as session:
                    execution_repo = WorkflowExecutionRepository()
                    
                    # Note: GitHub API doesn't return run_id immediately for workflow_dispatch
                    # We'll need to poll for the run_id
                    execution = await execution_repo.create_execution(
                        session=session,
                        workflow_id=workflow_id,
                        org_name=org_name,
                        repo_name=repo_name,
                        workflow_name=workflow_id,  # Use workflow_id as name for now
                        workflow_path=f".github/workflows/{workflow_id}",
                        triggered_by=user_id,
                        parameters={},
                        inputs=inputs or {}
                    )
                    
                    await session.commit()
                
                # Start background task to get run_id
                asyncio.create_task(self._update_run_id(str(execution.id), org_name, repo_name, workflow_id, user_id))
                
                return {
                    'execution_id': str(execution.id),
                    'workflow_id': workflow_id,
                    'status': execution.status,
                    'github_run_id': None,  # Will be updated later
                    'message': 'Workflow triggered successfully'
                }
            
            else:
                error_msg = f"Failed to trigger workflow: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'execution_id': None,
                    'workflow_id': workflow_id,
                    'status': 'failed',
                    'github_run_id': None,
                    'message': error_msg
                }
        
        except Exception as e:
            logger.error(f"Error triggering workflow: {str(e)}", exc_info=True)
            return {
                'execution_id': None,
                'workflow_id': workflow_id,
                'status': 'failed',
                'github_run_id': None,
                'message': f'Error: {str(e)}'
            }
    
    async def _update_run_id(self, execution_id: str, org_name: str, repo_name: str, workflow_id: str, user_id: str):
        """
        Background task to update execution with GitHub run_id
        Polls recent workflow runs to find the matching one
        """
        try:
            # Wait a bit for GitHub to create the run
            await asyncio.sleep(2)
            
            # Get recent workflow runs
            url = f"{self.github_service_url}/api/workflows/{org_name}/{repo_name}/{workflow_id}/runs"
            
            response = await self.http_client.get(
                url,
                headers={'X-User-Id': user_id},
                params={'per_page': 5}  # Get latest 5 runs
            )
            
            if response.status_code == 200:
                runs = response.json().get('workflow_runs', [])
                if runs:
                    # Get the most recent run
                    latest_run = runs[0]
                    github_run_id = latest_run.get('id')
                    
                    # Update execution record
                    from database.config import db_manager
                    async with db_manager.get_session() as session:
                        execution_repo = WorkflowExecutionRepository()
                        await execution_repo.update_execution_status(
                            session=session,
                            execution_id=execution_id,
                            status=ExecutionStatus.RUNNING,
                            github_run_id=github_run_id
                        )
                        await session.commit()
                    
                    logger.info(f"Updated execution {execution_id} with run_id {github_run_id}")
                    
                    # Start polling for status updates
                    asyncio.create_task(self._poll_execution_status(execution_id, org_name, repo_name, github_run_id, user_id))
        
        except Exception as e:
            logger.error(f"Error updating run_id: {str(e)}", exc_info=True)
    
    async def get_execution_status(
        self,
        org_name: str,
        repo_name: str,
        run_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get current status of a workflow execution from GitHub
        
        Args:
            org_name: GitHub organization/owner
            repo_name: Repository name
            run_id: GitHub workflow run ID
            user_id: User ID for auth
        
        Returns:
            {
                'status': str,
                'conclusion': str,
                'started_at': str,
                'completed_at': str,
                'duration_seconds': int,
                'jobs': List[Dict]
            }
        """
        try:
            # Get run details from GitHub Service
            url = f"{self.github_service_url}/api/workflows/{org_name}/{repo_name}/runs/{run_id}"
            
            response = await self.http_client.get(
                url,
                headers={'X-User-Id': user_id}
            )
            
            if response.status_code == 200:
                run_data = response.json()
                
                # Calculate duration
                started_at = run_data.get('created_at') or run_data.get('run_started_at')
                completed_at = run_data.get('updated_at')
                
                duration_seconds = None
                if started_at and completed_at:
                    start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                    duration_seconds = int((end - start).total_seconds())
                
                # Get jobs for this run
                jobs = await self._get_run_jobs(org_name, repo_name, run_id, user_id)
                
                return {
                    'status': run_data.get('status', 'unknown'),
                    'conclusion': run_data.get('conclusion'),
                    'started_at': started_at,
                    'completed_at': completed_at,
                    'duration_seconds': duration_seconds,
                    'jobs': jobs
                }
            
            else:
                logger.error(f"Failed to get run status: {response.status_code}")
                return {
                    'status': 'unknown',
                    'conclusion': None,
                    'started_at': None,
                    'completed_at': None,
                    'duration_seconds': None,
                    'jobs': []
                }
        
        except Exception as e:
            logger.error(f"Error getting execution status: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'conclusion': None,
                'started_at': None,
                'completed_at': None,
                'duration_seconds': None,
                'jobs': []
            }
    
    async def _get_run_jobs(self, org_name: str, repo_name: str, run_id: int, user_id: str) -> List[Dict]:
        """Get jobs for a workflow run"""
        try:
            url = f"{self.github_service_url}/api/workflows/{org_name}/{repo_name}/runs/{run_id}/jobs"
            
            response = await self.http_client.get(
                url,
                headers={'X-User-Id': user_id}
            )
            
            if response.status_code == 200:
                jobs_data = response.json().get('jobs', [])
                
                # Extract relevant job information
                jobs = []
                for job in jobs_data:
                    jobs.append({
                        'id': job.get('id'),
                        'name': job.get('name'),
                        'status': job.get('status'),
                        'conclusion': job.get('conclusion'),
                        'started_at': job.get('started_at'),
                        'completed_at': job.get('completed_at'),
                        'steps': [
                            {
                                'name': step.get('name'),
                                'status': step.get('status'),
                                'conclusion': step.get('conclusion'),
                                'number': step.get('number')
                            }
                            for step in job.get('steps', [])
                        ]
                    })
                
                return jobs
            
            return []
        
        except Exception as e:
            logger.error(f"Error getting run jobs: {str(e)}")
            return []
    
    async def _poll_execution_status(self, execution_id: str, org_name: str, repo_name: str, run_id: int, user_id: str):
        """
        Background task to poll execution status until completion
        Updates database with status changes
        """
        from database.config import db_manager
        
        try:
            max_polls = 60  # Poll for max 30 minutes (60 * 30s)
            poll_count = 0
            
            while poll_count < max_polls:
                await asyncio.sleep(30)  # Poll every 30 seconds
                poll_count += 1
                
                # Get current status from GitHub
                status_data = await self.get_execution_status(org_name, repo_name, run_id, user_id)
                
                github_status = status_data['status']
                conclusion = status_data['conclusion']
                
                # Map GitHub status to our ExecutionStatus
                if github_status == 'completed':
                    if conclusion == 'success':
                        new_status = ExecutionStatus.SUCCESS
                    elif conclusion == 'failure':
                        new_status = ExecutionStatus.FAILURE
                    elif conclusion == 'cancelled':
                        new_status = ExecutionStatus.CANCELLED
                    elif conclusion == 'timed_out':
                        new_status = ExecutionStatus.TIMEOUT
                    else:
                        new_status = ExecutionStatus.FAILURE
                    
                    # Update execution with final status
                    async with db_manager.get_session() as session:
                        execution_repo = WorkflowExecutionRepository()
                        metrics_repo = MetricsRepository()
                        
                        await execution_repo.update_execution_status(
                            session=session,
                            execution_id=execution_id,
                            status=new_status,
                            steps=status_data['jobs'],
                            duration_seconds=status_data['duration_seconds']
                        )
                        
                        # Update metrics
                        await metrics_repo.update_metrics_after_execution(
                            session=session,
                            org_name=org_name,
                            workflow_id=f"{repo_name}/{github_status}",
                            duration_seconds=status_data['duration_seconds'] or 0,
                            success=(new_status == ExecutionStatus.SUCCESS)
                        )
                        
                        await session.commit()
                    
                    logger.info(f"Execution {execution_id} completed with status {new_status}")
                    break
                
                elif github_status in ['queued', 'in_progress']:
                    # Still running, update status if needed
                    async with db_manager.get_session() as session:
                        execution_repo = WorkflowExecutionRepository()
                        await execution_repo.update_execution_status(
                            session=session,
                            execution_id=execution_id,
                            status=ExecutionStatus.RUNNING,
                            steps=status_data['jobs']
                        )
                        await session.commit()
                    logger.debug(f"Execution {execution_id} still running (poll {poll_count})")
                
                else:
                    # Unknown status
                    logger.warning(f"Unknown GitHub status: {github_status}")
                    break
            
            if poll_count >= max_polls:
                # Timeout - stopped polling
                logger.warning(f"Stopped polling execution {execution_id} after {max_polls} attempts")
                async with db_manager.get_session() as session:
                    execution_repo = WorkflowExecutionRepository()
                    await execution_repo.update_execution_status(
                        session=session,
                        execution_id=execution_id,
                        status=ExecutionStatus.TIMEOUT
                    )
                    await session.commit()
        
        except Exception as e:
            logger.error(f"Error polling execution status: {str(e)}", exc_info=True)
    
    async def cancel_execution(self, org_name: str, repo_name: str, run_id: int, user_id: str) -> bool:
        """
        Cancel a running workflow execution
        
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            url = f"{self.github_service_url}/api/workflows/{org_name}/{repo_name}/runs/{run_id}/cancel"
            
            response = await self.http_client.post(
                url,
                headers={'X-User-Id': user_id}
            )
            
            if response.status_code == 202:
                logger.info(f"Cancelled workflow run {run_id}")
                return True
            
            logger.error(f"Failed to cancel run: {response.status_code}")
            return False
        
        except Exception as e:
            logger.error(f"Error cancelling execution: {str(e)}", exc_info=True)
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
