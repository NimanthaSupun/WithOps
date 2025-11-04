"""
Workflow Data Analyzer

Analyzes the collected GitHub workflow files to understand patterns
and prepare for ML feature extraction.
"""

import json
import yaml
from pathlib import Path
from collections import defaultdict, Counter
import re

class WorkflowAnalyzer:
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data" / "workflows"
        self.metadata_file = self.data_dir / "metadata.json"
        
    def load_metadata(self):
        """Load collection metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def get_workflow_files(self):
        """Get all workflow files"""
        yml_files = list(self.data_dir.glob('*.yml'))
        yaml_files = list(self.data_dir.glob('*.yaml'))
        return yml_files + yaml_files
    
    def parse_workflow(self, file_path):
        """Parse a workflow file and extract key information"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = yaml.safe_load(content)
            
            if not isinstance(data, dict):
                return None
            
            info = {
                'filename': file_path.name,
                'triggers': self.extract_triggers(data),
                'jobs': self.extract_jobs(data),
                'actions_used': self.extract_actions(data),
                'secrets_used': self.extract_secrets(content),
                'permissions': self.extract_permissions(data),
                'env_vars': self.extract_env_vars(data),
                'security_concerns': self.identify_security_concerns(data, content)
            }
            
            return info
            
        except Exception as e:
            print(f"Error parsing {file_path.name}: {e}")
            return None
    
    def extract_triggers(self, data):
        """Extract workflow triggers"""
        triggers = []
        if 'on' in data:
            trigger_data = data['on']
            if isinstance(trigger_data, str):
                triggers.append(trigger_data)
            elif isinstance(trigger_data, list):
                triggers.extend(trigger_data)
            elif isinstance(trigger_data, dict):
                triggers.extend(trigger_data.keys())
        return triggers
    
    def extract_jobs(self, data):
        """Extract job information"""
        jobs = []
        if 'jobs' in data and isinstance(data['jobs'], dict):
            for job_id, job_data in data['jobs'].items():
                if isinstance(job_data, dict):
                    jobs.append({
                        'id': job_id,
                        'runs_on': job_data.get('runs-on', 'unknown'),
                        'steps_count': len(job_data.get('steps', []))
                    })
        return jobs
    
    def extract_actions(self, data):
        """Extract GitHub Actions used"""
        actions = []
        
        def find_actions(obj):
            if isinstance(obj, dict):
                if 'uses' in obj:
                    action = obj['uses']
                    if isinstance(action, str):
                        actions.append(action)
                for value in obj.values():
                    find_actions(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_actions(item)
        
        find_actions(data)
        return list(set(actions))  # Remove duplicates
    
    def extract_secrets(self, content):
        """Find potential secrets in workflow content"""
        secret_patterns = [
            r'secrets\.',
            r'\$\{\{\s*secrets\.',
            r'password',
            r'token',
            r'api[_-]?key',
            r'private[_-]?key'
        ]
        
        secrets = []
        for pattern in secret_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            secrets.extend(matches)
        
        return list(set(secrets))
    
    def extract_permissions(self, data):
        """Extract permissions used"""
        permissions = []
        
        def find_permissions(obj):
            if isinstance(obj, dict):
                if 'permissions' in obj:
                    perm_data = obj['permissions']
                    if isinstance(perm_data, dict):
                        permissions.extend(perm_data.keys())
                    elif isinstance(perm_data, str):
                        permissions.append(perm_data)
                for value in obj.values():
                    find_permissions(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_permissions(item)
        
        find_permissions(data)
        return list(set(permissions))
    
    def extract_env_vars(self, data):
        """Extract environment variables"""
        env_vars = []
        
        def find_env(obj):
            if isinstance(obj, dict):
                if 'env' in obj and isinstance(obj['env'], dict):
                    env_vars.extend(obj['env'].keys())
                for value in obj.values():
                    find_env(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_env(item)
        
        find_env(data)
        return list(set(env_vars))
    
    def identify_security_concerns(self, data, content):
        """Identify potential security issues"""
        concerns = []
        
        # Check for overprivileged permissions
        if 'write-all' in content:
            concerns.append('overprivileged_permissions')
        
        # Check for hardcoded secrets
        if re.search(r'["\'][a-zA-Z0-9]{20,}["\']', content):
            concerns.append('potential_hardcoded_secrets')
        
        # Check for pull_request_target (can be dangerous)
        if 'pull_request_target' in content:
            concerns.append('pull_request_target_trigger')
        
        # Check for checkout without ref pinning
        if 'actions/checkout@' in content and '@v' not in content:
            concerns.append('unpinned_checkout_action')
        
        # Check for script injection potential
        if '${{' in content and 'github.event' in content:
            concerns.append('potential_script_injection')
        
        return concerns
    
    def analyze_dataset(self):
        """Analyze the entire dataset"""
        print("🔍 Analyzing Workflow Dataset")
        print("="*50)
        
        # Load metadata
        metadata = self.load_metadata()
        workflow_files = self.get_workflow_files()
        
        print(f"Total workflow files: {len(workflow_files)}")
        if metadata:
            print(f"Repositories processed: {len(metadata.get('collected_repos', []))}")
        
        # Parse all workflows
        parsed_workflows = []
        for file_path in workflow_files:
            workflow_info = self.parse_workflow(file_path)
            if workflow_info:
                parsed_workflows.append(workflow_info)
        
        print(f"Successfully parsed: {len(parsed_workflows)} workflows")
        print()
        
        # Analyze patterns
        self.analyze_triggers(parsed_workflows)
        self.analyze_actions(parsed_workflows)
        self.analyze_security_concerns(parsed_workflows)
        self.analyze_job_patterns(parsed_workflows)
        
        return parsed_workflows
    
    def analyze_triggers(self, workflows):
        """Analyze workflow triggers"""
        print("📋 Trigger Analysis")
        print("-" * 30)
        
        trigger_counts = Counter()
        for workflow in workflows:
            for trigger in workflow['triggers']:
                trigger_counts[trigger] += 1
        
        print("Most common triggers:")
        for trigger, count in trigger_counts.most_common(10):
            print(f"  {trigger}: {count} workflows")
        print()
    
    def analyze_actions(self, workflows):
        """Analyze GitHub Actions usage"""
        print("🔧 Actions Analysis")
        print("-" * 30)
        
        action_counts = Counter()
        for workflow in workflows:
            for action in workflow['actions_used']:
                # Normalize action names (remove version)
                action_name = action.split('@')[0] if '@' in action else action
                action_counts[action_name] += 1
        
        print("Most used actions:")
        for action, count in action_counts.most_common(15):
            print(f"  {action}: {count} workflows")
        print()
    
    def analyze_security_concerns(self, workflows):
        """Analyze security patterns"""
        print("🔒 Security Analysis")
        print("-" * 30)
        
        concern_counts = Counter()
        total_concerns = 0
        
        for workflow in workflows:
            for concern in workflow['security_concerns']:
                concern_counts[concern] += 1
                total_concerns += 1
        
        print(f"Workflows with security concerns: {len([w for w in workflows if w['security_concerns']])}")
        print(f"Total security issues found: {total_concerns}")
        print()
        
        if concern_counts:
            print("Security concerns found:")
            for concern, count in concern_counts.most_common():
                print(f"  {concern}: {count} workflows")
        else:
            print("No major security concerns detected in this sample")
        print()
    
    def analyze_job_patterns(self, workflows):
        """Analyze job patterns"""
        print("⚙️  Job Patterns Analysis")
        print("-" * 30)
        
        runner_counts = Counter()
        total_jobs = 0
        total_steps = 0
        
        for workflow in workflows:
            for job in workflow['jobs']:
                # Handle runs-on as list or string
                runs_on = job['runs_on']
                if isinstance(runs_on, list):
                    runs_on = ', '.join(runs_on)
                runner_counts[runs_on] += 1
                total_jobs += 1
                total_steps += job['steps_count']
        
        avg_steps = total_steps / total_jobs if total_jobs > 0 else 0
        
        print(f"Total jobs analyzed: {total_jobs}")
        print(f"Average steps per job: {avg_steps:.1f}")
        print()
        
        print("Runner usage:")
        for runner, count in runner_counts.most_common():
            print(f"  {runner}: {count} jobs")
        print()

def main():
    analyzer = WorkflowAnalyzer()
    workflows = analyzer.analyze_dataset()
    
    print("📊 Analysis Complete!")
    print("="*50)
    print("This data shows patterns in your collected workflows.")
    print("Next: Use this info to build ML features for security scanning.")

if __name__ == "__main__":
    main()