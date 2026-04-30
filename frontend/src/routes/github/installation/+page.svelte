<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { githubClient } from '$lib/github.js';
	import { isDarkMode } from '$lib/stores.js';

	let loading = true;
	let error = null;
	let message = 'Processing GitHub App installation...';
	let installationResult = null;

	$: darkMode = $isDarkMode;

	onMount(async () => {
		await handleInstallationCallback();
	});

	async function handleInstallationCallback() {
		try {
			loading = true;
			error = null;

			// Get URL parameters from GitHub App installation redirect
			const params = $page.url.searchParams;
			const installation_id = params.get('installation_id');
			const setup_action = params.get('setup_action');
			const state = params.get('state');

			console.log('GitHub App installation callback params:', {
				installation_id,
				setup_action,
				state
			});

			if (installation_id && setup_action) {
				message = 'Completing GitHub App installation...';

				const result = await githubClient.processInstallationCallback(
					installation_id,
					setup_action,
					state
				);

				if (result.success) {
					installationResult = result;
					message = `GitHub App successfully installed in ${result.organization.login}`;
					loading = false;

					// Immediately start prefetching workspace data for instant access
					console.log('🚀 Prefetching workspace data for instant navigation');
					githubClient.preloadOrganizationWorkspace(result.organization.login);

					// Reduce redirect delay since workspace is being prefetched
					setTimeout(() => {
						goto(`/github/workspace/${result.organization.login}`);
					}, 1500); // Reduced from 2000ms
				} else {
					throw new Error(result.error);
				}
			} else {
				throw new Error('Missing required parameters from GitHub App installation');
			}
		} catch (err) {
			console.error('Installation callback error:', err);
			error = err.message || 'Failed to process GitHub App installation';
			loading = false;
		}
	}

	function goBack() {
		goto('/');
	}
</script>

<svelte:head>
	<title>GitHub App Installation - WithOps</title>
</svelte:head>

<div class="install-page {darkMode ? 'dark' : 'light'}">
	<!-- Grid Backdrop -->
	<div class="grid-backdrop"></div>

	<div class="page-shell">
		{#if loading}
			<!-- Loading State -->
			<div class="state-container">
				<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
				<div class="progress-bar">
					<div class="progress-fill"></div>
				</div>
				<div class="status-label">{message.toUpperCase()}</div>
				<p class="status-sub">Configuring workspace environment...</p>
			</div>
		{:else if error}
			<!-- Error State -->
			<div class="state-container">
				<div class="state-indicator error">
					<svg
						width="22"
						height="22"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</div>
				<h2 class="state-title">Installation Failed</h2>
				<p class="state-description">{error}</p>
				<button on:click={goBack} class="btn btn-primary">
					Back to Dashboard
					<span class="button-arrow">→</span>
				</button>
			</div>
		{:else if installationResult}
			<!-- Success State -->
			<div class="state-container">
				<div class="state-indicator success">
					<svg
						width="22"
						height="22"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
					</svg>
				</div>
				<h2 class="state-title">Installation Complete</h2>
				<p class="state-description">{message}</p>

				<div class="org-result-card">
					<img
						src={installationResult.organization.avatar_url}
						alt={installationResult.organization.login}
						class="org-avatar"
					/>
					<div class="org-result-meta">
						<span class="org-result-name">{installationResult.organization.login}</span>
						<span class="org-result-id">ID: {installationResult.installation_id}</span>
					</div>
					<div class="status-tag connected">
						<div class="tag-dot"></div>
						ACTIVE
					</div>
				</div>

				<div class="redirect-notice">
					<div class="spinner"></div>
					<span class="redirect-text">REDIRECTING TO WORKSPACE...</span>
				</div>
			</div>
		{/if}
	</div>

	<!-- Footer -->
	<div class="page-footer">
		<svg
			width="14"
			height="14"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
			stroke-width="1.5"
			style="opacity:0.3"
		>
			<rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0110 0v4" />
		</svg>
		<span>SECURE INSTALLATION</span>
	</div>
</div>

<style>
	/* ============================================
       MATTE ENGINEERING DESIGN SYSTEM
       ============================================ */
	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
	}

	.install-page.dark {
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
	}

	.install-page.light {
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
	}

	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	.install-page {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		position: relative;
		overflow: hidden;
		transition: background 0.3s ease;
	}

	/* Grid Backdrop */
	.grid-backdrop {
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

	/* Page Shell */
	.page-shell {
		position: relative;
		z-index: 10;
		width: 100%;
		max-width: 460px;
		padding: 0 1.5rem;
	}

	/* State Container */
	.state-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: 1.25rem;
	}

	/* Loader */
	.loader-icon {
		width: 44px;
		height: 44px;
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
		width: 180px;
		height: 2px;
		background: var(--border);
		border-radius: 4px;
		overflow: hidden;
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

	.status-label {
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	.status-sub {
		font-size: 0.8125rem;
		color: var(--text-secondary);
	}

	/* State Indicators */
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

	.state-indicator.success {
		border: 1px solid rgba(16, 185, 129, 0.15);
		background: rgba(16, 185, 129, 0.05);
		color: var(--success);
	}

	.state-title {
		font-size: 1.25rem;
		font-weight: 700;
		letter-spacing: -0.02em;
	}

	.state-description {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		line-height: 1.6;
		max-width: 360px;
	}

	/* Organization Result Card */
	.org-result-card {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		width: 100%;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1rem 1.25rem;
		margin-top: 0.5rem;
	}

	.org-avatar {
		width: 36px;
		height: 36px;
		border-radius: 8px;
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
	}

	.org-result-meta {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.125rem;
	}

	.org-result-name {
		font-weight: 600;
		font-size: 0.875rem;
	}

	.org-result-id {
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		color: var(--text-muted);
	}

	/* Status Tag */
	.status-tag {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.25rem 0.625rem;
		border-radius: 6px;
		font-size: 0.625rem;
		font-weight: 600;
		font-family: var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.status-tag.connected {
		color: var(--success);
		border: 1px solid rgba(16, 185, 129, 0.1);
	}

	.tag-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: currentColor;
	}

	/* Redirect Notice */
	.redirect-notice {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		margin-top: 0.75rem;
	}

	.redirect-text {
		font-family: var(--font-mono);
		font-size: 0.625rem;
		color: var(--text-muted);
		letter-spacing: 0.08em;
	}

	/* Spinner */
	.spinner {
		width: 12px;
		height: 12px;
		border: 1.5px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Button */
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem 1.25rem;
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
		margin-top: 0.5rem;
	}

	.btn-primary {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
	}

	.btn-primary:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.button-arrow {
		transition: transform 0.15s;
	}

	.btn:hover .button-arrow {
		transform: translateX(3px);
	}

	/* Footer */
	.page-footer {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 10;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 1rem;
		font-family: var(--font-mono);
		font-size: 0.5625rem;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		text-transform: uppercase;
		border-top: 1px solid var(--border);
		background: var(--bg-app);
	}

	/* Responsive */
	@media (max-width: 480px) {
		.page-shell {
			padding: 0 1rem;
		}
		.org-result-card {
			padding: 0.875rem 1rem;
		}
	}
</style>
