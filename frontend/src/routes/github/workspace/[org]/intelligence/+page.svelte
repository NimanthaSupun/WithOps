<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isDarkMode } from '$lib/stores';
	import ChatModal from '$lib/components/ChatModal.svelte';

	const org = $page.params.org;
	const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

	// Chat Modal State
	let isChatModalOpen = false;

	function openChatModal() {
		isChatModalOpen = true;
	}

	function closeChatModal() {
		isChatModalOpen = false;
	}

	// Helper function to get auth token (matches github.js logic)
	function getAuthToken() {
		return localStorage.getItem('auth0_token') || localStorage.getItem('auth_token');
	}

	// Debug logging
	console.log('[INIT] Intelligence Page Initialized');
	console.log('[PARAM] Org param:', org);
	console.log('[CONFIG] API Base URL:', API_BASE_URL);
	console.log('[AUTH] Has auth token:', !!getAuthToken());

	let loading = true;
	let error = null;
	let analysisData = null;
	let activeTab = 'overview';
	let isUnifiedAnalysis = false;
	let projectBreakdowns = [];
	let expandedProjects = new Set();

	// Analysis History
	let allAnalyses = [];
	let selectedAnalysisId = null;
	let deletingAnalysisId = null;

	// UI State
	let selectedRepository = null;
	let expandedFindings = new Set();

	// Load existing analyses on page mount
	onMount(async () => {
		await fetchAnalysis();
	});

	// DSOMM Dimensions mapping
	const dsommDimensions = [
		{
			id: 'build_deployment',
			name: 'Build & Deployment',
			description: 'CI/CD pipeline security, automated testing, deployment practices',
			icon: 'BD'
		},
		{
			id: 'implementation',
			name: 'Implementation',
			description: 'Secure coding, dependency management, secret management',
			icon: 'IM'
		},
		{
			id: 'test_verification',
			name: 'Test & Verification',
			description: 'SAST, DAST, SCA, penetration testing',
			icon: 'TV'
		},
		{
			id: 'information_gathering',
			name: 'Information Gathering',
			description: 'Vulnerability management, logging, monitoring',
			icon: 'IG'
		},
		{
			id: 'culture_organization',
			name: 'Culture & Organization',
			description: 'Security champions, training, collaboration',
			icon: 'CO'
		}
	];

	// Level indicators
	const levelConfig = {
		0: { label: 'None', color: '#E5E7EB', emoji: '', bgDark: '#374151' },
		1: { label: 'Basic', color: '#FCD34D', emoji: '', bgDark: '#78350F' },
		2: { label: 'Advanced', color: '#FB923C', emoji: '', bgDark: '#9A3412' },
		3: { label: 'Mature', color: '#86EFAC', emoji: '', bgDark: '#14532D' },
		4: { label: 'Optimized', color: '#22C55E', emoji: '', bgDark: '#052E16' }
	};

	onMount(async () => {
		console.log('[MOUNT] Intelligence page mounted for org:', org);
		await fetchAnalysis();
	});

	async function triggerNewAnalysis() {
		loading = true;
		error = null;

		try {
			const token = getAuthToken();
			if (!token) {
				error = 'Authentication required. Please login to access Workspace Intelligence.';
				loading = false;
				return;
			}

			console.log('[TRIGGER] Triggering new analysis for org:', org);

			// Fetch repository tree data
			const treeResponse = await fetch(`${API_BASE_URL}/api/repository-tree/${org}`, {
				headers: {
					Authorization: `Bearer ${token}`,
					'Content-Type': 'application/json'
				}
			});

			if (!treeResponse.ok) {
				throw new Error(
					'Failed to fetch repository tree. Please ensure you have accessed the repository tree view first.'
				);
			}

			const treeResult = await treeResponse.json();
			console.log('[TREE] Tree result fetched:', treeResult);

			// Extract tree data and ID from response
			const treeData = treeResult.data || [];
			const repositoryTreeId = treeResult.metadata?.id;

			if (!repositoryTreeId) {
				throw new Error(
					'No repository tree ID found. Please access the repository tree view first to create your workspace structure.'
				);
			}

			console.log('[TREE] Tree ID:', repositoryTreeId, 'Tree data items:', treeData.length);

			// Trigger analysis
			const analyzeResponse = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/analyze-workspace`,
				{
					method: 'POST',
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						organization_name: org,
						tree_data: treeData,
						repository_tree_id: repositoryTreeId,
						fetch_github_data: true
					})
				}
			);

			if (!analyzeResponse.ok) {
				const errorData = await analyzeResponse.json();
				throw new Error(errorData.detail || 'Failed to trigger analysis');
			}

			console.log('[OK] Analysis triggered successfully');

			// Wait a moment then fetch results
			await new Promise((resolve) => setTimeout(resolve, 2000));
			await fetchAnalysis();
		} catch (err) {
			console.error('[ERR] Failed to trigger analysis:', err);
			error = err.message;
		} finally {
			loading = false;
		}
	}

	async function fetchAnalysis() {
		loading = true;
		error = null;

		try {
			const token = getAuthToken();
			console.log('[AUTH] Token exists:', !!token);

			if (!token) {
				console.warn('[ERR] No token found');
				error = 'Authentication required. Please login to access Workspace Intelligence.';
				loading = false;
				return;
			}

			console.log('[FETCH] Fetching analysis for org:', org);

			// Get latest analysis for this org
			const response = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/organization/${org}`,
				{
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}
			);

			console.log('[API] Response status:', response.status);

			if (!response.ok) {
				const errorText = await response.text();
				console.error('[ERR] API Error:', response.status, errorText);
				throw new Error(`Failed to fetch analysis: ${response.statusText}`);
			}

			const data = await response.json();
			console.log('[OK] Analysis data received:', data);

			if (data.analyses && data.analyses.length > 0) {
				// Store all analyses for history
				allAnalyses = data.analyses;

				// Get the most recent analysis or selected one
				const latestAnalysis = selectedAnalysisId
					? data.analyses.find((a) => a.id === selectedAnalysisId) || data.analyses[0]
					: data.analyses[0];

				selectedAnalysisId = latestAnalysis.id;

				// Fetch detailed analysis data
				const detailResponse = await fetch(
					`${API_BASE_URL}/api/workspace-intelligence/analysis/${latestAnalysis.id}`,
					{
						headers: {
							Authorization: `Bearer ${token}`,
							'Content-Type': 'application/json'
						}
					}
				);

				if (detailResponse.ok) {
					const detailData = await detailResponse.json();
					console.log('[DETAIL] Analysis response:', detailData);

					// Check if this is a unified analysis
					isUnifiedAnalysis = detailData.analysis?.analysis_scope === 'unified';

					// Properly merge the response structure
					analysisData = {
						...(detailData.analysis || {}),
						repositories: detailData.repositories || [],
						findings: detailData.findings || [],
						maturity_scores: detailData.maturity_scores,
						findings_summary: detailData.findings_summary
					};

					// If unified, extract project breakdowns
					if (isUnifiedAnalysis && detailData.analysis?.analysis_data?.project_analyses) {
						projectBreakdowns = detailData.analysis.analysis_data.project_analyses;
						console.log('[INFO] Found', projectBreakdowns.length, 'project breakdowns');
					}

					console.log('[DATA] Final analysisData:', analysisData);
					console.log('[INFO] Is Unified Analysis:', isUnifiedAnalysis);
					console.log('[INFO] Repositories count:', analysisData.repositories?.length || 0);
					console.log('[INFO] Findings count:', analysisData.findings?.length || 0);
				} else {
					console.warn('[WARN]ï¸ Detail fetch failed, using basic data');
					analysisData = latestAnalysis;
				}
			} else {
				error = 'No analysis found for this organization. Please run an analysis first.';
			}
		} catch (err) {
			console.error('[ERR] Failed to fetch analysis:', err);
			error = err.message;
			// Don't redirect on error, stay on page and show error
		} finally {
			loading = false;
			console.log('[OK] Loading complete. Error:', error);
		}
	}

	function toggleFinding(findingId) {
		if (expandedFindings.has(findingId)) {
			expandedFindings.delete(findingId);
		} else {
			expandedFindings.add(findingId);
		}
		expandedFindings = expandedFindings;
	}

	function getSeverityColor(severity) {
		const colors = {
			critical: { light: '#DC2626', dark: '#EF4444' },
			high: { light: '#EA580C', dark: '#F97316' },
			medium: { light: '#D97706', dark: '#F59E0B' },
			low: { light: '#65A30D', dark: '#84CC16' },
			info: { light: '#0284C7', dark: '#06B6D4' }
		};
		return $isDarkMode ? colors[severity]?.dark : colors[severity]?.light;
	}

	function calculateDimensionLevel(dimension, practices) {
		if (!practices) return 0;

		// Map practices to DSOMM dimensions
		switch (dimension.id) {
			case 'build_deployment':
				return practices.repos_with_workflows > 0
					? practices.uses_centralized_workflows
						? 2
						: 1
					: 0;

			case 'implementation':
				const hasSecrets = practices.secret_scanning_tools?.length > 0;
				const hasSCA = practices.sca_tools?.length > 0;
				if (hasSecrets && hasSCA) return 2;
				if (hasSecrets || hasSCA) return 1;
				return 0;

			case 'test_verification':
				const hasSAST = practices.sast_tools?.length > 0;
				const hasDAST = practices.dast_tools?.length > 0;
				const hasContainer = practices.container_scanning_tools?.length > 0;
				const toolCount = (hasSAST ? 1 : 0) + (hasDAST ? 1 : 0) + (hasContainer ? 1 : 0);
				if (toolCount >= 3) return 3;
				if (toolCount >= 2) return 2;
				if (toolCount >= 1) return 1;
				return 0;

			case 'information_gathering':
				// Based on monitoring and vulnerability tracking
				return practices.branch_protection_enabled ? 1 : 0;

			case 'culture_organization':
				// Based on code review practices
				const hasCodeOwners = practices.has_codeowners;
				const hasReviews = practices.required_reviews > 0;
				if (hasCodeOwners && hasReviews >= 2) return 2;
				if (hasCodeOwners || hasReviews > 0) return 1;
				return 0;

			default:
				return 0;
		}
	}

	function getOverallScore(practices) {
		// For unified analyses, use the overall_maturity_score from the database
		if (isUnifiedAnalysis && analysisData?.overall_maturity_score !== undefined) {
			return Math.round(analysisData.overall_maturity_score);
		}

		if (!practices) return 0;

		const dimensions = dsommDimensions.map((d) => calculateDimensionLevel(d, practices));
		const total = dimensions.reduce((sum, level) => sum + level, 0);
		const max = dimensions.length * 4; // Max level is 4

		return Math.round((total / max) * 100);
	}

	function getRepositoriesWithWorkflows() {
		if (!analysisData?.repositories) return [];
		return analysisData.repositories.filter((r) => r.has_workflows !== false);
	}

	function getRepositoriesWithoutWorkflows() {
		if (!analysisData?.repositories) return [];
		return analysisData.repositories.filter((r) => r.has_workflows === false);
	}

	async function switchToAnalysis(analysisId) {
		selectedAnalysisId = analysisId;
		await fetchAnalysis();
	}

	async function deleteAnalysis(analysisId) {
		if (!confirm('Are you sure you want to delete this analysis? This action cannot be undone.')) {
			return;
		}

		try {
			deletingAnalysisId = analysisId;
			const token = getAuthToken();

			const response = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/analysis/${analysisId}`,
				{
					method: 'DELETE',
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}
			);

			if (!response.ok) {
				throw new Error('Failed to delete analysis');
			}

			console.log('[OK] Analysis deleted successfully');

			// Reload analyses
			selectedAnalysisId = null;
			await fetchAnalysis();
		} catch (err) {
			console.error('[ERR] Failed to delete analysis:', err);
			alert(`Failed to delete analysis: ${err.message}`);
		} finally {
			deletingAnalysisId = null;
		}
	}

	function formatDate(dateString) {
		if (!dateString) return 'N/A';
		const date = new Date(dateString);
		return date.toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function toggleProjectExpansion(projectId) {
		if (expandedProjects.has(projectId)) {
			expandedProjects.delete(projectId);
		} else {
			expandedProjects.add(projectId);
		}
		expandedProjects = expandedProjects;
	}

	function getAnalysisTypeLabel(analysis) {
		if (analysis.analysis_scope === 'unified') return 'Unified';
		if (analysis.analysis_scope === 'folder') return 'Folder';
		if (analysis.analysis_scope === 'project') return 'Project';
		return 'Workspace';
	}
</script>

<svelte:head>
	<title>Workspace Intelligence - {org}</title>
</svelte:head>

{#if loading && !analysisData}
	<div class="loading-screen">
		<div class="loading-content">
			<img src="/icons/excellence_17274210.png" alt="WithOps" class="loading-icon" />
			<div class="progress-bar">
				<div class="progress-fill"></div>
			</div>
			<div class="status-message">SCANNING WORKSPACE INTELLIGENCE...</div>
		</div>
	</div>
{:else}
	<div class="intel-page {$isDarkMode ? 'dark' : 'light'}">
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
					<a href="/github/workspace/{org}" class="nav-link">Workspace</a>
					<a href="/github/workspace/{org}/repo-treeview" class="nav-link">Treeview</a>
					<a href="/github/workspace/{org}/intelligence" class="nav-link active">Intelligence</a>
					<button
						onclick={() => isDarkMode.set(!$isDarkMode)}
						class="theme-toggle"
						title="Toggle theme"
					>
						{#if $isDarkMode}
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
			<a href="/github/workspace/{org}" class="bc-node">{org}</a>
			<span class="bc-sep">/</span>
			<a href="/github/workspace/{org}/repo-treeview" class="bc-node">Treeview</a>
			<span class="bc-sep">/</span>
			<span class="bc-node active">Intelligence</span>
			<div class="system-status">
				<div class="status-pulse"></div>
				DSOMM: ACTIVE
			</div>
		</div>

		<!-- Inline re-analysis loader -->
		{#if loading && analysisData}
			<div class="inline-loader">
				<div class="inline-progress">
					<div class="inline-progress-fill"></div>
				</div>
			</div>
		{/if}

		<div class="page-content">
			<main class="page-main">
				{#if error && !error.includes('No analysis')}
					<!-- Error State -->
					<div class="state-card">
						<div class="state-icon">[WARN]ï¸</div>
						<h3 class="state-title">
							{error.includes('Authentication')
								? 'Authentication Required'
								: 'Error Loading Analysis'}
						</h3>
						<p class="state-message">{error}</p>
						{#if error.includes('Authentication')}
							<button onclick={() => goto('/github/login')} class="btn btn-primary"
								>Go to Login</button
							>
						{:else}
							<button onclick={fetchAnalysis} class="btn btn-primary">Try Again</button>
						{/if}
					</div>
				{:else if !analysisData || error?.includes('No analysis')}
					<!-- Empty State -->
					<div class="state-card">
						<div class="state-icon">&#9881;</div>
						<h3 class="state-title">No Analysis Found</h3>
						<p class="state-message">
							No workspace intelligence data is available yet. Run your first analysis to get
							started.
						</p>
						<button onclick={triggerNewAnalysis} class="btn btn-primary">
							Run Analysis Now
							<span class="button-arrow">→</span>
						</button>
					</div>
				{:else}
					<!-- Page Header -->
					<header class="view-header">
						<div class="title-group">
							<h1>Workspace Intelligence</h1>
							<p>OWASP DSOMM security maturity assessment for <strong>{org}</strong></p>
						</div>
						<div class="header-cta">
							<div class="score-pill">
								<span class="score-lbl">MATURITY</span>
								<span class="score-num"
									>{getOverallScore(analysisData.detected_practices)}<span class="score-unit"
										>/100</span
									></span
								>
							</div>
							<button onclick={openChatModal} class="btn btn-secondary">Ask AI</button>
							<button onclick={triggerNewAnalysis} class="btn btn-primary" disabled={loading}>
								{#if loading}
									<span class="btn-spinner"></span>
									Analyzing...
								{:else}
									Analyze Now
									<span class="button-arrow">→</span>
								{/if}
							</button>
						</div>
					</header>

					<!-- Tab Filter Navigation -->
					<div class="filter-nav">
						{#each [{ key: 'overview', label: 'OVERVIEW' }, { key: 'dsomm', label: 'DSOMM LEVELS' }, { key: 'repositories', label: 'REPOSITORIES' }, { key: 'findings', label: 'FINDINGS' }, { key: 'history', label: 'HISTORY' }] as tab}
							<button
								class="filter-btn {activeTab === tab.key ? 'active' : ''}"
								onclick={() => (activeTab = tab.key)}
							>
								{tab.label}
							</button>
						{/each}
					</div>

					<!-- ===== OVERVIEW TAB ===== -->
					{#if activeTab === 'overview'}
						{#if isUnifiedAnalysis}
							<div class="info-banner success">
								<div class="banner-content">
									<strong>Unified Workspace Analysis</strong>
									<span
										>Organization-wide security assessment across {projectBreakdowns.length} projects</span
									>
								</div>
							</div>
						{:else if analysisData.analysis?.analysis_scope === 'folder'}
							<div class="info-banner info">
								<div class="banner-content">
									<strong>Folder Analysis</strong>
									<span
										>Team-specific security assessment for: {analysisData.analysis?.project_name ||
											'Selected Folder'}</span
									>
								</div>
							</div>
						{/if}

						<!-- Quick Stats -->
						<div class="stats-grid">
							<div class="stat-card">
								<div class="feature-number">REPOSITORIES</div>
								<div class="stat-val">{analysisData.detected_practices?.total_repos || 0}</div>
								<div class="stat-detail">
									{analysisData.detected_practices?.repos_with_workflows || 0} with CI/CD workflows
								</div>
							</div>
							<div class="stat-card">
								<div class="feature-number">SECURITY TOOLS</div>
								<div class="stat-val">
									{(analysisData.detected_practices?.sast_tools?.length || 0) +
										(analysisData.detected_practices?.sca_tools?.length || 0) +
										(analysisData.detected_practices?.dast_tools?.length || 0) +
										(analysisData.detected_practices?.secret_scanning_tools?.length || 0) +
										(analysisData.detected_practices?.container_scanning_tools?.length || 0)}
								</div>
								<div class="stat-detail">Detected across all repos</div>
							</div>
							<div class="stat-card">
								<div class="feature-number">TOTAL FINDINGS</div>
								<div class="stat-val">
									{(analysisData.findings_count?.critical || 0) +
										(analysisData.findings_count?.high || 0) +
										(analysisData.findings_count?.medium || 0) +
										(analysisData.findings_count?.low || 0)}
								</div>
								<div class="stat-detail-badges">
									<span class="severity-badge critical"
										>{analysisData.findings_count?.critical || 0} Critical</span
									>
									<span class="severity-badge high"
										>{analysisData.findings_count?.high || 0} High</span
									>
								</div>
							</div>
							<div class="stat-card">
								<div class="feature-number">CENTRALIZED WORKFLOWS</div>
								<div class="stat-val">
									{analysisData.detected_practices?.uses_centralized_workflows ? 'Yes' : 'No'}
								</div>
								<div class="stat-detail">
									{analysisData.detected_practices?.uses_centralized_workflows
										? 'Implemented'
										: 'Not detected'}
								</div>
							</div>
						</div>

						<!-- Security Practices -->
						<div class="intel-card">
							<h2 class="card-heading">Detected Security Practices</h2>
							<div class="practices-grid">
								<div class="practice-item">
									<div class="practice-label">SAST TOOLS</div>
									{#if analysisData.detected_practices?.sast_tools?.length > 0}
										<div class="tool-list">
											{#each analysisData.detected_practices.sast_tools as tool}
												<span class="tool-tag active">{tool}</span>
											{/each}
										</div>
									{:else}
										<span class="tool-tag inactive">Not configured</span>
									{/if}
								</div>
								<div class="practice-item">
									<div class="practice-label">DAST TOOLS</div>
									{#if analysisData.detected_practices?.dast_tools?.length > 0}
										<div class="tool-list">
											{#each analysisData.detected_practices.dast_tools as tool}
												<span class="tool-tag active">{tool}</span>
											{/each}
										</div>
									{:else}
										<span class="tool-tag inactive">Not configured</span>
									{/if}
								</div>
								<div class="practice-item">
									<div class="practice-label">SCA TOOLS</div>
									{#if analysisData.detected_practices?.sca_tools?.length > 0}
										<div class="tool-list">
											{#each analysisData.detected_practices.sca_tools as tool}
												<span class="tool-tag active">{tool}</span>
											{/each}
										</div>
									{:else}
										<span class="tool-tag inactive">Not configured</span>
									{/if}
								</div>
								<div class="practice-item">
									<div class="practice-label">SECRET SCANNING</div>
									{#if analysisData.detected_practices?.secret_scanning_tools?.length > 0}
										<div class="tool-list">
											{#each analysisData.detected_practices.secret_scanning_tools as tool}
												<span class="tool-tag active">{tool}</span>
											{/each}
										</div>
									{:else}
										<span class="tool-tag inactive">Not configured</span>
									{/if}
								</div>
								<div class="practice-item">
									<div class="practice-label">CONTAINER SCANNING</div>
									{#if analysisData.detected_practices?.container_scanning_tools?.length > 0}
										<div class="tool-list">
											{#each analysisData.detected_practices.container_scanning_tools as tool}
												<span class="tool-tag active">{tool}</span>
											{/each}
										</div>
									{:else}
										<span class="tool-tag inactive">Not configured</span>
									{/if}
								</div>
								<div class="practice-item">
									<div class="practice-label">PRE-COMMIT HOOKS</div>
									{#if analysisData.detected_practices?.has_precommit_hooks}
										<div class="tool-list">
											{#each analysisData.detected_practices.precommit_hooks || [] as tool}
												<span class="tool-tag active">{tool}</span>
											{/each}
										</div>
									{:else}
										<span class="tool-tag inactive">Not configured</span>
									{/if}
								</div>
							</div>
						</div>

						<!-- Repository Policies -->
						<div class="intel-card">
							<h2 class="card-heading">Repository Policies</h2>
							<div class="policies-grid">
								<div class="policy-row">
									<span class="policy-name">Branch Protection</span>
									<span
										class="policy-status {analysisData.detected_practices?.branch_protection_enabled
											? 'enabled'
											: 'disabled'}"
										>{analysisData.detected_practices?.branch_protection_enabled
											? 'Enabled'
											: 'Disabled'}</span
									>
								</div>
								<div class="policy-row">
									<span class="policy-name">CODEOWNERS File</span>
									<span
										class="policy-status {analysisData.detected_practices?.has_codeowners
											? 'enabled'
											: 'disabled'}"
										>{analysisData.detected_practices?.has_codeowners ? 'Present' : 'Missing'}</span
									>
								</div>
								<div class="policy-row">
									<span class="policy-name">Required Reviews</span>
									<span class="policy-value"
										>{analysisData.detected_practices?.required_reviews || 0}</span
									>
								</div>
								<div class="policy-row">
									<span class="policy-name">Signed Commits Required</span>
									<span
										class="policy-status {analysisData.detected_practices?.signed_commits_required
											? 'enabled'
											: 'disabled'}"
										>{analysisData.detected_practices?.signed_commits_required
											? 'Enabled'
											: 'Disabled'}</span
									>
								</div>
								<div class="policy-row">
									<span class="policy-name">Status Checks Required</span>
									<span
										class="policy-status {analysisData.detected_practices?.required_status_checks
											? 'enabled'
											: 'disabled'}"
										>{analysisData.detected_practices?.required_status_checks
											? 'Enabled'
											: 'Disabled'}</span
									>
								</div>
								<div class="policy-row">
									<span class="policy-name">PR Workflows</span>
									<span
										class="policy-status {analysisData.detected_practices?.has_pr_workflows
											? 'enabled'
											: 'disabled'}"
										>{analysisData.detected_practices?.has_pr_workflows
											? 'Enabled'
											: 'Disabled'}</span
									>
								</div>
							</div>
						</div>

						<!-- Project Breakdowns (Unified) -->
						{#if isUnifiedAnalysis && projectBreakdowns.length > 0}
							<div class="intel-card">
								<h2 class="card-heading">
									Project Breakdown
									<span class="count-badge">{projectBreakdowns.length}</span>
								</h2>
								<div class="projects-list">
									{#each projectBreakdowns as project}
										{@const projectMaturity = project.maturity || {}}
										{@const projectId = project.project_id || project.project_name}
										{@const isExpanded = expandedProjects.has(projectId)}
										<div class="project-item">
											<button
												class="project-header"
												onclick={() => toggleProjectExpansion(projectId)}
											>
												<div class="project-info">
													<h3 class="project-name">{project.project_name}</h3>
													<div class="project-meta">
														<span>{project.repository_count || 0} repos</span>
														<span>{project.workflow_count || 0} workflows</span>
													</div>
												</div>
												<div class="project-score">
													<span class="p-score-num"
														>{Math.round(projectMaturity.overall_maturity_score || 0)}</span
													>
													<span class="p-score-lbl">Score</span>
												</div>
												<svg
													class="chevron {isExpanded ? 'open' : ''}"
													width="16"
													height="16"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													stroke-width="2"><path d="M19 9l-7 7-7-7" /></svg
												>
											</button>
											{#if isExpanded}
												<div class="project-details">
													<div class="detail-scores">
														<div class="detail-item">
															<span class="detail-label">Technology</span>
															<span class="detail-value"
																>{Math.round(
																	projectMaturity.domain_scores?.technology?.score ||
																		projectMaturity.implementation_score ||
																		0
																)}</span
															>
														</div>
														<div class="detail-item">
															<span class="detail-label">Process</span>
															<span class="detail-value"
																>{Math.round(
																	projectMaturity.domain_scores?.process?.score ||
																		projectMaturity.build_deployment_score ||
																		0
																)}</span
															>
														</div>
														<div class="detail-item">
															<span class="detail-label">Level</span>
															<span class="detail-value"
																>{projectMaturity.maturity_level !== undefined
																	? projectMaturity.maturity_level
																	: 'â€”'}</span
															>
														</div>
														<div class="detail-item">
															<span class="detail-label">Overall</span>
															<span class="detail-value"
																>{Math.round(projectMaturity.overall_maturity_score || 0)}</span
															>
														</div>
													</div>
													{#if project.findings_count}
														<div class="detail-findings">
															{#if project.findings_count.critical > 0}
																<span class="severity-badge critical"
																	>{project.findings_count.critical} Critical</span
																>
															{/if}
															{#if project.findings_count.high > 0}
																<span class="severity-badge high"
																	>{project.findings_count.high} High</span
																>
															{/if}
															{#if project.findings_count.medium > 0}
																<span class="severity-badge medium"
																	>{project.findings_count.medium} Medium</span
																>
															{/if}
															{#if project.findings_count.low > 0}
																<span class="severity-badge low"
																	>{project.findings_count.low} Low</span
																>
															{/if}
														</div>
													{/if}
													{#if project.detected_practices}
														<div class="detail-tools">
															{#each (project.detected_practices.sast_tools || []).slice(0, 3) as tool}
																<span class="tool-tag active sm">{tool}</span>
															{/each}
															{#each (project.detected_practices.sca_tools || []).slice(0, 2) as tool}
																<span class="tool-tag active sm">{tool}</span>
															{/each}
														</div>
													{/if}
												</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- ===== DSOMM TAB ===== -->
					{:else if activeTab === 'dsomm'}
						<div class="intel-card">
							<h2 class="card-heading">OWASP DSOMM Maturity Levels</h2>
							<div class="dsomm-table-wrap">
								<table class="dsomm-table">
									<thead>
										<tr>
											<th>Dimension</th>
											{#each [0, 1, 2, 3, 4] as level}
												<th class="level-th">L{level}</th>
											{/each}
										</tr>
									</thead>
									<tbody>
										{#each dsommDimensions as dimension}
											{@const currentLevel = calculateDimensionLevel(
												dimension,
												analysisData.detected_practices
											)}
											<tr>
												<td>
													<div class="dim-cell">
														<span class="dim-icon">{dimension.icon}</span>
														<div>
															<div class="dim-name">{dimension.name}</div>
															<div class="dim-desc">{dimension.description}</div>
														</div>
													</div>
												</td>
												{#each [0, 1, 2, 3, 4] as level}
													<td class="level-cell">
														<div
															class="level-dot {level <= currentLevel ? 'filled' : 'empty'}"
															style="--dot-color: {levelConfig[level].color}"
														></div>
													</td>
												{/each}
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						</div>

						<div class="dimension-grid">
							{#each dsommDimensions as dimension}
								{@const currentLevel = calculateDimensionLevel(
									dimension,
									analysisData.detected_practices
								)}
								{@const levelInfo = levelConfig[currentLevel]}
								<div class="intel-card compact">
									<div class="dim-card-header">
										<div class="dim-card-title">
											<span>{dimension.icon}</span>
											<h3>{dimension.name}</h3>
										</div>
										<div class="dim-level-badge">Level {currentLevel}</div>
									</div>
									<div class="progress-track">
										<div
											class="progress-fill-bar"
											style="width: {(currentLevel / 4) *
												100}%; background-color: {levelInfo.color}"
										></div>
									</div>
									<p class="dim-card-desc">{dimension.description}</p>
								</div>
							{/each}
						</div>

						<!-- ===== REPOSITORIES TAB ===== -->
					{:else if activeTab === 'repositories'}
						{#if isUnifiedAnalysis && projectBreakdowns.length > 0}
							{#each projectBreakdowns as project}
								{@const projectRepos =
									analysisData?.repositories?.filter(
										(r) => r.project_name === project.project_name
									) || []}
								{@const reposWithWorkflows = projectRepos.filter((r) => r.has_workflows !== false)}
								{@const reposWithoutWorkflows = projectRepos.filter(
									(r) => r.has_workflows === false
								)}
								{#if projectRepos.length > 0}
									<div class="intel-card">
										<div class="repo-project-header">
											<h2 class="card-heading">{project.project_name}</h2>
											<span class="count-badge">{projectRepos.length} repositories</span>
										</div>
										{#if reposWithWorkflows.length > 0}
											<div class="repo-section">
												<h3 class="repo-section-title">
													With CI/CD Workflows <span class="count-badge success"
														>{reposWithWorkflows.length}</span
													>
												</h3>
												<div class="repo-list">
													{#each reposWithWorkflows as repo}
														<div class="repo-item">
															<div class="repo-info">
																<span class="repo-name">{repo.repository_name}</span>
																<span class="repo-meta"
																	>{repo.workflows_analyzed || 0} workflows analyzed</span
																>
															</div>
															{#if repo.security_score !== null && repo.security_score !== undefined}
																<div class="repo-score">
																	{Math.round(repo.security_score)}<span class="score-unit"
																		>/100</span
																	>
																</div>
															{/if}
															{#if repo.findings_count}
																<div class="repo-findings">
																	{#if repo.findings_count.critical > 0}<span
																			class="severity-badge critical sm"
																			>{repo.findings_count.critical} C</span
																		>{/if}
																	{#if repo.findings_count.high > 0}<span
																			class="severity-badge high sm"
																			>{repo.findings_count.high} H</span
																		>{/if}
																	{#if repo.findings_count.medium > 0}<span
																			class="severity-badge medium sm"
																			>{repo.findings_count.medium} M</span
																		>{/if}
																	{#if repo.findings_count.low > 0}<span
																			class="severity-badge low sm"
																			>{repo.findings_count.low} L</span
																		>{/if}
																</div>
															{/if}
														</div>
													{/each}
												</div>
											</div>
										{/if}
										{#if reposWithoutWorkflows.length > 0}
											<div class="repo-section">
												<h3 class="repo-section-title">
													Without CI/CD Workflows <span class="count-badge warning"
														>{reposWithoutWorkflows.length}</span
													>
												</h3>
												<div class="repo-list">
													{#each reposWithoutWorkflows as repo}
														<div class="repo-item muted">
															<div class="repo-info">
																<span class="repo-name">{repo.repository_name}</span>
																<span class="repo-meta">No CI/CD workflows configured</span>
															</div>
														</div>
													{/each}
												</div>
											</div>
										{/if}
									</div>
								{/if}
							{/each}
						{:else}
							{#if getRepositoriesWithWorkflows().length > 0}
								<div class="intel-card">
									<h2 class="card-heading">
										Repositories with CI/CD Workflows <span class="count-badge success"
											>{getRepositoriesWithWorkflows().length}</span
										>
									</h2>
									<div class="repo-list">
										{#each getRepositoriesWithWorkflows() as repo}
											<div class="repo-item">
												<div class="repo-info">
													<span class="repo-name">{repo.repository_name}</span>
													<span class="repo-meta"
														>{repo.workflows_analyzed || 0} workflows analyzed</span
													>
												</div>
												{#if repo.security_score !== null && repo.security_score !== undefined}
													<div class="repo-score">
														{Math.round(repo.security_score)}<span class="score-unit">/100</span>
													</div>
												{/if}
												{#if repo.findings_count}
													<div class="repo-findings">
														{#if repo.findings_count.critical > 0}<span
																class="severity-badge critical sm"
																>{repo.findings_count.critical} Critical</span
															>{/if}
														{#if repo.findings_count.high > 0}<span class="severity-badge high sm"
																>{repo.findings_count.high} High</span
															>{/if}
														{#if repo.findings_count.medium > 0}<span
																class="severity-badge medium sm"
																>{repo.findings_count.medium} Medium</span
															>{/if}
														{#if repo.findings_count.low > 0}<span class="severity-badge low sm"
																>{repo.findings_count.low} Low</span
															>{/if}
													</div>
												{/if}
											</div>
										{/each}
									</div>
								</div>
							{/if}
							{#if getRepositoriesWithoutWorkflows().length > 0}
								<div class="intel-card">
									<h2 class="card-heading">
										Repositories without CI/CD Workflows <span class="count-badge warning"
											>{getRepositoriesWithoutWorkflows().length}</span
										>
									</h2>
									<div class="info-banner warning">
										<span
											>These repositories are not included in the overall security score since they
											don't have GitHub Actions workflows configured.</span
										>
									</div>
									<div class="repo-list">
										{#each getRepositoriesWithoutWorkflows() as repo}
											<div class="repo-item muted">
												<div class="repo-info">
													<span class="repo-name">{repo.repository_name}</span>
													<span class="repo-meta">No CI/CD workflows configured</span>
												</div>
											</div>
										{/each}
									</div>
								</div>
							{/if}
						{/if}

						<!-- ===== FINDINGS TAB ===== -->
					{:else if activeTab === 'findings'}
						{#if analysisData.findings && analysisData.findings.length > 0}
							{#each analysisData.findings as finding, idx}
								<div class="finding-card">
									<button class="finding-header" onclick={() => toggleFinding(idx)}>
										<span class="severity-badge {finding.severity}">{finding.severity}</span>
										<div class="finding-info">
											<h3 class="finding-title">{finding.title}</h3>
											<p class="finding-desc">{finding.description}</p>
										</div>
										<svg
											class="chevron {expandedFindings.has(idx) ? 'open' : ''}"
											width="16"
											height="16"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"><path d="M19 9l-7 7-7-7" /></svg
										>
									</button>
									{#if expandedFindings.has(idx)}
										<div class="finding-details">
											<div class="finding-section">
												<h4>Recommendation</h4>
												<p>{finding.recommendation}</p>
											</div>
											{#if finding.affected_component}
												<div class="finding-section">
													<h4>Affected Component</h4>
													<code class="component-code">{finding.affected_component}</code>
												</div>
											{/if}
										</div>
									{/if}
								</div>
							{/each}
						{:else}
							<div class="state-card">
								<div class="state-icon">&#10003;</div>
								<h3 class="state-title">No Findings</h3>
								<p class="state-message">No security issues detected.</p>
							</div>
						{/if}

						<!-- ===== HISTORY TAB ===== -->
					{:else if activeTab === 'history'}
						<div class="history-header-row">
							<h2 class="card-heading">Analysis History</h2>
							<span class="count-badge">{allAnalyses.length}</span>
						</div>
						{#if allAnalyses.length > 0}
							{#each allAnalyses as analysis (analysis.id)}
								<div class="history-item {analysis.id === selectedAnalysisId ? 'selected' : ''}">
									<div class="history-info">
										<div class="history-top">
											<h3 class="history-title">
												{analysis.id === selectedAnalysisId ? '* ' : ''}Analysis - {formatDate(
													analysis.created_at
												)}
											</h3>
											{#if analysis.id === selectedAnalysisId}
												<span class="tag-badge viewing">VIEWING</span>
											{/if}
											{#if analysis.analysis_scope === 'unified'}
												<span class="tag-badge unified">UNIFIED</span>
											{:else if analysis.analysis_scope === 'folder'}
												<span class="tag-badge folder">FOLDER</span>
											{:else if analysis.analysis_scope === 'project'}
												<span class="tag-badge project">PROJECT</span>
											{/if}
										</div>
										<div class="history-stats">
											<div class="history-stat">
												<span class="history-stat-label">Repos</span>
												<span class="history-stat-value">{analysis.total_repositories || 0}</span>
											</div>
											<div class="history-stat">
												<span class="history-stat-label">Findings</span>
												<span class="history-stat-value">{analysis.findings_count || 0}</span>
											</div>
											<div class="history-stat">
												<span class="history-stat-label">Maturity</span>
												<span class="history-stat-value">{analysis.maturity_score || 0}%</span>
											</div>
											<div class="history-stat">
												<span class="history-stat-label">Status</span>
												<span class="history-stat-value">{analysis.status || 'completed'}</span>
											</div>
										</div>
										{#if analysis.project_name}
											<div class="history-project">
												{analysis.analysis_scope === 'folder' ? 'Folder' : 'Project'}:
												<strong>{analysis.project_name}</strong>
											</div>
										{/if}
									</div>
									<div class="history-actions">
										{#if analysis.id !== selectedAnalysisId}
											<button
												onclick={() => switchToAnalysis(analysis.id)}
												class="btn btn-secondary sm">View</button
											>
										{/if}
										<button
											onclick={() => deleteAnalysis(analysis.id)}
											disabled={deletingAnalysisId === analysis.id}
											class="btn btn-danger sm"
										>
											{deletingAnalysisId === analysis.id ? '...' : 'Delete'}
										</button>
									</div>
								</div>
							{/each}
						{:else}
							<div class="state-card">
								<div class="state-icon">&#128269;</div>
								<h3 class="state-title">No Analysis History</h3>
								<p class="state-message">Run your first analysis to see it here!</p>
							</div>
						{/if}
					{/if}
				{/if}
			</main>
		</div>
	</div>
{/if}

<!-- Chat Modal -->
<ChatModal
	bind:isOpen={isChatModalOpen}
	orgName={org}
	analysisScope={isUnifiedAnalysis ? 'unified' : 'folder'}
	analysisId={selectedAnalysisId}
	projectName={analysisData?.project_name}
	folderPath={analysisData?.folder_path}
	on:close={closeChatModal}
/>

<style>
	/* ============================================
	   PROFESSIONAL DESIGN SYSTEM (MATTE ENGINEERING)
	   Consistent with Dashboard & Organizations
	   ============================================ */
	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
		--nav-height: 64px;
	}

	.intel-page.dark {
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
		--error: #ef4444;
		--warning: #f59e0b;
		--card-shadow: none;
	}

	.intel-page.light {
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
		--error: #dc2626;
		--warning: #d97706;
		--card-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
	}

	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	.intel-page {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
		overflow-x: hidden;
	}

	.intel-page::before {
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

	/* ============================================
	   LOADING SCREEN
	   ============================================ */
	.loading-screen {
		position: fixed;
		inset: 0;
		background: #000000;
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 9999;
	}

	.loading-content {
		text-align: center;
		max-width: 300px;
	}

	.loading-icon {
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

	.progress-bar {
		height: 2px;
		background: rgba(255, 255, 255, 0.05);
		border-radius: 4px;
		overflow: hidden;
		margin: 1rem 0;
	}

	.progress-fill {
		height: 100%;
		background: #00adef;
		width: 40%;
		animation: load 1.5s ease-in-out infinite;
	}

	@keyframes load {
		0% {
			transform: translateX(-100%);
			width: 20%;
		}
		50% {
			width: 50%;
		}
		100% {
			transform: translateX(300%);
			width: 20%;
		}
	}

	.status-message {
		font-family: var(--font-mono, monospace);
		font-size: 0.7rem;
		color: rgba(255, 255, 255, 0.4);
		letter-spacing: 0.15em;
		text-transform: uppercase;
	}

	/* Inline re-analysis loader */
	.inline-loader {
		padding: 0 2rem;
	}

	.inline-progress {
		height: 2px;
		background: var(--border);
		border-radius: 1px;
		overflow: hidden;
	}

	.inline-progress-fill {
		height: 100%;
		background: var(--accent);
		width: 30%;
		animation: load 1.5s ease-in-out infinite;
	}

	/* ============================================
	   HEADER NAVIGATION
	   ============================================ */
	.dashboard-header {
		position: sticky;
		top: 0;
		z-index: 100;
		height: var(--nav-height);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
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
		padding: 0.5rem 0;
	}

	.nav-link:hover,
	.nav-link.active {
		color: var(--text-primary);
	}

	.nav-actions {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}

	.theme-toggle {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 6px;
		transition: all 0.2s;
	}

	.theme-toggle:hover {
		background: var(--border);
		color: var(--text-primary);
	}

	.theme-icon {
		width: 18px;
		height: 18px;
	}

	/* ============================================
	   TECHNICAL BREADCRUMB BAR
	   ============================================ */
	.technical-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 0 2rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		height: 40px;
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

	.bc-node:hover {
		color: var(--accent);
	}

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

	/* ============================================
	   PAGE LAYOUT
	   ============================================ */
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

	/* ============================================
	   VIEW HEADER
	   ============================================ */
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
		line-height: 1.5;
	}

	.title-group strong {
		color: var(--accent);
		font-weight: 700;
	}

	.header-cta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	/* Score Pill */
	.score-pill {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		padding: 0.5rem 1rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 8px;
	}

	.score-lbl {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	.score-num {
		font-family: var(--font-mono);
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--accent);
		line-height: 1;
	}

	.score-unit {
		font-size: 0.75rem;
		color: var(--text-muted);
		font-weight: 500;
	}

	/* ============================================
	   FILTER NAV (TABS)
	   ============================================ */
	.filter-nav {
		display: flex;
		gap: 0.25rem;
		background: var(--bg-surface-alt);
		padding: 0.25rem;
		border-radius: 8px;
		border: 1px solid var(--border);
		margin-bottom: 2rem;
		width: fit-content;
	}

	.filter-btn {
		background: none;
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.2s;
		font-family: var(--font-sans);
		letter-spacing: 0.02em;
	}

	.filter-btn:hover {
		color: var(--text-primary);
	}

	.filter-btn.active {
		background: var(--bg-surface);
		color: var(--accent);
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	/* ============================================
	   INTEL CARD
	   ============================================ */
	.intel-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		margin-bottom: 1.25rem;
		box-shadow: var(--card-shadow);
		transition: all 0.2s var(--ease-premium);
	}

	.intel-card:hover {
		border-color: var(--border-focus);
	}

	.intel-card.compact {
		padding: 1.25rem;
	}

	.card-heading {
		font-size: 0.9375rem;
		font-weight: 700;
		margin-bottom: 1.25rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	/* ============================================
	   STATS GRID
	   ============================================ */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
		margin-bottom: 1.25rem;
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

	.stat-detail-badges {
		display: flex;
		gap: 0.375rem;
		margin-top: 0.5rem;
	}

	/* ============================================
	   PRACTICES GRID
	   ============================================ */
	.practices-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1rem;
	}

	.practice-item {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 1rem;
	}

	.practice-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.5rem;
	}

	.tool-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.375rem;
	}

	.tool-tag {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		display: inline-flex;
		align-items: center;
	}

	.tool-tag.active {
		background: rgba(16, 185, 129, 0.08);
		color: var(--success);
		border: 1px solid rgba(16, 185, 129, 0.15);
	}

	.tool-tag.inactive {
		color: var(--text-muted);
		font-style: italic;
		font-size: 0.75rem;
	}

	.tool-tag.sm {
		font-size: 0.7rem;
		padding: 0.125rem 0.375rem;
	}

	/* ============================================
	   POLICIES
	   ============================================ */
	.policies-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.5rem;
	}

	.policy-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.625rem 0.875rem;
		background: var(--bg-surface-alt);
		border-radius: 6px;
	}

	.policy-name {
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--text-primary);
	}

	.policy-status {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.policy-status.enabled {
		color: var(--success);
	}

	.policy-status.disabled {
		color: var(--text-muted);
	}

	.policy-value {
		font-family: var(--font-mono);
		font-size: 0.875rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	/* ============================================
	   PROJECTS LIST
	   ============================================ */
	.projects-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.project-item {
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}

	.project-header {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.15s;
	}

	.project-header:hover {
		background: var(--bg-surface-alt);
	}

	.project-info {
		flex: 1;
	}

	.project-name {
		font-size: 0.875rem;
		font-weight: 700;
		margin-bottom: 0.25rem;
	}

	.project-meta {
		display: flex;
		gap: 1rem;
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	.project-score {
		text-align: right;
	}

	.p-score-num {
		font-family: var(--font-mono);
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--accent);
		display: block;
	}

	.p-score-lbl {
		font-size: 0.6rem;
		color: var(--text-muted);
	}

	.chevron {
		transition: transform 0.2s;
		color: var(--text-muted);
		flex-shrink: 0;
	}

	.chevron.open {
		transform: rotate(180deg);
	}

	.project-details {
		padding: 1rem;
		border-top: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.detail-scores {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 0.5rem;
	}

	.detail-item {
		background: var(--bg-surface-alt);
		border-radius: 6px;
		padding: 0.625rem;
	}

	.detail-label {
		font-size: 0.6rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.detail-value {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
		color: var(--accent);
	}

	.detail-findings,
	.detail-tools {
		display: flex;
		flex-wrap: wrap;
		gap: 0.375rem;
	}

	/* ============================================
	   DSOMM TABLE
	   ============================================ */
	.dsomm-table-wrap {
		overflow-x: auto;
	}

	.dsomm-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.8125rem;
	}

	.dsomm-table th {
		padding: 0.75rem;
		text-align: left;
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		border-bottom: 1px solid var(--border);
	}

	.dsomm-table th.level-th {
		text-align: center;
		width: 60px;
	}

	.dsomm-table td {
		padding: 0.75rem;
		border-bottom: 1px solid var(--border);
	}

	.dsomm-table tr:last-child td {
		border-bottom: none;
	}

	.dsomm-table tr:hover {
		background: var(--bg-surface-alt);
	}

	.dim-cell {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.dim-icon {
		font-size: 1.25rem;
	}

	.dim-name {
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.125rem;
	}

	.dim-desc {
		font-size: 0.7rem;
		color: var(--text-secondary);
	}

	.level-cell {
		text-align: center;
	}

	.level-dot {
		width: 16px;
		height: 16px;
		border-radius: 3px;
		margin: 0 auto;
	}

	.level-dot.filled {
		background: var(--dot-color);
	}

	.level-dot.empty {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
	}

	/* Dimension Grid */
	.dimension-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1rem;
		margin-top: 1.25rem;
	}

	.dim-card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}

	.dim-card-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.dim-card-title h3 {
		font-size: 0.875rem;
		font-weight: 700;
	}

	.dim-level-badge {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 600;
		color: var(--accent);
		border: 1px solid var(--border);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
	}

	.progress-track {
		height: 4px;
		background: var(--bg-surface-alt);
		border-radius: 2px;
		overflow: hidden;
		margin-bottom: 0.75rem;
	}

	.progress-fill-bar {
		height: 100%;
		border-radius: 2px;
		transition: width 0.5s var(--ease-premium);
	}

	.dim-card-desc {
		font-size: 0.75rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	/* ============================================
	   REPOSITORY LIST
	   ============================================ */
	.repo-project-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1.25rem;
	}

	.repo-project-header .card-heading {
		margin-bottom: 0;
	}

	.repo-section {
		margin-bottom: 1.5rem;
	}

	.repo-section:last-child {
		margin-bottom: 0;
	}

	.repo-section-title {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--text-secondary);
		margin-bottom: 0.75rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.repo-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.repo-item {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.75rem 1rem;
		background: var(--bg-surface-alt);
		border-radius: 8px;
		border: 1px solid var(--border);
	}

	.repo-item.muted {
		opacity: 0.6;
	}

	.repo-info {
		flex: 1;
	}

	.repo-name {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.repo-meta {
		font-size: 0.7rem;
		color: var(--text-secondary);
		margin-top: 0.125rem;
	}

	.repo-score {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
		color: var(--accent);
	}

	.repo-score .score-unit {
		font-size: 0.7rem;
		color: var(--text-muted);
	}

	.repo-findings {
		display: flex;
		gap: 0.25rem;
	}

	/* ============================================
	   FINDING CARDS
	   ============================================ */
	.finding-card {
		border: 1px solid var(--border);
		border-radius: 8px;
		margin-bottom: 0.5rem;
		overflow: hidden;
		background: var(--bg-surface);
	}

	.finding-header {
		width: 100%;
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.875rem 1rem;
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.15s;
	}

	.finding-header:hover {
		background: var(--bg-surface-alt);
	}

	.finding-info {
		flex: 1;
	}

	.finding-title {
		font-size: 0.8125rem;
		font-weight: 600;
		margin-bottom: 0.25rem;
	}

	.finding-desc {
		font-size: 0.75rem;
		color: var(--text-secondary);
		line-height: 1.4;
	}

	.finding-details {
		padding: 0.875rem 1rem;
		border-top: 1px solid var(--border);
	}

	.finding-section {
		margin-bottom: 0.75rem;
	}

	.finding-section:last-child {
		margin-bottom: 0;
	}

	.finding-section h4 {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.375rem;
	}

	.finding-section p {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	.component-code {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
		background: var(--bg-surface-alt);
		border-radius: 4px;
		color: var(--accent);
	}

	/* ============================================
	   HISTORY
	   ============================================ */
	.history-header-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1.25rem;
	}

	.history-header-row .card-heading {
		margin-bottom: 0;
	}

	.history-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		margin-bottom: 0.5rem;
		background: var(--bg-surface);
		transition: border-color 0.15s;
	}

	.history-item.selected {
		border-color: var(--accent);
		background: var(--accent-soft);
	}

	.history-info {
		flex: 1;
	}

	.history-top {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-bottom: 0.75rem;
	}

	.history-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.tag-badge {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.tag-badge.viewing {
		background: var(--accent-soft);
		color: var(--accent);
	}

	.tag-badge.unified {
		background: rgba(16, 185, 129, 0.08);
		color: var(--success);
	}

	.tag-badge.folder {
		background: var(--accent-soft);
		color: var(--accent);
	}

	.tag-badge.project {
		background: var(--bg-surface-alt);
		color: var(--text-muted);
	}

	.history-stats {
		display: flex;
		gap: 1.5rem;
		margin-bottom: 0.5rem;
	}

	.history-stat-label {
		font-size: 0.65rem;
		color: var(--text-muted);
		display: block;
	}

	.history-stat-value {
		font-family: var(--font-mono);
		font-size: 0.875rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.history-project {
		font-size: 0.75rem;
		color: var(--text-secondary);
	}

	.history-actions {
		display: flex;
		gap: 0.375rem;
		flex-shrink: 0;
	}

	/* ============================================
	   STATE CARDS (ERROR / EMPTY)
	   ============================================ */
	.state-card {
		text-align: center;
		padding: 5rem 2rem;
		max-width: 500px;
		margin: 0 auto;
	}

	.state-icon {
		font-size: 3rem;
		margin-bottom: 1rem;
	}

	.state-title {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	.state-message {
		font-size: 0.875rem;
		color: var(--text-secondary);
		margin-bottom: 1.5rem;
		line-height: 1.6;
	}

	/* ============================================
	   INFO BANNERS
	   ============================================ */
	.info-banner {
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1.25rem;
		font-size: 0.8125rem;
		border: 1px solid var(--border);
	}

	.info-banner.success {
		background: rgba(16, 185, 129, 0.04);
		border-color: rgba(16, 185, 129, 0.15);
	}

	.info-banner.info {
		background: var(--accent-soft);
		border-color: rgba(0, 173, 239, 0.15);
	}

	.info-banner.warning {
		background: rgba(245, 158, 11, 0.04);
		border-color: rgba(245, 158, 11, 0.15);
		color: var(--text-secondary);
	}

	.banner-content {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.banner-content strong {
		color: var(--text-primary);
	}

	.banner-content span {
		color: var(--text-secondary);
		font-size: 0.75rem;
	}

	/* ============================================
	   SEVERITY BADGES
	   ============================================ */
	.severity-badge {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 600;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.severity-badge.critical {
		background: rgba(220, 38, 38, 0.08);
		color: #ef4444;
	}

	.severity-badge.high {
		background: rgba(234, 88, 12, 0.08);
		color: #f97316;
	}

	.severity-badge.medium {
		background: rgba(217, 119, 6, 0.08);
		color: #f59e0b;
	}

	.severity-badge.low {
		background: rgba(101, 163, 13, 0.08);
		color: #84cc16;
	}

	.severity-badge.info {
		background: rgba(2, 132, 199, 0.08);
		color: #06b6d4;
	}

	.severity-badge.sm {
		font-size: 0.6rem;
		padding: 0.125rem 0.375rem;
	}

	/* Count Badge */
	.count-badge {
		font-size: 0.65rem;
		font-weight: 600;
		background: var(--bg-surface-alt);
		color: var(--text-muted);
		padding: 0.125rem 0.5rem;
		border-radius: 4px;
	}

	.count-badge.success {
		background: rgba(16, 185, 129, 0.08);
		color: var(--success);
	}

	.count-badge.warning {
		background: rgba(245, 158, 11, 0.08);
		color: var(--warning);
	}

	/* ============================================
	   BUTTONS
	   ============================================ */
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.625rem 1.25rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
		font-family: var(--font-sans);
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		white-space: nowrap;
	}

	.btn:hover:not(:disabled) {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
		transform: translateY(-1px);
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		transform: none;
	}

	.btn-primary {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
	}

	.btn-primary:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}

	.btn-secondary {
		background: var(--bg-surface-alt);
		border-color: var(--border);
	}

	.btn-danger {
		background: transparent;
		border-color: rgba(239, 68, 68, 0.2);
		color: var(--error);
	}

	.btn-danger:hover:not(:disabled) {
		background: var(--error);
		color: #fff;
		border-color: var(--error);
	}

	.btn.sm {
		padding: 0.4375rem 0.75rem;
		font-size: 0.75rem;
	}

	.button-arrow {
		font-size: 1rem;
		transition: transform 0.15s;
	}

	.btn:hover .button-arrow {
		transform: translateX(3px);
	}

	.btn-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ============================================
	   RESPONSIVE
	   ============================================ */
	@media (max-width: 1200px) {
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.practices-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 768px) {
		.view-header {
			flex-direction: column;
			align-items: flex-start;
		}

		.nav-menu {
			display: none;
		}

		.stats-grid {
			grid-template-columns: 1fr;
		}

		.practices-grid {
			grid-template-columns: 1fr;
		}

		.policies-grid {
			grid-template-columns: 1fr;
		}

		.detail-scores {
			grid-template-columns: repeat(2, 1fr);
		}

		.page-main {
			padding: 1.5rem 1rem;
		}

		.header-cta {
			flex-wrap: wrap;
		}

		.filter-nav {
			overflow-x: auto;
			width: 100%;
		}

		.history-item {
			flex-direction: column;
			align-items: flex-start;
		}

		.history-actions {
			width: 100%;
		}

		.header-content {
			padding: 0 1rem;
		}

		.technical-bar {
			padding: 0 1rem;
		}
	}
</style>
