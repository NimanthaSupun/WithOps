"""
Workspace Analyzer - Organization-Wide DevSecOps Intelligence
Orchestrates comprehensive analysis of entire workspace including:
- All projects/folders and their repositories
- Centralized workflow detection across organization
- Workflow dependency mapping
- Organization-wide maturity assessment
- Cross-project architectural patterns
"""

import asyncio
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import logging
import hashlib
import re
from collections import defaultdict

from .workflow_parser import WorkflowParser
from .security_practice_detector import SecurityPracticeDetector
from .maturity_scorer import MaturityScorer

logger = logging.getLogger(__name__)


class WorkspaceAnalyzer:
    """
    Comprehensive workspace analyzer for DevSecOps intelligence
    Analyzes entire organization including cross-project workflow dependencies
    """
    
    def __init__(self, github_client):
        """
        Initialize workspace analyzer
        
        Args:
            github_client: GitHub client for fetching data
        """
        self.github_client = github_client
        self.workflow_parser = WorkflowParser()
        self.security_detector = SecurityPracticeDetector()
        self.maturity_scorer = MaturityScorer()
        
        # Analysis state
        self.analyzed_workflows = {}  # Cache of parsed workflows
        self.centralized_workflows = {}  # Map of centralized/reusable workflows
        self.workflow_dependencies = defaultdict(list)  # Who calls what
        self.all_repositories = []  # All repos across workspace
    
    async def analyze_workspace(self, 
                                org_name: str, 
                                tree_data: List[Dict],
                                fetch_github_data: bool = True) -> Dict:
        """
        Analyze entire workspace for DevSecOps maturity and intelligence
        
        Args:
            org_name: Organization name
            tree_data: Complete repository tree structure from frontend
            fetch_github_data: Whether to fetch fresh data from GitHub API
            
        Returns:
            Comprehensive workspace analysis results
        """
        start_time = datetime.utcnow()
        logger.info(f"🚀 Starting workspace analysis for organization: {org_name}")
        
        try:
            # Step 1: Extract all repositories and workflows from tree
            all_repos, all_workflows = self._extract_repositories_and_workflows(tree_data)
            self.all_repositories = all_repos
            
            logger.info(f"📊 Found {len(all_repos)} repositories and {len(all_workflows)} workflows")
            
            # Step 2: Parse all workflows
            parsed_workflows = await self._parse_all_workflows(all_workflows)
            
            # Step 3: Detect centralized/reusable workflows
            centralized_workflows = self._detect_centralized_workflows(parsed_workflows)
            
            # Step 4: Map workflow dependencies (who calls what)
            dependency_map = self._map_workflow_dependencies(parsed_workflows)
            
            # Step 5: Fetch additional GitHub data if needed
            github_data = {}
            if fetch_github_data:
                github_data = await self._fetch_github_metadata(org_name, all_repos)
            
            # Step 6: Analyze each project/folder
            project_analyses = await self._analyze_all_projects(
                tree_data, 
                parsed_workflows,
                github_data
            )
            
            # Step 7: Calculate organization-wide metrics
            org_metrics = self._calculate_organization_metrics(
                project_analyses,
                centralized_workflows,
                dependency_map
            )
            
            # Step 8: Generate insights and recommendations
            insights = self._generate_workspace_insights(
                org_metrics,
                centralized_workflows,
                dependency_map,
                project_analyses
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ Workspace analysis completed in {duration:.2f}s")
            
            return {
                'organization': org_name,
                'analyzed_at': start_time.isoformat(),
                'duration_seconds': duration,
                'summary': {
                    'total_projects': len([n for n in tree_data if n.get('type') == 'folder']),
                    'total_repositories': len(all_repos),
                    'total_workflows': len(all_workflows),
                    'centralized_workflows_count': len(centralized_workflows),
                },
                'organization_metrics': org_metrics,
                'centralized_workflows': centralized_workflows,
                'workflow_dependencies': dict(dependency_map),
                'project_analyses': project_analyses,
                'insights': insights,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"❌ Workspace analysis failed: {str(e)}", exc_info=True)
            return {
                'organization': org_name,
                'analyzed_at': datetime.utcnow().isoformat(),
                'status': 'failed',
                'error': str(e)
            }
    
    def _extract_repositories_and_workflows(self, tree_data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Extract all repositories and workflows from tree structure
        
        Returns:
            Tuple of (repositories, workflows)
        """
        repositories = []
        workflows = []
        
        def traverse(nodes, project_id=None, project_name=None):
            for node in nodes:
                if node.get('type') == 'folder':
                    # This is a project
                    proj_id = node.get('id')
                    proj_name = node.get('name')
                    if node.get('children'):
                        traverse(node['children'], proj_id, proj_name)
                
                elif node.get('type') == 'repository':
                    # Add repository with project context
                    repo = {
                        'id': node.get('id'),
                        'name': node.get('name'),
                        'project_id': project_id,
                        'project_name': project_name,
                        'metadata': node.get('metadata', {}),
                        'full_name': node.get('metadata', {}).get('full_name', node.get('name'))
                    }
                    repositories.append(repo)
                    
                    # Extract workflows from this repo
                    if node.get('children'):
                        for child in node['children']:
                            if child.get('type') == 'workflow':
                                workflow = {
                                    'id': child.get('id'),
                                    'name': child.get('name'),
                                    'repository_id': node.get('id'),
                                    'repository_name': node.get('name'),
                                    'project_id': project_id,
                                    'project_name': project_name,
                                    'content': child.get('content', ''),
                                    'metadata': child.get('metadata', {}),
                                    'path': child.get('metadata', {}).get('path', f'.github/workflows/{child.get("name")}')
                                }
                                workflows.append(workflow)
        
        traverse(tree_data)
        return repositories, workflows
    
    async def _parse_all_workflows(self, workflows: List[Dict]) -> Dict[str, Dict]:
        """
        Parse all workflow files
        
        Returns:
            Dictionary mapping workflow_id to parsed data
        """
        parsed = {}
        
        for workflow in workflows:
            workflow_id = workflow['id']
            content = workflow.get('content', '')
            
            if content:
                try:
                    parsed_data = self.workflow_parser.parse_workflow(
                        content,
                        workflow.get('path', workflow['name'])
                    )
                    
                    # Add context
                    parsed_data['workflow_id'] = workflow_id
                    parsed_data['repository_name'] = workflow['repository_name']
                    parsed_data['project_id'] = workflow.get('project_id')
                    parsed_data['project_name'] = workflow.get('project_name')
                    
                    parsed[workflow_id] = parsed_data
                    
                except Exception as e:
                    logger.error(f"Failed to parse workflow {workflow['name']}: {str(e)}")
                    parsed[workflow_id] = {
                        'workflow_id': workflow_id,
                        'parse_status': 'error',
                        'parse_error': str(e)
                    }
            
            # Small delay to avoid overwhelming the system
            if len(workflows) > 50:
                await asyncio.sleep(0.01)
        
        logger.info(f"✅ Parsed {len(parsed)} workflows")
        return parsed
    
    def _detect_centralized_workflows(self, parsed_workflows: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Detect centralized/reusable workflows in the organization
        
        A workflow is considered centralized if:
        1. It's marked as reusable (workflow_call trigger)
        2. It's called by other workflows
        """
        centralized = {}
        
        for workflow_id, parsed in parsed_workflows.items():
            if parsed.get('is_reusable'):
                # This is a reusable workflow
                centralized[workflow_id] = {
                    'workflow_id': workflow_id,
                    'workflow_name': parsed.get('workflow_name'),
                    'repository': parsed.get('repository_name'),
                    'project': parsed.get('project_name'),
                    'path': parsed.get('workflow_path'),
                    'is_reusable': True,
                    'called_by': [],  # Will be populated later
                    'detected_tools': parsed.get('detected_tools', {}),
                    'type': 'centralized'
                }
        
        logger.info(f"🎯 Detected {len(centralized)} centralized/reusable workflows")
        return centralized
    
    def _map_workflow_dependencies(self, parsed_workflows: Dict[str, Dict]) -> Dict[str, List[Dict]]:
        """
        Map workflow dependencies - which workflows call which reusable workflows
        
        Returns:
            Dictionary mapping workflow_id to list of workflows it calls
        """
        dependency_map = defaultdict(list)
        
        for workflow_id, parsed in parsed_workflows.items():
            calls_reusable = parsed.get('calls_reusable', [])
            
            if calls_reusable:
                for reusable_ref in calls_reusable:
                    # Parse the reusable workflow reference
                    # Format: owner/repo/.github/workflows/workflow.yml@ref
                    match = re.match(r'([^/]+)/([^/]+)/(.+\.ya?ml)(@.+)?', reusable_ref)
                    
                    if match:
                        owner, repo, workflow_path, ref = match.groups()
                        
                        dependency_map[workflow_id].append({
                            'reusable_workflow': reusable_ref,
                            'owner': owner,
                            'repository': repo,
                            'workflow_path': workflow_path,
                            'ref': ref or '@main',
                            'caller_workflow': parsed.get('workflow_name'),
                            'caller_repository': parsed.get('repository_name'),
                            'caller_project': parsed.get('project_name')
                        })
        
        logger.info(f"🔗 Mapped {len(dependency_map)} workflow dependencies")
        return dependency_map
    
    async def _fetch_github_metadata(self, org_name: str, repositories: List[Dict]) -> Dict:
        """
        Fetch additional metadata from GitHub API
        Currently returns empty dict - can be extended to fetch:
        - Branch protection rules
        - CODEOWNERS files
        - Repository settings
        """
        # TODO: Implement GitHub API calls for additional data
        # For now, we'll work with what we have from the tree
        logger.info(f"ℹ️ GitHub metadata fetch not yet implemented (using tree data)")
        return {}
    
    async def _analyze_all_projects(self,
                                    tree_data: List[Dict],
                                    parsed_workflows: Dict[str, Dict],
                                    github_data: Dict) -> List[Dict]:
        """
        Analyze each project/folder in the workspace
        """
        project_analyses = []
        
        for node in tree_data:
            if node.get('type') == 'folder':
                # This is a project
                analysis = await self._analyze_project(
                    node,
                    parsed_workflows,
                    github_data
                )
                project_analyses.append(analysis)
        
        return project_analyses
    
    async def _analyze_project(self,
                               project_node: Dict,
                               parsed_workflows: Dict[str, Dict],
                               github_data: Dict) -> Dict:
        """
        Analyze a single project/folder
        """
        project_id = project_node.get('id')
        project_name = project_node.get('name')
        
        logger.info(f"📁 Analyzing project: {project_name}")
        
        # Get all repos in this project
        repos_in_project = []
        workflows_in_project = []
        
        def get_project_content(children):
            for child in children or []:
                if child.get('type') == 'repository':
                    repos_in_project.append(child)
                    # Get workflows
                    for wf_child in child.get('children', []):
                        if wf_child.get('type') == 'workflow':
                            workflows_in_project.append(wf_child.get('id'))
        
        get_project_content(project_node.get('children', []))
        
        # Analyze each repository
        repo_analyses = []
        all_findings = []
        
        for repo in repos_in_project:
            repo_analysis = await self._analyze_repository(
                repo,
                parsed_workflows,
                github_data
            )
            repo_analyses.append(repo_analysis)
            all_findings.extend(repo_analysis.get('findings', []))
        
        # Aggregate detected practices across all repos
        aggregated_practices = self._aggregate_practices(repo_analyses)
        
        # Calculate project maturity
        total_workflows = len(workflows_in_project)
        maturity = self.maturity_scorer.calculate_maturity(
            aggregated_practices,
            total_workflows,
            total_workflows > 0
        )
        
        # Count findings by severity
        findings_count = {
            'critical': len([f for f in all_findings if f['severity'] == 'critical']),
            'high': len([f for f in all_findings if f['severity'] == 'high']),
            'medium': len([f for f in all_findings if f['severity'] == 'medium']),
            'low': len([f for f in all_findings if f['severity'] == 'low']),
            'info': len([f for f in all_findings if f['severity'] == 'info']),
        }
        
        return {
            'project_id': project_id,
            'project_name': project_name,
            'repository_count': len(repos_in_project),
            'workflow_count': len(workflows_in_project),
            'maturity': maturity,
            'findings_count': findings_count,
            'total_findings': len(all_findings),
            'repositories': repo_analyses,
            'detected_practices': aggregated_practices,
            'analyzed_at': datetime.utcnow().isoformat()
        }
    
    async def _analyze_repository(self,
                                  repo_node: Dict,
                                  parsed_workflows: Dict[str, Dict],
                                  github_data: Dict) -> Dict:
        """
        Analyze a single repository
        """
        repo_name = repo_node.get('name')
        repo_metadata = repo_node.get('metadata', {})
        
        # Get workflows for this repo
        repo_workflows = []
        for child in repo_node.get('children', []):
            if child.get('type') == 'workflow':
                workflow_id = child.get('id')
                if workflow_id in parsed_workflows:
                    repo_workflows.append(parsed_workflows[workflow_id])
        
        # Get branch protection from metadata or github_data
        branch_protection = repo_metadata.get('branch_protection', None)
        has_codeowners = repo_metadata.get('has_codeowners', False)
        
        # Analyze using SecurityPracticeDetector
        analysis = self.security_detector.analyze_repository(
            {'name': repo_name, **repo_metadata},
            repo_workflows,
            branch_protection,
            has_codeowners
        )
        
        return analysis
    
    def _aggregate_practices(self, repo_analyses: List[Dict]) -> Dict:
        """
        Aggregate detected practices across multiple repositories
        ✅ ONLY counts repositories that HAVE workflows
        """
        aggregated = {
            'sast_tools': set(),
            'sca_tools': set(),
            'dast_tools': set(),
            'secret_scanning_tools': set(),
            'container_scanning_tools': set(),
            'precommit_hooks': set(),
            'branch_protection_enabled': False,
            'required_reviews': 0,
            'required_status_checks': False,
            'signed_commits_required': False,
            'has_codeowners': False,
            'has_pr_workflows': False,
            'uses_reusable_workflows': False,
            'uses_centralized_workflows': False,
            'pins_action_versions': False,
            'repos_with_workflows': 0,
            'repos_without_workflows': 0,
            'total_repos': 0,
        }
        
        if not repo_analyses:
            return aggregated
        
        for analysis in repo_analyses:
            aggregated['total_repos'] += 1
            
            # ✅ CRITICAL: Skip repos without workflows for scoring
            has_workflows = analysis.get('has_workflows', False)
            if not has_workflows:
                aggregated['repos_without_workflows'] += 1
                continue
            
            aggregated['repos_with_workflows'] += 1
            practices = analysis.get('detected_practices', {})
            
            aggregated['sast_tools'].update(practices.get('sast_tools', []))
            aggregated['sca_tools'].update(practices.get('sca_tools', []))
            aggregated['dast_tools'].update(practices.get('dast_tools', []))
            aggregated['secret_scanning_tools'].update(practices.get('secret_scanning_tools', []))
            aggregated['container_scanning_tools'].update(practices.get('container_scanning_tools', []))
            aggregated['precommit_hooks'].update(practices.get('precommit_hooks', []))
            
            if practices.get('branch_protection_enabled'):
                aggregated['branch_protection_enabled'] = True
            
            aggregated['required_reviews'] = max(
                aggregated['required_reviews'],
                practices.get('required_reviews', 0)
            )
            
            if practices.get('required_status_checks'):
                aggregated['required_status_checks'] = True
            
            if practices.get('signed_commits_required'):
                aggregated['signed_commits_required'] = True
            
            if practices.get('has_codeowners'):
                aggregated['has_codeowners'] = True
            
            if practices.get('has_pr_workflows'):
                aggregated['has_pr_workflows'] = True
            
            if practices.get('uses_reusable_workflows'):
                aggregated['uses_reusable_workflows'] = True
                aggregated['uses_centralized_workflows'] = True  # Same concept
            
            if practices.get('pins_action_versions'):
                aggregated['pins_action_versions'] = True
        
        # Convert sets to lists for JSON serialization
        aggregated['sast_tools'] = list(aggregated['sast_tools'])
        aggregated['sca_tools'] = list(aggregated['sca_tools'])
        aggregated['dast_tools'] = list(aggregated['dast_tools'])
        aggregated['secret_scanning_tools'] = list(aggregated['secret_scanning_tools'])
        aggregated['container_scanning_tools'] = list(aggregated['container_scanning_tools'])
        aggregated['precommit_hooks'] = list(aggregated['precommit_hooks'])
        
        # Add detection summary
        aggregated['has_trivy'] = 'trivy' in aggregated['sast_tools'] or 'trivy' in aggregated['container_scanning_tools']
        aggregated['has_precommit_hooks'] = len(aggregated['precommit_hooks']) > 0
        
        return aggregated
    
    def _calculate_organization_metrics(self,
                                       project_analyses: List[Dict],
                                       centralized_workflows: Dict,
                                       dependency_map: Dict) -> Dict:
        """
        Calculate organization-wide metrics
        """
        if not project_analyses:
            return {
                'overall_maturity': 0,
                'maturity_level': 0,
                'maturity_label': 'Not Started'
            }
        
        # Average maturity across projects
        maturity_scores = [
            p['maturity']['overall_maturity_score'] 
            for p in project_analyses 
            if 'maturity' in p
        ]
        
        avg_maturity = sum(maturity_scores) / len(maturity_scores) if maturity_scores else 0
        
        # Count repos using centralized workflows
        repos_with_centralized = len([
            p for p in project_analyses
            if p.get('detected_practices', {}).get('uses_reusable_workflows')
        ])
        
        total_repos = sum(p.get('repository_count', 0) for p in project_analyses)
        
        centralization_percentage = (
            (repos_with_centralized / total_repos * 100) if total_repos > 0 else 0
        )
        
        return {
            'overall_maturity': round(avg_maturity, 2),
            'maturity_level': self.maturity_scorer._score_to_level(avg_maturity),
            'maturity_label': self.maturity_scorer._level_to_label(
                self.maturity_scorer._score_to_level(avg_maturity)
            ),
            'centralization_percentage': round(centralization_percentage, 2),
            'projects_analyzed': len(project_analyses),
            'total_repositories': total_repos,
            'repos_using_centralized_workflows': repos_with_centralized,
            'centralized_workflows_available': len(centralized_workflows),
            'workflow_dependencies_detected': len(dependency_map)
        }
    
    def _generate_workspace_insights(self,
                                    org_metrics: Dict,
                                    centralized_workflows: Dict,
                                    dependency_map: Dict,
                                    project_analyses: List[Dict]) -> List[Dict]:
        """
        Generate actionable insights for the organization
        """
        insights = []
        
        # Centralization insight
        centralization_pct = org_metrics.get('centralization_percentage', 0)
        if centralization_pct < 30:
            insights.append({
                'type': 'architecture',
                'priority': 'high',
                'title': 'Low Workflow Centralization',
                'description': f'Only {centralization_pct:.0f}% of repositories use centralized workflows.',
                'recommendation': 'Create centralized, reusable deployment workflows to standardize CI/CD processes.',
                'impact': 'Improves consistency, reduces duplication, easier to maintain'
            })
        elif centralization_pct >= 70:
            insights.append({
                'type': 'architecture',
                'priority': 'info',
                'title': 'Strong Workflow Centralization',
                'description': f'{centralization_pct:.0f}% of repositories use centralized workflows.',
                'recommendation': 'Continue promoting reusable workflow patterns across the organization.',
                'impact': 'Excellent architectural maturity'
            })
        
        # Maturity insight
        maturity_level = org_metrics.get('maturity_level', 0)
        if maturity_level < 2:
            insights.append({
                'type': 'maturity',
                'priority': 'high',
                'title': 'DevSecOps Maturity Needs Improvement',
                'description': f'Organization maturity is at level {maturity_level}/3.',
                'recommendation': 'Focus on implementing SAST, SCA, and branch protection across all projects.',
                'impact': 'Significantly improves security posture'
            })
        
        # Project-specific insights
        low_maturity_projects = [
            p for p in project_analyses 
            if p.get('maturity', {}).get('maturity_level', 0) < 2
        ]
        
        if low_maturity_projects:
            insights.append({
                'type': 'projects',
                'priority': 'medium',
                'title': 'Projects Needing Attention',
                'description': f'{len(low_maturity_projects)} projects have maturity below "Managed" level.',
                'projects': [p['project_name'] for p in low_maturity_projects],
                'recommendation': 'Prioritize security improvements in these projects.',
                'impact': 'Raises overall organization maturity'
            })
        
        return insights
