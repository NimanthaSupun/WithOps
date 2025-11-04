"""
Simple user token storage system with organization context
In production, this should be replaced with a proper database
"""

from typing import Optional, Dict, List
import time

# Simple in-memory storage (replace with database in production)
user_tokens: Dict[str, Dict] = {}
user_organizations: Dict[str, str] = {}  # user_id -> selected_org_name

# NEW: User-Organization Installation Mapping
user_installed_organizations: Dict[str, List[str]] = {}  # user_id -> [org_names]
organization_installers: Dict[str, str] = {}  # org_name -> user_id who installed it
installation_metadata: Dict[str, Dict] = {}  # org_name -> installation details

def store_user_github_token(user_id: str, access_token: str, user_info: Dict) -> None:
    """Store GitHub access token for a user"""
    user_tokens[user_id] = {
        "access_token": access_token,
        "user_info": user_info,
        "created_at": time.time(),
        "last_used": time.time()
    }
    # Initialize user's organization list if not exists
    if user_id not in user_installed_organizations:
        user_installed_organizations[user_id] = []
    print(f"✅ Stored GitHub token for user: {user_id}")

def get_user_github_token(user_id: str) -> Optional[str]:
    """Get GitHub access token for a user"""
    if user_id in user_tokens:
        user_tokens[user_id]["last_used"] = time.time()
        return user_tokens[user_id]["access_token"]
    return None

def get_user_github_info(user_id: str) -> Optional[Dict]:
    """Get stored GitHub user info"""
    if user_id in user_tokens:
        return user_tokens[user_id]["user_info"]
    return None

def user_has_github_token(user_id: str) -> bool:
    """Check if user has a GitHub token stored"""
    return user_id in user_tokens

def remove_user_github_token(user_id: str) -> bool:
    """Remove user's GitHub token"""
    if user_id in user_tokens:
        del user_tokens[user_id]
        
        # Also clean up user's organization installations
        user_orgs = get_user_installed_organizations(user_id)
        for org_name in user_orgs:
            # Remove this user's claim to the organization
            if organization_installers.get(org_name) == user_id:
                del organization_installers[org_name]
                if org_name in installation_metadata:
                    del installation_metadata[org_name]
        
        # Clear user's organization list
        if user_id in user_installed_organizations:
            del user_installed_organizations[user_id]
            
        print(f"🗑️ Removed GitHub token and organization access for user: {user_id}")
        return True
    return False

def set_user_current_organization(user_id: str, org_name: str) -> None:
    """Set the user's current selected organization workspace"""
    user_organizations[user_id] = org_name
    print(f"🏢 Set current organization for user {user_id}: {org_name}")

def get_user_current_organization(user_id: str) -> Optional[str]:
    """Get the user's currently selected organization workspace"""
    return user_organizations.get(user_id)

def clear_user_current_organization(user_id: str) -> None:
    """Clear the user's current organization selection"""
    if user_id in user_organizations:
        del user_organizations[user_id]
        print(f"🗑️ Cleared current organization for user: {user_id}")

def get_all_users_with_tokens() -> Dict[str, Dict]:
    """Get all users with GitHub tokens (for debugging)"""
    return {
        user_id: {
            "user_info": data["user_info"],
            "created_at": data["created_at"],
            "last_used": data["last_used"],
            "current_organization": user_organizations.get(user_id)
        }
        for user_id, data in user_tokens.items()
    }

"""
Simple user storage system with organization workspace context
In production, this should be replaced with a proper database
"""

# Simple in-memory storage (replace with database in production)
user_workspaces: Dict[str, Dict] = {}  # user_id -> workspace_info

class UserStorage:
    """User storage for workspace and GitHub App installation data"""
    
    def set_user_workspace(self, user_id: str, workspace_info: Dict) -> None:
        """Set the user's current organization workspace"""
        user_workspaces[user_id] = {
            **workspace_info,
            "created_at": time.time(),
            "last_used": time.time()
        }
        print(f"✅ Set workspace for user {user_id}: {workspace_info.get('organization')}")

    def get_user_workspace(self, user_id: str) -> Optional[Dict]:
        """Get user's current workspace info"""
        if user_id in user_workspaces:
            user_workspaces[user_id]["last_used"] = time.time()
            return user_workspaces[user_id]
        return None

    def clear_user_workspace(self, user_id: str) -> bool:
        """Clear user's current workspace"""
        if user_id in user_workspaces:
            del user_workspaces[user_id]
            print(f"🗑️ Cleared workspace for user: {user_id}")
            return True
        return False

    def has_user_workspace(self, user_id: str) -> bool:
        """Check if user has a workspace set"""
        return user_id in user_workspaces

    def store_discovered_organizations(self, user_id: str, organizations: List[Dict]) -> None:
        """Store discovered organizations for user"""
        if user_id not in user_workspaces:
            user_workspaces[user_id] = {}
        
        user_workspaces[user_id]["discovered_organizations"] = organizations
        user_workspaces[user_id]["discovery_time"] = time.time()
        print(f"✅ Stored {len(organizations)} discovered organizations for user {user_id}")

    def get_discovered_organizations(self, user_id: str) -> List[Dict]:
        """Get discovered organizations for user"""
        if user_id in user_workspaces and "discovered_organizations" in user_workspaces[user_id]:
            return user_workspaces[user_id]["discovered_organizations"]
        return []

# Global instance
user_storage = UserStorage()

# Legacy OAuth-based storage (will be removed)

# NEW: Organization Installation Management Functions

def record_organization_installation(user_id: str, org_name: str, installation_data: Dict) -> None:
    """Record that a user has installed the app in an organization"""
    # Track which user installed this organization
    organization_installers[org_name] = user_id
    
    # Add to user's list of installed organizations
    if user_id not in user_installed_organizations:
        user_installed_organizations[user_id] = []
    
    if org_name not in user_installed_organizations[user_id]:
        user_installed_organizations[user_id].append(org_name)
    
    # Store installation metadata
    installation_metadata[org_name] = {
        **installation_data,
        "installed_by": user_id,
        "installed_at": time.time()
    }
    
    print(f"🔐 Recorded installation: {org_name} installed by {user_id}")

def get_user_installed_organizations(user_id: str) -> List[str]:
    """Get list of organizations that this user has installed"""
    return user_installed_organizations.get(user_id, [])

def is_user_authorized_for_organization(user_id: str, org_name: str) -> bool:
    """Check if user is authorized to access this organization"""
    installer = organization_installers.get(org_name)
    return installer == user_id

def get_organization_installer(org_name: str) -> Optional[str]:
    """Get the user ID who installed this organization"""
    return organization_installers.get(org_name)

def remove_organization_installation(org_name: str) -> bool:
    """Remove organization installation (when app is uninstalled)"""
    installer = organization_installers.get(org_name)
    if installer:
        # Remove from user's list
        if installer in user_installed_organizations:
            user_installed_organizations[installer] = [
                org for org in user_installed_organizations[installer] 
                if org != org_name
            ]
        
        # Remove from global tracking
        del organization_installers[org_name]
        if org_name in installation_metadata:
            del installation_metadata[org_name]
        
        print(f"🗑️ Removed installation record for: {org_name}")
        return True
    return False
