"""
Database operations for Workspace Intelligence
Handles saving and retrieving analysis results
"""

from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, select
import logging

from database.models import (
    WorkspaceAnalysis,
    ProjectAnalysis,
    RepositoryTree
)

logger = logging.getLogger(__name__)


class WorkspaceIntelligenceDB:
    """
    Database operations for workspace intelligence features
    """
    
    @staticmethod
    async def save_workspace_analysis(
        db: Session,
        user_id: str,
        org_name: str,
        repository_tree_id: str,
        analysis_data: Dict
    ) -> WorkspaceAnalysis:
        """
        Save workspace analysis results to database
        """
        try:
            maturity_score = analysis_data.get('organization_metrics', {}).get('overall_maturity', 0)
            maturity_level = analysis_data.get('organization_metrics', {}).get('maturity_level', 0)
            maturity_label = analysis_data.get('organization_metrics', {}).get('maturity_label', 'Unknown')
            
            summary = analysis_data.get('summary', {})
            
            analysis = WorkspaceAnalysis(
                user_id=user_id,
                organization_name=org_name,
                repository_tree_id=repository_tree_id,
                analysis_type='full_workspace',
                analysis_data=analysis_data,
                maturity_score=maturity_score,
                maturity_level=maturity_level,
                maturity_label=maturity_label,
                total_repositories=summary.get('total_repositories', 0),
                total_workflows=summary.get('total_workflows', 0),
                total_projects=summary.get('total_projects', 0),
                analysis_duration_seconds=analysis_data.get('duration_seconds', 0),
                status='completed'
            )
            
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            
            logger.info(f"Saved workspace analysis {analysis.id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error saving workspace analysis: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def save_project_analysis(
        db: Session,
        repository_tree_id: str,
        project_id: str,
        project_name: str,
        organization_name: str,
        user_id: str,
        project_data: Dict
    ) -> ProjectAnalysis:
        """
        Save individual project analysis to database
        """
        try:
            maturity = project_data.get('maturity', {})
            metrics = project_data.get('metrics', {})
            findings_summary = project_data.get('findings_summary', {})
            
            analysis = ProjectAnalysis(
                repository_tree_id=repository_tree_id,
                project_id=project_id,
                project_name=project_name,
                organization_name=organization_name,
                user_id=user_id,
                status='completed',
                completed_at=datetime.utcnow(),
                overall_maturity_score=maturity.get('overall_score', 0),
                maturity_level=maturity.get('level', 'Unknown'),
                implementation_score=maturity.get('implementation_score', 0),
                build_deployment_score=maturity.get('build_deployment_score', 0),
                verification_score=maturity.get('verification_score', 0),
                information_gathering_score=maturity.get('information_gathering_score', 0),
                total_repositories=metrics.get('total_repositories', 0),
                repositories_analyzed=metrics.get('repositories_analyzed', 0),
                total_workflows=metrics.get('total_workflows', 0),
                critical_findings=findings_summary.get('critical', 0),
                high_findings=findings_summary.get('high', 0),
                medium_findings=findings_summary.get('medium', 0),
                low_findings=findings_summary.get('low', 0),
                detected_practices=project_data.get('detected_practices', {}),
                analysis_config=project_data.get('analysis_config', {})
            )
            
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            
            logger.info(f"Saved project analysis {analysis.id} for project {project_data.get('project_name')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error saving project analysis: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_analysis_with_details(
        db: Session,
        analysis_id: str
    ) -> Optional[ProjectAnalysis]:
        """
        Get project analysis by ID with all details
        """
        try:
            result = await db.execute(
                select(ProjectAnalysis).where(ProjectAnalysis.id == analysis_id)
            )
            analysis = result.scalar_one_or_none()
            
            if analysis:
                logger.info(f"Retrieved analysis {analysis_id}")
            else:
                logger.warning(f"Analysis {analysis_id} not found")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error retrieving analysis: {e}")
            raise