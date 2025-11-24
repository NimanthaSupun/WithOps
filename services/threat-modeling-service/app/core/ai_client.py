"""
AI Service Client
HTTP client for communicating with the AI microservice
"""

import httpx
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AIServiceClient:
    """Client for AI Service communication"""
    
    def __init__(self):
        self.base_url = os.getenv("AI_SERVICE_URL", "http://ai-service:8001")
        self.timeout = 120.0
        logger.info(f"AI Service Client initialized: {self.base_url}")
    
    async def analyze_threats(self, analysis_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send threat analysis request to AI Service
        
        Args:
            analysis_request: Analysis parameters and context
            
        Returns:
            AI analysis results
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/analyze",
                    json=analysis_request
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error("AI Service timeout")
            raise Exception("AI Service timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"AI Service HTTP error: {e.response.status_code}")
            raise Exception(f"AI Service error: {e.response.text}")
        except Exception as e:
            logger.error(f"AI Service request failed: {e}")
            raise Exception(f"AI Service unavailable: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check AI Service health"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


# Global instance
ai_client = AIServiceClient()
