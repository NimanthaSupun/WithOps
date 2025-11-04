"""
Simple analyzer test
"""
import yaml
from pathlib import Path

def quick_analysis():
    print("🔍 Quick Workflow Analysis")
    print("=" * 40)
    
    data_dir = Path("data/workflows")
    yml_files = list(data_dir.glob("*.yml"))
    
    print(f"Found {len(yml_files)} YAML files")
    
    # Sample analysis of first few files
    secrets_count = 0
    external_actions_count = 0
    risky_permissions_count = 0
    
    for i, file_path in enumerate(yml_files[:10]):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = yaml.safe_load(content)
            
            if not data:
                continue
                
            # Check for secrets usage
            if 'secrets.' in content.lower() or '${{ secrets' in content.lower():
                secrets_count += 1
            
            # Check for external actions
            jobs = data.get('jobs', {})
            for job in jobs.values():
                if isinstance(job, dict):
                    steps = job.get('steps', [])
                    for step in steps:
                        if isinstance(step, dict) and 'uses' in step:
                            action = step['uses']
                            if '/' in action and not action.startswith(('actions/', 'github/')):
                                external_actions_count += 1
                                break
            
            # Check for risky permissions
            if 'permissions' in data:
                perms = data['permissions']
                if isinstance(perms, dict):
                    if any('write' in str(v).lower() for v in perms.values()):
                        risky_permissions_count += 1
            
            print(f"{i+1:2d}. {file_path.name[:30]:<30} ✓")
            
        except Exception as e:
            print(f"{i+1:2d}. {file_path.name[:30]:<30} ❌ {str(e)[:20]}")
    
    print("\n" + "=" * 40)
    print("📊 Quick Analysis Results:")
    print(f"   🔐 Workflows using secrets: {secrets_count}/10")
    print(f"   🔗 Workflows with external actions: {external_actions_count}/10")
    print(f"   ⚠️  Workflows with write permissions: {risky_permissions_count}/10")
    print("=" * 40)

if __name__ == "__main__":
    quick_analysis()