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
			console.log(` Retry result for ${orgName}:`, statsResult);

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
	<title>Organizations - WithOps DevSecOps Platform</title>
</svelte:head>

<div class="organizations-page {darkMode ? 'dark' : 'light'}">
	<!-- Header Navigation -->
	<nav class="dashboard-header">
		<div class="header-content">
			<a href="/" class="nav-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
				<span class="brand-name">WithOps</span>
			</a>

			<div class="nav-menu">
				<a href="/dashboard" class="nav-link">Overview</a>
				<a href="/organizations" class="nav-link active">Organizations</a>
			</div>

			<div class="nav-actions">
				<button onclick={toggleTheme} class="theme-toggle" title="Toggle theme">
					{#if darkMode}
						<svg
							class="theme-icon"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							stroke-width="2"
						>
							<circle cx="12" cy="12" r="5" /><path
								d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
							/>
						</svg>
					{:else}
						<svg
							class="theme-icon"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
						</svg>
					{/if}
				</button>
			</div>
		</div>
	</nav>

	<!-- Technical Breadcrumb Bar -->
	<div class="technical-bar">
		<div class="breadcrumb">
			<span class="breadcrumb-item">WithOps</span>
			<span class="breadcrumb-sep">/</span>
			<span class="breadcrumb-item active">Organizations</span>
		</div>
		<div class="system-status">
			<div class="status-pulse"></div>
			NODES: GLOBAL ACTIVE
		</div>
	</div>

	<div class="page-content">
		<main class="page-main">
			<header class="view-header">
				<div class="title-group">
					<h1>Workspaces</h1>
					<p>Govern your secure development lifecycle across all managed GitHub organizations.</p>
				</div>
				<div class="header-cta">
					<button onclick={refreshOrganizations} class="btn btn-secondary">
						<svg
							width="14"
							height="14"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path
								d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
							/>
						</svg>
						Sync
					</button>
					<button onclick={connectNewOrganization} class="btn btn-primary">
						Authorize New Org
						<span class="button-arrow">→</span>
					</button>
				</div>
			</header>

			<!-- Notifications / Invites -->
			{#if pendingInvitations.length > 0}
				<div class="invitations-banner">
					<div class="banner-header">
						<h3>PENDING INVITATIONS ({pendingInvitations.length})</h3>
					</div>
					<div class="invites-list">
						{#each pendingInvitations as invitation}
							<div class="invite-item">
								<div class="invite-org-info">
									<img
										src={invitation.organization.avatar_url || '/default-org.png'}
										alt=""
										class="invite-avatar"
									/>
									<div class="invite-details">
										<span class="invite-name"
											>{invitation.organization.name || invitation.organization.login}</span
										>
										<span class="invite-meta"
											>Role: {invitation.role} • via {invitation.invited_by.name ||
												invitation.invited_by.email}</span
										>
									</div>
								</div>
								<div class="org-actions">
									<button
										class="btn btn-primary"
										onclick={() =>
											acceptInvitation(
												invitation.invite_token,
												invitation.organization.name || invitation.organization.login
											)}
										disabled={isAcceptingInvitation === invitation.invite_token}
									>
										Accept
									</button>
									<button
										class="btn btn-outline"
										onclick={() => declineInvitation(invitation.invite_token)}
										disabled={isDecliningInvitation === invitation.invite_token}
									>
										Decline
									</button>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if !loading && !error && connectedOrganizations.length > 0}
				<!-- Sub-navigation Filter -->
				<div class="filter-nav">
					<button
						class="filter-btn {filterType === 'all' ? 'active' : ''}"
						onclick={() => (filterType = 'all')}
					>
						ALL ORGS <span class="count-badge">{connectedOrganizations.length}</span>
					</button>
					<button
						class="filter-btn {filterType === 'owned' ? 'active' : ''}"
						onclick={() => (filterType = 'owned')}
					>
						OWNED <span class="count-badge"
							>{connectedOrganizations.filter((o) => o.installed_by_you).length}</span
						>
					</button>
					<button
						class="filter-btn {filterType === 'shared' ? 'active' : ''}"
						onclick={() => (filterType = 'shared')}
					>
						SHARED <span class="count-badge"
							>{connectedOrganizations.filter((o) => o.auto_linked).length}</span
						>
					</button>
				</div>
			{/if}

			{#if loading}
				<div class="loader-view">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="loader-text">SCANNING INFRASTRUCTURE...</div>
				</div>
			{:else if error}
				<div class="loader-view">
					<p class="error-text">{error}</p>
					<button onclick={loadConnectedOrganizations} class="btn btn-primary mt-4"
						>Retry Connection</button
					>
				</div>
			{:else if connectedOrganizations.length === 0 && !needsGitHubConnection}
				<div class="loader-view">
					<p>No active organizations found.</p>
					<button onclick={connectNewOrganization} class="btn btn-primary mt-4"
						>Connect GitHub</button
					>
				</div>
			{:else if needsGitHubConnection}
				<div class="invitations-banner">
					<div class="banner-header">
						<h3>GITHUB CONNECTION REQUIRED</h3>
					</div>
					<p class="mb-4">
						{githubConnectionMessage || 'Bridge your account to access team installations.'}
					</p>
					<button
						onclick={connectGitHubAccount}
						class="btn btn-primary"
						disabled={isConnectingGitHub}
					>
						{isConnectingGitHub ? 'Redirecting...' : 'Link GitHub Account'}
					</button>
				</div>
			{:else}
				<!-- Grid -->
				<div class="org-grid">
					{#each connectedOrganizations.filter((org) => {
						if (filterType === 'owned') return org.installed_by_you;
						if (filterType === 'shared') return org.auto_linked;
						return true;
					}) as org}
						<div class="org-card">
							<div class="org-card-top">
								<img src={org.avatar_url} alt="" class="org-avatar" />
								<div class="org-meta">
									<h3 class="org-name">{org.login}</h3>
									<div class="status-tag {org.status === 'connected' ? 'connected' : 'pending'}">
										<div class="tag-dot"></div>
										{org.status === 'connected' ? 'VERIFIED' : 'PENDING'}
									</div>
								</div>
							</div>

							<div class="org-stats-row">
								<div class="stat-box">
									<span class="stat-label">Repos</span>
									<span class="stat-value"
										>{org.loading_details ? '...' : (org.repositories_count ?? 0)}</span
									>
								</div>
								<div class="stat-box">
									<span class="stat-label">Flows</span>
									<span class="stat-value"
										>{org.loading_details ? '...' : (org.workflows_count ?? 0)}</span
									>
								</div>
								<div class="stat-box">
									<span class="stat-label">Tier</span>
									<span class="stat-value">{org.installed_by_you ? 'Admin' : 'Member'}</span>
								</div>
							</div>

							<div class="org-actions">
								{#if org.app_installed && org.status === 'connected'}
									<button
										onclick={() => viewOrganizationWorkspace(org.login)}
										class="btn btn-primary btn-full"
									>
										<span>Open Workspace</span>
										<span class="button-arrow">→</span>
									</button>
									{#if org.installed_by_you}
										<button
											onclick={() => goto(`/organizations/${org.login}/team`)}
											class="btn btn-outline"
											title="Settings"
											aria-label="Organization settings"
										>
											<svg
												width="14"
												height="14"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
											>
												<path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
											</svg>
										</button>
									{/if}
								{:else}
									<button
										onclick={() => generateInstallationUrl(org.login, org.id)}
										class="btn btn-secondary btn-full"
									>
										<span>Authorize Access</span>
										<span class="button-arrow">→</span>
									</button>
								{/if}
							</div>
						</div>
					{/each}
				</div>

				{#if discoveredOrganizations.length > 0}
					<div class="view-header border-border mt-12 border-b pb-4">
						<div class="title-group">
							<h2 class="text-lg font-bold">Discoverable Hubs</h2>
							<p>Select a hub from your GitHub profile to integrate with WithOps.</p>
						</div>
					</div>
					<div class="org-grid mt-6">
						{#each discoveredOrganizations.filter((o) => !o.app_installed) as org}
							<div class="org-card">
								<div class="org-card-top">
									<img src={org.avatar_url} alt="" class="org-avatar" />
									<div class="org-meta">
										<h3 class="org-name">{org.login}</h3>
										<div class="status-tag pending">
											<div class="tag-dot"></div>
											UNLINKED
										</div>
									</div>
								</div>
								<div class="org-actions">
									<button
										onclick={() => generateInstallationUrl(org.login, org.id)}
										class="btn btn-secondary btn-full"
									>
										<span>Initialize Hub</span>
										<span class="button-arrow">→</span>
									</button>
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
       PROFESSIONAL DESIGN SYSTEM (MATTE ENGINEERING)
       ============================================ */
	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
		--nav-height: 64px;
	}

	.organizations-page.dark {
		--bg-app: #000000;
		--bg-surface: #020202;
		--bg-surface-alt: #050505;
		--border: rgba(255, 255, 255, 0.03);
		--border-focus: rgba(255, 255, 255, 0.08);
		--text-primary: #f8fafc;
		--text-secondary: #94a3b8;
		--text-muted: #475569;
		--accent: #00adef;
		--accent-soft: rgba(0, 173, 239, 0.05);
		--success: #10b981;
		--error: #ef4444;
		--card-shadow: none;
	}

	.organizations-page.light {
		--bg-app: #ffffff;
		--bg-surface: #f8fafc;
		--bg-surface-alt: #f1f5f9;
		--border: rgba(0, 0, 0, 0.06);
		--border-focus: rgba(0, 173, 239, 0.2);
		--text-primary: #0f172a;
		--text-secondary: #475569;
		--text-muted: #94a3b8;
		--accent: #0082b4;
		--accent-soft: rgba(0, 130, 180, 0.08);
		--success: #059669;
		--error: #dc2626;
		--card-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
	}

	.organizations-page {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
		overflow-x: hidden;
	}

	/* Architectural Backdrop */
	.organizations-page::before {
		content: '';
		position: fixed;
		inset: 0;
		background-image:
			linear-gradient(var(--border) 1px, transparent 1px),
			linear-gradient(90deg, var(--border) 1px, transparent 1px);
		background-size: 40px 40px;
		mask-image: radial-gradient(circle at 50% 50%, black, transparent 80%);
		pointer-events: none;
		z-index: 0;
		opacity: 0.5;
	}

	.page-content {
		position: relative;
		z-index: 10;
		padding-bottom: 5rem;
	}

	/* Header Navigation */
	.dashboard-header {
		height: var(--nav-height);
		background: rgba(var(--bg-app), 0.8);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		position: sticky;
		top: 0;
		z-index: 100;
	}

	.header-content {
		max-width: 1440px;
		width: 100%;
		margin: 0 auto;
		padding: 0 2rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		text-decoration: none;
		color: var(--text-primary);
	}

	.brand-icon {
		width: 28px;
		height: 28px;
	}
	.brand-name {
		font-weight: 700;
		font-size: 1rem;
		letter-spacing: -0.02em;
	}

	.nav-menu {
		display: flex;
		gap: 1.5rem;
		margin-left: 3rem;
	}
	.nav-link {
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
		padding: 0.5rem 0;
	}
	.nav-link:hover,
	.nav-link.active {
		color: var(--text-primary);
	}

	.nav-actions {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}

	.theme-toggle {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 6px;
		transition: all 0.2s;
	}
	.theme-toggle:hover {
		background: var(--border);
		color: var(--text-primary);
	}
	.theme-icon {
		width: 18px;
		height: 18px;
	}

	/* Technical Bar */
	.technical-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 0 2rem;
		display: flex;
		align-items: center;
		height: 40px;
	}

	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.breadcrumb-sep {
		color: var(--border);
	}
	.breadcrumb-item.active {
		color: var(--accent);
	}

	.system-status {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--success);
		opacity: 0.8;
	}
	.status-pulse {
		width: 4px;
		height: 4px;
		background: currentColor;
		border-radius: 50%;
		animation: blink 2s infinite;
	}
	@keyframes blink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.3;
		}
	}

	/* Main Content Layout */
	.page-main {
		max-width: 1440px;
		margin: 0 auto;
		padding: 3rem 2rem;
	}

	.view-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		margin-bottom: 3rem;
	}

	.title-group h1 {
		font-size: 1.75rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		margin-bottom: 0.5rem;
	}
	.title-group p {
		color: var(--text-secondary);
		font-size: 0.9375rem;
		max-width: 500px;
		line-height: 1.5;
	}

	.header-cta {
		display: flex;
		gap: 0.75rem;
	}

	/* Specialized Filters */
	.filter-nav {
		display: flex;
		gap: 0.25rem;
		background: var(--bg-surface-alt);
		padding: 0.25rem;
		border-radius: 8px;
		border: 1px solid var(--border);
		margin-bottom: 2rem;
		width: fit-content;
	}

	.filter-btn {
		background: none;
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.filter-btn:hover {
		color: var(--text-primary);
	}
	.filter-btn.active {
		background: var(--bg-surface);
		color: var(--accent);
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.count-badge {
		font-size: 0.65rem;
		background: var(--border);
		color: var(--text-muted);
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
	}

	/* Organization Grid & Cards */
	.org-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 1.5rem;
	}

	.org-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2rem;
		transition: all 0.2s var(--ease-premium);
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		position: relative;
		overflow: hidden;
		box-shadow: var(--card-shadow);
	}

	.org-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-2px);
		box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
	}

	.org-card-top {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.org-avatar {
		width: 48px;
		height: 48px;
		border-radius: 8px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		padding: 2px;
	}

	.org-meta {
		flex: 1;
	}
	.org-name {
		font-weight: 700;
		font-size: 1rem;
		margin-bottom: 0.25rem;
	}

	.status-tag {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.75rem;
		border-radius: 6px;
		font-size: 0.75rem;
		font-weight: 600;
		font-family: var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.status-tag.connected {
		color: var(--success);
		border: 1px solid rgba(16, 185, 129, 0.1);
		opacity: 0.9;
	}
	.status-tag.pending {
		color: var(--text-muted);
		border: 1px solid var(--border);
		opacity: 0.7;
	}
	.tag-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: currentColor;
	}

	.org-stats-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1rem;
		padding: 1rem 0;
		border-top: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
	}

	.stat-box {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}
	.stat-label {
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.stat-value {
		font-family: var(--font-mono);
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.org-actions {
		display: flex;
		gap: 0.5rem;
	}

	/* Buttons */
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.8125rem 1.25rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
		font-family: var(--font-sans);
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		white-space: nowrap;
	}

	.btn:hover:not(:disabled) {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
		transform: translateY(-1px);
	}

	.btn-primary {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
	}
	.btn-primary:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.btn-outline {
		background: transparent;
		border-color: var(--border);
		color: var(--text-secondary);
	}

	.btn-outline:hover:not(:disabled) {
		border-color: var(--border-focus);
		color: var(--text-primary);
		background: var(--bg-surface-alt);
	}

	.button-arrow {
		font-size: 1.1rem;
		transition: transform 0.2s var(--ease-premium);
	}

	.btn:hover .button-arrow {
		transform: translateX(4px);
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.btn-full {
		width: 100%;
	}

	/* Loader */
	.loader-view {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 10rem 2rem;
		text-align: center;
	}

	.loader-icon {
		width: 48px;
		height: 48px;
		margin-bottom: 1.5rem;
		animation: pulse 2s infinite;
	}
	@keyframes pulse {
		0%,
		100% {
			opacity: 0.5;
			transform: scale(0.95);
		}
		50% {
			opacity: 1;
			transform: scale(1);
		}
	}
	.loader-text {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	/* Banner / Notifications */
	.invitations-banner {
		background: var(--bg-surface-alt);
		border: 1px solid var(--accent);
		border-radius: 12px;
		padding: 1.25rem;
		margin-bottom: 2rem;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.banner-header h3 {
		font-size: 0.9375rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.invites-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.invite-item {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		padding: 0.75rem 1rem;
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.invite-org-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.invite-avatar {
		width: 32px;
		height: 32px;
		border-radius: 4px;
	}
	.invite-details {
		display: flex;
		flex-direction: column;
	}
	.invite-name {
		font-weight: 600;
		font-size: 0.8125rem;
	}
	.invite-meta {
		font-size: 0.7rem;
		color: var(--text-secondary);
	}

	@media (max-width: 768px) {
		.page-content {
			padding: 1rem;
		}
		.view-header {
			flex-direction: column;
			align-items: flex-start;
			gap: 1.5rem;
		}
		.nav-menu {
			display: none;
		}
		.org-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
