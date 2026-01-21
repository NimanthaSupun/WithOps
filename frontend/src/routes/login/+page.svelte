<script>
	import { getAuthClient } from '$lib/auth';
	import { onMount } from 'svelte';
	import { isDarkMode } from '$lib/stores.js';

	let loading = false;
	let error = null;
	let darkMode = false;

	// Subscribe to the global theme store
	isDarkMode.subscribe((value) => {
		darkMode = value;
	});

	async function login() {
		try {
			loading = true;
			error = null;
			const client = await getAuthClient();
			await client.loginWithRedirect();
		} catch (err) {
			error = err.message;
			console.error('Login error:', err);
		} finally {
			loading = false;
		}
	}

	// Toggle theme function
	function toggleTheme() {
		isDarkMode.toggle();
	}

	// Check if user is already authenticated
	onMount(async () => {
		try {
			// Initialize theme
			isDarkMode.init();

			const client = await getAuthClient();
			const isAuthenticated = await client.isAuthenticated();
			if (isAuthenticated) {
				// Redirect to dashboard or home page
				window.location.href = '/';
			}
		} catch (err) {
			console.error('Auth check error:', err);
		}
	});
</script>

<svelte:head>
	<title>Sign In - WithOps DevSecOps Platform</title>
</svelte:head>

<div class="login-container {darkMode ? 'dark' : 'light'}">
	<!-- Background Effects -->
	<div class="login-background">
		<div class="login-glow-1"></div>
		<div class="login-glow-2"></div>
		<div class="login-particles"></div>
		<div class="github-pattern"></div>
	</div>

	<!-- Theme Toggle -->
	<button on:click={toggleTheme} class="theme-toggle" title="Toggle theme">
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

	<!-- Main Content -->
	<div class="login-content">
		<!-- Header with Logo -->
		<div class="login-header">
			<div class="brand-section">
				<div class="brand-icon-wrapper">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<div class="brand-glow"></div>
				</div>
				<div class="brand-text">
					<span class="brand-name">WithOps</span>
					<span class="brand-subtitle">DevSecOps Platform</span>
				</div>
			</div>

			<div class="welcome-text">
				<h1 class="welcome-title">Welcome Back</h1>
				<p class="welcome-description">
					Sign in to your secure DevSecOps workspace and continue building with confidence.
				</p>
			</div>
		</div>

		<!-- Login Card -->
		<div class="login-card">
			<!-- Error Message -->
			{#if error}
				<div class="error-alert">
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
						<h4>Authentication Error</h4>
						<p>{error}</p>
					</div>
				</div>
			{/if}

			<!-- Auth0 Login Section -->
			<div class="auth-section">
				<div class="auth-provider">
					<div class="provider-header">
						<div class="auth0-logo">
							<svg viewBox="0 0 24 24" fill="currentColor">
								<path
									d="M21.98 7.448L19.62 0H4.347L2.02 7.448c-1.352 4.312.03 9.206 3.815 12.015L12.017 24l6.183-4.537c3.785-2.809 5.167-7.703 3.815-12.015z"
								/>
							</svg>
						</div>
						<div class="provider-info">
							<h3>Enterprise Authentication</h3>
							<p>Powered by Auth0 - Industry-leading security</p>
						</div>
					</div>

					<button on:click={login} disabled={loading} class="auth-button">
						{#if loading}
							<div class="loading-spinner">
								<div class="spinner-ring"></div>
								<div class="spinner-ring"></div>
							</div>
							<span>Redirecting to Auth0...</span>
						{:else}
							<div class="auth-icon">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
									/>
								</svg>
							</div>
							<span>Continue with Auth0</span>
							<div class="auth-arrow">→</div>
						{/if}
					</button>
				</div>

				<!-- Security Features -->
				<div class="security-features">
					<div class="feature-item">
						<div class="feature-icon">🔐</div>
						<span>Multi-factor Authentication</span>
					</div>
					<div class="feature-item">
						<div class="feature-icon">🛡️</div>
						<span>Enterprise SSO Support</span>
					</div>
					<div class="feature-item">
						<div class="feature-icon">⚡</div>
						<span>Instant Access</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Platform Features -->
		<div class="platform-features">
			<h3>What you'll get access to:</h3>
			<div class="features-grid">
				<div class="platform-feature">
					<div class="platform-icon github">
						<svg fill="currentColor" viewBox="0 0 24 24">
							<path
								d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
							/>
						</svg>
					</div>
					<span>GitHub Integration</span>
				</div>
				<div class="platform-feature">
					<div class="platform-icon security">🔍</div>
					<span>Security Scanning</span>
				</div>
				<div class="platform-feature">
					<div class="platform-icon workflow">⚙️</div>
					<span>Workflow Automation</span>
				</div>
				<div class="platform-feature">
					<div class="platform-icon analytics">📊</div>
					<span>Analytics Dashboard</span>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div class="login-footer">
			<div class="security-notice">
				<div class="security-icon">🔒</div>
				<span>Your data is protected with enterprise-grade security</span>
			</div>
		</div>
	</div>
</div>

<style>
	/* Global Variables */
	.login-container {
		--bg-primary: #000000;
		--text-primary: #ffffff;
		--text-secondary: #b8b8b8;
		--primary-color: #00d9ff;
		--error-color: #ef4444;
	}

	.login-container.light {
		--bg-primary: #ffffff;
		--text-primary: #000000;
		--text-secondary: #666666;
		--primary-color: #00d9ff;
		--error-color: #dc2626;
	}

	/* Main Container */
	.login-container {
		position: relative;
		min-height: 100vh;
		background: var(--bg-primary);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		font-family:
			'Inter',
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			Roboto,
			sans-serif;
	}

	/* Background Effects - Minimal */
	.login-background {
		display: none;
	}

	.login-glow-1,
	.login-glow-2,
	.login-particles,
	.github-pattern {
		display: none;
	}

	/* Theme Toggle */
	.theme-toggle {
		position: fixed;
		top: 2rem;
		right: 2rem;
		z-index: 1000;
		width: 48px;
		height: 48px;
		background: #ffffff;
		backdrop-filter: blur(10px);
		border: 2px solid rgba(0, 217, 255, 0.4);
		border-radius: 50%;
		color: #000000;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.1),
			0 1px 3px rgba(0, 0, 0, 0.08),
			inset 0 0 0 1px rgba(255, 255, 255, 0.1);
	}

	.theme-toggle:hover {
		background: #00d9ff;
		border-color: #00d9ff;
		box-shadow:
			0 8px 16px rgba(0, 217, 255, 0.25),
			0 4px 8px rgba(0, 217, 255, 0.15),
			0 0 0 1px rgba(0, 217, 255, 0.5),
			0 0 20px rgba(0, 217, 255, 0.3),
			inset 0 1px 0 rgba(255, 255, 255, 0.2);
		transform: translateY(-3px);
	}

	.theme-toggle:active {
		transform: translateY(-1px);
	}

	.login-container.light .theme-toggle {
		background: #ffffff;
		border-color: rgba(0, 217, 255, 0.4);
		color: #000000;
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.08),
			0 1px 3px rgba(0, 0, 0, 0.05),
			inset 0 0 0 1px rgba(0, 217, 255, 0.1);
	}

	.login-container.light .theme-toggle:hover {
		background: #00d9ff;
		border-color: #00d9ff;
		box-shadow:
			0 8px 16px rgba(0, 217, 255, 0.2),
			0 4px 8px rgba(0, 217, 255, 0.12),
			0 0 0 1px rgba(0, 217, 255, 0.5),
			0 0 20px rgba(0, 217, 255, 0.25),
			inset 0 1px 0 rgba(255, 255, 255, 0.3);
	}

	.theme-icon {
		width: 22px;
		height: 22px;
	}

	/* Main Content */
	.login-content {
		position: relative;
		z-index: 2;
		width: 100%;
		max-width: 500px;
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	/* Header */
	.login-header {
		text-align: center;
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.brand-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	.brand-icon-wrapper {
		position: relative;
		width: 80px;
		height: 80px;
	}

	.brand-icon {
		width: 80px;
		height: 80px;
		filter: drop-shadow(0 0 10px rgba(0, 217, 255, 0.5));
		transition: filter 0.3s ease;
	}

	.brand-icon:hover {
		filter: drop-shadow(0 0 15px rgba(0, 217, 255, 0.7));
	}

	.brand-glow {
		display: none;
	}

	.brand-text {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.brand-name {
		font-size: 2.5rem;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1;
		margin-bottom: 0.5rem;
	}

	.brand-subtitle {
		font-size: 1rem;
		color: var(--text-secondary);
		opacity: 0.8;
		letter-spacing: 0.1em;
		font-weight: 500;
	}

	.welcome-text {
		max-width: 400px;
		margin: 0 auto;
	}

	.welcome-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
		line-height: 1.2;
	}

	.welcome-description {
		font-size: 1rem;
		color: var(--text-secondary);
		line-height: 1.6;
		opacity: 0.9;
	}

	/* Login Card */
	.login-card {
		background: rgba(0, 0, 0, 0.3);
		backdrop-filter: blur(20px);
		border: 2px solid rgba(0, 217, 255, 0.3);
		border-radius: 16px;
		padding: 2.5rem;
		box-shadow:
			0 8px 32px rgba(0, 0, 0, 0.4),
			0 0 0 1px rgba(0, 217, 255, 0.1);
	}

	.login-container.light .login-card {
		background: rgba(255, 255, 255, 0.9);
		border-color: rgba(0, 217, 255, 0.4);
		box-shadow:
			0 8px 32px rgba(0, 0, 0, 0.1),
			0 0 0 1px rgba(0, 217, 255, 0.15);
	}

	/* Error Alert */
	.error-alert {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1rem 1.25rem;
		background: rgba(255, 71, 87, 0.1);
		border: 1px solid rgba(255, 71, 87, 0.2);
		border-radius: 12px;
		margin-bottom: 1.5rem;
	}

	.error-icon {
		width: 20px;
		height: 20px;
		color: var(--error-color);
		flex-shrink: 0;
		margin-top: 0.1rem;
	}

	.error-content h4 {
		color: var(--error-color);
		font-weight: 600;
		margin-bottom: 0.25rem;
		font-size: 0.9rem;
	}

	.error-content p {
		color: var(--text-secondary);
		font-size: 0.85rem;
		margin: 0;
	}

	/* Auth Section */
	.auth-section {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.auth-provider {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.provider-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid rgba(0, 217, 255, 0.2);
	}

	.auth0-logo {
		width: 40px;
		height: 40px;
		background: #ffffff;
		border: 2px solid rgba(0, 217, 255, 0.4);
		border-radius: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #000000;
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.1),
			0 0 0 1px rgba(0, 217, 255, 0.2);
	}

	.login-container.light .auth0-logo {
		background: #ffffff;
		border-color: rgba(0, 217, 255, 0.5);
	}

	.auth0-logo svg {
		width: 24px;
		height: 24px;
	}

	.provider-info h3 {
		color: var(--text-primary);
		font-weight: 600;
		margin-bottom: 0.25rem;
		font-size: 1rem;
	}

	.provider-info p {
		color: var(--text-secondary);
		font-size: 0.85rem;
		margin: 0;
		opacity: 0.8;
	}

	/* Auth Button */
	.auth-button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 1.25rem 2rem;
		background: #ffffff;
		color: #000000;
		border: 2px solid rgba(0, 217, 255, 0.4);
		border-radius: 8px;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		position: relative;
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.1),
			0 1px 3px rgba(0, 0, 0, 0.08),
			inset 0 0 0 1px rgba(255, 255, 255, 0.1);
	}

	.auth-button::before {
		display: none;
	}

	.auth-button:hover:not(:disabled) {
		background: #00d9ff;
		border-color: #00d9ff;
		color: #000000;
		box-shadow:
			0 8px 16px rgba(0, 217, 255, 0.25),
			0 4px 8px rgba(0, 217, 255, 0.15),
			0 0 0 1px rgba(0, 217, 255, 0.5),
			0 0 20px rgba(0, 217, 255, 0.3),
			inset 0 1px 0 rgba(255, 255, 255, 0.2);
		transform: translateY(-3px);
	}

	.auth-button:active:not(:disabled) {
		transform: translateY(-1px);
	}

	.auth-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		transform: none;
	}

	.login-container.light .auth-button {
		background: #ffffff;
		border-color: rgba(0, 217, 255, 0.4);
		color: #000000;
		box-shadow:
			0 4px 6px rgba(0, 0, 0, 0.08),
			0 1px 3px rgba(0, 0, 0, 0.05),
			inset 0 0 0 1px rgba(0, 217, 255, 0.1);
	}

	.login-container.light .auth-button:hover:not(:disabled) {
		background: #00d9ff;
		border-color: #00d9ff;
		box-shadow:
			0 8px 16px rgba(0, 217, 255, 0.2),
			0 4px 8px rgba(0, 217, 255, 0.12),
			0 0 0 1px rgba(0, 217, 255, 0.5),
			0 0 20px rgba(0, 217, 255, 0.25),
			inset 0 1px 0 rgba(255, 255, 255, 0.3);
	}

	.auth-icon {
		width: 20px;
		height: 20px;
	}

	.auth-arrow {
		font-size: 1.2rem;
		transition: transform 0.3s ease;
	}

	.auth-button:hover .auth-arrow {
		transform: translateX(4px);
	}

	/* Loading Spinner */
	.loading-spinner {
		position: relative;
		width: 20px;
		height: 20px;
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

	.spinner-ring:nth-child(2) {
		animation-delay: -0.5s;
		opacity: 0.7;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}

	/* Security Features */
	.security-features {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		padding-top: 1rem;
		border-top: 1px solid rgba(0, 217, 255, 0.2);
	}

	.feature-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		color: var(--text-secondary);
		font-size: 0.9rem;
	}

	.feature-icon {
		font-size: 1.1rem;
	}

	/* Platform Features */
	.platform-features {
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		padding: 1.5rem;
	}

	.login-container.light .platform-features {
		background: rgba(0, 217, 255, 0.03);
		border-color: rgba(0, 217, 255, 0.25);
	}

	.platform-features h3 {
		color: var(--text-primary);
		font-weight: 600;
		margin-bottom: 1rem;
		font-size: 1rem;
		text-align: center;
	}

	.features-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.platform-feature {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		color: var(--text-secondary);
		font-size: 0.85rem;
		font-weight: 500;
	}

	.platform-icon {
		width: 32px;
		height: 32px;
		border-radius: 8px;
		background: #ffffff;
		border: 2px solid rgba(0, 217, 255, 0.3);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 14px;
		flex-shrink: 0;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.login-container.light .platform-icon {
		background: #ffffff;
		border-color: rgba(0, 217, 255, 0.4);
	}

	.platform-icon.github {
		color: #000000;
	}

	.platform-icon.github svg {
		width: 16px;
		height: 16px;
	}

	/* Footer */
	.login-footer {
		text-align: center;
	}

	.security-notice {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		color: var(--text-muted);
		font-size: 0.85rem;
		opacity: 0.8;
	}

	.security-icon {
		font-size: 1rem;
	}

	/* Responsive Design */
	@media (max-width: 640px) {
		.login-container {
			padding: 1rem;
		}

		.login-card {
			padding: 2rem 1.5rem;
		}

		.brand-name {
			font-size: 2rem;
		}

		.welcome-title {
			font-size: 1.75rem;
		}

		.features-grid {
			grid-template-columns: 1fr;
		}

		.theme-toggle {
			top: 1rem;
			right: 1rem;
			padding: 0.5rem;
		}
	}
</style>
