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

# Global instance
data_collector = DataCollector()
