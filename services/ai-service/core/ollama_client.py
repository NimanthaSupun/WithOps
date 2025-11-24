"""
Ollama Client for AI-Powered PR Description Generation
Integrates with local Ollama Docker container for generating GitHub PR descriptions
"""
import httpx
import json
import os
from typing import Dict, List, Optional
import asyncio

class OllamaClient:
    """
    Client for interacting with Ollama Docker container
    Generates AI-powered PR descriptions based on code changes
    """
    
    def __init__(self):
        self.base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.default_model = os.getenv('OLLAMA_MODEL', 'llama3.2:latest')
        self.timeout = 60.0  # Increased timeout for AI generation
        
    async def check_health(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/version")
                return response.status_code == 200
        except Exception as e:
            print(f"❌ Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """List available models in Ollama"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [model['name'] for model in data.get('models', [])]
                    return models
                return []
        except Exception as e:
            print(f"❌ Error listing Ollama models: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model if it's not already available"""
        try:
            print(f"📥 Pulling Ollama model: {model_name}")
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes timeout
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name}
                )
                return response.status_code == 200
        except Exception as e:
            print(f"❌ Error pulling model {model_name}: {e}")
            return False
    
    async def generate_pr_description(self, 
                                    title: str,
                                    changes: List[Dict],
                                    workflow_context: str = "",
                                    model: str = None) -> str:
        """
        Generate a comprehensive PR description using AI
        
        Args:
            title: PR title
            changes: List of file changes with diffs
            workflow_context: Context about affected workflows
            model: Ollama model to use (defaults to configured model)
        
        Returns:
            Generated PR description
        """
        model_name = model or self.default_model
        
        # Ensure model is available
        available_models = await self.list_models()
        if not available_models:
            print("🔄 No models found, pulling default model...")
            await self.pull_model(model_name)
        elif model_name not in available_models and f"{model_name}:latest" not in available_models:
            print(f"🔄 Model {model_name} not found, pulling...")
            await self.pull_model(model_name)
        
        # Build context from changes
        change_summary = self._build_change_summary(changes)
        
        # Create AI prompt
        prompt = self._create_pr_prompt(title, change_summary, workflow_context)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "max_tokens": 1000
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    generated_text = data.get('response', '').strip()
                    print(f"✅ Generated PR description using {model_name}")
                    return generated_text
                else:
                    print(f"❌ Ollama API error: {response.status_code}")
                    return self._fallback_description(title, changes)
                    
        except Exception as e:
            print(f"❌ Error generating PR description: {e}")
            return self._fallback_description(title, changes)
    
    async def generate_workflow(self, prompt: str, model: str = None) -> str:
        """
        Generate a GitHub Actions workflow using AI
        
        Args:
            prompt: The workflow generation prompt
            model: Ollama model to use (defaults to configured model)
        
        Returns:
            Generated workflow YAML content
        """
        model_name = model or self.default_model
        
        print(f"🤖 Generating workflow with model: {model_name}")
        print(f"🔍 Prompt preview: {prompt[:200]}...")
        
        # Ensure model is available
        available_models = await self.list_models()
        if not available_models:
            print("🔄 No models found, pulling default model...")
            success = await self.pull_model(model_name)
            if not success:
                print(f"❌ Failed to pull model {model_name}")
                return ""
        elif model_name not in available_models and f"{model_name}:latest" not in available_models:
            print(f"🔄 Model {model_name} not found, pulling...")
            success = await self.pull_model(model_name)
            if not success:
                print(f"❌ Failed to pull model {model_name}")
                return ""
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:  # 2 minutes timeout
                print(f"🚀 Sending request to Ollama at {self.base_url}")
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # Lower for more consistent YAML
                            "top_p": 0.9,
                            "num_predict": 2048,  # Maximum tokens to generate
                            "repeat_penalty": 1.1
                        }
                    }
                )
                
                print(f"📊 Ollama response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    generated_content = result.get('response', '').strip()
                    print(f"✅ Generated {len(generated_content)} characters")
                    print(f"🔍 Generated content preview: {generated_content[:200]}...")
                    return generated_content
                else:
                    print(f"❌ Ollama API error: {response.status_code}")
                    print(f"❌ Response content: {response.text}")
                    return ""
                    
        except httpx.TimeoutException:
            print("⏰ Request timed out - Ollama might be busy")
            return ""
        except httpx.ConnectError:
            print("🔌 Connection error - Is Ollama running?")
            return ""
        except Exception as e:
            print(f"❌ Error generating workflow: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return ""
    

    
    def _build_change_summary(self, changes: List[Dict]) -> str:
        """Build a summary of code changes"""
        if not changes:
            return "No specific changes provided"
        
        summary_parts = []
        
        for change in changes:
            file_path = change.get('file', 'unknown')
            change_type = change.get('type', 'modified')
            additions = change.get('additions', 0)
            deletions = change.get('deletions', 0)
            
            # Extract relevant code snippets
            diff = change.get('diff', '')
            
            summary_parts.append(f"""
File: {file_path}
Type: {change_type}
Changes: +{additions} -{deletions}
Key Changes: {self._extract_key_changes(diff)}
""")
        
        return "\n".join(summary_parts)
    
    def _extract_key_changes(self, diff: str) -> str:
        """Extract key changes from diff"""
        if not diff:
            return "No diff available"
        
        # Look for added/removed lines
        lines = diff.split('\n')
        added_lines = [line[1:].strip() for line in lines if line.startswith('+') and not line.startswith('+++')]
        removed_lines = [line[1:].strip() for line in lines if line.startswith('-') and not line.startswith('---')]
        
        key_changes = []
        if added_lines:
            key_changes.append(f"Added: {', '.join(added_lines[:3])}")
        if removed_lines:
            key_changes.append(f"Removed: {', '.join(removed_lines[:3])}")
        
        return "; ".join(key_changes) if key_changes else "Minor changes"
    
    def _create_pr_prompt(self, title: str, change_summary: str, workflow_context: str) -> str:
        """Create a comprehensive prompt for PR description generation"""
        return f"""
You are a DevSecOps engineer creating a professional GitHub Pull Request description.

PR Title: {title}

Code Changes Summary:
{change_summary}

Workflow Context:
{workflow_context}

Generate a comprehensive PR description that includes:

1. **Overview** - Brief summary of what this PR does
2. **Changes Made** - Detailed list of modifications
3. **Impact** - How this affects the system/workflows
4. **Testing** - What testing was done or should be done
5. **Security Considerations** - Any security implications
6. **Deployment Notes** - Any deployment considerations

Use GitHub markdown formatting with appropriate headers, bullet points, and code blocks where necessary.
Keep it professional, concise, and informative.
Focus on the DevSecOps aspects like security, automation, and CI/CD improvements.
"""
    
    def _fallback_description(self, title: str, changes: List[Dict]) -> str:
        """Fallback description when AI generation fails"""
        file_count = len(changes)
        total_additions = sum(change.get('additions', 0) for change in changes)
        total_deletions = sum(change.get('deletions', 0) for change in changes)
        
        return f"""## Overview

{title}

## Changes Made

- Modified {file_count} file(s)
- Total additions: +{total_additions}
- Total deletions: -{total_deletions}

## Files Changed

{chr(10).join(f"- `{change.get('file', 'unknown')}`" for change in changes)}

## Testing

- [ ] Manual testing completed
- [ ] Automated tests pass
- [ ] Security scan completed

## Deployment Notes

Please review the changes carefully before merging.

---
*This description was generated automatically due to AI service unavailability.*
"""

# Global instance
ollama_client = OllamaClient()
