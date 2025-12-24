"""
Service Clients - Fetch data from other microservices
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)


class GithubServiceClient:
    """
    Client for fetching workflow data from github-service
    """
    
    def __init__(self):
        self.base_url = os.getenv("GITHUB_SERVICE_URL", "http://github-service:8002")
        self.timeout = 30.0
    
    async def fetch_workflows(self, org_name: str, repo_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch workflow files for an organization
        
        Args:
            org_name: GitHub organization name
            repo_name: Optional specific repository name
            
        Returns:
            List of workflow file data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Endpoint to get workflows (adjust based on actual github-service API)
                endpoint = f"{self.base_url}/api/workflows/{org_name}"
                if repo_name:
                    endpoint += f"?repo={repo_name}"
                
                logger.info(f"Fetching workflows from: {endpoint}")
                response = await client.get(endpoint)
                response.raise_for_status()
                
                data = response.json()
                workflows = data.get("workflows", [])
                logger.info(f"Fetched {len(workflows)} workflows for {org_name}")
                
                return workflows
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching workflows: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching workflows: {str(e)}")
            return []
    
    async def fetch_workflow_content(self, org_name: str, repo_name: str, workflow_path: str) -> Optional[str]:
        """
        Fetch raw content of a specific workflow file
        
        Args:
            org_name: Organization name
            repo_name: Repository name
            workflow_path: Path to workflow file
            
        Returns:
            Workflow file content as string
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                endpoint = f"{self.base_url}/api/workflows/{org_name}/{repo_name}/content"
                params = {"path": workflow_path}
                
                logger.info(f"Fetching workflow content: {workflow_path}")
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                
                data = response.json()
                content = data.get("content", "")
                
                return content
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching workflow content: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching workflow content: {str(e)}")
            return None


class WorkspaceIntelligenceClient:
    """
    Client for fetching analysis data from workspace-intelligence-service
    """
    
    def __init__(self):
        self.base_url = os.getenv("WORKSPACE_INTELLIGENCE_URL", "http://workspace-intelligence-service:8006")
        self.timeout = 30.0
    
    async def fetch_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch specific analysis results by ID
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Analysis data dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                endpoint = f"{self.base_url}/api/analysis/{analysis_id}"
                
                logger.info(f"Fetching analysis: {analysis_id}")
                response = await client.get(endpoint)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Fetched analysis for ID: {analysis_id}")
                
                return data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching analysis: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching analysis: {str(e)}")
            return None
    
    async def fetch_org_analyses(self, org_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch recent analyses for an organization
        
        Args:
            org_name: Organization name
            limit: Maximum number of analyses to fetch
            
        Returns:
            List of analysis data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                endpoint = f"{self.base_url}/api/analyses/{org_name}"
                params = {"limit": limit}
                
                logger.info(f"Fetching analyses for org: {org_name}")
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                
                data = response.json()
                analyses = data.get("analyses", [])
                logger.info(f"Fetched {len(analyses)} analyses for {org_name}")
                
                return analyses
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching org analyses: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching org analyses: {str(e)}")
            return []
    
    async def fetch_folder_analysis(self, org_name: str, repo_name: str, folder_path: str) -> Optional[Dict[str, Any]]:
        """
        Fetch folder-level analysis results
        
        Args:
            org_name: Organization name
            repo_name: Repository name
            folder_path: Path to folder
            
        Returns:
            Folder analysis data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                endpoint = f"{self.base_url}/api/folder-analysis/{org_name}/{repo_name}"
                params = {"path": folder_path}
                
                logger.info(f"Fetching folder analysis: {folder_path}")
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                
                data = response.json()
                return data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching folder analysis: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching folder analysis: {str(e)}")
            return None
