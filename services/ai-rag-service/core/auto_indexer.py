"""
Event Handlers for automatic indexing
Triggered when workspace/project analysis completes
"""

import logging
import httpx
from typing import Dict, Any
import os
import uuid

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore
from core.chunking import WorkflowChunker
from core.analysis_chunking_fixed import AnalysisChunker

logger = logging.getLogger(__name__)


class AutoIndexer:
    """
    Handles automatic indexing when analysis events occur
    """
    
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.workflow_chunker = WorkflowChunker()
        self.analysis_chunker = AnalysisChunker()
        self.github_service_url = os.getenv("GITHUB_SERVICE_URL", "http://github-service:8002")
        self.workspace_service_url = os.getenv("WORKSPACE_SERVICE_URL", "http://workspace-intelligence-service:8006")
    
    async def handle_workspace_event(self, event_data: Dict[str, Any]):
        """
        Handle workspace intelligence events and route to appropriate handler
        Filters by event type
        """
        event_type = event_data.get("type")
        
        if event_type == "workspace_analysis.completed":
            await self.handle_workspace_analysis_completed(event_data)
        elif event_type == "project_analysis.completed":
            await self.handle_project_analysis_completed(event_data)
        else:
            logger.debug(f"Ignoring event type: {event_type}")
    
    def _extract_workflows_from_tree(self, tree_data: list) -> list:
        """Extract all workflows from repository tree structure"""
        workflows = []
        
        def traverse(nodes, parent_folder=None):
            for node in nodes:
                if node.get('type') == 'folder':
                    folder_name = node.get('name')
                    if node.get('children'):
                        traverse(node['children'], parent_folder=folder_name)
                elif node.get('type') == 'repository':
                    if node.get('children'):
                        for child in node['children']:
                            if child.get('type') == 'workflow':
                                repo_name = node.get('name')
                                full_repo_path = f"{parent_folder}/{repo_name}" if parent_folder else repo_name
                                logger.debug(f"📦 Found workflow {child.get('name')} in: {full_repo_path}")
                                workflow = {
                                    'content': child.get('content', ''),
                                    'path': child.get('metadata', {}).get('path', f".github/workflows/{child.get('name')}"),
                                    'name': child.get('name'),
                                    'repository_name': repo_name,
                                    'folder_name': parent_folder,
                                    'full_repo_path': full_repo_path
                                }
                                workflows.append(workflow)
        
        traverse(tree_data)
        return workflows
    
    async def handle_workspace_analysis_completed(self, event_data: Dict[str, Any]):
        """
        Handle workspace analysis completion event
        Auto-index workflows and analysis results with user isolation
        """
        try:
            data = event_data.get("data", {})
            org_name = data.get("organization_name")
            analysis_id = data.get("analysis_id")
            tree_id = data.get("tree_id")
            user_id = data.get("user_id")  # Extract user_id from event
            project_name = data.get("project_name")  # Optional project name
            folder_path = data.get("folder_path")  # Optional folder path
            analysis_scope = data.get("analysis_scope", "unified")  # unified or folder
            
            if not user_id:
                logger.warning(f"⚠️ No user_id in event for analysis {analysis_id}, skipping indexing")
                return
            
            logger.info(f"🎯 Auto-indexing triggered for user: {user_id}, org: {org_name}, analysis: {analysis_id}")
            
            # Step 1: Cleanup old data for this specific analysis (not all analyses)
            await self._cleanup_old_analysis_data(
                user_id=user_id,
                org_name=org_name,
                analysis_id=analysis_id,
                project_name=project_name,
                folder_path=folder_path
            )
            
            # Step 2: Fetch and index workflows with user context
            await self._index_workflows_for_org(
                org_name=org_name,
                user_id=user_id,
                analysis_id=analysis_id,
                project_name=project_name,
                folder_path=folder_path
            )
            
            # Step 3: Fetch and index analysis results with user context
            await self._index_analysis_results(
                org_name=org_name,
                tree_id=tree_id,
                analysis_id=analysis_id,
                user_id=user_id,
                project_name=project_name,
                folder_path=folder_path,
                analysis_scope=analysis_scope
            )
            
            logger.info(f"✅ Auto-indexing completed for {org_name} (user: {user_id})")
            
        except Exception as e:
            logger.error(f"❌ Error in auto-indexing: {str(e)}")
    
    async def handle_project_analysis_completed(self, event_data: Dict[str, Any]):
        """
        Handle individual project analysis completion with user isolation
        Index specific repository workflows
        """
        try:
            data = event_data.get("data", {})
            org_name = data.get("organization_name")
            project_name = data.get("project_name")
            user_id = data.get("user_id")
            
            if not user_id:
                logger.warning(f"⚠️ No user_id in event for project {project_name}, skipping indexing")
                return
            
            logger.info(f"🎯 Auto-indexing project: {project_name} in {org_name} for user: {user_id}")
            
            # Index workflows for this specific repository with user context
            await self._index_repo_workflows(
                org_name=org_name,
                repo_name=project_name,
                user_id=user_id,
                project_name=project_name
            )
            
        except Exception as e:
            logger.error(f"❌ Error indexing project: {str(e)}")
    
    async def _index_workflows_for_org(self, org_name: str, user_id: str, analysis_id: str = None, project_name: str = None, folder_path: str = None):
        """Fetch and index all workflows for an organization with user isolation"""
        try:
            logger.info(f"🔍 _index_workflows_for_org called with: project_name={project_name}, folder_path={folder_path}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch repository tree which contains workflow content
                url = f"{self.workspace_service_url}/api/repository-tree/{org_name}"
                logger.info(f"🔗 Fetching workflows from: {url}")
                response = await client.get(url)
                
                if response.status_code != 200:
                    logger.warning(f"No repository tree found for {org_name}")
                    return
                
                tree_response = response.json()
                tree_data = tree_response.get("data", [])
                
                # Extract workflows from tree
                workflows = self._extract_workflows_from_tree(tree_data)
                logger.info(f"📄 Found {len(workflows)} workflows to index")
                
                indexed_count = 0
                for workflow in workflows:
                    try:
                        # Chunk workflow
                        chunks = self.workflow_chunker.chunk_workflow(
                            workflow_content=workflow.get("content", ""),
                            workflow_path=workflow.get("path", ""),
                            org_name=org_name
                        )
                        
                        # Generate embeddings and store with user isolation
                        for chunk in chunks:
                            embedding = await self.embedding_service.generate_embedding(chunk["content"])
                            
                            # Add user context and repository metadata
                            chunk["metadata"]["user_id"] = user_id
                            chunk["metadata"]["org_name"] = org_name
                            chunk["metadata"]["analysis_id"] = analysis_id  # Link to analysis
                            # For folder analysis: use folder_path as project_name, otherwise use repository_name
                            chunk["metadata"]["project_name"] = project_name or folder_path or workflow.get("repository_name", "unknown")
                            chunk["metadata"]["repo_name"] = workflow.get("full_repo_path", workflow.get("repository_name", "unknown"))
                            chunk["metadata"]["file_path"] = workflow.get("path", "unknown")
                            # Use workflow's actual folder_name for accurate filtering
                            # For folder analyses: use the workflow's folder, not the analysis folder_path
                            # This ensures each workflow is tagged with its correct folder location
                            workflow_folder = workflow.get("folder_name")
                            logger.info(f"📁 Workflow {workflow.get('name')} folder: {workflow_folder} (analysis folder_path: {folder_path})")
                            if workflow_folder:
                                chunk["metadata"]["folder_path"] = workflow_folder
                            elif folder_path:
                                chunk["metadata"]["folder_path"] = folder_path  # Fallback to analysis folder_path
                            chunk["metadata"]["content"] = chunk["content"]  # Store content in payload
                            chunk["metadata"]["indexed_at"] = str(uuid.uuid4())  # Versioning via UUID timestamp
                            
                            # Debug: Log metadata being stored
                            logger.info(f"🔍 Storing workflow chunk with metadata: user_id={chunk['metadata'].get('user_id')}, org_name={chunk['metadata'].get('org_name')}, analysis_id={chunk['metadata'].get('analysis_id')}, project_name={chunk['metadata'].get('project_name')}, folder_path={chunk['metadata'].get('folder_path')}")
                            
                            await self.vector_store.insert(
                                collection_name=self.vector_store.workflow_collection,
                                point_id=str(uuid.uuid4()),
                                vector=embedding,
                                payload=chunk["metadata"]
                            )
                            indexed_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error indexing workflow {workflow.get('path')}: {str(e)}")
                        continue
                
                logger.info(f"✅ Indexed {indexed_count} workflow chunks for {org_name} (user: {user_id})")
                
        except Exception as e:
            logger.error(f"Error fetching workflows: {str(e)}")
            logger.error(f"WORKSPACE_SERVICE_URL: {self.workspace_service_url}")
            logger.error(f"GITHUB_SERVICE_URL: {self.github_service_url}")
    
    async def _index_repo_workflows(self, org_name: str, repo_name: str, user_id: str, project_name: str):
        """Index workflows for a specific repository with user isolation"""
        try:
            # Fetch repository tree and filter for this repo's workflows
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.workspace_service_url}/api/repository-tree/{org_name}"
                )
                
                if response.status_code != 200:
                    logger.warning(f"No repository tree found for {org_name}")
                    return
                
                tree_response = response.json()
                tree_data = tree_response.get("data", [])
                
                # Extract all workflows and filter by repo
                all_workflows = self._extract_workflows_from_tree(tree_data)
                repo_workflows = [w for w in all_workflows if w.get("repository_name") == repo_name]
                logger.info(f"📄 Found {len(repo_workflows)} workflows for {org_name}/{repo_name}")
                
                indexed_count = 0
                for workflow in repo_workflows:
                    chunks = self.workflow_chunker.chunk_workflow(
                        workflow_content=workflow.get("content", ""),
                        workflow_path=workflow.get("path", ""),
                        org_name=org_name
                    )
                    
                    for chunk in chunks:
                        embedding = await self.embedding_service.generate_embedding(chunk["content"])
                        
                        # Add user context and repository metadata
                        chunk["metadata"]["user_id"] = user_id
                        chunk["metadata"]["org_name"] = org_name
                        chunk["metadata"]["project_name"] = project_name
                        chunk["metadata"]["repo_name"] = workflow.get("full_repo_path", workflow.get("repository_name", repo_name))
                        chunk["metadata"]["file_path"] = workflow.get("path", "unknown")
                        chunk["metadata"]["content"] = chunk["content"]  # Store content in payload
                        chunk["metadata"]["indexed_at"] = str(uuid.uuid4())  # Versioning
                        
                        await self.vector_store.insert(
                            collection_name=self.vector_store.workflow_collection,
                            vector=embedding,
                            payload=chunk["metadata"],
                            point_id=str(uuid.uuid4())
                        )
                        indexed_count += 1
                
                logger.info(f"✅ Indexed {indexed_count} chunks for {org_name}/{repo_name} (user: {user_id})")
                
        except Exception as e:
            logger.error(f"Error indexing repo workflows: {str(e)}")
    
    async def _index_analysis_results(
        self, 
        org_name: str, 
        tree_id: str, 
        analysis_id: str, 
        user_id: str, 
        project_name: str = None, 
        folder_path: str = None,
        analysis_scope: str = "unified"
    ):
        """Fetch and index analysis results with user isolation"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch analysis results from workspace-intelligence-service
                response = await client.get(
                    f"{self.workspace_service_url}/api/workspace-intelligence/analysis/{analysis_id}"
                )
                
                if response.status_code != 200:
                    logger.warning(f"No analysis results found for analysis {analysis_id}")
                    return
                
                analysis_data = response.json()
                logger.info(f"📊 Indexing analysis results for tree {tree_id}")
                
                # Chunk analysis results
                chunks = self.analysis_chunker.chunk_analysis(
                    analysis_data=analysis_data,
                    org_name=org_name
                )
                
                indexed_count = 0
                for chunk in chunks:
                    embedding = await self.embedding_service.generate_embedding(chunk["content"])
                    
                    # Create payload with ALL chunk data + user context
                    payload = {
                        **chunk["metadata"],  # Spread metadata fields
                        "content": chunk["content"],  # Add content field
                        "user_id": user_id,  # User isolation
                        "organization": org_name,  # Organization (note: analysis uses "organization" not "org_name")
                        "project_name": project_name,  # Project name (if folder analysis)
                        "folder_path": folder_path,  # Folder path (if folder analysis)
                        "analysis_id": analysis_id,  # Analysis ID for tracking
                        "analysis_scope": analysis_scope,  # unified or folder
                        "indexed_at": str(uuid.uuid4())  # Versioning
                    }
                    
                    await self.vector_store.insert(
                        collection_name=self.vector_store.analysis_collection,
                        point_id=str(uuid.uuid4()),
                        vector=embedding,
                        payload=payload  # Use the complete payload, not just chunk["metadata"]
                    )
                    indexed_count += 1
                
                logger.info(f"✅ Indexed {indexed_count} analysis chunks for {org_name} (user: {user_id})")
                
        except Exception as e:
            logger.error(f"Error indexing analysis results: {str(e)}")
    
    async def _cleanup_old_analysis_data(
        self, 
        user_id: str, 
        org_name: str,
        analysis_id: str = None,
        project_name: str = None, 
        folder_path: str = None
    ):
        """
        Delete old vector data before re-indexing to prevent duplicate/stale data
        Filters by user_id + org_name + analysis_id + optional project/folder
        
        This ensures each analysis keeps its own vector data in the database.
        When viewing historical analyses, their vectors remain intact.
        """
        try:
            # Build filter for cleanup - MUST include analysis_id to preserve other analyses
            cleanup_filter = {
                "user_id": user_id,
                "org_name": org_name
            }
            
            # Include analysis_id to only clean THIS analysis, not all analyses
            if analysis_id:
                cleanup_filter["analysis_id"] = analysis_id
            
            if project_name:
                cleanup_filter["project_name"] = project_name
            if folder_path:
                cleanup_filter["folder_path"] = folder_path
            
            # Cleanup workflows
            try:
                await self.vector_store.delete_by_filter(
                    collection_name=self.vector_store.workflow_collection,
                    filter_dict=cleanup_filter
                )
                logger.info(f"🗑️ Cleaned up old workflow data for filter: {cleanup_filter}")
            except Exception as e:
                logger.warning(f"Could not cleanup workflows: {str(e)}")
            
            # Cleanup analysis results
            try:
                await self.vector_store.delete_by_filter(
                    collection_name=self.vector_store.analysis_collection,
                    filter_dict=cleanup_filter
                )
                logger.info(f"🗑️ Cleaned up old analysis data for filter: {cleanup_filter}")
            except Exception as e:
                logger.warning(f"Could not cleanup analysis: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")
