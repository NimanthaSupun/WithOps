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
	console.log('🚀 Intelligence Page Initialized');
	console.log('📍 Org param:', org);
	console.log('🌐 API Base URL:', API_BASE_URL);
	console.log('🔐 Has auth token:', !!getAuthToken());

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
			icon: '🚀'
		},
		{
			id: 'implementation',
			name: 'Implementation',
			description: 'Secure coding, dependency management, secret management',
			icon: '💻'
		},
		{
			id: 'test_verification',
			name: 'Test & Verification',
			description: 'SAST, DAST, SCA, penetration testing',
			icon: '🔍'
		},
		{
			id: 'information_gathering',
			name: 'Information Gathering',
			description: 'Vulnerability management, logging, monitoring',
			icon: '📊'
		},
		{
			id: 'culture_organization',
			name: 'Culture & Organization',
			description: 'Security champions, training, collaboration',
			icon: '👥'
		}
	];

	// Level indicators
	const levelConfig = {
		0: { label: 'None', color: '#E5E7EB', emoji: '⬜', bgDark: '#374151' },
		1: { label: 'Basic', color: '#FCD34D', emoji: '🟨', bgDark: '#78350F' },
		2: { label: 'Advanced', color: '#FB923C', emoji: '🟧', bgDark: '#9A3412' },
		3: { label: 'Mature', color: '#86EFAC', emoji: '🟩', bgDark: '#14532D' },
		4: { label: 'Optimized', color: '#22C55E', emoji: '🟩', bgDark: '#052E16' }
	};

	onMount(async () => {
		console.log('🔍 Intelligence page mounted for org:', org);
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

			console.log('🚀 Triggering new analysis for org:', org);

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
			console.log('📦 Tree result fetched:', treeResult);

			// Extract tree data and ID from response
			const treeData = treeResult.data || [];
			const repositoryTreeId = treeResult.metadata?.id;

			if (!repositoryTreeId) {
				throw new Error(
					'No repository tree ID found. Please access the repository tree view first to create your workspace structure.'
				);
			}

			console.log('📋 Tree ID:', repositoryTreeId, 'Tree data items:', treeData.length);

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

			console.log('✅ Analysis triggered successfully');

			// Wait a moment then fetch results
			await new Promise((resolve) => setTimeout(resolve, 2000));
			await fetchAnalysis();
		} catch (err) {
			console.error('❌ Failed to trigger analysis:', err);
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
			console.log('🔑 Token exists:', !!token);

			if (!token) {
				console.warn('❌ No token found');
				error = 'Authentication required. Please login to access Workspace Intelligence.';
				loading = false;
				return;
			}

			console.log('📡 Fetching analysis for org:', org);

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

			console.log('📊 API Response status:', response.status);

			if (!response.ok) {
				const errorText = await response.text();
				console.error('❌ API Error:', response.status, errorText);
				throw new Error(`Failed to fetch analysis: ${response.statusText}`);
			}

			const data = await response.json();
			console.log('✅ Analysis data received:', data);

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
					console.log('📋 Detailed analysis response:', detailData);

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
						console.log('📂 Found', projectBreakdowns.length, 'project breakdowns');
					}

					console.log('📦 Final analysisData:', analysisData);
					console.log('🔍 Is Unified Analysis:', isUnifiedAnalysis);
					console.log('📊 Repositories count:', analysisData.repositories?.length || 0);
					console.log('🔍 Findings count:', analysisData.findings?.length || 0);
				} else {
					console.warn('⚠️ Detail fetch failed, using basic data');
					analysisData = latestAnalysis;
				}
			} else {
				error = 'No analysis found for this organization. Please run an analysis first.';
			}
		} catch (err) {
			console.error('❌ Failed to fetch analysis:', err);
			error = err.message;
			// Don't redirect on error, stay on page and show error
		} finally {
			loading = false;
			console.log('✅ Loading complete. Error:', error);
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

			console.log('✅ Analysis deleted successfully');

			// Reload analyses
			selectedAnalysisId = null;
			await fetchAnalysis();
		} catch (err) {
			console.error('❌ Failed to delete analysis:', err);
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

<div class="intelligence-container {$isDarkMode ? 'dark' : 'light'}">
	<!-- Professional Navigation Header -->
	<nav class="intelligence-header">
		<div class="header-content">
			<div class="header-left">
				<button onclick={() => goto(`/github/workspace/${org}/repo-treeview`)} class="back-button">
					<svg
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path d="M19 12H5M12 19l-7-7 7-7" />
					</svg>
					<span>Back</span>
				</button>

				<div class="header-title-section">
					<h1 class="page-title">
						<span class="title-icon">🧠</span>
						<span class="title-text">Workspace Intelligence</span>
					</h1>
					<p class="page-subtitle">
						OWASP DSOMM Security Maturity Assessment for <span class="org-name">{org}</span>
					</p>
				</div>
			</div>

			{#if !loading && analysisData}
				<div class="header-actions">
					<div class="maturity-score-display">
						<div class="score-label">Overall Maturity Score</div>
						<div class="score-value">
							{getOverallScore(analysisData.detected_practices)}<span class="score-max">/100</span>
						</div>
					</div>

					<button onclick={openChatModal} class="btn-ai">
						<span class="btn-icon">🤖</span>
						<span class="btn-text">Ask AI</span>
					</button>

					<button onclick={triggerNewAnalysis} class="btn-primary">
						<span class="btn-icon">🔄</span>
						<span class="btn-text">Analyze Now</span>
					</button>
				</div>
			{/if}
		</div>
	</nav>

	<!-- Main Content -->
	<div class="main-content">
		{#if loading}
			<div class="loading-state">
				<div class="loading-content">
					<div class="loading-spinner"></div>
					<p class="loading-text">Loading workspace intelligence...</p>
				</div>
			</div>
		{:else if error && !error.includes('No analysis')}
			<div class="error-state">
				<div class="error-content">
					<span class="error-icon">⚠️</span>
					<div class="error-details">
						<h3 class="error-title">
							{error.includes('Authentication')
								? '🔐 Authentication Required'
								: 'Error Loading Analysis'}
						</h3>
						<p class="error-message">{error}</p>
						{#if error.includes('Authentication')}
							<button onclick={() => goto('/github/login')} class="btn-primary">
								Go to Login
							</button>
						{:else}
							<button onclick={fetchAnalysis} class="btn-primary"> Try Again </button>
						{/if}
					</div>
				</div>
			</div>
		{:else if !analysisData || error?.includes('No analysis')}
			<div class="empty-state">
				<div class="empty-content">
					<span class="empty-icon">🧠</span>
					<div class="empty-details">
						<h3 class="empty-title">No Analysis Found</h3>
						<p class="empty-message">
							No workspace intelligence data is available yet. Click below to run your first
							analysis!
						</p>
						<button onclick={triggerNewAnalysis} class="btn-primary">
							<span class="btn-icon">🚀</span>
							<span class="btn-text">Run Analysis Now</span>
						</button>
					</div>
				</div>
			</div>
		{:else if analysisData}
			<!-- Professional Tab Navigation -->
			<div class="tab-navigation">
				<nav class="tab-nav">
					{#each ['overview', 'dsomm', 'repositories', 'findings', 'history'] as tab}
						<button
							onclick={() => (activeTab = tab)}
							class="tab-button {activeTab === tab ? 'active' : ''}"
						>
							{tab === 'dsomm' ? 'DSOMM Levels' : tab === 'history' ? 'Analysis History' : tab}
						</button>
					{/each}
				</nav>
			</div>

			<!-- Tab Content -->
			{#if activeTab === 'overview'}
				<!-- Overview Tab -->
				<div class="space-y-6">
					<!-- Analysis Type Header -->
					{#if isUnifiedAnalysis}
						<div
							class="rounded-lg p-4 transition-colors {$isDarkMode
								? 'border border-green-700 bg-gradient-to-r from-green-900/20 to-blue-900/20'
								: 'border border-green-200 bg-gradient-to-r from-green-50 to-blue-50'}"
						>
							<div class="flex items-center gap-3">
								<span class="text-3xl">🌐</span>
								<div>
									<h3
										class="text-lg font-bold transition-colors {$isDarkMode
											? 'text-green-400'
											: 'text-green-800'}"
									>
										Unified Workspace Analysis
									</h3>
									<p
										class="text-sm transition-colors {$isDarkMode
											? 'text-green-300'
											: 'text-green-700'}"
									>
										Organization-wide security assessment across {projectBreakdowns.length} projects
									</p>
								</div>
							</div>
						</div>
					{:else if analysisData.analysis?.analysis_scope === 'folder'}
						<div
							class="rounded-lg p-4 transition-colors {$isDarkMode
								? 'border border-blue-700 bg-blue-900/20'
								: 'border border-blue-200 bg-blue-50'}"
						>
							<div class="flex items-center gap-3">
								<span class="text-3xl">📁</span>
								<div>
									<h3
										class="text-lg font-bold transition-colors {$isDarkMode
											? 'text-blue-400'
											: 'text-blue-800'}"
									>
										Folder Analysis
									</h3>
									<p
										class="text-sm transition-colors {$isDarkMode
											? 'text-blue-300'
											: 'text-blue-700'}"
									>
										Team-specific security assessment for: {analysisData.analysis?.project_name ||
											'Selected Folder'}
									</p>
								</div>
							</div>
						</div>
					{/if}

					<!-- Quick Stats -->
					<div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
						<div class="stat-card dashboard-card">
							<div class="stat-label">Total Repositories</div>
							<div class="stat-value">{analysisData.detected_practices?.total_repos || 0}</div>
							<div class="stat-detail">
								{analysisData.detected_practices?.repos_with_workflows || 0} with CI/CD workflows
							</div>
						</div>

						<div class="stat-card dashboard-card">
							<div class="stat-label">Security Tools</div>
							<div class="stat-value">
								{(analysisData.detected_practices?.sast_tools?.length || 0) +
									(analysisData.detected_practices?.sca_tools?.length || 0) +
									(analysisData.detected_practices?.dast_tools?.length || 0) +
									(analysisData.detected_practices?.secret_scanning_tools?.length || 0) +
									(analysisData.detected_practices?.container_scanning_tools?.length || 0)}
							</div>
							<div class="stat-detail">Detected across all repos</div>
						</div>

						<div
							class="rounded-lg p-6 transition-colors {$isDarkMode
								? 'bg-gray-800'
								: 'bg-white shadow-sm'}"
						>
							<div
								class="mb-2 text-sm font-medium transition-colors {$isDarkMode
									? 'text-gray-400'
									: 'text-gray-600'}"
							>
								Total Findings
							</div>
							<div
								class="text-3xl font-bold transition-colors {$isDarkMode
									? 'text-white'
									: 'text-gray-900'}"
							>
								{analysisData.findings_count?.critical +
									analysisData.findings_count?.high +
									analysisData.findings_count?.medium +
									analysisData.findings_count?.low || 0}
							</div>
							<div class="mt-2 flex gap-2 text-xs">
								<span
									class="rounded px-2 py-1"
									style="background-color: {getSeverityColor(
										'critical'
									)}20; color: {getSeverityColor('critical')}"
								>
									{analysisData.findings_count?.critical || 0} Critical
								</span>
								<span
									class="rounded px-2 py-1"
									style="background-color: {getSeverityColor('high')}20; color: {getSeverityColor(
										'high'
									)}"
								>
									{analysisData.findings_count?.high || 0} High
								</span>
							</div>
						</div>

						<div
							class="rounded-lg p-6 transition-colors {$isDarkMode
								? 'bg-gray-800'
								: 'bg-white shadow-sm'}"
						>
							<div
								class="mb-2 text-sm font-medium transition-colors {$isDarkMode
									? 'text-gray-400'
									: 'text-gray-600'}"
							>
								Centralized Workflows
							</div>
							<div
								class="text-3xl font-bold transition-colors {$isDarkMode
									? 'text-white'
									: 'text-gray-900'}"
							>
								{analysisData.detected_practices?.uses_centralized_workflows ? '✅' : '❌'}
							</div>
							<div
								class="mt-2 text-sm transition-colors {$isDarkMode
									? 'text-gray-500'
									: 'text-gray-600'}"
							>
								{analysisData.detected_practices?.uses_centralized_workflows
									? 'Implemented'
									: 'Not detected'}
							</div>
						</div>
					</div>

					<!-- Key Security Practices -->
					<div
						class="rounded-lg p-6 transition-colors {$isDarkMode
							? 'bg-gray-800'
							: 'bg-white shadow-sm'}"
					>
						<h2
							class="mb-4 text-xl font-bold transition-colors {$isDarkMode
								? 'text-white'
								: 'text-gray-900'}"
						>
							🔐 Detected Security Practices
						</h2>

						<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
							<!-- SAST Tools -->
							<div
								class="rounded-lg p-4 transition-colors {$isDarkMode
									? 'bg-gray-700'
									: 'bg-gray-50'}"
							>
								<div
									class="mb-2 font-semibold transition-colors {$isDarkMode
										? 'text-white'
										: 'text-gray-900'}"
								>
									🔍 SAST Tools
								</div>
								{#if analysisData.detected_practices?.sast_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.sast_tools as tool}
											<div
												class="rounded px-2 py-1 text-sm transition-colors {$isDarkMode
													? 'bg-green-900/30 text-green-400'
													: 'bg-green-100 text-green-800'}"
											>
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div
										class="text-sm transition-colors {$isDarkMode
											? 'text-gray-500'
											: 'text-gray-600'}"
									>
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- DAST Tools -->
							<div
								class="rounded-lg p-4 transition-colors {$isDarkMode
									? 'bg-gray-700'
									: 'bg-gray-50'}"
							>
								<div
									class="mb-2 font-semibold transition-colors {$isDarkMode
										? 'text-white'
										: 'text-gray-900'}"
								>
									🎯 DAST Tools
								</div>
								{#if analysisData.detected_practices?.dast_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.dast_tools as tool}
											<div
												class="rounded px-2 py-1 text-sm transition-colors {$isDarkMode
													? 'bg-green-900/30 text-green-400'
													: 'bg-green-100 text-green-800'}"
											>
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div
										class="text-sm transition-colors {$isDarkMode
											? 'text-gray-500'
											: 'text-gray-600'}"
									>
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- SCA Tools -->
							<div
								class="rounded-lg p-4 transition-colors {$isDarkMode
									? 'bg-gray-700'
									: 'bg-gray-50'}"
							>
								<div
									class="mb-2 font-semibold transition-colors {$isDarkMode
										? 'text-white'
										: 'text-gray-900'}"
								>
									📦 SCA Tools
								</div>
								{#if analysisData.detected_practices?.sca_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.sca_tools as tool}
											<div
												class="rounded px-2 py-1 text-sm transition-colors {$isDarkMode
													? 'bg-green-900/30 text-green-400'
													: 'bg-green-100 text-green-800'}"
											>
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div
										class="text-sm transition-colors {$isDarkMode
											? 'text-gray-500'
											: 'text-gray-600'}"
									>
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- Secret Scanning -->
							<div
								class="rounded-lg p-4 transition-colors {$isDarkMode
									? 'bg-gray-700'
									: 'bg-gray-50'}"
							>
								<div
									class="mb-2 font-semibold transition-colors {$isDarkMode
										? 'text-white'
										: 'text-gray-900'}"
								>
									🔑 Secret Scanning
								</div>
								{#if analysisData.detected_practices?.secret_scanning_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.secret_scanning_tools as tool}
											<div
												class="rounded px-2 py-1 text-sm transition-colors {$isDarkMode
													? 'bg-green-900/30 text-green-400'
													: 'bg-green-100 text-green-800'}"
											>
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div
										class="text-sm transition-colors {$isDarkMode
											? 'text-gray-500'
											: 'text-gray-600'}"
									>
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- Container Scanning -->
							<div
								class="rounded-lg p-4 transition-colors {$isDarkMode
									? 'bg-gray-700'
									: 'bg-gray-50'}"
							>
								<div
									class="mb-2 font-semibold transition-colors {$isDarkMode
										? 'text-white'
										: 'text-gray-900'}"
								>
									🐳 Container Scanning
								</div>
								{#if analysisData.detected_practices?.container_scanning_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.container_scanning_tools as tool}
											<div
												class="rounded px-2 py-1 text-sm transition-colors {$isDarkMode
													? 'bg-green-900/30 text-green-400'
													: 'bg-green-100 text-green-800'}"
											>
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div
										class="text-sm transition-colors {$isDarkMode
											? 'text-gray-500'
											: 'text-gray-600'}"
									>
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- Pre-commit Hooks -->
							<div
								class="rounded-lg p-4 transition-colors {$isDarkMode
									? 'bg-gray-700'
									: 'bg-gray-50'}"
							>
								<div
									class="mb-2 font-semibold transition-colors {$isDarkMode
										? 'text-white'
										: 'text-gray-900'}"
								>
									🪝 Pre-commit Hooks
								</div>
								{#if analysisData.detected_practices?.has_precommit_hooks}
									<div class="space-y-1">
										{#each analysisData.detected_practices.precommit_hooks || [] as tool}
											<div
												class="rounded px-2 py-1 text-sm transition-colors {$isDarkMode
													? 'bg-green-900/30 text-green-400'
													: 'bg-green-100 text-green-800'}"
											>
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div
										class="text-sm transition-colors {$isDarkMode
											? 'text-gray-500'
											: 'text-gray-600'}"
									>
										❌ Not configured
									</div>
								{/if}
							</div>
						</div>
					</div>

					<!-- Policy Configuration -->
					<div
						class="rounded-lg p-6 transition-colors {$isDarkMode
							? 'bg-gray-800'
							: 'bg-white shadow-sm'}"
					>
						<h2
							class="mb-4 text-xl font-bold transition-colors {$isDarkMode
								? 'text-white'
								: 'text-gray-900'}"
						>
							📋 Repository Policies
						</h2>

						<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
							<div class="space-y-3">
								<div
									class="flex items-center justify-between rounded-lg p-3 transition-colors {$isDarkMode
										? 'bg-gray-700'
										: 'bg-gray-50'}"
								>
									<span
										class="font-medium transition-colors {$isDarkMode
											? 'text-white'
											: 'text-gray-900'}"
									>
										Branch Protection
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.branch_protection_enabled ? '✅' : '❌'}
									</span>
								</div>

								<div
									class="flex items-center justify-between rounded-lg p-3 transition-colors {$isDarkMode
										? 'bg-gray-700'
										: 'bg-gray-50'}"
								>
									<span
										class="font-medium transition-colors {$isDarkMode
											? 'text-white'
											: 'text-gray-900'}"
									>
										CODEOWNERS File
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.has_codeowners ? '✅' : '❌'}
									</span>
								</div>

								<div
									class="flex items-center justify-between rounded-lg p-3 transition-colors {$isDarkMode
										? 'bg-gray-700'
										: 'bg-gray-50'}"
								>
									<span
										class="font-medium transition-colors {$isDarkMode
											? 'text-white'
											: 'text-gray-900'}"
									>
										Required Reviews
									</span>
									<span
										class="text-xl font-bold transition-colors {$isDarkMode
											? 'text-white'
											: 'text-gray-900'}"
									>
										{analysisData.detected_practices?.required_reviews || 0}
									</span>
								</div>
							</div>

							<div class="space-y-3">
								<div
									class="flex items-center justify-between rounded-lg p-3 transition-colors {$isDarkMode
										? 'bg-gray-700'
										: 'bg-gray-50'}"
								>
									<span
										class="font-medium transition-colors {$isDarkMode
											? 'text-white'
											: 'text-gray-900'}"
									>
										Signed Commits Required
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.signed_commits_required ? '✅' : '❌'}
									</span>
								</div>

								<div
									class="flex items-center justify-between rounded-lg p-3 transition-colors {$isDarkMode
										? 'bg-gray-700'
										: 'bg-gray-50'}"
								>
									<span
										class="font-medium transition-colors {$isDarkMode
											? 'text-white'
											: 'text-gray-900'}"
									>
										Status Checks Required
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.required_status_checks ? '✅' : '❌'}
									</span>
								</div>

								<div
									class="flex items-center justify-between rounded-lg p-3 transition-colors {$isDarkMode
										? 'bg-gray-700'
										: 'bg-gray-50'}"
								>
									<span
										class="font-medium transition-colors {$isDarkMode
											? 'text-white'
											: 'text-gray-900'}"
									>
										PR Workflows
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.has_pr_workflows ? '✅' : '❌'}
									</span>
								</div>
							</div>
						</div>
					</div>

					<!-- Project Breakdown Section (for Unified Analysis) -->
					{#if isUnifiedAnalysis && projectBreakdowns.length > 0}
						<div
							class="rounded-lg p-6 transition-colors {$isDarkMode
								? 'bg-gray-800'
								: 'bg-white shadow-sm'}"
						>
							<h2
								class="mb-4 flex items-center gap-2 text-xl font-bold transition-colors {$isDarkMode
									? 'text-white'
									: 'text-gray-900'}"
							>
								<span>📂 Project Breakdown</span>
								<span
									class="rounded px-3 py-1 text-sm font-normal transition-colors {$isDarkMode
										? 'bg-blue-900/30 text-blue-400'
										: 'bg-blue-100 text-blue-800'}"
								>
									{projectBreakdowns.length}
									{projectBreakdowns.length === 1 ? 'Project' : 'Projects'}
								</span>
							</h2>

							<div class="space-y-4">
								{#each projectBreakdowns as project}
									{@const projectMaturity = project.maturity || {}}
									{@const projectId = project.project_id || project.project_name}
									{@const isExpanded = expandedProjects.has(projectId)}

									<div
										class="rounded-lg border-2 transition-all {$isDarkMode
											? 'bg-gray-750 border-gray-700'
											: 'border-gray-200 bg-gray-50'}"
									>
										<!-- Project Header -->
										<button
											onclick={() => toggleProjectExpansion(projectId)}
											class="flex w-full items-center justify-between p-4 transition-opacity hover:opacity-80"
										>
											<div class="flex flex-1 items-center gap-4">
												<svg
													class="h-8 w-8 transition-colors {$isDarkMode
														? 'text-blue-400'
														: 'text-blue-600'}"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
													/>
												</svg>

												<div class="flex-1 text-left">
													<h3
														class="text-lg font-bold transition-colors {$isDarkMode
															? 'text-white'
															: 'text-gray-900'}"
													>
														{project.project_name}
													</h3>
													<div
														class="mt-1 flex items-center gap-4 text-sm transition-colors {$isDarkMode
															? 'text-gray-400'
															: 'text-gray-600'}"
													>
														<span>📦 {project.repository_count || 0} repositories</span>
														<span>⚙️ {project.workflow_count || 0} workflows</span>
													</div>
												</div>

												<div class="text-right">
													<div
														class="text-3xl font-bold transition-colors {$isDarkMode
															? 'text-green-400'
															: 'text-green-600'}"
													>
														{Math.round(projectMaturity.overall_maturity_score || 0)}
													</div>
													<div
														class="text-xs transition-colors {$isDarkMode
															? 'text-gray-400'
															: 'text-gray-600'}"
													>
														Maturity Score
													</div>
												</div>
											</div>

											<svg
												class="ml-4 h-6 w-6 transition-transform {isExpanded ? 'rotate-180' : ''}"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										</button>

										<!-- Project Details (Expanded) -->
										{#if isExpanded}
											<div
												class="space-y-4 border-t p-4 transition-colors {$isDarkMode
													? 'border-gray-700'
													: 'border-gray-200'}"
											>
												<!-- DSOMM Scores -->
												<div>
													<h4
														class="mb-2 font-semibold transition-colors {$isDarkMode
															? 'text-white'
															: 'text-gray-900'}"
													>
														DSOMM Dimension Scores
													</h4>
													<div class="grid grid-cols-2 gap-2 md:grid-cols-4">
														<div
															class="rounded p-2 transition-colors {$isDarkMode
																? 'bg-gray-700'
																: 'bg-white'}"
														>
															<div
																class="text-xs transition-colors {$isDarkMode
																	? 'text-gray-400'
																	: 'text-gray-600'}"
															>
																Technology
															</div>
															<div
																class="text-lg font-bold transition-colors {$isDarkMode
																	? 'text-blue-400'
																	: 'text-blue-600'}"
															>
																{Math.round(
																	projectMaturity.domain_scores?.technology?.score ||
																		projectMaturity.implementation_score ||
																		0
																)}
															</div>
														</div>
														<div
															class="rounded p-2 transition-colors {$isDarkMode
																? 'bg-gray-700'
																: 'bg-white'}"
														>
															<div
																class="text-xs transition-colors {$isDarkMode
																	? 'text-gray-400'
																	: 'text-gray-600'}"
															>
																Process
															</div>
															<div
																class="text-lg font-bold transition-colors {$isDarkMode
																	? 'text-orange-400'
																	: 'text-orange-600'}"
															>
																{Math.round(
																	projectMaturity.domain_scores?.process?.score ||
																		projectMaturity.build_deployment_score ||
																		0
																)}
															</div>
														</div>
														<div
															class="rounded p-2 transition-colors {$isDarkMode
																? 'bg-gray-700'
																: 'bg-white'}"
														>
															<div
																class="text-xs transition-colors {$isDarkMode
																	? 'text-gray-400'
																	: 'text-gray-600'}"
															>
																Level
															</div>
															<div
																class="text-lg font-bold transition-colors {$isDarkMode
																	? 'text-purple-400'
																	: 'text-purple-600'}"
															>
																{projectMaturity.maturity_level !== undefined
																	? projectMaturity.maturity_level
																	: '—'}
															</div>
														</div>
														<div
															class="rounded p-2 transition-colors {$isDarkMode
																? 'bg-gray-700'
																: 'bg-white'}"
														>
															<div
																class="text-xs transition-colors {$isDarkMode
																	? 'text-gray-400'
																	: 'text-gray-600'}"
															>
																Overall Score
															</div>
															<div
																class="text-lg font-bold transition-colors {$isDarkMode
																	? 'text-green-400'
																	: 'text-green-600'}"
															>
																{Math.round(projectMaturity.overall_maturity_score || 0)}
															</div>
														</div>
													</div>
												</div>

												<!-- Findings Summary -->
												{#if project.findings_count}
													<div>
														<h4
															class="mb-2 font-semibold transition-colors {$isDarkMode
																? 'text-white'
																: 'text-gray-900'}"
														>
															Findings Summary
														</h4>
														<div class="flex flex-wrap gap-2">
															{#if project.findings_count.critical > 0}
																<span
																	class="rounded px-3 py-1 text-sm font-medium"
																	style="background-color: {getSeverityColor(
																		'critical'
																	)}20; color: {getSeverityColor('critical')}"
																>
																	{project.findings_count.critical} Critical
																</span>
															{/if}
															{#if project.findings_count.high > 0}
																<span
																	class="rounded px-3 py-1 text-sm font-medium"
																	style="background-color: {getSeverityColor(
																		'high'
																	)}20; color: {getSeverityColor('high')}"
																>
																	{project.findings_count.high} High
																</span>
															{/if}
															{#if project.findings_count.medium > 0}
																<span
																	class="rounded px-3 py-1 text-sm font-medium"
																	style="background-color: {getSeverityColor(
																		'medium'
																	)}20; color: {getSeverityColor('medium')}"
																>
																	{project.findings_count.medium} Medium
																</span>
															{/if}
															{#if project.findings_count.low > 0}
																<span
																	class="rounded px-3 py-1 text-sm font-medium"
																	style="background-color: {getSeverityColor(
																		'low'
																	)}20; color: {getSeverityColor('low')}"
																>
																	{project.findings_count.low} Low
																</span>
															{/if}
														</div>
													</div>
												{/if}

												<!-- Top Security Tools -->
												{#if project.detected_practices}
													<div>
														<h4
															class="mb-2 font-semibold transition-colors {$isDarkMode
																? 'text-white'
																: 'text-gray-900'}"
														>
															Security Tools Detected
														</h4>
														<div class="flex flex-wrap gap-2">
															{#each (project.detected_practices.sast_tools || []).slice(0, 3) as tool}
																<span
																	class="rounded px-2 py-1 text-xs transition-colors {$isDarkMode
																		? 'bg-green-900/30 text-green-400'
																		: 'bg-green-100 text-green-800'}"
																>
																	🔍 {tool}
																</span>
															{/each}
															{#each (project.detected_practices.sca_tools || []).slice(0, 2) as tool}
																<span
																	class="rounded px-2 py-1 text-xs transition-colors {$isDarkMode
																		? 'bg-blue-900/30 text-blue-400'
																		: 'bg-blue-100 text-blue-800'}"
																>
																	📦 {tool}
																</span>
															{/each}
														</div>
													</div>
												{/if}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{:else if activeTab === 'dsomm'}
				<!-- DSOMM Levels Tab -->
				<div class="space-y-6">
					<!-- DSOMM Level Grid -->
					<div
						class="rounded-lg p-6 transition-colors {$isDarkMode
							? 'bg-gray-800'
							: 'bg-white shadow-sm'}"
					>
						<h2
							class="mb-6 text-xl font-bold transition-colors {$isDarkMode
								? 'text-white'
								: 'text-gray-900'}"
						>
							OWASP DSOMM Maturity Levels
						</h2>

						<div class="overflow-x-auto">
							<table class="w-full border-collapse">
								<thead>
									<tr class="transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-100'}">
										<th
											class="p-4 text-left font-semibold transition-colors {$isDarkMode
												? 'text-white'
												: 'text-gray-900'}"
										>
											Dimension
										</th>
										{#each [0, 1, 2, 3, 4] as level}
											<th
												class="p-4 text-center font-semibold transition-colors {$isDarkMode
													? 'text-white'
													: 'text-gray-900'}"
											>
												Level {level}
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each dsommDimensions as dimension}
										{@const currentLevel = calculateDimensionLevel(
											dimension,
											analysisData.detected_practices
										)}
										<tr
											class="border-t transition-colors {$isDarkMode
												? 'hover:bg-gray-750 border-gray-700'
												: 'border-gray-200 hover:bg-gray-50'}"
										>
											<td class="p-4">
												<div class="flex items-start gap-3">
													<span class="text-2xl">{dimension.icon}</span>
													<div>
														<div
															class="font-semibold transition-colors {$isDarkMode
																? 'text-white'
																: 'text-gray-900'}"
														>
															{dimension.name}
														</div>
														<div
															class="text-sm transition-colors {$isDarkMode
																? 'text-gray-400'
																: 'text-gray-600'}"
														>
															{dimension.description}
														</div>
													</div>
												</div>
											</td>
											{#each [0, 1, 2, 3, 4] as level}
												<td class="p-4 text-center">
													<div class="text-3xl">
														{#if level <= currentLevel}
															{levelConfig[level].emoji}
														{:else}
															⬜
														{/if}
													</div>
												</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>

					<!-- Dimension Details -->
					<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
						{#each dsommDimensions as dimension}
							{@const currentLevel = calculateDimensionLevel(
								dimension,
								analysisData.detected_practices
							)}
							{@const levelInfo = levelConfig[currentLevel]}
							<div
								class="rounded-lg p-6 transition-colors {$isDarkMode
									? 'bg-gray-800'
									: 'bg-white shadow-sm'}"
							>
								<div class="mb-4 flex items-center justify-between">
									<div class="flex items-center gap-3">
										<span class="text-3xl">{dimension.icon}</span>
										<h3
											class="font-bold transition-colors {$isDarkMode
												? 'text-white'
												: 'text-gray-900'}"
										>
											{dimension.name}
										</h3>
									</div>
									<div class="text-right">
										<div class="mb-1 text-3xl">{levelInfo.emoji}</div>
										<div
											class="text-xs font-medium transition-colors {$isDarkMode
												? 'text-gray-400'
												: 'text-gray-600'}"
										>
											Level {currentLevel}
										</div>
									</div>
								</div>

								<!-- Progress bar -->
								<div class="mb-4">
									<div
										class="h-3 overflow-hidden rounded-full transition-colors {$isDarkMode
											? 'bg-gray-700'
											: 'bg-gray-200'}"
									>
										<div
											class="h-full rounded-full transition-all duration-500"
											style="width: {(currentLevel / 4) *
												100}%; background-color: {levelInfo.color}"
										></div>
									</div>
								</div>

								<p
									class="text-sm transition-colors {$isDarkMode
										? 'text-gray-400'
										: 'text-gray-600'}"
								>
									{dimension.description}
								</p>
							</div>
						{/each}
					</div>
				</div>
			{:else if activeTab === 'repositories'}
				<!-- Repositories Tab -->
				<div class="space-y-6">
					{#if isUnifiedAnalysis && projectBreakdowns.length > 0}
						<!-- Unified Analysis: Group by Project -->
						{#each projectBreakdowns as project}
							{@const projectRepos =
								analysisData?.repositories?.filter(
									(r) => r.project_name === project.project_name
								) || []}
							{@const reposWithWorkflows = projectRepos.filter((r) => r.has_workflows !== false)}
							{@const reposWithoutWorkflows = projectRepos.filter((r) => r.has_workflows === false)}

							{#if projectRepos.length > 0}
								<div
									class="overflow-hidden rounded-lg transition-colors {$isDarkMode
										? 'border border-gray-700 bg-gray-800'
										: 'border border-gray-200 bg-white shadow-sm'}"
								>
									<!-- Project Header -->
									<div
										class="p-4 transition-colors {$isDarkMode
											? 'bg-gray-750 border-b border-gray-700'
											: 'border-b border-gray-200 bg-gray-50'}"
									>
										<div class="flex items-center gap-3">
											<svg
												class="h-6 w-6 transition-colors {$isDarkMode
													? 'text-blue-400'
													: 'text-blue-600'}"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
												/>
											</svg>
											<h3
												class="text-lg font-bold transition-colors {$isDarkMode
													? 'text-white'
													: 'text-gray-900'}"
											>
												{project.project_name}
											</h3>
											<span
												class="rounded px-2 py-1 text-sm transition-colors {$isDarkMode
													? 'bg-blue-900/30 text-blue-400'
													: 'bg-blue-100 text-blue-800'}"
											>
												{projectRepos.length} repositories
											</span>
										</div>
									</div>

									<!-- Project Repositories -->
									<div class="p-4">
										{#if reposWithWorkflows.length > 0}
											<div class="mb-6">
												<h4
													class="mb-3 flex items-center gap-2 font-semibold transition-colors {$isDarkMode
														? 'text-white'
														: 'text-gray-900'}"
												>
													<span>🚀 With CI/CD Workflows</span>
													<span
														class="rounded px-2 py-1 text-xs transition-colors {$isDarkMode
															? 'bg-green-900/30 text-green-400'
															: 'bg-green-100 text-green-800'}"
													>
														{reposWithWorkflows.length}
													</span>
												</h4>

												<div class="space-y-3">
													{#each reposWithWorkflows as repo}
														<div
															class="rounded-lg p-3 transition-colors {$isDarkMode
																? 'bg-gray-700'
																: 'bg-gray-50'}"
														>
															<div class="mb-2 flex items-start justify-between">
																<div>
																	<h5
																		class="font-semibold transition-colors {$isDarkMode
																			? 'text-white'
																			: 'text-gray-900'}"
																	>
																		📁 {repo.repository_name}
																	</h5>
																	<div
																		class="text-sm transition-colors {$isDarkMode
																			? 'text-gray-400'
																			: 'text-gray-600'}"
																	>
																		{repo.workflows_analyzed || 0} workflows analyzed
																	</div>
																</div>
																{#if repo.security_score !== null && repo.security_score !== undefined}
																	<div class="text-right">
																		<div
																			class="text-xl font-bold transition-colors {$isDarkMode
																				? 'text-green-400'
																				: 'text-green-600'}"
																		>
																			{Math.round(repo.security_score)}/100
																		</div>
																		<div
																			class="text-xs transition-colors {$isDarkMode
																				? 'text-gray-400'
																				: 'text-gray-600'}"
																		>
																			Score
																		</div>
																	</div>
																{/if}
															</div>

															{#if repo.findings_count}
																<div class="flex flex-wrap gap-2">
																	{#if repo.findings_count.critical > 0}
																		<span
																			class="rounded px-2 py-1 text-xs font-medium"
																			style="background-color: {getSeverityColor(
																				'critical'
																			)}20; color: {getSeverityColor('critical')}"
																		>
																			{repo.findings_count.critical} Critical
																		</span>
																	{/if}
																	{#if repo.findings_count.high > 0}
																		<span
																			class="rounded px-2 py-1 text-xs font-medium"
																			style="background-color: {getSeverityColor(
																				'high'
																			)}20; color: {getSeverityColor('high')}"
																		>
																			{repo.findings_count.high} High
																		</span>
																	{/if}
																	{#if repo.findings_count.medium > 0}
																		<span
																			class="rounded px-2 py-1 text-xs font-medium"
																			style="background-color: {getSeverityColor(
																				'medium'
																			)}20; color: {getSeverityColor('medium')}"
																		>
																			{repo.findings_count.medium} Medium
																		</span>
																	{/if}
																	{#if repo.findings_count.low > 0}
																		<span
																			class="rounded px-2 py-1 text-xs font-medium"
																			style="background-color: {getSeverityColor(
																				'low'
																			)}20; color: {getSeverityColor('low')}"
																		>
																			{repo.findings_count.low} Low
																		</span>
																	{/if}
																</div>
															{/if}
														</div>
													{/each}
												</div>
											</div>
										{/if}

										{#if reposWithoutWorkflows.length > 0}
											<div>
												<h4
													class="mb-3 flex items-center gap-2 font-semibold transition-colors {$isDarkMode
														? 'text-white'
														: 'text-gray-900'}"
												>
													<span>⚠️ Without CI/CD Workflows</span>
													<span
														class="rounded px-2 py-1 text-xs transition-colors {$isDarkMode
															? 'bg-yellow-900/30 text-yellow-400'
															: 'bg-yellow-100 text-yellow-800'}"
													>
														{reposWithoutWorkflows.length}
													</span>
												</h4>

												<div class="space-y-2">
													{#each reposWithoutWorkflows as repo}
														<div
															class="rounded-lg p-3 transition-colors {$isDarkMode
																? 'bg-gray-700'
																: 'bg-gray-50'}"
														>
															<h5
																class="font-semibold transition-colors {$isDarkMode
																	? 'text-white'
																	: 'text-gray-900'}"
															>
																📁 {repo.repository_name}
															</h5>
															<div
																class="mt-1 text-sm transition-colors {$isDarkMode
																	? 'text-gray-400'
																	: 'text-gray-600'}"
															>
																No CI/CD workflows configured
															</div>
														</div>
													{/each}
												</div>
											</div>
										{/if}
									</div>
								</div>
							{/if}
						{/each}
					{:else}
						<!-- Folder Analysis: Flat List -->
						<!-- Repositories WITH workflows -->
						{#if getRepositoriesWithWorkflows().length > 0}
							<div
								class="rounded-lg p-6 transition-colors {$isDarkMode
									? 'bg-gray-800'
									: 'bg-white shadow-sm'}"
							>
								<h2
									class="mb-4 flex items-center gap-2 text-xl font-bold transition-colors {$isDarkMode
										? 'text-white'
										: 'text-gray-900'}"
								>
									<span>🚀 Repositories with CI/CD Workflows</span>
									<span
										class="rounded px-2 py-1 text-sm font-normal transition-colors {$isDarkMode
											? 'bg-green-900/30 text-green-400'
											: 'bg-green-100 text-green-800'}"
									>
										{getRepositoriesWithWorkflows().length}
									</span>
								</h2>

								<div class="space-y-4">
									{#each getRepositoriesWithWorkflows() as repo}
										<div
											class="rounded-lg p-4 transition-colors {$isDarkMode
												? 'bg-gray-700'
												: 'bg-gray-50'}"
										>
											<div class="mb-3 flex items-start justify-between">
												<div>
													<h3
														class="text-lg font-bold transition-colors {$isDarkMode
															? 'text-white'
															: 'text-gray-900'}"
													>
														📁 {repo.repository_name}
													</h3>
													<div
														class="text-sm transition-colors {$isDarkMode
															? 'text-gray-400'
															: 'text-gray-600'}"
													>
														{repo.workflows_analyzed || 0} workflows analyzed
													</div>
												</div>
												{#if repo.security_score !== null && repo.security_score !== undefined}
													<div class="text-right">
														<div
															class="text-2xl font-bold transition-colors {$isDarkMode
																? 'text-green-400'
																: 'text-green-600'}"
														>
															{Math.round(repo.security_score)}/100
														</div>
														<div
															class="text-xs transition-colors {$isDarkMode
																? 'text-gray-400'
																: 'text-gray-600'}"
														>
															Security Score
														</div>
													</div>
												{/if}
											</div>

											<!-- Findings Summary -->
											{#if repo.findings_count}
												<div class="flex flex-wrap gap-2">
													{#if repo.findings_count.critical > 0}
														<span
															class="rounded px-2 py-1 text-xs font-medium"
															style="background-color: {getSeverityColor(
																'critical'
															)}20; color: {getSeverityColor('critical')}"
														>
															{repo.findings_count.critical} Critical
														</span>
													{/if}
													{#if repo.findings_count.high > 0}
														<span
															class="rounded px-2 py-1 text-xs font-medium"
															style="background-color: {getSeverityColor(
																'high'
															)}20; color: {getSeverityColor('high')}"
														>
															{repo.findings_count.high} High
														</span>
													{/if}
													{#if repo.findings_count.medium > 0}
														<span
															class="rounded px-2 py-1 text-xs font-medium"
															style="background-color: {getSeverityColor(
																'medium'
															)}20; color: {getSeverityColor('medium')}"
														>
															{repo.findings_count.medium} Medium
														</span>
													{/if}
													{#if repo.findings_count.low > 0}
														<span
															class="rounded px-2 py-1 text-xs font-medium"
															style="background-color: {getSeverityColor(
																'low'
															)}20; color: {getSeverityColor('low')}"
														>
															{repo.findings_count.low} Low
														</span>
													{/if}
												</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Repositories WITHOUT workflows -->
						{#if getRepositoriesWithoutWorkflows().length > 0}
							<div
								class="rounded-lg p-6 transition-colors {$isDarkMode
									? 'bg-gray-800'
									: 'bg-white shadow-sm'}"
							>
								<h2
									class="mb-4 flex items-center gap-2 text-xl font-bold transition-colors {$isDarkMode
										? 'text-white'
										: 'text-gray-900'}"
								>
									<span>⚠️ Repositories without CI/CD Workflows</span>
									<span
										class="rounded px-2 py-1 text-sm font-normal transition-colors {$isDarkMode
											? 'bg-yellow-900/30 text-yellow-400'
											: 'bg-yellow-100 text-yellow-800'}"
									>
										{getRepositoriesWithoutWorkflows().length}
									</span>
								</h2>

								<div
									class="mb-4 rounded-lg p-4 transition-colors {$isDarkMode
										? 'border border-yellow-800 bg-yellow-900/20'
										: 'border border-yellow-200 bg-yellow-50'}"
								>
									<p
										class="text-sm transition-colors {$isDarkMode
											? 'text-yellow-300'
											: 'text-yellow-800'}"
									>
										ℹ️ These repositories are not included in the overall security score calculation
										since they don't have any GitHub Actions workflows configured.
									</p>
								</div>

								<div class="space-y-4">
									{#each getRepositoriesWithoutWorkflows() as repo}
										<div
											class="rounded-lg p-4 transition-colors {$isDarkMode
												? 'bg-gray-700'
												: 'bg-gray-50'}"
										>
											<h3
												class="text-lg font-bold transition-colors {$isDarkMode
													? 'text-white'
													: 'text-gray-900'}"
											>
												📁 {repo.repository_name}
											</h3>
											<div
												class="mt-2 text-sm transition-colors {$isDarkMode
													? 'text-gray-400'
													: 'text-gray-600'}"
											>
												No CI/CD workflows configured - Consider adding GitHub Actions for automated
												security testing
											</div>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					{/if}
				</div>
			{:else if activeTab === 'findings'}
				<!-- Findings Tab -->
				<div class="space-y-4">
					{#if analysisData.findings && analysisData.findings.length > 0}
						{#each analysisData.findings as finding, idx}
							<div
								class="overflow-hidden rounded-lg transition-colors {$isDarkMode
									? 'border border-gray-700 bg-gray-800'
									: 'border border-gray-200 bg-white shadow-sm'}"
							>
								<button
									onclick={() => toggleFinding(idx)}
									class="flex w-full items-start justify-between p-4 transition-all hover:opacity-80"
								>
									<div class="flex flex-1 items-start gap-4 text-left">
										<span
											class="rounded px-3 py-1 text-sm font-medium uppercase"
											style="background-color: {getSeverityColor(
												finding.severity
											)}20; color: {getSeverityColor(finding.severity)}"
										>
											{finding.severity}
										</span>
										<div class="flex-1">
											<h3
												class="mb-1 font-semibold transition-colors {$isDarkMode
													? 'text-white'
													: 'text-gray-900'}"
											>
												{finding.title}
											</h3>
											<p
												class="text-sm transition-colors {$isDarkMode
													? 'text-gray-400'
													: 'text-gray-600'}"
											>
												{finding.description}
											</p>
										</div>
									</div>
									<span
										class="text-xl transition-transform {expandedFindings.has(idx)
											? 'rotate-180'
											: ''}"
									>
										▼
									</span>
								</button>

								{#if expandedFindings.has(idx)}
									<div
										class="border-t px-4 pb-4 transition-colors {$isDarkMode
											? 'border-gray-700'
											: 'border-gray-200'}"
									>
										<div class="mt-4 space-y-4">
											<div>
												<h4
													class="mb-2 font-semibold transition-colors {$isDarkMode
														? 'text-white'
														: 'text-gray-900'}"
												>
													💡 Recommendation
												</h4>
												<p
													class="text-sm transition-colors {$isDarkMode
														? 'text-gray-300'
														: 'text-gray-700'}"
												>
													{finding.recommendation}
												</p>
											</div>

											{#if finding.affected_component}
												<div>
													<h4
														class="mb-2 font-semibold transition-colors {$isDarkMode
															? 'text-white'
															: 'text-gray-900'}"
													>
														📍 Affected Component
													</h4>
													<code
														class="rounded px-2 py-1 text-sm transition-colors {$isDarkMode
															? 'bg-gray-700 text-gray-300'
															: 'bg-gray-100 text-gray-800'}"
													>
														{finding.affected_component}
													</code>
												</div>
											{/if}
										</div>
									</div>
								{/if}
							</div>
						{/each}
					{:else}
						<div
							class="rounded-lg py-12 text-center transition-colors {$isDarkMode
								? 'bg-gray-800'
								: 'bg-white shadow-sm'}"
						>
							<span class="mb-4 block text-6xl">🎉</span>
							<h3
								class="mb-2 text-xl font-bold transition-colors {$isDarkMode
									? 'text-white'
									: 'text-gray-900'}"
							>
								No Findings
							</h3>
							<p class="transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
								Great! No security issues detected.
							</p>
						</div>
					{/if}
				</div>
			{/if}

			<!-- History Tab -->
			{#if activeTab === 'history'}
				<div class="space-y-4">
					<div class="mb-6 flex items-center justify-between">
						<h2
							class="text-2xl font-bold transition-colors {$isDarkMode
								? 'text-white'
								: 'text-gray-900'}"
						>
							📜 Analysis History
						</h2>
						<div class="transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
							{allAnalyses.length}
							{allAnalyses.length === 1 ? 'analysis' : 'analyses'}
						</div>
					</div>

					{#if allAnalyses.length > 0}
						<div class="space-y-3">
							{#each allAnalyses as analysis (analysis.id)}
								<div
									class="rounded-lg border-2 p-5 transition-all
									{analysis.id === selectedAnalysisId
										? $isDarkMode
											? 'border-blue-500 bg-blue-900/30'
											: 'border-blue-500 bg-blue-50'
										: $isDarkMode
											? 'border-gray-700 bg-gray-800 hover:border-gray-600'
											: 'border-gray-200 bg-white hover:border-gray-300'}"
								>
									<div class="flex items-center justify-between">
										<div class="flex-1">
											<div class="mb-2 flex flex-wrap items-center gap-3">
												<h3
													class="text-lg font-semibold transition-colors {$isDarkMode
														? 'text-white'
														: 'text-gray-900'}"
												>
													{analysis.id === selectedAnalysisId ? '✓ ' : ''}Analysis - {formatDate(
														analysis.created_at
													)}
												</h3>

												{#if analysis.id === selectedAnalysisId}
													<span
														class="rounded-full px-3 py-1 text-xs font-medium transition-colors
														{$isDarkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'}"
													>
														Currently Viewing
													</span>
												{/if}

												<!-- Analysis Type Badge -->
												{#if analysis.analysis_scope === 'unified'}
													<span
														class="rounded-full px-3 py-1 text-xs font-medium transition-colors
														{$isDarkMode
															? 'border border-green-700 bg-green-900/30 text-green-400'
															: 'border border-green-300 bg-green-100 text-green-800'}"
													>
														🌐 Unified Analysis
													</span>
												{:else if analysis.analysis_scope === 'folder'}
													<span
														class="rounded-full px-3 py-1 text-xs font-medium transition-colors
														{$isDarkMode
															? 'border border-blue-700 bg-blue-900/30 text-blue-400'
															: 'border border-blue-300 bg-blue-100 text-blue-800'}"
													>
														📁 Folder Analysis
													</span>
												{:else if analysis.analysis_scope === 'project'}
													<span
														class="rounded-full px-3 py-1 text-xs font-medium transition-colors
														{$isDarkMode
															? 'border border-gray-600 bg-gray-700 text-gray-400'
															: 'border border-gray-300 bg-gray-100 text-gray-700'}"
													>
														📦 Project Analysis
													</span>
												{/if}
											</div>

											<div class="mb-3 grid grid-cols-2 gap-4 md:grid-cols-4">
												<div>
													<div
														class="text-sm transition-colors {$isDarkMode
															? 'text-gray-400'
															: 'text-gray-500'}"
													>
														Repositories
													</div>
													<div
														class="text-xl font-bold transition-colors {$isDarkMode
															? 'text-blue-400'
															: 'text-blue-600'}"
													>
														{analysis.total_repositories || 0}
													</div>
												</div>
												<div>
													<div
														class="text-sm transition-colors {$isDarkMode
															? 'text-gray-400'
															: 'text-gray-500'}"
													>
														Findings
													</div>
													<div
														class="text-xl font-bold transition-colors {$isDarkMode
															? 'text-yellow-400'
															: 'text-yellow-600'}"
													>
														{analysis.findings_count || 0}
													</div>
												</div>
												<div>
													<div
														class="text-sm transition-colors {$isDarkMode
															? 'text-gray-400'
															: 'text-gray-500'}"
													>
														Maturity Score
													</div>
													<div
														class="text-xl font-bold transition-colors {$isDarkMode
															? 'text-green-400'
															: 'text-green-600'}"
													>
														{analysis.maturity_score || 0}%
													</div>
												</div>
												<div>
													<div
														class="text-sm transition-colors {$isDarkMode
															? 'text-gray-400'
															: 'text-gray-500'}"
													>
														Status
													</div>
													<div
														class="text-xl font-bold transition-colors {$isDarkMode
															? 'text-green-400'
															: 'text-green-600'}"
													>
														{analysis.status || 'completed'}
													</div>
												</div>
											</div>

											{#if analysis.project_name}
												<div
													class="flex items-center gap-2 text-sm transition-colors {$isDarkMode
														? 'text-gray-400'
														: 'text-gray-600'}"
												>
													{#if analysis.analysis_scope === 'folder'}
														📂 Folder:
													{:else}
														📦 Project:
													{/if}
													<span class="font-medium">{analysis.project_name}</span>
												</div>
											{/if}
										</div>

										<div class="ml-4 flex items-center gap-2">
											{#if analysis.id !== selectedAnalysisId}
												<button onclick={() => switchToAnalysis(analysis.id)} class="btn-primary">
													View
												</button>
											{/if}

											<button
												onclick={() => deleteAnalysis(analysis.id)}
												disabled={deletingAnalysisId === analysis.id}
												class="btn-delete {deletingAnalysisId === analysis.id ? 'disabled' : ''}"
											>
												{deletingAnalysisId === analysis.id ? '...' : 'Delete'}
											</button>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{:else}
						<div
							class="rounded-lg py-12 text-center transition-colors {$isDarkMode
								? 'bg-gray-800'
								: 'bg-white shadow-sm'}"
						>
							<span class="mb-4 block text-6xl">📭</span>
							<h3
								class="mb-2 text-xl font-bold transition-colors {$isDarkMode
									? 'text-white'
									: 'text-gray-900'}"
							>
								No Analysis History
							</h3>
							<p class="transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
								Run your first analysis to see it here!
							</p>
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
</div>

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
	   PROFESSIONAL WORKSPACE INTELLIGENCE DESIGN
	   Following WithOps Design Pattern
	   ============================================ */

	/* Container */
	.intelligence-container {
		min-height: 100vh;
		width: 100%;
		background: #000000;
		transition: background-color 0.3s ease;
	}

	.intelligence-container.light {
		background: #ffffff;
	}

	/* ============================================
	   NAVIGATION HEADER
	   ============================================ */
	.intelligence-header {
		width: 100%;
		background: #000000;
		border-bottom: 1px solid rgba(0, 217, 255, 0.2);
		padding: 1.5rem 0;
		position: sticky;
		top: 0;
		z-index: 100;
		backdrop-filter: blur(10px);
	}

	.intelligence-container.light .intelligence-header {
		background: #ffffff;
		border-bottom-color: rgba(0, 217, 255, 0.15);
	}

	.header-content {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 2rem;
		padding: 0 3rem;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 2rem;
		flex: 1;
	}

	/* Back Button - Professional Secondary Style */
	.back-button {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		background: transparent;
		color: #00d9ff;
		border: 1px solid rgba(0, 217, 255, 0.4);
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.95rem;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow: none;
	}

	.back-button svg {
		transition: transform 0.3s ease;
	}

	.back-button:hover {
		background: rgba(0, 217, 255, 0.1);
		color: #00d9ff;
		border-color: #00d9ff;
		transform: translateY(-1px);
	}

	.back-button:hover svg {
		transform: translateX(-3px);
	}

	.intelligence-container.light .back-button {
		background: transparent;
		color: #00d9ff;
		border-color: rgba(0, 217, 255, 0.4);
	}

	.intelligence-container.light .back-button:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: #00d9ff;
	}

	/* Title Section */
	.header-title-section {
		flex: 1;
	}

	.page-title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 2rem;
		font-weight: 700;
		color: #ffffff;
		margin-bottom: 0.5rem;
		line-height: 1.2;
	}

	.intelligence-container.light .page-title {
		color: #000000;
	}

	.title-icon {
		font-size: 2rem;
		filter: drop-shadow(0 0 8px rgba(0, 217, 255, 0.5));
	}

	.title-text {
		background: linear-gradient(135deg, #00d9ff 0%, #ffffff 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.intelligence-container.light .title-text {
		background: linear-gradient(135deg, #00d9ff 0%, #00a0c0 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.page-subtitle {
		font-size: 1rem;
		color: #b8b8b8;
		line-height: 1.5;
	}

	.intelligence-container.light .page-subtitle {
		color: #666666;
	}

	.org-name {
		font-weight: 600;
		color: #00d9ff;
	}

	/* Header Actions */
	.header-actions {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}

	/* Maturity Score Display */
	.maturity-score-display {
		text-align: right;
		padding: 1rem 1.5rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
	}

	.score-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #b8b8b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.25rem;
	}

	.intelligence-container.light .score-label {
		color: #666666;
	}

	.score-value {
		font-size: 2.5rem;
		font-weight: 700;
		color: #00d9ff;
		line-height: 1;
	}

	.score-max {
		font-size: 1.5rem;
		color: #b8b8b8;
	}

	/* AI Button - Professional Primary Style with AI Accent */
	.btn-ai {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 1rem 1.5rem;
		background: #ffffff;
		color: #000000;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.95rem;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
		position: relative;
		overflow: hidden;
	}

	.btn-ai::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(99, 102, 241, 0.1) 100%);
		opacity: 0;
		transition: opacity 0.3s ease;
		z-index: 0;
	}

	.btn-ai:hover::before {
		opacity: 1;
	}

	.btn-ai .btn-icon,
	.btn-ai .btn-text {
		position: relative;
		z-index: 1;
	}

	.btn-ai:hover {
		background: #00d9ff;
		color: #000000;
		transform: translateY(-3px);
		box-shadow:
			0 15px 40px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}

	.intelligence-container.light .btn-ai {
		background: #00d9ff;
		color: #000000;
		box-shadow:
			0 8px 25px rgba(0, 217, 255, 0.3),
			0 4px 12px rgba(0, 217, 255, 0.15);
	}

	.intelligence-container.light .btn-ai:hover {
		background: #00d9ff;
		box-shadow:
			0 12px 32px rgba(0, 217, 255, 0.5),
			0 6px 16px rgba(0, 217, 255, 0.25);
		transform: translateY(-3px);
	}

	/* Primary Button */
	.btn-primary {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 1rem 1.5rem;
		background: #ffffff;
		color: #000000;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.95rem;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
	}

	.intelligence-container.light .btn-primary {
		background: #00d9ff;
		box-shadow:
			0 8px 25px rgba(0, 217, 255, 0.3),
			0 4px 12px rgba(0, 217, 255, 0.15);
	}

	.btn-primary:hover {
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
		background: #00d9ff;
		color: #000000;
	}

	.intelligence-container.light .btn-primary:hover {
		background: #33e3ff;
		box-shadow: 0 12px 32px rgba(0, 217, 255, 0.4);
	}

	.btn-icon {
		font-size: 1.25rem;
	}

	.btn-text {
		font-weight: 600;
	}

	/* Delete Button - Professional Pattern */
	.btn-delete {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 1rem 1.5rem;
		background: rgba(239, 68, 68, 0.1);
		color: #ef4444;
		border: 2px solid #ef4444;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.95rem;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow:
			0 10px 30px rgba(239, 68, 68, 0.2),
			0 0 20px rgba(239, 68, 68, 0.1);
	}

	.btn-delete:hover:not(.disabled) {
		background: #ef4444;
		color: #ffffff;
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(239, 68, 68, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}

	.btn-delete.disabled {
		opacity: 0.5;
		cursor: not-allowed;
		transform: none;
	}

	.intelligence-container.light .btn-delete {
		background: rgba(239, 68, 68, 0.08);
		border-color: #dc2626;
		color: #dc2626;
		box-shadow: 0 4px 16px rgba(239, 68, 68, 0.15);
	}

	.intelligence-container.light .btn-delete:hover:not(.disabled) {
		background: #ef4444;
		color: #ffffff;
		box-shadow: 0 12px 32px rgba(239, 68, 68, 0.3);
	}

	/* ============================================
	   MAIN CONTENT
	   ============================================ */
	.main-content {
		padding: 3rem;
	}

	/* ============================================
	   LOADING STATE
	   ============================================ */
	.loading-state {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		padding: 4rem 2rem;
	}

	.loading-content {
		text-align: center;
	}

	.loading-spinner {
		width: 64px;
		height: 64px;
		border: 4px solid rgba(0, 217, 255, 0.1);
		border-top-color: #00d9ff;
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin: 0 auto 1.5rem;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-text {
		font-size: 1.125rem;
		color: #b8b8b8;
		font-weight: 500;
	}

	.intelligence-container.light .loading-text {
		color: #666666;
	}

	/* ============================================
	   ERROR STATE
	   ============================================ */
	.error-state {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		padding: 4rem 2rem;
	}

	.error-content {
		text-align: center;
		max-width: 600px;
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(239, 68, 68, 0.3);
		border-radius: 12px;
		padding: 3rem;
	}

	.intelligence-container.light .error-content {
		background: rgba(255, 255, 255, 0.95);
		border-color: rgba(239, 68, 68, 0.2);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
	}

	.error-icon {
		font-size: 4rem;
		display: block;
		margin-bottom: 1.5rem;
	}

	.error-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: #ef4444;
		margin-bottom: 1rem;
	}

	.error-message {
		font-size: 1rem;
		color: #b8b8b8;
		margin-bottom: 2rem;
		line-height: 1.6;
	}

	.intelligence-container.light .error-message {
		color: #666666;
	}

	/* ============================================
	   EMPTY STATE
	   ============================================ */
	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		padding: 4rem 2rem;
	}

	.empty-content {
		text-align: center;
		max-width: 600px;
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		padding: 3rem;
	}

	.intelligence-container.light .empty-content {
		background: rgba(255, 255, 255, 0.95);
		border-color: rgba(0, 217, 255, 0.15);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
	}

	.empty-icon {
		font-size: 4rem;
		display: block;
		margin-bottom: 1.5rem;
	}

	.empty-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: #00d9ff;
		margin-bottom: 1rem;
	}

	.empty-message {
		font-size: 1rem;
		color: #b8b8b8;
		margin-bottom: 2rem;
		line-height: 1.6;
	}

	.intelligence-container.light .empty-message {
		color: #666666;
	}

	/* ============================================
	   TAB NAVIGATION
	   ============================================ */
	.tab-navigation {
		margin-bottom: 2.5rem;
		border-bottom: 1px solid rgba(0, 217, 255, 0.2);
	}

	.intelligence-container.light .tab-navigation {
		border-bottom-color: rgba(0, 217, 255, 0.15);
	}

	.tab-nav {
		display: flex;
		gap: 0.5rem;
		margin-bottom: -1px;
	}

	.tab-button {
		padding: 1rem 2rem;
		background: transparent;
		border: none;
		border-bottom: 3px solid transparent;
		color: #b8b8b8;
		font-size: 0.95rem;
		font-weight: 600;
		text-transform: capitalize;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
	}

	.intelligence-container.light .tab-button {
		color: #666666;
	}

	.tab-button:hover {
		color: #00d9ff;
		background: rgba(0, 217, 255, 0.05);
	}

	.tab-button.active {
		color: #00d9ff;
		border-bottom-color: #00d9ff;
		background: rgba(0, 217, 255, 0.1);
	}

	/* ============================================
	   RESPONSIVE DESIGN
	   ============================================ */
	@media (max-width: 1200px) {
		.header-content {
			flex-wrap: wrap;
		}

		.header-actions {
			width: 100%;
			justify-content: flex-start;
		}
	}

	@media (max-width: 768px) {
		.header-content {
			padding: 0 1rem;
		}

		.header-left {
			flex-direction: column;
			align-items: flex-start;
			gap: 1rem;
		}

		.header-actions {
			flex-direction: column;
			width: 100%;
			align-items: stretch;
		}

		.maturity-score-display {
			text-align: center;
		}

		.btn-ai,
		.btn-primary {
			width: 100%;
			justify-content: center;
		}

		.page-title {
			font-size: 1.5rem;
		}

		.page-subtitle {
			font-size: 0.875rem;
		}

		.main-content {
			padding: 2rem 1rem;
		}

		.tab-nav {
			overflow-x: auto;
			-webkit-overflow-scrolling: touch;
		}

		.tab-button {
			padding: 0.75rem 1.5rem;
			white-space: nowrap;
		}
	}

	@media (max-width: 480px) {
		.back-button {
			padding: 0.5rem 1rem;
			font-size: 0.875rem;
		}

		.score-value {
			font-size: 2rem;
		}

		.score-max {
			font-size: 1.25rem;
		}
	}

	/* Custom Scrollbar */
	::-webkit-scrollbar {
		width: 12px;
		height: 12px;
	}

	::-webkit-scrollbar-track {
		background: rgba(0, 0, 0, 0.3);
	}

	::-webkit-scrollbar-thumb {
		background: rgba(0, 217, 255, 0.3);
		border-radius: 6px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: rgba(0, 217, 255, 0.5);
	}

	.intelligence-container.light ::-webkit-scrollbar-track {
		background: rgba(0, 0, 0, 0.05);
	}

	.intelligence-container.light ::-webkit-scrollbar-thumb {
		background: rgba(0, 217, 255, 0.3);
	}

	.intelligence-container.light ::-webkit-scrollbar-thumb:hover {
		background: rgba(0, 217, 255, 0.5);
	}

	/* ============================================
	   CONTENT CARDS & BLOCKS - Professional Pattern
	   ============================================ */

	/* Professional Feature Card */
	.dashboard-card,
	div[class*='rounded-lg p-6'] {
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		padding: 2.5rem;
		transition: all 0.4s ease;
		position: relative;
		overflow: hidden;
	}

	.intelligence-container.light .dashboard-card,
	.intelligence-container.light div[class*='rounded-lg p-6'] {
		background: rgba(255, 255, 255, 0.95);
		border-color: rgba(0, 217, 255, 0.15);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
	}

	.dashboard-card::before,
	div[class*='rounded-lg p-6']::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		transition: left 0.6s;
	}

	.dashboard-card:hover::before,
	div[class*='rounded-lg p-6']:hover::before {
		left: 100%;
	}

	.dashboard-card:hover,
	div[class*='rounded-lg p-6']:hover {
		transform: translateY(-5px);
		border-color: rgba(0, 217, 255, 0.5);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.15);
		background: rgba(0, 0, 0, 0.6);
	}

	.intelligence-container.light .dashboard-card:hover,
	.intelligence-container.light div[class*='rounded-lg p-6']:hover {
		background: rgba(255, 255, 255, 1);
		border-color: rgba(0, 217, 255, 0.3);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.12);
	}

	/* Stat Card Specific Styling */
	:global(.stat-card) {
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		padding: 1.5rem;
		transition: all 0.3s ease;
	}

	.intelligence-container.light :global(.stat-card) {
		background: rgba(255, 255, 255, 0.95);
		border-color: rgba(0, 217, 255, 0.15);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
	}

	:global(.stat-card:hover) {
		transform: translateY(-3px);
		border-color: rgba(0, 217, 255, 0.4);
		box-shadow: 0 10px 25px rgba(0, 217, 255, 0.15);
	}

	:global(.stat-label) {
		font-size: 0.875rem;
		font-weight: 600;
		color: #b8b8b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.75rem;
	}

	.intelligence-container.light :global(.stat-label) {
		color: #666666;
	}

	:global(.stat-value) {
		font-size: 2.5rem;
		font-weight: 700;
		color: #ffffff;
		line-height: 1;
		margin-bottom: 0.5rem;
	}

	.intelligence-container.light :global(.stat-value) {
		color: #000000;
	}

	:global(.stat-detail) {
		font-size: 0.875rem;
		color: #b8b8b8;
		line-height: 1.5;
	}

	.intelligence-container.light :global(.stat-detail) {
		color: #666666;
	}

	/* ============================================
	   BADGES & SEVERITY INDICATORS
	   ============================================ */

	/* Professional Badge Styling */
	:global(.badge),
	:global(.status-badge) {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 600;
		transition: all 0.3s ease;
	}

	/* Severity Badge Coloring */
	:global(.severity-critical) {
		background: rgba(220, 38, 38, 0.1);
		color: #dc2626;
		border: 1px solid rgba(220, 38, 38, 0.3);
	}

	:global(.severity-high) {
		background: rgba(234, 88, 12, 0.1);
		color: #ea580c;
		border: 1px solid rgba(234, 88, 12, 0.3);
	}

	:global(.severity-medium) {
		background: rgba(217, 119, 6, 0.1);
		color: #d97706;
		border: 1px solid rgba(217, 119, 6, 0.3);
	}

	:global(.severity-low) {
		background: rgba(101, 163, 13, 0.1);
		color: #65a30d;
		border: 1px solid rgba(101, 163, 13, 0.3);
	}

	:global(.severity-info) {
		background: rgba(2, 132, 199, 0.1);
		color: #0284c7;
		border: 1px solid rgba(2, 132, 199, 0.3);
	}

	/* Status Badges */
	:global(.badge-success) {
		background: rgba(0, 217, 255, 0.1);
		color: #00d9ff;
		border: 1px solid rgba(0, 217, 255, 0.3);
	}

	:global(.badge-warning) {
		background: rgba(245, 158, 11, 0.1);
		color: #f59e0b;
		border: 1px solid rgba(245, 158, 11, 0.3);
	}

	:global(.badge-unified) {
		background: rgba(16, 185, 129, 0.1);
		color: #10b981;
		border: 1px solid rgba(16, 185, 129, 0.3);
	}

	/* ============================================
	   TEXT & TYPOGRAPHY
	   ============================================ */

	:global(h1),
	:global(h2),
	:global(h3),
	:global(h4),
	:global(h5),
	:global(h6) {
		color: #ffffff;
		font-weight: 700;
	}

	.intelligence-container.light :global(h1),
	.intelligence-container.light :global(h2),
	.intelligence-container.light :global(h3),
	.intelligence-container.light :global(h4),
	.intelligence-container.light :global(h5),
	.intelligence-container.light :global(h6) {
		color: #000000;
	}

	:global(p) {
		color: #b8b8b8;
		line-height: 1.6;
	}

	.intelligence-container.light :global(p) {
		color: #666666;
	}

	/* Secondary Text */
	:global(.text-secondary) {
		color: #b8b8b8 !important;
	}

	.intelligence-container.light :global(.text-secondary) {
		color: #666666 !important;
	}

	/* Muted Text */
	:global(.text-muted) {
		color: rgba(255, 255, 255, 0.6) !important;
	}

	.intelligence-container.light :global(.text-muted) {
		color: rgba(0, 0, 0, 0.5) !important;
	}

	/* ============================================
	   UTILITY CLASSES
	   ============================================ */

	:global(.space-y-4 > * + *) {
		margin-top: 1rem;
	}

	:global(.space-y-6 > * + *) {
		margin-top: 1.5rem;
	}

	:global(.grid) {
		display: grid;
	}

	:global(.gap-4) {
		gap: 1rem;
	}

	:global(.gap-6) {
		gap: 1.5rem;
	}

	/* ============================================
	   ANIMATIONS
	   ============================================ */

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateX(-20px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	@keyframes shimmer {
		0% {
			background-position: -1000px 0;
		}
		100% {
			background-position: 1000px 0;
		}
	}

	:global(.animate-fade-in) {
		animation: fadeIn 0.5s ease-out;
	}

	:global(.animate-slide-in) {
		animation: slideIn 0.5s ease-out;
	}
</style>
