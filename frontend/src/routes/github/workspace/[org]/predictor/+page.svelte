<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isDarkMode } from '$lib/stores.js';
	import { pipelinePredictionApi } from '$lib/api/pipelinePrediction';
	import PipelineRiskPanel from '$lib/components/PipelineRiskPanel.svelte';
	import GitHubCacheNotification from '$lib/components/GitHubCacheNotification.svelte';

	const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

	let orgName = $state('');
	let loading = $state(true);
	let error = $state(null);
	let workspaceData = $state(null);
	let darkMode = $state(false);
	let predictions = $state({}); // Map of repo_name -> { workflow_path -> prediction }

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
		await loadWorkspaceData();
	});

	async function loadWorkspaceData() {
		try {
			loading = true;
			error = null;

			const token = localStorage.getItem('auth0_token') || localStorage.getItem('auth_token');
			if (!token) {
				goto('/login');
				return;
			}

			const response = await fetch(`${API_BASE_URL}/api/github/workspace/${orgName}`, {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				throw new Error('Failed to load workspace data');
			}

			workspaceData = await response.json();

			// Start pre-fetching predictions
			fetchPredictions();
		} catch (err) {
			console.error('Failed to load workspace:', err);
			error = err.message;
		} finally {
			loading = false;
		}
	}

	async function fetchPredictions() {
		if (!workspaceData?.repositories) return;

		for (const repo of workspaceData.repositories) {
			if (repo.workflows && repo.workflows.length > 0) {
				for (const workflow of repo.workflows) {
					if (workflow.state === 'active') {
						getPrediction(repo.name, workflow.path);
					}
				}
			}
		}
	}

	async function getPrediction(repoName, workflowPath) {
		try {
			const result = await pipelinePredictionApi.predict({
				org_name: orgName,
				repo_name: repoName,
				branch: 'main',
				commit_message: `Predictor check for ${workflowPath}`
			});
			if (!predictions[repoName]) predictions[repoName] = {};
			predictions[repoName][workflowPath] = result;
			predictions = { ...predictions };
		} catch (err) {
			console.error(`Failed to get prediction for ${repoName}/${workflowPath}:`, err);
		}
	}

	function getOverallRiskScore() {
		let totalScore = 0;
		let count = 0;
		Object.values(predictions).forEach(repoPreds => {
			Object.values(repoPreds).forEach(pred => {
				if (pred && typeof pred.overall_risk_score === 'number') {
					totalScore += pred.overall_risk_score;
					count++;
				}
			});
		});
		return count > 0 ? Math.round(totalScore / count) : 0;
	}

	const globalRiskScore = $derived(getOverallRiskScore());
	const activeWorkflowCount = $derived(
		workspaceData?.repositories?.reduce(
			(sum, r) => sum + (r.workflows?.filter((w) => w.state === 'active').length || 0),
			0
		) || 0
	);
</script>

<svelte:head>
	<title>Pipeline Predictor - {orgName} - WithOps</title>
</svelte:head>

<GitHubCacheNotification organization={orgName} />

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
				<button
					onclick={toggleTheme}
					class="theme-toggle"
					title="Toggle theme"
					aria-label="Toggle dark mode"
				>
					{#if darkMode}
						<svg class="theme-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<circle cx="12" cy="12" r="5" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
						</svg>
					{:else}
						<svg class="theme-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
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
		<span class="bc-node active">Pipeline Predictor</span>
		<div class="system-status">
			<div class="status-pulse"></div>
			ML CORE: {#if globalRiskScore > 70}ACTIVE_MONITORING{:else if globalRiskScore > 40}STABLE{:else}IDLE{/if}
		</div>
	</div>

	<div class="page-content">
		<main class="page-main">
			<!-- View Header -->
			<div class="view-header">
				<div class="title-group">
					<h1>Pipeline Intelligence</h1>
					<p>Machine learning powered failure risk assessment for all organization CI/CD workflows.</p>
				</div>
				<div class="header-cta">
					<div class="score-pill">
						<span class="score-lbl">GLOBAL RISK</span>
						<div class="score-container">
							<span class="score-num">{globalRiskScore}</span>
							<span class="score-unit">/100</span>
						</div>
					</div>
					<a href="/github/workspace/{orgName}/predictor/accuracy" class="btn btn-secondary">
						VIEW ACCURACY
						<span class="button-arrow">→</span>
					</a>
				</div>
			</div>

			<!-- Quick Stats -->
			<div class="stats-grid">
				<div class="stat-card">
					<div class="feature-number">ACTIVE PIPELINES</div>
					<div class="stat-val">{activeWorkflowCount}</div>
					<div class="stat-detail">Monitoring organization-wide</div>
				</div>
				<div class="stat-card">
					<div class="feature-number">HIGH RISK DETECTED</div>
					<div class="stat-val" style="color: var(--error)">
						{Object.values(predictions).reduce((sum, repoPreds) => sum + Object.values(repoPreds).filter(p => p.overall_risk_score > 70).length, 0)}
					</div>
					<div class="stat-detail">Requires immediate attention</div>
				</div>
				<div class="stat-card">
					<div class="feature-number">AVG FAILURE RATE</div>
					<div class="stat-val">24.5%</div>
					<div class="stat-detail">Historical trend (30d)</div>
				</div>
				<div class="stat-card">
					<div class="feature-number">PREDICTION ACCURACY</div>
					<div class="stat-val">92.4%</div>
					<div class="stat-detail">Model confidence level</div>
				</div>
			</div>

			{#if loading}
				<div class="center-state">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="loader-text">SCANNING WORKFLOW ARCHITECTURES...</div>
				</div>
			{:else if error}
				<div class="state-card">
					<div class="state-icon">⚠️</div>
					<h3 class="state-title">Analysis Failed</h3>
					<p class="state-message">{error}</p>
					<button onclick={loadWorkspaceData} class="btn btn-primary">RETRY SCAN</button>
				</div>
			{:else}
				<div class="prediction-view">
					{#each workspaceData?.repositories || [] as repo}
						{#if repo.workflows && repo.workflows.length > 0}
							<div class="repo-section">
								<div class="repo-header-row">
									<div class="repo-meta">
										<div class="repo-icon-box">
											<svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
											</svg>
										</div>
										<h3>{repo.name}</h3>
										<span class="repo-badge">{repo.default_branch}</span>
									</div>
									<a href={repo.html_url} target="_blank" class="github-tool-link">
										VIEW SOURCE
										<svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
											<path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
										</svg>
									</a>
								</div>

								<div class="workflows-list">
									{#each repo.workflows as workflow}
										{#if workflow.state === 'active'}
											<div class="intel-card workflow-card">
												<div class="workflow-header">
													<div class="workflow-info">
														<span class="workflow-node">/</span>
														<span class="workflow-path">{workflow.path.split('/').pop()}</span>
														<span class="full-path">{workflow.path}</span>
													</div>
													<div class="workflow-actions">
														<button class="btn-micro">ANALYSIS HISTORY</button>
													</div>
												</div>

												{#if predictions[repo.name] && predictions[repo.name][workflow.path]}
													<div class="prediction-view">
														<PipelineRiskPanel
															prediction={predictions[repo.name][workflow.path]}
															repoName={repo.name}
															workflowPath={workflow.path}
														/>
													</div>
												{:else}
													<div class="prediction-skeleton">
														<div class="shimmer-row"></div>
														<div class="shimmer-block"></div>
													</div>
												{/if}
											</div>
										{/if}
									{/each}
								</div>
							</div>
						{/if}
					{:else}
						<div class="state-card">
							<div class="state-icon">📂</div>
							<h3 class="state-title">No Workflows Detected</h3>
							<p class="state-message">No GitHub Actions workflows were found in this organization's active repositories.</p>
							<div class="empty-actions">
								<a href="/github/workspace/{orgName}/repo-treeview" class="btn btn-primary">SCAN REPOSITORIES</a>
								<button onclick={loadWorkspaceData} class="btn btn-secondary">REFRESH</button>
							</div>
						</div>
					{/each}
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

	.nav-link:hover, .nav-link.active {
		color: var(--text-primary);
	}

	.nav-actions {
		display: flex;
		align-items: center;
		gap: 1rem;
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

	/* Technical Breadcrumb Bar */
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

	.bc-node:hover, .bc-node.active {
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
		0%, 100% { opacity: 1; }
		50% { opacity: 0.3; }
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

	.header-cta {
		display: flex;
		align-items: center;
		gap: 1rem;
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

	.score-pill {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		padding: 0.5rem 1.25rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		box-shadow: var(--card-shadow);
	}

	.score-lbl {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	.score-container {
		display: flex;
		align-items: baseline;
		gap: 0.25rem;
	}

	.score-num {
		font-family: var(--font-mono);
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--accent);
		line-height: 1;
	}

	.score-unit {
		font-size: 0.75rem;
		color: var(--text-muted);
		font-weight: 500;
	}

	/* Stats Grid */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
		margin-bottom: 3rem;
	}

	.stat-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.25rem;
		box-shadow: var(--card-shadow);
		transition: all 0.2s var(--ease-premium);
	}

	.stat-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-2px);
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
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	/* Repo Section */
	.repo-section {
		margin-bottom: 4rem;
	}

	.repo-header-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--border);
		margin-bottom: 1.5rem;
	}

	.repo-meta {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.repo-icon-box {
		width: 32px;
		height: 32px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--accent);
	}

	.repo-meta h3 {
		font-size: 1.25rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}

	.repo-badge {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		color: var(--text-muted);
	}

	.github-tool-link {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.7rem;
		font-weight: 700;
		color: var(--text-muted);
		text-decoration: none;
		padding: 0.4rem 0.75rem;
		border-radius: 6px;
		border: 1px solid var(--border);
		transition: all 0.15s;
		font-family: var(--font-mono);
	}

	.github-tool-link:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		border-color: var(--border-focus);
	}

	/* Workflow Cards */
	.workflows-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
		gap: 1.5rem;
	}

	.intel-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		box-shadow: var(--card-shadow);
		transition: all 0.2s var(--ease-premium);
	}

	.intel-card:hover {
		border-color: var(--border-focus);
	}

	.workflow-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	.workflow-info {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.workflow-node {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		color: var(--accent);
		opacity: 0.5;
	}

	.workflow-path {
		font-weight: 700;
		font-size: 0.95rem;
		color: var(--text-primary);
	}

	.full-path {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
	}

	.btn-micro {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		background: transparent;
		border: 1px solid var(--border);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.15s;
	}

	.btn-micro:hover {
		color: var(--text-primary);
		border-color: var(--border-focus);
		background: var(--bg-surface-alt);
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
		0%, 100% { opacity: 0.5; transform: scale(0.95); }
		50% { opacity: 1; transform: scale(1); }
	}

	.loader-text {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--accent);
		letter-spacing: 0.2em;
		text-transform: uppercase;
	}

	.state-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 4rem 2rem;
		text-align: center;
		max-width: 500px;
		margin: 4rem auto;
		box-shadow: var(--card-shadow);
	}

	.state-icon {
		font-size: 2.5rem;
		margin-bottom: 1.5rem;
		opacity: 0.5;
	}

	.state-title {
		font-size: 1.25rem;
		font-weight: 700;
		margin-bottom: 1rem;
	}

	.state-message {
		color: var(--text-secondary);
		font-size: 0.9rem;
		margin-bottom: 2rem;
		line-height: 1.5;
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
		text-decoration: none;
	}

	.btn-primary {
		background: var(--accent);
		color: #000;
	}

	.btn-primary:hover {
		transform: translateY(-1px);
		box-shadow: 0 4px 12px var(--accent-soft);
	}

	.btn-secondary {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		border: 1px solid var(--border);
	}

	.btn-secondary:hover {
		background: var(--border);
	}

	.button-arrow {
		transition: transform 0.2s var(--ease-premium);
	}

	.btn:hover .button-arrow {
		transform: translateX(3px);
	}

	/* Skeletons */
	.prediction-skeleton {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.shimmer-row {
		height: 20px;
		width: 60%;
		background: var(--bg-surface-alt);
		border-radius: 4px;
		animation: shimmer 1.5s infinite linear;
	}

	.shimmer-block {
		height: 80px;
		width: 100%;
		background: var(--bg-surface-alt);
		border-radius: 8px;
		animation: shimmer 1.5s infinite linear;
	}

	@keyframes shimmer {
		0% { opacity: 0.5; }
		50% { opacity: 0.8; }
		100% { opacity: 0.5; }
	}
</style>