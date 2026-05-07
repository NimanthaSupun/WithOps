"""
Database operations for Workflow Orchestration Service
CRUD operations for workflow trees, executions, scans, and metrics
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from .models import (
    ProjectTree, WorkflowTree, WorkflowExecution, WorkflowSecurityScan,
    WorkflowCanvasDesign, WorkflowMetric,
    ExecutionStatus, ScanRiskLevel
)

logger = logging.getLogger(__name__)


class ProjectTreeRepository:
    """Project tree operations using main schema project_trees table"""
    
    @staticmethod
    async def get_tree(session: AsyncSession, org_name: str, user_id: str) -> Optional[ProjectTree]:
        """Get project tree for organization and user"""
        # First get organization by login name
        from sqlalchemy import text
        
        # Query to get organization_id and user internal id
        org_query = text("""
            SELECT o.id as org_id, u.id as user_db_id
            FROM organizations o
            CROSS JOIN users u
            WHERE o.login = :org_name AND u.auth_user_id = :user_id
        """)
        
        result = await session.execute(org_query, {"org_name": org_name, "user_id": user_id})
        row = result.first()
        
        if not row:
            logger.warning(f"Organization or user not found: {org_name} / {user_id}")
            return None
        
        org_id, user_db_id = row.org_id, row.user_db_id
        
        # Get project tree
        stmt = select(ProjectTree).where(
            and_(
                ProjectTree.organization_id == org_id,
                ProjectTree.user_id == user_db_id,
                ProjectTree.is_active == True
            )
        ).order_by(ProjectTree.updated_at.desc())
        
        result = await session.execute(stmt)
        return result.scalars().first()
    
    @staticmethod
    async def save_tree(
        session: AsyncSession,
        org_name: str,
        user_id: str,
        tree_data: List[Dict[str, Any]]
    ) -> ProjectTree:
        """Save or update project tree"""
        from sqlalchemy import text
        import uuid
        
        # Get organization and user IDs
        org_query = text("""
            SELECT o.id as org_id, u.id as user_db_id
            FROM organizations o
            CROSS JOIN users u
            WHERE o.login = :org_name AND u.auth_user_id = :user_id
        """)
        
        result = await session.execute(org_query, {"org_name": org_name, "user_id": user_id})
        row = result.first()
        
        if not row:
            raise ValueError(f"Organization or user not found: {org_name} / {user_id}")
        
        org_id, user_db_id = row.org_id, row.user_db_id
        
        # Check if project tree exists
        stmt = select(ProjectTree).where(
            and_(
                ProjectTree.organization_id == org_id,
                ProjectTree.user_id == user_db_id,
                ProjectTree.is_active == True
            )
        )
        
        result = await session.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            # Update existing tree
            existing.tree_data = tree_data
            existing.updated_at = datetime.utcnow()
            existing.version += 1
            
            await session.flush()
            logger.info(f"✅ Updated project tree for {org_name} (user: {user_id})")
            return existing
        else:
            # Create new tree
            tree = ProjectTree(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                user_id=user_db_id,
                tree_data=tree_data,
                name="Project Structure",
                version=1,
                is_active=True
            )
            session.add(tree)
            await session.flush()
            logger.info(f"✅ Created project tree for {org_name} (user: {user_id})")
            return tree


class WorkflowTreeRepository:
    """Workflow tree management operations"""
    
    @staticmethod
    async def get_tree(session: AsyncSession, org_name: str, user_id: str) -> Optional[WorkflowTree]:
        """Get workflow tree for organization and user"""
        stmt = select(WorkflowTree).where(
            and_(
                WorkflowTree.org_name == org_name,
                WorkflowTree.user_id == user_id
            )
        )
        result = await session.execute(stmt)
        return result.scalars().first()
    
    @staticmethod
    async def save_tree(
        session: AsyncSession,
        org_name: str,
        user_id: str,
        tree_data: Dict[str, Any]
    ) -> WorkflowTree:
        """Save or update workflow tree"""
        existing = await WorkflowTreeRepository.get_tree(session, org_name, user_id)
        
        if existing:
            # Update existing tree
            existing.tree_data = tree_data
            existing.updated_at = datetime.utcnow()
            existing.last_accessed = datetime.utcnow()
            existing.version += 1
            
            # Count nodes
            node_count, workflow_count, folder_count = WorkflowTreeRepository._count_nodes(tree_data)
            existing.node_count = node_count
            existing.workflow_count = workflow_count
            existing.folder_count = folder_count
            
            await session.flush()
            logger.info(f"✅ Updated tree for {org_name} (user: {user_id})")
            return existing
        else:
            # Create new tree
            node_count, workflow_count, folder_count = WorkflowTreeRepository._count_nodes(tree_data)
            
            tree = WorkflowTree(
                user_id=user_id,
                org_name=org_name,
                tree_data=tree_data,
                node_count=node_count,
                workflow_count=workflow_count,
                folder_count=folder_count
            )
            session.add(tree)
            await session.flush()
            logger.info(f"✅ Created tree for {org_name} (user: {user_id})")
            return tree
    
    @staticmethod
    def _count_nodes(tree_data: Any, counts: Dict[str, int] = None) -> tuple:
        """Recursively count nodes in tree"""
        if counts is None:
            counts = {"total": 0, "workflows": 0, "folders": 0}
        
        if isinstance(tree_data, list):
            for node in tree_data:
                WorkflowTreeRepository._count_nodes(node, counts)
        elif isinstance(tree_data, dict):
            counts["total"] += 1
            node_type = tree_data.get("type", "")
            if node_type == "workflow":
                counts["workflows"] += 1
            elif node_type == "folder":
                counts["folders"] += 1
            
            if "children" in tree_data:
                WorkflowTreeRepository._count_nodes(tree_data["children"], counts)
        
        return counts["total"], counts["workflows"], counts["folders"]


class WorkflowExecutionRepository:
    """Workflow execution operations"""
    
    @staticmethod
    async def create_execution(
        session: AsyncSession,
        workflow_id: str,
        org_name: str,
        repo_name: str,
        workflow_name: str,
        workflow_path: str,
        triggered_by: str,
        parameters: Optional[Dict] = None,
        inputs: Optional[Dict] = None
    ) -> WorkflowExecution:
        """Create new workflow execution record"""
        
        # Get next execution number for this workflow
        stmt = select(func.max(WorkflowExecution.execution_number)).where(
            WorkflowExecution.workflow_id == workflow_id
        )
        result = await session.execute(stmt)
        max_number = result.scalar() or 0
        
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            execution_number=max_number + 1,
            org_name=org_name,
            repo_name=repo_name,
            workflow_name=workflow_name,
            workflow_path=workflow_path,
            triggered_by=triggered_by,
            parameters=parameters,
            inputs=inputs,
            status=ExecutionStatus.PENDING
        )
        
        session.add(execution)
        await session.flush()
        logger.info(f"✅ Created execution #{execution.execution_number} for {workflow_name}")
        return execution
    
    @staticmethod
    async def update_execution_status(
        session: AsyncSession,
        execution_id: str,
        status: ExecutionStatus,
        steps: Optional[Dict] = None,
        github_run_id: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[WorkflowExecution]:
        """Update execution status"""
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        result = await session.execute(stmt)
        execution = result.scalars().first()
        
        if execution:
            execution.status = status
            
            if github_run_id:
                execution.github_run_id = github_run_id
            
            if status == ExecutionStatus.RUNNING and not execution.started_at:
                execution.started_at = datetime.utcnow()
            
            if status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILURE, ExecutionStatus.CANCELLED, ExecutionStatus.TIMEOUT]:
                execution.completed_at = datetime.utcnow()
                if execution.started_at:
                    execution.duration_seconds = int((execution.completed_at - execution.started_at).total_seconds())
            
            if duration_seconds is not None:
                execution.duration_seconds = duration_seconds
            
            if steps:
                execution.steps = steps
            
            if error_message:
                execution.error_message = error_message
            
            await session.flush()
            logger.info(f"✅ Updated execution {execution_id} status to {status}")
        
        return execution
    
    @staticmethod
    async def get_execution_history(
        session: AsyncSession,
        workflow_id: str,
        org_name: str,
        repo_name: str,
        limit: int = 10
    ) -> List[WorkflowExecution]:
        """Get execution history for a workflow"""
        stmt = select(WorkflowExecution).where(
            and_(
                WorkflowExecution.org_name == org_name,
                WorkflowExecution.repo_name == repo_name,
                WorkflowExecution.workflow_id == workflow_id
            )
        ).order_by(desc(WorkflowExecution.created_at)).limit(limit)
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_execution_by_id(session: AsyncSession, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by ID"""
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        result = await session.execute(stmt)
        return result.scalars().first()


class SecurityScanRepository:
    """Security scan operations"""
    
    @staticmethod
    async def create_scan(
        session: AsyncSession,
        user_id: str,
        org_name: str,
        repo_name: str,
        workflow_id: str,
        scan_type: str,
        risk_level: ScanRiskLevel,
        risk_score: float,
        findings: List[Dict],
        recommendations: List[str]
    ) -> WorkflowSecurityScan:
        """Create security scan record"""
        
        # Count finding categories
        secrets_found = sum(1 for f in findings if f.get('category') == 'secrets')
        unsafe_actions = sum(1 for f in findings if f.get('category') == 'unsafe_actions')
        permission_issues = sum(1 for f in findings if f.get('category') == 'permissions')
        script_injection_risks = sum(1 for f in findings if f.get('category') == 'injection')
        
        scan = WorkflowSecurityScan(
            scan_type=scan_type,
            org_name=org_name,
            repo_name=repo_name,
            workflow_id=workflow_id,
            scanned_by=user_id,
            risk_level=risk_level,
            risk_score=risk_score,
            findings=findings,
            recommendations=recommendations,
            secrets_found=secrets_found,
            unsafe_actions=unsafe_actions,
            permission_issues=permission_issues,
            script_injection_risks=script_injection_risks
        )
        
        session.add(scan)
        await session.flush()
        logger.info(f"✅ Created {scan_type} security scan for {org_name} (risk: {risk_level})")
        return scan
    
    @staticmethod
    async def get_latest_scans(
        session: AsyncSession,
        org_name: str,
        scan_type: Optional[str] = None,
        limit: int = 10
    ) -> List[WorkflowSecurityScan]:
        """Get latest security scans"""
        stmt = select(WorkflowSecurityScan).where(
            WorkflowSecurityScan.org_name == org_name
        )
        
        if scan_type:
            stmt = stmt.where(WorkflowSecurityScan.scan_type == scan_type)
        
        stmt = stmt.order_by(desc(WorkflowSecurityScan.created_at)).limit(limit)
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_scan_by_id(session: AsyncSession, scan_id: str) -> Optional[WorkflowSecurityScan]:
        """Get scan by ID"""
        stmt = select(WorkflowSecurityScan).where(WorkflowSecurityScan.id == scan_id)
        result = await session.execute(stmt)
        return result.scalars().first()


class CanvasDesignRepository:
    """Canvas design operations"""
    
    @staticmethod
    async def save_canvas(
        session: AsyncSession,
        user_id: str,
        org_name: str,
        repo_name: str,
        design_data: Dict,
        relationships: Optional[List[Dict]] = None,
        canvas_metadata: Optional[Dict] = None
    ) -> WorkflowCanvasDesign:
        """Save or update canvas design"""
        
        # Check if design exists for this org/repo/user
        stmt = select(WorkflowCanvasDesign).where(
            and_(
                WorkflowCanvasDesign.org_name == org_name,
                WorkflowCanvasDesign.repo_name == repo_name,
                WorkflowCanvasDesign.user_id == user_id
            )
        )
        result = await session.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            existing.design_data = design_data
            existing.relationships = relationships or []
            existing.canvas_metadata = canvas_metadata or {}
            existing.updated_at = datetime.utcnow()
            existing.version += 1
            await session.flush()
            return existing
        else:
            design = WorkflowCanvasDesign(
                user_id=user_id,
                org_name=org_name,
                repo_name=repo_name,
                design_data=design_data,
                relationships=relationships or [],
                canvas_metadata=canvas_metadata or {}
            )
            session.add(design)
            await session.flush()
            return design
    
    @staticmethod
    async def get_canvas(
        session: AsyncSession,
        org_name: str,
        repo_name: str,
        user_id: str
    ) -> Optional[WorkflowCanvasDesign]:
        """Get canvas design"""
        stmt = select(WorkflowCanvasDesign).where(
            and_(
                WorkflowCanvasDesign.org_name == org_name,
                WorkflowCanvasDesign.repo_name == repo_name,
                WorkflowCanvasDesign.user_id == user_id
            )
        )
        result = await session.execute(stmt)
        return result.scalars().first()


class MetricsRepository:
    """Workflow metrics operations"""
    
    @staticmethod
    async def update_metrics_after_execution(
        session: AsyncSession,
        org_name: str,
        workflow_id: str,
        duration_seconds: int,
        success: bool
    ):
        """Update workflow metrics after execution"""
        
        # Get or create metrics
        stmt = select(WorkflowMetric).where(
            and_(
                WorkflowMetric.org_name == org_name,
                WorkflowMetric.workflow_id == workflow_id
            )
        )
        result = await session.execute(stmt)
        metrics = result.scalars().first()
        
        if not metrics:
            metrics = WorkflowMetric(
                workflow_id=workflow_id,
                org_name=org_name
            )
            session.add(metrics)
        
        # Update counts
        metrics.total_runs += 1
        
        current_time = datetime.utcnow()
        if success:
            metrics.successful_runs += 1
            metrics.last_success_at = current_time
        else:
            metrics.failed_runs += 1
            metrics.last_failure_at = current_time
        
        # Update duration metrics
        if duration_seconds:
            if not metrics.avg_duration_seconds:
                metrics.avg_duration_seconds = duration_seconds
                metrics.min_duration_seconds = duration_seconds
                metrics.max_duration_seconds = duration_seconds
            else:
                total_duration = metrics.avg_duration_seconds * (metrics.total_runs - 1) + duration_seconds
                metrics.avg_duration_seconds = int(total_duration / metrics.total_runs)
                metrics.min_duration_seconds = min(metrics.min_duration_seconds or duration_seconds, duration_seconds)
                metrics.max_duration_seconds = max(metrics.max_duration_seconds or 0, duration_seconds)
        
        # Update success rate
        if metrics.total_runs > 0:
            metrics.success_rate = (metrics.successful_runs / metrics.total_runs) * 100
        
        metrics.last_run_at = current_time
        metrics.updated_at = current_time
        
        await session.flush()
        logger.info(f"✅ Updated metrics for workflow {workflow_id}")

