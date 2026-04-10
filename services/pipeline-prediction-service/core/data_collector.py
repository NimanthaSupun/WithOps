"""
Data Collector for Pipeline Prediction Service
Fetches historical workflow run data from the GitHub Service.
"""
import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DataCollector:
    """Handles communication with github-service to collect historical data"""
    
    def __init__(self):
        self.github_service_url = os.getenv("GITHUB_SERVICE_URL", "http://github-service:8002")
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        
    async def fetch_workflow_runs(self, org_name: str, repo_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch historical workflow runs for a specific repository.
        
        Args:
            org_name: GitHub organization name
            repo_name: Repository name
            limit: Number of recent runs to fetch
            
        Returns:
            List of workflow run objects
        """
        logger.info(f"🔍 Fetching up to {limit} workflow runs for {org_name}/{repo_name}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Assuming github-service has an endpoint like /api/github/workspace/{org}/runs
                # Note: We may need to add this endpoint to github-service if it doesn't exist
                url = f"{self.github_service_url}/api/github/workspace/{org_name}/repositories/{repo_name}/runs"
                
                params = {"limit": limit}
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    runs = response.json().get("workflow_runs", [])
                    logger.info(f"✅ Successfully fetched {len(runs)} runs")
                    return runs
                else:
                    logger.error(f"❌ Failed to fetch runs from github-service: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Error during data collection: {e}")
            return []

    async def fetch_commit_details(self, org_name: str, repo_name: str, sha: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed commit information including file change counts.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.github_service_url}/api/github/workspace/{org_name}/repositories/{repo_name}/commits/{sha}"
                response = await client.get(url)
                
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"❌ Error fetching commit details: {e}")
            return None

    async def fetch_workflow_runs_by_commit(self, org_name: str, repo_name: str, commit_sha: str) -> List[Dict[str, Any]]:
        """
        Fetch workflow runs associated with a specific commit SHA.
        
        Used for outcome reconciliation to find actual pipeline conclusions.
        
        Args:
            org_name: GitHub organization name
            repo_name: Repository name
            commit_sha: Commit SHA (40 hex chars)
            
        Returns:
            List of workflow run objects (filtered by commit)
        """
        logger.info(f"🔍 Fetching workflow runs for commit {commit_sha[:8]}...")
        
        try:
            # First, try direct query to github-service if available
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.github_service_url}/api/github/workspace/{org_name}/repositories/{repo_name}/runs"
                params = {
                    "commit_sha": commit_sha,
                    "limit": 10
                }
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    runs = response.json().get("workflow_runs", [])
                    logger.info(f"✅ Found {len(runs)} runs for commit {commit_sha[:8]}")
                    return runs
                else:
                    # Fallback: query GitHub API directly
                    logger.debug(f"GitHub service returned {response.status_code}, trying direct API")
                    return await self._fetch_from_github_api(org_name, repo_name, commit_sha)
        
        except Exception as e:
            logger.warning(f"⚠️ Error fetching workflow runs for commit: {e}")
            return []

    async def _fetch_from_github_api(self, org_name: str, repo_name: str, commit_sha: str) -> List[Dict[str, Any]]:
        """
        Fallback: Query GitHub API directly for workflow runs by commit.
        Requires GitHub App credentials.
        """
        github_token = os.getenv("GITHUB_TOKEN", "")
        if not github_token:
            logger.warning("No GITHUB_TOKEN available for direct GitHub API access")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"https://api.github.com/repos/{org_name}/{repo_name}/commits/{commit_sha}/check-runs"
                headers = {
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    check_runs = response.json().get("check_runs", [])
                    logger.info(f"✅ Found {len(check_runs)} check runs via GitHub API")
                    return check_runs
                else:
                    logger.warning(f"GitHub API returned {response.status_code}")
                    return []
        
        except Exception as e:
            logger.error(f"❌ Error fetching from GitHub API: {e}")
            return []

# Global instance
data_collector = DataCollector()
