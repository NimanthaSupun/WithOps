<script>
	import { onMount } from 'svelte';

	let visible = $state(false);
	let copiedStates = $state({});
	let activeTab = $state('cloud');

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
	<title>Quick Start — WithOps Documentation</title>
	<meta
		name="description"
		content="Get WithOps running in under 5 minutes. Choose between cloud-hosted or self-hosted deployment with Docker Compose."
	/>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<!-- Breadcrumb -->
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Getting Started</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Quick Start</span>
	</div>

	<!-- Chapter tag -->
	<div class="chapter-tag">
		<svg
			width="14"
			height="14"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
		>
			<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
		</svg>
		Chapter II
	</div>

	<h1 class="page-title" id="quick-start">Quick Start</h1>
	<p class="page-subtitle">
		Get the platform running in under five minutes — choose cloud-hosted for instant access or
		self-hosted for full control.
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
			6 min read
		</span>
		<span class="meta-tag">Setup</span>
		<span class="meta-tag">Docker</span>
	</div>

	<!-- Deployment Mode Tabs -->
	<h2 class="section-heading" id="choose-deployment">Choose Your Deployment</h2>
	<p class="prose-text">
		WithOps supports two deployment modes. Pick the one that suits your needs — you can always
		switch later.
	</p>

	<div class="deploy-tabs">
		<button
			class="deploy-tab {activeTab === 'cloud' ? 'active' : ''}"
			onclick={() => (activeTab = 'cloud')}
		>
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<path d="M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z" />
			</svg>
			Cloud Hosted
		</button>
		<button
			class="deploy-tab {activeTab === 'self' ? 'active' : ''}"
			onclick={() => (activeTab = 'self')}
		>
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<rect x="2" y="2" width="20" height="8" rx="2" /><rect
					x="2"
					y="14"
					width="20"
					height="8"
					rx="2"
				/>
				<circle cx="6" cy="6" r="1" /><circle cx="6" cy="18" r="1" />
			</svg>
			Self-Hosted
		</button>
	</div>

	<!-- Cloud Hosted Tab -->
	{#if activeTab === 'cloud'}
		<div class="tab-panel" id="cloud-setup">
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
					<div class="callout-label">Fastest option</div>
					<p>
						Cloud-hosted requires no infrastructure setup. You'll be scanning repositories within 2
						minutes.
					</p>
				</div>
			</div>

			<div class="steps">
				<div class="step-card">
					<div class="step-num">1</div>
					<div class="step-body">
						<h4>Create your account</h4>
						<p>
							Navigate to <code>app.withops.io</code> and click <strong>"Get Started"</strong>. Sign
							up using your email address or authenticate directly with GitHub.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">2</div>
					<div class="step-body">
						<h4>Authorise GitHub</h4>
						<p>
							After account creation, you'll be prompted to connect your GitHub account. Click <strong
								>"Connect GitHub"</strong
							> and authorise the WithOps GitHub App. Select which repositories to grant access to.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">3</div>
					<div class="step-body">
						<h4>Select a workspace</h4>
						<p>
							Choose a repository to create your first workspace. WithOps will automatically analyse
							its structure, dependencies, and security posture.
						</p>
					</div>
				</div>

				<div class="step-card">
					<div class="step-num">4</div>
					<div class="step-body">
						<h4>Run your first scan</h4>
						<p>
							Navigate to the <strong>Security</strong> tab and click
							<strong>"Run Full Scan"</strong>. The AI-powered analysis will complete within 30–90
							seconds depending on repository size.
						</p>
					</div>
				</div>
			</div>

			<p class="prose-text">
				That's it — you're ready to explore your security dashboard. See <a
					href="/docs/getting-started/first-security-scan">First Security Scan</a
				> for a detailed walkthrough of scan results.
			</p>
		</div>
	{/if}

	<!-- Self-Hosted Tab -->
	{#if activeTab === 'self'}
		<div class="tab-panel" id="self-hosted-setup">
			<h3 id="system-requirements">System Requirements</h3>
			<div class="req-grid">
				<div class="req-item">
					<span class="req-label">OS</span>
					<span class="req-value">Linux, macOS, or WSL2</span>
				</div>
				<div class="req-item">
					<span class="req-label">Docker</span>
					<span class="req-value">24.0+ with Compose v2</span>
				</div>
				<div class="req-item">
					<span class="req-label">RAM</span>
					<span class="req-value">8 GB minimum, 16 GB recommended</span>
				</div>
				<div class="req-item">
					<span class="req-label">Disk</span>
					<span class="req-value">20 GB free space</span>
				</div>
				<div class="req-item">
					<span class="req-label">Node.js</span>
					<span class="req-value">18.x or 20.x LTS</span>
				</div>
				<div class="req-item">
					<span class="req-label">Python</span>
					<span class="req-value">3.11+</span>
				</div>
			</div>

			<h3 id="clone-and-configure">Step 1 — Clone &amp; Configure</h3>
			<div class="code-block">
				<div class="code-header">
					<span class="code-lang">bash</span>
					<button
						class="copy-btn"
						onclick={() =>
							copyCode('clone', 'git clone https://github.com/withops/platform.git\ncd platform')}
					>
						{copiedStates['clone'] ? '✓ Copied' : 'Copy'}
					</button>
				</div>
				<pre><code
						><span class="cm"># Clone the WithOps platform</span>
<span class="fn">git</span> clone https://github.com/withops/platform.git
<span class="fn">cd</span> platform</code
					></pre>
			</div>

			<h3 id="environment-setup">Step 2 — Environment Variables</h3>
			<p class="prose-text">Copy the example environment file and fill in your credentials:</p>
			<div class="code-block">
				<div class="code-header">
					<span class="code-lang">bash</span>
					<button class="copy-btn" onclick={() => copyCode('env', 'cp .env.example .env')}>
						{copiedStates['env'] ? '✓ Copied' : 'Copy'}
					</button>
				</div>
				<pre><code><span class="fn">cp</span> .env.example .env</code></pre>
			</div>

			<p class="prose-text">Open <code>.env</code> and configure the required variables:</p>

			<div class="code-block">
				<div class="code-header">
					<span class="code-lang">.env</span>
					<button class="copy-btn" onclick={() => copyCode('envfile', '')}>
						{copiedStates['envfile'] ? '✓ Copied' : 'Copy'}
					</button>
				</div>
				<pre><code
						><span class="cm"># ─── Authentication (Auth0) ───</span>
<span class="kw">AUTH0_DOMAIN</span>=<span class="str">your-tenant.auth0.com</span>
<span class="kw">AUTH0_CLIENT_ID</span>=<span class="str">your_client_id</span>
<span class="kw">AUTH0_CLIENT_SECRET</span>=<span class="str">your_client_secret</span>
<span class="kw">AUTH0_AUDIENCE</span>=<span class="str">https://api.withops.com</span>

<span class="cm"># ─── GitHub Integration ───</span>
<span class="kw">GITHUB_CLIENT_ID</span>=<span class="str">your_github_client_id</span>
<span class="kw">GITHUB_CLIENT_SECRET</span>=<span class="str">your_github_secret</span>

<span class="cm"># ─── Database ───</span>
<span class="kw">SUPABASE_URL</span>=<span class="str">https://your-project.supabase.co</span>
<span class="kw">SUPABASE_KEY</span>=<span class="str">your_supabase_key</span>
<span class="kw">SUPABASE_DATABASE_URL</span>=<span class="str"
							>postgresql://postgres:[password]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres</span
						>
<span class="kw">DATABASE_URL</span>=<span class="str">postgresql://user:pass@db:5432/withops</span>

<span class="cm"># ─── AI Providers ───</span>
<span class="kw">OPENAI_API_KEY</span>=<span class="str">sk-your-openai-key</span>
<span class="kw">ANTHROPIC_API_KEY</span>=<span class="str">sk-ant-your-key</span>
<span class="kw">GROQ_API_KEY</span>=<span class="str">gsk_your_groq_key</span></code
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
					<div class="callout-label">Security</div>
					<p>
						Never commit <code>.env</code> to version control. The file is already included in
						<code>.gitignore</code>.
					</p>
				</div>
			</div>

			<h3 id="start-services">Step 3 — Start All Services</h3>
			<div class="code-block">
				<div class="code-header">
					<span class="code-lang">bash</span>
					<button class="copy-btn" onclick={() => copyCode('start', 'docker compose up -d')}>
						{copiedStates['start'] ? '✓ Copied' : 'Copy'}
					</button>
				</div>
				<pre><code
						><span class="cm"># Start all 9 microservices + infrastructure</span>
<span class="fn">docker</span> compose up -d

<span class="cm"># Watch logs in real-time</span>
<span class="fn">docker</span> compose logs -f

<span class="cm"># Verify all services are healthy</span>
<span class="fn">docker</span> compose ps</code
					></pre>
			</div>

			<h3 id="verify-services">Step 4 — Verify Services</h3>
			<p class="prose-text">Confirm each service is reachable by running health checks:</p>

			<div class="service-health-grid">
				<div class="health-row">
					<span class="health-name">Frontend</span>
					<code class="health-url">http://localhost:5173</code>
					<span class="health-badge ok">Ready</span>
				</div>
				<div class="health-row">
					<span class="health-name">API Gateway</span>
					<code class="health-url">http://localhost:9000</code>
					<span class="health-badge ok">Ready</span>
				</div>
				<div class="health-row">
					<span class="health-name">Events Hub</span>
					<code class="health-url">http://localhost:9100/health</code>
					<span class="health-badge ok">Ready</span>
				</div>
				<div class="health-row">
					<span class="health-name">AI Service</span>
					<code class="health-url">http://localhost:9101/health</code>
					<span class="health-badge ok">Ready</span>
				</div>
				<div class="health-row">
					<span class="health-name">GitHub Service</span>
					<code class="health-url">http://localhost:9102/health</code>
					<span class="health-badge ok">Ready</span>
				</div>
				<div class="health-row">
					<span class="health-name">Threat Modeling</span>
					<code class="health-url">http://localhost:9103/health</code>
					<span class="health-badge ok">Ready</span>
				</div>
				<div class="health-row">
					<span class="health-name">Workflow Orch.</span>
					<code class="health-url">http://localhost:9107/health</code>
					<span class="health-badge ok">Ready</span>
				</div>
				<div class="health-row">
					<span class="health-name">AI RAG Service</span>
					<code class="health-url">http://localhost:9108/health</code>
					<span class="health-badge ok">Ready</span>
				</div>
				<div class="health-row">
					<span class="health-name">Grafana</span>
					<code class="health-url">http://localhost:3001</code>
					<span class="health-badge ok">Ready</span>
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
					<div class="callout-label">Troubleshooting</div>
					<p>
						If a service shows as unhealthy, check its container logs with <code
							>docker compose logs &lt;service-name&gt;</code
						>. Common issues include missing environment variables and port conflicts.
					</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Common Configurations -->
	<h2 class="section-heading" id="initial-configuration">Initial Configuration</h2>
	<p class="prose-text">
		After your platform is running (cloud or self-hosted), complete these one-time configuration
		steps.
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
					<circle cx="12" cy="7" r="4" /><path d="M5.5 21a6.5 6.5 0 0113 0" />
				</svg>
			</div>
			<div>
				<strong>Set up your profile</strong>
				<p>
					Add your name, avatar, and notification preferences in <strong>Settings → Profile</strong
					>.
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
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
				</svg>
			</div>
			<div>
				<strong>Configure scan defaults</strong>
				<p>
					Choose default scan types (SAST, Dependencies, Secrets, STRIDE) in <strong
						>Settings → Security</strong
					>.
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
					<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" />
				</svg>
			</div>
			<div>
				<strong>Enable notifications</strong>
				<p>
					Set up email or Slack alerts for critical vulnerabilities in <strong
						>Settings → Notifications</strong
					>.
				</p>
			</div>
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

	.prose-text {
		font-family: 'Lora', serif;
		font-size: 15px;
		line-height: 1.85;
		color: var(--text-primary);
		margin-bottom: 16px;
	}
	.prose-text a {
		color: var(--accent);
		text-decoration: none;
	}
	.prose-text a:hover {
		text-decoration: underline;
	}
	.prose-text code {
		font-family: 'DM Mono', monospace;
		font-size: 12px;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		padding: 1px 5px;
		border-radius: 3px;
		color: var(--accent);
	}

	/* Deploy Tabs */
	.deploy-tabs {
		display: flex;
		gap: 8px;
		margin: 16px 0 24px;
	}
	.deploy-tab {
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
	.deploy-tab:hover {
		border-color: var(--border-focus);
		color: var(--text-primary);
	}
	.deploy-tab.active {
		background: var(--accent-subtle);
		border-color: var(--accent);
		color: var(--accent);
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
	.step-body code {
		font-family: 'DM Mono', monospace;
		font-size: 12px;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		padding: 1px 5px;
		border-radius: 3px;
		color: var(--accent);
	}
	.step-body strong {
		font-weight: 600;
		color: var(--text-primary);
	}

	/* Requirements Grid */
	h3 {
		font-family: 'Lora', serif;
		font-size: 17px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 28px 0 12px;
	}
	.req-grid {
		display: grid;
		grid-template-columns: 1fr 1fr 1fr;
		gap: 8px;
		margin: 12px 0 24px;
	}
	.req-item {
		padding: 12px 14px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 4px;
	}
	.req-label {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		color: var(--accent);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		display: block;
		margin-bottom: 4px;
	}
	.req-value {
		font-family: 'Lora', serif;
		font-size: 12.5px;
		color: var(--text-secondary);
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
	.fn {
		color: #8bb8d4;
	}

	/* Service health */
	.service-health-grid {
		display: flex;
		flex-direction: column;
		gap: 6px;
		margin: 16px 0 24px;
	}
	.health-row {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 4px;
	}
	.health-name {
		font-family: 'Inter', sans-serif;
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		width: 120px;
		flex-shrink: 0;
	}
	.health-url {
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		color: var(--text-muted);
		flex: 1;
	}
	.health-badge {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		padding: 2px 8px;
		border-radius: 3px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.health-badge.ok {
		background: rgba(16, 185, 129, 0.08);
		color: var(--success);
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

	/* Callout */
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
	.callout-content code {
		font-family: 'DM Mono', monospace;
		font-size: 12px;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		padding: 1px 5px;
		border-radius: 3px;
		color: var(--accent);
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
		.req-grid {
			grid-template-columns: 1fr;
		}
		.deploy-tabs {
			flex-direction: column;
		}
		.health-name {
			width: auto;
		}
		.health-url {
			display: none;
		}
	}
</style>
