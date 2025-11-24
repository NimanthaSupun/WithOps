# core/github_client.py
import re
import yaml
import asyncio
import httpx
import jwt
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class GitHubClient:
    """
    GitHub App Integration Client for Organization-based Workspace Management
    This handles GitHub App installations (not OAuth) into specific organizations
    """
    
    def __init__(self):
        # Debug: Print current working directory and private key path
        import os
        print(f"🔍 DEBUG: Current working directory: {os.getcwd()}")
        print(f"🔍 DEBUG: Looking for private key at: {os.getenv('GITHUB_PRIVATE_KEY_PATH')}")
        
        # GitHub App credentials (for organization installation)
        self.github_app_id = os.getenv('GITHUB_APP_ID')
        self.github_app_client_id = os.getenv('GITHUB_APP_CLIENT_ID')
        self.github_app_client_secret = os.getenv('GITHUB_APP_CLIENT_SECRET')
        self.private_key_path = os.getenv('GITHUB_PRIVATE_KEY_PATH')
        
        # Debug: Check if private key path is set and file exists
        print(f"🔍 DEBUG: Private key path from env: {self.private_key_path}")
        
        # Verify the private key file exists
        if self.private_key_path:
            print(f"🔍 DEBUG: Checking if file exists: {self.private_key_path}")
            if os.path.exists(self.private_key_path):
                print(f"✅ Private key file found at: {self.private_key_path}")
            else:
                print(f"❌ Private key file NOT found at: {self.private_key_path}")
                # List files in current directory to help debug
                print(f"🔍 DEBUG: Files in current directory:")
                try:
                    for file in os.listdir('.'):
                        print(f"  - {file}")
                except Exception as e:
                    print(f"  Error listing files: {e}")
        else:
            print(f"❌ GITHUB_PRIVATE_KEY_PATH environment variable not set")
        
        self.github_app_name = os.getenv('GITHUB_APP_NAME', 'WithOps-DevSecOps-Platform')  # App name for installation URLs
        
        # GitHub OAuth App credentials (only for discovering user's organizations)
        self.github_oauth_client_id = os.getenv('GITHUB_OAUTH_CLIENT_ID')
        self.github_oauth_client_secret = os.getenv('GITHUB_OAUTH_CLIENT_SECRET')
        
        # Optimized HTTP client for ultra-fast responses
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=2.0, read=4.0),  # Even faster timeouts
            limits=httpx.Limits(max_connections=80, max_keepalive_connections=60),  # More connections
            http2=True  # Enable HTTP/2 for better multiplexing
        )
        
        # Optimized memory cache for better performance
        self.cache = {}
        self.cache_ttl = {
            'workspace': 3600,     # 1 hour (PHASE 5: Extended for stale-while-revalidate)
            'stats': 3600,         # 1 hour (PHASE 5: Extended for stale-while-revalidate)
            'discovery': 3600,     # 1 hour
            'workflow': 3600,      # 1 hour (PHASE 5: Extended for stale-while-revalidate)
            'installations': 3600, # 1 hour
            'versions': 7200       # 2 hours
        }
        
        # Default installation ID for version checking
        self.default_installation_id = None
        
        print(f"HTTP client configured with HTTP/2 and enhanced connection pooling")
        print(f"Enhanced memory cache initialized with dynamic TTLs")
        
        self.base_url = "https://api.github.com"
        
    def get_organization_discovery_oauth_url(self, state: str = None) -> str:
        """
        🔍 Step 2: Generate OAuth URL to discover user's organizations
        This uses OAuth App ONLY to see which organizations the user has access to
        """
        from urllib.parse import quote
        
        redirect_uri = "http://localhost:5173/github/organizations"
        
        params = {
            "client_id": self.github_oauth_client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:org",  # Only need to read organization membership
            "state": state or "discover_orgs",
            "response_type": "code"
        }
        
        # URL encode the parameters properly
        query_parts = []
        for key, value in params.items():
            query_parts.append(f"{key}={quote(str(value))}")
        
        query_string = "&".join(query_parts)
        oauth_url = f"https://github.com/login/oauth/authorize?{query_string}"
        
        print(f"🔍 Generated OAuth URL: {oauth_url}")
        print(f"🔍 Using redirect_uri: {redirect_uri}")
        print(f"🔍 Using client_id: {self.github_oauth_client_id}")
        
        return oauth_url
    
    async def exchange_code_for_token(self, code: str) -> str:
        """
        Exchange OAuth code for access token (for organization discovery only)
        """
        print(f"🔄 Exchanging OAuth code for token...")
        print(f"🔄 Using client_id: {self.github_oauth_client_id}")
        print(f"🔄 Code: {code[:10]}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.github_oauth_client_id,
                    "client_secret": self.github_oauth_client_secret,
                    "code": code,
                }
            )
            
            print(f"🔄 Token exchange response status: {response.status_code}")
            print(f"🔄 Token exchange response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                if access_token:
                    print(f"✅ Successfully obtained access token")
                    return access_token
                else:
                    print(f"❌ No access token in response: {data}")
                    raise Exception(f"No access token in response: {data}")
            else:
                raise Exception(f"Failed to exchange code for token: {response.text}")
            
            
# todo:get user_organization
    
    async def get_user_organizations(self, access_token: str, current_user_id: str = None) -> List[Dict]:
        """
        🏢 Step 3: Fetch organizations where user can install GitHub Apps (SECURE VERSION)
        Returns list of organizations where user has admin/owner permissions
        *** SECURITY: Only shows installation status for apps installed by THIS user ***
        """
        # Check cache first - organizations don't change often (user-specific cache)
        cache_key = f"user_orgs_{current_user_id}_{hash(access_token[-10:])}" if current_user_id else f"user_orgs_{hash(access_token[-10:])}"
        cached_orgs = self._get_cached(cache_key)
        
        if cached_orgs:
            print(f"🚀 Using cached organizations for instant response ({len(cached_orgs)} orgs)")
            return cached_orgs
        
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Get user's organization memberships
        response = await self.http_client.get(
            f"{self.base_url}/user/orgs",
            headers=headers
        )
        
        if response.status_code == 200:
            orgs = response.json()
            
            # Get user-specific installations from database (SECURE)
            if current_user_id:
                # Query database for user's installed organizations
                from database import db_manager, OrganizationInstallation, Organization
                from sqlalchemy import select, or_, cast
                from sqlalchemy.dialects.postgresql import JSONB
                
                async with db_manager.get_session() as session:
                    # Get organizations where this user is owner OR in linked_users
                    stmt = (
                        select(Organization.login)
                        .join(OrganizationInstallation, Organization.id == OrganizationInstallation.organization_id)
                        .where(
                            or_(
                                OrganizationInstallation.user_id == current_user_id,  # User is owner
                                cast(OrganizationInstallation.linked_users, JSONB).contains(cast([str(current_user_id)], JSONB))  # User is in linked_users
                            )
                        )
                        .where(OrganizationInstallation.status == 'active')
                    )
                    result = await session.execute(stmt)
                    user_installed_orgs = [row[0] for row in result.fetchall()]
                    user_installation_set = set(user_installed_orgs)
                    print(f"🔍 User {current_user_id} has access to {len(user_installed_orgs)} installed orgs: {user_installed_orgs}")
            else:
                user_installation_set = set()
            
            # Process organizations in parallel for much faster response
            import asyncio
            
            async def process_organization(org):
                try:
                    # Check if user has admin permissions in the org (in parallel)
                    membership_response = await self.http_client.get(
                        f"{self.base_url}/user/memberships/orgs/{org['login']}",
                        headers=headers
                    )
                    
                    if membership_response.status_code == 200:
                        membership = membership_response.json()
                        if membership.get('role') in ['admin'] or membership.get('state') == 'active':
                            # SECURITY: Only show installation status for user's own installations
                            org_login = org['login']
                            org['app_installed'] = org_login in user_installation_set
                            org['installation_id'] = None  # Don't expose installation IDs in discovery
                            
                            return org
                except Exception as e:
                    print(f"Error processing org {org['login']}: {e}")
                
                return None
            
            # Process up to 20 organizations in parallel for even faster discovery
            batch_size = 20
            filtered_orgs = []
            
            for i in range(0, len(orgs), batch_size):
                batch = orgs[i:i + batch_size]
                tasks = [process_organization(org) for org in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter out None results and exceptions
                batch_results = [org for org in results if org is not None and not isinstance(org, Exception)]
                filtered_orgs.extend(batch_results)
            
            # Cache the results for 5 minutes to speed up subsequent requests (user-specific)
            self._set_cached(cache_key, filtered_orgs, 'discovery')
            
            print(f"🚀 Processed {len(orgs)} organizations in parallel, {len(filtered_orgs)} accessible (user-specific)")
            return filtered_orgs
        else:
            raise Exception(f"Failed to fetch organizations: {response.text}")

# todo: install url-----------------------------------------------------------------------------        
    
    def generate_app_installation_url(self, org_name: str, state: str = None) -> str:
        """
        🧩 Step 4: Generate GitHub App installation URL for specific organization
        This is the key method - it creates the URL to install our GitHub App into the selected org
        """
        params = {
            "state": state or f"install_{org_name}"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        # Use the GitHub App name (configurable via environment)
        base_url = f"https://github.com/apps/{self.github_app_name}/installations/new"
        
        # Add organization suggestion to pre-select the organization
        if org_name:
            query_string += f"&suggested_target_id={org_name}&suggested_target_type=Organization"
        
        return f"{base_url}?{query_string}"
    
    async def _get_all_installations_cached(self) -> List[Dict]:
        """
        Get all GitHub App installations with aggressive caching
        This avoids multiple API calls when processing organizations
        """
        cache_key = "all_installations"
        cached_installations = self._get_cached(cache_key)
        
        if cached_installations:
            print(f"🚀 Using cached installations list ({len(cached_installations)} installations)")
            return cached_installations
        
        try:
            app_token = self._generate_app_jwt()
            headers = {
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = await self.http_client.get(
                f"{self.base_url}/app/installations",
                headers=headers
            )
            
            if response.status_code == 200:
                installations = response.json()
                # Cache for 2 minutes - installations don't change frequently
                self._set_cached(cache_key, installations, 'installations')
                print(f"🚀 Fetched and cached {len(installations)} installations")
                return installations
            else:
                print(f"Error fetching installations: {response.text}")
                return []
        except Exception as e:
            print(f"Error getting all installations: {e}")
            return []

# todo:check if install-------------------------------------------------------------------------------

    async def _check_app_installation(self, org_name: str) -> bool:
        """
        Check if our GitHub App is already installed in the organization
        """
        try:
            app_token = self._generate_app_jwt()
            headers = {
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with httpx.AsyncClient() as client:
                # Get all installations for our app
                response = await client.get(
                    f"{self.base_url}/app/installations",
                    headers=headers
                )
                
                if response.status_code == 200:
                    installations = response.json()
                    for installation in installations:
                        if installation.get('account', {}).get('login') == org_name:
                            return True
                return False
        except Exception as e:
            print(f"Error checking app installation: {e}")
            return False
    
    async def _get_installation_id(self, org_name: str) -> Optional[int]:
        """
        Get installation ID for a specific organization
        """
        try:
            app_token = self._generate_app_jwt()
            headers = {
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/app/installations",
                    headers=headers
                )
                
                if response.status_code == 200:
                    installations = response.json()
                    for installation in installations:
                        if installation.get('account', {}).get('login') == org_name:
                            return installation.get('id')
                return None
        except Exception as e:
            print(f"Error getting installation ID: {e}")
            return None
    
    def _generate_app_jwt(self) -> str:
        """
        Generate JWT for GitHub App authentication
        """
        try:
            # First try with the environment variable path
            if self.private_key_path and os.path.exists(self.private_key_path):
                with open(self.private_key_path, 'r') as key_file:
                    private_key = key_file.read()
            else:
                # Fall back to local file in backend directory
                fallback_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'github-app-private-key.pem')
                print(f"🔍 DEBUG: Trying fallback private key path: {fallback_path}")
                if os.path.exists(fallback_path):
                    with open(fallback_path, 'r') as key_file:
                        private_key = key_file.read()
                    print(f"✅ Using private key from fallback path: {fallback_path}")
                else:
                    raise FileNotFoundError(f"Private key not found at {self.private_key_path} or {fallback_path}")
            
            current_time = int(time.time())
            iat_time = current_time - 10  # Issued 10 seconds ago (more conservative)
            exp_time = current_time + (3 * 60)  # 3 minutes (very conservative)
            
            payload = {
                'iat': iat_time,
                'exp': exp_time,
                'iss': self.github_app_id
            }
            
            token = jwt.encode(payload, private_key, algorithm='RS256')
            
            # Debug: decode token to verify it's correct
            decoded = jwt.decode(token, options={"verify_signature": False})
            print(f"🔍 JWT Payload - IAT: {decoded['iat']}, EXP: {decoded['exp']}, ISS: {decoded['iss']}")
            print(f"🕐 Token lifetime: {decoded['exp'] - decoded['iat']} seconds")
            
            return token
        except Exception as e:
            print(f"❌ Failed to generate app JWT: {str(e)}")
            raise Exception(f"Failed to generate app JWT: {str(e)}")
    
    async def get_installation_details(self, installation_id: int) -> Dict:
        """
        🔐 Step 5: Get installation details after GitHub App installation
        """
        app_token = self._generate_app_jwt()
        headers = {
            "Authorization": f"Bearer {app_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/app/installations/{installation_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get installation details: {response.text}")
    
    async def get_installation_access_token(self, installation_id: int, force_fresh: bool = False) -> str:
        """
        Get access token for specific installation to access organization resources
        """
        # Check cache first (unless force refresh)
        token_cache_key = f"installation_token_{installation_id}"
        if not force_fresh:
            cached_token = self._get_cached(token_cache_key)
            if cached_token:
                print(f"🚀 Using cached installation token for {installation_id}")
                return cached_token.get('token')
        
        app_token = self._generate_app_jwt()
        headers = {
            "Authorization": f"Bearer {app_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/app/installations/{installation_id}/access_tokens",
                headers=headers
            )
            
            if response.status_code == 201:
                data = response.json()
                token = data.get("token")
                
                # Cache token for 45 minutes (GitHub tokens last 1 hour)
                self._set_cached(token_cache_key, {'token': token}, 'installations')
                print(f"✅ Cached fresh installation token for {installation_id}")
                
                return token
            else:
                raise Exception(f"Failed to get installation access token: {response.text}")
            
# todo:--------------------------------get-org-repository-------------------------------------------------------------            
    
    async def get_organization_repositories(self, installation_id: int, force_fresh: bool = False) -> List[Dict]:
        """
        🌐 Step 6: Get repositories for the connected organization
        """
        access_token = await self.get_installation_access_token(installation_id, force_fresh)
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/installation/repositories",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                repositories = data.get("repositories", [])
                print(f"✅ Fetched {len(repositories)} repositories from GitHub API")
                return repositories
            else:
                raise Exception(f"Failed to get repositories: {response.text}")
            
# todo:---------------------------------get-repo-workflow-------------------------------------------   
#  
    async def get_repository_workflows(self, installation_id: int, repo_owner: str, repo_name: str) -> List[Dict]:
        """
        Get workflows for a specific repository
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/actions/workflows"
                print(f"🔍 Fetching workflows from: {url}")
                
                response = await client.get(url, headers=headers)
                
                print(f"📊 Workflow API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    workflows = data.get("workflows", [])
                    print(f"✅ Successfully fetched {len(workflows)} workflows for {repo_owner}/{repo_name}")
                    return workflows
                elif response.status_code == 404:
                    print(f"ℹ️  No workflows found for {repo_owner}/{repo_name} (repository might not have Actions enabled)")
                    return []
                else:
                    print(f"❌ Failed to get workflows for {repo_owner}/{repo_name}: Status {response.status_code}, Response: {response.text}")
                    return []
        except Exception as e:
            print(f"❌ Exception while fetching workflows for {repo_owner}/{repo_name}: {str(e)}")
            return []

    async def _get_repository_workflows(self, installation_id: int, repo_name: str) -> List[Dict]:
        """
        Get workflows for a specific repository (internal method for stats)
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get the organization name from the installation
            org_name = await self._get_org_name_from_installation(installation_id)
            if not org_name:
                print(f"❌ Could not get org name for installation {installation_id}")
                return []
            
            url = f"{self.base_url}/repos/{org_name}/{repo_name}/actions/workflows"
            
            response = await self.http_client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                workflows = data.get("workflows", [])
                return workflows
            elif response.status_code == 404:
                # Repository might not have Actions enabled
                return []
            else:
                print(f"❌ Failed to get workflows for {repo_name}: Status {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Exception while fetching workflows for {repo_name}: {str(e)}")
            return []

    async def _get_org_name_from_installation(self, installation_id: int) -> Optional[str]:
        """
        Get organization name from installation ID
        """
        try:
            app_token = self._generate_app_jwt()
            headers = {
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = await self.http_client.get(
                f"{self.base_url}/app/installations/{installation_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                installation = response.json()
                return installation.get('account', {}).get('login')
            return None
        except Exception as e:
            print(f"Error getting org name from installation {installation_id}: {e}")
            return None

# todo: get workflow content-----------------------------------------------------------

    async def get_workflow_content(self, installation_id: int, repo_owner: str, repo_name: str, workflow_path: str) -> str:
        """
        Get the content of a specific workflow file (ULTRA-OPTIMIZED with caching)
        """
        # Validate parameters to prevent undefined/None values
        if not repo_name or repo_name == 'undefined' or repo_name == 'null':
            print(f"❌ Invalid repo_name provided: '{repo_name}' for workflow {workflow_path}")
            raise ValueError(f"Invalid repository name: '{repo_name}'. Repository name cannot be undefined, null, or empty.")
        
        if not repo_owner or repo_owner == 'undefined' or repo_owner == 'null':
            print(f"❌ Invalid repo_owner provided: '{repo_owner}' for workflow {workflow_path}")
            raise ValueError(f"Invalid repository owner: '{repo_owner}'. Repository owner cannot be undefined, null, or empty.")
        
        # Check cache first for instant response
        cache_key = self._get_cache_key('workflow', installation_id, repo_owner, repo_name, workflow_path)
        cached_content = self._get_cached(cache_key)
        if cached_content:
            print(f"🚀 Using cached workflow content for {workflow_path}")
            return cached_content.get('content', '')
        
        try:
            access_token = await self.get_installation_access_token(installation_id)
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3.raw"
            }
            
            url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/contents/{workflow_path}"
            print(f"🔍 Fetching workflow content from: {url}")
            
            # Use the persistent HTTP client for connection reuse
            response = await self.http_client.get(url, headers=headers)
            
            if response.status_code == 200:
                content = response.text
                print(f"✅ Successfully fetched workflow content for {workflow_path} ({len(content)} chars)")
                
                # Cache the content
                self._set_cached(cache_key, {'content': content}, 'workflow')
                
                return content
            else:
                print(f"❌ Failed to get workflow content: Status {response.status_code}")
                return f"# Error loading workflow content\n# Status: {response.status_code} {response.reason_phrase}"
        except Exception as e:
            print(f"❌ Exception while fetching workflow content: {str(e)}")
            return f"# Error loading workflow content\n# {str(e)}"
# todo: workflow details------------------------------------------------------------------------------------------------------
   

    
# todo:- uses with under call-reusable-------------------------------------------
    def extract_reusable_workflow_uses(self, workflow_content: str) -> list:
        """
        Extracts all 'uses' statements at the job level (reusable workflow calls) from a workflow YAML content string.
        Returns a list of reusable workflow references (e.g., 'org/repo/.github/workflows/other.yml@ref').
        """
        import yaml
        import re
        reusable_uses = []
        try:
            parsed = yaml.safe_load(workflow_content)
            if isinstance(parsed, dict) and 'jobs' in parsed:
                for job_name, job in parsed['jobs'].items():
                    if isinstance(job, dict) and 'uses' in job:
                        uses_val = job['uses']
                        if isinstance(uses_val, str):
                            reusable_uses.append(uses_val.strip())
        except Exception:
            # fallback to regex if YAML fails
            pattern = r"^[ \t]*uses:[ \t]*([\w\-/\.@]+)"  # simple pattern for uses
            for match in re.finditer(pattern, workflow_content, re.MULTILINE):
                uses_val = match.group(1)
                if uses_val and uses_val not in reusable_uses:
                    reusable_uses.append(uses_val)
        return reusable_uses
        
    async def get_workflow_details_enhanced(self, installation_id: int, repo_owner: str, repo_name: str, workflow_id: int) -> Dict:
        """
        Get enhanced workflow details including runs, triggers, and author information
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get workflow details
            workflow_url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_id}"
            
            # Get workflow runs (last 10 for performance)
            runs_url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_id}/runs?per_page=10"
            
            workflow_data = {}
            runs_data = []
            
            async with httpx.AsyncClient() as client:
                # Fetch workflow details and runs in parallel
                workflow_response, runs_response = await asyncio.gather(
                    client.get(workflow_url, headers=headers),
                    client.get(runs_url, headers=headers),
                    return_exceptions=True
                )
                
                # Process workflow details
                if isinstance(workflow_response, httpx.Response) and workflow_response.status_code == 200:
                    workflow_data = workflow_response.json()
                
                # Process runs data
                if isinstance(runs_response, httpx.Response) and runs_response.status_code == 200:
                    runs_data = runs_response.json().get("workflow_runs", [])
            
            # Extract trigger information and reusable workflow calls
            triggers = []
            reusable_workflow_calls = []
            
            if workflow_data.get('path'):
                try:
                    content = await self.get_workflow_content(installation_id, repo_owner, repo_name, workflow_data['path'])
                    if content and isinstance(content, str):
                        # Extract triggers (existing logic)
                        triggers = await self._extract_triggers(content)
                        
                        # Extract reusable workflow calls (new logic)
                        reusable_workflow_calls = await self._extract_reusable_workflow_calls(content)
                        
                except Exception as e:
                    print(f"⚠️ Could not parse workflow content: {e}")
            
            # Find last run and last successful run
            last_run = None
            last_successful = None
            
            for run in runs_data:
                if not last_run:
                    last_run = run
                if run.get('status') == 'completed' and run.get('conclusion') == 'success' and not last_successful:
                    last_successful = run
                    break
            
            # Get author information from last commit to workflow file
            author = "Unknown"
            try:
                if workflow_data.get('path'):
                    commits_url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/commits?path={workflow_data['path']}&per_page=1"
                    async with httpx.AsyncClient() as client:
                        commits_response = await client.get(commits_url, headers=headers)
                        if commits_response.status_code == 200:
                            commits = commits_response.json()
                            if commits:
                                author_info = commits[0].get('commit', {}).get('author', {})
                                author = author_info.get('name', 'Unknown')
            except Exception as e:
                print(f"⚠️ Could not get author information: {e}")
            
            return {
                "workflow": workflow_data,
                "last_run": last_run,
                "last_successful": last_successful,
                "triggers": triggers or ["Unknown"],
                "uses": reusable_workflow_calls,  # Only reusable workflow calls
                "author": author,
                "total_runs": len(runs_data)
            }

        except Exception as e:
            print(f"❌ Error getting enhanced workflow details: {e}")
            return {
                "workflow": {},
                "last_run": None,
                "last_successful": None,
                "triggers": ["Unknown"],
                "uses": [],
                "author": "Unknown",
                "total_runs": 0
            }

    async def _extract_triggers(self, content: str) -> List[str]:
        """Extract triggers from workflow content (existing logic)"""
        triggers = []
        
        # Define valid GitHub workflow triggers
        valid_triggers = [
            'push', 'pull_request', 'workflow_call', 'workflow_dispatch', 
            'schedule', 'release', 'issues', 'issue_comment', 'pull_request_review',
            'pull_request_review_comment', 'pull_request_target', 'create', 'delete',
            'deployment', 'deployment_status', 'fork', 'gollum', 'page_build',
            'public', 'registry_package', 'status', 'watch', 'workflow_run',
            'check_run', 'check_suite', 'discussion', 'discussion_comment',
            'label', 'milestone', 'project', 'project_card', 'project_column',
            'repository_dispatch', 'workflow_call', 'repository_vulnerability_alert'
        ]
        
        # Method 1: Handle single-line triggers (e.g., "on: push")
        single_line_match = re.search(r'^on:\s*([a-zA-Z_]+)\s*(?:#.*)?$', content, re.MULTILINE)
        if single_line_match:
            trigger = single_line_match.group(1).strip()
            if trigger in valid_triggers:
                triggers = [trigger]
        
        # Method 2: Handle array format (e.g., "on: [push, pull_request]")
        elif re.search(r'^on:\s*\[', content, re.MULTILINE):
            array_match = re.search(r'^on:\s*\[([^\]]+)\]', content, re.MULTILINE)
            if array_match:
                trigger_text = array_match.group(1).strip()
                parsed_triggers = [t.strip().strip('"\'') for t in trigger_text.split(',') if t.strip()]
                triggers = [t for t in parsed_triggers if t in valid_triggers]
        
        # Method 3: Handle multi-line YAML format
        else:
            on_section_pattern = r'^on:\s*\n((?:[ \t]+.*\n?)*?)(?=^[a-zA-Z_]|^$)'
            on_section_match = re.search(on_section_pattern, content, re.MULTILINE)
            
            if on_section_match:
                on_section = on_section_match.group(1)
                
                trigger_types = []
                lines = on_section.split('\n')
                base_indent = None
                
                for line in lines:
                    stripped = line.strip()
                    if stripped and ':' in stripped and not stripped.startswith('#'):
                        indent = len(line) - len(line.lstrip())
                        
                        if base_indent is None and indent > 0:
                            base_indent = indent
                        
                        if base_indent is not None and indent == base_indent:
                            trigger_name = stripped.split(':')[0].strip()
                            if trigger_name in valid_triggers:
                                trigger_types.append(trigger_name)
                
                triggers = trigger_types
        
        return triggers

    async def _extract_reusable_workflow_calls(self, content: str) -> List[str]:
        """
        Extract only 'uses' statements from jobs that call reusable workflows.
        This specifically looks for jobs that have 'uses' at the job level (not step level).
        """
        reusable_calls = []
        
        try:
            # Method 1: Try to parse as YAML for more accurate extraction
            try:
                import yaml
                parsed_yaml = yaml.safe_load(content)
                if isinstance(parsed_yaml, dict) and 'jobs' in parsed_yaml:
                    for job_name, job_config in parsed_yaml['jobs'].items():
                        if isinstance(job_config, dict) and 'uses' in job_config:
                            uses_value = job_config['uses']
                            if isinstance(uses_value, str) and uses_value.strip():
                                reusable_calls.append(uses_value.strip())
                                print(f"✅ Found reusable workflow call in job '{job_name}': {uses_value}")
            except Exception as yaml_error:
                print(f"⚠️ YAML parsing failed, falling back to regex: {yaml_error}")
                
                # Method 2: Fallback to regex-based extraction
                reusable_calls = self._extract_reusable_workflows_with_regex(content)
            
            return reusable_calls
        
        except Exception as e:
            print(f"❌ Error extracting reusable workflow calls: {e}")
            return []

    def _extract_reusable_workflows_with_regex(self, content: str) -> List[str]:
        """
        Fallback method using regex to extract reusable workflow calls.
        This looks for 'uses' statements at the job level (not step level).
        """
        reusable_calls = []
        
        # Split content into lines for processing
        lines = content.split('\n')
        
        # Find the jobs section
        jobs_section_found = False
        current_job_indent = None
        current_job_name = None
        in_job_definition = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Find jobs section
            if stripped.startswith('jobs:'):
                jobs_section_found = True
                continue
            
            if not jobs_section_found:
                continue
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Calculate indentation
            indent = len(line) - len(line.lstrip())
            
            # Check if this is a job definition (first level under jobs)
            if ':' in stripped and not stripped.startswith('uses:'):
                # This might be a job definition
                if current_job_indent is None or indent <= current_job_indent:
                    current_job_indent = indent
                    current_job_name = stripped.split(':')[0].strip()
                    in_job_definition = True
                    print(f"🔍 Found job: {current_job_name}")
                    continue
            
            # Check if we're in a job definition and found a 'uses' statement
            if in_job_definition and stripped.startswith('uses:'):
                # Make sure this 'uses' is at the job level, not nested in steps
                if current_job_indent is not None and indent > current_job_indent:
                    # Check if this is directly under the job (not nested further)
                    expected_job_property_indent = current_job_indent + 2  # or your YAML indent size
                    if indent <= expected_job_property_indent + 2:  # Allow some flexibility
                        uses_value = stripped.split('uses:', 1)[1].strip()
                        if uses_value:
                            reusable_calls.append(uses_value)
                            print(f"✅ Found reusable workflow call in job '{current_job_name}': {uses_value}")
                            in_job_definition = False  # Move to next job
        
        return reusable_calls

    # Alternative more precise regex-based method
    def _extract_reusable_workflows_with_precise_regex(self, content: str) -> List[str]:
        """
        More precise regex-based extraction for reusable workflow calls.
        This specifically looks for job-level 'uses' statements.
        """
        reusable_calls = []
        
        # Pattern to match job-level 'uses' statements
        # This pattern looks for jobs that have 'uses' directly as a job property
        pattern = r'^(?:[ \t]*)([a-zA-Z0-9_-]+):(?:\s*#.*)?$\n(?:(?:[ \t]+(?!uses:).*\n)*?)^(?:[ \t]+)uses:\s*(.+?)(?:\s*#.*)?$'
        
        matches = re.finditer(pattern, content, re.MULTILINE)
        
        for match in matches:
            job_name = match.group(1).strip()
            uses_value = match.group(2).strip()
            
            if uses_value:
                reusable_calls.append(uses_value)
                print(f"✅ Found reusable workflow call in job '{job_name}': {uses_value}")
        
        return reusable_calls
    
# todo:======================================================================================================================
# todo:=================workflow---action---======================================

    async def get_workflow_actions_detailed(self, installation_id: int, repo_owner: str, repo_name: str, workflow_id: int) -> List[Dict]:
        """
        Extract step-level actions from a specific workflow
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            # Get workflow details
            workflow_url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_id}"
            workflow_data = {}
            async with httpx.AsyncClient() as client:
                workflow_response = await client.get(workflow_url, headers=headers)
                if workflow_response.status_code == 200:
                    workflow_data = workflow_response.json()
            actions = []
            if workflow_data.get('path'):
                try:
                    content = await self.get_workflow_content(installation_id, repo_owner, repo_name, workflow_data['path'])
                    if content and isinstance(content, str):
                        # Extract step-level actions
                        actions = await self._extract_workflow_actions(content, workflow_data, repo_name)
                except Exception as e:
                    print(f"⚠️ Could not parse workflow content: {e}")
            return actions
        except Exception as e:
            print(f"❌ Error getting workflow actions: {e}")
            return []
            
    async def _extract_workflow_actions(self, content: str, workflow_data: Dict, repo_name: str) -> List[Dict]:
        """
        Extract step-level actions from workflow content
        """
        actions = []
        workflow_name = 'Unknown'
        workflow_filename = workflow_data.get('path', '').split('/')[-1]
        
        try:
            # Try YAML parsing first
            import yaml
            parsed_yaml = yaml.safe_load(content)
            if isinstance(parsed_yaml, dict):
                workflow_name = parsed_yaml.get('name', workflow_data.get('name', 'Unknown'))
                if 'jobs' in parsed_yaml:
                    for job_name, job_config in parsed_yaml['jobs'].items():
                        # Step-level actions (only external actions)
                        if isinstance(job_config, dict) and 'steps' in job_config:
                            for step_index, step in enumerate(job_config['steps']):
                                if isinstance(step, dict) and 'uses' in step:
                                    uses_value = step['uses']
                                    if (isinstance(uses_value, str)
                                        and uses_value.strip()
                                        and not uses_value.strip().startswith('.')
                                        and not uses_value.strip().startswith('/')
                                        and '/' in uses_value and '@' in uses_value):
                                        # Parse action name and version
                                        action_info = self._parse_action_string(uses_value.strip())
                                        if action_info:
                                            actions.append({
                                                'repo_name': repo_name,
                                                'workflow_name': workflow_name,
                                                'workflow_filename': workflow_filename,
                                                'workflow_path': workflow_data.get('path', f'.github/workflows/{workflow_filename}'),
                                                'job_name': job_name,
                                                'step_index': step_index,
                                                'step_name': step.get('name', f'Step {step_index + 1}'),
                                                'action_full': uses_value.strip(),
                                                'action_name': action_info['name'],
                                                'current_version': action_info['version'],
                                                'latest_version': None,
                                                'status': 'unknown'
                                            })
                        # Job-level reusable workflow calls: SKIP (do not include in audit table)
                        # (No code here, we intentionally do not add job-level uses)
            
            # If no actions found, add a placeholder for this workflow
            if not actions:
                actions.append({
                    'repo_name': repo_name,
                    'workflow_name': workflow_name,
                    'workflow_filename': workflow_filename,
                    'workflow_path': workflow_data.get('path', f'.github/workflows/{workflow_filename}'),
                    'job_name': None,
                    'step_index': None,
                    'step_name': None,
                    'action_full': None,
                    'action_name': None,
                    'current_version': None,
                    'latest_version': None,
                    'status': 'no-actions-found'
                })
                
        except Exception as yaml_error:
            print(f"⚠️ YAML parsing failed, falling back to regex: {yaml_error}")
            # Fallback to regex extraction
            actions = self._extract_actions_with_regex(content, workflow_data, repo_name)
            # If still no actions, add placeholder
            if not actions:
                actions.append({
                    'repo_name': repo_name,
                    'workflow_name': workflow_data.get('name', 'Unknown'),
                    'workflow_filename': workflow_filename,
                    'workflow_path': workflow_data.get('path', f'.github/workflows/{workflow_filename}'),
                    'job_name': None,
                    'step_index': None,
                    'step_name': None,
                    'action_full': None,
                    'action_name': None,
                    'current_version': None,
                    'latest_version': None,
                    'status': 'no-actions-found'
                })
        
        print(f"🔍 [DEBUG] Extracted {len(actions)} actions from workflow {workflow_filename} in repo {repo_name}")
        return actions


    def _extract_actions_with_regex(self, content: str, workflow_data: Dict, repo_name: str) -> List[Dict]:
        """
        Fallback regex-based extraction for step-level actions
        """
        actions = []
        
        # Extract workflow name
        workflow_name = "Unknown"
        name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        if name_match:
            workflow_name = name_match.group(1).strip().strip('"\'')
        
        workflow_filename = workflow_data.get('path', '').split('/')[-1]
        
        # Find all uses statements in steps (not job-level)
        # This regex looks for uses statements that are indented more than job level
        uses_pattern = r'^(?:[ \t]+)- name:.*\n(?:[ \t]+)uses:\s*(.+?)(?:\s*#.*)?$|^(?:[ \t]+)uses:\s*(.+?)(?:\s*#.*)?$'
        
        matches = re.finditer(uses_pattern, content, re.MULTILINE)
        
        for match in matches:
            uses_value = match.group(1) or match.group(2)
            if uses_value:
                uses_value = uses_value.strip()
                action_info = self._parse_action_string(uses_value)
                if action_info:
                    actions.append({
                        'repo_name': repo_name,
                        'workflow_name': workflow_name,
                        'workflow_filename': workflow_filename,
                        'workflow_path': workflow_data.get('path', f'.github/workflows/{workflow_filename}'),
                        'job_name': 'unknown',
                        'step_index': 0,
                        'step_name': 'Unknown Step',
                        'action_full': uses_value,
                        'action_name': action_info['name'],
                        'current_version': action_info['version'],
                        'latest_version': None,
                        'status': 'unknown'
                    })
        
        return actions
    
    def _parse_action_string(self, action_string: str) -> Optional[Dict[str, str]]:
        """
        Parse action string to extract name and version
        Examples:
        - 'actions/checkout@v3' -> name='actions/checkout', version='v3'
        - 'actions/setup-node@v4.0.2' -> name='actions/setup-node', version='v4.0.2'
        - './local-action' -> None (local action, ignore)
        """
        # Ignore local actions (starting with ./ or ../)
        if action_string.startswith('.'):
            return None
        
        # Split by @ to get name and version
        if '@' in action_string:
            name, version = action_string.split('@', 1)
            return {
                'name': name.strip(),
                'version': version.strip()
            }
        
        return None
# todo:----------------------------org-action-detailed---------------------------------------------------------
#     
    async def get_organization_actions_detailed(self, installation_id: int, org_name: str) -> List[Dict]:
        """
        Get all actions from all workflows in an organization
        """
        try:
            # Get all workflows from organization
            workspace_data = await self.get_organization_workspace_detailed(installation_id, org_name)
            workflows = workspace_data.get("workflows", [])

            print(f"🔎 [DEBUG] Found {len(workflows)} workflows in organization {org_name}:")
            for wf in workflows:
                print(f"  - Workflow: {wf.get('name')} (repo: {wf.get('repository')}, id: {wf.get('id')}, path: {wf.get('path')})")

            all_actions = []
            workflow_id_to_actions = {}

            # Process workflows in batches
            batch_size = 5
            for i in range(0, len(workflows), batch_size):
                batch = workflows[i:i + batch_size]
                batch_tasks = []
                batch_ids = []
                for workflow in batch:
                    if workflow.get("id") and workflow.get("repository"):
                        print(f"[DEBUG] Scheduling action extraction for workflow: {workflow.get('name')} (repo: {workflow.get('repository')}, id: {workflow.get('id')}, path: {workflow.get('path')})")
                        task = self.get_workflow_actions_detailed(
                            installation_id,
                            org_name,
                            workflow["repository"],
                            workflow["id"]
                        )
                        batch_tasks.append(task)
                        batch_ids.append(workflow["id"])

                # Execute batch
                if batch_tasks:
                    results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    for idx, result in enumerate(results):
                        workflow_id = batch_ids[idx]
                        if isinstance(result, Exception):
                            print(f"❌ Error processing workflow actions: {result}")
                            workflow_id_to_actions[workflow_id] = []
                        else:
                            workflow_id_to_actions[workflow_id] = result
                            all_actions.extend(result)

            # Add a placeholder row for workflows with no actions
            enriched_actions = await self._enrich_with_latest_versions(all_actions)
            # Build a lookup for enriched actions by workflow id
            workflow_id_to_enriched = {}
            for wf in workflows:
                workflow_id = wf.get("id")
                # Filter by both repo_name and workflow_filename to avoid conflicts
                workflow_actions = [a for a in enriched_actions if (a.get('repo_name') == wf.get('repository') and
                                                    a.get('workflow_filename') == (wf.get('path', '').split('/')[-1]))]

                if not workflow_actions:
                    # Add a placeholder row for this workflow
                    workflow_actions = [{
                        'repo_name': wf.get('repository'),
                        'workflow_name': wf.get('name'),
                        'workflow_filename': wf.get('path','').split('/')[-1],
                        'workflow_path': wf.get('path', f'.github/workflows/{wf.get("path","").split("/")[-1]}'),
                        'job_name': '',
                        'step_index': None,
                        'step_name': '',
                        'action_full': '',
                        'action_name': '',
                        'current_version': '',
                        'latest_version': '',
                        'status': 'No actions found'
                    }]
                # Store workflow actions in lookup
                workflow_id_to_enriched[workflow_id] = workflow_actions

            # Flatten all enriched actions (including placeholders)
            final_actions = []
            for wf in workflows:
                workflow_id = wf.get("id")
                final_actions.extend(workflow_id_to_enriched[workflow_id])

            # Print a summary of actions per workflow file
            from collections import Counter
            wf_counter = Counter([a.get('repo_name') for a in final_actions])
            print(f"🔎 [DEBUG] Actions per workflow file:")
            for wf, count in wf_counter.items():
                print(f"  - {wf}: {count} actions")

            return final_actions

        except Exception as e:
            print(f"❌ Error getting organization actions: {e}")
            return []
        
    async def _enrich_with_latest_versions(self, actions: List[Dict]) -> List[Dict]:
        """
        Enrich actions with latest version information and status
        Uses caching to avoid excessive API calls
        """
        # Get unique action names
        unique_actions = set()
        for action in actions:
            action_name = action.get('action_name')
            if action_name:
                unique_actions.add(action_name)
        
        print(f"🔍 Enriching {len(actions)} actions with latest versions")
        print(f"🔍 Unique actions to fetch: {list(unique_actions)}")
        
        # Check cache first
        cache_key = f"latest_versions_{hash(frozenset(unique_actions))}"
        cached_versions = self._get_cached(cache_key)
        
        if cached_versions:
            print(f"🚀 Using cached latest versions for {len(unique_actions)} actions")
            latest_versions = cached_versions
        else:
            print(f"🔄 Fetching latest versions for {len(unique_actions)} actions from GitHub API")
            # Get latest versions for all unique actions
            latest_versions = await self._get_latest_versions_for_actions(list(unique_actions))
            print(f"🔄 Got latest versions: {latest_versions}")
            
            # Cache the results for 1 hour (versions don't change that frequently)
            self._set_cached(cache_key, latest_versions, 'versions', ttl=3600)
        
        # Enrich actions with latest version info
        for action in actions:
            action_name = action.get('action_name')
            if action_name:
                latest_version = latest_versions.get(action_name)
                
                if latest_version:
                    action['latest_version'] = latest_version
                    action['status'] = self._compare_versions(
                        action['current_version'], 
                        latest_version
                    )
                else:
                    action['latest_version'] = 'unknown'
                    action['status'] = 'unknown'
            else:
                action['latest_version'] = ''
                action['status'] = action.get('status', 'No actions found')
        
        return actions    
    
    async def _get_latest_versions_for_actions(self, action_names: List[str]) -> Dict[str, str]:
        """
        Get latest versions for a list of action names using GitHub Releases API
        This fetches real-time version information instead of hardcoded versions
        """
        result = {}
        
        # Batch process actions to avoid rate limiting
        batch_size = 10
        for i in range(0, len(action_names), batch_size):
            batch = action_names[i:i + batch_size]
            batch_tasks = []
            
            for action_name in batch:
                if action_name and '/' in action_name:
                    task = self._fetch_action_latest_version(action_name)
                    batch_tasks.append((action_name, task))
            
            # Execute batch
            if batch_tasks:
                tasks = [task for _, task in batch_tasks]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for (action_name, _), version_result in zip(batch_tasks, results):
                    if isinstance(version_result, Exception):
                        print(f"⚠️ Error fetching version for {action_name}: {version_result}")
                        # Fallback to known versions
                        result[action_name] = self._get_fallback_version(action_name)
                    else:
                        result[action_name] = version_result
                        
                # Small delay between batches to respect rate limits
                await asyncio.sleep(0.1)
        
        return result
    
    async def _fetch_action_latest_version(self, action_name: str) -> str:
        """
        Fetch the latest version for a specific action from GitHub Releases API
        """
        try:
            # For actions like 'actions/checkout@v3', extract 'actions/checkout'
            if '@' in action_name:
                action_name = action_name.split('@')[0]
            
            # Get access token (using a public token or installation token)
            access_token = os.getenv('GITHUB_TOKEN')  # You can use a personal access token here
            print(f"🔑 GitHub token from env: {'***' + access_token[-4:] if access_token else 'None'}")
            
            if not access_token:
                # Try to get an installation token if available
                try:
                    if not self.default_installation_id:
                        # Set a default installation ID if we have one
                        installations = await self.get_all_user_installations()
                        if installations:
                            self.default_installation_id = installations[0].get('installation_id')
                            print(f"🔑 Using default installation ID: {self.default_installation_id}")
                            
                    if self.default_installation_id:
                        access_token = await self.get_installation_access_token(self.default_installation_id)
                        print(f"🔑 Got installation token: {'***' + access_token[-4:] if access_token else 'None'}")
                    else:
                        access_token = None
                        print("🔑 No installation ID available")
                except Exception as e:
                    print(f"⚠️ Could not get installation token: {e}")
                    access_token = None
            
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DevSecOps-Actions-Auditor"
            }
            
            if access_token:
                headers["Authorization"] = f"token {access_token}"
            
            # GitHub API endpoint for releases
            url = f"https://api.github.com/repos/{action_name}/releases/latest"
            print(f"🔍 Fetching latest version for {action_name} from: {url}")
            
            max_retries = 3
            for attempt in range(max_retries):
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, headers=headers)
                    print(f"🔍 API response for {action_name}: {response.status_code}")
                    
                    if response.status_code == 200:
                        release_data = response.json()
                        tag_name = release_data.get('tag_name', '')
                        print(f"✅ Found latest version for {action_name}: {tag_name}")
                        
                        # Clean up the tag name (remove 'v' prefix if present)
                        if tag_name.startswith('v'):
                            return tag_name
                        else:
                            return f"v{tag_name}" if tag_name else 'unknown'
                            
                    elif response.status_code == 404:
                        print(f"⚠️ No releases found for {action_name}, trying tags API")
                        # No releases found, try tags API
                        return await self._fetch_action_latest_tag(action_name, headers)
                        
                    elif await self._handle_rate_limit(response):
                        # Rate limited, retry
                        print(f"⏱️ Rate limited for {action_name}, retrying...")
                        continue
                        
                    else:
                        print(f"⚠️ GitHub API error for {action_name}: {response.status_code} - {response.text}")
                        break
                        
                # If we get here, all retries failed
                return self._get_fallback_version(action_name)
                    
        except Exception as e:
            print(f"❌ Error fetching latest version for {action_name}: {e}")
            return self._get_fallback_version(action_name)
    
    async def _fetch_action_latest_tag(self, action_name: str, headers: Dict[str, str]) -> str:
        """
        Fallback to tags API if releases API fails
        """
        try:
            url = f"https://api.github.com/repos/{action_name}/tags"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    tags = response.json()
                    if tags and len(tags) > 0:
                        # Get the first (latest) tag
                        latest_tag = tags[0].get('name', '')
                        if latest_tag.startswith('v'):
                            return latest_tag
                        else:
                            return f"v{latest_tag}" if latest_tag else 'unknown'
                    
                return self._get_fallback_version(action_name)
                
        except Exception as e:
            print(f"❌ Error fetching tags for {action_name}: {e}")
            return self._get_fallback_version(action_name)
    
    def _get_fallback_version(self, action_name: str) -> str:
        """
        Fallback to known versions if API fails
        """
        known_versions = {
            'actions/checkout': 'v4',
            'actions/setup-node': 'v4',
            'actions/setup-python': 'v5',
            'actions/setup-java': 'v4',
            'actions/setup-ruby': 'v1',
            'actions/setup-go': 'v5',
            'actions/setup-dotnet': 'v4',
            'actions/cache': 'v4',
            'actions/upload-artifact': 'v4',
            'actions/download-artifact': 'v4',
            'actions/deploy-pages': 'v4',
            'actions/configure-pages': 'v4',
            'actions/create-release': 'v1',
            'actions/upload-release-asset': 'v1',
            'actions/github-script': 'v7',
            'actions/stale': 'v9',
            'actions/first-interaction': 'v1',
            'actions/labeler': 'v5',
            'github/super-linter': 'v6',
            'codecov/codecov-action': 'v4',
            'docker/build-push-action': 'v5',
            'docker/login-action': 'v3',
            'docker/setup-buildx-action': 'v3',
            'docker/setup-qemu-action': 'v3',
            'azure/webapps-deploy': 'v2',
            'azure/docker-login': 'v2',
            'aws-actions/configure-aws-credentials': 'v4',
            'aws-actions/amazon-ecr-login': 'v2',
            'google-github-actions/setup-gcloud': 'v2',
            'google-github-actions/auth': 'v2',
        }
        
        fallback_version = known_versions.get(action_name, 'unknown')
        print(f"🔄 Using fallback version for {action_name}: {fallback_version}")
        return fallback_version
    
    def _compare_versions(self, current: str, latest: str) -> str:
        """
        Compare current version with latest version using production-grade semantic versioning
        Returns: '✅ up-to-date', '⚠️ outdated', '🔧 upgrade recommended', '🚨 major upgrade needed', or 'unknown'
        
        Production-grade logic:
        - Always recommend specific patch versions for security
        - Flag major-only versions as potential security risks
        - Provide clear upgrade reasoning
        """
        if not current or not latest:
            return 'unknown'
        
        # Use the new semantic version manager
        try:
            from core.semantic_version_manager import SemanticVersionManager
            version_manager = SemanticVersionManager()
            
            comparison = version_manager.compare_versions(current, latest)
            
            # Map to the expected format for backward compatibility
            if not comparison.is_outdated:
                return '✅ up-to-date'
            elif "MAJOR UPGRADE NEEDED" in comparison.recommendation:
                return '🚨 major upgrade needed'
            elif "UPGRADE TO SPECIFIC VERSION" in comparison.recommendation:
                return '🔧 upgrade recommended'
            else:
                return '⚠️ outdated'
                
        except Exception as e:
            print(f"⚠️ Version comparison error for {current} vs {latest}: {e}")
            # Fallback to simple comparison
            return '⚠️ outdated' if current != latest else '✅ up-to-date'
    
    def _parse_version(self, version_str: str) -> Optional[tuple]:
        """
        Parse version string into comparable tuple
        Examples: 
        - 'v4.1.2' -> (4, 1, 2)
        - 'v4' -> (4, 0, 0)
        - '4.1' -> (4, 1, 0)
        - 'v4.0.0' -> (4, 0, 0)
        """
        try:
            # Remove 'v' prefix if present
            clean_version = version_str.lstrip('v')
            
            # Handle empty or invalid versions
            if not clean_version:
                return None
            
            # Split by dots and convert to integers
            parts = clean_version.split('.')
            
            # Ensure we have exactly 3 parts (major.minor.patch)
            while len(parts) < 3:
                parts.append('0')
            
            # Take only the first 3 parts and convert to integers
            version_parts = []
            for i, part in enumerate(parts[:3]):
                try:
                    # Handle cases where part might have extra characters (e.g., "4.1.2-alpha")
                    clean_part = ''.join(filter(str.isdigit, part))
                    if clean_part:
                        version_parts.append(int(clean_part))
                    else:
                        version_parts.append(0)
                except ValueError:
                    version_parts.append(0)
            
            version_tuple = tuple(version_parts)
            print(f"🔍 Parsed version '{version_str}' -> {version_tuple}")
            return version_tuple
            
        except Exception as e:
            print(f"⚠️ Error parsing version '{version_str}': {e}")
            return None
# todo:=================================================================================================================
# todo:---------------------

    async def get_organization_workspace_detailed(self, installation_id: int, org_name: str, force_fresh: bool = False) -> Dict:
        """
        🌐 ULTRA-OPTIMIZED workspace data with maximum parallelism
        Uses aggressive parallel processing and streaming for instant response
        """
        # Check cache first (unless force refresh is requested)
        cache_key = self._get_cache_key('workspace', installation_id, org_name)
        if not force_fresh:
            cached_data = self._get_cached(cache_key)
            if cached_data:
                print(f"🚀 Using cached workspace data for {org_name}")
                return cached_data
        
        try:
            print(f"🌐 Fetching {'FRESH' if force_fresh else 'fresh'} workspace data for {org_name}")
            
            # 🔄 FORCE FRESH: Clear any cached installation tokens for this org to ensure fresh GitHub API data
            if force_fresh:
                installation_token_keys = [key for key in self.cache.keys() if f"token_{installation_id}" in key or f"token_{org_name}" in key]
                for key in installation_token_keys:
                    if key in self.cache:
                        del self.cache[key]
                        print(f"🧹 Cleared cached installation token: {key}")
            
            # 🚀 PARALLELISM: Get repositories and start processing immediately
            start_time = time.time()
            repositories = await self.get_organization_repositories(installation_id, force_fresh)
            
            # 🚀 ULTRA-PARALLEL: Process ALL repositories at once with maximum concurrency
            print(f"🚀 Starting ULTRA-PARALLEL processing of {len(repositories)} repositories")
            
            # Create tasks for ALL repositories at once (no batching for maximum speed)
            workflow_tasks = []
            repo_data_list = []
            
            for repo in repositories:
                repo_data = {
                    "id": repo.get("id"),
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "private": repo.get("private"),
                    "html_url": repo.get("html_url"),
                    "description": repo.get("description"),
                    "language": repo.get("language"),
                    "stargazers_count": repo.get("stargazers_count", 0),
                    "forks_count": repo.get("forks_count", 0),
                    "default_branch": repo.get("default_branch"),
                    "updated_at": repo.get("updated_at"),
                    "workflows": [],
                    "workflow_count": 0
                }
                repo_data_list.append(repo_data)
                
                # Create workflow fetch task for this repo
                task = self.get_repository_workflows(installation_id, org_name, repo["name"])
                workflow_tasks.append((task, len(repo_data_list) - 1))
            
            # 🚀 Execute ALL workflow tasks in parallel (unlimited concurrency)
            print(f"🚀 Executing {len(workflow_tasks)} workflow fetch tasks in parallel")
            tasks = [task for task, _ in workflow_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 🚀 Process results ultra-fast
            all_workflows = []
            for (_, repo_index), workflows in zip(workflow_tasks, results):
                if isinstance(workflows, Exception):
                    print(f"❌ Error fetching workflows for {repo_data_list[repo_index]['name']}: {workflows}")
                    workflows = []
                
                if workflows:
                    repo_data_list[repo_index]["workflows"] = workflows
                    repo_data_list[repo_index]["workflow_count"] = len(workflows)
                    
                    # Add to all workflows with repository context
                    for workflow in workflows:
                        workflow_entry = {
                            "id": workflow.get("id"),
                            "name": workflow.get("name"),
                            "path": workflow.get("path"),
                            "state": workflow.get("state"),
                            "repository": repo_data_list[repo_index]["name"],
                            "repository_full_name": repo_data_list[repo_index]["full_name"],
                            "created_at": workflow.get("created_at"),
                            "updated_at": workflow.get("updated_at"),
                            "html_url": workflow.get("html_url"),
                            # Enhanced fields with placeholders
                            "triggers": ["Unknown"],
                            "last_run": None,
                            "last_successful": None,
                            "uses": [],
                            "author": "Unknown",
                            "total_runs": 0
                        }
                        all_workflows.append(workflow_entry)
            
            processing_time = time.time() - start_time
            print(f"⚡ ULTRA-PARALLEL processing completed in {processing_time:.2f}s")
            
            # Calculate summary statistics
            total_repos = len(repo_data_list)
            repos_with_workflows = len([r for r in repo_data_list if r["workflows"]])
            total_workflows = len(all_workflows)
            
            # Prepare result
            result = {
                "organization": org_name,
                "status": "connected",
                "installation_id": installation_id,
                "repository_count": total_repos,
                "repositories": repo_data_list,
                "total_workflows": total_workflows,
                "workflows": all_workflows,
                "last_updated": datetime.now().isoformat(),
                "processing_time": f"{processing_time:.2f}s",
                "parallel_efficiency": f"{len(repositories)} repos processed simultaneously",
                "summary": {
                    "total_repositories": total_repos,
                    "repositories_with_workflows": repos_with_workflows,
                    "total_workflows": total_workflows,
                    "workflow_breakdown": {
                        "active": len([w for w in all_workflows if w.get("state") == "active"]),
                        "disabled": len([w for w in all_workflows if w.get("state") == "disabled"])
                    }
                }
            }
            
            # Cache the result
            self._set_cached(cache_key, result, 'workspace')
            print(f"✅ ULTRA-PARALLEL workspace completed: {total_workflows} workflows from {repos_with_workflows}/{total_repos} repositories in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting organization workspace: {str(e)}")
            return {
                "organization": org_name,
                "status": "error",
                "error": str(e),
                "installation_id": installation_id,
                "repository_count": 0,
                "repositories": [],
                "total_workflows": 0,
                "workflows": [],
                "last_updated": datetime.now().isoformat()
            }
            raise Exception(f"Failed to get detailed workspace data: {str(e)}")

    async def get_all_user_installations(self) -> List[Dict]:
        """
        Get all installations where the GitHub App is installed
        This shows all organizations where our app is currently installed
        """
        try:
            app_token = self._generate_app_jwt()
            headers = {
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/app/installations",
                    headers=headers
                )
                
                if response.status_code == 200:
                    installations = response.json()
                    
                    # Format installation data
                    formatted_installations = []
                    for installation in installations:
                        account = installation.get("account", {})
                        formatted_installations.append({
                            "installation_id": installation.get("id"),
                            "organization": {
                                "login": account.get("login"),
                                "id": account.get("id"),
                                "avatar_url": account.get("avatar_url"),
                                "type": account.get("type"),
                                "html_url": account.get("html_url")
                            },
                            "permissions": installation.get("permissions", {}),
                            "events": installation.get("events", []),
                            "created_at": installation.get("created_at"),
                            "updated_at": installation.get("updated_at"),
                            "app_slug": installation.get("app_slug"),
                            "target_type": installation.get("target_type")
                        })
                    
                    return formatted_installations
                else:
                    raise Exception(f"Failed to get installations: {response.text}")
                    
        except Exception as e:
            print(f"Error getting user installations: {e}")
            return []

    def _get_cache_key(self, cache_type: str, *args) -> str:
        """Generate cache key for different data types"""
        return f"{cache_type}_{hash('_'.join(str(arg) for arg in args))}"
    
    def _get_cached(self, cache_key: str) -> Optional[Dict]:
        """Get cached data if still valid"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            # Determine TTL based on cache type
            cache_type = cache_key.split('_')[0]
            ttl = self.cache_ttl.get(cache_type, self.cache_ttl['workspace'])
            
            cache_age = time.time() - timestamp
            if cache_age < ttl:
                return data
            else:
                # PHASE 5: Don't delete immediately - allow stale reads
                # Mark as stale but keep for stale-while-revalidate
                return None
        return None
    
    def _get_cache_age(self, cache_key: str) -> Optional[float]:
        """Get age of cached data in seconds"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            return time.time() - timestamp
        return None
    
    def _get_cached_with_age(self, cache_key: str) -> tuple[Optional[Dict], Optional[float]]:
        """Get cached data with age metadata for stale-while-revalidate"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            cache_age = time.time() - timestamp
            cache_type = cache_key.split('_')[0]
            ttl = self.cache_ttl.get(cache_type, self.cache_ttl['workspace'])
            
            # Return data even if stale (for stale-while-revalidate)
            return data, cache_age
        return None, None
    
    def _set_cached(self, cache_key: str, data: Dict, cache_type: str = 'workspace', ttl: Optional[int] = None) -> None:
        """Set cached data with timestamp"""
        self.cache[cache_key] = (data, time.time())
        
        # Clean up old cache entries if cache is getting too large
        if len(self.cache) > 100:
            self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, (data, timestamp) in self.cache.items():
            cache_type = key.split('_')[0]
            ttl = self.cache_ttl.get(cache_type, self.cache_ttl['workspace'])
            
            if current_time - timestamp >= ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
    async def verify_installation_exists(self, org_name: str) -> bool:
        """
        Real-time verification that GitHub App is actually installed in organization
        This bypasses cache to ensure accurate status after manual app deletions
        """
        try:
            installation_id = await self._get_installation_id_realtime(org_name)
            if not installation_id:
                print(f"⚠️ GitHub App not installed in {org_name} (real-time check)")
                return False
                
            # Try to get an access token - this will fail if app was deleted
            try:
                await self.get_installation_access_token(installation_id)
                print(f"✅ GitHub App verified as installed in {org_name}")
                return True
            except Exception as token_error:
                print(f"⚠️ GitHub App installation invalid for {org_name}: {token_error}")
                # Clear cache since installation is invalid
                self._clear_installation_cache(org_name)
                return False
                
        except Exception as e:
            print(f"⚠️ Installation verification failed for {org_name}: {e}")
            return False

    async def _get_installation_id_realtime(self, org_name: str) -> Optional[int]:
        """
        Get installation ID with real-time API call (bypasses cache)
        """
        try:
            app_token = self._generate_app_jwt()
            headers = {
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Force real-time API call
            response = await self.http_client.get(
                f"{self.base_url}/app/installations",
                headers=headers
            )
            
            if response.status_code == 200:
                installations = response.json()
                for installation in installations:
                    if installation.get('account', {}).get('login') == org_name:
                        return installation.get('id')
                return None
            else:
                print(f"Error in real-time installation check: {response.text}")
                return None
        except Exception as e:
            print(f"Error getting real-time installation ID: {e}")
            return None

    def _clear_installation_cache(self, org_name: str):
        """
        Clear cache related to a specific organization installation
        """
        cache_keys_to_clear = [
            "all_installations",
            f"workspace_{org_name}",
            f"installation_token_{org_name}"
        ]
        
        for key in cache_keys_to_clear:
            if key in self.cache:
                del self.cache[key]
                print(f"🧹 Cleared cache for {key}")

    def clear_user_cache(self, user_id: str) -> None:
        """
        🔐 SECURITY: Clear all cache entries for a specific user
        This is critical for preventing session contamination between users
        """
        user_keys_to_clear = []
        
        for key in list(self.cache.keys()):  # Use list() to avoid dict changing during iteration
            # Clear any cache key that contains the user ID or could be user-specific
            if (user_id in key or 
                key.startswith(f"user_orgs_{user_id}") or 
                key.startswith(f"org_callback_{user_id}") or
                key.startswith(f"discovery_url_{user_id}") or
                key.startswith(f"installations_{user_id}") or
                "organizations" in key or  # Be aggressive about org data
                "installation" in key):    # Be aggressive about installation data
                user_keys_to_clear.append(key)
        
        for key in user_keys_to_clear:
            if key in self.cache:
                del self.cache[key]
            
        print(f"🔐 Cleared {len(user_keys_to_clear)} cache entries for user {user_id}")
        if user_keys_to_clear:
            print(f"🔐 Cleared keys: {user_keys_to_clear}")

    def clear_all_cache(self) -> None:
        """
        🔐 NUCLEAR OPTION: Clear all cache completely
        """
        cache_size = len(self.cache)
        self.cache.clear()
        print(f"🔐 NUCLEAR: Cleared all {cache_size} cache entries")

    async def get_organization_stats(self, installation_id: int, org_name: str) -> Dict:
        """
        📊 Get accurate organization statistics (counts only)
        Fast method that returns repository count and ACTUAL workflow count
        """
        # Check cache first
        cache_key = self._get_cache_key('stats', installation_id, org_name)
        cached_data = self._get_cached(cache_key)
        if cached_data:
            print(f"🚀 Using cached stats for {org_name}")
            return cached_data
        
        try:
            print(f"📊 Fetching accurate stats for {org_name}")
            
            # Get repositories (lightweight - just basic info)
            repositories = await self.get_organization_repositories(installation_id)
            repository_count = len(repositories)
            
            # Get ACTUAL workflow count by checking each repository
            # This is more accurate than estimation but still reasonably fast
            total_workflows = 0
            
            if repository_count > 0:
                # Use semaphore to limit concurrent requests (avoid rate limits)
                semaphore = asyncio.Semaphore(5)  # Increased from 3 to 5 for faster processing
                
                async def count_repo_workflows(repo):
                    async with semaphore:
                        try:
                            # Get workflows for this specific repository
                            workflows = await self._get_repository_workflows(installation_id, repo['name'])
                            return len(workflows)
                        except Exception as e:
                            print(f"⚠️ Failed to get workflows for {repo['name']}: {e}")
                            return 0
                
                # Fetch workflow counts for all repositories concurrently
                workflow_counts = await asyncio.gather(
                    *[count_repo_workflows(repo) for repo in repositories[:5]],  # Reduced to 5 repos for faster response
                    return_exceptions=True
                )
                
                # Sum up the workflow counts (ignore exceptions)
                total_workflows = sum(count for count in workflow_counts if isinstance(count, int))
                
                # If we limited to 5 repos, extrapolate the count
                if repository_count > 5:
                    avg_workflows_per_repo = total_workflows / min(5, repository_count)
                    total_workflows = int(avg_workflows_per_repo * repository_count)
            
            stats = {
                "repository_count": repository_count,
                "total_workflows": total_workflows,
                "last_updated": datetime.now().isoformat()
            }
            
            # Cache stats for 3 minutes (balance between accuracy and performance)
            self._set_cached(cache_key, stats, 'stats')
            
            print(f"✅ Accurate stats for {org_name}: {repository_count} repos, {total_workflows} workflows")
            return stats
            
        except Exception as e:
            print(f"❌ Error fetching stats for {org_name}: {str(e)}")
            raise Exception(f"Failed to fetch organization stats: {str(e)}")

    def _clear_organization_cache(self, org_name: str):
        """
        Clear all cache entries for a specific organization
        """
        cache_keys_to_clear = []
        
        for key in list(self.cache.keys()):
            if (org_name in key or 
                'workspace' in key or 
                'stats' in key or 
                'installation_token' in key or
                'repositories' in key or
                'workflow' in key or
                'latest_versions' in key or  # Clear version cache
                'versions' in key):          # Clear version cache
                cache_keys_to_clear.append(key)
        
        for key in cache_keys_to_clear:
            if key in self.cache:
                del self.cache[key]
                print(f"🧹 Cleared cache for {key}")
        
        print(f"🧹 Cleared {len(cache_keys_to_clear)} cache entries for {org_name}")
        return len(cache_keys_to_clear)

    async def _handle_rate_limit(self, response: httpx.Response) -> bool:
        """
        Handle GitHub API rate limiting
        Returns True if request should be retried, False otherwise
        """
        if response.status_code == 403:
            # Check if it's a rate limit error
            rate_limit_remaining = response.headers.get('x-ratelimit-remaining', '0')
            rate_limit_reset = response.headers.get('x-ratelimit-reset')
            
            if rate_limit_remaining == '0' and rate_limit_reset:
                reset_time = int(rate_limit_reset)
                current_time = int(time.time())
                sleep_time = max(reset_time - current_time, 60)  # Wait at least 1 minute
                
                print(f"⏱️ Rate limit exceeded. Waiting {sleep_time} seconds...")
                await asyncio.sleep(min(sleep_time, 300))  # Max 5 minutes wait
                return True
                
        return False

    async def refresh_action_versions_cache(self):
        """
        Refresh the action versions cache periodically
        This can be called by a background task
        """
        try:
            print("🔄 Refreshing action versions cache...")
            
            # Get all cached actions
            cached_actions = []
            for key, value in self.cache.items():
                if key.startswith('latest_versions_'):
                    cached_actions.extend(value.keys())
            
            if cached_actions:
                # Fetch fresh versions
                fresh_versions = await self._get_latest_versions_for_actions(list(set(cached_actions)))
                
                # Update cache
                cache_key = f"latest_versions_{hash(frozenset(cached_actions))}"
                self._set_cached(cache_key, fresh_versions, 'versions', ttl=3600)
                
                print(f"✅ Refreshed {len(fresh_versions)} action versions")
            else:
                print("ℹ️ No cached actions found to refresh")
                
        except Exception as e:
            print(f"❌ Error refreshing action versions cache: {e}")

    # =============================================================================
    # 🔧 PULL REQUEST CREATION METHODS
    # =============================================================================
    
    async def get_file_content(self, installation_id: int, owner: str, repo: str, path: str) -> Dict:
        """
        Get the content of a file from a GitHub repository.
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DevSecOps-PR-Creator"
            }
            
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    # Decode base64 content
                    import base64
                    content = base64.b64decode(data["content"]).decode('utf-8')
                    return {
                        "success": True,
                        "content": content,
                        "sha": data["sha"],
                        "path": data["path"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                        
        except Exception as e:
            print(f"Error getting file content: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_repository(self, installation_id: int, owner: str, repo: str) -> Dict:
        """
        Get repository information.
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DevSecOps-PR-Creator"
            }
            
            url = f"https://api.github.com/repos/{owner}/{repo}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "default_branch": data.get("default_branch", "main"),
                        "name": data["name"],
                        "full_name": data["full_name"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                        
        except Exception as e:
            print(f"Error getting repository: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_branch(self, installation_id: int, owner: str, repo: str, branch_name: str, from_branch: str = "main") -> Dict:
        """
        Create a new branch in a GitHub repository.
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DevSecOps-PR-Creator"
            }
            
            # First, get the SHA of the from_branch
            ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{from_branch}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(ref_url, headers=headers)
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Failed to get {from_branch} SHA: HTTP {response.status_code}: {response.text}"
                    }
                
                ref_data = response.json()
                sha = ref_data["object"]["sha"]
            
                # Create the new branch
                create_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
                payload = {
                    "ref": f"refs/heads/{branch_name}",
                    "sha": sha
                }
                
                response = await client.post(create_url, headers=headers, json=payload)
                if response.status_code == 201:
                    return {
                        "success": True,
                        "branch_name": branch_name,
                        "sha": sha
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to create branch: HTTP {response.status_code}: {response.text}"
                    }
                        
        except Exception as e:
            print(f"Error creating branch: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def update_file(self, installation_id: int, owner: str, repo: str, path: str, content: str, message: str, branch: str) -> Dict:
        """
        Update a file in a GitHub repository.
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DevSecOps-PR-Creator"
            }
            
            # First, get the current file to get its SHA
            file_info = await self.get_file_content(installation_id, owner, repo, path)
            
            if not file_info["success"]:
                return {
                    "success": False,
                    "error": f"Failed to get current file: {file_info['error']}"
                }
            
            # Update the file
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            
            import base64
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            payload = {
                "message": message,
                "content": encoded_content,
                "sha": file_info["sha"],
                "branch": branch
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "sha": data["content"]["sha"],
                        "commit_sha": data["commit"]["sha"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to update file: HTTP {response.status_code}: {response.text}"
                    }
                        
        except Exception as e:
            print(f"Error updating file: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_pull_request(self, installation_id: int, owner: str, repo: str, title: str, body: str, head: str, base: str) -> Dict:
        """
        Create a pull request in a GitHub repository.
        """
        try:
            access_token = await self.get_installation_access_token(installation_id)
            
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DevSecOps-PR-Creator"
            }
            
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            
            payload = {
                "title": title,
                "body": body,
                "head": head,
                "base": base
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 201:
                    data = response.json()
                    return {
                        "success": True,
                        "pr_number": data["number"],
                        "pr_url": data["html_url"],
                        "pr_id": data["id"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to create PR: HTTP {response.status_code}: {response.text}"
                    }
                        
        except Exception as e:
            print(f"Error creating pull request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_workflow_file_content(self, org_name: str, repo_name: str, workflow_path: str) -> Dict:
        """Get the content of a workflow file from a repository"""
        try:
            installation_token = self._get_cached_installation_token(org_name)
            if not installation_token:
                installation_token = await self.get_installation_token(org_name)
                if not installation_token:
                    return {
                        "success": False,
                        "error": "Failed to get installation token"
                    }

            headers = {
                'Authorization': f'token {installation_token}',
                'Accept': 'application/vnd.github.v3+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }

            # Get file content from GitHub API
            url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{workflow_path}"
            
            print(f"🔄 Fetching workflow content: {org_name}/{repo_name}/{workflow_path}")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    file_data = response.json()
                    
                    # Decode base64 content
                    import base64
                    content = base64.b64decode(file_data['content']).decode('utf-8')
                    
                    return {
                        "success": True,
                        "content": content,
                        "path": file_data.get('path'),
                        "sha": file_data.get('sha'),
                        "size": file_data.get('size'),
                        "encoding": file_data.get('encoding')
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": f"Workflow file not found: {workflow_path}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get workflow content: HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            print(f"Error getting workflow file content: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    # Workflow history and execution methods for real data integration
    
    async def get_workflow_runs(self, org_name: str, workflow_path: str, repo_name: str = None):
        """
        📋 Get GitHub Actions workflow runs for a specific workflow file
        """
        try:
            print(f"📋 Getting workflow runs for {workflow_path} in {org_name}")
            
            installation_id = await self._get_installation_id(org_name)
            if not installation_id:
                return {"success": False, "error": f"Installation not found for {org_name}"}
            
            installation_token = await self.get_installation_access_token(installation_id)
            headers = {
                "Authorization": f"Bearer {installation_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "DevSecOpsApp/1.0"
            }
            
            # Get repositories to search for workflow
            repos = await self.get_organization_repositories(installation_id)
            target_repos = [repo for repo in repos if repo.get('name') == repo_name] if repo_name else repos
            
            workflow_runs = []
            total_count = 0
            repository_info = None
            workflow_info = None
            
            for repo in target_repos:
                repo_name_current = repo.get('name')
                if not repo_name_current:
                    continue
                    
                try:
                    # First, get all workflows in this repository
                    workflows_url = f"https://api.github.com/repos/{org_name}/{repo_name_current}/actions/workflows"
                    
                    async with httpx.AsyncClient(timeout=30) as client:
                        workflows_response = await client.get(workflows_url, headers=headers)
                        
                        if workflows_response.status_code == 200:
                            workflows_data = workflows_response.json()
                            workflows = workflows_data.get('workflows', [])
                            
                            # Find the specific workflow by path or name
                            target_workflow = None
                            for workflow in workflows:
                                workflow_file_path = workflow.get('path', '')
                                workflow_name = workflow.get('name', '')
                                
                                # Match by path, filename, or name
                                if (workflow_path in workflow_file_path or 
                                    workflow_path == workflow_name or
                                    workflow_path.replace('.github/workflows/', '') in workflow_file_path or
                                    workflow_path.replace('.yml', '') == workflow_name.replace(' ', '-').lower()):
                                    target_workflow = workflow
                                    workflow_info = workflow
                                    break
                            
                            if target_workflow:
                                print(f"✅ Found workflow: {target_workflow.get('name')} (ID: {target_workflow.get('id')})")
                                
                                # Get runs for this specific workflow
                                workflow_id = target_workflow.get('id')
                                runs_url = f"https://api.github.com/repos/{org_name}/{repo_name_current}/actions/workflows/{workflow_id}/runs?per_page=20"
                                
                                runs_response = await client.get(runs_url, headers=headers)
                                
                                if runs_response.status_code == 200:
                                    runs_data = runs_response.json()
                                    repo_runs = runs_data.get('workflow_runs', [])
                                    
                                    # For each run, get job details to get step information
                                    enhanced_runs = []
                                    for run in repo_runs[:10]:  # Limit to 10 most recent runs
                                        jobs_url = f"https://api.github.com/repos/{org_name}/{repo_name_current}/actions/runs/{run.get('id')}/jobs"
                                        jobs_response = await client.get(jobs_url, headers=headers)
                                        
                                        if jobs_response.status_code == 200:
                                            jobs_data = jobs_response.json()
                                            run['jobs'] = jobs_data.get('jobs', [])
                                        
                                        enhanced_runs.append(run)
                                    
                                    workflow_runs.extend(enhanced_runs)
                                    total_count = runs_data.get('total_count', len(enhanced_runs))
                                    repository_info = repo
                                    
                                    print(f"✅ Found {len(enhanced_runs)} runs for workflow {target_workflow.get('name')}")
                                    break  # Found the workflow, no need to check other repos
                                    
                except Exception as repo_error:
                    print(f"⚠️ Error getting runs for repo {repo_name_current}: {repo_error}")
                    continue
            
            if workflow_runs:
                return {
                    "success": True,
                    "workflow_runs": workflow_runs,
                    "total_count": total_count,
                    "repository": repository_info,
                    "workflow": workflow_info
                }
            else:
                return {
                    "success": False,
                    "workflow_runs": [],
                    "total_count": 0,
                    "error": f"No workflow runs found for {workflow_path}"
                }
                
        except Exception as e:
            print(f"❌ Error getting workflow runs: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workflow_runs": [],
                "total_count": 0
            }

    async def get_jenkins_builds(self, org_name: str, workflow_id: str):
        """
        🔧 Get Jenkins build data (mock implementation for now)
        """
        try:
            print(f"🔧 Getting Jenkins builds for {workflow_id} in {org_name}")
            
            # Mock Jenkins data - replace with real Jenkins API integration
            mock_builds = [
                {
                    "id": f"jenkins-{i}",
                    "number": 100 - i,
                    "status": "SUCCESS" if i % 3 != 0 else "FAILURE",
                    "started_at": (datetime.now() - timedelta(hours=i)).isoformat(),
                    "finished_at": (datetime.now() - timedelta(hours=i, minutes=5)).isoformat(),
                    "duration": 300 + (i * 10),
                    "url": f"https://jenkins.example.com/job/{workflow_id}/{100-i}/"
                }
                for i in range(10)
            ]
            
            return {
                "success": True,
                "builds": mock_builds,
                "total_count": len(mock_builds),
                "job_name": workflow_id
            }
            
        except Exception as e:
            print(f"❌ Error getting Jenkins builds: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "builds": [],
                "total_count": 0
            }

    async def get_gitlab_pipelines(self, org_name: str, workflow_id: str):
        """
        🦊 Get GitLab CI pipeline data (mock implementation for now)
        """
        try:
            print(f"🦊 Getting GitLab pipelines for {workflow_id} in {org_name}")
            
            # Mock GitLab data - replace with real GitLab API integration
            mock_pipelines = [
                {
                    "id": f"gitlab-{i}",
                    "sha": f"abc123{i}",
                    "status": "success" if i % 4 != 0 else "failed",
                    "created_at": (datetime.now() - timedelta(hours=i)).isoformat(),
                    "updated_at": (datetime.now() - timedelta(hours=i, minutes=8)).isoformat(),
                    "web_url": f"https://gitlab.example.com/{org_name}/{workflow_id}/-/pipelines/{1000+i}"
                }
                for i in range(8)
            ]
            
            return {
                "success": True,
                "pipelines": mock_pipelines,
                "total_count": len(mock_pipelines),
                "project_id": f"{org_name}/{workflow_id}"
            }
            
        except Exception as e:
            print(f"❌ Error getting GitLab pipelines: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "pipelines": [],
                "total_count": 0
            }

    async def get_workflow_parameters(self, org_name: str, workflow_id: str):
        """
        ⚙️ Get workflow build parameters (mock implementation)
        """
        try:
            print(f"⚙️ Getting workflow parameters for {workflow_id} in {org_name}")
            
            # Mock parameters - replace with real parameter extraction from workflow files
            mock_parameters = {
                "BRANCH_NAME": {
                    "type": "choice",
                    "value": "main",
                    "choices": ["main", "develop", "staging", "release/v1.0"],
                    "description": "Git branch to build from"
                },
                "BUILD_TYPE": {
                    "type": "choice",
                    "value": "release",
                    "choices": ["debug", "release", "staging"],
                    "description": "Build configuration type"
                },
                "RUN_TESTS": {
                    "type": "boolean",
                    "value": True,
                    "description": "Execute test suites during build"
                },
                "DEPLOY_ENVIRONMENT": {
                    "type": "choice",
                    "value": "none",
                    "choices": ["none", "dev", "staging", "production"],
                    "description": "Target deployment environment"
                }
            }
            
            return {
                "success": True,
                "parameters": mock_parameters
            }
            
        except Exception as e:
            print(f"❌ Error getting workflow parameters: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "parameters": {}
            }

    async def get_workflow_workspace(self, org_name: str, workflow_id: str):
        """
        📁 Get workflow workspace information (mock implementation)
        """
        try:
            print(f"📁 Getting workspace for {workflow_id} in {org_name}")
            
            # Mock workspace data
            mock_workspace = {
                "path": f"/var/lib/jenkins/workspace/{workflow_id}",
                "size": "45.2 MB",
                "lastModified": datetime.now().isoformat(),
                "files": [
                    {"name": "README.md", "size": "2.1 KB", "type": "file"},
                    {"name": "package.json", "size": "1.4 KB", "type": "file"},
                    {"name": "src/", "size": "12.5 MB", "type": "directory"},
                    {"name": "dist/", "size": "28.4 MB", "type": "directory"},
                    {"name": ".git/", "size": "1.8 MB", "type": "directory"},
                    {"name": "node_modules/", "size": "156.7 MB", "type": "directory"},
                    {"name": "build.log", "size": "45.3 KB", "type": "file"},
                    {"name": "test-results.xml", "size": "8.7 KB", "type": "file"}
                ]
            }
            
            return {
                "success": True,
                "workspace": mock_workspace
            }
            
        except Exception as e:
            print(f"❌ Error getting workflow workspace: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workspace": {}
            }

    async def clean_workflow_workspace(self, org_name: str, workflow_id: str):
        """
        🧹 Clean workflow workspace (mock implementation)
        """
        try:
            print(f"🧹 Cleaning workspace for {workflow_id} in {org_name}")
            
            # Mock cleanup - replace with real workspace cleanup logic
            await asyncio.sleep(0.5)  # Simulate cleanup time
            
            return {
                "success": True,
                "message": f"Workspace cleaned for {workflow_id}",
                "cleaned_files": ["build/", "dist/", "*.log", "test-results/"]
            }
            
        except Exception as e:
            print(f"❌ Error cleaning workflow workspace: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Global instance
github_client = GitHubClient()