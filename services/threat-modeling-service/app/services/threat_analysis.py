"""
Threat Analysis Service
Business logic for threat model analysis, STRIDE methodology, and risk assessment
"""

from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ThreatAnalysisService:
    """Service for threat model analysis operations"""
    
    @staticmethod
    def calculate_complexity_score(elements: List, connections: List) -> int:
        """Calculate architecture complexity score (1-10)"""
        base_score = min(len(elements) * 0.5 + len(connections) * 0.3, 8)
        
        # Increase complexity for multiple data stores, external entities
        datastore_count = len([e for e in elements if e.get("type") == "datastore"])
        external_count = len([e for e in elements if e.get("type") == "external_entity"])
        
        complexity_bonus = min(datastore_count * 0.5 + external_count * 0.3, 2)
        
        return min(int(base_score + complexity_bonus), 10)
    
    @staticmethod
    def identify_critical_components(elements: List, connections: List) -> List:
        """Identify components with high connectivity or sensitive data"""
        critical = []
        
        # Count connections per element
        connection_counts = {}
        for conn in connections:
            source = conn.get("source")
            target = conn.get("target")
            connection_counts[source] = connection_counts.get(source, 0) + 1
            connection_counts[target] = connection_counts.get(target, 0) + 1
        
        for element in elements:
            element_id = element.get("id")
            connections_count = connection_counts.get(element_id, 0)
            
            # Critical if highly connected or sensitive type
            if connections_count >= 3 or element.get("type") in ["datastore", "process"]:
                critical.append({
                    "id": element_id,
                    "name": element.get("name", "Unnamed"),
                    "type": element.get("type"),
                    "connection_count": connections_count,
                    "reason": "High connectivity" if connections_count >= 3 else "Sensitive component type"
                })
        
        return critical
    
    @staticmethod
    def analyze_threat_coverage(elements: List, threats: List, methodology: str) -> Dict:
        """Analyze how well threats cover the architecture"""
        total_elements = len(elements)
        threatened_elements = set()
        
        for threat in threats:
            if threat.get("elementId"):
                threatened_elements.add(threat.get("elementId"))
        
        coverage_percentage = (len(threatened_elements) / max(total_elements, 1)) * 100
        
        return {
            "total_elements": total_elements,
            "threatened_elements": len(threatened_elements),
            "coverage_percentage": round(coverage_percentage, 1),
            "uncovered_elements": total_elements - len(threatened_elements),
            "methodology": methodology
        }
    
    @staticmethod
    def identify_risk_hotspots(elements: List, connections: List, threats: List) -> List:
        """Identify components with highest risk concentration"""
        risk_scores = {}
        
        # Calculate risk per element based on threats
        for threat in threats:
            element_id = threat.get("elementId")
            if element_id:
                risk_score = threat.get("riskScore", 5)  # Default medium risk
                risk_scores[element_id] = risk_scores.get(element_id, 0) + risk_score
        
        # Sort by risk score
        hotspots = []
        for element in elements:
            element_id = element.get("id")
            total_risk = risk_scores.get(element_id, 0)
            
            if total_risk > 0:
                hotspots.append({
                    "id": element_id,
                    "name": element.get("name", "Unnamed"),
                    "type": element.get("type"),
                    "total_risk_score": total_risk,
                    "threat_count": len([t for t in threats if t.get("elementId") == element_id])
                })
        
        # Return top 5 hotspots
        return sorted(hotspots, key=lambda x: x["total_risk_score"], reverse=True)[:5]
    
    @staticmethod
    def identify_security_gaps(elements: List, connections: List, methodology: str) -> List:
        """Identify potential security gaps in the architecture"""
        gaps = []
        
        # Check for unprotected data stores
        datastores = [e for e in elements if e.get("type") == "datastore"]
        for ds in datastores:
            # Check if datastore has authentication/encryption connections
            ds_connections = [c for c in connections 
                             if c.get("source") == ds.get("id") or c.get("target") == ds.get("id")]
            
            if not any("auth" in c.get("label", "").lower() for c in ds_connections):
                gaps.append({
                    "type": "authentication",
                    "component": ds.get("name", "Unnamed Datastore"),
                    "description": "Datastore may lack proper authentication controls",
                    "severity": "High"
                })
        
        # Check for unencrypted external communications
        for conn in connections:
            source_el = next((e for e in elements if e.get("id") == conn.get("source")), None)
            target_el = next((e for e in elements if e.get("id") == conn.get("target")), None)
            
            if (source_el and source_el.get("type") == "external_entity") or \
               (target_el and target_el.get("type") == "external_entity"):
                if "encrypt" not in conn.get("label", "").lower() and "https" not in conn.get("label", "").lower():
                    gaps.append({
                        "type": "encryption",
                        "component": f"Connection: {conn.get('label', 'Unnamed')}",
                        "description": "External communication may lack encryption",
                        "severity": "Medium"
                    })
        
        return gaps
    
    @staticmethod
    def extract_compliance_requirements(document_context: Dict) -> List:
        """Extract compliance requirements from document analysis"""
        compliance_terms = {
            "GDPR": ["gdpr", "general data protection regulation", "data protection"],
            "HIPAA": ["hipaa", "health insurance portability"],
            "SOX": ["sarbanes-oxley", "sox", "financial reporting"],
            "PCI DSS": ["pci", "payment card industry", "card data"],
            "ISO 27001": ["iso 27001", "information security management"]
        }
        
        requirements = []
        security_keywords = document_context.get("security_keywords", [])
        key_insights = document_context.get("key_insights", [])
        
        all_text = " ".join(security_keywords + key_insights).lower()
        
        for standard, keywords in compliance_terms.items():
            if any(keyword in all_text for keyword in keywords):
                requirements.append(standard)
        
        return requirements
    
    @staticmethod
    def generate_document_recommendations(document_context: Dict, elements: List) -> List:
        """Generate recommendations based on document analysis"""
        recommendations = []
        
        technologies = document_context.get("technologies", [])
        security_keywords = document_context.get("security_keywords", [])
        
        # Technology-specific recommendations
        if "Database" in technologies:
            recommendations.append("Consider implementing database encryption at rest based on document requirements")
        
        if "Web Application" in technologies:
            recommendations.append("Implement web application security controls as mentioned in documentation")
        
        # Security keyword driven recommendations
        if "compliance" in security_keywords:
            recommendations.append("Ensure threat model addresses compliance requirements from documentation")
        
        if "monitoring" in security_keywords:
            recommendations.append("Add monitoring and logging components as specified in requirements")
        
        return recommendations
    
    @staticmethod
    def generate_comprehensive_recommendations(
        elements: List, connections: List, threats: List, metadata: Dict, document_context: Optional[Dict]
    ) -> List:
        """Generate comprehensive AI-powered recommendations"""
        recommendations = []
        
        # Architecture recommendations
        if len(elements) > 10:
            recommendations.append({
                "category": "Architecture",
                "priority": "Medium",
                "title": "Consider Microservices Decomposition",
                "description": "Large monolithic architecture detected. Consider breaking into smaller services.",
                "rationale": "Improved security isolation and maintainability"
            })
        
        # Security recommendations based on methodology
        methodology = metadata.get("methodology", "STRIDE")
        
        if methodology == "STRIDE":
            # STRIDE-specific recommendations
            process_count = len([e for e in elements if e.get("type") == "process"])
            if process_count > 0 and len(threats) < process_count * 2:
                recommendations.append({
                    "category": "Threat Coverage",
                    "priority": "High", 
                    "title": "Increase STRIDE Threat Coverage",
                    "description": f"Only {len(threats)} threats identified for {process_count} processes. Consider all STRIDE categories.",
                    "rationale": "Comprehensive threat coverage ensures no attack vectors are missed"
                })
        
        # Document-driven recommendations
        if document_context:
            technologies = document_context.get("technologies", [])
            if "API" in technologies:
                recommendations.append({
                    "category": "API Security",
                    "priority": "High",
                    "title": "Implement API Security Controls", 
                    "description": "Document mentions APIs. Ensure rate limiting, authentication, and input validation.",
                    "rationale": "APIs are common attack vectors requiring specific security measures"
                })
        
        # Risk-based recommendations
        high_risk_threats = [t for t in threats if t.get("riskScore", 0) > 15]
        if high_risk_threats:
            recommendations.append({
                "category": "Risk Management",
                "priority": "Critical",
                "title": "Address Critical Risk Threats",
                "description": f"{len(high_risk_threats)} high-risk threats require immediate attention.",
                "rationale": "High-risk threats can lead to significant security incidents"
            })
        
        return recommendations
    
    @staticmethod
    def generate_action_items(recommendations: List) -> List:
        """Convert recommendations into actionable items"""
        action_items = []
        
        for i, rec in enumerate(recommendations[:5]):  # Top 5 recommendations
            action_items.append({
                "id": f"action_{i+1}",
                "title": rec.get("title", ""),
                "priority": rec.get("priority", "Medium"),
                "category": rec.get("category", "General"),
                "estimated_effort": "Medium",
                "timeline": "Next Sprint" if rec.get("priority") == "Critical" else "Next Release"
            })
        
        return action_items
    
    @staticmethod
    def generate_executive_summary(architecture_analysis: Dict, security_analysis: Dict, document_insights: Dict) -> str:
        """Generate executive summary of the analysis"""
        
        complexity = architecture_analysis.get("complexity_score", 0)
        threat_count = security_analysis.get("existing_threat_count", 0)
        coverage = security_analysis.get("coverage_analysis", {}).get("coverage_percentage", 0)
        
        summary_parts = []
        
        # Architecture overview
        summary_parts.append(f"Architecture contains {architecture_analysis.get('component_count', 0)} components with complexity score {complexity}/10.")
        
        # Security posture
        if coverage < 50:
            summary_parts.append(f"Security coverage at {coverage:.1f}% requires improvement.")
        else:
            summary_parts.append(f"Good security coverage at {coverage:.1f}%.")
        
        # Document integration
        if document_insights.get("document_available"):
            summary_parts.append("Analysis enhanced with uploaded documentation context.")
        
        # Risk assessment
        risk_hotspots = len(security_analysis.get("risk_hotspots", []))
        if risk_hotspots > 0:
            summary_parts.append(f"{risk_hotspots} high-risk components identified requiring attention.")
        
        return " ".join(summary_parts)
    
    @staticmethod
    def generate_compliance_guidance(methodology: str, document_context: Optional[Dict]) -> Dict:
        """Generate compliance-specific guidance"""
        guidance = {
            "methodology_compliance": {},
            "document_driven": []
        }
        
        # Methodology-specific compliance
        if methodology == "STRIDE":
            guidance["methodology_compliance"] = {
                "framework": "STRIDE",
                "compliance_benefits": [
                    "Comprehensive threat categorization",
                    "Structured security analysis",
                    "Industry-standard methodology"
                ]
            }
        
        # Document-driven compliance
        if document_context:
            requirements = ThreatAnalysisService.extract_compliance_requirements(document_context)
            for req in requirements:
                guidance["document_driven"].append({
                    "standard": req,
                    "recommendation": f"Ensure threat model addresses {req} requirements"
                })
        
        return guidance
    
    @staticmethod
    def generate_methodology_insights(methodology: str, elements: List, connections: List) -> Dict:
        """Generate methodology-specific insights and recommendations"""
        
        insights = {
            "methodology": methodology,
            "specific_recommendations": []
        }
        
        if methodology == "STRIDE":
            # STRIDE-specific analysis
            process_count = len([e for e in elements if e.get("type") == "process"])
            dataflow_count = len([e for e in elements if e.get("type") == "dataflow"])
            datastore_count = len([e for e in elements if e.get("type") == "datastore"])
            
            insights["component_breakdown"] = {
                "processes": process_count,
                "dataflows": dataflow_count, 
                "datastores": datastore_count
            }
            
            insights["specific_recommendations"] = [
                f"Analyze all {process_count} processes for Spoofing and Tampering threats",
                f"Review {datastore_count} datastores for Information Disclosure risks",
                f"Ensure {dataflow_count} dataflows have proper Elevation of Privilege controls"
            ]
        
        elif methodology == "CIA":
            # CIA Triad specific analysis
            insights["specific_recommendations"] = [
                "Verify Confidentiality controls for sensitive data elements",
                "Ensure Integrity mechanisms for all data modifications", 
                "Confirm Availability requirements for critical services"
            ]
        
        return insights
    
    @staticmethod
    async def analyze_comprehensive(
        model_id: str,
        canvas_data: Dict,
        metadata: Dict,
        document_context: Optional[Dict]
    ) -> Dict:
        """
        Perform comprehensive threat model analysis combining multiple data sources
        """
        
        # Extract canvas components
        elements = canvas_data.get("elements", [])
        connections = canvas_data.get("connections", [])
        existing_threats = canvas_data.get("threats", [])
        
        # Architecture Analysis
        architecture_analysis = {
            "component_count": len(elements),
            "connection_count": len(connections),
            "methodology": metadata.get("methodology", "STRIDE"),
            "complexity_score": ThreatAnalysisService.calculate_complexity_score(elements, connections),
            "critical_components": ThreatAnalysisService.identify_critical_components(elements, connections)
        }
        
        # Security Posture Analysis
        security_analysis = {
            "existing_threat_count": len(existing_threats),
            "coverage_analysis": ThreatAnalysisService.analyze_threat_coverage(elements, existing_threats, metadata.get("methodology")),
            "risk_hotspots": ThreatAnalysisService.identify_risk_hotspots(elements, connections, existing_threats),
            "security_gaps": ThreatAnalysisService.identify_security_gaps(elements, connections, metadata.get("methodology"))
        }
        
        # Document Context Integration
        document_insights = {}
        if document_context:
            document_insights = {
                "document_available": True,
                "technologies_mentioned": document_context.get("technologies", []),
                "security_keywords": document_context.get("security_keywords", []),
                "compliance_requirements": ThreatAnalysisService.extract_compliance_requirements(document_context),
                "document_driven_recommendations": ThreatAnalysisService.generate_document_recommendations(document_context, elements)
            }
        else:
            document_insights = {"document_available": False}
        
        # Generate AI Recommendations
        recommendations = ThreatAnalysisService.generate_comprehensive_recommendations(
            elements, connections, existing_threats, metadata, document_context
        )
        
        # Create comprehensive analysis response
        analysis_response = {
            "model_id": model_id,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "analysis_version": "2.0-comprehensive",
            
            "executive_summary": ThreatAnalysisService.generate_executive_summary(
                architecture_analysis, security_analysis, document_insights
            ),
            
            "architecture_analysis": architecture_analysis,
            "security_analysis": security_analysis,
            "document_insights": document_insights,
            
            "recommendations": recommendations,
            
            "action_items": ThreatAnalysisService.generate_action_items(recommendations),
            
            "compliance_guidance": ThreatAnalysisService.generate_compliance_guidance(
                metadata.get("methodology"), document_context
            ),
            
            "methodology_specific_insights": ThreatAnalysisService.generate_methodology_insights(
                metadata.get("methodology"), elements, connections
            )
        }
        
        return analysis_response
