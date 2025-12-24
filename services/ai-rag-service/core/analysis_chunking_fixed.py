"""
Analysis Chunking - Fixed to match actual workspace-intelligence-service response structure

The actual analysis response has this structure:
{
    "success": true,
    "analysis": {
        "project_name": str,
        "overall_maturity_score": float,
        "maturity_level": str,
        "detected_practices": {...},
        ...
    },
    "repositories": [],
    "findings": [],
    "maturity_scores": {},
    "findings_summary": {}
}
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class AnalysisChunker:
    """Chunks analysis results for RAG indexing"""
    
    def chunk_analysis(self, analysis_data: Dict, org_name: str) -> List[Dict[str, Any]]:
        """
        Chunk analysis results for indexing
        
        Args:
            analysis_data: Complete analysis results from workspace-intelligence-service
            org_name: Organization name
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        
        # Debug: Log the structure we received
        logger.info(f"📋 Analysis data keys: {list(analysis_data.keys())}")
        
        try:
            # Extract the actual analysis object
            analysis = analysis_data.get("analysis", {})
            maturity_scores = analysis_data.get("maturity_scores", {})
            findings = analysis_data.get("findings", [])
            findings_summary = analysis_data.get("findings_summary", {})
            repositories = analysis_data.get("repositories", [])
            
            # Skip if no meaningful data
            overall_score = analysis.get("overall_maturity_score", 0)
            if not analysis or overall_score == 0:
                logger.warning("⚠️ Analysis has no maturity scores or data to index (score=0, likely no repositories)")
                return chunks
            
            # Chunk 1: Overall project maturity
            project_chunk = self._create_project_maturity_chunk(
                analysis, 
                maturity_scores,
                findings_summary,
                org_name
            )
            if project_chunk:
                chunks.append(project_chunk)
            
            # Chunk 2: Security findings (if any)
            if findings:
                findings_chunk = self._create_findings_chunk(findings, analysis, org_name)
                if findings_chunk:
                    chunks.append(findings_chunk)
            
            # Chunk 3: Detected practices and tools
            detected_practices = analysis.get("detected_practices")
            if detected_practices:
                practices_chunk = self._create_practices_chunk(
                    detected_practices,
                    analysis,
                    org_name
                )
                if practices_chunk:
                    chunks.append(practices_chunk)
            
            logger.info(f"Created {len(chunks)} chunks from analysis")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking analysis: {e}", exc_info=True)
            return chunks
    
    def _create_project_maturity_chunk(
        self, 
        analysis: Dict,
        maturity_scores: Dict,
        findings_summary: Dict,
        org_name: str
    ) -> Optional[Dict[str, Any]]:
        """Create chunk for project maturity overview"""
        try:
            project_name = analysis.get("project_name", "Unknown")
            overall_score = analysis.get("overall_maturity_score", 0)
            maturity_level = analysis.get("maturity_level", "0")
            
            content_parts = [
                f"📊 DevSecOps Maturity Analysis for {project_name}",
                f"Organization: {org_name}",
                f"",
                f"🎯 Overall Maturity Score: {overall_score}/100 (Level {maturity_level})",
                f""
            ]
            
            # Domain scores
            if maturity_scores:
                content_parts.append("📈 Domain Scores:")
                for domain, score in maturity_scores.items():
                    if isinstance(score, (int, float)):
                        domain_label = domain.replace('_', ' ').title()
                        content_parts.append(f"  • {domain_label}: {score}/100")
                content_parts.append("")
            
            # Findings summary
            if findings_summary:
                total_findings = sum(findings_summary.values())
                if total_findings > 0:
                    content_parts.append(f"🔍 Security Findings ({total_findings} total):")
                    for severity, count in findings_summary.items():
                        if count > 0:
                            content_parts.append(f"  • {severity.title()}: {count}")
                    content_parts.append("")
            
            # Repository stats
            total_repos = analysis.get("total_repositories", 0)
            total_workflows = analysis.get("total_workflows", 0)
            content_parts.append(f"📦 Repository Statistics:")
            content_parts.append(f"  • Total Repositories: {total_repos}")
            content_parts.append(f"  • Total Workflows: {total_workflows}")
            
            return {
                "content": "\n".join(content_parts),
                "metadata": {
                    "type": "analysis",
                    "chunk_type": "project_maturity",
                    "organization": org_name,
                    "project_name": project_name,
                    "maturity_score": overall_score,
                    "maturity_level": maturity_level,
                    "total_findings": sum(findings_summary.values()) if findings_summary else 0,
                    "total_repositories": total_repos,
                    "analysis_id": analysis.get("id", "unknown")
                }
            }
        except Exception as e:
            logger.error(f"Error creating project maturity chunk: {e}")
            return None
    
    def _create_findings_chunk(
        self,
        findings: List[Dict],
        analysis: Dict,
        org_name: str
    ) -> Optional[Dict[str, Any]]:
        """Create chunk for security findings"""
        try:
            project_name = analysis.get("project_name", "Unknown")
            content_parts = [
                f"🔒 Security Findings for {project_name}",
                f"Organization: {org_name}",
                f"",
                f"Total Findings: {len(findings)}",
                f""
            ]
            
            # Group findings by severity
            by_severity = {}
            for finding in findings[:50]:  # Limit to avoid huge chunks
                severity = finding.get("severity", "unknown")
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(finding)
            
            # Add findings by severity
            for severity in ["critical", "high", "medium", "low"]:
                if severity in by_severity:
                    content_parts.append(f"\n{severity.upper()} Priority:")
                    for finding in by_severity[severity][:10]:  # Limit per severity
                        title = finding.get("title", "Unknown")
                        repo = finding.get("repository", "")
                        content_parts.append(f"  • {title}")
                        if repo:
                            content_parts.append(f"    Repository: {repo}")
            
            return {
                "content": "\n".join(content_parts),
                "metadata": {
                    "type": "analysis",
                    "chunk_type": "findings",
                    "organization": org_name,
                    "project_name": project_name,
                    "finding_count": len(findings),
                    "analysis_id": analysis.get("id", "unknown")
                }
            }
        except Exception as e:
            logger.error(f"Error creating findings chunk: {e}")
            return None
    
    def _create_practices_chunk(
        self,
        detected_practices: Dict,
        analysis: Dict,
        org_name: str
    ) -> Optional[Dict[str, Any]]:
        """Create chunk for detected security practices and tools"""
        try:
            project_name = analysis.get("project_name", "Unknown")
            content_parts = [
                f"🛠️ Detected Security Practices for {project_name}",
                f"Organization: {org_name}",
                f""
            ]
            
            # Tool detection
            tool_sections = []
            
            # SAST tools
            sast_tools = detected_practices.get("sast_tools", [])
            if sast_tools:
                tool_sections.append(f"🔍 SAST Tools: {', '.join(sast_tools)}")
            
            # SCA tools
            sca_tools = detected_practices.get("sca_tools", [])
            if sca_tools:
                tool_sections.append(f"📦 SCA Tools: {', '.join(sca_tools)}")
            
            # Secret scanning
            secret_tools = detected_practices.get("secret_scanning_tools", [])
            if secret_tools:
                tool_sections.append(f"🔑 Secret Scanning: {', '.join(secret_tools)}")
            
            # Container scanning
            container_tools = detected_practices.get("container_scanning_tools", [])
            if container_tools:
                tool_sections.append(f"🐳 Container Scanning: {', '.join(container_tools)}")
            
            # DAST tools
            dast_tools = detected_practices.get("dast_tools", [])
            if dast_tools:
                tool_sections.append(f"🌐 DAST Tools: {', '.join(dast_tools)}")
            
            if tool_sections:
                content_parts.extend(tool_sections)
                content_parts.append("")
            
            # Security practices
            practices = []
            
            if detected_practices.get("branch_protection_enabled"):
                practices.append("✅ Branch protection enabled")
            
            if detected_practices.get("has_codeowners"):
                practices.append("✅ CODEOWNERS file present")
            
            if detected_practices.get("has_pr_workflows"):
                practices.append("✅ Pull request workflows configured")
            
            if detected_practices.get("uses_reusable_workflows"):
                practices.append("✅ Using reusable workflows")
            
            if detected_practices.get("uses_centralized_workflows"):
                practices.append("✅ Centralized workflow management")
            
            if detected_practices.get("signed_commits_required"):
                practices.append("✅ Signed commits required")
            
            if detected_practices.get("required_status_checks"):
                practices.append("✅ Required status checks")
            
            if practices:
                content_parts.append("🔐 Security Practices:")
                for practice in practices:
                    content_parts.append(f"  {practice}")
                content_parts.append("")
            
            # Repository coverage
            repos_with_workflows = detected_practices.get("repos_with_workflows", 0)
            total_repos = detected_practices.get("total_repos", 0)
            if total_repos > 0:
                coverage = (repos_with_workflows / total_repos) * 100
                content_parts.append(f"📊 Workflow Coverage: {repos_with_workflows}/{total_repos} repos ({coverage:.1f}%)")
            
            return {
                "content": "\n".join(content_parts),
                "metadata": {
                    "type": "analysis",
                    "chunk_type": "practices",
                    "organization": org_name,
                    "project_name": project_name,
                    "sast_tools": sast_tools,
                    "sca_tools": sca_tools,
                    "secret_scanning_tools": secret_tools,
                    "container_scanning_tools": container_tools,
                    "dast_tools": dast_tools,
                    "analysis_id": analysis.get("id", "unknown")
                }
            }
        except Exception as e:
            logger.error(f"Error creating practices chunk: {e}")
            return None
