import os
import json
import asyncio
import aiohttp
import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class GroqRateLimiter:
    """Rate limiter to prevent 429 errors from Groq API"""
    def __init__(self, max_requests_per_minute=10):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            # If we've hit the limit, wait
            if len(self.requests) >= self.max_requests:
                wait_time = 60 - (now - self.requests[0]) + 1  # Wait until oldest request is > 1 minute old
                print(f"⏱️ Rate limit reached, waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
                return await self.acquire()  # Recursive call after waiting
            
            # Add current request to the list
            self.requests.append(now)
            return True

class ThreatCategory(Enum):
    # STRIDE Categories
    STRIDE_SPOOFING = "spoofing"
    STRIDE_TAMPERING = "tampering"
    STRIDE_REPUDIATION = "repudiation"
    STRIDE_INFORMATION_DISCLOSURE = "information_disclosure"
    STRIDE_DENIAL_OF_SERVICE = "denial_of_service"
    STRIDE_ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"
    
    # CIA Categories  
    CIA_CONFIDENTIALITY = "confidentiality"
    CIA_INTEGRITY = "integrity"
    CIA_AVAILABILITY = "availability"
    
    # LINDDUN Categories
    LINDDUN_LINKABILITY = "linkability"
    LINDDUN_IDENTIFIABILITY = "identifiability"
    LINDDUN_NON_REPUDIATION = "non_repudiation"
    LINDDUN_DETECTABILITY = "detectability"
    LINDDUN_DISCLOSURE = "disclosure_of_information"
    LINDDUN_UNAWARENESS = "unawareness"
    LINDDUN_NON_COMPLIANCE = "non_compliance"
    
    # OWASP Categories
    OWASP_INJECTION = "injection"
    OWASP_BROKEN_AUTH = "broken_authentication"
    OWASP_SENSITIVE_DATA = "sensitive_data_exposure"
    OWASP_XXE = "xml_external_entities"
    OWASP_BROKEN_ACCESS = "broken_access_control"

@dataclass
class ThreatSuggestion:
    id: str
    title: str
    description: str
    category: ThreatCategory
    severity: str  # "Low", "Medium", "High", "Critical"
    likelihood: str  # "Low", "Medium", "High"
    impact: str  # "Low", "Medium", "High"
    mitigation: str
    confidence: float  # 0.0 - 1.0
    component_ids: List[str]  # Which components this threat affects
    dismissed: bool = False  # Track if user dismissed this suggestion
    jira_ticket_created: bool = False  # Track if Jira ticket was created
    mitigation_steps: List[str] = None  # Detailed mitigation steps
    tools_required: List[str] = None  # Tools/technologies needed
    estimated_effort: str = None  # Low/Medium/High effort estimation
    canvas_hash: str = None  # Hash of canvas state when threat was generated

class GroqAIClient:
    # Class-level rate limiter shared across all instances
    _rate_limiter = GroqRateLimiter(max_requests_per_minute=8)  # Conservative limit
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "llama3-8b-8192"  # Fast and available model
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def analyze_component_threats(self, component_data: Dict[str, Any], canvas_context: Dict[str, Any] = None) -> List[ThreatSuggestion]:
        """
        Intelligent threat analysis with full canvas awareness and dynamic threat count
        """
        
        # Extract methodology and actual canvas components
        methodology = canvas_context.get('methodology', 'STRIDE') if canvas_context else 'STRIDE'
        canvas_components = canvas_context.get('components', []) if canvas_context else []
        canvas_connections = canvas_context.get('connections', []) if canvas_context else []
        
        print(f"🔍 DEBUG: Component Analysis Request:")
        print(f"   Component: {component_data.get('name', 'unnamed')} ({component_data.get('type', 'unknown')})")
        print(f"   Methodology from request: {methodology}")
        print(f"   Canvas context: {bool(canvas_context)}")
        if canvas_context:
            print(f"   Canvas context keys: {list(canvas_context.keys())}")
        
        # Generate canvas hash for change detection
        canvas_hash = self._generate_canvas_hash(canvas_components, canvas_connections, methodology)
        
        # Get methodology-specific categories
        categories = self._get_methodology_categories(methodology)
        
        # Build comprehensive canvas context
        full_context = self._build_comprehensive_context(component_data, canvas_components, canvas_connections, methodology)
        
        # Determine appropriate threat count based on component complexity
        threat_count = self._calculate_optimal_threat_count(component_data, canvas_components, canvas_connections)
        
        prompt = f"""
You are an expert threat modeling AI with full awareness of the entire system architecture.

COMPLETE SYSTEM CONTEXT:
{full_context}

TARGET COMPONENT ANALYSIS:
- Component: {component_data.get('type', 'unknown')} ({component_data.get('name', 'unnamed')})
- Technology: {component_data.get('technology', 'not specified')}
- Data Handled: {component_data.get('dataTypes', 'unknown')}
- Trust Level: {component_data.get('trustLevel', 'unknown')}
- Connections: {self._get_component_connections(component_data.get('id'), canvas_connections)}

🎯 CRITICAL: METHODOLOGY IS {methodology} - DO NOT USE STRIDE UNLESS SPECIFIED
ANALYZE USING ONLY: {', '.join(categories)}

METHODOLOGY-SPECIFIC REQUIREMENTS:
{self._get_methodology_specific_instructions(methodology)}

INSTRUCTIONS:
1. Consider the ENTIRE system architecture and component relationships
2. Provide {threat_count} most relevant threats using ONLY {methodology} methodology
3. Focus on threats specific to this component's role in the overall system
4. Reference actual component names and connections
5. Use ONLY the {methodology} threat categories: {', '.join(categories)}
6. Include detailed mitigation steps and effort estimation

⚠️ IMPORTANT: Only use threats from {methodology} methodology. Do NOT use STRIDE threats unless methodology is STRIDE.

Return JSON with {threat_count} CONTEXTUAL threats:
{{
  "threats": [
    {{
      "title": "Specific {methodology} threat considering full system context",
      "description": "Detailed description referencing actual components and flows",
      "category": "{categories[0] if categories else 'information_disclosure'}",
      "severity": "Low|Medium|High|Critical",
      "likelihood": "Low|Medium|High", 
      "impact": "Low|Medium|High",
      "mitigation": "High-level mitigation summary",
      "mitigation_steps": ["Step 1: Specific action", "Step 2: Another action", "Step 3: Validation"],
      "tools_required": ["Tool/Technology 1", "Security control 2"],
      "estimated_effort": "Low|Medium|High",
      "confidence": 0.85
    }}
  ]
}}

ONLY use {methodology} methodology threats. Be PRECISE and reference the actual system architecture.
        """
        
        try:
            response = await self._make_request(prompt, max_tokens=800)
            
            # Debug: Log the raw AI response for troubleshooting
            print(f"🔍 DEBUG: AI Response for {methodology} methodology:")
            print(f"   Raw response length: {len(response)} chars")
            print(f"   Response preview: {response[:200]}...")
            
            threats = self._parse_threat_response(response, [component_data.get('id', 'unknown')], methodology)
            
            print(f"   Parsed threats: {len(threats)}")
            for threat in threats:
                print(f"   - {threat.title} | {threat.category}")
            
            # Add canvas hash to each threat for change detection
            for threat in threats:
                if hasattr(threat, 'canvas_hash'):
                    threat.canvas_hash = canvas_hash
                    
            return threats
        except Exception as e:
            print(f"Error analyzing component threats: {e}")
            return []

    def _generate_canvas_hash(self, components: List[Dict], connections: List[Dict], methodology: str) -> str:
        """Generate hash of current canvas state for change detection"""
        canvas_state = {
            'components': sorted([{k: v for k, v in comp.items() if k in ['id', 'type', 'name']} for comp in components], key=lambda x: x.get('id', '')),
            'connections': sorted([{k: v for k, v in conn.items() if k in ['source', 'target', 'protocol']} for conn in connections], key=lambda x: f"{x.get('source', '')}-{x.get('target', '')}"),
            'methodology': methodology
        }
        canvas_json = json.dumps(canvas_state, sort_keys=True)
        return hashlib.md5(canvas_json.encode()).hexdigest()

    def _calculate_optimal_threat_count(self, target_component: Dict, all_components: List[Dict], connections: List[Dict]) -> int:
        """Calculate optimal number of threats based on system complexity"""
        base_count = 2  # Minimum threats
        
        # Add threats based on component complexity
        if target_component.get('type') in ['database', 'external_service', 'api']:
            base_count += 1
        
        # Add threats based on connections
        component_id = target_component.get('id')
        related_connections = [c for c in connections if c.get('source') == component_id or c.get('target') == component_id]
        connection_bonus = min(len(related_connections), 2)  # Max 2 extra for connections
        
        # Add threats based on trust level
        if target_component.get('trustLevel') == 'external':
            base_count += 1
        
        return min(base_count + connection_bonus, 6)  # Cap at 6 threats max

    def _build_comprehensive_context(self, target_component: Dict, components: List[Dict], connections: List[Dict], methodology: str) -> str:
        """Build comprehensive understanding of entire system"""
        context_parts = []
        
        # System overview
        context_parts.append(f"SYSTEM OVERVIEW ({methodology} Analysis):")
        context_parts.append(f"- Total Components: {len(components)}")
        context_parts.append(f"- Total Connections: {len(connections)}")
        
        # Component relationships
        if components:
            component_summary = {}
            for comp in components:
                comp_type = comp.get('type', 'unknown')
                component_summary[comp_type] = component_summary.get(comp_type, 0) + 1
            
            comp_details = ", ".join([f"{count} {ctype}" for ctype, count in component_summary.items()])
            context_parts.append(f"- Component Types: {comp_details}")
        
        # Data flow analysis
        if connections:
            context_parts.append("\nDATA FLOW ARCHITECTURE:")
            flow_details = []
            for conn in connections[:5]:  # Limit to first 5 for context
                source_comp = next((c for c in components if c.get('id') == conn.get('source')), {})
                target_comp = next((c for c in components if c.get('id') == conn.get('target')), {})
                flow_details.append(f"- {source_comp.get('name', 'unknown')} ({source_comp.get('type', '')}) → {target_comp.get('name', 'unknown')} ({target_comp.get('type', '')}) via {conn.get('protocol', 'unknown')}")
            context_parts.extend(flow_details)
        
        # Target component's role in system
        target_id = target_component.get('id')
        target_connections = self._get_component_connections(target_id, connections)
        context_parts.append(f"\nTARGET COMPONENT ROLE:")
        context_parts.append(f"- Connections: {target_connections}")
        
        return "\n".join(context_parts)

    def _get_component_connections(self, component_id: str, connections: List[Dict]) -> str:
        """Get summary of component's connections"""
        if not component_id:
            return "No connections"
            
        incoming = [c for c in connections if c.get('target') == component_id]
        outgoing = [c for c in connections if c.get('source') == component_id]
        
        details = []
        if incoming:
            details.append(f"{len(incoming)} incoming")
        if outgoing:
            details.append(f"{len(outgoing)} outgoing")
            
        return ", ".join(details) if details else "No connections"

    def _get_methodology_categories(self, methodology: str) -> List[str]:
        """Get threat categories for specific methodology"""
        if methodology.upper() == "CIA":
            return ["confidentiality", "integrity", "availability"]
        elif methodology.upper() == "LINDDUN":
            return ["linkability", "identifiability", "non_repudiation", "detectability", "disclosure_of_information", "unawareness", "non_compliance"]
        elif methodology.upper() == "STRIDE":
            return ["spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege"]
        else:  # CUSTOM or unknown
            return ["confidentiality", "integrity", "availability", "spoofing", "tampering"]

    def _get_methodology_specific_instructions(self, methodology: str) -> str:
        """Get methodology-specific instructions for AI threat analysis"""
        methodology_upper = methodology.upper()
        
        if methodology_upper == "CIA":
            return """
🔒 CIA METHODOLOGY REQUIREMENTS:
- CONFIDENTIALITY threats: unauthorized access, data exposure, encryption bypasses
- INTEGRITY threats: data modification, tampering, unauthorized changes  
- AVAILABILITY threats: service disruption, denial of service, resource exhaustion
❌ DO NOT mention: spoofing, elevation of privilege, repudiation (these are STRIDE concepts)
✅ Focus on: data protection, access control, service availability"""

        elif methodology_upper == "LINDDUN":
            return """
🔒 LINDDUN METHODOLOGY REQUIREMENTS:
- LINKABILITY: connecting activities/identities across contexts
- IDENTIFIABILITY: determining identity from data sets
- NON-REPUDIATION: inability to deny actions  
- DETECTABILITY: inferring data subject involvement
- DISCLOSURE OF INFORMATION: unauthorized information release
- UNAWARENESS: lack of knowledge about data processing
- NON-COMPLIANCE: violating privacy regulations
❌ DO NOT mention: spoofing, tampering, elevation of privilege (these are STRIDE concepts)
✅ Focus on: privacy protection, data subject rights, anonymity"""

        elif methodology_upper == "STRIDE":
            return """
🔒 STRIDE METHODOLOGY REQUIREMENTS:
- SPOOFING: identity falsification
- TAMPERING: data/code modification  
- REPUDIATION: denying actions
- INFORMATION DISCLOSURE: unauthorized data access
- DENIAL OF SERVICE: availability attacks
- ELEVATION OF PRIVILEGE: gaining unauthorized access
✅ Use all STRIDE categories as appropriate"""

        else:
            return """
🔒 CUSTOM METHODOLOGY:
- Use a mix of security concepts appropriate for the component
- Focus on confidentiality, integrity, and availability
- Include relevant security controls and mitigations"""

    def _build_component_context(self, target_component: Dict[str, Any], canvas_components: List[Dict], canvas_connections: List[Dict]) -> str:
        """Build actual canvas context for relevant threat analysis"""
        
        context_parts = []
        
        # List actual components on canvas
        if canvas_components:
            component_types = [f"- {comp.get('type', 'unknown')} ({comp.get('name', 'unnamed')})" for comp in canvas_components]
            context_parts.append(f"Components on Canvas:\n" + "\n".join(component_types))
        else:
            context_parts.append("Components on Canvas: Only the target component")
        
        # Find connections involving the target component
        target_id = target_component.get('id')
        relevant_connections = []
        if target_id and canvas_connections:
            for conn in canvas_connections:
                if conn.get('source') == target_id or conn.get('target') == target_id:
                    relevant_connections.append(conn)
        
        if relevant_connections:
            conn_details = []
            for conn in relevant_connections:
                source_comp = next((c for c in canvas_components if c.get('id') == conn.get('source')), {})
                target_comp = next((c for c in canvas_components if c.get('id') == conn.get('target')), {})
                conn_details.append(f"- {source_comp.get('type', 'unknown')} → {target_comp.get('type', 'unknown')} ({conn.get('protocol', 'unknown protocol')})")
            context_parts.append(f"Data Flows:\n" + "\n".join(conn_details))
        else:
            context_parts.append("Data Flows: No connections yet")
        
        return "\n\n".join(context_parts)

    def _build_canvas_summary(self, components: List[Dict], connections: List[Dict]) -> str:
        """Build a summary of the current canvas state"""
        
        if not components:
            return "Canvas is empty - no components added yet."
        
        summary_parts = []
        
        # Component summary
        component_types = {}
        for comp in components:
            comp_type = comp.get('type', 'unknown')
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        comp_summary = ", ".join([f"{count} {ctype}" for ctype, count in component_types.items()])
        summary_parts.append(f"Components: {comp_summary}")
        
        # Connection summary
        if connections:
            summary_parts.append(f"Data flows: {len(connections)} connections between components")
        else:
            summary_parts.append("Data flows: No connections defined yet")
        
        return " | ".join(summary_parts)

    async def get_detailed_mitigation(self, threat_id: str, threat_title: str, component_type: str, canvas_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get comprehensive mitigation details with implementation steps and Jira integration
        """
        
        methodology = canvas_context.get('methodology', 'STRIDE') if canvas_context else 'STRIDE'
        
        prompt = f"""
Provide COMPREHENSIVE mitigation details for this threat:

THREAT: {threat_title}
COMPONENT TYPE: {component_type}
METHODOLOGY: {methodology}

Return detailed JSON with implementation guidance:
{{
  "mitigation": {{
    "summary": "Brief 1-sentence summary",
    "description": "Detailed explanation of the mitigation approach",
    "implementation_steps": [
      "Step 1: Specific technical action with tools/commands",
      "Step 2: Configuration or code changes required", 
      "Step 3: Testing and validation procedures",
      "Step 4: Monitoring and maintenance"
    ],
    "tools_required": [
      "Security tool/technology 1",
      "Framework/library 2", 
      "Monitoring solution 3"
    ],
    "estimated_effort_hours": "2-4|4-8|8-16|16-32|32+",
    "skill_level_required": "Junior|Mid|Senior|Expert",
    "cost_category": "Free|Low ($100-1k)|Medium ($1k-10k)|High ($10k+)",
    "effectiveness_rating": "Low|Medium|High|Critical",
    "implementation_priority": "Low|Medium|High|Critical",
    "jira_task_template": {{
      "summary": "Implement {threat_title} mitigation for {component_type}",
      "description": "Detailed task description with acceptance criteria",
      "acceptance_criteria": [
        "Criteria 1: Measurable outcome",
        "Criteria 2: Security control verification"
      ],
      "labels": ["security", "threat-mitigation", "{methodology.lower()}"],
      "components": ["{component_type}"],
      "epic_link": "Security Hardening"
    }}
  }}
}}

Focus on ACTIONABLE, specific guidance with real implementation details.
        """
        
        try:
            response = await self._make_request(prompt, max_tokens=600)
            mitigation_data = self._parse_json_response(response)
            return mitigation_data.get('mitigation', {})
        except Exception as e:
            print(f"Error getting detailed mitigation: {e}")
            return {}

    async def dismiss_threat_suggestion(self, threat_id: str, component_id: str, reason: str = None) -> bool:
        """
        Mark a threat suggestion as dismissed by user
        """
        # In a real implementation, this would update a database
        # For now, we'll return success
        print(f"Threat {threat_id} dismissed for component {component_id}. Reason: {reason}")
        return True

    async def create_jira_task(self, threat_data: Dict[str, Any], mitigation_data: Dict[str, Any], jira_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Jira task from threat and mitigation data
        """
        
        jira_template = mitigation_data.get('jira_task_template', {})
        
        # Build Jira task payload
        task_payload = {
            "fields": {
                "project": {"key": jira_config.get('project_key', 'SEC')},
                "summary": jira_template.get('summary', f"Security: {threat_data.get('title', 'Unknown threat')}"),
                "description": self._build_jira_description(threat_data, mitigation_data),
                "issuetype": {"name": jira_config.get('issue_type', 'Task')},
                "priority": {"name": self._map_severity_to_priority(threat_data.get('severity', 'Medium'))},
                "labels": jira_template.get('labels', ['security', 'threat-mitigation']),
                "components": [{"name": comp} for comp in jira_template.get('components', [])]
            }
        }
        
        # Add custom fields if configured
        if jira_config.get('epic_link_field'):
            task_payload["fields"][jira_config['epic_link_field']] = jira_template.get('epic_link', 'Security Hardening')
        
        # Simulate Jira API call (in real implementation, use Jira REST API)
        jira_response = {
            "success": True,
            "ticket_id": f"SEC-{hash(threat_data.get('title', ''))%10000}",
            "ticket_url": f"{jira_config.get('base_url', 'https://yourorg.atlassian.net')}/browse/SEC-{hash(threat_data.get('title', ''))%10000}",
            "created_at": "2025-08-12T13:54:00Z"
        }
        
        print(f"Jira task created: {jira_response['ticket_url']}")
        return jira_response

    def _build_jira_description(self, threat_data: Dict[str, Any], mitigation_data: Dict[str, Any]) -> str:
        """Build comprehensive Jira task description"""
        
        description_parts = [
            f"*Threat Overview:*",
            f"Title: {threat_data.get('title', 'Unknown')}",
            f"Severity: {threat_data.get('severity', 'Medium')}",
            f"Category: {threat_data.get('category', 'Unknown')}",
            f"Component(s): {', '.join(threat_data.get('component_ids', []))}",
            "",
            f"*Description:*",
            threat_data.get('description', 'No description available'),
            "",
            f"*Mitigation Approach:*",
            mitigation_data.get('description', 'See implementation steps'),
            "",
            f"*Implementation Steps:*"
        ]
        
        # Add implementation steps
        for i, step in enumerate(mitigation_data.get('implementation_steps', []), 1):
            description_parts.append(f"{i}. {step}")
        
        description_parts.extend([
            "",
            f"*Tools Required:*",
            "* " + "\n* ".join(mitigation_data.get('tools_required', ['TBD'])),
            "",
            f"*Estimated Effort:* {mitigation_data.get('estimated_effort_hours', 'TBD')}",
            f"*Skill Level:* {mitigation_data.get('skill_level_required', 'TBD')}",
            "",
            f"*Acceptance Criteria:*"
        ])
        
        # Add acceptance criteria
        for criteria in mitigation_data.get('jira_task_template', {}).get('acceptance_criteria', ['Mitigation implemented and tested']):
            description_parts.append(f"* {criteria}")
        
        return "\n".join(description_parts)

    def _map_severity_to_priority(self, severity: str) -> str:
        """Map threat severity to Jira priority"""
        mapping = {
            'Critical': 'Highest',
            'High': 'High', 
            'Medium': 'Medium',
            'Low': 'Low'
        }
        return mapping.get(severity, 'Medium')

    async def refresh_threats_for_canvas_change(self, old_canvas_hash: str, new_canvas_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect canvas changes and refresh threat suggestions accordingly
        """
        
        new_canvas_hash = self._generate_canvas_hash(
            new_canvas_context.get('components', []),
            new_canvas_context.get('connections', []),
            new_canvas_context.get('methodology', 'STRIDE')
        )
        
        canvas_changed = old_canvas_hash != new_canvas_hash
        
        refresh_response = {
            "canvas_changed": canvas_changed,
            "old_hash": old_canvas_hash,
            "new_hash": new_canvas_hash,
            "refresh_required": canvas_changed,
            "change_summary": self._analyze_canvas_changes(old_canvas_hash, new_canvas_hash, new_canvas_context) if canvas_changed else None
        }
        
        return refresh_response

    def _analyze_canvas_changes(self, old_hash: str, new_hash: str, new_context: Dict[str, Any]) -> str:
        """Analyze what changed in the canvas"""
        # In a real implementation, you'd store previous canvas state and compare
        # For now, provide a generic change summary
        components_count = len(new_context.get('components', []))
        connections_count = len(new_context.get('connections', []))
        methodology = new_context.get('methodology', 'STRIDE')
        
        return f"Canvas updated: {components_count} components, {connections_count} connections, using {methodology} methodology"

    async def analyze_data_flow_threats(self, flow_data: Dict[str, Any]) -> List[ThreatSuggestion]:
        """
        Analyze threats for data flows between components
        """
        
        prompt = f"""
Analyze this data flow for security threats. Be FAST and PRECISE.

Data Flow:
- From: {flow_data.get('source', 'unknown')} 
- To: {flow_data.get('target', 'unknown')}
- Data Type: {flow_data.get('dataType', 'unknown')}
- Protocol: {flow_data.get('protocol', 'unknown')}
- Encryption: {flow_data.get('encryption', 'unknown')}

Return 2 most critical data flow threats in JSON:
{{
  "threats": [
    {{
      "title": "Threat title",
      "description": "Brief description", 
      "category": "tampering|information_disclosure|denial_of_service",
      "severity": "Low|Medium|High|Critical",
      "likelihood": "Low|Medium|High",
      "impact": "Low|Medium|High", 
      "mitigation": "Specific mitigation",
      "confidence": 0.9
    }}
  ]
}}
        """
        
        try:
            response = await self._make_request(prompt, max_tokens=400)
            flow_id = f"{flow_data.get('source', 'src')}-{flow_data.get('target', 'dst')}"
            return self._parse_threat_response(response, [flow_id])
        except Exception as e:
            print(f"Error analyzing flow threats: {e}")
            return []

    async def analyze_architecture_threats(self, canvas_data: Dict[str, Any]) -> List[ThreatSuggestion]:
        """
        Analyze overall architecture for systemic threats
        """
        
        components = canvas_data.get('components', [])
        connections = canvas_data.get('connections', [])
        
        prompt = f"""
Analyze this system architecture for HIGH-LEVEL security threats.

Architecture Overview:
- Components: {len(components)} ({[c.get('type') for c in components[:5]]})
- Data Flows: {len(connections)} connections
- External Interfaces: {len([c for c in components if c.get('trustLevel') == 'external'])}

Find 3 ARCHITECTURAL threats (not component-specific):
{{
  "threats": [
    {{
      "title": "Architecture-level threat",
      "description": "System-wide security issue",
      "category": "spoofing|tampering|information_disclosure|denial_of_service|elevation_of_privilege",
      "severity": "Medium|High|Critical",
      "likelihood": "Low|Medium|High",
      "impact": "Medium|High",
      "mitigation": "Architectural solution",
      "confidence": 0.8
    }}
  ]
}}
        """
        
        try:
            response = await self._make_request(prompt, max_tokens=600)
            component_ids = [c.get('id', '') for c in components]
            return self._parse_threat_response(response, component_ids)
        except Exception as e:
            print(f"Error analyzing architecture threats: {e}")
            return []

    async def get_mitigation_details(self, threat_title: str, component_type: str) -> Dict[str, Any]:
        """
        Get detailed mitigation steps for a specific threat
        """
        
        prompt = f"""
Provide detailed mitigation for: "{threat_title}" on {component_type}

Return ACTIONABLE steps in JSON:
{{
  "mitigation": {{
    "summary": "Brief mitigation summary",
    "steps": ["Step 1", "Step 2", "Step 3"],
    "tools": ["Tool/Technology 1", "Tool 2"],
    "cost": "Low|Medium|High",
    "effort": "Low|Medium|High",
    "effectiveness": "Medium|High"
  }}
}}
        """
        
        try:
            response = await self._make_request(prompt, max_tokens=300)
            return self._parse_json_response(response)
        except Exception as e:
            print(f"Error getting mitigation details: {e}")
            return {}

    async def ask_threat_question(self, question: str, canvas_context: Dict[str, Any]) -> str:
        """
        Answer threat modeling questions with methodology and canvas awareness
        """
        
        methodology = canvas_context.get('methodology', 'STRIDE')
        canvas_components = canvas_context.get('components', [])
        canvas_connections = canvas_context.get('connections', [])
        
        # Build canvas summary
        canvas_summary = self._build_canvas_summary(canvas_components, canvas_connections)
        
        prompt = f"""
You are a threat modeling expert specializing in {methodology} methodology.

CURRENT CANVAS STATE:
{canvas_summary}

METHODOLOGY: {methodology}

USER QUESTION: {question}

Provide a helpful, specific answer considering:
1. The actual components and connections on the canvas
2. The {methodology} methodology framework  
3. Real-world security best practices

Be concise but actionable. Reference specific components when relevant.
Respond in plain text, not JSON format.
        """
        
        try:
            response = await self._make_request(prompt, max_tokens=300)
            return response.strip()
        except Exception as e:
            print(f"Error answering question: {e}")
            return "Sorry, I couldn't process that question right now."

    async def _make_request(self, prompt: str, max_tokens: int = 500) -> str:
        """Make fast API request to Groq with rate limiting"""
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        # Apply rate limiting before making request
        await self._rate_limiter.acquire()
        print(f"🚦 Rate limit check passed, making API request...")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a fast, expert cybersecurity threat modeling assistant. Be concise and actionable. Only respond with JSON when specifically requested for structured data."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,  # Lower temperature for consistent security analysis
            "stream": False
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=12)  # Increased timeout for rate-limited requests
            ) as response:
                if response.status == 429:
                    print(f"⚠️ Rate limit hit (429), backing off for 30 seconds...")
                    await asyncio.sleep(30)
                    # Retry once after backoff
                    return await self._make_request(prompt, max_tokens)
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Groq API error: {response.status}, {error_text}")
                    
                data = await response.json()
                return data["choices"][0]["message"]["content"]
        except asyncio.TimeoutError:
            raise Exception("Request timeout - Groq API taking too long")
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ Rate limit error caught, backing off...")
                await asyncio.sleep(30)
                # Don't retry again to avoid infinite loop
                raise Exception("Rate limit exceeded - please wait before making more requests")
            raise e

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response that should contain JSON, handling markdown wrapping"""
        
        try:
            # Extract JSON from markdown code blocks if present
            if "```" in response:
                # Find JSON between code blocks
                start = response.find("```")
                if start != -1:
                    # Skip the opening ```
                    start = response.find("\n", start) + 1
                    end = response.find("```", start)
                    if end != -1:
                        response = response[start:end].strip()
            
            # Clean up any remaining markdown or extra text
            response = response.strip()
            if response.startswith("json"):
                response = response[4:].strip()
            
            # Try to find JSON in the response
            json_start = -1
            for i, char in enumerate(response):
                if char in ['{', '[']:
                    json_start = i
                    break
            
            if json_start != -1:
                response = response[json_start:]
            
            # Parse JSON
            return json.loads(response)
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Response was: {response}")
            return {}

    def _map_category_to_enum(self, category_str: str, methodology: str = "STRIDE") -> ThreatCategory:
        """Map AI response category string to proper ThreatCategory enum"""
        category_lower = category_str.lower().strip()
        
        # Direct enum value matching (if AI returns exact enum value)
        try:
            return ThreatCategory(category_lower)
        except ValueError:
            pass
        
        # Methodology-specific mapping
        if methodology.upper() == "STRIDE":
            stride_mapping = {
                "spoofing": ThreatCategory.STRIDE_SPOOFING,
                "tampering": ThreatCategory.STRIDE_TAMPERING,
                "repudiation": ThreatCategory.STRIDE_REPUDIATION,
                "information_disclosure": ThreatCategory.STRIDE_INFORMATION_DISCLOSURE,
                "denial_of_service": ThreatCategory.STRIDE_DENIAL_OF_SERVICE,
                "elevation_of_privilege": ThreatCategory.STRIDE_ELEVATION_OF_PRIVILEGE,
                "dos": ThreatCategory.STRIDE_DENIAL_OF_SERVICE,
                "privilege_escalation": ThreatCategory.STRIDE_ELEVATION_OF_PRIVILEGE
            }
            return stride_mapping.get(category_lower, ThreatCategory.STRIDE_INFORMATION_DISCLOSURE)
            
        elif methodology.upper() == "CIA":
            cia_mapping = {
                "confidentiality": ThreatCategory.CIA_CONFIDENTIALITY,
                "integrity": ThreatCategory.CIA_INTEGRITY,
                "availability": ThreatCategory.CIA_AVAILABILITY
            }
            return cia_mapping.get(category_lower, ThreatCategory.CIA_CONFIDENTIALITY)
            
        elif methodology.upper() == "LINDDUN":
            linddun_mapping = {
                "linkability": ThreatCategory.LINDDUN_LINKABILITY,
                "identifiability": ThreatCategory.LINDDUN_IDENTIFIABILITY,
                "non_repudiation": ThreatCategory.LINDDUN_NON_REPUDIATION,
                "detectability": ThreatCategory.LINDDUN_DETECTABILITY,
                "disclosure_of_information": ThreatCategory.LINDDUN_DISCLOSURE,
                "disclosure": ThreatCategory.LINDDUN_DISCLOSURE,
                "unawareness": ThreatCategory.LINDDUN_UNAWARENESS,
                "non_compliance": ThreatCategory.LINDDUN_NON_COMPLIANCE
            }
            return linddun_mapping.get(category_lower, ThreatCategory.LINDDUN_DISCLOSURE)
        
        # Default fallback
        return ThreatCategory.STRIDE_INFORMATION_DISCLOSURE

    def _parse_threat_response(self, response: str, component_ids: List[str], methodology: str = "STRIDE") -> List[ThreatSuggestion]:
        """Parse AI response into ThreatSuggestion objects with improved JSON handling"""
        
        try:
            print(f"🔍 DEBUG: AI Response for {methodology} methodology:")
            print(f"   Raw response length: {len(response)} chars")
            print(f"   Response preview: {response[:200]}...")
            
            # Extract JSON from markdown code blocks if present
            if "```" in response:
                # Find JSON between code blocks
                start = response.find("```")
                if start != -1:
                    # Skip the opening ```json or ```
                    start = response.find("\n", start) + 1
                    end = response.find("```", start)
                    if end != -1:
                        response = response[start:end].strip()
            
            # Clean up any remaining markdown or extra text
            response = response.strip()
            if response.startswith("json"):
                response = response[4:].strip()
            
            # Try to find JSON in the response
            json_start = -1
            for i, char in enumerate(response):
                if char in ['{', '[']:
                    json_start = i
                    break
            
            if json_start != -1:
                response = response[json_start:]
            
            # NEW: Try to find the END of valid JSON to avoid "extra data" errors
            json_end = -1
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(response):
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char in ['{', '[']:
                        brace_count += 1
                    elif char in ['}', ']']:
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
            
            if json_end != -1:
                response = response[:json_end]
                print(f"   Trimmed to valid JSON ending at position {json_end}")
            
            print(f"   Parsing JSON of length: {len(response)}")
            
            # Parse JSON
            data = json.loads(response)
            print(f"   ✅ JSON parsed successfully")
            
            # Handle both array format and object format
            if isinstance(data, list):
                threats_data = data
            elif isinstance(data, dict):
                threats_data = data.get("threats", [])
            else:
                threats_data = []
            
            threats = []
            
            for i, threat in enumerate(threats_data):
                category_str = threat.get("category", "information_disclosure")
                category = self._map_category_to_enum(category_str, methodology)
                
                threat_obj = ThreatSuggestion(
                    id=f"ai-threat-{hash(threat.get('title', ''))}-{i}",
                    title=threat.get("title", "Unknown Threat"),
                    description=threat.get("description", ""),
                    category=category,
                    severity=threat.get("severity", "Medium"),
                    likelihood=threat.get("likelihood", "Medium"), 
                    impact=threat.get("impact", "Medium"),
                    mitigation=threat.get("mitigation", ""),
                    confidence=threat.get("confidence", 0.7),
                    component_ids=component_ids
                )
                threats.append(threat_obj)
                
            return threats
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error for {methodology}: {e}")
            print(f"   Raw response: {response}")
            print(f"   Parsed threats: 0")
            return []
        except Exception as e:
            print(f"❌ General parsing error for {methodology}: {e}")
            print(f"   Raw response: {response[:500]}...")
            return []

# Singleton instance for fast access
groq_client = None

async def get_groq_client() -> GroqAIClient:
    """Get shared Groq client instance"""
    global groq_client
    if groq_client is None:
        groq_client = GroqAIClient()
    return groq_client

# Convenience functions for real-time use
async def quick_component_analysis(component_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Quick threat analysis for immediate UI feedback"""
    async with GroqAIClient() as client:
        threats = await client.analyze_component_threats(component_data)
        return [
            {
                "id": threat.id,
                "title": threat.title,
                "description": threat.description,
                "severity": threat.severity,
                "category": threat.category.value,
                "mitigation": threat.mitigation,
                "confidence": threat.confidence
            }
            for threat in threats
        ]

async def quick_flow_analysis(flow_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Quick data flow threat analysis"""
    async with GroqAIClient() as client:
        threats = await client.analyze_data_flow_threats(flow_data)
        return [
            {
                "id": threat.id,
                "title": threat.title,
                "description": threat.description,
                "severity": threat.severity,
                "mitigation": threat.mitigation
            }
            for threat in threats
        ]
