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

			const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';
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

			const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';
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
		<!-- Main Loading Content -->
		<div class="loading-content">
			<!-- Icon Container -->
			<div class="loading-icon-container">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="loading-icon" />
			</div>

			<!-- Info Section -->
			<div class="info-section">
				<h1 class="loading-title">WithOps</h1>
				<p class="loading-subtitle">DEVSECOPS PLATFORM</p>

				<!-- Progress Bar -->
				<div class="progress-section">
					<div class="progress-bar">
						<div class="progress-fill"></div>
					</div>
				</div>

				<!-- Status Message -->
				<div class="status-message">
					<div class="status-dot"></div>
					<span>Initializing your secure development environment</span>
				</div>
			</div>
		</div>
	</div>
{:else}
	<div class="dashboard-container {darkMode ? 'dark' : 'light'}">
		<!-- Navigation Header - Matching Landing Page -->
		<nav class="dashboard-header">
			<div class="header-content">
				<!-- Left side - Brand & Navigation -->
				<div class="nav-brand">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<span class="brand-name">WithOps</span>
				</div>

				<div class="nav-menu">
					<a href="/dashboard" class="nav-link active">Dashboard</a>
					<a href="/organizations" class="nav-link">Organizations</a>
					<a href="#analytics" class="nav-link">Analytics</a>
				</div>

				<!-- Right side - User Profile & Theme -->
				<div class="nav-actions">
					<!-- Theme Toggle -->
					<button onclick={toggleTheme} class="theme-toggle" title="Toggle theme">
						{#if darkMode}
							<svg class="theme-icon" fill="currentColor" viewBox="0 0 24 24">
								<path
									d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z"
								/>
							</svg>
						{:else}
							<svg class="theme-icon" fill="currentColor" viewBox="0 0 24 24">
								<path
									fill-rule="evenodd"
									d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z"
									clip-rule="evenodd"
								/>
							</svg>
						{/if}
					</button>

					<!-- User Profile -->
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
									<div class="dropdown-avatar">
										{#if user?.picture && !profilePictureError}
											<img
												src={getProfilePictureUrl(user.picture, pictureRetryCount)}
												alt={user.name || 'User'}
												class="avatar-image"
												onerror={handlePictureError}
											/>
										{:else}
											<span class="avatar-text">
												{user?.name?.charAt(0)?.toUpperCase() ||
													user?.email?.charAt(0)?.toUpperCase() ||
													'U'}
											</span>
										{/if}
									</div>
									<div class="dropdown-user-details">
										<p class="dropdown-name">{user?.name || 'User'}</p>
										<p class="dropdown-email">{user?.email || ''}</p>
									</div>
								</div>

								<div class="dropdown-divider"></div>

								<button onclick={logout} class="dropdown-logout-button">
									<svg
										class="logout-icon-svg"
										width="18"
										height="18"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
									>
										<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
										<polyline points="16 17 21 12 16 7"></polyline>
										<line x1="21" y1="12" x2="9" y2="12"></line>
									</svg>
									Sign Out
								</button>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<!-- Hero Section with Platform Description -->
		<section class="hero-section">
			<div class="hero-content">
				<div class="hero-text">
					<h1 class="hero-title">
						Welcome to <span class="title-highlight">WithOps</span>
					</h1>
					<p class="hero-description">
						Your comprehensive DevSecOps platform for secure development workflows. Connect your
						GitHub repositories and organizations to enhance your development pipeline with
						enterprise-grade security built-in.
					</p>
				</div>
			</div>
		</section>

		<!-- SVG Workflow Art Section -->
		
		<!-- todo:---- -->

		<!-- Main Dashboard Content -->
		<main class="dashboard-main">
			<div class="dashboard-grid">
				<!-- GitHub Connection Section -->
				<div class="dashboard-card github-card">
					<div class="feature-number">01</div>
					<h3 class="card-title">GitHub Integration</h3>
					<p class="card-description">
						Connect your repositories for automated security scanning and continuous monitoring
					</p>

					<div class="card-features">
						<ul class="feature-list">
							<li>Automated vulnerability scanning</li>
							<li>Real-time security workflow automation</li>
							<li>Compliance checks and reporting</li>
							<li>Pull request security analysis</li>
						</ul>
					</div>

					{#if !isGitHubConnected}
						<div class="card-status">
							<div class="status-badge disconnected">
								<span class="status-icon">◆</span>
								<span>Not Connected</span>
							</div>
						</div>
						<button onclick={connectToGitHub} class="card-action-button">
							<span class="button-text">Connect GitHub Account</span>
							<span class="button-arrow">→</span>
						</button>
					{:else}
						<div class="card-status">
							<div class="status-badge connected">
								<span class="status-icon">✓</span>
								<span>Connected & Active</span>
							</div>
						</div>
						<button
							onclick={discoverOrganizations}
							disabled={isDiscovering}
							class="card-action-button {isDiscovering ? 'loading' : ''}"
						>
							{#if isDiscovering}
								<span class="button-text">Discovering Organizations...</span>
								<span class="button-spinner"></span>
							{:else}
								<span class="button-text">Discover Organizations</span>
								<span class="button-arrow">→</span>
							{/if}
						</button>
					{/if}
				</div>

				<!-- Organization Workspaces Section -->
				<div class="dashboard-card workspace-card">
					<div class="feature-number">02</div>
					<h3 class="card-title">Organization Workspaces</h3>
					<p class="card-description">
						Manage your DevSecOps pipelines and security workflows across all organizations
					</p>

					<div class="card-features">
						<ul class="feature-list">
							<li>Repository-level security policies</li>
							<li>Automated scanning and monitoring</li>
							<li>Compliance tracking and reporting</li>
							<li>Team collaboration and insights</li>
						</ul>
					</div>

					<button onclick={() => goto('/organizations')} class="card-action-button">
						<span class="button-text">View Workspaces</span>
						<span class="button-arrow">→</span>
					</button>
				</div>
			</div>
		</main>
	</div>
{/if}

<style>
	/* Global Reset and Dark Theme Variables */
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	:global(body) {
		font-family:
			'Inter',
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			Roboto,
			sans-serif;
	}

	/* Dashboard Container */
	.dashboard-container {
		position: relative;
		min-height: 100vh;
		background: var(--bg-primary);
		overflow-x: hidden;
		--bg-primary: #000000;
		--bg-secondary: #0a0a0a;
		--text-primary: #ffffff;
		--text-secondary: #b8b8b8;
		--border-color: rgba(0, 217, 255, 0.3);
		--card-bg: rgba(255, 255, 255, 0.05);
		--card-bg-hover: rgba(255, 255, 255, 0.08);
		--primary-color: #00d9ff;
		--accent-color: #00d9ff;
		--github-bg: #24292f;
		--github-text: #f0f6ff;
	}

	.dashboard-container.light {
		--bg-primary: #ffffff;
		--bg-secondary: #f8fafc;
		--text-primary: #1a1a1a;
		--text-secondary: #666666;
		--border-color: rgba(0, 217, 255, 0.4);
		--card-bg: rgba(0, 217, 255, 0.05);
		--card-bg-hover: rgba(0, 217, 255, 0.1);
		--primary-color: #00d9ff;
		--accent-color: #00b8d4;
		--github-bg: #f0f6ff;
		--github-text: #24292f;
	}

	/* ============================================
       ADVANCED LOADING SCREEN - MODERN UI
       ============================================ */

	.loading-screen {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background: #000000;
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 9999;
	}

	.loading-content {
		position: relative;
		text-align: center;
		z-index: 1;
		animation: fadeIn 0.5s ease-out;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	/* Icon Container */
	.loading-icon-container {
		position: relative;
		width: 120px;
		height: 120px;
		margin: 0 auto 3rem;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.loading-icon {
		width: 120px;
		height: 120px;
		filter: drop-shadow(0 0 20px rgba(0, 217, 255, 0.5));
		animation: iconFloat 3s ease-in-out infinite;
	}

	@keyframes iconFloat {
		0%,
		100% {
			transform: translateY(0);
		}
		50% {
			transform: translateY(-10px);
		}
	}

	/* Info Section */
	.info-section {
		max-width: 420px;
		margin: 0 auto;
		text-align: center;
	}

	.loading-title {
		font-size: 2.5rem;
		font-weight: 700;
		margin-bottom: 0.5rem;
		color: #ffffff;
		letter-spacing: -0.02em;
	}

	.loading-subtitle {
		font-size: 0.875rem;
		color: #b8b8b8;
		letter-spacing: 0.15em;
		font-weight: 500;
		margin-bottom: 2.5rem;
	}

	/* Progress Section */
	.progress-section {
		margin-bottom: 2rem;
	}

	.progress-bar {
		width: 100%;
		height: 3px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 10px;
		overflow: hidden;
		position: relative;
	}

	.progress-fill {
		height: 100%;
		background: #00d9ff;
		border-radius: 10px;
		animation: progressLoad 2s ease-in-out infinite;
		box-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
	}

	@keyframes progressLoad {
		0% {
			width: 0%;
		}
		50% {
			width: 70%;
		}
		100% {
			width: 100%;
		}
	}

	/* Status Message */
	.status-message {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
	}

	.status-dot {
		width: 8px;
		height: 8px;
		background: #00d9ff;
		border-radius: 50%;
		box-shadow: 0 0 10px rgba(0, 217, 255, 0.6);
		animation: dotPulse 1.5s ease-in-out infinite;
	}

	@keyframes dotPulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.4;
		}
	}

	.status-message span {
		font-size: 0.875rem;
		color: #b8b8b8;
		font-weight: 400;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Dashboard Header */
	.dashboard-header {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 1000;
		background: rgba(0, 0, 0, 0.95);
		backdrop-filter: blur(20px);
		border-bottom: 1px solid rgba(0, 217, 255, 0.3);
		padding: 1rem 0;
		transition: all 0.3s ease;
	}

	.dashboard-container.light .dashboard-header {
		background: rgba(255, 255, 255, 0.95);
		border-bottom: 1px solid rgba(0, 217, 255, 0.2);
	}

	.header-content {
		max-width: 1200px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 2rem;
	}

	/* Brand - Matching Landing Page */
	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		cursor: pointer;
		transition: transform 0.3s ease;
	}

	.nav-brand:hover {
		transform: translateY(-1px);
	}

	.brand-icon {
		width: 48px;
		height: 48px;
		filter: drop-shadow(0 0 10px rgba(0, 217, 255, 0.5));
		transition: filter 0.3s ease;
	}

	.nav-brand:hover .brand-icon {
		filter: drop-shadow(0 0 15px rgba(0, 217, 255, 0.7));
	}

	.brand-name {
		font-size: 1.5rem;
		font-weight: 700;
		color: #ffffff;
		letter-spacing: -0.02em;
	}

	.dashboard-container.light .brand-name {
		color: #000000;
	}

	/* Navigation Menu - Matching Landing Page */
	.nav-menu {
		display: flex;
		gap: 2rem;
		align-items: center;
	}

	.nav-link {
		color: #b8b8b8;
		text-decoration: none;
		font-weight: 500;
		transition: color 0.3s ease;
		position: relative;
	}

	.nav-link:hover,
	.nav-link.active {
		color: #00d9ff;
	}

	.nav-link::after {
		content: '';
		position: absolute;
		bottom: -5px;
		left: 0;
		width: 0;
		height: 2px;
		background: #00d9ff;
		transition: width 0.3s ease;
	}

	.nav-link:hover::after,
	.nav-link.active::after {
		width: 100%;
	}

	.dashboard-container.light .nav-link {
		color: #666666;
	}

	.dashboard-container.light .nav-link:hover,
	.dashboard-container.light .nav-link.active {
		color: #00d9ff;
	}

	/* Navigation Actions */
	.nav-actions {
		display: flex;
		gap: 1rem;
		align-items: center;
	}

	.theme-toggle {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		background: #ffffff;
		border: 2px solid rgba(0, 217, 255, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.1),
			0 1px 3px rgba(0, 0, 0, 0.08);
		flex-shrink: 0;
	}

	.theme-toggle:hover {
		background: #00d9ff;
		border-color: #00d9ff;
		transform: translateY(-3px);
		box-shadow:
			0 8px 16px rgba(0, 217, 255, 0.25),
			0 0 20px rgba(0, 217, 255, 0.3);
	}

	.theme-toggle:active {
		transform: translateY(-1px);
	}

	.dashboard-container.light .theme-toggle {
		background: #ffffff;
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.08),
			0 1px 3px rgba(0, 0, 0, 0.05);
	}

	.dashboard-container.light .theme-toggle:hover {
		background: #00d9ff;
		box-shadow:
			0 8px 16px rgba(0, 217, 255, 0.2),
			0 0 20px rgba(0, 217, 255, 0.25);
		transform: translateY(-3px);
	}

	.theme-icon {
		width: 20px;
		height: 20px;
		color: #000000;
	}

	/* User Profile */
	.profile-dropdown-container {
		position: relative;
	}

	.user-profile-trigger {
		position: relative;
		width: 48px;
		height: 48px;
		border-radius: 50%;
		border: 2px solid rgba(0, 217, 255, 0.4);
		background: #ffffff;
		backdrop-filter: blur(10px);
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		overflow: hidden;
		flex-shrink: 0;
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.1),
			0 1px 3px rgba(0, 0, 0, 0.08),
			inset 0 0 0 1px rgba(255, 255, 255, 0.1);
	}

	.user-profile-trigger:hover {
		border-color: #00d9ff;
		background: #00d9ff;
		box-shadow:
			0 8px 16px rgba(0, 217, 255, 0.25),
			0 4px 8px rgba(0, 217, 255, 0.15),
			0 0 0 1px rgba(0, 217, 255, 0.5),
			0 0 20px rgba(0, 217, 255, 0.3),
			inset 0 1px 0 rgba(255, 255, 255, 0.2);
		transform: translateY(-3px);
	}

	.user-profile-trigger:active {
		transform: translateY(-1px);
	}

	.dashboard-container.light .user-profile-trigger {
		background: #ffffff;
		border-color: rgba(0, 217, 255, 0.4);
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.08),
			0 1px 3px rgba(0, 0, 0, 0.05),
			inset 0 0 0 1px rgba(0, 217, 255, 0.1);
	}

	.dashboard-container.light .user-profile-trigger:hover {
		background: #00d9ff;
		border-color: #00d9ff;
		box-shadow:
			0 8px 16px rgba(0, 217, 255, 0.2),
			0 4px 8px rgba(0, 217, 255, 0.12),
			0 0 0 1px rgba(0, 217, 255, 0.5),
			0 0 20px rgba(0, 217, 255, 0.25),
			inset 0 1px 0 rgba(255, 255, 255, 0.3);
	}

	.user-profile-trigger .avatar-image {
		width: 100%;
		height: 100%;
		object-fit: cover;
		border-radius: 50%;
		display: block;
		transition: transform 0.3s ease;
	}

	.user-profile-trigger:hover .avatar-image {
		transform: scale(1.05);
	}

	.user-profile-trigger .avatar-text {
		color: #000000;
		font-weight: 700;
		font-size: 1.1rem;
		transition: all 0.3s ease;
	}

	.user-profile-trigger:hover .avatar-text {
		color: #000000;
		text-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
	}

	.dashboard-container.light .user-profile-trigger .avatar-text {
		color: #000000;
	}

	/* Profile Dropdown */
	.profile-dropdown-container {
		position: relative;
	}

	@keyframes dropdownSlideIn {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.profile-dropdown {
		position: absolute;
		top: calc(100% + 0.5rem);
		right: 0;
		min-width: 280px;
		background: rgba(0, 0, 0, 0.95);
		backdrop-filter: blur(20px);
		border: 2px solid rgba(0, 217, 255, 0.4);
		border-radius: 12px;
		padding: 1rem;
		box-shadow:
			0 8px 32px rgba(0, 0, 0, 0.4),
			0 0 0 1px rgba(0, 217, 255, 0.2),
			0 0 20px rgba(0, 217, 255, 0.2);
		z-index: 1000;
		animation: dropdownSlideIn 0.3s ease-out;
	}

	.dashboard-container.light .profile-dropdown {
		background: rgba(255, 255, 255, 0.95);
		border-color: rgba(0, 217, 255, 0.5);
		box-shadow:
			0 8px 32px rgba(0, 0, 0, 0.15),
			0 0 0 1px rgba(0, 217, 255, 0.2),
			0 0 20px rgba(0, 217, 255, 0.15);
	}

	.dropdown-user-info {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.75rem;
		border-radius: 8px;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid rgba(0, 217, 255, 0.15);
	}

	.dashboard-container.light .dropdown-user-info {
		background: rgba(0, 217, 255, 0.03);
		border-color: rgba(0, 217, 255, 0.2);
	}

	.dropdown-avatar {
		position: relative;
		width: 56px;
		height: 56px;
		border-radius: 50%;
		overflow: hidden;
		background: #ffffff;
		border: 2px solid rgba(0, 217, 255, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.1),
			0 0 0 1px rgba(0, 217, 255, 0.2);
	}

	.dashboard-container.light .dropdown-avatar {
		background: #ffffff;
		border-color: rgba(0, 217, 255, 0.5);
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.08),
			0 0 0 1px rgba(0, 217, 255, 0.2);
	}

	.dropdown-avatar .avatar-image {
		width: 100%;
		height: 100%;
		object-fit: cover;
		border-radius: 50%;
	}

	.dropdown-avatar .avatar-text {
		color: #000000;
		font-weight: 700;
		font-size: 1.2rem;
	}

	.dropdown-user-details {
		flex: 1;
		min-width: 0;
	}

	.dropdown-name {
		font-size: 0.95rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.25rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.dropdown-email {
		font-size: 0.8rem;
		color: var(--text-secondary);
		opacity: 0.8;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.dropdown-divider {
		height: 1px;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.4), transparent);
		margin: 0.75rem 0;
	}

	.dropdown-logout-button {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		background: rgba(239, 68, 68, 0.1);
		color: #ef4444;
		border: 1px solid rgba(239, 68, 68, 0.2);
		padding: 0.75rem 1rem;
		border-radius: 8px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.3s ease;
		font-size: 0.9rem;
		text-align: left;
	}

	.dropdown-logout-button:hover {
		background: rgba(239, 68, 68, 0.2);
		border-color: rgba(239, 68, 68, 0.4);
		transform: translateX(4px);
	}

	.dashboard-container.light .dropdown-logout-button {
		background: rgba(239, 68, 68, 0.08);
		color: #dc2626;
		border-color: rgba(239, 68, 68, 0.15);
	}

	.dashboard-container.light .dropdown-logout-button:hover {
		background: rgba(239, 68, 68, 0.15);
		border-color: rgba(239, 68, 68, 0.3);
	}

	.logout-icon-svg {
		flex-shrink: 0;
		opacity: 0.9;
	}

	.dropdown-logout-button:hover .logout-icon-svg {
		opacity: 1;
	}

	/* Hero Section */
	.hero-section {
		margin-top: 100px;
		padding: 4rem 0 3rem;
		background: #000000;
		position: relative;
		z-index: 2;
		overflow: hidden;
	}

	.hero-section::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 1px;
		background: linear-gradient(90deg, transparent 0%, #00d9ff 50%, transparent 100%);
		opacity: 0.5;
	}

	.hero-content {
		max-width: 1400px;
		margin: 0 auto;
		padding: 0 2rem;
	}

	.hero-text {
		text-align: center;
	}

	.hero-title {
		font-size: clamp(2.5rem, 6vw, 4rem);
		font-weight: 700;
		margin-bottom: 1.5rem;
		color: var(--text-primary);
		line-height: 1.1;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
	}

	.title-highlight {
		background: linear-gradient(135deg, #00d9ff 0%, #ffffff 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.hero-description {
		font-size: 1.25rem;
		color: var(--text-secondary);
		max-width: 900px;
		margin: 0 auto 2rem;
		line-height: 1.6;
	}

	/* SVG Workflow Art Section */

	
	/* Main Dashboard Content */
	.dashboard-main {
		padding: 4rem 0;
		position: relative;
		z-index: 2;
		background: #000000;
	}

	.dashboard-container.light .dashboard-main {
		background: #ffffff;
	}

	.dashboard-grid {
		max-width: 1400px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 2rem;
		padding: 0 2rem;
	}

	/* Dashboard Cards - Matching Landing Page Feature Cards */
	.dashboard-card {
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		padding: 2.5rem;
		transition: all 0.4s ease;
		position: relative;
		overflow: hidden;
	}

	.dashboard-container.light .dashboard-card {
		background: rgba(255, 255, 255, 0.95);
		border: 1px solid rgba(0, 217, 255, 0.15);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
	}

	.dashboard-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		transition: left 0.6s;
	}

	.dashboard-card:hover::before {
		left: 100%;
	}

	.dashboard-card:hover {
		transform: translateY(-5px);
		border-color: rgba(0, 217, 255, 0.5);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.15);
		background: rgba(0, 0, 0, 0.6);
	}

	.dashboard-container.light .dashboard-card:hover {
		background: rgba(255, 255, 255, 1);
		border-color: rgba(0, 217, 255, 0.3);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.12);
	}

	/* Feature Number Badge */
	.feature-number {
		font-size: 0.9rem;
		font-weight: 700;
		color: #00d9ff;
		margin-bottom: 1.5rem;
		letter-spacing: 0.1em;
		display: block;
	}

	/* Card Title and Description */
	.dashboard-card h3.card-title {
		color: #ffffff;
		font-size: 1.5rem;
		font-weight: 600;
		margin-bottom: 1rem;
		line-height: 1.3;
	}

	.dashboard-container.light .dashboard-card h3.card-title {
		color: #000000;
	}

	.card-description {
		color: #b8b8b8;
		line-height: 1.7;
		margin-bottom: 1.5rem;
		font-size: 1rem;
	}

	.dashboard-container.light .card-description {
		color: #666666;
	}

	/* Feature List */
	.card-features {
		margin-bottom: 2rem;
	}

	.feature-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.feature-list li {
		color: #b8b8b8;
		padding: 0.5rem 0;
		padding-left: 1.5rem;
		position: relative;
		font-size: 0.95rem;
		line-height: 1.6;
	}

	.dashboard-container.light .feature-list li {
		color: #666666;
	}

	.feature-list li::before {
		content: '→';
		position: absolute;
		left: 0;
		color: #00d9ff;
		font-weight: 700;
	}

	/* Status Badge */
	.card-status {
		margin-bottom: 1.5rem;
		display: flex;
		align-items: center;
		justify-content: flex-start;
	}

	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 600;
		transition: all 0.3s ease;
	}

	.status-badge.connected {
		background: rgba(0, 217, 255, 0.1);
		color: #00d9ff;
		border: 1px solid rgba(0, 217, 255, 0.3);
	}

	.dashboard-container.light .status-badge.connected {
		background: rgba(0, 217, 255, 0.08);
		color: #00a0c0;
	}

	.status-badge.disconnected {
		background: rgba(184, 184, 184, 0.1);
		color: #b8b8b8;
		border: 1px solid rgba(184, 184, 184, 0.3);
	}

	.dashboard-container.light .status-badge.disconnected {
		background: rgba(100, 100, 100, 0.08);
		color: #666666;
	}

	.status-icon {
		font-size: 1rem;
		font-weight: 700;
	}

	/* Card Action Button - Matching Landing Page Primary Button */
	.card-action-button {
		width: 100%;
		padding: 1.2rem 2rem;
		border: none;
		border-radius: 8px;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		text-decoration: none;
		display: flex;
		align-items: center;
		justify-content: space-between;
		position: relative;
		background: #ffffff;
		color: #000000;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
	}

	.dashboard-container.light .card-action-button {
		background: #00d9ff;
		color: #000000;
		box-shadow:
			0 8px 25px rgba(0, 217, 255, 0.3),
			0 4px 12px rgba(0, 217, 255, 0.15);
	}

	.card-action-button:hover {
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
		background: #00d9ff;
		color: #000000;
	}

	.dashboard-container.light .card-action-button:hover {
		background: #33e3ff;
		box-shadow:
			0 12px 32px rgba(0, 217, 255, 0.4),
			0 6px 16px rgba(0, 217, 255, 0.25);
	}

	.card-action-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		transform: none;
	}

	.card-action-button.loading {
		background: rgba(0, 217, 255, 0.2);
		color: #00d9ff;
	}

	.button-text {
		flex: 1;
		text-align: center;
		font-weight: 600;
	}

	.button-arrow {
		font-size: 1.25rem;
		transition: transform 0.3s ease;
	}

	.card-action-button:hover .button-arrow {
		transform: translateX(5px);
	}

	.button-spinner {
		width: 16px;
		height: 16px;
		border: 2px solid rgba(0, 217, 255, 0.3);
		border-radius: 50%;
		border-top-color: #00d9ff;
		animation: spin 1s linear infinite;
	}

	@keyframes pulse-enhanced {
		0%,
		100% {
			opacity: 0.6;
			transform: translate(-50%, -50%) scale(1);
		}
		50% {
			opacity: 1;
			transform: translate(-50%, -50%) scale(1.3);
		}
	}

	.card-title {
		font-size: 1.75rem;
		font-weight: 700;
		background: linear-gradient(135deg, #4a9eff 0%, #66d9ff 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		margin-bottom: 0.5rem;
		line-height: 1.2;
		letter-spacing: -0.02em;
	}

	.dashboard-container.light .card-title {
		background: linear-gradient(135deg, #00d9ff 0%, #00a0c0 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.status-dot {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		position: relative;
		animation: pulse-dot 2s ease-in-out infinite;
	}

	@keyframes pulse-dot {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.2);
		}
	}

	@keyframes pulse-ring {
		0%,
		100% {
			transform: scale(1);
			opacity: 1;
		}
		50% {
			transform: scale(1.3);
			opacity: 0.7;
		}
	}

	/* Responsive Design */
	@media (max-width: 768px) {
		.header-content {
			padding: 0 1rem;
		}

		.hero-section {
			padding: 3rem 1rem 1rem;
		}

		.dashboard-main {
			padding: 2rem 1rem;
		}

		.dashboard-grid {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}
	}

	@media (max-width: 480px) {
		.brand-name {
			font-size: 1.2rem;
		}

		.hero-title {
			font-size: 2rem;
		}

		.hero-description {
			font-size: 1rem;
		}

		.dashboard-grid {
			grid-template-columns: 1fr;
			gap: 1rem;
		}
	}

	/* Animations for better UX */
	.dashboard-card,
	.nav-link,
	.theme-toggle,
	.user-profile-trigger {
		transform-origin: center;
	}

	/* Disabled state */
</style>
