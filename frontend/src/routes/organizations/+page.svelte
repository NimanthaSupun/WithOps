<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import { githubClient } from '$lib/github.js';
    import { userOrganizations, appStore, isDarkMode } from '$lib/stores.js';
    import { authState } from '$lib/authState.js';

    let loading = $state(true);
    let error = $state(null);
    let connectedOrganizations = $state([]);
    let discoveredOrganizations = $state([]); // Organizations from OAuth discovery
    let isRedirecting = $state(false); // Add flag to prevent multiple redirects
    let filterType = $state('all'); // 'all', 'owned', 'shared'
    
    // Subscribe to dark mode using Svelte 5 runes
    let darkMode = $state(false);
    
    $effect(() => {
        const unsubscribe = isDarkMode.subscribe(value => {
            darkMode = value;
        });
        return unsubscribe;
    });

    onMount(async () => {
        // Add a small delay to allow Auth0 to fully initialize after redirect
        await new Promise(resolve => setTimeout(resolve, 200));
        
        // Check if already redirecting to prevent loops
        if (isRedirecting) {
            console.log('🔄 Already redirecting, skipping...');
            return;
        }
        
        // Check for OAuth callback parameters (organization discovery)
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        
        if (code && state === 'discover_orgs') {
            console.log('🔍 OAuth callback detected - processing discovered organizations');
            await handleOrganizationDiscoveryCallback(code, state);
            // Clean up URL params after processing
            window.history.replaceState({}, '', window.location.pathname);
        } else {
            await loadConnectedOrganizations();
        }
        
        // Preload discovery URL in background for faster "Connect" button response
        githubClient.startOrganizationDiscovery().catch(error => {
            console.warn('Discovery URL preload failed:', error);
        });
    });

    async function loadConnectedOrganizations() {
        try {
            loading = true;
            error = null;
            
            console.log('🔐 Organizations page: Starting authentication check...');
            
            // Prevent multiple authentication attempts
            if (authState.isCurrentlyAuthenticating()) {
                console.log('🔐 Authentication already in progress, skipping...');
                loading = false;
                return;
            }
            
            // Skip if we just checked authentication recently
            if (authState.shouldSkipAuthCheck() && authState.hasValidToken()) {
                console.log('🔐 Recent auth check passed, proceeding with token...');
                // Continue to load organizations
            } else {
                // Mark auth check as done
                authState.markAuthCheckDone();
                
                // First check if we have a stored token (faster)
                if (authState.hasValidToken()) {
                    console.log('✅ Found stored auth token, proceeding...');
                } else {
                    // Only do Auth0 check if no stored token
                    console.log('🔐 No stored token, checking Auth0...');
                    authState.setAuthenticating(true);
                    
                    const { getAuthClient } = await import('$lib/auth');
                    const client = await getAuthClient();
                    const isAuthenticated = await client.isAuthenticated();
                    
                    console.log('🔐 Organizations page: Auth0 isAuthenticated:', isAuthenticated);
                    
                    if (!isAuthenticated) {
                        console.log('❌ User not authenticated - redirecting to login');
                        await client.loginWithRedirect();
                        return;
                    }
                    
                    authState.setAuthenticating(false);
                }
            }
            
            console.log('✅ User authenticated, loading organizations...');
            
            // Simple GitHub client check
            const token = await githubClient.getAuthToken();
            console.log('🔐 Organizations page: GitHub token available:', !!token);
            
            if (!token) {
                console.log('❌ No GitHub token available - need to login');
                // Clear auth state and redirect
                authState.clearAuthState();
                const { getAuthClient } = await import('$lib/auth');
                const client = await getAuthClient();
                await client.loginWithRedirect();
                return;
            }
            
            // For organization list, always fetch fresh data to ensure accurate installation status
            // This prevents showing organizations where the app was uninstalled
            console.log('🔄 Loading organizations with active app installations only...');
            
            const result = await githubClient.getMyActiveOrganizations();
            
            if (result.success) {
                console.log('📋 Raw organizations from backend:', result.organizations);
                
                // Show all organizations that the user has interacted with, but mark status correctly
                connectedOrganizations = result.organizations.map(org => {
                    console.log(`📋 Processing organization: ${org.login || org.name}, app_installed: ${org.app_installed}, can_access: ${org.can_access}`);
                    return {
                        login: org.login || org.name, // Use login field first, fallback to name
                        id: org.id,
                        avatar_url: org.avatar_url,
                        status: org.app_installed ? 'connected' : 'disconnected',
                        installation_id: org.installation_id,
                        repositories_count: 0,
                        workflows_count: 0,
                        last_synced: null,
                        last_verified: org.last_verified,
                        html_url: `https://github.com/${org.login || org.name}`,
                        loading_details: org.app_installed,
                        can_access: org.can_access,
                        installed_by_you: org.installed_by_you,
                        auto_linked: org.auto_linked,
                        installation: org.installation,
                        app_installed: org.app_installed // Preserve this field for consistency
                    };
                });
                
                console.log('📋 Processed organizations:', connectedOrganizations);
                
                appStore.setUserOrganizations(result.organizations);
                loading = false;
                
                // Load stats in background WITHOUT blocking UI
                setTimeout(() => loadOrganizationStats(), 100);
            } else {
                throw new Error(result.error || 'Failed to load organizations');
            }
        } catch (err) {
            console.error('❌ Error loading organizations:', err);
            
            // Handle authentication errors specifically
            const errorMessage = err.message || err.toString();
            if (errorMessage.includes('Authentication required') || 
                errorMessage.includes('Authentication expired') ||
                errorMessage.includes('Missing Refresh Token') ||
                errorMessage.includes('authentication failed')) {
                
                console.log('🔐 Authentication error detected, clearing state and redirecting...');
                // await forceReAuthentication();
                appStore.reset();
                goto('/');
                return;
            }
            
            error = errorMessage || 'Failed to load organizations';
            loading = false;
        }
    }
    
    async function handleOrganizationDiscoveryCallback(code, state) {
        try {
            loading = true;
            error = null;
            
            console.log('🔍 Processing organization discovery callback...');
            
            // Process the OAuth callback to get discovered organizations
            const callbackResult = await githubClient.processOrganizationCallback(code, state);
            
            if (!callbackResult.success) {
                throw new Error(callbackResult.error || 'Failed to process callback');
            }
            
            console.log('📋 Discovered organizations:', callbackResult.organizations);
            
            // Load installed organizations to cross-reference
            const installedResult = await githubClient.getMyActiveOrganizations();
            const installedOrgs = installedResult.success ? installedResult.organizations : [];
            
            console.log('📋 Installed organizations:', installedOrgs);
            
            // Create a map of installed org logins for quick lookup
            const installedOrgMap = new Map(
                installedOrgs.map(org => [org.login || org.name, org])
            );
            
            // Merge discovered organizations with installation status
            discoveredOrganizations = callbackResult.organizations.map(org => {
                const installedOrg = installedOrgMap.get(org.login);
                const isInstalled = !!installedOrg;
                
                console.log(`🔍 Org ${org.login}: installed=${isInstalled}`, installedOrg);
                
                return {
                    login: org.login,
                    id: org.id,
                    avatar_url: org.avatar_url,
                    html_url: `https://github.com/${org.login}`,
                    status: isInstalled ? 'connected' : 'available',
                    app_installed: isInstalled,
                    can_access: isInstalled ? installedOrg.can_access : false,
                    installation_id: isInstalled ? installedOrg.installation_id : null,
                    installed_by_you: isInstalled ? installedOrg.installed_by_you : false,
                    repositories_count: 0,
                    workflows_count: 0,
                    last_synced: null,
                    loading_details: false
                };
            });
            
            // Also load connected organizations
            connectedOrganizations = installedOrgs.map(org => ({
                login: org.login || org.name,
                id: org.id,
                avatar_url: org.avatar_url,
                status: 'connected',
                installation_id: org.installation_id,
                repositories_count: 0,
                workflows_count: 0,
                last_synced: null,
                last_verified: org.last_verified,
                html_url: `https://github.com/${org.login || org.name}`,
                loading_details: true,
                can_access: org.can_access,
                installed_by_you: org.installed_by_you,
                auto_linked: org.auto_linked,
                installation: org.installation,
                app_installed: org.app_installed
            }));
            
            console.log('✅ Discovery complete:', {
                discovered: discoveredOrganizations.length,
                connected: connectedOrganizations.length
            });
            
            loading = false;
            
            // Load stats for connected orgs in background
            setTimeout(() => loadOrganizationStats(), 100);
            
        } catch (err) {
            console.error('❌ Error processing discovery callback:', err);
            error = err.message || 'Failed to process organization discovery';
            loading = false;
        }
    }
    
    async function loadOrganizationStats() {
        console.log('📊 Starting to load organization stats...');
        
        // Load stats for ALL connected organizations (only those with app installed)
        const connectedOrgs = connectedOrganizations.filter(org => org.can_access && org.app_installed && org.status === 'connected');
        console.log(`📊 Loading stats for ${connectedOrgs.length} organizations:`, connectedOrgs.map(org => org.login));
        
        if (connectedOrgs.length === 0) {
            console.log('📊 No connected organizations found to load stats for');
            return;
        }
        
        const statsPromises = connectedOrgs.map(async (org) => {
            try {
                // Mark as loading IMMEDIATELY
                const orgIndex = connectedOrganizations.findIndex(o => o.login === org.login);
                if (orgIndex !== -1) {
                    connectedOrganizations[orgIndex] = {
                        ...connectedOrganizations[orgIndex],
                        loading_details: true,
                        error_loading: false
                    };
                    connectedOrganizations = [...connectedOrganizations];
                }
                
                console.log(`📊 Loading stats for ${org.login}...`);
                const statsResult = await githubClient.getOrganizationStats(org.login);
                
                if (statsResult.success) {
                    console.log(`✅ Stats loaded for ${org.login}:`, statsResult);
                    // Update organization data
                    const currentOrgIndex = connectedOrganizations.findIndex(o => o.login === org.login);
                    if (currentOrgIndex !== -1) {
                        connectedOrganizations[currentOrgIndex] = {
                            ...connectedOrganizations[currentOrgIndex],
                            repositories_count: statsResult.repository_count || 0,
                            workflows_count: statsResult.total_workflows || 0,
                            last_synced: statsResult.last_updated || new Date().toISOString(),
                            loading_details: false,
                            error_loading: false
                        };
                        connectedOrganizations = [...connectedOrganizations];
                    }
                } else {
                    console.warn(`❌ Failed to load stats for ${org.login}:`, statsResult.error);
                    const currentOrgIndex = connectedOrganizations.findIndex(o => o.login === org.login);
                    if (currentOrgIndex !== -1) {
                        connectedOrganizations[currentOrgIndex] = {
                            ...connectedOrganizations[currentOrgIndex],
                            loading_details: false,
                            error_loading: true
                        };
                        connectedOrganizations = [...connectedOrganizations];
                    }
                }
            } catch (error) {
                console.warn(`Failed to load stats for ${org.login}:`, error);
                const currentOrgIndex = connectedOrganizations.findIndex(o => o.login === org.login);
                if (currentOrgIndex !== -1) {
                    connectedOrganizations[currentOrgIndex] = {
                        ...connectedOrganizations[currentOrgIndex],
                        loading_details: false,
                        error_loading: true
                    };
                    connectedOrganizations = [...connectedOrganizations];
                }
            }
        });
        
        // Wait for all stats to load with better error handling
        try {
            await Promise.allSettled(statsPromises);
            console.log('📊 All organization stats loading completed');
        } catch (error) {
            console.error('Error during stats loading:', error);
        }
    }

    async function connectNewOrganization() {
        try {
            const result = await githubClient.startOrganizationDiscovery();
            
            if (result.success) {
                // Redirect to GitHub OAuth for organization discovery
                window.location.href = result.oauth_url;
            } else {
                console.error('Failed to start GitHub connection:', result.error);
                alert('Failed to start GitHub connection. Please try again.');
            }
        } catch (error) {
            console.error('GitHub connection error:', error);
            alert('Failed to connect to GitHub. Please try again.');
        }
    }
    
    async function viewOrganizationWorkspace(orgName) {
        try {
            console.log(`🏢 Attempting to view workspace for ${orgName}`);
            
            // Simple approach: just try to navigate and let the workspace page handle verification
            // The backend logs show it's working correctly, so trust that
            const org = connectedOrganizations.find(o => o.login === orgName);
            if (org && org.app_installed === false) {
                alert(`GitHub App is not installed in ${orgName}. Please install the app to access the workspace.`);
                return;
            }
            
            console.log(`✅ Navigating to workspace for ${orgName}`);
            
            // Optimistic navigation - go to workspace immediately
            goto(`/github/workspace/${orgName}`);
            
            // Preload data if not cached to ensure it's ready
            const cached = githubClient.getCachedData(`workspace_${orgName}`);
            if (!cached) {
                // Start loading in background while user sees the UI
                githubClient.getOrganizationWorkspace(orgName).then((result) => {
                    if (result.success) {
                        // If workspace loads successfully, restore org status in case cache was wrong
                        githubClient.restoreOrganizationStatus(orgName);
                    }
                }).catch(error => {
                    console.warn(`Background workspace load failed for ${orgName}:`, error);
                });
            }
        } catch (error) {
            console.error('Workspace navigation error:', error);
            alert('Failed to navigate to workspace. Please try again.');
        }
    }
    
    
    async function cleanupStaleInstallations() {
        try {
            loading = true;
            
            // Only clear specific cache entries, not everything
            githubClient.cache.delete('my_organizations');
            githubClient.cache.delete('user_installations');
            
            // Also clear stats cache for all organizations
            connectedOrganizations.forEach(org => {
                githubClient.cache.delete(`stats_${org.login}`);
            });
            
            const result = await githubClient.cleanupInstallations();
            
            if (result.success) {
                console.log('🧹 Cleanup completed:', result);
                alert(`Cleanup completed! Removed ${result.cleaned_count} stale installations.`);
                
                // Reload organizations after cleanup
                await loadConnectedOrganizations();
            } else {
                console.error('Cleanup failed:', result.error);
                alert('Cleanup failed: ' + result.error);
            }
        } catch (error) {
            console.error('Cleanup error:', error);
            alert('Cleanup failed: ' + error.message);
        } finally {
            loading = false;
        }
    }

    async function retryLoadDetails(orgName) {
        try {
            const orgIndex = connectedOrganizations.findIndex(o => o.login === orgName);
            if (orgIndex === -1) return;
            
            // Mark as loading again
            connectedOrganizations[orgIndex] = {
                ...connectedOrganizations[orgIndex],
                loading_details: true,
                error_loading: false
            };
            connectedOrganizations = [...connectedOrganizations];
            
            console.log(`🔄 Retrying stats for ${orgName}...`);
            const statsResult = await githubClient.getOrganizationStats(orgName);
            console.log(`� Retry result for ${orgName}:`, statsResult);
            
            if (statsResult.success) {
                connectedOrganizations[orgIndex] = {
                    ...connectedOrganizations[orgIndex],
                    repositories_count: statsResult.repository_count || 0,
                    workflows_count: statsResult.total_workflows || 0,
                    last_synced: statsResult.last_updated || new Date().toISOString(),
                    loading_details: false,
                    error_loading: false
                };
                connectedOrganizations = [...connectedOrganizations];
                console.log(`✅ Retry successful for ${orgName}`);
            } else {
                connectedOrganizations[orgIndex] = {
                    ...connectedOrganizations[orgIndex],
                    loading_details: false,
                    error_loading: true
                };
                connectedOrganizations = [...connectedOrganizations];
            }
        } catch (error) {
            console.warn(`Failed to retry ${orgName}:`, error);
            const orgIndex = connectedOrganizations.findIndex(o => o.login === orgName);
            if (orgIndex !== -1) {
                connectedOrganizations[orgIndex] = {
                    ...connectedOrganizations[orgIndex],
                    loading_details: false,
                    error_loading: true
                };
                connectedOrganizations = [...connectedOrganizations];
            }
        }
    }

    async function refreshOrganizations() {
        try {
            loading = true;
            error = null;
            
            console.log('🔄 Starting organizations refresh...');
            
            // Clear cache to force fresh data
            githubClient.cache.delete('my_organizations');
            
            // Also clear stats cache for all organizations
            connectedOrganizations.forEach(org => {
                githubClient.cache.delete(`stats_${org.login}`);
            });
            
            // Force reload organizations and stats
            await loadConnectedOrganizations();
            
            console.log('🔄 Organizations refreshed successfully');
        } catch (err) {
            console.error('Failed to refresh organizations:', err);
            error = err.message || 'Failed to refresh organizations';
        } finally {
            loading = false;
        }
    }

    // Debug function to test API connectivity
    async function testApiConnectivity() {
        try {
            console.log('🧪 Testing API connectivity...');
            
            // Test basic auth
            const token = await githubClient.getAuthToken();
            console.log('✅ Auth token obtained:', token ? 'Success' : 'Failed');
            
            // Test organizations endpoint
            const orgsResult = await githubClient.getMyOrganizations();
            console.log('✅ Organizations API result:', orgsResult);
            
            // Test stats endpoint for first org if available
            if (orgsResult.success && orgsResult.organizations.length > 0) {
                const firstOrg = orgsResult.organizations[0].name;
                console.log(`🧪 Testing stats for ${firstOrg}...`);
                const statsResult = await githubClient.getOrganizationStats(firstOrg);
                console.log('✅ Stats API result:', statsResult);
            }
            
            alert('API test completed. Check console for details.');
        } catch (error) {
            console.error('❌ API test failed:', error);
            alert('API test failed: ' + error.message);
        }
    }

    async function generateInstallationUrl(orgName, orgId) {
        try {
            console.log(`🔧 Generating installation URL for ${orgName}`);
            
            const result = await githubClient.generateInstallationUrl(orgName, orgId);
            
            if (result.success) {
                // Redirect to GitHub for app installation
                window.location.href = result.installation_url;
            } else {
                console.error('Failed to generate installation URL:', result.error);
                alert('Failed to generate installation URL. Please try again.');
            }
        } catch (error) {
            console.error('Installation URL generation error:', error);
            alert('Failed to generate installation URL. Please try again.');
        }
    }
</script>

<svelte:head>
    <title>GitHub Organizations - WithOps DevSecOps Platform</title>
</svelte:head>

<div class="organizations-page {darkMode ? 'dark' : 'light'}">
  <!-- Background Effects -->
  <div class="page-background">
    <div class="page-glow-1"></div>
    <div class="page-glow-2"></div>
    <div class="github-pattern"></div>
  </div>

  <div class="page-content">
    <!-- Header Section -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-main">
          <div class="header-icon">
            <svg fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
          </div>
          <div class="header-text">
            <h1 class="header-title">GitHub Organizations</h1>
            <p class="header-description">Manage your connected GitHub organizations and workspaces</p>
          </div>
        </div>
        
        <div class="header-actions">
          <button 
            onclick={cleanupStaleInstallations}
            class="action-button cleanup-button"
            title="Clean up deleted GitHub App installations"
          >
            <div class="button-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </div>
            <span>Cleanup</span>
          </button>

          <button 
            onclick={refreshOrganizations}
            class="action-button refresh-button"
          >
            <div class="button-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
            </div>
            <span>Refresh</span>
          </button>

          <button 
            onclick={connectNewOrganization}
            class="action-button primary-button"
          >
            <div class="button-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
              </svg>
            </div>
            <span>Connect Organization</span>
            <div class="button-arrow">→</div>
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="page-main">
      {#if loading}
        <!-- Loading State -->
        <div class="state-card loading-state">
          <div class="loading-section">
            <div class="loading-icon">
              <div class="github-logo">
                <svg fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
              </div>
              <div class="scanning-animation">
                <div class="scan-line"></div>
              </div>
            </div>
            <div class="loading-content">
              <h2 class="loading-title">Loading Organizations</h2>
              <p class="loading-message">Discovering your GitHub workspaces...</p>
              <div class="progress-dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
              </div>
            </div>
          </div>
        </div>
      {:else if error}
        <!-- Error State -->
        <div class="state-card error-state">
          <div class="error-section">
            <div class="error-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.958-.833-2.728 0L4.186 14.5c-.77.833.192 2.5 1.732 2.5z"/>
              </svg>
            </div>
            <div class="error-content">
              <h2 class="error-title">Error Loading Organizations</h2>
              <p class="error-message">{error}</p>
              <button 
                onclick={loadConnectedOrganizations}
                class="retry-button"
              >
                <svg class="retry-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                Try Again
              </button>
            </div>
          </div>
        </div>
      {:else if connectedOrganizations.length === 0}
        <!-- Empty State -->
        <div class="state-card empty-state">
          <div class="empty-section">
            <div class="empty-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
              </svg>
            </div>
            <div class="empty-content">
              <h3 class="empty-title">No Organizations Connected</h3>
              <p class="empty-description">
                Connect your first GitHub organization to get started with DevSecOps workflows and security scanning.
              </p>
              <button 
                onclick={connectNewOrganization}
                class="connect-button"
              >
                <div class="button-icon">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                  </svg>
                </div>
                <span>Connect to GitHub</span>
                <div class="button-arrow">→</div>
              </button>
            </div>
          </div>
        </div>
      {:else}
        <!-- Filter Controls -->
        <div class="filter-section">
          <div class="filter-buttons">
            <button 
              class="filter-button {filterType === 'all' ? 'active' : ''}"
              onclick={() => filterType = 'all'}
            >
              <span class="filter-icon">📊</span>
              All Organizations
              <span class="filter-count">{connectedOrganizations.length}</span>
            </button>
            
            <button 
              class="filter-button {filterType === 'owned' ? 'active' : ''}"
              onclick={() => filterType = 'owned'}
            >
              <span class="filter-icon">🏆</span>
              My Installations
              <span class="filter-count">{connectedOrganizations.filter(o => o.installed_by_you).length}</span>
            </button>
            
            <button 
              class="filter-button {filterType === 'shared' ? 'active' : ''}"
              onclick={() => filterType = 'shared'}
            >
              <span class="filter-icon">👥</span>
              Shared with Me
              <span class="filter-count">{connectedOrganizations.filter(o => o.auto_linked).length}</span>
            </button>
          </div>
        </div>
        
        <!-- Organizations Grid -->
        <div class="organizations-grid">
          {#each connectedOrganizations.filter(org => {
            if (filterType === 'owned') return org.installed_by_you;
            if (filterType === 'shared') return org.auto_linked;
            return true;
          }) as org}
            <div class="org-card {org.status === 'connected' ? 'connected' : 'disconnected'}">
              <!-- Organization Header -->
              <div class="org-card-header">
                <div class="org-info">
                  <div class="org-avatar">
                    <img src={org.avatar_url} alt="{org.login} avatar" />
                    <div class="avatar-glow"></div>
                  </div>
                  <div class="org-details">
                    <h3 class="org-name">{org.login}</h3>
                    <div class="org-status">
                      {#if org.status === 'connected'}
                        <div class="status-badge connected-badge">
                          <div class="badge-icon">✅</div>
                          <span>Connected</span>
                        </div>
                        
                        <!-- Owner/Shared Badge -->
                        {#if org.installed_by_you}
                          <div class="status-badge owner-badge">
                            <div class="badge-icon">🏆</div>
                            <span>Owner</span>
                          </div>
                        {:else if org.auto_linked}
                          <div class="status-badge shared-badge">
                            <div class="badge-icon">👥</div>
                            <span>Shared Access</span>
                          </div>
                        {/if}
                      {:else}
                        <div class="status-badge pending-badge">
                          <div class="badge-icon">⏳</div>
                          <span>Pending</span>
                        </div>
                      {/if}
                    </div>
                  </div>
                </div>
              </div>

              <!-- Statistics -->
              <div class="org-stats">
                <div class="stat-item">
                  <div class="stat-label">Repositories</div>
                  <div class="stat-value">
                    {#if org.loading_details}
                      <div class="stat-skeleton"></div>
                    {:else if org.error_loading}
                      <span class="stat-error">—</span>
                    {:else}
                      {org.repositories_count ?? '—'}
                    {/if}
                  </div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">Workflows</div>
                  <div class="stat-value">
                    {#if org.loading_details}
                      <div class="stat-skeleton"></div>
                    {:else if org.error_loading}
                      <span class="stat-error">—</span>
                    {:else}
                      {org.workflows_count ?? '—'}
                    {/if}
                  </div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">Team Size</div>
                  <div class="stat-value">
                    {#if org.installation?.linked_user_count}
                      {org.installation.linked_user_count + 1} members
                    {:else if org.installed_by_you}
                      1 member
                    {:else}
                      —
                    {/if}
                  </div>
                </div>
                <div class="stat-item full-width">
                  <div class="stat-label">Last verified</div>
                  <div class="stat-value">
                    {#if org.last_verified}
                      {new Date(org.last_verified).toLocaleString()}
                    {:else if org.last_synced}
                      {new Date(org.last_synced).toLocaleDateString()}
                    {:else}
                      Never
                    {/if}
                  </div>
                </div>
              </div>

              <!-- Actions -->
              <div class="org-actions">
                {#if org.app_installed && org.status === 'connected'}
                  <button 
                    onclick={() => viewOrganizationWorkspace(org.login)}
                    onmouseenter={() => githubClient.preloadOrganizationWorkspace(org.login)}
                    class="org-button workspace-button"
                  >
                    <div class="button-icon">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                      </svg>
                    </div>
                    <span>View Workspace</span>
                    <div class="button-arrow">→</div>
                  </button>
                {:else}
                  <button 
                    onclick={() => generateInstallationUrl(org.login, org.id)}
                    class="org-button install-button"
                  >
                    <div class="button-icon">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                      </svg>
                    </div>
                    <span>Install App</span>
                    <div class="button-arrow">→</div>
                  </button>
                {/if}
                
                {#if org.error_loading}
                  <button 
                    onclick={() => retryLoadDetails(org.login)}
                    class="org-button retry-button"
                    title="Retry loading details"
                  >
                    <div class="button-icon">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                      </svg>
                    </div>
                    <span>Retry</span>
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
        
        <!-- Discovered Organizations Section (from OAuth discovery) -->
        {#if discoveredOrganizations.length > 0}
          <div class="section-divider"></div>
          
          <div class="section-header">
            <h2 class="section-title">Select Organization to Connect</h2>
            <p class="section-description">
              Choose an organization from your GitHub account to install the DevSecOps app
            </p>
          </div>
          
          <div class="organizations-grid">
            {#each discoveredOrganizations as org}
              <div class="org-card {org.status === 'connected' ? 'connected' : 'available'}">
                <!-- Organization Header -->
                <div class="org-card-header">
                  <div class="org-info">
                    <div class="org-avatar">
                      <img src={org.avatar_url} alt="{org.login} avatar" />
                      <div class="avatar-glow"></div>
                    </div>
                    <div class="org-details">
                      <h3 class="org-name">{org.login}</h3>
                      <div class="org-status">
                        {#if org.app_installed}
                          <div class="status-badge connected-badge">
                            <div class="badge-icon">✅</div>
                            <span>Connected</span>
                          </div>
                        {:else}
                          <div class="status-badge available-badge">
                            <div class="badge-icon">📦</div>
                            <span>Available</span>
                          </div>
                        {/if}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Statistics Placeholder -->
                <div class="org-stats">
                  <div class="stat-item">
                    <div class="stat-label">GitHub Organization</div>
                    <div class="stat-value">
                      <a href={org.html_url} target="_blank" class="org-link">View on GitHub →</a>
                    </div>
                  </div>
                </div>

                <!-- Actions -->
                <div class="org-actions">
                  {#if org.app_installed && org.status === 'connected'}
                    <button 
                      onclick={() => viewOrganizationWorkspace(org.login)}
                      class="org-button workspace-button"
                    >
                      <div class="button-icon">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                      </div>
                      <span>View Workspace</span>
                      <div class="button-arrow">→</div>
                    </button>
                  {:else}
                    <button 
                      onclick={() => generateInstallationUrl(org.login, org.id)}
                      class="org-button install-button"
                    >
                      <div class="button-icon">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                        </svg>
                      </div>
                      <span>Install App</span>
                      <div class="button-arrow">→</div>
                    </button>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </main>

    <!-- Footer -->
    <footer class="page-footer">
      <button 
        onclick={() => goto('/dashboard')}
        class="back-button"
      >
        <svg class="back-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
        </svg>
        Back to Dashboard
      </button>
    </footer>
  </div>
</div>

<style>
  /* Global Variables */
  .organizations-page {
    --bg-primary: #000000;
    --bg-secondary: #0A0A0A;
    --text-primary: #FFFFFF;
    --text-secondary: #CCCCCC;
    --text-muted: #888888;
    --border-color: rgba(74, 158, 255, 0.2);
    --card-bg: rgba(255, 255, 255, 0.05);
    --primary-color: #4A9EFF;
    --success-color: #00FF66;
    --error-color: #ff4757;
    --accent-color: #FF8B4A;
    --github-color: #24292f;
    --connected-color: #16a34a;
    --warning-color: #f59e0b;
  }

  .organizations-page.light {
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --text-primary: #1a1a1a;
    --text-secondary: #2d3748;
    --text-muted: #64748b;
    --border-color: rgba(9, 105, 218, 0.2);
    --card-bg: rgba(255, 255, 255, 0.95);
    --primary-color: #0969da;
    --success-color: #16a34a;
    --error-color: #dc2626;
    --accent-color: #ea580c;
    --github-color: #24292f;
    --connected-color: #16a34a;
    --warning-color: #f59e0b;
  }

  /* Main Container */
  .organizations-page {
    position: relative;
    min-height: 100vh;
    background: var(--bg-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    overflow-x: hidden;
  }

  /* Background Effects */
  .page-background {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
  }

  .page-glow-1 {
    position: absolute;
    top: 5%;
    left: 5%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(74, 158, 255, 0.12) 0%, transparent 70%);
    border-radius: 50%;
    animation: float-large 20s ease-in-out infinite;
  }

  .page-glow-2 {
    position: absolute;
    bottom: 5%;
    right: 5%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(255, 139, 74, 0.08) 0%, transparent 70%);
    border-radius: 50%;
    animation: float-large 25s ease-in-out infinite reverse;
  }

  .github-pattern {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: 
      radial-gradient(circle at 25% 25%, rgba(74, 158, 255, 0.06) 2px, transparent 2px),
      radial-gradient(circle at 75% 75%, rgba(255, 139, 74, 0.06) 2px, transparent 2px);
    background-size: 150px 150px;
    animation: pattern-drift 30s linear infinite;
  }

  @keyframes float-large {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-50px) rotate(5deg); }
  }

  @keyframes pattern-drift {
    0% { transform: translateX(0) translateY(0); }
    100% { transform: translateX(-150px) translateY(-150px); }
  }

  /* Content Container */
  .page-content {
    position: relative;
    z-index: 2;
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* Header */
  .page-header {
    margin-bottom: 3rem;
  }

  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
    flex-wrap: wrap;
  }

  .header-main {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }

  .header-icon {
    width: 70px;
    height: 70px;
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    box-shadow: 0 10px 30px rgba(74, 158, 255, 0.3);
  }

  .header-icon svg {
    width: 35px;
    height: 35px;
  }

  .header-text {
    flex: 1;
  }

  .header-title {
    font-size: 3rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.5rem 0;
    line-height: 1.1;
    background: linear-gradient(135deg, var(--text-primary) 0%, var(--primary-color) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .header-description {
    font-size: 1.2rem;
    color: var(--text-secondary);
    margin: 0;
    opacity: 0.9;
  }

  /* Header Actions */
  .header-actions {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .action-button {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 1.5rem;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    font-size: 0.95rem;
  }

  .action-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.6s ease;
  }

  .action-button:hover::before {
    left: 100%;
  }

  .cleanup-button {
    background: rgba(245, 158, 11, 0.1);
    color: var(--warning-color);
    border: 1px solid rgba(245, 158, 11, 0.2);
  }

  .cleanup-button:hover {
    background: var(--warning-color);
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(245, 158, 11, 0.3);
  }

  .refresh-button {
    background: rgba(136, 136, 136, 0.1);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
  }

  .refresh-button:hover {
    background: var(--primary-color);
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3);
  }

  .primary-button {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
    color: white;
    box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3);
  }

  .primary-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 35px rgba(74, 158, 255, 0.4);
  }

  .button-icon {
    width: 20px;
    height: 20px;
  }

  .button-arrow {
    font-size: 1.2rem;
    transition: transform 0.3s ease;
  }

  .action-button:hover .button-arrow {
    transform: translateX(4px);
  }

  /* Main Content */
  .page-main {
    flex: 1;
    margin-bottom: 3rem;
  }

  /* State Cards */
  .state-card {
    background: linear-gradient(145deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-color);
    border-radius: 24px;
    padding: 3rem;
    text-align: center;
    box-shadow: 
      0 20px 40px rgba(0, 0, 0, 0.1),
      0 8px 16px rgba(74, 158, 255, 0.05),
      inset 0 1px 0 rgba(255, 255, 255, 0.1);
  }

  .organizations-page.light .state-card {
    box-shadow: 
      0 20px 40px rgba(0, 0, 0, 0.08),
      0 8px 16px rgba(9, 105, 218, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
  }

  /* Loading State */
  .loading-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
  }

  .loading-icon {
    position: relative;
    width: 120px;
    height: 120px;
  }

  .github-logo {
    width: 100px;
    height: 100px;
    color: var(--primary-color);
    margin: 0 auto;
  }

  .github-logo svg {
    width: 100%;
    height: 100%;
    filter: drop-shadow(0 0 20px currentColor);
  }

  .scanning-animation {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: 2px solid var(--primary-color);
    border-radius: 50%;
    animation: scan-pulse 2s ease-in-out infinite;
  }

  .scan-line {
    position: absolute;
    top: 50%;
    left: 10%;
    width: 80%;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
    transform: translateY(-50%);
    animation: scan-sweep 2s ease-in-out infinite;
  }

  @keyframes scan-pulse {
    0%, 100% { opacity: 0.3; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.1); }
  }

  @keyframes scan-sweep {
    0%, 100% { opacity: 0; transform: translateY(-50%) rotate(0deg); }
    50% { opacity: 1; transform: translateY(-50%) rotate(180deg); }
  }

  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .loading-title {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }

  .loading-message {
    font-size: 1.2rem;
    color: var(--text-secondary);
    margin: 0;
  }

  .progress-dots {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
  }

  .dot {
    width: 10px;
    height: 10px;
    background: var(--primary-color);
    border-radius: 50%;
    animation: dot-bounce 1.5s ease-in-out infinite;
  }

  .dot:nth-child(2) { animation-delay: 0.3s; }
  .dot:nth-child(3) { animation-delay: 0.6s; }

  @keyframes dot-bounce {
    0%, 80%, 100% { transform: scale(1); opacity: 0.7; }
    40% { transform: scale(1.3); opacity: 1; }
  }

  /* Error State */
  .error-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
  }

  .error-icon {
    width: 100px;
    height: 100px;
    color: var(--error-color);
    background: rgba(255, 71, 87, 0.1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .error-icon svg {
    width: 50px;
    height: 50px;
  }

  .error-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
    max-width: 500px;
  }

  .error-title {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }

  .error-message {
    font-size: 1.1rem;
    color: var(--error-color);
    margin: 0;
    line-height: 1.6;
  }

  .retry-button {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 2rem;
    background: var(--error-color);
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .retry-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(255, 71, 87, 0.3);
  }

  .retry-icon {
    width: 18px;
    height: 18px;
  }
  
  /* Filter Section */
  .filter-section {
    padding: 0 2.5rem 1.5rem;
  }
  
  .filter-buttons {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }
  
  .filter-button {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.5rem;
    background: rgba(74, 158, 255, 0.05);
    border: 1px solid rgba(74, 158, 255, 0.2);
    border-radius: 12px;
    color: var(--text-secondary);
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
  }
  
  .filter-button:hover {
    background: rgba(74, 158, 255, 0.1);
    border-color: var(--primary-color);
    transform: translateY(-2px);
  }
  
  .filter-button.active {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
    border-color: var(--primary-color);
    color: white;
    box-shadow: 0 4px 15px rgba(74, 158, 255, 0.3);
  }
  
  .filter-icon {
    font-size: 1.1rem;
  }
  
  .filter-count {
    padding: 0.25rem 0.5rem;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
  }
  
  .filter-button.active .filter-count {
    background: rgba(255, 255, 255, 0.3);
  }

  /* Empty State */
  .empty-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
  }

  .empty-icon {
    width: 120px;
    height: 120px;
    background: rgba(136, 136, 136, 0.1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
  }

  .empty-icon svg {
    width: 60px;
    height: 60px;
  }

  .empty-content {
    max-width: 600px;
  }

  .empty-title {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 1rem 0;
  }

  .empty-description {
    font-size: 1.2rem;
    color: var(--text-secondary);
    line-height: 1.6;
    margin: 0 0 2rem 0;
  }

  .connect-button {
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1.25rem 2rem;
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
    color: white;
    border: none;
    border-radius: 16px;
    font-weight: 600;
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3);
  }

  .connect-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.6s ease;
  }

  .connect-button:hover::before {
    left: 100%;
  }

  .connect-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 35px rgba(74, 158, 255, 0.4);
  }

  .connect-button:hover .button-arrow {
    transform: translateX(4px);
  }

  /* Organizations Grid */
  .organizations-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
  }

  /* Organization Card */
  .org-card {
    background: linear-gradient(145deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 2rem;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    box-shadow: 
      0 10px 30px rgba(0, 0, 0, 0.1),
      0 4px 12px rgba(74, 158, 255, 0.05),
      inset 0 1px 0 rgba(255, 255, 255, 0.1);
  }

  .organizations-page.light .org-card {
    box-shadow: 
      0 10px 30px rgba(0, 0, 0, 0.08),
      0 4px 12px rgba(9, 105, 218, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
  }

  .org-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 4px;
    background: linear-gradient(90deg, var(--primary-color) 0%, var(--accent-color) 100%);
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.3s ease;
  }

  .org-card:hover::before {
    transform: scaleX(1);
  }

  .org-card:hover {
    transform: translateY(-6px);
    border-color: var(--primary-color);
    box-shadow: 
      0 20px 50px rgba(0, 0, 0, 0.15),
      0 8px 20px rgba(74, 158, 255, 0.15),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
  }

  .org-card.connected {
    border-color: rgba(22, 163, 74, 0.3);
  }

  .org-card.connected::before {
    background: var(--connected-color);
  }

  .org-card.connected:hover {
    border-color: var(--connected-color);
    box-shadow: 
      0 20px 50px rgba(0, 0, 0, 0.15),
      0 8px 20px rgba(22, 163, 74, 0.15),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
  }

  /* Organization Card Header */
  .org-card-header {
    margin-bottom: 2rem;
  }

  .org-info {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .org-avatar {
    position: relative;
    width: 70px;
    height: 70px;
  }

  .org-avatar img {
    width: 100%;
    height: 100%;
    border-radius: 16px;
    border: 2px solid var(--border-color);
  }

  .avatar-glow {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 90px;
    height: 90px;
    background: radial-gradient(circle, rgba(74, 158, 255, 0.2) 0%, transparent 70%);
    border-radius: 50%;
    animation: avatar-pulse 3s ease-in-out infinite;
  }

  @keyframes avatar-pulse {
    0%, 100% { opacity: 0.3; transform: translate(-50%, -50%) scale(1); }
    50% { opacity: 0.6; transform: translate(-50%, -50%) scale(1.2); }
  }

  .org-details {
    flex: 1;
  }

  .org-name {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 0.75rem 0;
  }

  .org-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border-radius: 10px;
    font-size: 0.9rem;
    font-weight: 500;
  }

  .connected-badge {
    background: rgba(22, 163, 74, 0.1);
    color: var(--connected-color);
    border: 1px solid rgba(22, 163, 74, 0.2);
  }

  .pending-badge {
    background: rgba(245, 158, 11, 0.1);
    color: var(--warning-color);
    border: 1px solid rgba(245, 158, 11, 0.2);
  }
  
  .available-badge {
    background: rgba(74, 158, 255, 0.1);
    color: var(--primary-color);
    border: 1px solid rgba(74, 158, 255, 0.2);
  }
  
  .owner-badge {
    background: rgba(255, 215, 0, 0.1);
    color: #fbbf24;
    border: 1px solid rgba(255, 215, 0, 0.3);
    box-shadow: 0 0 10px rgba(255, 215, 0, 0.1);
  }
  
  .shared-badge {
    background: rgba(139, 92, 246, 0.1);
    color: #a78bfa;
    border: 1px solid rgba(139, 92, 246, 0.3);
  }

  .badge-icon {
    font-size: 1rem;
  }
  
  /* Section Divider */
  .section-divider {
    height: 1px;
    background: linear-gradient(
      to right,
      transparent,
      rgba(74, 158, 255, 0.3),
      transparent
    );
    margin: 3rem 0 2rem;
  }
  
  .section-header {
    text-align: center;
    margin-bottom: 2rem;
  }
  
  .section-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
  }
  
  .section-description {
    font-size: 1rem;
    color: var(--text-secondary);
  }
  
  .org-link {
    color: var(--primary-color);
    text-decoration: none;
    font-size: 0.9rem;
    transition: opacity 0.2s;
  }
  
  .org-link:hover {
    opacity: 0.8;
  }

  /* Statistics */
  .org-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: rgba(74, 158, 255, 0.05);
    border: 1px solid rgba(74, 158, 255, 0.1);
    border-radius: 12px;
  }

  .stat-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .stat-item.full-width {
    grid-column: 1 / -1;
  }

  .stat-label {
    font-size: 0.85rem;
    color: var(--text-muted);
    font-weight: 500;
  }

  .stat-value {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .stat-skeleton {
    width: 40px;
    height: 16px;
    background: rgba(136, 136, 136, 0.2);
    border-radius: 4px;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
  }

  @keyframes skeleton-pulse {
    0%, 100% { opacity: 0.7; }
    50% { opacity: 1; }
  }

  .stat-error {
    color: var(--error-color);
    font-size: 0.9rem;
  }

  /* Organization Actions */
  .org-actions {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .org-button {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 1.5rem;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    font-size: 0.9rem;
    flex: 1;
    justify-content: center;
  }

  .org-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.6s ease;
  }

  .org-button:hover::before {
    left: 100%;
  }

  .workspace-button {
    background: linear-gradient(135deg, var(--connected-color) 0%, #22c55e 100%);
    color: white;
    box-shadow: 0 6px 20px rgba(22, 163, 74, 0.3);
  }

  .workspace-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(22, 163, 74, 0.4);
  }

  .install-button {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
    color: white;
    box-shadow: 0 6px 20px rgba(74, 158, 255, 0.3);
  }

  .install-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(74, 158, 255, 0.4);
  }

  .retry-button {
    background: rgba(245, 158, 11, 0.1);
    color: var(--warning-color);
    border: 1px solid rgba(245, 158, 11, 0.2);
    flex: 0 0 auto;
    min-width: auto;
  }

  .retry-button:hover {
    background: var(--warning-color);
    color: white;
    transform: translateY(-2px);
  }

  .org-button:hover .button-arrow {
    transform: translateX(4px);
  }

  /* Footer */
  .page-footer {
    text-align: center;
    padding-top: 2rem;
    border-top: 1px solid var(--border-color);
  }

  .back-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem 1.5rem;
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .back-button:hover {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
    transform: translateY(-1px);
  }

  .back-icon {
    width: 18px;
    height: 18px;
  }

  /* Responsive Design */
  @media (max-width: 1024px) {
    .organizations-grid {
      grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
      gap: 1.5rem;
    }

    .header-content {
      flex-direction: column;
      align-items: flex-start;
      gap: 1.5rem;
    }

    .header-title {
      font-size: 2.5rem;
    }
  }

  @media (max-width: 768px) {
    .page-content {
      padding: 1.5rem;
    }

    .header-main {
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 1rem;
    }

    .header-actions {
      width: 100%;
      justify-content: center;
    }

    .action-button {
      flex: 1;
      justify-content: center;
    }

    .organizations-grid {
      grid-template-columns: 1fr;
    }

    .org-stats {
      grid-template-columns: 1fr;
    }

    .org-actions {
      flex-direction: column;
    }

    .header-title {
      font-size: 2rem;
    }

    .state-card {
      padding: 2rem;
    }
  }

  @media (max-width: 480px) {
    .page-content {
      padding: 1rem;
    }

    .org-card {
      padding: 1.5rem;
    }

    .header-actions {
      flex-direction: column;
      gap: 0.75rem;
    }

    .action-button {
      width: 100%;
    }
  }
</style>
