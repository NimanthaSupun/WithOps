<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<svelte:head>
	<title>Threat Modeling — WithOps Documentation</title>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Docs</a>
		<span class="bc-sep">/</span>
		<a href="/docs/features" class="bc-link">Features & Tools</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Threat Modeling</span>
	</div>

	<div class="chapter-tag">
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
			<line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
		</svg>
		Feature Overview
	</div>

	<h1 class="page-title" id="threat-modeling">Threat Modeling Canvas</h1>
	<p class="page-subtitle">
		Visual Security Design & AI-Powered Attack Surface Analysis.
	</p>

	<hr class="divider" />

	<div class="prose">
		<h2 id="overview" class="section-heading">What is Threat Modeling?</h2>
		<p>
			Threat modeling is the practice of "thinking like an attacker." It involves looking at a system's design and identifying potential security risks <em>before</em> a single line of code is written. 
		</p>
		<p>
			The <strong>Threat Modeling Canvas</strong> in WithOps is a visual, collaborative whiteboard where you can draw your system's architecture and let AI help you find the "hidden" threats in your design.
		</p>

		<h2 id="methodologies" class="section-heading">Methodologies Supported</h2>
		<div class="capability-grid">
			<div class="capability-card">
				<h4>STRIDE</h4>
				<p>Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege.</p>
			</div>
			<div class="capability-card">
				<h4>LINDDUN</h4>
				<p>Specifically for Privacy concerns like data linkage or non-repudiation.</p>
			</div>
			<div class="capability-card">
				<h4>CIA</h4>
				<p>The classic security triad: Confidentiality, Integrity, and Availability.</p>
			</div>
		</div>

		<h2 id="ai-analysis" class="section-heading">AI Security Engine</h2>
		<p>
			Once you draw your diagram, the AI "sees" your architecture and generates a structured security report including service overviews, threat scope, suggested threats, and recommended mitigations.
		</p>

		<div class="callout tip">
			<div class="callout-icon">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
				</svg>
			</div>
			<div class="callout-content">
				<div class="callout-label">Live Collaboration</div>
				<p>Multiple users can be on the same whiteboard simultaneously, seeing each other's cursor movements and shape placements in real-time.</p>
			</div>
		</div>
	</div>

	<div class="page-nav">
		<a href="/docs/features/workspace-intelligence" class="page-nav-btn prev">
			<span class="page-nav-label">← Previous</span>
			<span class="page-nav-title">Workspace Intelligence</span>
		</a>
		<a href="/docs/features/action-audit" class="page-nav-btn next">
			<span class="page-nav-label">Next →</span>
			<span class="page-nav-title">Action Audit</span>
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
	.callout { display: flex; gap: 14px; padding: 16px 20px; background: var(--callout-tip-bg); border-left: 3px solid var(--callout-tip-border); border-radius: 0 6px 6px 0; margin: 24px 0; }
	.callout-icon { color: var(--callout-tip-text); }
	.callout-label { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--callout-tip-text); text-transform: uppercase; margin-bottom: 4px; }
	.page-nav { display: flex; justify-content: space-between; margin-top: 40px; border-top: 1px solid var(--border); padding-top: 20px; }
	.page-nav-btn { text-decoration: none; }
	.page-nav-label { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--text-muted); }
	.page-nav-title { font-family: 'Lora', serif; display: block; color: var(--text-secondary); }
</style>
