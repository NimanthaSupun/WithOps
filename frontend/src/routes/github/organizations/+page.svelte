<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { githubClient } from '$lib/github.js';
    import { isDarkMode } from '$lib/stores.js';
    
    let loading = true;
    let error = null;
    let message = 'Discovering your GitHub organizations...';
    let organizations = [];
    let selectedOrg = null;
    let installingApp = false;
    
    // Theme reactivity
    $: darkMode = $isDarkMode;

    onMount(async () => {
        await handleOrganizationDiscovery();
    });

    async function handleOrganizationDiscovery() {
        try {
            loading = true;
            error = null;
            
            // Get URL parameters from GitHub OAuth redirect
            const params = $page.url.searchParams;
            const code = params.get('code');
            const state = params.get('state');
            
            console.log('Organization discovery callback params:', { 
                code: code ? 'present' : 'missing',
                state: state
            });

            if (code && state) {
                // Process OAuth callback to get user's organizations
                message = 'Discovering organizations where you can install the GitHub App...';
                
                const result = await githubClient.processOrganizationCallback(code, state);
                
                if (result.success) {
                    organizations = result.organizations;
                    message = `Found ${result.total_count} organizations where you can install the GitHub App`;
                    loading = false;
                    
                    // Aggressive prefetching for instant navigation
                    console.log('🚀 Starting ultra-aggressive organization workspace prefetching');
                    
                    // Prefetch workspace data for all installed organizations in background
                    const installedOrgs = organizations.filter(org => org.app_installed);
                    const uninstalledOrgs = organizations.filter(org => !org.app_installed);
                    
                    // Immediate prefetch for first 2 installed orgs
                    installedOrgs.slice(0, 2).forEach(org => {
                        githubClient.preloadOrganizationWorkspace(org.login);
                    });
                    
                    // Background prefetch for remaining installed orgs (with delay to avoid API rate limits)
                    installedOrgs.slice(2).forEach((org, index) => {
                        setTimeout(() => {
                            githubClient.preloadOrganizationWorkspace(org.login);
                        }, (index + 1) * 500); // Stagger requests
                    });
                    
                    // Pre-generate installation URLs for uninstalled orgs for faster clicks
                    console.log('🚀 Pre-generating installation URLs for faster app installation');
                    uninstalledOrgs.slice(0, 3).forEach(org => {
                        githubClient.generateInstallationUrl(org.login).then(result => {
                            if (result.success) {
                                org.cached_installation_url = result.installation_url;
                            }
                        });
                    });
                } else {
                    throw new Error(result.error);
                }
            } else {
                throw new Error('Missing required parameters from GitHub OAuth');
            }
            
        } catch (err) {
            console.error('Organization discovery error:', err);
            error = err.message || 'Failed to discover organizations';
            message = 'Error occurred during organization discovery';
            loading = false;
        }
    }

    async function installAppInOrganization(org) {
        try {
            installingApp = true;
            selectedOrg = org;
            
            // Use cached installation URL if available for instant redirect
            if (org.cached_installation_url) {
                console.log('🚀 Using cached installation URL for instant redirect');
                window.location.href = org.cached_installation_url;
                return;
            }
            
            const result = await githubClient.generateInstallationUrl(org.login);
            
            if (result.success) {
                console.log('Redirecting to GitHub App installation:', result.installation_url);
                // Redirect to GitHub App installation page (not OAuth)
                window.location.href = result.installation_url;
            } else {
                throw new Error(result.error);
            }
        } catch (err) {
            console.error('App installation error:', err);
            error = err.message || 'Failed to start app installation';
            installingApp = false;
        }
    }

    async function verifyAndViewWorkspace(org) {
        try {
            // Show loading state
            org.verifying = true;
            organizations = [...organizations]; // Trigger reactivity
            
            // Verify installation is still active
            console.log(`🔍 Verifying installation for ${org.login}...`);
            const verification = await githubClient.verifyInstallation(org.login);
            
            console.log(`🔍 Verification result for ${org.login}:`, verification);
            console.log(`🔍 Verification check - success: ${verification.success}, installed: ${verification.installed}`);
            
            if (verification.success && verification.installed) {
                // Installation verified, proceed to workspace
                console.log(`✅ Verification passed for ${org.login}, navigating to workspace`);
                goto(`/github/workspace/${org.login}`);
            } else {
                // Installation no longer exists
                console.warn(`⚠️ App no longer installed in ${org.login}`);
                console.log(`❌ Verification failed for ${org.login} - success: ${verification.success}, installed: ${verification.installed}`);
                
                // Update organization status
                org.app_installed = false;
                org.installation_id = null;
                organizations = [...organizations]; // Trigger reactivity
                
                // Clear cache
                githubClient.clearOrganizationCache(org.login);
                
                // Show helpful message
                error = `GitHub App is no longer installed in ${org.login}. Please reinstall the app to access the workspace.`;
                
                // Auto-clear error after 5 seconds
                setTimeout(() => {
                    error = null;
                }, 5000);
            }
        } catch (err) {
            console.error(`Verification error for ${org.login}:`, err);
            error = `Failed to verify installation for ${org.login}. Please try again.`;
        } finally {
            org.verifying = false;
            organizations = [...organizations]; // Trigger reactivity
        }
    }

    function goToDashboard() {
        goto('/dashboard');
    }

    function viewWorkspace(org) {
        // Use verification instead of direct navigation
        verifyAndViewWorkspace(org);
    }
</script>

<svelte:head>
    <title>GitHub Organizations - WithOps DevSecOps Platform</title>
</svelte:head>

<div class="organizations-container {darkMode ? 'dark' : 'light'}">
  <!-- Background Effects -->
  <div class="orgs-background">
    <div class="orgs-glow-1"></div>
    <div class="orgs-glow-2"></div>
    <div class="github-pattern"></div>
  </div>

  <div class="orgs-content">
    {#if loading}
      <!-- Loading State -->
      <div class="orgs-card loading-card">
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
            <h2 class="loading-title">Discovering Organizations</h2>
            <p class="loading-message">{message}</p>
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
      <div class="orgs-card error-card">
        <div class="error-section">
          <div class="error-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.958-.833-2.728 0L4.186 14.5c-.77.833.192 2.5 1.732 2.5z"/>
            </svg>
          </div>
          <div class="error-content">
            <h2 class="error-title">Discovery Error</h2>
            <p class="error-message">{error}</p>
            <div class="error-actions">
              <button 
                on:click={handleOrganizationDiscovery}
                class="retry-button"
              >
                <svg class="retry-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                Try Again
              </button>
              <button 
                on:click={goToDashboard}
                class="dashboard-button"
              >
                <svg class="dashboard-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
                </svg>
                Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    {:else if organizations.length > 0}
      <!-- Organizations List -->
      <div class="orgs-card main-card">
        <!-- Header -->
        <div class="orgs-header">
          <div class="header-content">
            <div class="header-icon">
              <svg fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
              </svg>
            </div>
            <div class="header-text">
              <h1 class="header-title">Select Organization</h1>
              <p class="header-description">{message}</p>
              <div class="github-app-notice">
                <div class="notice-icon">ℹ️</div>
                <span>You will install the <strong>WithOps GitHub App</strong> into the selected organization</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Organizations Grid -->
        <div class="organizations-grid">
          {#each organizations as org}
            <div class="org-card {org.app_installed ? 'installed' : 'not-installed'}">
              <!-- Organization Info -->
              <div class="org-header">
                <div class="org-avatar">
                  <img src={org.avatar_url} alt="{org.login} avatar" />
                  <div class="avatar-glow"></div>
                </div>
                <div class="org-info">
                  <h3 class="org-name">{org.login}</h3>
                  <div class="org-status">
                    {#if org.app_installed}
                      <div class="status-badge installed-badge">
                        <div class="badge-icon">✅</div>
                        <span>GitHub App installed</span>
                      </div>
                    {:else}
                      <div class="status-badge not-installed-badge">
                        <div class="badge-icon">📦</div>
                        <span>GitHub App not installed</span>
                      </div>
                    {/if}
                  </div>
                  {#if org.description}
                    <p class="org-description">{org.description}</p>
                  {/if}
                </div>
              </div>

              <!-- Action Button -->
              <div class="org-actions">
                {#if org.app_installed}
                  <button 
                    on:click={() => viewWorkspace(org)}
                    on:mouseenter={() => githubClient.preloadOrganizationWorkspace(org.login)}
                    disabled={org.verifying}
                    class="action-button workspace-button"
                  >
                    {#if org.verifying}
                      <div class="button-spinner">
                        <div class="spinner-ring"></div>
                      </div>
                      <span>Verifying...</span>
                    {:else}
                      <div class="button-icon">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                      </div>
                      <span>View Workspace</span>
                      <div class="button-arrow">→</div>
                    {/if}
                  </button>
                {:else}
                  <button 
                    on:click={() => installAppInOrganization(org)}
                    disabled={installingApp && selectedOrg?.login === org.login}
                    class="action-button install-button"
                  >
                    {#if installingApp && selectedOrg?.login === org.login}
                      <div class="button-spinner">
                        <div class="spinner-ring"></div>
                      </div>
                      <span>Installing...</span>
                    {:else}
                      <div class="button-icon">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                        </svg>
                      </div>
                      <span>Install GitHub App</span>
                      <div class="button-arrow">→</div>
                    {/if}
                  </button>
                {/if}
              </div>

              <!-- Installation Info -->
              {#if !org.app_installed}
                <div class="installation-info">
                  <div class="info-header">
                    <div class="info-icon">📋</div>
                    <span>What happens next:</span>
                  </div>
                  <ul class="info-steps">
                    <li>• You'll be redirected to GitHub</li>
                    <li>• Install the WithOps GitHub App in {org.login}</li>
                    <li>• App will have access only to this organization</li>
                    <li>• Return here to access your workspace</li>
                  </ul>
                </div>
              {/if}
            </div>
          {/each}
        </div>

        <!-- Footer -->
        <div class="orgs-footer">
          <button 
            on:click={goToDashboard}
            class="back-button"
          >
            <svg class="back-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
            Back to Dashboard
          </button>
        </div>
      </div>
    {:else}
      <!-- No Organizations Found -->
      <div class="orgs-card empty-card">
        <div class="empty-section">
          <div class="empty-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
          </div>
          <div class="empty-content">
            <h3 class="empty-title">No Organizations Found</h3>
            <p class="empty-description">
              We couldn't find any GitHub organizations where you have permission to install apps.
              Make sure you have admin/owner access to at least one organization.
            </p>
            <button 
              on:click={goToDashboard}
              class="dashboard-button"
            >
              <svg class="dashboard-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
              </svg>
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  /* Global Variables */
  .organizations-container {
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
    --installed-color: #16a34a;
  }

  .organizations-container.light {
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
    --installed-color: #16a34a;
  }

  /* Main Container */
  .organizations-container {
    position: relative;
    min-height: 100vh;
    background: var(--bg-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    overflow: hidden;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  /* Background Effects */
  .orgs-background {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
  }

  .orgs-glow-1 {
    position: absolute;
    top: 10%;
    left: 10%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(74, 158, 255, 0.15) 0%, transparent 70%);
    border-radius: 50%;
    animation: float-slow 12s ease-in-out infinite;
  }

  .orgs-glow-2 {
    position: absolute;
    bottom: 10%;
    right: 10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(255, 139, 74, 0.1) 0%, transparent 70%);
    border-radius: 50%;
    animation: float-slow 15s ease-in-out infinite reverse;
  }

  .github-pattern {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: 
      radial-gradient(circle at 25% 25%, rgba(74, 158, 255, 0.08) 2px, transparent 2px),
      radial-gradient(circle at 75% 75%, rgba(255, 139, 74, 0.08) 2px, transparent 2px);
    background-size: 120px 120px;
    animation: pattern-drift 25s linear infinite;
  }

  @keyframes float-slow {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-40px) rotate(3deg); }
  }

  @keyframes pattern-drift {
    0% { transform: translateX(0) translateY(0); }
    100% { transform: translateX(-120px) translateY(-120px); }
  }

  /* Content Container */
  .orgs-content {
    position: relative;
    z-index: 2;
    width: 100%;
    max-width: 1200px;
  }

  /* Card Base */
  .orgs-card {
    background: linear-gradient(145deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-color);
    border-radius: 24px;
    box-shadow: 
      0 20px 40px rgba(0, 0, 0, 0.1),
      0 8px 16px rgba(74, 158, 255, 0.05),
      inset 0 1px 0 rgba(255, 255, 255, 0.1);
  }

  .organizations-container.light .orgs-card {
    box-shadow: 
      0 20px 40px rgba(0, 0, 0, 0.08),
      0 8px 16px rgba(9, 105, 218, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
  }

  /* Loading Card */
  .loading-card {
    padding: 3rem;
    text-align: center;
  }

  .loading-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
  }

  .loading-icon {
    position: relative;
    width: 100px;
    height: 100px;
  }

  .github-logo {
    width: 80px;
    height: 80px;
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
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }

  .loading-message {
    font-size: 1.1rem;
    color: var(--text-secondary);
    margin: 0;
  }

  .progress-dots {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
  }

  .dot {
    width: 8px;
    height: 8px;
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

  /* Error Card */
  .error-card {
    padding: 3rem;
    text-align: center;
  }

  .error-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
  }

  .error-icon {
    width: 80px;
    height: 80px;
    color: var(--error-color);
    background: rgba(255, 71, 87, 0.1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .error-icon svg {
    width: 40px;
    height: 40px;
  }

  .error-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
  }

  .error-title {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }

  .error-message {
    font-size: 1.1rem;
    color: var(--error-color);
    margin: 0;
    max-width: 500px;
  }

  .error-actions {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  .retry-button, .dashboard-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem 1.5rem;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .retry-button {
    background: var(--error-color);
    color: white;
  }

  .retry-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(255, 71, 87, 0.3);
  }

  .dashboard-button {
    background: rgba(136, 136, 136, 0.2);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
  }

  .dashboard-button:hover {
    background: var(--primary-color);
    color: white;
    transform: translateY(-2px);
  }

  .retry-icon, .dashboard-icon {
    width: 18px;
    height: 18px;
  }

  /* Main Card */
  .main-card {
    padding: 0;
    overflow: hidden;
  }

  /* Header */
  .orgs-header {
    padding: 2.5rem 2.5rem 2rem;
    border-bottom: 1px solid var(--border-color);
    background: linear-gradient(135deg, rgba(74, 158, 255, 0.05) 0%, transparent 100%);
  }

  .header-content {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }

  .header-icon {
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3);
  }

  .header-icon svg {
    width: 30px;
    height: 30px;
  }

  .header-text {
    flex: 1;
  }

  .header-title {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.5rem 0;
    line-height: 1.2;
  }

  .header-description {
    font-size: 1.1rem;
    color: var(--text-secondary);
    margin: 0 0 1rem 0;
  }

  .github-app-notice {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: rgba(74, 158, 255, 0.1);
    border: 1px solid rgba(74, 158, 255, 0.2);
    border-radius: 10px;
    font-size: 0.9rem;
    color: var(--text-secondary);
  }

  .notice-icon {
    font-size: 1.1rem;
  }

  /* Organizations Grid */
  .organizations-grid {
    padding: 2rem 2.5rem;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 1.5rem;
  }

  /* Organization Card */
  .org-card {
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 1.5rem;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
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
    transform: translateY(-4px);
    border-color: var(--primary-color);
    box-shadow: 0 12px 35px rgba(74, 158, 255, 0.15);
  }

  .org-card.installed {
    border-color: var(--installed-color);
  }

  .org-card.installed::before {
    background: var(--installed-color);
  }

  .org-card.installed:hover {
    border-color: var(--installed-color);
    box-shadow: 0 12px 35px rgba(22, 163, 74, 0.15);
  }

  /* Organization Header */
  .org-header {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .org-avatar {
    position: relative;
    width: 60px;
    height: 60px;
  }

  .org-avatar img {
    width: 100%;
    height: 100%;
    border-radius: 12px;
    border: 2px solid var(--border-color);
  }

  .avatar-glow {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 80px;
    height: 80px;
    background: radial-gradient(circle, rgba(74, 158, 255, 0.2) 0%, transparent 70%);
    border-radius: 50%;
    animation: avatar-pulse 3s ease-in-out infinite;
  }

  @keyframes avatar-pulse {
    0%, 100% { opacity: 0.3; transform: translate(-50%, -50%) scale(1); }
    50% { opacity: 0.6; transform: translate(-50%, -50%) scale(1.2); }
  }

  .org-info {
    flex: 1;
  }

  .org-name {
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 0.5rem 0;
  }

  .org-status {
    margin-bottom: 0.75rem;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.8rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 500;
  }

  .installed-badge {
    background: rgba(22, 163, 74, 0.1);
    color: var(--installed-color);
    border: 1px solid rgba(22, 163, 74, 0.2);
  }

  .not-installed-badge {
    background: rgba(255, 139, 74, 0.1);
    color: var(--accent-color);
    border: 1px solid rgba(255, 139, 74, 0.2);
  }

  .badge-icon {
    font-size: 1rem;
  }

  .org-description {
    font-size: 0.9rem;
    color: var(--text-muted);
    margin: 0;
    line-height: 1.4;
  }

  /* Action Buttons */
  .org-actions {
    margin-bottom: 1rem;
  }

  .action-button {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 1rem 1.5rem;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
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

  .workspace-button {
    background: linear-gradient(135deg, var(--installed-color) 0%, #22c55e 100%);
    color: white;
    box-shadow: 0 6px 20px rgba(22, 163, 74, 0.3);
  }

  .workspace-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(22, 163, 74, 0.4);
  }

  .install-button {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
    color: white;
    box-shadow: 0 6px 20px rgba(74, 158, 255, 0.3);
  }

  .install-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(74, 158, 255, 0.4);
  }

  .action-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
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

  /* Button Spinner */
  .button-spinner {
    width: 20px;
    height: 20px;
    position: relative;
  }

  .spinner-ring {
    position: absolute;
    width: 100%;
    height: 100%;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  /* Installation Info */
  .installation-info {
    background: rgba(74, 158, 255, 0.05);
    border: 1px solid rgba(74, 158, 255, 0.1);
    border-radius: 10px;
    padding: 1rem;
  }

  .info-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  .info-icon {
    font-size: 1rem;
  }

  .info-steps {
    margin: 0;
    padding: 0;
    list-style: none;
    color: var(--text-muted);
    font-size: 0.85rem;
    line-height: 1.5;
  }

  .info-steps li {
    margin-bottom: 0.25rem;
  }

  /* Footer */
  .orgs-footer {
    padding: 2rem 2.5rem;
    border-top: 1px solid var(--border-color);
    text-align: center;
  }

  .back-button {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 10px;
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

  /* Empty Card */
  .empty-card {
    padding: 3rem;
    text-align: center;
  }

  .empty-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
  }

  .empty-icon {
    width: 100px;
    height: 100px;
    background: rgba(136, 136, 136, 0.1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
  }

  .empty-icon svg {
    width: 50px;
    height: 50px;
  }

  .empty-content {
    max-width: 500px;
  }

  .empty-title {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 1rem 0;
  }

  .empty-description {
    font-size: 1.1rem;
    color: var(--text-secondary);
    line-height: 1.6;
    margin: 0 0 2rem 0;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .organizations-container {
      padding: 1rem;
    }

    .orgs-header {
      padding: 2rem 1.5rem 1.5rem;
    }

    .header-content {
      flex-direction: column;
      text-align: center;
      gap: 1rem;
    }

    .header-title {
      font-size: 2rem;
    }

    .organizations-grid {
      padding: 1.5rem;
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .org-header {
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .orgs-footer {
      padding: 1.5rem;
    }
  }

  @media (max-width: 480px) {
    .organizations-grid {
      padding: 1rem;
    }

    .org-card {
      padding: 1rem;
    }

    .error-actions {
      flex-direction: column;
      width: 100%;
    }

    .retry-button, .dashboard-button {
      width: 100%;
      justify-content: center;
    }
  }
</style>
