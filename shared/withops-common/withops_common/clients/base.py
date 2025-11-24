"""
Base HTTP client for service-to-service communication with retry logic
"""

import httpx
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)


class BaseServiceClient:
    """
    Base client for HTTP communication between microservices
    Includes retry logic, timeout handling, and error handling
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """GET request with retry logic"""
        url = f"{self.base_url}{path}"
        logger.debug(f"GET {url}")
        
        try:
            response = await self.client.get(
                url,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            return response
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """POST request with retry logic"""
        url = f"{self.base_url}{path}"
        logger.debug(f"POST {url}")
        
        try:
            response = await self.client.post(
                url,
                json=json,
                headers=headers
            )
            response.raise_for_status()
            return response
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {e}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
