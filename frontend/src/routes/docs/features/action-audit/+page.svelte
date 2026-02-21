<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<svelte:head>
	<title>Action Audit — WithOps Documentation</title>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Docs</a>
		<span class="bc-sep">/</span>
		<a href="/docs/features" class="bc-link">Features & Tools</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Action Audit</span>
	</div>

	<div class="chapter-tag">
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" />
		</svg>
		Feature Overview
	</div>

	<h1 class="page-title" id="action-audit">Action Audit</h1>
	<p class="page-subtitle">
		GitHub Actions Supply Chain Governance and Automated Version Remediation.
	</p>

	<hr class="divider" />

	<div class="prose">
		<h2 id="overview" class="section-heading">What is Action Audit?</h2>
		<p>
			<strong>Action Audit</strong> is a specialized security governance tool that monitors, audits, and automatically remediates the versions of GitHub Actions used across your entire organization.
		</p>
		<p>
			Every third-party action you use in your CI/CD pipelines is a potential security risk. Action Audit provides transparency into your supply chain by identifying every action and its version compliance status.
		</p>

		<h2 id="status-categories" class="section-heading">Compliance Status</h2>
		<div class="capability-grid">
			<div class="capability-card">
				<h4>✅ Up to Date</h4>
				<p>You are using the latest version available in the GitHub Marketplace.</p>
			</div>
			<div class="capability-card">
				<h4>🚨 Major Upgrade Needed</h4>
				<p>You are on an old major version (e.g., v1 when v3 is out), likely missing critical security patches.</p>
			</div>
			<div class="capability-card">
				<h4>⚠️ Outdated</h4>
				<p>A minor version update or bug fix is available for your current action.</p>
			</div>
		</div>

		<h2 id="remediation" class="section-heading">Automated Remediation</h2>
		<p>
			Instead of just listing problems, Action Audit can fix them. The <strong>"Fix via PR"</strong> feature automatically creates a branch, updates the YAML file to the latest version, and opens a Pull Request for you to review and merge.
		</p>

		<div class="callout warn">
			<div class="callout-icon">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
				</svg>
			</div>
			<div class="callout-content">
				<div class="callout-label">Supply Chain Security</div>
				<p>By monitoring the Marketplace Name and Owner of actions, the system helps you ensure you are using official actions, not malicious clones (Anti-Typosquatting).</p>
			</div>
		</div>
	</div>

	<div class="page-nav">
		<a href="/docs/features/threat-modeling" class="page-nav-btn prev">
			<span class="page-nav-label">← Previous</span>
			<span class="page-nav-title">Threat Modeling</span>
		</a>
		<a href="/docs/features/canvas-builder" class="page-nav-btn next">
			<span class="page-nav-label">Next →</span>
			<span class="page-nav-title">Canvas Builder</span>
		</a>
	</div>
</div>

<style>
	/* Standard docs styles */
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
	.capability-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 24px 0; }
	.capability-card { padding: 20px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; }
	.capability-card h4 { font-weight: 600; margin-bottom: 8px; font-size: 15px; }
	.capability-card p { font-size: 13px; color: var(--text-secondary); margin: 0; }
	.callout { display: flex; gap: 14px; padding: 16px 20px; background: var(--callout-warn-bg); border-left: 3px solid var(--callout-warn-border); border-radius: 0 6px 6px 0; margin: 24px 0; }
	.callout-icon { color: var(--callout-warn-text); }
	.callout-label { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--callout-warn-text); text-transform: uppercase; margin-bottom: 4px; }
	.page-nav { display: flex; justify-content: space-between; margin-top: 40px; border-top: 1px solid var(--border); padding-top: 20px; }
	.page-nav-btn { text-decoration: none; }
	.page-nav-label { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--text-muted); }
	.page-nav-title { font-family: 'Lora', serif; display: block; color: var(--text-secondary); }
</style>
