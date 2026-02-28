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
				// Check if this is a GitHub account connection (not organization discovery)
				if (state === 'connect_github') {
					message = 'Connecting your GitHub account...';

					const result = await githubClient.processGitHubConnectionCallback(code, state);

					if (result.success) {
						const linkedCount = result.linked_organizations?.length || 0;
						message = `GitHub account connected! ${linkedCount > 0 ? `Auto-linked to ${linkedCount} organization(s).` : ''}`;

						console.log('✅ GitHub connected:', result.github_username);
						console.log('🔗 Linked organizations:', result.linked_organizations);

						// Redirect to dashboard after short delay
						setTimeout(() => {
							goto('/dashboard?github_connected=true');
						}, 2000);

						loading = false;
						return;
					} else {
						throw new Error(result.error || 'Failed to connect GitHub account');
					}
				}

				// Original organization discovery flow
				message = 'Discovering organizations where you can install the GitHub App...';

				const result = await githubClient.processOrganizationCallback(code, state);

				if (result.success) {
					organizations = result.organizations;
					message = `Found ${result.total_count} organizations where you can install the GitHub App`;
					loading = false;

					// Aggressive prefetching for instant navigation
					console.log('🚀 Starting ultra-aggressive organization workspace prefetching');

					// Prefetch workspace data for all installed organizations in background
					const installedOrgs = organizations.filter((org) => org.app_installed);
					const uninstalledOrgs = organizations.filter((org) => !org.app_installed);

					// Immediate prefetch for first 2 installed orgs
					installedOrgs.slice(0, 2).forEach((org) => {
						githubClient.preloadOrganizationWorkspace(org.login);
					});

					// Background prefetch for remaining installed orgs (with delay to avoid API rate limits)
					installedOrgs.slice(2).forEach((org, index) => {
						setTimeout(
							() => {
								githubClient.preloadOrganizationWorkspace(org.login);
							},
							(index + 1) * 500
						); // Stagger requests
					});

					// Pre-generate installation URLs for uninstalled orgs for faster clicks
					console.log('🚀 Pre-generating installation URLs for faster app installation');
					uninstalledOrgs.slice(0, 3).forEach((org) => {
						githubClient.generateInstallationUrl(org.login).then((result) => {
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
			console.log(
				`🔍 Verification check - success: ${verification.success}, installed: ${verification.installed}`
			);

			if (verification.success && verification.installed) {
				// Installation verified, proceed to workspace
				console.log(`✅ Verification passed for ${org.login}, navigating to workspace`);
				goto(`/github/workspace/${org.login}`);
			} else {
				// Installation no longer exists
				console.warn(`⚠️ App no longer installed in ${org.login}`);
				console.log(
					`❌ Verification failed for ${org.login} - success: ${verification.success}, installed: ${verification.installed}`
				);

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

<div class="discovery-page {darkMode ? 'dark' : 'light'}">
	<!-- Header Navigation -->
	<nav class="dashboard-header">
		<div class="header-content">
			<a href="/" class="nav-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
				<span class="brand-name">WithOps</span>
			</a>
			<div class="nav-menu">
				<a href="/dashboard" class="nav-link">Overview</a>
				<a href="/organizations" class="nav-link">Organizations</a>
			</div>
			<div class="nav-actions">
				<!-- spacer -->
			</div>
		</div>
	</nav>

	<!-- Technical Breadcrumb Bar -->
	<div class="technical-bar">
		<span class="breadcrumb-item">WithOps</span>
		<span class="breadcrumb-sep">/</span>
		<span class="breadcrumb-item">Organizations</span>
		<span class="breadcrumb-sep">/</span>
		<span class="breadcrumb-item active">Discovery</span>
		<div class="system-status">
			<div class="status-pulse"></div>
			SCANNING
		</div>
	</div>

	<div class="page-content">
		<main class="page-main">
			{#if loading}
				<!-- Loading State -->
				<div class="loader-view">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="progress-bar">
						<div class="progress-fill"></div>
					</div>
					<div class="loader-text">{message.toUpperCase()}</div>
				</div>
			{:else if error}
				<!-- Error State -->
				<div class="state-card">
					<div class="state-indicator error">
						<svg
							width="22"
							height="22"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.958-.833-2.728 0L4.186 14.5c-.77.833.192 2.5 1.732 2.5z"
							/>
						</svg>
					</div>
					<h2 class="state-title">Discovery Error</h2>
					<p class="state-description">{error}</p>
					<div class="state-actions">
						<button on:click={handleOrganizationDiscovery} class="btn btn-primary">
							<svg
								width="14"
								height="14"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								stroke-width="2"
							>
								<path
									d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
								/>
							</svg>
							Retry
							<span class="button-arrow">→</span>
						</button>
						<button on:click={goToDashboard} class="btn btn-outline">
							<svg
								width="14"
								height="14"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								stroke-width="2"
							>
								<path d="M10 19l-7-7m0 0l7-7m-7 7h18" />
							</svg>
							Back to Dashboard
						</button>
					</div>
				</div>
			{:else if organizations.length > 0}
				<!-- Organizations List -->
				<header class="view-header">
					<div class="title-group">
						<h1>Select Organization</h1>
						<p>{message}</p>
					</div>
					<button on:click={goToDashboard} class="btn btn-outline">
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
						Dashboard
					</button>
				</header>

				<!-- App Notice -->
				<div class="notice-bar">
					<svg
						width="14"
						height="14"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" />
					</svg>
					<span
						>You will install the <strong>WithOps GitHub App</strong> into the selected organization</span
					>
				</div>

				<!-- Organizations Grid -->
				<div class="org-grid">
					{#each organizations as org}
						<div class="org-card">
							<div class="org-card-top">
								<img src={org.avatar_url} alt="{org.login} avatar" class="org-avatar" />
								<div class="org-meta">
									<h3 class="org-name">{org.login}</h3>
									<div class="org-badges">
										{#if org.app_installed}
											<div class="status-tag connected">
												<div class="tag-dot"></div>
												INSTALLED
											</div>
											{#if org.installed_by_you}
												<div class="status-tag owner">
													<div class="tag-dot"></div>
													OWNER
												</div>
											{:else if org.auto_linked}
												<div class="status-tag shared">
													<div class="tag-dot"></div>
													SHARED
												</div>
											{/if}
										{:else}
											<div class="status-tag pending">
												<div class="tag-dot"></div>
												NOT INSTALLED
											</div>
										{/if}
									</div>
								</div>
							</div>

							{#if org.description}
								<p class="org-description">{org.description}</p>
							{/if}

							<div class="org-actions">
								{#if org.app_installed}
									<button
										on:click={() => viewWorkspace(org)}
										on:mouseenter={() => githubClient.preloadOrganizationWorkspace(org.login)}
										disabled={org.verifying}
										class="btn btn-primary btn-full"
									>
										{#if org.verifying}
											<span class="spinner"></span>
											<span>Verifying...</span>
										{:else}
											<span>Open Workspace</span>
											<span class="button-arrow">→</span>
										{/if}
									</button>
								{:else}
									<button
										on:click={() => installAppInOrganization(org)}
										disabled={installingApp && selectedOrg?.login === org.login}
										class="btn btn-secondary btn-full"
									>
										{#if installingApp && selectedOrg?.login === org.login}
											<span class="spinner"></span>
											<span>Redirecting...</span>
										{:else}
											<span>Install GitHub App</span>
											<span class="button-arrow">→</span>
										{/if}
									</button>
								{/if}
							</div>

							{#if !org.app_installed}
								<div class="install-info">
									<span class="info-label">NEXT STEPS</span>
									<ul class="info-steps">
										<li>Redirect to GitHub for app installation</li>
										<li>Grant access to {org.login} only</li>
										<li>Return to access your workspace</li>
									</ul>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{:else}
				<!-- No Organizations Found -->
				<div class="state-card">
					<div class="state-indicator empty">
						<svg
							width="22"
							height="22"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
							/>
						</svg>
					</div>
					<h2 class="state-title">No Organizations</h2>
					<p class="state-description">
						No GitHub organizations found with installation permissions. Ensure you have admin or
						owner access.
					</p>
					<div class="state-actions">
						<button on:click={goToDashboard} class="btn btn-primary">
							Back to Dashboard
							<span class="button-arrow">→</span>
						</button>
					</div>
				</div>
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

	.discovery-page.dark {
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

	.discovery-page.light {
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

	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	.discovery-page {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
		overflow-x: hidden;
	}

	/* Grid Backdrop */
	.discovery-page::before {
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

	.nav-link:hover {
		color: var(--text-primary);
	}

	.nav-actions {
		display: flex;
		align-items: center;
	}

	/* Technical Bar */
	.technical-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 0 2rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		height: 40px;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.breadcrumb-sep {
		color: var(--border-focus);
	}
	.breadcrumb-item.active {
		color: var(--accent);
	}

	.system-status {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 0.5rem;
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

	/* Page Content */
	.page-content {
		position: relative;
		z-index: 10;
		padding-bottom: 5rem;
	}

	.page-main {
		max-width: 1440px;
		margin: 0 auto;
		padding: 3rem 2rem;
	}

	/* View Header */
	.view-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		margin-bottom: 2rem;
	}

	.title-group h1 {
		font-size: 1.75rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		margin-bottom: 0.5rem;
	}

	.title-group p {
		color: var(--text-secondary);
		font-size: 0.875rem;
		max-width: 500px;
		line-height: 1.5;
	}

	/* Notice Bar */
	.notice-bar {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		padding: 0.75rem 1rem;
		background: var(--accent-soft);
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 0.8125rem;
		color: var(--text-secondary);
		margin-bottom: 2rem;
	}

	.notice-bar svg {
		color: var(--accent);
		flex-shrink: 0;
	}
	.notice-bar strong {
		color: var(--text-primary);
	}

	/* Loading View */
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

	.progress-bar {
		width: 200px;
		height: 2px;
		background: var(--border);
		border-radius: 4px;
		overflow: hidden;
		margin-bottom: 1.5rem;
	}

	.progress-fill {
		height: 100%;
		background: var(--accent);
		width: 40%;
		animation: load 1.5s ease-in-out infinite;
	}

	@keyframes load {
		0% {
			transform: translateX(-100%);
			width: 20%;
		}
		50% {
			width: 50%;
		}
		100% {
			transform: translateX(300%);
			width: 20%;
		}
	}

	.loader-text {
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	/* State Card (Error / Empty) */
	.state-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 8rem 2rem;
		text-align: center;
		gap: 1.25rem;
	}

	.state-indicator {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.state-indicator.error {
		border: 1px solid rgba(239, 68, 68, 0.15);
		background: rgba(239, 68, 68, 0.05);
		color: var(--error);
	}

	.state-indicator.empty {
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--text-muted);
	}

	.state-title {
		font-size: 1.125rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}

	.state-description {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		line-height: 1.6;
		max-width: 400px;
	}

	.state-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	/* Organization Grid */
	.org-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
		gap: 1.5rem;
	}

	/* Organization Card */
	.org-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		transition: all 0.2s var(--ease-premium);
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
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
		width: 44px;
		height: 44px;
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
		font-size: 0.9375rem;
		margin-bottom: 0.375rem;
	}

	.org-badges {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		flex-wrap: wrap;
	}

	/* Status Tags */
	.status-tag {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.25rem 0.625rem;
		border-radius: 6px;
		font-size: 0.6875rem;
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

	.status-tag.owner {
		color: var(--accent);
		border: 1px solid rgba(0, 173, 239, 0.1);
		opacity: 0.9;
	}

	.status-tag.shared {
		color: var(--text-secondary);
		border: 1px solid var(--border);
		opacity: 0.8;
	}

	.status-tag.pending {
		color: var(--text-muted);
		border: 1px solid var(--border);
		opacity: 0.7;
	}

	.tag-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: currentColor;
	}

	.org-description {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	.org-actions {
		display: flex;
		gap: 0.5rem;
	}

	/* Install Info */
	.install-info {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.875rem 1rem;
	}

	.info-label {
		display: block;
		font-family: var(--font-mono);
		font-size: 0.5625rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		margin-bottom: 0.5rem;
	}

	.info-steps {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.info-steps li {
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin-bottom: 0.25rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.info-steps li::before {
		content: '';
		width: 3px;
		height: 3px;
		background: var(--text-muted);
		border-radius: 50%;
		flex-shrink: 0;
	}

	/* Buttons */
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem 1.125rem;
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
		text-decoration: none;
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

	.btn-secondary {
		background: var(--bg-surface-alt);
		border-color: var(--border);
		color: var(--text-primary);
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

	.btn-full {
		width: 100%;
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		transform: none;
	}

	.button-arrow {
		transition: transform 0.15s;
	}

	.btn:hover:not(:disabled) .button-arrow {
		transform: translateX(3px);
	}

	/* Spinner */
	.spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Responsive */
	@media (max-width: 768px) {
		.page-main {
			padding: 2rem 1rem;
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

		.state-actions {
			flex-direction: column;
			width: 100%;
		}

		.state-actions .btn {
			width: 100%;
		}
	}
</style>
