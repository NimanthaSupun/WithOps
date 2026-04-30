<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<svelte:head>
	<title>API Reference — WithOps Documentation</title>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Docs</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">API Reference</span>
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
			<polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
		</svg>
		Technical Reference
	</div>

	<h1 class="page-title" id="api-reference">API Reference</h1>
	<p class="page-subtitle">
		Detailed documentation for the WithOps microservices REST and WebSocket endpoints.
	</p>

	<hr class="divider" />

	<div class="prose">
		<h2 id="authentication" class="section-heading">Authentication</h2>
		<p>
			All API requests must be authenticated using a **Bearer JWT Token** in the `Authorization`
			header. Tokens are issued by the platform's Auth0 integration and are validated by the Kong
			API Gateway.
		</p>
		<div class="code-block">
			<pre><code>Authorization: Bearer &lt;your_jwt_token&gt;</code></pre>
		</div>

		<h2 id="base-urls" class="section-heading">Base URLs</h2>
		<div class="perm-table">
			<div class="perm-header">
				<span>Service</span>
				<span>Gateway Path</span>
				<span>Direct Port</span>
			</div>
			<div class="perm-row">
				<span class="perm-name">Kong Gateway</span>
				<span>`/api/*`</span>
				<span>9000</span>
			</div>
			<div class="perm-row">
				<span class="perm-name">AI Service</span>
				<span>`/api/ai/*`</span>
				<span>9101</span>
			</div>
			<div class="perm-row">
				<span class="perm-name">GitHub Service</span>
				<span>`/api/github/*`</span>
				<span>9102</span>
			</div>
			<div class="perm-row">
				<span class="perm-name">Threat Modeling</span>
				<span>`/api/threats/*`</span>
				<span>9103</span>
			</div>
		</div>

		<h2 id="ai-service" class="section-heading">AI Service (9101)</h2>
		<div class="endpoint-item">
			<span class="method post">POST</span>
			<code class="path">/api/ai/analyze</code>
			<p>Analyze code for security issues and vulnerabilities.</p>
		</div>
		<div class="endpoint-item">
			<span class="method post">POST</span>
			<code class="path">/api/ai/chat</code>
			<p>Interactive AI assistance with DevSecOps context.</p>
		</div>

		<h2 id="github-service" class="section-heading">GitHub Service (9102)</h2>
		<div class="endpoint-item">
			<span class="method get">GET</span>
			<code class="path">/api/github/organisations</code>
			<p>List user organizations from GitHub.</p>
		</div>
		<div class="endpoint-item">
			<span class="method get">GET</span>
			<code class="path">/api/github/repositories</code>
			<p>List repositories with security metadata.</p>
		</div>

		<h2 id="events-hub" class="section-heading">Events Hub (WebSocket)</h2>
		<p>Real-time events are streamed via WebSockets on port **9100**.</p>
		<div class="code-block">
			<pre><code>ws://localhost:9000/api/events/ws</code></pre>
		</div>

		<h3 id="event-types">Common Event Types</h3>
		<ul>
			<li>
				<code>threat.analysis.completed</code>: Triggered when an AI threat analysis finishes.
			</li>
			<li><code>scan.complete</code>: Triggered when a vulnerability scan is done.</li>
			<li><code>pr.created</code>: Triggered when an automated remediation PR is opened.</li>
		</ul>
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
	}
	.bc-current {
		color: var(--accent);
	}
	.chapter-tag {
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		color: var(--accent);
		margin-bottom: 12px;
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.page-title {
		font-family: 'Playfair Display', serif;
		font-size: 38px;
		font-weight: 700;
		color: var(--text-primary);
	}
	.page-subtitle {
		font-family: 'Lora', serif;
		font-style: italic;
		font-size: 15px;
		color: var(--text-secondary);
	}
	.divider {
		border: none;
		border-top: 1px solid var(--border);
		margin: 24px 0;
	}
	.perm-table {
		margin: 24px 0 40px;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
		background: var(--bg-surface);
	}
	.perm-header {
		display: grid;
		grid-template-columns: 180px 180px 1fr;
		gap: 12px;
		padding: 12px 20px;
		background: var(--bg-surface-2);
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.perm-row {
		display: grid;
		grid-template-columns: 180px 180px 1fr;
		gap: 12px;
		padding: 12px 20px;
		border-top: 1px solid var(--border);
		transition: background 0.15s;
	}
	.perm-row:hover {
		background: var(--bg-surface-2);
	}
	.perm-name {
		font-weight: 600;
		font-size: 13px;
		color: var(--text-primary);
	}

	.endpoint-item {
		display: flex;
		align-items: center;
		gap: 16px;
		padding: 14px 20px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		margin-bottom: 12px;
		transition: all 0.2s;
	}
	.endpoint-item:hover {
		border-color: var(--accent);
		transform: translateX(4px);
		background: var(--bg-surface-2);
	}
	.method {
		font-family: 'DM Mono', monospace;
		font-size: 9px;
		font-weight: 800;
		padding: 4px 8px;
		border-radius: 4px;
		color: white;
		width: 50px;
		text-align: center;
		letter-spacing: 0.05em;
	}
	.method.post {
		background: #10b981;
		box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
	}
	.method.get {
		background: #00adef;
		box-shadow: 0 2px 8px rgba(0, 173, 239, 0.2);
	}
	.path {
		font-family: 'DM Mono', monospace;
		font-size: 13px;
		color: var(--text-primary);
		font-weight: 500;
	}
	.endpoint-item p {
		font-family: 'Lora', serif;
		font-size: 13px;
		color: var(--text-secondary);
		margin: 0;
		flex: 1;
		text-align: right;
	}
</style>
