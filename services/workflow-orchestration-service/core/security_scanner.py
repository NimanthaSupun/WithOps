"""
Security Scanner - Analyze workflows for security vulnerabilities
Detects hardcoded secrets, unsafe actions, permission issues, and injection risks
"""

import re
import yaml
from typing import Dict, List, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SeverityLevel(str, Enum):
    """Severity levels for security findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityScanner:
    """Scan GitHub Actions workflows for security issues"""
    
    # Known vulnerable or risky actions
    RISKY_ACTIONS = {
        'actions/checkout@v1': 'Outdated version with known security issues',
        'actions/checkout@v2': 'Use v3 or later for better security',
        'ad-m/github-push-action': 'Potential for token exposure',
    }
    
    # Risky permissions
    RISKY_PERMISSIONS = {
        'write-all': 'Grants full write access to repository',
        'contents: write': 'Allows modification of repository contents',
        'packages: write': 'Allows publishing packages',
        'deployments: write': 'Allows creating deployments',
    }
    
    # Secret patterns
    SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']', 'API Key'),
        (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']([^"\']{8,})["\']', 'Password'),
        (r'(?i)(token|auth[_-]?token)\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']', 'Token'),
        (r'(?i)(secret|secret[_-]?key)\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']', 'Secret Key'),
        (r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*["\']([A-Z0-9]{20})["\']', 'AWS Access Key'),
        (r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*["\']([a-zA-Z0-9/+]{40})["\']', 'AWS Secret Key'),
        (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
        (r'gho_[a-zA-Z0-9]{36}', 'GitHub OAuth Token'),
        (r'ghs_[a-zA-Z0-9]{36}', 'GitHub Server Token'),
    ]
    
    @staticmethod
    def scan_workflow(workflow_content: str, workflow_name: str = "Unknown") -> Dict[str, Any]:
        """
        Perform comprehensive security scan on workflow
        
        Returns:
            {
                'workflow_name': str,
                'risk_level': str (minimal, low, medium, high, critical),
                'risk_score': float (0-100),
                'issues': List[Dict],
                'recommendations': List[str],
                'summary': Dict
            }
        """
        issues = []
        
        # 1. Scan for hardcoded secrets
        secret_issues = SecurityScanner._scan_secrets(workflow_content)
        issues.extend(secret_issues)
        
        # 2. Scan for unsafe actions
        unsafe_action_issues = SecurityScanner._scan_unsafe_actions(workflow_content)
        issues.extend(unsafe_action_issues)
        
        # 3. Scan for permission issues
        permission_issues = SecurityScanner._scan_permissions(workflow_content)
        issues.extend(permission_issues)
        
        # 4. Scan for script injection risks
        injection_issues = SecurityScanner._scan_injection_risks(workflow_content)
        issues.extend(injection_issues)
        
        # 5. Scan for other common issues
        other_issues = SecurityScanner._scan_common_issues(workflow_content)
        issues.extend(other_issues)
        
        # Calculate risk score and level
        risk_score, risk_level = SecurityScanner._calculate_risk(issues)
        
        # Generate recommendations
        recommendations = SecurityScanner._generate_recommendations(issues)
        
        # Summary
        summary = {
            'total_issues': len(issues),
            'critical': sum(1 for i in issues if i['severity'] == SeverityLevel.CRITICAL),
            'high': sum(1 for i in issues if i['severity'] == SeverityLevel.HIGH),
            'medium': sum(1 for i in issues if i['severity'] == SeverityLevel.MEDIUM),
            'low': sum(1 for i in issues if i['severity'] == SeverityLevel.LOW),
            'info': sum(1 for i in issues if i['severity'] == SeverityLevel.INFO),
        }
        
        return {
            'workflow_name': workflow_name,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'issues': issues,
            'recommendations': recommendations,
            'summary': summary
        }
    
    @staticmethod
    def _scan_secrets(content: str) -> List[Dict]:
        """Scan for hardcoded secrets"""
        issues = []
        
        for pattern, secret_type in SecurityScanner.SECRET_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                # Don't flag if it's using secrets.VARIABLE syntax
                if '${{ secrets.' in content[max(0, match.start()-20):match.start()]:
                    continue
                
                issues.append({
                    'category': 'secrets',
                    'severity': SeverityLevel.CRITICAL,
                    'title': f'Potential hardcoded {secret_type} detected',
                    'description': f'Found what appears to be a hardcoded {secret_type}. Use GitHub secrets instead.',
                    'line': content[:match.start()].count('\n') + 1,
                    'snippet': match.group(0)[:50] + '...' if len(match.group(0)) > 50 else match.group(0)
                })
        
        return issues
    
    @staticmethod
    def _scan_unsafe_actions(content: str) -> List[Dict]:
        """Scan for outdated or risky GitHub Actions"""
        issues = []
        
        # Extract all 'uses:' statements
        uses_pattern = r'uses:\s*([^\s\n]+)'
        matches = re.finditer(uses_pattern, content)
        
        for match in matches:
            action = match.group(1).strip()
            
            # Check against known risky actions
            for risky_action, reason in SecurityScanner.RISKY_ACTIONS.items():
                if action.startswith(risky_action.split('@')[0]):
                    issues.append({
                        'category': 'unsafe_actions',
                        'severity': SeverityLevel.HIGH,
                        'title': f'Risky action: {action}',
                        'description': reason,
                        'line': content[:match.start()].count('\n') + 1,
                        'action': action
                    })
            
            # Check for pinned versions (security best practice)
            if '@' in action and not re.match(r'.*@[a-f0-9]{40}$', action):
                # Not pinned to commit SHA
                if action.count('@') == 1 and not action.endswith('@main') and not action.endswith('@master'):
                    issues.append({
                        'category': 'unsafe_actions',
                        'severity': SeverityLevel.LOW,
                        'title': f'Action not pinned to commit SHA: {action}',
                        'description': 'Consider pinning actions to specific commit SHAs for better security',
                        'line': content[:match.start()].count('\n') + 1,
                        'action': action
                    })
        
        return issues
    
    @staticmethod
    def _scan_permissions(content: str) -> List[Dict]:
        """Scan for overly permissive permissions"""
        issues = []
        
        try:
            workflow_data = yaml.safe_load(content)
            permissions = workflow_data.get('permissions', {})
            
            if isinstance(permissions, str) and permissions == 'write-all':
                issues.append({
                    'category': 'permissions',
                    'severity': SeverityLevel.HIGH,
                    'title': 'Overly permissive: write-all',
                    'description': 'Workflow has write-all permissions. Use least privilege principle.',
                    'permission': 'write-all'
                })
            elif isinstance(permissions, dict):
                for perm, value in permissions.items():
                    if value == 'write':
                        issues.append({
                            'category': 'permissions',
                            'severity': SeverityLevel.MEDIUM,
                            'title': f'Write permission: {perm}',
                            'description': f'Workflow has write permission for {perm}. Ensure this is necessary.',
                            'permission': f'{perm}: write'
                        })
        except:
            pass
        
        return issues
    
    @staticmethod
    def _scan_injection_risks(content: str) -> List[Dict]:
        """Scan for script injection vulnerabilities"""
        issues = []
        
        # Pattern for dangerous input usage in run commands
        dangerous_patterns = [
            (r'run:.*\$\{\{.*github\.event\.(issue|pull_request)\.(title|body)', 'Potential script injection from issue/PR content'),
            (r'run:.*\$\{\{.*github\.event\.comment\.body', 'Potential script injection from comment'),
            (r'run:.*\$\{\{.*github\.event\.head_commit\.message', 'Potential script injection from commit message'),
        ]
        
        for pattern, description in dangerous_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                issues.append({
                    'category': 'injection',
                    'severity': SeverityLevel.HIGH,
                    'title': 'Script injection risk detected',
                    'description': description,
                    'line': content[:match.start()].count('\n') + 1,
                    'recommendation': 'Sanitize user input or use environment variables'
                })
        
        return issues
    
    @staticmethod
    def _scan_common_issues(content: str) -> List[Dict]:
        """Scan for other common security issues"""
        issues = []
        
        # Check for pull_request_target with checkout
        if 'pull_request_target' in content and 'actions/checkout' in content:
            issues.append({
                'category': 'workflow_design',
                'severity': SeverityLevel.MEDIUM,
                'title': 'pull_request_target with checkout',
                'description': 'Using pull_request_target with checkout can be dangerous. Ensure you checkout the base branch, not the PR branch.',
                'recommendation': 'Review pull_request_target usage carefully'
            })
        
        # Check for workflows without timeout
        if 'timeout-minutes' not in content:
            issues.append({
                'category': 'workflow_design',
                'severity': SeverityLevel.INFO,
                'title': 'No timeout configured',
                'description': 'Workflow does not have timeout configured. This can lead to runaway jobs.',
                'recommendation': 'Add timeout-minutes to prevent runaway jobs'
            })
        
        return issues
    
    @staticmethod
    def _calculate_risk(issues: List[Dict]) -> Tuple[float, str]:
        """Calculate overall risk score and level"""
        if not issues:
            return 0.0, 'minimal'
        
        # Weight by severity
        weights = {
            SeverityLevel.CRITICAL: 25,
            SeverityLevel.HIGH: 15,
            SeverityLevel.MEDIUM: 8,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 1
        }
        
        total_score = sum(weights.get(issue['severity'], 0) for issue in issues)
        
        # Normalize to 0-100
        risk_score = min(100, total_score)
        
        # Determine risk level
        if risk_score >= 75:
            risk_level = 'critical'
        elif risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 25:
            risk_level = 'medium'
        elif risk_score >= 10:
            risk_level = 'low'
        else:
            risk_level = 'minimal'
        
        return round(risk_score, 2), risk_level
    
    @staticmethod
    def _generate_recommendations(issues: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on issues found"""
        recommendations = []
        
        categories = set(issue['category'] for issue in issues)
        
        if 'secrets' in categories:
            recommendations.append('🔐 Use GitHub Secrets to store sensitive data instead of hardcoding')
            recommendations.append('🔍 Review and remove all hardcoded credentials immediately')
        
        if 'unsafe_actions' in categories:
            recommendations.append('📌 Pin GitHub Actions to specific commit SHAs for better security')
            recommendations.append('🔄 Update outdated actions to their latest versions')
        
        if 'permissions' in categories:
            recommendations.append('🔒 Apply least privilege principle - only grant necessary permissions')
            recommendations.append('📝 Document why write permissions are needed')
        
        if 'injection' in categories:
            recommendations.append('🛡️ Sanitize all user inputs before using in shell commands')
            recommendations.append('💡 Use environment variables instead of directly interpolating user input')
        
        if not recommendations:
            recommendations.append('✅ No major security issues found - continue following best practices')
        
        return recommendations
