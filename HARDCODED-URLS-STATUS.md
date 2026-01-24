# CRITICAL HARDCODED URLs TO FIX

## ❌ NOT YET FIXED - Still have hardcoded localhost URLs:

### Frontend Files (.svelte):

1. frontend/src/routes/github/workspace/[org]/threat-modeling/[model_id]/+page.svelte
   - Multiple hardcoded http://localhost:8000 URLs (lines 1550, 3172, 3683, 3747, 3865, 3936, 4106, 4637, 4740, 4852, 4881, 4966)
2. frontend/src/routes/github/workspace/[org]/repo-treeview/+page.svelte
   - Lines 519, 628, 694, 740 have hardcoded http://localhost:8000

3. frontend/src/routes/github/workspace/[org]/threat-modeling/+page.svelte
   - Lines 62, 90, 127, 177, 252, 329 have hardcoded http://localhost:8000

### Backend File:

4. backend/core/github_client.py
   - Line 92: redirect_uri = "http://localhost:5173/github/organizations"
   - NEEDS: self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')

### Frontend Stores:

5. frontend/src/lib/stores/aiThreatStore.js
6. frontend/src/lib/stores/aiThreatStore_fixed.js

### Configuration Files (Less Critical - for local dev only):

- Kong config (infra/kong/kong.yml) - Lines 164-165
- Vite proxy config (frontend/vite.config.js)
- Docker compose comments/dev helper files

## ✅ ALREADY FIXED:

- frontend/src/lib/auth.js - ✅ Dynamic callback URL
- frontend/src/lib/github.js - ✅ Uses VITE_API_BASE_URL
- frontend/src/lib/workspaceIntelligence.js - ✅ Uses VITE_API_BASE_URL
- frontend/src/lib/api/conversations.js - ✅ Fixed
- frontend/src/lib/api/rag.js - ✅ Uses VITE_API_BASE_URL
- frontend/src/routes/dashboard/+page.svelte - ✅ Fixed
- frontend/src/routes/callback/+page.svelte - ✅ Fixed
- services/github-service/core/github_client.py - ✅ Uses FRONTEND_URL
- backend/.env - ✅ Has FRONTEND_URL
- backend/.env.production - ✅ Has FRONTEND_URL
- services/github-service/.env - ✅ Has FRONTEND_URL
- services/github-service/.env.production - ✅ Has FRONTEND_URL

## 🎯 RECOMMENDED APPROACH:

Use the new centralized config:

```javascript
import { buildApiUrl, API_BASE_URL } from "$lib/config";

// Instead of: 'http://localhost:8000/api/...'
// Use: buildApiUrl('/api/...')
// Or: `${API_BASE_URL}/api/...`
```

## 🔥 URGENT FIXES NEEDED:

1. Threat modeling pages (both +page.svelte files)
2. Repo treeview page
3. backend/core/github_client.py OAuth redirect
