<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<svelte:head>
	<title>Workspace Intelligence — WithOps Documentation</title>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Docs</a>
		<span class="bc-sep">/</span>
		<a href="/docs/features" class="bc-link">Features & Tools</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Workspace Intelligence</span>
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
			<rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" />
			<line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" />
		</svg>
		Feature Overview
	</div>

	<h1 class="page-title" id="workspace-intelligence">Workspace Intelligence</h1>
	<p class="page-subtitle">
		DSOMM-Powered Security Maturity Assessment for your entire organization.
	</p>

	<hr class="divider" />

	<div class="prose">
		<h2 id="overview" class="section-heading">What is Workspace Intelligence?</h2>
		<p>
			Workspace Intelligence is the strategic "command center" of the WithOps platform. It provides
			a high-level, yet deeply technical, analysis of an entire organization's security posture. By
			scanning every repository, workflow, and policy, it determines the overall "Maturity Level" of
			your DevSecOps practices.
		</p>
		<p>
			Unlike traditional scanners that just list vulnerabilities, Workspace Intelligence evaluates <strong
				>governance and process</strong
			>. It tells you not just <em>if</em> you have a bug, but <em>how</em> well you are equipped to
			prevent, find, and fix bugs across your entire fleet.
		</p>

		<h2 id="dsomm" class="section-heading">The OWASP DSOMM Framework</h2>
		<p>
			Workspace Intelligence is built on the <strong>OWASP DSOMM (DevSecOps Maturity Model)</strong>
			framework. This is a real-world, industry-standard model for measuring how integrated security
			is within a development lifecycle.
		</p>

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
				<div class="callout-label">The 5 Core Dimensions</div>
				<p>
					1. Build & Deployment, 2. Implementation, 3. Test & Verification, 4. Information
					Gathering, 5. Culture & Organization.
				</p>
			</div>
		</div>

		<h2 id="maturity-levels" class="section-heading">Maturity Levels (L0 - L4)</h2>
		<ul>
			<li><strong>L0 (None):</strong> No security practices detected.</li>
			<li><strong>L1 (Basic):</strong> Occasional use of security tools or manual processes.</li>
			<li>
				<strong>L2 (Advanced):</strong> Consistent use of security tools across most repositories.
			</li>
			<li>
				<strong>L3 (Mature):</strong> Fully integrated security with automated gates and centralized
				governance.
			</li>
			<li>
				<strong>L4 (Optimized):</strong> Continuous improvement and proactive security measures.
			</li>
		</ul>

		<h2 id="key-features" class="section-heading">Key Features</h2>
		<div class="capability-grid">
			<div class="capability-card">
				<h4>Unified Analysis</h4>
				<p>
					Aggregates data from every project, providing a single "Maturity Score" for the whole
					company.
				</p>
			</div>
			<div class="capability-card">
				<h4>Practice Detection</h4>
				<p>
					Automatically identifies SAST, SCA, and Secret Scanning tools in your CI/CD pipelines.
				</p>
			</div>
			<div class="capability-card">
				<h4>AI Insights</h4>
				<p>Ask the AI "Why is my score low?" or "How do I reach Level 3?" for tailored advice.</p>
			</div>
		</div>
	</div>
</div>

<style>
	/* Use inherited styles from +layout.svelte */
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
	.section-heading {
		font-family: 'Playfair Display', serif;
		font-size: 22px;
		font-weight: 700;
		margin: 40px 0 12px;
		border-bottom: 1px solid var(--border);
		padding-bottom: 8px;
	}
	.prose p {
		font-family: 'Lora', serif;
		font-size: 15px;
		margin-bottom: 16px;
		line-height: 1.85;
	}
	.capability-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
		margin: 24px 0;
	}
	.capability-card {
		padding: 20px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 6px;
	}
	.capability-card h4 {
		font-weight: 600;
		margin-bottom: 8px;
		font-size: 15px;
	}
	.capability-card p {
		font-size: 13px;
		color: var(--text-secondary);
		margin: 0;
	}
	.callout {
		display: flex;
		gap: 14px;
		padding: 16px 20px;
		background: var(--callout-info-bg);
		border-left: 3px solid var(--accent);
		border-radius: 0 6px 6px 0;
		margin: 24px 0;
	}
	.callout-icon {
		color: var(--callout-info-text);
	}
	.callout-label {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		color: var(--accent);
		text-transform: uppercase;
		margin-bottom: 4px;
	}
</style>
