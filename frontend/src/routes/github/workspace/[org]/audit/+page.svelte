<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { githubClient } from '$lib/github.js';

	let orgName = '';
	let actions = [];
	let loading = true;
	let error = null;
	let workspaceData = null;
	let loadingactions = false;
	let loadingStage = 'Initializing...';
	let viewMode = 'detailed'; // 'detailed' or 'grouped'
	
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

		actions.forEach(action => {
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
		return status === '⚠️ outdated' || 
			   status === 'outdated' || 
			   status === '🔧 upgrade recommended' ||
			   status === '🚨 major upgrade needed';
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
		
		actions.forEach(action => {
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
		await loadActionDetails();
	});

	function goBack() {
		goto(`/github/workspace/${orgName}`);
	}

	// Load action details with pagination and search
	async function loadActionDetails(page = 1, search = '') {
		try {
			loadingactions = true;
			loadingStage = isCached ? 'Loading from cache...' : 'Fetching workflow data...';
			
			console.log(`🔍 Loading workflow actions for ${orgName} (page ${page}, search: "${search}")...`);

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

					actions.forEach(action => {
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
				action_name: action.action_name,  // Use action_name instead of action
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
				action_name: action.action_name,  // Use action_name instead of action
				current_version: action.current_version,
				latest_version: action.latest_version
			});
			
			if (result.success) {
				// Show success message
				alert(`✅ Pull request created successfully!\n\nPR #${result.pr_number}: ${result.pr_title}\n\nYou can view it at: ${result.pr_url}`);
				
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
			const outdatedActions = workflowGroup.actions.filter(action => 
				action.status === '⚠️ outdated' || action.status === 'outdated'
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
				actions: outdatedActions.map(action => ({
					action_name: action.action,
					current_version: action.current_version,
					latest_version: action.latest_version
				}))
			});
			
			if (result.success) {
				alert(`✅ Pull request created successfully!\n\nPR #${result.pr_number}: ${result.pr_title}\n\nYou can view it at: ${result.pr_url}`);
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

<div class="min-h-screen bg-gray-50">
	<div class="container mx-auto px-4 py-8">
		<header class="mb-8 flex items-center justify-between">
			<div>
				<h1 class="text-3xl font-bold text-gray-900">Actions Version Audit Table</h1>
				<p class="text-gray-600">Organization: <span class="font-mono">{orgName}</span></p>
			</div>
			<div class="flex items-center space-x-4">
				<!-- View Mode Toggle -->
				<div class="flex items-center space-x-2">
					<span class="text-sm text-gray-600">View:</span>
					<button
						on:click={() => (viewMode = 'detailed')}
						class="rounded px-3 py-1 text-sm font-medium transition-colors
                        {viewMode === 'detailed'
							? 'bg-blue-100 text-blue-700'
							: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
					>
						Detailed
					</button>
					<button
						on:click={() => (viewMode = 'grouped')}
						class="rounded px-3 py-1 text-sm font-medium transition-colors
                        {viewMode === 'grouped'
							? 'bg-blue-100 text-blue-700'
							: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
					>
						Grouped
					</button>
				</div>
				<!-- Refresh Button -->
				<button
					on:click={refreshActionDetails}
					disabled={loadingactions}
					class="flex items-center space-x-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
				>
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
						></path>
					</svg>
					<span>{loadingactions ? 'Refreshing...' : 'Refresh'}</span>
				</button>
				<button
					on:click={goBack}
					class="rounded-lg bg-gray-100 px-4 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-200"
				>
					← Back to Workspace
				</button>
			</div>
		</header>

		{#if loading || loadingactions}
			<div class="rounded-lg bg-white p-6 text-center shadow">
				<div
					class="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"
				></div>
				<p class="text-gray-600">Loading workflow actions...</p>
			</div>
		{:else if error}
			<div class="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
				<div class="flex items-center">
					<svg
						class="mr-2 h-5 w-5 text-red-400"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<span class="font-medium text-red-800">Error: {error}</span>
				</div>
			</div>
		{:else if actions.length === 0}
			<div class="rounded-lg bg-white p-6 text-center shadow">
				<p class="text-gray-600">No workflow actions found for this organization.</p>
			</div>
		{:else}
			<!-- Search and Pagination Controls -->
			<div class="mb-6 rounded-lg bg-white p-6 shadow">
				<div class="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
					<!-- Search Bar -->
					<div class="flex-1 md:max-w-md">
						<div class="relative">
							<svg
								class="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
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
								class="w-full rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
								on:input={handleSearch}
								value={searchQuery}
							/>
						</div>
					</div>

					<!-- Stats and Cache Status -->
					<div class="flex items-center space-x-4 text-sm">
						{#if isCached}
							<div class="flex items-center space-x-1 text-green-600">
								<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
						<div class="text-gray-500">
							{totalItems} total actions
						</div>
					</div>
				</div>

				<!-- Statistics -->
				<div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-5">
					<div class="flex items-center space-x-2">
						<div class="h-3 w-3 rounded-full bg-green-500"></div>
						<span class="text-sm text-gray-600">
							{statistics.up_to_date} up-to-date
						</span>
					</div>
					<div class="flex items-center space-x-2">
						<div class="h-3 w-3 rounded-full bg-red-500"></div>
						<span class="text-sm text-gray-600">
							{statistics.major_upgrade_needed} major upgrades
						</span>
					</div>
					<div class="flex items-center space-x-2">
						<div class="h-3 w-3 rounded-full bg-blue-500"></div>
						<span class="text-sm text-gray-600">
							{statistics.upgrade_recommended} recommended
						</span>
					</div>
					<div class="flex items-center space-x-2">
						<div class="h-3 w-3 rounded-full bg-yellow-500"></div>
						<span class="text-sm text-gray-600">
							{statistics.outdated} outdated
						</span>
					</div>
					<div class="flex items-center space-x-2">
						<div class="h-3 w-3 rounded-full bg-gray-500"></div>
						<span class="text-sm text-gray-600">
							{statistics.unknown} unknown
						</span>
					</div>
				</div>
			</div>

			<div class="overflow-hidden rounded-lg bg-white shadow">
				<div class="border-b border-gray-200 px-6 py-4">
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-semibold text-gray-900">
							{viewMode === 'detailed' ? 'Workflow Actions' : 'Workflow Summary'} ({viewMode ===
							'detailed'
								? actions.length
								: Object.keys(workflowGroups).length}
							{viewMode === 'detailed' ? 'actions' : 'workflows'})
						</h2>
						<div class="flex items-center space-x-2 text-sm text-gray-500">
							<svg
								class="h-4 w-4 text-green-500"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
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
									class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
								>
									Repository
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
								>
									Workflow Name
								</th>
								{#if viewMode === 'detailed'}
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Action
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Current Version
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Latest Version
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Status
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Actions
									</th>
								{:else}
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Actions Count
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Up to Date
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Major Upgrades
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Recommended
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Outdated
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
									>
										Summary
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
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
										<td class="whitespace-nowrap px-6 py-4">
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
										<td class="whitespace-nowrap px-6 py-4">
											<div class="text-sm text-gray-900">
												{action.workflow_name || action.workflow || 'Unknown Workflow'}
											</div>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<div class="font-mono text-sm text-gray-900">
												{action.action_name || action.action || 'No actions found'}
											</div>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<span class="rounded bg-gray-100 px-2 py-1 font-mono text-sm text-gray-700">
												{action.current_version || 'N/A'}
											</span>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<span class="rounded bg-gray-100 px-2 py-1 font-mono text-sm text-gray-700">
												{action.latest_version}
											</span>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<span
												class="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium {getStatusColorClass(action.status)}"
											>
												{action.status}
											</span>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											{#if isOutdated(action.status)}
												<button
													on:click={() => createPullRequest(action)}
													disabled={action.prCreating}
													class="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
												>
													{#if action.prCreating}
														<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
															<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
															<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
														</svg>
														Creating PR...
													{:else}
														<svg class="-ml-1 mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
														</svg>
														{action.status === '🚨 major upgrade needed' ? 'Major Update' : 'Fix via PR'}
													{/if}
												</button>
											{:else if isUpToDate(action.status)}
												<span class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700">
													✅ Up to date
												</span>
											{:else}
												<span class="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-500">
													-
												</span>
											{/if}
										</td>
									</tr>
								{/each}
							{:else}
								{#each Object.values(workflowGroups) as workflowGroup, index}
									<tr class="transition-colors duration-200 hover:bg-gray-50">
										<td class="whitespace-nowrap px-6 py-4">
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
										<td class="whitespace-nowrap px-6 py-4">
											<div class="text-sm text-gray-900">
												{workflowGroup.workflow_name || workflowGroup.workflow || 'Unknown Workflow'}
											</div>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<div class="text-sm text-gray-900">
												{workflowGroup.hasActions ? workflowGroup.total : 'No actions'}
											</div>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<span class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-green-100 text-green-800">
												{workflowGroup.upToDate}
											</span>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<span class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-red-100 text-red-800">
												{workflowGroup.majorUpgradeNeeded}
											</span>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<span class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800">
												{workflowGroup.upgradeRecommended}
											</span>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
											<span class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800">
												{workflowGroup.outdated}
											</span>
										</td>
										<td class="whitespace-nowrap px-6 py-4">
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
										<td class="whitespace-nowrap px-6 py-4">
											{#if workflowGroup.majorUpgradeNeeded > 0 || workflowGroup.upgradeRecommended > 0 || workflowGroup.outdated > 0}
												<button
													on:click={() => fixAllOutdatedInWorkflow(workflowGroup)}
													class="inline-flex items-center rounded-md px-3 py-2 text-sm font-semibold text-white shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2
													{workflowGroup.majorUpgradeNeeded > 0 
														? 'bg-red-600 hover:bg-red-500 focus-visible:outline-red-600' 
														: 'bg-blue-600 hover:bg-blue-500 focus-visible:outline-blue-600'}"
												>
													<svg class="-ml-1 mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
													</svg>
													{workflowGroup.majorUpgradeNeeded > 0 
														? `Major Update (${workflowGroup.majorUpgradeNeeded + workflowGroup.upgradeRecommended + workflowGroup.outdated})` 
														: `Fix All (${workflowGroup.upgradeRecommended + workflowGroup.outdated})`}
												</button>
											{:else if workflowGroup.hasActions}
												<span class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700">
													✅ All up to date
												</span>
											{:else}
												<span class="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-500">
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
							<div class="flex-1 flex justify-between sm:hidden">
								<!-- Mobile pagination -->
								<button
									on:click={previousPage}
									disabled={!hasPrevious}
									class="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
								>
									Previous
								</button>
								<button
									on:click={nextPage}
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
											on:click={previousPage}
											disabled={!hasPrevious}
											class="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
										>
											<span class="sr-only">Previous</span>
											<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd" />
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
													on:click={() => goToPage(pageNum)}
													class="relative inline-flex items-center px-4 py-2 text-sm font-semibold ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 {pageNum === currentPage ? 'z-10 bg-blue-600 text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600' : 'text-gray-900'}"
												>
													{pageNum}
												</button>
											{/if}
										{/each}
										
										<!-- Next button -->
										<button
											on:click={nextPage}
											disabled={!hasNext}
											class="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
										>
											<span class="sr-only">Next</span>
											<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
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
