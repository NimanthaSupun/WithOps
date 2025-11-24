"""
Redis Queue Configuration for Async Background Jobs
"""
from enum import Enum
from typing import TypedDict, Optional


class RefreshChannel(str, Enum):
    """Redis pub/sub channels for background refresh"""
    WORKSPACE_REFRESH = "github:workspace:refresh"
    ACTIONS_REFRESH = "github:actions:refresh"
    WORKFLOWS_REFRESH = "github:workflows:refresh"


class RefreshJobType(str, Enum):
    """Types of refresh jobs"""
    WORKSPACE_FULL = "workspace_full"
    ACTIONS_PAGINATED = "actions_paginated"
    WORKFLOWS_DETAILED = "workflows_detailed"


class RefreshMessage(TypedDict):
    """Schema for refresh job messages"""
    type: str  # RefreshJobType
    org_name: str
    user_id: Optional[str]
    timestamp: str
    params: dict  # Additional parameters (page, per_page, search, etc.)


# Default TTL for cached data (1 hour)
DEFAULT_CACHE_TTL = 3600

# Cache age threshold for background refresh (5 minutes)
REFRESH_THRESHOLD = 300
