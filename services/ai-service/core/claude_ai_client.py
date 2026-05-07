"""
Claude AI Client for Advanced Threat Modeling Analysis

This service integrates with Anthropic's Claude API to provide:
- Context-aware security analysis
- Progressive threat modeling
- Visual diagram comprehension
- Document-based architecture analysis
"""

import os
import re
from typing import Dict, List, Any
from anthropic import Anthropic
from datetime import datetime

class ClaudeAIClient:
    def __init__(self):
        """Initialize Claude AI client with API key from environment"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=self.api_key)
        # Using Claude 3 Opus - stable model that should be available
        # If this fails, check your Anthropic API tier/access
        self.model = "claude-3-opus-20240229"
        self.max_tokens = 4000
        
    async def analyze_threats(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive threat analysis using Claude AI
        
        Args:
            request: Analysis request containing components, connections, documents, etc.
            
        Returns:
            Structured analysis response with threats, recommendations, etc.
        """
        try:
            # Build context-aware prompt
            prompt = self._build_context_prompt(request)
            
            # Prepare messages for Claude
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # Add diagram image if provided
            diagram_image = request.get('diagram_image')
            if diagram_image:
                messages[0]["content"].append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": diagram_image
                    }
                })
            
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                temperature=0.3
            )
            
            # Extract and structure response
            analysis_text = response.content[0].text
            methodology = request.get('methodology', 'STRIDE')
            
            # Parse the response into structured sections
            parsed_analysis = self.parse_structured_analysis(analysis_text, methodology)
            
            return {
                "success": True,
                "analysis": analysis_text,
                "analysis_type": request.get('analysis_type', 'comprehensive'),
                "methodology": methodology,
                "structured_analysis": parsed_analysis,
                "model_used": self.model,
                "timestamp": datetime.utcnow().isoformat(),
                "components_analyzed": len(request.get('components', [])),
                "has_document": bool(request.get('document_text')),
                "has_diagram": bool(request.get('diagram_image')),
                "context_used": {
                    "has_diagram": bool(diagram_image),
                    "has_document": bool(request.get('document_text')),
                    "component_count": len(request.get('components', [])),
                    "connection_count": len(request.get('connections', [])),
                    "existing_threats": sum(len(comp.get('threats', [])) for comp in request.get('components', []))
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "analysis": "",
                "analysis_type": request.get('analysis_type', 'comprehensive'),
                "methodology": request.get('methodology', 'STRIDE'),
                "timestamp": datetime.utcnow().isoformat(),
                "components_analyzed": len(request.get('components', [])),
                "has_document": bool(request.get('document_text')),
                "has_diagram": bool(request.get('diagram_image')),
                "error": f"Claude AI analysis failed: {str(e)}"
            }
    
    async def analyze_threat_model(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze threat model - alias for analyze_threats for backward compatibility
        
        Args:
            request: Analysis request containing components, connections, documents, etc.
            
        Returns:
            Structured analysis response with threats, recommendations, etc.
        """
        return await self.analyze_threats(request)
    
    def _get_framework_prompt_template(self, methodology: str) -> str:
        """
        Get framework-specific prompt template
        
        Args:
            methodology: Selected threat modeling framework (STRIDE, CIA, LINDDUN)
            
        Returns:
            Framework-specific analysis prompt
        """
        if methodology == 'STRIDE':
            return """You are an expert cybersecurity analyst specializing in STRIDE threat modeling methodology. 
Please analyze the provided system architecture using the STRIDE framework (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).

STRIDE ANALYSIS APPROACH:
1. Examine each component and connection for STRIDE threats
2. Categorize threats according to STRIDE methodology  
3. Provide specific threat scenarios and attack vectors
4. Focus on practical, implementable security controls
5. Structure analysis per STRIDE category with detailed scenarios

🤝 COLLABORATIVE ANALYSIS MODE:
- If user threats exist: Validate, enhance, and complement existing analysis
- Mark your contributions clearly: 'User Identified: ✓', 'AI Suggested: 🤖', 'Enhanced: ⚡'
- Focus on gaps and missing threats in user's analysis
- Avoid duplicating well-covered threats
- Provide constructive feedback on existing threats

"""
        elif methodology == 'CIA':
            return """You are an expert cybersecurity analyst specializing in CIA Triad threat modeling methodology.
Please analyze the provided system architecture using the CIA Triad framework (Confidentiality, Integrity, Availability).

CIA TRIAD ANALYSIS APPROACH:
1. Examine each component for Confidentiality, Integrity, and Availability threats
2. Categorize all security concerns according to CIA principles
3. Identify data protection requirements and access control needs
4. Focus on data-centric security controls and safeguards
5. Structure analysis per CIA category with specific scenarios

🤝 COLLABORATIVE ANALYSIS MODE:
- If user threats exist: Validate, enhance, and complement existing analysis
- Mark your contributions clearly: 'User Identified: ✓', 'AI Suggested: 🤖', 'Enhanced: ⚡'
- Focus on gaps and missing threats in user's analysis
- Avoid duplicating well-covered threats
- Provide constructive feedback on existing threats

"""
        elif methodology == 'LINDDUN':
            return """You are an expert privacy and cybersecurity analyst specializing in LINDDUN privacy threat modeling methodology.
Please analyze the provided system architecture using the LINDDUN framework (Linkability, Identifiability, Non-repudiation, Detectability, Disclosure of Information, Unawareness, Non-compliance).

LINDDUN ANALYSIS APPROACH:
1. Examine each component for privacy threats according to LINDDUN categories
2. Focus on personal data processing and privacy implications
3. Identify privacy risks and GDPR/privacy regulation compliance issues
4. Provide privacy-by-design recommendations
5. Structure analysis per LINDDUN category with privacy-specific scenarios

🤝 COLLABORATIVE ANALYSIS MODE:
- If user threats exist: Validate, enhance, and complement existing analysis
- Mark your contributions clearly: 'User Identified: ✓', 'AI Suggested: 🤖', 'Enhanced: ⚡'
- Focus on gaps and missing threats in user's analysis
- Avoid duplicating well-covered threats
- Provide constructive feedback on existing threats

"""
        else:
            # Default to STRIDE if unknown methodology
            return self._get_framework_prompt_template('STRIDE')
    
    def _get_framework_output_template(self, methodology: str) -> str:
        """
        Get framework-specific output template
        
        Args:
            methodology: Selected threat modeling framework
            
        Returns:
            Framework-specific output format template
        """
        if methodology == 'STRIDE':
            return """

OUTPUT FORMAT - STRIDE Threat Modeling Template:

## 1. Service Overview
**Service Name:** [Name from architecture]
**Description:** [What does the service do, main purpose]
**Architecture Summary:** [Details description of components and dependencies]
**Assets to Protect:** [Customer data, tokens, configs, secrets, etc.]

## 2. Threat Modeling Scope  
**In-Scope Components:** [List all analyzed components]
**Out-of-Scope Components:** [Components not analyzed]
**Assumptions:** [TLS, network isolation, IAM controls, etc.]

## 3. STRIDE Analysis
### 3.1 Spoofing Identity
**Threat Assessment:** [What can be spoofed: Users, tokens, services, etc.]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🔍 AI Validation & Opinion**
• [For EACH user threat above, provide validation:]
  - ✅ Valid: [If threat is realistic] OR
  - ⚠️ Partially Valid: [What's correct, what needs refinement] OR
  - ❌ Unlikely: [Why this may not apply] OR
  - 💡 Enhancement: [How to improve the threat description]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.2 Tampering with Data
**Threat Assessment:** [Data at rest/in transit vulnerable points]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🔍 AI Validation & Opinion**
• [For EACH user threat above, provide validation:]
  - ✅ Valid: [If threat is realistic] OR
  - ⚠️ Partially Valid: [What's correct, what needs refinement] OR
  - ❌ Unlikely: [Why this may not apply] OR
  - 💡 Enhancement: [How to improve the threat description]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.3 Repudiation (denying actions)
**Threat Assessment:** [What actions might lack accountability]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🔍 AI Validation & Opinion**
• [For EACH user threat above, provide validation:]
  - ✅ Valid: [If threat is realistic] OR
  - ⚠️ Partially Valid: [What's correct, what needs refinement] OR
  - ❌ Unlikely: [Why this may not apply] OR
  - 💡 Enhancement: [How to improve the threat description]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.4 Information Disclosure
**Threat Assessment:** [Sensitive data exposure vectors: API, DB, logs, etc.]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🔍 AI Validation & Opinion**
• [For EACH user threat above, provide validation:]
  - ✅ Valid: [If threat is realistic] OR
  - ⚠️ Partially Valid: [What's correct, what needs refinement] OR
  - ❌ Unlikely: [Why this may not apply] OR
  - 💡 Enhancement: [How to improve the threat description]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.5 Denial of Service
**Threat Assessment:** [Entry points for abuse: Specific attack surfaces]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🔍 AI Validation & Opinion**
• [For EACH user threat above, provide validation:]
  - ✅ Valid: [If threat is realistic] OR
  - ⚠️ Partially Valid: [What's correct, what needs refinement] OR
  - ❌ Unlikely: [Why this may not apply] OR
  - 💡 Enhancement: [How to improve the threat description]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.6 Elevation of Privilege
**Threat Assessment:** [Where privilege escalation could occur]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🔍 AI Validation & Opinion**
• [For EACH user threat above, provide validation:]
  - ✅ Valid: [If threat is realistic] OR
  - ⚠️ Partially Valid: [What's correct, what needs refinement] OR
  - ❌ Unlikely: [Why this may not apply] OR
  - 💡 Enhancement: [How to improve the threat description]

**🤖 AI Suggested Threats**
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.6 Elevation of Privilege
**Threat Assessment:** [Where privilege escalation could occur]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

## 4. Risk Rating
**Methodology:** [DREAD, CVSS, High/Medium/Low]
**Top Risks Identified:**
1. [Risk 1 with severity]
2. [Risk 2 with severity]  
3. [Risk 3 with severity]

## 5. Mitigation Plan
**Short-Term Actions (quick wins):** [Immediate implementations]
**Long-Term Actions (architecture/security roadmap):** [Strategic improvements]


"""
        elif methodology == 'CIA':
            return """

OUTPUT FORMAT - CIA Triad Threat Modeling Template:

## 1. Service Overview
**Service Name:** [Name from architecture]
**Description:** [What does the service do, main purpose]
**Architecture Summary:** [more Details description of components and dependencies]
**Assets to Protect:** [Customer data, financial records, system configurations, etc.]

## 2. Threat Modeling Scope
**In-Scope Components:** [List all analyzed components]
**Out-of-Scope Components:** [Components not analyzed]
**Assumptions:** [TLS, network isolation, access controls, etc.]

## 3. CIA Analysis
### 3.1 Confidentiality Breach
**Threat Assessment:** [Sensitive data exposure points: API endpoints, database fields, logs, backups]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.2 Integrity Violation
**Threat Assessment:** [Data modification vulnerabilities: API tampering, database corruption, file modification]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.3 Availability Disruption
**Threat Assessment:** [Service disruption vectors: DDoS, resource exhaustion, dependency failures]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

## 4. Risk Rating
**Methodology:** [DREAD, CVSS, High/Medium/Low]
**Top Risks Identified:**
1. [Risk 1 with severity]
2. [Risk 2 with severity]
3. [Risk 3 with severity]

## 5. Mitigation Plan
**Short-Term Actions (quick wins):** [Immediate implementations]
**Long-Term Actions (architecture/security roadmap):** [Strategic improvements]


"""
        elif methodology == 'LINDDUN':
            return """

OUTPUT FORMAT - LINDDUN Privacy Threat Modeling Template:

## 1. Service Overview
**Service Name:** [Name from architecture]
**Description:** [What does the service do, main purpose]
**Architecture Summary:** [Details description of components and dependencies]
**Personal Data Processed:** [PII, behavioral data, location, biometrics, etc.]

## 2. Threat Modeling Scope
**In-Scope Components:** [List all analyzed components]
**Out-of-Scope Components:** [Components not analyzed]
**Assumptions:** [GDPR compliance, consent management, data minimization, etc.]

## 3. LINDDUN Analysis
### 3.1 Linkability
**Threat Assessment:** [Data linkage points: Cross-system correlation, behavioral patterns]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.2 Identifiability
**Threat Assessment:** [Re-identification vectors: Unique identifiers, quasi-identifiers, inference]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]
### 3.3 Non-repudiation
**Threat Assessment:** [Accountability challenges: Action attribution, audit trails]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.4 Detectability
**Threat Assessment:** [Presence detection risks: Activity tracking, profiling, surveillance]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.5 Disclosure of Information
**Threat Assessment:** [Privacy leakage points: Data breaches, inference attacks, side channels]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.6 Unawareness
**Threat Assessment:** [Transparency gaps: Hidden data collection, unclear processing]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

### 3.7 Non-compliance
**Threat Assessment:** [Regulatory violation risks: GDPR, CCPA, sector-specific requirements]

**✓ User Identified Threats**
• [List existing user threats here with 'User Identified: ✓' marker]
• [Each threat on separate line with bullet point]

**🤖 AI Suggested Threats**
• [List new AI-identified threats here with 'AI Suggested: 🤖' marker]
• [Each threat on separate line with detailed scenario]

**🛡️ Recommended Mitigations**
• [Specific actionable steps for all threats]
• [Implementation recommendations]

## 4. Privacy Risk Rating
**Methodology:** [Privacy Impact Assessment scale]
**Top Privacy Risks Identified:**
1. [Risk 1 with severity]
2. [Risk 2 with severity]
3. [Risk 3 with severity]

## 5. Privacy Mitigation Plan
**Short-Term Actions:** [Consent fixes, data minimization]
**Long-Term Actions:** [Privacy-by-design, technical controls]


"""
        else:
            # Default to STRIDE template
            return self._get_framework_output_template('STRIDE')
    
    def parse_structured_analysis(self, analysis_text: str, methodology: str) -> Dict[str, Any]:
        """
        Parse AI response into structured sections based on framework
        
        Args:
            analysis_text: Raw AI analysis response
            methodology: Framework used (STRIDE, CIA, LINDDUN)
            
        Returns:
            Structured analysis data with parsed sections
        """
        try:
            if methodology == 'STRIDE':
                return self._parse_stride_analysis(analysis_text)
            elif methodology == 'CIA':
                return self._parse_cia_analysis(analysis_text)
            elif methodology == 'LINDDUN':
                return self._parse_linddun_analysis(analysis_text)
            else:
                # Fallback to basic parsing
                return self._parse_basic_analysis(analysis_text)
        except Exception as e:
            # If parsing fails, return basic structure with raw text
            return {
                "success": False,
                "error": f"Failed to parse analysis: {str(e)}",
                "raw_analysis": analysis_text,
                "methodology": methodology,
                "parsed_sections": {}
            }
    
    def _parse_stride_analysis(self, text: str) -> Dict[str, Any]:
        """Parse STRIDE-specific analysis structure"""
        sections = {}
        
        # Extract service overview
        service_overview = self._extract_section(text, r"## 1\. Service Overview", r"## 2\.")
        if service_overview:
            sections["service_overview"] = {
                "service_name": self._extract_field(service_overview, r"\*\*Service Name:\*\*\s*(.+)"),
                "description": self._extract_field(service_overview, r"\*\*Description:\*\*\s*(.+)"),
                "architecture_summary": self._extract_field(service_overview, r"\*\*Architecture Summary:\*\*\s*(.+)"),
                "assets_to_protect": self._extract_field(service_overview, r"\*\*Assets to Protect:\*\*\s*(.+)")
            }
        
        # Extract threat modeling scope
        scope_section = self._extract_section(text, r"## 2\. Threat Modeling Scope", r"## 3\.")
        if scope_section:
            sections["scope"] = {
                "in_scope": self._extract_field(scope_section, r"\*\*In-Scope Components:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                "out_of_scope": self._extract_field(scope_section, r"\*\*Out-of-Scope Components:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                "assumptions": self._extract_field(scope_section, r"\*\*Assumptions:\*\*\s*(.+?)(?=\*\*|$)", multiline=True)
            }
        
        # Extract STRIDE categories
        stride_categories = ["spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege"]
        stride_patterns = [
            r"### 3\.1 Spoofing Identity",
            r"### 3\.2 Tampering with Data", 
            r"### 3\.3 Repudiation",
            r"### 3\.4 Information Disclosure",
            r"### 3\.5 Denial of Service",
            r"### 3\.6 Elevation of Privilege"
        ]
        
        sections["stride_analysis"] = {}
        sections["threat_categories"] = {}  # For collaborative display
        
        for i, (category, pattern) in enumerate(zip(stride_categories, stride_patterns)):
            next_pattern = stride_patterns[i + 1] if i + 1 < len(stride_patterns) else r"## 4\."
            category_text = self._extract_section(text, pattern, next_pattern)
            
            if category_text:
                # Parse structured threat data
                category_data = {
                    "threat_assessment": self._extract_field(category_text, r"\*\*Threat Assessment:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                    "user_threats": self._extract_field(category_text, r"\*\*✓ User Identified Threats\*\*\s*(.*?)(?=\*\*🔍|$)", multiline=True),
                    "ai_validation": self._extract_field(category_text, r"\*\*🔍 AI Validation & Opinion\*\*\s*(.*?)(?=\*\*🤖|$)", multiline=True),
                    "ai_threats": self._extract_field(category_text, r"\*\*🤖 AI Suggested Threats\*\*\s*(.*?)(?=\*\*🛡️|$)", multiline=True),
                    "mitigations": self._extract_field(category_text, r"\*\*🛡️ Recommended Mitigations\*\*\s*(.*?)(?=\*\*|$)", multiline=True)
                }
                
                sections["stride_analysis"][category] = category_data
                
                # 🤝 COLLABORATIVE THREAT PARSING
                # Extract individual threats with source markers
                threats = self._parse_collaborative_threats(category_text, category)
                
                # Store in threat_categories for frontend display (use category_data directly!)
                sections["threat_categories"][category] = category_data
        
        # Extract risk rating
        risk_section = self._extract_section(text, r"## 4\. Risk Rating", r"## 5\.")
        if risk_section:
            # Extract methodology (optional)
            methodology = self._extract_field(risk_section, r"\*\*Methodology:\*\*\s*(.+?)(?=\n|\*\*|$)", multiline=True)
            
            # Extract top risks with improved pattern
            top_risks_text = self._extract_field(risk_section, r"\*\*Top Risks Identified:\*\*\s*\n?(.*?)(?=\n\n|##|$)", multiline=True)
            top_risks = []
            if top_risks_text:
                # Split by numbered list items
                risk_items = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', top_risks_text, re.DOTALL)
                top_risks = [item.strip() for item in risk_items if item.strip()]
            
            sections["risk_rating"] = {
                "methodology": methodology,
                "top_risks": top_risks
            }
        
        # Extract mitigation plan
        mitigation_section = self._extract_section(text, r"## 5\. Mitigation Plan", r"## 6\.")
        if mitigation_section:
            sections["mitigation_plan"] = {
                "short_term": self._extract_field(mitigation_section, r"\*\*Short-Term Actions.*?:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                "long_term": self._extract_field(mitigation_section, r"\*\*Long-Term Actions.*?:\*\*\s*(.+?)(?=\*\*|$)", multiline=True)
            }
        
        return {
            "success": True,
            "methodology": "STRIDE",
            "parsed_sections": sections,
            "threat_categories": sections.get("threat_categories", {}),  # Return the actual dict, not just keys
            "raw_analysis": text
        }
    
    def _parse_cia_analysis(self, text: str) -> Dict[str, Any]:
        """Parse CIA Triad-specific analysis structure"""
        sections = {}
        
        # Extract service overview
        service_overview = self._extract_section(text, r"## 1\. Service Overview", r"## 2\.")
        if service_overview:
            sections["service_overview"] = {
                "service_name": self._extract_field(service_overview, r"\*\*Service Name:\*\*\s*(.+)"),
                "description": self._extract_field(service_overview, r"\*\*Description:\*\*\s*(.+)"),
                "architecture_summary": self._extract_field(service_overview, r"\*\*Architecture Summary:\*\*\s*(.+)"),
                "assets_to_protect": self._extract_field(service_overview, r"\*\*Assets to Protect:\*\*\s*(.+)")
            }
        
        # Extract scope information
        scope_section = self._extract_section(text, r"## 2\. Threat Modeling Scope", r"## 3\.")
        if scope_section:
            sections["scope"] = {
                "in_scope": self._extract_field(scope_section, r"\*\*In-Scope Components:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                "out_of_scope": self._extract_field(scope_section, r"\*\*Out-of-Scope Components:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                "assumptions": self._extract_field(scope_section, r"\*\*Assumptions:\*\*\s*(.+?)(?=\*\*|$)", multiline=True)
            }
        
        # Extract CIA categories
        cia_categories = ["confidentiality_breach", "integrity_violation", "availability_disruption"]
        cia_patterns = [
            r"### 3\.1 Confidentiality Breach",
            r"### 3\.2 Integrity Violation",
            r"### 3\.3 Availability Disruption"
        ]
        
        sections["cia_analysis"] = {}
        sections["threat_categories"] = {}  # For collaborative display
        
        for i, (category, pattern) in enumerate(zip(cia_categories, cia_patterns)):
            next_pattern = cia_patterns[i + 1] if i + 1 < len(cia_patterns) else r"## 4\."
            category_text = self._extract_section(text, pattern, next_pattern)
            
            if category_text:
                # Parse structured threat data
                category_data = {
                    "threat_assessment": self._extract_field(category_text, r"\*\*Threat Assessment:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                    "user_threats": self._extract_field(category_text, r"\*\*✓ User Identified Threats\*\*\s*(.*?)(?=\*\*🤖|$)", multiline=True),
                    "ai_threats": self._extract_field(category_text, r"\*\*🤖 AI Suggested Threats\*\*\s*(.*?)(?=\*\*🛡️|$)", multiline=True),
                    "mitigations": self._extract_field(category_text, r"\*\*🛡️ Recommended Mitigations\*\*\s*(.*?)(?=\*\*|$)", multiline=True)
                }
                
                sections["cia_analysis"][category] = category_data
                
                # Parse individual threats with source markers
                threats = self._parse_collaborative_threats(category_text, category)
                
                # Store in threat_categories for frontend display (use category_data directly!)
                sections["threat_categories"][category] = category_data
        
        # Extract risk rating
        risk_section = self._extract_section(text, r"## 4\. Risk Rating", r"## 5\.")
        if risk_section:
            # Extract methodology (optional)
            methodology = self._extract_field(risk_section, r"\*\*Methodology:\*\*\s*(.+?)(?=\n|\*\*|$)", multiline=True)
            
            # Extract top risks with improved pattern
            top_risks_text = self._extract_field(risk_section, r"\*\*Top Risks Identified:\*\*\s*\n?(.*?)(?=\n\n|##|$)", multiline=True)
            top_risks = []
            if top_risks_text:
                # Split by numbered list items
                risk_items = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', top_risks_text, re.DOTALL)
                top_risks = [item.strip() for item in risk_items if item.strip()]
            
            sections["risk_rating"] = {
                "methodology": methodology,
                "top_risks": top_risks
            }
        
        return {
            "success": True,
            "methodology": "CIA",
            "parsed_sections": sections,
            "threat_categories": sections.get("threat_categories", {}),  # Return the actual dict, not just keys
            "raw_analysis": text
        }
    
    def _parse_linddun_analysis(self, text: str) -> Dict[str, Any]:
        """Parse LINDDUN-specific analysis structure"""
        sections = {}
        
        # Extract service overview
        service_overview = self._extract_section(text, r"## 1\. Service Overview", r"## 2\.")
        if service_overview:
            sections["service_overview"] = {
                "service_name": self._extract_field(service_overview, r"\*\*Service Name:\*\*\s*(.+)"),
                "description": self._extract_field(service_overview, r"\*\*Description:\*\*\s*(.+)"),
                "architecture_summary": self._extract_field(service_overview, r"\*\*Architecture Summary:\*\*\s*(.+)"),
                "personal_data_processed": self._extract_field(service_overview, r"\*\*Personal Data Processed:\*\*\s*(.+)")
            }
        
        # Extract scope information
        scope_section = self._extract_section(text, r"## 2\. Threat Modeling Scope", r"## 3\.")
        if scope_section:
            sections["scope"] = {
                "in_scope": self._extract_field(scope_section, r"\*\*In-Scope Components:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                "out_of_scope": self._extract_field(scope_section, r"\*\*Out-of-Scope Components:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                "assumptions": self._extract_field(scope_section, r"\*\*Assumptions:\*\*\s*(.+?)(?=\*\*|$)", multiline=True)
            }
        
        # Extract LINDDUN categories
        linddun_categories = ["linkability", "identifiability", "non_repudiation", "detectability", "disclosure_of_information", "unawareness", "non_compliance"]
        linddun_patterns = [
            r"### 3\.1 Linkability",
            r"### 3\.2 Identifiability", 
            r"### 3\.3 Non-repudiation",
            r"### 3\.4 Detectability",
            r"### 3\.5 Disclosure of Information",
            r"### 3\.6 Unawareness",
            r"### 3\.7 Non-compliance"
        ]
        
        sections["linddun_analysis"] = {}
        sections["threat_categories"] = {}  # For collaborative display
        
        for i, (category, pattern) in enumerate(zip(linddun_categories, linddun_patterns)):
            next_pattern = linddun_patterns[i + 1] if i + 1 < len(linddun_patterns) else r"## 4\."
            category_text = self._extract_section(text, pattern, next_pattern)
            
            if category_text:
                # Parse structured threat data
                category_data = {
                    "threat_assessment": self._extract_field(category_text, r"\*\*Threat Assessment:\*\*\s*(.+?)(?=\*\*|$)", multiline=True),
                    "user_threats": self._extract_field(category_text, r"\*\*✓ User Identified Threats\*\*\s*(.*?)(?=\*\*🤖|$)", multiline=True),
                    "ai_threats": self._extract_field(category_text, r"\*\*🤖 AI Suggested Threats\*\*\s*(.*?)(?=\*\*🛡️|$)", multiline=True),
                    "mitigations": self._extract_field(category_text, r"\*\*🛡️ Recommended Mitigations\*\*\s*(.*?)(?=\*\*|$)", multiline=True)
                }
                
                sections["linddun_analysis"][category] = category_data
                
                # Parse individual threats with source markers
                threats = self._parse_collaborative_threats(category_text, category)
                
                # Store in threat_categories for frontend display (use category_data directly!)
                sections["threat_categories"][category] = category_data
        
        # Extract risk rating
        risk_section = self._extract_section(text, r"## 4\. Risk Rating", r"## 5\.")
        if risk_section:
            # Extract methodology (optional)
            methodology = self._extract_field(risk_section, r"\*\*Methodology:\*\*\s*(.+?)(?=\n|\*\*|$)", multiline=True)
            
            # Extract top risks with improved pattern
            top_risks_text = self._extract_field(risk_section, r"\*\*Top Risks Identified:\*\*\s*\n?(.*?)(?=\n\n|##|$)", multiline=True)
            top_risks = []
            if top_risks_text:
                # Split by numbered list items
                risk_items = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', top_risks_text, re.DOTALL)
                top_risks = [item.strip() for item in risk_items if item.strip()]
            
            sections["risk_rating"] = {
                "methodology": methodology,
                "top_risks": top_risks
            }
        
        return {
            "success": True,
            "methodology": "LINDDUN",
            "parsed_sections": sections,
            "threat_categories": sections.get("threat_categories", {}),  # Return the actual dict, not just keys
            "raw_analysis": text
        }
    
    def _parse_basic_analysis(self, text: str) -> Dict[str, Any]:
        """Basic parsing for unknown methodologies"""
        return {
            "success": True,
            "methodology": "basic",
            "parsed_sections": {
                "raw_content": text
            },
            "threat_categories": [],
            "raw_analysis": text
        }
    
    def _extract_section(self, text: str, start_pattern: str, end_pattern: str) -> str:
        """Extract text between two regex patterns"""
        try:
            match = re.search(f"{start_pattern}(.*?)(?={end_pattern}|$)", text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""
        except Exception:
            return ""
    
    def _extract_field(self, text: str, pattern: str, multiline: bool = False) -> str:
        """Extract a specific field using regex"""
        try:
            flags = re.DOTALL | re.IGNORECASE if multiline else re.IGNORECASE
            match = re.search(pattern, text, flags)
            return match.group(1).strip() if match else ""
        except Exception:
            return ""
    
    def _extract_list_items(self, text: str, pattern: str) -> List[str]:
        """Extract numbered list items"""
        try:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                items_text = match.group(1)
                items = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', items_text, re.DOTALL)
                return [item.strip() for item in items]
            return []
        except Exception:
            return []
    
    def _build_context_prompt(self, request: Dict[str, Any]) -> str:
        """
        Build comprehensive context-aware prompt for collaborative threat analysis
        
        Args:
            request: Analysis request with components, documents, user threat context, etc.
            
        Returns:
            Structured prompt with all relevant context including user threats
        """
        components = request.get('components', [])
        connections = request.get('connections', [])
        document_text = request.get('document_text', '')
        requirements = request.get('requirements', '')
        methodology = request.get('methodology', 'STRIDE')
        user_threat_context = request.get('user_threat_context')
        
        # Get framework-specific prompt template
        prompt = self._get_framework_prompt_template(methodology)
        
        # 🤝 COLLABORATIVE THREAT ANALYSIS SECTION
        # Add user threat context for intelligent collaboration
        if user_threat_context and user_threat_context.get('total_threats', 0) > 0:
            print(f"🤝 DEBUG: Found user threat context with {user_threat_context['total_threats']} threats")
            print(f"🎯 DEBUG: Threat categories: {list(user_threat_context.get('threats_by_category', {}).keys())}")
            
            prompt += "\n\n🛡️ EXISTING USER THREAT ANALYSIS (COLLABORATIVE MODE)\n"
            prompt += f"The user has already identified {user_threat_context['total_threats']} threats using {user_threat_context['methodology']} methodology.\n"
            
            # Add threats by category
            threats_by_category = user_threat_context.get('threats_by_category', {})
            if threats_by_category:
                prompt += "\nEXISTING THREATS BY CATEGORY:\n"
                for category, category_threats in threats_by_category.items():
                    prompt += f"\n{category} ({len(category_threats)} threats):\n"
                    for threat in category_threats:
                        prompt += f"  • {threat['title']} (Component: {threat['componentName']})\n"
                        prompt += f"    Severity: {threat['severity']} | Risk: {threat['riskLevel']}\n"
                        if threat.get('description'):
                            prompt += f"    Description: {threat['description'][:100]}{'...' if len(threat['description']) > 100 else ''}\n"
                        if threat.get('mitigation'):
                            prompt += f"    Mitigation: {threat['mitigation'][:100]}{'...' if len(threat['mitigation']) > 100 else ''}\n"
            
            # Add analysis gaps
            analysis_notes = user_threat_context.get('analysis_notes', {})
            if analysis_notes.get('gaps_to_analyze'):
                prompt += f"\nCATEGORIES WITH NO USER THREATS (FOCUS HERE): {', '.join(analysis_notes['gaps_to_analyze'])}\n"
            
            if analysis_notes.get('components_without_threats', 0) > 0:
                prompt += f"\nCOMPONENTS WITHOUT THREATS: {analysis_notes['components_without_threats']} components need analysis\n"
            
            # Collaborative analysis instructions
            prompt += "\n🎯 COLLABORATIVE ANALYSIS INSTRUCTIONS:\n"
            prompt += "1. VALIDATE existing user threats - are they accurate and well-described?\n"
            prompt += "2. IDENTIFY GAPS - what threats are missing from user's analysis?\n"
            prompt += "3. AVOID DUPLICATES - don't repeat threats the user already identified\n"
            prompt += "4. FOCUS ON UNCOVERED AREAS - prioritize categories with no user threats\n"
            prompt += "5. ENHANCE EXISTING - suggest improvements to user threat descriptions/mitigations\n"
            prompt += "6. PROVIDE COMPLEMENTARY ANALYSIS - add value to user's work\n"
            
            prompt += "\n📋 MANDATORY OUTPUT FORMAT:\n"
            prompt += "- Use the exact template structure with ✓, 🤖, and 🛡️ section headers\n"
            prompt += "- List user threats under '**✓ User Identified Threats**' with bullet points\n"
            prompt += "- List new AI threats under '**🤖 AI Suggested Threats**' with bullet points\n"
            prompt += "- List mitigations under '**🛡️ Recommended Mitigations**' with bullet points\n"
            prompt += "- Use '• ' (bullet + space) for each threat/mitigation item\n"
            prompt += "- DO NOT use other markers like 'User Identified: ✓' within the content\n"
            
        else:
            prompt += "\n\n📝 FRESH THREAT ANALYSIS\n"
            prompt += "No existing user threats found. Provide comprehensive threat analysis.\n"

        # Legacy threat context (keep for backward compatibility)
        existing_threats = []
        for component in components:
            comp_threats = component.get('threats', [])
            if comp_threats:
                for threat in comp_threats:
                    existing_threats.append({
                        'component': component.get('name', 'Unknown'),
                        'threat': threat
                    })
        
        if existing_threats and not user_threat_context:
            # Fallback to legacy format if no structured context
            prompt += "\nLEGACY THREAT CONTEXT:\n"
            for item in existing_threats:
                prompt += f"- Component '{item['component']}': {item['threat']}\n"
        
        # Add system architecture
        if components:
            prompt += "\nSYSTEM ARCHITECTURE:\n"
            prompt += "Components:\n"
            for comp in components:
                prompt += f"- {comp.get('name', 'Unknown')}: {comp.get('type', 'Unknown type')}\n"
                if comp.get('description'):
                    prompt += f"  Description: {comp['description']}\n"
                if comp.get('technologies'):
                    prompt += f"  Technologies: {', '.join(comp['technologies'])}\n"
        
        # Add connections
        if connections:
            prompt += "\nConnections/Data Flows:\n"
            for conn in connections:
                source = conn.get('source', 'Unknown')
                target = conn.get('target', 'Unknown')
                protocol = conn.get('protocol', 'Unknown protocol')
                prompt += f"- {source} → {target} (Protocol: {protocol})\n"
                if conn.get('data'):
                    prompt += f"  Data: {conn['data']}\n"
        
        # Add document context if available
        if document_text:
            prompt += f"\nADDITIONAL CONTEXT FROM UPLOADED DOCUMENT:\n{document_text[:2000]}"
            if len(document_text) > 2000:
                prompt += "\n... (document truncated for analysis)"
        
        # Add requirements if specified
        if requirements:
            prompt += f"\nSPECIFIC REQUIREMENTS:\n{requirements}\n"
        
        # Add framework-specific output format
        prompt += self._get_framework_output_template(methodology)
        
        return prompt

    async def analyze_progressive_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform progressive threat analysis with iterative refinement
        
        This method performs analysis in stages:
        1. Initial component-level analysis
        2. Connection/flow analysis
        3. Integration analysis
        4. Final comprehensive review
        
        Args:
            request: Analysis request with full context
            
        Returns:
            Progressive analysis results with detailed insights
        """
        try:
            stages = []
            
            # Stage 1: Component Analysis
            component_request = {
                **request,
                'analysis_focus': 'components'
            }
            component_analysis = await self.analyze_threats(component_request)
            stages.append({
                'stage': 'component_analysis',
                'result': component_analysis
            })
            
            # Stage 2: Connection Analysis (if connections exist)
            if request.get('connections'):
                connection_request = {
                    **request,
                    'analysis_focus': 'connections',
                    'previous_analysis': component_analysis.get('analysis', '')
                }
                connection_analysis = await self.analyze_threats(connection_request)
                stages.append({
                    'stage': 'connection_analysis',
                    'result': connection_analysis
                })
            
            # Stage 3: Integration Analysis
            integration_request = {
                **request,
                'analysis_focus': 'integration',
                'previous_stages': stages
            }
            final_analysis = await self.analyze_threats(integration_request)
            stages.append({
                'stage': 'integration_analysis',
                'result': final_analysis
            })
            
            return {
                "success": True,
                "progressive_analysis": stages,
                "final_analysis": final_analysis,
                "model_used": self.model,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Progressive analysis failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _parse_collaborative_threats(self, category_text: str, category: str) -> List[Dict[str, Any]]:
        """
        Parse individual threats from category text with source markers
        
        Args:
            category_text: Text for this threat category
            category: Category name (e.g., "Spoofing")
            
        Returns:
            List of threat objects with source markers
        """
        threats = []
        
        try:
            # Extract threat sections using improved patterns
            user_threats_section = self._extract_field(category_text, r"\*\*✓ User Identified Threats\*\*\s*(.*?)(?=\*\*🤖|$)", multiline=True)
            ai_threats_section = self._extract_field(category_text, r"\*\*🤖 AI Suggested Threats\*\*\s*(.*?)(?=\*\*🛡️|$)", multiline=True)
            mitigations_section = self._extract_field(category_text, r"\*\*🛡️ Recommended Mitigations\*\*\s*(.*?)(?=\*\*|$)", multiline=True)
            
            # Parse user identified threats
            if user_threats_section:
                user_threat_items = self._extract_threat_items(user_threats_section)
                for threat_item in user_threat_items:
                    threats.append({
                        'title': threat_item,
                        'source': 'user',
                        'category': category,
                        'description': f'User identified threat: {threat_item}',
                        'mitigation': '',
                        'section': 'user_identified'
                    })
            
            # Parse AI suggested threats
            if ai_threats_section:
                ai_threat_items = self._extract_threat_items(ai_threats_section)
                for threat_item in ai_threat_items:
                    threats.append({
                        'title': threat_item,
                        'source': 'ai',
                        'category': category,
                        'description': f'AI suggested threat: {threat_item}',
                        'mitigation': '',
                        'section': 'ai_suggested'
                    })
            
            # Parse recommended mitigations
            if mitigations_section:
                mitigation_items = self._extract_threat_items(mitigations_section)
                # Associate mitigations with threats or create general mitigation entry
                if threats:
                    # Distribute mitigations among threats
                    for i, mitigation in enumerate(mitigation_items):
                        if i < len(threats):
                            threats[i]['mitigation'] = mitigation
                        else:
                            # Create additional mitigation-only entries
                            threats.append({
                                'title': f'General {category} Mitigation',
                                'source': 'mitigation',
                                'category': category,
                                'description': '',
                                'mitigation': mitigation,
                                'section': 'mitigations'
                            })
                else:
                    # No threats found, create mitigation entries
                    for mitigation in mitigation_items:
                        threats.append({
                            'title': f'{category} Security Control',
                            'source': 'mitigation',
                            'category': category,
                            'description': '',
                            'mitigation': mitigation,
                            'section': 'mitigations'
                        })
            
            # Fallback: Legacy parsing for older format
            if not threats:
                threats = self._parse_legacy_threats(category_text, category)
            
            return threats
            
        except Exception:
            # Return empty list if parsing fails
            return []
    
    def _extract_threat_items(self, section_text: str) -> List[str]:
        """
        Extract individual threat items from a section using bullet points
        
        Args:
            section_text: Text containing bullet point list
            
        Returns:
            List of individual threat items
        """
        items = []
        lines = section_text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for bullet points (• or -)
            if line.startswith('• ') or line.startswith('- '):
                item = line[2:].strip()
                # Clean any remaining markers
                item = re.sub(r'(User Identified: ✓|AI Suggested: 🤖|Enhanced: ⚡)', '', item).strip()
                if item and item not in items:  # Avoid duplicates
                    items.append(item)
        
        return items
    
    def _parse_legacy_threats(self, category_text: str, category: str) -> List[Dict[str, Any]]:
        """
        Parse threats using legacy format for backward compatibility
        
        Args:
            category_text: Text for this threat category
            category: Category name
            
        Returns:
            List of threat objects in legacy format
        """
        threats = []
        
        # Look for various legacy patterns
        scenarios_text = self._extract_field(category_text, r"\*\*Possible Scenarios:\*\*\s*(.+?)(?=\*\*|$)", multiline=True)
        mitigations_text = self._extract_field(category_text, r"\*\*Mitigations / Recommendations:\*\*\s*(.+?)(?=\*\*|$)", multiline=True)
        
        # Check for data points like "Data linkage points:"
        data_points = self._extract_field(category_text, r"Data linkage points:\s*(.+?)(?=Possible Scenarios|Mitigations|$)", multiline=True)
        
        if scenarios_text or data_points:
            # Create a general threat entry for this category
            threat_description = data_points or scenarios_text
            threats.append({
                'title': f'{category} Analysis',
                'source': 'ai',
                'category': category,
                'description': threat_description[:300] + '...' if len(threat_description) > 300 else threat_description,
                'mitigation': mitigations_text[:300] + '...' if mitigations_text and len(mitigations_text) > 300 else mitigations_text or '',
                'section': 'legacy'
            })
        
        return threats


# Initialize claude_client on import, but handle missing API key gracefully
try:
    claude_client = ClaudeAIClient()
except ValueError as e:
    # API key not set - claude_client will be None until properly configured
    claude_client = None
    print(f"⚠️  Claude AI client not initialized: {e}")
    print("💡 Set ANTHROPIC_API_KEY environment variable to enable Claude AI features")