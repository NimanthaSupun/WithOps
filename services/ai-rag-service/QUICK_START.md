# Quick Start Guide: Multi-User Authentication

## Prerequisites

- Redis running on localhost:6379
- Auth0 account with API configured
- Qdrant vector database running
- Python 3.9+

## Step 1: Install Dependencies

```bash
cd services/ai-rag-service
pip install -r requirements.txt
```

New dependencies added:

- `PyJWT==2.8.0` - JWT token validation
- `cryptography==42.0.0` - RS256 algorithm support

## Step 2: Configure Environment Variables

Create or update `.env` file:

```bash
# Auth0 Configuration
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_API_IDENTIFIER=your-api-identifier

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Anthropic API
ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Service URLs
WORKSPACE_SERVICE_URL=http://workspace-intelligence-service:8006
GITHUB_SERVICE_URL=http://github-service:8002

# Optional
MAX_TOKENS=4096
TEMPERATURE=0.7
TOP_K_RESULTS=5
```

## Step 3: Start Required Services

### Start Redis (if not running)

**Windows:**

```powershell
# If using Docker
docker run -d -p 6379:6379 redis:latest

# Or install Redis for Windows and start it
redis-server
```

**Linux/Mac:**

```bash
redis-server
```

### Start Qdrant (if not running)

```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### Verify Services

```bash
# Test Redis
redis-cli ping
# Expected: PONG

# Test Qdrant
curl http://localhost:6333/healthz
# Expected: {"title":"qdrant - vector search engine","version":"1.x.x"}
```

## Step 4: Start AI RAG Service

```bash
cd services/ai-rag-service
python -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload
```

Expected output:

```
INFO:     🚀 Starting AI RAG Service...
INFO:     Initializing Redis connection...
INFO:     Initializing Ollama Embedding Service...
INFO:     Initializing Qdrant Vector Store...
INFO:     Initializing Event Bus...
INFO:     ✅ All services initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8004
```

## Step 5: Test Authentication

### Get JWT Token

**Option 1: From Auth0 Dashboard**

1. Go to Auth0 Dashboard → Applications → Your App → Test
2. Click "Try" to get a test token

**Option 2: From Frontend**

```javascript
// After user login
const token = await auth0Client.getTokenSilently();
console.log(token);
```

**Option 3: Create Test Token (Development Only)**

```python
# test_token.py
import jwt
import time

payload = {
    "sub": "auth0|test-user-123",
    "email": "test@example.com",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3600
}

# Note: This won't work with real Auth0 validation
# Use for understanding token structure only
token = jwt.encode(payload, "secret", algorithm="HS256")
print(token)
```

### Test Health Check

```bash
curl http://localhost:8004/health
```

Expected:

```json
{
  "status": "healthy",
  "service": "AI RAG Service",
  "version": "1.0.0"
}
```

### Test Chat Endpoint (Authenticated)

```bash
# Set your JWT token
export JWT_TOKEN="your_jwt_token_here"

# Test basic chat
curl -X POST http://localhost:8004/api/rag/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What security tools do we have?",
    "org_name": "your-org-name"
  }'
```

Expected response:

```json
{
  "answer": "Based on the analysis...",
  "sources": [
    {
      "type": "workflow",
      "file": ".github/workflows/security.yml",
      "project": "backend"
    }
  ],
  "confidence": "high",
  "contexts_used": 3,
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Test Without Token (Should Fail)

```bash
curl -X POST http://localhost:8004/api/rag/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "test",
    "org_name": "test-org"
  }'
```

Expected:

```json
{
  "detail": "Authorization required"
}
```

## Step 6: Test Conversation Management

### List Conversations

```bash
curl -X GET http://localhost:8004/api/rag/chat/conversations \
  -H "Authorization: Bearer $JWT_TOKEN"
```

Expected:

```json
{
  "conversations": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ],
  "total": 2
}
```

### Get Specific Conversation

```bash
export CONV_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X GET http://localhost:8004/api/rag/chat/$CONV_ID \
  -H "Authorization: Bearer $JWT_TOKEN"
```

Expected:

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "What security tools do we have?"
    },
    {
      "role": "assistant",
      "content": "Based on the analysis..."
    }
  ],
  "message_count": 2
}
```

### Clear Conversation

```bash
curl -X DELETE http://localhost:8004/api/rag/chat/$CONV_ID \
  -H "Authorization: Bearer $JWT_TOKEN"
```

Expected:

```json
{
  "message": "Conversation cleared",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Step 7: Test Data Isolation

### Scenario: Folder-Specific Query

```bash
# Query for specific folder
curl -X POST http://localhost:8004/api/rag/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Do we have SAST tools configured?",
    "org_name": "my-org",
    "project_name": "my-project",
    "folder_path": "backend",
    "analysis_scope": "folder"
  }'
```

Expected: AI should only see data from `backend` folder, not other folders.

### Scenario: Project-Specific Query

```bash
# Query for specific project
curl -X POST http://localhost:8004/api/rag/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What CI/CD workflows are configured?",
    "org_name": "my-org",
    "project_name": "frontend"
  }'
```

Expected: AI should only see workflows from `frontend` project.

## Step 8: Monitor Logs

Watch the logs for important information:

```bash
# In the terminal where service is running, you should see:

INFO:     📝 Processing query: Do we have SAST tools configured?
INFO:     ✅ Generated query embedding (768 dimensions)
INFO:     Found 3 workflow contexts with filters: {'user_id': 'auth0|123', 'org_name': 'my-org', 'project_name': 'my-project', 'folder_path': 'backend'}
INFO:     Found 2 analysis contexts with filters: {'user_id': 'auth0|123', 'organization': 'my-org', 'project_name': 'my-project', 'folder_path': 'backend'}
INFO:     ✅ Retrieved 5 relevant contexts
INFO:     ✅ Answer generated successfully
```

## Step 9: Test Auto-Indexing

### Trigger Workspace Analysis

From workspace-intelligence-service (after implementing migration):

```bash
curl -X POST http://localhost:8006/api/workspace-intelligence/analyze \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "org_name": "my-org",
    "project_name": "my-project",
    "folder_path": "backend"
  }'
```

### Watch for Auto-Indexing

In AI RAG service logs:

```
INFO:     🎯 Auto-indexing triggered for user: auth0|123, org: my-org, analysis: abc-123
INFO:     🗑️ Cleaned up old workflow data for filter: {'user_id': 'auth0|123', 'org_name': 'my-org', 'project_name': 'my-project'}
INFO:     🗑️ Cleaned up old analysis data for filter: {'user_id': 'auth0|123', 'org_name': 'my-org', 'project_name': 'my-project'}
INFO:     📄 Found 5 workflows to index
INFO:     ✅ Indexed 25 workflow chunks for my-org (user: auth0|123)
INFO:     📊 Indexing analysis results for tree xyz-789
INFO:     ✅ Indexed 15 analysis chunks for my-org (user: auth0|123)
INFO:     ✅ Auto-indexing completed for my-org (user: auth0|123)
```

## Troubleshooting

### Error: "Authorization required"

**Cause**: Missing or invalid JWT token

**Solution**:

1. Verify token is included in Authorization header
2. Check token format: `Bearer <token>`
3. Ensure token is not expired

### Error: "No user_id in event, skipping indexing"

**Cause**: Workspace intelligence service not sending user_id

**Solution**:

1. Update workspace-intelligence-service (see MIGRATION_GUIDE.md)
2. Ensure JWT token passed to workspace service
3. Verify event includes user_id field

### Error: Redis connection refused

**Cause**: Redis not running

**Solution**:

```bash
# Start Redis
docker run -d -p 6379:6379 redis:latest

# Or
redis-server
```

### Error: Qdrant connection refused

**Cause**: Qdrant not running

**Solution**:

```bash
# Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant
```

### Error: Empty results from RAG

**Cause**: No data indexed yet or wrong filters

**Solution**:

1. Run workspace analysis to trigger indexing
2. Verify user_id matches indexed data
3. Check org_name filter is correct
4. Query Qdrant directly to verify data:

```bash
curl http://localhost:6333/collections/workflow_files/points/scroll \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must": [
        {"key": "user_id", "match": {"value": "auth0|123"}}
      ]
    },
    "limit": 10
  }'
```

## Verification Checklist

- [ ] Redis is running and accessible
- [ ] Qdrant is running and accessible
- [ ] AI RAG service starts without errors
- [ ] Health check returns 200 OK
- [ ] Chat endpoint requires authentication
- [ ] Valid JWT token accepted
- [ ] Invalid/missing token rejected (401)
- [ ] Conversations stored in Redis
- [ ] User can list their conversations
- [ ] User cannot access other user's conversations
- [ ] Auto-indexing triggered by workspace events
- [ ] Vectors include user_id in metadata
- [ ] Filters applied correctly in vector search
- [ ] Data isolation working (folder-specific queries)

## Next Steps

1. **Update Frontend**: Pass JWT token and context in API calls
2. **Update Workspace Service**: Emit user_id in events (see MIGRATION_GUIDE.md)
3. **Test End-to-End**: Full flow from frontend → RAG → vector DB
4. **Monitor Performance**: Check query response times
5. **Review Security**: Audit token validation and data isolation

## Documentation

- **AUTHENTICATION.md**: Detailed authentication documentation
- **IMPLEMENTATION_SUMMARY.md**: Overview of implementation
- **MIGRATION_GUIDE.md**: Workspace service migration steps

## Support

If you encounter issues:

1. Check logs for error messages
2. Verify all environment variables are set
3. Test each service independently
4. Review documentation files
5. Check Redis/Qdrant status

---

**Status**: ✅ Ready for Testing

All components implemented and ready for integration testing.
