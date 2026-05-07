import jwt
import time
import os
from dotenv import load_dotenv

load_dotenv()

class GitHubAppJWT:
    def __init__(self):
        self.app_id = os.getenv("GITHUB_APP_ID")
        self.private_key_path = os.getenv("GITHUB_PRIVATE_KEY_PATH")
        
        if not self.app_id:
            raise ValueError("GITHUB_APP_ID not found in environment variables")
        if not self.private_key_path:
            raise ValueError("GITHUB_PRIVATE_KEY_PATH not found in environment variables")
    
    def _load_private_key(self) -> str:
        """Load GitHub App private key from file"""
        try:
            with open(self.private_key_path, 'r') as key_file:
                return key_file.read()
        except FileNotFoundError:
            raise Exception(f"Private key file not found: {self.private_key_path}")
    
    def generate_jwt_token(self) -> str:
        """Generate JWT token for GitHub App authentication"""
        now = int(time.time())
        payload = {
            'iat': now,  # Issued at time
            'exp': now + (10 * 60),  # Expires in 10 minutes
            'iss': int(self.app_id)  # GitHub App ID (must be integer)
        }
        
        private_key = self._load_private_key()
        token = jwt.encode(payload, private_key, algorithm='RS256')
        return token

# Global instance
github_jwt = GitHubAppJWT()