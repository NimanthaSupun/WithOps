<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<svelte:head>
	<title>Canvas Builder — WithOps Documentation</title>
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Docs</a>
		<span class="bc-sep">/</span>
		<a href="/docs/features" class="bc-link">Features & Tools</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">Canvas Builder</span>
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
			<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
		</svg>
		Feature Overview
	</div>

	<h1 class="page-title" id="canvas-builder">Canvas Builder</h1>
	<p class="page-subtitle">Visual CI/CD Workflow Engineering and YAML Automation.</p>

	<hr class="divider" />

	<div class="prose">
		<h2 id="overview" class="section-heading">What is the Canvas Builder?</h2>
		<p>
			<strong>Canvas Builder</strong> is a visual orchestrator for your CI/CD pipelines. It turns complex,
			abstract YAML code into a clear, visual map of your automation. Instead of wrestling with indentation,
			you can build your workflows using a drag-and-drop interface.
		</p>

		<h2 id="core-features" class="section-heading">Core Features</h2>
		<div class="capability-grid">
			<div class="capability-card">
				<h4>Visual Mapping</h4>
				<p>See your workflow triggers, active states, and file paths as interactive blocks.</p>
			</div>
			<div class="capability-card">
				<h4>Relationship Detection</h4>
				<p>Automatically maps connections between calling workflows and reusable workflows.</p>
			</div>
			<div class="capability-card">
				<h4>Action Library</h4>
				<p>
					Drag predefined, pre-vetted actions (Checkout, Setup, Build, etc.) directly into your
					workflow.
				</p>
			</div>
		</div>

		<h2 id="yaml-sync" class="section-heading">YAML Synchronization</h2>
		<p>
			The Canvas Builder is a true WYSIWYG editor. As you modify your visual design, it generates
			the corresponding GitHub Actions YAML in the background. Saving your design automatically
			triggers a Pull Request to your repository to update the actual code.
		</p>

		<div class="callout tip">
			<div class="callout-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M22 12h-4l-3 9L9 3l-3 9H2" />
				</svg>
			</div>
			<div class="callout-content">
				<div class="callout-label">Zero Syntax Errors</div>
				<p>
					The platform handles all the formatting and schema compliance, ensuring you never push a
					workflow that fails due to a missing space or typo.
				</p>
			</div>
		</div>
	</div>
</div>

<style>
	/* Standard docs styles */
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
		background: var(--callout-tip-bg);
		border-left: 3px solid var(--callout-tip-border);
		border-radius: 0 6px 6px 0;
		margin: 24px 0;
	}
	.callout-icon {
		color: var(--callout-tip-text);
	}
	.callout-label {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		color: var(--callout-tip-text);
		text-transform: uppercase;
		margin-bottom: 4px;
	}
</style>
