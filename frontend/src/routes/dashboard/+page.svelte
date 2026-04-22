<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getAuthClient } from '$lib/auth';
	import { githubClient } from '$lib/github.js';
	import { isDarkMode } from '$lib/stores.js';

	let user = $state(null);
	let loading = $state(true);
	let dashboardData = $state(null);
	let isGitHubConnected = $state(false);
	let isDiscovering = $state(false);
	let profilePictureError = $state(false);
	let pictureRetryCount = $state(0);
	let isProfileDropdownOpen = $state(false);

	// Subscribe to the global theme store
	let darkMode = $state(false);
	isDarkMode.subscribe((value) => {
		darkMode = value;
	});

	// Helper function to get a working profile picture URL
	function getProfilePictureUrl(picture, retryCount = 0) {
		if (!picture) return null;

		// If it's a Google profile picture, try different formats
		if (picture.includes('googleusercontent.com')) {
			const baseUrl = picture.split('=')[0];

			switch (retryCount) {
				case 0:
					// Original format with size parameter
					return `${baseUrl}=s96-c`;
				case 1:
					// Without size parameter
					return baseUrl;
				case 2:
					// With different size
					return `${baseUrl}=s64-c`;
				default:
					return picture; // Original as last resort
			}
		}

		return picture;
	}

	// Function to handle picture loading errors with retry
	function handlePictureError(e) {
		pictureRetryCount++;
		console.warn(
			`Profile picture failed to load (attempt ${pictureRetryCount}):`,
			getProfilePictureUrl(user.picture, pictureRetryCount - 1)
		);

		if (pictureRetryCount < 4) {
			// Try again with different URL format
			e.target.src = getProfilePictureUrl(user.picture, pictureRetryCount);
			console.log('Retrying with URL:', e.target.src);
		} else {
			// Give up and show initials
			console.warn('All profile picture attempts failed, showing initials');
			profilePictureError = true;
		}
	}

	onMount(async () => {
		try {
			// Initialize theme
			isDarkMode.init();

			// Add click outside listener for dropdown
			document.addEventListener('click', handleClickOutside);

			const client = await getAuthClient();
			const isAuthenticated = await client.isAuthenticated();

			if (!isAuthenticated) {
				// Redirect unauthenticated users to home
				goto('/');
				return;
			}

			user = await client.getUser();
			console.log('✅ User authenticated on dashboard:', user.name);
			console.log('👤 User profile data:', $state.snapshot(user)); // Use $state.snapshot for proper logging
			console.log('🖼️ Profile picture URL:', user.picture); // Debug the picture URL specifically

			// Reset profile picture error state when user changes
			profilePictureError = false;
			pictureRetryCount = 0;

			// Check URL parameters for GitHub OAuth callback
			const urlParams = new URLSearchParams(window.location.search);
			if (urlParams.get('github_connected') === 'true') {
				isGitHubConnected = true;
			}

			await loadDashboardData();
		} catch (error) {
			console.error('Dashboard auth check failed:', error);
			goto('/');
		} finally {
			loading = false;
		}

		// Cleanup listener on unmount
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});

	async function loadDashboardData() {
		try {
			const client = await getAuthClient();
			const token = await client.getTokenSilently();

			const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9060';
			const response = await fetch(`${apiBase}/api/auth/dashboard`, {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (response.ok) {
				dashboardData = await response.json();
				// Check if GitHub is connected based on dashboard data
				if (
					dashboardData &&
					(dashboardData.github_connected ||
						dashboardData.github_token ||
						dashboardData.organizations)
				) {
					isGitHubConnected = true;
				}
			}

			// Also check GitHub connection status via dedicated endpoint
			await checkGitHubConnection();
		} catch (error) {
			console.error('Failed to load dashboard data:', error);
		}
	}

	async function checkGitHubConnection() {
		try {
			// First check GitHub connection status via dedicated endpoint
			const connectionStatus = await githubClient.getGitHubConnectionStatus();

			if (connectionStatus.success && connectionStatus.github_connected) {
				isGitHubConnected = true;
				console.log('✅ GitHub connected:', connectionStatus.github_username);
				return;
			}

			// Fallback: check if user has organizations
			const client = await getAuthClient();
			const token = await client.getTokenSilently();

			const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9060';
			const response = await fetch(`${apiBase}/api/github/my-organizations`, {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				// User is connected if they have any organizations
				isGitHubConnected = data.organizations && data.organizations.length > 0;
				console.log('GitHub connection status:', isGitHubConnected);
				console.log('User organizations:', data.organizations);
			}
		} catch (error) {
			console.error('Failed to check GitHub connection status:', error);
			// Don't throw error, just leave isGitHubConnected as false
		}
	}

	async function logout() {
		const client = await getAuthClient();
		await client.logout({ returnTo: window.location.origin });
		// Clear the cached client after logout to force re-initialization on next login
		const { clearAuthClient } = await import('$lib/auth');
		clearAuthClient();
	}

	async function connectToGitHub() {
		try {
			// Use the new GitHub connection endpoint
			const result = await githubClient.startGitHubConnection();

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

	function toggleTheme() {
		isDarkMode.toggle();
	}

	function toggleProfileDropdown() {
		isProfileDropdownOpen = !isProfileDropdownOpen;
	}

	function closeProfileDropdown() {
		isProfileDropdownOpen = false;
	}

	// Close dropdown when clicking outside
	function handleClickOutside(event) {
		const dropdown = document.querySelector('.profile-dropdown-container');
		if (dropdown && !dropdown.contains(event.target)) {
			closeProfileDropdown();
		}
	}

	async function connectGitHub() {
		await connectToGitHub();
	}

	async function discoverOrganizations() {
		isDiscovering = true;
		try {
			const result = await githubClient.startOrganizationDiscovery();

			if (result.success) {
				// Redirect to GitHub OAuth for organization discovery
				window.location.href = result.oauth_url;
			} else {
				console.error('Failed to start organization discovery:', result.error);
				alert('Failed to start organization discovery. Please try again.');
			}
		} catch (error) {
			console.error('Organization discovery error:', error);
			alert('Failed to discover organizations. Please try again.');
		} finally {
			isDiscovering = false;
		}
	}
</script>


<svelte:head>
	<title>Dashboard - WithOps DevSecOps Platform</title>
</svelte:head>

{#if loading}
	<div class="loading-screen">
		<div class="loading-content">
			<img src="/icons/excellence_17274210.png" alt="WithOps" class="loading-icon" />
			<div class="progress-bar">
				<div class="progress-fill"></div>
			</div>
			<div class="status-message">INITIALIZING SECURE ENVIRONMENT...</div>
		</div>
	</div>
{:else}
	<div class="dashboard-container {darkMode ? 'dark' : 'light'}">
		<!-- Header -->
		<nav class="dashboard-header">
			<div class="header-content">
				<a href="/" class="nav-brand">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<span class="brand-name">WithOps</span>
				</a>

				<div class="nav-menu">
					<a href="/dashboard" class="nav-link active">Overview</a>
					<a href="/organizations" class="nav-link">Organizations</a>
				</div>

				<div class="nav-actions">
					<button onclick={toggleTheme} class="theme-toggle" title="Toggle theme">
						{#if darkMode}
							<svg class="theme-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
							</svg>
						{:else}
							<svg class="theme-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
							</svg>
						{/if}
					</button>

					<div class="profile-dropdown-container">
						<button class="user-profile-trigger" onclick={toggleProfileDropdown}>
							{#if user?.picture && !profilePictureError}
								<img
									src={getProfilePictureUrl(user.picture, pictureRetryCount)}
									alt={user.name || 'User'}
									class="avatar-image"
									onerror={handlePictureError}
								/>
							{:else}
								<span class="avatar-text">
									{user?.name?.charAt(0)?.toUpperCase() || 'U'}
								</span>
							{/if}
						</button>

						{#if isProfileDropdownOpen}
							<div class="profile-dropdown">
								<div class="dropdown-user-info">
									<p class="dropdown-name">{user?.name || 'User'}</p>
									<p class="dropdown-email">{user?.email || ''}</p>
								</div>
								<div class="dropdown-divider"></div>
								<button onclick={logout} class="dropdown-logout-button">
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
									</svg>
									Sign Out
								</button>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<!-- Technical Status Bar -->
		<div class="technical-bar">
			<div class="breadcrumb-node">WithOps</div>
			<div class="breadcrumb-sep">/</div>
			<div class="breadcrumb-node active">Overview</div>
			<div class="system-status-pill">
				<div class="status-pulse"></div>
				SYSTEM: ACTIVE
			</div>
		</div>

		<!-- Main Layout -->
		<main class="dashboard-main">
			<header class="hero-section">
				<h1 class="hero-title">
					Welcome back, <span class="title-highlight">{user?.name?.split(' ')[0] || 'User'}</span>
				</h1>
				<p class="hero-description">
					Manage your secure development pipelines and organizational security posture from a single, high-fidelity command center.
				</p>
			</header>

			<div class="dashboard-grid">
				<!-- GitHub Card -->
				<div class="dashboard-card github-card">
					<div class="feature-number">01 / INTEGRATION</div>
					<h3 class="card-title">GitHub Connectivity</h3>
					<p class="card-description">
						Bridge your development lifecycle with automated security intelligence and real-time scanning.
					</p>

					<ul class="feature-list">
						<li>Automated vulnerability detection</li>
						<li>Security workflow orchestration</li>
						<li>Enterprise compliance auditing</li>
					</ul>

					<div class="card-status">
						{#if isGitHubConnected}
							<div class="status-badge connected">
								<div class="status-icon"></div>
								ACCOUNT VERIFIED
							</div>
						{:else}
							<div class="status-badge disconnected">
								<div class="status-icon"></div>
								ACTION REQUIRED
							</div>
						{/if}
					</div>

					{#if isGitHubConnected}
						<button
							onclick={discoverOrganizations}
							disabled={isDiscovering}
							class="card-action-button"
						>
							{#if isDiscovering}
								<span class="button-spinner"></span>
								<span>Locating Organizations...</span>
							{:else}
								<span>Discover Organizations</span>
								<span class="button-arrow">→</span>
							{/if}
						</button>
					{:else}
						<button onclick={connectGitHub} class="card-action-button">
							<span>Authorize GitHub Account</span>
							<span class="button-arrow">→</span>
						</button>
					{/if}
				</div>

				<!-- Workspaces Card -->
				<div class="dashboard-card workspace-card">
					<div class="feature-number">02 / MANAGEMENT</div>
					<h3 class="card-title">Command Center</h3>
					<p class="card-description">
						Govern your organization-wide security policies and monitor continuous deployment health.
					</p>

					<ul class="feature-list">
						<li>Multi-org policy management</li>
						<li>Aggregated security insights</li>
						<li>Team access & governance</li>
					</ul>

					<button onclick={() => goto('/organizations')} class="card-action-button">
						<span>Open Command Center</span>
						<span class="button-arrow">→</span>
					</button>
				</div>
			</div>
		</main>
	</div>
{/if}


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

	.dashboard-container.dark {
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

	.dashboard-container.light {
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

	/* Global Reset & Base */
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	.dashboard-container {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
		overflow-x: hidden;
	}

	.dashboard-container::before {
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

	.dashboard-container::after {
		content: '';
		position: fixed;
		inset: 0;
		background: radial-gradient(circle at 50% -20%, var(--accent-soft), transparent 70%);
		pointer-events: none;
		z-index: 0;
	}

	/* Loader */
	.loading-screen {
		position: fixed;
		inset: 0;
		background: #000000;
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 9999;
	}

	.loading-content {
		text-align: center;
		max-width: 300px;
	}

	.loading-icon {
		width: 48px;
		height: 48px;
		margin-bottom: 2rem;
		animation: pulse 2s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 0.5; transform: scale(0.95); }
		50% { opacity: 1; transform: scale(1); }
	}

	.progress-bar {
		height: 2px;
		background: rgba(255, 255, 255, 0.05);
		border-radius: 4px;
		overflow: hidden;
		margin: 1rem 0;
	}

	.progress-fill {
		height: 100%;
		background: var(--accent, #00adef);
		width: 40%;
		animation: load 1.5s ease-in-out infinite;
	}

	@keyframes load {
		0% { transform: translateX(-100%); width: 20%; }
		50% { width: 50%; }
		100% { transform: translateX(300%); width: 20%; }
	}

	/* Sub-Header / Breadcrumbs */
	.technical-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 0.5rem 2rem;
		display: flex;
		align-items: center;
		gap: 1rem;
		height: 40px;
		z-index: 90;
	}

	.breadcrumb-node {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.breadcrumb-node.active {
		color: var(--accent);
	}

	.breadcrumb-sep {
		color: var(--border-focus);
	}

	.system-status-pill {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--success);
		padding: 0.25rem 0.5rem;
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
		0%, 100% { opacity: 1; }
		50% { opacity: 0.3; }
	}

	/* Header Navigation */
	.dashboard-header {
		position: sticky;
		top: 0;
		z-index: 100;
		height: var(--nav-height);
		background: rgba(var(--bg-app), 0.8);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
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
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
		padding: 0.5rem 0;
		position: relative;
	}

	.nav-link:hover, .nav-link.active {
		color: var(--text-primary);
	}

	.nav-link.active::after {
		content: '';
		position: absolute;
		bottom: -1px;
		left: 0;
		right: 0;
		height: 2px;
		background: var(--accent);
	}

	.nav-actions {
		display: flex;
		align-items: center;
		gap: 1.25rem;
	}

	/* Theme Toggle */
	.theme-toggle {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		padding: 0.5rem;
		border-radius: 8px;
		cursor: pointer;
		display: flex;
		transition: all 0.15s;
	}

	.theme-toggle:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		border-color: var(--border-focus);
	}

	.theme-icon {
		width: 18px;
		height: 18px;
	}

	/* Profile Dropdown */
	.user-profile-trigger {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		width: 32px;
		height: 32px;
		border-radius: 50%;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		transition: border-color 0.15s;
	}

	.user-profile-trigger:hover {
		border-color: var(--border-focus);
	}

	.avatar-image {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.avatar-text {
		font-size: 0.75rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.profile-dropdown {
		position: absolute;
		top: calc(100% + 8px);
		right: 0;
		width: 240px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
		padding: 0.75rem;
		z-index: 1000;
	}

	.dropdown-user-info {
		padding: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.dropdown-name {
		font-weight: 600;
		font-size: 0.875rem;
		margin-bottom: 0.125rem;
	}

	.dropdown-email {
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	.dropdown-divider {
		height: 1px;
		background: var(--border);
		margin: 0.5rem 0;
	}

	.dropdown-logout-button {
		width: 100%;
		padding: 0.625rem;
		border-radius: 6px;
		border: none;
		background: transparent;
		color: var(--error);
		font-size: 0.875rem;
		font-weight: 500;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		transition: background 0.15s;
	}

	.dropdown-logout-button:hover {
		background: rgba(239, 68, 68, 0.08);
	}

	/* Main Dashboard Content */
	.dashboard-main {
		max-width: 1440px;
		margin: 0 auto;
		padding: 3rem 2rem;
	}

	.hero-section {
		margin-bottom: 4rem;
	}

	.hero-title {
		font-size: 2rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		margin-bottom: 0.75rem;
	}

	.title-highlight {
		color: var(--accent);
	}

	.hero-description {
		font-size: 1rem;
		color: var(--text-secondary);
		max-width: 600px;
		line-height: 1.6;
	}

	.dashboard-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
		gap: 1.5rem;
	}

	/* Dashboard Cards */
	.dashboard-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2rem;
		display: flex;
		flex-direction: column;
		transition: all 0.2s var(--ease-premium);
		box-shadow: var(--card-shadow);
	}

	.dashboard-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-2px);
		box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
	}

	.feature-number {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		color: var(--text-muted);
		margin-bottom: 1.5rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.feature-number::before {
		content: '';
		width: 12px;
		height: 1px;
		background: var(--border);
	}

	.card-title {
		font-size: 1.125rem;
		font-weight: 700;
		margin-bottom: 0.75rem;
		letter-spacing: -0.01em;
	}

	.card-description {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.6;
		margin-bottom: 1.5rem;
		flex-grow: 1;
	}

	.feature-list {
		margin-bottom: 2rem;
		list-style: none;
	}

	.feature-list li {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		margin-bottom: 0.5rem;
		display: flex;
		align-items: center;
		gap: 0.625rem;
	}

	.feature-list li::before {
		content: '';
		width: 4px;
		height: 4px;
		background: var(--text-muted);
		border-radius: 50%;
	}

	.card-status {
		margin-bottom: 1.5rem;
	}

	.status-badge {
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

	.status-badge.connected {
		color: var(--success);
		border: 1px solid rgba(16, 185, 129, 0.1);
		opacity: 0.9;
	}

	.status-badge.disconnected {
		color: var(--text-muted);
		border: 1px solid var(--border);
		opacity: 0.7;
	}

	.status-icon {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: currentColor;
	}

	/* Buttons */
	.card-action-button {
		width: 100%;
		padding: 0.875rem;
		border-radius: 8px;
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		font-size: 0.875rem;
		font-weight: 600;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.card-action-button:hover:not(:disabled) {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
	}

	.github-card .card-action-button {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
	}

	.github-card .card-action-button:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.button-arrow {
		transition: transform 0.15s;
	}

	.card-action-button:hover .button-arrow {
		transform: translateX(3px);
	}

	.button-spinner {
		width: 16px;
		height: 16px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Responsive */
	@media (max-width: 1024px) {
		.dashboard-grid {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 640px) {
		.header-content {
			padding: 0 1rem;
		}
		.nav-menu {
			display: none;
		}
		.dashboard-main {
			padding: 2rem 1rem;
		}
		.hero-title {
			font-size: 1.5rem;
		}
	}
</style>

