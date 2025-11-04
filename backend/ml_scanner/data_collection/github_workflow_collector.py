"""
GitHub Workflow Data Collector

This script collects GitHub Actions workflow files from popular public repositories
to build a dataset for training the ML security scanner.
"""

import os
import json
import time
import requests
import yaml
from pathlib import Path
from typing import List, Dict, Any
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitHubWorkflowCollector:
    def __init__(self, github_token: str = None):
        """
        Initialize the workflow collector.
        
        Args:
            github_token: GitHub personal access token (optional, but recommended for higher rate limits)
        """
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevSecOps-ML-Scanner"
        }
        
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
        
        # Create data directory
        self.data_dir = Path(__file__).parent.parent / "data" / "workflows"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata storage
        self.metadata_file = self.data_dir / "metadata.json"
        self.metadata = self.load_metadata()
    
    def load_metadata(self) -> Dict[str, Any]:
        """Load existing metadata or create empty dict"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {"collected_repos": [], "workflow_count": 0, "last_updated": None}
    
    def save_metadata(self):
        """Save metadata to file"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def get_popular_repos(self, language: str = None, limit: int = 50) -> List[Dict]:
        """
        Get popular repositories with GitHub Actions workflows.
        
        Args:
            language: Programming language to filter by
            limit: Number of repositories to return
        """
        logger.info(f"Fetching popular repositories (language: {language}, limit: {limit})")
        
        # Search for repositories with workflows
        query = "workflows in:path .github/workflows"
        if language:
            query += f" language:{language}"
        
        url = f"{self.base_url}/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(limit, 100)
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            repos = data.get("items", [])
            
            logger.info(f"Found {len(repos)} repositories")
            return repos
            
        except requests.RequestException as e:
            logger.error(f"Error fetching repositories: {e}")
            return []
    
    def get_workflow_files(self, repo_owner: str, repo_name: str) -> List[Dict]:
        """
        Get workflow files from a specific repository.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
        """
        logger.info(f"Fetching workflows from {repo_owner}/{repo_name}")
        
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/contents/.github/workflows"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            files = response.json()
            workflow_files = []
            
            for file in files:
                if file["name"].endswith((".yml", ".yaml")) and file["type"] == "file":
                    workflow_files.append(file)
            
            logger.info(f"Found {len(workflow_files)} workflow files")
            return workflow_files
            
        except requests.RequestException as e:
            if response.status_code == 404:
                logger.warning(f"No .github/workflows directory found in {repo_owner}/{repo_name}")
            else:
                logger.error(f"Error fetching workflow files: {e}")
            return []
    
    def download_workflow_content(self, file_info: Dict) -> str:
        """
        Download the content of a workflow file.
        
        Args:
            file_info: File information from GitHub API
        """
        try:
            response = requests.get(file_info["download_url"], headers=self.headers)
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"Error downloading workflow content: {e}")
            return None
    
    def validate_workflow(self, content: str) -> bool:
        """
        Validate that the workflow content is valid YAML and has expected structure.
        
        Args:
            content: Workflow file content
        """
        try:
            data = yaml.safe_load(content)
            
            # Basic validation - check for required fields
            if not isinstance(data, dict):
                return False
            
            # Must have 'on' or 'jobs' sections
            if 'on' not in data and 'jobs' not in data:
                return False
            
            return True
            
        except yaml.YAMLError:
            return False
    
    def save_workflow(self, repo_owner: str, repo_name: str, filename: str, content: str) -> str:
        """
        Save workflow content to local file.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            filename: Workflow filename
            content: Workflow content
        """
        # Create safe filename
        safe_repo_name = f"{repo_owner}_{repo_name}".replace("/", "_")
        safe_filename = f"{safe_repo_name}_{filename}"
        
        file_path = self.data_dir / safe_filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    
    def collect_workflows(self, languages: List[str] = None, repos_per_language: int = 20) -> Dict[str, int]:
        """
        Main method to collect workflow files.
        
        Args:
            languages: List of programming languages to target
            repos_per_language: Number of repositories per language
        """
        if languages is None:
            languages = ["python", "javascript", "java", "go", "rust", "typescript"]
        
        logger.info(f"Starting workflow collection for languages: {languages}")
        
        total_workflows = 0
        stats = {}
        
        for language in languages:
            logger.info(f"Processing {language} repositories...")
            language_count = 0
            
            repos = self.get_popular_repos(language, repos_per_language)
            
            for repo in repos:
                repo_owner = repo["owner"]["login"]
                repo_name = repo["name"]
                repo_key = f"{repo_owner}/{repo_name}"
                
                # Skip if already processed
                if repo_key in self.metadata["collected_repos"]:
                    logger.info(f"Skipping {repo_key} (already processed)")
                    continue
                
                workflow_files = self.get_workflow_files(repo_owner, repo_name)
                
                for file_info in workflow_files:
                    content = self.download_workflow_content(file_info)
                    
                    if content and self.validate_workflow(content):
                        file_path = self.save_workflow(
                            repo_owner, repo_name, file_info["name"], content
                        )
                        logger.info(f"Saved workflow: {file_path}")
                        language_count += 1
                        total_workflows += 1
                    
                    # Rate limiting - be nice to GitHub API
                    time.sleep(0.1)
                
                # Mark repo as processed
                self.metadata["collected_repos"].append(repo_key)
                
                # Rate limiting between repos
                time.sleep(1)
            
            stats[language] = language_count
            logger.info(f"Collected {language_count} workflows for {language}")
        
        # Update metadata
        self.metadata["workflow_count"] = total_workflows
        self.metadata["last_updated"] = time.time()
        self.save_metadata()
        
        logger.info(f"Collection complete! Total workflows collected: {total_workflows}")
        logger.info(f"Stats by language: {stats}")
        
        return stats

def main():
    """
    Main function to run the workflow collector.
    
    Automatically loads GITHUB_TOKEN from .env file.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    
    if github_token:
        logger.info("✅ Using GitHub token from .env file (higher rate limits)")
    else:
        logger.warning("No GITHUB_TOKEN found in .env file. Using anonymous access (lower rate limits)")
    
    collector = GitHubWorkflowCollector(github_token)
    
    # Start with a small collection for testing
    stats = collector.collect_workflows(
        languages=["python", "javascript"],  # Start with 2 languages
        repos_per_language=10  # 10 repos per language = ~20-50 workflows
    )
    
    print("\n" + "="*50)
    print("COLLECTION SUMMARY")
    print("="*50)
    for language, count in stats.items():
        print(f"{language}: {count} workflows")
    print(f"Total: {sum(stats.values())} workflows")
    print("="*50)

if __name__ == "__main__":
    main()