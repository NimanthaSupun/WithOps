"""
Workflow Security Analyzer

Analyzes GitHub Actions workflow files for security vulnerabilities and patterns.
This forms the foundation for ML feature extraction.
"""

import os
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class SecurityFinding:
    """Represents a security finding in a workflow"""
    category: str
    severity: RiskLevel
    description: str
    line_number: int = None
    suggestion: str = None

@dataclass
class WorkflowAnalysis:
    """Complete analysis results for a workflow"""
    filename: str
    total_jobs: int
    uses_secrets: bool
    permissions: Dict[str, str]
    external_actions: List[str]
    security_findings: List[SecurityFinding]
    risk_score: float
    triggers: List[str]

class WorkflowSecurityAnalyzer:
    """Analyzes GitHub Actions workflows for security issues"""
    
    def __init__(self):
        # Known risky patterns
        self.secret_patterns = [
            r'password.*=.*["\'].*["\']',
            r'token.*=.*["\'].*["\']',
            r'key.*=.*["\'].*["\']',
            r'secret.*=.*["\'].*["\']',
        ]
        
        # Trusted action sources
        self.trusted_sources = {
            'actions/',
            'github/',
            'docker/',
            'azure/',
            'aws-actions/',
            'google-github-actions/',
        }
        
        # Risky permissions
        self.risky_permissions = {
            'write-all': RiskLevel.CRITICAL,
            'admin': RiskLevel.CRITICAL,
            'contents: write': RiskLevel.HIGH,
            'actions: write': RiskLevel.HIGH,
            'checks: write': RiskLevel.MEDIUM,
            'deployments: write': RiskLevel.MEDIUM,
        }

    def analyze_workflow(self, file_path: Path) -> WorkflowAnalysis:
        """
        Analyze a single workflow file for security issues.
        
        Args:
            file_path: Path to the workflow YAML file
            
        Returns:
            WorkflowAnalysis object with complete analysis results
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                workflow_data = yaml.safe_load(content)
            
            if not workflow_data or not isinstance(workflow_data, dict):
                return self._create_empty_analysis(file_path.name, "Invalid YAML structure")
            
            # Extract basic information
            jobs = workflow_data.get('jobs', {})
            permissions = self._extract_permissions(workflow_data)
            external_actions = self._find_external_actions(workflow_data)
            triggers = self._extract_triggers(workflow_data)
            
            # Analyze for security issues
            security_findings = []
            security_findings.extend(self._check_hardcoded_secrets(content))
            security_findings.extend(self._check_permissions(permissions))
            security_findings.extend(self._check_external_actions(external_actions))
            security_findings.extend(self._check_pull_request_triggers(triggers))
            security_findings.extend(self._check_code_injection(workflow_data))
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(security_findings, permissions, external_actions)
            
            # Check if secrets are used
            uses_secrets = self._uses_secrets(workflow_data)
            
            return WorkflowAnalysis(
                filename=file_path.name,
                total_jobs=len(jobs),
                uses_secrets=uses_secrets,
                permissions=permissions,
                external_actions=external_actions,
                security_findings=security_findings,
                risk_score=risk_score,
                triggers=triggers
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return self._create_empty_analysis(file_path.name, f"Analysis error: {str(e)}")

    def _create_empty_analysis(self, filename: str, error_msg: str) -> WorkflowAnalysis:
        """Create empty analysis for failed parsing"""
        return WorkflowAnalysis(
            filename=filename,
            total_jobs=0,
            uses_secrets=False,
            permissions={},
            external_actions=[],
            security_findings=[SecurityFinding("parse_error", RiskLevel.LOW, error_msg)],
            risk_score=0.0,
            triggers=[]
        )

    def _extract_permissions(self, workflow_data: Dict) -> Dict[str, str]:
        """Extract permissions from workflow"""
        permissions = {}
        
        # Global permissions
        if 'permissions' in workflow_data:
            perm_data = workflow_data['permissions']
            if isinstance(perm_data, dict):
                permissions.update(perm_data)
            elif isinstance(perm_data, str):
                permissions['global'] = perm_data
        
        # Job-level permissions
        jobs = workflow_data.get('jobs', {})
        for job_name, job_data in jobs.items():
            if isinstance(job_data, dict) and 'permissions' in job_data:
                job_perms = job_data['permissions']
                if isinstance(job_perms, dict):
                    for perm, value in job_perms.items():
                        permissions[f"{job_name}.{perm}"] = value
                elif isinstance(job_perms, str):
                    permissions[f"{job_name}.global"] = job_perms
        
        return permissions

    def _find_external_actions(self, workflow_data: Dict) -> List[str]:
        """Find all external actions used in the workflow"""
        external_actions = []
        
        jobs = workflow_data.get('jobs', {})
        for job_data in jobs.values():
            if not isinstance(job_data, dict):
                continue
                
            steps = job_data.get('steps', [])
            for step in steps:
                if isinstance(step, dict) and 'uses' in step:
                    action = step['uses']
                    if self._is_external_action(action):
                        external_actions.append(action)
        
        return list(set(external_actions))  # Remove duplicates

    def _is_external_action(self, action: str) -> bool:
        """Check if an action is from an external (potentially untrusted) source"""
        if not action:
            return False
            
        # Check if it starts with a trusted source
        for trusted in self.trusted_sources:
            if action.startswith(trusted):
                return False
        
        # If it contains a slash, it's probably external
        return '/' in action

    def _extract_triggers(self, workflow_data: Dict) -> List[str]:
        """Extract workflow triggers"""
        triggers = []
        
        on_data = workflow_data.get('on', workflow_data.get('true', {}))
        
        if isinstance(on_data, str):
            triggers.append(on_data)
        elif isinstance(on_data, list):
            triggers.extend(on_data)
        elif isinstance(on_data, dict):
            triggers.extend(on_data.keys())
        
        return triggers

    def _check_hardcoded_secrets(self, content: str) -> List[SecurityFinding]:
        """Check for hardcoded secrets in workflow content"""
        findings = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in self.secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        category="hardcoded_secrets",
                        severity=RiskLevel.HIGH,
                        description=f"Potential hardcoded secret found: {line.strip()[:50]}...",
                        line_number=i,
                        suggestion="Use GitHub secrets instead of hardcoding sensitive values"
                    ))
        
        return findings

    def _check_permissions(self, permissions: Dict[str, str]) -> List[SecurityFinding]:
        """Check for overly permissive settings"""
        findings = []
        
        for perm_key, perm_value in permissions.items():
            # Check for write-all or overly broad permissions
            if perm_value in ['write-all', 'write']:
                if perm_key == 'global' or '.' not in perm_key:
                    findings.append(SecurityFinding(
                        category="excessive_permissions",
                        severity=RiskLevel.HIGH,
                        description=f"Overly broad permissions: {perm_key}={perm_value}",
                        suggestion="Use specific permissions instead of write-all"
                    ))
            
            # Check for specific risky permissions
            perm_string = f"{perm_key}: {perm_value}"
            for risky_pattern, risk_level in self.risky_permissions.items():
                if risky_pattern.lower() in perm_string.lower():
                    findings.append(SecurityFinding(
                        category="risky_permissions",
                        severity=risk_level,
                        description=f"Risky permission detected: {perm_string}",
                        suggestion="Consider if this permission level is necessary"
                    ))
        
        return findings

    def _check_external_actions(self, external_actions: List[str]) -> List[SecurityFinding]:
        """Check for potentially risky external actions"""
        findings = []
        
        for action in external_actions:
            # Check for unpinned versions
            if not re.search(r'@v\d+|\@[a-f0-9]{40}', action):
                findings.append(SecurityFinding(
                    category="unpinned_action",
                    severity=RiskLevel.MEDIUM,
                    description=f"Unpinned external action: {action}",
                    suggestion="Pin actions to specific versions or commit hashes"
                ))
            
            # Check for suspicious action names
            suspicious_patterns = ['curl', 'wget', 'download', 'install', 'execute']
            action_lower = action.lower()
            for pattern in suspicious_patterns:
                if pattern in action_lower:
                    findings.append(SecurityFinding(
                        category="suspicious_action",
                        severity=RiskLevel.MEDIUM,
                        description=f"Potentially risky action: {action}",
                        suggestion="Review this action's source code and trustworthiness"
                    ))
                    break
        
        return findings

    def _check_pull_request_triggers(self, triggers: List[str]) -> List[SecurityFinding]:
        """Check for risky pull request triggers"""
        findings = []
        
        if 'pull_request_target' in triggers:
            findings.append(SecurityFinding(
                category="risky_trigger",
                severity=RiskLevel.HIGH,
                description="pull_request_target trigger detected",
                suggestion="Be careful with pull_request_target - it runs with repository secrets"
            ))
        
        return findings

    def _check_code_injection(self, workflow_data: Dict) -> List[SecurityFinding]:
        """Check for potential code injection vulnerabilities"""
        findings = []
        
        jobs = workflow_data.get('jobs', {})
        for job_name, job_data in jobs.items():
            if not isinstance(job_data, dict):
                continue
                
            steps = job_data.get('steps', [])
            for step in steps:
                if not isinstance(step, dict):
                    continue
                
                # Check for dangerous command patterns
                if 'run' in step:
                    command = str(step['run'])
                    if '${{' in command and any(dangerous in command.lower() for dangerous in ['github.event', 'github.head_ref']):
                        findings.append(SecurityFinding(
                            category="code_injection",
                            severity=RiskLevel.HIGH,
                            description=f"Potential code injection in job '{job_name}'",
                            suggestion="Sanitize user inputs in run commands"
                        ))
        
        return findings

    def _uses_secrets(self, workflow_data: Dict) -> bool:
        """Check if workflow uses any secrets"""
        content_str = str(workflow_data).lower()
        return 'secrets.' in content_str or '${{ secrets' in content_str

    def _calculate_risk_score(self, findings: List[SecurityFinding], 
                            permissions: Dict[str, str], 
                            external_actions: List[str]) -> float:
        """Calculate overall risk score (0-100)"""
        score = 0.0
        
        # Base score from findings
        for finding in findings:
            if finding.severity == RiskLevel.CRITICAL:
                score += 25
            elif finding.severity == RiskLevel.HIGH:
                score += 15
            elif finding.severity == RiskLevel.MEDIUM:
                score += 10
            else:
                score += 5
        
        # Additional score factors
        if len(external_actions) > 5:
            score += 10  # Many external dependencies
        
        if any('write' in str(p).lower() for p in permissions.values()):
            score += 5  # Has write permissions
        
        return min(score, 100.0)  # Cap at 100

def main():
    """Test the security analyzer on collected workflows"""
    data_dir = Path(__file__).parent / "data" / "workflows"
    
    if not data_dir.exists():
        print("❌ No workflow data found. Run the collector first.")
        return
    
    analyzer = WorkflowSecurityAnalyzer()
    workflow_files = list(data_dir.glob("*.yml")) + list(data_dir.glob("*.yaml"))
    
    print(f"🔍 Analyzing {len(workflow_files)} workflow files...")
    print("="*60)
    
    high_risk_workflows = []
    total_findings = 0
    
    for file_path in workflow_files[:10]:  # Analyze first 10 for demo
        analysis = analyzer.analyze_workflow(file_path)
        total_findings += len(analysis.security_findings)
        
        print(f"\n📄 {analysis.filename}")
        print(f"   Risk Score: {analysis.risk_score:.1f}/100")
        print(f"   Jobs: {analysis.total_jobs}")
        print(f"   External Actions: {len(analysis.external_actions)}")
        print(f"   Security Findings: {len(analysis.security_findings)}")
        
        if analysis.risk_score > 50:
            high_risk_workflows.append(analysis)
        
        # Show top findings
        for finding in analysis.security_findings[:2]:  # Show first 2 findings
            print(f"   ⚠️  {finding.category}: {finding.description[:50]}...")
    
    print(f"\n" + "="*60)
    print(f"📊 ANALYSIS SUMMARY")
    print(f"="*60)
    print(f"Total workflows analyzed: {min(len(workflow_files), 10)}")
    print(f"Total security findings: {total_findings}")
    print(f"High-risk workflows (>50 score): {len(high_risk_workflows)}")
    
    if high_risk_workflows:
        print(f"\n🚨 Highest risk workflows:")
        for analysis in sorted(high_risk_workflows, key=lambda x: x.risk_score, reverse=True)[:5]:
            print(f"   {analysis.filename}: {analysis.risk_score:.1f}/100")

if __name__ == "__main__":
    main()