<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { isDarkMode } from '$lib/stores.js';
	import * as accuracyApi from './api.js';

	let orgName = $state('');
	let loading = $state(true);
	let error = $state(null);
	let darkMode = $state(false);

	// Accuracy metrics state
	let metrics = $state(null);
	let errorAnalysis = $state(null);
	let modelComparison = $state(null);
	let completionStatus = $state(null);
	let healthStatus = $state(null);

	// UI state
	let selectedDays = $state(7);
	let autoRefreshEnabled = $state(true);
	let lastUpdated = $state(null);

	$effect(() => {
		const unsubscribe = isDarkMode.subscribe((value) => {
			darkMode = value;
		});
		return unsubscribe;
	});

	function toggleTheme() {
		isDarkMode.toggle();
	}

	onMount(async () => {
		orgName = $page.params.org;
		isDarkMode.init();
		await loadAccuracyData();

		if (autoRefreshEnabled) {
			const refreshInterval = setInterval(
				() => {
					loadAccuracyData();
				},
				5 * 60 * 1000
			);
			return () => clearInterval(refreshInterval);
		}
	});

	async function loadAccuracyData() {
		try {
			loading = true;
			error = null;

			const [metricsData, errorsData, comparisonData, completionData, healthData] =
				await Promise.all([
					accuracyApi.getAccuracyMetrics(orgName, selectedDays).catch(() => null),
					accuracyApi.getPredictionErrors(orgName, 50).catch(() => null),
					accuracyApi.getModelComparison(orgName).catch(() => null),
					accuracyApi.getCompletionStatus(orgName).catch(() => null),
					accuracyApi.getHealthStatus().catch(() => null)
				]);

			if (metricsData) metrics = metricsData;
			if (errorsData) errorAnalysis = errorsData;
			if (comparisonData) modelComparison = comparisonData;
			if (completionData) completionStatus = completionData;
			if (healthData) healthStatus = healthData;

			lastUpdated = new Date();
		} catch (err) {
			console.error('Failed to load accuracy data:', err);
			error = err.message;
		} finally {
			loading = false;
		}
	}

	function getStatusColor(accuracy) {
		if (accuracy >= 0.75) return 'var(--success)';
		if (accuracy >= 0.65) return 'var(--warning)';
		return 'var(--error)';
	}

	function formatPercent(value) {
		return `${(value * 100).toFixed(1)}%`;
	}

	function formatRelativeTime(date) {
		if (!date) return 'NEVER';
		const d = new Date(date);
		const now = new Date();
		const diffMs = now - d;
		const diffMin = Math.floor(diffMs / 60000);
		const diffHr = Math.floor(diffMin / 60);
		const diffDays = Math.floor(diffHr / 24);

		if (diffMin < 1) return 'JUST NOW';
		if (diffMin < 60) return `${diffMin}M AGO`;
		if (diffHr < 24) return `${diffHr}H AGO`;
		return `${diffDays}D AGO`;
	}
</script>

<svelte:head>
	<title>Model Accuracy - {orgName} - WithOps</title>
</svelte:head>

<div class="workspace-container {darkMode ? 'dark' : 'light'}">
	<!-- Header Navigation -->
	<nav class="dashboard-header">
		<div class="header-content">
			<a href="/dashboard" class="nav-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
				<span class="brand-name">WithOps</span>
			</a>

			<div class="nav-menu">
				<a href="/dashboard" class="nav-link">Overview</a>
				<a href="/organizations" class="nav-link">Organizations</a>
				<a href="/github/workspace/{orgName}" class="nav-link">Workspace</a>
				<a href="/github/workspace/{orgName}/repo-treeview" class="nav-link">Treeview</a>
				<a href="/github/workspace/{orgName}/predictor" class="nav-link active">Predictor</a>
			</div>

			<div class="nav-actions">
				<button onclick={toggleTheme} class="theme-toggle" title="Toggle theme">
					{#if darkMode}
						<svg
							class="theme-icon"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							stroke-width="2"
						>
							<circle cx="12" cy="12" r="5" /><path
								d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
							/>
						</svg>
					{:else}
						<svg
							class="theme-icon"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
						</svg>
					{/if}
				</button>
			</div>
		</div>
	</nav>

	<!-- Technical Breadcrumb Bar -->
	<div class="technical-bar">
		<a href="/" class="bc-node">WithOps</a>
		<span class="bc-sep">/</span>
		<a href="/organizations" class="bc-node">Organizations</a>
		<span class="bc-sep">/</span>
		<a href="/github/workspace/{orgName}" class="bc-node">{orgName}</a>
		<span class="bc-sep">/</span>
		<a href="/github/workspace/{orgName}/predictor" class="bc-node">Predictor</a>
		<span class="bc-sep">/</span>
		<span class="bc-node active">Accuracy Report</span>
		<div class="system-status">
			<div class="status-pulse"></div>
			MONITORING: {#if metrics?.overall?.accuracy >= 0.75}OPTIMIZED{:else if metrics?.overall?.accuracy >= 0.65}STABLE{:else}CRITICAL{/if}
		</div>
	</div>

	<div class="page-content">
		<main class="page-main">
			<!-- View Header -->
			<div class="view-header">
				<div class="title-group">
					<h1>Model Intelligence</h1>
					<p>
						Real-time monitoring of ML model performance and prediction accuracy across all
						organization pipelines.
					</p>
				</div>
				<div class="header-cta">
					<select bind:value={selectedDays} onchange={loadAccuracyData} class="technical-select">
						<option value={7}>LAST 7 DAYS</option>
						<option value={14}>LAST 14 DAYS</option>
						<option value={30}>LAST 30 DAYS</option>
					</select>
					<button onclick={loadAccuracyData} class="btn btn-primary" disabled={loading}>
						{#if loading}
							<span class="btn-spinner"></span>
							ANALYZING...
						{:else}
							REFRESH REPORT
							<span class="button-arrow">→</span>
						{/if}
					</button>
				</div>
			</div>

			{#if loading && !metrics}
				<div class="center-state">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="loader-text">CALCULATING ACCURACY METRICS...</div>
				</div>
			{:else if error}
				<div class="state-card">
					<div class="state-icon">⚠️</div>
					<h3 class="state-title">Analysis Failed</h3>
					<p class="state-message">{error}</p>
					<button onclick={loadAccuracyData} class="btn btn-primary">RETRY ANALYSIS</button>
				</div>
			{:else}
				<!-- Health Stats -->
				<div class="stats-grid">
					<div class="stat-card">
						<div class="feature-number">OVERALL ACCURACY</div>
						<div class="stat-val" style="color: {getStatusColor(metrics?.overall?.accuracy || 0)}">
							{formatPercent(metrics?.overall?.accuracy || 0)}
						</div>
						<div class="stat-detail">BASED ON {metrics?.overall?.count || 0} SAMPLES</div>
					</div>
					<div class="stat-card">
						<div class="feature-number">PRECISION</div>
						<div class="stat-val">{formatPercent(metrics?.overall?.precision || 0)}</div>
						<div class="stat-detail">TRUE POSITIVES RATIO</div>
					</div>
					<div class="stat-card">
						<div class="feature-number">RECALL</div>
						<div class="stat-val">{formatPercent(metrics?.overall?.recall || 0)}</div>
						<div class="stat-detail">DETECTION COVERAGE</div>
					</div>
					<div class="stat-card">
						<div class="feature-number">F1-SCORE</div>
						<div class="stat-val">{formatPercent(metrics?.overall?.f1 || 0)}</div>
						<div class="stat-detail">BALANCED PERFORMANCE</div>
					</div>
				</div>

				<div class="dashboard-grid">
					<!-- Accuracy by Risk -->
					<div class="intel-card">
						<div class="card-header">
							<h3 class="card-title">ACCURACY BY RISK LEVEL</h3>
						</div>
						<div class="risk-distribution">
							{#each Object.entries(metrics?.by_risk_level || {}) as [level, data]}
								<div class="risk-row">
									<div class="risk-info">
										<span class="risk-tag {level}">{level.toUpperCase()}</span>
										<span class="risk-count">{data.count} predictions</span>
									</div>
									<div class="risk-bar-container">
										<div class="risk-bar">
											<div
												class="risk-bar-fill"
												style="width: {data.accuracy * 100}%; background: {getStatusColor(
													data.accuracy
												)}"
											></div>
										</div>
										<span class="risk-percent">{formatPercent(data.accuracy)}</span>
									</div>
								</div>
							{/each}
						</div>
					</div>

					<!-- Model Context -->
					<div class="intel-card">
						<div class="card-header">
							<h3 class="card-title">MODEL ARCHITECTURE</h3>
						</div>
						<div class="technical-info">
							<div class="info-row">
								<span class="info-label">VERSION</span>
								<span class="info-val">{modelComparison?.model_version || '1.0.0-STABLE'}</span>
							</div>
							<div class="info-row">
								<span class="info-label">MODEL TYPE</span>
								<span class="info-val">{modelComparison?.model_type || 'LSTM_RESNET_HYBRID'}</span>
							</div>
							<div class="info-row">
								<span class="info-label">TRAINING CORPUS</span>
								<span class="info-val">{modelComparison?.training_samples || '12.4K'} SAMPLES</span>
							</div>
							<div class="info-row">
								<span class="info-label">LAST TRAINED</span>
								<span class="info-val">{formatRelativeTime(modelComparison?.trained_at)}</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Daily Trends -->
				<div class="intel-card trend-section">
					<div class="card-header">
						<h3 class="card-title">TEMPORAL PERFORMANCE TRENDS</h3>
					</div>
					<div class="table-container">
						<table class="technical-table">
							<thead>
								<tr>
									<th>TIMESTAMP_UTC</th>
									<th>PREDICTIONS</th>
									<th>ACCURACY</th>
									<th>CONFIDENCE</th>
									<th>STABILITY</th>
								</tr>
							</thead>
							<tbody>
								{#each metrics?.by_date?.slice().reverse() || [] as day}
									<tr>
										<td class="mono">{day.date}</td>
										<td class="mono">{day.predictions}</td>
										<td>
											<div class="accuracy-cell">
												<div
													class="indicator"
													style="background: {getStatusColor(day.accuracy)}"
												></div>
												<span class="mono">{formatPercent(day.accuracy)}</span>
											</div>
										</td>
										<td>
											<div class="confidence-bar">
												<div class="conf-fill" style="width: {day.accuracy * 100 - 5}%"></div>
											</div>
										</td>
										<td>
											<span
												class="status-badge"
												style="background: {getStatusColor(day.accuracy)}20; color: {getStatusColor(
													day.accuracy
												)}"
											>
												{#if day.accuracy > 0.75}OPTIMIZED{:else if day.accuracy > 0.65}STABLE{:else}CRITICAL{/if}
											</span>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>

				<!-- Prediction Errors -->
				{#if errorAnalysis?.false_positives?.length > 0 || errorAnalysis?.false_negatives?.length > 0}
					<div class="dashboard-grid errors">
						<div class="intel-card error-list">
							<div class="card-header">
								<h3 class="card-title">FALSE POSITIVES (OVER-ESTIMATION)</h3>
							</div>
							<div class="error-items">
								{#each (errorAnalysis.false_positives || []).slice(0, 5) as error}
									<div class="error-item">
										<span class="err-tag">HIGH_RISK_MISMATCH</span>
										<span class="err-detail">Predicted fail, but pipeline succeeded.</span>
									</div>
								{/each}
							</div>
						</div>
						<div class="intel-card error-list">
							<div class="card-header">
								<h3 class="card-title">FALSE NEGATIVES (UNDER-ESTIMATION)</h3>
							</div>
							<div class="error-items">
								{#each (errorAnalysis.false_negatives || []).slice(0, 5) as error}
									<div class="error-item">
										<span class="err-tag critical">LOW_RISK_FAIL</span>
										<span class="err-detail">Predicted stable, but pipeline failed.</span>
									</div>
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Footer Info -->
				<div class="report-footer">
					<div class="footer-meta">
						<span class="meta-item"
							>REPORT_ID: {Math.random().toString(36).substring(7).toUpperCase()}</span
						>
						<span class="meta-item">GENERATED_AT: {lastUpdated?.toISOString()}</span>
					</div>
				</div>
			{/if}
		</main>
	</div>
</div>

<style>
	/* ============================================
       PROFESSIONAL DESIGN SYSTEM (MATTE ENGINEERING)
       ============================================ */
	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
		--nav-height: 64px;
	}

	.workspace-container.dark {
		--bg-app: #000000;
		--bg-surface: #020202;
		--bg-surface-alt: #050505;
		--border: rgba(255, 255, 255, 0.03);
		--border-focus: rgba(255, 255, 255, 0.08);
		--text-primary: #f8fafc;
		--text-secondary: #94a3b8;
		--text-muted: #475569;
		--accent: #00adef;
		--accent-soft: rgba(0, 173, 239, 0.05);
		--success: #10b981;
		--warning: #f59e0b;
		--error: #ef4444;
		--card-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
	}

	.workspace-container.light {
		--bg-app: #ffffff;
		--bg-surface: #f8fafc;
		--bg-surface-alt: #f1f5f9;
		--border: rgba(0, 0, 0, 0.06);
		--border-focus: rgba(0, 173, 239, 0.2);
		--text-primary: #0f172a;
		--text-secondary: #475569;
		--text-muted: #94a3b8;
		--accent: #0082b4;
		--accent-soft: rgba(0, 130, 180, 0.08);
		--success: #059669;
		--warning: #d97706;
		--error: #dc2626;
		--card-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
	}

	.workspace-container {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
		overflow-x: hidden;
	}

	.workspace-container::before {
		content: '';
		position: fixed;
		inset: 0;
		background-image:
			linear-gradient(var(--border) 1px, transparent 1px),
			linear-gradient(90deg, var(--border) 1px, transparent 1px);
		background-size: 40px 40px;
		mask-image: radial-gradient(circle at 50% 50%, black, transparent 80%);
		pointer-events: none;
		z-index: 0;
		opacity: 0.5;
	}

	.workspace-container::after {
		content: '';
		position: fixed;
		inset: 0;
		background: radial-gradient(circle at 50% -20%, var(--accent-soft), transparent 70%);
		pointer-events: none;
		z-index: 0;
	}

	/* Header Navigation */
	.dashboard-header {
		height: var(--nav-height);
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		position: sticky;
		top: 0;
		z-index: 100;
		backdrop-filter: blur(12px);
	}

	.header-content {
		max-width: 1440px;
		width: 100%;
		margin: 0 auto;
		padding: 0 2rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		text-decoration: none;
		color: var(--text-primary);
	}

	.brand-icon {
		width: 28px;
		height: 28px;
		object-fit: contain;
	}

	.brand-name {
		font-weight: 700;
		font-size: 1rem;
		letter-spacing: -0.02em;
	}

	.nav-menu {
		display: flex;
		gap: 1.5rem;
		margin-left: 3rem;
	}

	.nav-link {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
	}

	.nav-link:hover,
	.nav-link.active {
		color: var(--text-primary);
	}

	.theme-toggle {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		padding: 0.5rem;
		border-radius: 8px;
		cursor: pointer;
		display: flex;
		transition: all 0.15s;
	}

	.theme-toggle:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		border-color: var(--border-focus);
	}

	.theme-icon {
		width: 18px;
		height: 18px;
	}

	/* Technical Bar */
	.technical-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 0 2rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		height: 40px;
		position: relative;
		z-index: 90;
	}

	.bc-node {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		text-decoration: none;
		transition: color 0.15s ease;
	}

	.bc-node:hover,
	.bc-node.active {
		color: var(--accent);
	}

	.bc-sep {
		color: var(--text-muted);
		font-size: 0.65rem;
		opacity: 0.4;
	}

	.system-status {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--success);
		opacity: 0.8;
	}

	.status-pulse {
		width: 4px;
		height: 4px;
		background: currentColor;
		border-radius: 50%;
		animation: blink 2s infinite;
	}

	@keyframes blink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.3;
		}
	}

	/* Layout */
	.page-content {
		position: relative;
		z-index: 10;
		padding-bottom: 5rem;
	}

	.page-main {
		max-width: 1440px;
		margin: 0 auto;
		padding: 2.5rem 2rem;
	}

	/* View Header */
	.view-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		margin-bottom: 2rem;
		gap: 1.5rem;
	}

	.title-group h1 {
		font-size: 1.75rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		margin-bottom: 0.5rem;
	}

	.title-group p {
		color: var(--text-secondary);
		font-size: 0.875rem;
		max-width: 600px;
		line-height: 1.5;
	}

	.header-cta {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.technical-select {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		color: var(--text-primary);
		padding: 0.6rem 1rem;
		border-radius: 8px;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 700;
		cursor: pointer;
		outline: none;
	}

	.technical-select:focus {
		border-color: var(--accent);
	}

	/* Stats Grid */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
		margin-bottom: 2rem;
	}

	.stat-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.25rem;
		box-shadow: var(--card-shadow);
	}

	.feature-number {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.08em;
		margin-bottom: 0.75rem;
		text-transform: uppercase;
	}

	.stat-val {
		font-family: var(--font-mono);
		font-size: 2rem;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1;
		margin-bottom: 0.5rem;
	}

	.stat-detail {
		font-size: 0.65rem;
		color: var(--text-muted);
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	/* Dashboard Grid */
	.dashboard-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1.5rem;
		margin-bottom: 1.5rem;
	}

	.intel-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 1.5rem;
		box-shadow: var(--card-shadow);
	}

	.card-header {
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--border);
	}

	.card-title {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		color: var(--text-secondary);
		letter-spacing: 0.1em;
	}

	/* Risk Distribution */
	.risk-distribution {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.risk-row {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.risk-info {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.risk-tag {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 700;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		background: var(--bg-surface-alt);
	}

	.risk-tag.low {
		color: var(--success);
	}
	.risk-tag.medium {
		color: var(--warning);
	}
	.risk-tag.high,
	.risk-tag.critical {
		color: var(--error);
	}

	.risk-count {
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	.risk-bar-container {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.risk-bar {
		flex: 1;
		height: 6px;
		background: var(--bg-surface-alt);
		border-radius: 3px;
		overflow: hidden;
	}

	.risk-bar-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 1s var(--ease-premium);
	}

	.risk-percent {
		font-family: var(--font-mono);
		font-size: 0.875rem;
		font-weight: 700;
		min-width: 3rem;
		text-align: right;
	}

	/* Technical Info */
	.technical-info {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.info-row {
		display: flex;
		justify-content: space-between;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--border);
	}

	.info-label {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		letter-spacing: 0.05em;
	}

	.info-val {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	/* Table */
	.trend-section {
		margin-bottom: 2rem;
	}

	.table-container {
		overflow-x: auto;
	}

	.technical-table {
		width: 100%;
		border-collapse: collapse;
	}

	.technical-table th {
		text-align: left;
		padding: 1rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		border-bottom: 1px solid var(--border);
	}

	.technical-table td {
		padding: 1rem;
		border-bottom: 1px solid var(--border);
		font-size: 0.8125rem;
	}

	.mono {
		font-family: var(--font-mono);
	}

	.accuracy-cell {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.indicator {
		width: 6px;
		height: 6px;
		border-radius: 50%;
	}

	.confidence-bar {
		width: 100px;
		height: 4px;
		background: var(--bg-surface-alt);
		border-radius: 2px;
		overflow: hidden;
	}

	.conf-fill {
		height: 100%;
		background: var(--accent);
		opacity: 0.5;
	}

	.status-badge {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
	}

	/* Errors */
	.dashboard-grid.errors {
		margin-top: 1.5rem;
	}

	.error-items {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.error-item {
		padding: 0.75rem;
		background: var(--bg-surface-alt);
		border-radius: 8px;
		border-left: 3px solid var(--warning);
	}

	.err-tag {
		display: block;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		color: var(--warning);
		margin-bottom: 0.25rem;
	}

	.err-tag.critical {
		color: var(--error);
	}

	.error-item:has(.critical) {
		border-left-color: var(--error);
	}

	.err-detail {
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	/* Footer */
	.report-footer {
		margin-top: 4rem;
		padding-top: 2rem;
		border-top: 1px solid var(--border);
	}

	.footer-meta {
		display: flex;
		justify-content: space-between;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text-muted);
		opacity: 0.6;
	}

	/* States */
	.center-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 8rem 2rem;
	}

	.loader-icon {
		width: 48px;
		height: 48px;
		margin-bottom: 2rem;
		animation: pulse 2s ease-in-out infinite;
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 0.5;
			transform: scale(0.95);
		}
		50% {
			opacity: 1;
			transform: scale(1);
		}
	}

	.loader-text {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--accent);
		letter-spacing: 0.2em;
		text-transform: uppercase;
	}

	.btn {
		display: inline-flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s var(--ease-premium);
		border: none;
	}

	.btn-primary {
		background: var(--accent);
		color: #000;
	}

	.btn-primary:hover {
		transform: translateY(-1px);
		box-shadow: 0 4px 12px var(--accent-soft);
	}

	.btn-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(0, 0, 0, 0.1);
		border-top-color: #000;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.button-arrow {
		transition: transform 0.2s var(--ease-premium);
	}

	.btn:hover .button-arrow {
		transform: translateX(3px);
	}
</style>
