"""
Vector Store - Manages Qdrant vector database operations
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http import models
from typing import List, Dict, Optional, Any
import logging
import os
from uuid import uuid4

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Service for managing vector database operations with Qdrant
    """
    
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.client = None
        
        # Collection names
        self.workflow_collection = "workflow_files"
        self.analysis_collection = "analysis_results"
        
        # Embedding dimension (must match nomic-embed-text)
        self.embedding_dim = 768
        
    async def initialize(self):
        """Initialize Qdrant client and create collections"""
        try:
            self.client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port
            )
            
            logger.info(f"✅ Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
            
            # Create collections if they don't exist
            await self._create_collections()
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {str(e)}")
            raise
            
    async def close(self):
        """Close Qdrant client"""
        if self.client:
            self.client.close()
            logger.info("Qdrant client closed")
            
    async def _create_collections(self):
        """Create vector collections if they don't exist"""
        try:
            # Get list of existing collections
            existing_collections = self.client.get_collections().collections
            existing_names = [col.name for col in existing_collections]
            
            # Create workflow files collection
            if self.workflow_collection not in existing_names:
                self.client.create_collection(
                    collection_name=self.workflow_collection,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created collection: {self.workflow_collection}")
            else:
                logger.info(f"Collection already exists: {self.workflow_collection}")
                
            # Create analysis results collection
            if self.analysis_collection not in existing_names:
                self.client.create_collection(
                    collection_name=self.analysis_collection,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created collection: {self.analysis_collection}")
            else:
                logger.info(f"Collection already exists: {self.analysis_collection}")
                
        except Exception as e:
            logger.error(f"Error creating collections: {str(e)}")
            raise
            
    async def insert(
        self,
        collection_name: str,
        point_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> str:
        """
        Generic insert method for any collection
        
        Args:
            collection_name: Name of the collection
            point_id: Unique ID for the point
            vector: Embedding vector
            payload: Metadata and content
            
        Returns:
            ID of the inserted point
        """
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            
            logger.debug(f"Inserted point: {point_id} into {collection_name}")
            return point_id
            
        except Exception as e:
            logger.error(f"Error inserting point: {str(e)}")
            raise
            
    async def delete_by_filter(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any]
    ):
        """
        Delete points matching a filter
        
        Args:
            collection_name: Name of the collection
            filter_dict: Dictionary of field:value filters
        """
        try:
            filter_conditions = models.Filter(
                must=[
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                    for key, value in filter_dict.items()
                ]
            )
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(filter=filter_conditions)
            )
            
            logger.info(f"Deleted points from {collection_name} with filter: {filter_dict}")
            
        except Exception as e:
            logger.error(f"Error deleting points: {str(e)}")
            raise
    
    async def count(
        self,
        collection_name: str,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count points in a collection, optionally with filters
        
        Args:
            collection_name: Name of the collection
            filter_dict: Optional dictionary of field:value filters
            
        Returns:
            Count of matching points
        """
        try:
            if filter_dict:
                filter_conditions = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                        for key, value in filter_dict.items()
                    ]
                )
                
                result = self.client.count(
                    collection_name=collection_name,
                    count_filter=filter_conditions
                )
            else:
                result = self.client.count(collection_name=collection_name)
            
            return result.count
            
        except Exception as e:
            logger.error(f"Error counting points: {str(e)}")
            return 0
            
    async def insert_workflow(
        self,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Insert workflow file chunk into vector store
        
        Args:
            content: Text content of the workflow chunk
            embedding: Embedding vector
            metadata: Metadata (repo, file path, job name, etc.)
            
        Returns:
            ID of the inserted point
        """
        try:
            point_id = str(uuid4())
            
            payload = {
                "content": content,
                **metadata
            }
            
            self.client.upsert(
                collection_name=self.workflow_collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            logger.debug(f"Inserted workflow chunk: {point_id}")
            return point_id
            
        except Exception as e:
            logger.error(f"Error inserting workflow: {str(e)}")
            raise
            
    async def insert_analysis(
        self,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Insert analysis result into vector store
        
        Args:
            content: Text description of analysis
            embedding: Embedding vector
            metadata: Metadata (analysis ID, org, scores, etc.)
            
        Returns:
            ID of the inserted point
        """
        try:
            point_id = str(uuid4())
            
            payload = {
                "content": content,
                **metadata
            }
            
            self.client.upsert(
                collection_name=self.analysis_collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            logger.debug(f"Inserted analysis result: {point_id}")
            return point_id
            
        except Exception as e:
            logger.error(f"Error inserting analysis: {str(e)}")
            raise
            
    async def search(
        self,
        query_vector: List[float],
        collection: str,
        limit: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar vectors
        
        Args:
            query_vector: Query embedding vector
            collection: Collection name to search
            limit: Maximum number of results
            filters: Optional metadata filters
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            # Build filter conditions
            filter_conditions = None
            if filters:
                filter_conditions = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                        for key, value in filters.items()
                    ]
                )
            
            logger.info(f"🔍 Searching collection '{collection}' with limit={limit}, filters={filters}")
            
            # Perform search
            results = self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=filter_conditions,
                score_threshold=0.0  # Include all results regardless of score
            )
            
            logger.info(f"Search returned {len(results)} results from collection '{collection}'")
            if len(results) > 0:
                logger.info(f"Top result score: {results[0].score:.4f}")
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "content": result.payload.get("content", ""),
                    "metadata": {
                        k: v for k, v in result.payload.items()
                        if k != "content"
                    }
                })
            
            logger.info(f"Search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise
            
    async def delete_by_org(self, org_name: str, collection: str):
        """
        Delete all vectors for an organization
        
        Args:
            org_name: Organization name
            collection: Collection name
        """
        try:
            self.client.delete(
                collection_name=collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="org_name",
                                match=models.MatchValue(value=org_name)
                            )
                        ]
                    )
                )
            )
            logger.info(f"Deleted all vectors for org: {org_name} from {collection}")
            
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            raise
            
    async def get_collection_info(self, collection: str) -> Dict:
        """
        Get collection information and stats
        
        Args:
            collection: Collection name
            
        Returns:
            Collection information
        """
        try:
            info = self.client.get_collection(collection_name=collection)
            return {
                "name": collection,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            raise
