"""
Workflow Parser for GitHub Actions YAML files
Extracts security-relevant information and detects tools/practices
"""

import yaml
import re
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WorkflowParser:
    """
    Parse GitHub Actions workflow files to extract security practices and tools
    """
    
    # Security tool patterns
    SAST_TOOLS = {
        'codeql': ['github/codeql-action', 'codeql-action/init', 'codeql-action/analyze'],
        'semgrep': ['semgrep', 'returntocorp/semgrep-action'],
        'sonarqube': ['sonarqube', 'sonar-scanner', 'sonarsource'],
        'snyk_code': ['snyk/actions', 'snyk test', 'snyk code'],
        'checkmarx': ['checkmarx', 'cx-flow'],
        'fortify': ['fortify', 'fortifysca'],
        'veracode': ['veracode'],
        'bandit': ['bandit'],
        'brakeman': ['brakeman'],
        'eslint': ['eslint'],
        'pylint': ['pylint'],
    }
    
    SCA_TOOLS = {
        'dependabot': ['dependabot'],
        'snyk': ['snyk/actions', 'snyk test', 'snyk monitor'],
        'owasp_dependency_check': ['dependency-check', 'owasp'],
        'trivy': ['aquasecurity/trivy', 'trivy'],
        'grype': ['anchore/scan-action', 'grype'],
        'whitesource': ['whitesource', 'mend'],
        'safety': ['safety check', 'pyup'],
    }
    
    DAST_TOOLS = {
        'zap': ['zaproxy', 'owasp-zap', 'zap-scan'],
        'burp': ['burp suite', 'burp-scan'],
        'arachni': ['arachni'],
        'nikto': ['nikto'],
        'nuclei': ['nuclei', 'projectdiscovery'],
    }
    
    SECRET_SCANNING_TOOLS = {
        'gitleaks': ['gitleaks', 'zricethezav/gitleaks'],
        'trufflehog': ['trufflehog', 'trufflesecurity'],
        'detect_secrets': ['detect-secrets'],
        'secretlint': ['secretlint'],
    }
    
    CONTAINER_SCANNING_TOOLS = {
        'trivy': ['aquasecurity/trivy', 'trivy'],
        'grype': ['anchore/scan-action', 'grype'],
        'snyk_container': ['snyk container'],
        'clair': ['clair'],
        'docker_scan': ['docker scan'],
    }
    
    # Pre-commit hook patterns
    PRECOMMIT_PATTERNS = {
        'pre_commit': ['pre-commit', 'pre_commit', 'pre-commit/action'],
        'husky': ['husky', 'typicode/husky'],
        'git_hooks': ['git hooks', 'githooks'],
    }
    
    def __init__(self):
        self.all_tools = {
            'sast': self.SAST_TOOLS,
            'sca': self.SCA_TOOLS,
            'dast': self.DAST_TOOLS,
            'secret_scanning': self.SECRET_SCANNING_TOOLS,
            'container_scanning': self.CONTAINER_SCANNING_TOOLS,
            'precommit_hooks': self.PRECOMMIT_PATTERNS,
        }
    
    def parse_workflow(self, content: str, workflow_path: str = "") -> Dict:
        """
        Parse a GitHub Actions workflow file
        
        Args:
            content: YAML content of the workflow
            workflow_path: Path to the workflow file
            
        Returns:
            Dictionary with extracted information
        """
        try:
            # Parse YAML
            workflow_data = yaml.safe_load(content)
            
            if not workflow_data:
                return self._empty_result("Empty workflow file")
            
            # Extract basic info
            result = {
                'workflow_name': workflow_data.get('name', 'Unnamed Workflow'),
                'workflow_path': workflow_path,
                'triggers': self._extract_triggers(workflow_data),
                'jobs': self._extract_jobs(workflow_data),
                'detected_tools': self._detect_tools(workflow_data, content),
                'security_practices': self._detect_security_practices(workflow_data, content),
                'is_reusable': self._is_reusable_workflow(workflow_data),
                'calls_reusable': self._calls_reusable_workflows(workflow_data),
                'environment_secrets': self._extract_secrets(workflow_data),
                'permissions': self._extract_permissions(workflow_data),
                'parsed_at': datetime.utcnow().isoformat(),
                'parse_status': 'success',
            }
            
            return result
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {workflow_path}: {str(e)}")
            return self._empty_result(f"YAML error: {str(e)}")
        except Exception as e:
            logger.error(f"Workflow parsing error in {workflow_path}: {str(e)}")
            return self._empty_result(f"Parse error: {str(e)}")
    
    def _extract_triggers(self, workflow_data: Dict) -> List[str]:
        """Extract workflow triggers (on: events)"""
        triggers = []
        
        if 'on' in workflow_data:
            on_data = workflow_data['on']
            
            if isinstance(on_data, str):
                triggers.append(on_data)
            elif isinstance(on_data, list):
                triggers.extend(on_data)
            elif isinstance(on_data, dict):
                triggers.extend(on_data.keys())
        
        return triggers
    
    def _extract_jobs(self, workflow_data: Dict) -> List[Dict]:
        """Extract job information"""
        jobs = []
        
        if 'jobs' not in workflow_data:
            return jobs
        
        for job_id, job_data in workflow_data['jobs'].items():
            if not isinstance(job_data, dict):
                continue
                
            job_info = {
                'job_id': job_id,
                'name': job_data.get('name', job_id),
                'runs_on': job_data.get('runs-on', 'unknown'),
                'steps_count': len(job_data.get('steps', [])),
                'uses_environment': 'environment' in job_data,
                'needs': job_data.get('needs', []),
            }
            jobs.append(job_info)
        
        return jobs
    
    def _detect_tools(self, workflow_data: Dict, content: str) -> Dict[str, List[str]]:
        """Detect security tools used in the workflow"""
        detected = {
            'sast': [],
            'sca': [],
            'dast': [],
            'secret_scanning': [],
            'container_scanning': [],
        }
        
        content_lower = content.lower()
        
        for category, tools in self.all_tools.items():
            for tool_name, patterns in tools.items():
                for pattern in patterns:
                    if pattern.lower() in content_lower:
                        if tool_name not in detected[category]:
                            detected[category].append(tool_name)
                        break
        
        return detected
    
    def _detect_security_practices(self, workflow_data: Dict, content: str) -> Dict[str, bool]:
        """Detect security best practices"""
        practices = {
            'uses_checkout_action': False,
            'pins_action_versions': False,
            'uses_secrets': False,
            'has_security_scanning': False,
            'runs_on_pr': False,
            'runs_on_push': False,
            'has_approval_step': False,
            'uses_environments': False,
            'has_caching': False,
            'uses_github_script': False,
        }
        
        # Check triggers
        triggers = self._extract_triggers(workflow_data)
        practices['runs_on_pr'] = 'pull_request' in triggers or 'pull_request_target' in triggers
        practices['runs_on_push'] = 'push' in triggers
        
        # Check content
        content_lower = content.lower()
        practices['uses_checkout_action'] = 'actions/checkout@' in content
        practices['pins_action_versions'] = '@v' in content or '@sha' in content
        practices['uses_secrets'] = 'secrets.' in content_lower
        practices['uses_github_script'] = 'actions/github-script' in content
        practices['has_caching'] = 'actions/cache@' in content
        
        # Check for security scanning
        detected_tools = self._detect_tools(workflow_data, content)
        has_any_tool = any(tools for tools in detected_tools.values())
        practices['has_security_scanning'] = has_any_tool
        
        # Check for environments (deployment protection)
        if 'jobs' in workflow_data:
            for job_data in workflow_data['jobs'].values():
                if isinstance(job_data, dict) and 'environment' in job_data:
                    practices['uses_environments'] = True
                    break
        
        return practices
    
    def _is_reusable_workflow(self, workflow_data: Dict) -> bool:
        """Check if this is a reusable workflow"""
        if 'on' in workflow_data:
            on_data = workflow_data['on']
            if isinstance(on_data, dict) and 'workflow_call' in on_data:
                return True
        return False
    
    def _calls_reusable_workflows(self, workflow_data: Dict) -> List[str]:
        """Detect calls to reusable workflows"""
        reusable_calls = []
        
        if 'jobs' not in workflow_data:
            return reusable_calls
        
        for job_data in workflow_data['jobs'].values():
            if not isinstance(job_data, dict):
                continue
            
            if 'uses' in job_data:
                reusable_calls.append(job_data['uses'])
        
        return reusable_calls
    
    def _extract_secrets(self, workflow_data: Dict) -> List[str]:
        """Extract environment and secrets references"""
        secrets = set()
        
        # Convert to string and search for secrets.
        content_str = str(workflow_data)
        secret_pattern = r'secrets\.([A-Z_][A-Z0-9_]*)'
        matches = re.findall(secret_pattern, content_str)
        secrets.update(matches)
        
        return list(secrets)
    
    def _extract_permissions(self, workflow_data: Dict) -> Dict:
        """Extract workflow permissions"""
        permissions = workflow_data.get('permissions', {})
        
        if isinstance(permissions, str):
            return {'all': permissions}
        
        return permissions if isinstance(permissions, dict) else {}
    
    def _empty_result(self, error: str) -> Dict:
        """Return empty result with error"""
        return {
            'workflow_name': 'Unknown',
            'workflow_path': '',
            'triggers': [],
            'jobs': [],
            'detected_tools': {
                'sast': [],
                'sca': [],
                'dast': [],
                'secret_scanning': [],
                'container_scanning': [],
            },
            'security_practices': {},
            'is_reusable': False,
            'calls_reusable': [],
            'environment_secrets': [],
            'permissions': {},
            'parsed_at': datetime.utcnow().isoformat(),
            'parse_status': 'error',
            'parse_error': error,
        }
    
    def get_security_score(self, parsed_workflow: Dict) -> Dict[str, any]:
        """
        Calculate a basic security score for the workflow
        
        Returns:
            Dictionary with score and breakdown
        """
        score = 0
        max_score = 100
        breakdown = {}
        
        # Tools detection (40 points)
        tools = parsed_workflow.get('detected_tools', {})
        tools_score = 0
        if tools.get('sast'):
            tools_score += 15
        if tools.get('sca'):
            tools_score += 10
        if tools.get('secret_scanning'):
            tools_score += 10
        if tools.get('dast'):
            tools_score += 5
        
        breakdown['tools'] = tools_score
        score += tools_score
        
        # Best practices (30 points)
        practices = parsed_workflow.get('security_practices', {})
        practices_score = 0
        if practices.get('pins_action_versions'):
            practices_score += 10
        if practices.get('uses_secrets'):
            practices_score += 5
        if practices.get('runs_on_pr'):
            practices_score += 10
        if practices.get('uses_environments'):
            practices_score += 5
        
        breakdown['practices'] = practices_score
        score += practices_score
        
        # Permissions (20 points)
        permissions = parsed_workflow.get('permissions', {})
        if permissions and permissions != {'all': 'write'}:
            breakdown['permissions'] = 20
            score += 20
        else:
            breakdown['permissions'] = 0
        
        # Reusable workflows (10 points)
        if parsed_workflow.get('is_reusable') or parsed_workflow.get('calls_reusable'):
            breakdown['reusability'] = 10
            score += 10
        else:
            breakdown['reusability'] = 0
        
        return {
            'score': score,
            'max_score': max_score,
            'percentage': (score / max_score) * 100,
            'breakdown': breakdown,
        }
