"""
Semantic Version Manager for GitHub Actions Updates
Handles proper semantic versioning (major.minor.patch) with production-grade recommendations
"""

import re
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class VersionType(Enum):
    """Types of version references in GitHub Actions"""
    MAJOR_ONLY = "major"        # @v4
    MAJOR_MINOR = "major.minor" # @v4.1
    FULL_SEMANTIC = "full"      # @v4.1.2
    COMMIT_SHA = "sha"          # @abc123
    BRANCH = "branch"           # @main

@dataclass
class VersionInfo:
    """Information about a version"""
    original: str
    clean: str
    type: VersionType
    major: int
    minor: int
    patch: int
    is_prerelease: bool = False
    prerelease_suffix: str = ""

@dataclass
class VersionComparison:
    """Result of version comparison"""
    is_outdated: bool
    recommendation: str
    security_risk: str
    upgrade_reason: str
    current_info: VersionInfo
    latest_info: VersionInfo

class SemanticVersionManager:
    """
    Manages semantic versioning for GitHub Actions with production-grade recommendations
    """
    
    def __init__(self):
        self.version_pattern = re.compile(r'^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+](.+))?$')
    
    def parse_version(self, version_str: str) -> Optional[VersionInfo]:
        """
        Parse a version string into structured information.
        
        Examples:
        - 'v4' -> VersionInfo(major=4, minor=0, patch=0, type=MAJOR_ONLY)
        - 'v4.1' -> VersionInfo(major=4, minor=1, patch=0, type=MAJOR_MINOR)
        - 'v4.1.2' -> VersionInfo(major=4, minor=1, patch=2, type=FULL_SEMANTIC)
        - 'v4.1.2-alpha' -> VersionInfo(major=4, minor=1, patch=2, type=FULL_SEMANTIC, is_prerelease=True)
        """
        if not version_str:
            return None
            
        # Handle special cases
        if version_str.startswith('@'):
            version_str = version_str[1:]
            
        # Check for commit SHA (40 hex characters)
        if re.match(r'^[a-f0-9]{40}$', version_str):
            return VersionInfo(
                original=version_str,
                clean=version_str,
                type=VersionType.COMMIT_SHA,
                major=0, minor=0, patch=0
            )
            
        # Check for branch names (common ones)
        if version_str in ['main', 'master', 'develop', 'dev']:
            return VersionInfo(
                original=version_str,
                clean=version_str,
                type=VersionType.BRANCH,
                major=0, minor=0, patch=0
            )
        
        # Parse semantic version
        match = self.version_pattern.match(version_str)
        if not match:
            return None
            
        major_str, minor_str, patch_str, prerelease = match.groups()
        
        try:
            major = int(major_str)
            minor = int(minor_str) if minor_str else 0
            patch = int(patch_str) if patch_str else 0
            
            # Determine version type
            if not minor_str and not patch_str:
                version_type = VersionType.MAJOR_ONLY
            elif not patch_str:
                version_type = VersionType.MAJOR_MINOR
            else:
                version_type = VersionType.FULL_SEMANTIC
                
            return VersionInfo(
                original=version_str,
                clean=f"{major}.{minor}.{patch}",
                type=version_type,
                major=major,
                minor=minor,
                patch=patch,
                is_prerelease=bool(prerelease),
                prerelease_suffix=prerelease or ""
            )
            
        except ValueError:
            return None
    
    def compare_versions(self, current: str, latest: str) -> VersionComparison:
        """
        Compare two versions with production-grade recommendations.
        
        Production-grade logic:
        - Always recommend specific patch versions for security
        - Flag major-only versions as potential security risks
        - Provide clear upgrade reasoning
        """
        current_info = self.parse_version(current)
        latest_info = self.parse_version(latest)
        
        if not current_info or not latest_info:
            return VersionComparison(
                is_outdated=True,
                recommendation="⚠️ Unable to parse version",
                security_risk="🔒 Unknown security status",
                upgrade_reason="Version parsing failed",
                current_info=current_info,
                latest_info=latest_info
            )
        
        # Handle special cases
        if current_info.type in [VersionType.COMMIT_SHA, VersionType.BRANCH]:
            return VersionComparison(
                is_outdated=True,
                recommendation="🔧 Upgrade to specific version",
                security_risk="🔒 HIGH: Using unstable reference",
                upgrade_reason="Commit SHA or branch references are unstable and insecure",
                current_info=current_info,
                latest_info=latest_info
            )
        
        # Compare versions numerically
        current_tuple = (current_info.major, current_info.minor, current_info.patch)
        latest_tuple = (latest_info.major, latest_info.minor, latest_info.patch)
        
        is_outdated = current_tuple < latest_tuple
        
        # Production-grade recommendations
        if current_info.type == VersionType.MAJOR_ONLY:
            # Major-only versions like @v4 are flexible but less secure
            if current_info.major < latest_info.major:
                return VersionComparison(
                    is_outdated=True,
                    recommendation="🚨 MAJOR UPGRADE NEEDED",
                    security_risk="🔒 HIGH: Using outdated major version",
                    upgrade_reason=f"Major version {current_info.major} is behind latest {latest_info.major}",
                    current_info=current_info,
                    latest_info=latest_info
                )
            else:
                return VersionComparison(
                    is_outdated=True,  # Always recommend upgrading to specific version
                    recommendation="🔧 UPGRADE TO SPECIFIC VERSION",
                    security_risk="🔒 MEDIUM: Using flexible version",
                    upgrade_reason=f"Pin to specific version {latest} for better security and stability",
                    current_info=current_info,
                    latest_info=latest_info
                )
        
        elif current_info.type == VersionType.MAJOR_MINOR:
            # Major.minor versions like @v4.1 are better but still flexible
            if current_info.major < latest_info.major:
                return VersionComparison(
                    is_outdated=True,
                    recommendation="🚨 MAJOR UPGRADE NEEDED",
                    security_risk="🔒 HIGH: Using outdated major version",
                    upgrade_reason=f"Major version {current_info.major} is behind latest {latest_info.major}",
                    current_info=current_info,
                    latest_info=latest_info
                )
            elif current_info.major == latest_info.major and current_info.minor < latest_info.minor:
                return VersionComparison(
                    is_outdated=True,
                    recommendation="🔧 MINOR UPGRADE AVAILABLE",
                    security_risk="🔒 MEDIUM: Using older minor version",
                    upgrade_reason=f"Minor version {current_info.minor} is behind latest {latest_info.minor}",
                    current_info=current_info,
                    latest_info=latest_info
                )
            else:
                return VersionComparison(
                    is_outdated=True,  # Always recommend upgrading to specific patch version
                    recommendation="🔧 UPGRADE TO SPECIFIC VERSION",
                    security_risk="🔒 LOW: Consider pinning to patch version",
                    upgrade_reason=f"Pin to specific version {latest} for better security and stability",
                    current_info=current_info,
                    latest_info=latest_info
                )
        
        else:  # FULL_SEMANTIC
            # Full semantic versions are the gold standard
            if is_outdated:
                if current_info.major < latest_info.major:
                    return VersionComparison(
                        is_outdated=True,
                        recommendation="🚨 MAJOR UPGRADE NEEDED",
                        security_risk="🔒 HIGH: Using outdated major version",
                        upgrade_reason=f"Major version {current_info.major} is behind latest {latest_info.major}",
                        current_info=current_info,
                        latest_info=latest_info
                    )
                elif current_info.minor < latest_info.minor:
                    return VersionComparison(
                        is_outdated=True,
                        recommendation="🔧 MINOR UPGRADE AVAILABLE",
                        security_risk="🔒 MEDIUM: Using older minor version",
                        upgrade_reason=f"Minor version {current_info.minor} is behind latest {latest_info.minor}",
                        current_info=current_info,
                        latest_info=latest_info
                    )
                else:
                    return VersionComparison(
                        is_outdated=True,
                        recommendation="🔧 PATCH UPGRADE AVAILABLE",
                        security_risk="🔒 LOW: Patch update available",
                        upgrade_reason=f"Patch version {current_info.patch} is behind latest {latest_info.patch}",
                        current_info=current_info,
                        latest_info=latest_info
                    )
            else:
                return VersionComparison(
                    is_outdated=False,
                    recommendation="✅ UP TO DATE",
                    security_risk="🔒 SECURE: Using latest version",
                    upgrade_reason="Version is current",
                    current_info=current_info,
                    latest_info=latest_info
                )
    
    def get_upgrade_recommendations(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a list of actions and provide upgrade recommendations.
        
        Returns categorized recommendations by security risk level.
        """
        recommendations = {
            "critical": [],    # Major version upgrades
            "high": [],        # Security-related upgrades
            "medium": [],      # Minor version upgrades
            "low": [],         # Patch upgrades
            "info": []         # Recommendations for better practices
        }
        
        for action in actions:
            current_version = action.get("current_version", "")
            latest_version = action.get("latest_version", "")
            action_name = action.get("action_name", "")
            
            comparison = self.compare_versions(current_version, latest_version)
            
            recommendation_item = {
                "action_name": action_name,
                "current_version": current_version,
                "latest_version": latest_version,
                "comparison": comparison,
                "workflow_path": action.get("workflow_path", ""),
                "repo_name": action.get("repo_name", "")
            }
            
            if "MAJOR UPGRADE NEEDED" in comparison.recommendation:
                recommendations["critical"].append(recommendation_item)
            elif "HIGH" in comparison.security_risk:
                recommendations["high"].append(recommendation_item)
            elif "MEDIUM" in comparison.security_risk:
                recommendations["medium"].append(recommendation_item)
            elif "LOW" in comparison.security_risk:
                recommendations["low"].append(recommendation_item)
            else:
                recommendations["info"].append(recommendation_item)
        
        return recommendations
    
    def generate_upgrade_summary(self, recommendations: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of upgrade recommendations.
        """
        critical_count = len(recommendations["critical"])
        high_count = len(recommendations["high"])
        medium_count = len(recommendations["medium"])
        low_count = len(recommendations["low"])
        info_count = len(recommendations["info"])
        
        total_actions = critical_count + high_count + medium_count + low_count + info_count
        
        if total_actions == 0:
            return "✅ All actions are up to date!"
        
        summary_lines = [
            f"📊 **GitHub Actions Upgrade Summary** ({total_actions} actions analyzed)",
            ""
        ]
        
        if critical_count > 0:
            summary_lines.extend([
                f"🚨 **CRITICAL ({critical_count})**: Major version upgrades needed",
                "   → These actions are using outdated major versions and should be upgraded immediately"
            ])
        
        if high_count > 0:
            summary_lines.extend([
                f"🔒 **HIGH RISK ({high_count})**: Security-related upgrades",
                "   → These actions have security implications and should be upgraded soon"
            ])
        
        if medium_count > 0:
            summary_lines.extend([
                f"🔧 **MEDIUM ({medium_count})**: Minor version upgrades",
                "   → These actions have newer features and bug fixes available"
            ])
        
        if low_count > 0:
            summary_lines.extend([
                f"📦 **LOW ({low_count})**: Patch updates available",
                "   → These actions have small bug fixes and improvements"
            ])
        
        if info_count > 0:
            summary_lines.extend([
                f"💡 **INFO ({info_count})**: Best practice recommendations",
                "   → Consider pinning to specific versions for better security"
            ])
        
        summary_lines.extend([
            "",
            "🔐 **Production Best Practices:**",
            "• Use full semantic versions (e.g., `@v4.2.2`) instead of `@v4`",
            "• Pin to specific patch versions for maximum security and stability",
            "• Review changelogs before upgrading major versions",
            "• Test workflows after upgrades to ensure compatibility"
        ])
        
        return "\n".join(summary_lines)
