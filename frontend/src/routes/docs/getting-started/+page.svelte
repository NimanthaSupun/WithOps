<script>
	import { isDarkMode } from '$lib/stores.js';

	let darkMode = $state(false);
	isDarkMode.subscribe((v) => (darkMode = v));

	const capabilities = [
		{
			num: '01',
			label: 'SCANNING',
			title: 'Code Scanning',
			description:
				'Automated SAST, DAST, and dependency vulnerability detection across your entire codebase.',
			icon: 'scan',
			color: '#00adef'
		},
		{
			num: '02',
			label: 'PIPELINE',
			title: 'CI/CD Security',
			description:
				'Inject security gates into your build pipelines without disrupting developer velocity.',
			icon: 'pipeline',
			color: '#10b981'
		},
		{
			num: '03',
			label: 'COMPLIANCE',
			title: 'Policy Engine',
			description:
				'Enforce organizational security policies with automated compliance verification and reporting.',
			icon: 'policy',
			color: '#d4a054'
		},
		{
			num: '04',
			label: 'THREAT MODEL',
			title: 'Threat Modeling',
			description:
				'AI-assisted threat analysis that maps attack surfaces and generates mitigation strategies.',
			icon: 'threat',
			color: '#8b5cf6'
		},
		{
			num: '05',
			label: 'INTELLIGENCE',
			title: 'Security Intel',
			description:
				'Real-time vulnerability feeds and contextual risk scoring across your dependency graph.',
			icon: 'intel',
			color: '#06b6d4'
		},
		{
			num: '06',
			label: 'REMEDIATION',
			title: 'Auto-Remediation',
			description:
				'AI-generated fix suggestions with one-click pull request creation for identified vulnerabilities.',
			icon: 'fix',
			color: '#f43f5e'
		}
	];

	const prerequisites = [
		{ item: 'GitHub account with repository access', type: 'required' },
		{ item: 'Node.js 18+ (for self-hosted deployment)', type: 'optional' },
		{ item: 'Modern browser (Chrome, Firefox, Edge, Safari)', type: 'required' },
		{ item: 'Organization admin access for GitHub App installation', type: 'recommended' }
	];
</script>

<div class="intro-page">
	<!-- Hero -->
	<header class="page-hero">
		<div class="hero-badge">
			<span class="badge-dot"></span>
			DOCUMENTATION
		</div>
		<h1 class="hero-title">
			WithOps <span class="title-accent">DevSecOps</span> Platform
		</h1>
		<p class="hero-subtitle">
			Integrate security into every phase of your development lifecycle. From code commit to
			production deployment — continuous, automated, intelligent.
		</p>
	</header>

	<!-- Quick Path Cards -->
	<section class="quick-paths" id="quick-paths">
		<h2 id="getting-started" class="section-heading">
			<span class="heading-marker">§</span>
			Getting Started
		</h2>
		<p class="section-intro">Three steps to a fully secured development pipeline.</p>

		<div class="path-grid">
			<a href="/docs/getting-started/quick-start" class="path-card">
				<div class="path-step">01</div>
				<div class="path-content">
					<h3 class="path-title">Quick Start</h3>
					<p class="path-desc">
						Set up your account, configure your environment, and deploy your first secured pipeline
						in under 10 minutes.
					</p>
				</div>
				<span class="path-arrow">→</span>
			</a>
			<a href="/docs/getting-started/connecting-github" class="path-card">
				<div class="path-step">02</div>
				<div class="path-content">
					<h3 class="path-title">Connect GitHub</h3>
					<p class="path-desc">
						Link your repositories with fine-grained permission control. Choose OAuth or GitHub App
						integration.
					</p>
				</div>
				<span class="path-arrow">→</span>
			</a>
			<a href="/docs/getting-started/first-security-scan" class="path-card">
				<div class="path-step">03</div>
				<div class="path-content">
					<h3 class="path-title">First Security Scan</h3>
					<p class="path-desc">
						Run your first comprehensive security analysis and understand the results, severity
						levels, and remediation paths.
					</p>
				</div>
				<span class="path-arrow">→</span>
			</a>
		</div>
	</section>

	<!-- Capabilities -->
	<section class="capabilities-section" id="capabilities-section">
		<h2 id="capabilities" class="section-heading">
			<span class="heading-marker">§</span>
			Platform Capabilities
		</h2>
		<p class="section-intro">
			A comprehensive security toolkit built for modern engineering teams.
		</p>

		<div class="cap-grid">
			{#each capabilities as cap}
				<div class="cap-card">
					<div class="cap-header">
						<span class="cap-number" style="color: {cap.color}">{cap.num}</span>
						<span class="cap-label">{cap.label}</span>
					</div>
					<h3 class="cap-title">{cap.title}</h3>
					<p class="cap-desc">{cap.description}</p>
					<div class="cap-indicator" style="background: {cap.color}"></div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Prerequisites -->
	<section class="prereq-section" id="prereq-section">
		<h2 id="prerequisites" class="section-heading">
			<span class="heading-marker">§</span>
			Prerequisites
		</h2>

		<div class="prereq-table">
			<div class="prereq-header-row">
				<span class="prereq-col-item">Requirement</span>
				<span class="prereq-col-type">Status</span>
			</div>
			{#each prerequisites as req}
				<div class="prereq-row">
					<span class="prereq-item">{req.item}</span>
					<span
						class="prereq-type"
						class:required={req.type === 'required'}
						class:optional={req.type === 'optional'}
						class:recommended={req.type === 'recommended'}
					>
						{req.type.toUpperCase()}
					</span>
				</div>
			{/each}
		</div>
	</section>

	<!-- Architecture Overview -->
	<section class="arch-section" id="arch-section">
		<h2 id="architecture" class="section-heading">
			<span class="heading-marker">§</span>
			How It Works
		</h2>
		<p class="section-intro">
			WithOps operates as a security overlay across your existing development infrastructure.
		</p>

		<div class="arch-flow">
			<div class="arch-node">
				<div class="arch-node-num">1</div>
				<div class="arch-node-label">Code Push</div>
				<div class="arch-node-detail">Developer commits to repository</div>
			</div>
			<div class="arch-connector">
				<div class="arch-connector-line"></div>
			</div>
			<div class="arch-node">
				<div class="arch-node-num">2</div>
				<div class="arch-node-label">Webhook Trigger</div>
				<div class="arch-node-detail">WithOps receives event notification</div>
			</div>
			<div class="arch-connector">
				<div class="arch-connector-line"></div>
			</div>
			<div class="arch-node">
				<div class="arch-node-num">3</div>
				<div class="arch-node-label">Security Analysis</div>
				<div class="arch-node-detail">Multi-dimensional scan execution</div>
			</div>
			<div class="arch-connector">
				<div class="arch-connector-line"></div>
			</div>
			<div class="arch-node">
				<div class="arch-node-num">4</div>
				<div class="arch-node-label">Report & Remediate</div>
				<div class="arch-node-detail">Results, scoring, and auto-fix PRs</div>
			</div>
		</div>
	</section>

	<!-- Field Note CTA -->
	<section class="cta-section">
		<div class="cta-card">
			<div class="cta-label">FIELD NOTE</div>
			<h3 class="cta-title">Ready to begin?</h3>
			<p class="cta-desc">
				Start with the Quick Start guide to have your first secured pipeline running in minutes.
			</p>
			<a href="/docs/getting-started/quick-start" class="cta-button">
				Start Quick Setup
				<span class="cta-arrow">→</span>
			</a>
		</div>
	</section>
</div>

<style>
	.intro-page {
		max-width: 720px;
	}

	/* ── Hero ── */
	.page-hero {
		margin-bottom: 3.5rem;
		padding-bottom: 2rem;
		border-bottom: 1px dashed var(--border);
	}

	.hero-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--accent);
		letter-spacing: 0.12em;
		margin-bottom: 1rem;
	}

	.badge-dot {
		width: 6px;
		height: 6px;
		background: var(--accent);
		border-radius: 50%;
		animation: pulse-dot 2s ease-in-out infinite;
	}

	@keyframes pulse-dot {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.4;
		}
	}

	.hero-title {
		font-size: 2rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		line-height: 1.15;
		margin-bottom: 0.875rem;
		color: var(--text-primary);
	}

	.title-accent {
		color: var(--accent);
	}

	.hero-subtitle {
		font-size: 0.95rem;
		color: var(--text-secondary);
		line-height: 1.7;
		max-width: 560px;
	}

	/* ── Sections ── */
	.section-heading {
		font-size: 1.15rem;
		font-weight: 700;
		letter-spacing: -0.01em;
		margin-bottom: 0.5rem;
		color: var(--text-primary);
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.heading-marker {
		color: var(--complement);
		font-weight: 400;
		font-size: 1.1rem;
		opacity: 0.6;
	}

	.section-intro {
		font-size: 0.875rem;
		color: var(--text-secondary);
		margin-bottom: 1.5rem;
		line-height: 1.6;
	}

	/* ── Quick Path Cards ── */
	.quick-paths {
		margin-bottom: 3.5rem;
	}

	.path-grid {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.path-card {
		display: flex;
		align-items: flex-start;
		gap: 1.25rem;
		padding: 1.25rem 1.5rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		text-decoration: none;
		transition: all 0.2s var(--ease-premium);
		background: var(--bg-surface);
		box-shadow: var(--card-shadow);
	}

	.path-card:hover {
		border-color: var(--accent-border);
		background: var(--accent-soft);
		transform: translateX(4px);
	}

	.path-step {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		font-weight: 700;
		color: var(--accent);
		flex-shrink: 0;
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1.5px solid var(--accent-border);
		border-radius: var(--radius-sm);
		margin-top: 2px;
	}

	.path-content {
		flex: 1;
		min-width: 0;
	}

	.path-title {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.3rem;
	}

	.path-desc {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	.path-arrow {
		color: var(--text-muted);
		font-size: 1rem;
		flex-shrink: 0;
		transition: all 0.15s;
		margin-top: 4px;
	}

	.path-card:hover .path-arrow {
		color: var(--accent);
		transform: translateX(3px);
	}

	/* ── Capabilities Grid ── */
	.capabilities-section {
		margin-bottom: 3.5rem;
	}

	.cap-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 0.875rem;
	}

	.cap-card {
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-surface);
		transition: all 0.2s var(--ease-premium);
		position: relative;
		overflow: hidden;
		box-shadow: var(--card-shadow);
	}

	.cap-card:hover {
		border-color: var(--border-strong);
		transform: translateY(-2px);
	}

	.cap-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}

	.cap-number {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
	}

	.cap-label {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	.cap-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	.cap-desc {
		font-size: 0.75rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	.cap-indicator {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		height: 2px;
		opacity: 0.4;
		transition: opacity 0.2s;
	}

	.cap-card:hover .cap-indicator {
		opacity: 0.8;
	}

	/* ── Prerequisites ── */
	.prereq-section {
		margin-bottom: 3.5rem;
	}

	.prereq-table {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
	}

	.prereq-header-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.625rem 1.25rem;
		background: var(--bg-surface-alt);
		border-bottom: 1px solid var(--border);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	.prereq-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1.25rem;
		border-bottom: 1px solid var(--border);
		font-size: 0.8rem;
		color: var(--text-primary);
		transition: background 0.1s;
	}

	.prereq-row:last-child {
		border-bottom: none;
	}

	.prereq-row:hover {
		background: var(--accent-soft);
	}

	.prereq-item {
		flex: 1;
	}

	.prereq-type {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		letter-spacing: 0.06em;
		padding: 0.2rem 0.5rem;
		border-radius: 3px;
		flex-shrink: 0;
	}

	.prereq-type.required {
		color: var(--accent);
		background: var(--accent-soft);
	}

	.prereq-type.optional {
		color: var(--text-muted);
		background: var(--bg-surface-alt);
	}

	.prereq-type.recommended {
		color: var(--complement);
		background: var(--complement-soft);
	}

	/* ── Architecture Flow ── */
	.arch-section {
		margin-bottom: 3.5rem;
	}

	.arch-flow {
		display: flex;
		align-items: flex-start;
		gap: 0;
		padding: 1.5rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-surface);
		overflow-x: auto;
		box-shadow: var(--card-shadow);
	}

	.arch-node {
		flex: 1;
		min-width: 120px;
		text-align: center;
		position: relative;
	}

	.arch-node-num {
		width: 28px;
		height: 28px;
		margin: 0 auto 0.625rem;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 700;
		color: var(--accent);
		border: 1.5px solid var(--accent-border);
		border-radius: 50%;
		background: var(--accent-soft);
	}

	.arch-node-label {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.25rem;
	}

	.arch-node-detail {
		font-size: 0.7rem;
		color: var(--text-muted);
		line-height: 1.4;
	}

	.arch-connector {
		display: flex;
		align-items: center;
		padding-top: 12px;
		width: 40px;
		flex-shrink: 0;
	}

	.arch-connector-line {
		width: 100%;
		height: 1px;
		background: var(--border-strong);
		position: relative;
	}

	.arch-connector-line::after {
		content: '';
		position: absolute;
		right: -3px;
		top: -3px;
		width: 6px;
		height: 6px;
		border-right: 1.5px solid var(--accent);
		border-bottom: 1.5px solid var(--accent);
		transform: rotate(-45deg);
	}

	/* ── CTA ── */
	.cta-section {
		margin-bottom: 1rem;
	}

	.cta-card {
		padding: 1.75rem 2rem;
		border: 1px solid var(--complement-border);
		border-radius: var(--radius-sm);
		background: var(--complement-soft);
		position: relative;
	}

	.cta-label {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 700;
		color: var(--complement);
		letter-spacing: 0.12em;
		margin-bottom: 0.75rem;
	}

	.cta-title {
		font-size: 1.05rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	.cta-desc {
		font-size: 0.825rem;
		color: var(--text-secondary);
		margin-bottom: 1.25rem;
		line-height: 1.6;
	}

	.cta-button {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1.25rem;
		font-size: 0.825rem;
		font-weight: 600;
		color: var(--bg-app);
		background: var(--accent);
		border: none;
		border-radius: var(--radius-sm);
		text-decoration: none;
		transition: all 0.15s var(--ease-premium);
		cursor: pointer;
	}

	.cta-button:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.cta-arrow {
		transition: transform 0.15s;
	}

	.cta-button:hover .cta-arrow {
		transform: translateX(3px);
	}

	/* ── Responsive ── */
	@media (max-width: 640px) {
		.hero-title {
			font-size: 1.5rem;
		}

		.cap-grid {
			grid-template-columns: 1fr;
		}

		.arch-flow {
			flex-direction: column;
			align-items: stretch;
		}

		.arch-connector {
			width: auto;
			height: 24px;
			justify-content: center;
			padding-top: 0;
		}

		.arch-connector-line {
			width: 1px;
			height: 100%;
		}

		.arch-connector-line::after {
			right: -3px;
			top: auto;
			bottom: -3px;
			transform: rotate(45deg);
		}

		.path-card {
			padding: 1rem;
		}
	}
</style>
