"""
Analysis Chunking - Updated to match workspace-intelligence-service structure
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class AnalysisChunker:
    """Chunks analysis results from workspace-intelligence-service into searchable segments"""
    
    def __init__(self, max_chunk_size: int = 2000):
        self.max_chunk_size = max_chunk_size
    
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
        logger.info(f"📋 Analysis data type: {type(analysis_data)}")
        
        try:
            # Extract the actual analysis object
            analysis = analysis_data.get("analysis", {})
            maturity_scores = analysis_data.get("maturity_scores", {})
            findings = analysis_data.get("findings", [])
            findings_summary = analysis_data.get("findings_summary", {})
            repositories = analysis_data.get("repositories", [])
            
            # Skip if no meaningful data
            if not analysis or analysis.get("overall_maturity_score", 0) == 0:
                logger.warning("⚠️ Analysis has no maturity scores or data to index")
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
            
            # Chunk 2: Security findings
            if findings:
                for project in analysis_data["project_analyses"]:
                    project_chunk = self._create_project_chunk(project, org_name, analysis_data)
                    chunks.append(project_chunk)
            
            # Chunk: Centralized Workflows
            if "centralized_workflows" in analysis_data and analysis_data["centralized_workflows"]:
                central_chunk = self._create_centralized_workflows_chunk(
                    analysis_data["centralized_workflows"],
                    org_name,
                    analysis_data
                )
                chunks.append(central_chunk)
            
            # Chunk: Insights and Recommendations
            if "insights" in analysis_data:
                insights_chunk = self._create_insights_chunk(
                    analysis_data["insights"],
                    org_name,
                    analysis_data
                )
                chunks.append(insights_chunk)
            
            logger.info(f"Created {len(chunks)} chunks from analysis")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking analysis: {str(e)}")
            return []
    
    def _create_organization_metrics_chunk(self, org_metrics: Dict, org_name: str, full_analysis: Dict) -> Dict[str, Any]:
        """Create chunk for organization-wide metrics and DSOMM scores"""
        content_parts = [f"DevSecOps Maturity Analysis for {org_name}"]
        
        # Overall maturity
        overall_maturity = org_metrics.get("overall_maturity", 0)
        maturity_level = org_metrics.get("maturity_level", 0)
        maturity_label = org_metrics.get("maturity_label", "Unknown")
        
        content_parts.append(f"\n🎯 Overall DSOMM Maturity Score: {overall_maturity:.1f}/100")
        content_parts.append(f"Maturity Level: {maturity_level}/3 - {maturity_label}")
        
        # Domain scores
        if "domain_scores" in org_metrics:
            content_parts.append("\n📊 Domain Scores:")
            domain_scores = org_metrics["domain_scores"]
            
            if "technology" in domain_scores:
                tech_score = domain_scores["technology"].get("domain_score", 0)
                content_parts.append(f"  • Technology Domain: {tech_score:.1f}/100")
                
                # Technology activities
                if "activities" in domain_scores["technology"]:
                    content_parts.append("    Activities:")
                    for activity_key, activity_data in domain_scores["technology"]["activities"].items():
                        activity_name = activity_data.get("activity_name", activity_key)
                        activity_score = activity_data.get("score", 0)
                        level = activity_data.get("level", 0)
                        tools = activity_data.get("detected_tools", [])
                        
                        tools_str = f" (Tools: {', '.join(tools)})" if tools else ""
                        content_parts.append(f"      - {activity_name}: {activity_score}/100 (Level {level}){tools_str}")
            
            if "process" in domain_scores:
                process_score = domain_scores["process"].get("domain_score", 0)
                content_parts.append(f"  • Process Domain: {process_score:.1f}/100")
                
                # Process activities
                if "activities" in domain_scores["process"]:
                    content_parts.append("    Activities:")
                    for activity_key, activity_data in domain_scores["process"]["activities"].items():
                        activity_name = activity_data.get("activity_name", activity_key)
                        activity_score = activity_data.get("score", 0)
                        level = activity_data.get("level", 0)
                        content_parts.append(f"      - {activity_name}: {activity_score}/100 (Level {level})")
        
        # Detected security tools
        if "detected_tools" in org_metrics:
            content_parts.append("\n🛠️ Detected Security Tools:")
            tools = org_metrics["detected_tools"]
            
            if "sast_tools" in tools and tools["sast_tools"]:
                content_parts.append(f"  • SAST: {', '.join(tools['sast_tools'])}")
            if "sca_tools" in tools and tools["sca_tools"]:
                content_parts.append(f"  • SCA: {', '.join(tools['sca_tools'])}")
            if "dast_tools" in tools and tools["dast_tools"]:
                content_parts.append(f"  • DAST: {', '.join(tools['dast_tools'])}")
            if "secret_tools" in tools and tools["secret_tools"]:
                content_parts.append(f"  • Secret Scanning: {', '.join(tools['secret_tools'])}")
            if "container_tools" in tools and tools["container_tools"]:
                content_parts.append(f"  • Container Scanning: {', '.join(tools['container_tools'])}")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content[:self.max_chunk_size],
            "metadata": {
                "type": "analysis",
                "org_name": org_name,
                "chunk_type": "organization_metrics",
                "overall_maturity": overall_maturity,
                "maturity_level": maturity_level,
                "maturity_label": maturity_label,
                "analysis_id": full_analysis.get("id", "")
            }
        }
    
    def _create_project_chunk(self, project: Dict, org_name: str, full_analysis: Dict) -> Dict[str, Any]:
        """Create chunk for a single project/folder analysis"""
        project_name = project.get("project_name", "Unknown")
        content_parts = [f"📁 Project: {project_name}"]
        
        # Project summary
        repo_count = project.get("repository_count", 0)
        workflow_count = project.get("workflow_count", 0)
        content_parts.append(f"Repositories: {repo_count} | Workflows: {workflow_count}")
        
        # Project maturity
        if "maturity" in project:
            maturity = project["maturity"]
            overall_score = maturity.get("overall_maturity", 0)
            level = maturity.get("maturity_level", 0)
            label = maturity.get("maturity_label", "Unknown")
            
            content_parts.append(f"\n🎯 Project DSOMM Score: {overall_score:.1f}/100 (Level {level} - {label})")
            
            # Project domain scores
            if "domain_scores" in maturity:
                content_parts.append("\nDomain Scores:")
                for domain_name, domain_data in maturity["domain_scores"].items():
                    domain_score = domain_data.get("domain_score", 0)
                    content_parts.append(f"  • {domain_name.title()}: {domain_score:.1f}/100")
        
        # Findings summary
        if "findings_count" in project:
            findings = project["findings_count"]
            total_findings = sum(findings.values())
            
            if total_findings > 0:
                content_parts.append(f"\n⚠️ Security Findings ({total_findings} total):")
                if findings.get("critical", 0) > 0:
                    content_parts.append(f"  • Critical: {findings['critical']}")
                if findings.get("high", 0) > 0:
                    content_parts.append(f"  • High: {findings['high']}")
                if findings.get("medium", 0) > 0:
                    content_parts.append(f"  • Medium: {findings['medium']}")
                if findings.get("low", 0) > 0:
                    content_parts.append(f"  • Low: {findings['low']}")
        
        # Detected practices for this project
        if "detected_practices" in project:
            practices = project["detected_practices"]
            content_parts.append("\n🔍 Detected Security Practices:")
            
            if practices.get("sast_tools"):
                content_parts.append(f"  • SAST Tools: {', '.join(practices['sast_tools'])}")
            if practices.get("sca_tools"):
                content_parts.append(f"  • SCA Tools: {', '.join(practices['sca_tools'])}")
            if practices.get("secret_tools"):
                content_parts.append(f"  • Secret Scanning: {', '.join(practices['secret_tools'])}")
            
            if practices.get("has_ci_cd"):
                content_parts.append("  • CI/CD: Enabled")
            if practices.get("uses_reusable_workflows"):
                content_parts.append("  • Reusable Workflows: Yes")
            if practices.get("branch_protection_enabled"):
                content_parts.append("  • Branch Protection: Enabled")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content[:self.max_chunk_size],
            "metadata": {
                "type": "analysis",
                "org_name": org_name,
                "chunk_type": "project_analysis",
                "project_name": project_name,
                "project_id": project.get("project_id"),
                "maturity_score": project.get("maturity", {}).get("overall_maturity", 0),
                "maturity_level": project.get("maturity", {}).get("maturity_level", 0),
                "repository_count": repo_count,
                "workflow_count": workflow_count,
                "analysis_id": full_analysis.get("id", "")
            }
        }
    
    def _create_centralized_workflows_chunk(self, centralized_wf: Dict, org_name: str, full_analysis: Dict) -> Dict[str, Any]:
        """Create chunk for centralized workflows information"""
        content_parts = ["🔄 Centralized Workflows"]
        
        for wf_name, wf_data in centralized_wf.items():
            used_by = wf_data.get("used_by", [])
            content_parts.append(f"\n📦 {wf_name}")
            content_parts.append(f"  Used by {len(used_by)} repositories: {', '.join(used_by[:5])}")
            if len(used_by) > 5:
                content_parts.append(f"  ...and {len(used_by) - 5} more")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content[:self.max_chunk_size],
            "metadata": {
                "type": "analysis",
                "org_name": org_name,
                "chunk_type": "centralized_workflows",
                "workflow_count": len(centralized_wf),
                "analysis_id": full_analysis.get("id", "")
            }
        }
    
    def _create_insights_chunk(self, insights: List[Dict], org_name: str, full_analysis: Dict) -> Dict[str, Any]:
        """Create chunk for insights and recommendations"""
        content_parts = ["💡 DevSecOps Insights and Recommendations"]
        
        # Group by priority
        high_priority = [i for i in insights if i.get("priority") == "high"]
        medium_priority = [i for i in insights if i.get("priority") == "medium"]
        
        if high_priority:
            content_parts.append("\n🔴 High Priority:")
            for insight in high_priority:
                title = insight.get("title", "")
                rec = insight.get("recommendation", "")
                impact = insight.get("impact", "")
                content_parts.append(f"  • {title}")
                content_parts.append(f"    Recommendation: {rec}")
                content_parts.append(f"    Impact: {impact}")
        
        if medium_priority:
            content_parts.append("\n🟡 Medium Priority:")
            for insight in medium_priority:
                title = insight.get("title", "")
                rec = insight.get("recommendation", "")
                content_parts.append(f"  • {title}")
                content_parts.append(f"    {rec}")
        
        content = "\n".join(content_parts)
        
        return {
            "content": content[:self.max_chunk_size],
            "metadata": {
                "type": "analysis",
                "org_name": org_name,
                "chunk_type": "insights",
                "insight_count": len(insights),
                "high_priority_count": len(high_priority),
                "analysis_id": full_analysis.get("id", "")
            }
        }
