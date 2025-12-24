"""
Indexing Routes - Manages document indexing into vector store
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from core.embeddings import EmbeddingService
from core.vector_store import VectorStore
from core.chunking import WorkflowChunker, AnalysisChunker
from core.service_clients import GithubServiceClient, WorkspaceIntelligenceClient
from uuid import uuid4

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (will be initialized in main.py lifespan)
embedding_service: Optional[EmbeddingService] = None
vector_store: Optional[VectorStore] = None


class IndexWorkflowsRequest(BaseModel):
    """Request to index workflows for an organization"""
    org_name: str
    force_reindex: Optional[bool] = False


class IndexAnalysisRequest(BaseModel):
    """Request to index analysis results"""
    analysis_id: str
    org_name: str


class IndexStatusResponse(BaseModel):
    """Status of indexing operations"""
    total_documents: int
    indexed_workflows: int
    indexed_analyses: int
    last_updated: Optional[str] = None


@router.post("/index/workflows")
async def index_workflows(request: IndexWorkflowsRequest):
    """
    Index all workflow files for an organization
    
    Args:
        request: Organization name and indexing options
        
    Returns:
        Indexing status and count
    """
    try:
        logger.info(f"Indexing workflows for org: {request.org_name}")
        
        # Initialize clients
        github_client = GithubServiceClient()
        workflow_chunker = WorkflowChunker()
        
        # Fetch workflows from github-service
        workflows = await github_client.fetch_workflows(request.org_name)
        
        if not workflows:
            logger.warning(f"No workflows found for org: {request.org_name}")
            return {
                "message": "No workflows found",
                "org_name": request.org_name,
                "indexed_count": 0
            }
        
        indexed_count = 0
        total_chunks = 0
        
        # Process each workflow
        for workflow in workflows:
            try:
                repo_name = workflow.get("repo_name", "")
                workflow_path = workflow.get("path", "")
                workflow_content = workflow.get("content", "")
                
                # If content not provided, fetch it
                if not workflow_content:
                    workflow_content = await github_client.fetch_workflow_content(
                        request.org_name, repo_name, workflow_path
                    )
                
                if not workflow_content:
                    logger.warning(f"No content for workflow: {workflow_path}")
                    continue
                
                # Chunk the workflow
                chunks = workflow_chunker.chunk_workflow(
                    workflow_content, 
                    workflow_path,
                    request.org_name
                )
                
                # Generate embeddings and store in Qdrant
                for chunk in chunks:
                    # Generate embedding
                    embedding = await embedding_service.generate_embedding(chunk["content"])
                    
                    # Store in Qdrant
                    point_id = str(uuid4())
                    await vector_store.insert(
                        collection_name=vector_store.workflow_collection,
                        point_id=point_id,
                        vector=embedding,
                        payload={
                            **chunk["metadata"],
                            "content": chunk["content"],
                            "repo_name": repo_name
                        }
                    )
                    total_chunks += 1
                
                indexed_count += 1
                logger.info(f"Indexed workflow: {workflow_path} ({len(chunks)} chunks)")
                
            except Exception as e:
                logger.error(f"Error indexing workflow {workflow.get('path')}: {str(e)}")
                continue
        
        logger.info(f"Workflow indexing complete: {indexed_count} workflows, {total_chunks} chunks")
        
        return {
            "message": "Workflow indexing complete",
            "org_name": request.org_name,
            "indexed_count": indexed_count,
            "total_chunks": total_chunks,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error indexing workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/analysis")
async def index_analysis(request: IndexAnalysisRequest):
    """
    Index analysis results
    
    Args:
        request: Analysis ID and organization name
        
    Returns:
        Indexing status
    """
    try:
        logger.info(f"Indexing analysis: {request.analysis_id}")
        
        # Initialize clients
        intelligence_client = WorkspaceIntelligenceClient()
        analysis_chunker = AnalysisChunker()
        
        # Fetch analysis from workspace-intelligence-service
        analysis_data = await intelligence_client.fetch_analysis(request.analysis_id)
        
        if not analysis_data:
            logger.warning(f"Analysis not found: {request.analysis_id}")
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Chunk the analysis
        chunks = analysis_chunker.chunk_analysis(analysis_data, request.org_name)
        
        if not chunks:
            logger.warning(f"No chunks created for analysis: {request.analysis_id}")
            return {
                "message": "No indexable content in analysis",
                "analysis_id": request.analysis_id,
                "indexed_chunks": 0
            }
        
        indexed_chunks = 0
        
        # Generate embeddings and store in Qdrant
        for chunk in chunks:
            try:
                # Generate embedding
                embedding = await embedding_service.generate_embedding(chunk["content"])
                
                # Store in Qdrant
                point_id = str(uuid4())
                await vector_store.insert(
                    collection_name=vector_store.analysis_collection,
                    point_id=point_id,
                    vector=embedding,
                    payload={
                        **chunk["metadata"],
                        "content": chunk["content"]
                    }
                )
                indexed_chunks += 1
                
            except Exception as e:
                logger.error(f"Error indexing chunk: {str(e)}")
                continue
        
        logger.info(f"Analysis indexing complete: {indexed_chunks} chunks indexed")
        
        return {
            "message": "Analysis indexing complete",
            "analysis_id": request.analysis_id,
            "indexed_chunks": indexed_chunks,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex/{org_name}")
async def reindex_organization(org_name: str):
    """
    Full reindex of all data for an organization
    
    Args:
        org_name: Organization name
        
    Returns:
        Reindex status
    """
    try:
        logger.info(f"Starting full reindex for org: {org_name}")
        
        # Delete existing data for this org
        await vector_store.delete_by_filter(
            collection_name=vector_store.workflow_collection,
            filter_dict={"org_name": org_name}
        )
        await vector_store.delete_by_filter(
            collection_name=vector_store.analysis_collection,
            filter_dict={"org_name": org_name}
        )
        
        # Reindex workflows
        workflow_result = await index_workflows(
            IndexWorkflowsRequest(org_name=org_name, force_reindex=True)
        )
        
        # Fetch and reindex recent analyses
        intelligence_client = WorkspaceIntelligenceClient()
        analyses = await intelligence_client.fetch_org_analyses(org_name, limit=50)
        
        analysis_count = 0
        for analysis in analyses:
            analysis_id = analysis.get("id", "")
            if analysis_id:
                try:
                    await index_analysis(
                        IndexAnalysisRequest(analysis_id=analysis_id, org_name=org_name)
                    )
                    analysis_count += 1
                except Exception as e:
                    logger.error(f"Error reindexing analysis {analysis_id}: {str(e)}")
                    continue
        
        logger.info(f"Reindex complete for {org_name}")
        
        return {
            "message": "Reindex complete",
            "org_name": org_name,
            "workflows_indexed": workflow_result.get("indexed_count", 0),
            "analyses_indexed": analysis_count,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error reindexing org {org_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/status/{org_name}")
async def get_index_status(org_name: str):
    """
    Get indexing status for an organization
    
    Args:
        org_name: Organization name
        
    Returns:
        Index statistics
    """
    try:
        # Count indexed documents
        workflow_count = await vector_store.count(
            collection_name=vector_store.workflow_collection,
            filter_dict={"org_name": org_name}
        )
        
        analysis_count = await vector_store.count(
            collection_name=vector_store.analysis_collection,
            filter_dict={"org_name": org_name}
        )
        
        return IndexStatusResponse(
            total_documents=workflow_count + analysis_count,
            indexed_workflows=workflow_count,
            indexed_analyses=analysis_count,
            last_updated=None  # TODO: Track last update timestamp
        )
        
    except Exception as e:
        logger.error(f"Error getting index status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    """
    Full reindex of all data for an organization
    
    Args:
        org_name: Organization name
        
    Returns:
        Reindexing status
    """
    try:
        logger.info(f"Full reindex for org: {org_name}")
        
        # TODO: Implement full reindex
        # 1. Clear existing vectors for org
        # 2. Reindex all workflows
        # 3. Reindex all analyses
        
        return {
            "message": "Full reindex started",
            "org_name": org_name,
            "status": "in_progress"
        }
        
    except Exception as e:
        logger.error(f"Error during reindex: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/status/{org_name}", response_model=IndexStatusResponse)
async def get_index_status(org_name: str):
    """
    Get indexing status for an organization
    
    Args:
        org_name: Organization name
        
    Returns:
        Current index statistics
    """
    try:
        # TODO: Query Qdrant for collection stats
        return IndexStatusResponse(
            total_documents=0,
            indexed_workflows=0,
            indexed_analyses=0,
            last_updated=None
        )
        
    except Exception as e:
        logger.error(f"Error getting index status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
