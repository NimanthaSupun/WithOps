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

<div class="auth-container {darkMode ? 'dark' : 'light'}">
	<!-- Background Effects -->
	<div class="auth-background">
		<div class="auth-glow-1"></div>
		<div class="auth-glow-2"></div>
		<div class="auth-particles"></div>
	</div>

	<!-- Main Content -->
	<div class="auth-content">
		<!-- Header with Logo -->
		<div class="auth-header">
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
		</div>

		<!-- Authentication Status Card -->
		<div class="auth-card">
			{#if status === 'processing'}
				<div class="status-section">
					<div class="status-icon processing">
						<div class="loading-spinner">
							<div class="spinner-ring"></div>
							<div class="spinner-ring"></div>
							<div class="spinner-ring"></div>
						</div>
					</div>
					<h2 class="status-title">Authenticating...</h2>
					<p class="status-description">Securely processing your login credentials with Auth0</p>
					<div class="progress-bar">
						<div class="progress-fill"></div>
					</div>
				</div>
			{:else if status === 'success'}
				<div class="status-section">
					<div class="status-icon success">
						<svg class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="3"
								d="M5 13l4 4L19 7"
							></path>
						</svg>
						<div class="success-ripple"></div>
					</div>
					<h2 class="status-title">Authentication Successful!</h2>
					<p class="status-description">
						Welcome to WithOps! Redirecting you to your secure dashboard...
					</p>
					<div class="redirect-info">
						<div class="redirect-icon">🚀</div>
						<span>Preparing your workspace...</span>
					</div>
				</div>
			{:else if status === 'error'}
				<div class="status-section">
					<div class="status-icon error">
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
					<p class="status-description">
						We encountered an issue during authentication. Please try again.
					</p>
					<div class="error-details">
						<div class="error-message">
							<strong>Error:</strong>
							{error}
						</div>
						<a href="/login" class="retry-button">
							<svg class="retry-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
								></path>
							</svg>
							Try Again
						</a>
					</div>
				</div>
			{/if}
		</div>

		<!-- Security Notice -->
		<div class="security-notice">
			<div class="security-icon">🔒</div>
			<span>Secured by Auth0 • Enterprise-grade authentication</span>
		</div>
	</div>
</div>

<style>
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	/* Main Container */
	.auth-container {
		position: relative;
		min-height: 100vh;
		background: #000000;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		overflow: hidden;
		font-family:
			'Segoe UI',
			-apple-system,
			BlinkMacSystemFont,
			Arial,
			sans-serif;
	}

	.auth-container.light {
		background: #ffffff;
	}

	/* Background Effects - Matching Landing Page */
	.auth-background {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
		z-index: 1;
	}

	.auth-glow-1 {
		position: absolute;
		top: 20%;
		left: 10%;
		width: 400px;
		height: 400px;
		background: radial-gradient(ellipse at center, rgba(0, 217, 255, 0.2) 0%, transparent 60%);
		border-radius: 50%;
		animation: float 8s ease-in-out infinite;
		opacity: 0.6;
	}

	.auth-glow-2 {
		position: absolute;
		bottom: 20%;
		right: 10%;
		width: 500px;
		height: 500px;
		background: radial-gradient(ellipse at center, rgba(0, 217, 255, 0.15) 0%, transparent 70%);
		border-radius: 50%;
		animation: float 10s ease-in-out infinite reverse;
		opacity: 0.4;
	}

	.auth-particles {
		position: absolute;
		inset: 0;
		opacity: 0.03;
		pointer-events: none;
		background-image:
			linear-gradient(rgba(0, 217, 255, 0.1) 1px, transparent 1px),
			linear-gradient(90deg, rgba(0, 217, 255, 0.1) 1px, transparent 1px);
		background-size: 50px 50px;
	}

	@keyframes float {
		0%,
		100% {
			transform: translateY(0px);
		}
		50% {
			transform: translateY(-30px);
		}
	}

	/* Main Content */
	.auth-content {
		position: relative;
		z-index: 2;
		width: 100%;
		max-width: 500px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2.5rem;
	}

	/* Header with Brand - Matching Landing Page */
	.auth-header {
		text-align: center;
		margin-bottom: 1rem;
	}

	.brand-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.5rem;
	}

	.brand-icon-wrapper {
		position: relative;
		width: 80px;
		height: 80px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.brand-icon {
		width: 80px;
		height: 80px;
		filter: drop-shadow(0 0 15px rgba(0, 217, 255, 0.5));
		transition: all 0.3s ease;
		animation: pulse-brand 3s ease-in-out infinite;
	}

	.brand-glow {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 150px;
		height: 150px;
		background: radial-gradient(circle, rgba(0, 217, 255, 0.3) 0%, transparent 70%);
		border-radius: 50%;
		animation: pulse-glow 3s ease-in-out infinite;
	}

	@keyframes pulse-brand {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.08);
		}
	}

	@keyframes pulse-glow {
		0%,
		100% {
			opacity: 0.4;
			transform: translate(-50%, -50%) scale(1);
		}
		50% {
			opacity: 0.8;
			transform: translate(-50%, -50%) scale(1.25);
		}
	}

	.brand-text {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
	}

	.brand-name {
		font-size: 2.5rem;
		font-weight: 700;
		color: #ffffff;
		line-height: 1;
		letter-spacing: -0.02em;
	}

	.auth-container.light .brand-name {
		color: #000000;
	}

	.brand-subtitle {
		font-size: 0.9rem;
		color: #00d9ff;
		opacity: 0.9;
		letter-spacing: 0.05em;
		font-weight: 600;
		text-transform: uppercase;
	}

	/* Authentication Card - Matching Dashboard Card Pattern */
	.auth-card {
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		padding: 2.5rem;
		width: 100%;
		transition: all 0.4s ease;
		position: relative;
		overflow: hidden;
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.15);
	}

	.auth-container.light .auth-card {
		background: rgba(255, 255, 255, 0.95);
		border: 1px solid rgba(0, 217, 255, 0.15);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
	}

	.auth-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		transition: left 0.6s;
	}

	.auth-card:hover::before {
		left: 100%;
	}

	/* Status Section */
	.status-section {
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.5rem;
	}

	.status-icon {
		width: 80px;
		height: 80px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		position: relative;
		margin-bottom: 0.5rem;
	}

	/* Processing State */
	.status-icon.processing {
		background: rgba(0, 217, 255, 0.1);
		border: 2px solid rgba(0, 217, 255, 0.3);
	}

	.loading-spinner {
		position: relative;
		width: 40px;
		height: 40px;
	}

	.spinner-ring {
		position: absolute;
		width: 100%;
		height: 100%;
		border: 3px solid transparent;
		border-top-color: #00d9ff;
		border-radius: 50%;
		animation: spin 1.2s linear infinite;
	}

	.spinner-ring:nth-child(2) {
		width: 70%;
		height: 70%;
		top: 15%;
		left: 15%;
		border-top-color: #33e3ff;
		animation-duration: 1.5s;
		animation-direction: reverse;
	}

	.spinner-ring:nth-child(3) {
		width: 40%;
		height: 40%;
		top: 30%;
		left: 30%;
		border-top-color: #00d9ff;
		animation-duration: 2s;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}

	/* Success State */
	.status-icon.success {
		background: rgba(0, 217, 255, 0.15);
		border: 2px solid #00d9ff;
		animation: success-bounce 0.6s ease-out;
	}

	.check-icon {
		width: 40px;
		height: 40px;
		color: #00d9ff;
		filter: drop-shadow(0 0 10px rgba(0, 217, 255, 0.5));
	}

	.success-ripple {
		position: absolute;
		top: -10px;
		left: -10px;
		right: -10px;
		bottom: -10px;
		border: 2px solid #00d9ff;
		border-radius: 50%;
		animation: ripple 2s ease-out infinite;
	}

	@keyframes success-bounce {
		0% {
			transform: scale(0);
		}
		50% {
			transform: scale(1.2);
		}
		100% {
			transform: scale(1);
		}
	}

	@keyframes ripple {
		0% {
			transform: scale(1);
			opacity: 1;
		}
		100% {
			transform: scale(1.5);
			opacity: 0;
		}
	}

	/* Error State */
	.status-icon.error {
		background: rgba(255, 71, 87, 0.15);
		border: 2px solid #ff4757;
		animation: error-shake 0.5s ease-out;
	}

	.error-icon {
		width: 40px;
		height: 40px;
		color: #ff4757;
	}

	@keyframes error-shake {
		0%,
		100% {
			transform: translateX(0);
		}
		25% {
			transform: translateX(-5px);
		}
		75% {
			transform: translateX(5px);
		}
	}

	/* Status Text */
	.status-title {
		font-size: 1.75rem;
		font-weight: 700;
		color: #ffffff;
		margin: 0;
		line-height: 1.2;
	}

	.auth-container.light .status-title {
		color: #000000;
	}

	.status-description {
		font-size: 1rem;
		color: #b8b8b8;
		line-height: 1.7;
		margin: 0;
		max-width: 400px;
	}

	.auth-container.light .status-description {
		color: #666666;
	}

	/* Progress Bar */
	.progress-bar {
		width: 100%;
		height: 4px;
		background: rgba(0, 217, 255, 0.2);
		border-radius: 2px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #00d9ff, #33e3ff);
		border-radius: 2px;
		animation: progress 2s ease-in-out infinite;
	}

	@keyframes progress {
		0% {
			width: 0%;
			transform: translateX(-100%);
		}
		50% {
			width: 100%;
			transform: translateX(0%);
		}
		100% {
			width: 100%;
			transform: translateX(100%);
		}
	}

	/* Redirect Info */
	.redirect-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem 1.5rem;
		background: rgba(0, 217, 255, 0.1);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 8px;
		color: #b8b8b8;
		font-size: 0.9rem;
	}

	.auth-container.light .redirect-info {
		background: rgba(0, 217, 255, 0.08);
		color: #666666;
	}

	.redirect-icon {
		font-size: 1.2rem;
		animation: rocket 2s ease-in-out infinite;
	}

	@keyframes rocket {
		0%,
		100% {
			transform: translateY(0px);
		}
		50% {
			transform: translateY(-4px);
		}
	}

	/* Error Details */
	.error-details {
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.error-message {
		padding: 1rem 1.25rem;
		background: rgba(255, 71, 87, 0.1);
		border: 1px solid rgba(255, 71, 87, 0.3);
		border-radius: 8px;
		color: #b8b8b8;
		font-size: 0.9rem;
		text-align: left;
		line-height: 1.6;
	}

	.auth-container.light .error-message {
		background: rgba(255, 71, 87, 0.08);
		color: #666666;
	}

	.error-message strong {
		color: #ff4757;
		font-weight: 600;
	}

	/* Retry Button - Matching Primary Button Pattern */
	.retry-button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 1.2rem 2rem;
		background: #ffffff;
		color: #000000;
		text-decoration: none;
		border-radius: 8px;
		font-weight: 600;
		font-size: 1rem;
		transition: all 0.3s ease;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
		cursor: pointer;
	}

	.retry-button:hover {
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
		background: #00d9ff;
		color: #000000;
	}

	.auth-container.light .retry-button {
		background: #00d9ff;
		color: #000000;
		box-shadow:
			0 8px 25px rgba(0, 217, 255, 0.3),
			0 4px 12px rgba(0, 217, 255, 0.15);
	}

	.auth-container.light .retry-button:hover {
		background: #33e3ff;
		box-shadow:
			0 12px 32px rgba(0, 217, 255, 0.4),
			0 6px 16px rgba(0, 217, 255, 0.25);
	}

	.retry-icon {
		width: 20px;
		height: 20px;
		transition: transform 0.3s ease;
	}

	.retry-button:hover .retry-icon {
		transform: rotate(180deg);
	}

	/* Security Notice */
	.security-notice {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: #b8b8b8;
		font-size: 0.875rem;
		opacity: 0.8;
	}

	.auth-container.light .security-notice {
		color: #666666;
	}

	.security-icon {
		font-size: 1rem;
	}

	/* Responsive Design */
	@media (max-width: 640px) {
		.auth-container {
			padding: 1.5rem;
		}

		.auth-card {
			padding: 2rem 1.5rem;
		}

		.brand-name {
			font-size: 2rem;
		}

		.brand-subtitle {
			font-size: 0.8rem;
		}

		.status-title {
			font-size: 1.5rem;
		}

		.status-description {
			font-size: 0.95rem;
		}

		.status-icon {
			width: 70px;
			height: 70px;
		}

		.loading-spinner {
			width: 35px;
			height: 35px;
		}

		.check-icon,
		.error-icon {
			width: 35px;
			height: 35px;
		}

		.retry-button {
			padding: 1rem 1.5rem;
			font-size: 0.95rem;
		}
	}

	@media (max-width: 480px) {
		.auth-content {
			gap: 2rem;
		}

		.brand-icon-wrapper {
			width: 70px;
			height: 70px;
		}

		.brand-icon {
			width: 70px;
			height: 70px;
		}

		.brand-name {
			font-size: 1.75rem;
		}

		.status-title {
			font-size: 1.35rem;
		}

		.status-icon {
			width: 60px;
			height: 60px;
		}

		.loading-spinner {
			width: 30px;
			height: 30px;
		}

		.check-icon,
		.error-icon {
			width: 30px;
			height: 30px;
		}
	}
</style>
