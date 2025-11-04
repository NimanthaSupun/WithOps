<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isDarkMode } from '$lib/stores';
	
	const org = $page.params.org;
	const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
	
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
	
	// UI State
	let selectedRepository = null;
	let expandedFindings = new Set();
	
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
					'Authorization': `Bearer ${token}`,
					'Content-Type': 'application/json'
				}
			});
			
			if (!treeResponse.ok) {
				throw new Error('Failed to fetch repository tree. Please ensure you have accessed the repository tree view first.');
			}
			
			const treeResult = await treeResponse.json();
			console.log('📦 Tree result fetched:', treeResult);
			
			// Extract tree data and ID from response
			const treeData = treeResult.data || [];
			const repositoryTreeId = treeResult.metadata?.id;
			
			if (!repositoryTreeId) {
				throw new Error('No repository tree ID found. Please access the repository tree view first to create your workspace structure.');
			}
			
			console.log('📋 Tree ID:', repositoryTreeId, 'Tree data items:', treeData.length);
			
			// Trigger analysis
			const analyzeResponse = await fetch(`${API_BASE_URL}/api/workspace-intelligence/analyze-workspace`, {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${token}`,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					organization_name: org,
					tree_data: treeData,
					repository_tree_id: repositoryTreeId,
					fetch_github_data: true
				})
			});
			
			if (!analyzeResponse.ok) {
				const errorData = await analyzeResponse.json();
				throw new Error(errorData.detail || 'Failed to trigger analysis');
			}
			
			console.log('✅ Analysis triggered successfully');
			
			// Wait a moment then fetch results
			await new Promise(resolve => setTimeout(resolve, 2000));
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
			const response = await fetch(`${API_BASE_URL}/api/workspace-intelligence/organization/${org}`, {
				headers: {
					'Authorization': `Bearer ${token}`,
					'Content-Type': 'application/json'
				}
			});
			
			console.log('📊 API Response status:', response.status);
			
			if (!response.ok) {
				const errorText = await response.text();
				console.error('❌ API Error:', response.status, errorText);
				throw new Error(`Failed to fetch analysis: ${response.statusText}`);
			}
			
			const data = await response.json();
			console.log('✅ Analysis data received:', data);
			
			if (data.analyses && data.analyses.length > 0) {
				// Get the most recent analysis
				const latestAnalysis = data.analyses[0];
				
				// Fetch detailed analysis data
				const detailResponse = await fetch(
					`${API_BASE_URL}/api/workspace-intelligence/analysis/${latestAnalysis.id}`,
					{
						headers: {
							'Authorization': `Bearer ${token}`,
							'Content-Type': 'application/json'
						}
					}
				);
				
				if (detailResponse.ok) {
					const detailData = await detailResponse.json();
					console.log('📋 Detailed analysis response:', detailData);
					analysisData = detailData.analysis || detailData; // Handle nested structure
					console.log('📦 Final analysisData:', analysisData);
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
				return practices.repos_with_workflows > 0 ? 
					(practices.uses_centralized_workflows ? 2 : 1) : 0;
			
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
		if (!practices) return 0;
		
		const dimensions = dsommDimensions.map(d => calculateDimensionLevel(d, practices));
		const total = dimensions.reduce((sum, level) => sum + level, 0);
		const max = dimensions.length * 4; // Max level is 4
		
		return Math.round((total / max) * 100);
	}
	
	function getRepositoriesWithWorkflows() {
		if (!analysisData?.repositories) return [];
		return analysisData.repositories.filter(r => r.has_workflows !== false);
	}
	
	function getRepositoriesWithoutWorkflows() {
		if (!analysisData?.repositories) return [];
		return analysisData.repositories.filter(r => r.has_workflows === false);
	}
</script>

<svelte:head>
	<title>Workspace Intelligence - {org}</title>
</svelte:head>

<div class="min-h-screen w-full transition-colors duration-200 {$isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}">
	<!-- Header -->
	<div class="w-full border-b transition-colors {$isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}">
		<div class="max-w-full px-8 py-6">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<button
						on:click={() => goto(`/github/workspace/${org}/repo-treeview`)}
						class="px-4 py-2 rounded-lg font-medium transition-all hover:scale-105
							{$isDarkMode 
								? 'bg-gray-700 hover:bg-gray-600 text-white' 
								: 'bg-gray-200 hover:bg-gray-300 text-gray-900'}"
					>
						← Back
					</button>
					<div>
						<h1 class="text-3xl font-bold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
							🧠 Workspace Intelligence
						</h1>
						<p class="mt-2 text-lg transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
							OWASP DSOMM Security Maturity Assessment for <span class="font-semibold">{org}</span>
						</p>
					</div>
				</div>
				
				{#if !loading && analysisData}
					<div class="flex items-center gap-4">
						<div class="text-right">
							<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
								Overall Maturity Score
							</div>
							<div class="text-4xl font-bold transition-colors {$isDarkMode ? 'text-green-400' : 'text-green-600'}">
								{getOverallScore(analysisData.detected_practices)}<span class="text-2xl">/100</span>
							</div>
						</div>
						<button
							on:click={triggerNewAnalysis}
							class="px-4 py-2 rounded-lg font-medium transition-all hover:scale-105
								{$isDarkMode 
									? 'bg-blue-600 hover:bg-blue-700 text-white' 
									: 'bg-blue-500 hover:bg-blue-600 text-white'}"
						>
							🔄 Analyze Now
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="max-w-full px-8 py-6">
		{#if loading}
			<div class="flex items-center justify-center py-20">
				<div class="text-center">
					<div class="animate-spin rounded-full h-16 w-16 border-b-2 mx-auto mb-4
						{$isDarkMode ? 'border-blue-400' : 'border-blue-600'}">
					</div>
					<p class="text-lg transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
						Loading workspace intelligence...
					</p>
				</div>
			</div>
		{:else if error && !error.includes('No analysis')}
			<div class="rounded-lg p-8 transition-colors {$isDarkMode ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}">
				<div class="flex flex-col items-center gap-4 text-center">
					<span class="text-6xl">⚠️</span>
					<div>
						<h3 class="font-semibold text-xl mb-2 transition-colors {$isDarkMode ? 'text-red-400' : 'text-red-800'}">
							{error.includes('Authentication') ? '🔐 Authentication Required' : 'Error Loading Analysis'}
						</h3>
						<p class="transition-colors mb-4 {$isDarkMode ? 'text-red-300' : 'text-red-700'}">
							{error}
						</p>
						{#if error.includes('Authentication')}
							<button
								on:click={() => goto('/github/login')}
								class="px-6 py-3 rounded-lg font-medium transition-all hover:scale-105
									{$isDarkMode 
										? 'bg-blue-600 hover:bg-blue-700 text-white' 
										: 'bg-blue-500 hover:bg-blue-600 text-white'}"
							>
								Go to Login
							</button>
						{:else}
							<button
								on:click={fetchAnalysis}
								class="px-6 py-3 rounded-lg font-medium transition-all hover:scale-105
									{$isDarkMode 
										? 'bg-blue-600 hover:bg-blue-700 text-white' 
										: 'bg-blue-500 hover:bg-blue-600 text-white'}"
							>
								Try Again
							</button>
						{/if}
					</div>
				</div>
			</div>
		{:else if !analysisData || error?.includes('No analysis')}
			<div class="rounded-lg p-8 transition-colors {$isDarkMode ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}">
				<div class="flex flex-col items-center gap-4 text-center">
					<span class="text-6xl">🧠</span>
					<div>
						<h3 class="font-semibold text-xl mb-2 transition-colors {$isDarkMode ? 'text-blue-400' : 'text-blue-800'}">
							No Analysis Found
						</h3>
						<p class="transition-colors mb-4 {$isDarkMode ? 'text-blue-300' : 'text-blue-700'}">
							No workspace intelligence data is available yet. Click below to run your first analysis!
						</p>
						<button
							on:click={triggerNewAnalysis}
							class="px-6 py-3 rounded-lg font-medium transition-all hover:scale-105
								{$isDarkMode 
									? 'bg-blue-600 hover:bg-blue-700 text-white' 
									: 'bg-blue-500 hover:bg-blue-600 text-white'}"
						>
							🚀 Run Analysis Now
						</button>
					</div>
				</div>
			</div>
		{:else if analysisData}
			<!-- Tab Navigation -->
			<div class="mb-6 border-b transition-colors {$isDarkMode ? 'border-gray-700' : 'border-gray-200'}">
				<nav class="flex gap-2 -mb-px">
					{#each ['overview', 'dsomm', 'repositories', 'findings'] as tab}
						<button
							on:click={() => activeTab = tab}
							class="px-6 py-3 font-medium border-b-2 transition-all capitalize
								{activeTab === tab
									? $isDarkMode
										? 'border-blue-400 text-blue-400'
										: 'border-blue-600 text-blue-600'
									: $isDarkMode
										? 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
										: 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
								}"
						>
							{tab === 'dsomm' ? 'DSOMM Levels' : tab}
						</button>
					{/each}
				</nav>
			</div>

			<!-- Tab Content -->
			{#if activeTab === 'overview'}
				<!-- Overview Tab -->
				<div class="space-y-6">
					<!-- Quick Stats -->
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
						<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
							<div class="text-sm font-medium mb-2 transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
								Total Repositories
							</div>
							<div class="text-3xl font-bold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
								{analysisData.detected_practices?.total_repos || 0}
							</div>
							<div class="mt-2 text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
								{analysisData.detected_practices?.repos_with_workflows || 0} with CI/CD workflows
							</div>
						</div>

						<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
							<div class="text-sm font-medium mb-2 transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
								Security Tools
							</div>
							<div class="text-3xl font-bold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
								{(analysisData.detected_practices?.sast_tools?.length || 0) +
								 (analysisData.detected_practices?.sca_tools?.length || 0) +
								 (analysisData.detected_practices?.dast_tools?.length || 0) +
								 (analysisData.detected_practices?.secret_scanning_tools?.length || 0) +
								 (analysisData.detected_practices?.container_scanning_tools?.length || 0)}
							</div>
							<div class="mt-2 text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
								Detected across all repos
							</div>
						</div>

						<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
							<div class="text-sm font-medium mb-2 transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
								Total Findings
							</div>
							<div class="text-3xl font-bold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
								{analysisData.findings_count?.critical + analysisData.findings_count?.high + 
								 analysisData.findings_count?.medium + analysisData.findings_count?.low || 0}
							</div>
							<div class="mt-2 flex gap-2 text-xs">
								<span class="px-2 py-1 rounded" style="background-color: {getSeverityColor('critical')}20; color: {getSeverityColor('critical')}">
									{analysisData.findings_count?.critical || 0} Critical
								</span>
								<span class="px-2 py-1 rounded" style="background-color: {getSeverityColor('high')}20; color: {getSeverityColor('high')}">
									{analysisData.findings_count?.high || 0} High
								</span>
							</div>
						</div>

						<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
							<div class="text-sm font-medium mb-2 transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
								Centralized Workflows
							</div>
							<div class="text-3xl font-bold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
								{analysisData.detected_practices?.uses_centralized_workflows ? '✅' : '❌'}
							</div>
							<div class="mt-2 text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
								{analysisData.detected_practices?.uses_centralized_workflows ? 'Implemented' : 'Not detected'}
							</div>
						</div>
					</div>

					<!-- Key Security Practices -->
					<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
						<h2 class="text-xl font-bold mb-4 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
							🔐 Detected Security Practices
						</h2>
						
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
							<!-- SAST Tools -->
							<div class="p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
								<div class="font-semibold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
									🔍 SAST Tools
								</div>
								{#if analysisData.detected_practices?.sast_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.sast_tools as tool}
											<div class="text-sm px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'}">
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- DAST Tools -->
							<div class="p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
								<div class="font-semibold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
									🎯 DAST Tools
								</div>
								{#if analysisData.detected_practices?.dast_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.dast_tools as tool}
											<div class="text-sm px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'}">
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- SCA Tools -->
							<div class="p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
								<div class="font-semibold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
									📦 SCA Tools
								</div>
								{#if analysisData.detected_practices?.sca_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.sca_tools as tool}
											<div class="text-sm px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'}">
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- Secret Scanning -->
							<div class="p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
								<div class="font-semibold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
									🔑 Secret Scanning
								</div>
								{#if analysisData.detected_practices?.secret_scanning_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.secret_scanning_tools as tool}
											<div class="text-sm px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'}">
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- Container Scanning -->
							<div class="p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
								<div class="font-semibold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
									🐳 Container Scanning
								</div>
								{#if analysisData.detected_practices?.container_scanning_tools?.length > 0}
									<div class="space-y-1">
										{#each analysisData.detected_practices.container_scanning_tools as tool}
											<div class="text-sm px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'}">
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
										❌ Not configured
									</div>
								{/if}
							</div>

							<!-- Pre-commit Hooks -->
							<div class="p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
								<div class="font-semibold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
									🪝 Pre-commit Hooks
								</div>
								{#if analysisData.detected_practices?.has_precommit_hooks}
									<div class="space-y-1">
										{#each analysisData.detected_practices.precommit_hooks || [] as tool}
											<div class="text-sm px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'}">
												✅ {tool}
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-500' : 'text-gray-600'}">
										❌ Not configured
									</div>
								{/if}
							</div>
						</div>
					</div>

					<!-- Policy Configuration -->
					<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
						<h2 class="text-xl font-bold mb-4 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
							📋 Repository Policies
						</h2>
						
						<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
							<div class="space-y-3">
								<div class="flex items-center justify-between p-3 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
									<span class="font-medium transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
										Branch Protection
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.branch_protection_enabled ? '✅' : '❌'}
									</span>
								</div>

								<div class="flex items-center justify-between p-3 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
									<span class="font-medium transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
										CODEOWNERS File
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.has_codeowners ? '✅' : '❌'}
									</span>
								</div>

								<div class="flex items-center justify-between p-3 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
									<span class="font-medium transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
										Required Reviews
									</span>
									<span class="font-bold text-xl transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
										{analysisData.detected_practices?.required_reviews || 0}
									</span>
								</div>
							</div>

							<div class="space-y-3">
								<div class="flex items-center justify-between p-3 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
									<span class="font-medium transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
										Signed Commits Required
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.signed_commits_required ? '✅' : '❌'}
									</span>
								</div>

								<div class="flex items-center justify-between p-3 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
									<span class="font-medium transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
										Status Checks Required
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.required_status_checks ? '✅' : '❌'}
									</span>
								</div>

								<div class="flex items-center justify-between p-3 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
									<span class="font-medium transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
										PR Workflows
									</span>
									<span class="text-2xl">
										{analysisData.detected_practices?.has_pr_workflows ? '✅' : '❌'}
									</span>
								</div>
							</div>
						</div>
					</div>
				</div>

			{:else if activeTab === 'dsomm'}
				<!-- DSOMM Levels Tab -->
				<div class="space-y-6">
					<!-- DSOMM Level Grid -->
					<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
						<h2 class="text-xl font-bold mb-6 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
							OWASP DSOMM Maturity Levels
						</h2>
						
						<div class="overflow-x-auto">
							<table class="w-full border-collapse">
								<thead>
									<tr class="transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-100'}">
										<th class="text-left p-4 font-semibold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
											Dimension
										</th>
										{#each [0, 1, 2, 3, 4] as level}
											<th class="text-center p-4 font-semibold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
												Level {level}
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each dsommDimensions as dimension}
										{@const currentLevel = calculateDimensionLevel(dimension, analysisData.detected_practices)}
										<tr class="border-t transition-colors {$isDarkMode ? 'border-gray-700 hover:bg-gray-750' : 'border-gray-200 hover:bg-gray-50'}">
											<td class="p-4">
												<div class="flex items-start gap-3">
													<span class="text-2xl">{dimension.icon}</span>
													<div>
														<div class="font-semibold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
															{dimension.name}
														</div>
														<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
															{dimension.description}
														</div>
													</div>
												</div>
											</td>
											{#each [0, 1, 2, 3, 4] as level}
												<td class="text-center p-4">
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
					<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
						{#each dsommDimensions as dimension}
							{@const currentLevel = calculateDimensionLevel(dimension, analysisData.detected_practices)}
							{@const levelInfo = levelConfig[currentLevel]}
							<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
								<div class="flex items-center justify-between mb-4">
									<div class="flex items-center gap-3">
										<span class="text-3xl">{dimension.icon}</span>
										<h3 class="font-bold transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
											{dimension.name}
										</h3>
									</div>
									<div class="text-right">
										<div class="text-3xl mb-1">{levelInfo.emoji}</div>
										<div class="text-xs font-medium transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
											Level {currentLevel}
										</div>
									</div>
								</div>
								
								<!-- Progress bar -->
								<div class="mb-4">
									<div class="h-3 rounded-full overflow-hidden transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-200'}">
										<div 
											class="h-full rounded-full transition-all duration-500"
											style="width: {(currentLevel / 4) * 100}%; background-color: {levelInfo.color}"
										></div>
									</div>
								</div>
								
								<p class="text-sm transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
									{dimension.description}
								</p>
							</div>
						{/each}
					</div>
				</div>

			{:else if activeTab === 'repositories'}
				<!-- Repositories Tab -->
				<div class="space-y-6">
					<!-- Repositories WITH workflows -->
					{#if getRepositoriesWithWorkflows().length > 0}
						<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
							<h2 class="text-xl font-bold mb-4 flex items-center gap-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
								<span>🚀 Repositories with CI/CD Workflows</span>
								<span class="text-sm font-normal px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'}">
									{getRepositoriesWithWorkflows().length}
								</span>
							</h2>
							
							<div class="space-y-4">
								{#each getRepositoriesWithWorkflows() as repo}
									<div class="p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
										<div class="flex items-start justify-between mb-3">
											<div>
												<h3 class="font-bold text-lg transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
													📁 {repo.repository_name}
												</h3>
												<div class="text-sm transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
													{repo.workflows_analyzed || 0} workflows analyzed
												</div>
											</div>
											{#if repo.security_score !== null && repo.security_score !== undefined}
												<div class="text-right">
													<div class="text-2xl font-bold transition-colors {$isDarkMode ? 'text-green-400' : 'text-green-600'}">
														{Math.round(repo.security_score)}/100
													</div>
													<div class="text-xs transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
														Security Score
													</div>
												</div>
											{/if}
										</div>
										
										<!-- Findings Summary -->
										{#if repo.findings_count}
											<div class="flex gap-2 flex-wrap">
												{#if repo.findings_count.critical > 0}
													<span class="px-2 py-1 rounded text-xs font-medium" 
														style="background-color: {getSeverityColor('critical')}20; color: {getSeverityColor('critical')}">
														{repo.findings_count.critical} Critical
													</span>
												{/if}
												{#if repo.findings_count.high > 0}
													<span class="px-2 py-1 rounded text-xs font-medium" 
														style="background-color: {getSeverityColor('high')}20; color: {getSeverityColor('high')}">
														{repo.findings_count.high} High
													</span>
												{/if}
												{#if repo.findings_count.medium > 0}
													<span class="px-2 py-1 rounded text-xs font-medium" 
														style="background-color: {getSeverityColor('medium')}20; color: {getSeverityColor('medium')}">
														{repo.findings_count.medium} Medium
													</span>
												{/if}
												{#if repo.findings_count.low > 0}
													<span class="px-2 py-1 rounded text-xs font-medium" 
														style="background-color: {getSeverityColor('low')}20; color: {getSeverityColor('low')}">
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
						<div class="rounded-lg p-6 transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
							<h2 class="text-xl font-bold mb-4 flex items-center gap-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
								<span>⚠️ Repositories without CI/CD Workflows</span>
								<span class="text-sm font-normal px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-yellow-900/30 text-yellow-400' : 'bg-yellow-100 text-yellow-800'}">
									{getRepositoriesWithoutWorkflows().length}
								</span>
							</h2>
							
							<div class="mb-4 p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-yellow-900/20 border border-yellow-800' : 'bg-yellow-50 border border-yellow-200'}">
								<p class="text-sm transition-colors {$isDarkMode ? 'text-yellow-300' : 'text-yellow-800'}">
									ℹ️ These repositories are not included in the overall security score calculation since they don't have any GitHub Actions workflows configured.
								</p>
							</div>
							
							<div class="space-y-4">
								{#each getRepositoriesWithoutWorkflows() as repo}
									<div class="p-4 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}">
										<h3 class="font-bold text-lg transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
											📁 {repo.repository_name}
										</h3>
										<div class="text-sm mt-2 transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
											No CI/CD workflows configured - Consider adding GitHub Actions for automated security testing
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>

			{:else if activeTab === 'findings'}
				<!-- Findings Tab -->
				<div class="space-y-4">
					{#if analysisData.findings && analysisData.findings.length > 0}
						{#each analysisData.findings as finding, idx}
							<div class="rounded-lg overflow-hidden transition-colors {$isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white shadow-sm border border-gray-200'}">
								<button
									on:click={() => toggleFinding(idx)}
									class="w-full p-4 flex items-start justify-between hover:opacity-80 transition-all"
								>
									<div class="flex items-start gap-4 text-left flex-1">
										<span 
											class="px-3 py-1 rounded font-medium text-sm uppercase"
											style="background-color: {getSeverityColor(finding.severity)}20; color: {getSeverityColor(finding.severity)}"
										>
											{finding.severity}
										</span>
										<div class="flex-1">
											<h3 class="font-semibold mb-1 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
												{finding.title}
											</h3>
											<p class="text-sm transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
												{finding.description}
											</p>
										</div>
									</div>
									<span class="text-xl transition-transform {expandedFindings.has(idx) ? 'rotate-180' : ''}">
										▼
									</span>
								</button>
								
								{#if expandedFindings.has(idx)}
									<div class="px-4 pb-4 border-t transition-colors {$isDarkMode ? 'border-gray-700' : 'border-gray-200'}">
										<div class="mt-4 space-y-4">
											<div>
												<h4 class="font-semibold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
													💡 Recommendation
												</h4>
												<p class="text-sm transition-colors {$isDarkMode ? 'text-gray-300' : 'text-gray-700'}">
													{finding.recommendation}
												</p>
											</div>
											
											{#if finding.affected_component}
												<div>
													<h4 class="font-semibold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
														📍 Affected Component
													</h4>
													<code class="text-sm px-2 py-1 rounded transition-colors {$isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-800'}">
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
						<div class="text-center py-12 rounded-lg transition-colors {$isDarkMode ? 'bg-gray-800' : 'bg-white shadow-sm'}">
							<span class="text-6xl mb-4 block">🎉</span>
							<h3 class="text-xl font-bold mb-2 transition-colors {$isDarkMode ? 'text-white' : 'text-gray-900'}">
								No Findings
							</h3>
							<p class="transition-colors {$isDarkMode ? 'text-gray-400' : 'text-gray-600'}">
								Great! No security issues detected.
							</p>
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
</div>

<style>
	/* Smooth transitions for dark mode */
	* {
		transition-property: background-color, border-color, color;
		transition-duration: 200ms;
		transition-timing-function: ease-in-out;
	}
	
	/* Custom scrollbar for dark mode */
	:global(.dark-mode) ::-webkit-scrollbar {
		width: 12px;
		height: 12px;
	}
	
	:global(.dark-mode) ::-webkit-scrollbar-track {
		background: #1f2937;
	}
	
	:global(.dark-mode) ::-webkit-scrollbar-thumb {
		background: #4b5563;
		border-radius: 6px;
	}
	
	:global(.dark-mode) ::-webkit-scrollbar-thumb:hover {
		background: #6b7280;
	}
</style>