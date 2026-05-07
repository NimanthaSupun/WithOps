"""
Database operations for Workspace Intelligence
Handles saving and retrieving analysis results, findings, and maturity scores
"""

from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from database.models import (
    ProjectAnalysis,
    RepositoryFinding,
    MaturityScore,
    WorkflowEmbedding,
    QueryHistory
)

logger = logging.getLogger(__name__)


class WorkspaceIntelligenceDB:
    """
    Database operations for workspace intelligence features
    """
    
    @staticmethod
    async def save_project_analysis(
        db: Session,
        repository_tree_id: str,
        project_id: str,
        project_name: str,
        org_name: str,
        user_id: str,
        analysis_result: Dict
    ) -> ProjectAnalysis:
        """
        Save project analysis results to database
        
        Args:
            db: Database session
            repository_tree_id: ID of the repository tree
            project_id: ID of the project/folder being analyzed
            project_name: Name of the project
            org_name: Organization name
            user_id: User who triggered the analysis
            analysis_result: Analysis results dictionary
            
        Returns:
            ProjectAnalysis model instance
        """
        try:
            maturity = analysis_result.get('maturity', {})
            findings_count = analysis_result.get('findings_count', {})
            
            # Create project analysis record (user_id can be None if user doesn't exist)
            analysis = ProjectAnalysis(
                repository_tree_id=repository_tree_id,
                project_id=project_id,
                project_name=project_name,
                organization_name=org_name,
                user_id=None,  # Make optional for now - will be set if user exists
                status='completed',
                started_at=datetime.fromisoformat(analysis_result.get('analyzed_at', datetime.utcnow().isoformat())),
                completed_at=datetime.utcnow(),
                overall_maturity_score=maturity.get('overall_maturity_score', 0),
                maturity_level=str(maturity.get('maturity_level', 0)),
                implementation_score=maturity.get('domain_scores', {}).get('technology', {}).get('score', 0),
                build_deployment_score=maturity.get('domain_scores', {}).get('process', {}).get('score', 0),
                verification_score=maturity.get('domain_scores', {}).get('technology', {}).get('score', 0),  # Can be split further
                information_gathering_score=0,  # Future implementation
                total_repositories=analysis_result.get('repository_count', 0),
                repositories_analyzed=analysis_result.get('repository_count', 0),
                total_workflows=analysis_result.get('workflow_count', 0),
                critical_findings=findings_count.get('critical', 0),
                high_findings=findings_count.get('high', 0),
                medium_findings=findings_count.get('medium', 0),
                low_findings=findings_count.get('low', 0),
                detected_practices=analysis_result.get('detected_practices', {}),  # Store aggregated practices
                analysis_config={'version': '1.0', 'analyzer': 'workspace_analyzer'}
            )
            
            db.add(analysis)
            await db.flush()  # Get the ID (must await for async session)
            
            # Save findings
            await WorkspaceIntelligenceDB._save_findings(
                db,
                analysis.id,
                analysis_result.get('repositories', [])
            )
            
            # Save maturity scores
            await WorkspaceIntelligenceDB._save_maturity_scores(
                db,
                analysis.id,
                maturity
            )
            
            await db.commit()  # Must await for async session
            logger.info(f"✅ Saved analysis for project: {project_name}")
            
            return analysis
            
        except Exception as e:
            await db.rollback()  # Must await for async session
            logger.error(f"❌ Failed to save project analysis: {str(e)}")
            raise
    
    @staticmethod
    async def _save_findings(
        db: Session,
        analysis_id: str,
        repositories: List[Dict]
    ):
        """Save repository findings"""
        for repo in repositories:
            repo_name = repo.get('repository_name', 'Unknown')
            findings = repo.get('findings', [])
            
            for finding in findings:
                finding_record = RepositoryFinding(
                    analysis_id=analysis_id,
                    repository_name=repo_name,
                    repository_full_name=repo_name,  # Can be enhanced
                    finding_type=finding.get('finding_type'),
                    category=finding.get('category'),
                    severity=finding.get('severity'),
                    title=finding.get('title'),
                    description=finding.get('description'),
                    detected_by=finding.get('detected_by'),
                    confidence=finding.get('confidence'),
                    recommendation=finding.get('recommendation'),
                    remediation_effort=finding.get('remediation_effort'),
                    priority=WorkspaceIntelligenceDB._severity_to_priority(finding.get('severity')),
                    status='open',
                    metadata=finding.get('metadata', {})
                )
                db.add(finding_record)
    
    @staticmethod
    async def _save_maturity_scores(
        db: Session,
        analysis_id: str,
        maturity: Dict
    ):
        """Save detailed maturity scores"""
        domain_scores = maturity.get('domain_scores', {})
        
        for domain_name, domain_data in domain_scores.items():
            activities = domain_data.get('activities', {})
            
            for activity_key, activity_data in activities.items():
                score_record = MaturityScore(
                    analysis_id=analysis_id,
                    dimension=domain_name,
                    sub_dimension=activity_data.get('activity_name'),
                    score=activity_data.get('score', 0),
                    max_score=100,
                    level=activity_data.get('level', 0),
                    practices_found=activity_data.get('detected_tools', []),
                    practices_missing=[],  # Can be enhanced
                    recommendations=[activity_data.get('description', '')],
                    weight=1.0
                )
                db.add(score_record)
    
    @staticmethod
    def _severity_to_priority(severity: str) -> int:
        """Convert severity to priority number"""
        severity_map = {
            'critical': 1,
            'high': 2,
            'medium': 3,
            'low': 4,
            'info': 5
        }
        return severity_map.get(severity, 5)
    
    @staticmethod
    async def get_latest_analysis(
        db: Session,
        project_id: str
    ) -> Optional[ProjectAnalysis]:
        """Get the latest analysis for a project"""
        try:
            from sqlalchemy import select, desc
            stmt = select(ProjectAnalysis)\
                .filter(ProjectAnalysis.project_id == project_id)\
                .order_by(desc(ProjectAnalysis.created_at))\
                .limit(1)
            
            result = await db.execute(stmt)
            analysis = result.scalar_one_or_none()
            
            return analysis
        except Exception as e:
            logger.error(f"Failed to get latest analysis: {str(e)}")
            return None
    
    @staticmethod
    async def get_analysis_with_details(
        db: Session,
        analysis_id: str
    ) -> Optional[Dict]:
        """Get analysis with all findings and scores"""
        try:
            from sqlalchemy import select
            stmt = select(ProjectAnalysis)\
                .filter(ProjectAnalysis.id == analysis_id)
            
            result = await db.execute(stmt)
            analysis = result.scalar_one_or_none()
            
            if not analysis:
                return None
            
            # Get findings
            from sqlalchemy import select
            findings_stmt = select(RepositoryFinding)\
                .filter(RepositoryFinding.analysis_id == analysis_id)
            findings_result = await db.execute(findings_stmt)
            findings = findings_result.scalars().all()
            
            # Get maturity scores
            scores_stmt = select(MaturityScore)\
                .filter(MaturityScore.analysis_id == analysis_id)
            scores_result = await db.execute(scores_stmt)
            scores = scores_result.scalars().all()
            
            return {
                'analysis': analysis,
                'findings': findings,
                'maturity_scores': scores
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis details: {str(e)}")
            return None
    
    @staticmethod
    async def get_all_project_analyses(
        db: Session,
        repository_tree_id: str
    ) -> List[ProjectAnalysis]:
        """Get all analyses for projects in a repository tree"""
        try:
            from sqlalchemy import select, desc
            stmt = select(ProjectAnalysis)\
                .filter(ProjectAnalysis.repository_tree_id == repository_tree_id)\
                .order_by(desc(ProjectAnalysis.created_at))
            
            result = await db.execute(stmt)
            analyses = result.scalars().all()
            
            return analyses
        except Exception as e:
            logger.error(f"Failed to get project analyses: {str(e)}")
            return []
    
    @staticmethod
    async def save_workflow_embedding(
        db: Session,
        org_name: str,
        repo_name: str,
        workflow_path: str,
        workflow_name: str,
        content: str,
        embedding: List[float],
        embedding_model: str,
        detected_tools: Dict,
        triggers: List[str],
        security_practices: Dict
    ) -> WorkflowEmbedding:
        """Save workflow embedding for RAG"""
        try:
            import hashlib
            
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Check if embedding already exists
            existing = db.query(WorkflowEmbedding)\
                .filter(
                    WorkflowEmbedding.organization_name == org_name,
                    WorkflowEmbedding.repository_name == repo_name,
                    WorkflowEmbedding.workflow_path == workflow_path,
                    WorkflowEmbedding.content_hash == content_hash
                )\
                .first()
            
            if existing:
                logger.info(f"Embedding already exists for {workflow_path}")
                return existing
            
            embedding_record = WorkflowEmbedding(
                organization_name=org_name,
                repository_name=repo_name,
                workflow_path=workflow_path,
                workflow_name=workflow_name,
                content=content,
                content_hash=content_hash,
                embedding=embedding,
                embedding_model=embedding_model,
                detected_tools=detected_tools,
                triggers=triggers,
                security_practices=security_practices,
                last_embedded_at=datetime.utcnow()
            )
            
            db.add(embedding_record)
            db.commit()
            
            logger.info(f"✅ Saved embedding for workflow: {workflow_path}")
            return embedding_record
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to save workflow embedding: {str(e)}")
            raise
    
    @staticmethod
    async def save_query_history(
        db: Session,
        user_id: str,
        org_name: str,
        query_text: str,
        response_text: str,
        response_sources: List[Dict],
        context_used: List[Dict],
        processing_time_ms: int
    ) -> QueryHistory:
        """Save RAG query history"""
        try:
            query_record = QueryHistory(
                user_id=user_id,
                organization_name=org_name,
                query_text=query_text,
                response_text=response_text,
                response_sources=response_sources,
                context_used=context_used,
                processing_time_ms=processing_time_ms,
                embeddings_retrieved=len(context_used)
            )
            
            db.add(query_record)
            db.commit()
            
            return query_record
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to save query history: {str(e)}")
            raise
