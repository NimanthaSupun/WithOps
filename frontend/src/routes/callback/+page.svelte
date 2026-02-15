<script>
	import { getAuthClient } from '$lib/auth';
	import { onMount } from 'svelte';
	import { authState } from '$lib/authState.js';
	import { isDarkMode } from '$lib/stores.js';

	let status = 'processing';
	let error = null;
	let darkMode = false;

	// Subscribe to the global theme store
	isDarkMode.subscribe((value) => {
		darkMode = value;
	});

	onMount(async () => {
		try {
			// Initialize theme
			isDarkMode.init();

			console.log('🔐 Callback: Processing authentication...');

			const client = await getAuthClient();
			await client.handleRedirectCallback();
			const user = await client.getUser();

			// Get ACCESS token for API calls (not ID token)
			const accessToken = await client.getTokenSilently();

			// Store the token in localStorage for immediate access by other components
			localStorage.setItem('auth0_token', accessToken);
			localStorage.setItem('auth_token', accessToken);

			// Clear any auth state flags
			authState.clearAuthState();

			// Send the access token to FastAPI backend
			const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';
			const response = await fetch(`${apiBase}/api/auth/callback`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${accessToken}`,
					'Content-Type': 'application/json'
				}
			});

			if (response.ok) {
				status = 'success';
				console.log('✅ Authentication successful, token stored');

				// Check if there's a redirect URL in the state
				const urlParams = new URLSearchParams(window.location.search);
				const state = urlParams.get('state');
				let redirectUrl = '/';

				// Prevent redirect loops - don't redirect back to organizations immediately
				if (state) {
					try {
						// Decode the state to see if it contains a redirect URL
						const decodedState = atob(state);
						if (decodedState.startsWith('redirect:')) {
							const requestedUrl = decodedState.replace('redirect:', '');
							// If the requested URL is organizations, redirect to main page first
							// to avoid authentication loops
							if (requestedUrl.includes('/organizations')) {
								console.log('🔄 Preventing organizations redirect loop, going to main page first');
								redirectUrl = '/';
							} else {
								redirectUrl = requestedUrl;
							}
						}
					} catch (e) {
						console.log('State is not a redirect URL, using default');
					}
				}

				console.log('🔄 Redirecting to:', redirectUrl);

				// Redirect after a short delay
				setTimeout(() => {
					window.location.href = redirectUrl;
				}, 800); // Slightly longer delay
			} else {
				const errorData = await response.json();
				throw new Error(errorData.detail || 'Backend authentication failed');
			}
		} catch (err) {
			console.error('Callback error:', err);
			authState.clearAuthState(); // Clear state on error
			error = err.message;
			status = 'error';
		}
	});
</script>

<svelte:head>
	<title>Authentication - WithOps DevSecOps Platform</title>
</svelte:head>

<div class="auth-page {darkMode ? 'dark' : 'light'}">
	<div class="auth-content">
		<!-- Brand -->
		<div class="auth-brand">
			<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
			<span class="brand-name">WithOps</span>
		</div>

		<!-- Status Card -->
		<div class="auth-card">
			{#if status === 'processing'}
				<div class="status-section">
					<div class="status-indicator processing">
						<div class="spinner"></div>
					</div>
					<h2 class="status-title">Authenticating</h2>
					<p class="status-description">Processing your secure login credentials</p>
					<div class="progress-bar">
						<div class="progress-fill"></div>
					</div>
					<span class="status-label">ESTABLISHING SECURE SESSION...</span>
				</div>
			{:else if status === 'success'}
				<div class="status-section">
					<div class="status-indicator success">
						<svg class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2.5"
								d="M5 13l4 4L19 7"
							></path>
						</svg>
					</div>
					<h2 class="status-title">Authenticated</h2>
					<p class="status-description">Session verified. Redirecting to your workspace.</p>
					<span class="status-label">REDIRECT IN PROGRESS...</span>
				</div>
			{:else if status === 'error'}
				<div class="status-section">
					<div class="status-indicator error">
						<svg class="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</div>
					<h2 class="status-title">Authentication Failed</h2>
					<p class="status-description">An error occurred during the authentication handshake.</p>
					<div class="error-details">
						<div class="error-message">
							<strong>Error:</strong>
							{error}
						</div>
						<a href="/login" class="btn btn-primary">
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
								></path>
							</svg>
							Retry Authentication
							<span class="button-arrow">→</span>
						</a>
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="auth-footer">
			<svg
				width="12"
				height="12"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path
					d="M7 11V7a5 5 0 0110 0v4"
				/>
			</svg>
			<span>Secured by Auth0 · Enterprise-grade authentication</span>
		</div>
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
	}

	.auth-page.dark {
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

	.auth-page.light {
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

	/* Page Shell */
	.auth-page {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background 0.3s ease;
		position: relative;
		overflow: hidden;
	}

	/* Grid Backdrop */
	.auth-page::before {
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

	.auth-page::after {
		content: '';
		position: fixed;
		inset: 0;
		background: radial-gradient(circle at 50% -20%, var(--accent-soft), transparent 70%);
		pointer-events: none;
		z-index: 0;
	}

	/* Content */
	.auth-content {
		position: relative;
		z-index: 1;
		width: 100%;
		max-width: 400px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2rem;
		padding: 2rem;
	}

	/* Brand */
	.auth-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.brand-icon {
		width: 32px;
		height: 32px;
	}

	.brand-name {
		font-weight: 700;
		font-size: 1.125rem;
		letter-spacing: -0.02em;
		color: var(--text-primary);
	}

	/* Card */
	.auth-card {
		width: 100%;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2.5rem 2rem;
		box-shadow: var(--card-shadow);
		transition: border-color 0.2s var(--ease-premium);
	}

	/* Status Section */
	.status-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.25rem;
		text-align: center;
	}

	/* Status Indicator */
	.status-indicator {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.status-indicator.processing {
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
	}

	.status-indicator.success {
		border: 1px solid rgba(16, 185, 129, 0.15);
		background: rgba(16, 185, 129, 0.05);
	}

	.status-indicator.error {
		border: 1px solid rgba(239, 68, 68, 0.15);
		background: rgba(239, 68, 68, 0.05);
	}

	/* Spinner */
	.spinner {
		width: 20px;
		height: 20px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Icons */
	.check-icon {
		width: 22px;
		height: 22px;
		color: var(--success);
	}

	.error-icon {
		width: 22px;
		height: 22px;
		color: var(--error);
	}

	/* Status Text */
	.status-title {
		font-size: 1.125rem;
		font-weight: 700;
		letter-spacing: -0.01em;
		color: var(--text-primary);
	}

	.status-description {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		line-height: 1.6;
		max-width: 320px;
	}

	.status-label {
		font-family: var(--font-mono);
		font-size: 0.625rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	/* Progress Bar */
	.progress-bar {
		width: 100%;
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

	/* Error Details */
	.error-details {
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.error-message {
		padding: 0.75rem 1rem;
		background: rgba(239, 68, 68, 0.04);
		border: 1px solid rgba(239, 68, 68, 0.1);
		border-radius: 8px;
		color: var(--text-secondary);
		font-size: 0.8125rem;
		text-align: left;
		line-height: 1.6;
	}

	.error-message strong {
		color: var(--error);
		font-weight: 600;
	}

	/* Button */
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
		text-decoration: none;
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--text-primary);
	}

	.btn-primary {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
		width: 100%;
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
	.auth-footer {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.6875rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
		letter-spacing: 0.02em;
	}

	/* Responsive */
	@media (max-width: 480px) {
		.auth-content {
			padding: 1.5rem;
			gap: 1.5rem;
		}

		.auth-card {
			padding: 2rem 1.5rem;
		}

		.status-title {
			font-size: 1rem;
		}
	}
</style>
