"""
Security Practice Detector
Analyzes repositories to detect security practices, configurations, and policies
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SecurityPracticeDetector:
    """
    Detects security practices across repositories
    Based on DevSecOps best practices and OWASP guidelines
    """
    
    # Finding categories
    CATEGORIES = {
        'tools': 'Security Tools',
        'policies': 'Repository Policies',
        'architecture': 'Architecture & Design',
        'configuration': 'Configuration',
    }
    
    # Severity levels
    SEVERITY = {
        'critical': {'priority': 1, 'score_impact': -25},
        'high': {'priority': 2, 'score_impact': -15},
        'medium': {'priority': 3, 'score_impact': -10},
        'low': {'priority': 4, 'score_impact': -5},
        'info': {'priority': 5, 'score_impact': 0},
    }
    
    def __init__(self):
        self.findings = []
    
    def analyze_repository(self, 
                          repo_data: Dict,
                          workflows: List[Dict],
                          branch_protection: Optional[Dict] = None,
                          has_codeowners: bool = False) -> Dict:
        """
        Analyze a repository for security practices
        
        Args:
            repo_data: Repository metadata from GitHub
            workflows: List of parsed workflow data
            branch_protection: Branch protection rules
            has_codeowners: Whether CODEOWNERS file exists
            
        Returns:
            Analysis results with findings and scores
        """
        self.findings = []
        
        repo_name = repo_data.get('name', 'Unknown')
        
        # ✅ CRITICAL: Check if repo has workflows first
        has_workflows = len(workflows) > 0
        
        if not has_workflows:
            # Repository has no CI/CD workflows - return minimal analysis
            return {
                'repository_name': repo_name,
                'analyzed_at': datetime.utcnow().isoformat(),
                'has_workflows': False,
                'findings': [{
                    'finding_type': 'no_cicd_workflows',
                    'category': 'configuration',
                    'severity': 'info',
                    'title': 'No CI/CD Configuration',
                    'description': f'Repository "{repo_name}" does not have any GitHub Actions workflows configured.',
                    'recommendation': 'Consider setting up CI/CD workflows with security tools for automated testing.',
                    'affected_component': repo_name,
                }],
                'findings_count': {
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0,
                    'info': 1,
                },
                'security_score': None,  # Not applicable without workflows
                'detected_practices': {
                    'sast_tools': [],
                    'sca_tools': [],
                    'dast_tools': [],
                    'secret_scanning_tools': [],
                    'container_scanning_tools': [],
                    'branch_protection_enabled': branch_protection is not None if branch_protection else False,
                    'has_codeowners': has_codeowners,
                    'required_reviews': branch_protection.get('required_reviewers', 0) if branch_protection else 0,
                    'required_status_checks': False,
                    'signed_commits_required': False,
                    'has_pr_workflows': False,
                    'uses_reusable_workflows': False,
                    'pins_action_versions': False,
                    'has_precommit_hooks': False,
                },
                'workflows_analyzed': 0,
            }
        
        # Analyze different aspects (only for repos WITH workflows)
        tool_findings = self._check_security_tools(repo_name, workflows)
        policy_findings = self._check_repository_policies(repo_name, branch_protection, has_codeowners)
        workflow_findings = self._check_workflow_security(repo_name, workflows)
        architecture_findings = self._check_architecture_patterns(repo_name, workflows)
        
        # Combine all findings
        all_findings = (
            tool_findings + 
            policy_findings + 
            workflow_findings + 
            architecture_findings
        )
        
        # Calculate scores
        security_score = self._calculate_security_score(all_findings)
        
        # Detected practices
        detected_practices = self._summarize_detected_practices(workflows, branch_protection, has_codeowners)
        
        return {
            'repository_name': repo_name,
            'analyzed_at': datetime.utcnow().isoformat(),
            'has_workflows': True,  # This repo has workflows
            'findings': all_findings,
            'findings_count': {
                'critical': len([f for f in all_findings if f['severity'] == 'critical']),
                'high': len([f for f in all_findings if f['severity'] == 'high']),
                'medium': len([f for f in all_findings if f['severity'] == 'medium']),
                'low': len([f for f in all_findings if f['severity'] == 'low']),
                'info': len([f for f in all_findings if f['severity'] == 'info']),
            },
            'security_score': security_score,
            'detected_practices': detected_practices,
            'workflows_analyzed': len(workflows),
        }
    
    def _check_security_tools(self, repo_name: str, workflows: List[Dict]) -> List[Dict]:
        """Check for presence of security tools"""
        findings = []
        
        # Aggregate tools across all workflows
        all_sast = set()
        all_sca = set()
        all_dast = set()
        all_secret_scanning = set()
        all_container_scanning = set()
        
        for workflow in workflows:
            tools = workflow.get('detected_tools', {})
            all_sast.update(tools.get('sast', []))
            all_sca.update(tools.get('sca', []))
            all_dast.update(tools.get('dast', []))
            all_secret_scanning.update(tools.get('secret_scanning', []))
            all_container_scanning.update(tools.get('container_scanning', []))
        
        # Check SAST
        if not all_sast:
            findings.append({
                'finding_type': 'missing_sast',
                'category': 'tools',
                'severity': 'high',
                'title': 'No SAST Tools Detected',
                'description': f'Repository "{repo_name}" does not have Static Application Security Testing (SAST) tools configured.',
                'recommendation': 'Add a SAST tool like CodeQL, Semgrep, or SonarQube to your CI/CD pipeline.',
                'detected_by': 'tool_detector',
                'confidence': 0.9,
                'remediation_effort': 'medium',
                'metadata': {'checked_workflows': len(workflows)},
            })
        
        # Check SCA
        if not all_sca:
            findings.append({
                'finding_type': 'missing_sca',
                'category': 'tools',
                'severity': 'high',
                'title': 'No SCA Tools Detected',
                'description': f'Repository "{repo_name}" does not have Software Composition Analysis (SCA) tools for dependency scanning.',
                'recommendation': 'Add Dependabot, Snyk, or OWASP Dependency-Check to scan for vulnerable dependencies.',
                'detected_by': 'tool_detector',
                'confidence': 0.9,
                'remediation_effort': 'low',
                'metadata': {'checked_workflows': len(workflows)},
            })
        
        # Check Secret Scanning
        if not all_secret_scanning:
            findings.append({
                'finding_type': 'missing_secret_scanning',
                'category': 'tools',
                'severity': 'medium',
                'title': 'No Secret Scanning Detected',
                'description': f'Repository "{repo_name}" does not have secret scanning tools configured.',
                'recommendation': 'Add Gitleaks, TruffleHog, or enable GitHub Secret Scanning.',
                'detected_by': 'tool_detector',
                'confidence': 0.85,
                'remediation_effort': 'low',
                'metadata': {'checked_workflows': len(workflows)},
            })
        
        # Info: DAST not critical but good to have
        if not all_dast:
            findings.append({
                'finding_type': 'missing_dast',
                'category': 'tools',
                'severity': 'low',
                'title': 'No DAST Tools Detected',
                'description': f'Repository "{repo_name}" does not have Dynamic Application Security Testing (DAST) tools.',
                'recommendation': 'Consider adding DAST tools like OWASP ZAP for runtime security testing.',
                'detected_by': 'tool_detector',
                'confidence': 0.8,
                'remediation_effort': 'high',
                'metadata': {'checked_workflows': len(workflows)},
            })
        
        return findings
    
    def _check_repository_policies(self, repo_name: str, branch_protection: Optional[Dict], has_codeowners: bool) -> List[Dict]:
        """Check repository policies and configurations"""
        findings = []
        
        # Check branch protection
        if not branch_protection or not branch_protection.get('enabled'):
            findings.append({
                'finding_type': 'no_branch_protection',
                'category': 'policies',
                'severity': 'critical',
                'title': 'Branch Protection Not Enabled',
                'description': f'Repository "{repo_name}" does not have branch protection rules enabled on the default branch.',
                'recommendation': 'Enable branch protection rules to require pull request reviews, status checks, and prevent force pushes.',
                'detected_by': 'policy_checker',
                'confidence': 1.0,
                'remediation_effort': 'low',
                'metadata': {},
            })
        else:
            # Check specific protection rules
            if not branch_protection.get('required_approving_review_count', 0) > 0:
                findings.append({
                    'finding_type': 'no_required_reviews',
                    'category': 'policies',
                    'severity': 'high',
                    'title': 'No Required Code Reviews',
                    'description': f'Repository "{repo_name}" does not require code reviews before merging.',
                    'recommendation': 'Require at least one or two approving reviews before allowing pull request merges.',
                    'detected_by': 'policy_checker',
                    'confidence': 1.0,
                    'remediation_effort': 'low',
                    'metadata': {},
                })
            
            if not branch_protection.get('required_status_checks'):
                findings.append({
                    'finding_type': 'no_status_checks',
                    'category': 'policies',
                    'severity': 'medium',
                    'title': 'No Required Status Checks',
                    'description': f'Repository "{repo_name}" does not require status checks to pass before merging.',
                    'recommendation': 'Require CI/CD checks and security scans to pass before allowing merges.',
                    'detected_by': 'policy_checker',
                    'confidence': 1.0,
                    'remediation_effort': 'low',
                    'metadata': {},
                })
            
            if not branch_protection.get('require_signed_commits'):
                findings.append({
                    'finding_type': 'no_signed_commits',
                    'category': 'policies',
                    'severity': 'low',
                    'title': 'Signed Commits Not Required',
                    'description': f'Repository "{repo_name}" does not require signed commits.',
                    'recommendation': 'Require commit signing to verify commit authenticity.',
                    'detected_by': 'policy_checker',
                    'confidence': 1.0,
                    'remediation_effort': 'medium',
                    'metadata': {},
                })
        
        # Check CODEOWNERS
        if not has_codeowners:
            findings.append({
                'finding_type': 'no_codeowners',
                'category': 'policies',
                'severity': 'medium',
                'title': 'No CODEOWNERS File',
                'description': f'Repository "{repo_name}" does not have a CODEOWNERS file.',
                'recommendation': 'Add a CODEOWNERS file to define code ownership and ensure appropriate reviews.',
                'detected_by': 'policy_checker',
                'confidence': 1.0,
                'remediation_effort': 'low',
                'metadata': {},
            })
        
        return findings
    
    def _check_workflow_security(self, repo_name: str, workflows: List[Dict]) -> List[Dict]:
        """Check workflow security best practices"""
        findings = []
        
        if not workflows:
            findings.append({
                'finding_type': 'no_workflows',
                'category': 'configuration',
                'severity': 'medium',
                'title': 'No CI/CD Workflows',
                'description': f'Repository "{repo_name}" has no GitHub Actions workflows.',
                'recommendation': 'Implement CI/CD pipelines with automated testing and security scanning.',
                'detected_by': 'workflow_checker',
                'confidence': 1.0,
                'remediation_effort': 'high',
                'metadata': {},
            })
            return findings
        
        # Check for workflows running on PR
        pr_workflows = [w for w in workflows if w.get('security_practices', {}).get('runs_on_pr')]
        if not pr_workflows:
            findings.append({
                'finding_type': 'no_pr_workflows',
                'category': 'configuration',
                'severity': 'medium',
                'title': 'No PR Validation Workflows',
                'description': f'Repository "{repo_name}" has no workflows that run on pull requests.',
                'recommendation': 'Configure workflows to run automated checks on pull requests.',
                'detected_by': 'workflow_checker',
                'confidence': 0.9,
                'remediation_effort': 'low',
                'metadata': {'total_workflows': len(workflows)},
            })
        
        # Check action version pinning
        unpinned_workflows = [
            w for w in workflows 
            if not w.get('security_practices', {}).get('pins_action_versions')
        ]
        if unpinned_workflows:
            findings.append({
                'finding_type': 'unpinned_actions',
                'category': 'configuration',
                'severity': 'low',
                'title': 'Actions Not Version Pinned',
                'description': f'{len(unpinned_workflows)} workflow(s) use unpinned action versions.',
                'recommendation': 'Pin GitHub Actions to specific versions or commit SHAs for supply chain security.',
                'detected_by': 'workflow_checker',
                'confidence': 0.85,
                'remediation_effort': 'low',
                'metadata': {'unpinned_count': len(unpinned_workflows)},
            })
        
        return findings
    
    def _check_architecture_patterns(self, repo_name: str, workflows: List[Dict]) -> List[Dict]:
        """Check for architectural patterns like centralized workflows"""
        findings = []
        
        # Check for reusable workflows
        has_reusable = any(w.get('is_reusable') for w in workflows)
        calls_reusable = any(w.get('calls_reusable') for w in workflows)
        
        if not has_reusable and not calls_reusable and len(workflows) > 2:
            findings.append({
                'finding_type': 'no_reusable_workflows',
                'category': 'architecture',
                'severity': 'info',
                'title': 'No Reusable Workflows',
                'description': f'Repository "{repo_name}" has multiple workflows but none are reusable.',
                'recommendation': 'Consider creating reusable workflows to centralize common CI/CD patterns.',
                'detected_by': 'architecture_checker',
                'confidence': 0.7,
                'remediation_effort': 'medium',
                'metadata': {'workflow_count': len(workflows)},
            })
        
        return findings
    
    def _calculate_security_score(self, findings: List[Dict]) -> float:
        """Calculate overall security score based on findings"""
        base_score = 100.0
        
        for finding in findings:
            severity = finding.get('severity', 'info')
            impact = self.SEVERITY.get(severity, {}).get('score_impact', 0)
            base_score += impact
        
        # Ensure score is between 0 and 100
        return max(0.0, min(100.0, base_score))
    
    def _summarize_detected_practices(self, workflows: List[Dict], branch_protection: Optional[Dict], has_codeowners: bool) -> Dict:
        """Summarize all detected security practices"""
        practices = {
            'sast_tools': set(),
            'sca_tools': set(),
            'dast_tools': set(),
            'secret_scanning_tools': set(),
            'container_scanning_tools': set(),
            'precommit_hooks': set(),
            'branch_protection_enabled': bool(branch_protection and branch_protection.get('enabled')),
            'required_reviews': branch_protection.get('required_approving_review_count', 0) if branch_protection else 0,
            'required_status_checks': bool(branch_protection and branch_protection.get('required_status_checks')),
            'signed_commits_required': bool(branch_protection and branch_protection.get('require_signed_commits')),
            'has_codeowners': has_codeowners,
            'has_pr_workflows': False,
            'uses_reusable_workflows': False,
            'pins_action_versions': False,
            'has_precommit_hooks': False,
        }
        
        for workflow in workflows:
            tools = workflow.get('detected_tools', {})
            practices['sast_tools'].update(tools.get('sast', []))
            practices['sca_tools'].update(tools.get('sca', []))
            practices['dast_tools'].update(tools.get('dast', []))
            practices['secret_scanning_tools'].update(tools.get('secret_scanning', []))
            practices['container_scanning_tools'].update(tools.get('container_scanning', []))
            practices['precommit_hooks'].update(tools.get('precommit_hooks', []))
            
            security = workflow.get('security_practices', {})
            if security.get('runs_on_pr'):
                practices['has_pr_workflows'] = True
            if workflow.get('is_reusable') or workflow.get('calls_reusable'):
                practices['uses_reusable_workflows'] = True
            if security.get('pins_action_versions'):
                practices['pins_action_versions'] = True
        
        # Set precommit flag
        practices['has_precommit_hooks'] = len(practices['precommit_hooks']) > 0
        
        # Convert sets to lists for JSON serialization
        practices['sast_tools'] = list(practices['sast_tools'])
        practices['sca_tools'] = list(practices['sca_tools'])
        practices['dast_tools'] = list(practices['dast_tools'])
        practices['secret_scanning_tools'] = list(practices['secret_scanning_tools'])
        practices['container_scanning_tools'] = list(practices['container_scanning_tools'])
        practices['precommit_hooks'] = list(practices['precommit_hooks'])
        
        return practices
