"""
GitHub Service Client for Backend
HTTP client to communicate with the GitHub microservice
"""
import httpx
import os
import logging
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class GitHubServiceClient:
    """
    Client for communicating with the GitHub Service microservice
    Handles all GitHub-related operations via HTTP
    """
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("GITHUB_SERVICE_URL", "http://github-service:8002")
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
        logger.info(f"GitHub Service Client initialized: {self.base_url}")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to GitHub Service with retry logic
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling GitHub Service: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error calling GitHub Service: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling GitHub Service: {e}")
            raise
    
    # ============================================================================
    # ORGANIZATION DISCOVERY & INSTALLATION
    # ============================================================================
    
    async def start_organization_discovery(self) -> Dict[str, Any]:
        """Start GitHub organization discovery OAuth flow"""
        return await self._make_request("GET", "/api/github/organizations/discover")
    
    async def handle_organization_callback(self, code: str, state: str = None) -> Dict[str, Any]:
        """Handle OAuth callback for organization discovery"""
        params = {"code": code}
        if state:
            params["state"] = state
        return await self._make_request("GET", "/api/github/organizations/callback", params=params)
    
    async def start_app_installation(self, org_name: str, state: str = None) -> Dict[str, Any]:
        """Generate GitHub App installation URL for organization"""
        params = {}
        if state:
            params["state"] = state
        return await self._make_request("POST", f"/api/github/organizations/{org_name}/install", params=params)
    
    async def handle_installation_callback(
        self,
        installation_id: int,
        setup_action: str,
        state: str = None
    ) -> Dict[str, Any]:
        """Handle GitHub App installation callback"""
        params = {
            "installation_id": installation_id,
            "setup_action": setup_action
        }
        if state:
            params["state"] = state
        return await self._make_request("POST", "/api/github/installation/callback", params=params)
    
    # ============================================================================
    # WORKSPACE OPERATIONS
    # ============================================================================
    
    async def get_organization_workspace(
        self,
        org_name: str,
        force_fresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get comprehensive workspace data for an organization
        """
        params = {"force_fresh": force_fresh}
        return await self._make_request("GET", f"/api/github/workspace/{org_name}", params=params)
    
    async def get_installations(self) -> Dict[str, Any]:
        """Get all GitHub App installations"""
        return await self._make_request("GET", "/api/github/installations")
    
    async def get_my_organizations(
        self,
        cleanup: bool = False,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Get organizations for the authenticated user
        Proxies to github-service with authentication
        """
        params = {"cleanup": cleanup}
        kwargs = {"params": params}
        if headers:
            kwargs["headers"] = headers
        return await self._make_request("GET", "/api/github/my-organizations", **kwargs)
    
    async def get_organization_stats(self, org_name: str) -> Dict[str, Any]:
        """Get organization statistics (repository and workflow counts)"""
        return await self._make_request("GET", f"/api/github/organizations/{org_name}/stats")
    
    # ============================================================================
    # WORKFLOW OPERATIONS
    # ============================================================================
    
    async def get_workflow_content(
        self,
        org_name: str,
        repo_name: str,
        workflow_path: str
    ) -> Dict[str, Any]:
        """Get content of a specific workflow file"""
        return await self._make_request(
            "GET",
            f"/api/github/workspace/{org_name}/workflow/{repo_name}/{workflow_path}"
        )
    
    async def get_organization_workflows_detailed(self, org_name: str) -> Dict[str, Any]:
        """Get detailed workflow information for an organization"""
        return await self._make_request(
            "GET",
            f"/api/github/workspace/{org_name}/workflows/detailed"
        )
    
    async def get_organization_actions(self, org_name: str) -> Dict[str, Any]:
        """Get all GitHub Actions from all workflows in an organization"""
        return await self._make_request(
            "GET",
            f"/api/github/workspace/{org_name}/actions/detailed"
        )
    
    async def get_organization_actions_paginated(
        self,
        org_name: str,
        page: int = 1,
        per_page: int = 20,
        search: str = ""
    ) -> Dict[str, Any]:
        """Get paginated GitHub Actions from all workflows in an organization"""
        params = {
            "page": page,
            "per_page": per_page,
            "search": search
        }
        return await self._make_request(
            "GET",
            f"/api/github/workspace/{org_name}/actions/paginated",
            params=params
        )
    
    # ============================================================================
    # CACHE MANAGEMENT
    # ============================================================================
    
    async def clear_organization_cache(self, org_name: str) -> Dict[str, Any]:
        """Clear cache for a specific organization"""
        return await self._make_request(
            "DELETE",
            f"/api/github/workspace/{org_name}/cache"
        )
    
    # ============================================================================
    # HEALTH CHECK
    # ============================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if GitHub Service is healthy"""
        return await self._make_request("GET", "/health")


# Global instance
github_service_client = GitHubServiceClient()
