"""
Document Chunking Utilities - Process and chunk documents for embedding
"""

from typing import List, Dict, Any
import yaml
import logging

logger = logging.getLogger(__name__)


class WorkflowChunker:
    """
    Chunk GitHub Actions workflow files into meaningful segments
    """
    
    def __init__(self, max_chunk_size: int = 1000):
        """
        Args:
            max_chunk_size: Maximum characters per chunk
        """
        self.max_chunk_size = max_chunk_size
    
    def chunk_workflow(self, workflow_content: str, workflow_path: str, org_name: str) -> List[Dict[str, Any]]:
        """
        Chunk a workflow file by jobs and steps
        
        Args:
            workflow_content: Raw YAML content of workflow
            workflow_path: Path to the workflow file
            org_name: Organization name
            
        Returns:
            List of chunks with metadata
        """
        try:
            workflow_data = yaml.safe_load(workflow_content)
            chunks = []
            
            # Chunk 1: Workflow overview (name, triggers, env)
            overview = self._create_overview_chunk(workflow_data, workflow_path, org_name)
            if overview:
                chunks.append(overview)
            
            # Chunk 2-N: Each job as a separate chunk
            if "jobs" in workflow_data:
                for job_id, job_data in workflow_data["jobs"].items():
                    job_chunk = self._create_job_chunk(
                        job_id, job_data, workflow_path, org_name
                    )
                    chunks.append(job_chunk)
            
            logger.info(f"Created {len(chunks)} chunks from workflow: {workflow_path}")
            return chunks
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing workflow YAML: {str(e)}")
            # Fallback: create single chunk with raw content
            return [{
                "content": workflow_content[:self.max_chunk_size],
                "metadata": {
                    "type": "workflow",
                    "path": workflow_path,
                    "org_name": org_name,
                    "chunk_type": "raw"
                }
            }]
        except Exception as e:
            logger.error(f"Error chunking workflow: {str(e)}")
            return []
    
    def _create_overview_chunk(self, workflow_data: Dict, workflow_path: str, org_name: str) -> Dict[str, Any]:
        """Create overview chunk with workflow-level information"""
        overview_parts = []
        
        # Workflow name
        if "name" in workflow_data:
            overview_parts.append(f"Workflow: {workflow_data['name']}")
        
        # Triggers
        if "on" in workflow_data:
            triggers = workflow_data["on"]
            if isinstance(triggers, dict):
                trigger_names = list(triggers.keys())
            elif isinstance(triggers, list):
                trigger_names = triggers
            else:
                trigger_names = [str(triggers)]
            overview_parts.append(f"Triggers: {', '.join(trigger_names)}")
        
        # Environment variables
        if "env" in workflow_data:
            env_vars = list(workflow_data["env"].keys())
            overview_parts.append(f"Environment Variables: {', '.join(env_vars)}")
        
        # Permissions
        if "permissions" in workflow_data:
            overview_parts.append(f"Permissions: {workflow_data['permissions']}")
        
        content = "\n".join(overview_parts)
        
        return {
            "content": content,
            "metadata": {
                "type": "workflow",
                "path": workflow_path,
                "org_name": org_name,
                "chunk_type": "overview",
                "workflow_name": workflow_data.get("name", ""),
                "triggers": workflow_data.get("on", {})
            }
        }
    
    def _create_job_chunk(self, job_id: str, job_data: Dict, workflow_path: str, org_name: str) -> Dict[str, Any]:
        """Create chunk for a single job"""
        content_parts = [f"Job: {job_id}"]
        
        # Job name
        if "name" in job_data:
            content_parts.append(f"Name: {job_data['name']}")
        
        # Runs-on
        if "runs-on" in job_data:
            content_parts.append(f"Runs on: {job_data['runs-on']}")
        
        # Steps
        if "steps" in job_data:
            content_parts.append(f"\nSteps ({len(job_data['steps'])}):")
            for idx, step in enumerate(job_data["steps"], 1):
                step_name = step.get("name", f"Step {idx}")
                step_desc = f"  {idx}. {step_name}"
                
                # Add action/run information
                if "uses" in step:
                    step_desc += f" (uses: {step['uses']})"
                elif "run" in step:
                    run_cmd = step["run"].split("\n")[0][:50]  # First line, truncated
                    step_desc += f" (run: {run_cmd}...)"
                
                content_parts.append(step_desc)
        
        # Security tools detection
        security_tools = self._detect_security_tools(job_data)
        if security_tools:
            content_parts.append(f"\nSecurity Tools: {', '.join(security_tools)}")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content[:self.max_chunk_size],
            "metadata": {
                "type": "workflow",
                "path": workflow_path,
                "org_name": org_name,
                "chunk_type": "job",
                "job_id": job_id,
                "job_name": job_data.get("name", ""),
                "security_tools": security_tools
            }
        }
    
    def _detect_security_tools(self, job_data: Dict) -> List[str]:
        """Detect security tools used in a job"""
        tools = []
        security_actions = {
            "aquasecurity/trivy-action": "Trivy",
            "snyk/actions": "Snyk",
            "github/codeql-action": "CodeQL",
            "ossf/scorecard-action": "Scorecard",
            "anchore/scan-action": "Anchore",
            "trufflesecurity/trufflehog": "TruffleHog",
            "gitleaks/gitleaks-action": "Gitleaks",
        }
        
        if "steps" in job_data:
            for step in job_data["steps"]:
                if "uses" in step:
                    action = step["uses"]
                    for key, tool in security_actions.items():
                        if key in action:
                            tools.append(tool)
        
        return list(set(tools))


class AnalysisChunker:
    """
    Chunk analysis results for embedding
    """
    
    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size
    
    def chunk_analysis(self, analysis_data: Dict[str, Any], org_name: str) -> List[Dict[str, Any]]:
        """
        Chunk analysis results into meaningful segments
        
        Args:
            analysis_data: Analysis result data
            org_name: Organization name
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        
        try:
            # Chunk 1: DSOMM Summary
            if "dsomm" in analysis_data:
                dsomm_chunk = self._create_dsomm_chunk(analysis_data["dsomm"], org_name, analysis_data)
                chunks.append(dsomm_chunk)
            
            # Chunk 2: Security Tools
            if "tools" in analysis_data:
                tools_chunk = self._create_tools_chunk(analysis_data["tools"], org_name, analysis_data)
                chunks.append(tools_chunk)
            
            # Chunk 3: Key Findings
            if "findings" in analysis_data:
                findings_chunk = self._create_findings_chunk(analysis_data["findings"], org_name, analysis_data)
                chunks.append(findings_chunk)
            
            # Chunk 4: Recommendations
            if "recommendations" in analysis_data:
                rec_chunk = self._create_recommendations_chunk(
                    analysis_data["recommendations"], org_name, analysis_data
                )
                chunks.append(rec_chunk)
            
            logger.info(f"Created {len(chunks)} chunks from analysis")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking analysis: {str(e)}")
            return []
    
    def _create_dsomm_chunk(self, dsomm_data: Dict, org_name: str, full_analysis: Dict) -> Dict[str, Any]:
        """Create chunk for DSOMM scores"""
        content_parts = ["DevSecOps Maturity Model (DSOMM) Analysis:"]
        
        if "overall_score" in dsomm_data:
            content_parts.append(f"Overall Score: {dsomm_data['overall_score']}/100")
        
        if "dimensions" in dsomm_data:
            content_parts.append("\nDimension Scores:")
            for dim, score in dsomm_data["dimensions"].items():
                content_parts.append(f"  - {dim}: {score}/100")
        
        if "maturity_level" in dsomm_data:
            content_parts.append(f"\nMaturity Level: {dsomm_data['maturity_level']}")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content,
            "metadata": {
                "type": "analysis",
                "org_name": org_name,
                "chunk_type": "dsomm",
                "overall_score": dsomm_data.get("overall_score"),
                "maturity_level": dsomm_data.get("maturity_level"),
                "analysis_id": full_analysis.get("id", "")
            }
        }
    
    def _create_tools_chunk(self, tools_data: List[Dict], org_name: str, full_analysis: Dict) -> Dict[str, Any]:
        """Create chunk for detected security tools"""
        content_parts = ["Detected Security Tools:"]
        
        for tool in tools_data:
            tool_name = tool.get("name", "Unknown")
            tool_type = tool.get("type", "")
            content_parts.append(f"  - {tool_name} ({tool_type})")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content,
            "metadata": {
                "type": "analysis",
                "org_name": org_name,
                "chunk_type": "tools",
                "tool_count": len(tools_data),
                "tool_names": [t.get("name") for t in tools_data],
                "analysis_id": full_analysis.get("id", "")
            }
        }
    
    def _create_findings_chunk(self, findings: List[Dict], org_name: str, full_analysis: Dict) -> Dict[str, Any]:
        """Create chunk for key findings"""
        content_parts = ["Key Security Findings:"]
        
        for idx, finding in enumerate(findings[:10], 1):  # Limit to top 10
            severity = finding.get("severity", "")
            message = finding.get("message", "")
            content_parts.append(f"  {idx}. [{severity}] {message}")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content[:self.max_chunk_size],
            "metadata": {
                "type": "analysis",
                "org_name": org_name,
                "chunk_type": "findings",
                "finding_count": len(findings),
                "analysis_id": full_analysis.get("id", "")
            }
        }
    
    def _create_recommendations_chunk(self, recommendations: List[str], org_name: str, full_analysis: Dict) -> Dict[str, Any]:
        """Create chunk for recommendations"""
        content_parts = ["Security Recommendations:"]
        
        for idx, rec in enumerate(recommendations[:10], 1):
            content_parts.append(f"  {idx}. {rec}")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content[:self.max_chunk_size],
            "metadata": {
                "type": "analysis",
                "org_name": org_name,
                "chunk_type": "recommendations",
                "recommendation_count": len(recommendations),
                "analysis_id": full_analysis.get("id", "")
            }
        }
