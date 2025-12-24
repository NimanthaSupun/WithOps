# Authentication & Multi-User Deployment Guide

This guide covers the deployment and configuration steps for the authenticated multi-user AI RAG and Workspace Intelligence services.

## Prerequisites

- Docker and Docker Compose
- Auth0 account with configured API
- PostgreSQL database (Supabase or self-hosted)
- Redis instance
- Qdrant vector database
- Ollama with nomic-embed-text model
- Anthropic API key (for Claude)

## 1. Auth0 Setup

### Create Auth0 API

1. Log in to [Auth0 Dashboard](https://manage.auth0.com)
2. Navigate to **Applications > APIs**
3. Click **Create API**
4. Fill in:
   - **Name**: `DevSecOps Platform API`
   - **Identifier**: `https://api.withops.com` (or your custom identifier)
   - **Signing Algorithm**: RS256
5. Click **Create**
6. Note down the **Identifier** - this is your `AUTH0_API_IDENTIFIER`

### Configure Auth0 Application

1. Go to **Applications > Applications**
2. Select your application (or create a new Single Page Application)
3. Configure:
   - **Allowed Callback URLs**: `http://localhost:3000/callback, https://your-domain.com/callback`
   - **Allowed Logout URLs**: `http://localhost:3000, https://your-domain.com`
   - **Allowed Web Origins**: `http://localhost:3000, https://your-domain.com`
4. Note down:
   - **Domain** (e.g., `your-tenant.us.auth0.com`) - this is your `AUTH0_DOMAIN`
   - **Client ID** - used in frontend configuration

## 2. Environment Configuration

### AI RAG Service

Copy and configure `.env`:

```bash
cd services/ai-rag-service
cp .env.example .env
```

Edit `.env` with your values:

```dotenv
# Auth0 Configuration (REQUIRED)
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_IDENTIFIER=https://api.withops.com

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Redis
REDIS_URL=redis://redis:6379
CONVERSATION_TTL_HOURS=24
MAX_CONVERSATION_LENGTH=20

# Ollama
OLLAMA_HOST=http://ollama:11434

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Service
LOG_LEVEL=INFO
MAX_EMBEDDING_BATCH_SIZE=10
VECTOR_SEARCH_LIMIT=5
```

### Workspace Intelligence Service

```bash
cd services/workspace-intelligence-service
cp .env.example .env
```

Edit `.env`:

```dotenv
# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://api.withops.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://redis:6379

# GitHub Service
GITHUB_SERVICE_URL=http://github-service:8002
```

### Frontend Configuration

Update `frontend/.env`:

```dotenv
# Auth0
VITE_AUTH0_DOMAIN=your-tenant.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id
VITE_AUTH0_AUDIENCE=https://api.withops.com

# API
VITE_API_BASE_URL=http://localhost:8000
```

## 3. Database Setup

### Run Migrations

The services automatically create required tables on startup, but you can manually run migrations:

```bash
# AI RAG Service (if migrations exist)
cd services/ai-rag-service
python -m alembic upgrade head

# Workspace Intelligence Service
cd services/workspace-intelligence-service
python -m alembic upgrade head
```

### Verify Tables

Connect to PostgreSQL and verify:

```sql
-- AI RAG Service (uses Redis primarily, minimal DB)
-- No specific tables required

-- Workspace Intelligence Service
\dt workspace_intelligence.*

-- Expected tables:
-- - workspace_intelligence.workspace_analyses
-- - workspace_intelligence.repository_findings
-- - workspace_intelligence.maturity_scores
```

## 4. Vector Database Setup

### Initialize Qdrant Collections

The AI RAG service automatically creates collections on first run. To manually create:

```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Collections are auto-created with:
# - github_workflows (768-dim vectors)
# - workspace_analysis (768-dim vectors)
```

### Verify Collections

```bash
curl http://localhost:6333/collections
```

## 5. Deploy Services

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f ai-rag-service
docker-compose logs -f workspace-intelligence-service

# Verify health
curl http://localhost:8003/health  # AI RAG Service
curl http://localhost:8004/health  # Workspace Intelligence Service
```

### Manual Start (Development)

```bash
# Terminal 1: AI RAG Service
cd services/ai-rag-service
python -m uvicorn api.main:app --host 0.0.0.0 --port 8003 --reload

# Terminal 2: Workspace Intelligence Service
cd services/workspace-intelligence-service
python -m uvicorn api.main:app --host 0.0.0.0 --port 8004 --reload

# Terminal 3: Frontend
cd frontend
npm run dev
```

## 6. Verify Authentication

### Test JWT Token Validation

```bash
# Get a token from Auth0 (use Auth0's test tool or login to your app)
TOKEN="your-jwt-token"

# Test AI RAG Service
curl -X POST http://localhost:8003/api/rag/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What security tools are used?",
    "org_name": "test-org",
    "analysis_scope": "unified"
  }'

# Expected: 200 OK with answer
# Without token: 401 Unauthorized
```

### Test Workspace Intelligence

```bash
curl http://localhost:8004/api/workspace-intelligence/organization/test-org \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with analysis data
# Without token: 401 Unauthorized
```

## 7. Data Migration (If Upgrading from Non-Auth Version)

If you have existing data in Qdrant without user_id metadata:

### Option A: Clean Start (Recommended)

```bash
# Delete existing collections
curl -X DELETE http://localhost:6333/collections/github_workflows
curl -X DELETE http://localhost:6333/collections/workspace_analysis

# Re-run analysis to populate with user context
# Users will trigger new analysis through the UI
```

### Option B: Migrate Existing Data

```python
# services/ai-rag-service/scripts/migrate_vectors.py
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Get all vectors
vectors = client.scroll(
    collection_name="workspace_analysis",
    limit=1000
)

# Update with default user_id (requires manual mapping)
for vector in vectors[0]:
    # Add user_id based on org_name or manual mapping
    user_id = map_org_to_user(vector.payload.get("org_name"))

    client.set_payload(
        collection_name="workspace_analysis",
        payload={"user_id": user_id},
        points=[vector.id]
    )
```

## 8. Monitoring & Verification

### Check Redis Conversations

```bash
redis-cli

# List all conversation keys for a user
KEYS conversation:auth0|12345*

# View conversation
LRANGE conversation:auth0|12345:conv-uuid-123 0 -1

# Check TTL
TTL conversation:auth0|12345:conv-uuid-123
```

### Monitor Vector Database

```bash
# Check collection stats
curl http://localhost:6333/collections/workspace_analysis

# Search with user filter
curl -X POST http://localhost:6333/collections/workspace_analysis/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [...],
    "filter": {
      "must": [
        {"key": "user_id", "match": {"value": "auth0|12345"}}
      ]
    },
    "limit": 5
  }'
```

### Check Service Logs

```bash
# AI RAG Service
tail -f services/ai-rag-service/logs/app.log | grep "Authentication\|user_id"

# Workspace Intelligence Service
tail -f services/workspace-intelligence-service/logs/app.log | grep "user_id\|JWT"
```

## 9. Troubleshooting

### Issue: 401 Unauthorized on API Calls

**Cause**: JWT token validation failing

**Solutions**:

1. Verify `AUTH0_DOMAIN` matches your Auth0 tenant
2. Check `AUTH0_API_IDENTIFIER` matches your API Identifier in Auth0
3. Ensure token is not expired (check `exp` claim)
4. Verify token is in `Authorization: Bearer <token>` format

```bash
# Decode JWT to check claims
echo "your-token" | cut -d. -f2 | base64 -d | jq .
```

### Issue: Empty Search Results

**Cause**: User filter blocking results

**Solutions**:

1. Check if data exists for this user_id:

   ```bash
   curl http://localhost:6333/collections/workspace_analysis/points/scroll \
     -X POST -H "Content-Type: application/json" \
     -d '{
       "filter": {
         "must": [{"key": "user_id", "match": {"value": "auth0|12345"}}]
       },
       "limit": 10
     }'
   ```

2. Re-run workspace analysis to index with user context

3. Check auto-indexer logs:
   ```bash
   docker logs ai-rag-service | grep "Indexing analysis"
   ```

### Issue: Conversations Not Persisting

**Cause**: Redis connection or TTL issues

**Solutions**:

1. Check Redis connection:

   ```bash
   redis-cli ping
   ```

2. Verify conversation keys:

   ```bash
   redis-cli KEYS "conversation:*"
   ```

3. Check TTL settings in .env:
   ```dotenv
   CONVERSATION_TTL_HOURS=24  # Increase if needed
   ```

### Issue: Frontend Not Passing Token

**Cause**: Auth0 session not configured

**Solutions**:

1. Check browser localStorage:

   ```javascript
   localStorage.getItem("auth_token");
   ```

2. Verify Auth0 configuration in frontend:

   ```javascript
   // Check network tab for Authorization header
   // Should see: Authorization: Bearer eyJ...
   ```

3. Check frontend console for errors:
   ```javascript
   console.log("Token:", $page.data.user?.accessToken);
   ```

## 10. Security Best Practices

1. **Use HTTPS in Production**: Always use TLS for API communication
2. **Rotate Secrets**: Regularly rotate Anthropic API keys and database passwords
3. **Monitor Access**: Set up alerts for authentication failures
4. **Rate Limiting**: Implement rate limiting on chat endpoints
5. **Audit Logs**: Enable comprehensive logging for security events
6. **Backup Redis**: Regularly backup conversation data if needed
7. **Clean Old Data**: The auto-indexer automatically cleans stale vectors (7+ days)

## 11. Production Checklist

- [ ] Auth0 API configured with RS256
- [ ] Environment variables set in all services
- [ ] Database migrations applied
- [ ] Redis configured with persistence
- [ ] Qdrant backed up (if needed)
- [ ] SSL certificates configured
- [ ] Rate limiting enabled on APIs
- [ ] Monitoring and alerting set up
- [ ] Backup strategy implemented
- [ ] Log aggregation configured
- [ ] Health checks configured in load balancer
- [ ] Secrets stored in vault (not in .env files)

## Support

For issues or questions:

1. Check service logs: `docker-compose logs -f <service>`
2. Verify Auth0 configuration in dashboard
3. Test JWT tokens using jwt.io
4. Check Redis and Qdrant connectivity
5. Review [AUTHENTICATION.md](./AUTHENTICATION.md) for implementation details
