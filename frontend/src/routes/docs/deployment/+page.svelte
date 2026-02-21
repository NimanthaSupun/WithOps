<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<svelte:head>
	<title>Deployment Guide — WithOps Documentation</title>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Docs</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Deployment Guide</span>
	</div>

	<div class="chapter-tag">
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
			<line x1="7" y1="2" x2="7" y2="22" /><line x1="17" y1="2" x2="17" y2="22" />
			<line x1="2" y1="12" x2="22" y2="12" /><line x1="2" y1="7" x2="22" y2="7" />
			<line x1="2" y1="17" x2="22" y2="17" />
		</svg>
		Infrastructure
	</div>

	<h1 class="page-title" id="deployment-guide">Deployment Guide</h1>
	<p class="page-subtitle">
		Strategies for deploying WithOps in development, staging, and production environments.
	</p>

	<hr class="divider" />

	<div class="prose">
		<h2 id="development" class="section-heading">Development Environment</h2>
		<p>
			The simplest way to run WithOps locally is using **Docker Compose**. This spins up all 9 microservices, the Kong Gateway, and the observability stack.
		</p>
		<div class="code-block">
			<pre><code>docker compose up -d</code></pre>
		</div>

		<h2 id="staging" class="section-heading">Staging & Production</h2>
		<p>
			For production workloads, we recommend **Kubernetes** for orchestration and high availability.
		</p>
		
		<h3 id="kubernetes">Kubernetes (Helm)</h3>
		<p>The WithOps Helm chart simplifies deployment to EKS, GKE, or AKS.</p>
		<div class="code-block">
			<pre><code>helm install withops ./charts/withops -f values.prod.yaml</code></pre>
		</div>

		<h2 id="secrets-management" class="section-heading">Secrets Management</h2>
		<p>
			Never use plain text environment variables in production. Use a secure vault:
		</p>
		<ul>
			<li><strong>AWS Secrets Manager:</strong> Integrated via IAM roles.</li>
			<li><strong>HashiCorp Vault:</strong> For multi-cloud deployments.</li>
			<li><strong>GitHub Actions Secrets:</strong> For automated CI/CD pipelines.</li>
		</ul>

		<div class="callout warn">
			<div class="callout-icon">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
				</svg>
			</div>
			<div class="callout-content">
				<div class="callout-label">Production Checklist</div>
				<p>Ensure SSL termination at Kong Gateway, enable RBAC in the Auth Service, and configure persistent volume backups for PostgreSQL and Qdrant.</p>
			</div>
		</div>
	</div>

	<div class="page-nav">
		<a href="/docs/api" class="page-nav-btn prev">
			<span class="page-nav-label">← Previous</span>
			<span class="page-nav-title">API Reference</span>
		</a>
		<a href="/docs/getting-started" class="page-nav-btn next">
			<span class="page-nav-label">Next →</span>
			<span class="page-nav-title">Introduction</span>
		</a>
	</div>
</div>

<style>
	.getting-started { opacity: 0; transform: translateY(10px); transition: all 0.5s ease; }
	.getting-started.visible { opacity: 1; transform: translateY(0); }
	.breadcrumb { display: flex; align-items: center; gap: 8px; font-family: 'DM Mono', monospace; font-size: 11px; margin-bottom: 24px; }
	.bc-link { color: var(--text-muted); text-decoration: none; }
	.bc-current { color: var(--accent); }
	.chapter-tag { font-family: 'DM Mono', monospace; font-size: 11px; color: var(--accent); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
	.page-title { font-family: 'Playfair Display', serif; font-size: 38px; font-weight: 700; color: var(--text-primary); }
	.page-subtitle { font-family: 'Lora', serif; font-style: italic; font-size: 15px; color: var(--text-secondary); }
	.divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
	.section-heading { font-family: 'Playfair Display', serif; font-size: 22px; font-weight: 700; margin: 40px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
	.prose p { font-family: 'Lora', serif; font-size: 15px; margin-bottom: 16px; line-height: 1.85; }
	.code-block { background: var(--code-bg); border-radius: 6px; margin: 16px 0; border: 1px solid var(--code-border); padding: 16px; }
	pre { color: var(--code-text); font-family: 'DM Mono', monospace; font-size: 13px; margin: 0; }
	
	.callout { display: flex; gap: 14px; padding: 16px 20px; background: var(--callout-warn-bg); border-left: 3px solid var(--callout-warn-border); border-radius: 0 6px 6px 0; margin: 24px 0; }
	.callout-icon { color: var(--callout-warn-text); }
	.callout-label { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--callout-warn-text); text-transform: uppercase; margin-bottom: 4px; }

	.page-nav { display: flex; justify-content: space-between; margin-top: 40px; border-top: 1px solid var(--border); padding-top: 20px; }
	.page-nav-btn { text-decoration: none; }
	.page-nav-label { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--text-muted); }
	.page-nav-title { font-family: 'Lora', serif; display: block; color: var(--text-secondary); }
</style>
