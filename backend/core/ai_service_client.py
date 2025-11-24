"""
AI Service Client
Handles HTTP communication with the AI microservice
"""
import httpx
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AIServiceClient:
    """Client for communicating with the AI microservice"""
    
    def __init__(self):
        """Initialize AI Service client"""
        # Use internal Docker network URL when running in containers
        # Falls back to localhost for development
        self.base_url = os.getenv("AI_SERVICE_URL", "http://ai-service:8001")
        self.timeout = 120.0  # AI operations can take time
        
        logger.info(f"AI Service Client initialized with base URL: {self.base_url}")
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to AI service with error handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request
            
        Returns:
            Response JSON as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"AI Service request timeout: {endpoint}")
            raise Exception(f"AI Service timeout: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"AI Service HTTP error: {e.response.status_code} - {endpoint}")
            raise Exception(f"AI Service error: {e.response.text}")
        except Exception as e:
            logger.error(f"AI Service request failed: {endpoint} - {str(e)}")
            raise Exception(f"AI Service communication failed: {str(e)}")
    
    # ==================== Ollama Endpoints ====================
    
    async def generate_pr_description(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate PR description using Ollama
        
        Args:
            data: PR data including diff, context, etc.
            
        Returns:
            Generated PR description
        """
        return await self._make_request(
            "POST",
            "/api/ai/generate-pr-description",
            json=data
        )
    
    async def generate_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate GitHub Actions workflow using Ollama
        
        Args:
            data: Workflow requirements data
            
        Returns:
            Generated workflow YAML
        """
        return await self._make_request(
            "POST",
            "/api/ai/generate-workflow",
            json=data
        )
    
    async def check_ollama_health(self) -> Dict[str, Any]:
        """Check Ollama service health"""
        return await self._make_request("GET", "/health")
    
    # ==================== Claude AI Endpoints ====================
    
    async def analyze_threats_with_claude(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze threats using Claude AI
        
        Args:
            data: Threat model data with components, connections, etc.
            
        Returns:
            Claude's threat analysis
        """
        return await self._make_request(
            "POST",
            "/api/ai/claude/analyze-threats",
            json=data
        )
    
    async def check_claude_health(self) -> Dict[str, Any]:
        """Check Claude AI service health"""
        return await self._make_request("GET", "/api/ai/claude/health")
    
    # ==================== Groq AI Endpoints ====================
    
    async def analyze_with_groq(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze using Groq AI (when implemented)
        
        Args:
            data: Analysis request data
            
        Returns:
            Groq analysis results
        """
        # TODO: Implement when Groq endpoints are added to AI service
        raise NotImplementedError("Groq AI integration pending")
    
    # ==================== Health & Status ====================
    
    async def get_service_health(self) -> Dict[str, Any]:
        """
        Get overall AI service health status
        
        Returns:
            Health status for all AI providers
        """
        try:
            health_status = {
                "ai_service": "unknown",
                "ollama": "unknown",
                "claude": "unknown",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Check Ollama
            try:
                ollama_health = await self.check_ollama_health()
                health_status["ollama"] = ollama_health.get("status", "unknown")
            except Exception as e:
                logger.error(f"Ollama health check failed: {e}")
                health_status["ollama"] = "unhealthy"
            
            # Check Claude
            try:
                claude_health = await self.check_claude_health()
                health_status["claude"] = claude_health.get("status", "unknown")
            except Exception as e:
                logger.error(f"Claude health check failed: {e}")
                health_status["claude"] = "unhealthy"
            
            # Overall service status
            if health_status["ollama"] == "healthy" or health_status["claude"] == "healthy":
                health_status["ai_service"] = "healthy"
            else:
                health_status["ai_service"] = "unhealthy"
            
            return health_status
            
        except Exception as e:
            logger.error(f"AI Service health check failed: {e}")
            return {
                "ai_service": "unreachable",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global singleton instance
ai_service_client = AIServiceClient()
