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
        project_data: Dict,
        analysis_scope: str = 'organization',
        folder_id: Optional[str] = None,
        folder_path: Optional[str] = None,
        repositories_in_scope: Optional[List[str]] = None
    ) -> ProjectAnalysis:
        """
        Save individual project analysis to database
        
        Args:
            db: Database session
            repository_tree_id: ID of the repository tree
            project_id: Project identifier
            project_name: Name of the project
            organization_name: Organization name
            user_id: User ID performing analysis
            project_data: Complete analysis data
            analysis_scope: Scope of analysis ('organization', 'folder', 'repository')
            folder_id: ID of folder if scope is 'folder'
            folder_path: Path of folder if scope is 'folder'
            repositories_in_scope: List of repository names included in analysis
        """
        try:
            maturity = project_data.get('maturity', {})
            findings_count = project_data.get('findings_count', {})
            
            # Extract domain scores from nested structure
            domain_scores = maturity.get('domain_scores', {})
            technology_score = domain_scores.get('technology', {}).get('score', 0)
            process_score = domain_scores.get('process', {}).get('score', 0)
            
            analysis = ProjectAnalysis(
                repository_tree_id=repository_tree_id,
                project_id=project_id,
                project_name=project_name,
                organization_name=organization_name,
                user_id=user_id,
                # Folder scope metadata
                analysis_scope=analysis_scope,
                folder_id=folder_id,
                folder_path=folder_path,
                repositories_in_scope=repositories_in_scope,
                # Status
                status='completed',
                completed_at=datetime.utcnow(),
                # Maturity scores - extract from domain_scores structure
                overall_maturity_score=maturity.get('overall_maturity_score', 0),
                maturity_level=str(maturity.get('maturity_level', 'Unknown')),
                implementation_score=technology_score,  # Technology maps to implementation
                build_deployment_score=process_score,   # Process maps to build/deployment
                verification_score=0,  # Not in current structure
                information_gathering_score=0,  # Not in current structure
                # Metrics
                total_repositories=project_data.get('repository_count', 0),
                repositories_analyzed=project_data.get('repository_count', 0),
                total_workflows=project_data.get('workflow_count', 0),
                critical_findings=findings_count.get('critical', 0),
                high_findings=findings_count.get('high', 0),
                medium_findings=findings_count.get('medium', 0),
                low_findings=findings_count.get('low', 0),
                detected_practices=project_data.get('detected_practices', {}),
                analysis_config=project_data.get('analysis_config', {}),
                analysis_data=project_data  # Store complete analysis data with repositories and findings
            )
            
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            
            scope_info = f" (scope: {analysis_scope}" + (f", folder: {folder_path}" if folder_path else "") + ")"
            logger.info(f"Saved project analysis {analysis.id} for project {project_data.get('project_name')}{scope_info}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error saving project analysis: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def save_unified_analysis(
        db: Session,
        repository_tree_id: str,
        organization_name: str,
        user_id: str,
        analysis_result: Dict
    ) -> ProjectAnalysis:
        """
        Save unified workspace analysis as ONE record with project breakdowns
        
        This creates a single analysis record containing organization-wide metrics
        with embedded project_analyses array for drill-down capability.
        
        Args:
            db: Database session
            repository_tree_id: ID of the repository tree
            organization_name: Organization name
            user_id: User ID performing analysis
            analysis_result: Complete analysis result from WorkspaceAnalyzer
        
        Returns:
            Created ProjectAnalysis record with analysis_scope='unified'
        """
        try:
            org_metrics = analysis_result.get('organization_metrics', {})
            project_analyses = analysis_result.get('project_analyses', [])
            summary = analysis_result.get('summary', {})
            
            # Calculate aggregated metrics
            total_repos = sum(p.get('repository_count', 0) for p in project_analyses)
            total_workflows = sum(p.get('workflow_count', 0) for p in project_analyses)
            
            # Aggregate all findings across projects
            all_findings = []
            for project in project_analyses:
                all_findings.extend(project.get('all_findings', []))
            
            findings_count = {
                'critical': len([f for f in all_findings if f.get('severity') == 'critical']),
                'high': len([f for f in all_findings if f.get('severity') == 'high']),
                'medium': len([f for f in all_findings if f.get('severity') == 'medium']),
                'low': len([f for f in all_findings if f.get('severity') == 'low']),
            }
            
            # Calculate average DSOMM scores across projects
            def _average_score(projects, score_key):
                scores = [p.get('maturity', {}).get(f"{score_key}_score", 0) for p in projects if p.get('maturity')]
                return round(sum(scores) / len(scores), 2) if scores else 0
            
            # Aggregate detected practices across all projects
            def _aggregate_practices(projects):
                """Combine practices from all projects"""
                aggregated = {
                    'total_repos': total_repos,
                    'repos_with_workflows': sum(1 for p in projects if p.get('workflow_count', 0) > 0),
                    'uses_centralized_workflows': any(p.get('detected_practices', {}).get('uses_centralized_workflows') for p in projects),
                    'sast_tools': list(set(tool for p in projects for tool in p.get('detected_practices', {}).get('sast_tools', []))),
                    'sca_tools': list(set(tool for p in projects for tool in p.get('detected_practices', {}).get('sca_tools', []))),
                    'dast_tools': list(set(tool for p in projects for tool in p.get('detected_practices', {}).get('dast_tools', []))),
                    'secret_scanning_tools': list(set(tool for p in projects for tool in p.get('detected_practices', {}).get('secret_scanning_tools', []))),
                    'container_scanning_tools': list(set(tool for p in projects for tool in p.get('detected_practices', {}).get('container_scanning_tools', []))),
                    'branch_protection_enabled': any(p.get('detected_practices', {}).get('branch_protection_enabled') for p in projects),
                    'has_codeowners': any(p.get('detected_practices', {}).get('has_codeowners') for p in projects),
                    'required_reviews': max((p.get('detected_practices', {}).get('required_reviews', 0) for p in projects), default=0),
                    'signed_commits_required': any(p.get('detected_practices', {}).get('signed_commits_required') for p in projects),
                    'required_status_checks': any(p.get('detected_practices', {}).get('required_status_checks') for p in projects),
                    'has_pr_workflows': any(p.get('detected_practices', {}).get('has_pr_workflows') for p in projects),
                    'has_precommit_hooks': any(p.get('detected_practices', {}).get('has_precommit_hooks') for p in projects),
                    'precommit_hooks': list(set(hook for p in projects for hook in p.get('detected_practices', {}).get('precommit_hooks', [])))
                }
                return aggregated
            
            # Create single unified analysis record
            analysis = ProjectAnalysis(
                project_name=f"{organization_name} - Unified Workspace",
                organization_name=organization_name,
                repository_tree_id=repository_tree_id,
                user_id=user_id,
                
                # Mark as unified analysis
                analysis_scope='unified',
                
                # Organization-level metrics
                overall_maturity_score=org_metrics.get('overall_maturity', 0),
                maturity_level=str(org_metrics.get('maturity_level', 'Unknown')),
                
                # Average DSOMM scores across all projects
                implementation_score=_average_score(project_analyses, 'implementation'),
                build_deployment_score=_average_score(project_analyses, 'build_deployment'),
                verification_score=_average_score(project_analyses, 'test_verification'),
                information_gathering_score=_average_score(project_analyses, 'information_gathering'),
                
                # Totals
                total_repositories=total_repos,
                repositories_analyzed=total_repos,
                total_workflows=total_workflows,
                
                # Aggregated findings
                critical_findings=findings_count['critical'],
                high_findings=findings_count['high'],
                medium_findings=findings_count['medium'],
                low_findings=findings_count['low'],
                
                # Store complete analysis with project breakdowns
                analysis_data={
                    'organization_metrics': org_metrics,
                    'project_analyses': project_analyses,  # Array of per-folder analyses
                    'centralized_workflows': analysis_result.get('centralized_workflows', {}),
                    'workflow_dependencies': analysis_result.get('workflow_dependencies', {}),
                    'insights': analysis_result.get('insights', []),
                    'summary': summary
                },
                
                # Aggregated practices
                detected_practices=_aggregate_practices(project_analyses),
                
                # Analysis config
                analysis_config={
                    'analysis_type': 'unified_workspace',
                    'fetch_github_data': True,
                    'total_projects': len(project_analyses)
                },
                
                # Status
                status='completed',
                completed_at=datetime.utcnow()
            )
            
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            
            logger.info(f"✅ Saved unified analysis {analysis.id} for {organization_name} ({len(project_analyses)} projects)")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error saving unified analysis: {e}")
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