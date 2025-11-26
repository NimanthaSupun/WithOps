"""
Workflow Parser - Parse GitHub Actions YAML workflows
Extracts steps, jobs, triggers, dependencies, and metadata
"""

import yaml
import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class WorkflowParser:
    """Parse GitHub Actions workflow YAML files"""
    
    @staticmethod
    def parse_workflow(workflow_content: str) -> Dict[str, Any]:
        """
        Parse workflow YAML content and extract structured data
        
        Returns:
            {
                'name': str,
                'triggers': List[str],
                'jobs': List[Dict],
                'steps': List[Dict],
                'uses': List[str],
                'secrets': List[str],
                'permissions': Dict,
                'env': Dict,
                'metadata': Dict
            }
        """
        try:
            # Parse YAML
            workflow_data = yaml.safe_load(workflow_content)
            
            if not workflow_data:
                return WorkflowParser._empty_workflow()
            
            # Extract basic info
            name = workflow_data.get('name', 'Unnamed Workflow')
            
            # Extract triggers
            triggers = WorkflowParser._extract_triggers(workflow_data.get('on', {}))
            
            # Extract jobs
            jobs = WorkflowParser._extract_jobs(workflow_data.get('jobs', {}))
            
            # Extract all steps from all jobs
            all_steps = []
            for job in jobs:
                all_steps.extend(job.get('steps', []))
            
            # Extract used actions
            uses = WorkflowParser._extract_uses(all_steps)
            
            # Extract potential secrets
            secrets = WorkflowParser._extract_secrets(workflow_content)
            
            # Extract permissions
            permissions = workflow_data.get('permissions', {})
            
            # Extract environment variables
            env = workflow_data.get('env', {})
            
            # Metadata
            metadata = {
                'total_jobs': len(jobs),
                'total_steps': len(all_steps),
                'total_actions': len(uses),
                'has_secrets': len(secrets) > 0,
                'has_permissions': len(permissions) > 0
            }
            
            return {
                'name': name,
                'triggers': triggers,
                'jobs': jobs,
                'steps': all_steps,
                'uses': uses,
                'secrets': secrets,
                'permissions': permissions,
                'env': env,
                'metadata': metadata
            }
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            return WorkflowParser._empty_workflow(error=str(e))
        except Exception as e:
            logger.error(f"Workflow parsing error: {e}")
            return WorkflowParser._empty_workflow(error=str(e))
    
    @staticmethod
    def _extract_triggers(on_config: Any) -> List[str]:
        """Extract trigger events from 'on' configuration"""
        triggers = []
        
        if isinstance(on_config, str):
            triggers.append(on_config)
        elif isinstance(on_config, list):
            triggers.extend(on_config)
        elif isinstance(on_config, dict):
            triggers.extend(on_config.keys())
        
        return triggers
    
    @staticmethod
    def _extract_jobs(jobs_config: Dict) -> List[Dict]:
        """Extract job information"""
        jobs = []
        
        for job_id, job_data in jobs_config.items():
            if not isinstance(job_data, dict):
                continue
            
            job_info = {
                'id': job_id,
                'name': job_data.get('name', job_id),
                'runs_on': job_data.get('runs-on', 'ubuntu-latest'),
                'needs': job_data.get('needs', []),
                'if': job_data.get('if'),
                'env': job_data.get('env', {}),
                'steps': WorkflowParser._extract_steps(job_data.get('steps', []))
            }
            
            jobs.append(job_info)
        
        return jobs
    
    @staticmethod
    def _extract_steps(steps_config: List) -> List[Dict]:
        """Extract step information"""
        steps = []
        
        for idx, step_data in enumerate(steps_config):
            if not isinstance(step_data, dict):
                continue
            
            step_info = {
                'id': step_data.get('id', f'step-{idx + 1}'),
                'name': step_data.get('name', f'Step {idx + 1}'),
                'uses': step_data.get('uses'),
                'run': step_data.get('run'),
                'with': step_data.get('with', {}),
                'env': step_data.get('env', {}),
                'if': step_data.get('if'),
                'continue_on_error': step_data.get('continue-on-error', False),
                'timeout_minutes': step_data.get('timeout-minutes'),
                'type': 'action' if step_data.get('uses') else 'script'
            }
            
            steps.append(step_info)
        
        return steps
    
    @staticmethod
    def _extract_uses(steps: List[Dict]) -> List[str]:
        """Extract all GitHub Actions used in workflow"""
        uses = []
        
        for step in steps:
            if step.get('uses'):
                uses.append(step['uses'])
        
        return list(set(uses))  # Remove duplicates
    
    @staticmethod
    def _extract_secrets(workflow_content: str) -> List[str]:
        """Extract potential hardcoded secrets or secret references"""
        secrets = []
        
        # Pattern for secrets.VARIABLE
        secret_pattern = r'\$\{\{\s*secrets\.(\w+)\s*\}\}'
        matches = re.findall(secret_pattern, workflow_content)
        secrets.extend(matches)
        
        # Pattern for potential hardcoded secrets (basic detection)
        # Look for common secret keywords
        hardcoded_patterns = [
            r'(api[_-]?key|apikey)\s*[:=]\s*["\']([^"\']+)["\']',
            r'(password|passwd|pwd)\s*[:=]\s*["\']([^"\']+)["\']',
            r'(token|auth[_-]?token)\s*[:=]\s*["\']([^"\']+)["\']',
            r'(secret|secret[_-]?key)\s*[:=]\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in hardcoded_patterns:
            matches = re.findall(pattern, workflow_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    secrets.append(f"POTENTIAL_HARDCODED_{match[0].upper()}")
        
        return list(set(secrets))
    
    @staticmethod
    def _empty_workflow(error: Optional[str] = None) -> Dict[str, Any]:
        """Return empty workflow structure"""
        return {
            'name': 'Unknown',
            'triggers': [],
            'jobs': [],
            'steps': [],
            'uses': [],
            'secrets': [],
            'permissions': {},
            'env': {},
            'metadata': {
                'total_jobs': 0,
                'total_steps': 0,
                'total_actions': 0,
                'has_secrets': False,
                'has_permissions': False,
                'parse_error': error
            }
        }
    
    @staticmethod
    def extract_step_details(workflow_content: str) -> List[Dict]:
        """
        Extract just the steps from workflow for execution monitoring
        Simplified version for treeview display
        """
        try:
            workflow_data = yaml.safe_load(workflow_content)
            if not workflow_data or 'jobs' not in workflow_data:
                return []
            
            all_steps = []
            jobs = workflow_data.get('jobs', {})
            
            for job_id, job_data in jobs.items():
                if not isinstance(job_data, dict):
                    continue
                
                steps = job_data.get('steps', [])
                for idx, step in enumerate(steps):
                    if not isinstance(step, dict):
                        continue
                    
                    all_steps.append({
                        'id': f"{job_id}-step-{idx + 1}",
                        'name': step.get('name', f'Step {idx + 1}'),
                        'type': 'action' if step.get('uses') else 'script',
                        'action': step.get('uses') or step.get('run', '')[:50],
                        'job': job_id
                    })
            
            return all_steps
            
        except Exception as e:
            logger.error(f"Error extracting step details: {e}")
            return []
    
    @staticmethod
    def get_workflow_dependencies(parsed_workflow: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract workflow dependencies (reusable workflows called)
        Returns mapping of workflow to its dependencies
        """
        dependencies = {}
        
        for job in parsed_workflow.get('jobs', []):
            job_id = job.get('id')
            
            # Check for reusable workflow calls
            for step in job.get('steps', []):
                uses = step.get('uses', '')
                if uses and uses.startswith('./'):
                    # Local reusable workflow
                    if job_id not in dependencies:
                        dependencies[job_id] = []
                    dependencies[job_id].append(uses)
        
        return dependencies
