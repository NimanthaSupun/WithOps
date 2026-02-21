<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<div class="gs-page {visible ? 'visible' : ''}">
	<!-- Page Header -->
	<div class="page-header">
		<div class="breadcrumb">
			<span class="bc-muted">Docs</span>
			<span class="bc-sep">/</span>
			<a href="/docs/getting-started" class="bc-link">Getting Started</a>
			<span class="bc-sep">/</span>
			<span class="bc-current">Connecting GitHub</span>
		</div>
		<h1 class="page-title" id="connecting-github">Connecting GitHub</h1>
		<p class="page-lead">
			Link your GitHub account and organizations to unlock automated security scanning, PR analysis,
			and workflow monitoring.
		</p>
	</div>

	<!-- Overview -->
	<h2 id="how-it-works">How GitHub Integration Works</h2>
	<p class="body-text">
		WithOps connects to GitHub through two mechanisms that work together to provide comprehensive
		repository coverage:
	</p>

	<div class="two-col-cards">
		<div class="method-card">
			<div class="method-badge oauth">OAuth</div>
			<h4>GitHub OAuth</h4>
			<p>
				Authenticates your identity and grants read access to your organizations and repositories.
			</p>
			<ul class="method-features">
				<li>View organizations & repos</li>
				<li>Read repository metadata</li>
				<li>User identity verification</li>
			</ul>
		</div>
		<div class="method-card">
			<div class="method-badge app">GitHub App</div>
			<h4>WithOps GitHub App</h4>
			<p>
				Provides fine-grained permissions for automated scanning, PR comments, and webhook events.
			</p>
			<ul class="method-features">
				<li>Automated security scanning</li>
				<li>PR review comments</li>
				<li>Webhook event processing</li>
			</ul>
		</div>
	</div>

	<!-- Step by Step -->
	<h2 id="step-1-authorize">Step 1 — Authorize via OAuth</h2>
	<p class="body-text">From your WithOps dashboard, initiate the GitHub connection:</p>

	<div class="instruction-block">
		<div class="instruction-number">1</div>
		<div class="instruction-content">
			<p>
				Navigate to <strong>Dashboard → GitHub Connectivity</strong> and click
				<strong>"Authorize GitHub Account"</strong>
			</p>
		</div>
	</div>

	<div class="instruction-block">
		<div class="instruction-number">2</div>
		<div class="instruction-content">
			<p>Review the OAuth permission scopes. WithOps requests minimal access:</p>
			<div class="scope-list">
				<div class="scope-item">
					<code>read:org</code>
					<span>List organizations you belong to</span>
				</div>
				<div class="scope-item">
					<code>read:user</code>
					<span>Read your GitHub profile information</span>
				</div>
				<div class="scope-item">
					<code>repo</code>
					<span>Access repository data for security analysis</span>
				</div>
			</div>
		</div>
	</div>

	<div class="instruction-block">
		<div class="instruction-number">3</div>
		<div class="instruction-content">
			<p>
				Click <strong>"Authorize"</strong> on GitHub. You'll be redirected back to WithOps with your
				account linked.
			</p>
			<div class="callout callout-tip">
				<div class="callout-icon">
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg
					>
				</div>
				<div class="callout-content">
					<strong>Token security</strong>
					<p>
						Your GitHub token is encrypted at rest and transmitted via HTTPS only. It's never
						exposed to the frontend client.
					</p>
				</div>
			</div>
		</div>
	</div>

	<!-- Step 2 -->
	<h2 id="step-2-discover-orgs">Step 2 — Discover Organizations</h2>
	<p class="body-text">
		Once connected, WithOps can discover all organizations your GitHub account has access to.
	</p>

	<div class="instruction-block">
		<div class="instruction-number">1</div>
		<div class="instruction-content">
			<p>On the Dashboard, your GitHub card should now show <strong>"ACCOUNT VERIFIED"</strong></p>
		</div>
	</div>

	<div class="instruction-block">
		<div class="instruction-number">2</div>
		<div class="instruction-content">
			<p>
				Click <strong>"Discover Organizations"</strong> to enumerate all orgs and their repositories
			</p>
		</div>
	</div>

	<div class="instruction-block">
		<div class="instruction-number">3</div>
		<div class="instruction-content">
			<p>
				Navigate to <strong>Organizations</strong> in the top nav to view the results. Each organization
				shows:
			</p>
			<div class="feature-table">
				<div class="ft-row">
					<div class="ft-label">Repositories</div>
					<div class="ft-desc">All repos in the org with language breakdown and visibility</div>
				</div>
				<div class="ft-row">
					<div class="ft-label">Members</div>
					<div class="ft-desc">Organization member count and your role</div>
				</div>
				<div class="ft-row">
					<div class="ft-label">Security Status</div>
					<div class="ft-desc">Aggregated security posture once scanning is enabled</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Step 3 -->
	<h2 id="step-3-install-app">Step 3 — Install the GitHub App (Optional)</h2>
	<p class="body-text">
		For deeper integration — automated PR comments, webhook-driven scanning, and branch protection —
		install the WithOps GitHub App on your organization.
	</p>

	<div class="callout callout-info">
		<div class="callout-icon">
			<svg
				width="14"
				height="14"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				><circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line
					x1="12"
					y1="8"
					x2="12.01"
					y2="8"
				/></svg
			>
		</div>
		<div class="callout-content">
			<strong>Organization admin required</strong>
			<p>
				You need admin access to the GitHub organization to install the GitHub App. Contact your org
				admin if you don't have this permission.
			</p>
		</div>
	</div>

	<div class="app-permissions">
		<h4>GitHub App Permissions</h4>
		<p class="body-text">The WithOps app requests these permissions:</p>
		<div class="perm-grid">
			<div class="perm-item">
				<div class="perm-level read">Read</div>
				<span>Repository contents, metadata, workflows</span>
			</div>
			<div class="perm-item">
				<div class="perm-level write">Write</div>
				<span>Pull request comments, check runs, issues</span>
			</div>
			<div class="perm-item">
				<div class="perm-level read">Read</div>
				<span>Organization members, teams</span>
			</div>
			<div class="perm-item">
				<div class="perm-level events">Events</div>
				<span>Push, pull request, workflow run webhooks</span>
			</div>
		</div>
	</div>

	<!-- Troubleshooting -->
	<h2 id="troubleshooting">Troubleshooting</h2>

	<div class="faq-list">
		<div class="faq-item">
			<h4>Organization not appearing after discovery?</h4>
			<p>
				Ensure you have accepted the organization invitation on GitHub. Private organizations
				require explicit membership — ask an admin to add you.
			</p>
		</div>
		<div class="faq-item">
			<h4>OAuth callback error?</h4>
			<p>
				Clear your browser cookies for the WithOps domain and try again. If the issue persists,
				check that your Auth0 configuration includes the correct callback URLs.
			</p>
		</div>
		<div class="faq-item">
			<h4>Rate limiting issues?</h4>
			<p>
				WithOps caches GitHub API responses via Redis and implements token-bucket rate limiting
				(handles 700+ concurrent requests). If you encounter rate limits, wait a few minutes and
				retry.
			</p>
		</div>
	</div>

	<!-- Next -->
	<div class="next-step-card">
		<div class="next-step-text">
			<h3>Run Your First Scan</h3>
			<p>
				Now that your repositories are connected, run your first AI-powered security scan and see
				the results in real time.
			</p>
		</div>
		<a href="/docs/getting-started/first-security-scan" class="next-step-btn">
			Next: First Scan
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"><polyline points="9 18 15 12 9 6" /></svg
			>
		</a>
	</div>
</div>

<style>
	.gs-page {
		opacity: 0;
		transform: translateY(8px);
		transition: all 0.4s cubic-bezier(0.2, 0, 0, 1);
	}
	.gs-page.visible {
		opacity: 1;
		transform: translateY(0);
	}

	/* Page Header */
	.page-header {
		margin-bottom: 2.5rem;
		padding-bottom: 2rem;
		border-bottom: 1px solid var(--border);
	}

	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		margin-bottom: 1rem;
		font-size: 0.75rem;
		font-family: var(--font-mono);
	}

	.bc-muted {
		color: var(--text-muted);
	}
	.bc-sep {
		color: var(--text-muted);
	}
	.bc-current {
		color: var(--text-secondary);
	}
	.bc-link {
		color: var(--text-muted);
		text-decoration: none;
	}
	.bc-link:hover {
		color: var(--accent);
	}

	.page-title {
		font-family: var(--font-serif);
		font-size: 2.25rem;
		font-weight: 700;
		letter-spacing: -0.03em;
		line-height: 1.2;
		margin-bottom: 0.75rem;
		color: var(--text-primary);
	}

	.page-lead {
		font-size: 1.05rem;
		color: var(--text-secondary);
		line-height: 1.7;
		max-width: 640px;
		font-family: var(--font-serif);
	}

	h2 {
		font-family: var(--font-serif);
		font-size: 1.375rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		margin-top: 3rem;
		margin-bottom: 0.75rem;
		color: var(--text-primary);
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--border);
	}

	.body-text {
		font-size: 0.9rem;
		line-height: 1.75;
		color: var(--text-secondary);
		margin-bottom: 1.25rem;
		max-width: 640px;
	}

	/* ── Two-Col Method Cards ── */
	.two-col-cards {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.method-card {
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--bg-surface);
		transition: border-color 0.15s;
	}

	.method-card:hover {
		border-color: var(--border-strong);
	}

	.method-badge {
		display: inline-block;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		margin-bottom: 0.75rem;
	}

	.method-badge.oauth {
		background: rgba(167, 139, 250, 0.1);
		color: var(--accent);
		border: 1px solid var(--accent-border);
	}

	.method-badge.app {
		background: var(--callout-info-bg);
		color: var(--callout-info-text);
		border: 1px solid var(--callout-info-border);
	}

	.method-card h4 {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.375rem;
	}

	.method-card > p {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.55;
		margin-bottom: 0.75rem;
	}

	.method-features {
		list-style: none;
		padding: 0;
	}

	.method-features li {
		font-size: 0.775rem;
		color: var(--text-muted);
		padding: 0.2rem 0;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.method-features li::before {
		content: '';
		width: 4px;
		height: 4px;
		border-radius: 50%;
		background: var(--text-muted);
		flex-shrink: 0;
	}

	/* ── Instruction Blocks ── */
	.instruction-block {
		display: flex;
		gap: 1rem;
		padding: 1.25rem 0;
		border-bottom: 1px solid var(--border);
	}

	.instruction-block:last-of-type {
		border-bottom: none;
	}

	.instruction-number {
		flex-shrink: 0;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--accent-soft);
		border: 1px solid var(--accent-border);
		color: var(--accent);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.instruction-content {
		flex: 1;
		min-width: 0;
	}

	.instruction-content > p {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.6;
		margin-bottom: 0.75rem;
	}

	.instruction-content > p strong {
		color: var(--text-primary);
		font-weight: 600;
	}

	/* ── Scope List ── */
	.scope-list {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.scope-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--bg-surface);
		font-size: 0.8rem;
	}

	.scope-item code {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--accent);
		background: var(--accent-soft);
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		flex-shrink: 0;
	}

	.scope-item span {
		color: var(--text-secondary);
	}

	/* ── Feature Table ── */
	.feature-table {
		border: 1px solid var(--border);
		border-radius: 10px;
		overflow: hidden;
		margin: 0.5rem 0;
	}

	.ft-row {
		display: flex;
		gap: 1rem;
		padding: 0.75rem 1.25rem;
		border-bottom: 1px solid var(--border);
		align-items: baseline;
	}

	.ft-row:last-child {
		border-bottom: none;
	}

	.ft-label {
		font-size: 0.825rem;
		font-weight: 600;
		color: var(--text-primary);
		min-width: 120px;
		flex-shrink: 0;
	}

	.ft-desc {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	/* ── Callouts ── */
	.callout {
		display: flex;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		border-radius: 8px;
		margin: 1rem 0;
		border: 1px solid;
	}

	.callout-info {
		background: var(--callout-info-bg);
		border-color: var(--callout-info-border);
	}
	.callout-info .callout-icon {
		color: var(--callout-info-text);
	}
	.callout-tip {
		background: var(--callout-tip-bg);
		border-color: var(--callout-tip-border);
	}
	.callout-tip .callout-icon {
		color: var(--callout-tip-text);
	}

	.callout-icon {
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.callout-content strong {
		display: block;
		font-size: 0.825rem;
		color: var(--text-primary);
		margin-bottom: 0.25rem;
	}

	.callout-content p {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	/* ── App Permissions ── */
	.app-permissions {
		margin: 1.5rem 0;
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--bg-surface);
	}

	.app-permissions h4 {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	.app-permissions .body-text {
		margin-bottom: 0.75rem;
	}

	.perm-grid {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.perm-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 0.8rem;
	}

	.perm-level {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		flex-shrink: 0;
		min-width: 52px;
		text-align: center;
	}

	.perm-level.read {
		background: var(--callout-tip-bg);
		color: var(--callout-tip-text);
		border: 1px solid var(--callout-tip-border);
	}

	.perm-level.write {
		background: var(--callout-warn-bg);
		color: var(--callout-warn-text);
		border: 1px solid var(--callout-warn-border);
	}

	.perm-level.events {
		background: var(--accent-soft);
		color: var(--accent);
		border: 1px solid var(--accent-border);
	}

	.perm-item span {
		color: var(--text-secondary);
	}

	/* ── FAQ ── */
	.faq-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.faq-item {
		padding: 1rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--bg-surface);
	}

	.faq-item h4 {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.375rem;
	}

	.faq-item p {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.6;
	}

	/* ── Next Step Card ── */
	.next-step-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1.5rem;
		padding: 1.5rem 2rem;
		border: 1px solid var(--accent-border);
		border-radius: 12px;
		background: var(--accent-soft);
		margin-top: 3rem;
	}

	.next-step-text h3 {
		font-family: var(--font-serif);
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.25rem;
	}

	.next-step-text p {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	.next-step-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1.25rem;
		border-radius: 8px;
		background: var(--accent);
		color: white;
		font-size: 0.825rem;
		font-weight: 600;
		text-decoration: none;
		white-space: nowrap;
		transition: all 0.15s;
	}

	.next-step-btn:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	@media (max-width: 768px) {
		.page-title {
			font-size: 1.75rem;
		}
		.two-col-cards {
			grid-template-columns: 1fr;
		}
		.ft-row {
			flex-direction: column;
			gap: 0.25rem;
		}
		.next-step-card {
			flex-direction: column;
			text-align: center;
		}
	}
</style>
