<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<svelte:head>
	<title>Features & Tools — WithOps Documentation</title>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Docs</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Features & Tools</span>
	</div>

	<h1 class="page-title">Features & Tools Overview</h1>
	<p class="page-subtitle">
		Deep dive into the specialized security modules and technical tools of the WithOps platform.
	</p>

	<hr class="divider" />

	<div class="steps">
		<a href="/docs/features/workspace-intelligence" class="step-card">
			<div class="step-num">1</div>
			<div class="step-content">
				<h4>Workspace Intelligence</h4>
				<p>DSOMM-based maturity assessment and organization-wide security governance.</p>
				<span class="step-arrow">→</span>
			</div>
		</a>

		<a href="/docs/features/threat-modeling" class="step-card">
			<div class="step-num">2</div>
			<div class="step-content">
				<h4>Threat Modeling Canvas</h4>
				<p>Visual architecture design with automated STRIDE and CIA analysis.</p>
				<span class="step-arrow">→</span>
			</div>
		</a>

		<a href="/docs/features/action-audit" class="step-card">
			<div class="step-num">3</div>
			<div class="step-content">
				<h4>Action Audit</h4>
				<p>Supply chain security for GitHub Actions with automated PR remediation.</p>
				<span class="step-arrow">→</span>
			</div>
		</a>

		<a href="/docs/features/canvas-builder" class="step-card">
			<div class="step-num">4</div>
			<div class="step-content">
				<h4>Canvas Builder</h4>
				<p>Visual CI/CD workflow engineering and YAML code generation.</p>
				<span class="step-arrow">→</span>
			</div>
		</a>
	</div>
</div>

<style>
	.getting-started { opacity: 0; transform: translateY(10px); transition: all 0.5s ease; }
	.getting-started.visible { opacity: 1; transform: translateY(0); }
	.breadcrumb { display: flex; align-items: center; gap: 8px; font-family: 'DM Mono', monospace; font-size: 11px; margin-bottom: 24px; }
	.bc-link { color: var(--text-muted); text-decoration: none; }
	.bc-current { color: var(--accent); }
	.page-title { font-family: 'Playfair Display', serif; font-size: 38px; font-weight: 700; color: var(--text-primary); }
	.page-subtitle { font-family: 'Lora', serif; font-style: italic; font-size: 15px; color: var(--text-secondary); }
	.divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
	.steps { display: flex; flex-direction: column; gap: 12px; margin-top: 32px; }
	.step-card { display: flex; gap: 18px; padding: 24px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; text-decoration: none; color: inherit; transition: all 0.2s; position: relative; }
	.step-card:hover { border-color: var(--accent); transform: translateY(-2px); }
	.step-num { width: 32px; height: 32px; background: var(--bg-surface-2); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--accent); font-family: 'Playfair Display', serif; }
	.step-content h4 { font-weight: 600; font-size: 16px; margin-bottom: 4px; }
	.step-content p { font-size: 14px; color: var(--text-secondary); margin: 0; }
	.step-arrow { position: absolute; right: 24px; top: 50%; transform: translateY(-50%); color: var(--text-muted); }
</style>
