"""
OWASP DevSecOps Maturity Model (DSOMM) Scorer
Maps detected security practices to maturity levels based on the actual DSOMM framework

Reference: https://maverix.ai/help/mergedProjects/KB/DevSecOps_Maturity_Model.htm

Maturity Levels:
- Level 0 (Initial): ○ - Not started
- Level 1 (Initial): ◑ - Partially implemented
- Level 2 (Managed): ● - Implemented
- Level 3 (Optimized): ● - Fully optimized

Domains:
1. Technology (Application Security Testing, Protection, Orchestration)
2. Process (SSDL, Roadmap, Metrics, DevSecOps Factory)
3. People (SSG, Champions, Training, Executive Sponsorship)
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MaturityScorer:
    """
    Calculate DSOMM maturity scores based on detected practices
    Maps real security tool usage and practices to DSOMM framework
    """
    
    # DSOMM Activity Definitions with maturity criteria
    TECHNOLOGY_ACTIVITIES = {
        # Application Security Testing
        'sast': {
            'name': 'Static Application Security Testing (SAST)',
            'description': 'Source code analysis for security vulnerabilities',
            'maturity_criteria': {
                0: {'tools': [], 'description': 'No SAST tools'},
                1: {'tools': ['basic'], 'description': 'Basic SAST tool (linters, basic scanners)'},
                2: {'tools': ['advanced'], 'description': 'Enterprise SAST (CodeQL, SonarQube, Semgrep)'},
                3: {'tools': ['multiple', 'integrated'], 'description': 'Multiple SAST tools, integrated in CI/CD, customized rules'},
            },
            'tool_mapping': {
                'basic': ['eslint', 'pylint', 'bandit', 'brakeman'],
                'advanced': ['codeql', 'semgrep', 'sonarqube', 'checkmarx', 'fortify', 'veracode'],
            }
        },
        'sca': {
            'name': 'Software Composition Analysis (SCA)',
            'description': 'Dependency and open-source vulnerability scanning',
            'maturity_criteria': {
                0: {'tools': [], 'description': 'No SCA tools'},
                1: {'tools': ['basic'], 'description': 'Basic dependency scanning'},
                2: {'tools': ['advanced'], 'description': 'Enterprise SCA with policy enforcement'},
                3: {'tools': ['multiple', 'automated'], 'description': 'Automated SCA with auto-remediation'},
            },
            'tool_mapping': {
                'basic': ['dependabot', 'safety'],
                'advanced': ['snyk', 'owasp_dependency_check', 'trivy', 'grype', 'whitesource'],
            }
        },
        'dast': {
            'name': 'Dynamic Application Security Testing (DAST)',
            'description': 'Runtime security testing of running applications',
            'maturity_criteria': {
                0: {'tools': [], 'description': 'No DAST tools'},
                1: {'tools': ['basic'], 'description': 'Basic DAST scanning'},
                2: {'tools': ['advanced'], 'description': 'Enterprise DAST integrated in pipeline'},
                3: {'tools': ['continuous'], 'description': 'Continuous DAST with authenticated scanning'},
            },
            'tool_mapping': {
                'basic': ['nikto', 'arachni'],
                'advanced': ['zap', 'burp', 'nuclei'],
            }
        },
        'secret_scanning': {
            'name': 'Secret Scanning',
            'description': 'Detection of hardcoded secrets and credentials',
            'maturity_criteria': {
                0: {'tools': [], 'description': 'No secret scanning'},
                1: {'tools': ['basic'], 'description': 'Basic secret detection'},
                2: {'tools': ['advanced'], 'description': 'Enterprise secret scanning in CI/CD'},
                3: {'tools': ['prevention'], 'description': 'Pre-commit hooks preventing secret commits'},
            },
            'tool_mapping': {
                'basic': ['detect_secrets', 'secretlint'],
                'advanced': ['gitleaks', 'trufflehog'],
            }
        },
        'container_scanning': {
            'name': 'Container and Image Scanning (CKS)',
            'description': 'Container and Kubernetes security scanning',
            'maturity_criteria': {
                0: {'tools': [], 'description': 'No container scanning'},
                1: {'tools': ['basic'], 'description': 'Basic container vulnerability scanning'},
                2: {'tools': ['advanced'], 'description': 'Advanced container scanning with policy enforcement'},
                3: {'tools': ['runtime'], 'description': 'Runtime container security monitoring'},
            },
            'tool_mapping': {
                'basic': ['docker_scan'],
                'advanced': ['trivy', 'grype', 'snyk_container', 'clair'],
            }
        },
    }
    
    PROCESS_ACTIVITIES = {
        'ci_cd_integration': {
            'name': 'DevSecOps Factory / CI/CD Integration',
            'description': 'Automation of security testing in CI/CD pipeline',
            'maturity_criteria': {
                0: {'description': 'No CI/CD workflows'},
                1: {'description': 'Basic CI/CD with manual security steps'},
                2: {'description': 'Automated security testing in CI/CD'},
                3: {'description': 'Fully automated DevSecOps pipeline with gates'},
            }
        },
        'branch_protection': {
            'name': 'SSDL Process - Code Review',
            'description': 'Secure software development lifecycle practices',
            'maturity_criteria': {
                0: {'description': 'No branch protection or code review'},
                1: {'description': 'Basic branch protection enabled'},
                2: {'description': 'Required reviews and status checks'},
                3: {'description': 'Comprehensive SSDL with signed commits and CODEOWNERS'},
            }
        },
        'reusable_components': {
            'name': 'Reusable Security Components',
            'description': 'Centralized and reusable security workflows',
            'maturity_criteria': {
                0: {'description': 'No reusable workflows'},
                1: {'description': 'Some workflow reuse'},
                2: {'description': 'Centralized reusable workflows'},
                3: {'description': 'Library of security-tested reusable components'},
            }
        },
        'metrics': {
            'name': 'Security Metrics and Reporting',
            'description': 'Collection and visualization of security metrics',
            'maturity_criteria': {
                0: {'description': 'No security metrics tracked'},
                1: {'description': 'Basic metrics collection'},
                2: {'description': 'Regular security reporting'},
                3: {'description': 'Real-time dashboards and data-driven decisions'},
            }
        }
    }
    
    def __init__(self):
        self.domain_weights = {
            'technology': 0.6,  # 60% - Most impactful
            'process': 0.4,     # 40% - Important but harder to detect automatically
        }
    
    def calculate_maturity(self, 
                          detected_practices: Dict,
                          workflows_count: int,
                          has_ci_cd: bool) -> Dict:
        """
        Calculate DSOMM maturity scores based on actual detected practices
        
        Args:
            detected_practices: Dictionary from SecurityPracticeDetector
            workflows_count: Number of workflows analyzed
            has_ci_cd: Whether CI/CD workflows exist
            
        Returns:
            Comprehensive maturity assessment
        """
        
        # Calculate Technology domain maturity
        technology_scores = self._assess_technology_domain(detected_practices)
        
        # Calculate Process domain maturity
        process_scores = self._assess_process_domain(
            detected_practices, 
            workflows_count,
            has_ci_cd
        )
        
        # Calculate overall scores
        technology_avg = self._calculate_domain_average(technology_scores)
        process_avg = self._calculate_domain_average(process_scores)
        
        # Weighted overall maturity
        overall_maturity = (
            technology_avg * self.domain_weights['technology'] +
            process_avg * self.domain_weights['process']
        )
        
        # Determine maturity level (0-3)
        maturity_level = self._score_to_level(overall_maturity)
        
        return {
            'overall_maturity_score': round(overall_maturity, 2),
            'maturity_level': maturity_level,
            'maturity_label': self._level_to_label(maturity_level),
            'domain_scores': {
                'technology': {
                    'score': round(technology_avg, 2),
                    'level': self._score_to_level(technology_avg),
                    'activities': technology_scores
                },
                'process': {
                    'score': round(process_avg, 2),
                    'level': self._score_to_level(process_avg),
                    'activities': process_scores
                }
            },
            'recommendations': self._generate_recommendations(
                technology_scores, 
                process_scores
            ),
            'calculated_at': datetime.utcnow().isoformat()
        }
    
    def _assess_technology_domain(self, detected_practices: Dict) -> Dict[str, Dict]:
        """Assess technology domain activities"""
        scores = {}
        
        # SAST Assessment
        sast_tools = set(detected_practices.get('sast_tools', []))
        scores['sast'] = self._assess_sast(sast_tools)
        
        # SCA Assessment
        sca_tools = set(detected_practices.get('sca_tools', []))
        scores['sca'] = self._assess_sca(sca_tools)
        
        # DAST Assessment
        dast_tools = set(detected_practices.get('dast_tools', []))
        scores['dast'] = self._assess_dast(dast_tools)
        
        # Secret Scanning Assessment
        secret_tools = set(detected_practices.get('secret_scanning_tools', []))
        scores['secret_scanning'] = self._assess_secret_scanning(secret_tools)
        
        # Container Scanning Assessment
        container_tools = set(detected_practices.get('container_scanning_tools', []))
        scores['container_scanning'] = self._assess_container_scanning(container_tools)
        
        return scores
    
    def _assess_sast(self, tools: set) -> Dict:
        """Assess SAST maturity level based on actual tools detected"""
        activity = self.TECHNOLOGY_ACTIVITIES['sast']
        
        if not tools:
            level = 0
            score = 0
        else:
            # Check for advanced tools
            advanced_tools = set(activity['tool_mapping']['advanced'])
            basic_tools = set(activity['tool_mapping']['basic'])
            
            has_advanced = bool(tools & advanced_tools)
            has_basic = bool(tools & basic_tools)
            
            if len(tools & advanced_tools) >= 2:
                # Multiple advanced tools
                level = 3
                score = 100
            elif has_advanced:
                # At least one advanced tool
                level = 2
                score = 75
            elif has_basic:
                # Only basic tools
                level = 1
                score = 40
            else:
                # Unknown tools (assume basic)
                level = 1
                score = 40
        
        return {
            'activity_name': activity['name'],
            'level': level,
            'score': score,
            'detected_tools': list(tools),
            'status': self._level_to_status(level),
            'description': activity['maturity_criteria'][level]['description']
        }
    
    def _assess_sca(self, tools: set) -> Dict:
        """Assess SCA maturity level"""
        activity = self.TECHNOLOGY_ACTIVITIES['sca']
        
        if not tools:
            level = 0
            score = 0
        else:
            advanced_tools = set(activity['tool_mapping']['advanced'])
            basic_tools = set(activity['tool_mapping']['basic'])
            
            has_advanced = bool(tools & advanced_tools)
            
            if len(tools & advanced_tools) >= 2:
                level = 3
                score = 100
            elif has_advanced:
                level = 2
                score = 75
            elif bool(tools & basic_tools):
                level = 1
                score = 40
            else:
                level = 1
                score = 40
        
        return {
            'activity_name': activity['name'],
            'level': level,
            'score': score,
            'detected_tools': list(tools),
            'status': self._level_to_status(level),
            'description': activity['maturity_criteria'][level]['description']
        }
    
    def _assess_dast(self, tools: set) -> Dict:
        """Assess DAST maturity level"""
        activity = self.TECHNOLOGY_ACTIVITIES['dast']
        
        if not tools:
            level = 0
            score = 0
        else:
            advanced_tools = set(activity['tool_mapping']['advanced'])
            
            if len(tools & advanced_tools) >= 2:
                level = 3
                score = 100
            elif bool(tools & advanced_tools):
                level = 2
                score = 75
            else:
                level = 1
                score = 40
        
        return {
            'activity_name': activity['name'],
            'level': level,
            'score': score,
            'detected_tools': list(tools),
            'status': self._level_to_status(level),
            'description': activity['maturity_criteria'][level]['description']
        }
    
    def _assess_secret_scanning(self, tools: set) -> Dict:
        """Assess Secret Scanning maturity"""
        activity = self.TECHNOLOGY_ACTIVITIES['secret_scanning']
        
        if not tools:
            level = 0
            score = 0
        else:
            advanced_tools = set(activity['tool_mapping']['advanced'])
            
            if len(tools) >= 2:
                level = 3
                score = 100
            elif bool(tools & advanced_tools):
                level = 2
                score = 75
            else:
                level = 1
                score = 40
        
        return {
            'activity_name': activity['name'],
            'level': level,
            'score': score,
            'detected_tools': list(tools),
            'status': self._level_to_status(level),
            'description': activity['maturity_criteria'][level]['description']
        }
    
    def _assess_container_scanning(self, tools: set) -> Dict:
        """Assess Container Scanning maturity"""
        activity = self.TECHNOLOGY_ACTIVITIES['container_scanning']
        
        if not tools:
            level = 0
            score = 0
        else:
            advanced_tools = set(activity['tool_mapping']['advanced'])
            
            if len(tools & advanced_tools) >= 2:
                level = 3
                score = 100
            elif bool(tools & advanced_tools):
                level = 2
                score = 75
            else:
                level = 1
                score = 40
        
        return {
            'activity_name': activity['name'],
            'level': level,
            'score': score,
            'detected_tools': list(tools),
            'status': self._level_to_status(level),
            'description': activity['maturity_criteria'][level]['description']
        }
    
    def _assess_process_domain(self, detected_practices: Dict, workflows_count: int, has_ci_cd: bool) -> Dict[str, Dict]:
        """Assess process domain activities"""
        scores = {}
        
        # CI/CD Integration
        scores['ci_cd_integration'] = self._assess_ci_cd(detected_practices, workflows_count, has_ci_cd)
        
        # Branch Protection / SSDL
        scores['branch_protection'] = self._assess_branch_protection(detected_practices)
        
        # Reusable Components
        scores['reusable_components'] = self._assess_reusable_workflows(detected_practices)
        
        return scores
    
    def _assess_ci_cd(self, detected_practices: Dict, workflows_count: int, has_ci_cd: bool) -> Dict:
        """Assess CI/CD integration maturity"""
        activity = self.PROCESS_ACTIVITIES['ci_cd_integration']
        
        if not has_ci_cd or workflows_count == 0:
            level = 0
            score = 0
        else:
            has_pr_workflows = detected_practices.get('has_pr_workflows', False)
            has_security_tools = any([
                detected_practices.get('sast_tools'),
                detected_practices.get('sca_tools'),
            ])
            
            if has_pr_workflows and has_security_tools and workflows_count >= 3:
                # Comprehensive automation
                level = 3
                score = 100
            elif has_security_tools and workflows_count >= 2:
                # Automated security testing
                level = 2
                score = 75
            elif has_ci_cd:
                # Basic CI/CD
                level = 1
                score = 40
            else:
                level = 0
                score = 0
        
        return {
            'activity_name': activity['name'],
            'level': level,
            'score': score,
            'workflows_count': workflows_count,
            'status': self._level_to_status(level),
            'description': activity['maturity_criteria'][level]['description']
        }
    
    def _assess_branch_protection(self, detected_practices: Dict) -> Dict:
        """Assess branch protection and SSDL practices"""
        activity = self.PROCESS_ACTIVITIES['branch_protection']
        
        has_protection = detected_practices.get('branch_protection_enabled', False)
        required_reviews = detected_practices.get('required_reviews', 0)
        has_status_checks = detected_practices.get('required_status_checks', False)
        signed_commits = detected_practices.get('signed_commits_required', False)
        has_codeowners = detected_practices.get('has_codeowners', False)
        
        if not has_protection:
            level = 0
            score = 0
        elif signed_commits and has_codeowners and required_reviews >= 2:
            # Comprehensive SSDL
            level = 3
            score = 100
        elif required_reviews > 0 and has_status_checks:
            # Required reviews and checks
            level = 2
            score = 75
        elif has_protection:
            # Basic protection
            level = 1
            score = 40
        else:
            level = 0
            score = 0
        
        return {
            'activity_name': activity['name'],
            'level': level,
            'score': score,
            'branch_protection': has_protection,
            'required_reviews': required_reviews,
            'status': self._level_to_status(level),
            'description': activity['maturity_criteria'][level]['description']
        }
    
    def _assess_reusable_workflows(self, detected_practices: Dict) -> Dict:
        """Assess reusable workflow usage"""
        activity = self.PROCESS_ACTIVITIES['reusable_components']
        
        uses_reusable = detected_practices.get('uses_reusable_workflows', False)
        
        if not uses_reusable:
            level = 0
            score = 0
        else:
            # Since we can detect if they're using reusable workflows
            # Assume level 2 (centralized) if they use them
            level = 2
            score = 75
        
        return {
            'activity_name': activity['name'],
            'level': level,
            'score': score,
            'uses_reusable': uses_reusable,
            'status': self._level_to_status(level),
            'description': activity['maturity_criteria'][level]['description']
        }
    
    def _calculate_domain_average(self, scores: Dict[str, Dict]) -> float:
        """Calculate average score for a domain"""
        if not scores:
            return 0.0
        
        total = sum(activity['score'] for activity in scores.values())
        return total / len(scores)
    
    def _score_to_level(self, score: float) -> int:
        """Convert percentage score to maturity level (0-3)"""
        if score >= 90:
            return 3  # Optimized
        elif score >= 60:
            return 2  # Managed
        elif score >= 30:
            return 1  # Initial (partial)
        else:
            return 0  # Not started
    
    def _level_to_label(self, level: int) -> str:
        """Convert maturity level to human-readable label"""
        labels = {
            0: 'Not Started (Initial)',
            1: 'Partially Implemented (Initial)',
            2: 'Implemented (Managed)',
            3: 'Fully Optimized'
        }
        return labels.get(level, 'Unknown')
    
    def _level_to_status(self, level: int) -> str:
        """Convert level to status symbol"""
        symbols = {
            0: '○',  # Empty circle - not started
            1: '◑',  # Half circle - partial
            2: '●',  # Full circle - implemented
            3: '●',  # Full circle - optimized
        }
        return symbols.get(level, '○')
    
    def _generate_recommendations(self, technology_scores: Dict, process_scores: Dict) -> List[Dict]:
        """Generate actionable recommendations based on gaps"""
        recommendations = []
        
        # Technology recommendations
        for activity_key, activity_data in technology_scores.items():
            if activity_data['level'] < 2:  # Below "Managed" level
                priority = 'high' if activity_data['level'] == 0 else 'medium'
                recommendations.append({
                    'category': 'technology',
                    'activity': activity_data['activity_name'],
                    'current_level': activity_data['level'],
                    'target_level': 2,
                    'priority': priority,
                    'recommendation': self._get_technology_recommendation(activity_key, activity_data),
                })
        
        # Process recommendations
        for activity_key, activity_data in process_scores.items():
            if activity_data['level'] < 2:
                priority = 'high' if activity_data['level'] == 0 else 'medium'
                recommendations.append({
                    'category': 'process',
                    'activity': activity_data['activity_name'],
                    'current_level': activity_data['level'],
                    'target_level': 2,
                    'priority': priority,
                    'recommendation': self._get_process_recommendation(activity_key, activity_data),
                })
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 999))
        
        return recommendations
    
    def _get_technology_recommendation(self, activity_key: str, activity_data: Dict) -> str:
        """Get specific recommendation for technology activity"""
        recommendations_map = {
            'sast': 'Implement enterprise SAST tools like CodeQL, Semgrep, or SonarQube in your CI/CD pipeline.',
            'sca': 'Add Software Composition Analysis with tools like Snyk, Dependabot, or OWASP Dependency-Check.',
            'dast': 'Implement Dynamic Application Security Testing with OWASP ZAP or similar tools.',
            'secret_scanning': 'Add secret scanning tools like Gitleaks or TruffleHog to prevent credential leaks.',
            'container_scanning': 'Implement container security scanning with Trivy or Grype.',
        }
        return recommendations_map.get(activity_key, 'Improve security testing coverage.')
    
    def _get_process_recommendation(self, activity_key: str, activity_data: Dict) -> str:
        """Get specific recommendation for process activity"""
        recommendations_map = {
            'ci_cd_integration': 'Integrate security testing tools into your CI/CD pipelines with automated gates.',
            'branch_protection': 'Enable branch protection rules with required reviews and status checks.',
            'reusable_components': 'Create centralized, reusable workflows for common security testing patterns.',
        }
        return recommendations_map.get(activity_key, 'Improve DevSecOps processes.')
