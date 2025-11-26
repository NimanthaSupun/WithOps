// lib/github.js

/**
 * GitHub Organization Integration Client
 * Handles the complete workflow for organization-based GitHub App integration
 */

class GitHubOrganizationClient {
	/**
	 * 📋 ACTIONS: Get detailed GitHub Actions usage/version info for an organization
	 */

	constructor() {
		this.baseUrl = 'http://localhost:8000/api/github';
		this.cache = new Map(); // In-memory cache for speed
		this.persistentCache = new Map(); // Persistent cache with localStorage
		this.cacheExpiry = 30 * 1000; // 30 seconds for ultra-fast repo updates
		this.persistentCacheExpiry = 2 * 60 * 1000; // 2 minutes for persistent cache
		this.prefetchQueue = new Set(); // Track ongoing prefetch operations
		this.requestDeduplication = new Map(); // Deduplicate concurrent requests
		this.requestQueue = new Map(); // Request batching queue
		this.maxRetries = 3;
		this.retryDelay = 1000;

		// 🔧 FIX: Add request rate limiting to prevent backend overload
		this.activeRequests = new Map(); // Track active requests
		this.maxConcurrentRequests = 8; // Increased from 5 for better parallelism
		this.requestDelay = 100; // Reduced delay for faster processing

		// Initialize persistent cache from localStorage
		this.initializePersistentCache();

		// 🚀 REAL-TIME: WebSocket connection for live updates
		this.wsConnection = null;
		this.wsReconnectAttempts = 0;
		this.wsMaxReconnectAttempts = 5;
		this.wsReconnectDelay = 1000;
		this.wsEventHandlers = new Map();
		// Don't initialize WebSocket here - wait for authentication to complete
	}

	/**
	 * 🚀 PERFORMANCE BOOST: Initialize persistent cache from localStorage
	 * Loads non-sensitive cached data that survives page refreshes
	 */
	initializePersistentCache() {
		if (typeof window === 'undefined') return;

		try {
			const stored = localStorage.getItem('github_cache_v2');
			if (stored) {
				const { data, timestamp } = JSON.parse(stored);
				const now = Date.now();

				// Only load if cache is still valid
				if (now - timestamp < this.persistentCacheExpiry) {
					this.persistentCache = new Map(Object.entries(data));
					console.log(`🚀 Loaded ${this.persistentCache.size} items from persistent cache`);
				} else {
					console.log('⏰ Persistent cache expired, starting fresh');
					localStorage.removeItem('github_cache_v2');
				}
			}
		} catch (error) {
			console.warn('Failed to load persistent cache:', error);
			localStorage.removeItem('github_cache_v2');
		}
	}

	/**
	 * 🚀 PERFORMANCE BOOST: Save persistent cache to localStorage
	 * Stores non-sensitive data for faster subsequent loads
	 */
	savePersistentCache() {
		if (typeof window === 'undefined') return;

		try {
			const cacheData = {
				data: Object.fromEntries(this.persistentCache),
				timestamp: Date.now()
			};
			localStorage.setItem('github_cache_v2', JSON.stringify(cacheData));
		} catch (error) {
			console.warn('Failed to save persistent cache:', error);
		}
	}

	/**
	 * 🚀 ENHANCED: Get cached data with persistent fallback
	 */
	getCachedData(key, allowStale = false) {
		// Check in-memory cache first (fastest)
		const memoryCache = this.cache.get(key);
		if (memoryCache) {
			if (Date.now() - memoryCache.timestamp < this.cacheExpiry) {
				return memoryCache.data;
			} else if (allowStale) {
				console.log(`📊 Using stale in-memory cache for ${key}`);
				return memoryCache.data;
			}
		}

		// Fallback to persistent cache
		const persistentCache = this.persistentCache.get(key);
		if (persistentCache) {
			if (Date.now() - persistentCache.timestamp < this.persistentCacheExpiry) {
				// Promote to in-memory cache for next time
				this.cache.set(key, persistentCache);
				return persistentCache.data;
			} else if (allowStale) {
				console.log(`📊 Using stale persistent cache for ${key}`);
				return persistentCache.data;
			}
		}

		return null;
	}

	/**
	 * 🚀 ENHANCED: Set cached data with persistent storage
	 */
	setCachedData(key, data, isPersistent = true) {
		const cacheEntry = {
			data: data,
			timestamp: Date.now()
		};

		// Always set in memory cache
		this.cache.set(key, cacheEntry);

		// Set in persistent cache for non-sensitive data
		if (isPersistent && this.isDataPersistable(key, data)) {
			this.persistentCache.set(key, cacheEntry);
			// Throttled save to localStorage
			this.throttledSavePersistentCache();
		}
	}

	/**
	 * Set cache data with optional custom TTL
	 */
	setCacheData(key, data, customTTL = null) {
		const cacheEntry = {
			data: data,
			timestamp: Date.now()
		};

		// Set in memory cache
		this.cache.set(key, cacheEntry);

		// Set in persistent cache if it's important data
		if (customTTL || this.persistentCacheExpiry > this.cacheExpiry) {
			this.persistentCache.set(key, cacheEntry);
			this.savePersistentCache();
		}

		console.log(`📦 Cached data for ${key}${customTTL ? ` with custom TTL: ${customTTL}ms` : ''}`);
	}

	/**
	 * 🔐 SECURITY: Determine if data can be persisted
	 */
	isDataPersistable(key, data) {
		// Don't persist sensitive data
		const sensitiveKeys = ['token', 'auth', 'installation_id', 'private'];
		if (sensitiveKeys.some((sensitive) => key.toLowerCase().includes(sensitive))) {
			return false;
		}

		// Don't persist user-specific organization data
		if (key.includes('my_organizations') || key.includes('user_orgs')) {
			return false;
		}

		return true;
	}

	/**
	 * 🚀 PERFORMANCE: Throttled persistent cache save
	 */
	throttledSavePersistentCache = this.throttle(() => {
		this.savePersistentCache();
	}, 2000);

	/**
	 * 🚀 UTILITY: Simple throttle function
	 */
	throttle(func, delay) {
		let timeoutId;
		return (...args) => {
			clearTimeout(timeoutId);
			timeoutId = setTimeout(() => func.apply(this, args), delay);
		};
	}

	/**
	 * 🚀 Step 1: Start organization discovery process (ULTRA-OPTIMIZED)
	 * Returns OAuth URL for user to authorize organization access
	 */
	async startOrganizationDiscovery() {
		try {
			// Ultra-aggressive caching for discovery URL (1 hour)
			const cacheKey = 'discovery_url';
			const cached = this.getCachedData(cacheKey);

			if (cached) {
				console.log('🚀 Using cached discovery URL for instant redirect');
				return cached;
			}

			const token = await this.getAuthToken();
			if (!token) {
				return {
					success: false,
					error: 'Authentication required. Please log in first.'
				};
			}

			// Use centralized request method with deduplication and retry logic
			const data = await this.makeRequest(`${this.baseUrl}/organizations/discover`, {
				method: 'GET'
			});

			console.log('🚀 Organization discovery started:', data);

			const result = {
				success: true,
				oauth_url: data.oauth_url,
				message: data.message
			};

			// Cache the discovery URL with persistent storage for ultra-fast subsequent access
			this.setCachedData(cacheKey, result, true);

			return result;
		} catch (error) {
			console.error('❌ Organization discovery error:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🔍 Step 2: Handle OAuth callback and fetch organizations (ULTRA-OPTIMIZED)
	 * Process the callback from GitHub OAuth
	 */
	async processOrganizationCallback(code, state) {
		try {
			// Check if we have cached organization data from a recent discovery
			const orgCacheKey = `organizations_${state}`;
			const cached = this.getCachedData(orgCacheKey);

			if (cached) {
				console.log('🚀 Using cached organization data for instant display');
				return cached;
			}

			const token = await this.getAuthToken();

			// Send parameters as query params to match backend expectations
			const url = new URL(`${this.baseUrl}/organizations/callback`);
			url.searchParams.set('code', code);
			url.searchParams.set('state', state);

			const controller = new AbortController();
			const timeoutId = setTimeout(() => {
				console.warn('⏰ Callback request timeout after 60 seconds');
				controller.abort();
			}, 25000); // Reduced to 25 seconds for callback processing

			try {
				const data = await this.makeRequest(url.toString(), {
					method: 'POST',
					signal: controller.signal
				});

				clearTimeout(timeoutId);
				console.log('🔍 Organizations discovered:', data);

				const result = {
					success: true,
					organizations: data.organizations,
					total_count: data.total_count,
					message: data.message
				};

				// Cache organization data for 5 minutes
				this.cache.set(orgCacheKey, {
					data: result,
					timestamp: Date.now()
				});

				return result;
			} catch (fetchError) {
				clearTimeout(timeoutId);

				// Handle abort errors more gracefully
				if (fetchError.name === 'AbortError') {
					throw new Error(
						'Request timed out during organization discovery. Please check your connection and try again.'
					);
				}
				throw fetchError;
			}
		} catch (error) {
			console.error('❌ Callback processing error:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🧩 Step 4: Generate installation URL for specific organization (ULTRA-OPTIMIZED)
	 * Creates GitHub App installation URL for the selected organization
	 */
	async generateInstallationUrl(orgName, orgId) {
		try {
			// Check cache first - installation URLs are static and can be cached aggressively
			const cacheKey = `installation_url_${orgName}`;
			const cached = this.getCachedData(cacheKey);

			if (cached) {
				console.log(`🚀 Using cached installation URL for ${orgName}`);
				return cached;
			}

			// Check if request is already in progress to avoid duplicate API calls
			if (this.requestDeduplication.has(cacheKey)) {
				console.log(`🚀 Installation URL request already in progress for ${orgName}, waiting...`);
				return await this.requestDeduplication.get(cacheKey);
			}

			const token = await this.getAuthToken();

			const controller = new AbortController();
			const timeoutId = setTimeout(() => {
				console.warn(`⏰ Installation URL request timeout for ${orgName} after 20 seconds`);
				controller.abort();
			}, 20000); // Reduced to 20 seconds

			const requestPromise = this.makeRequest(`${this.baseUrl}/organizations/${orgName}/install`, {
				method: 'POST',
				body: JSON.stringify({ org_id: orgId }),
				signal: controller.signal
			})
				.then(async (data) => {
					clearTimeout(timeoutId);
					console.log('🧩 Installation URL generated:', data);

					const result = {
						success: true,
						installation_url: data.installation_url,
						organization: data.organization,
						message: data.message
					};

					// Cache installation URL for 30 minutes - they don't change
					this.cache.set(cacheKey, {
						data: result,
						timestamp: Date.now()
					});

					return result;
				})
				.catch((error) => {
					clearTimeout(timeoutId);

					// Handle abort errors more gracefully
					if (error.name === 'AbortError') {
						console.error(`❌ Installation URL generation timeout for ${orgName}`);
						return {
							success: false,
							error: `Request timed out while generating installation URL for ${orgName}. Please check your connection and try again.`
						};
					}

					console.error('❌ Installation URL generation error:', error);
					return {
						success: false,
						error: error.message
					};
				})
				.finally(() => {
					// Remove from deduplication map
					this.requestDeduplication.delete(cacheKey);
				});

			// Store the promise for deduplication
			this.requestDeduplication.set(cacheKey, requestPromise);

			return await requestPromise;
		} catch (error) {
			console.error('❌ Installation URL generation error:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🔐 Step 5: Handle installation callback
	 * Process the callback after GitHub App installation
	 */
	async processInstallationCallback(installationId, setupAction, state) {
		try {
			const token = await this.getAuthToken();

			const params = new URLSearchParams({
				installation_id: installationId,
				setup_action: setupAction
			});

			if (state) {
				params.append('state', state);
			}

			const data = await this.makeRequest(`${this.baseUrl}/installation/callback?${params}`, {
				method: 'POST'
			});

			console.log('🔐 Installation completed:', data);

			return {
				success: true,
				installation_id: data.installation_id,
				organization: data.organization,
				permissions: data.permissions,
				events: data.events,
				message: data.message
			};
		} catch (error) {
			console.error('❌ Installation callback error:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🏢 Get user's active organizations with GitHub App installed
	 * Returns list of organizations where the user has installed the app
	 */
	async getMyActiveOrganizations(cleanup = false) {
		try {
			const token = await this.getAuthToken();
			if (!token) {
				return {
					success: false,
					error: 'Authentication required'
				};
			}

			const url = new URL(`${this.baseUrl}/my-organizations`);
			if (cleanup) {
				url.searchParams.set('cleanup', 'true');
			}

			const data = await this.makeRequest(url.toString(), {
				method: 'GET'
			});

			console.log('🏢 Active organizations loaded:', data);

			return {
				success: true,
				organizations: data.organizations || [],
				total_count: data.total_count || 0
			};
		} catch (error) {
			console.error('❌ Failed to load active organizations:', error);
			return {
				success: false,
				error: error.message,
				organizations: []
			};
		}
	}

	/**
	 * 🚀 PERFORMANCE: Get workflow priority for sorting
	 */
	getWorkflowPriority(workflow) {
		if (!workflow) return 0;

		let score = 0;
		const path = workflow.path?.toLowerCase() || '';
		const name = workflow.name?.toLowerCase() || '';

		// High priority workflows
		if (path.includes('ci') || name.includes('ci')) score += 10;
		if (path.includes('test') || name.includes('test')) score += 8;
		if (path.includes('build') || name.includes('build')) score += 6;
		if (path.includes('deploy') || name.includes('deploy')) score += 7;
		if (path.includes('release') || name.includes('release')) score += 5;

		// Recently modified workflows get priority
		if (workflow.updated_at) {
			const daysSinceUpdate =
				(Date.now() - new Date(workflow.updated_at).getTime()) / (1000 * 60 * 60 * 24);
			if (daysSinceUpdate < 7) score += 3;
			if (daysSinceUpdate < 1) score += 2;
		}

		return score;
	}

	/**
	 * 🚀 PERFORMANCE: Preload workflow content in background
	 */
	async preloadWorkflowContent(orgName, repoName, workflowPath) {
		try {
			await this.getWorkflowContent(orgName, repoName, workflowPath);
		} catch (error) {
			console.warn(`⚠️ Workflow preload failed for ${workflowPath}:`, error);
		}
	}

	/**
	 * 🚀 PERFORMANCE: Batch preload workflows for instant access
	 */
	async batchPreloadWorkflows(orgName, workflows) {
		try {
			console.log(`🚀 Starting batch preload of ${workflows.length} workflows for ${orgName}`);
			console.log(`🔍 Sample workflow data:`, workflows[0]);

			// Preload the most important workflows first (limit to top 5 to avoid overwhelming)
			const priorityWorkflows = workflows
				.sort((a, b) => this.getWorkflowPriority(b) - this.getWorkflowPriority(a))
				.slice(0, 5);

			// Batch preload in background
			const preloadPromises = priorityWorkflows.map(async (workflow) => {
				try {
					console.log(`🚀 Preloading workflow: ${workflow.path} from repo: ${workflow.repository}`);
					await this.preloadWorkflowContent(orgName, workflow.repository, workflow.path);
				} catch (error) {
					console.warn(
						`⚠️ Failed to preload workflow ${workflow.path} from repo ${workflow.repository}:`,
						error
					);
				}
			});

			// Don't wait for all to complete, just start them
			Promise.allSettled(preloadPromises).then(() => {
				console.log(`✅ Batch workflow preload completed for ${orgName}`);
			});

			console.log(`🚀 Batch workflow preload started for ${orgName}`);
		} catch (error) {
			console.warn(`⚠️ Batch workflow preload failed for ${orgName}:`, error);
		}
	}

	/**
	 * 🚀 BACKGROUND: Refresh workspace data in background
	 */
	async refreshWorkspaceInBackground(orgName) {
		try {
			// Clear cache and fetch fresh data
			this.clearOrganizationCache(orgName);
			await this.getOrganizationWorkspace(orgName);
			console.log(`🔄 Background refresh completed for ${orgName}`);
		} catch (error) {
			console.warn(`⚠️ Background refresh failed for ${orgName}:`, error);
		}
	}

	/**
	 * 🚀 BACKGROUND: Refresh workflow content in background
	 */
	async refreshWorkflowInBackground(orgName, repoName, workflowPath) {
		try {
			// Clear cache and fetch fresh content
			const cacheKey = `workflow_${orgName}_${repoName}_${workflowPath}`;
			this.cache.delete(cacheKey);
			this.persistentCache.delete(cacheKey);

			await this.getWorkflowContent(orgName, repoName, workflowPath);
			console.log(`🔄 Background workflow refresh completed for ${workflowPath}`);
		} catch (error) {
			console.warn(`⚠️ Background workflow refresh failed for ${workflowPath}:`, error);
		}
	}

	/**
	 * 🚀 CACHE: Clear organization-specific cache data
	 */
	clearOrganizationCache(orgName) {
		const keysToDelete = [];

		// Find all cache keys related to this organization
		for (const [key] of this.cache) {
			if (key.includes(orgName) || key.includes(`_${orgName}_`) || key.includes(`${orgName}/`)) {
				keysToDelete.push(key);
			}
		}

		// Delete from both caches
		keysToDelete.forEach((key) => {
			this.cache.delete(key);
			this.persistentCache.delete(key);
		});

		console.log(`🗑️ Cleared ${keysToDelete.length} cache entries for ${orgName}`);
		this.savePersistentCache();
	}

	/**
	 * 🔍 INSTALLATION: Verify GitHub app installation for organization
	 */
	async verifyInstallation(orgName) {
		try {
			// For verification calls, always check with backend to get authoritative status
			// Don't rely on potentially stale cache for verification
			console.log(`🔍 Making verification request for ${orgName}...`);

			const data = await this.makeRequest(
				`${this.baseUrl}/organizations/${orgName}/verify-installation`,
				{
					method: 'GET',
					signal: AbortSignal.timeout(10000) // Increased timeout to 10 seconds
				}
			);

			console.log(`🔍 Verification response for ${orgName}:`, data);
			console.log(
				`🔍 Raw app_installed value:`,
				data.app_installed,
				`(type: ${typeof data.app_installed})`
			);

			const result = {
				success: true,
				installed: Boolean(data.app_installed), // Ensure boolean conversion
				installation_id: data.installation_id
			};

			console.log(`🔍 Processed verification result for ${orgName}:`, result);
			console.log(
				`🔍 Verification details - success: ${result.success}, installed: ${result.installed}, app_installed: ${data.app_installed}`
			);

			// Update cache with fresh verification result
			const cacheKey = 'my_organizations';
			const orgData = this.getCachedData(cacheKey);
			if (orgData && orgData.organizations) {
				const orgIndex = orgData.organizations.findIndex((o) => (o.login || o.name) === orgName);
				if (orgIndex !== -1) {
					orgData.organizations[orgIndex].app_installed = Boolean(data.app_installed);
					orgData.organizations[orgIndex].can_access = Boolean(data.app_installed);
					this.setCachedData(cacheKey, orgData, false);
					console.log(
						`📋 Updated cached status for ${orgName} based on verification: ${Boolean(data.app_installed)}`
					);
				}
			}

			return result;
		} catch (error) {
			console.warn(`⚠️ Installation verification failed for ${orgName}:`, error);

			// Provide more detailed error information
			let errorMessage = error.message;
			if (error.name === 'AbortError' || errorMessage.includes('timeout')) {
				errorMessage = 'Verification request timed out';
			} else if (errorMessage.includes('HTTP 403')) {
				errorMessage = 'Access denied - app may not be installed';
			} else if (errorMessage.includes('HTTP 404')) {
				errorMessage = 'Organization not found or app not installed';
			}

			return {
				success: false,
				installed: false,
				error: errorMessage
			};
		}
	}

	/**
	 * Get user's organizations (ULTRA-OPTIMIZED with smart caching)
	 */
	async getMyOrganizations() {
		try {
			// Ultra-aggressive caching for organization list (5 minutes)
			const cacheKey = 'my_organizations';
			const cached = this.getCachedData(cacheKey);

			if (cached) {
				console.log('🚀 Using cached organization list for instant display');

				// Background refresh if data is older than 2 minutes
				const cacheEntry = this.cache.get(cacheKey);
				if (cacheEntry && Date.now() - cacheEntry.timestamp > 2 * 60 * 1000) {
					this.refreshOrganizationsInBackground();
				}

				return cached;
			}

			const token = await this.getAuthToken();
			if (!token) {
				return {
					success: false,
					error: 'Authentication required. Please log in first.'
				};
			}

			const controller = new AbortController();
			const timeoutId = setTimeout(() => {
				console.warn('⏰ Organizations request timeout after 30 seconds');
				controller.abort();
			}, 30000); // 30 seconds timeout for organization fetching

			try {
				const data = await this.makeRequest(`${this.baseUrl}/my-organizations`, {
					method: 'GET',
					signal: controller.signal
				});

				clearTimeout(timeoutId);
				console.log('🔐 User organizations (secure):', data);

				const result = {
					success: true,
					organizations: data.organizations,
					total_count: data.total_count,
					message: data.message,
					user_id: data.user_id
				};

				// Cache the result with longer TTL for better navigation experience (5 minutes)
				this.cache.set(cacheKey, {
					data: result,
					timestamp: Date.now()
				});

				return result;
			} catch (fetchError) {
				clearTimeout(timeoutId);

				// Handle abort errors more gracefully
				if (fetchError.name === 'AbortError') {
					throw new Error(
						'Request timed out while loading organizations. Please check your connection and try again.'
					);
				}
				throw fetchError;
			}
		} catch (error) {
			console.error('❌ User organizations fetch error:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * Get user's organizations with active app installations only
	 * This method filters out organizations where the app has been uninstalled
	 */
	async getMyActiveOrganizations() {
		try {
			// The /my-organizations endpoint already returns only organizations
			// that the user has installed and can access, so no additional filtering needed
			console.log('🔍 Getting user organizations with active installations...');

			const result = await this.getMyOrganizations();

			if (result.success) {
				console.log(`✅ Found ${result.organizations?.length || 0} accessible organizations`);
				console.log('📋 Raw organizations from getMyOrganizations:', result.organizations);

				// Trust the backend's determination completely - don't override
				const organizations = (result.organizations || []).map((org) => {
					console.log(
						`📋 Mapping organization: ${org.login || org.name}, backend app_installed: ${org.app_installed}, can_access: ${org.can_access}`
					);
					return {
						...org,
						// Trust backend completely - if it returns the org, it's accessible
						can_access: org.can_access !== false,
						app_installed: org.app_installed !== false,
						// Add a timestamp to track when this data was loaded
						_loaded_at: Date.now()
					};
				});

				console.log('📋 Final mapped organizations:', organizations);

				return {
					success: true,
					organizations: organizations,
					total_count: organizations.length,
					message: `Found ${organizations.length} organizations with active GitHub App installations`,
					user_id: result.user_id,
					filtered: false // Backend already filtered
				};
			} else {
				return result;
			}
		} catch (error) {
			console.error('❌ Active organizations fetch error:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🚀 PERFORMANCE: Initialize GitHub client with smart prefetching
	 * Call this on app startup to warm up the cache
	 */
	async initializeWithPrefetch() {
		console.log('🚀 Initializing GitHub client with smart prefetching');

		try {
			// Prefetch user organizations in background
			this.getMyOrganizations()
				.then((result) => {
					if (result.success && result.organizations && Array.isArray(result.organizations)) {
						console.log('🚀 Prefetching workspaces for organizations:', result.organizations);

						// Preload workspace data for first 2 organizations
						const topOrgs = result.organizations
							.filter((org) => org && (org.login || org.name)) // Safety check for both field names
							.slice(0, 2);

						topOrgs.forEach((org) => {
							// Handle both GitHub API structure (login) and our backend structure (name)
							const orgName = org.login || org.name;
							if (
								orgName &&
								orgName.trim() !== '' &&
								orgName !== 'undefined' &&
								orgName !== 'null'
							) {
								console.log(`🚀 Preloading workspace for: ${orgName}`);
								this.preloadOrganizationWorkspace(orgName.trim());
							} else {
								console.warn('⚠️ Organization missing valid name/login:', org);
							}
						});
					} else {
						console.warn('⚠️ No organizations found for prefetch:', result);
					}
				})
				.catch((error) => {
					console.warn('⚠️ Initial prefetch failed:', error);
				});

			// Prefetch discovery URL for instant access
			this.startOrganizationDiscovery().catch((error) => {
				console.warn('⚠️ Discovery URL prefetch failed:', error);
			});

			console.log('✅ GitHub client initialization completed');
		} catch (error) {
			console.warn('⚠️ GitHub client initialization failed:', error);
		}
	}

	/**
	 * 🚀 PERFORMANCE: Preload organization workspace data
	 */
	async preloadOrganizationWorkspace(orgName) {
		// Safety check for valid organization name
		if (!orgName || typeof orgName !== 'string' || orgName.trim() === '') {
			console.warn('⚠️ Invalid organization name for preload:', orgName);
			return;
		}

		// Additional safety checks for invalid values
		const cleanOrgName = orgName.trim();
		if (cleanOrgName === 'undefined' || cleanOrgName === 'null' || cleanOrgName === '') {
			console.warn('⚠️ Invalid organization name detected in preload:', orgName);
			return;
		}

		const cacheKey = `workspace_${cleanOrgName}`;

		// Skip if already cached
		if (this.getCachedData(cacheKey)) {
			console.log(`🚀 Workspace already cached for ${cleanOrgName}`);
			return;
		}

		// Skip if already in prefetch queue
		if (this.prefetchQueue.has(cacheKey)) {
			return;
		}

		this.prefetchQueue.add(cacheKey);

		try {
			console.log(`🚀 Starting workspace preload for: ${cleanOrgName}`);
			await this.getOrganizationWorkspace(cleanOrgName);
			console.log(`🚀 Preloaded workspace for ${cleanOrgName}`);
		} catch (error) {
			console.warn(`⚠️ Workspace preload failed for ${cleanOrgName}:`, error);
		} finally {
			this.prefetchQueue.delete(cacheKey);
		}
	}

	/**
	 * 🚀 BACKGROUND: Refresh organizations in background
	 */
	async refreshOrganizationsInBackground() {
		try {
			// Clear cache and fetch fresh data
			this.cache.delete('my_organizations');
			await this.getMyOrganizations();
			console.log('🔄 Background organization refresh completed');
		} catch (error) {
			console.warn('⚠️ Background organization refresh failed:', error);
		}
	}

	/**
	 * 🔄 Force refresh organization data
	 * Clears all caches and fetches fresh data from GitHub
	 */
	async forceRefreshOrganization(orgName) {
		try {
			console.log(`🔄 Force refreshing organization: ${orgName}`);

			// Clear local caches
			const cacheKey = `workspace_${orgName}`;
			this.cache.delete(cacheKey);
			this.persistentCache.delete(cacheKey);

			// Clear any workflow caches for this org
			for (const key of this.cache.keys()) {
				if (key.includes(orgName)) {
					this.cache.delete(key);
				}
			}

			for (const key of this.persistentCache.keys()) {
				if (key.includes(orgName)) {
					this.persistentCache.delete(key);
				}
			}

			// Update localStorage
			this.savePersistentCache();

			// Call backend force refresh endpoint
			const data = await this.makeRequest(`${this.baseUrl}/workspace/${orgName}/refresh`, {
				method: 'POST'
			});

			console.log('🔄 Force refresh completed:', data);

			// Validate and cache the response
			if (!data || typeof data !== 'object') {
				throw new Error('Invalid workspace data received from server');
			}

			const result = {
				success: true,
				organization: data.organization || orgName,
				repositories: Array.isArray(data.repositories) ? data.repositories : [],
				workflows: Array.isArray(data.workflows) ? data.workflows : [],
				repository_count: data.repository_count || 0,
				total_workflows: data.total_workflows || 0,
				last_updated: data.last_updated || new Date().toISOString(),
				installation_id: data.installation_id,
				permissions: data.permissions || {},
				refreshed: true
			};

			// Cache the fresh data
			this.setCachedData(cacheKey, result, true);

			return result;
		} catch (error) {
			console.error('❌ Force refresh failed:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🚀 Get organization workspace with detailed repository and workflow information
	 */
	async getOrganizationWorkspace(orgName) {
		try {
			// Ultra-aggressive caching for workspace data (30 seconds)
			const cacheKey = `workspace_${orgName}`;
			const cached = this.getCachedData(cacheKey);

			if (cached) {
				console.log('🚀 Using cached workspace data for instant display');

				// Background refresh if data is older than 15 seconds
				const cacheEntry = this.cache.get(cacheKey);
				if (cacheEntry && Date.now() - cacheEntry.timestamp > 15 * 1000) {
					this.refreshWorkspaceInBackground(orgName);
				}

				return cached;
			}

			try {
				const data = await this.makeRequest(`${this.baseUrl}/workspace/${orgName}`, {
					method: 'GET'
				});

				console.log('🏢 Organization workspace loaded:', data);

				// Validate the response structure
				if (!data || typeof data !== 'object') {
					throw new Error('Invalid workspace data received from server');
				}

				// Ensure arrays exist
				const result = {
					success: true,
					organization: data.organization || orgName,
					repositories: Array.isArray(data.repositories) ? data.repositories : [],
					workflows: Array.isArray(data.workflows) ? data.workflows : [],
					repository_count: data.repository_count || 0,
					total_workflows: data.total_workflows || 0,
					last_updated: data.last_updated || new Date().toISOString(),
					installation_id: data.installation_id,
					permissions: data.permissions || {}
				};

				// Cache the result with persistent storage
				this.setCachedData(cacheKey, result, true);

				return result;
			} catch (requestError) {
				// Check if it's an installation issue (403/404 errors)
				if (
					requestError.message.includes('HTTP 403') ||
					requestError.message.includes('HTTP 404')
				) {
					this.clearOrganizationCache(orgName);
					console.log(`🔍 Installation issue detected for ${orgName}, clearing cache`);

					// Don't automatically update org cache as this might be a temporary error
					// Let the verification endpoint handle the authoritative status
					console.log(
						`⚠️ Workspace access failed for ${orgName}, but not updating org cache automatically`
					);

					throw new Error(
						`GitHub App is not installed in organization "${orgName}". Please install the app first.`
					);
				}
				throw requestError;
			}
		} catch (error) {
			console.error('❌ Workspace fetch error:', error);
			return {
				success: false,
				error: error.message,
				organization: orgName,
				repositories: [],
				workflows: [],
				repository_count: 0,
				total_workflows: 0
			};
		}
	}

	/**
	 * 📊 STATS: Get organization statistics (repository and workflow counts)
	 */
	async getOrganizationStats(orgName) {
		try {
			console.log(`📊 Getting stats for ${orgName}...`);

			// Check cache first
			const cacheKey = `stats_${orgName}`;
			const cached = this.getCachedData(cacheKey);
			if (cached) {
				console.log('🚀 Using cached stats for instant display');
				return cached;
			}

			const data = await this.makeRequest(`${this.baseUrl}/organizations/${orgName}/stats`, {
				method: 'GET'
			});

			const result = {
				success: true,
				organization: orgName,
				repository_count: data.repository_count || 0,
				total_workflows: data.total_workflows || 0,
				last_updated: data.last_updated || new Date().toISOString()
			};

			// Cache stats for 2 minutes
			this.setCachedData(cacheKey, result, false, 2 * 60 * 1000);

			console.log(
				`✅ Stats loaded for ${orgName}: ${result.repository_count} repos, ${result.total_workflows} workflows`
			);
			return result;
		} catch (error) {
			console.error(`❌ Error loading stats for ${orgName}:`, error);
			return {
				success: false,
				error: error.message,
				organization: orgName,
				repository_count: 0,
				total_workflows: 0
			};
		}
	}

	/**
	 * 🌐 WORKFLOWS: Get detailed workflow information for an organization
	 */
	async getOrganizationWorkflowsDetailed(orgName) {
		try {
			console.log(`🔍 Getting detailed workflows for ${orgName}...`);

			const data = await this.makeRequest(`${this.baseUrl}/workspace/${orgName}`, {
				method: 'GET'
			});

			if (data.workflows) {
				console.log(`✅ Found ${data.workflows.length} workflows for ${orgName}`);
				return {
					success: true,
					workflows: data.workflows,
					organization: orgName,
					total_count: data.workflows.length
				};
			} else {
				return {
					success: true,
					workflows: [],
					organization: orgName,
					total_count: 0
				};
			}
		} catch (error) {
			console.error(`❌ Error loading detailed workflows for ${orgName}:`, error);
			return {
				success: false,
				error: error.message,
				workflows: [],
				organization: orgName,
				total_count: 0
			};
		}
	}

	/**
	 * 📄 CONTENT: Get workflow file content
	 */
	async getWorkflowContent(orgName, repoName, workflowPath) {
		try {
			console.log(`📄 Getting workflow content: ${orgName}/${repoName}/${workflowPath}`);

			// Check cache first
			const cacheKey = `workflow_content_${orgName}_${repoName}_${workflowPath}`;
			const cached = this.getCachedData(cacheKey);
			if (cached) {
				console.log('🚀 Using cached workflow content');
				return cached;
			}

			const data = await this.makeRequest(
				`${this.baseUrl}/workspace/${orgName}/workflow/${repoName}/${encodeURIComponent(workflowPath)}`,
				{
					method: 'GET'
				}
			);

			const result = {
				success: true,
				content: data.content || '',
				workflow_path: workflowPath,
				repository: repoName,
				organization: orgName
			};

			// Cache workflow content for 5 minutes
			this.setCachedData(cacheKey, result, false, 5 * 60 * 1000);

			console.log(`✅ Workflow content loaded: ${workflowPath} (${result.content.length} chars)`);
			return result;
		} catch (error) {
			console.error(`❌ Error loading workflow content for ${workflowPath}:`, error);
			return {
				success: false,
				error: error.message,
				content: `# Error loading workflow content\n# ${error.message}`,
				workflow_path: workflowPath,
				repository: repoName,
				organization: orgName
			};
		}
	}

	/**
	 * 🔍 Get detailed workflow information with triggers, runs, and metadata
	 */

	//  todo:Detail workflow--------------------------------------------------
	async getDetailedWorkflows(orgName) {
		try {
			// Cache detailed workflows for 60 seconds (they don't change often)
			const cacheKey = `detailed_workflows_${orgName}`;
			const cached = this.getCachedData(cacheKey);

			if (cached) {
				console.log('🚀 Using cached detailed workflows');
				return cached;
			}

			const data = await this.makeRequest(
				`${this.baseUrl}/workspace/${orgName}/workflows/detailed`,
				{
					method: 'GET'
				}
			);

			console.log('📊 Detailed workflows loaded:', data);

			// Validate response structure
			if (!data || typeof data !== 'object') {
				throw new Error('Invalid detailed workflows data received from server');
			}

			const result = {
				success: true,
				organization: data.organization || orgName,
				workflows: Array.isArray(data.workflows) ? data.workflows : [],
				total_workflows: data.total_workflows || 0,
				last_updated: data.last_updated || new Date().toISOString()
			};

			// Cache with extended TTL since workflow metadata doesn't change often
			this.setCachedData(cacheKey, result, true, 60 * 1000);

			return result;
		} catch (error) {
			console.error('❌ Error loading detailed workflows:', error);
			return {
				success: false,
				error: error.message || 'Failed to load detailed workflows',
				workflows: []
			};
		}
	}

	/**
	 * 🎨 CANVAS WORKFLOW BUILDER: Save workflow changes and create PR
	 */
	async saveCanvasWorkflowChanges(orgName, repository, workflowPath, yamlContent, actions) {
		try {
			console.log(`🎨 Saving Canvas workflow changes for ${orgName}/${repository}/${workflowPath}`);

			const requestBody = {
				repository: repository,
				workflow_path: workflowPath,
				yaml_content: yamlContent,
				actions: actions
			};

			const result = await this.makeRequest(
				`${this.baseUrl}/workspace/${orgName}/canvas/save-workflow`,
				{
					method: 'POST',
					body: JSON.stringify(requestBody)
				}
			);

			console.log('✅ Canvas workflow changes saved:', result);
			return { success: true, ...result };
		} catch (error) {
			console.error('❌ Error saving Canvas workflow changes:', error);
			return { success: false, error: error.message };
		}
	}

	/**
	 * 🎨 CANVAS WORKFLOW BUILDER: Get workflow relationships
	 */
	async getWorkflowRelationships(orgName) {
		try {
			console.log(`🔗 Getting workflow relationships for ${orgName}`);

			const result = await this.makeRequest(
				`${this.baseUrl}/workspace/${orgName}/canvas/workflow-relationships`
			);

			console.log('✅ Workflow relationships loaded:', result);
			return { success: true, ...result };
		} catch (error) {
			console.error('❌ Error getting workflow relationships:', error);
			return { success: false, error: error.message };
		}
	}

	/**
	 * 🎨 CANVAS WORKFLOW BUILDER: Get predefined actions
	 */
	async getPredefinedActions(orgName) {
		try {
			console.log(`📦 Getting predefined actions for ${orgName}`);

			const result = await this.makeRequest(
				`${this.baseUrl}/workspace/${orgName}/canvas/predefined-actions`
			);

			console.log('✅ Predefined actions loaded:', result);
			return { success: true, ...result };
		} catch (error) {
			console.error('❌ Error getting predefined actions:', error);
			return { success: false, error: error.message };
		}
	}

	/**
	 * 🚀 REAL-TIME: Initialize WebSocket connection for live updates
	 */
	async initializeWebSocket() {
		if (typeof window === 'undefined') return;

		// Get user ID from auth token
		const token = await this.getAuthToken();
		if (!token) {
			console.log('🔌 WebSocket initialization skipped - no auth token available yet');
			return;
		}

		// Extract user ID from token (Auth0 format)
		try {
			const payload = JSON.parse(atob(token.split('.')[1]));
			const userId = payload.sub;

			if (userId) {
				this.connectWebSocket(userId);
			} else {
				console.warn('⚠️ No user ID found in auth token');
			}
		} catch (tokenError) {
			console.warn('⚠️ Failed to parse auth token:', tokenError);
		}
	} /**
	 * 🚀 REAL-TIME: Connect to WebSocket server
	 */
	connectWebSocket(userId) {
		if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
			return;
		}

		try {
			const wsUrl = `ws://localhost:8000/ws/${encodeURIComponent(userId)}`;
			this.wsConnection = new WebSocket(wsUrl);

			this.wsConnection.onopen = () => {
				console.log('🔌 WebSocket connected for real-time updates');
				this.wsReconnectAttempts = 0;
				this.wsReconnectDelay = 1000;
			};

			this.wsConnection.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data);
					this.handleWebSocketMessage(message);
				} catch (error) {
					console.error('❌ WebSocket message parsing failed:', error);
				}
			};

			this.wsConnection.onclose = () => {
				console.log('🔌 WebSocket disconnected');
				this.scheduleWebSocketReconnect(userId);
			};

			this.wsConnection.onerror = (error) => {
				console.error('❌ WebSocket error:', error);
			};
		} catch (error) {
			console.error('❌ WebSocket connection failed:', error);
			this.scheduleWebSocketReconnect(userId);
		}
	}

	/**
	 * 🚀 REAL-TIME: Schedule WebSocket reconnection
	 */
	scheduleWebSocketReconnect(userId) {
		if (this.wsReconnectAttempts < this.wsMaxReconnectAttempts) {
			setTimeout(() => {
				this.wsReconnectAttempts++;
				console.log(
					`🔄 WebSocket reconnect attempt ${this.wsReconnectAttempts}/${this.wsMaxReconnectAttempts}`
				);
				this.connectWebSocket(userId);
			}, this.wsReconnectDelay);

			// Exponential backoff
			this.wsReconnectDelay = Math.min(this.wsReconnectDelay * 2, 30000);
		}
	}

	/**
	 * 🚀 REAL-TIME: Handle incoming WebSocket messages
	 */
	handleWebSocketMessage(message) {
		console.log('🔌 WebSocket message received:', message);

		// Handle different message types
		switch (message.type) {
			case 'workspace_changes':
				this.handleWorkspaceChanges(message.data);
				break;
			case 'repository_added':
				this.handleRepositoryAdded(message.data);
				break;
			case 'repository_removed':
				this.handleRepositoryRemoved(message.data);
				break;
			case 'workflow_added':
				this.handleWorkflowAdded(message.data);
				break;
			case 'workflow_removed':
				this.handleWorkflowRemoved(message.data);
				break;
			// 🚀 NEW: GitHub cache refresh events
			case 'github.workspace_updated':
				this.handleGitHubWorkspaceUpdated(message.data);
				break;
			case 'github.actions_updated':
				this.handleGitHubActionsUpdated(message.data);
				break;
			case 'github.workflows_updated':
				this.handleGitHubWorkflowsUpdated(message.data);
				break;
			default:
				console.log('📨 Unknown WebSocket message type:', message.type);
		}

		// Trigger registered event handlers
		if (this.wsEventHandlers.has(message.type)) {
			const handlers = this.wsEventHandlers.get(message.type);
			handlers.forEach((handler) => {
				try {
					handler(message.data);
				} catch (error) {
					console.error('❌ WebSocket event handler failed:', error);
				}
			});
		}
	}

	/**
	 * 🚀 REAL-TIME: Handle workspace changes
	 */
	handleWorkspaceChanges(data) {
		console.log('🔄 Workspace changes detected:', data);

		// Clear cache for the affected organization
		const orgName = data.organization;
		this.clearOrganizationCache(orgName);

		// Trigger UI updates
		this.emitEvent('workspace_updated', {
			organization: orgName,
			changes: data.changes,
			timestamp: Date.now()
		});
	}

	/**
	 * 🚀 REAL-TIME: Handle repository added event
	 */
	handleRepositoryAdded(data) {
		console.log('🆕 Repository added:', data);

		// Clear cache for the affected organization
		this.clearOrganizationCache(data.organization);

		// Emit event for UI updates
		this.emitEvent('repository_added', data);
	}

	/**
	 * 🚀 REAL-TIME: Handle repository removed event
	 */
	handleRepositoryRemoved(data) {
		console.log('🗑️ Repository removed:', data);

		// Clear cache for the affected organization
		this.clearOrganizationCache(data.organization);

		// Emit event for UI updates
		this.emitEvent('repository_removed', data);
	}

	/**
	 * 🚀 REAL-TIME: Handle workflow added event
	 */
	handleWorkflowAdded(data) {
		console.log('🆕 Workflow added:', data);

		// Clear cache for the affected organization
		this.clearOrganizationCache(data.organization);

		// Emit event for UI updates
		this.emitEvent('workflow_added', data);
	}

	/**
	 * 🚀 REAL-TIME: Handle workflow removed event
	 */
	handleWorkflowRemoved(data) {
		console.log('🗑️ Workflow removed:', data);

		// Clear cache for the affected organization
		this.clearOrganizationCache(data.organization);

		// Emit event for UI updates
		this.emitEvent('workflow_removed', data);
	}

	/**
	 * 🚀 NEW: Handle GitHub workspace cache refresh complete
	 */
	handleGitHubWorkspaceUpdated(data) {
		console.log('✨ GitHub workspace cache refreshed:', data);

		const orgName = data.org_name;

		// Clear local cache to force refetch
		this.clearOrganizationCache(orgName);

		// Emit event for UI updates
		this.emitEvent('github_workspace_refreshed', {
			organization: orgName,
			timestamp: data.timestamp || Date.now(),
			repositories_count: data.repositories_count,
			cached_data_available: true
		});
	}

	/**
	 * 🚀 NEW: Handle GitHub actions cache refresh complete
	 */
	handleGitHubActionsUpdated(data) {
		console.log('✨ GitHub actions cache refreshed:', data);

		const orgName = data.org_name;

		// Clear actions cache
		const cacheKey = `actions_${orgName}`;
		this.cache.delete(cacheKey);
		this.persistentCache.delete(cacheKey);

		// Emit event for UI updates
		this.emitEvent('github_actions_refreshed', {
			organization: orgName,
			timestamp: data.timestamp || Date.now(),
			actions_count: data.actions_count,
			cached_data_available: true
		});
	}

	/**
	 * 🚀 NEW: Handle GitHub workflows cache refresh complete
	 */
	handleGitHubWorkflowsUpdated(data) {
		console.log('✨ GitHub workflows cache refreshed:', data);

		const orgName = data.org_name;

		// Clear workflows cache
		const cacheKey = `workflows_${orgName}`;
		this.cache.delete(cacheKey);
		this.persistentCache.delete(cacheKey);

		// Emit event for UI updates
		this.emitEvent('github_workflows_refreshed', {
			organization: orgName,
			timestamp: data.timestamp || Date.now(),
			workflows_count: data.workflows_count,
			cached_data_available: true
		});
	}

	/**
	 * 🚀 REAL-TIME: Register event handler
	 */
	onRealtimeEvent(eventType, handler) {
		if (!this.wsEventHandlers.has(eventType)) {
			this.wsEventHandlers.set(eventType, []);
		}
		this.wsEventHandlers.get(eventType).push(handler);
	}

	/**
	 * 🚀 REAL-TIME: Remove event handler
	 */
	offRealtimeEvent(eventType, handler) {
		if (this.wsEventHandlers.has(eventType)) {
			const handlers = this.wsEventHandlers.get(eventType);
			const index = handlers.indexOf(handler);
			if (index > -1) {
				handlers.splice(index, 1);
			}
		}
	}

	/**
	 * 🚀 REAL-TIME: Emit custom event
	 */
	emitEvent(eventType, data) {
		if (typeof window !== 'undefined') {
			window.dispatchEvent(new CustomEvent(`github-${eventType}`, { detail: data }));
		}
	}

	/**
	 * 🚀 REAL-TIME: Trigger real-time sync for an organization
	 */
	async syncOrganizationRealtime(orgName) {
		try {
			const result = await this.makeRequest(
				`${this.baseUrl}/organizations/${orgName}/sync-realtime`,
				{
					method: 'POST'
				}
			);

			console.log('🚀 Real-time sync completed:', result);
			return result;
		} catch (error) {
			console.error('❌ Real-time sync failed:', error);
			throw error;
		}
	}

	/**
	 * 🔐 AUTHENTICATION: Get Auth0 JWT token with expiration check
	 */
	async getAuthToken() {
		try {
			console.log('🔐 Getting auth token...');

			// Method 1: Check stored tokens first (fastest)
			if (typeof window !== 'undefined') {
				const storedToken =
					localStorage.getItem('auth0_token') || localStorage.getItem('auth_token');
				console.log(
					'🔐 Stored token exists:',
					!!storedToken,
					storedToken ? `(length: ${storedToken.length})` : ''
				);

				if (
					storedToken &&
					storedToken !== 'null' &&
					storedToken !== 'undefined' &&
					storedToken.length > 10
				) {
					// Check if token is expired before using it
					if (this.isTokenExpired(storedToken)) {
						console.log('🔐 Stored token is expired, clearing...');
						localStorage.removeItem('auth0_token');
						localStorage.removeItem('auth_token');
					} else {
						console.log('🔐 Using stored auth token');
						return storedToken;
					}
				}
			}

			// Method 2: Try to get fresh token from Auth0 client
			if (typeof window !== 'undefined') {
				console.log('🔐 Attempting to get fresh token from Auth0...');
				try {
					// Get Auth0 client
					let auth0Client = window.auth0Client;
					if (!auth0Client) {
						console.log('🔐 Auth0 client not found in window, importing...');
						const { getAuthClient } = await import('./auth.js');
						auth0Client = await getAuthClient();
						window.auth0Client = auth0Client;
						console.log('🔐 Auth0 client imported and cached');
					}

					// Check if authenticated and get token
					if (auth0Client) {
						const isAuthenticated = await auth0Client.isAuthenticated();
						console.log('🔐 Auth0 isAuthenticated:', isAuthenticated);

						if (isAuthenticated) {
							const token = await auth0Client.getTokenSilently({
								audience: 'https://api.withops.com',
								timeoutInSeconds: 10
							});

							if (token) {
								console.log('🔐 Got fresh Auth0 token, storing...');
								localStorage.setItem('auth0_token', token);
								return token;
							} else {
								console.log('🔐 No token returned from getTokenSilently');
							}
						} else {
							console.log('🔐 User not authenticated with Auth0');
						}
					} else {
						console.log('🔐 Auth0 client is null');
					}
				} catch (auth0Error) {
					console.error('🔐 Auth0 error:', auth0Error.message);
				}
			}

			console.log('🔐 No authentication token available');
			return null;
		} catch (error) {
			console.error('⚠️ Auth token retrieval failed:', error);
			return null;
		}
	}

	/**
	 * 🕐 HELPER: Check if JWT token is expired
	 */
	isTokenExpired(token) {
		try {
			if (!token) return true;

			// JWT tokens have 3 parts separated by dots
			const parts = token.split('.');
			if (parts.length !== 3) return true;

			// Decode the payload (second part)
			const payload = JSON.parse(atob(parts[1]));

			// Check expiration (exp is in seconds, Date.now() is in milliseconds)
			if (!payload.exp) return false; // No expiration claim means it doesn't expire

			const now = Math.floor(Date.now() / 1000);
			const isExpired = payload.exp < now;

			if (isExpired) {
				console.log(`🕐 Token expired: exp=${payload.exp}, now=${now}`);
			}

			return isExpired;
		} catch (error) {
			console.warn('⚠️ Error checking token expiration:', error);
			// If we can't parse it, assume it's invalid/expired
			return true;
		}
	}

	/**
	 * 🔐 AUTHENTICATION: Simple initialization after auth
	 */
	async initializeAfterAuth() {
		console.log('🔐 Initializing GitHub client features...');
		try {
			// Just initialize WebSocket if we have a token
			await this.initializeWebSocket();
			console.log('✅ GitHub client initialized');
			return true;
		} catch (error) {
			console.warn('⚠️ GitHub client initialization failed:', error);
			return false;
		}
	}

	/**
	 * 🔐 AUTHENTICATION: Check if user is authenticated for GitHub operations
	 */
	async isAuthenticated() {
		const token = await this.getAuthToken();
		return token !== null;
	}

	/**
	 * 🧪 TESTING: Force token refresh (useful for testing and debugging)
	 */
	async forceTokenRefresh() {
		console.log('🧪 Forcing token refresh for testing...');
		await this.refreshAuthToken();
		console.log('✅ Token refresh completed');
	}

	/**
	 * 🚀 PERFORMANCE: Wait for available request slot to prevent backend overload
	 */
	async waitForRequestSlot(requestKey) {
		// Simple rate limiting to prevent overwhelming the backend
		if (this.activeRequests.size >= this.maxConcurrentRequests) {
			await new Promise((resolve) => setTimeout(resolve, this.requestDelay));
		}

		this.activeRequests.set(requestKey, Date.now());

		// Clean up old requests after a timeout
		setTimeout(() => {
			this.activeRequests.delete(requestKey);
		}, 30000);
	}

	/**
	 * 🌐 CORE: Make authenticated HTTP request to backend with automatic token refresh
	 */
	async makeRequest(url, options = {}) {
		const maxRetries = 2; // Allow up to 2 retries for token refresh

		for (let attempt = 0; attempt <= maxRetries; attempt++) {
			try {
				const token = await this.getAuthToken();
				if (!token) {
					throw new Error('No authentication token available');
				}

				const defaultHeaders = {
					Authorization: `Bearer ${token}`,
					'Content-Type': 'application/json',
					...options.headers
				};

				const requestOptions = {
					...options,
					headers: defaultHeaders
				};

				console.log(`🌐 Making request to: ${url}`);
				const response = await fetch(url, requestOptions);

				if (!response.ok) {
					const errorText = await response.text();

					// Handle 401 Unauthorized - Token might be expired
					if (response.status === 401 && attempt < maxRetries) {
						console.warn(
							`🔄 Token expired (attempt ${attempt + 1}/${maxRetries + 1}), refreshing...`
						);

						// Clear stored tokens and force refresh
						await this.refreshAuthToken();

						// Continue to next iteration for retry
						continue;
					}

					throw new Error(`HTTP ${response.status}: ${errorText}`);
				}

				return await response.json();
			} catch (error) {
				// If this was our last attempt or not a token-related error, throw
				if (attempt >= maxRetries || !this.isTokenError(error)) {
					console.error(`❌ Request failed for ${url}:`, error);
					throw error;
				}

				// On token errors, try to refresh and continue
				console.warn(`🔄 Token error on attempt ${attempt + 1}, refreshing...`);
				await this.refreshAuthToken();
			}
		}

		// This shouldn't be reached, but just in case
		throw new Error(`Request failed after ${maxRetries + 1} attempts`);
	}

	/**
	 * 🔄 AUTHENTICATION: Refresh the authentication token
	 */
	async refreshAuthToken() {
		try {
			console.log('🔄 Refreshing authentication token...');

			// Clear stored tokens
			if (typeof window !== 'undefined') {
				localStorage.removeItem('auth0_token');
				localStorage.removeItem('auth_token');
			}

			// Try to get fresh token from Auth0
			if (typeof window !== 'undefined') {
				try {
					let auth0Client = window.auth0Client;
					if (!auth0Client) {
						const { getAuthClient } = await import('./auth.js');
						auth0Client = await getAuthClient();
						window.auth0Client = auth0Client;
					}

					if (auth0Client) {
						const isAuthenticated = await auth0Client.isAuthenticated();

						if (isAuthenticated) {
							// Force token refresh by including ignoreCache option
							const token = await auth0Client.getTokenSilently({
								audience: 'https://api.withops.com',
								timeoutInSeconds: 10,
								ignoreCache: true // Force fresh token
							});

							if (token) {
								console.log('✅ Successfully refreshed authentication token');
								localStorage.setItem('auth0_token', token);
								return token;
							}
						} else {
							console.warn('🔐 User not authenticated, redirecting to login...');
							// Redirect to login if user is not authenticated
							await auth0Client.loginWithRedirect({
								authorizationParams: {
									redirect_uri: window.location.origin,
									audience: 'https://api.withops.com'
								}
							});
						}
					}
				} catch (auth0Error) {
					console.error('🔐 Auth0 token refresh error:', auth0Error);

					// If refresh fails, redirect to login
					if (auth0Error.error === 'login_required' || auth0Error.error === 'consent_required') {
						console.warn('🔐 Login required, redirecting...');
						if (window.auth0Client) {
							await window.auth0Client.loginWithRedirect({
								authorizationParams: {
									redirect_uri: window.location.origin,
									audience: 'https://api.withops.com'
								}
							});
						}
					}

					throw auth0Error;
				}
			}

			console.warn('❌ Unable to refresh token');
			return null;
		} catch (error) {
			console.error('❌ Token refresh failed:', error);
			return null;
		}
	}

	/**
	 * 🔍 HELPER: Check if error is token-related
	 */
	isTokenError(error) {
		if (!error || !error.message) return false;

		const message = error.message.toLowerCase();
		return (
			message.includes('401') ||
			message.includes('unauthorized') ||
			message.includes('expired') ||
			message.includes('invalid token') ||
			message.includes('token validation failed')
		);
	}

	/**
	 * 🏢 ORGANIZATIONS: Filter organizations to show only those with active app installations
	 */
	async filterActiveOrganizations(organizations) {
		try {
			console.log(`🔍 Filtering ${organizations.length} organizations for active installations...`);

			// For each organization, check if the GitHub App is installed and user has access
			const activeOrgs = [];

			for (const org of organizations) {
				try {
					// Check if the app is installed in this organization using the correct endpoint
					const response = await this.makeRequest(
						`${this.baseUrl}/organizations/${org.name}/verify-installation`
					);

					if (response.app_installed) {
						org.app_installed = true;
						org.installation_id = response.installation_id;
						org.can_access = true;
						org.installed_by_you = response.installed_by_you || false;
						activeOrgs.push(org);
						console.log(`✅ Active installation found for ${org.name}`);
					} else {
						console.log(`⚠️ No active installation for ${org.name}`);
					}
				} catch (error) {
					console.warn(`⚠️ Could not verify installation for ${org.name}:`, error.message);
					// Still include the org but mark as not installed
					org.app_installed = false;
					org.can_access = false;
					activeOrgs.push(org);
				}
			}

			console.log(`🔍 Found ${activeOrgs.length} organizations with active installations`);
			return activeOrgs;
		} catch (error) {
			console.error('❌ Error filtering active organizations:', error);
			// Return all organizations if filtering fails
			return organizations.map((org) => ({
				...org,
				app_installed: false,
				can_access: false
			}));
		}
	}

	/**
	 * 🚀 SMART NAVIGATION: Navigate to organization workspace with intelligent status checking
	 * This method avoids redundant verification calls by using cached organization data
	 */
	async navigateToWorkspace(orgName) {
		try {
			console.log(`🏢 Smart navigation to ${orgName} workspace`);

			// First, try to get workspace data directly to see if it's working
			const workspaceCheck = this.getCachedData(`workspace_${orgName}`);
			if (workspaceCheck) {
				console.log(`✅ Found cached workspace data for ${orgName} - navigation should work`);
				return {
					success: true,
					canNavigate: true,
					cached: true
				};
			}

			// Check our cached organization data for installation status
			const cacheKey = 'my_organizations';
			const orgData = this.getCachedData(cacheKey);

			if (orgData && orgData.organizations) {
				const org = orgData.organizations.find((o) => (o.login || o.name) === orgName);

				if (org) {
					console.log(`📋 Found cached org data for ${orgName}:`, {
						app_installed: org.app_installed,
						can_access: org.can_access
					});

					// Only block navigation if we're CERTAIN the app is not installed
					// Don't trust stale cache that might be wrong
					if (org.app_installed === false) {
						const cacheAge = Date.now() - (this.cache.get(cacheKey)?.timestamp || 0);
						// Only trust this if cache is fresh (less than 2 minutes)
						if (cacheAge < 2 * 60 * 1000) {
							console.warn(`⚠️ App no longer installed in ${orgName} (fresh cache)`);
							return {
								success: false,
								error: `GitHub App is no longer installed in ${orgName}. Please reinstall the app to access the workspace.`,
								needsInstallation: true
							};
						} else {
							console.log(`🔄 Cache might be stale for ${orgName}, allowing verification`);
						}
					}

					// If we have recent data showing the app is installed, proceed with navigation
					if (org.app_installed === true && org.can_access !== false) {
						console.log(`✅ Proceeding with navigation to ${orgName} - app confirmed installed`);
						return {
							success: true,
							canNavigate: true,
							organization: org
						};
					}
				}
			}

			// If we don't have cached data or status is unclear, do a verification call
			console.log(`🔍 No reliable cached data for ${orgName}, performing verification`);
			const verification = await this.verifyInstallation(orgName);

			if (!verification.success || !verification.installed) {
				console.warn(`❌ Verification failed for ${orgName}:`, verification);
				return {
					success: false,
					error:
						verification.error ||
						`GitHub App is not installed in ${orgName}. Please install the app to access the workspace.`,
					needsInstallation: !verification.installed
				};
			}

			console.log(`✅ Verification successful for ${orgName}`);
			return {
				success: true,
				canNavigate: true,
				verification: verification
			};
		} catch (error) {
			console.error(`❌ Smart navigation failed for ${orgName}:`, error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🔄 CACHE: Refresh organization data and clear stale cache
	 */
	async refreshOrganizationData(force = false) {
		try {
			console.log('🔄 Refreshing organization data...');

			// Clear organization cache
			const cacheKey = 'my_organizations';
			if (force) {
				this.cache.delete(cacheKey);
				this.persistentCache.delete(cacheKey);
			}

			// Fetch fresh organization data
			const result = await this.getMyOrganizations();

			if (result.success) {
				console.log('✅ Organization data refreshed successfully');

				// Clear workspace cache for organizations where app is no longer installed
				result.organizations.forEach((org) => {
					const orgName = org.login || org.name;
					if (!org.app_installed) {
						console.log(`🗑️ Clearing workspace cache for ${orgName} - app no longer installed`);
						this.clearOrganizationCache(orgName);
					}
				});
			}

			return result;
		} catch (error) {
			console.error('❌ Failed to refresh organization data:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🔄 CACHE: Restore organization installation status when backend confirms it's working
	 */
	async restoreOrganizationStatus(orgName) {
		try {
			console.log(`🔄 Restoring organization status for ${orgName}`);

			// Get fresh organization data to restore correct status
			const result = await this.getMyOrganizations();
			if (result.success) {
				const org = result.organizations.find((o) => (o.login || o.name) === orgName);
				if (org && org.app_installed) {
					console.log(`✅ Restored ${orgName} status - app is installed`);
					return true;
				}
			}
			return false;
		} catch (error) {
			console.warn(`⚠️ Failed to restore organization status for ${orgName}:`, error);
			return false;
		}
	}

	/**
	 * 🧹 CLEANUP: Clean up stale installations
	 */
	async cleanupInstallations() {
		try {
			console.log('🧹 Starting installation cleanup...');

			// This would typically involve checking with backend for stale installations
			// For now, just refresh the organization data
			const result = await this.refreshOrganizationData(true);

			return {
				success: result.success,
				cleaned_count: 0,
				message: 'Organization data refreshed'
			};
		} catch (error) {
			console.error('❌ Cleanup failed:', error);
			return {
				success: false,
				error: error.message
			};
		}
	}

	/**
	 * 🚀 SMART PREFETCH: Intelligent workflow content prefetching
	 */
	async smartPrefetch(orgName, repoName, workflowPath) {
		try {
			console.log(`🚀 Smart prefetch for ${orgName}/${repoName}/${workflowPath}`);

			// Check if already cached
			const cacheKey = `workflow_content_${orgName}_${repoName}_${workflowPath}`;
			const cached = this.getCachedData(cacheKey);
			if (cached) {
				console.log(`✅ Workflow content already cached for ${workflowPath}`);
				return cached;
			}

			// Prefetch in background
			this.getWorkflowContent(orgName, repoName, workflowPath).catch((error) => {
				console.warn(`⚠️ Smart prefetch failed for ${workflowPath}:`, error);
			});

			return { success: true, prefetching: true };
		} catch (error) {
			console.warn(`⚠️ Smart prefetch error for ${workflowPath}:`, error);
			return { success: false, error: error.message };
		}
	}

	// todo:getAction details
	async getActionDetails(orgName) {
		try {
			// Cache action details for 60 seconds (they don't change often)
			const cacheKey = `action_details_${orgName}`;
			const cached = this.getCachedData(cacheKey);

			if (cached) {
				console.log('🚀 Using cached action details');
				return cached;
			}

			const data = await this.makeRequest(`${this.baseUrl}/workspace/${orgName}/actions/detailed`, {
				method: 'GET'
			});

			console.log('📋 Action details loaded:', data);

			// Validate response structure
			if (!data || typeof data !== 'object') {
				throw new Error('Invalid action details data received from server');
			}

			const result = {
				success: true,
				organization: data.organization || orgName,
				actions: Array.isArray(data.actions) ? data.actions : [],
				total_actions:
					data.total_actions || (Array.isArray(data.actions) ? data.actions.length : 0),
				last_updated: data.last_updated || new Date().toISOString()
			};

			// Cache with extended TTL since action metadata doesn't change often
			this.setCachedData(cacheKey, result, true, 60 * 1000);

			return result;
		} catch (error) {
			console.error('❌ Error loading action details:', error);
			return {
				success: false,
				error: error.message || 'Failed to load action details',
				actions: []
			};
		}
	}

	/**
	 * 📋 ALIAS: Get organization actions detailed (alias for getActionDetails)
	 */
	async getOrganizationActionsDetailed(orgName) {
		return await this.getActionDetails(orgName);
	}

	// Get paginated action details with search and caching
	async getActionDetailsPaginated(orgName, page = 1, perPage = 20, search = '') {
		try {
			// Create cache key that includes pagination and search parameters
			const cacheKey = `action_details_paginated_${orgName}_${page}_${perPage}_${search}`;
			const cached = this.getCachedData(cacheKey);

			if (cached) {
				console.log('🚀 Using cached paginated action details');
				return cached;
			}

			// Build query parameters
			const params = new URLSearchParams({
				page: page.toString(),
				per_page: perPage.toString()
			});

			if (search && search.trim()) {
				params.append('search', search.trim());
			}

			const data = await this.makeRequest(
				`${this.baseUrl}/workspace/${orgName}/actions/paginated?${params}`,
				{
					method: 'GET'
				}
			);

			console.log('📋 Paginated action details loaded:', data);

			// Validate response structure
			if (!data || typeof data !== 'object') {
				throw new Error('Invalid paginated action details data received from server');
			}

			const result = {
				success: true,
				organization: data.organization || orgName,
				actions: Array.isArray(data.actions) ? data.actions : [],
				page: data.page || page,
				per_page: data.per_page || perPage,
				total_items: data.total_items || 0,
				total_pages: data.total_pages || 1,
				has_next: data.has_next || false,
				has_previous: data.has_previous || false,
				search_query: data.search_query || search,
				cached: data.cached || false,
				statistics: data.statistics || { up_to_date: 0, outdated: 0, unknown: 0 },
				last_updated: data.last_updated || new Date().toISOString()
			};

			// Cache with shorter TTL for paginated data (2 minutes)
			this.setCachedData(cacheKey, result, true, 2 * 60 * 1000);

			return result;
		} catch (error) {
			console.error('❌ Error loading paginated action details:', error);
			return {
				success: false,
				error: error.message || 'Failed to load paginated action details',
				actions: [],
				page: page,
				per_page: perPage,
				total_items: 0,
				total_pages: 1,
				has_next: false,
				has_previous: false,
				search_query: search,
				cached: false,
				statistics: { up_to_date: 0, outdated: 0, unknown: 0 }
			};
		}
	}

	// Clear cache for an organization
	async clearOrgCache(orgName) {
		try {
			console.log(`🗑️ Clearing cache for ${orgName}...`);

			// Clear frontend cache
			const keysToRemove = [];
			for (const key of this.cache.keys()) {
				if (key.includes(orgName)) {
					keysToRemove.push(key);
				}
			}
			for (const key of this.persistentCache.keys()) {
				if (key.includes(orgName)) {
					keysToRemove.push(key);
				}
			}

			keysToRemove.forEach((key) => {
				this.cache.delete(key);
				this.persistentCache.delete(key);
			});

			console.log(`🗑️ Cleared ${keysToRemove.length} frontend cache entries`);

			// Clear backend cache
			const data = await this.makeRequest(`${this.baseUrl}/workspace/${orgName}/cache`, {
				method: 'DELETE'
			});

			console.log('✅ Backend cache cleared:', data);

			return {
				success: true,
				message: data.message || 'Cache cleared successfully',
				cleared_entries: data.cleared_entries || 0
			};
		} catch (error) {
			console.error('❌ Error clearing cache:', error);
			return {
				success: false,
				error: error.message || 'Failed to clear cache'
			};
		}
	}

	// Get cache statistics
	async getCacheStats() {
		try {
			const data = await this.makeRequest(`${this.baseUrl}/cache/stats`, {
				method: 'GET'
			});

			return {
				success: true,
				stats: data
			};
		} catch (error) {
			console.error('❌ Error getting cache stats:', error);
			return {
				success: false,
				error: error.message || 'Failed to get cache stats'
			};
		}
	}

	// Refresh action details by clearing cache and fetching fresh data
	async refreshActionDetails(orgName) {
		try {
			console.log(`🔄 Refreshing action details for ${orgName}...`);

			// Clear cache for this organization's actions
			const cacheKey = `action_details_${orgName}`;
			this.cache.delete(cacheKey);
			this.persistentCache.delete(cacheKey);

			// Make API call to refresh endpoint
			const data = await this.makeRequest(`${this.baseUrl}/workspace/${orgName}/actions/refresh`, {
				method: 'POST'
			});

			console.log('🔄 Action details refreshed:', data);

			// Validate response structure
			if (!data || typeof data !== 'object') {
				throw new Error('Invalid refresh response received from server');
			}

			const result = {
				success: true,
				organization: data.organization || orgName,
				actions: Array.isArray(data.actions) ? data.actions : [],
				total_actions:
					data.total_actions || (Array.isArray(data.actions) ? data.actions.length : 0),
				statistics: data.statistics || {},
				cache_cleared: data.cache_cleared || 0,
				last_updated: data.last_updated || new Date().toISOString(),
				refreshed: true
			};

			// Cache the fresh data
			this.setCachedData(cacheKey, result, true, 60 * 1000);

			return result;
		} catch (error) {
			console.error('❌ Error refreshing action details:', error);
			return {
				success: false,
				error: error.message || 'Failed to refresh action details',
				actions: []
			};
		}
	}

	// Create pull request to update a single outdated action
	async createActionUpdatePR(actionData) {
		try {
			console.log('🔧 Creating PR for action update:', actionData);

			const data = await this.makeRequest(
				`${this.baseUrl}/workspace/${actionData.org}/actions/create-pr`,
				{
					method: 'POST',
					body: JSON.stringify({
						repo: actionData.repo,
						workflow_path: actionData.workflow_path,
						action_name: actionData.action_name,
						current_version: actionData.current_version,
						latest_version: actionData.latest_version
					})
				}
			);

			console.log('✅ PR created successfully:', data);

			return {
				success: true,
				pr_number: data.pr_number,
				pr_title: data.pr_title,
				pr_url: data.pr_url,
				branch_name: data.branch_name,
				message: data.message || 'Pull request created successfully'
			};
		} catch (error) {
			console.error('❌ Error creating PR:', error);
			return {
				success: false,
				error: error.message || 'Failed to create pull request'
			};
		}
	}

	// Create pull request to update multiple outdated actions in a single workflow
	async createBulkActionUpdatePR(actionData) {
		try {
			console.log('🔧 Creating bulk PR for action updates:', actionData);

			const data = await this.makeRequest(
				`${this.baseUrl}/workspace/${actionData.org}/actions/create-bulk-pr`,
				{
					method: 'POST',
					body: JSON.stringify({
						repo: actionData.repo,
						workflow_path: actionData.workflow_path,
						actions: actionData.actions
					})
				}
			);

			console.log('✅ Bulk PR created successfully:', data);

			return {
				success: true,
				pr_number: data.pr_number,
				pr_title: data.pr_title,
				pr_url: data.pr_url,
				branch_name: data.branch_name,
				updated_actions: data.updated_actions || [],
				message: data.message || 'Bulk pull request created successfully'
			};
		} catch (error) {
			console.error('❌ Error creating bulk PR:', error);
			return {
				success: false,
				error: error.message || 'Failed to create bulk pull request'
			};
		}
	}

	/**
	 *todo:------------------------ 🌲 PROJECT TREEVIEW: Get project tree data from database------------------------------------
	 */
	async getProjectTreeData(orgName) {
		try {
			const response = await fetch(`${this.baseUrl}/project-tree/${orgName}`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${this.getAuthToken()}`
				}
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.error || 'Failed to get project tree data');
			}

			const data = await response.json();
			return {
				success: true,
				data: data.tree_data || []
			};
		} catch (error) {
			console.error('❌ Error getting project tree data:', error);
			return {
				success: false,
				error: error.message || 'Failed to get project tree data',
				data: []
			};
		}
	}

	/**
	 *todo:--------------------- 🌲 PROJECT TREEVIEW: Save project tree data to database--------------------------------------
	 */
	async saveProjectTreeData(orgName, treeData) {
		try {
			const response = await fetch(`${this.baseUrl}/project-tree/${orgName}`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${this.getAuthToken()}`
				},
				body: JSON.stringify({
					tree_data: treeData
				})
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.error || 'Failed to save project tree data');
			}

			const data = await response.json();
			return {
				success: true,
				message: data.message || 'Project tree data saved successfully'
			};
		} catch (error) {
			console.error('❌ Error saving project tree data:', error);
			return {
				success: false,
				error: error.message || 'Failed to save project tree data'
			};
		}
	}

	/**
	 *todo:------------------- 📄 WORKFLOW CONTENT: Get workflow file content------------------------------------
	 */
	async getWorkflowContent(orgName, repoName, workflowPath) {
		try {
			const cacheKey = `workflow-content-${orgName}-${repoName}-${workflowPath}`;

			// Check cache first
			if (this.cache.has(cacheKey)) {
				const cached = this.cache.get(cacheKey);
				if (Date.now() - cached.timestamp < this.cacheExpiry) {
					return cached.data;
				}
			}

			const response = await fetch(
				`${this.baseUrl}/workspace/${orgName}/workflow/${repoName}/${encodeURIComponent(workflowPath)}`,
				{
					method: 'GET',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${await this.getAuthToken()}`
					}
				}
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.error || 'Failed to get workflow content');
			}

			const data = await response.json();
			const result = {
				success: true,
				content: data.content,
				path: data.path,
				sha: data.sha
			};

			// Cache the result
			this.cache.set(cacheKey, {
				data: result,
				timestamp: Date.now()
			});

			return result;
		} catch (error) {
			console.error('❌ Error getting workflow content:', error);
			return {
				success: false,
				error: error.message || 'Failed to get workflow content',
				content: ''
			};
		}
	}

	/**
	 * � WORKFLOW HISTORY: Get GitHub Actions workflow run history for real data
	 */
	async getGitHubActionsHistory(workflowId, orgName, repositoryName = null) {
		try {
			console.log(`📋 Getting GitHub Actions history for workflow ${workflowId} in ${orgName}`);
			if (repositoryName) {
				console.log(`📁 Repository specified: ${repositoryName}`);
			}

			// Check if we have a valid auth token
			const token = await this.getAuthToken();
			if (!token) {
				console.warn('⚠️ No authentication token available');
				return {
					success: false,
					error: 'No authentication token available',
					data: { runs: [], total_count: 0 }
				};
			}

			// Build URL with optional repository parameter
			let url = `${this.baseUrl}/workspace/${orgName}/workflows/${encodeURIComponent(workflowId)}/actions/history`;
			if (repositoryName && repositoryName !== 'undefined' && repositoryName !== 'unknown') {
				url += `?repo_name=${encodeURIComponent(repositoryName)}`;
			}

			console.log(`🌐 Making request to: ${url}`);

			// Use makeRequest method which handles auth and retries
			const data = await this.makeRequest(url, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			console.log('📊 Received GitHub Actions data:', data);

			// Check if the response indicates success
			if (data && data.success !== false) {
				return {
					success: true,
					source: 'GitHub Actions',
					data: {
						runs: data.workflow_runs || data.runs || [],
						total_count: data.total_count || 0,
						repository: data.repository
					}
				};
			} else {
				console.warn('⚠️ GitHub Actions API returned unsuccessful response:', data);
				return {
					success: false,
					error:
						data?.detail || data?.message || 'GitHub Actions API returned unsuccessful response',
					data: { runs: [], total_count: 0 }
				};
			}
		} catch (error) {
			console.error('❌ Error getting GitHub Actions history:', error);
			return {
				success: false,
				error: error.message || 'Failed to get GitHub Actions history',
				data: { runs: [], total_count: 0 }
			};
		}
	}

	/**
	 * 🔧 JENKINS: Get Jenkins build history for real data
	 */
	async getJenkinsBuilds(workflowId, orgName) {
		try {
			console.log(`🔧 Getting Jenkins builds for workflow ${workflowId} in ${orgName}`);

			const response = await this.makeRequest(
				`${this.baseUrl}/workspace/${orgName}/workflows/${workflowId}/jenkins/builds`,
				{
					method: 'GET',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${await this.getAuthToken()}`
					}
				}
			);

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			const data = await response.json();

			return {
				success: true,
				source: 'Jenkins',
				data: {
					runs: data.builds || data.runs || [],
					total_count: data.builds?.length || 0,
					job_name: data.name
				}
			};
		} catch (error) {
			console.error('❌ Error getting Jenkins builds:', error);
			return {
				success: false,
				error: error.message || 'Failed to get Jenkins builds',
				data: { runs: [], total_count: 0 }
			};
		}
	}

	/**
	 * 🦊 GITLAB: Get GitLab CI pipeline history for real data
	 */
	async getGitLabPipelines(workflowId, orgName) {
		try {
			console.log(`🦊 Getting GitLab CI pipelines for workflow ${workflowId} in ${orgName}`);

			const response = await this.makeRequest(
				`${this.baseUrl}/workspace/${orgName}/workflows/${workflowId}/gitlab/pipelines`,
				{
					method: 'GET',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${await this.getAuthToken()}`
					}
				}
			);

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			const data = await response.json();

			return {
				success: true,
				source: 'GitLab CI',
				data: {
					runs: data.pipelines || data.runs || [],
					total_count: data.pipelines?.length || 0,
					project_id: data.project_id
				}
			};
		} catch (error) {
			console.error('❌ Error getting GitLab pipelines:', error);
			return {
				success: false,
				error: error.message || 'Failed to get GitLab pipelines',
				data: { runs: [], total_count: 0 }
			};
		}
	}

	/**
	 * 🔐 SECURITY: Get organization security overview
	 */
	async getSecurityOverview(orgName) {
		const cacheKey = `security_overview_${orgName}`;

		// Check cache first
		const cached = this.getCachedData(cacheKey, true);
		if (cached) {
			return cached;
		}

		try {
			const result = await this.makeRequest(
				`${this.baseUrl}/security/organization/${orgName}/overview`
			);

			if (result.success) {
				this.setCachedData(cacheKey, result);
			}

			return result;
		} catch (error) {
			console.error('Failed to get security overview:', error);
			return { success: false, error: error.message };
		}
	}

	/**
	 * 🔐 SECURITY: Get recent security scans for organization
	 */
	async getRecentSecurityScans(orgName, limit = 10) {
		const cacheKey = `recent_scans_${orgName}_${limit}`;

		// Check cache first
		const cached = this.getCachedData(cacheKey, true);
		if (cached) {
			return cached;
		}

		try {
			const result = await this.makeRequest(
				`${this.baseUrl}/security/organization/${orgName}/scans/recent?limit=${limit}`
			);

			if (result.success) {
				this.setCachedData(cacheKey, result);
			}

			return result;
		} catch (error) {
			console.error('Failed to get recent security scans:', error);
			return { success: false, error: error.message, scans: [] };
		}
	}

	/**
	 * 🔐 SECURITY: Get organization security metrics
	 */
	async getOrganizationSecurityMetrics(orgName) {
		const cacheKey = `org_security_metrics_${orgName}`;

		// Check cache first
		const cached = this.getCachedData(cacheKey, true);
		if (cached) {
			return cached;
		}

		try {
			const result = await this.makeRequest(
				`${this.baseUrl}/security/organization/${orgName}/metrics`
			);

			if (result.success) {
				this.setCachedData(cacheKey, result);
			}

			return result;
		} catch (error) {
			console.error('Failed to get organization security metrics:', error);
			return { success: false, error: error.message, metrics: {} };
		}
	}

	/**
	 * 🔐 SECURITY: Get repository risk distribution for organization
	 */
	async getRepositoryRiskDistribution(orgName) {
		const cacheKey = `repo_risk_dist_${orgName}`;

		// Check cache first
		const cached = this.getCachedData(cacheKey, true);
		if (cached) {
			return cached;
		}

		try {
			const result = await this.makeRequest(
				`${this.baseUrl}/security/organization/${orgName}/repositories/risk`
			);

			if (result.success) {
				this.setCachedData(cacheKey, result);
			}

			return result;
		} catch (error) {
			console.error('Failed to get repository risk distribution:', error);
			return { success: false, error: error.message, repositories: [] };
		}
	}

	/**
	 * 🔐 SECURITY: Initiate organization-wide security scan
	 */
	async scanOrganizationSecurity(orgName, options = {}) {
		try {
			const scanPayload = {
				timeframe: options.timeframe || '7d',
				repositories: options.repositories || [] // Support repository selection
			};

			const result = await this.makeRequest(
				`${this.baseUrl}/security/organization/${orgName}/scan`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(scanPayload)
				}
			);

			// Clear security caches after scan
			this.clearSecurityCaches(orgName);

			return result;
		} catch (error) {
			console.error('Failed to initiate organization security scan:', error);
			return { success: false, error: error.message };
		}
	}

	/**
	 * 🔐 SECURITY: Clear security-related caches for organization
	 */
	clearSecurityCaches(orgName) {
		const securityKeys = Array.from(this.cache.keys()).filter(
			(key) => key.includes('security') && key.includes(orgName)
		);

		securityKeys.forEach((key) => {
			this.cache.delete(key);
			this.persistentCache.delete(key);
		});

		this.savePersistentCache();
		console.log(`🔄 Cleared ${securityKeys.length} security cache entries for ${orgName}`);
	}

	/**
	 * 🔐 AUTH: Get authentication token from localStorage or session
	 */
	getAuthToken() {
		if (typeof window === 'undefined') return null;

		// Try localStorage first, then sessionStorage
		return (
			localStorage.getItem('auth_token') ||
			sessionStorage.getItem('auth_token') ||
			localStorage.getItem('github_token')
		);
	}
}

// Export singleton instance
export const githubClient = new GitHubOrganizationClient();

// Make githubClient available globally for testing and debugging
if (typeof window !== 'undefined') {
	window.githubClient = githubClient;
	console.log('🧪 GitHub client available globally as window.githubClient for testing');
}
