"""
AI-Powered PR Description Generation API
Uses Ollama to generate comprehensive GitHub PR descriptions
Also includes Claude AI for advanced threat modeling analysis
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import logging
import json
import yaml
from core.ollama_client import ollama_client
from core.claude_ai_client import claude_client

# Set up logging
logger = logging.getLogger(__name__)

print("🔍 DEBUG: AI routes module loaded successfully")
print(f"🔍 DEBUG: OllamaClient initialized: {ollama_client}")

router = APIRouter(prefix="/api/ai", tags=["AI"])

print("🔍 DEBUG: AI router created with prefix /api/ai")

class FileChange(BaseModel):
    file: str
    type: str = "modified"  # added, modified, deleted
    additions: int = 0
    deletions: int = 0
    diff: str = ""

class PRDescriptionRequest(BaseModel):
    title: str
    changes: List[FileChange]
    workflow_context: Optional[str] = ""
    model: Optional[str] = None

class PRDescriptionResponse(BaseModel):
    success: bool
    description: str
    model_used: str
    generation_time: float
    message: str

@router.get("/health")
async def check_ai_health():
    """Check if Ollama AI service is available"""
    try:
        is_healthy = await ollama_client.check_health()
        available_models = await ollama_client.list_models()
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "ollama_url": ollama_client.base_url,
            "available_models": available_models,
            "default_model": ollama_client.default_model
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify AI routes are working"""
    return {"message": "AI routes are working!", "timestamp": "2025-07-11T20:22:00Z"}

@router.post("/test-post")
async def test_post_endpoint(data: dict):
    """Simple test POST endpoint to verify POST is working"""
    return {"received": data, "message": "POST endpoint working!"}

@router.post("/debug-pydantic")
async def debug_pydantic_endpoint(request: PRDescriptionRequest):
    """Debug endpoint to test Pydantic model validation"""
    try:
        logger.info(f"🔍 DEBUG: Pydantic validation successful!")
        logger.info(f"🔍 DEBUG: Title: {request.title}")
        logger.info(f"🔍 DEBUG: Changes count: {len(request.changes)}")
        logger.info(f"🔍 DEBUG: First change: {request.changes[0] if request.changes else 'None'}")
        
        return {
            "success": True,
            "message": "Pydantic model validation successful",
            "received_title": request.title,
            "changes_count": len(request.changes),
            "workflow_context": request.workflow_context or "None provided"
        }
        
    except Exception as e:
        logger.error(f"🔍 DEBUG: Pydantic validation failed: {e}")
        import traceback
        logger.error(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-pr-description", response_model=PRDescriptionResponse)
async def generate_pr_description(request: PRDescriptionRequest):
    """
    Generate an AI-powered PR description based on code changes
    
    This endpoint uses Ollama to generate comprehensive PR descriptions
    that include overview, changes, impact, testing, and security considerations.
    """
    print("🔍 DEBUG: Endpoint function called!")
    print(f"🔍 DEBUG: Request type: {type(request)}")
    logger.info("🔍 DEBUG: PR description endpoint called!")
    
    try:
        import time
        start_time = time.time()
        
        print(f"🔍 DEBUG: Inside try block - Title: {request.title}")
        print(f"🔍 DEBUG: Changes count: {len(request.changes)}")
        
        logger.info(f"⭐ Starting PR description generation for: {request.title}")
        logger.info(f"⭐ Changes: {len(request.changes)} files")
        
        # Test ollama_client access
        print(f"🔍 DEBUG: Ollama client base_url: {ollama_client.base_url}")
        print(f"🔍 DEBUG: Ollama client default_model: {ollama_client.default_model}")
        
        # Check if Ollama is available
        print("🔍 DEBUG: Checking Ollama health...")
        health_check = await ollama_client.check_health()
        print(f"🔍 DEBUG: Health check result: {health_check}")
        
        if not health_check:
            raise HTTPException(
                status_code=503, 
                detail="AI service (Ollama) is not available. Please ensure Ollama Docker container is running."
            )
        
        print("🔍 DEBUG: About to call generate_pr_description...")
        # Generate PR description
        description = await ollama_client.generate_pr_description(
            title=request.title,
            changes=[change.model_dump() for change in request.changes],
            workflow_context=request.workflow_context or "",
            model=request.model
        )
        
        generation_time = time.time() - start_time
        model_used = request.model or ollama_client.default_model
        
        logger.info(f"PR description generated in {generation_time:.2f}s using {model_used}")
        
        return PRDescriptionResponse(
            success=True,
            description=description,
            model_used=model_used,
            generation_time=generation_time,
            message="PR description generated successfully"
        )
        
    except HTTPException as he:
        print(f"🔍 DEBUG: HTTPException caught: {he}")
        raise
    except Exception as e:
        print(f"🔍 DEBUG: General exception caught: {e}")
        print(f"🔍 DEBUG: Exception type: {type(e)}")
        import traceback
        print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        logger.error(f"Failed to generate PR description: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PR description: {str(e)}")

# Workflow Generation Models
class WorkflowGenerationRequest(BaseModel):
    prompt: str
    workflowType: str = "general"
    context: Dict = {}

class WorkflowGenerationResponse(BaseModel):
    success: bool
    workflowName: str = ""
    workflowContent: str = ""
    description: str = ""
    triggers: List[str] = []
    error: str = ""

@router.post("/generate-workflow")
async def generate_workflow(request: WorkflowGenerationRequest):
    """
    Generate a GitHub Actions workflow using AI
    """
    try:
        print(f"🔍 DEBUG: Workflow generation requested - Type: {request.workflowType}")
        print(f"🔍 DEBUG: Prompt: {request.prompt}")
        
        # Validate input
        if not request.prompt.strip():
            print("🔍 DEBUG: Empty prompt provided")
            return WorkflowGenerationResponse(
                success=False,
                error="Prompt cannot be empty"
            )
        
        # Try AI generation first
        try:
            print("🔍 DEBUG: Attempting AI generation...")
            is_healthy = await ollama_client.check_health()
            
            if is_healthy:
                prompt = build_workflow_generation_prompt(request)
                print(f"🔍 DEBUG: Using AI with prompt length: {len(prompt)}")
                
                ai_response = await ollama_client.generate_workflow(
                    prompt=prompt,
                    model="llama3.2:latest"
                )
                
                if ai_response and ai_response.strip():
                    print("🔍 DEBUG: AI response received, parsing...")
                    print(f"🔍 DEBUG: Raw response length: {len(ai_response)}")
                    print(f"🔍 DEBUG: Raw response preview: {ai_response[:200]}...")
                    
                    # Try to parse AI response as JSON first, then as raw text
                    workflow_data = parse_ai_workflow_response(ai_response, request)
                    if workflow_data:
                        print("🔍 DEBUG: AI generation successful!")
                        return WorkflowGenerationResponse(
                            success=True,
                            workflowName=workflow_data["name"],
                            workflowContent=workflow_data["content"],
                            description=workflow_data["description"] + " (AI Generated)",
                            triggers=workflow_data["triggers"]
                        )
                    else:
                        print("🔍 DEBUG: Failed to parse AI response, trying raw parsing...")
                        # Try to extract workflow from raw response
                        workflow_data = extract_workflow_from_raw_response(ai_response, request)
                        if workflow_data:
                            print("🔍 DEBUG: Raw parsing successful!")
                            return WorkflowGenerationResponse(
                                success=True,
                                workflowName=workflow_data["name"],
                                workflowContent=workflow_data["content"],
                                description=workflow_data["description"] + " (AI Generated)",
                                triggers=workflow_data["triggers"]
                            )
                        else:
                            print("🔍 DEBUG: Both parsing methods failed, using fallback...")
                else:
                    print("🔍 DEBUG: Empty AI response, using fallback...")
            else:
                print("🔍 DEBUG: Ollama not healthy, using fallback...")
                
        except Exception as ai_error:
            print(f"🔍 DEBUG: AI generation error: {ai_error}, using fallback...")
            import traceback
            print(f"🔍 DEBUG: AI error traceback: {traceback.format_exc()}")
        
        # Fallback to intelligent template generation
        print("🔍 DEBUG: Using intelligent fallback generation...")
        # fallback_data = generate_intelligent_fallback(request)
        
        # print(f"🔍 DEBUG: Fallback workflow generated: {fallback_data['name']}")
        
        # return WorkflowGenerationResponse(
        #     success=True,
        #     workflowName=fallback_data["name"],
        #     workflowContent=fallback_data["content"],
        #     description=fallback_data["description"] + " (Template-based)",
        #     triggers=fallback_data["triggers"]
        # )
        
    except Exception as e:
        print(f"🔍 DEBUG: Exception in workflow generation: {e}")
        import traceback
        print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        return WorkflowGenerationResponse(
            success=False,
            error=f"Failed to generate workflow: {str(e)}"
        )

def build_workflow_generation_prompt(request: WorkflowGenerationRequest) -> str:
    """
    Build a comprehensive prompt for AI workflow generation
    """
    workflow_templates = {
        "ci-cd": "continuous integration and deployment",
        "testing": "automated testing and quality assurance", 
        "security": "security scanning and vulnerability checks",
        "docker": "Docker container building and deployment",
        "npm": "Node.js/NPM package management and publishing",
        "python": "Python application testing and deployment",
        "nodejs": "Node.js application CI/CD pipeline",
        "deployment": "application deployment automation",
        "general": "general purpose automation"
    }
    
    workflow_description = workflow_templates.get(request.workflowType, "general purpose automation")
    
    prompt = f"""Create a complete GitHub Actions workflow YAML file for {workflow_description}.

Request: {request.prompt}

Generate a production-ready GitHub Actions workflow that includes:
- Complete YAML structure starting with 'name:'
- Appropriate triggers (push, pull_request, etc.)
- Proper job definitions with steps
- Use latest action versions (@v4, @v3)
- Include error handling and best practices
- Add useful comments

IMPORTANT: Generate the complete YAML workflow content. Start with 'name:' and include all necessary sections (on, jobs, steps, etc.). Do not include explanatory text before or after - only the YAML content.

Generate the complete workflow YAML now:"""

    return prompt

def parse_workflow_response(response: str, request: WorkflowGenerationRequest) -> Dict:
    """
    Parse the AI response and extract workflow data
    """
    try:
        # Try to parse as JSON first
        if response.strip().startswith('{'):
            data = json.loads(response.strip())
            return {
                "name": data.get("name", f"{request.workflowType}-workflow"),
                "content": data.get("content", ""),
                "description": data.get("description", "AI-generated workflow"),
                "triggers": data.get("triggers", ["push"])
            }
    except json.JSONDecodeError:
        pass
    
    # Fallback: Generate basic workflow

def parse_ai_workflow_response(ai_response: str, request: WorkflowGenerationRequest) -> Optional[Dict]:
    """
    Parse AI response to extract workflow YAML and metadata
    """
    try:
        # First try to parse as JSON (if AI returns structured response)
        if ai_response.strip().startswith('{'):
            try:
                data = json.loads(ai_response.strip())
                if all(key in data for key in ["name", "content"]):
                    return {
                        "name": data.get("name", f"{request.workflowType}-workflow"),
                        "content": data.get("content", ""),
                        "description": data.get("description", "AI-generated workflow"),
                        "triggers": data.get("triggers", ["push"])
                    }
            except json.JSONDecodeError:
                pass
        
        # Try to extract workflow from raw text response
        return extract_workflow_from_raw_response(ai_response, request)
        
    except Exception as e:
        print(f"🔍 DEBUG: Error parsing AI response: {e}")
        return None

def extract_workflow_from_raw_response(ai_response: str, request: WorkflowGenerationRequest) -> Optional[Dict]:
    """
    Extract workflow content from raw AI response text
    """
    try:
        lines = ai_response.split('\n')
        yaml_start = -1
        yaml_end = len(lines)
        workflow_name = f"{request.workflowType}-workflow"
        
        # Look for the actual YAML content
        # Skip any introductory text and find where the YAML starts
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            
            # Look for YAML start patterns
            if (stripped_line.startswith('name:') or 
                (stripped_line.startswith('```yaml') or stripped_line == '```')):
                
                if stripped_line.startswith('```'):
                    # Skip the markdown code block marker and find the actual YAML
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith('name:'):
                            yaml_start = j
                            break
                else:
                    yaml_start = i
                    # Extract workflow name if present
                    name_match = stripped_line.split('name:')
                    if len(name_match) > 1:
                        potential_name = name_match[1].strip().strip('"').strip("'")
                        if potential_name:
                            workflow_name = potential_name
                break
        
        if yaml_start >= 0:
            # Find end of YAML content
            for i in range(yaml_start + 1, len(lines)):
                line = lines[i].strip()
                # Stop at closing code block or when we hit explanatory text
                if (line == '```' or 
                    line.startswith('This workflow') or 
                    line.startswith('The above') or
                    line.startswith('Note:') or
                    (line == '' and i > yaml_start + 15 and 
                     all(l.strip() == '' for l in lines[i:i+3]))):  # Multiple empty lines
                    yaml_end = i
                    break
            
            yaml_content = '\n'.join(lines[yaml_start:yaml_end]).strip()
            
            # Remove any trailing explanation text that might have been included
            yaml_lines = yaml_content.split('\n')
            cleaned_lines = []
            
            for line in yaml_lines:
                stripped = line.strip()
                # Stop if we hit explanatory text
                if (stripped.startswith('This workflow') or 
                    stripped.startswith('The above') or
                    stripped.startswith('Note:') or
                    stripped.startswith('Explanation:')):
                    break
                cleaned_lines.append(line)
            
            yaml_content = '\n'.join(cleaned_lines).strip()
            
            # Validate that we have meaningful YAML content
            if len(yaml_content) < 50:  # Too short to be a real workflow
                print(f"🔍 DEBUG: Content too short ({len(yaml_content)} chars), treating as invalid")
                return None
            
            # Try to validate YAML structure
            try:
                import yaml
                parsed = yaml.safe_load(yaml_content)
                if parsed and isinstance(parsed, dict):
                    # Extract workflow metadata
                    actual_name = parsed.get('name', workflow_name)
                    
                    triggers = []
                    if 'on' in parsed:
                        if isinstance(parsed['on'], dict):
                            triggers = list(parsed['on'].keys())
                        elif isinstance(parsed['on'], list):
                            triggers = parsed['on']
                        elif isinstance(parsed['on'], str):
                            triggers = [parsed['on']]
                    
                    print(f"🔍 DEBUG: Successfully parsed workflow: {actual_name}")
                    return {
                        "name": actual_name,
                        "content": yaml_content,
                        "description": f"AI-generated {request.workflowType} workflow",
                        "triggers": triggers or ["push"]
                    }
                else:
                    print(f"🔍 DEBUG: YAML parsed but not a dict: {type(parsed)}")
                    
            except yaml.YAMLError as ye:
                print(f"🔍 DEBUG: YAML validation failed: {ye}")
                # Return raw content if it looks like it could be YAML
                if 'name:' in yaml_content and 'jobs:' in yaml_content:
                    print("🔍 DEBUG: Returning raw content despite YAML error")
                    return {
                        "name": workflow_name,
                        "content": yaml_content,
                        "description": f"AI-generated {request.workflowType} workflow (raw)",
                        "triggers": ["push"]
                    }
        
        print("🔍 DEBUG: No valid YAML content found in response")
        return None
        
    except Exception as e:
        print(f"🔍 DEBUG: Error extracting workflow from raw response: {e}")
        import traceback
        print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        return None



# TODO:-  =============================================================================
# TODO:-   CLAUDE AI THREAT MODELING ENDPOINTS
# TODO:-  =============================================================================

class ThreatModelComponent(BaseModel):
    id: str
    type: str
    name: str
    user_label: Optional[str] = None
    position: Dict[str, float]
    size: Dict[str, float]
    properties: Optional[Dict] = {}

class ThreatModelConnection(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = ""

class ClaudeAnalysisRequest(BaseModel):
    """Request model for Claude AI threat analysis"""
    # Core data
    components: List[ThreatModelComponent] = []
    connections: List[ThreatModelConnection] = []
    methodology: str = "STRIDE"
    
    # Optional context
    document_text: Optional[str] = ""
    diagram_image: Optional[str] = ""  # Base64 encoded image
    analysis_type: str = "comprehensive"  # document_only, partial, comprehensive
    user_threat_context: Optional[Dict] = None  # User's existing threats for collaborative analysis
    
    # Model metadata
    model_id: str
    model_name: str

class ClaudeAnalysisResponse(BaseModel):
    """Response model for Claude AI analysis"""
    success: bool
    analysis: Optional[str] = ""
    analysis_type: str
    methodology: str
    structured_analysis: Optional[dict] = None  # ✅ ADD THIS FIELD!
    timestamp: str
    components_analyzed: int
    has_document: bool
    has_diagram: bool
    error: Optional[str] = None

@router.post("/claude/analyze-threats", response_model=ClaudeAnalysisResponse)
async def analyze_threats_with_claude(request: ClaudeAnalysisRequest):
    """
    Advanced threat modeling analysis using Claude AI
    
    This endpoint provides:
    - Context-aware security analysis based on user-labeled components
    - Progressive analysis as users build their threat models
    - Document + diagram comprehension for comprehensive insights
    - Technology-specific threat identification
    """
    try:
        logger.info(f"🤖 Starting Claude threat analysis for model: {request.model_name}")
        logger.info(f"📊 Components: {len(request.components)}, Connections: {len(request.connections)}")
        logger.info(f"📋 Has document: {bool(request.document_text)}, Has diagram: {bool(request.diagram_image)}")
        
        if request.document_text:
            logger.info(f"📄 Document content length: {len(request.document_text)} characters")
            logger.info(f"📄 Document preview: {request.document_text[:200]}...")
        
        # Prepare analysis request
        analysis_request = {
            "components": [comp.dict() for comp in request.components],
            "connections": [conn.dict() for conn in request.connections],
            "methodology": request.methodology,
            "document_text": request.document_text,
            "diagram_image": request.diagram_image,
            "analysis_type": request.analysis_type,
            "user_threat_context": request.user_threat_context
        }
        
        # Log user threat context for debugging
        if request.user_threat_context:
            logger.info(f"🛡️ User threat context: {request.user_threat_context.get('total_threats', 0)} existing threats")
            logger.info(f"🎯 Threat categories: {list(request.user_threat_context.get('threats_by_category', {}).keys())}")
        
        # Call Claude AI
        result = await claude_client.analyze_threat_model(analysis_request)
        
        if result["success"]:
            logger.info("✅ Claude analysis completed successfully")
            return ClaudeAnalysisResponse(**result)
        else:
            logger.error(f"❌ Claude analysis failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))
            
    except Exception as e:
        logger.error(f"❌ Error in Claude threat analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/claude/review-threat")
async def review_individual_threat(request: dict):
    """Handle individual threat reviews for AI learning"""
    try:
        logger.info(f"📝 Received threat review: {request.get('review', {}).get('threat_title', 'Unknown')}")
        logger.info(f"✅ Review result: {request.get('review', {}).get('is_valid', False)}")
        
        # For now, just log the review. In the future, this could:
        # - Store in database for AI training
        # - Update AI model confidence scores
        # - Trigger re-analysis if needed
        
        return {
            "success": True,
            "message": "Threat review recorded for AI learning",
            "review_id": f"review_{request.get('review', {}).get('threat_id', 'unknown')}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling threat review: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/claude/progressive-analysis")
async def progressive_threat_analysis(
    previous_analysis: Optional[str] = None,
    new_components: List[ThreatModelComponent] = [],
    methodology: str = "STRIDE"
):
    """
    Progressive threat analysis as user builds their model step by step
    Focuses on incremental changes and new threats
    """
    try:
        logger.info(f"🔄 Progressive analysis for {len(new_components)} new components")
        
        result = await claude_client.analyze_progressive_context(
            previous_analysis=previous_analysis,
            new_components=[comp.dict() for comp in new_components],
            methodology=methodology
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Progressive analysis failed"))
            
    except Exception as e:
        logger.error(f"❌ Error in progressive analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Progressive analysis failed: {str(e)}")

@router.get("/claude/health")
async def claude_health_check():
    """Check Claude AI service health"""
    try:
        # Simple test call to verify API key and connectivity
        test_request = {
            "components": [{"id": "test", "type": "process", "user_label": "Test Process", "name": "Test"}],
            "connections": [],
            "methodology": "STRIDE",
            "analysis_type": "partial"
        }
        
        result = await claude_client.analyze_threat_model(test_request)
        
        return {
            "service": "Claude AI",
            "status": "healthy" if result["success"] else "error",
            "model": claude_client.model,
            "api_configured": bool(claude_client.api_key),
            "timestamp": result["timestamp"]
        }
        
    except Exception as e:
        return {
            "service": "Claude AI", 
            "status": "error",
            "error": str(e),
            "api_configured": bool(claude_client.api_key)
        }

class PDFExportRequest(BaseModel):
    analysis: dict
    model_info: dict
    export_date: str
    diagram_image: Optional[str] = None

@router.options("/claude/export-pdf")
async def export_pdf_options():
    """Handle preflight OPTIONS request for PDF export"""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Access-Control-Max-Age": "3600"
        }
    )

@router.post("/claude/export-pdf")
async def export_ai_analysis_pdf(request: PDFExportRequest):
    """Export Claude AI analysis results to PDF"""
    from fastapi.responses import Response
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.units import inch
    import reportlab
    import io
    import base64
    from datetime import datetime
    
    try:
        logger.info("📄 Generating PDF export for AI analysis")
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=inch, leftMargin=inch, 
                              topMargin=inch, bottomMargin=inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkred
        )
        
        # Story for PDF content
        story = []
        
        # Title page
        title = f"AI Threat Analysis Report"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 20))
        
        # Model Information
        model_info = request.model_info
        story.append(Paragraph("Model Information", heading_style))
        story.append(Paragraph(f"<b>Name:</b> {model_info.get('name', 'Untitled')}", styles['Normal']))
        story.append(Paragraph(f"<b>Description:</b> {model_info.get('description', 'No description')}", styles['Normal']))
        story.append(Paragraph(f"<b>Methodology:</b> {model_info.get('methodology', 'Unknown')}", styles['Normal']))
        story.append(Paragraph(f"<b>Components:</b> {model_info.get('components_count', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Connections:</b> {model_info.get('connections_count', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Threats:</b> {model_info.get('threats_count', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Export Date:</b> {datetime.fromisoformat(request.export_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Add diagram if available
        if request.diagram_image:
            try:
                story.append(Paragraph("Architecture Diagram", heading_style))
                # Decode base64 image
                image_data = base64.b64decode(request.diagram_image)
                image_buffer = io.BytesIO(image_data)
                
                # Create image object with proper sizing
                img = Image(image_buffer, width=6*inch, height=4*inch)
                story.append(img)
                story.append(Spacer(1, 20))
            except Exception as img_error:
                logger.warning(f"⚠️ Could not include diagram image: {img_error}")
        
        story.append(PageBreak())
        
        # AI Analysis Results
        analysis = request.analysis
        story.append(Paragraph("Claude AI Analysis", title_style))
        story.append(Spacer(1, 10))
        
        # Analysis metadata
        story.append(Paragraph("Analysis Overview", heading_style))
        story.append(Paragraph(f"<b>Analysis Type:</b> {analysis.get('analysis_type', 'Unknown')}", styles['Normal']))
        story.append(Paragraph(f"<b>Methodology:</b> {analysis.get('methodology', 'Unknown')}", styles['Normal']))
        story.append(Paragraph(f"<b>Components Analyzed:</b> {analysis.get('components_analyzed', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Has Document:</b> {'Yes' if analysis.get('has_document') else 'No'}", styles['Normal']))
        story.append(Paragraph(f"<b>Has Diagram:</b> {'Yes' if analysis.get('has_diagram') else 'No'}", styles['Normal']))
        story.append(Paragraph(f"<b>Analysis Date:</b> {datetime.fromisoformat(analysis.get('timestamp', '').replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Main analysis content
        story.append(Paragraph("Security Analysis", heading_style))
        analysis_text = analysis.get('analysis', 'No analysis available')
        
        # Split analysis text into paragraphs for better formatting
        paragraphs = analysis_text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Clean up the paragraph text for PDF
                clean_para = para.strip().replace('\n', ' ')
                if clean_para.startswith('##'):
                    # Convert markdown headers to PDF headings
                    clean_para = clean_para.replace('##', '').strip()
                    story.append(Paragraph(clean_para, heading_style))
                elif clean_para.startswith('**') and clean_para.endswith('**'):
                    # Convert bold text
                    clean_para = f"<b>{clean_para[2:-2]}</b>"
                    story.append(Paragraph(clean_para, styles['Normal']))
                else:
                    story.append(Paragraph(clean_para, styles['Normal']))
                story.append(Spacer(1, 6))
        
        # Footer information
        story.append(Spacer(1, 30))
        story.append(Paragraph("Report Generated by WithOps DevSecOps Platform", styles['Italic']))
        story.append(Paragraph("Powered by Anthropic Claude AI", styles['Italic']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create response
        pdf_content = buffer.getvalue()
        filename = f"{model_info.get('name', 'threat_model').replace(' ', '_')}_AI_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        logger.info(f"✅ PDF export generated successfully: {filename}")
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Access-Control-Max-Age": "3600",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ PDF export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


@router.post("/claude/export-pdf-url")
async def export_ai_analysis_pdf_url(request: PDFExportRequest):
    """Export Claude AI analysis results to PDF as base64 URL (alternative for CORS issues)"""
    from fastapi.responses import Response
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.units import inch
    import io
    import base64
    from datetime import datetime
    
    try:
        logger.info("📄 Generating PDF export as base64 URL for AI analysis")
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=inch, leftMargin=inch, 
                              topMargin=inch, bottomMargin=inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkred
        )
        
        # Story for PDF content
        story = []
        
        # Title page
        title = f"AI Threat Analysis Report"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 20))
        
        # Model Information
        model_info = request.model_info
        story.append(Paragraph("Model Information", heading_style))
        story.append(Paragraph(f"<b>Name:</b> {model_info.get('name', 'Untitled')}", styles['Normal']))
        story.append(Paragraph(f"<b>Description:</b> {model_info.get('description', 'No description')}", styles['Normal']))
        story.append(Paragraph(f"<b>Methodology:</b> {model_info.get('methodology', 'Unknown')}", styles['Normal']))
        story.append(Paragraph(f"<b>Components:</b> {model_info.get('components_count', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Connections:</b> {model_info.get('connections_count', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Threats:</b> {model_info.get('threats_count', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Export Date:</b> {datetime.fromisoformat(request.export_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Add diagram if available
        if request.diagram_image:
            try:
                story.append(Paragraph("Architecture Diagram", heading_style))
                # Decode base64 image
                image_data = base64.b64decode(request.diagram_image)
                image_buffer = io.BytesIO(image_data)
                
                # Create image object with proper sizing
                img = Image(image_buffer, width=6*inch, height=4*inch)
                story.append(img)
                story.append(Spacer(1, 20))
            except Exception as img_error:
                logger.warning(f"⚠️ Could not include diagram image: {img_error}")
        
        story.append(PageBreak())
        
        # AI Analysis Results
        analysis = request.analysis
        story.append(Paragraph("Claude AI Analysis", title_style))
        story.append(Spacer(1, 10))
        
        # Analysis metadata
        story.append(Paragraph("Analysis Overview", heading_style))
        story.append(Paragraph(f"<b>Analysis Type:</b> {analysis.get('analysis_type', 'Unknown')}", styles['Normal']))
        story.append(Paragraph(f"<b>Methodology:</b> {analysis.get('methodology', 'Unknown')}", styles['Normal']))
        story.append(Paragraph(f"<b>Components Analyzed:</b> {analysis.get('components_analyzed', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Has Document:</b> {'Yes' if analysis.get('has_document') else 'No'}", styles['Normal']))
        story.append(Paragraph(f"<b>Has Diagram:</b> {'Yes' if analysis.get('has_diagram') else 'No'}", styles['Normal']))
        story.append(Paragraph(f"<b>Analysis Date:</b> {datetime.fromisoformat(analysis.get('timestamp', '').replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Main analysis content
        story.append(Paragraph("Security Analysis", heading_style))
        analysis_text = analysis.get('analysis', 'No analysis available')
        
        # Split analysis text into paragraphs for better formatting
        paragraphs = analysis_text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Clean up the paragraph text for PDF
                clean_para = para.strip().replace('\n', ' ')
                if clean_para.startswith('##'):
                    # Convert markdown headers to PDF headings
                    clean_para = clean_para.replace('##', '').strip()
                    story.append(Paragraph(clean_para, heading_style))
                elif clean_para.startswith('**') and clean_para.endswith('**'):
                    # Convert bold text
                    clean_para = f"<b>{clean_para[2:-2]}</b>"
                    story.append(Paragraph(clean_para, styles['Normal']))
                else:
                    story.append(Paragraph(clean_para, styles['Normal']))
                story.append(Spacer(1, 6))
        
        # Footer information
        story.append(Spacer(1, 30))
        story.append(Paragraph("Report Generated by WithOps DevSecOps Platform", styles['Italic']))
        story.append(Paragraph("Powered by Anthropic Claude AI", styles['Italic']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Encode PDF as base64
        pdf_content = buffer.getvalue()
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        filename = f"{model_info.get('name', 'threat_model').replace(' ', '_')}_AI_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        logger.info(f"✅ PDF export generated successfully as base64: {filename}")
        
        # Return JSON response with PDF data
        return {
            "success": True,
            "filename": filename,
            "pdf_data": pdf_base64,
            "download_url": f"data:application/pdf;base64,{pdf_base64}"
        }
        
    except Exception as e:
        logger.error(f"❌ PDF export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")
