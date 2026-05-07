"""
RAG Engine - Orchestrates Retrieval Augmented Generation
"""

import anthropic
from typing import List, Dict, Optional, Any
import logging
import os

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Main RAG engine that orchestrates:
    1. Query embedding
    2. Vector search across collections
    3. Context assembly
    4. Claude API generation
    5. Citation tracking
    """
    
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        
        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY not set. Chat functionality will be limited.")
            self.anthropic_client = None
        else:
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            logger.info("✅ Anthropic client initialized")
        
        # Configuration
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "4096"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.top_k_results = int(os.getenv("TOP_K_RESULTS", "5"))
        
    async def query(
        self,
        question: str,
        org_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a RAG query end-to-end
        
        Args:
            question: User's question
            org_name: Optional organization filter
            filters: Optional metadata filters
            conversation_history: Previous messages for context
            
        Returns:
            Dict with answer, sources, and metadata
        """
        try:
            logger.info(f"📝 Processing query: {question[:100]}...")
            
            # Step 1: Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(question)
            logger.info(f"✅ Generated query embedding ({len(query_embedding)} dimensions)")
            
            # Step 2: Search across collections
            contexts = await self._retrieve_contexts(
                query_embedding,
                org_name,
                filters
            )
            
            if not contexts:
                return {
                    "answer": "I don't have enough information to answer that question. Please make sure workflows and analysis results are indexed first.",
                    "sources": [],
                    "confidence": "low",
                    "contexts_used": 0
                }
            
            logger.info(f"✅ Retrieved {len(contexts)} relevant contexts")
            
            # Step 3: Generate answer with Claude
            if not self.anthropic_client:
                return {
                    "answer": "Chat functionality is not available (ANTHROPIC_API_KEY not configured).",
                    "sources": self._extract_sources(contexts),
                    "confidence": "n/a",
                    "contexts_used": len(contexts)
                }
            
            answer_data = await self._generate_answer(
                question,
                contexts,
                conversation_history
            )
            
            logger.info("✅ Answer generated successfully")
            
            return {
                **answer_data,
                "sources": self._extract_sources(contexts),
                "contexts_used": len(contexts)
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing query: {str(e)}")
            raise
    
    async def _retrieve_contexts(
        self,
        query_embedding: List[float],
        org_name: Optional[str],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant contexts from both workflow and analysis collections
        Applies user-level and project-level filters for data isolation
        """
        contexts = []
        
        # Search workflow files
        try:
            # Workflows use "org_name" field - ensure user filters are applied
            workflow_filters = {}
            
            if filters:
                # Copy user_id, org_name, project_name, analysis_id if present
                if "user_id" in filters:
                    workflow_filters["user_id"] = filters["user_id"]
                if "analysis_id" in filters:
                    workflow_filters["analysis_id"] = filters["analysis_id"]  # Filter by specific analysis
                if "project_name" in filters:
                    workflow_filters["project_name"] = filters["project_name"]
                if "folder_path" in filters:
                    workflow_filters["folder_path"] = filters["folder_path"]
                    
            # Always add org_name filter for basic isolation
            if org_name:
                workflow_filters["org_name"] = org_name
            elif filters and "org_name" in filters:
                workflow_filters["org_name"] = filters["org_name"]
            
            workflow_results = await self.vector_store.search(
                query_vector=query_embedding,
                collection=self.vector_store.workflow_collection,
                limit=self.top_k_results,
                filters=workflow_filters if workflow_filters else None
            )
            
            for result in workflow_results:
                contexts.append({
                    "type": "workflow",
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "score": result.get("score", 0.0)
                })
                
            logger.info(f"Found {len(workflow_results)} workflow contexts with filters: {workflow_filters}")
            
        except Exception as e:
            logger.error(f"Error searching workflows: {str(e)}")
        
        # Search analysis results
        try:
            # Analysis uses "organization" field - ensure user filters are applied
            analysis_filters = {}
            
            if filters:
                # Copy user_id, org_name, project_name, analysis_id if present
                if "user_id" in filters:
                    analysis_filters["user_id"] = filters["user_id"]
                if "analysis_id" in filters:
                    analysis_filters["analysis_id"] = filters["analysis_id"]  # Filter by specific analysis
                if "project_name" in filters:
                    analysis_filters["project_name"] = filters["project_name"]
                if "folder_path" in filters:
                    analysis_filters["folder_path"] = filters["folder_path"]
                if "analysis_id" in filters:
                    analysis_filters["analysis_id"] = filters["analysis_id"]
                    
            # Always add organization filter for basic isolation
            if org_name:
                analysis_filters["organization"] = org_name
            elif filters and "org_name" in filters:
                analysis_filters["organization"] = filters["org_name"]
            
            analysis_results = await self.vector_store.search(
                query_vector=query_embedding,
                collection=self.vector_store.analysis_collection,
                limit=self.top_k_results,
                filters=analysis_filters if analysis_filters else None
            )
            
            for result in analysis_results:
                contexts.append({
                    "type": "analysis",
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "score": result.get("score", 0.0)
                })
                
            logger.info(f"Found {len(analysis_results)} analysis contexts with filters: {analysis_filters}")
            
        except Exception as e:
            logger.error(f"Error searching analysis: {str(e)}")
        
        # Sort by relevance score (descending)
        contexts.sort(key=lambda x: x["score"], reverse=True)
        
        # Take top K overall
        return contexts[:self.top_k_results]
    
    async def _generate_answer(
        self,
        question: str,
        contexts: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate answer using Claude with retrieved contexts
        """
        # Extract project context from retrieved documents
        project_context = self._extract_project_context(contexts)
        
        # Build context string
        context_str = self._format_contexts(contexts)
        
        # Build system prompt with project context
        system_prompt = self._build_system_prompt(context_str, project_context)
        
        # Build messages with conversation history
        messages = []
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({
            "role": "user",
            "content": question
        })
        
        # Call Claude API
        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages
            )
            
            answer = response.content[0].text
            
            # Determine confidence based on context relevance
            avg_score = sum(c["score"] for c in contexts) / len(contexts) if contexts else 0
            confidence = "high" if avg_score > 0.8 else "medium" if avg_score > 0.6 else "low"
            
            return {
                "answer": answer,
                "confidence": confidence,
                "model": self.model,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens
            }
            
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise
    
    def _format_contexts(self, contexts: List[Dict[str, Any]]) -> str:
        """
        Format retrieved contexts into a readable string
        """
        formatted = []
        
        for i, ctx in enumerate(contexts, 1):
            ctx_type = ctx["type"]
            content = ctx["content"]
            metadata = ctx["metadata"]
            score = ctx["score"]
            
            if ctx_type == "workflow":
                project = metadata.get('project_name', 'unknown')
                folder = metadata.get('folder_path', 'unknown')
                repo = metadata.get('repo_name', 'unknown')
                file_path = metadata.get('file_path', 'unknown')
                # Include project/folder context in source attribution
                if project != 'unknown' and project != repo:
                    source = f"Project: {project} | {repo}/{file_path}"
                else:
                    source = f"{repo}/{file_path}"
                formatted.append(f"[Workflow {i}] (relevance: {score:.2f})\nSource: {source}\n{content}\n")
            
            elif ctx_type == "analysis":
                org = metadata.get('organization', 'unknown')
                project = metadata.get('project_name', 'unknown')
                chunk_type = metadata.get('chunk_type', 'analysis')
                source = f"{org}/{project} - {chunk_type}"
                formatted.append(f"[Analysis {i}] (relevance: {score:.2f})\nSource: {source}\n{content}\n")
        
        return "\n---\n".join(formatted)
    
    def _extract_project_context(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract project/folder context from retrieved documents
        """
        project_info = {
            "project_name": None,
            "folder_path": None,
            "org_name": None
        }
        
        # Get from first context (all should have same project for filtered queries)
        if contexts:
            metadata = contexts[0].get("metadata", {})
            project_info["project_name"] = metadata.get("project_name")
            project_info["folder_path"] = metadata.get("folder_path")
            project_info["org_name"] = metadata.get("org_name") or metadata.get("organization")
        
        return project_info
    
    def _build_system_prompt(self, context_str: str, project_context: Dict[str, Any] = None) -> str:
        """
        Build system prompt for Claude with retrieved contexts
        """
        # Build project context header if available
        project_header = ""
        if project_context:
            project_name = project_context.get("project_name")
            folder_path = project_context.get("folder_path")
            org_name = project_context.get("org_name")
            
            if project_name or folder_path:
                project_header = "\n**Current Analysis Context:**\n"
                if project_name and project_name != "unknown":
                    project_header += f"- Project/Folder: {project_name}\n"
                if org_name and org_name != "unknown":
                    project_header += f"- Organization: {org_name}\n"
                project_header += "\n"
        
        return f"""You are an expert DevSecOps AI assistant specializing in security analysis, CI/CD workflows, and software security practices.

Your role is to help users understand their DevSecOps posture by analyzing workflow files, security assessments, and maturity scores.
{project_header}
You have access to the following relevant information from the user's repositories and analysis results:

{context_str}

Guidelines:
1. Answer questions based ONLY on the provided context above
2. If the context doesn't contain enough information, say so clearly
3. When referencing information, mention the source (workflow file or analysis result)
4. Provide actionable insights and recommendations when appropriate
5. Be concise but thorough
6. Use technical terms accurately
7. If asked about security issues, prioritize clarity and actionable advice

If the user asks about something not in the context, politely explain that you need more information or that the relevant data hasn't been indexed yet."""
    
    def _extract_sources(self, contexts: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract source citations from contexts
        """
        sources = []
        
        for ctx in contexts:
            metadata = ctx["metadata"]
            
            if ctx["type"] == "workflow":
                sources.append({
                    "type": "workflow",
                    "repo": metadata.get("repo_name") or "unknown",
                    "file": metadata.get("file_path") or "unknown",
                    "relevance": f"{ctx['score']:.2f}"
                })
            
            elif ctx["type"] == "analysis":
                sources.append({
                    "type": "analysis",
                    "organization": metadata.get("organization") or "unknown",
                    "project": metadata.get("project_name") or "unknown",
                    "chunk_type": metadata.get("chunk_type") or "unknown",
                    "relevance": f"{ctx['score']:.2f}"
                })
        
        return sources
