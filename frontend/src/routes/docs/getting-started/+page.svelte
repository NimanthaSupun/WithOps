<script>
	import { onMount } from 'svelte';

	let visible = $state(false);
	let copiedStates = $state({});

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
	<title>Getting Started — WithOps Documentation</title>
	<meta name="description" content="Learn how to set up WithOps, the AI-powered DevSecOps platform. Connect your GitHub account and run your first security scan in minutes." />
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<!-- Breadcrumb -->
	<div class="breadcrumb">
		<span class="bc-muted">Docs</span>
		<span class="bc-sep">/</span>
		<span class="bc-muted">Getting Started</span>
		<span class="bc-sep">/</span>
		<span class="bc-current">Introduction</span>
	</div>

	<!-- Chapter tag -->
	<div class="chapter-tag">
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09zM12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z" />
		</svg>
		Chapter I
	</div>

	<!-- Title -->
	<h1 class="page-title" id="introduction">Getting Started with WithOps</h1>
	<p class="page-subtitle">
		Everything you need to set up the AI-powered DevSecOps platform and run your first automated security analysis.
	</p>

	<hr class="divider" />

	<!-- Meta row -->
	<div class="meta-row">
		<span class="meta-reading">
			<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
			</svg>
			8 min read
		</span>
		<span class="meta-tag">Beginner</span>
		<span class="meta-tag">Setup</span>
		<span class="meta-tag">v2.0</span>
	</div>

	<!-- Welcome prose -->
	<div class="prose">
		<p>
			Welcome to <strong>WithOps</strong> — an enterprise-grade, AI-powered DevSecOps platform that automates security analysis, threat modeling, and compliance assessment for your development workflow. This guide walks you through the fundamentals — from creating your account to running your first security scan.
		</p>
		<p>
			WithOps follows the principle of <em>"Everything After Code"</em> — intelligent automation that empowers development teams to ship code faster, safer, and smarter. By the end of this guide, you'll have a fully connected workspace ready to analyse your repositories.
		</p>
	</div>

	<!-- Callout: Before you begin -->
	<div class="callout info">
		<div class="callout-icon">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" />
			</svg>
		</div>
		<div class="callout-content">
			<div class="callout-label">Before you begin</div>
			<p>You'll need a <strong>GitHub account</strong> with at least one repository, and a modern browser (Chrome, Firefox, Safari, or Edge). No local installation is required for the cloud-hosted version.</p>
		</div>
	</div>

	<!-- What You'll Learn — 3 Step preview cards -->
	<h2 class="section-heading" id="what-youll-learn">What You'll Learn</h2>
	<p class="prose-text">
		This Getting Started guide is divided into three focused chapters. Complete them in order to go from zero to your first comprehensive security report.
	</p>

	<div class="steps">
		<a href="/docs/getting-started/quick-start" class="step-card">
			<div class="step-num">1</div>
			<div class="step-content">
				<h4>Quick Start</h4>
				<p>Set up your account and choose between cloud-hosted or self-hosted deployment. Get the platform running in under five minutes.</p>
				<span class="step-arrow">→</span>
			</div>
		</a>

		<a href="/docs/getting-started/connecting-github" class="step-card">
			<div class="step-num">2</div>
			<div class="step-content">
				<h4>Connecting GitHub</h4>
				<p>Link your GitHub account using OAuth or GitHub App. Configure organization access and repository permissions.</p>
				<span class="step-arrow">→</span>
			</div>
		</a>

		<a href="/docs/getting-started/first-security-scan" class="step-card">
			<div class="step-num">3</div>
			<div class="step-content">
				<h4>First Security Scan</h4>
				<p>Run a comprehensive scan covering SAST, dependency audit, secret detection, CI/CD analysis, and AI-powered threat assessment.</p>
				<span class="step-arrow">→</span>
			</div>
		</a>
	</div>

	<!-- Platform Capabilities -->
	<h2 class="section-heading" id="platform-capabilities">Platform Capabilities</h2>
	<p class="prose-text">
		WithOps combines multiple security disciplines into a single, cohesive platform. Each capability is powered by AI models and integrates directly with your development workflow.
	</p>

	<div class="capability-grid">
		<div class="capability-card">
			<div class="cap-icon-wrap blue">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
					<path d="M9 12l2 2 4-4" />
				</svg>
			</div>
			<h4>AI Security Analysis</h4>
			<p>Multi-model vulnerability detection (GPT-4, Claude 3, Llama 3) with automated remediation suggestions and CVSS risk scoring.</p>
		</div>

		<div class="capability-card">
			<div class="cap-icon-wrap green">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
					<line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
				</svg>
			</div>
			<h4>Threat Modeling</h4>
			<p>Automated STRIDE, CIA, and LINDDUN analysis with attack surface mapping and OWASP-aligned mitigation strategies.</p>
		</div>

		<div class="capability-card">
			<div class="cap-icon-wrap amber">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
				</svg>
			</div>
			<h4>GitHub Integration</h4>
			<p>Deep integration for repository management, PR automation, workflow monitoring, and real-time dependency tracking.</p>
		</div>

		<div class="capability-card">
			<div class="cap-icon-wrap purple">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
				</svg>
			</div>
			<h4>Workflow Orchestration</h4>
			<p>CI/CD workflow analysis, GitHub Actions YAML validation, integrated security scanning, and performance recommendations.</p>
		</div>
	</div>

	<!-- Prerequisites -->
	<h2 class="section-heading" id="prerequisites">Prerequisites</h2>
	<p class="prose-text">
		Before you begin, ensure you have the following ready. The cloud-hosted version requires no local installation — just a browser and a GitHub account.
	</p>

	<div class="prereq-grid">
		<div class="prereq-item">
			<div class="prereq-check">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
					<polyline points="20 6 9 17 4 12" />
				</svg>
			</div>
			<div>
				<strong>GitHub Account</strong>
				<p>A personal or organisation GitHub account with repository access.</p>
			</div>
		</div>
		<div class="prereq-item">
			<div class="prereq-check">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
					<polyline points="20 6 9 17 4 12" />
				</svg>
			</div>
			<div>
				<strong>Modern Browser</strong>
				<p>Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+.</p>
			</div>
		</div>
		<div class="prereq-item">
			<div class="prereq-check">
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
					<polyline points="20 6 9 17 4 12" />
				</svg>
			</div>
			<div>
				<strong>Repository Access</strong>
				<p>At least one repository you own or have admin access to.</p>
			</div>
		</div>
	</div>

	<!-- Self-Hosted callout -->
	<div class="callout tip">
		<div class="callout-icon">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
			</svg>
		</div>
		<div class="callout-content">
			<div class="callout-label">Self-Hosted Deployment</div>
			<p>For self-hosted installations, you'll also need <strong>Docker 24+</strong>, <strong>8GB+ RAM</strong>, <strong>Node.js 18+</strong>, and <strong>Python 3.11+</strong>. See the <a href="/docs/getting-started/quick-start">Quick Start</a> guide for detailed setup instructions.</p>
		</div>
	</div>

	<!-- Architecture Overview -->
	<h2 class="section-heading" id="architecture">Architecture Overview</h2>
	<p class="prose-text">
		WithOps uses a microservices architecture with an API Gateway pattern. Here's how requests flow through the system:
	</p>

	<div class="code-block">
		<div class="code-header">
			<span class="code-lang">architecture</span>
			<button class="copy-btn" onclick={() => copyCode('arch', 'Browser → Kong API Gateway → Microservices → AI + Data')}>
				{copiedStates['arch'] ? '✓ Copied' : 'Copy'}
			</button>
		</div>
		<pre><code class="arch-code"><span class="cm">┌─────────────────────────────────────────────────┐</span>
<span class="cm">│</span>  <span class="kw">Browser / Client</span>                                <span class="cm">│</span>
<span class="cm">└──────────────────────┬──────────────────────────┘</span>
                       <span class="cm">│</span>
                       <span class="cm">▼</span>
<span class="cm">┌─────────────────────────────────────────────────┐</span>
<span class="cm">│</span>  <span class="fn">Kong API Gateway</span> <span class="str">(Port 9000)</span>                     <span class="cm">│</span>
<span class="cm">│</span>  <span class="cm">Rate limiting · CORS · Auth · Routing</span>          <span class="cm">│</span>
<span class="cm">└──────────────────────┬──────────────────────────┘</span>
                       <span class="cm">│</span>
        <span class="cm">┌──────────────┼──────────────┐</span>
        <span class="cm">▼</span>              <span class="cm">▼</span>              <span class="cm">▼</span>
<span class="cm">┌──────────────┐┌──────────────┐┌──────────────┐</span>
<span class="cm">│</span><span class="fn"> AI Service   </span><span class="cm">││</span><span class="fn"> GitHub Svc   </span><span class="cm">││</span><span class="fn"> Auth Service </span><span class="cm">│</span>
<span class="cm">│</span> <span class="str">GPT4/Claude/L3</span><span class="cm">││</span> <span class="str">REST + GQL</span>   <span class="cm">││</span> <span class="str">Auth0 + JWT</span>  <span class="cm">│</span>
<span class="cm">└──────────────┘└──────────────┘└──────────────┘</span>
        <span class="cm">│</span>              <span class="cm">│</span>              <span class="cm">│</span>
        <span class="cm">▼</span>              <span class="cm">▼</span>              <span class="cm">▼</span>
<span class="cm">┌──────────────┐┌──────────────┐┌──────────────┐</span>
<span class="cm">│</span><span class="fn"> Threat Model </span><span class="cm">││</span><span class="fn"> Workspace    </span><span class="cm">││</span><span class="fn"> Workflow     </span><span class="cm">│</span>
<span class="cm">│</span> <span class="str">STRIDE</span>       <span class="cm">││</span> <span class="str">Intelligence</span> <span class="cm">││</span> <span class="str">Orchestrator</span> <span class="cm">│</span>
<span class="cm">└──────────────┘└──────────────┘└──────────────┘</span>
        <span class="cm">│</span>              <span class="cm">│</span>              <span class="cm">│</span>
        <span class="cm">└──────────────┼──────────────┘</span>
                       <span class="cm">▼</span>
<span class="cm">┌──────────────┐┌──────────────┐┌──────────────┐</span>
<span class="cm">│</span><span class="kw"> PostgreSQL   </span><span class="cm">││</span><span class="kw"> Redis Cache  </span><span class="cm">││</span><span class="kw"> Ollama LLM   </span><span class="cm">│</span>
<span class="cm">│</span> <span class="str">Supabase</span>     <span class="cm">││</span> <span class="str">Pub/Sub</span>      <span class="cm">││</span> <span class="str">Local AI</span>     <span class="cm">│</span>
<span class="cm">└──────────────┘└──────────────┘└──────────────┘</span></code></pre>
	</div>

	<div class="prose">
		<h3 id="microservices">9 Microservices</h3>
		<p>
			Each service is independently deployable, communicates via REST APIs and Redis pub/sub, and is containerised with Docker. The platform uses Auth0 for authentication with RS256 JWT tokens.
		</p>
	</div>

	<!-- Service list -->
	<div class="service-grid">
		<div class="service-item">
			<span class="service-port">9100</span>
			<div>
				<strong>Events Hub (Backend)</strong>
				<span class="service-desc">Real-time WebSocket manager, event bus, and notification hub</span>
			</div>
		</div>
		<div class="service-item">
			<span class="service-port">9101</span>
			<div>
				<strong>AI Service</strong>
				<span class="service-desc">AI/ML operations, code analysis, vulnerability detection</span>
			</div>
		</div>
		<div class="service-item">
			<span class="service-port">9102</span>
			<div>
				<strong>GitHub Service</strong>
				<span class="service-desc">Repository management, webhook handling, GraphQL</span>
			</div>
		</div>
		<div class="service-item">
			<span class="service-port">9103</span>
			<div>
				<strong>Threat Modeling</strong>
				<span class="service-desc">STRIDE analysis, attack surface mapping, risk scoring</span>
			</div>
		</div>
		<div class="service-item">
			<span class="service-port">9104</span>
			<div>
				<strong>Workspace Intelligence</strong>
				<span class="service-desc">Code analysis, maturity scoring, pattern detection</span>
			</div>
		</div>
		<div class="service-item">
			<span class="service-port">9105</span>
			<div>
				<strong>Collaboration</strong>
				<span class="service-desc">Team messaging, workspace sharing, live notifications</span>
			</div>
		</div>
		<div class="service-item">
			<span class="service-port">9106</span>
			<div>
				<strong>Auth Service</strong>
				<span class="service-desc">Authentication, SSO, RBAC, session management</span>
			</div>
		</div>
		<div class="service-item">
			<span class="service-port">9107</span>
			<div>
				<strong>Workflow Orchestration</strong>
				<span class="service-desc">CI/CD management, GitHub Actions, security scanning</span>
			</div>
		</div>
		<div class="service-item">
			<span class="service-port">9108</span>
			<div>
				<strong>AI RAG Service</strong>
				<span class="service-desc">Conversational AI, vector search, knowledge base</span>
			</div>
		</div>
	</div>

	<!-- Quick Install for Self-Hosted -->
	<h2 class="section-heading" id="quick-install">Quick Install (Self-Hosted)</h2>
	<p class="prose-text">
		For those who prefer self-hosted deployment, here's a quick overview. The full step-by-step guide is available in <a href="/docs/getting-started/quick-start">Quick Start</a>.
	</p>

	<div class="code-block">
		<div class="code-header">
			<span class="code-lang">bash</span>
			<button class="copy-btn" onclick={() => copyCode('clone', 'git clone https://github.com/withops/platform.git\ncd platform\ncp .env.example .env\ndocker compose up -d')}>
				{copiedStates['clone'] ? '✓ Copied' : 'Copy'}
			</button>
		</div>
		<pre><code><span class="cm"># Clone the repository</span>
<span class="fn">git</span> clone https://github.com/withops/platform.git
<span class="fn">cd</span> platform

<span class="cm"># Configure environment</span>
<span class="fn">cp</span> .env.example .env
<span class="cm"># Edit .env with your API keys (Auth0, GitHub, etc.)</span>

<span class="cm"># Start all services</span>
<span class="fn">docker</span> compose up -d

<span class="cm"># Access the platform</span>
<span class="cm"># Frontend:  http://localhost:5173</span>
<span class="cm"># API:       http://localhost:9000</span>
<span class="cm"># Grafana:   http://localhost:3001</span></code></pre>
	</div>

	<div class="callout warn">
		<div class="callout-icon">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
				<line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
			</svg>
		</div>
		<div class="callout-content">
			<div class="callout-label">Environment Variables</div>
			<p>Never commit your <code>.env</code> file. It contains sensitive API keys for Auth0, GitHub, Supabase, and AI providers. The <code>.env.example</code> file includes all required variables with placeholder values.</p>
		</div>
	</div>

	<!-- Tech Stack Summary -->
	<h2 class="section-heading" id="tech-stack">Technology Stack</h2>
	<div class="prose">
		<p>WithOps is built with a modern, production-grade technology stack designed for scalability and developer experience.</p>
	</div>

	<div class="tech-grid">
		<div class="tech-item">
			<span class="tech-category">Frontend</span>
			<span class="tech-value">SvelteKit 2 · Svelte 5 · Vite 6 · Tailwind CSS 4</span>
		</div>
		<div class="tech-item">
			<span class="tech-category">Backend</span>
			<span class="tech-value">FastAPI · Python 3.11+ · SQLAlchemy 2 · Uvicorn</span>
		</div>
		<div class="tech-item">
			<span class="tech-category">AI / ML</span>
			<span class="tech-value">Ollama · GPT-4 · Anthropic Claude · Qdrant Vector DB</span>
		</div>
		<div class="tech-item">
			<span class="tech-category">Database</span>
			<span class="tech-value">PostgreSQL 15 (Supabase) · Redis 7 · Qdrant</span>
		</div>
		<div class="tech-item">
			<span class="tech-category">Infrastructure</span>
			<span class="tech-value">Docker · Kubernetes · Kong Gateway · CI/CD</span>
		</div>
		<div class="tech-item">
			<span class="tech-category">Monitoring</span>
			<span class="tech-value">Prometheus · Grafana · Jaeger · Loki · OpenTelemetry</span>
		</div>
	</div>

	<!-- Next Step Card -->
	<div class="next-step-card">
		<a href="/docs/getting-started/quick-start" class="nsc-link">
			<div class="nsc-content">
				<div class="nsc-label">Next Step</div>
				<h3 class="nsc-title">Quick Start Guide →</h3>
				<p class="nsc-desc">Set up your account and get the platform running in under five minutes — cloud or self-hosted.</p>
			</div>
			<div class="nsc-arrow">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M5 12h14M12 5l7 7-7 7" />
				</svg>
			</div>
		</a>
	</div>

	<!-- Footer nav -->
	<div class="page-nav">
		<a href="/" class="page-nav-btn prev">
			<span class="page-nav-label">← Previous</span>
			<span class="page-nav-title">Landing Page</span>
		</a>
		<a href="/docs/getting-started/quick-start" class="page-nav-btn next">
			<span class="page-nav-label">Next →</span>
			<span class="page-nav-title">Quick Start</span>
		</a>
	</div>
</div>

<style>
	/* ── Page entry animation ── */
	.getting-started {
		opacity: 0;
		transform: translateY(10px);
		transition: all 0.5s ease;
	}
	.getting-started.visible {
		opacity: 1;
		transform: translateY(0);
	}

	/* ── Breadcrumb ── */
	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 8px;
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		margin-bottom: 24px;
	}
	.bc-muted { color: var(--text-muted); }
	.bc-sep { color: var(--border-focus); }
	.bc-current { color: var(--accent); }

	/* ── Chapter tag ── */
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
		animation: fadeSlide 0.5s ease both;
	}
	.chapter-tag::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--accent);
		opacity: 0.2;
		max-width: 50px;
	}

	/* ── Title ── */
	.page-title {
		font-family: 'Playfair Display', serif;
		font-size: 38px;
		font-weight: 700;
		line-height: 1.15;
		color: var(--text-primary);
		margin-bottom: 10px;
		animation: fadeSlide 0.5s ease 0.05s both;
	}

	.page-subtitle {
		font-family: 'Lora', serif;
		font-style: italic;
		font-size: 15px;
		color: var(--text-secondary);
		margin-bottom: 0;
		line-height: 1.6;
		animation: fadeSlide 0.5s ease 0.1s both;
	}

	.divider {
		border: none;
		border-top: 1px solid var(--border);
		margin: 24px 0;
		animation: fadeSlide 0.5s ease 0.12s both;
	}

	/* ── Meta row ── */
	.meta-row {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 28px;
		font-family: 'DM Mono', monospace;
		font-size: 11px;
		color: var(--text-muted);
		animation: fadeSlide 0.5s ease 0.15s both;
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
		letter-spacing: 0.04em;
	}

	/* ── Prose ── */
	.prose {
		animation: fadeSlide 0.5s ease 0.2s both;
	}
	.prose p, .prose-text {
		font-family: 'Lora', serif;
		font-size: 15px;
		line-height: 1.85;
		color: var(--text-primary);
		margin-bottom: 16px;
	}
	.prose strong { font-weight: 600; }
	.prose em { font-style: italic; color: var(--text-secondary); }
	.prose a, .prose-text a {
		color: var(--accent);
		text-decoration: none;
		border-bottom: 1px solid transparent;
		transition: border-color 0.15s;
	}
	.prose a:hover, .prose-text a:hover {
		border-bottom-color: var(--accent);
	}

	/* ── Section headings ── */
	.section-heading {
		font-family: 'Playfair Display', serif;
		font-size: 22px;
		font-weight: 700;
		color: var(--text-primary);
		margin: 40px 0 12px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	/* ── Callout boxes ── */
	.callout {
		display: flex;
		gap: 14px;
		padding: 16px 20px;
		border-radius: 0 6px 6px 0;
		margin: 24px 0;
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
	.callout.info .callout-icon { color: var(--callout-info-text); }
	.callout.tip .callout-icon { color: var(--callout-tip-text); }
	.callout.warn .callout-icon { color: var(--callout-warn-text); }
	.callout-label {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		margin-bottom: 4px;
	}
	.callout.info .callout-label { color: var(--callout-info-text); }
	.callout.tip .callout-label { color: var(--callout-tip-text); }
	.callout.warn .callout-label { color: var(--callout-warn-text); }
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
	.callout-content a {
		color: var(--accent);
		text-decoration: none;
	}
	.callout-content a:hover {
		text-decoration: underline;
	}

	/* ── Step cards ── */
	.steps {
		display: flex;
		flex-direction: column;
		gap: 12px;
		margin: 20px 0 32px;
	}

	.step-card {
		display: flex;
		gap: 18px;
		padding: 20px;
		background: var(--bg-surface);
		border-radius: 6px;
		border: 1px solid var(--border);
		transition: all 0.2s ease;
		box-shadow: var(--card-shadow);
		text-decoration: none;
		color: inherit;
		position: relative;
	}
	.step-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-1px);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
	}

	.step-num {
		width: 32px;
		height: 32px;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: 'Playfair Display', serif;
		font-size: 15px;
		color: var(--accent);
		flex-shrink: 0;
	}

	.step-content {
		flex: 1;
	}
	.step-content h4 {
		font-family: 'Lora', serif;
		font-weight: 600;
		font-size: 15px;
		color: var(--text-primary);
		margin-bottom: 4px;
	}
	.step-content p {
		font-family: 'Lora', serif;
		font-size: 13px;
		line-height: 1.65;
		color: var(--text-secondary);
		margin: 0;
	}

	.step-arrow {
		position: absolute;
		right: 20px;
		top: 50%;
		transform: translateY(-50%);
		font-size: 16px;
		color: var(--text-muted);
		transition: all 0.15s;
	}
	.step-card:hover .step-arrow {
		color: var(--accent);
		transform: translateY(-50%) translateX(3px);
	}

	/* ── Capability grid ── */
	.capability-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
		margin: 16px 0 32px;
	}

	.capability-card {
		padding: 20px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 6px;
		transition: all 0.2s ease;
		box-shadow: var(--card-shadow);
	}
	.capability-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-1px);
	}

	.cap-icon-wrap {
		width: 36px;
		height: 36px;
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 12px;
	}
	.cap-icon-wrap.blue { background: rgba(0, 173, 239, 0.08); color: var(--accent); }
	.cap-icon-wrap.green { background: rgba(16, 185, 129, 0.08); color: var(--success); }
	.cap-icon-wrap.amber { background: rgba(245, 158, 11, 0.08); color: var(--warn); }
	.cap-icon-wrap.purple { background: rgba(139, 92, 246, 0.08); color: #8b5cf6; }

	.capability-card h4 {
		font-family: 'Inter', sans-serif;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 6px;
	}
	.capability-card p {
		font-family: 'Lora', serif;
		font-size: 12.5px;
		line-height: 1.65;
		color: var(--text-secondary);
		margin: 0;
	}

	/* ── Prerequisites ── */
	.prereq-grid {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin: 16px 0 24px;
	}
	.prereq-item {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		padding: 14px 16px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 6px;
	}
	.prereq-check {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: rgba(16, 185, 129, 0.08);
		color: var(--success);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		margin-top: 1px;
	}
	.prereq-item strong {
		font-family: 'Inter', sans-serif;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		display: block;
		margin-bottom: 2px;
	}
	.prereq-item p {
		font-family: 'Lora', serif;
		font-size: 12.5px;
		line-height: 1.6;
		color: var(--text-secondary);
		margin: 0;
	}

	/* ── Code block ── */
	.code-block {
		background: var(--code-bg);
		border-radius: 6px;
		margin: 20px 0;
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
		letter-spacing: 0.06em;
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
		padding: 18px 20px;
		overflow-x: auto;
		font-family: 'DM Mono', monospace;
		font-size: 12.5px;
		line-height: 1.7;
		color: var(--code-text);
		margin: 0;
	}

	/* Syntax tokens */
	.kw { color: #c8956e; }
	.str { color: #a5c985; }
	.cm { color: #5a6e4a; }
	.fn { color: #8bb8d4; }
	.num { color: #c884a0; }

	/* ── Service grid ── */
	.service-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
		margin: 16px 0 32px;
	}
	.service-item {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		padding: 12px 14px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 4px;
		transition: border-color 0.15s;
	}
	.service-item:hover {
		border-color: var(--border-focus);
	}
	.service-port {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		color: var(--accent);
		background: var(--accent-subtle);
		padding: 2px 6px;
		border-radius: 3px;
		flex-shrink: 0;
		margin-top: 2px;
	}
	.service-item strong {
		font-family: 'Inter', sans-serif;
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		display: block;
		margin-bottom: 2px;
	}
	.service-desc {
		font-family: 'Lora', serif;
		font-size: 11px;
		line-height: 1.5;
		color: var(--text-muted);
	}

	/* ── Tech grid ── */
	.tech-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
		margin: 16px 0 32px;
	}
	.tech-item {
		padding: 12px 14px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 4px;
	}
	.tech-category {
		font-family: 'DM Mono', monospace;
		font-size: 9px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--accent);
		display: block;
		margin-bottom: 4px;
	}
	.tech-value {
		font-family: 'Lora', serif;
		font-size: 12px;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	/* ── Next Step Card ── */
	.next-step-card {
		margin: 40px 0 32px;
		border-radius: 8px;
		overflow: hidden;
		border: 1px solid var(--border);
		background: var(--bg-surface);
		transition: all 0.2s ease;
	}
	.next-step-card:hover {
		border-color: var(--accent);
		box-shadow: 0 4px 20px rgba(0, 173, 239, 0.08);
	}
	.nsc-link {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 24px;
		text-decoration: none;
		color: inherit;
	}
	.nsc-label {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--accent);
		margin-bottom: 6px;
	}
	.nsc-title {
		font-family: 'Playfair Display', serif;
		font-size: 18px;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 4px;
	}
	.nsc-desc {
		font-family: 'Lora', serif;
		font-size: 13px;
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.5;
	}
	.nsc-arrow {
		color: var(--accent);
		flex-shrink: 0;
		margin-left: 20px;
		transition: transform 0.15s;
	}
	.next-step-card:hover .nsc-arrow {
		transform: translateX(4px);
	}

	/* ── Page navigation ── */
	.page-nav {
		display: flex;
		justify-content: space-between;
		margin-top: 32px;
		padding-top: 20px;
		border-top: 1px solid var(--border);
	}
	.page-nav-btn {
		display: flex;
		flex-direction: column;
		gap: 3px;
		text-decoration: none;
		transition: all 0.15s;
	}
	.page-nav-label {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-muted);
	}
	.page-nav-title {
		font-family: 'Lora', serif;
		font-size: 14px;
		color: var(--text-secondary);
		transition: color 0.15s;
	}
	.page-nav-btn:hover .page-nav-title {
		color: var(--accent);
	}
	.page-nav-btn.next {
		text-align: right;
		margin-left: auto;
	}

	/* ── Animations ── */
	@keyframes fadeSlide {
		from { opacity: 0; transform: translateY(10px); }
		to { opacity: 1; transform: translateY(0); }
	}

	/* ── Responsive ── */
	@media (max-width: 768px) {
		.page-title {
			font-size: 28px;
		}
		.capability-grid,
		.service-grid,
		.tech-grid {
			grid-template-columns: 1fr;
		}
		.meta-row {
			flex-wrap: wrap;
		}
	}

	@media (max-width: 480px) {
		.page-title {
			font-size: 24px;
		}
		.section-heading {
			font-size: 18px;
		}
		.step-arrow {
			display: none;
		}
	}
</style>
