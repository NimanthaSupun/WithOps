<script>
	import { onMount } from 'svelte';

	let visible = $state(false);
	let copiedStates = $state({});
	let activeMethod = $state('oauth');

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});

	function copyCode(id, text) {
		navigator.clipboard.writeText(text).then(() => {
			copiedStates[id] = true;
			setTimeout(() => {
				copiedStates[id] = false;
			}, 1800);
		});
	}
</script>

<svelte:head>
	<title>Connecting GitHub — WithOps Documentation</title>
	<meta
		name="description"
		content="Connect your GitHub account to WithOps using OAuth or GitHub App. Configure repository permissions and organisation access for continuous security monitoring."
	/>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Getting Started</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Connecting GitHub</span>
	</div>

	<div class="chapter-tag">
		<svg
			width="14"
			height="14"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
		>
			<path
				d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22"
			/>
		</svg>
		Chapter III
	</div>

	<h1 class="page-title" id="connecting-github">Connecting GitHub</h1>
	<p class="page-subtitle">
		Link your GitHub account to enable repository scanning, PR automation, and real-time security
		monitoring.
	</p>

	<hr class="divider" />

	<div class="meta-row">
		<span class="meta-reading">
			<svg
				width="12"
				height="12"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
			</svg>
			5 min read
		</span>
		<span class="meta-tag">Integration</span>
		<span class="meta-tag">OAuth</span>
	</div>

	<!-- Auth Methods -->
	<h2 class="section-heading" id="authentication-methods">Authentication Methods</h2>
	<p class="prose-text">
		WithOps supports two ways to connect GitHub. Both methods use secure OAuth 2.0 flows and never
		store your GitHub password.
	</p>

	<div class="method-tabs">
		<button
			class="method-tab {activeMethod === 'oauth' ? 'active' : ''}"
			onclick={() => (activeMethod = 'oauth')}
		>
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0110 0v4" />
			</svg>
			OAuth App
		</button>
		<button
			class="method-tab {activeMethod === 'app' ? 'active' : ''}"
			onclick={() => (activeMethod = 'app')}
		>
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
			</svg>
			GitHub App
			<span class="rec-badge">Recommended</span>
		</button>
	</div>

	{#if activeMethod === 'oauth'}
		<div class="tab-panel">
			<div class="prose">
				<h3 id="oauth-flow">OAuth Flow</h3>
				<p>
					OAuth provides a simple, quick connection. Best for individual developers or personal
					accounts.
				</p>
			</div>

			<div class="steps">
				<div class="step-card">
					<div class="step-num">1</div>
					<div class="step-body">
						<h4>Navigate to Settings</h4>
						<p>
							Open the WithOps dashboard and go to <strong>Settings → Integrations → GitHub</strong
							>.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">2</div>
					<div class="step-body">
						<h4>Click "Connect with GitHub"</h4>
						<p>
							You'll be redirected to GitHub to authorise the WithOps OAuth application. Review the
							requested permissions.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">3</div>
					<div class="step-body">
						<h4>Grant access</h4>
						<p>
							Authorise WithOps to access your repositories. You can choose <strong
								>all repositories</strong
							>
							or <strong>select repositories</strong> individually.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">4</div>
					<div class="step-body">
						<h4>Verify connection</h4>
						<p>
							After redirect, your connected account will appear in the dashboard with a green <strong
								>"Connected"</strong
							> badge.
						</p>
					</div>
				</div>
			</div>

			<div class="callout info">
				<div class="callout-icon">
					<svg
						width="16"
						height="16"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" />
					</svg>
				</div>
				<div class="callout-content">
					<div class="callout-label">OAuth scope</div>
					<p>
						The OAuth app requests <code>repo</code>, <code>read:org</code>, and
						<code>read:user</code> scopes. No write access to your code is requested.
					</p>
				</div>
			</div>
		</div>
	{/if}

	{#if activeMethod === 'app'}
		<div class="tab-panel">
			<div class="prose">
				<h3 id="github-app">GitHub App Installation</h3>
				<p>
					The GitHub App offers finer-grained permissions, organisation support, and webhook-based
					real-time notifications. This is the recommended integration method for teams.
				</p>
			</div>

			<div class="steps">
				<div class="step-card">
					<div class="step-num">1</div>
					<div class="step-body">
						<h4>Install the WithOps GitHub App</h4>
						<p>
							Visit the GitHub Marketplace or navigate to <strong
								>Settings → Integrations → GitHub → Install App</strong
							>. Select your organisation or personal account.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">2</div>
					<div class="step-body">
						<h4>Select repositories</h4>
						<p>
							Choose <strong>"All repositories"</strong> for comprehensive monitoring or select
							specific repositories. You can change this later in GitHub's
							<strong>Settings → Applications</strong>.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">3</div>
					<div class="step-body">
						<h4>Configure webhooks</h4>
						<p>
							The app automatically creates webhooks for push events, pull requests, and workflow
							runs. No manual configuration is needed.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">4</div>
					<div class="step-body">
						<h4>Start monitoring</h4>
						<p>
							Repositories will appear in your dashboard within seconds. WithOps begins baseline
							analysis automatically.
						</p>
					</div>
				</div>
			</div>

			<div class="callout tip">
				<div class="callout-icon">
					<svg
						width="16"
						height="16"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
					</svg>
				</div>
				<div class="callout-content">
					<div class="callout-label">Why GitHub App?</div>
					<p>
						GitHub Apps offer per-repository permissions, support for organisation-level
						installation, webhook-based events, and don't count against your personal API rate
						limit.
					</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Permissions -->
	<h2 class="section-heading" id="permissions">Permissions Reference</h2>
	<p class="prose-text">
		WithOps follows the principle of least privilege. Here's exactly what each permission is used
		for:
	</p>

	<div class="perm-table">
		<div class="perm-header">
			<span>Permission</span>
			<span>Access</span>
			<span>Used For</span>
		</div>
		<div class="perm-row">
			<span class="perm-name">Repository contents</span>
			<span class="perm-access read">Read</span>
			<span class="perm-purpose">Code analysis, dependency scanning, and secret detection</span>
		</div>
		<div class="perm-row">
			<span class="perm-name">Pull requests</span>
			<span class="perm-access read">Read</span>
			<span class="perm-purpose">PR security reviews and automated vulnerability comments</span>
		</div>
		<div class="perm-row">
			<span class="perm-name">Issues</span>
			<span class="perm-access write">Write</span>
			<span class="perm-purpose">Creating security advisory issues and tracking remediation</span>
		</div>
		<div class="perm-row">
			<span class="perm-name">Workflows</span>
			<span class="perm-access read">Read</span>
			<span class="perm-purpose">CI/CD pipeline analysis and GitHub Actions validation</span>
		</div>
		<div class="perm-row">
			<span class="perm-name">Organisation</span>
			<span class="perm-access read">Read</span>
			<span class="perm-purpose">Team structure mapping for access control and collaboration</span>
		</div>
		<div class="perm-row">
			<span class="perm-name">Webhooks</span>
			<span class="perm-access write">Write</span>
			<span class="perm-purpose"
				>Real-time event notifications for push, PR, and workflow events</span
			>
		</div>
	</div>

	<!-- Managing Repos -->
	<h2 class="section-heading" id="managing-repositories">Managing Repositories</h2>
	<p class="prose-text">
		After connecting, you can manage which repositories WithOps has access to and configure per-repo
		settings.
	</p>

	<div class="config-grid">
		<div class="config-item">
			<div class="config-icon">
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
				</svg>
			</div>
			<div>
				<strong>Add or remove repositories</strong>
				<p>
					Go to <strong>Settings → GitHub → Manage Repositories</strong> to add or revoke access to specific
					repositories at any time.
				</p>
			</div>
		</div>
		<div class="config-item">
			<div class="config-icon">
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<circle cx="12" cy="12" r="3" /><path
						d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"
					/>
				</svg>
			</div>
			<div>
				<strong>Per-repo scan policies</strong>
				<p>
					Configure which scan types run on each repository. Enable or disable SAST, dependency
					audit, secrets scanning, and STRIDE analysis.
				</p>
			</div>
		</div>
		<div class="config-item">
			<div class="config-icon">
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
				</svg>
			</div>
			<div>
				<strong>Branch protection rules</strong>
				<p>
					Set up security gates that must pass before PRs can be merged. Requires GitHub App
					integration for status check reporting.
				</p>
			</div>
		</div>
	</div>

	<!-- Self-Hosted GitHub Config -->
	<h2 class="section-heading" id="self-hosted-config">Self-Hosted Configuration</h2>
	<p class="prose-text">
		For self-hosted deployments, configure the GitHub integration in your environment variables:
	</p>

	<div class="code-block">
		<div class="code-header">
			<span class="code-lang">.env</span>
			<button
				class="copy-btn"
				onclick={() =>
					copyCode(
						'ghenv',
						'GITHUB_CLIENT_ID=your_client_id\nGITHUB_CLIENT_SECRET=your_client_secret\nGITHUB_REDIRECT_URI=http://localhost:5173/auth/callback/github\nGITHUB_APP_ID=your_app_id\nGITHUB_PRIVATE_KEY_PATH=./github-app-key.pem'
					)}
			>
				{copiedStates['ghenv'] ? '✓ Copied' : 'Copy'}
			</button>
		</div>
		<pre><code
				><span class="cm"># ─── GitHub OAuth (for user authentication) ───</span>
<span class="kw">GITHUB_CLIENT_ID</span>=<span class="str">your_oauth_client_id</span>
<span class="kw">GITHUB_CLIENT_SECRET</span>=<span class="str">your_oauth_client_secret</span>
<span class="kw">GITHUB_REDIRECT_URI</span>=<span class="str"
					>http://localhost:5173/github/organizations</span
				>

<span class="cm"># ─── GitHub App (for repository access) ───</span>
<span class="kw">GITHUB_APP_ID</span>=<span class="str">your_app_id</span>
<span class="kw">GITHUB_PRIVATE_KEY_PATH</span>=<span class="str">./github-app-key.pem</span>
<span class="kw">GITHUB_WEBHOOK_SECRET</span>=<span class="str">your_webhook_secret</span></code
			></pre>
	</div>

	<div class="callout warn">
		<div class="callout-icon">
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<path
					d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
				/>
				<line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
			</svg>
		</div>
		<div class="callout-content">
			<div class="callout-label">GitHub Enterprise</div>
			<p>
				For GitHub Enterprise Server, also set <code>GITHUB_API_URL</code> and
				<code>GITHUB_HOSTNAME</code> to point to your instance.
			</p>
		</div>
	</div>
</div>

<style>
	.getting-started {
		opacity: 0;
		transform: translateY(10px);
		transition: all 0.5s ease;
	}
	.getting-started.visible {
		opacity: 1;
		transform: translateY(0);
	}

	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 8px;
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		margin-bottom: 24px;
	}
	.bc-link {
		color: var(--text-muted);
		text-decoration: none;
		transition: color 0.15s;
	}
	.bc-link:hover {
		color: var(--accent);
	}
	.bc-sep {
		color: var(--border-focus);
	}
	.bc-current {
		color: var(--accent);
	}

	.chapter-tag {
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--accent);
		margin-bottom: 12px;
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.chapter-tag::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--accent);
		opacity: 0.2;
		max-width: 50px;
	}

	.page-title {
		font-family: 'Playfair Display', serif;
		font-size: 38px;
		font-weight: 700;
		line-height: 1.15;
		color: var(--text-primary);
		margin-bottom: 10px;
	}
	.page-subtitle {
		font-family: 'Lora', serif;
		font-style: italic;
		font-size: 15px;
		color: var(--text-secondary);
		line-height: 1.6;
	}
	.divider {
		border: none;
		border-top: 1px solid var(--border);
		margin: 24px 0;
	}

	.meta-row {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 28px;
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		color: var(--text-muted);
	}
	.meta-reading {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.meta-tag {
		padding: 2px 8px;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--text-secondary);
		font-size: 10px;
	}

	.section-heading {
		font-family: 'Playfair Display', serif;
		font-size: 22px;
		font-weight: 700;
		color: var(--text-primary);
		margin: 40px 0 12px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	.prose-text,
	.prose p {
		font-family: 'Lora', serif;
		font-size: 15px;
		line-height: 1.85;
		color: var(--text-primary);
		margin-bottom: 16px;
	}
	.callout-content code {
		font-family: 'DM Mono', monospace;
		font-size: 12px;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		padding: 1px 5px;
		border-radius: 3px;
		color: var(--accent);
	}

	h3 {
		font-family: 'Lora', serif;
		font-size: 17px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 28px 0 12px;
	}

	/* Method Tabs */
	.method-tabs {
		display: flex;
		gap: 8px;
		margin: 16px 0 24px;
	}
	.method-tab {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 20px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 6px;
		font-family: 'Inter', sans-serif;
		font-size: 13px;
		font-weight: 500;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}
	.method-tab:hover {
		border-color: var(--border-focus);
		color: var(--text-primary);
	}
	.method-tab.active {
		background: var(--accent-subtle);
		border-color: var(--accent);
		color: var(--accent);
	}
	.rec-badge {
		font-size: 9px;
		background: rgba(16, 185, 129, 0.1);
		color: var(--success);
		padding: 2px 6px;
		border-radius: 3px;
		letter-spacing: 0.04em;
		text-transform: uppercase;
	}
	.tab-panel {
		animation: fadeIn 0.3s ease;
	}

	/* Steps */
	.steps {
		display: flex;
		flex-direction: column;
		gap: 12px;
		margin: 20px 0 24px;
	}
	.step-card {
		display: flex;
		gap: 16px;
		padding: 18px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 6px;
		box-shadow: var(--card-shadow);
	}
	.step-num {
		width: 30px;
		height: 30px;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: 'Playfair Display', serif;
		font-size: 14px;
		color: var(--accent);
		flex-shrink: 0;
	}
	.step-body h4 {
		font-family: 'Lora', serif;
		font-weight: 600;
		font-size: 14px;
		color: var(--text-primary);
		margin-bottom: 4px;
	}
	.step-body p {
		font-family: 'Lora', serif;
		font-size: 13px;
		line-height: 1.65;
		color: var(--text-secondary);
		margin: 0;
	}
	.step-body strong {
		font-weight: 600;
		color: var(--text-primary);
	}

	/* Permissions Table */
	.perm-table {
		margin: 16px 0 32px;
		border: 1px solid var(--border);
		border-radius: 6px;
		overflow: hidden;
	}
	.perm-header {
		display: grid;
		grid-template-columns: 160px 80px 1fr;
		gap: 12px;
		padding: 10px 16px;
		background: var(--bg-surface-2);
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-muted);
	}
	.perm-row {
		display: grid;
		grid-template-columns: 160px 80px 1fr;
		gap: 12px;
		padding: 10px 16px;
		border-top: 1px solid var(--border);
		align-items: center;
	}
	.perm-name {
		font-family: 'Inter', sans-serif;
		font-size: 12.5px;
		font-weight: 500;
		color: var(--text-primary);
	}
	.perm-access {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		padding: 2px 8px;
		border-radius: 3px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		display: inline-block;
		width: fit-content;
	}
	.perm-access.read {
		background: rgba(0, 173, 239, 0.08);
		color: var(--accent);
	}
	.perm-access.write {
		background: rgba(245, 158, 11, 0.08);
		color: var(--warn);
	}
	.perm-purpose {
		font-family: 'Lora', serif;
		font-size: 12px;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	/* Config Grid */
	.config-grid {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin: 16px 0 32px;
	}
	.config-item {
		display: flex;
		gap: 14px;
		align-items: flex-start;
		padding: 16px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 6px;
	}
	.config-icon {
		width: 36px;
		height: 36px;
		background: var(--accent-subtle);
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--accent);
		flex-shrink: 0;
	}
	.config-item strong {
		font-family: 'Inter', sans-serif;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		display: block;
		margin-bottom: 3px;
	}
	.config-item p {
		font-family: 'Lora', serif;
		font-size: 12.5px;
		line-height: 1.6;
		color: var(--text-secondary);
		margin: 0;
	}
	.config-item p strong {
		display: inline;
		font-family: inherit;
		font-size: inherit;
	}

	/* Code Block */
	.code-block {
		background: var(--code-bg);
		border-radius: 6px;
		margin: 16px 0;
		overflow: hidden;
		border: 1px solid var(--code-border);
	}
	.code-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 16px;
		border-bottom: 1px solid var(--code-border);
	}
	.code-lang {
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		color: #6b7a5e;
	}
	.copy-btn {
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		color: #6b7a5e;
		background: none;
		border: none;
		cursor: pointer;
		padding: 2px 8px;
		border-radius: 3px;
		transition: all 0.15s;
	}
	.copy-btn:hover {
		background: rgba(255, 255, 255, 0.06);
		color: #b5c9a0;
	}
	pre {
		padding: 16px 20px;
		overflow-x: auto;
		font-family: 'DM Mono', monospace;
		font-size: 12.5px;
		line-height: 1.7;
		color: var(--code-text);
		margin: 0;
	}
	.kw {
		color: #c8956e;
	}
	.str {
		color: #a5c985;
	}
	.cm {
		color: #5a6e4a;
	}

	/* Callouts */
	.callout {
		display: flex;
		gap: 14px;
		padding: 16px 20px;
		border-radius: 0 6px 6px 0;
		margin: 20px 0;
		border-left: 3px solid;
	}
	.callout.info {
		background: var(--callout-info-bg);
		border-left-color: var(--accent);
	}
	.callout.tip {
		background: var(--callout-tip-bg);
		border-left-color: var(--callout-tip-border);
	}
	.callout.warn {
		background: var(--callout-warn-bg);
		border-left-color: var(--callout-warn-border);
	}
	.callout-icon {
		flex-shrink: 0;
		margin-top: 2px;
	}
	.callout.info .callout-icon {
		color: var(--callout-info-text);
	}
	.callout.tip .callout-icon {
		color: var(--callout-tip-text);
	}
	.callout.warn .callout-icon {
		color: var(--callout-warn-text);
	}
	.callout-label {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		margin-bottom: 4px;
	}
	.callout.info .callout-label {
		color: var(--callout-info-text);
	}
	.callout.tip .callout-label {
		color: var(--callout-tip-text);
	}
	.callout.warn .callout-label {
		color: var(--callout-warn-text);
	}
	.callout-content p {
		font-family: 'Lora', serif;
		font-size: 13.5px;
		line-height: 1.7;
		color: var(--text-secondary);
		margin: 0;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@media (max-width: 768px) {
		.page-title {
			font-size: 28px;
		}
		.method-tabs {
			flex-direction: column;
		}
		.perm-header,
		.perm-row {
			grid-template-columns: 1fr;
			gap: 4px;
		}
		.perm-header span:nth-child(2),
		.perm-header span:nth-child(3) {
			display: none;
		}
	}
</style>
