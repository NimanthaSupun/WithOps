"""
Pull Request Creator for GitHub Actions Updates
Handles creating pull requests to update outdated GitHub Actions
"""
import yaml
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio

class PRCreator:
    """
    Creates pull requests to update outdated GitHub Actions
    """
    
    def __init__(self, github_client, installation_id: int):
        self.github_client = github_client
        self.installation_id = installation_id
        self.app_name = "withops-devsecops"
        
    async def create_single_action_update_pr(
        self,
        org_name: str,
        repo_name: str,
        workflow_path: str,
        action_name: str,
        current_version: str,
        latest_version: str
    ) -> Dict[str, Any]:
        """
        Create a pull request to update a single outdated GitHub Action.
        """
        try:
            print(f"🔧 Creating PR to update {action_name} from {current_version} to {latest_version}")
            
            # Get the workflow file content
            workflow_content = await self._get_workflow_content(org_name, repo_name, workflow_path)
            if not workflow_content:
                return {
                    "success": False,
                    "error": f"Unable to access workflow file at {workflow_path}. This could be due to: 1) File doesn't exist, 2) Repository doesn't exist, 3) GitHub App not installed on the repository, or 4) Authentication failure. Please ensure the GitHub App is properly installed and has access to the repository."
                }
            
            # Update the action version in the workflow
            updated_content = self._update_action_version(
                workflow_content, 
                action_name, 
                current_version, 
                latest_version
            )
            
            if updated_content == workflow_content:
                return {
                    "success": False,
                    "error": f"No changes detected for {action_name}@{current_version}. The action was not found in the workflow file, or it may already be at the target version. Please verify the action name and version in the workflow file."
                }
            
            # Create branch name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            branch_name = f"{self.app_name}/update-{action_name.replace('/', '-')}-{timestamp}"
            
            # Create PR title and description
            pr_title = f"🔧 Update {action_name} to {latest_version}"
            pr_description = await self._generate_pr_description(
                action_name, current_version, latest_version, [action_name]
            )
            
            # Create the pull request
            result = await self._create_github_pr(
                org_name=org_name,
                repo_name=repo_name,
                branch_name=branch_name,
                pr_title=pr_title,
                pr_description=pr_description,
                workflow_path=workflow_path,
                updated_content=updated_content
            )
            
            return result
            
        except Exception as e:
            print(f"Error creating single action update PR: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_bulk_action_update_pr(
        self,
        org_name: str,
        repo_name: str,
        workflow_path: str,
        actions: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Create a pull request to update multiple outdated GitHub Actions in a single workflow.
        """
        try:
            print(f"🔧 Creating bulk PR to update {len(actions)} actions")
            
            # Get the workflow file content
            workflow_content = await self._get_workflow_content(org_name, repo_name, workflow_path)
            if not workflow_content:
                return {
                    "success": False,
                    "error": f"Unable to access workflow file at {workflow_path}. This could be due to: 1) File doesn't exist, 2) Repository doesn't exist, 3) GitHub App not installed on the repository, or 4) Authentication failure. Please ensure the GitHub App is properly installed and has access to the repository."
                }
            
            # Update all actions in the workflow
            updated_content = workflow_content
            updated_actions = []
            
            for action in actions:
                action_name = action["action_name"]
                current_version = action["current_version"]
                latest_version = action["latest_version"]
                
                new_content = self._update_action_version(
                    updated_content,
                    action_name,
                    current_version,
                    latest_version
                )
                
                if new_content != updated_content:
                    updated_content = new_content
                    updated_actions.append({
                        "action_name": action_name,
                        "current_version": current_version,
                        "latest_version": latest_version
                    })
            
            if not updated_actions:
                return {
                    "success": False,
                    "error": "No changes detected for any actions"
                }
            
            # Create branch name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            branch_name = f"{self.app_name}/update-actions-{timestamp}"
            
            # Create PR title and description
            pr_title = f"🔧 Update {len(updated_actions)} GitHub Actions"
            pr_description = await self._generate_bulk_pr_description(updated_actions)
            
            # Create the pull request
            result = await self._create_github_pr(
                org_name=org_name,
                repo_name=repo_name,
                branch_name=branch_name,
                pr_title=pr_title,
                pr_description=pr_description,
                workflow_path=workflow_path,
                updated_content=updated_content
            )
            
            if result["success"]:
                result["updated_actions"] = updated_actions
            
            return result
            
        except Exception as e:
            print(f"Error creating bulk action update PR: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_workflow_content(self, org_name: str, repo_name: str, workflow_path: str) -> Optional[str]:
        """
        Get the content of a workflow file from GitHub.
        """
        try:
            print(f"🔍 DEBUG: Getting workflow content for {org_name}/{repo_name}/{workflow_path}")
            
            # Use the existing GitHub client to get file content
            response = await self.github_client.get_file_content(
                installation_id=self.installation_id,
                owner=org_name,
                repo=repo_name,
                path=workflow_path
            )
            
            print(f"🔍 DEBUG: GitHub client response: {response}")
            
            if response and "content" in response:
                content = response["content"]
                print(f"🔍 DEBUG: Workflow content length: {len(content)} chars")
                print(f"🔍 DEBUG: First 200 chars: {content[:200]}")
                return content
            
            print(f"❌ No content found in response")
            return None
            
        except Exception as e:
            print(f"Error getting workflow content: {str(e)}")
            return None
    
    def _update_action_version(self, workflow_content: str, action_name: str, current_version: str, latest_version: str) -> str:
        """
        Update the version of a specific action in the workflow YAML content.
        """
        try:
            print(f"🔍 DEBUG: Updating action {action_name} from {current_version} to {latest_version}")
            print(f"🔍 DEBUG: Workflow content preview (first 500 chars):")
            print(workflow_content[:500])
            print(f"🔍 DEBUG: Looking for pattern: {action_name}@{current_version}")
            
            # Handle different action reference formats
            patterns = [
                # Standard format: action_name@current_version
                rf"(\s+uses:\s+['\"]?{re.escape(action_name)}@){re.escape(current_version)}(['\"]?)",
                # With quotes: 'action_name@current_version'
                rf"(\s+uses:\s+['\"]){re.escape(action_name)}@{re.escape(current_version)}(['\"])",
                # Without quotes in uses field
                rf"(\s+uses:\s+){re.escape(action_name)}@{re.escape(current_version)}(\s|$)",
            ]
            
            updated_content = workflow_content
            
            for i, pattern in enumerate(patterns):
                print(f"🔍 DEBUG: Trying pattern {i+1}: {pattern}")
                matches = re.findall(pattern, updated_content, re.MULTILINE)
                print(f"🔍 DEBUG: Found {len(matches)} matches for pattern {i+1}")
                
                if matches:
                    updated_content = re.sub(
                        pattern,
                        rf"\g<1>{latest_version}\g<2>",
                        updated_content,
                        flags=re.MULTILINE
                    )
                    print(f"✅ Updated {action_name} from {current_version} to {latest_version}")
                    break
            
            if updated_content == workflow_content:
                print(f"❌ No changes detected for {action_name}@{current_version}")
                print(f"🔍 DEBUG: Searching for any occurrence of {action_name}:")
                simple_search = re.findall(rf"{re.escape(action_name)}@\w+", workflow_content)
                print(f"🔍 DEBUG: Found action references: {simple_search}")
            
            return updated_content
            
        except Exception as e:
            print(f"Error updating action version: {str(e)}")
            return workflow_content
    
    async def _generate_pr_description(self, action_name: str, current_version: str, latest_version: str, actions: List[str]) -> str:
        """
        Generate a PR description for the action update.
        """
        try:
            # Try to use AI helper if available
            from core.ai_helper import AIHelper
            ai_helper = AIHelper()
            
            description = await ai_helper.generate_pr_description(
                action_name=action_name,
                current_version=current_version,
                latest_version=latest_version
            )
            
            return description
            
        except Exception as e:
            print(f"AI description generation failed, using fallback: {str(e)}")
            # Fallback to manual description
            return f"""## 🔧 Update {action_name}

This PR updates the GitHub Action `{action_name}` from version `{current_version}` to `{latest_version}`.

### Changes
- ⬆️ Updated `{action_name}` to latest version `{latest_version}`
- 🔒 Ensures security updates and bug fixes are applied
- 📦 Maintains compatibility with existing workflow

### Benefits
- 🛡️ Security improvements
- 🐛 Bug fixes from recent releases
- 🚀 Performance enhancements
- 📋 Latest features and capabilities

### Testing
- [ ] Verify workflow still functions correctly
- [ ] Check for any breaking changes in the action
- [ ] Ensure all existing functionality is preserved

---
*This PR was automatically generated by WithOps DevSecOps Platform*
*Review the changes and merge when ready*"""

    async def _generate_bulk_pr_description(self, actions: List[Dict[str, str]]) -> str:
        """
        Generate a PR description for bulk action updates.
        """
        action_list = "\n".join([
            f"- `{action['action_name']}`: {action['current_version']} → {action['latest_version']}"
            for action in actions
        ])
        
        return f"""## 🔧 Update {len(actions)} GitHub Actions

This PR updates multiple GitHub Actions to their latest versions for improved security and functionality.

### Updated Actions
{action_list}

### Benefits
- 🛡️ Security improvements across all actions
- 🐛 Bug fixes from recent releases
- 🚀 Performance enhancements
- 📋 Access to latest features and capabilities

### Testing
- [ ] Verify workflow still functions correctly
- [ ] Check for any breaking changes in the actions
- [ ] Ensure all existing functionality is preserved
- [ ] Test the workflow with the updated actions

---
*This PR was automatically generated by WithOps DevSecOps Platform*
*Review the changes and merge when ready*"""

    async def _create_github_pr(
        self,
        org_name: str,
        repo_name: str,
        branch_name: str,
        pr_title: str,
        pr_description: str,
        workflow_path: str,
        updated_content: str
    ) -> Dict[str, Any]:
        """
        Create the actual GitHub pull request.
        """
        try:
            # Get the default branch
            repo_info = await self.github_client.get_repository(
                installation_id=self.installation_id,
                owner=org_name,
                repo=repo_name
            )
            
            default_branch = repo_info.get("default_branch", "main")
            
            # Create a new branch
            branch_result = await self.github_client.create_branch(
                installation_id=self.installation_id,
                owner=org_name,
                repo=repo_name,
                branch_name=branch_name,
                from_branch=default_branch
            )
            
            if not branch_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to create branch: {branch_result.get('error', 'Unknown error')}"
                }
            
            # Update the workflow file
            commit_result = await self.github_client.update_file(
                installation_id=self.installation_id,
                owner=org_name,
                repo=repo_name,
                path=workflow_path,
                content=updated_content,
                message=f"🔧 {pr_title}",
                branch=branch_name
            )
            
            if not commit_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to update file: {commit_result.get('error', 'Unknown error')}"
                }
            
            # Create the pull request
            pr_result = await self.github_client.create_pull_request(
                installation_id=self.installation_id,
                owner=org_name,
                repo=repo_name,
                title=pr_title,
                body=pr_description,
                head=branch_name,
                base=default_branch
            )
            
            if pr_result.get("success"):
                return {
                    "success": True,
                    "pr_number": pr_result.get("pr_number"),
                    "pr_title": pr_title,
                    "pr_url": pr_result.get("pr_url"),
                    "branch_name": branch_name
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create PR: {pr_result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            print(f"Error creating GitHub PR: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_workflow_update_pr(
        self,
        org_name: str,
        repo_name: str,
        workflow_path: str,
        new_content: str,
        pr_title: str,
        pr_body: str
    ) -> Dict[str, Any]:
        """
        Create a pull request with updated workflow content from Canvas Workflow Builder.
        """
        try:
            print(f"🎨 Creating Canvas Workflow Builder PR for {workflow_path}")
            
            # Generate branch name
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"canvas-workflow-update-{timestamp}"
            
            # Use the existing _create_github_pr method which handles everything
            result = await self._create_github_pr(
                org_name=org_name,
                repo_name=repo_name,
                branch_name=branch_name,
                pr_title=pr_title,
                pr_description=pr_body,
                workflow_path=workflow_path,
                updated_content=new_content
            )
            
            return result
                
        except Exception as e:
            print(f"❌ Error creating Canvas workflow PR: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create pull request: {str(e)}"
            }
    
    async def _get_default_branch(self, org_name: str, repo_name: str) -> str:
        """
        Get the default branch name for a repository.
        """
        try:
            repo_info = await self.github_client.get_repository(
                installation_id=self.installation_id,
                owner=org_name,
                repo=repo_name
            )
            
            return repo_info.get("default_branch", "main")
        except Exception as e:
            print(f"❌ Error getting default branch for {org_name}/{repo_name}: {e}")
            return "main"  # Fallback to main if unable to get default branch
    
    async def _create_branch(self, org_name: str, repo_name: str, branch_name: str, from_branch: str) -> bool:
        """
        Create a new branch in the repository.
        """
        try:
            branch_result = await self.github_client.create_branch(
                installation_id=self.installation_id,
                owner=org_name,
                repo=repo_name,
                branch_name=branch_name,
                from_branch=from_branch
            )
            
            if not branch_result.get("success"):
                print(f"❌ Failed to create branch {branch_name}: {branch_result.get('error', 'Unknown error')}")
                return False
            
            print(f"✅ Created branch {branch_name} from {from_branch}")
            return True
        except Exception as e:
            print(f"❌ Error creating branch {branch_name}: {e}")
            return False
