"""
Embedding Service - Handles text embedding generation using Ollama
"""

import httpx
import logging
from typing import List, Optional
import os

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using Ollama
    """
    
    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.model = "nomic-embed-text"
        self.embedding_dim = 768
        self.client = None
        
    async def initialize(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"✅ Embedding service initialized with model: {self.model}")
        logger.info(f"   Ollama host: {self.ollama_host}")
        
    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = await self.client.post(
                f"{self.ollama_host}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            
            result = response.json()
            embedding = result.get("embedding", [])
            
            if len(embedding) != self.embedding_dim:
                logger.warning(
                    f"Unexpected embedding dimension: {len(embedding)}, expected {self.embedding_dim}"
                )
            
            return embedding
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error generating embedding: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
            
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
            
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
        
    async def health_check(self) -> bool:
        """
        Check if Ollama service is healthy
        
        Returns:
            True if service is accessible, False otherwise
        """
        try:
            response = await self.client.get(f"{self.ollama_host}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
