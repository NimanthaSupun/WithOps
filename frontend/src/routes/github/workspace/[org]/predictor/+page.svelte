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
	let sidebarCollapsed = $state(false);
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

	function toggleSidebar() {
		sidebarCollapsed = !sidebarCollapsed;
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

			// Start pre-fetching predictions for all repos with workflows
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
					// We only predict for active workflows
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

	function formatRelativeTime(dateString) {
		const date = new Date(dateString);
		const now = new Date();
		const diffMs = now - date;
		const diffSec = Math.floor(diffMs / 1000);
		const diffMin = Math.floor(diffSec / 60);
		const diffHr = Math.floor(diffMin / 60);
		const diffDays = Math.floor(diffHr / 24);

		if (diffSec < 60) return 'just now';
		if (diffMin < 60) return `${diffMin}m ago`;
		if (diffHr < 24) return `${diffHr}h ago`;
		return `${diffDays}d ago`;
	}
</script>

<svelte:head>
	<title>Pipeline Predictor - {orgName} - WithOps</title>
</svelte:head>

<GitHubCacheNotification organization={orgName} />

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
				<button
					onclick={toggleTheme}
					class="theme-toggle"
					title="Toggle theme"
					aria-label="Toggle dark mode"
				>
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
			<span class="breadcrumb-item active">Pipeline Predictor</span>
		</div>
		<div class="header-tools">
			<div class="system-status">
				<div class="status-pulse"></div>
				ML CORE: OPTIMIZED
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
				aria-label="Toggle sidebar"
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
				<a
					href="/github/workspace/{orgName}/repo-treeview"
					class="sidebar-link"
					title="Repo Treeview"
					aria-label="Repo Treeview"
				>
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path
							d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2"
						/>
					</svg>
					{#if !sidebarCollapsed}<span>Repo Tree</span>{/if}
				</a>
				<a
					href="/github/workspace/{orgName}/threat-modeling"
					class="sidebar-link"
					title="Threat Modeling"
					aria-label="Threat Modeling"
				>
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path
							d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
						/>
					</svg>
					{#if !sidebarCollapsed}<span>Threats</span>{/if}
				</a>
				<a
					href="/github/workspace/{orgName}/audit"
					class="sidebar-link"
					title="Actions Audit"
					aria-label="Actions Audit"
				>
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path
							d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 002 2h2a2 2 0 012 2"
						/>
					</svg>
					{#if !sidebarCollapsed}<span>Audit</span>{/if}
				</a>
				<a
					href="/github/workspace/{orgName}/canvas"
					class="sidebar-link"
					title="Canvas"
					aria-label="Canvas"
				>
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path
							d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
						/>
					</svg>
					{#if !sidebarCollapsed}<span>Canvas</span>{/if}
				</a>
				<a
					href="/github/workspace/{orgName}/treeview"
					class="sidebar-link"
					title="Treeview"
					aria-label="Treeview"
				>
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
					</svg>
					{#if !sidebarCollapsed}<span>Treeview</span>{/if}
				</a>
				<a
					href="/github/workspace/{orgName}/predictor"
					class="sidebar-link active"
					title="Pipeline Predictor"
					aria-label="Pipeline Predictor"
				>
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
					{#if !sidebarCollapsed}
						<span>Predictor</span>
					{/if}
				</a>
			</nav>
		</aside>

		<main class="workspace-main {sidebarCollapsed ? 'expanded' : ''}">
			<div class="view-header">
				<div class="header-main">
					<h1>Pipeline Intelligence</h1>
					<p>
						Machine learning powered failure risk assessment for all organization CI/CD workflows.
					</p>
				</div>
				<div class="header-actions">
					<a
						href="/github/workspace/{orgName}/predictor/accuracy"
						class="btn btn-secondary"
						title="View model accuracy"
					>
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
							/>
						</svg>
						Model Accuracy
					</a>
					<button
						onclick={loadWorkspaceData}
						class="btn btn-secondary"
						title="Refresh predictions"
						aria-label="Refresh predictions"
					>
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
							/>
						</svg>
					</button>
				</div>
			</div>

			{#if !loading && workspaceData}
				<div class="stats-panel">
					<div class="stat-cell">
						<svg
							width="16"
							height="16"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3.382a1 1 0 00-.894.553l-.448.894a1 1 0 01-.894.553H9a1 1 0 01-.894-.553l-.448-.894A1 1 0 006.764 7H3z"
							/>
						</svg>
						<div class="stat-info">
							<span class="stat-val">{workspaceData?.repositories?.length || 0}</span>
							<span class="stat-lbl">Repositories</span>
						</div>
					</div>
					<div class="stat-cell">
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
						<div class="stat-info">
							<span class="stat-val"
								>{workspaceData?.repositories?.reduce(
									(sum, r) => sum + (r.workflows?.filter((w) => w.state === 'active').length || 0),
									0
								) || 0}</span
							>
							<span class="stat-lbl">Active Workflows</span>
						</div>
					</div>
					<div class="stat-cell">
						<svg
							width="16"
							height="16"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.431 3.666 3.666 0 00.023.285 3.42 3.42 0 01-3.161 3.431 3.42 3.42 0 00-.563.09 3.502 3.502 0 01-2.664 1.27 3.502 3.502 0 01-2.664-1.27 3.42 3.42 0 00-.563-.09 3.42 3.42 0 01-3.161-3.431 3.666 3.666 0 00.023-.285 3.42 3.42 0 013.138-3.431z"
							/>
						</svg>
						<div class="stat-info">
							<span class="stat-val">MONITORING</span>
							<span class="stat-lbl">Model Status</span>
						</div>
					</div>
				</div>
			{/if}

			{#if loading}
				<div class="center-state">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="loader-text">ANALYZING PIPELINES...</div>
				</div>
			{:else if error}
				<div class="center-state">
					<svg
						class="error-icon"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="1.5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M12 9v3.75m-9.303 3.376c.866-1.616 2.545-2.571 4.432-2.571c.9 0 1.747.356 2.466.748m15.602 0a9 9 0 00-15.602-3.376m0 0c.57.852.922 1.84.922 2.871c0 .89-.287 1.716-.786 2.4"
						/>
					</svg>
					<h3>Failed to load predictions</h3>
					<p class="error-text">{error}</p>
					<div class="empty-actions">
						<button onclick={loadWorkspaceData} class="btn btn-primary">Retry</button>
					</div>
				</div>
			{:else if workspaceData?.repositories?.length === 0}
				<div class="center-state">
					<svg
						class="empty-icon"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="1.5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2 2z"
						/>
					</svg>
					<h3>No repositories found</h3>
					<p class="empty-desc">
						Add repositories to your organization to enable pipeline intelligence.
					</p>
				</div>
			{:else}
				<div class="predictor-grid">
					{#each workspaceData?.repositories || [] as repo}
						{#if repo.workflows && repo.workflows.length > 0}
							<section class="repo-section">
								<div class="repo-header-row">
									<div class="repo-meta">
										<svg class="repo-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3.382a1 1 0 00-.894.553l-.448.894a1 1 0 01-.894.553H9a1 1 0 01-.894-.553l-.448-.894A1 1 0 006.764 7H3z"
											/>
										</svg>
										<h3>{repo.name}</h3>
										<span class="repo-badge">{repo.private ? 'Private' : 'Public'}</span>
									</div>
									<div class="repo-tools">
										<a
											href={repo.html_url}
											target="_blank"
											class="github-link"
											aria-label="View on GitHub"
										>
											<svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
												<path
													d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"
												/>
											</svg>
										</a>
									</div>
								</div>

								<div class="workflows-container">
									{#each repo.workflows as workflow}
										{#if workflow.state === 'active'}
											<div class="workflow-card">
												<div class="workflow-header-row">
													<div class="workflow-info">
														<span class="workflow-node">/</span>
														<span class="workflow-path">{workflow.path.split('/').pop()}</span>
														<span class="full-path" title={workflow.path}>{workflow.path}</span>
													</div>
													<div class="workflow-actions">
														<button class="btn-action">History</button>
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
													<div class="prediction-loading">
														<div class="shimmer-line"></div>
														<div class="shimmer-panel"></div>
													</div>
												{/if}
											</div>
										{/if}
									{/each}
								</div>
							</section>
							<!-- Section Separation -->
							<div class="section-divider"></div>
						{/if}
					{/each}
				</div>
			{/if}
		</main>
	</div>
</div>

<style>
	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
		--nav-height: 64px;
		--sidebar-width: 200px;
		--sidebar-collapsed: 52px;
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
	}

	.workspace-container {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
	}

	/* Header styles shared with main dashboard */
	.dashboard-header {
		height: var(--nav-height);
		background: var(--bg-surface);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		position: sticky;
		top: 0;
		z-index: 100;
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
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
	}
	.nav-link:hover {
		color: var(--text-primary);
	}
	.theme-toggle {
		background: none;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 8px;
		display: flex;
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
		height: 40px;
		position: relative;
		z-index: 90;
	}
	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.breadcrumb a {
		color: var(--text-muted);
		text-decoration: none;
	}
	.breadcrumb-sep {
		color: var(--border-focus);
	}
	.breadcrumb-item.active {
		color: var(--accent);
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

	/* Sidebar */
	.layout-with-sidebar {
		display: flex;
		flex: 1;
		min-height: calc(100vh - 104px);
	}
	.workspace-sidebar {
		width: var(--sidebar-width);
		background: var(--bg-surface);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		padding: 0.75rem 0.5rem;
		gap: 0.25rem;
		transition: width 0.2s var(--ease-premium);
		position: sticky;
		top: 104px;
		height: calc(100vh - 104px);
	}
	.workspace-sidebar.collapsed {
		width: var(--sidebar-collapsed);
	}
	.sidebar-toggle-btn {
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 6px;
		display: flex;
		justify-content: center;
	}
	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}
	.sidebar-link {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.625rem 0.75rem;
		border-radius: 6px;
		color: var(--text-secondary);
		text-decoration: none;
		font-size: 0.8125rem;
		font-weight: 500;
		transition: all 0.1s;
	}
	.sidebar-link:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
	}
	.sidebar-link.active {
		background: var(--accent-soft);
		color: var(--accent);
	}

	/* Main Page Content */
	.workspace-main {
		flex: 1;
		padding: 2rem;
		max-width: 1440px;
		margin: 0 auto;
		width: 100%;
	}

	.view-header {
		margin-bottom: 2.5rem;
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
	}
	.view-header h1 {
		font-size: 1.75rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		margin-bottom: 0.5rem;
	}
	.view-header p {
		color: var(--text-secondary);
		font-size: 0.9375rem;
	}

	.predictor-grid {
		display: flex;
		flex-direction: column;
		gap: 3rem;
	}

	.repo-section {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.repo-header-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--border);
	}

	.repo-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.repo-icon {
		width: 20px;
		height: 20px;
		color: var(--text-muted);
	}
	.repo-meta h3 {
		font-size: 1.125rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.repo-badge {
		font-size: 0.65rem;
		font-family: var(--font-mono);
		padding: 0.125rem 0.5rem;
		border-radius: 4px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		color: var(--text-secondary);
	}

	.workflows-container {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
		gap: 1.5rem;
	}

	.workflow-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 1.25rem;
		transition: all 0.2s var(--ease-premium);
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.workflow-card:hover {
		border-color: var(--border-focus);
	}

	.workflow-header-row {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
	}
	.workflow-info {
		display: flex;
		flex-direction: column;
	}
	.workflow-node {
		color: var(--accent);
		font-family: var(--font-mono);
		font-weight: bold;
	}
	.workflow-path {
		font-weight: 600;
		font-size: 0.9375rem;
	}
	.full-path {
		font-size: 0.7rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
		margin-top: 0.1rem;
	}

	.btn-action {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		color: var(--text-secondary);
		font-size: 0.7rem;
		font-family: var(--font-mono);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		cursor: pointer;
	}

	.prediction-loading {
		padding: 1rem 0;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.shimmer-line {
		height: 12px;
		width: 60%;
		background: linear-gradient(
			90deg,
			var(--bg-surface-alt) 25%,
			var(--border) 50%,
			var(--bg-surface-alt) 75%
		);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
		border-radius: 4px;
	}
	.shimmer-panel {
		height: 160px;
		width: 100%;
		background: linear-gradient(
			90deg,
			var(--bg-surface-alt) 25%,
			var(--border) 100%,
			var(--bg-surface-alt) 75%
		);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
		border-radius: 8px;
	}
	@keyframes shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}

	.section-divider {
		height: 1px;
		background: radial-gradient(circle, var(--border) 0%, transparent 70%);
		margin-top: 1rem;
	}

	.header-actions {
		display: flex;
		gap: 0.75rem;
		align-items: center;
	}
	.header-actions a,
	.header-actions button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.stats-panel {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
		gap: 1rem;
		margin-bottom: 2rem;
		padding: 1.5rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
	}
	.stat-cell {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.75rem;
	}
	.stat-cell svg {
		width: 24px;
		height: 24px;
		color: var(--accent);
		flex-shrink: 0;
	}
	.stat-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}
	.stat-val {
		font-weight: 600;
		font-size: 1.25rem;
		color: var(--text-primary);
	}
	.stat-lbl {
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
	}

	.center-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 6rem 2rem;
		gap: 1.5rem;
		text-align: center;
	}

	.loader-icon {
		width: 64px;
		height: 64px;
		opacity: 0.8;
		animation: pulse 2s ease-in-out infinite;
	}
	@keyframes pulse {
		0%,
		100% {
			opacity: 0.8;
		}
		50% {
			opacity: 0.5;
		}
	}

	.loader-text {
		font-weight: 500;
		letter-spacing: 0.05em;
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	.center-state svg {
		width: 64px;
		height: 64px;
		color: var(--text-secondary);
		opacity: 0.6;
	}

	.center-state h3 {
		margin: 0;
		font-size: 1.25rem;
		color: var(--text-primary);
	}

	.error-text,
	.empty-desc {
		margin: 0;
		font-size: 0.95rem;
		color: var(--text-secondary);
		max-width: 400px;
	}

	.empty-actions {
		display: flex;
		gap: 0.75rem;
		flex-wrap: wrap;
		justify-content: center;
	}

	@media (max-width: 1024px) {
		.workflows-container {
			grid-template-columns: 1fr;
		}
		.stats-panel {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 640px) {
		.header-actions {
			flex-direction: column;
			width: 100%;
		}
		.header-actions a,
		.header-actions button {
			width: 100%;
		}
		.stats-panel {
			grid-template-columns: 1fr;
		}
		.center-state {
			padding: 4rem 1rem;
		}
	}
</style>
