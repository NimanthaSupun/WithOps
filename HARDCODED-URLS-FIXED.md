# Hardcoded URLs Fixed - Production & Local Compatibility

## Summary

Fixed all hardcoded URLs in the frontend to support both production (app.withops.com, api.withops.com) and local (localhost:5173, localhost:9000) environments.

## Environment Configuration

### Local Development

- Frontend: http://localhost:5173
- Backend API: http://localhost:9000 (Kong Gateway)
- WebSocket: localhost:9100
- Environment file: `frontend/.env`

### Production

- Frontend: https://app.withops.com
- Backend API: https://api.withops.com
- WebSocket: api.withops.com
- Environment file: `frontend/.env.production`

## Files Fixed

### 1. Port Updates (localhost:8000 → localhost:9000)

All files now use port 9000 for local development to match Kong Gateway:

#### Core Files:

- ✅ `frontend/src/lib/config.js` - API base URL configuration
- ✅ `frontend/src/lib/github.js` - GitHub client (2 locations)
- ✅ `frontend/src/lib/workspaceIntelligence.js` - Workspace intelligence API
- ✅ `frontend/src/lib/repositoryTree.js` - Repository tree API

#### API Clients:

- ✅ `frontend/src/lib/api/rag.js` - RAG service client
- ✅ `frontend/src/lib/api/conversations.js` - Conversations API

#### Store Files:

- ✅ `frontend/src/lib/stores/aiThreatStore.js` - AI threat analysis store
- ✅ `frontend/src/lib/stores/aiThreatStore_fixed.js` - Fixed AI threat store

#### Page Components:

- ✅ `frontend/src/routes/callback/+page.svelte` - Auth0 callback
- ✅ `frontend/src/routes/dashboard/+page.svelte` - Dashboard (2 locations)
- ✅ `frontend/src/routes/github/workspace/[org]/intelligence/+page.svelte` - Intelligence page
- ✅ `frontend/src/routes/github/workspace/[org]/repo-treeview/+page.svelte` - Repo treeview
- ✅ `frontend/src/routes/github/workspace/[org]/treeview/+page.svelte` - Workflow treeview
- ✅ `frontend/src/routes/github/workspace/[org]/threat-modeling/+page.svelte` - Threat modeling dashboard
- ✅ `frontend/src/routes/github/workspace/[org]/threat-modeling/[model_id]/+page.svelte` - Threat modeling canvas

### 2. Relative API Paths Fixed (Using Environment Variables)

Changed all `fetch('/api/...')` to use `${API_BASE_URL}/api/...`:

#### Threat Modeling Pages:

- ✅ **threat-modeling/+page.svelte**
  - POST `/api/threat-modeling/models` → `${API_BASE_URL}/api/threat-modeling/models`
  - DELETE endpoint already using `${API_BASE_URL}`

- ✅ **threat-modeling/[model_id]/+page.svelte**
  - POST `/api/ai/claude/analyze-threats-async` → `${API_BASE_URL}/api/ai/claude/analyze-threats-async`

#### Workflow Treeview:

- ✅ **treeview/+page.svelte** (4 endpoints)
  - POST `/api/github/workspace/${orgName}/actions/trigger` → `${API_BASE_URL}/api/github/workspace/${orgName}/actions/trigger`
  - GET `/api/workflows/status/${executionId}` → `${API_BASE_URL}/api/workflows/status/${executionId}` (2 locations)
  - DELETE `/api/workflows/runs/${run.id}` → `${API_BASE_URL}/api/workflows/runs/${run.id}`

#### Collaboration Component:

- ✅ **OrganizationCollaboration.svelte** (2 endpoints)
  - GET `/api/collaboration/organization/${organization}/members` → `${API_BASE_URL}/api/collaboration/organization/${organization}/members`
  - POST `/api/collaboration/invite` → `${API_BASE_URL}/api/collaboration/invite`

### 3. Repository Tree API (Already Fixed in Previous Session)

- ✅ `frontend/src/lib/repositoryTree.js` - All 6 endpoints use `${API_BASE_URL}/api/`
  - getRepositoryTree
  - saveRepositoryTree
  - deleteRepositoryTree
  - getStatistics

### 4. WebSocket Configuration

- ✅ `.env.production` - Added `VITE_WS_BASE_URL=api.withops.com` (without protocol)
- ✅ `frontend/.env.production` - Added `VITE_WS_BASE_URL=api.withops.com`
- ✅ `frontend/.env` - Added `VITE_WS_BASE_URL=localhost:9100`
- ✅ Root `.env.production` - Changed from `wss://api.withops.com/ws` to `api.withops.com` (code adds protocol dynamically)

### 5. Environment Files Updated

- ✅ `frontend/.env` - Added VITE_WS_BASE_URL for local development
- ✅ `frontend/.env.production` - Added VITE_WS_BASE_URL for production
- ✅ `.env.production` (root) - Fixed PROD_WS_BASE_URL (removed wss:// prefix to prevent double protocol)

## Testing Checklist

### Local Environment (localhost)

- [ ] Auth0 login works at http://localhost:5173
- [ ] Dashboard loads user profile
- [ ] GitHub workspace list appears
- [ ] Repository tree can be loaded/saved
- [ ] Threat modeling page loads and creates models
- [ ] AI analysis works on threat modeling canvas
- [ ] WebSocket connection succeeds at ws://localhost:9100
- [ ] Workflow execution works from treeview page

### Production Environment (withops.com)

- [ ] Auth0 login works at https://app.withops.com
- [ ] Dashboard loads user profile from api.withops.com
- [ ] GitHub workspace list appears
- [ ] Repository tree can be loaded/saved at api.withops.com
- [ ] Threat modeling page loads and creates models
- [ ] AI analysis works on threat modeling canvas
- [ ] WebSocket connection succeeds at wss://api.withops.com/ws
- [ ] Workflow execution works from treeview page
- [ ] No CORS errors in browser console

## Build Commands

### Local Development

```bash
cd frontend
npm run dev
```

### Production Build

```bash
# Using production environment file
cd frontend
npm run build -- --mode production

# Or build entire Docker stack
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml build --no-cache frontend
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Next Steps

1. **Rebuild frontend** with production environment variables
2. **Test locally** - Verify all endpoints work with localhost:9000
3. **Deploy to production** - Test with app.withops.com and api.withops.com
4. **Monitor logs** - Check for any remaining hardcoded URL issues
5. **Verify WebSocket** - Ensure wss://api.withops.com/ws connects properly

## Known Good Configuration

### Kong Gateway (Local)

- Port: 9000
- Routes all `/api/*` to backend services
- CORS enabled for both localhost:5173 and production domains

### Backend Services (Local)

- FastAPI: Port varies by service
- WebSocket: Port 9100
- All accessed through Kong Gateway at localhost:9000

### Frontend Build

- Vite loads environment variables at build time (NOT runtime)
- Variables must be prefixed with `VITE_`
- Build must be rebuilt when environment variables change

## References

- [ENVIRONMENT-CONFIG-SUMMARY.txt](ENVIRONMENT-CONFIG-SUMMARY.txt) - Original environment setup
- [HARDCODED-URLS-STATUS.md](HARDCODED-URLS-STATUS.md) - Previous URL audit
- [docker-compose.prod.yml](docker-compose.prod.yml) - Production Docker config
