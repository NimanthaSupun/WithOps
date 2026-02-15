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

<div class="audit-page {darkMode ? 'dark' : 'light'}">
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
				<a href="/github/workspace/{orgName}" class="nav-link">{orgName}</a>
				<a href="/github/workspace/{orgName}/audit" class="nav-link active">Audit</a>
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
			<a href="/dashboard" class="breadcrumb-item">WithOps</a>
			<span class="breadcrumb-sep">/</span>
			<a href="/organizations" class="breadcrumb-item">Organizations</a>
			<span class="breadcrumb-sep">/</span>
			<a href="/github/workspace/{orgName}" class="breadcrumb-item">{orgName}</a>
			<span class="breadcrumb-sep">/</span>
			<span class="breadcrumb-item active">Audit</span>
		</div>
		<div class="system-status">
			<div class="status-pulse"></div>
			AUDIT: ACTIVE
		</div>
	</div>

	<div class="page-content">
		<main class="page-main">
			<!-- View Header -->
			<header class="view-header">
				<div class="title-group">
					<h1>Actions Version Audit</h1>
					<p>
						Audit and remediate GitHub Actions version compliance across <span class="accent-text"
							>{orgName}</span
						>.
					</p>
				</div>
				<div class="header-cta">
					<button onclick={goBack} class="btn btn-secondary">
						<svg
							width="14"
							height="14"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M19 12H5M12 19l-7-7 7-7" />
						</svg>
						Workspace
					</button>
					<button
						onclick={refreshActionDetails}
						disabled={loadingactions}
						class="btn btn-secondary"
					>
						<svg
							width="14"
							height="14"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path
								d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
							/>
						</svg>
						{loadingactions ? 'Syncing...' : 'Sync'}
					</button>
				</div>
			</header>

			{#if loading || loadingactions}
				<div class="center-state">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="loader-text">
						{loading ? 'SCANNING WORKFLOW ACTIONS...' : 'SCANNING WORKFLOWS...'}
					</div>
				</div>
			{:else if error}
				<div class="error-banner">
					<p class="error-text">{error}</p>
					<button onclick={() => loadActionDetails(1, '')} class="btn btn-primary">Retry</button>
				</div>
			{:else if actions.length === 0}
				<div class="center-state">
					<p class="empty-text">No workflow actions found for this organization.</p>
					<button onclick={refreshActionDetails} class="btn btn-primary" style="margin-top: 1.5rem;"
						>Scan Now</button
					>
				</div>
			{:else}
				<!-- Stats Cards Row -->
				<div class="stats-grid">
					<div class="stat-card">
						<div class="stat-card-top">
							<span class="stat-card-label">Up to Date</span>
							<div class="stat-dot dot-success"></div>
						</div>
						<span class="stat-card-value">{statistics.up_to_date}</span>
					</div>
					<div class="stat-card">
						<div class="stat-card-top">
							<span class="stat-card-label">Major Upgrades</span>
							<div class="stat-dot dot-error"></div>
						</div>
						<span class="stat-card-value">{statistics.major_upgrade_needed}</span>
					</div>
					<div class="stat-card">
						<div class="stat-card-top">
							<span class="stat-card-label">Recommended</span>
							<div class="stat-dot dot-accent"></div>
						</div>
						<span class="stat-card-value">{statistics.upgrade_recommended}</span>
					</div>
					<div class="stat-card">
						<div class="stat-card-top">
							<span class="stat-card-label">Outdated</span>
							<div class="stat-dot dot-warning"></div>
						</div>
						<span class="stat-card-value">{statistics.outdated}</span>
					</div>
				</div>

				<!-- Controls Row: Filter + Search -->
				<div class="controls-row">
					<div class="filter-nav">
						<button
							class="filter-btn {viewMode === 'detailed' ? 'active' : ''}"
							onclick={() => (viewMode = 'detailed')}
						>
							DETAILED <span class="count-badge">{actions.length}</span>
						</button>
						<button
							class="filter-btn {viewMode === 'grouped' ? 'active' : ''}"
							onclick={() => (viewMode = 'grouped')}
						>
							GROUPED <span class="count-badge">{Object.keys(workflowGroups).length}</span>
						</button>
					</div>

					<div class="controls-right">
						{#if isCached}
							<div class="cached-pill">
								<svg
									width="12"
									height="12"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"><path d="M13 10V3L4 14h7v7l9-11h-7z" /></svg
								>
								Cached
							</div>
						{/if}
						<span class="total-label">{totalItems} actions</span>
						<div class="search-box">
							<svg
								class="search-icon"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
							>
								<circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
							</svg>
							<input
								type="text"
								placeholder="Search..."
								class="search-input"
								oninput={handleSearch}
								value={searchQuery}
							/>
						</div>
					</div>
				</div>

				<!-- Data Table -->
				<div class="table-container">
					<div class="table-scroll">
						<table class="data-table">
							<thead>
								<tr>
									<th>Repository</th>
									<th>Workflow</th>
									{#if viewMode === 'detailed'}
										<th>Action</th>
										<th>Current</th>
										<th>Latest</th>
										<th>Status</th>
										<th>Fix</th>
									{:else}
										<th>Count</th>
										<th>Current</th>
										<th>Major</th>
										<th>Recommended</th>
										<th>Outdated</th>
										<th>Summary</th>
										<th>Fix</th>
									{/if}
								</tr>
							</thead>
							<tbody>
								{#if viewMode === 'detailed'}
									{#each actions as action, index}
										<tr>
											<td>
												<span class="cell-mono">{action.repo_name}</span>
											</td>
											<td>{action.workflow_name || action.workflow || 'Unknown'}</td>
											<td>
												<span class="cell-mono"
													>{action.action_name || action.action || 'No actions found'}</span
												>
											</td>
											<td><span class="version-tag">{action.current_version || 'N/A'}</span></td>
											<td><span class="version-tag">{action.latest_version}</span></td>
											<td>
												{#if isUpToDate(action.status)}
													<span class="status-tag connected">CURRENT</span>
												{:else if action.status === '🚨 major upgrade needed'}
													<span class="status-tag critical">CRITICAL</span>
												{:else if action.status === '🔧 upgrade recommended'}
													<span class="status-tag recommended">UPGRADE</span>
												{:else if action.status === '⚠️ outdated' || action.status === 'outdated'}
													<span class="status-tag outdated">OUTDATED</span>
												{:else}
													<span class="status-tag pending">{action.status}</span>
												{/if}
											</td>
											<td>
												{#if isOutdated(action.status)}
													<button
														class="btn btn-sm btn-primary"
														onclick={() => createPullRequest(action)}
														disabled={action.prCreating}
													>
														{#if action.prCreating}
															<span class="btn-spinner"></span> Creating...
														{:else}
															Fix via PR <span class="button-arrow">→</span>
														{/if}
													</button>
												{:else if isUpToDate(action.status)}
													<span class="status-tag connected">OK</span>
												{:else}
													<span class="cell-muted">—</span>
												{/if}
											</td>
										</tr>
									{/each}
								{:else}
									{#each Object.values(workflowGroups) as workflowGroup, index}
										<tr>
											<td>
												<span class="cell-mono">{workflowGroup.repo_name}</span>
											</td>
											<td>{workflowGroup.workflow_name || workflowGroup.workflow || 'Unknown'}</td>
											<td>{workflowGroup.hasActions ? workflowGroup.total : '—'}</td>
											<td><span class="status-tag connected">{workflowGroup.upToDate}</span></td>
											<td
												><span class="status-tag critical">{workflowGroup.majorUpgradeNeeded}</span
												></td
											>
											<td
												><span class="status-tag recommended"
													>{workflowGroup.upgradeRecommended}</span
												></td
											>
											<td><span class="status-tag outdated">{workflowGroup.outdated}</span></td>
											<td>
												{#if workflowGroup.hasActions}
													{#if workflowGroup.majorUpgradeNeeded > 0}
														<span class="status-tag critical"
															>CRITICAL ({workflowGroup.majorUpgradeNeeded})</span
														>
													{:else if workflowGroup.upgradeRecommended > 0 || workflowGroup.outdated > 0}
														<span class="status-tag outdated"
															>UPDATES ({workflowGroup.upgradeRecommended +
																workflowGroup.outdated})</span
														>
													{:else}
														<span class="status-tag connected">ALL CURRENT</span>
													{/if}
												{:else}
													<span class="cell-muted">No actions</span>
												{/if}
											</td>
											<td>
												{#if workflowGroup.majorUpgradeNeeded > 0 || workflowGroup.upgradeRecommended > 0 || workflowGroup.outdated > 0}
													<button
														class="btn btn-sm btn-primary"
														onclick={() => fixAllOutdatedInWorkflow(workflowGroup)}
													>
														Fix All ({workflowGroup.majorUpgradeNeeded +
															workflowGroup.upgradeRecommended +
															workflowGroup.outdated})
														<span class="button-arrow">→</span>
													</button>
												{:else if workflowGroup.hasActions}
													<span class="status-tag connected">OK</span>
												{:else}
													<span class="cell-muted">—</span>
												{/if}
											</td>
										</tr>
									{/each}
								{/if}
							</tbody>
						</table>
					</div>

					<!-- Pagination -->
					{#if totalPages > 1}
						<div class="pagination-bar">
							<span class="pagination-info">
								Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> — {totalItems}
								total
							</span>
							<div class="pagination-controls">
								<button
									class="btn btn-sm btn-secondary"
									onclick={previousPage}
									disabled={!hasPrevious}
									aria-label="Previous page"
								>
									<svg
										width="14"
										height="14"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"><path d="M15 18l-6-6 6-6" /></svg
									>
								</button>
								{#each Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
									const startPage = Math.max(1, currentPage - 2);
									return startPage + i;
								}) as pageNum}
									{#if pageNum <= totalPages}
										<button
											class="btn btn-sm {pageNum === currentPage ? 'btn-primary' : 'btn-secondary'}"
											onclick={() => goToPage(pageNum)}
										>
											{pageNum}
										</button>
									{/if}
								{/each}
								<button
									class="btn btn-sm btn-secondary"
									onclick={nextPage}
									disabled={!hasNext}
									aria-label="Next page"
								>
									<svg
										width="14"
										height="14"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"><path d="M9 18l6-6-6-6" /></svg
									>
								</button>
							</div>
						</div>
					{/if}
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

	.audit-page.dark {
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
		--card-shadow: none;
	}

	.audit-page.light {
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
		--card-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
	}

	/* Global Reset */
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	.audit-page {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
		overflow-x: hidden;
	}

	/* Architectural Backdrop */
	.audit-page::before {
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

	.page-content {
		position: relative;
		z-index: 10;
		padding-bottom: 5rem;
	}

	/* ============================================
	   LOADER / CENTER STATE
	   ============================================ */
	.center-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 6rem 2rem;
		text-align: center;
		gap: 1rem;
	}

	.loader-icon {
		width: 40px;
		height: 40px;
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
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	/* ============================================
	   HEADER NAVIGATION
	   ============================================ */
	.dashboard-header {
		height: var(--nav-height);
		background: var(--bg-app);
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
		padding: 0.5rem 0;
		position: relative;
	}

	.nav-link:hover,
	.nav-link.active {
		color: var(--text-primary);
	}

	.nav-link.active::after {
		content: '';
		position: absolute;
		bottom: -1px;
		left: 0;
		right: 0;
		height: 2px;
		background: var(--accent);
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
	   TECHNICAL BAR
	   ============================================ */
	.technical-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 0 2rem;
		display: flex;
		align-items: center;
		height: 40px;
	}

	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.breadcrumb-item {
		color: var(--text-muted);
		text-decoration: none;
		transition: color 0.15s;
	}

	.breadcrumb-item:hover {
		color: var(--text-secondary);
	}
	.breadcrumb-item.active {
		color: var(--accent);
	}
	.breadcrumb-sep {
		color: var(--border);
	}

	.system-status {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
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
	   PAGE MAIN
	   ============================================ */
	.page-main {
		max-width: 1440px;
		margin: 0 auto;
		padding: 2.5rem 2rem;
	}

	.view-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		margin-bottom: 2rem;
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
		max-width: 500px;
		line-height: 1.5;
	}

	.accent-text {
		color: var(--accent);
		font-weight: 600;
	}

	.header-cta {
		display: flex;
		gap: 0.75rem;
	}

	/* ============================================
	   ERROR / EMPTY STATES
	   ============================================ */
	.error-banner {
		background: var(--bg-surface-alt);
		border: 1px solid var(--error);
		border-radius: 12px;
		padding: 1.25rem;
		margin-bottom: 2rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.error-text {
		color: var(--error);
		font-weight: 600;
		font-size: 0.875rem;
	}
	.empty-text {
		color: var(--text-secondary);
		font-size: 0.9375rem;
	}

	/* ============================================
	   STATS CARDS
	   ============================================ */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.stat-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		transition: all 0.2s var(--ease-premium);
		box-shadow: var(--card-shadow);
	}

	.stat-card:hover {
		border-color: var(--border-focus);
	}

	.stat-card-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.stat-card-label {
		font-size: 0.65rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.stat-card-value {
		font-family: var(--font-mono);
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.stat-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}

	.dot-success {
		background: var(--success);
	}
	.dot-error {
		background: var(--error);
	}
	.dot-accent {
		background: var(--accent);
	}
	.dot-warning {
		background: var(--warning);
	}

	/* ============================================
	   CONTROLS ROW
	   ============================================ */
	.controls-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}

	.filter-nav {
		display: flex;
		gap: 0.25rem;
		background: var(--bg-surface-alt);
		padding: 0.25rem;
		border-radius: 8px;
		border: 1px solid var(--border);
	}

	.filter-btn {
		background: none;
		border: none;
		padding: 0.4rem 0.75rem;
		border-radius: 6px;
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.filter-btn:hover {
		color: var(--text-primary);
	}

	.filter-btn.active {
		background: var(--bg-surface);
		color: var(--accent);
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.count-badge {
		font-size: 0.6rem;
		background: var(--border);
		color: var(--text-muted);
		padding: 0.1rem 0.35rem;
		border-radius: 4px;
	}

	.controls-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.cached-pill {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--accent);
		padding: 0.25rem 0.5rem;
		border: 1px solid var(--border);
		border-radius: 4px;
	}

	.total-label {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text-muted);
	}

	.search-box {
		position: relative;
	}

	.search-icon {
		position: absolute;
		left: 0.625rem;
		top: 50%;
		transform: translateY(-50%);
		color: var(--text-muted);
		pointer-events: none;
	}

	.search-input {
		padding: 0.4rem 0.75rem 0.4rem 2rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text-primary);
		font-size: 0.8125rem;
		font-family: var(--font-sans);
		width: 200px;
		transition: all 0.15s;
	}

	.search-input:focus {
		outline: none;
		border-color: var(--border-focus);
		width: 280px;
	}

	.search-input::placeholder {
		color: var(--text-muted);
	}

	/* ============================================
	   DATA TABLE
	   ============================================ */
	.table-container {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
		box-shadow: var(--card-shadow);
	}

	.table-scroll {
		overflow-x: auto;
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.8125rem;
	}

	.data-table thead {
		background: var(--bg-surface-alt);
	}

	.data-table th {
		padding: 0.625rem 1rem;
		text-align: left;
		font-size: 0.65rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid var(--border);
		white-space: nowrap;
	}

	.data-table td {
		padding: 0.625rem 1rem;
		border-bottom: 1px solid var(--border);
		color: var(--text-secondary);
		white-space: nowrap;
	}

	.data-table tbody tr {
		transition: background 0.1s;
	}

	.data-table tbody tr:hover {
		background: var(--bg-surface-alt);
	}

	.data-table tbody tr:last-child td {
		border-bottom: none;
	}

	.cell-mono {
		font-family: var(--font-mono);
		font-size: 0.8125rem;
		color: var(--text-primary);
		font-weight: 500;
	}

	.cell-muted {
		color: var(--text-muted);
	}

	.version-tag {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		padding: 0.15rem 0.4rem;
		border-radius: 4px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		color: var(--text-secondary);
	}

	/* ============================================
	   STATUS TAGS
	   ============================================ */
	.status-tag {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-size: 0.65rem;
		font-weight: 600;
		font-family: var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.status-tag.connected {
		color: var(--success);
		border: 1px solid rgba(16, 185, 129, 0.15);
	}

	.status-tag.critical {
		color: var(--error);
		border: 1px solid rgba(239, 68, 68, 0.15);
	}

	.status-tag.outdated {
		color: var(--warning);
		border: 1px solid rgba(245, 158, 11, 0.15);
	}

	.status-tag.recommended {
		color: var(--accent);
		border: 1px solid rgba(0, 173, 239, 0.15);
	}

	.status-tag.pending {
		color: var(--text-muted);
		border: 1px solid var(--border);
	}

	/* ============================================
	   PAGINATION
	   ============================================ */
	.pagination-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		border-top: 1px solid var(--border);
	}

	.pagination-info {
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	.pagination-info strong {
		color: var(--text-secondary);
	}

	.pagination-controls {
		display: flex;
		gap: 0.25rem;
	}

	/* ============================================
	   BUTTONS
	   ============================================ */
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.625rem 1rem;
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
		opacity: 0.4;
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
		color: var(--text-secondary);
	}

	.btn-sm {
		padding: 0.3rem 0.6rem;
		font-size: 0.7rem;
		border-radius: 6px;
		gap: 0.3rem;
	}

	.button-arrow {
		font-size: 0.9rem;
		transition: transform 0.2s var(--ease-premium);
	}

	.btn:hover .button-arrow {
		transform: translateX(3px);
	}

	.btn-spinner {
		width: 12px;
		height: 12px;
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
	@media (max-width: 1024px) {
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 768px) {
		.page-main {
			padding: 1.5rem 1rem;
		}
		.nav-menu {
			display: none;
		}

		.view-header {
			flex-direction: column;
			align-items: flex-start;
			gap: 1.25rem;
		}

		.controls-row {
			flex-direction: column;
			align-items: flex-start;
		}

		.controls-right {
			flex-wrap: wrap;
		}

		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.title-group h1 {
			font-size: 1.375rem;
		}
	}

	@media (max-width: 480px) {
		.stats-grid {
			grid-template-columns: 1fr;
		}
		.header-cta {
			flex-direction: column;
			width: 100%;
		}
		.btn {
			width: 100%;
		}
		.search-input {
			width: 160px;
		}
		.search-input:focus {
			width: 200px;
		}
	}
</style>
