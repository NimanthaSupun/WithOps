"""
Test script to run the GitHub workflow collector.

This will collect a small sample of workflow files to get started.
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
    print("Starting GitHub Workflow Collection...")
    print("="*50)
    
    # Get GitHub token from .env file
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        print("✅ Using GitHub token from .env file (higher rate limits)")
    else:
        print("⚠️  No GitHub token found in .env file")
        print("   Add GITHUB_TOKEN to .env file for better results")
    
    print("\nCreating collector...")
    collector = GitHubWorkflowCollector(github_token)
    
    print("Starting collection (this may take a few minutes)...")
    print("Collecting from Python and JavaScript repositories...")
    
    try:
        stats = collector.collect_workflows(
            languages=["python", "javascript"],
            repos_per_language=5  # Small test - 5 repos per language
        )
        
        print("\n" + "="*50)
        print("✅ COLLECTION COMPLETED!")
        print("="*50)
        
        total = sum(stats.values())
        print(f"Total workflows collected: {total}")
        
        for language, count in stats.items():
            print(f"  {language}: {count} workflows")
        
        # Show where files are saved
        data_dir = Path(__file__).parent / "data" / "workflows"
        workflow_files = list(data_dir.glob('*.yml')) + list(data_dir.glob('*.yaml'))
        
        print(f"\nFiles saved to: {data_dir}")
        print(f"Number of workflow files: {len(workflow_files)}")
        
        if len(workflow_files) > 0:
            print("\nSample files:")
            for i, file in enumerate(workflow_files[:5]):  # Show first 5 files
                print(f"  {i+1}. {file.name}")
            if len(workflow_files) > 5:
                print(f"  ... and {len(workflow_files) - 5} more")
        
    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        print("Check your internet connection and GitHub API access")

if __name__ == "__main__":
    main()