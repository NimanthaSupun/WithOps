# Migration Guide: Adding user_id to Workspace Events

## Overview

The workspace-intelligence-service needs to emit `user_id` in all analysis events for the AI RAG service to properly isolate data per user.

## Changes Required

### 1. Extract user_id from JWT Token

Update your analysis endpoint to extract user_id from the JWT token:

```python
from fastapi import Header, HTTPException
from core.jwt_helper import decode_access_token  # Your existing JWT helper

@router.post("/analyze-workspace")
async def analyze_workspace(
    request: AnalysisRequest,
    authorization: str = Header(None)
):
    # Extract user_id from JWT token
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")

    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")  # Auth0 user ID from 'sub' claim

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

    # Continue with analysis...
    # Pass user_id to analysis functions
```

### 2. Update Event Emission

Modify the event publishing to include user_id:

**Before:**

```python
await event_bus.publish("workspace_intelligence_events", {
    "type": "workspace_analysis.completed",
    "data": {
        "organization_name": org_name,
        "project_name": project_name,
        "analysis_id": analysis_id,
        "tree_id": tree_id
    }
})
```

**After:**

```python
await event_bus.publish("workspace_intelligence_events", {
    "type": "workspace_analysis.completed",
    "data": {
        "user_id": user_id,  # NEW - Required for AI RAG service
        "organization_name": org_name,
        "project_name": project_name,
        "folder_path": folder_path,  # Optional - for folder analysis
        "analysis_scope": "folder",  # "unified" or "folder"
        "analysis_id": analysis_id,
        "tree_id": tree_id
    }
})
```

### 3. Update workspace_analyzer.py

If you have a workspace_analyzer.py or similar, update the analysis functions to accept and pass user_id:

```python
async def analyze_workspace(
    org_name: str,
    user_id: str,  # NEW parameter
    project_name: str = None,
    folder_path: str = None
):
    # ... analysis logic ...

    # Save to database with user_id
    await workspace_intelligence_db.save_project_analysis(
        org_name=org_name,
        user_id=user_id,  # NEW
        project_name=project_name,
        analysis_data=analysis_data
    )

    # Publish event with user_id
    await event_bus.publish("workspace_intelligence_events", {
        "type": "workspace_analysis.completed",
        "data": {
            "user_id": user_id,  # NEW
            "organization_name": org_name,
            "project_name": project_name,
            "folder_path": folder_path,
            "analysis_id": str(analysis_id),
            "tree_id": tree_id,
            "analysis_scope": "folder" if folder_path else "unified"
        }
    })
```

### 4. Update Database Schema (Optional)

If you want to track which user ran each analysis:

```sql
-- Add user_id column to project_analyses table
ALTER TABLE project_analyses
ADD COLUMN user_id VARCHAR(255);

-- Add index for faster queries
CREATE INDEX idx_project_analyses_user_id ON project_analyses(user_id);

-- Add combined index for common queries
CREATE INDEX idx_project_analyses_user_org ON project_analyses(user_id, organization_name);
```

### 5. Update API Routes

**File: services/workspace-intelligence-service/api/routes/workspace_intelligence.py**

```python
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

router = APIRouter()

@router.post("/analyze-workspace-unified")
async def analyze_workspace_unified(
    request: UnifiedAnalysisRequest,
    authorization: Optional[str] = Header(None)
):
    """Analyze entire workspace with user context"""

    # Extract user_id from JWT
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")

    token = authorization.replace("Bearer ", "")
    user_info = verify_jwt_token(token)  # Your JWT verification function
    user_id = user_info["user_id"]

    # Start analysis with user context
    analysis_result = await workspace_analyzer.analyze_workspace(
        org_name=request.org_name,
        user_id=user_id,
        project_name=None,
        folder_path=None
    )

    return analysis_result


@router.post("/analyze-folder")
async def analyze_folder(
    request: FolderAnalysisRequest,
    authorization: Optional[str] = Header(None)
):
    """Analyze specific folder with user context"""

    # Extract user_id from JWT
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")

    token = authorization.replace("Bearer ", "")
    user_info = verify_jwt_token(token)
    user_id = user_info["user_id"]

    # Start folder analysis with user context
    analysis_result = await workspace_analyzer.analyze_workspace(
        org_name=request.org_name,
        user_id=user_id,
        project_name=request.project_name,
        folder_path=request.folder_path
    )

    return analysis_result
```

## Complete Example

Here's a complete example showing the full flow:

```python
# File: services/workspace-intelligence-service/core/workspace_analyzer.py

import logging
from typing import Optional
from core.event_bus import event_bus
from database.operations import workspace_intelligence_db

logger = logging.getLogger(__name__)

async def analyze_workspace(
    org_name: str,
    user_id: str,
    project_name: Optional[str] = None,
    folder_path: Optional[str] = None
):
    """
    Analyze workspace/project/folder with user context
    """
    try:
        logger.info(f"Starting analysis for user {user_id}, org {org_name}")

        # Determine analysis scope
        if folder_path:
            analysis_scope = "folder"
            analysis_type = f"Folder: {folder_path}"
        elif project_name:
            analysis_scope = "project"
            analysis_type = f"Project: {project_name}"
        else:
            analysis_scope = "unified"
            analysis_type = "Unified Workspace"

        logger.info(f"Analysis scope: {analysis_scope}")

        # Perform analysis (your existing logic)
        analysis_data = await perform_analysis(
            org_name=org_name,
            project_name=project_name,
            folder_path=folder_path
        )

        # Save to database with user_id
        analysis_id = await workspace_intelligence_db.save_project_analysis(
            org_name=org_name,
            user_id=user_id,
            project_name=project_name,
            folder_path=folder_path,
            analysis_data=analysis_data,
            analysis_scope=analysis_scope
        )

        logger.info(f"Saved analysis {analysis_id}")

        # Publish event with user context
        event_data = {
            "type": "workspace_analysis.completed",
            "data": {
                "user_id": user_id,
                "organization_name": org_name,
                "project_name": project_name,
                "folder_path": folder_path,
                "analysis_id": str(analysis_id),
                "analysis_scope": analysis_scope,
                "tree_id": analysis_data.get("tree_id")
            }
        }

        await event_bus.publish("workspace_intelligence_events", event_data)

        logger.info(f"Published event for analysis {analysis_id}")

        return {
            "analysis_id": str(analysis_id),
            "status": "completed",
            "user_id": user_id,
            "organization": org_name,
            "analysis_type": analysis_type
        }

    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        raise
```

## Testing

### 1. Test Event Emission

```python
# Test that events include user_id
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_analysis_emits_user_id():
    # Mock event bus
    with patch('core.event_bus.event_bus.publish') as mock_publish:
        # Run analysis
        await analyze_workspace(
            org_name="test-org",
            user_id="auth0|123456",
            project_name="test-project"
        )

        # Verify event was published with user_id
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        event_data = call_args[0][1]

        assert event_data["type"] == "workspace_analysis.completed"
        assert event_data["data"]["user_id"] == "auth0|123456"
        assert event_data["data"]["organization_name"] == "test-org"
        assert event_data["data"]["project_name"] == "test-project"
```

### 2. Test JWT Extraction

```python
@pytest.mark.asyncio
async def test_extract_user_from_jwt():
    # Create test JWT
    token = create_test_jwt(user_id="auth0|123456")

    # Call endpoint
    response = await client.post(
        "/analyze-workspace",
        json={"org_name": "test-org"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    result = response.json()
    assert result["user_id"] == "auth0|123456"
```

## Rollout Strategy

### Phase 1: Add Optional user_id

1. Update code to extract user_id from JWT
2. Include user_id in events (optional field)
3. Update database schema (nullable column)
4. Deploy and test

### Phase 2: Make user_id Required

1. Verify all events include user_id
2. Make user_id required in event schema
3. Make user_id NOT NULL in database
4. Deploy

### Phase 3: Cleanup

1. Re-index old data with user_id
2. Delete orphaned data without user_id
3. Monitor for errors

## Troubleshooting

### Missing user_id in events

**Symptom**: AI RAG service logs show "No user_id in event, skipping indexing"

**Solution**:

1. Check JWT token is being sent in Authorization header
2. Verify user_id extraction logic
3. Check event_bus.publish includes user_id in data

### Database errors

**Symptom**: Foreign key constraint violations

**Solution**:

1. Ensure user_id column is created before inserting data
2. Make column nullable initially
3. Add NOT NULL constraint after data migration

### Event not received by AI RAG service

**Symptom**: Auto-indexing not triggered

**Solution**:

1. Verify event_bus is connected
2. Check event channel name matches ("workspace_intelligence_events")
3. Check event type matches ("workspace_analysis.completed")
4. Verify Redis connection is working

## Checklist

- [ ] Extract user_id from JWT token in analysis endpoints
- [ ] Update event emission to include user_id
- [ ] Update database schema (optional user_id column)
- [ ] Update workspace_analyzer to accept user_id parameter
- [ ] Update API routes to require Authorization header
- [ ] Test event emission with user_id
- [ ] Test JWT extraction
- [ ] Deploy and monitor
- [ ] Re-index old data (migration)
- [ ] Make user_id required (phase 2)

## Questions?

Contact the AI RAG service team or see `AUTHENTICATION.md` for more details on the authentication implementation.
