"""
Enhanced GitHub Workflow Data Collector

This script collects a larger, more diverse dataset of GitHub Actions workflow files
from multiple programming languages and repository types.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Add the parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data_collection.github_workflow_collector import GitHubWorkflowCollector

def main():
    print("🚀 Enhanced GitHub Workflow Collection")
    print("="*60)
    
    # Get GitHub token from .env file
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        print("✅ Using GitHub token from .env file (higher rate limits)")
    else:
        print("⚠️  No GitHub token found in .env file")
        print("   This collection will be limited without a token")
        return
    
    print("\nTarget: Collect 100-200 workflow files from diverse languages")
    print("="*60)
    
    collector = GitHubWorkflowCollector(github_token)
    
    # Expanded language list for better diversity
    languages_config = {
        # Backend languages
        "python": 15,      # Web apps, data science, APIs
        "javascript": 12,  # Node.js, full-stack apps
        "typescript": 12,  # Modern web development
        "java": 10,        # Enterprise applications
        "go": 10,          # Cloud-native, microservices
        "rust": 8,         # Systems programming, CLI tools
        "csharp": 8,       # .NET applications
        "php": 6,          # Web applications
        
        # Frontend frameworks
        "vue": 5,          # Vue.js applications
        "react": 5,        # React applications (via JavaScript)
        
        # DevOps & Infrastructure
        "shell": 4,        # DevOps scripts
        "dockerfile": 4,   # Container workflows
    }
    
    print(f"Languages to collect from: {list(languages_config.keys())}")
    print(f"Total target repositories: {sum(languages_config.values())}")
    print("\nStarting collection (this will take 10-15 minutes)...\n")
    
    all_stats = {}
    total_collected = 0
    
    try:
        for i, (language, repo_count) in enumerate(languages_config.items(), 1):
            print(f"[{i}/{len(languages_config)}] Processing {language} repositories ({repo_count} repos)...")
            
            # Collect workflows for this language
            stats = collector.collect_workflows(
                languages=[language],
                repos_per_language=repo_count
            )
            
            # Track stats
            if language in stats:
                all_stats[language] = stats[language]
                total_collected += stats[language]
                print(f"  ✅ Collected {stats[language]} workflows from {language}")
            else:
                all_stats[language] = 0
                print(f"  ⚠️  No new workflows collected from {language}")
            
            print(f"  Running total: {total_collected} workflows\n")
        
        # Final summary
        print("="*60)
        print("🎉 ENHANCED COLLECTION COMPLETED!")
        print("="*60)
        
        print(f"Total workflows collected this session: {sum(all_stats.values())}")
        print(f"Grand total workflows: {total_collected}")
        
        print("\nBreakdown by language:")
        for language, count in all_stats.items():
            if count > 0:
                print(f"  ✅ {language}: {count} workflows")
            else:
                print(f"  ⚪ {language}: {count} workflows (already collected)")
        
        # Show file information
        data_dir = Path(__file__).parent / "data" / "workflows"
        workflow_files = list(data_dir.glob('*.yml')) + list(data_dir.glob('*.yaml'))
        
        print(f"\nTotal workflow files on disk: {len(workflow_files)}")
        print(f"Files location: {data_dir}")
        
        if len(workflow_files) >= 50:
            print("\n🎯 Great! You now have enough data to start ML training")
            print("   Next step: Build the security analyzer")
        elif len(workflow_files) >= 20:
            print("\n👍 Good dataset size for initial development")
            print("   Can start building basic security rules")
        else:
            print("\n📝 Small dataset - consider running again or")
            print("   adding GitHub personal access token for better results")
        
        # Show some sample recent files
        recent_files = sorted(workflow_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        print(f"\nRecent workflow files:")
        for i, file in enumerate(recent_files, 1):
            print(f"  {i}. {file.name}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Collection interrupted by user")
        print(f"Collected {total_collected} workflows before interruption")
    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        print("Check your internet connection and GitHub API access")

if __name__ == "__main__":
    main()