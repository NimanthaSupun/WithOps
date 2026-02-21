<script>
	import { onMount } from 'svelte';

	let visible = $state(false);
	let activeTab = $state('cloud');

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
			<span class="bc-current">Quick Start</span>
		</div>
		<h1 class="page-title" id="quick-start">Quick Start</h1>
		<p class="page-lead">
			Get up and running with WithOps in under 2 minutes. Choose your deployment model and follow
			the steps below.
		</p>
	</div>

	<!-- Deployment Toggle -->
	<h2 id="choose-deployment">Choose Your Deployment</h2>

	<div class="tab-switcher">
		<button
			class="tab-btn {activeTab === 'cloud' ? 'active' : ''}"
			onclick={() => (activeTab = 'cloud')}
		>
			<svg
				width="14"
				height="14"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
			</svg>
			Cloud (Recommended)
		</button>
		<button
			class="tab-btn {activeTab === 'selfhost' ? 'active' : ''}"
			onclick={() => (activeTab = 'selfhost')}
		>
			<svg
				width="14"
				height="14"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<rect x="2" y="2" width="20" height="8" rx="2" ry="2" /><rect
					x="2"
					y="14"
					width="20"
					height="8"
					rx="2"
					ry="2"
				/><line x1="6" y1="6" x2="6.01" y2="6" /><line x1="6" y1="18" x2="6.01" y2="18" />
			</svg>
			Self-Hosted
		</button>
	</div>

	{#if activeTab === 'cloud'}
		<!-- CLOUD PATH -->
		<h2 id="step-1-sign-up">Step 1 — Sign Up</h2>
		<p class="body-text">
			Navigate to the WithOps platform and create your account using GitHub OAuth. This
			automatically links your GitHub identity.
		</p>

		<div class="instruction-block">
			<div class="instruction-number">1</div>
			<div class="instruction-content">
				<p>Visit the WithOps landing page and click <strong>"Connect GitHub"</strong></p>
				<div class="code-block">
					<div class="code-header">
						<span class="code-lang">URL</span>
					</div>
					<pre><code>https://your-withops-instance.com</code></pre>
				</div>
			</div>
		</div>

		<div class="instruction-block">
			<div class="instruction-number">2</div>
			<div class="instruction-content">
				<p>Authorize WithOps via Auth0. You'll be redirected to GitHub for OAuth consent.</p>
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
						<strong>Secure by default</strong>
						<p>
							WithOps uses Auth0 with RS256 JWT tokens. Your credentials are never stored on our
							servers.
						</p>
					</div>
				</div>
			</div>
		</div>

		<div class="instruction-block">
			<div class="instruction-number">3</div>
			<div class="instruction-content">
				<p>
					After authorization, you'll land on your <strong>Dashboard</strong> — your central command
					center.
				</p>
			</div>
		</div>

		<h2 id="step-2-explore">Step 2 — Explore the Dashboard</h2>
		<p class="body-text">
			The dashboard surfaces your security posture at a glance. Here's what you'll see:
		</p>

		<div class="feature-table">
			<div class="ft-row">
				<div class="ft-label">GitHub Connectivity</div>
				<div class="ft-desc">
					Connection status, organization discovery, and account verification
				</div>
			</div>
			<div class="ft-row">
				<div class="ft-label">Command Center</div>
				<div class="ft-desc">
					Multi-org policy management, aggregated security insights, and team governance
				</div>
			</div>
			<div class="ft-row">
				<div class="ft-label">System Status</div>
				<div class="ft-desc">
					Real-time health monitoring of all connected services and pipelines
				</div>
			</div>
		</div>
	{:else}
		<!-- SELF-HOSTED PATH -->
		<h2 id="step-1-requirements">Step 1 — System Requirements</h2>
		<p class="body-text">To self-host WithOps, you'll need the following infrastructure:</p>

		<div class="prereq-list">
			<div class="prereq-item">
				<div class="prereq-check">
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2.5"><polyline points="20 6 9 17 4 12" /></svg
					>
				</div>
				<div>
					<strong>Docker & Docker Compose</strong>
					<span class="prereq-detail">— v24+ with Compose v2</span>
				</div>
			</div>
			<div class="prereq-item">
				<div class="prereq-check">
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2.5"><polyline points="20 6 9 17 4 12" /></svg
					>
				</div>
				<div>
					<strong>8GB RAM minimum</strong>
					<span class="prereq-detail">— 16GB recommended for AI services + Ollama</span>
				</div>
			</div>
			<div class="prereq-item">
				<div class="prereq-check">
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2.5"><polyline points="20 6 9 17 4 12" /></svg
					>
				</div>
				<div>
					<strong>Node.js 18+ & Python 3.11+</strong>
					<span class="prereq-detail">— for frontend and backend services</span>
				</div>
			</div>
		</div>

		<h2 id="step-2-docker-compose">Step 2 — Launch with Docker Compose</h2>
		<p class="body-text">Clone the repository and start all services with a single command:</p>

		<div class="code-block">
			<div class="code-header">
				<span class="code-lang">Terminal</span>
				<button
					class="code-copy"
					onclick={(e) => {
						navigator.clipboard.writeText(
							'git clone https://github.com/your-org/withops.git\ncd withops\ndocker-compose up -d'
						);
						e.target.textContent = 'Copied!';
						setTimeout(() => (e.target.textContent = 'Copy'), 1500);
					}}>Copy</button
				>
			</div>
			<pre><code
					><span class="code-comment"># Clone the repository</span>
<span class="code-cmd">git clone</span> https://github.com/your-org/withops.git
<span class="code-cmd">cd</span> withops

<span class="code-comment"># Start all services</span>
<span class="code-cmd">docker-compose</span> up -d</code
				></pre>
		</div>

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
				<strong>Service Ports</strong>
				<p>
					Frontend runs on :5173, Kong Gateway on :9000, and microservices on the 91xx range. See
					Deployment docs for the full port map.
				</p>
			</div>
		</div>

		<h2 id="step-3-configure">Step 3 — Configure Environment</h2>
		<p class="body-text">Copy the environment template and fill in your credentials:</p>

		<div class="code-block">
			<div class="code-header">
				<span class="code-lang">Terminal</span>
			</div>
			<pre><code
					><span class="code-cmd">cp</span> .env.example .env

<span class="code-comment"># Required variables:</span>
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
GITHUB_APP_ID=your-github-app-id</code
				></pre>
		</div>
	{/if}

	<!-- Common Next Steps -->
	<h2 id="whats-next">What's Next</h2>
	<p class="body-text">
		Now that you're in the platform, the next step is to connect your GitHub organizations for
		automated security scanning.
	</p>

	<div class="next-step-card">
		<div class="next-step-text">
			<h3>Connect Your GitHub Account</h3>
			<p>
				Link your organizations and repositories to enable automated vulnerability scanning and
				workflow monitoring.
			</p>
		</div>
		<a href="/docs/getting-started/connecting-github" class="next-step-btn">
			Next: Connect GitHub
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
	/* ═══════════════════════════════
	   QUICK START PAGE
	   ═══════════════════════════════ */

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

	/* ── Tab Switcher ── */
	.tab-switcher {
		display: flex;
		gap: 0.375rem;
		padding: 0.25rem;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		border-radius: 10px;
		margin-bottom: 0.5rem;
		width: fit-content;
	}

	.tab-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		border: 1px solid transparent;
		border-radius: 7px;
		background: transparent;
		color: var(--text-secondary);
		font-size: 0.8rem;
		font-weight: 550;
		cursor: pointer;
		font-family: var(--font-sans);
		transition: all 0.15s;
	}

	.tab-btn:hover {
		color: var(--text-primary);
	}

	.tab-btn.active {
		background: var(--bg-surface);
		border-color: var(--border);
		color: var(--text-primary);
		box-shadow: var(--shadow-sm);
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

	/* ── Code Blocks ── */
	.code-block {
		border: 1px solid var(--code-border);
		border-radius: 8px;
		overflow: hidden;
		margin: 0.75rem 0;
		background: var(--code-bg);
	}

	.code-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 0.875rem;
		border-bottom: 1px solid var(--code-border);
		background: var(--bg-surface-2);
	}

	.code-lang {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.code-copy {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 0.15rem 0.5rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.code-copy:hover {
		color: var(--text-primary);
		border-color: var(--border-strong);
	}

	pre {
		padding: 1rem;
		overflow-x: auto;
		margin: 0;
	}

	code {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		line-height: 1.7;
		color: var(--text-primary);
	}

	.code-comment {
		color: var(--text-muted);
	}
	.code-cmd {
		color: var(--accent);
		font-weight: 500;
	}

	/* ── Feature Table ── */
	.feature-table {
		border: 1px solid var(--border);
		border-radius: 10px;
		overflow: hidden;
		margin: 1rem 0;
	}

	.ft-row {
		display: flex;
		gap: 1rem;
		padding: 0.875rem 1.25rem;
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
		min-width: 160px;
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

	/* ── Prerequisites ── */
	.prereq-list {
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
		margin-bottom: 0.5rem;
	}

	.prereq-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-surface);
		font-size: 0.85rem;
	}

	.prereq-check {
		flex-shrink: 0;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: var(--callout-tip-bg);
		border: 1px solid var(--callout-tip-border);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--callout-tip-text);
	}

	.prereq-item strong {
		color: var(--text-primary);
		font-weight: 600;
	}
	.prereq-detail {
		color: var(--text-muted);
		font-size: 0.8rem;
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
		margin-top: 2rem;
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
		.tab-switcher {
			width: 100%;
		}
		.tab-btn {
			flex: 1;
			justify-content: center;
		}
		.ft-row {
			flex-direction: column;
			gap: 0.25rem;
		}
		.ft-label {
			min-width: unset;
		}
		.next-step-card {
			flex-direction: column;
			text-align: center;
		}
	}
</style>
