"""
ML Feature Extraction Pipeline

Converts GitHub Actions workflow YAML files into numerical features
for machine learning model training and prediction.
"""

import numpy as np
import pandas as pd
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set
from dataclasses import dataclass
from collections import Counter
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, LabelEncoder

logger = logging.getLogger(__name__)

@dataclass
class WorkflowFeatures:
    """Container for extracted workflow features"""
    # Basic workflow metadata
    filename: str
    job_count: int
    step_count: int
    trigger_count: int
    
    # Security-related features
    uses_secrets: bool
    external_action_count: int
    write_permission_count: int
    dangerous_trigger_count: int
    hardcoded_secret_count: int
    
    # Action and command features
    trusted_action_ratio: float
    unpinned_action_ratio: float
    shell_command_count: int
    curl_wget_count: int
    
    # Permission features
    has_write_all: bool
    has_admin_permissions: bool
    permission_scope_count: int
    
    # Trigger features  
    has_pull_request_target: bool
    has_workflow_dispatch: bool
    has_schedule: bool
    
    # Complexity features
    conditional_step_count: int
    matrix_job_count: int
    environment_count: int
    
    # Content analysis features
    yaml_complexity_score: float
    action_diversity_score: float
    
    # Risk indicators
    risk_score: float

class WorkflowFeatureExtractor:
    """Extracts ML features from GitHub Actions workflows"""
    
    def __init__(self):
        # Known trusted action sources
        self.trusted_sources = {
            'actions/', 'github/', 'docker/', 'azure/', 
            'aws-actions/', 'google-github-actions/'
        }
        
        # Dangerous patterns
        self.secret_patterns = [
            r'password.*=.*["\'].*["\']',
            r'token.*=.*["\'].*["\']', 
            r'key.*=.*["\'].*["\']',
            r'secret.*=.*["\'].*["\']',
            r'api.*key.*=.*["\'].*["\']'
        ]
        
        # Risky commands
        self.risky_commands = ['curl', 'wget', 'eval', 'bash', 'sh', 'sudo']
        
        # Initialize text vectorizer for action names
        self.action_vectorizer = TfidfVectorizer(
            max_features=50, 
            stop_words=None,
            lowercase=True
        )
        
        # Track all actions seen for vocabulary building
        self.all_actions = set()
        
    def extract_features(self, workflow_path: Path) -> WorkflowFeatures:
        """
        Extract comprehensive features from a single workflow file.
        
        Args:
            workflow_path: Path to workflow YAML file
            
        Returns:
            WorkflowFeatures object with extracted features
        """
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                content = f.read()
                workflow_data = yaml.safe_load(content)
            
            if not workflow_data or not isinstance(workflow_data, dict):
                return self._create_empty_features(workflow_path.name)
            
            # Extract all feature categories
            basic_features = self._extract_basic_features(workflow_data)
            security_features = self._extract_security_features(workflow_data, content)
            action_features = self._extract_action_features(workflow_data)
            permission_features = self._extract_permission_features(workflow_data)
            trigger_features = self._extract_trigger_features(workflow_data)
            complexity_features = self._extract_complexity_features(workflow_data)
            content_features = self._extract_content_features(workflow_data, content)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(
                security_features, permission_features, action_features
            )
            
            return WorkflowFeatures(
                filename=workflow_path.name,
                # Basic features
                job_count=basic_features['job_count'],
                step_count=basic_features['step_count'],
                trigger_count=basic_features['trigger_count'],
                
                # Security features
                uses_secrets=security_features['uses_secrets'],
                external_action_count=security_features['external_action_count'],
                write_permission_count=security_features['write_permission_count'],
                dangerous_trigger_count=security_features['dangerous_trigger_count'],
                hardcoded_secret_count=security_features['hardcoded_secret_count'],
                
                # Action features
                trusted_action_ratio=action_features['trusted_action_ratio'],
                unpinned_action_ratio=action_features['unpinned_action_ratio'],
                shell_command_count=action_features['shell_command_count'],
                curl_wget_count=action_features['curl_wget_count'],
                
                # Permission features
                has_write_all=permission_features['has_write_all'],
                has_admin_permissions=permission_features['has_admin_permissions'],
                permission_scope_count=permission_features['permission_scope_count'],
                
                # Trigger features
                has_pull_request_target=trigger_features['has_pull_request_target'],
                has_workflow_dispatch=trigger_features['has_workflow_dispatch'],
                has_schedule=trigger_features['has_schedule'],
                
                # Complexity features
                conditional_step_count=complexity_features['conditional_step_count'],
                matrix_job_count=complexity_features['matrix_job_count'],
                environment_count=complexity_features['environment_count'],
                
                # Content features
                yaml_complexity_score=content_features['yaml_complexity_score'],
                action_diversity_score=content_features['action_diversity_score'],
                
                # Risk score
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error(f"Error extracting features from {workflow_path}: {e}")
            return self._create_empty_features(workflow_path.name)
    
    def _create_empty_features(self, filename: str) -> WorkflowFeatures:
        """Create empty feature set for failed extractions"""
        return WorkflowFeatures(
            filename=filename,
            job_count=0, step_count=0, trigger_count=0,
            uses_secrets=False, external_action_count=0, write_permission_count=0,
            dangerous_trigger_count=0, hardcoded_secret_count=0,
            trusted_action_ratio=0.0, unpinned_action_ratio=0.0,
            shell_command_count=0, curl_wget_count=0,
            has_write_all=False, has_admin_permissions=False, permission_scope_count=0,
            has_pull_request_target=False, has_workflow_dispatch=False, has_schedule=False,
            conditional_step_count=0, matrix_job_count=0, environment_count=0,
            yaml_complexity_score=0.0, action_diversity_score=0.0,
            risk_score=0.0
        )
    
    def _extract_basic_features(self, workflow_data: Dict) -> Dict[str, Any]:
        """Extract basic workflow structure features"""
        jobs = workflow_data.get('jobs', {})
        job_count = len(jobs)
        
        step_count = 0
        for job_data in jobs.values():
            if isinstance(job_data, dict):
                steps = job_data.get('steps', [])
                step_count += len(steps)
        
        # Count triggers
        on_data = workflow_data.get('on', {})
        if isinstance(on_data, str):
            trigger_count = 1
        elif isinstance(on_data, list):
            trigger_count = len(on_data)
        elif isinstance(on_data, dict):
            trigger_count = len(on_data)
        else:
            trigger_count = 0
            
        return {
            'job_count': job_count,
            'step_count': step_count,
            'trigger_count': trigger_count
        }
    
    def _extract_security_features(self, workflow_data: Dict, content: str) -> Dict[str, Any]:
        """Extract security-related features"""
        # Check for secrets usage
        uses_secrets = ('secrets.' in content.lower() or 
                       '${{ secrets' in content.lower() or
                       'secrets:' in content.lower())
        
        # Count external actions
        external_action_count = 0
        jobs = workflow_data.get('jobs', {})
        for job_data in jobs.values():
            if isinstance(job_data, dict):
                steps = job_data.get('steps', [])
                for step in steps:
                    if isinstance(step, dict) and 'uses' in step:
                        action = step['uses']
                        if self._is_external_action(action):
                            external_action_count += 1
        
        # Count write permissions
        write_permission_count = 0
        permissions = self._get_all_permissions(workflow_data)
        for perm_value in permissions.values():
            if 'write' in str(perm_value).lower():
                write_permission_count += 1
        
        # Count dangerous triggers
        dangerous_trigger_count = 0
        triggers = self._get_triggers(workflow_data)
        dangerous_triggers = ['pull_request_target', 'repository_dispatch']
        for trigger in triggers:
            if trigger in dangerous_triggers:
                dangerous_trigger_count += 1
        
        # Count hardcoded secrets
        hardcoded_secret_count = 0
        for pattern in self.secret_patterns:
            hardcoded_secret_count += len(re.findall(pattern, content, re.IGNORECASE))
        
        return {
            'uses_secrets': uses_secrets,
            'external_action_count': external_action_count,
            'write_permission_count': write_permission_count,
            'dangerous_trigger_count': dangerous_trigger_count,
            'hardcoded_secret_count': hardcoded_secret_count
        }
    
    def _extract_action_features(self, workflow_data: Dict) -> Dict[str, Any]:
        """Extract action-related features"""
        all_actions = []
        shell_command_count = 0
        curl_wget_count = 0
        
        jobs = workflow_data.get('jobs', {})
        for job_data in jobs.values():
            if isinstance(job_data, dict):
                steps = job_data.get('steps', [])
                for step in steps:
                    if isinstance(step, dict):
                        # Collect actions
                        if 'uses' in step:
                            all_actions.append(step['uses'])
                            self.all_actions.add(step['uses'])
                        
                        # Count shell commands
                        if 'run' in step:
                            shell_command_count += 1
                            command = str(step['run']).lower()
                            if 'curl' in command or 'wget' in command:
                                curl_wget_count += 1
        
        # Calculate ratios
        total_actions = len(all_actions)
        if total_actions > 0:
            trusted_count = sum(1 for action in all_actions if self._is_trusted_action(action))
            unpinned_count = sum(1 for action in all_actions if not self._is_pinned_action(action))
            
            trusted_action_ratio = trusted_count / total_actions
            unpinned_action_ratio = unpinned_count / total_actions
        else:
            trusted_action_ratio = 0.0
            unpinned_action_ratio = 0.0
        
        return {
            'trusted_action_ratio': trusted_action_ratio,
            'unpinned_action_ratio': unpinned_action_ratio,
            'shell_command_count': shell_command_count,
            'curl_wget_count': curl_wget_count
        }
    
    def _extract_permission_features(self, workflow_data: Dict) -> Dict[str, Any]:
        """Extract permission-related features"""
        permissions = self._get_all_permissions(workflow_data)
        
        has_write_all = any('write-all' in str(perm).lower() for perm in permissions.values())
        has_admin_permissions = any('admin' in str(perm).lower() for perm in permissions.values())
        permission_scope_count = len(permissions)
        
        return {
            'has_write_all': has_write_all,
            'has_admin_permissions': has_admin_permissions,
            'permission_scope_count': permission_scope_count
        }
    
    def _extract_trigger_features(self, workflow_data: Dict) -> Dict[str, Any]:
        """Extract trigger-related features"""
        triggers = self._get_triggers(workflow_data)
        
        return {
            'has_pull_request_target': 'pull_request_target' in triggers,
            'has_workflow_dispatch': 'workflow_dispatch' in triggers,
            'has_schedule': 'schedule' in triggers
        }
    
    def _extract_complexity_features(self, workflow_data: Dict) -> Dict[str, Any]:
        """Extract workflow complexity features"""
        conditional_step_count = 0
        matrix_job_count = 0
        environment_count = 0
        
        jobs = workflow_data.get('jobs', {})
        for job_data in jobs.values():
            if isinstance(job_data, dict):
                # Check for matrix strategy
                if 'strategy' in job_data and 'matrix' in job_data['strategy']:
                    matrix_job_count += 1
                
                # Check for environment
                if 'environment' in job_data:
                    environment_count += 1
                
                # Count conditional steps
                steps = job_data.get('steps', [])
                for step in steps:
                    if isinstance(step, dict) and 'if' in step:
                        conditional_step_count += 1
        
        return {
            'conditional_step_count': conditional_step_count,
            'matrix_job_count': matrix_job_count,
            'environment_count': environment_count
        }
    
    def _extract_content_features(self, workflow_data: Dict, content: str) -> Dict[str, Any]:
        """Extract content analysis features"""
        # YAML complexity (rough measure)
        yaml_lines = len(content.split('\n'))
        yaml_complexity_score = min(yaml_lines / 100.0, 1.0)  # Normalize to 0-1
        
        # Action diversity
        all_actions = []
        jobs = workflow_data.get('jobs', {})
        for job_data in jobs.values():
            if isinstance(job_data, dict):
                steps = job_data.get('steps', [])
                for step in steps:
                    if isinstance(step, dict) and 'uses' in step:
                        action_base = step['uses'].split('@')[0]  # Remove version
                        all_actions.append(action_base)
        
        if all_actions:
            unique_actions = len(set(all_actions))
            total_actions = len(all_actions)
            action_diversity_score = unique_actions / total_actions
        else:
            action_diversity_score = 0.0
        
        return {
            'yaml_complexity_score': yaml_complexity_score,
            'action_diversity_score': action_diversity_score
        }
    
    def _calculate_risk_score(self, security_features: Dict, 
                             permission_features: Dict, 
                             action_features: Dict) -> float:
        """Calculate overall risk score"""
        score = 0.0
        
        # Security risk factors
        if security_features['uses_secrets']:
            score += 10
        score += security_features['external_action_count'] * 2
        score += security_features['write_permission_count'] * 5
        score += security_features['dangerous_trigger_count'] * 15
        score += security_features['hardcoded_secret_count'] * 20
        
        # Permission risk factors
        if permission_features['has_write_all']:
            score += 25
        if permission_features['has_admin_permissions']:
            score += 30
        
        # Action risk factors
        score += action_features['unpinned_action_ratio'] * 15
        score += action_features['curl_wget_count'] * 5
        
        return min(score, 100.0)  # Cap at 100
    
    def _is_external_action(self, action: str) -> bool:
        """Check if action is external (potentially untrusted)"""
        if not action or not isinstance(action, str):
            return False
        return not any(action.startswith(trusted) for trusted in self.trusted_sources)
    
    def _is_trusted_action(self, action: str) -> bool:
        """Check if action is from trusted source"""
        return not self._is_external_action(action)
    
    def _is_pinned_action(self, action: str) -> bool:
        """Check if action is pinned to specific version/commit"""
        if not action:
            return False
        return bool(re.search(r'@(v\d+|\d+\.\d+|[a-f0-9]{40})', action))
    
    def _get_all_permissions(self, workflow_data: Dict) -> Dict[str, str]:
        """Extract all permissions from workflow"""
        permissions = {}
        
        # Global permissions
        if 'permissions' in workflow_data:
            global_perms = workflow_data['permissions']
            if isinstance(global_perms, dict):
                permissions.update(global_perms)
            elif isinstance(global_perms, str):
                permissions['global'] = global_perms
        
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
    
    def _get_triggers(self, workflow_data: Dict) -> List[str]:
        """Extract workflow triggers"""
        triggers = []
        on_data = workflow_data.get('on', {})
        
        if isinstance(on_data, str):
            triggers.append(on_data)
        elif isinstance(on_data, list):
            triggers.extend(on_data)
        elif isinstance(on_data, dict):
            triggers.extend(on_data.keys())
        
        return triggers

def main():
    """Test the feature extraction pipeline"""
    print("🔬 Testing ML Feature Extraction Pipeline")
    print("=" * 60)
    
    # Initialize extractor
    extractor = WorkflowFeatureExtractor()
    
    # Find workflow files
    data_dir = Path("data/workflows")
    workflow_files = list(data_dir.glob("*.yml")) + list(data_dir.glob("*.yaml"))
    
    if not workflow_files:
        print("❌ No workflow files found!")
        return
    
    print(f"Extracting features from {len(workflow_files)} workflow files...")
    
    # Extract features from first 10 files for demo
    feature_data = []
    
    for i, file_path in enumerate(workflow_files[:10]):
        print(f"Processing {i+1}/10: {file_path.name}")
        
        features = extractor.extract_features(file_path)
        feature_data.append(features)
    
    # Convert to pandas DataFrame for analysis
    feature_dict = {}
    for field in WorkflowFeatures.__dataclass_fields__:
        if field != 'filename':
            feature_dict[field] = [getattr(f, field) for f in feature_data]
    
    df = pd.DataFrame(feature_dict)
    
    print(f"\n" + "=" * 60)
    print("📊 FEATURE EXTRACTION RESULTS")
    print("=" * 60)
    print(f"Features extracted: {len(df.columns)}")
    print(f"Workflows processed: {len(df)}")
    
    print(f"\n📈 Feature Statistics:")
    print(f"Average risk score: {df['risk_score'].mean():.1f}")
    print(f"Workflows using secrets: {df['uses_secrets'].sum()}/{len(df)}")
    print(f"Workflows with external actions: {(df['external_action_count'] > 0).sum()}/{len(df)}")
    print(f"Average jobs per workflow: {df['job_count'].mean():.1f}")
    
    print(f"\n🔍 High-risk workflows (score > 30):")
    high_risk = df[df['risk_score'] > 30]
    for i, (idx, row) in enumerate(high_risk.iterrows()):
        filename = feature_data[idx].filename
        print(f"  {i+1}. {filename}: {row['risk_score']:.1f}/100")
    
    print(f"\n✅ Feature extraction pipeline ready!")
    print(f"💾 Ready to create training dataset from all {len(workflow_files)} workflows")

if __name__ == "__main__":
    main()