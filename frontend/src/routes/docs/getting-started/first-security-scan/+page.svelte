<script>
	import { isDarkMode } from '$lib/stores.js';
	import { onMount } from 'svelte';

	let darkMode = $state(false);
	isDarkMode.subscribe((v) => (darkMode = v));

	let scanProgress = $state(0);
	let scanRunning = $state(false);
	let scanComplete = $state(false);

	function startScanDemo() {
		if (scanRunning) return;
		scanRunning = true;
		scanComplete = false;
		scanProgress = 0;
		const interval = setInterval(() => {
			scanProgress += Math.random() * 8 + 2;
			if (scanProgress >= 100) {
				scanProgress = 100;
				scanRunning = false;
				scanComplete = true;
				clearInterval(interval);
			}
		}, 200);
	}

	const scanDimensions = [
		{
			num: '01',
			label: 'SAST',
			title: 'Static Analysis',
			description:
				'Analyzes source code patterns, control flow, and data flow to identify security flaws before runtime.',
			color: '#00adef'
		},
		{
			num: '02',
			label: 'SCA',
			title: 'Dependency Scan',
			description:
				'Maps your dependency graph and cross-references against CVE databases for known vulnerabilities.',
			color: '#10b981'
		},
		{
			num: '03',
			label: 'SECRETS',
			title: 'Secret Detection',
			description:
				'Scans for hardcoded credentials, API keys, tokens, and other sensitive data in code and configuration files.',
			color: '#d4a054'
		},
		{
			num: '04',
			label: 'IaC',
			title: 'Infrastructure Scan',
			description:
				'Validates Infrastructure-as-Code templates (Terraform, CloudFormation, Kubernetes) against security benchmarks.',
			color: '#8b5cf6'
		},
		{
			num: '05',
			label: 'LICENSE',
			title: 'License Compliance',
			description:
				'Identifies open-source license types and flags potential compliance risks in your dependency chain.',
			color: '#06b6d4'
		}
	];

	const severityLevels = [
		{
			level: 'Critical',
			color: '#ef4444',
			score: '9.0 — 10.0',
			action: 'Immediate fix required. Blocks deployment.',
			indicator: '████'
		},
		{
			level: 'High',
			color: '#f97316',
			score: '7.0 — 8.9',
			action: 'Fix within 24 hours. PR blocked.',
			indicator: '███░'
		},
		{
			level: 'Medium',
			color: '#f59e0b',
			score: '4.0 — 6.9',
			action: 'Fix within sprint. Warning issued.',
			indicator: '██░░'
		},
		{
			level: 'Low',
			color: '#10b981',
			score: '0.1 — 3.9',
			action: 'Track and address in maintenance.',
			indicator: '█░░░'
		},
		{
			level: 'Info',
			color: '#64748b',
			score: '0.0',
			action: 'Informational only. No action needed.',
			indicator: '░░░░'
		}
	];

	const exampleFinding = {
		id: 'WO-2024-0847',
		title: 'SQL Injection via unsanitized user input',
		severity: 'Critical',
		file: 'src/api/routes/users.js',
		line: '47',
		scanner: 'SAST',
		cwe: 'CWE-89',
		description:
			'User-supplied input is concatenated directly into a SQL query string without parameterization, enabling SQL injection attacks.',
		recommendation:
			'Use parameterized queries or an ORM. Replace string concatenation with prepared statements.'
	};

	const maturityLevels = [
		{
			level: 1,
			label: 'Initial',
			desc: 'Ad-hoc scanning, no consistent process',
			threshold: '0-20'
		},
		{ level: 2, label: 'Developing', desc: 'Regular scans on main branches', threshold: '21-40' },
		{
			level: 3,
			label: 'Defined',
			desc: 'Automated pipeline integration, SLA tracking',
			threshold: '41-60'
		},
		{
			level: 4,
			label: 'Managed',
			desc: 'Policy enforcement, trend analysis, remediation SLAs',
			threshold: '61-80'
		},
		{
			level: 5,
			label: 'Optimizing',
			desc: 'Proactive threat modeling, zero critical backlog',
			threshold: '81-100'
		}
	];

	onMount(() => {
		isDarkMode.init();
	});
</script>

<div class="scan-page">
	<!-- Header -->
	<header class="page-header">
		<div class="page-badge">REFERENCE</div>
		<h1 class="page-title">First Security Scan</h1>
		<p class="page-desc">
			Understand how WithOps analyzes your code, what the results mean, and how to act on findings
			to improve your security posture.
		</p>
	</header>

	<!-- Scan Dimensions -->
	<section class="dimensions-section" id="dimensions-section">
		<h2 id="scan-dimensions" class="section-heading">
			<span class="heading-marker">§</span>
			Scan Dimensions
		</h2>
		<p class="section-intro">Each scan executes multiple analysis engines in parallel.</p>

		<div class="dim-grid">
			{#each scanDimensions as dim}
				<div class="dim-card">
					<div class="dim-header">
						<span class="dim-number" style="color: {dim.color}">{dim.num}</span>
						<span class="dim-label">{dim.label}</span>
					</div>
					<h3 class="dim-title">{dim.title}</h3>
					<p class="dim-desc">{dim.description}</p>
					<div class="dim-indicator" style="background: {dim.color}"></div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Interactive Scan Demo -->
	<section class="demo-section" id="demo-section">
		<h2 id="run-a-scan" class="section-heading">
			<span class="heading-marker">§</span>
			Run a Scan
		</h2>
		<p class="section-intro">See how a scan progresses through the analysis pipeline.</p>

		<div class="scan-demo">
			<div class="demo-header">
				<div class="demo-title-row">
					<span class="demo-label">SCAN SIMULATION</span>
					<span class="demo-status" class:running={scanRunning} class:complete={scanComplete}>
						{#if scanComplete}
							COMPLETE
						{:else if scanRunning}
							ANALYZING...
						{:else}
							READY
						{/if}
					</span>
				</div>
			</div>

			<div class="demo-body">
				<div class="progress-track">
					<div class="progress-fill" style="width: {scanProgress}%"></div>
				</div>
				<div class="progress-info">
					<span class="progress-pct">{Math.round(scanProgress)}%</span>
					<span class="progress-stage">
						{#if scanProgress === 0}
							Waiting for input
						{:else if scanProgress < 20}
							Initializing scanners...
						{:else if scanProgress < 40}
							Static analysis (SAST)...
						{:else if scanProgress < 60}
							Dependency scanning (SCA)...
						{:else if scanProgress < 80}
							Secret detection...
						{:else if scanProgress < 95}
							Infrastructure scan (IaC)...
						{:else}
							Generating report...
						{/if}
					</span>
				</div>

				{#if scanComplete}
					<div class="scan-results-summary">
						<div class="result-stat">
							<span class="stat-value critical">2</span>
							<span class="stat-label">Critical</span>
						</div>
						<div class="result-stat">
							<span class="stat-value high">5</span>
							<span class="stat-label">High</span>
						</div>
						<div class="result-stat">
							<span class="stat-value medium">12</span>
							<span class="stat-label">Medium</span>
						</div>
						<div class="result-stat">
							<span class="stat-value low">23</span>
							<span class="stat-label">Low</span>
						</div>
					</div>
				{/if}

				<button class="scan-btn" onclick={startScanDemo} disabled={scanRunning}>
					{#if scanComplete}
						Run Again
					{:else if scanRunning}
						<span class="btn-spinner"></span>
						Scanning...
					{:else}
						Start Scan Demo
					{/if}
				</button>
			</div>
		</div>
	</section>

	<!-- Severity Levels -->
	<section class="severity-section" id="severity-section">
		<h2 id="severity-levels" class="section-heading">
			<span class="heading-marker">§</span>
			Severity Classification
		</h2>
		<p class="section-intro">Findings are scored using CVSS v3.1 and mapped to action levels.</p>

		<div class="severity-table">
			<div class="severity-header">
				<span class="sev-col-level">Level</span>
				<span class="sev-col-score">CVSS Range</span>
				<span class="sev-col-action">Required Action</span>
			</div>
			{#each severityLevels as sev}
				<div class="severity-row">
					<span class="sev-level">
						<span class="sev-indicator" style="color: {sev.color}">{sev.indicator}</span>
						<span class="sev-name" style="color: {sev.color}">{sev.level}</span>
					</span>
					<span class="sev-score">{sev.score}</span>
					<span class="sev-action">{sev.action}</span>
				</div>
			{/each}
		</div>
	</section>

	<!-- Example Finding -->
	<section class="finding-section" id="finding-section">
		<h2 id="example-finding" class="section-heading">
			<span class="heading-marker">§</span>
			Anatomy of a Finding
		</h2>
		<p class="section-intro">A detailed look at what a security finding contains.</p>

		<div class="finding-card">
			<div class="finding-header">
				<div class="finding-id">{exampleFinding.id}</div>
				<span class="finding-severity">{exampleFinding.severity.toUpperCase()}</span>
			</div>
			<h3 class="finding-title">{exampleFinding.title}</h3>

			<div class="finding-meta">
				<div class="meta-item">
					<span class="meta-key">File</span>
					<code class="meta-value">{exampleFinding.file}:{exampleFinding.line}</code>
				</div>
				<div class="meta-item">
					<span class="meta-key">Scanner</span>
					<span class="meta-value">{exampleFinding.scanner}</span>
				</div>
				<div class="meta-item">
					<span class="meta-key">CWE</span>
					<span class="meta-value">{exampleFinding.cwe}</span>
				</div>
			</div>

			<div class="finding-body">
				<div class="finding-block">
					<div class="block-label">DESCRIPTION</div>
					<p class="block-text">{exampleFinding.description}</p>
				</div>
				<div class="finding-block">
					<div class="block-label">RECOMMENDATION</div>
					<p class="block-text">{exampleFinding.recommendation}</p>
				</div>
			</div>
		</div>
	</section>

	<!-- Security Maturity -->
	<section class="maturity-section" id="maturity-section">
		<h2 id="maturity-score" class="section-heading">
			<span class="heading-marker">§</span>
			Security Maturity Model
		</h2>
		<p class="section-intro">Track your team's security posture evolution over time.</p>

		<div class="maturity-scale">
			{#each maturityLevels as m}
				<div class="maturity-item">
					<div class="maturity-level-num">L{m.level}</div>
					<div class="maturity-content">
						<div class="maturity-bar-wrap">
							<div class="maturity-bar" style="width: {m.level * 20}%"></div>
						</div>
						<div class="maturity-info">
							<strong class="maturity-name">{m.label}</strong>
							<span class="maturity-threshold">{m.threshold}</span>
						</div>
						<p class="maturity-desc">{m.desc}</p>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Completion Card -->
	<section class="completion-section">
		<div class="completion-card">
			<div class="completion-check">
				<svg
					width="24"
					height="24"
					viewBox="0 0 24 24"
					fill="none"
					stroke="var(--success)"
					stroke-width="2"
				>
					<path d="M20 6L9 17l-5-5" />
				</svg>
			</div>
			<h3 class="completion-title">Getting Started — Complete</h3>
			<p class="completion-desc">
				You've covered the fundamentals. You now understand how to set up WithOps, connect your
				repositories, run security scans, and interpret results.
			</p>
			<div class="completion-actions">
				<a href="/dashboard" class="action-btn primary">
					Go to Dashboard
					<span class="action-arrow">→</span>
				</a>
				<a href="/docs/getting-started" class="action-btn secondary"> Back to Overview </a>
			</div>
		</div>
	</section>
</div>

<style>
	.scan-page {
		max-width: 720px;
	}

	/* ── Header ── */
	.page-header {
		margin-bottom: 2.5rem;
		padding-bottom: 1.75rem;
		border-bottom: 1px dashed var(--border);
	}

	.page-badge {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 700;
		color: var(--complement);
		letter-spacing: 0.12em;
		margin-bottom: 0.75rem;
	}

	.page-title {
		font-size: 1.75rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		color: var(--text-primary);
		margin-bottom: 0.625rem;
	}

	.page-desc {
		font-size: 0.9rem;
		color: var(--text-secondary);
		line-height: 1.65;
		max-width: 540px;
	}

	/* ── Section Heading ── */
	.section-heading {
		font-size: 1.1rem;
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
		font-size: 1.05rem;
		opacity: 0.6;
	}

	.section-intro {
		font-size: 0.875rem;
		color: var(--text-secondary);
		margin-bottom: 1.5rem;
		line-height: 1.6;
	}

	/* ── Scan Dimensions ── */
	.dimensions-section {
		margin-bottom: 2.5rem;
	}

	.dim-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 0.75rem;
	}

	.dim-card {
		padding: 1.125rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-surface);
		transition: all 0.2s var(--ease-premium);
		position: relative;
		overflow: hidden;
		box-shadow: var(--card-shadow);
	}

	.dim-card:hover {
		border-color: var(--border-strong);
		transform: translateY(-1px);
	}

	.dim-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.625rem;
	}

	.dim-number {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 700;
	}

	.dim-label {
		font-family: var(--font-mono);
		font-size: 0.5rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	.dim-title {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.375rem;
	}

	.dim-desc {
		font-size: 0.725rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	.dim-indicator {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		height: 2px;
		opacity: 0.35;
		transition: opacity 0.2s;
	}

	.dim-card:hover .dim-indicator {
		opacity: 0.75;
	}

	/* ── Scan Demo ── */
	.demo-section {
		margin-bottom: 2.5rem;
	}

	.scan-demo {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
		background: var(--bg-surface);
		box-shadow: var(--card-shadow);
	}

	.demo-header {
		padding: 0.75rem 1.25rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface-alt);
	}

	.demo-title-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.demo-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	.demo-status {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.06em;
	}

	.demo-status.running {
		color: var(--accent);
	}

	.demo-status.complete {
		color: var(--success);
	}

	.demo-body {
		padding: 1.25rem;
	}

	.progress-track {
		height: 4px;
		background: var(--bg-surface-alt);
		border-radius: 2px;
		overflow: hidden;
		margin-bottom: 0.75rem;
	}

	.progress-fill {
		height: 100%;
		background: var(--accent);
		border-radius: 2px;
		transition: width 0.3s var(--ease-premium);
	}

	.progress-info {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.25rem;
	}

	.progress-pct {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		font-weight: 700;
		color: var(--accent);
	}

	.progress-stage {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
	}

	.scan-results-summary {
		display: flex;
		gap: 1.5rem;
		margin-bottom: 1.25rem;
		padding: 1rem;
		border: 1px dashed var(--border);
		border-radius: var(--radius-sm);
	}

	.result-stat {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.25rem;
	}

	.stat-value {
		font-family: var(--font-mono);
		font-size: 1.25rem;
		font-weight: 800;
	}

	.stat-value.critical {
		color: #ef4444;
	}
	.stat-value.high {
		color: #f97316;
	}
	.stat-value.medium {
		color: #f59e0b;
	}
	.stat-value.low {
		color: #10b981;
	}

	.stat-label {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.scan-btn {
		width: 100%;
		padding: 0.75rem;
		font-size: 0.825rem;
		font-weight: 600;
		font-family: var(--font-sans);
		color: var(--bg-app);
		background: var(--accent);
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all 0.15s var(--ease-premium);
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}

	.scan-btn:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.scan-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ── Severity Table ── */
	.severity-section {
		margin-bottom: 2.5rem;
	}

	.severity-table {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
	}

	.severity-header {
		display: grid;
		grid-template-columns: 1.2fr 0.8fr 1.8fr;
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

	.severity-row {
		display: grid;
		grid-template-columns: 1.2fr 0.8fr 1.8fr;
		padding: 0.65rem 1.25rem;
		border-bottom: 1px solid var(--border);
		font-size: 0.8rem;
		align-items: center;
		transition: background 0.1s;
	}

	.severity-row:last-child {
		border-bottom: none;
	}

	.severity-row:hover {
		background: var(--accent-soft);
	}

	.sev-level {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.sev-indicator {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.05em;
	}

	.sev-name {
		font-weight: 600;
		font-size: 0.8rem;
	}

	.sev-score {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	.sev-action {
		font-size: 0.775rem;
		color: var(--text-secondary);
	}

	/* ── Example Finding ── */
	.finding-section {
		margin-bottom: 2.5rem;
	}

	.finding-card {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
		background: var(--bg-surface);
		box-shadow: var(--card-shadow);
	}

	.finding-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1.25rem;
		background: var(--bg-surface-alt);
		border-bottom: 1px solid var(--border);
	}

	.finding-id {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.04em;
	}

	.finding-severity {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: #ef4444;
		padding: 0.15rem 0.5rem;
		background: rgba(239, 68, 68, 0.08);
		border-radius: 3px;
		letter-spacing: 0.06em;
	}

	.finding-title {
		padding: 1rem 1.25rem 0.75rem;
		font-size: 0.95rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.finding-meta {
		padding: 0 1.25rem;
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.meta-key {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}

	.meta-value {
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	code.meta-value {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		padding: 0.1rem 0.35rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--accent);
	}

	.finding-body {
		padding: 0 1.25rem 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.875rem;
	}

	.finding-block {
		padding: 0.875rem;
		border: 1px dashed var(--border);
		border-radius: var(--radius-sm);
	}

	.block-label {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		margin-bottom: 0.4rem;
	}

	.block-text {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	/* ── Security Maturity ── */
	.maturity-section {
		margin-bottom: 2.5rem;
	}

	.maturity-scale {
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
	}

	.maturity-item {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 0.875rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		transition: background 0.1s;
	}

	.maturity-item:hover {
		background: var(--accent-soft);
	}

	.maturity-level-num {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		color: var(--accent);
		flex-shrink: 0;
		width: 24px;
		margin-top: 2px;
	}

	.maturity-content {
		flex: 1;
		min-width: 0;
	}

	.maturity-bar-wrap {
		height: 3px;
		background: var(--bg-surface-alt);
		border-radius: 2px;
		overflow: hidden;
		margin-bottom: 0.5rem;
	}

	.maturity-bar {
		height: 100%;
		background: var(--accent);
		border-radius: 2px;
		transition: width 0.6s var(--ease-premium);
	}

	.maturity-info {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.2rem;
	}

	.maturity-name {
		font-size: 0.825rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.maturity-threshold {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text-muted);
	}

	.maturity-desc {
		font-size: 0.75rem;
		color: var(--text-secondary);
		line-height: 1.45;
	}

	/* ── Completion ── */
	.completion-section {
		margin-bottom: 1rem;
	}

	.completion-card {
		text-align: center;
		padding: 2.5rem 2rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-surface);
		box-shadow: var(--card-shadow);
	}

	.completion-check {
		margin: 0 auto 1rem;
		width: 48px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 2px solid rgba(16, 185, 129, 0.2);
		border-radius: 50%;
		background: rgba(16, 185, 129, 0.05);
	}

	.completion-title {
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	.completion-desc {
		font-size: 0.825rem;
		color: var(--text-secondary);
		line-height: 1.6;
		max-width: 480px;
		margin: 0 auto 1.5rem;
	}

	.completion-actions {
		display: flex;
		gap: 0.75rem;
		justify-content: center;
		flex-wrap: wrap;
	}

	.action-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.625rem 1.25rem;
		font-size: 0.825rem;
		font-weight: 600;
		border-radius: var(--radius-sm);
		text-decoration: none;
		transition: all 0.15s var(--ease-premium);
		cursor: pointer;
	}

	.action-btn.primary {
		background: var(--accent);
		color: var(--bg-app);
		border: none;
	}

	.action-btn.primary:hover {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.action-btn.secondary {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
	}

	.action-btn.secondary:hover {
		border-color: var(--border-strong);
		color: var(--text-primary);
	}

	.action-arrow {
		transition: transform 0.15s;
	}

	.action-btn:hover .action-arrow {
		transform: translateX(3px);
	}

	/* ── Responsive ── */
	@media (max-width: 640px) {
		.page-title {
			font-size: 1.35rem;
		}

		.dim-grid {
			grid-template-columns: 1fr;
		}

		.severity-header,
		.severity-row {
			grid-template-columns: 1fr 0.7fr;
			font-size: 0.7rem;
		}

		.sev-col-action,
		.sev-action {
			display: none;
		}

		.scan-results-summary {
			flex-wrap: wrap;
			gap: 1rem;
		}

		.finding-meta {
			flex-direction: column;
			gap: 0.5rem;
		}
	}
</style>
