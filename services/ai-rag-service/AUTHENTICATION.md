# AI RAG Service - Authentication & Multi-User Support

## Overview

This document describes the authentication and multi-user data isolation implementation for the AI RAG Service.

## Security Features

### 1. JWT Token Authentication

All API endpoints now require a valid JWT token from Auth0:

```bash
Authorization: Bearer <jwt_token>
```

**Implementation:**

- `core/security.py` - SecurityService validates JWT using RS256 algorithm
- JWKS keys fetched from Auth0 endpoint: `https://<AUTH0_DOMAIN>/.well-known/jwks.json`
- Tokens cached to avoid repeated HTTP calls
- User identity extracted from `sub` claim (user_id) and `email` claim

### 2. User Data Isolation

**Multi-Layer Filtering:**

```
user_id (Auth0 sub) → org_name → project_name → folder_path → analysis_id
```

**Vector Search Filters:**

- All vector searches include `user_id` filter
- Organization filter (`org_name`) ensures org-level isolation
- Optional `project_name` filter for project-specific queries
- Optional `folder_path` filter for folder-level analysis
- Optional `analysis_id` filter for specific analysis results

### 3. Conversation Storage

**Redis-based Storage:**

- Conversations stored in Redis with user-scoped keys
- Key structure: `conversation:{user_id}:{conversation_id}`
- 24-hour TTL on conversation data
- Auto-trim to 20 messages per conversation
- User can only access their own conversations

### 4. Permission Service

**Organization Access Control:**

- `PermissionService` checks if user has access to organization
- Redis cache: `user:{user_id}:orgs` stores user's organizations
- 1-hour cache TTL
- Falls back to API call if cache miss

## API Changes

### Chat Endpoint

**POST /api/rag/chat**

**Request:**

```json
{
  "question": "Do we have SAST tools configured?",
  "org_name": "my-org",
  "project_name": "my-project", // Optional - for project-specific queries
  "folder_path": "backend", // Optional - for folder-specific queries
  "analysis_scope": "folder", // Optional - "unified" or "folder"
  "analysis_id": "uuid", // Optional - specific analysis ID
  "conversation_id": "uuid" // Optional - for conversation history
}
```

**Headers:**

```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Response:**

```json
{
  "answer": "Yes, the backend folder has GitHub Actions workflows configured with...",
  "sources": [
    {
      "type": "workflow",
      "file": ".github/workflows/backend-ci.yml",
      "project": "my-project"
    }
  ],
  "confidence": "high",
  "contexts_used": 3,
  "conversation_id": "uuid"
}
```

### Other Endpoints

All endpoints now require authentication:

**DELETE /api/rag/chat/{conversation_id}**

- Clear specific conversation
- User can only clear their own conversations

**GET /api/rag/chat/conversations**

- List user's conversations
- Returns only authenticated user's conversation IDs

**GET /api/rag/chat/{conversation_id}**

- Get conversation history
- User can only access their own conversations

## Auto-Indexing Changes

### Event Handler Updates

**Required Event Fields:**

```json
{
  "type": "workspace_analysis.completed",
  "data": {
    "user_id": "auth0|123456789", // NEW - Required for indexing
    "organization_name": "my-org",
    "project_name": "my-project", // Optional
    "folder_path": "backend", // Optional
    "analysis_id": "uuid",
    "tree_id": "uuid",
    "analysis_scope": "folder" // "unified" or "folder"
  }
}
```

### Vector Metadata

**Workflow Files:**

```json
{
  "user_id": "auth0|123456789",
  "org_name": "my-org",
  "project_name": "my-project",
  "repo_name": "my-project",
  "file_path": ".github/workflows/ci.yml",
  "content": "workflow file content...",
  "indexed_at": "uuid-timestamp"
}
```

**Analysis Results:**

```json
{
  "user_id": "auth0|123456789",
  "org_name": "my-org",
  "project_name": "my-project",
  "folder_path": "backend",
  "analysis_id": "uuid",
  "analysis_scope": "folder",
  "organization": "my-org",
  "content": "analysis content...",
  "indexed_at": "uuid-timestamp"
}
```

### Data Cleanup

**Before Re-Indexing:**

- Old vectors deleted using `user_id + org_name + project_name + folder_path` filter
- Prevents duplicate/stale data
- Implements versioning via `indexed_at` field

## Configuration

### Environment Variables

```bash
# Auth0 Configuration
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_API_IDENTIFIER=your-api-identifier

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Service URLs
WORKSPACE_SERVICE_URL=http://workspace-intelligence-service:8006
GITHUB_SERVICE_URL=http://github-service:8002
```

## Testing

### 1. Get JWT Token

```bash
# From Auth0 or your frontend
export JWT_TOKEN="your_jwt_token_here"
```

### 2. Test Chat Endpoint

**Unified Analysis Query:**

```bash
curl -X POST http://localhost:8004/api/rag/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What security tools do we have?",
    "org_name": "my-org"
  }'
```

**Folder-Specific Query:**

```bash
curl -X POST http://localhost:8004/api/rag/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Do we have SAST configured?",
    "org_name": "my-org",
    "project_name": "my-project",
    "folder_path": "backend",
    "analysis_scope": "folder"
  }'
```

### 3. Test Conversation Management

**List Conversations:**

```bash
curl -X GET http://localhost:8004/api/rag/chat/conversations \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Get Conversation:**

```bash
curl -X GET http://localhost:8004/api/rag/chat/{conversation_id} \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Clear Conversation:**

```bash
curl -X DELETE http://localhost:8004/api/rag/chat/{conversation_id} \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## Security Considerations

### 1. Token Validation

- All endpoints verify JWT signature using Auth0 public keys
- Expired tokens rejected with 401 Unauthorized
- Invalid tokens rejected with 401 Unauthorized

### 2. Data Isolation

- **User Level**: All queries filtered by `user_id` from JWT token
- **Organization Level**: User must have access to organization
- **Project Level**: Optional filtering by project name
- **Folder Level**: Optional filtering by folder path

### 3. Conversation Privacy

- Users can only access their own conversations
- Conversation IDs are UUIDs (not guessable)
- Redis keys include user_id for isolation
- Automatic TTL cleanup after 24 hours

### 4. Vector Database

- Filters applied at query time (Qdrant filter syntax)
- No cross-user data leakage
- Metadata includes user context for all vectors

## Migration from Old System

### 1. Existing Data

- Old vectors without `user_id` field will not be returned in queries
- Need to re-run analysis to index with user context
- Or run migration script to add `user_id` to existing vectors

### 2. Frontend Changes Required

- Pass JWT token in Authorization header
- Include `project_name`, `folder_path` in chat requests when in folder view
- Handle 401 Unauthorized responses (redirect to login)

### 3. Workspace Intelligence Service

- Update event emission to include `user_id` from authenticated request
- Extract user from JWT token in workspace analysis endpoints
- Include user context in published events

## Troubleshooting

### 401 Unauthorized

- Check JWT token is valid and not expired
- Verify AUTH0_DOMAIN is set correctly
- Check token includes required claims (sub, email)

### Empty Results

- Verify user_id matches indexed data
- Check org_name filter matches organization
- Ensure analysis has been re-indexed with user context

### Permission Denied

- User must be member of organization
- Check Redis cache: `user:{user_id}:orgs`
- Verify organization access in Auth0/database

## Performance

### Caching

- JWT public keys cached (lru_cache)
- Organization permissions cached in Redis (1 hour TTL)
- Conversation history cached in Redis (24 hour TTL)

### Vector Search

- Filters applied at Qdrant level (efficient)
- No post-filtering needed
- Maintains sub-second query times

## Future Enhancements

1. **Role-Based Access Control (RBAC)**

   - Admin vs Developer vs Viewer roles
   - Fine-grained permissions per project/folder

2. **Audit Logging**

   - Track all queries with user_id
   - Monitor access patterns
   - Compliance reporting

3. **Data Retention**

   - Automatic cleanup of old analyses
   - User-specific retention policies
   - Archive vs delete options

4. **Multi-Tenancy**
   - Tenant-level isolation
   - Dedicated vector collections per tenant
   - Resource quotas and rate limiting
