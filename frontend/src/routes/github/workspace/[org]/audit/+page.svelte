<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { githubClient } from '$lib/github.js';
	import { isDarkMode } from '$lib/stores.js';

	let orgName = '';
	let actions = [];
	let loading = true;
	let error = null;
	let workspaceData = null;
	let loadingactions = false;
	let loadingStage = 'Initializing...';
	let viewMode = 'detailed'; // 'detailed' or 'grouped'

	// Subscribe to dark mode
	let darkMode = false;
	$: {
		const unsubscribe = isDarkMode.subscribe((value) => {
			darkMode = value;
		});
	}

	// Pagination state
	let currentPage = 1;
	let perPage = 20;
	let totalPages = 1;
	let totalItems = 0;
	let hasNext = false;
	let hasPrevious = false;

	// Search state
	let searchQuery = '';
	let searchTimeout;

	// Statistics - enhanced with new status types
	let statistics = {
		up_to_date: 0,
		outdated: 0,
		upgrade_recommended: 0,
		major_upgrade_needed: 0,
		unknown: 0
	};

	// Calculate statistics from actions data
	$: if (actions.length > 0) {
		const newStats = {
			up_to_date: 0,
			outdated: 0,
			upgrade_recommended: 0,
			major_upgrade_needed: 0,
			unknown: 0
		};

		actions.forEach((action) => {
			if (isUpToDate(action.status)) {
				newStats.up_to_date++;
			} else if (action.status === '🚨 major upgrade needed') {
				newStats.major_upgrade_needed++;
			} else if (action.status === '🔧 upgrade recommended') {
				newStats.upgrade_recommended++;
			} else if (action.status === '⚠️ outdated' || action.status === 'outdated') {
				newStats.outdated++;
			} else {
				newStats.unknown++;
			}
		});

		statistics = newStats;
	}

	// Helper function to determine if action is outdated
	function isOutdated(status) {
		return (
			status === '⚠️ outdated' ||
			status === 'outdated' ||
			status === '🔧 upgrade recommended' ||
			status === '🚨 major upgrade needed'
		);
	}

	// Helper function to determine if action is up-to-date
	function isUpToDate(status) {
		return status === '✅ up-to-date' || status === 'up-to-date';
	}

	// Helper function to get status color class
	function getStatusColorClass(status) {
		if (isUpToDate(status)) {
			return 'bg-green-100 text-green-800';
		} else if (status === '🚨 major upgrade needed') {
			return 'bg-red-100 text-red-800';
		} else if (status === '🔧 upgrade recommended') {
			return 'bg-blue-100 text-blue-800';
		} else if (status === '⚠️ outdated' || status === 'outdated') {
			return 'bg-yellow-100 text-yellow-800';
		} else if (status === 'No actions found') {
			return 'bg-gray-100 text-gray-800';
		} else {
			return 'bg-gray-100 text-gray-600';
		}
	}

	// Workflow groups for grouped view
	let workflowGroups = {};

	// Calculate workflow groups from actions data
	$: if (actions.length > 0) {
		const groups = {};

		actions.forEach((action) => {
			const key = `${action.repo_name}/${action.workflow_filename || action.workflow}`;

			if (!groups[key]) {
				groups[key] = {
					repo_name: action.repo_name,
					workflow: action.workflow_name || action.workflow,
					workflow_name: action.workflow_name || action.workflow,
					workflow_filename: action.workflow_filename || action.workflow,
					actions: [],
					hasActions: false,
					upToDate: 0,
					upgradeRecommended: 0,
					majorUpgradeNeeded: 0,
					outdated: 0,
					unknown: 0,
					total: 0
				};
			}

			groups[key].actions.push(action);
			groups[key].total++;

			// Count by status with enhanced types
			if (isUpToDate(action.status)) {
				groups[key].upToDate++;
			} else if (action.status === '🚨 major upgrade needed') {
				groups[key].majorUpgradeNeeded++;
			} else if (action.status === '🔧 upgrade recommended') {
				groups[key].upgradeRecommended++;
			} else if (action.status === '⚠️ outdated' || action.status === 'outdated') {
				groups[key].outdated++;
			} else {
				groups[key].unknown++;
			}

			// Check if this workflow has actual actions (not just "No actions found")
			if (action.action_name && action.action_name.trim() !== '') {
				groups[key].hasActions = true;
			}
		});

		workflowGroups = groups;
		console.log('📊 Workflow groups calculated:', Object.keys(groups).length, 'groups');
		console.log('Sample group:', Object.values(groups)[0]);
	}

	// Cache status
	let isCached = false;
	let lastUpdated = null;

	onMount(async () => {
		orgName = $page.params.org;

		// Initialize theme
		isDarkMode.init();

		await loadActionDetails();
	});

	function toggleTheme() {
		isDarkMode.toggle();
	}

	function goBack() {
		goto(`/github/workspace/${orgName}`);
	}

	// Load action details with pagination and search
	async function loadActionDetails(page = 1, search = '') {
		try {
			loadingactions = true;
			loadingStage = isCached ? 'Loading from cache...' : 'Fetching workflow data...';

			console.log(
				`🔍 Loading workflow actions for ${orgName} (page ${page}, search: "${search}")...`
			);

			const result = await githubClient.getActionDetailsPaginated(orgName, page, perPage, search);

			if (result.success) {
				// Update pagination data
				actions = result.actions || [];
				currentPage = result.page || 1;
				totalPages = result.total_pages || 1;
				totalItems = result.total_items || 0;
				hasNext = result.has_next || false;
				hasPrevious = result.has_previous || false;

				// Update statistics - use backend statistics if available, otherwise calculate from actions
				if (result.statistics) {
					statistics = result.statistics;
				} else {
					// Calculate statistics from actions data
					const newStats = {
						up_to_date: 0,
						outdated: 0,
						upgrade_recommended: 0,
						major_upgrade_needed: 0,
						unknown: 0
					};

					actions.forEach((action) => {
						if (isUpToDate(action.status)) {
							newStats.up_to_date++;
						} else if (action.status === '🚨 major upgrade needed') {
							newStats.major_upgrade_needed++;
						} else if (action.status === '🔧 upgrade recommended') {
							newStats.upgrade_recommended++;
						} else if (action.status === '⚠️ outdated' || action.status === 'outdated') {
							newStats.outdated++;
						} else {
							newStats.unknown++;
						}
					});

					statistics = newStats;
				}

				// Update cache status
				isCached = result.cached || false;
				lastUpdated = result.last_updated;

				console.log(`✅ Loaded ${actions.length} actions (page ${currentPage}/${totalPages})`);
				console.log(`📊 Total items: ${totalItems}, Cached: ${isCached}`);

				if (actions.length > 0) {
					console.log('Sample action data:', actions[0]);
				}
			} else {
				console.error('Failed to load detailed workflows action:', result.error);
				error = result.error || 'Failed to load workflow actions';
			}
		} catch (err) {
			console.error('Error loading detailed workflows:', err);
			error = 'An error occurred while loading workflow actions';
		} finally {
			loadingactions = false;
			loading = false;
		}
	}

	// Handle search with debouncing
	function handleSearch(event) {
		clearTimeout(searchTimeout);
		const query = event.target.value;

		searchTimeout = setTimeout(() => {
			searchQuery = query;
			currentPage = 1; // Reset to first page
			loadActionDetails(currentPage, searchQuery);
		}, 500); // 500ms debounce
	}

	// Pagination functions
	function goToPage(page) {
		if (page >= 1 && page <= totalPages) {
			currentPage = page;
			loadActionDetails(currentPage, searchQuery);
		}
	}

	function nextPage() {
		if (hasNext) {
			goToPage(currentPage + 1);
		}
	}

	function previousPage() {
		if (hasPrevious) {
			goToPage(currentPage - 1);
		}
	}

	// Clear cache and refresh
	async function clearCache() {
		try {
			loadingactions = true;
			loadingStage = 'Clearing cache...';

			const result = await githubClient.clearOrgCache(orgName);
			if (result.success) {
				console.log('✅ Cache cleared successfully');
				// Reload data
				await loadActionDetails(currentPage, searchQuery);
			} else {
				console.error('Failed to clear cache:', result.error);
			}
		} catch (err) {
			console.error('Error clearing cache:', err);
		}
	}

	// Refresh action details (clear cache and fetch fresh data)
	async function refreshActionDetails() {
		try {
			loadingactions = true;
			console.log(`🔄 Refreshing action details for ${orgName}...`);

			// Clear cache first
			await clearCache();

			const result = await githubClient.refreshActionDetails(orgName);

			if (result.success) {
				// Update actions with fresh data
				if (Array.isArray(result.actions)) {
					actions = [...result.actions];
					console.log('Actions refreshed:', actions);
				} else {
					actions = [];
				}
				console.log(
					`✅ Refreshed ${actions.length} actions (cache cleared: ${result.cache_cleared || 0} entries)`
				);

				// Show success message briefly
				const successMsg = `Data refreshed! Found ${actions.length} actions.`;
				console.log(successMsg);
			} else {
				console.error('Failed to refresh action details:', result.error);
				error = result.error || 'Failed to refresh action details';
			}
		} catch (err) {
			console.error('Error refreshing action details:', err);
			error = err.message || 'An error occurred while refreshing action details';
		} finally {
			loadingactions = false;
		}
	}

	//todo:- Create-pull request for outdated action

	async function createPullRequest(action) {
		//TODO:_^_^_^_^_^_^_^_^_^_^_^_^_^_
		try {
			//todo:- Set loading state for this specific action
			action.prCreating = true;
			actions = [...actions]; // Trigger reactivity

			// Debug: Log the action object to see its structure
			console.log('🔍 Action object for PR creation:', action);
			console.log('🔍 All action fields:', Object.keys(action));
			console.log('🔍 Action fields:', {
				repo: action.repo_name,
				workflow_path: action.workflow_path,
				action_name: action.action_name, // Use action_name instead of action
				current_version: action.current_version,
				latest_version: action.latest_version
			});

			// Check for missing fields before sending request
			const missingFields = [];
			if (!action.repo_name) missingFields.push('repo_name');
			if (!action.workflow_path) missingFields.push('workflow_path');
			if (!action.action_name) missingFields.push('action_name');
			if (!action.current_version) missingFields.push('current_version');
			if (!action.latest_version) missingFields.push('latest_version');

			if (missingFields.length > 0) {
				console.error('❌ Missing required fields:', missingFields);
				alert(`❌ Cannot create PR: Missing required fields: ${missingFields.join(', ')}`);
				return;
			}

			const result = await githubClient.createActionUpdatePR({
				org: orgName,
				repo: action.repo_name,
				workflow_path: action.workflow_path,
				action_name: action.action_name, // Use action_name instead of action
				current_version: action.current_version,
				latest_version: action.latest_version
			});

			if (result.success) {
				// Show success message
				alert(
					`✅ Pull request created successfully!\n\nPR #${result.pr_number}: ${result.pr_title}\n\nYou can view it at: ${result.pr_url}`
				);

				// Refresh the data to reflect the changes
				await loadActionDetails(currentPage, searchQuery);
			} else {
				alert(`❌ Failed to create pull request: ${result.error}`);
			}
		} catch (err) {
			console.error('Error creating pull request:', err);
			alert(`❌ Error creating pull request: ${err.message}`);
		} finally {
			// Reset loading state
			action.prCreating = false;
			actions = [...actions]; // Trigger reactivity
		}
	}

	// Fix all outdated actions in a workflow
	async function fixAllOutdatedInWorkflow(workflowGroup) {
		try {
			const outdatedActions = workflowGroup.actions.filter(
				(action) => action.status === '⚠️ outdated' || action.status === 'outdated'
			);

			if (outdatedActions.length === 0) {
				return;
			}

			const confirmMsg = `Create pull request to fix ${outdatedActions.length} outdated action(s) in ${workflowGroup.repo_name}/${workflowGroup.workflow}?`;
			if (!confirm(confirmMsg)) {
				return;
			}

			// Create a single PR for all outdated actions in this workflow
			const result = await githubClient.createBulkActionUpdatePR({
				org: orgName,
				repo: workflowGroup.repo_name,
				workflow_path: outdatedActions[0].workflow_path, // They all have the same workflow path
				actions: outdatedActions.map((action) => ({
					action_name: action.action,
					current_version: action.current_version,
					latest_version: action.latest_version
				}))
			});

			if (result.success) {
				alert(
					`✅ Pull request created successfully!\n\nPR #${result.pr_number}: ${result.pr_title}\n\nYou can view it at: ${result.pr_url}`
				);
				await loadActionDetails(currentPage, searchQuery);
			} else {
				alert(`❌ Failed to create pull request: ${result.error}`);
			}
		} catch (err) {
			console.error('Error creating bulk pull request:', err);
			alert(`❌ Error creating pull request: ${err.message}`);
		}
	}

	// Group actions by repository for better organization
	$: groupedActions = actions.reduce((acc, action) => {
		const repo = action.repo_name;
		if (!acc[repo]) {
			acc[repo] = [];
		}
		acc[repo].push(action);
		return acc;
	}, {});

	$: displayActions = viewMode === 'grouped' ? Object.values(workflowGroups) : actions;
</script>

<svelte:head>
	<title>Actions Version Audit - {orgName} | WithOps</title>
</svelte:head>

<div class="audit-container {darkMode ? 'dark' : 'light'}">
	<!-- Top Navigation Bar -->
	<nav class="top-navbar">
		<div class="navbar-content">
			<!-- Left: Brand & Breadcrumb -->
			<div class="navbar-left">
				<div class="brand-section">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<div class="brand-text">
						<span class="brand-name">WithOps</span>
						<span class="brand-subtitle">Actions Audit</span>
					</div>
				</div>

				<!-- Breadcrumb -->
				<nav class="breadcrumb">
					<a href="/dashboard" class="breadcrumb-link">Dashboard</a>
					<span class="breadcrumb-separator">/</span>
					<a href="/github/organizations" class="breadcrumb-link">Organizations</a>
					<span class="breadcrumb-separator">/</span>
					<a href="/github/workspace/{orgName}" class="breadcrumb-link">{orgName}</a>
					<span class="breadcrumb-separator">/</span>
					<span class="breadcrumb-current">Audit</span>
				</nav>
			</div>

			<!-- Right: Theme Toggle -->
			<div class="navbar-right">
				<button onclick={toggleTheme} class="theme-toggle" title="Toggle theme">
					{#if darkMode}
						<svg class="theme-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
							/>
						</svg>
					{:else}
						<svg class="theme-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
							/>
						</svg>
					{/if}
				</button>
			</div>
		</div>
	</nav>

	<!-- Main Content Area with Full Width -->
	<div class="main-content">
		<!-- Header Section -->
		<div class="content-header">
			<div class="header-left">
				<h1 class="page-title">Actions Version Audit</h1>
				<p class="page-subtitle">Organization: <span class="org-name">{orgName}</span></p>
			</div>
			<div class="header-actions">
				<!-- View Mode Toggle -->
				<div class="view-mode-toggle">
					<span class="toggle-label">View:</span>
					<button
						onclick={() => (viewMode = 'detailed')}
						class="toggle-button {viewMode === 'detailed' ? 'active' : ''}"
					>
						Detailed
					</button>
					<button
						onclick={() => (viewMode = 'grouped')}
						class="toggle-button {viewMode === 'grouped' ? 'active' : ''}"
					>
						Grouped
					</button>
				</div>
				<!-- Refresh Button -->
				<button onclick={refreshActionDetails} disabled={loadingactions} class="refresh-button">
					<svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
						></path>
					</svg>
					<span>{loadingactions ? 'Refreshing...' : 'Refresh'}</span>
				</button>
				<button onclick={goBack} class="back-button"> ← Back to Workspace </button>
			</div>
		</div>

		{#if loading || loadingactions}
			<div class="loading-card">
				<div class="spinner"></div>
				<p class="loading-text">Loading workflow actions...</p>
			</div>
		{:else if error}
			<div class="error-card">
				<div class="error-content">
					<svg class="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<span class="error-message">Error: {error}</span>
				</div>
			</div>
		{:else if actions.length === 0}
			<div class="empty-card">
				<p class="empty-text">No workflow actions found for this organization.</p>
			</div>
		{:else}
			<!-- Search and Pagination Controls -->
			<div class="controls-card">
				<div class="controls-container">
					<!-- Search Bar -->
					<div class="search-wrapper">
						<div class="search-container">
							<svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
								/>
							</svg>
							<input
								type="text"
								placeholder="Search repositories, workflows, or actions..."
								class="search-input"
								oninput={handleSearch}
								value={searchQuery}
							/>
						</div>
					</div>

					<!-- Stats and Cache Status -->
					<div class="stats-container">
						{#if isCached}
							<div class="cached-indicator">
								<svg class="cached-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M13 10V3L4 14h7v7l9-11h-7z"
									/>
								</svg>
								<span>Cached</span>
							</div>
						{/if}
						<div class="total-count">
							{totalItems} total actions
						</div>
					</div>
				</div>

				<!-- Statistics -->
				<div class="statistics-grid">
					<div class="stat-item">
						<div class="stat-dot up-to-date"></div>
						<span class="stat-label">
							{statistics.up_to_date} up-to-date
						</span>
					</div>
					<div class="stat-item">
						<div class="stat-dot major-upgrade"></div>
						<span class="stat-label">
							{statistics.major_upgrade_needed} major upgrades
						</span>
					</div>
					<div class="stat-item">
						<div class="stat-dot recommended"></div>
						<span class="stat-label">
							{statistics.upgrade_recommended} recommended
						</span>
					</div>
					<div class="stat-item">
						<div class="stat-dot outdated"></div>
						<span class="stat-label">
							{statistics.outdated} outdated
						</span>
					</div>
					<div class="stat-item">
						<div class="stat-dot unknown"></div>
						<span class="stat-label">
							{statistics.unknown} unknown
						</span>
					</div>
				</div>
			</div>

			<div class="table-card">
				<div class="table-header">
					<div class="table-title-section">
						<h2 class="table-title">
							{viewMode === 'detailed' ? 'Workflow Actions' : 'Workflow Summary'} ({viewMode ===
							'detailed'
								? actions.length
								: Object.keys(workflowGroups).length}
							{viewMode === 'detailed' ? 'actions' : 'workflows'})
						</h2>
						<div class="realtime-badge">
							<svg class="badge-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							<span>Real-time versions from GitHub API</span>
						</div>
					</div>
				</div>

				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200">
						<thead class="bg-gray-50">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>
									Repository
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>
									Workflow Name
								</th>
								{#if viewMode === 'detailed'}
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Action
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Current Version
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Latest Version
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Status
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Actions
									</th>
								{:else}
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Actions Count
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Up to Date
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Major Upgrades
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Recommended
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Outdated
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Summary
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Actions
									</th>
								{/if}
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 bg-white">
							{#if viewMode === 'detailed'}
								{#each actions as action, index}
									<tr class="transition-colors duration-200 hover:bg-gray-50">
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="flex items-center">
												<div class="h-10 w-10 flex-shrink-0">
													<div
														class="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100"
													>
														<svg
															class="h-5 w-5 text-blue-600"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
															/>
														</svg>
													</div>
												</div>
												<div class="ml-4">
													<div class="font-mono text-sm font-medium text-gray-900">
														{action.repo_name}
													</div>
												</div>
											</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="text-sm text-gray-900">
												{action.workflow_name || action.workflow || 'Unknown Workflow'}
											</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="font-mono text-sm text-gray-900">
												{action.action_name || action.action || 'No actions found'}
											</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span class="rounded bg-gray-100 px-2 py-1 font-mono text-sm text-gray-700">
												{action.current_version || 'N/A'}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span class="rounded bg-gray-100 px-2 py-1 font-mono text-sm text-gray-700">
												{action.latest_version}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span
												class="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium {getStatusColorClass(
													action.status
												)}"
											>
												{action.status}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											{#if isOutdated(action.status)}
												<button
													onclick={() => createPullRequest(action)}
													disabled={action.prCreating}
													class="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
												>
													{#if action.prCreating}
														<svg
															class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
															xmlns="http://www.w3.org/2000/svg"
															fill="none"
															viewBox="0 0 24 24"
														>
															<circle
																class="opacity-25"
																cx="12"
																cy="12"
																r="10"
																stroke="currentColor"
																stroke-width="4"
															></circle>
															<path
																class="opacity-75"
																fill="currentColor"
																d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
															></path>
														</svg>
														Creating PR...
													{:else}
														<svg
															class="mr-2 -ml-1 h-4 w-4"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M13 10V3L4 14h7v7l9-11h-7z"
															/>
														</svg>
														{action.status === '🚨 major upgrade needed'
															? 'Major Update'
															: 'Fix via PR'}
													{/if}
												</button>
											{:else if isUpToDate(action.status)}
												<span
													class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700"
												>
													✅ Up to date
												</span>
											{:else}
												<span
													class="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-500"
												>
													-
												</span>
											{/if}
										</td>
									</tr>
								{/each}
							{:else}
								{#each Object.values(workflowGroups) as workflowGroup, index}
									<tr class="transition-colors duration-200 hover:bg-gray-50">
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="flex items-center">
												<div class="h-10 w-10 flex-shrink-0">
													<div
														class="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100"
													>
														<svg
															class="h-5 w-5 text-blue-600"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
															/>
														</svg>
													</div>
												</div>
												<div class="ml-4">
													<div class="font-mono text-sm font-medium text-gray-900">
														{workflowGroup.repo_name}
													</div>
												</div>
											</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="text-sm text-gray-900">
												{workflowGroup.workflow_name ||
													workflowGroup.workflow ||
													'Unknown Workflow'}
											</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="text-sm text-gray-900">
												{workflowGroup.hasActions ? workflowGroup.total : 'No actions'}
											</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span
												class="inline-flex items-center rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800"
											>
												{workflowGroup.upToDate}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span
												class="inline-flex items-center rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800"
											>
												{workflowGroup.majorUpgradeNeeded}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span
												class="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-800"
											>
												{workflowGroup.upgradeRecommended}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span
												class="inline-flex items-center rounded-full bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-800"
											>
												{workflowGroup.outdated}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span
												class="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium
                                            {workflowGroup.hasActions
													? workflowGroup.majorUpgradeNeeded > 0
														? 'bg-red-100 text-red-800'
														: workflowGroup.upgradeRecommended > 0 || workflowGroup.outdated > 0
															? 'bg-yellow-100 text-yellow-800'
															: 'bg-green-100 text-green-800'
													: 'bg-gray-100 text-gray-800'}"
											>
												{workflowGroup.hasActions
													? workflowGroup.majorUpgradeNeeded > 0
														? `🚨 ${workflowGroup.majorUpgradeNeeded} critical`
														: workflowGroup.upgradeRecommended > 0 || workflowGroup.outdated > 0
															? `⚠️ ${workflowGroup.upgradeRecommended + workflowGroup.outdated} updates`
															: '✅ All up-to-date'
													: 'No actions'}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											{#if workflowGroup.majorUpgradeNeeded > 0 || workflowGroup.upgradeRecommended > 0 || workflowGroup.outdated > 0}
												<button
													onclick={() => fixAllOutdatedInWorkflow(workflowGroup)}
													class="inline-flex items-center rounded-md px-3 py-2 text-sm font-semibold text-white shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2
													{workflowGroup.majorUpgradeNeeded > 0
														? 'bg-red-600 hover:bg-red-500 focus-visible:outline-red-600'
														: 'bg-blue-600 hover:bg-blue-500 focus-visible:outline-blue-600'}"
												>
													<svg
														class="mr-2 -ml-1 h-4 w-4"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M13 10V3L4 14h7v7l9-11h-7z"
														/>
													</svg>
													{workflowGroup.majorUpgradeNeeded > 0
														? `Major Update (${workflowGroup.majorUpgradeNeeded + workflowGroup.upgradeRecommended + workflowGroup.outdated})`
														: `Fix All (${workflowGroup.upgradeRecommended + workflowGroup.outdated})`}
												</button>
											{:else if workflowGroup.hasActions}
												<span
													class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700"
												>
													✅ All up to date
												</span>
											{:else}
												<span
													class="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-500"
												>
													No actions
												</span>
											{/if}
										</td>
									</tr>
								{/each}
							{/if}
						</tbody>
					</table>
				</div>

				<!-- Pagination Controls -->
				{#if totalPages > 1}
					<div class="border-t border-gray-200 bg-gray-50 px-6 py-4">
						<div class="flex items-center justify-between">
							<div class="flex flex-1 justify-between sm:hidden">
								<!-- Mobile pagination -->
								<button
									onclick={previousPage}
									disabled={!hasPrevious}
									class="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
								>
									Previous
								</button>
								<button
									onclick={nextPage}
									disabled={!hasNext}
									class="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
								>
									Next
								</button>
							</div>

							<div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
								<div>
									<p class="text-sm text-gray-700">
										Showing page <span class="font-medium">{currentPage}</span> of
										<span class="font-medium">{totalPages}</span>
										(<span class="font-medium">{totalItems}</span> total actions)
									</p>
								</div>
								<div>
									<nav class="isolate inline-flex -space-x-px rounded-md shadow-sm">
										<!-- Previous button -->
										<button
											onclick={previousPage}
											disabled={!hasPrevious}
											class="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
										>
											<span class="sr-only">Previous</span>
											<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path
													fill-rule="evenodd"
													d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z"
													clip-rule="evenodd"
												/>
											</svg>
										</button>

										<!-- Page numbers -->
										{#each Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
											const startPage = Math.max(1, currentPage - 2);
											const endPage = Math.min(totalPages, startPage + 4);
											return startPage + i;
										}) as pageNum}
											{#if pageNum <= totalPages}
												<button
													onclick={() => goToPage(pageNum)}
													class="relative inline-flex items-center px-4 py-2 text-sm font-semibold ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:z-20 focus:outline-offset-0 {pageNum ===
													currentPage
														? 'z-10 bg-blue-600 text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
														: 'text-gray-900'}"
												>
													{pageNum}
												</button>
											{/if}
										{/each}

										<!-- Next button -->
										<button
											onclick={nextPage}
											disabled={!hasNext}
											class="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-gray-300 ring-inset hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
										>
											<span class="sr-only">Next</span>
											<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path
													fill-rule="evenodd"
													d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
													clip-rule="evenodd"
												/>
											</svg>
										</button>
									</nav>
								</div>
							</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- Summary Statistics -->
			<div class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
				<div class="rounded-lg bg-white p-4 shadow">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-green-100">
								<svg
									class="h-5 w-5 text-green-600"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M5 13l4 4L19 7"
									/>
								</svg>
							</div>
						</div>
						<div class="ml-3">
							<p class="text-sm font-medium text-gray-500">Up to Date</p>
							<p class="text-2xl font-semibold text-gray-900">
								{actions.filter((a) => a.status === '✅ up-to-date' || a.status === 'up-to-date')
									.length}
							</p>
						</div>
					</div>
				</div>

				<div class="rounded-lg bg-white p-4 shadow">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-yellow-100">
								<svg
									class="h-5 w-5 text-yellow-600"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
									/>
								</svg>
							</div>
						</div>
						<div class="ml-3">
							<p class="text-sm font-medium text-gray-500">Outdated</p>
							<p class="text-2xl font-semibold text-gray-900">
								{actions.filter((a) => a.status === '⚠️ outdated' || a.status === 'outdated')
									.length}
							</p>
						</div>
					</div>
				</div>

				<div class="rounded-lg bg-white p-4 shadow">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100">
								<svg
									class="h-5 w-5 text-gray-600"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
									/>
								</svg>
							</div>
						</div>
						<div class="ml-3">
							<p class="text-sm font-medium text-gray-500">
								{viewMode === 'detailed' ? 'No Actions' : 'Workflows'}
							</p>
							<p class="text-2xl font-semibold text-gray-900">
								{viewMode === 'detailed'
									? actions.filter((a) => a.status === 'No actions found').length
									: Object.keys(workflowGroups).length}
							</p>
						</div>
					</div>
				</div>

				<div class="rounded-lg bg-white p-4 shadow">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100">
								<svg
									class="h-5 w-5 text-blue-600"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
									/>
								</svg>
							</div>
						</div>
						<div class="ml-3">
							<p class="text-sm font-medium text-gray-500">
								{viewMode === 'detailed' ? 'Total Actions' : 'Total Actions'}
							</p>
							<p class="text-2xl font-semibold text-gray-900">
								{actions.length}
							</p>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	/* ============================================
	   CSS VARIABLES - Cyan Design System
	   ============================================ */
	:global(:root) {
		--primary-color: #00d9ff;
		--primary-hover: #33e3ff;
		--primary-dark: #00c0e0;
		--text-primary: #ffffff;
		--text-secondary: #b8b8b8;
		--text-muted: #666666;
		--bg-primary: rgba(0, 0, 0, 0.95);
		--bg-card: rgba(0, 0, 0, 0.4);
		--border-color: rgba(0, 217, 255, 0.3);
	}

	/* ============================================
	   MAIN CONTAINER
	   ============================================ */
	.audit-container {
		min-height: 100vh;
		background: linear-gradient(135deg, #000000 0%, #0a0a0a 100%);
		color: var(--text-primary);
	}

	.audit-container.light {
		background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);
		color: #000000;
	}

	.audit-container.light {
		--text-primary: #000000;
		--text-secondary: #666666;
		--text-muted: #999999;
		--bg-primary: rgba(255, 255, 255, 0.95);
		--bg-card: rgba(255, 255, 255, 0.6);
		--border-color: rgba(0, 217, 255, 0.3);
	}

	/* ============================================
	   NAVIGATION BAR
	   ============================================ */
	.top-navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 1000;
		background: var(--bg-primary);
		backdrop-filter: blur(20px);
		border-bottom: 1px solid var(--border-color);
		padding: 1rem 2rem;
		transition: all 0.3s ease;
	}

	.navbar-content {
		display: flex;
		align-items: center;
		justify-content: space-between;
		max-width: 100%;
	}

	.navbar-left {
		display: flex;
		align-items: center;
		gap: 2rem;
	}

	.navbar-right {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	/* Brand Section */
	.brand-section {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		cursor: pointer;
		transition: transform 0.3s ease;
	}

	.brand-section:hover {
		transform: translateY(-1px);
	}

	.brand-icon {
		width: 48px;
		height: 48px;
		filter: drop-shadow(0 0 10px rgba(0, 217, 255, 0.5));
		transition: filter 0.3s ease;
	}

	.brand-section:hover .brand-icon {
		filter: drop-shadow(0 0 15px rgba(0, 217, 255, 0.7));
	}

	.brand-text {
		display: flex;
		flex-direction: column;
	}

	.brand-name {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1;
		letter-spacing: -0.02em;
	}

	.brand-subtitle {
		font-size: 0.7rem;
		color: var(--text-secondary);
		opacity: 0.8;
		margin-top: 0.2rem;
		letter-spacing: 0.05em;
	}

	/* Breadcrumb */
	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.breadcrumb-link {
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.3s ease;
		position: relative;
	}

	.breadcrumb-link:hover {
		color: var(--primary-color);
	}

	.breadcrumb-link::after {
		content: '';
		position: absolute;
		bottom: -2px;
		left: 0;
		width: 0;
		height: 2px;
		background: var(--primary-color);
		transition: width 0.3s ease;
	}

	.breadcrumb-link:hover::after {
		width: 100%;
	}

	.breadcrumb-separator {
		color: var(--text-muted);
	}

	.breadcrumb-current {
		color: var(--primary-color);
		font-weight: 600;
	}

	/* Theme Toggle */
	.theme-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		background: transparent;
		border: 1px solid var(--border-color);
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.theme-toggle:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: var(--primary-color);
		box-shadow: 0 4px 12px rgba(0, 217, 255, 0.2);
	}

	.theme-icon {
		width: 20px;
		height: 20px;
		color: var(--primary-color);
	}

	/* ============================================
	   MAIN CONTENT AREA - FULL WIDTH
	   ============================================ */
	.main-content {
		margin-top: 80px;
		padding: 2rem;
		width: 100%;
		min-height: calc(100vh - 80px);
	}

	/* Header Section */
	.content-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 2rem;
		flex-wrap: wrap;
		gap: 1.5rem;
	}

	.header-left {
		flex: 1;
		min-width: 250px;
	}

	.page-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	.page-subtitle {
		color: var(--text-secondary);
		font-size: 0.95rem;
	}

	.org-name {
		font-family: 'Courier New', monospace;
		color: var(--primary-color);
		font-weight: 600;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
	}

	/* View Mode Toggle */
	.view-mode-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: var(--bg-card);
		border: 1px solid var(--border-color);
		border-radius: 8px;
		padding: 0.5rem;
	}

	.toggle-label {
		font-size: 0.875rem;
		color: var(--text-secondary);
		padding: 0 0.5rem;
	}

	.toggle-button {
		padding: 0.5rem 1rem;
		background: transparent;
		border: 1px solid transparent;
		border-radius: 6px;
		color: var(--text-secondary);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.toggle-button:hover {
		background: rgba(0, 217, 255, 0.1);
		color: var(--primary-color);
	}

	.toggle-button.active {
		background: var(--primary-color);
		color: #000000;
		border-color: var(--primary-color);
		box-shadow: 0 2px 8px rgba(0, 217, 255, 0.3);
	}

	/* Refresh Button */
	.refresh-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		background: #ffffff;
		color: #000000;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
	}

	.refresh-button:hover:not(:disabled) {
		background: var(--primary-color);
		transform: translateY(-3px);
		box-shadow:
			0 15px 40px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 217, 255, 0.3);
	}

	.refresh-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.button-icon {
		width: 18px;
		height: 18px;
	}

	/* Back Button */
	.back-button {
		padding: 0.75rem 1.5rem;
		background: transparent;
		border: 1px solid var(--border-color);
		border-radius: 8px;
		color: var(--text-primary);
		font-weight: 500;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.back-button:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: var(--primary-color);
		transform: translateX(-4px);
		box-shadow: 0 4px 12px rgba(0, 217, 255, 0.2);
	}

	/* ============================================
	   CARD COMPONENTS - Cyan Design Pattern
	   ============================================ */
	.loading-card,
	.error-card,
	.empty-card,
	.controls-card,
	.table-card {
		background: var(--bg-card);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		padding: 1.5rem;
		backdrop-filter: blur(10px);
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
		margin-bottom: 1.5rem;
		position: relative;
		overflow: hidden;
	}

	.loading-card,
	.empty-card {
		text-align: center;
		padding: 3rem 1.5rem;
	}

	/* Loading State */
	.spinner {
		width: 40px;
		height: 40px;
		margin: 0 auto 1rem;
		border: 3px solid var(--border-color);
		border-top-color: var(--primary-color);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-text {
		color: var(--text-secondary);
		font-size: 0.95rem;
	}

	/* Error State */
	.error-card {
		border-color: rgba(255, 87, 87, 0.5);
		background: rgba(255, 87, 87, 0.1);
	}

	.error-content {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.error-icon {
		width: 24px;
		height: 24px;
		color: #ff5757;
		flex-shrink: 0;
	}

	.error-message {
		color: #ff5757;
		font-weight: 600;
	}

	/* Empty State */
	.empty-text {
		color: var(--text-secondary);
		font-size: 1rem;
	}

	/* ============================================
	   CONTROLS CARD
	   ============================================ */
	.controls-container {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.search-wrapper {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.search-container {
		position: relative;
		flex: 1;
		max-width: 500px;
		min-width: 250px;
	}

	.search-icon {
		position: absolute;
		left: 1rem;
		top: 50%;
		transform: translateY(-50%);
		width: 20px;
		height: 20px;
		color: var(--text-muted);
		pointer-events: none;
	}

	.search-input {
		width: 100%;
		padding: 0.75rem 1rem 0.75rem 3rem;
		background: rgba(0, 0, 0, 0.3);
		border: 1px solid var(--border-color);
		border-radius: 8px;
		color: var(--text-primary);
		font-size: 0.9rem;
		transition: all 0.3s ease;
	}

	.audit-container.light .search-input {
		background: rgba(255, 255, 255, 0.8);
	}

	.search-input:focus {
		outline: none;
		border-color: var(--primary-color);
		box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1);
	}

	.search-input::placeholder {
		color: var(--text-muted);
	}

	.stats-container {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		flex-wrap: wrap;
	}

	.cached-indicator {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: rgba(0, 217, 255, 0.1);
		border: 1px solid rgba(0, 217, 255, 0.3);
		border-radius: 6px;
		color: var(--primary-color);
		font-size: 0.875rem;
		font-weight: 500;
	}

	.cached-icon {
		width: 16px;
		height: 16px;
	}

	.total-count {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	/* Statistics Grid */
	.statistics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 1rem;
	}

	.stat-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.stat-dot {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.stat-dot.up-to-date {
		background: #00ff88;
		box-shadow: 0 0 8px rgba(0, 255, 136, 0.5);
	}

	.stat-dot.major-upgrade {
		background: #ff5757;
		box-shadow: 0 0 8px rgba(255, 87, 87, 0.5);
	}

	.stat-dot.recommended {
		background: var(--primary-color);
		box-shadow: 0 0 8px rgba(0, 217, 255, 0.5);
	}

	.stat-dot.outdated {
		background: #ffaa00;
		box-shadow: 0 0 8px rgba(255, 170, 0, 0.5);
	}

	.stat-dot.unknown {
		background: #888888;
		box-shadow: 0 0 8px rgba(136, 136, 136, 0.5);
	}

	.stat-label {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	/* ============================================
	   TABLE CARD
	   ============================================ */
	.table-header {
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--border-color);
		margin-bottom: 1rem;
	}

	.table-title-section {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.table-title {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.realtime-badge {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: rgba(0, 255, 136, 0.1);
		border: 1px solid rgba(0, 255, 136, 0.3);
		border-radius: 6px;
		color: #00ff88;
		font-size: 0.8rem;
		font-weight: 500;
	}

	.badge-icon {
		width: 16px;
		height: 16px;
	}

	/* ============================================
	   RESPONSIVE DESIGN
	   ============================================ */
	@media (max-width: 768px) {
		.navbar-left {
			flex-direction: column;
			align-items: flex-start;
			gap: 1rem;
		}

		.breadcrumb {
			font-size: 0.75rem;
		}

		.content-header {
			flex-direction: column;
			align-items: flex-start;
		}

		.header-actions {
			width: 100%;
			flex-direction: column;
		}

		.view-mode-toggle,
		.refresh-button,
		.back-button {
			width: 100%;
			justify-content: center;
		}

		.main-content {
			padding: 1rem;
		}

		.page-title {
			font-size: 1.5rem;
		}
	}

	@media (max-width: 480px) {
		.brand-name {
			font-size: 1.25rem;
		}

		.brand-icon {
			width: 36px;
			height: 36px;
		}

		.statistics-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
