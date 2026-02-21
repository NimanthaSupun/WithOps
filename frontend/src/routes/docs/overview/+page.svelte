<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<svelte:head>
	<title>Platform Overview — WithOps Documentation</title>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Docs</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Platform Overview</span>
	</div>

	<div class="chapter-tag">
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
		</svg>
		System Architecture
	</div>

	<h1 class="page-title" id="overview">Platform Overview</h1>
	<p class="page-subtitle">
		A deep dive into the WithOps microservices architecture, event-driven design, and observability stack.
	</p>

	<hr class="divider" />

	<div class="prose">
		<h2 id="architecture-principles" class="section-heading">Architecture Principles</h2>
		<p>
			WithOps is built on a modern, distributed microservices architecture designed for extreme isolation, scalability, and resilience.
		</p>
		<ul>
			<li><strong>Service Isolation:</strong> Each microservice owns its business domain and database schema.</li>
			<li><strong>Event-Driven Communication:</strong> Services use a Redis Pub/Sub event bus for loose coupling.</li>
			<li><strong>API Gateway Pattern:</strong> A Kong Gateway provides a single, secure entry point for all client requests.</li>
			<li><strong>Observability First:</strong> Built-in support for distributed tracing (Jaeger), metrics (Prometheus), and centralized logging (Loki).</li>
		</ul>

		<h2 id="system-diagram" class="section-heading">System Architecture</h2>
			<div class="arch-container">
				<!-- Users -->
				<div class="arch-box">
					<span class="arch-title">Entry Layer</span>
					<span class="arch-name">Users & Clients</span>
					<span class="arch-details">Web Browsers, Mobile Apps, CLI Tools</span>
				</div>

				<div class="arch-connector"></div>

				<!-- Frontend -->
				<div class="arch-box">
					<span class="arch-title">Frontend Layer</span>
					<span class="arch-name">SvelteKit Application</span>
					<span class="arch-details">Port 5173 · UI Components · WebSocket Client</span>
				</div>

				<div class="arch-connector"></div>

				<!-- Gateway -->
				<div class="arch-box">
					<span class="arch-title">Gateway Layer</span>
					<span class="arch-name">Kong API Gateway</span>
					<span class="arch-details">Port 8000 · Auth · Routing · Rate Limiting</span>
				</div>

				<div class="arch-multi-connector"></div>

				<!-- Microservices -->
				<div class="arch-box microservices">
					<span class="arch-title">Microservices Layer</span>
					<span class="arch-name">Core Domain Services</span>
					
					<div class="arch-grid">
						<div class="arch-sub-box">
							<span class="arch-sub-name">Auth</span>
							<span class="arch-sub-port">9106</span>
						</div>
						<div class="arch-sub-box">
							<span class="arch-sub-name">GitHub</span>
							<span class="arch-sub-port">9102</span>
						</div>
						<div class="arch-sub-box">
							<span class="arch-sub-name">AI Engine</span>
							<span class="arch-sub-port">8101</span>
						</div>
						<div class="arch-sub-box">
							<span class="arch-sub-name">Threat</span>
							<span class="arch-sub-port">9103</span>
						</div>
						<div class="arch-sub-box">
							<span class="arch-sub-name">Workspace</span>
							<span class="arch-sub-port">9104</span>
						</div>
						<div class="arch-sub-box">
							<span class="arch-sub-name">Collab</span>
							<span class="arch-sub-port">9105</span>
						</div>
						<div class="arch-sub-box">
							<span class="arch-sub-name">Workflow</span>
							<span class="arch-sub-port">9107</span>
						</div>
					</div>
				</div>

				<div class="arch-connector"></div>

				<!-- Communication & Data -->
				<div class="arch-box">
					<span class="arch-title">Communication & Data</span>
					<span class="arch-name">Events Hub & PostgreSQL</span>
					<span class="arch-details">Events (9100) · Redis Pub/Sub (16379) · Supabase</span>
				</div>

				<div class="arch-connector"></div>

				<!-- Observability -->
				<div class="arch-box">
					<span class="arch-title">Observability Layer</span>
					<span class="arch-name">Monitoring & Tracing</span>
					<div class="arch-grid">
						<div class="arch-sub-box">
							<span class="arch-sub-name">Prometheus</span>
							<span class="arch-sub-port">9090</span>
						</div>
						<div class="arch-sub-box">
							<span class="arch-sub-name">Grafana</span>
							<span class="arch-sub-port">3000</span>
						</div>
						<div class="arch-sub-box">
							<span class="arch-sub-name">Jaeger</span>
							<span class="arch-sub-port">16686</span>
						</div>
					</div>
				</div>
			</div>

		<h2 id="microservices" class="section-heading">Core Microservices</h2>
		<p>The platform consists of 9 specialized services, each handling a specific part of the DevSecOps lifecycle.</p>
		
		<div class="service-grid">
			<div class="service-item">
				<span class="service-port">9101</span>
				<div>
					<strong>AI Service</strong>
					<p>Intelligent code analysis, vulnerability detection, and security recommendations using LLMs (GPT-4, Claude, Llama).</p>
				</div>
			</div>
			<div class="service-item">
				<span class="service-port">9102</span>
				<div>
					<strong>GitHub Service</strong>
					<p>Deep integration with GitHub API v3/v4 for repository analysis, metrics, and automated PR orchestration.</p>
				</div>
			</div>
			<div class="service-item">
				<span class="service-port">9103</span>
				<div>
					<strong>Threat Modeling</strong>
					<p>Automated STRIDE, CIA, and LINDDUN analysis engine with MITRE ATT&CK mapping.</p>
				</div>
			</div>
			<div class="service-item">
				<span class="service-port">9104</span>
				<div>
					<strong>Workspace Intelligence</strong>
					<p>Dependency mapping (SCA), technology stack detection, and DSOMM maturity scoring.</p>
				</div>
			</div>
			<div class="service-item">
				<span class="service-port">9107</span>
				<div>
					<strong>Workflow Orchestration</strong>
					<p>GitHub Actions YAML validation, CI/CD security scanning, and pipeline optimization.</p>
				</div>
			</div>
			<div class="service-item">
				<span class="service-port">9108</span>
				<div>
					<strong>AI RAG Service</strong>
					<p>Retrieval-Augmented Generation for security knowledge base queries using Qdrant vector storage.</p>
				</div>
			</div>
		</div>

		<h2 id="observability" class="section-heading">Observability Stack</h2>
		<p>Every service is pre-instrumented with production-grade monitoring tools:</p>
		<div class="tech-grid">
			<div class="tech-item">
				<span class="tech-category">Metrics</span>
				<span class="tech-value">Prometheus + Grafana (Pre-configured Dashboards)</span>
			</div>
			<div class="tech-item">
				<span class="tech-category">Tracing</span>
				<span class="tech-value">Jaeger + OpenTelemetry (End-to-end Request context)</span>
			</div>
			<div class="tech-item">
				<span class="tech-category">Logging</span>
				<span class="tech-value">Loki + Promtail (Centralized JSON logging)</span>
			</div>
		</div>
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
	/* (Removed redundant code-block/pre styles - handled by layout) */
	.service-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 24px 0; }
	.service-item { display: flex; gap: 14px; padding: 16px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; }
	.service-port { font-family: 'DM Mono', monospace; font-size: 11px; color: var(--accent); background: var(--accent-subtle); padding: 2px 6px; border-radius: 4px; height: fit-content; }
	.service-item strong { display: block; margin-bottom: 4px; font-size: 14px; }
	.service-item p { font-size: 12.5px; color: var(--text-secondary); margin: 0; line-height: 1.5; }
	.tech-grid { display: grid; grid-template-columns: 1fr; gap: 10px; margin: 24px 0; }
	.tech-item { padding: 16px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; }
	.tech-category { display: block; font-family: 'DM Mono', monospace; font-size: 10px; color: var(--accent); text-transform: uppercase; margin-bottom: 4px; }
	.tech-value { font-size: 14px; color: var(--text-primary); }
</style>
