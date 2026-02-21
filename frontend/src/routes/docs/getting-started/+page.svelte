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
			<span class="bc-current">Getting Started</span>
		</div>
		<h1 class="page-title" id="introduction">Introduction</h1>
		<p class="page-lead">
			Everything you need to know to get started with the WithOps DevSecOps Platform — from
			connecting your first repository to running your initial security analysis.
		</p>
	</div>

	<!-- Welcome Card -->
	<div class="notebook-card welcome-card">
		<div class="card-ribbon"></div>
		<div class="card-body">
			<div class="card-icon">
				<svg
					width="24"
					height="24"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<path
						d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"
					/>
					<path
						d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"
					/>
					<path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
					<path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
				</svg>
			</div>
			<div class="card-text">
				<h3>Welcome to WithOps</h3>
				<p>
					WithOps is an AI-powered DevSecOps platform that automates security analysis, threat
					modeling, and CI/CD workflow monitoring — the complete <strong
						>"Everything After Code"</strong
					> solution for modern development teams.
				</p>
			</div>
		</div>
	</div>

	<!-- What You'll Learn -->
	<h2 id="what-youll-learn">What You'll Learn</h2>
	<p class="body-text">
		This guide covers the essential steps to get your environment ready and start leveraging the
		platform's security intelligence capabilities.
	</p>

	<div class="steps-overview">
		<a href="/docs/getting-started/quick-start" class="step-preview">
			<div class="step-num">01</div>
			<div class="step-info">
				<h4>Quick Start</h4>
				<p>Set up prerequisites and access the platform in under 2 minutes.</p>
			</div>
			<svg
				class="step-arrow"
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"><polyline points="9 18 15 12 9 6" /></svg
			>
		</a>
		<a href="/docs/getting-started/connecting-github" class="step-preview">
			<div class="step-num">02</div>
			<div class="step-info">
				<h4>Connecting GitHub</h4>
				<p>Link your GitHub organizations and repositories for automated scanning.</p>
			</div>
			<svg
				class="step-arrow"
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"><polyline points="9 18 15 12 9 6" /></svg
			>
		</a>
		<a href="/docs/getting-started/first-security-scan" class="step-preview">
			<div class="step-num">03</div>
			<div class="step-info">
				<h4>First Security Scan</h4>
				<p>Run your initial scan and interpret the results with AI-powered insights.</p>
			</div>
			<svg
				class="step-arrow"
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"><polyline points="9 18 15 12 9 6" /></svg
			>
		</a>
	</div>

	<!-- Platform Overview -->
	<h2 id="platform-overview">Platform at a Glance</h2>
	<p class="body-text">
		WithOps integrates multiple security and DevOps capabilities into a single, unified platform.
	</p>

	<div class="capabilities-grid">
		<div class="capability-card">
			<div class="cap-icon purple">
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
			<h4>AI Security Analysis</h4>
			<p>
				Automated vulnerability detection with AI-generated remediation suggestions and CVSS
				scoring.
			</p>
		</div>
		<div class="capability-card">
			<div class="cap-icon blue">
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<path
						d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
					/><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
				</svg>
			</div>
			<h4>Threat Modeling</h4>
			<p>
				STRIDE-based analysis with attack surface mapping and risk scoring for your architecture.
			</p>
		</div>
		<div class="capability-card">
			<div class="cap-icon green">
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<path
						d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
						fill="currentColor"
						stroke="none"
					/>
				</svg>
			</div>
			<h4>GitHub Integration</h4>
			<p>Deep integration with organizations, repos, PR automation, and Actions monitoring.</p>
		</div>
		<div class="capability-card">
			<div class="cap-icon amber">
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
				</svg>
			</div>
			<h4>Workflow Orchestration</h4>
			<p>
				CI/CD pipeline analysis, security scanning integration, and real-time execution monitoring.
			</p>
		</div>
	</div>

	<!-- Prerequisites Callout -->
	<h2 id="prerequisites">Prerequisites</h2>

	<div class="callout callout-info">
		<div class="callout-icon">
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line
					x1="12"
					y1="8"
					x2="12.01"
					y2="8"
				/>
			</svg>
		</div>
		<div class="callout-content">
			<strong>Before you begin</strong>
			<p>Make sure you have the following ready to get the most out of WithOps.</p>
		</div>
	</div>

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
				<strong>GitHub Account</strong>
				<span class="prereq-detail">— with access to at least one organization or repository</span>
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
				<strong>Modern Browser</strong>
				<span class="prereq-detail">— Chrome, Firefox, Safari, or Edge (latest version)</span>
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
				<strong>GitHub Organization Admin</strong>
				<span class="prereq-detail"
					>— required for installing the WithOps GitHub App (optional for basic scanning)</span
				>
			</div>
		</div>
	</div>

	<!-- Estimated Time -->
	<div class="callout callout-tip">
		<div class="callout-icon">
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
			</svg>
		</div>
		<div class="callout-content">
			<strong>Estimated time: ~5 minutes</strong>
			<p>From sign-up to your first security scan results.</p>
		</div>
	</div>

	<!-- Architecture Brief -->
	<h2 id="how-it-works">How It Works</h2>
	<p class="body-text">
		WithOps uses a microservices architecture with 8 specialized services coordinated through a Kong
		API Gateway. Here's a simplified view of the data flow:
	</p>

	<div class="arch-flow">
		<div class="flow-node">
			<div class="flow-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					><rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line
						x1="8"
						y1="21"
						x2="16"
						y2="21"
					/><line x1="12" y1="17" x2="12" y2="21" /></svg
				>
			</div>
			<span>Your Browser</span>
		</div>
		<div class="flow-connector">
			<svg width="24" height="12" viewBox="0 0 24 12"
				><path d="M0 6h20M16 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" fill="none" /></svg
			>
		</div>
		<div class="flow-node highlight">
			<div class="flow-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg
				>
			</div>
			<span>Kong Gateway</span>
		</div>
		<div class="flow-connector">
			<svg width="24" height="12" viewBox="0 0 24 12"
				><path d="M0 6h20M16 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" fill="none" /></svg
			>
		</div>
		<div class="flow-node">
			<div class="flow-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					><rect x="2" y="2" width="20" height="8" rx="2" ry="2" /><rect
						x="2"
						y="14"
						width="20"
						height="8"
						rx="2"
						ry="2"
					/><line x1="6" y1="6" x2="6.01" y2="6" /><line x1="6" y1="18" x2="6.01" y2="18" /></svg
				>
			</div>
			<span>Microservices</span>
		</div>
		<div class="flow-connector">
			<svg width="24" height="12" viewBox="0 0 24 12"
				><path d="M0 6h20M16 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" fill="none" /></svg
			>
		</div>
		<div class="flow-node">
			<div class="flow-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					><ellipse cx="12" cy="5" rx="9" ry="3" /><path
						d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"
					/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg
				>
			</div>
			<span>AI + Data</span>
		</div>
	</div>

	<!-- Next Step -->
	<div class="next-step-card">
		<div class="next-step-text">
			<h3>Ready to begin?</h3>
			<p>
				Start with the Quick Start guide to set up your WithOps account and connect your first
				repository.
			</p>
		</div>
		<a href="/docs/getting-started/quick-start" class="next-step-btn">
			Start Quick Start
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
	   GETTING STARTED — INTRODUCTION
	   Sophisticated notebook styling
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

	/* Headings */
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

	/* ── Welcome Card ── */
	.notebook-card {
		border: 1px solid var(--border);
		border-radius: 10px;
		overflow: hidden;
		margin-bottom: 2rem;
		background: var(--bg-surface);
		box-shadow: var(--shadow-sm);
		position: relative;
	}

	.card-ribbon {
		height: 3px;
		background: linear-gradient(90deg, var(--accent), transparent);
	}

	.card-body {
		padding: 1.5rem;
		display: flex;
		gap: 1.25rem;
		align-items: flex-start;
	}

	.card-icon {
		flex-shrink: 0;
		width: 40px;
		height: 40px;
		border-radius: 8px;
		background: var(--accent-soft);
		border: 1px solid var(--accent-border);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--accent);
	}

	.card-text h3 {
		font-family: var(--font-serif);
		font-size: 1rem;
		font-weight: 700;
		margin-bottom: 0.375rem;
		color: var(--text-primary);
	}

	.card-text p {
		font-size: 0.85rem;
		line-height: 1.65;
		color: var(--text-secondary);
	}

	.card-text strong {
		color: var(--accent);
		font-weight: 600;
	}

	/* ── Steps Overview ── */
	.steps-overview {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.step-preview {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: 10px;
		text-decoration: none;
		transition: all 0.15s cubic-bezier(0.2, 0, 0, 1);
		background: var(--bg-surface);
	}

	.step-preview:hover {
		border-color: var(--accent-border);
		background: var(--accent-soft);
		transform: translateX(4px);
	}

	.step-num {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 700;
		color: var(--accent);
		background: var(--accent-soft);
		border: 1px solid var(--accent-border);
		border-radius: 6px;
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.step-info {
		flex: 1;
		min-width: 0;
	}

	.step-info h4 {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.125rem;
	}

	.step-info p {
		font-size: 0.775rem;
		color: var(--text-muted);
		line-height: 1.4;
	}

	.step-arrow {
		color: var(--text-muted);
		flex-shrink: 0;
		transition: transform 0.15s;
	}

	.step-preview:hover .step-arrow {
		color: var(--accent);
		transform: translateX(3px);
	}

	/* ── Capabilities Grid ── */
	.capabilities-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.capability-card {
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--bg-surface);
		transition: border-color 0.15s;
	}

	.capability-card:hover {
		border-color: var(--border-strong);
	}

	.cap-icon {
		width: 32px;
		height: 32px;
		border-radius: 7px;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 0.75rem;
	}

	.cap-icon.purple {
		background: rgba(167, 139, 250, 0.1);
		color: #a78bfa;
		border: 1px solid rgba(167, 139, 250, 0.15);
	}
	.cap-icon.blue {
		background: rgba(96, 165, 250, 0.1);
		color: #60a5fa;
		border: 1px solid rgba(96, 165, 250, 0.15);
	}
	.cap-icon.green {
		background: rgba(52, 211, 153, 0.1);
		color: #34d399;
		border: 1px solid rgba(52, 211, 153, 0.15);
	}
	.cap-icon.amber {
		background: rgba(251, 191, 36, 0.1);
		color: #fbbf24;
		border: 1px solid rgba(251, 191, 36, 0.15);
	}

	.capability-card h4 {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.375rem;
	}

	.capability-card p {
		font-size: 0.775rem;
		color: var(--text-muted);
		line-height: 1.55;
	}

	/* ── Callouts ── */
	.callout {
		display: flex;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		border-radius: 8px;
		margin: 1.25rem 0;
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
		transition: border-color 0.15s;
	}

	.prereq-item:hover {
		border-color: var(--border-strong);
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

	/* ── Architecture Flow ── */
	.arch-flow {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 1.5rem;
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--bg-surface);
		margin-bottom: 2rem;
		overflow-x: auto;
		scrollbar-width: thin;
	}

	.flow-node {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-surface-2);
		flex-shrink: 0;
		min-width: 100px;
		transition: border-color 0.15s;
	}

	.flow-node.highlight {
		border-color: var(--accent-border);
		background: var(--accent-soft);
	}

	.flow-icon {
		color: var(--text-secondary);
	}

	.flow-node.highlight .flow-icon {
		color: var(--accent);
	}

	.flow-node span {
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-secondary);
		white-space: nowrap;
	}

	.flow-node.highlight span {
		color: var(--accent);
	}

	.flow-connector {
		color: var(--text-muted);
		flex-shrink: 0;
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

	/* ── Responsive ── */
	@media (max-width: 768px) {
		.page-title {
			font-size: 1.75rem;
		}
		.capabilities-grid {
			grid-template-columns: 1fr;
		}
		.arch-flow {
			flex-wrap: wrap;
			justify-content: center;
		}
		.flow-connector {
			transform: rotate(90deg);
		}
		.next-step-card {
			flex-direction: column;
			text-align: center;
		}
	}
</style>
