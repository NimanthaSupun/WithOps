<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { isDarkMode } from '$lib/stores.js';
	import * as accuracyApi from './api.js';

	let orgName = $state('');
	let loading = $state(true);
	let error = $state(null);
	let darkMode = $state(false);
	let sidebarCollapsed = $state(false);

	// Accuracy metrics state
	let metrics = $state(null);
	let errorAnalysis = $state(null);
	let modelComparison = $state(null);
	let completionStatus = $state(null);
	let healthStatus = $state(null);

	// UI state
	let selectedRepo = $state(null);
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

	function toggleSidebar() {
		sidebarCollapsed = !sidebarCollapsed;
	}

	onMount(async () => {
		orgName = $page.params.org;
		isDarkMode.init();
		await loadAccuracyData();

		// Set up auto-refresh every 5 minutes
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

			// Fetch all metrics in parallel using API module
			const [metricsData, errorsData, comparisonData, completionData, healthData] =
				await Promise.all([
					accuracyApi.getAccuracyMetrics(orgName, selectedDays).catch((err) => {
						console.error('Failed to load metrics:', err);
						return null;
					}),
					accuracyApi.getPredictionErrors(orgName, 50).catch((err) => {
						console.error('Failed to load errors:', err);
						return null;
					}),
					accuracyApi.getModelComparison(orgName).catch((err) => {
						console.error('Failed to load model comparison:', err);
						return null;
					}),
					accuracyApi.getCompletionStatus(orgName).catch((err) => {
						console.error('Failed to load completion status:', err);
						return null;
					}),
					accuracyApi.getHealthStatus().catch((err) => {
						console.error('Failed to load health status:', err);
						return null;
					})
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
		if (accuracy >= 0.75) return '#10b981';
		if (accuracy >= 0.65) return '#f59e0b';
		return '#ef4444';
	}

	function getStatusLabel(accuracy) {
		if (accuracy >= 0.75) return 'HEALTHY';
		if (accuracy >= 0.65) return 'WARNING';
		return 'CRITICAL';
	}

	function formatPercent(value) {
		return `${(value * 100).toFixed(1)}%`;
	}

	function formatTime(date) {
		if (!date) return 'Never';
		const d = new Date(date);
		const now = new Date();
		const diffMs = now - d;
		const diffMin = Math.floor(diffMs / 60000);
		const diffHr = Math.floor(diffMin / 60);
		const diffDays = Math.floor(diffHr / 24);

		if (diffMin < 1) return 'just now';
		if (diffMin < 60) return `${diffMin}m ago`;
		if (diffHr < 24) return `${diffHr}h ago`;
		return `${diffDays}d ago`;
	}
</script>

<svelte:head>
	<title>Model Accuracy - {orgName} - WithOps</title>
</svelte:head>

<div class="workspace-container {darkMode ? 'dark' : 'light'}">
	<!-- Header Navigation -->
	<nav class="dashboard-header">
		<div class="header-content">
			<a href="/" class="nav-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
				<span class="brand-name">WithOps</span>
			</a>

			<div class="nav-menu">
				<a href="/dashboard" class="nav-link">Overview</a>
				<a href="/organizations" class="nav-link">Organizations</a>
				<a href="/github/workspace/{orgName}" class="nav-link">Workspace</a>
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
		<div class="breadcrumb">
			<span class="breadcrumb-item">WithOps</span>
			<span class="breadcrumb-sep">/</span>
			<a href="/organizations" class="breadcrumb-item">Organizations</a>
			<span class="breadcrumb-sep">/</span>
			<a href="/github/workspace/{orgName}" class="breadcrumb-item">{orgName}</a>
			<span class="breadcrumb-sep">/</span>
			<a href="/github/workspace/{orgName}/predictor" class="breadcrumb-item">Pipeline Predictor</a>
			<span class="breadcrumb-sep">/</span>
			<span class="breadcrumb-item active">Model Accuracy</span>
		</div>
		<div class="header-tools">
			<div class="system-status">
				<div class="status-pulse"></div>
				ACCURACY MONITORING: {#if metrics?.overall?.accuracy >= 0.75}OPTIMIZED{:else if metrics?.overall?.accuracy >= 0.65}MONITORING{:else}CRITICAL{/if}
			</div>
		</div>
	</div>

	<!-- Sidebar Navigation -->
	<div class="layout-with-sidebar">
		<aside class="workspace-sidebar {sidebarCollapsed ? 'collapsed' : ''}">
			<button
				onclick={toggleSidebar}
				class="sidebar-toggle-btn"
				title="Toggle sidebar"
				aria-label="Toggle sidebar navigation"
			>
				<svg
					width="16"
					height="16"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					stroke-width="2"
				>
					<path d="M4 6h16M4 12h16M4 18h16" />
				</svg>
			</button>
			<nav class="sidebar-nav">
				<a href="/github/workspace/{orgName}/predictor" class="sidebar-link">
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path d="M13 10V3L4 14h7v7l9-11h-7z" />
					</svg>
					{#if !sidebarCollapsed}<span>Predictions</span>{/if}
				</a>
				<a href="/github/workspace/{orgName}/predictor/accuracy" class="sidebar-link active">
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path
							d="M13 10h8M13 14h8M13 18h8M2 14h.01M2 10h.01M2 18h.01M7 14a5 5 0 1110 0 5 5 0 01-10 0z"
						/>
					</svg>
					{#if !sidebarCollapsed}<span>Accuracy</span>{/if}
				</a>
			</nav>
		</aside>

		<main class="workspace-main {sidebarCollapsed ? 'expanded' : ''}">
			<!-- Page Header -->
			<div class="view-header">
				<div class="header-main">
					<h1>Model Accuracy Dashboard</h1>
					<p>
						Real-time monitoring of ML model performance and prediction accuracy across all
						pipelines.
					</p>
				</div>
				<div class="header-actions">
					<select bind:value={selectedDays} onchange={loadAccuracyData} class="days-selector">
						<option value={7}>Last 7 Days</option>
						<option value={14}>Last 14 Days</option>
						<option value={30}>Last 30 Days</option>
					</select>
					<button onclick={loadAccuracyData} class="refresh-btn" disabled={loading}>
						<svg
							width="16"
							height="16"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path d="M1 4v6h6M23 20v-6h-6" />
							<path d="M20.49 9A9 9 0 05.64 5.64M3.51 15A9 9 0 0018.36 18.36" />
						</svg>
						{#if loading}Refreshing...{:else}Refresh{/if}
					</button>
				</div>
			</div>

			{#if error}
				<div class="error-state">
					<p>⚠️ {error}</p>
					<button onclick={loadAccuracyData}>Try Again</button>
				</div>
			{:else if loading}
				<div class="loading-state">
					<div class="spinner"></div>
					<p>Loading accuracy metrics...</p>
				</div>
			{:else}
				<!-- Health Status Panel -->
				<div class="health-panel">
					<div class="panel-grid">
						<!-- Overall Accuracy -->
						<div class="metric-card primary">
							<div class="metric-icon">📊</div>
							<div class="metric-content">
								<span class="metric-label">Overall Accuracy</span>
								<span class="metric-value">{formatPercent(metrics?.overall?.accuracy || 0)}</span>
								<span
									class="metric-status"
									style="color: {getStatusColor(metrics?.overall?.accuracy || 0)}"
								>
									{getStatusLabel(metrics?.overall?.accuracy || 0)}
								</span>
							</div>
						</div>

						<!-- Precision -->
						<div class="metric-card">
							<div class="metric-icon">🎯</div>
							<div class="metric-content">
								<span class="metric-label">Precision</span>
								<span class="metric-value">{formatPercent(metrics?.overall?.precision || 0)}</span>
								<span class="metric-note">True positives / Total positives</span>
							</div>
						</div>

						<!-- Recall -->
						<div class="metric-card">
							<div class="metric-icon">🔍</div>
							<div class="metric-content">
								<span class="metric-label">Recall</span>
								<span class="metric-value">{formatPercent(metrics?.overall?.recall || 0)}</span>
								<span class="metric-note">Failures detected / Actual failures</span>
							</div>
						</div>

						<!-- F1 Score -->
						<div class="metric-card">
							<div class="metric-icon">⚡</div>
							<div class="metric-content">
								<span class="metric-label">F1-Score</span>
								<span class="metric-value">{formatPercent(metrics?.overall?.f1 || 0)}</span>
								<span class="metric-note">Precision/Recall balance</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Accuracy by Risk Level Section -->
				{#if metrics?.by_risk_level}
					<div class="section">
						<h2>Accuracy by Risk Level</h2>
						<div class="risk-level-grid">
							{#each Object.entries(metrics.by_risk_level) as [level, data]}
								<div class="risk-card {level}">
									<div class="risk-header">
										<span class="risk-label">{level.toUpperCase()}</span>
										<span class="risk-count">{data.count || 0} predictions</span>
									</div>
									<div class="risk-accuracy">{formatPercent(data.accuracy || 0)}</div>
									<div class="risk-bar">
										<div class="risk-bar-fill" style="width: {(data.accuracy || 0) * 100}%;"></div>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Daily Trends Section -->
				{#if metrics?.by_date && metrics.by_date.length > 0}
					<div class="section">
						<h2>Daily Accuracy Trends</h2>
						<div class="trends-table">
							<table>
								<thead>
									<tr>
										<th>Date</th>
										<th>Predictions</th>
										<th>Accuracy</th>
										<th>Trend</th>
									</tr>
								</thead>
								<tbody>
									{#each metrics.by_date.slice().reverse() as day}
										<tr>
											<td>{new Date(day.date).toLocaleDateString()}</td>
											<td>{day.predictions || 0}</td>
											<td>
												<span
													class="accuracy-badge"
													style="background-color: {getStatusColor(day.accuracy)}"
												>
													{formatPercent(day.accuracy || 0)}
												</span>
											</td>
											<td>
												{#if day.accuracy > 0.75}
													<span class="trend trend-up">↑ Good</span>
												{:else if day.accuracy > 0.65}
													<span class="trend trend-neutral">→ Fair</span>
												{:else}
													<span class="trend trend-down">↓ Low</span>
												{/if}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}

				<!-- Model Information -->
				{#if modelComparison}
					<div class="section">
						<h2>Model Information</h2>
						<div class="model-info-grid">
							<div class="info-card">
								<span class="info-label">Model Version</span>
								<span class="info-value">{modelComparison.model_version || 'N/A'}</span>
							</div>
							<div class="info-card">
								<span class="info-label">Model Type</span>
								<span class="info-value">{modelComparison.model_type || 'N/A'}</span>
							</div>
							<div class="info-card">
								<span class="info-label">Training Samples</span>
								<span class="info-value">{modelComparison.training_samples || 'N/A'}</span>
							</div>
							<div class="info-card">
								<span class="info-label">Last Updated</span>
								<span class="info-value"
									>{modelComparison.trained_at
										? formatTime(new Date(modelComparison.trained_at))
										: 'N/A'}</span
								>
							</div>
						</div>
					</div>
				{/if}

				<!-- Completion Status -->
				{#if completionStatus}
					<div class="section">
						<h2>Outcome Completion Status</h2>
						<div class="completion-grid">
							<div class="completion-card">
								<span class="completion-label">Pending Outcomes</span>
								<span class="completion-value">{completionStatus.pending_count || 0}</span>
								<span class="completion-detail">Awaiting pipeline completion</span>
							</div>
							<div class="completion-card">
								<span class="completion-label">Completion Rate</span>
								<span class="completion-value"
									>{formatPercent(completionStatus.completion_rate || 0)}</span
								>
								<span class="completion-detail">Outcomes received / Total predictions</span>
							</div>
							<div class="completion-card">
								<span class="completion-label">Avg Time to Outcome</span>
								<span class="completion-value"
									>{(completionStatus.avg_time_to_outcome_hours || 0).toFixed(1)}h</span
								>
								<span class="completion-detail">Average hours from prediction to outcome</span>
							</div>
							<div class="completion-card">
								<span class="completion-label">Oldest Pending</span>
								<span class="completion-value"
									>{completionStatus.oldest_pending
										? formatTime(new Date(completionStatus.oldest_pending))
										: 'N/A'}</span
								>
								<span class="completion-detail">Time since oldest unresolved</span>
							</div>
						</div>
					</div>
				{/if}

				<!-- Error Analysis -->
				{#if errorAnalysis?.false_positives?.length > 0 || errorAnalysis?.false_negatives?.length > 0}
					<div class="section">
						<h2>Prediction Errors</h2>
						<div class="error-analysis-grid">
							<!-- False Positives -->
							<div class="error-section">
								<h3>False Positives</h3>
								<p class="error-count">{errorAnalysis.false_positives?.length || 0} predictions</p>
								<div class="error-list">
									{#each (errorAnalysis.false_positives || []).slice(0, 5) as error}
										<div class="error-item">
											<span class="error-tag">Predicted High Risk</span>
											<span class="error-detail">but pipeline succeeded</span>
										</div>
									{/each}
								</div>
							</div>

							<!-- False Negatives -->
							<div class="error-section">
								<h3>False Negatives</h3>
								<p class="error-count">{errorAnalysis.false_negatives?.length || 0} predictions</p>
								<div class="error-list">
									{#each (errorAnalysis.false_negatives || []).slice(0, 5) as error}
										<div class="error-item">
											<span class="error-tag">Predicted Low Risk</span>
											<span class="error-detail">but pipeline failed</span>
										</div>
									{/each}
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Last Updated -->
				<div class="footer-info">
					<p>Last updated: {lastUpdated ? formatTime(lastUpdated) : 'Never'}</p>
				</div>
			{/if}
		</main>
	</div>
</div>

<style>
	.workspace-container {
		display: flex;
		flex-direction: column;
		height: 100vh;
		background: #f9fafb;
		color: #1f2937;
	}

	.workspace-container.dark {
		background: #0f172a;
		color: #e5e7eb;
	}

	.dashboard-header {
		background: white;
		border-bottom: 1px solid #e5e7eb;
		padding: 0.75rem 0;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.dark .dashboard-header {
		background: #1e293b;
		border-bottom: 1px solid #334155;
	}

	.header-content {
		max-width: 1600px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.5rem;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		text-decoration: none;
		font-weight: 600;
		font-size: 1.125rem;
		color: #1f2937;
	}

	.dark .nav-brand {
		color: #f1f5f9;
	}

	.brand-icon {
		width: 1.5rem;
		height: 1.5rem;
	}

	.nav-menu {
		display: flex;
		gap: 1rem;
		flex: 1;
		margin-left: 2rem;
	}

	.nav-link {
		color: #6b7280;
		text-decoration: none;
		font-size: 0.875rem;
		padding: 0.5rem 0;
		border-bottom: 2px solid transparent;
		transition: all 0.2s;
	}

	.dark .nav-link {
		color: #cbd5e1;
	}

	.nav-link:hover {
		color: #1f2937;
		border-bottom-color: #3b82f6;
	}

	.dark .nav-link:hover {
		color: #f1f5f9;
	}

	.nav-actions {
		display: flex;
		gap: 1rem;
		align-items: center;
	}

	.theme-toggle {
		background: none;
		border: none;
		cursor: pointer;
		color: #6b7280;
		padding: 0.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.dark .theme-toggle {
		color: #cbd5e1;
	}

	.theme-icon {
		width: 1.25rem;
		height: 1.25rem;
	}

	.technical-bar {
		background: #f3f4f6;
		border-bottom: 1px solid #e5e7eb;
		padding: 0.75rem 1.5rem;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.dark .technical-bar {
		background: #0f172a;
		border-bottom: 1px solid #334155;
	}

	.breadcrumb {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		font-size: 0.875rem;
		color: #6b7280;
	}

	.dark .breadcrumb {
		color: #cbd5e1;
	}

	.breadcrumb-item {
		color: #6b7280;
		text-decoration: none;
		cursor: pointer;
		transition: color 0.2s;
	}

	.dark .breadcrumb-item {
		color: #cbd5e1;
	}

	.breadcrumb-item:hover {
		color: #1f2937;
	}

	.dark .breadcrumb-item:hover {
		color: #f1f5f9;
	}

	.breadcrumb-item.active {
		color: #1f2937;
		font-weight: 500;
	}

	.dark .breadcrumb-item.active {
		color: #f1f5f9;
	}

	.breadcrumb-sep {
		color: #d1d5db;
	}

	.system-status {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: #10b981;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.status-pulse {
		width: 0.5rem;
		height: 0.5rem;
		background: #10b981;
		border-radius: 50%;
		animation: pulse 2s infinite;
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}

	.layout-with-sidebar {
		display: flex;
		flex: 1;
		overflow: hidden;
	}

	.workspace-sidebar {
		width: 250px;
		background: white;
		border-right: 1px solid #e5e7eb;
		overflow-y: auto;
		transition: width 0.3s ease;
		padding: 1rem 0;
	}

	.dark .workspace-sidebar {
		background: #1e293b;
		border-right: 1px solid #334155;
	}

	.workspace-sidebar.collapsed {
		width: 60px;
		padding: 1rem 0;
	}

	.sidebar-toggle-btn {
		display: none;
		background: none;
		border: none;
		cursor: pointer;
		color: #6b7280;
		padding: 0.5rem 0.75rem;
		margin: 0 0.75rem 1rem 0.75rem;
	}

	@media (max-width: 768px) {
		.sidebar-toggle-btn {
			display: flex;
		}
	}

	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 0 0.5rem;
	}

	.sidebar-link {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		color: #6b7280;
		text-decoration: none;
		border-radius: 0.375rem;
		transition: all 0.2s;
		font-size: 0.875rem;
	}

	.dark .sidebar-link {
		color: #cbd5e1;
	}

	.sidebar-link:hover {
		background: #f3f4f6;
		color: #1f2937;
	}

	.dark .sidebar-link:hover {
		background: #334155;
		color: #f1f5f9;
	}

	.sidebar-link.active {
		background: #dbeafe;
		color: #3b82f6;
		font-weight: 500;
	}

	.dark .sidebar-link.active {
		background: #1e3a8a;
		color: #60a5fa;
	}

	.workspace-sidebar.collapsed .sidebar-link span {
		display: none;
	}

	.workspace-main {
		flex: 1;
		overflow-y: auto;
		padding: 2rem;
		max-width: 1400px;
		margin: 0 auto;
		width: 100%;
	}

	.workspace-main.expanded {
		max-width: 100%;
	}

	.view-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 2rem;
		margin-bottom: 2rem;
	}

	.header-main h1 {
		font-size: 2rem;
		font-weight: 700;
		margin: 0;
		color: #1f2937;
	}

	.dark .header-main h1 {
		color: #f1f5f9;
	}

	.header-main p {
		color: #6b7280;
		margin: 0.5rem 0 0 0;
		font-size: 0.875rem;
	}

	.dark .header-main p {
		color: #cbd5e1;
	}

	.header-actions {
		display: flex;
		gap: 1rem;
		align-items: center;
	}

	.days-selector {
		padding: 0.5rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		background: white;
		color: #1f2937;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.dark .days-selector {
		background: #1e293b;
		color: #f1f5f9;
		border-color: #334155;
	}

	.refresh-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		cursor: pointer;
		font-size: 0.875rem;
		transition: background 0.2s;
	}

	.refresh-btn:hover {
		background: #2563eb;
	}

	.refresh-btn:disabled {
		background: #9ca3af;
		cursor: not-allowed;
	}

	.error-state {
		background: #fee2e2;
		border: 1px solid #fecaca;
		border-radius: 0.375rem;
		padding: 1.5rem;
		text-align: center;
	}

	.dark .error-state {
		background: #7f1d1d;
		border-color: #991b1b;
	}

	.error-state p {
		color: #dc2626;
		margin: 0;
	}

	.dark .error-state p {
		color: #fca5a5;
	}

	.error-state button {
		margin-top: 1rem;
		padding: 0.5rem 1rem;
		background: #dc2626;
		color: white;
		border: none;
		border-radius: 0.375rem;
		cursor: pointer;
	}

	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 3rem;
	}

	.spinner {
		width: 2rem;
		height: 2rem;
		border: 3px solid #e5e7eb;
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	.dark .spinner {
		border-color: #334155;
		border-top-color: #60a5fa;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-state p {
		color: #6b7280;
	}

	.dark .loading-state p {
		color: #cbd5e1;
	}

	/* Health Panel */
	.health-panel {
		margin-bottom: 2rem;
	}

	.panel-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		gap: 1.5rem;
	}

	.metric-card {
		background: white;
		border-radius: 0.5rem;
		padding: 1.5rem;
		border: 1px solid #e5e7eb;
		display: flex;
		align-items: center;
		gap: 1rem;
		transition:
			transform 0.2s,
			box-shadow 0.2s;
	}

	.dark .metric-card {
		background: #1e293b;
		border-color: #334155;
	}

	.metric-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.dark .metric-card:hover {
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	.metric-card.primary {
		border: 2px solid #3b82f6;
		background: #eff6ff;
	}

	.dark .metric-card.primary {
		background: #0c2340;
		border-color: #60a5fa;
	}

	.metric-icon {
		font-size: 2rem;
		min-width: 3rem;
		text-align: center;
	}

	.metric-content {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.metric-label {
		font-size: 0.875rem;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: 500;
	}

	.dark .metric-label {
		color: #cbd5e1;
	}

	.metric-value {
		font-size: 1.75rem;
		font-weight: 700;
		color: #1f2937;
		margin: 0.5rem 0;
	}

	.dark .metric-value {
		color: #f1f5f9;
	}

	.metric-status {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.metric-note {
		font-size: 0.75rem;
		color: #9ca3af;
	}

	.dark .metric-note {
		color: #64748b;
	}

	/* Sections */
	.section {
		background: white;
		border-radius: 0.5rem;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
		border: 1px solid #e5e7eb;
	}

	.dark .section {
		background: #1e293b;
		border-color: #334155;
	}

	.section h2 {
		margin: 0 0 1.5rem 0;
		font-size: 1.125rem;
		color: #1f2937;
	}

	.dark .section h2 {
		color: #f1f5f9;
	}

	/* Risk Level Grid */
	.risk-level-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
	}

	.risk-card {
		padding: 1.5rem;
		border-radius: 0.375rem;
		border-left: 4px solid;
	}

	.risk-card.low {
		background: #f0fdf4;
		border-left-color: #10b981;
	}

	.dark .risk-card.low {
		background: #0c2818;
		border-left-color: #6ee7b7;
	}

	.risk-card.medium {
		background: #fffbeb;
		border-left-color: #f59e0b;
	}

	.dark .risk-card.medium {
		background: #22190c;
		border-left-color: #fbbf24;
	}

	.risk-card.high {
		background: #fef2f2;
		border-left-color: #ef4444;
	}

	.dark .risk-card.high {
		background: #221415;
		border-left-color: #f87171;
	}

	.risk-card.critical {
		background: #fef2f2;
		border-left-color: #dc2626;
	}

	.dark .risk-card.critical {
		background: #1f0f0f;
		border-left-color: #dc2626;
	}

	.risk-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.75rem;
	}

	.risk-label {
		font-weight: 600;
		font-size: 0.875rem;
		text-transform: uppercase;
		color: #1f2937;
	}

	.dark .risk-label {
		color: #f1f5f9;
	}

	.risk-count {
		font-size: 0.75rem;
		color: #6b7280;
	}

	.dark .risk-count {
		color: #cbd5e1;
	}

	.risk-accuracy {
		font-size: 1.5rem;
		font-weight: 700;
		margin-bottom: 0.75rem;
		color: #1f2937;
	}

	.dark .risk-accuracy {
		color: #f1f5f9;
	}

	.risk-bar {
		height: 0.375rem;
		background: #e5e7eb;
		border-radius: 9999px;
		overflow: hidden;
	}

	.dark .risk-bar {
		background: #334155;
	}

	.risk-bar-fill {
		height: 100%;
		background: currentColor;
		border-radius: 9999px;
	}

	/* Trends Table */
	.trends-table {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
	}

	thead {
		background: #f9fafb;
	}

	.dark thead {
		background: #0f172a;
	}

	th {
		text-align: left;
		padding: 1rem;
		font-size: 0.875rem;
		color: #6b7280;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid #e5e7eb;
	}

	.dark th {
		color: #cbd5e1;
		border-bottom-color: #334155;
	}

	td {
		padding: 1rem;
		border-bottom: 1px solid #e5e7eb;
		font-size: 0.875rem;
		color: #1f2937;
	}

	.dark td {
		color: #e5e7eb;
		border-bottom-color: #334155;
	}

	.accuracy-badge {
		padding: 0.25rem 0.75rem;
		border-radius: 9999px;
		color: white;
		font-weight: 600;
		font-size: 0.75rem;
	}

	.trend {
		font-size: 0.875rem;
		font-weight: 600;
	}

	.trend-up {
		color: #10b981;
	}

	.trend-neutral {
		color: #f59e0b;
	}

	.trend-down {
		color: #ef4444;
	}

	/* Model Info */
	.model-info-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
	}

	.info-card {
		background: #f9fafb;
		border-radius: 0.375rem;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.dark .info-card {
		background: #0f172a;
	}

	.info-label {
		font-size: 0.75rem;
		text-transform: uppercase;
		color: #6b7280;
		font-weight: 600;
		letter-spacing: 0.05em;
	}

	.dark .info-label {
		color: #cbd5e1;
	}

	.info-value {
		font-size: 1rem;
		font-weight: 600;
		color: #1f2937;
	}

	.dark .info-value {
		color: #f1f5f9;
	}

	/* Completion Status */
	.completion-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
	}

	.completion-card {
		background: #f9fafb;
		border-radius: 0.375rem;
		padding: 1rem;
		border-left: 3px solid #3b82f6;
	}

	.dark .completion-card {
		background: #0f172a;
		border-left-color: #60a5fa;
	}

	.completion-label {
		display: block;
		font-size: 0.75rem;
		text-transform: uppercase;
		color: #6b7280;
		font-weight: 600;
		margin-bottom: 0.5rem;
	}

	.dark .completion-label {
		color: #cbd5e1;
	}

	.completion-value {
		display: block;
		font-size: 1.5rem;
		font-weight: 700;
		color: #1f2937;
		margin-bottom: 0.5rem;
	}

	.dark .completion-value {
		color: #f1f5f9;
	}

	.completion-detail {
		display: block;
		font-size: 0.75rem;
		color: #9ca3af;
	}

	.dark .completion-detail {
		color: #64748b;
	}

	/* Error Analysis */
	.error-analysis-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		gap: 1.5rem;
	}

	.error-section h3 {
		margin: 0 0 0.75rem 0;
		font-size: 1rem;
		color: #1f2937;
	}

	.dark .error-section h3 {
		color: #f1f5f9;
	}

	.error-count {
		margin: 0 0 1rem 0;
		font-size: 0.875rem;
		color: #6b7280;
	}

	.dark .error-count {
		color: #cbd5e1;
	}

	.error-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.error-item {
		background: #f9fafb;
		border-radius: 0.375rem;
		padding: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		font-size: 0.875rem;
	}

	.dark .error-item {
		background: #0f172a;
	}

	.error-tag {
		font-weight: 600;
		color: #ef4444;
	}

	.error-detail {
		color: #6b7280;
		font-size: 0.75rem;
	}

	.dark .error-detail {
		color: #cbd5e1;
	}

	/* Footer */
	.footer-info {
		text-align: center;
		margin-top: 2rem;
		padding-top: 2rem;
		border-top: 1px solid #e5e7eb;
		font-size: 0.875rem;
		color: #9ca3af;
	}

	.dark .footer-info {
		border-top-color: #334155;
		color: #64748b;
	}
</style>
