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

	// GitHub connection state for users who logged in with non-GitHub methods
	let needsGitHubConnection = $state(false);
	let isConnectingGitHub = $state(false);
	let githubConnectionMessage = $state(null);

	// Pending invitations state
	let pendingInvitations = $state([]);
	let isAcceptingInvitation = $state(null); // Track which invitation is being accepted
	let isDecliningInvitation = $state(null); // Track which invitation is being declined

	// Subscribe to dark mode using Svelte 5 runes
	let darkMode = $state(false);

	$effect(() => {
		const unsubscribe = isDarkMode.subscribe((value) => {
			darkMode = value;
		});
		return unsubscribe;
	});

	// Theme toggle function
	function toggleTheme() {
		darkMode = !darkMode;
		isDarkMode.set(darkMode);
	}

	onMount(async () => {
		// Add a small delay to allow Auth0 to fully initialize after redirect
		await new Promise((resolve) => setTimeout(resolve, 200));

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
		githubClient.startOrganizationDiscovery().catch((error) => {
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

				// Check if user needs to connect GitHub account
				// This is for users who logged in with Google/Email but haven't connected GitHub
				if (result.needs_github_connection) {
					needsGitHubConnection = true;
					githubConnectionMessage =
						result.message || "Connect your GitHub account to access your team's organizations";
					console.log('⚠️ User needs to connect GitHub account:', githubConnectionMessage);
				} else {
					needsGitHubConnection = false;
					githubConnectionMessage = null;
				}

				// Show all organizations that the user has interacted with, but mark status correctly
				connectedOrganizations = result.organizations.map((org) => {
					console.log(
						`📋 Processing organization: ${org.login || org.name}, app_installed: ${org.app_installed}, can_access: ${org.can_access}`
					);
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

				// Load pending invitations in background
				loadPendingInvitations();

				// Load stats in background WITHOUT blocking UI
				setTimeout(() => loadOrganizationStats(), 100);
			} else {
				throw new Error(result.error || 'Failed to load organizations');
			}
		} catch (err) {
			console.error('❌ Error loading organizations:', err);

			// Handle authentication errors specifically
			const errorMessage = err.message || err.toString();
			if (
				errorMessage.includes('Authentication required') ||
				errorMessage.includes('Authentication expired') ||
				errorMessage.includes('Missing Refresh Token') ||
				errorMessage.includes('authentication failed')
			) {
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
			const installedOrgMap = new Map(installedOrgs.map((org) => [org.login || org.name, org]));

			// Merge discovered organizations with installation status
			discoveredOrganizations = callbackResult.organizations.map((org) => {
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
			connectedOrganizations = installedOrgs.map((org) => ({
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
		const connectedOrgs = connectedOrganizations.filter(
			(org) => org.can_access && org.app_installed && org.status === 'connected'
		);
		console.log(
			`📊 Loading stats for ${connectedOrgs.length} organizations:`,
			connectedOrgs.map((org) => org.login)
		);

		if (connectedOrgs.length === 0) {
			console.log('📊 No connected organizations found to load stats for');
			return;
		}

		const statsPromises = connectedOrgs.map(async (org) => {
			try {
				// Mark as loading IMMEDIATELY
				const orgIndex = connectedOrganizations.findIndex((o) => o.login === org.login);
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
					const currentOrgIndex = connectedOrganizations.findIndex((o) => o.login === org.login);
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
					const currentOrgIndex = connectedOrganizations.findIndex((o) => o.login === org.login);
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
				const currentOrgIndex = connectedOrganizations.findIndex((o) => o.login === org.login);
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

	/**
	 * Connect GitHub account for users who logged in with non-GitHub methods (Google, Email, etc.)
	 * This allows them to access organizations where another team member installed the GitHub App
	 */
	async function connectGitHubAccount() {
		try {
			isConnectingGitHub = true;
			console.log('🔗 Starting GitHub account connection...');

			const result = await githubClient.startGitHubConnection();

			if (result.success) {
				// Redirect to GitHub OAuth to connect their GitHub account
				window.location.href = result.oauth_url;
			} else {
				console.error('Failed to start GitHub connection:', result.error);
				alert('Failed to start GitHub connection. Please try again.');
				isConnectingGitHub = false;
			}
		} catch (error) {
			console.error('GitHub connection error:', error);
			alert('Failed to connect to GitHub. Please try again.');
			isConnectingGitHub = false;
		}
	}

	// ============================================================================
	// PENDING INVITATIONS
	// ============================================================================

	async function loadPendingInvitations() {
		try {
			console.log('📨 Loading pending invitations...');
			const result = await githubClient.getMyInvitations();

			if (result.invitations && result.invitations.length > 0) {
				pendingInvitations = result.invitations;
				console.log(`📨 Found ${pendingInvitations.length} pending invitations`);
			} else {
				pendingInvitations = [];
			}
		} catch (error) {
			console.error('Error loading invitations:', error);
			pendingInvitations = [];
		}
	}

	async function acceptInvitation(inviteToken, orgName) {
		try {
			isAcceptingInvitation = inviteToken;
			console.log(`✅ Accepting invitation for ${orgName}...`);

			const result = await githubClient.acceptInvitation(inviteToken);

			if (result.success) {
				console.log(`✅ Successfully joined ${orgName}`);
				// Remove from pending invitations
				pendingInvitations = pendingInvitations.filter((inv) => inv.invite_token !== inviteToken);
				// Reload organizations to show the new one
				await loadConnectedOrganizations();
			} else {
				console.error('Failed to accept invitation:', result.error);
				alert(result.error || 'Failed to accept invitation. Please try again.');
			}
		} catch (error) {
			console.error('Error accepting invitation:', error);
			alert('Failed to accept invitation. Please try again.');
		} finally {
			isAcceptingInvitation = null;
		}
	}

	async function declineInvitation(inviteToken) {
		try {
			isDecliningInvitation = inviteToken;

			const result = await githubClient.declineInvitation(inviteToken);

			if (result.success) {
				console.log('❌ Invitation declined');
				// Remove from pending invitations
				pendingInvitations = pendingInvitations.filter((inv) => inv.invite_token !== inviteToken);
			} else {
				console.error('Failed to decline invitation:', result.error);
				alert(result.error || 'Failed to decline invitation. Please try again.');
			}
		} catch (error) {
			console.error('Error declining invitation:', error);
			alert('Failed to decline invitation. Please try again.');
		} finally {
			isDecliningInvitation = null;
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
			const org = connectedOrganizations.find((o) => o.login === orgName);
			if (org && org.app_installed === false) {
				alert(
					`GitHub App is not installed in ${orgName}. Please install the app to access the workspace.`
				);
				return;
			}

			console.log(`✅ Navigating to workspace for ${orgName}`);

			// Optimistic navigation - go to workspace immediately
			goto(`/github/workspace/${orgName}`);

			// Preload data if not cached to ensure it's ready
			const cached = githubClient.getCachedData(`workspace_${orgName}`);
			if (!cached) {
				// Start loading in background while user sees the UI
				githubClient
					.getOrganizationWorkspace(orgName)
					.then((result) => {
						if (result.success) {
							// If workspace loads successfully, restore org status in case cache was wrong
							githubClient.restoreOrganizationStatus(orgName);
						}
					})
					.catch((error) => {
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
			connectedOrganizations.forEach((org) => {
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
			const orgIndex = connectedOrganizations.findIndex((o) => o.login === orgName);
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
			const orgIndex = connectedOrganizations.findIndex((o) => o.login === orgName);
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
			connectedOrganizations.forEach((org) => {
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
		<!-- Professional Header Section -->
		<div class="page-header">
			<!-- Top Navigation Bar -->
			<div class="header-top-bar">
				<button onclick={() => goto('/dashboard')} class="back-nav-button">
					<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M10 19l-7-7m0 0l7-7m-7 7h18"
						/>
					</svg>
					<span>Back to Dashboard</span>
				</button>

				<button onclick={toggleTheme} class="theme-toggle-button">
					{#if darkMode}
						☀️
					{:else}
						🌙
					{/if}
				</button>
			</div>

			<!-- Main Header Content - Left: Title, Right: Actions -->
			<div class="header-main">
				<div class="header-left">
					<div class="header-icon">
						<svg fill="currentColor" viewBox="0 0 24 24">
							<path
								d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
							/>
						</svg>
					</div>
					<div class="header-text">
						<h1 class="header-title">GitHub Organizations</h1>
						<p class="header-subtitle">Manage your connected workspaces and repositories</p>
					</div>
				</div>

				<div class="header-actions">
					<button onclick={connectNewOrganization} class="action-button primary-action">
						<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6v6m0 0v6m0-6h6m-6 0H6"
							/>
						</svg>
						<span>Connect Organization</span>
					</button>
					<button onclick={refreshOrganizations} class="action-button secondary-action">
						<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
							/>
						</svg>
						<span>Refresh</span>
					</button>
				</div>
			</div>

			<!-- Filter Bar - Full Width Below Header -->
			{#if !loading && !error && connectedOrganizations.length > 0}
				<div class="filter-bar">
					<button
						class="filter-button {filterType === 'all' ? 'active' : ''}"
						onclick={() => (filterType = 'all')}
					>
						<span class="filter-icon">📊</span>
						<span>All Organizations</span>
						<span class="filter-count">{connectedOrganizations.length}</span>
					</button>

					<button
						class="filter-button {filterType === 'owned' ? 'active' : ''}"
						onclick={() => (filterType = 'owned')}
					>
						<span class="filter-icon">🏆</span>
						<span>My Installations</span>
						<span class="filter-count"
							>{connectedOrganizations.filter((o) => o.installed_by_you).length}</span
						>
					</button>

					<button
						class="filter-button {filterType === 'shared' ? 'active' : ''}"
						onclick={() => (filterType = 'shared')}
					>
						<span class="filter-icon">👥</span>
						<span>Shared with Me</span>
						<span class="filter-count"
							>{connectedOrganizations.filter((o) => o.auto_linked).length}</span
						>
					</button>
				</div>
			{/if}
		</div>

		<!-- Main Content -->
		<main class="page-main">
			<!-- Pending Invitations Banner -->
			{#if pendingInvitations.length > 0}
				<div class="invitations-banner">
					<div class="invitations-header">
						<div class="invitations-icon">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
								/>
							</svg>
						</div>
						<div class="invitations-title-section">
							<h3>
								You have {pendingInvitations.length} pending invitation{pendingInvitations.length >
								1
									? 's'
									: ''}
							</h3>
							<p>
								You've been invited to join the following organization{pendingInvitations.length > 1
									? 's'
									: ''}
							</p>
						</div>
					</div>
					<div class="invitations-list">
						{#each pendingInvitations as invitation}
							<div class="invitation-card">
								<div class="invitation-org">
									<img
										src={invitation.organization.avatar_url || '/default-org.png'}
										alt={invitation.organization.name}
										class="invitation-org-avatar"
									/>
									<div class="invitation-org-info">
										<span class="invitation-org-name"
											>{invitation.organization.name || invitation.organization.login}</span
										>
										<span class="invitation-meta">
											Invited by {invitation.invited_by.name || invitation.invited_by.email} as
											<strong>{invitation.role}</strong>
										</span>
									</div>
								</div>
								<div class="invitation-actions">
									<button
										class="btn-accept"
										onclick={() =>
											acceptInvitation(
												invitation.invite_token,
												invitation.organization.name || invitation.organization.login
											)}
										disabled={isAcceptingInvitation === invitation.invite_token ||
											isDecliningInvitation === invitation.invite_token}
									>
										{#if isAcceptingInvitation === invitation.invite_token}
											<div class="btn-spinner-small"></div>
											Joining...
										{:else}
											<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 13l4 4L19 7"
												/>
											</svg>
											Accept
										{/if}
									</button>
									<button
										class="btn-decline"
										onclick={() => declineInvitation(invitation.invite_token)}
										disabled={isAcceptingInvitation === invitation.invite_token ||
											isDecliningInvitation === invitation.invite_token}
									>
										{#if isDecliningInvitation === invitation.invite_token}
											<div class="btn-spinner-small"></div>
										{:else}
											<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M6 18L18 6M6 6l12 12"
												/>
											</svg>
											Decline
										{/if}
									</button>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if loading}
				<!-- Loading State -->
				<div class="state-card loading-state">
					<div class="loading-section">
						<div class="loading-icon">
							<div class="github-logo">
								<svg fill="currentColor" viewBox="0 0 24 24">
									<path
										d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
									/>
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
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.958-.833-2.728 0L4.186 14.5c-.77.833.192 2.5 1.732 2.5z"
								/>
							</svg>
						</div>
						<div class="error-content">
							<h2 class="error-title">Error Loading Organizations</h2>
							<p class="error-message">{error}</p>
							<button onclick={loadConnectedOrganizations} class="retry-button">
								<svg class="retry-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
									/>
								</svg>
								Try Again
							</button>
						</div>
					</div>
				</div>
			{:else if connectedOrganizations.length === 0}
				<!-- Empty State - Check if GitHub connection is needed first -->
				{#if needsGitHubConnection}
					<!-- GitHub Connection Required Prompt -->
					<div class="state-card github-connection-state">
						<div class="github-connect-section">
							<div class="github-connect-icon">
								<svg fill="currentColor" viewBox="0 0 24 24">
									<path
										d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
									/>
								</svg>
								<div class="link-badge">
									<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
										/>
									</svg>
								</div>
							</div>
							<div class="github-connect-content">
								<h3 class="github-connect-title">Connect Your GitHub Account</h3>
								<p class="github-connect-description">
									{githubConnectionMessage ||
										'You logged in without GitHub. Connect your GitHub account to access organizations where your team has already installed the WithOps App.'}
								</p>
								<div class="github-connect-info">
									<div class="info-item">
										<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
											/>
										</svg>
										<span>Auto-link to existing team installations</span>
									</div>
									<div class="info-item">
										<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
											/>
										</svg>
										<span>Access your organization's repositories</span>
									</div>
									<div class="info-item">
										<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
											/>
										</svg>
										<span>No need to reinstall the GitHub App</span>
									</div>
								</div>
								<button
									onclick={connectGitHubAccount}
									class="github-connect-button"
									disabled={isConnectingGitHub}
								>
									{#if isConnectingGitHub}
										<div class="button-spinner"></div>
										<span>Connecting...</span>
									{:else}
										<svg fill="currentColor" viewBox="0 0 24 24" class="button-icon">
											<path
												d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
											/>
										</svg>
										<span>Connect GitHub Account</span>
										<div class="button-arrow">→</div>
									{/if}
								</button>
							</div>
						</div>
					</div>
				{:else}
					<!-- Regular Empty State -->
					<div class="state-card empty-state">
						<div class="empty-section">
							<div class="empty-icon">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
									/>
								</svg>
							</div>
							<div class="empty-content">
								<h3 class="empty-title">No Organizations Connected</h3>
								<p class="empty-description">
									Connect your first GitHub organization to get started with DevSecOps workflows and
									security scanning.
								</p>
								<button onclick={connectNewOrganization} class="connect-button">
									<div class="button-icon">
										<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M13 10V3L4 14h7v7l9-11h-7z"
											/>
										</svg>
									</div>
									<span>Connect to GitHub</span>
									<div class="button-arrow">→</div>
								</button>
							</div>
						</div>
					</div>
				{/if}
			{:else}
				<!-- Organizations Grid -->
				<div class="organizations-grid">
					{#each connectedOrganizations.filter((org) => {
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
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M13 10V3L4 14h7v7l9-11h-7z"
												/>
											</svg>
										</div>
										<span>View Workspace</span>
										<div class="button-arrow">→</div>
									</button>

									{#if org.installed_by_you}
										<button
											onclick={() => goto(`/organizations/${org.login}/team`)}
											class="org-button team-button"
											title="Manage team members and invitations"
										>
											<div class="button-icon">
												<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
													/>
												</svg>
											</div>
											<span>Manage Team</span>
										</button>
									{/if}
								{:else}
									<button
										onclick={() => generateInstallationUrl(org.login, org.id)}
										class="org-button install-button"
									>
										<div class="button-icon">
											<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 6v6m0 0v6m0-6h6m-6 0H6"
												/>
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
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
												/>
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
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M13 10V3L4 14h7v7l9-11h-7z"
													/>
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
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M12 6v6m0 0v6m0-6h6m-6 0H6"
													/>
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
	</div>
</div>

<style>
	/* ============================================
	   PROFESSIONAL UI/UX DESIGN SYSTEM
	   ============================================ */

	/* ============================================
	   PROFESSIONAL DESIGN SYSTEM - MATCHING DASHBOARD
	   ============================================ */
	.organizations-page {
		/* Core Background Colors */
		--bg-primary: #000000;
		--bg-secondary: #0a0a0a;
		--bg-card: rgba(255, 255, 255, 0.05);
		--bg-card-hover: rgba(255, 255, 255, 0.08);

		/* Text Colors */
		--text-primary: #ffffff;
		--text-secondary: #b8b8b8;
		--text-muted: #888888;

		/* Brand Accent Colors - Matching Design Pattern */
		--primary-color: #00d9ff;
		--accent-color: #00d9ff;
		--cyan-primary: #00d9ff;
		--cyan-secondary: #00b8d4;
		--cyan-light: #33e3ff;
		--purple-primary: #8b5cf6;
		--pink-primary: #ec4899;
		--green-success: #10b981;
		--orange-warning: #f59e0b;
		--red-error: #ef4444;

		/* Border Colors */
		--border-color: rgba(0, 217, 255, 0.3);
		--border-subtle: rgba(0, 217, 255, 0.15);
		--border-medium: rgba(0, 217, 255, 0.3);
		--border-strong: rgba(0, 217, 255, 0.5);

		/* Glass Morphism Effects */
		--glass-bg: rgba(0, 0, 0, 0.4);
		--glass-border: rgba(0, 217, 255, 0.2);

		/* Professional Shadows - Matching Design */
		--shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
		--shadow-md: 0 10px 30px rgba(0, 0, 0, 0.5), 0 5px 15px rgba(0, 0, 0, 0.3);
		--shadow-lg: 0 15px 35px rgba(0, 217, 255, 0.4), 0 8px 20px rgba(0, 0, 0, 0.6);
		--shadow-glow: 0 0 20px rgba(0, 217, 255, 0.3);
		--shadow-glow-strong: 0 4px 15px rgba(0, 217, 255, 0.3);

		min-height: 100vh;
		background: var(--bg-primary);
		font-family:
			'Inter',
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			Roboto,
			sans-serif;
		position: relative;
		overflow-x: hidden;
	}

	.organizations-page.light {
		/* Light Mode Backgrounds */
		--bg-primary: #ffffff;
		--bg-secondary: #f8fafc;
		--bg-card: rgba(0, 217, 255, 0.05);
		--bg-card-hover: rgba(0, 217, 255, 0.1);

		/* Light Mode Text */
		--text-primary: #1a1a1a;
		--text-secondary: #666666;
		--text-muted: #999999;

		/* Light Mode Borders */
		--border-color: rgba(0, 217, 255, 0.4);
		--border-subtle: rgba(0, 217, 255, 0.2);
		--border-medium: rgba(0, 217, 255, 0.35);
		--border-strong: rgba(0, 217, 255, 0.6);

		/* Light Mode Glass */
		--glass-bg: rgba(255, 255, 255, 0.95);
		--glass-border: rgba(0, 217, 255, 0.15);

		/* Light Mode Shadows */
		--shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
		--shadow-md: 0 8px 25px rgba(0, 217, 255, 0.3), 0 4px 12px rgba(0, 217, 255, 0.15);
		--shadow-lg: 0 12px 32px rgba(0, 217, 255, 0.4), 0 6px 16px rgba(0, 217, 255, 0.25);
		--shadow-glow: 0 0 20px rgba(0, 217, 255, 0.2);
		--shadow-glow-strong: 0 4px 15px rgba(0, 217, 255, 0.25);
	}

	/* ============================================
	   BACKGROUND EFFECTS
	   ============================================ */
	.page-background {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
		z-index: 0;
		overflow: hidden;
	}

	.page-glow-1 {
		position: absolute;
		top: -10%;
		left: -5%;
		width: 800px;
		height: 800px;
		background: radial-gradient(circle, rgba(0, 217, 255, 0.12) 0%, transparent 70%);
		border-radius: 50%;
		animation: float-glow 20s ease-in-out infinite;
	}

	.page-glow-2 {
		position: absolute;
		bottom: -10%;
		right: -5%;
		width: 700px;
		height: 700px;
		background: radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, transparent 70%);
		border-radius: 50%;
		animation: float-glow 25s ease-in-out infinite reverse;
	}

	.github-pattern {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-image:
			radial-gradient(circle at 20% 30%, rgba(0, 217, 255, 0.03) 1px, transparent 1px),
			radial-gradient(circle at 80% 70%, rgba(139, 92, 246, 0.03) 1px, transparent 1px);
		background-size: 60px 60px;
		animation: pattern-shift 30s linear infinite;
	}

	@keyframes float-glow {
		0%,
		100% {
			transform: translate(0, 0) scale(1);
			opacity: 0.6;
		}
		50% {
			transform: translate(30px, -30px) scale(1.1);
			opacity: 0.8;
		}
	}

	@keyframes pattern-shift {
		0% {
			background-position: 0 0;
		}
		100% {
			background-position: 60px 60px;
		}
	}

	/* ============================================
	   PAGE LAYOUT
	   ============================================ */
	.page-content {
		position: relative;
		z-index: 1;
		width: 100%;
		max-width: 100%;
		margin: 0;
		padding: 2rem 4rem;
		min-height: 100vh;
	}

	/* ============================================
	   PROFESSIONAL HEADER SECTION
	   ============================================ */
	.page-header {
		margin-bottom: 2.5rem;
	}

	/* Top Navigation Bar */
	.header-top-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--border-subtle);
	}

	/* Main Header - Left Right Layout */
	.header-main {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 2rem;
		margin-bottom: 2rem;
		flex-wrap: wrap;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		flex: 1;
		min-width: 0;
	}

	.header-text {
		flex: 1;
		min-width: 0;
	}

	.back-nav-button {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		padding: 0.875rem 1.5rem;
		background: var(--bg-card);
		backdrop-filter: blur(20px);
		border: 1px solid var(--border-subtle);
		border-radius: 8px;
		color: var(--text-secondary);
		font-size: 0.95rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
	}

	.back-nav-button svg {
		width: 18px;
		height: 18px;
		transition: transform 0.3s ease;
	}

	.back-nav-button:hover {
		background: var(--bg-card-hover);
		border-color: var(--primary-color);
		color: var(--primary-color);
		transform: translateY(-1px);
		box-shadow: var(--shadow-glow-strong);
	}

	.back-nav-button:hover svg {
		transform: translateX(-3px);
	}

	.theme-toggle-button {
		width: 48px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 217, 255, 0.1);
		backdrop-filter: blur(20px);
		border: 2px solid rgba(0, 217, 255, 0.3);
		border-radius: 50%;
		font-size: 1.2rem;
		color: var(--primary-color);
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.theme-toggle-button:hover {
		background: rgba(0, 217, 255, 0.2);
		border-color: var(--primary-color);
		transform: translateY(-1px);
		box-shadow: 0 0 15px rgba(0, 217, 255, 0.3);
	}

	/* Header Icon */
	.header-icon {
		width: 64px;
		height: 64px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, var(--cyan-primary) 0%, var(--purple-primary) 100%);
		border-radius: 16px;
		box-shadow:
			var(--shadow-md),
			0 0 20px rgba(0, 217, 255, 0.3);
		flex-shrink: 0;
	}

	.header-icon svg {
		width: 36px;
		height: 36px;
		color: white;
	}

	.header-title {
		font-size: 2.5rem;
		font-weight: 800;
		margin: 0 0 0.5rem 0;
		background: linear-gradient(
			135deg,
			var(--cyan-primary) 0%,
			var(--purple-primary) 50%,
			var(--pink-primary) 100%
		);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		letter-spacing: -0.02em;
		line-height: 1.2;
	}

	.header-subtitle {
		font-size: 1.1rem;
		color: var(--text-secondary);
		margin: 0;
		font-weight: 400;
	}

	/* Action Buttons */
	.header-actions {
		display: flex;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.action-button {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem 2rem;
		border: none;
		border-radius: 14px;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		position: relative;
		overflow: hidden;
	}

	.action-button svg {
		width: 20px;
		height: 20px;
		transition: transform 0.3s ease;
	}

	.action-button::before {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		width: 0;
		height: 0;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.2);
		transform: translate(-50%, -50%);
		transition:
			width 0.6s,
			height 0.6s;
	}

	.action-button:hover::before {
		width: 300px;
		height: 300px;
	}

	.primary-action {
		background: #ffffff;
		color: #000000;
		box-shadow: var(--shadow-md);
		font-weight: 600;
		border-radius: 8px;
	}

	.primary-action:hover {
		background: var(--primary-color);
		color: #000000;
		transform: translateY(-3px);
		box-shadow: var(--shadow-lg);
	}

	.primary-action:hover svg {
		transform: rotate(90deg);
	}

	.secondary-action {
		background: rgba(0, 0, 0, 0.3);
		backdrop-filter: blur(20px);
		color: var(--primary-color);
		border: 2px solid var(--primary-color);
		border-radius: 8px;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.4),
			0 0 20px rgba(0, 217, 255, 0.2);
	}

	.organizations-page.light .secondary-action {
		background: rgba(255, 255, 255, 0.9);
		border-color: var(--primary-color);
	}

	.secondary-action:hover {
		background: var(--primary-color);
		color: #000000;
		font-weight: 600;
		transform: translateY(-3px);
		border-color: var(--primary-color);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.5),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}

	.secondary-action:hover svg {
		transform: rotate(180deg);
	}

	/* ============================================
	   INVITATIONS BANNER
	   ============================================ */
	.invitations-banner {
		background: linear-gradient(135deg, rgba(0, 217, 255, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
		backdrop-filter: blur(20px);
		border: 1px solid var(--border-medium);
		border-radius: 20px;
		padding: 2rem;
		margin-bottom: 2rem;
		box-shadow: var(--shadow-md);
	}

	.invitations-header {
		display: flex;
		align-items: flex-start;
		gap: 1.25rem;
		margin-bottom: 1.5rem;
	}

	.invitations-icon {
		width: 56px;
		height: 56px;
		background: linear-gradient(135deg, var(--cyan-primary) 0%, var(--purple-primary) 100%);
		border-radius: 14px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		box-shadow: var(--shadow-glow);
	}

	.invitations-icon svg {
		width: 28px;
		height: 28px;
		color: white;
	}

	.invitations-title-section h3 {
		margin: 0 0 0.5rem;
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.invitations-title-section p {
		margin: 0;
		font-size: 1rem;
		color: var(--text-secondary);
	}

	.invitations-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.invitation-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		background: var(--glass-bg);
		backdrop-filter: blur(20px);
		border: 1px solid var(--glass-border);
		border-radius: 16px;
		padding: 1.25rem 1.5rem;
		gap: 1.5rem;
		flex-wrap: wrap;
		transition: all 0.3s ease;
	}

	.invitation-card:hover {
		border-color: var(--cyan-primary);
		transform: translateX(4px);
		box-shadow: var(--shadow-md);
	}

	.invitation-org {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.invitation-org-avatar {
		width: 48px;
		height: 48px;
		border-radius: 12px;
		object-fit: cover;
		border: 2px solid var(--border-subtle);
	}

	.invitation-org-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.invitation-org-name {
		font-weight: 700;
		color: var(--text-primary);
		font-size: 1.05rem;
	}

	.invitation-meta {
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.invitation-meta strong {
		color: var(--cyan-primary);
		text-transform: capitalize;
		font-weight: 600;
	}

	.invitation-actions {
		display: flex;
		gap: 0.75rem;
	}

	.btn-accept {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.875rem 1.5rem;
		background: #ffffff;
		color: #000000;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.95rem;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow: var(--shadow-md);
	}

	.btn-accept:hover:not(:disabled) {
		background: var(--primary-color);
		color: #000000;
		transform: translateY(-2px);
		box-shadow: var(--shadow-lg);
	}

	.btn-accept:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-accept svg {
		width: 18px;
		height: 18px;
	}

	.organizations-page.light .btn-accept {
		background: var(--primary-color);
	}

	.organizations-page.light .btn-accept:hover:not(:disabled) {
		background: var(--cyan-light);
	}

	.btn-decline {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.875rem 1.25rem;
		background: rgba(0, 0, 0, 0.3);
		color: var(--red-error);
		border: 2px solid var(--red-error);
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.95rem;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.btn-decline:hover:not(:disabled) {
		background: var(--red-error);
		color: #ffffff;
		transform: translateY(-2px);
		box-shadow:
			0 15px 35px rgba(239, 68, 68, 0.5),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}

	.btn-decline:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-decline svg {
		width: 18px;
		height: 18px;
	}

	.btn-spinner-small {
		width: 16px;
		height: 16px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ============================================
	   MAIN CONTENT AREA
	   ============================================ */
	.page-main {
		margin-bottom: 2rem;
	}

	/* ============================================
	   STATE CARDS (Loading/Error/Empty)
	   ============================================ */
	.state-card {
		background: rgba(0, 0, 0, 0.4);
		backdrop-filter: blur(30px);
		border: 1px solid var(--border-subtle);
		border-radius: 12px;
		padding: 4rem 3rem;
		text-align: center;
		box-shadow: var(--shadow-md);
		position: relative;
		overflow: hidden;
	}

	.organizations-page.light .state-card {
		background: rgba(255, 255, 255, 0.95);
		border: 1px solid var(--border-subtle);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
	}

	.state-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		animation: shimmer 3s ease-in-out infinite;
	}

	@keyframes shimmer {
		0% {
			left: -100%;
		}
		100% {
			left: 100%;
		}
	}

	/* Loading State */
	.loading-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2.5rem;
	}

	.loading-icon {
		position: relative;
		width: 140px;
		height: 140px;
	}

	.github-logo {
		width: 100px;
		height: 100px;
		color: var(--cyan-primary);
		margin: 0 auto;
	}

	.github-logo svg {
		width: 100%;
		height: 100%;
		filter: drop-shadow(0 0 25px currentColor);
		animation: pulse-logo 2s ease-in-out infinite;
	}

	@keyframes pulse-logo {
		0%,
		100% {
			opacity: 0.8;
		}
		50% {
			opacity: 1;
		}
	}

	.scanning-animation {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		border: 3px solid var(--cyan-primary);
		border-radius: 50%;
		animation: scan-pulse 2s ease-in-out infinite;
	}

	.scan-line {
		position: absolute;
		top: 50%;
		left: 10%;
		width: 80%;
		height: 3px;
		background: linear-gradient(90deg, transparent, var(--cyan-primary), transparent);
		transform: translateY(-50%);
		animation: scan-sweep 2s ease-in-out infinite;
	}

	@keyframes scan-pulse {
		0%,
		100% {
			opacity: 0.4;
			transform: scale(1);
		}
		50% {
			opacity: 1;
			transform: scale(1.15);
		}
	}

	@keyframes scan-sweep {
		0%,
		100% {
			opacity: 0;
		}
		50% {
			opacity: 1;
		}
	}

	.loading-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.25rem;
	}

	.loading-title {
		font-size: 2.5rem;
		font-weight: 800;
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
		gap: 0.75rem;
		margin-top: 1rem;
	}

	.dot {
		width: 12px;
		height: 12px;
		background: var(--cyan-primary);
		border-radius: 50%;
		animation: dot-bounce 1.4s ease-in-out infinite;
	}

	.dot:nth-child(2) {
		animation-delay: 0.2s;
	}
	.dot:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes dot-bounce {
		0%,
		80%,
		100% {
			transform: scale(1);
			opacity: 0.5;
		}
		40% {
			transform: scale(1.4);
			opacity: 1;
		}
	}

	/* Error State */
	.error-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2.5rem;
	}

	.error-icon {
		width: 120px;
		height: 120px;
		color: var(--red-error);
		background: rgba(239, 68, 68, 0.1);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 0 30px rgba(239, 68, 68, 0.3);
	}

	.error-icon svg {
		width: 60px;
		height: 60px;
	}

	.error-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.5rem;
		max-width: 600px;
	}

	.error-title {
		font-size: 2.5rem;
		font-weight: 800;
		color: var(--text-primary);
		margin: 0;
	}

	.error-message {
		font-size: 1.15rem;
		color: var(--red-error);
		margin: 0;
		line-height: 1.7;
	}

	.retry-button {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1.2rem 2rem;
		background: #ffffff;
		color: #000000;
		border: none;
		border-radius: 8px;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow: var(--shadow-md);
	}

	.retry-button:hover {
		background: var(--primary-color);
		color: #000000;
		transform: translateY(-3px);
		box-shadow: var(--shadow-lg);
	}

	.organizations-page.light .retry-button {
		background: var(--primary-color);
	}

	.organizations-page.light .retry-button:hover {
		background: var(--cyan-light);
	}

	.retry-icon {
		width: 20px;
		height: 20px;
	}

	/* Empty State */
	.empty-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2.5rem;
	}

	.empty-icon {
		width: 140px;
		height: 140px;
		background: rgba(136, 136, 136, 0.08);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-muted);
		border: 2px dashed var(--border-subtle);
	}

	.empty-icon svg {
		width: 70px;
		height: 70px;
	}

	.empty-content {
		max-width: 700px;
	}

	.empty-title {
		font-size: 2.5rem;
		font-weight: 800;
		color: var(--text-primary);
		margin: 0 0 1rem 0;
	}

	.empty-description {
		font-size: 1.2rem;
		color: var(--text-secondary);
		line-height: 1.7;
		margin: 0 0 2rem 0;
	}

	/* GitHub Connection State */
	.github-connection-state {
		background: linear-gradient(135deg, rgba(0, 217, 255, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
		border: 2px solid var(--border-medium);
	}

	.github-connect-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2.5rem;
		max-width: 700px;
		margin: 0 auto;
	}

	.github-connect-icon {
		position: relative;
		width: 140px;
		height: 140px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.github-connect-icon > svg {
		width: 90px;
		height: 90px;
		color: var(--cyan-primary);
		filter: drop-shadow(0 0 35px rgba(0, 217, 255, 0.5));
	}

	.link-badge {
		position: absolute;
		bottom: 8px;
		right: 8px;
		width: 42px;
		height: 42px;
		background: linear-gradient(135deg, var(--cyan-primary) 0%, var(--purple-primary) 100%);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 6px 20px rgba(0, 217, 255, 0.5);
		animation: pulse-badge 2s ease-in-out infinite;
	}

	.link-badge svg {
		width: 22px;
		height: 22px;
		color: white;
	}

	@keyframes pulse-badge {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.12);
		}
	}

	.github-connect-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.75rem;
		text-align: center;
	}

	.github-connect-title {
		font-size: 2.25rem;
		font-weight: 800;
		color: var(--text-primary);
		margin: 0;
	}

	.github-connect-description {
		font-size: 1.2rem;
		color: var(--text-secondary);
		line-height: 1.8;
		margin: 0;
		max-width: 600px;
	}

	.github-connect-info {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding: 2rem;
		background: rgba(0, 217, 255, 0.05);
		border-radius: 18px;
		border: 1px solid var(--border-subtle);
		width: 100%;
	}

	.info-item {
		display: flex;
		align-items: center;
		gap: 1rem;
		color: var(--text-secondary);
		font-size: 1rem;
		font-weight: 500;
	}

	.info-item svg {
		width: 24px;
		height: 24px;
		color: var(--green-success);
		flex-shrink: 0;
	}

	.github-connect-button {
		display: inline-flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 1.2rem 2rem;
		background: #ffffff;
		color: #000000;
		border: none;
		border-radius: 8px;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
		box-shadow: var(--shadow-md);
	}

	.github-connect-button .button-icon {
		width: 26px;
		height: 26px;
	}

	.github-connect-button:hover:not(:disabled) {
		background: var(--primary-color);
		color: #000000;
		transform: translateY(-3px);
		box-shadow: var(--shadow-lg);
	}

	.github-connect-button .button-arrow {
		font-size: 1.25rem;
		transition: transform 0.3s ease;
	}

	.github-connect-button:hover .button-arrow {
		transform: translateX(5px);
	}

	.github-connect-button:disabled {
		opacity: 0.65;
		cursor: not-allowed;
		transform: none;
	}

	.organizations-page.light .github-connect-button {
		background: var(--primary-color);
	}

	.organizations-page.light .github-connect-button:hover:not(:disabled) {
		background: var(--cyan-light);
	}

	.button-spinner {
		width: 22px;
		height: 22px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.connect-button {
		display: inline-flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 1.2rem 2rem;
		background: #ffffff;
		color: #000000;
		border: none;
		border-radius: 8px;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
		box-shadow: var(--shadow-md);
	}

	.connect-button:hover {
		background: var(--primary-color);
		color: #000000;
		transform: translateY(-3px);
		box-shadow: var(--shadow-lg);
	}

	.connect-button .button-arrow {
		font-size: 1.25rem;
		transition: transform 0.3s ease;
	}

	.connect-button:hover .button-arrow {
		transform: translateX(5px);
	}

	.organizations-page.light .connect-button {
		background: var(--primary-color);
	}

	.organizations-page.light .connect-button:hover {
		background: var(--cyan-light);
	}

	.button-icon {
		width: 24px;
		height: 24px;
		transition: transform 0.3s ease;
	}

	.button-arrow {
		font-size: 1.3rem;
		font-weight: 700;
		transition: transform 0.3s ease;
	}

	/* ============================================
	   FILTER BAR - FULL WIDTH
	   ============================================ */
	.filter-bar {
		display: flex;
		gap: 1rem;
		padding: 1.5rem;
		background: rgba(0, 217, 255, 0.04);
		backdrop-filter: blur(10px);
		border: 1px solid var(--border-subtle);
		border-radius: 12px;
		justify-content: center;
		flex-wrap: wrap;
		margin-bottom: 2rem;
	}

	.organizations-page.light .filter-bar {
		background: rgba(0, 217, 255, 0.06);
	}

	.filter-button {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem 1.75rem;
		background: rgba(0, 0, 0, 0.3);
		backdrop-filter: blur(20px);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 8px;
		color: var(--text-secondary);
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.organizations-page.light .filter-button {
		background: rgba(255, 255, 255, 0.8);
		border-color: rgba(0, 217, 255, 0.2);
	}

	.filter-button:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: var(--primary-color);
		color: var(--primary-color);
		transform: translateY(-2px);
		box-shadow: var(--shadow-glow-strong);
	}

	.filter-button.active {
		background: #ffffff;
		border-color: transparent;
		color: #000000;
		box-shadow: var(--shadow-md);
	}

	.organizations-page.light .filter-button.active {
		background: var(--primary-color);
		color: #000000;
	}

	.filter-icon {
		font-size: 1.2rem;
	}

	.filter-count {
		padding: 0.25rem 0.65rem;
		background: rgba(255, 255, 255, 0.2);
		border-radius: 8px;
		font-size: 0.875rem;
		font-weight: 700;
	}

	.filter-button.active .filter-count {
		background: rgba(255, 255, 255, 0.3);
	}

	/* ============================================
	   ORGANIZATIONS GRID
	   ============================================ */
	.organizations-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(520px, 1fr));
		gap: 2rem;
	}

	/* ============================================
	   ORGANIZATION CARDS - PROFESSIONAL REDESIGN
	   ============================================ */
	.org-card {
		background: rgba(0, 0, 0, 0.4);
		backdrop-filter: blur(30px);
		border: 1px solid var(--border-subtle);
		border-radius: 12px;
		padding: 2.5rem;
		transition: all 0.4s ease;
		position: relative;
		overflow: hidden;
		box-shadow: var(--shadow-md);
	}

	.organizations-page.light .org-card {
		background: rgba(255, 255, 255, 0.95);
		border: 1px solid var(--border-subtle);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
	}

	.org-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		transition: left 0.6s;
	}

	.org-card:hover::before {
		left: 100%;
	}

	.org-card:hover {
		transform: translateY(-5px);
		border-color: rgba(0, 217, 255, 0.5);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.15);
		background: rgba(0, 0, 0, 0.6);
	}

	.organizations-page.light .org-card:hover {
		background: rgba(255, 255, 255, 1);
		border-color: rgba(0, 217, 255, 0.3);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.12);
	}

	.org-card.connected {
		border-color: rgba(0, 217, 255, 0.2);
	}

	.org-card.connected:hover {
		border-color: rgba(0, 217, 255, 0.5);
	}

	/* Organization Card Header */
	.org-card-header {
		margin-bottom: 2rem;
	}

	.org-info {
		display: flex;
		align-items: center;
		gap: 1.25rem;
	}

	.org-avatar {
		position: relative;
		width: 80px;
		height: 80px;
		flex-shrink: 0;
	}

	.org-avatar img {
		width: 100%;
		height: 100%;
		border-radius: 18px;
		border: 3px solid var(--border-medium);
		object-fit: cover;
	}

	.avatar-glow {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 110px;
		height: 110px;
		background: radial-gradient(circle, rgba(0, 217, 255, 0.4) 0%, transparent 70%);
		border-radius: 50%;
		animation: avatar-pulse 3s ease-in-out infinite;
		pointer-events: none;
	}

	@keyframes avatar-pulse {
		0%,
		100% {
			opacity: 0.4;
			transform: translate(-50%, -50%) scale(1);
		}
		50% {
			opacity: 0.7;
			transform: translate(-50%, -50%) scale(1.15);
		}
	}

	.org-details {
		flex: 1;
		min-width: 0;
	}

	.org-name {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0 0 0.875rem 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.org-status {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		flex-wrap: wrap;
	}

	/* Professional Status Badges - Matching Design Pattern */
	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 600;
		backdrop-filter: blur(10px);
		transition: all 0.3s ease;
	}

	.connected-badge {
		background: rgba(0, 217, 255, 0.1);
		color: var(--primary-color);
		border: 1px solid rgba(0, 217, 255, 0.3);
	}

	.organizations-page.light .connected-badge {
		background: rgba(0, 217, 255, 0.08);
		color: #00a0c0;
	}

	.pending-badge {
		background: rgba(184, 184, 184, 0.1);
		color: var(--text-secondary);
		border: 1px solid rgba(184, 184, 184, 0.3);
	}

	.organizations-page.light .pending-badge {
		background: rgba(100, 100, 100, 0.08);
		color: #666666;
	}

	.available-badge {
		background: rgba(0, 217, 255, 0.1);
		color: var(--primary-color);
		border: 1px solid rgba(0, 217, 255, 0.3);
	}

	.owner-badge {
		background: rgba(245, 158, 11, 0.1);
		color: var(--orange-warning);
		border: 1px solid rgba(245, 158, 11, 0.3);
	}

	.shared-badge {
		background: rgba(139, 92, 246, 0.1);
		color: var(--purple-primary);
		border: 1px solid rgba(139, 92, 246, 0.3);
	}

	.badge-icon {
		font-size: 1rem;
	}

	/* Statistics Section - Professional Design */
	.org-stats {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1.25rem;
		margin-bottom: 2rem;
		padding: 1.75rem;
		background: rgba(0, 217, 255, 0.04);
		backdrop-filter: blur(10px);
		border: 1px solid var(--border-subtle);
		border-radius: 16px;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
	}

	.stat-item.full-width {
		grid-column: 1 / -1;
		border-top: 1px solid var(--border-subtle);
		padding-top: 1rem;
		margin-top: 0.5rem;
	}

	.stat-label {
		font-size: 0.875rem;
		color: var(--text-muted);
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.stat-value {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.stat-skeleton {
		width: 50px;
		height: 20px;
		background: linear-gradient(
			90deg,
			rgba(136, 136, 136, 0.1) 25%,
			rgba(136, 136, 136, 0.2) 50%,
			rgba(136, 136, 136, 0.1) 75%
		);
		background-size: 200% 100%;
		border-radius: 6px;
		animation: skeleton-shimmer 1.5s ease-in-out infinite;
	}

	@keyframes skeleton-shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}

	.stat-error {
		color: var(--red-error);
		font-size: 1rem;
	}

	.org-link {
		color: var(--cyan-primary);
		text-decoration: none;
		font-size: 0.95rem;
		font-weight: 600;
		transition: opacity 0.2s;
	}

	.org-link:hover {
		opacity: 0.8;
		text-decoration: underline;
	}

	/* Organization Actions - Professional Buttons */
	.org-actions {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	/* Organization Action Buttons - Matching Design Pattern */
	.org-button {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 1.2rem 2rem;
		border: none;
		border-radius: 8px;
		font-weight: 700;
		font-size: 0.95rem;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
		flex: 1;
		min-width: 0;
	}

	.org-button .button-icon {
		width: 20px;
		height: 20px;
		flex-shrink: 0;
	}

	.org-button .button-arrow {
		font-size: 1.25rem;
		transition: transform 0.3s ease;
	}

	.org-button:hover .button-arrow {
		transform: translateX(5px);
	}

	.workspace-button {
		background: #ffffff;
		color: #000000;
		box-shadow: var(--shadow-md);
	}

	.workspace-button:hover {
		background: var(--primary-color);
		color: #000000;
		transform: translateY(-3px);
		box-shadow: var(--shadow-lg);
	}

	.organizations-page.light .workspace-button {
		background: var(--primary-color);
		color: #000000;
		box-shadow: var(--shadow-md);
	}

	.organizations-page.light .workspace-button:hover {
		background: var(--cyan-light);
		box-shadow: var(--shadow-lg);
	}

	.team-button {
		background: rgba(0, 0, 0, 0.3);
		color: var(--primary-color);
		border: 2px solid var(--primary-color);
		flex: 0 0 auto;
		min-width: auto;
	}

	.organizations-page.light .team-button {
		background: rgba(255, 255, 255, 0.9);
		border-color: var(--primary-color);
	}

	.team-button:hover {
		background: var(--primary-color);
		color: #000000;
		transform: translateY(-3px);
		box-shadow: var(--shadow-lg);
	}

	.install-button {
		background: rgba(0, 0, 0, 0.3);
		color: var(--primary-color);
		border: 2px solid var(--primary-color);
	}

	.install-button:hover {
		background: var(--primary-color);
		color: #000000;
		transform: translateY(-3px);
		box-shadow: var(--shadow-lg);
	}

	.retry-button {
		background: rgba(245, 158, 11, 0.1);
		color: var(--orange-warning);
		border: 2px solid var(--orange-warning);
		flex: 0 0 auto;
		min-width: auto;
	}

	.retry-button:hover {
		background: var(--orange-warning);
		color: #000000;
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(245, 158, 11, 0.5),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}

	/* Section Divider */
	.section-divider {
		height: 2px;
		background: linear-gradient(to right, transparent, var(--border-medium), transparent);
		margin: 4rem 0 3rem;
	}

	.section-header {
		text-align: center;
		margin-bottom: 2.5rem;
	}

	.section-title {
		font-size: 2rem;
		font-weight: 800;
		color: var(--text-primary);
		margin-bottom: 0.75rem;
	}

	.section-description {
		font-size: 1.15rem;
		color: var(--text-secondary);
	}

	/* ============================================
	   RESPONSIVE DESIGN
	   ============================================ */
	@media (max-width: 1200px) {
		.organizations-grid {
			grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
		}
	}

	@media (max-width: 768px) {
		.page-content {
			padding: 1.5rem;
		}

		.header-main {
			flex-direction: column;
			align-items: stretch;
		}

		.header-left {
			flex-direction: column;
			align-items: center;
			text-align: center;
		}

		.header-title {
			font-size: 2rem;
		}

		.header-subtitle {
			font-size: 1rem;
		}

		.header-actions {
			flex-direction: column;
			width: 100%;
		}

		.action-button {
			width: 100%;
			justify-content: center;
		}

		.filter-bar {
			flex-direction: column;
		}

		.filter-button {
			width: 100%;
			justify-content: center;
		}

		.organizations-grid {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}

		.org-stats {
			grid-template-columns: 1fr;
		}

		.org-actions {
			flex-direction: column;
		}

		.org-button {
			flex: 1;
		}

		.state-card {
			padding: 2.5rem 1.5rem;
		}
	}

	@media (max-width: 480px) {
		.page-content {
			padding: 1rem;
		}

		.header-icon {
			width: 60px;
			height: 60px;
		}

		.header-icon svg {
			width: 36px;
			height: 36px;
		}

		.header-title {
			font-size: 2rem;
		}

		.org-card {
			padding: 1.5rem;
		}

		.org-avatar {
			width: 60px;
			height: 60px;
		}

		.org-name {
			font-size: 1.25rem;
		}

		.invitation-card {
			flex-direction: column;
			align-items: stretch;
		}

		.invitation-actions {
			width: 100%;
			justify-content: stretch;
		}

		.btn-accept,
		.btn-decline {
			flex: 1;
		}
	}
</style>
