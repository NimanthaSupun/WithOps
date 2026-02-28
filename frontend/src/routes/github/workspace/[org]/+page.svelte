<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { githubClient } from '$lib/github.js';
	import { repositoryTreeClient } from '$lib/repositoryTree.js';
	import { userOrganizations, appStore, isDarkMode } from '$lib/stores.js';
	import GitHubCacheNotification from '$lib/components/GitHubCacheNotification.svelte';

	let loading = $state(true);
	let error = $state(null);
	let orgName = $state('');
	let workspaceData = $state(null);
	let selectedWorkflow = $state(null);
	let showWorkflowModal = $state(false);
	let workflowContent = $state('');
	let loadingWorkflow = $state(false);
	let loadingStage = $state('Initializing...');
	let authorizationChecked = $state(false);
	let userAuthorized = $state(false);
	let refreshing = $state(false);

	// Theme management
	let darkMode = $state(false);
	isDarkMode.subscribe((value) => {
		darkMode = value;
	});

	// Sidebar state
	let sidebarCollapsed = $state(false);

	// Tab management
	let activeTab = $state('repositories');
	let detailedWorkflows = $state([]);
	let loadingDetailedWorkflows = $state(false);

	// Real-time updates
	let realTimeEnabled = $state(true);
	let lastSyncTime = $state(null);
	let realtimeUpdateCount = $state(0);

	// Workflow action menu
	let activeWorkflowMenu = $state(null);

	// Repository action menu
	let activeRepoMenu = $state(null);

	// Add to Project modal
	let showAddToProjectModal = $state(false);
	let selectedWorkflowToAdd = $state(null);
	let projectTreeData = $state([]);
	let selectedProjectFolder = $state(null);
	let newFolderName = $state('');
	let showNewFolderInput = $state(false);
	let addingWorkflowToProject = $state(false);
	let selectedParentFolder = $state(null);

	// Add Repository to Project modal
	let showAddRepoToProjectModal = $state(false);
	let selectedRepoToAdd = $state(null);
	let addingRepoToProject = $state(false);
	let repoTreeData = $state([]);
	let selectedRepoFolder = $state(null);

	onMount(async () => {
		orgName = $page.params.org;
		console.log(`🚀 Loading workspace for organization: ${orgName}`);

		// Initialize theme
		isDarkMode.init();

		loadingStage = 'Checking authentication...';

		try {
			const orgsResult = await githubClient.getMyOrganizations();

			if (orgsResult.success) {
				console.log('✅ Authentication confirmed via API call');
				appStore.setUserOrganizations(orgsResult.organizations);
				userAuthorized = appStore.isUserAuthorizedForOrg(orgName, orgsResult.organizations);
				authorizationChecked = true;

				if (userAuthorized) {
					console.log('✅ User authorized for organization, loading workspace data');
					setupRealtimeUpdates();
					startAutoSync();
					await loadWorkspaceData();
				} else {
					error = `Access denied. You don't have permission to access organization '${orgName}'. This organization may have been installed by another user or the app may not be installed.`;
					loading = false;
				}
			} else {
				console.error('❌ Authentication failed:', orgsResult.error);

				if (orgsResult.error && orgsResult.error.includes('Authentication required')) {
					console.log('🔄 Redirecting to main page for authentication...');
					goto('/');
					return;
				}

				error = orgsResult.error || 'Authentication failed. Please try logging in again.';
				loading = false;
			}
		} catch (err) {
			console.error('❌ Failed to check authentication:', err);
			error = `Authentication failed: ${err.message}`;
			loading = false;
		}
	});

	async function loadWorkspaceData() {
		try {
			loading = true;
			error = null;

			console.log(`Loading workspace data for organization: ${orgName}`);

			const cached = githubClient.getCachedData(`workspace_${orgName}`);
			if (cached) {
				console.log('🚀 Loading from cache instantly');
				workspaceData = cached;
				loading = false;
				return;
			}

			loadingStage = 'Connecting to GitHub...';

			console.log(`🔍 Loading workspace data directly for ${orgName}...`);

			loadingStage = 'Fetching repositories and workflows...';
			const result = await githubClient.getOrganizationWorkspace(orgName);

			if (result.success) {
				loadingStage = 'Processing data...';
				workspaceData = result;
				console.log('Workspace data loaded:', workspaceData);

				if (workspaceData.workflows) {
					console.log('🚀 Starting batch prefetch of workflows');
					githubClient.batchPreloadWorkflows(orgName, workspaceData.workflows);
				}

				loadingStage = 'Complete!';
			} else {
				throw new Error(result.error);
			}
		} catch (err) {
			console.error('Failed to load workspace data:', err);

			const errorMessage = err.message || err.toString();

			if (
				err.error_type === 'app_not_installed' ||
				(errorMessage.includes('app_not_installed') && !errorMessage.includes('network')) ||
				(errorMessage.includes('not installed') && errorMessage.includes('organization'))
			) {
				error = `GitHub App is no longer installed in ${orgName}. Please reinstall the app to access the workspace.`;
			} else if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
				error = `Access denied to ${orgName}. You may not have permission to access this organization.`;
			} else if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
				error = `Network error: Unable to connect to server. Please check your connection and try again.`;
			} else {
				error = `Failed to load workspace: ${errorMessage}`;
			}

			loadingStage = 'Error occurred';
		} finally {
			loading = false;
		}
	}

	async function viewWorkflowContent(workflow, repo) {
		try {
			if (!repo || !repo.name) {
				console.error('❌ Invalid repo object:', repo);
				workflowContent = `# Error loading workflow content\n# Repository information is missing or invalid`;
				showWorkflowModal = true;
				loadingWorkflow = false;
				return;
			}

			selectedWorkflow = { ...workflow, repo: repo.name };
			showWorkflowModal = true;

			const cacheKey = `workflow_${orgName}_${repo.name}_${workflow.path}`;
			const cached = githubClient.getCachedData(cacheKey);

			if (cached) {
				console.log('🚀 Displaying cached YAML instantly');
				workflowContent = cached.content;
				loadingWorkflow = false;
				githubClient.smartPrefetch(orgName, repo.name, workflow.path);
				return;
			}

			loadingWorkflow = true;

			const result = await githubClient.getWorkflowContent(orgName, repo.name, workflow.path);

			if (result.success) {
				workflowContent = result.content;
				console.log('📄 YAML content loaded');
				githubClient.smartPrefetch(orgName, repo.name, workflow.path);
			} else {
				workflowContent = `# Error loading workflow content\n# ${result.error}`;
			}
		} catch (error) {
			console.error('Failed to load workflow content:', error);
			workflowContent = `# Error loading workflow content\n# ${error.message}`;
		} finally {
			loadingWorkflow = false;
		}
	}

	async function switchToWorkflowsTab() {
		if (activeTab === 'workflows') return;

		activeTab = 'workflows';

		if (detailedWorkflows.length === 0 && !loadingDetailedWorkflows) {
			await loadDetailedWorkflows();
		}
	}

	async function loadDetailedWorkflows() {
		if (!workspaceData || !workspaceData.total_workflows || workspaceData.total_workflows === 0) {
			detailedWorkflows = [];
			return;
		}

		try {
			loadingDetailedWorkflows = true;
			console.log(`🔍 Loading detailed workflow information for ${orgName}...`);

			const result = await githubClient.getDetailedWorkflows(orgName);

			if (result.success) {
				detailedWorkflows = result.workflows || [];
				console.log(`✅ Loaded ${detailedWorkflows.length} detailed workflows`);
			} else {
				console.error('Failed to load detailed workflows:', result.error);
				detailedWorkflows = workspaceData.workflows || [];
			}
		} catch (err) {
			console.error('Error loading detailed workflows:', err);
			detailedWorkflows = workspaceData.workflows || [];
		} finally {
			loadingDetailedWorkflows = false;
		}
	}

	function formatRelativeTime(dateString) {
		if (!dateString) return 'Never';

		const date = new Date(dateString);
		const now = new Date();
		const diffInSeconds = Math.floor((now - date) / 1000);

		if (diffInSeconds < 60) return 'Just now';
		if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
		if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
		if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)} days ago`;
		if (diffInSeconds < 31536000) return `${Math.floor(diffInSeconds / 2592000)} months ago`;
		return `${Math.floor(diffInSeconds / 31536000)} years ago`;
	}

	function closeWorkflowModal() {
		showWorkflowModal = false;
		selectedWorkflow = null;
		workflowContent = '';
	}

	async function forceRefresh() {
		try {
			refreshing = true;
			error = null;

			console.log(`🔄 Force refreshing data for ${orgName}...`);

			const result = await githubClient.forceRefreshOrganization(orgName);

			if (result.success) {
				workspaceData = result;
				console.log('✅ Organization data refreshed successfully');

				detailedWorkflows = [];
				if (activeTab === 'workflows') {
					await loadDetailedWorkflows();
				}
			} else {
				throw new Error(result.error || 'Failed to refresh organization data');
			}
		} catch (err) {
			console.error('Failed to refresh organization:', err);
			error = `Failed to refresh data: ${err.message}`;
		} finally {
			refreshing = false;
		}
	}

	function setupRealtimeUpdates() {
		console.log('🔔 Setting up real-time GitHub cache listeners');

		window.addEventListener('github-github_workspace_refreshed', handleWorkspaceRefreshed);
		window.addEventListener('github-github_workflows_refreshed', handleWorkflowsRefreshed);
		window.addEventListener('github-github_actions_refreshed', handleActionsRefreshed);

		window.addEventListener('github-workspace_updated', (event) => {
			const { organization, changes, timestamp } = event.detail;

			if (organization === orgName) {
				console.log('🔄 Real-time workspace update received:', changes);
				realtimeUpdateCount++;
				lastSyncTime = new Date(timestamp);
				loadWorkspaceData();
			}
		});
	}

	function handleWorkspaceRefreshed(event) {
		const data = event.detail;
		if (data.organization !== orgName) return;

		console.log('✨ Workspace cache refreshed, reloading data...');
		lastSyncTime = new Date();
		realtimeUpdateCount++;
		loadWorkspaceData();
	}

	function handleWorkflowsRefreshed(event) {
		const data = event.detail;
		if (data.organization !== orgName) return;

		console.log('✨ Workflows cache refreshed, reloading...');
		lastSyncTime = new Date();
		realtimeUpdateCount++;

		if (activeTab === 'workflows') {
			loadDetailedWorkflows();
		}
	}

	function handleActionsRefreshed(event) {
		const data = event.detail;
		if (data.organization !== orgName) return;

		console.log('✨ Actions cache refreshed');
		lastSyncTime = new Date();
		realtimeUpdateCount++;
	}

	function startAutoSync() {
		console.log('🔄 Auto-sync via background worker + WebSocket enabled');
	}

	function toggleTheme() {
		isDarkMode.toggle();
	}

	function toggleSidebar() {
		sidebarCollapsed = !sidebarCollapsed;
	}

	function toggleWorkflowActionMenu(workflowId) {
		if (activeWorkflowMenu === workflowId) {
			activeWorkflowMenu = null;
		} else {
			activeWorkflowMenu = workflowId;
		}
	}

	function toggleRepoActionMenu(repoId) {
		if (activeRepoMenu === repoId) {
			activeRepoMenu = null;
		} else {
			activeRepoMenu = repoId;
		}
	}

	function handleGlobalClick(event) {
		if (!event.target.closest('.relative')) {
			activeWorkflowMenu = null;
			activeRepoMenu = null;
		}
	}

	function viewRepository(repo) {
		window.open(repo.html_url, '_blank');
	}

	// Add to Project modal functions
	async function openAddToProjectModal(workflow) {
		selectedWorkflowToAdd = workflow;
		await loadProjectTreeData();
		showAddToProjectModal = true;
	}

	function closeAddToProjectModal() {
		showAddToProjectModal = false;
		selectedWorkflowToAdd = null;
		selectedProjectFolder = null;
		newFolderName = '';
		showNewFolderInput = false;
		selectedParentFolder = null;
	}

	async function loadProjectTreeData() {
		try {
			const result = await githubClient.getProjectTreeData(orgName);
			if (result.success) {
				projectTreeData = result.data || [];
			} else {
				projectTreeData = [];
			}
		} catch (err) {
			console.error('Failed to load project tree data:', err);
			projectTreeData = [];
		}
	}

	async function loadRepositoryTreeData() {
		try {
			const result = await repositoryTreeClient.getRepositoryTree(orgName);
			if (result.success) {
				repoTreeData = result.data || [];
			} else {
				repoTreeData = [];
			}
		} catch (err) {
			console.error('Failed to load repository tree data:', err);
			repoTreeData = [];
		}
	}

	function createNewFolderInModal() {
		if (!newFolderName.trim()) return;

		const newFolder = {
			id: `folder-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
			name: newFolderName.trim(),
			type: 'folder',
			children: [],
			created_at: new Date().toISOString()
		};

		const isRepoModal = showAddRepoToProjectModal;
		const targetTreeData = isRepoModal ? repoTreeData : projectTreeData;

		if (selectedParentFolder) {
			if (!selectedParentFolder.children) {
				selectedParentFolder.children = [];
			}
			selectedParentFolder.children.push(newFolder);
		} else {
			targetTreeData.push(newFolder);
		}

		if (isRepoModal) {
			selectedRepoFolder = newFolder;
			repoTreeData = [...repoTreeData];
		} else {
			selectedProjectFolder = newFolder;
			projectTreeData = [...projectTreeData];
		}

		newFolderName = '';
		showNewFolderInput = false;
		selectedParentFolder = null;
	}

	function getFlattenedFolders(folders, depth = 0) {
		let result = [];
		for (const folder of folders) {
			if (folder.type === 'folder') {
				result.push({ ...folder, depth });
				if (folder.children && folder.children.length > 0) {
					result.push(
						...getFlattenedFolders(
							folder.children.filter((child) => child.type === 'folder'),
							depth + 1
						)
					);
				}
			}
		}
		return result;
	}

	function countWorkflowsInFolder(folder) {
		if (!folder.children) return 0;
		let count = 0;
		for (const child of folder.children) {
			if (child.type === 'workflow' || child.type === 'repository') {
				count++;
			} else if (child.type === 'folder') {
				count += countWorkflowsInFolder(child);
			}
		}
		return count;
	}

	async function addWorkflowToProject() {
		if (!selectedWorkflowToAdd || !selectedProjectFolder) return;

		try {
			addingWorkflowToProject = true;

			const workflowContentResult = await githubClient.getWorkflowContent(
				orgName,
				selectedWorkflowToAdd.repository,
				selectedWorkflowToAdd.path
			);

			if (!workflowContentResult.success) {
				throw new Error('Failed to fetch workflow content');
			}

			const newWorkflowItem = {
				id: `workflow-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
				name: selectedWorkflowToAdd.name,
				type: 'workflow',
				content: workflowContentResult.content,
				metadata: {
					triggers: selectedWorkflowToAdd.triggers || [],
					repository: selectedWorkflowToAdd.repository,
					path: selectedWorkflowToAdd.path,
					lastModified: new Date().toISOString(),
					addedFrom: 'workspace'
				}
			};

			if (!selectedProjectFolder.children) {
				selectedProjectFolder.children = [];
			}
			selectedProjectFolder.children.push(newWorkflowItem);

			await saveProjectTreeData();

			console.log(`✅ Workflow "${selectedWorkflowToAdd.name}" added to project successfully!`);
			closeAddToProjectModal();
		} catch (err) {
			console.error('Failed to add workflow to project:', err);
			alert('Failed to add workflow to project');
		} finally {
			addingWorkflowToProject = false;
		}
	}

	async function saveProjectTreeData() {
		try {
			const result = await githubClient.saveProjectTreeData(orgName, projectTreeData);
			if (!result.success) {
				throw new Error(result.error || 'Failed to save project data');
			}
		} catch (err) {
			console.error('Failed to save project tree data:', err);
			throw err;
		}
	}

	async function saveRepositoryTreeData() {
		try {
			const result = await repositoryTreeClient.saveRepositoryTree(orgName, repoTreeData);
			if (!result.success) {
				throw new Error(result.error || 'Failed to save repository tree data');
			}
		} catch (err) {
			console.error('Failed to save repository tree data:', err);
			throw err;
		}
	}

	async function openAddRepoToProjectModal(repo) {
		selectedRepoToAdd = repo;
		await loadRepositoryTreeData();
		showAddRepoToProjectModal = true;
	}

	function closeAddRepoToProjectModal() {
		showAddRepoToProjectModal = false;
		selectedRepoToAdd = null;
		selectedRepoFolder = null;
		newFolderName = '';
		showNewFolderInput = false;
		selectedParentFolder = null;
	}

	async function addRepositoryToProject() {
		if (!selectedRepoToAdd || !selectedRepoFolder) return;

		try {
			addingRepoToProject = true;

			const repoWorkflows = selectedRepoToAdd.workflows || [];

			const repoFolderItem = {
				id: `repo-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
				name: selectedRepoToAdd.name,
				type: 'repository',
				description: selectedRepoToAdd.description || '',
				metadata: {
					full_name: selectedRepoToAdd.full_name,
					html_url: selectedRepoToAdd.html_url,
					private: selectedRepoToAdd.private,
					language: selectedRepoToAdd.language,
					stargazers_count: selectedRepoToAdd.stargazers_count,
					forks_count: selectedRepoToAdd.forks_count,
					workflow_count: selectedRepoToAdd.workflow_count,
					updated_at: selectedRepoToAdd.updated_at,
					addedFrom: 'workspace'
				},
				children: []
			};

			for (const workflow of repoWorkflows) {
				const workflowContentResult = await githubClient.getWorkflowContent(
					orgName,
					selectedRepoToAdd.name,
					workflow.path
				);

				if (workflowContentResult.success) {
					const workflowItem = {
						id: `workflow-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
						name: workflow.name,
						type: 'workflow',
						content: workflowContentResult.content,
						metadata: {
							triggers: workflow.triggers || [],
							repository: selectedRepoToAdd.name,
							path: workflow.path,
							state: workflow.state,
							lastModified: new Date().toISOString(),
							addedFrom: 'repository'
						}
					};
					repoFolderItem.children.push(workflowItem);
				}
			}

			if (!selectedRepoFolder.children) {
				selectedRepoFolder.children = [];
			}
			selectedRepoFolder.children.push(repoFolderItem);

			await saveRepositoryTreeData();

			console.log(
				`✅ Repository "${selectedRepoToAdd.name}" with ${repoWorkflows.length} workflows added successfully!`
			);
			closeAddRepoToProjectModal();
		} catch (err) {
			console.error('Failed to add repository to tree:', err);
			alert('Failed to add repository to tree');
		} finally {
			addingRepoToProject = false;
		}
	}
</script>

<svelte:head>
	<title>{orgName} Workspace - WithOps DevSecOps Platform</title>
</svelte:head>

<svelte:window on:click={handleGlobalClick} />

<!-- Real-time GitHub Cache Notifications -->
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
				<a href="/github/workspace/{orgName}" class="nav-link active">Workspace</a>
			</div>

			<div class="nav-actions">
				{#if workspaceData && !loading}
					<div class="live-status">
						<span class="status-dot"></span>
						<span class="status-text">Live</span>
					</div>
				{/if}

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
			<span class="breadcrumb-item active">{orgName}</span>
		</div>
		<div class="header-tools">
			<button onclick={forceRefresh} disabled={refreshing} class="btn btn-secondary btn-sm">
				<svg
					class="btn-icon {refreshing ? 'spinning' : ''}"
					width="14"
					height="14"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					stroke-width="2"
				>
					<path
						d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
					/>
				</svg>
				{refreshing ? 'Syncing...' : 'Sync'}
			</button>
			<div class="system-status">
				<div class="status-pulse"></div>
				{#if realtimeUpdateCount > 0}
					{realtimeUpdateCount} UPDATES
				{:else}
					SYSTEM: ACTIVE
				{/if}
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
				<a
					href="/github/workspace/{orgName}/repo-treeview"
					class="sidebar-link"
					title="Repo Treeview"
				>
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
						><path
							d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2"
						/></svg
					>
					{#if !sidebarCollapsed}<span>Repo Tree</span>{/if}
				</a>
				<a
					href="/github/workspace/{orgName}/threat-modeling"
					class="sidebar-link"
					title="Threat Modeling"
				>
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
						><path
							d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
						/></svg
					>
					{#if !sidebarCollapsed}<span>Threats</span>{/if}
				</a>
				<a href="/github/workspace/{orgName}/audit" class="sidebar-link" title="Actions Audit">
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
						><path
							d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
						/></svg
					>
					{#if !sidebarCollapsed}<span>Audit</span>{/if}
				</a>
				<a href="/github/workspace/{orgName}/canvas" class="sidebar-link" title="Canvas">
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
						><path
							d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
						/></svg
					>
					{#if !sidebarCollapsed}<span>Canvas</span>{/if}
				</a>
				<a href="/github/workspace/{orgName}/treeview" class="sidebar-link" title="Treeview">
					<svg
						width="16"
						height="16"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
						><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" /></svg
					>
					{#if !sidebarCollapsed}<span>Treeview</span>{/if}
				</a>
			</nav>
		</aside>

		<main class="workspace-main {sidebarCollapsed ? 'expanded' : ''}">
			{#if loading}
				<div class="center-state">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="loader-text">{loadingStage}</div>
				</div>
			{:else if error}
				<!-- Professional Error State -->
				<div class="error-state">
					<div class="error-content">
						<div class="error-icon">
							<svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
								/>
							</svg>
						</div>
						<h3 class="error-title">Unable to Load Workspace</h3>
						<p class="error-message">{error}</p>
						<div class="error-actions">
							<button onclick={loadWorkspaceData} class="retry-button">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
									/>
								</svg>
								Retry
							</button>
							<button onclick={() => goto('/organizations')} class="back-button">
								Back to Organizations
							</button>
						</div>
					</div>
				</div>
			{:else if workspaceData}
				<!-- Professional Stats Cards -->
				<div class="stats-grid">
					<div class="stat-card">
						<div class="stat-icon stat-icon-blue">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
								/>
							</svg>
						</div>
						<div class="stat-content">
							<p class="stat-label">Repositories</p>
							<p class="stat-value">{workspaceData.repository_count || 0}</p>
						</div>
						<div class="stat-trend">
							<span class="trend-up">Active</span>
						</div>
					</div>

					<div class="stat-card">
						<div class="stat-icon stat-icon-purple">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
								/>
							</svg>
						</div>
						<div class="stat-content">
							<p class="stat-label">Workflows</p>
							<p class="stat-value">{workspaceData.total_workflows || 0}</p>
						</div>
						<div class="stat-trend">
							<span class="trend-neutral">Total</span>
						</div>
					</div>

					<div class="stat-card">
						<div class="stat-icon stat-icon-green">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
						</div>
						<div class="stat-content">
							<p class="stat-label">Status</p>
							<p class="stat-value stat-value-small">{workspaceData.status || 'connected'}</p>
						</div>
						<div class="stat-trend">
							<span class="trend-up">Online</span>
						</div>
					</div>

					<div class="stat-card">
						<div class="stat-icon stat-icon-orange">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
						</div>
						<div class="stat-content">
							<p class="stat-label">Last Synced</p>
							<p class="stat-value stat-value-small">
								{#if workspaceData.last_updated}
									{formatRelativeTime(workspaceData.last_updated)}
								{:else}
									Just now
								{/if}
							</p>
						</div>
						<div class="stat-trend">
							{#if realtimeUpdateCount > 0}
								<span class="trend-up">{realtimeUpdateCount} updates</span>
							{:else}
								<span class="trend-neutral">Monitoring</span>
							{/if}
						</div>
					</div>
				</div>

				<!-- Tabbed Content Section -->
				<div class="content-tabs">
					<div class="tabs-header">
						<button
							onclick={() => (activeTab = 'repositories')}
							class="tab-button {activeTab === 'repositories' ? 'active' : ''}"
						>
							<svg class="tab-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
								/>
							</svg>
							<span>Repositories</span>
							<span class="tab-badge">{workspaceData.repository_count || 0}</span>
						</button>
						<button
							onclick={switchToWorkflowsTab}
							class="tab-button {activeTab === 'workflows' ? 'active' : ''}"
						>
							<svg class="tab-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
								/>
							</svg>
							<span>Workflows</span>
							<span class="tab-badge">{workspaceData.total_workflows || 0}</span>
						</button>
					</div>

					<div class="tabs-content">
						{#if activeTab === 'repositories'}
							<!-- Repositories Content -->
							{#if workspaceData.repositories && workspaceData.repositories.length > 0}
								<div class="repositories-grid">
									{#each workspaceData.repositories as repo}
										<div class="repository-card">
											<div class="repo-header relative">
												<div class="repo-info">
													<div class="repo-icon">
														<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3.382a1 1 0 00-.894.553l-.448.894a1 1 0 01-.894.553H9a1 1 0 01-.894-.553l-.448-.894A1 1 0 006.764 7H3z"
															/>
														</svg>
													</div>
													<div class="repo-title-section">
														<h3 class="repo-name">
															<a href={repo.html_url} target="_blank">{repo.name}</a>
														</h3>
														{#if repo.private}
															<span class="repo-badge private">Private</span>
														{:else}
															<span class="repo-badge public">Public</span>
														{/if}
													</div>
												</div>
												<button
													onclick={() => toggleRepoActionMenu(repo.id || repo.name)}
													class="repo-menu-button"
													aria-label="Repository actions menu"
												>
													<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
														/>
													</svg>
												</button>

												{#if activeRepoMenu === (repo.id || repo.name)}
													<div class="dropdown-menu">
														<button
															onclick={() => {
																viewRepository(repo);
																activeRepoMenu = null;
															}}
															class="dropdown-item"
														>
															<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="2"
																	d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
																/>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="2"
																	d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
																/>
															</svg>
															<span>View Details</span>
														</button>

														<button
															onclick={() => {
																goto(`/github/workspace/${orgName}/canvas?repo=${repo.name}`);
																activeRepoMenu = null;
															}}
															class="dropdown-item"
														>
															<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="2"
																	d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
																/>
															</svg>
															<span>🎨 Canvas Builder</span>
														</button>

														<div class="dropdown-divider"></div>

														<button
															onclick={() => {
																openAddRepoToProjectModal(repo);
																activeRepoMenu = null;
															}}
															class="dropdown-item dropdown-item-primary"
														>
															<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="2"
																	d="M12 4v16m8-8H4"
																/>
															</svg>
															<span>Add Repository to Project</span>
														</button>

														<a
															href={repo.html_url}
															target="_blank"
															onclick={() => (activeRepoMenu = null)}
															class="dropdown-item"
														>
															<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="2"
																	d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
																/>
															</svg>
															<span>Open in GitHub</span>
														</a>
													</div>
												{/if}
											</div>

											{#if repo.description}
												<p class="repo-description">{repo.description}</p>
											{/if}

											<div class="repo-meta">
												{#if repo.language}
													<div class="meta-item">
														<span class="language-dot"></span>
														<span>{repo.language}</span>
													</div>
												{/if}
												<div class="meta-item">
													<svg fill="currentColor" viewBox="0 0 20 20">
														<path
															d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
														/>
													</svg>
													<span>{repo.stargazers_count}</span>
												</div>
												<div class="meta-item">
													<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"
														/>
													</svg>
													<span>{repo.forks_count}</span>
												</div>
												<div class="meta-item">
													<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
														/>
													</svg>
													<span>{repo.workflow_count} workflows</span>
												</div>
											</div>

											{#if repo.workflows && repo.workflows.length > 0}
												<div class="repo-workflows">
													<h4 class="workflows-title">Workflows</h4>
													<div class="workflows-list">
														{#each repo.workflows as workflow}
															<div class="workflow-item">
																<div class="workflow-info">
																	<span class="workflow-name">{workflow.name}</span>
																	<span class="workflow-badge {workflow.state}"
																		>{workflow.state}</span
																	>
																</div>
																<button
																	onclick={() => viewWorkflowContent(workflow, repo)}
																	class="view-workflow-button"
																>
																	View YAML
																</button>
															</div>
														{/each}
													</div>
												</div>
											{/if}
										</div>
									{/each}
								</div>
							{:else}
								<div class="empty-state">
									<svg class="empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
										/>
									</svg>
									<h3 class="empty-title">No Repositories Found</h3>
									<p class="empty-message">This organization doesn't have any repositories yet.</p>
								</div>
							{/if}
						{:else if activeTab === 'workflows'}
							<!-- Workflows Content -->
							{#if loadingDetailedWorkflows}
								<div class="workflows-loading">
									<div class="loading-spinner"></div>
									<p>Loading workflow details...</p>
								</div>
							{:else if detailedWorkflows.length > 0}
								<div class="workflows-table-container">
									<table class="workflows-table">
										<thead>
											<tr>
												<th>Repository / Workflow</th>
												<th>Trigger</th>
												<th>Last Run</th>
												<th>Last Successful</th>
												<th>Uses</th>
												<th>Author</th>
												<th>Status</th>
												<th>Actions</th>
											</tr>
										</thead>
										<tbody>
											{#each detailedWorkflows as workflow}
												<tr class="workflow-row">
													<td>
														<div class="workflow-cell">
															<div class="workflow-icon-wrapper">
																<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																	<path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		stroke-width="2"
																		d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
																	/>
																</svg>
															</div>
															<div class="workflow-details">
																<span class="workflow-table-name">{workflow.name}</span>
																<span class="workflow-repo-name">{workflow.repository}</span>
															</div>
														</div>
													</td>
													<td>
														<div class="triggers-cell">
															{#if workflow.triggers && workflow.triggers.length > 0}
																{#each workflow.triggers.slice(0, 2) as trigger}
																	<span class="trigger-badge">{trigger}</span>
																{/each}
																{#if workflow.triggers.length > 2}
																	<span class="trigger-more">+{workflow.triggers.length - 2}</span>
																{/if}
															{:else}
																<span class="trigger-unknown">Unknown</span>
															{/if}
														</div>
													</td>
													<td>
														{#if workflow.last_run && workflow.last_run.created_at}
															<span class="last-run-time"
																>{formatRelativeTime(workflow.last_run.created_at)}</span
															>
														{:else}
															<span class="last-run-never">Never</span>
														{/if}
													</td>
													<td>
														{#if workflow.last_successful_run && workflow.last_successful_run.created_at}
															<span class="last-run-time"
																>{formatRelativeTime(workflow.last_successful_run.created_at)}</span
															>
														{:else}
															<span class="last-run-never">N/A</span>
														{/if}
													</td>
													<td>
														<div class="uses-cell">
															{#if workflow.uses && workflow.uses.length > 0}
																{#each workflow.uses.slice(0, 2) as actionPath}
																	<div class="uses-action">{actionPath}</div>
																{/each}
																{#if workflow.uses.length > 2}
																	<span class="uses-more">+{workflow.uses.length - 2} more</span>
																{/if}
															{:else}
																<span class="uses-none">None</span>
															{/if}
														</div>
													</td>
													<td>
														<div class="author-cell">
															<div class="author-avatar">
																{#if workflow.author && workflow.author !== 'Unknown'}
																	<span>{workflow.author.charAt(0).toUpperCase()}</span>
																{:else}
																	<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			stroke-width="2"
																			d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
																		/>
																	</svg>
																{/if}
															</div>
															<span class="author-name">
																{#if workflow.author && workflow.author !== 'Unknown'}
																	{workflow.author}
																{:else}
																	<span class="author-unknown">Unknown</span>
																{/if}
															</span>
														</div>
													</td>
													<td>
														<span class="status-badge {workflow.state || 'unknown'}">
															{workflow.state || 'unknown'}
														</span>
													</td>
													<td>
														<div class="relative">
															<button
																onclick={() =>
																	toggleWorkflowActionMenu(`${workflow.id}-${workflow.repository}`)}
																class="table-action-button"
																aria-label="Workflow actions"
															>
																<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																	<path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		stroke-width="2"
																		d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
																	/>
																</svg>
															</button>

															{#if activeWorkflowMenu === `${workflow.id}-${workflow.repository}`}
																<div class="dropdown-menu dropdown-menu-right">
																	<button
																		onclick={() => {
																			viewWorkflowContent(workflow, { name: workflow.repository });
																			activeWorkflowMenu = null;
																		}}
																		class="dropdown-item"
																	>
																		<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path
																				stroke-linecap="round"
																				stroke-linejoin="round"
																				stroke-width="2"
																				d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
																			/>
																		</svg>
																		<span>View YAML</span>
																	</button>
																	<button
																		onclick={() => {
																			goto(
																				`/github/workspace/${orgName}/canvas?repo=${workflow.repository}&workflow=${encodeURIComponent(workflow.name)}`
																			);
																			activeWorkflowMenu = null;
																		}}
																		class="dropdown-item"
																	>
																		<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path
																				stroke-linecap="round"
																				stroke-linejoin="round"
																				stroke-width="2"
																				d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
																			/>
																		</svg>
																		<span>Open Canvas</span>
																	</button>
																	<div class="dropdown-divider"></div>

																	<button
																		onclick={() => {
																			openAddToProjectModal(workflow);
																			activeWorkflowMenu = null;
																		}}
																		class="dropdown-item dropdown-item-primary"
																	>
																		<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path
																				stroke-linecap="round"
																				stroke-linejoin="round"
																				stroke-width="2"
																				d="M12 4v16m8-8H4"
																			/>
																		</svg>
																		<span>Add to Project</span>
																	</button>
																	{#if workflow.html_url}
																		<a
																			href={workflow.html_url}
																			target="_blank"
																			onclick={() => (activeWorkflowMenu = null)}
																			class="dropdown-item"
																		>
																			<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																				<path
																					stroke-linecap="round"
																					stroke-linejoin="round"
																					stroke-width="2"
																					d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
																				/>
																			</svg>
																			<span>Open in GitHub</span>
																		</a>
																	{/if}
																</div>
															{/if}
														</div>
													</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							{:else}
								<div class="empty-state">
									<svg class="empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
										/>
									</svg>
									<h3 class="empty-title">No Workflows Found</h3>
									<p class="empty-message">
										No GitHub Actions workflows configured in this organization.
									</p>
								</div>
							{/if}
						{/if}
					</div>
				</div>
			{/if}
		</main>
	</div>
</div>

<!-- Workflow Modal -->
{#if showWorkflowModal && selectedWorkflow}
	<div
		class="modal-overlay"
		onclick={closeWorkflowModal}
		onkeydown={(e) => e.key === 'Escape' && closeWorkflowModal()}
		role="button"
		tabindex="0"
		aria-label="Close modal overlay"
	>
		<div
			class="modal-content"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
			tabindex="-1"
		>
			<div class="modal-header">
				<div class="modal-title">
					<h3 id="modal-title">{selectedWorkflow.name}</h3>
					<p>{selectedWorkflow.repo}/{selectedWorkflow.path}</p>
				</div>
				<button onclick={closeWorkflowModal} class="modal-close" aria-label="Close workflow modal">
					<svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			<div class="modal-body">
				{#if loadingWorkflow}
					<div class="modal-loading">
						<div class="loading-spinner"></div>
						<span>Loading workflow content...</span>
					</div>
				{:else}
					<div class="code-viewer">
						<pre><code>{workflowContent}</code></pre>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Add Workflow to Project Modal -->
{#if showAddToProjectModal}
	<div
		class="modal-overlay"
		onclick={closeAddToProjectModal}
		onkeydown={(e) => e.key === 'Escape' && closeAddToProjectModal()}
		role="button"
		tabindex="0"
		aria-label="Close modal overlay"
	>
		<div
			class="modal-content modal-content-large"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="add-workflow-modal-title"
			tabindex="-1"
		>
			<div class="modal-header">
				<div class="modal-title">
					<h3 id="add-workflow-modal-title">Add Workflow to Project Treeview</h3>
					{#if selectedWorkflowToAdd}
						<p>
							Adding: <strong>{selectedWorkflowToAdd.name}</strong> from
							<strong>{selectedWorkflowToAdd.repository}</strong>
						</p>
					{/if}
				</div>
				<button onclick={closeAddToProjectModal} class="modal-close" aria-label="Close modal">
					<svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			<div class="modal-body modal-grid">
				<!-- Project Tree Structure -->
				<div class="tree-panel">
					<div class="tree-header">
						<h4>🌲 Project Structure</h4>
						<button
							onclick={() => (showNewFolderInput = !showNewFolderInput)}
							class="btn-primary-small"
						>
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 4v16m8-8H4"
								/>
							</svg>
							<span>New Folder</span>
						</button>
					</div>

					{#if showNewFolderInput}
						<div class="new-folder-form">
							<label for="workflow-folder-name">Folder Name</label>
							<input
								bind:value={newFolderName}
								placeholder="Enter folder name..."
								id="workflow-folder-name"
								onkeypress={(e) => e.key === 'Enter' && createNewFolderInModal()}
							/>

							{#if projectTreeData.filter((f) => f.type === 'folder').length > 0}
								<label for="workflow-parent-folder">Parent Folder (Optional)</label>
								<select bind:value={selectedParentFolder} id="workflow-parent-folder">
									<option value={null}>None (Create at root level)</option>
									{#each getFlattenedFolders(projectTreeData) as folder}
										<option value={folder}>
											{'  '.repeat(folder.depth)}📁 {folder.name}
										</option>
									{/each}
								</select>
							{/if}

							<div class="form-actions">
								<button
									onclick={() => {
										showNewFolderInput = false;
										newFolderName = '';
										selectedParentFolder = null;
									}}
									class="btn-secondary"
								>
									Cancel
								</button>
								<button
									onclick={createNewFolderInModal}
									disabled={!newFolderName.trim()}
									class="btn-primary"
								>
									Create
								</button>
							</div>
						</div>
					{/if}

					<div class="tree-list">
						{#if projectTreeData.length === 0}
							<div class="tree-empty">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
									/>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z"
									/>
								</svg>
								<p>No folders yet</p>
								<small>Create a folder to organize your workflows</small>
							</div>
						{:else}
							{#each getFlattenedFolders(projectTreeData) as folder}
								<button
									class="folder-item {selectedProjectFolder?.id === folder.id ? 'selected' : ''}"
									onclick={() => (selectedProjectFolder = folder)}
									style="padding-left: {folder.depth * 16 + 16}px"
								>
									<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z"
										/>
									</svg>
									<div class="folder-info">
										<span class="folder-name">{folder.name}</span>
										<span class="folder-count">{countWorkflowsInFolder(folder)} items</span>
									</div>
									{#if selectedProjectFolder?.id === folder.id}
										<svg class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M5 13l4 4L19 7"
											/>
										</svg>
									{/if}
								</button>
							{/each}
						{/if}
					</div>
				</div>

				<!-- Workflow Preview -->
				<div class="preview-panel">
					<h4>📄 Workflow Preview</h4>
					{#if selectedWorkflowToAdd}
						<div class="workflow-preview">
							<div class="preview-header">
								<div class="preview-icon">
									<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
										/>
									</svg>
								</div>
								<div>
									<div class="preview-name">{selectedWorkflowToAdd.name}</div>
									<div class="preview-repo">{selectedWorkflowToAdd.repository}</div>
								</div>
							</div>

							<div class="preview-details">
								<div class="detail-item">
									<span>Path:</span>
									<span>{selectedWorkflowToAdd.path || 'N/A'}</span>
								</div>
								<div class="detail-item">
									<span>State:</span>
									<span class="status-badge {selectedWorkflowToAdd.state || 'unknown'}">
										{selectedWorkflowToAdd.state || 'Unknown'}
									</span>
								</div>
								{#if selectedWorkflowToAdd.triggers && selectedWorkflowToAdd.triggers.length > 0}
									<div class="detail-item">
										<span>Triggers:</span>
										<div class="triggers-preview">
											{#each selectedWorkflowToAdd.triggers as trigger}
												<span class="trigger-badge">{trigger}</span>
											{/each}
										</div>
									</div>
								{/if}
							</div>
						</div>

						{#if selectedProjectFolder}
							<div class="status-message success">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
									/>
								</svg>
								<div>
									<strong>Ready to add</strong>
									<p>
										This workflow will be added to the "<strong>{selectedProjectFolder.name}</strong
										>" folder.
									</p>
								</div>
							</div>
						{:else}
							<div class="status-message warning">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
									/>
								</svg>
								<div>
									<strong>Select a folder</strong>
									<p>
										Please select a folder where you want to add this workflow, or create a new one.
									</p>
								</div>
							</div>
						{/if}
					{/if}
				</div>
			</div>

			<div class="modal-footer">
				<button onclick={closeAddToProjectModal} class="btn-secondary"> Cancel </button>
				<button
					onclick={addWorkflowToProject}
					disabled={!selectedProjectFolder || !selectedWorkflowToAdd || addingWorkflowToProject}
					class="btn-success"
				>
					{#if addingWorkflowToProject}
						<svg class="spinner" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
							/>
						</svg>
						<span>Adding...</span>
					{:else}
						<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 4v16m8-8H4"
							/>
						</svg>
						<span>Add to Project</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Add Repository to Project Modal -->
{#if showAddRepoToProjectModal}
	<div
		class="modal-overlay"
		onclick={closeAddRepoToProjectModal}
		onkeydown={(e) => e.key === 'Escape' && closeAddRepoToProjectModal()}
		role="button"
		tabindex="0"
		aria-label="Close modal overlay"
	>
		<div
			class="modal-content modal-content-large"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="add-repo-modal-title"
			tabindex="-1"
		>
			<div class="modal-header">
				<div class="modal-title">
					<h3 id="add-repo-modal-title">Add Repository to Repository Treeview</h3>
					{#if selectedRepoToAdd}
						<p>
							Adding: <strong>{selectedRepoToAdd.name}</strong>
							{#if selectedRepoToAdd.workflow_count}
								with <strong>{selectedRepoToAdd.workflow_count} workflows</strong>
							{/if}
						</p>
					{/if}
				</div>
				<button onclick={closeAddRepoToProjectModal} class="modal-close" aria-label="Close modal">
					<svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			<div class="modal-body modal-grid">
				<!-- Repository Tree Structure -->
				<div class="tree-panel">
					<div class="tree-header">
						<h4>🌲 Repository Structure</h4>
						<button
							onclick={() => (showNewFolderInput = !showNewFolderInput)}
							class="btn-primary-small"
						>
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 4v16m8-8H4"
								/>
							</svg>
							<span>New Folder</span>
						</button>
					</div>

					{#if showNewFolderInput}
						<div class="new-folder-form">
							<label for="repo-folder-name">Folder Name</label>
							<input
								bind:value={newFolderName}
								placeholder="Enter folder name..."
								id="repo-folder-name"
								onkeypress={(e) => e.key === 'Enter' && createNewFolderInModal()}
							/>

							{#if repoTreeData.filter((f) => f.type === 'folder').length > 0}
								<label for="repo-parent-folder">Parent Folder (Optional)</label>
								<select bind:value={selectedParentFolder} id="repo-parent-folder">
									<option value={null}>None (Create at root level)</option>
									{#each getFlattenedFolders(repoTreeData) as folder}
										<option value={folder}>
											{'  '.repeat(folder.depth)}📁 {folder.name}
										</option>
									{/each}
								</select>
							{/if}

							<div class="form-actions">
								<button
									onclick={() => {
										showNewFolderInput = false;
										newFolderName = '';
										selectedParentFolder = null;
									}}
									class="btn-secondary"
								>
									Cancel
								</button>
								<button
									onclick={createNewFolderInModal}
									disabled={!newFolderName.trim()}
									class="btn-primary"
								>
									Create
								</button>
							</div>
						</div>
					{/if}

					<div class="tree-list">
						{#if repoTreeData.length === 0}
							<div class="tree-empty">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
									/>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z"
									/>
								</svg>
								<p>No folders yet</p>
								<small>Create a folder to organize your repositories</small>
							</div>
						{:else}
							{#each getFlattenedFolders(repoTreeData) as folder}
								<button
									class="folder-item {selectedRepoFolder?.id === folder.id ? 'selected' : ''}"
									onclick={() => (selectedRepoFolder = folder)}
									style="padding-left: {folder.depth * 16 + 16}px"
								>
									<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z"
										/>
									</svg>
									<div class="folder-info">
										<span class="folder-name">{folder.name}</span>
										<span class="folder-count">{countWorkflowsInFolder(folder)} items</span>
									</div>
									{#if selectedRepoFolder?.id === folder.id}
										<svg class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M5 13l4 4L19 7"
											/>
										</svg>
									{/if}
								</button>
							{/each}
						{/if}
					</div>
				</div>

				<!-- Repository Preview -->
				<div class="preview-panel">
					<h4>📦 Repository Preview</h4>
					{#if selectedRepoToAdd}
						<div class="repo-preview">
							<div class="preview-header">
								<div class="preview-icon preview-icon-primary">
									<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3.382a1 1 0 00-.894.553l-.448.894a1 1 0 01-.894.553H9a1 1 0 01-.894-.553l-.448-.894A1 1 0 006.764 7H3z"
										/>
									</svg>
								</div>
								<div>
									<div class="preview-name">{selectedRepoToAdd.name}</div>
									{#if selectedRepoToAdd.description}
										<div class="preview-desc">{selectedRepoToAdd.description}</div>
									{/if}
								</div>
							</div>

							<div class="preview-details">
								<div class="detail-item">
									<span>Workflows:</span>
									<span>{selectedRepoToAdd.workflow_count || 0}</span>
								</div>
								{#if selectedRepoToAdd.language}
									<div class="detail-item">
										<span>Language:</span>
										<span>{selectedRepoToAdd.language}</span>
									</div>
								{/if}
								<div class="detail-item">
									<span>Visibility:</span>
									<span class="repo-badge {selectedRepoToAdd.private ? 'private' : 'public'}">
										{selectedRepoToAdd.private ? 'Private' : 'Public'}
									</span>
								</div>
							</div>
						</div>

						{#if selectedRepoFolder}
							<div class="status-message success">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
									/>
								</svg>
								<div>
									<strong>Ready to add</strong>
									<p>
										This repository will be added to the "<strong>{selectedRepoFolder.name}</strong
										>" folder.
									</p>
								</div>
							</div>
						{:else}
							<div class="status-message warning">
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
									/>
								</svg>
								<div>
									<strong>Select a folder</strong>
									<p>
										Please select a folder where you want to add this repository, or create a new
										one.
									</p>
								</div>
							</div>
						{/if}
					{/if}
				</div>
			</div>

			<div class="modal-footer">
				<button onclick={closeAddRepoToProjectModal} class="btn-secondary"> Cancel </button>
				<button
					onclick={addRepositoryToProject}
					disabled={!selectedRepoFolder || !selectedRepoToAdd || addingRepoToProject}
					class="btn-success"
				>
					{#if addingRepoToProject}
						<svg class="spinner" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
							/>
						</svg>
						<span>Adding...</span>
					{:else}
						<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 4v16m8-8H4"
							/>
						</svg>
						<span>Add Repository</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* ============================================
       MATTE ENGINEERING DESIGN SYSTEM
       Workspace Page — Matching Dashboard/Orgs
       ============================================ */
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
		--card-shadow: none;
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
		--card-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
	}

	/* Reset & Base */
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

	/* ─── Header ─── */
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
		gap: 1.25rem;
	}
	.live-status {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--success);
	}
	.status-dot {
		width: 6px;
		height: 6px;
		background: var(--success);
		border-radius: 50%;
		animation: blink 2s infinite;
	}
	.theme-toggle {
		background: none;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 8px;
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

	/* ─── Technical Bar ─── */
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
		gap: 0.75rem;
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
	.breadcrumb a:hover {
		color: var(--text-secondary);
	}
	.breadcrumb-sep {
		color: var(--border-focus);
	}
	.breadcrumb-item.active {
		color: var(--accent);
	}
	.header-tools {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 1rem;
	}
	.system-status {
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

	/* ─── Layout with Sidebar ─── */
	.layout-with-sidebar {
		display: flex;
		flex: 1;
		position: relative;
		z-index: 10;
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
		top: calc(var(--nav-height) + 40px);
		height: calc(100vh - var(--nav-height) - 40px);
		overflow-y: auto;
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
		align-items: center;
		justify-content: center;
		margin-bottom: 0.5rem;
		transition: all 0.15s;
	}
	.sidebar-toggle-btn:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
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
		transition: all 0.15s;
	}
	.sidebar-link:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
	}

	/* ─── Main Content ─── */
	.workspace-main {
		flex: 1;
		padding: 2rem;
		max-width: 1280px;
		min-width: 0;
	}
	.workspace-main.expanded {
		max-width: 1440px;
	}

	/* ─── Loading / Error / Empty ─── */
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
	.loading-spinner {
		width: 32px;
		height: 32px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		margin: 0 auto;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	.error-state,
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 8rem 2rem;
		text-align: center;
	}
	.error-content {
		text-align: center;
		max-width: 400px;
	}
	.error-icon {
		width: 40px;
		height: 40px;
		color: var(--error);
		margin-bottom: 1rem;
	}
	.error-icon svg {
		width: 100%;
		height: 100%;
	}
	.error-title {
		font-size: 1.125rem;
		font-weight: 700;
		margin-bottom: 0.5rem;
	}
	.error-message {
		color: var(--text-secondary);
		font-size: 0.875rem;
		margin-bottom: 1.5rem;
		line-height: 1.5;
	}
	.error-actions {
		display: flex;
		gap: 0.75rem;
	}
	.retry-button,
	.back-button {
		padding: 0.625rem 1.25rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		border: 1px solid var(--border);
	}
	.retry-button {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
	}
	.retry-button:hover {
		opacity: 0.9;
	}
	.retry-button svg {
		width: 14px;
		height: 14px;
	}
	.back-button {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
	}
	.back-button:hover {
		border-color: var(--border-focus);
	}

	/* ─── Stats Grid ─── */
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
		display: flex;
		align-items: center;
		gap: 1rem;
		transition: all 0.2s var(--ease-premium);
		box-shadow: var(--card-shadow);
	}
	.stat-card:hover {
		border-color: var(--border-focus);
	}
	.stat-icon {
		width: 36px;
		height: 36px;
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.stat-icon svg {
		width: 18px;
		height: 18px;
	}
	.stat-icon-blue {
		background: rgba(0, 173, 239, 0.08);
		color: var(--accent);
	}
	.stat-icon-purple {
		background: rgba(139, 92, 246, 0.08);
		color: #8b5cf6;
	}
	.stat-icon-green {
		background: rgba(16, 185, 129, 0.08);
		color: var(--success);
	}
	.stat-icon-orange {
		background: rgba(245, 158, 11, 0.08);
		color: var(--warning);
	}
	.stat-content {
		flex: 1;
		min-width: 0;
	}
	.stat-label {
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-family: var(--font-mono);
		margin-bottom: 0.25rem;
	}
	.stat-value {
		font-family: var(--font-mono);
		font-size: 1.25rem;
		font-weight: 700;
	}
	.stat-value-small {
		font-size: 0.875rem;
	}
	.stat-trend {
		flex-shrink: 0;
	}
	.trend-up {
		font-size: 0.65rem;
		font-family: var(--font-mono);
		color: var(--success);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		border: 1px solid rgba(16, 185, 129, 0.1);
	}
	.trend-neutral {
		font-size: 0.65rem;
		font-family: var(--font-mono);
		color: var(--text-muted);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		border: 1px solid var(--border);
	}

	/* ─── Tabs ─── */
	.content-tabs {
		margin-top: 0.5rem;
	}
	.tabs-header {
		display: flex;
		gap: 0.25rem;
		background: var(--bg-surface-alt);
		padding: 0.25rem;
		border-radius: 8px;
		border: 1px solid var(--border);
		width: fit-content;
		margin-bottom: 1.5rem;
	}
	.tab-button {
		background: none;
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.tab-button:hover {
		color: var(--text-primary);
	}
	.tab-button.active {
		background: var(--bg-surface);
		color: var(--accent);
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}
	.tab-icon {
		width: 14px;
		height: 14px;
	}
	.tab-badge {
		font-size: 0.65rem;
		font-family: var(--font-mono);
		background: var(--border);
		color: var(--text-muted);
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
	}
	.tab-button.active .tab-badge {
		background: var(--accent-soft);
		color: var(--accent);
	}

	/* ─── Repository Cards ─── */
	.repositories-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
		gap: 1rem;
	}
	.repository-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.25rem;
		transition: all 0.2s var(--ease-premium);
		box-shadow: var(--card-shadow);
	}
	.repository-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-1px);
	}
	.repo-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}
	.repo-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex: 1;
		min-width: 0;
	}
	.repo-icon {
		width: 32px;
		height: 32px;
		border-radius: 6px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.repo-icon svg {
		width: 16px;
		height: 16px;
		color: var(--text-muted);
	}
	.repo-title-section {
		min-width: 0;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	.repo-name {
		font-size: 0.875rem;
		font-weight: 600;
	}
	.repo-name a {
		color: var(--text-primary);
		text-decoration: none;
	}
	.repo-name a:hover {
		color: var(--accent);
	}
	.repo-badge {
		font-size: 0.6rem;
		font-family: var(--font-mono);
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: 600;
	}
	.repo-badge.private {
		color: var(--warning);
		border: 1px solid rgba(245, 158, 11, 0.15);
	}
	.repo-badge.public {
		color: var(--success);
		border: 1px solid rgba(16, 185, 129, 0.15);
	}
	.repo-description {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		line-height: 1.5;
		margin-bottom: 0.75rem;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.repo-meta {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		margin-bottom: 0.75rem;
	}
	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.75rem;
		color: var(--text-muted);
	}
	.meta-item svg {
		width: 12px;
		height: 12px;
	}
	.language-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--accent);
	}

	/* Repo Workflows sub-section */
	.repo-workflows {
		border-top: 1px solid var(--border);
		padding-top: 0.75rem;
	}
	.workflows-title {
		font-size: 0.65rem;
		font-family: var(--font-mono);
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.5rem;
	}
	.workflows-list {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}
	.workflow-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.375rem 0.5rem;
		border-radius: 6px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
	}
	.workflow-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex: 1;
		min-width: 0;
	}
	.workflow-name {
		font-size: 0.75rem;
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.workflow-badge {
		font-size: 0.6rem;
		font-family: var(--font-mono);
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
		text-transform: uppercase;
	}
	.workflow-badge.active {
		color: var(--success);
		border: 1px solid rgba(16, 185, 129, 0.15);
	}
	.workflow-badge.disabled {
		color: var(--text-muted);
		border: 1px solid var(--border);
	}
	.view-workflow-button {
		font-size: 0.7rem;
		font-family: var(--font-mono);
		color: var(--accent);
		background: none;
		border: none;
		cursor: pointer;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		transition: background 0.15s;
	}
	.view-workflow-button:hover {
		background: var(--accent-soft);
	}

	/* ─── Dropdown Menus ─── */
	.repo-menu-button,
	.table-action-button {
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		padding: 0.375rem;
		border-radius: 4px;
		transition: all 0.15s;
		flex-shrink: 0;
	}
	.repo-menu-button:hover,
	.table-action-button:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
	}
	.repo-menu-button svg,
	.table-action-button svg {
		width: 16px;
		height: 16px;
	}
	.relative {
		position: relative;
	}
	.dropdown-menu {
		position: absolute;
		top: calc(100% + 4px);
		right: 0;
		width: 200px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
		padding: 0.375rem;
		z-index: 50;
	}
	.dropdown-menu-right {
		right: 0;
	}
	.dropdown-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.625rem;
		border-radius: 6px;
		font-size: 0.8125rem;
		color: var(--text-secondary);
		background: none;
		border: none;
		cursor: pointer;
		width: 100%;
		text-align: left;
		text-decoration: none;
		transition: all 0.15s;
	}
	.dropdown-item:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
	}
	.dropdown-item svg {
		width: 14px;
		height: 14px;
		flex-shrink: 0;
	}
	.dropdown-item-primary {
		color: var(--accent);
	}
	.dropdown-item-primary:hover {
		background: var(--accent-soft);
	}
	.dropdown-divider {
		height: 1px;
		background: var(--border);
		margin: 0.25rem 0;
	}

	/* ─── Workflows Table ─── */
	.workflows-loading {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 4rem 2rem;
		gap: 1rem;
		color: var(--text-muted);
		font-size: 0.875rem;
	}
	.workflows-table-container {
		overflow-x: auto;
		border-radius: 12px;
		border: 1px solid var(--border);
	}
	.workflows-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.8125rem;
	}
	.workflows-table thead {
		background: var(--bg-surface-alt);
	}
	.workflows-table th {
		padding: 0.75rem 1rem;
		text-align: left;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid var(--border);
		white-space: nowrap;
	}
	.workflows-table td {
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--border);
		vertical-align: middle;
	}
	.workflow-row:hover {
		background: var(--bg-surface-alt);
	}
	.workflow-row:last-child td {
		border-bottom: none;
	}
	.workflow-cell {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.workflow-icon-wrapper {
		width: 28px;
		height: 28px;
		border-radius: 6px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.workflow-icon-wrapper svg {
		width: 14px;
		height: 14px;
		color: var(--text-muted);
	}
	.workflow-details {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.workflow-table-name {
		font-weight: 600;
		font-size: 0.8125rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.workflow-repo-name {
		font-size: 0.7rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
	}
	.triggers-cell {
		display: flex;
		gap: 0.375rem;
		flex-wrap: wrap;
	}
	.trigger-badge {
		font-size: 0.65rem;
		font-family: var(--font-mono);
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		color: var(--text-secondary);
	}
	.trigger-more,
	.trigger-unknown {
		font-size: 0.65rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
	}
	.last-run-time {
		font-size: 0.75rem;
		color: var(--text-secondary);
		font-family: var(--font-mono);
	}
	.last-run-never {
		font-size: 0.75rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
	}
	.uses-cell {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}
	.uses-action {
		font-size: 0.65rem;
		font-family: var(--font-mono);
		color: var(--text-secondary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 180px;
	}
	.uses-more,
	.uses-none {
		font-size: 0.65rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
	}
	.author-cell {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.author-avatar {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.65rem;
		font-weight: 700;
		color: var(--text-secondary);
		flex-shrink: 0;
	}
	.author-avatar svg {
		width: 12px;
		height: 12px;
	}
	.author-name {
		font-size: 0.8125rem;
	}
	.author-unknown {
		color: var(--text-muted);
	}
	.status-badge {
		display: inline-flex;
		align-items: center;
		font-size: 0.65rem;
		font-family: var(--font-mono);
		font-weight: 600;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.status-badge.active {
		color: var(--success);
		border: 1px solid rgba(16, 185, 129, 0.15);
	}
	.status-badge.disabled {
		color: var(--text-muted);
		border: 1px solid var(--border);
	}
	.status-badge.unknown {
		color: var(--text-muted);
		border: 1px solid var(--border);
	}

	/* ─── Empty State ─── */
	.empty-icon {
		width: 40px;
		height: 40px;
		color: var(--text-muted);
		margin-bottom: 1rem;
	}
	.empty-title {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
	}
	.empty-message {
		color: var(--text-secondary);
		font-size: 0.875rem;
	}

	/* ─── Buttons ─── */
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
		border-color: var(--border-focus);
		transform: translateY(-1px);
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.btn-secondary {
		background: var(--bg-surface-alt);
	}
	.btn-sm {
		padding: 0.375rem 0.75rem;
		font-size: 0.75rem;
	}
	.btn-icon {
		width: 14px;
		height: 14px;
	}
	.spinning {
		animation: spin 0.8s linear infinite;
	}

	/* ─── Modal ─── */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(4px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 2rem;
	}
	.modal-content {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		width: 100%;
		max-width: 640px;
		max-height: 85vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
	}
	.modal-content-large {
		max-width: 900px;
	}
	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid var(--border);
	}
	.modal-title h3 {
		font-size: 1rem;
		font-weight: 700;
	}
	.modal-title p {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		margin-top: 0.25rem;
	}
	.modal-close {
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		padding: 0.375rem;
		border-radius: 6px;
		transition: all 0.15s;
	}
	.modal-close:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
	}
	.modal-close svg {
		width: 18px;
		height: 18px;
	}
	.modal-body {
		padding: 1.5rem;
		overflow-y: auto;
		flex: 1;
	}
	.modal-loading {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 3rem;
		color: var(--text-muted);
		font-size: 0.875rem;
	}
	.modal-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
	}
	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding: 1rem 1.5rem;
		border-top: 1px solid var(--border);
	}
	.code-viewer {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: auto;
		max-height: 60vh;
	}
	.code-viewer pre {
		padding: 1rem 1.25rem;
		margin: 0;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		line-height: 1.6;
		color: var(--text-secondary);
		white-space: pre;
		tab-size: 2;
	}

	/* ─── Modal Buttons ─── */
	.btn-primary,
	.btn-primary-small {
		background: var(--text-primary);
		color: var(--bg-app);
		border: 1px solid var(--text-primary);
		padding: 0.625rem 1.25rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.btn-primary:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}
	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.btn-primary-small {
		padding: 0.375rem 0.75rem;
		font-size: 0.75rem;
	}
	.btn-primary-small svg {
		width: 12px;
		height: 12px;
	}
	.btn-secondary {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		border: 1px solid var(--border);
		padding: 0.625rem 1.25rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
	}
	.btn-secondary:hover {
		border-color: var(--border-focus);
	}
	.btn-success {
		background: var(--success);
		color: #fff;
		border: 1px solid var(--success);
		padding: 0.625rem 1.25rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.btn-success:hover:not(:disabled) {
		opacity: 0.9;
	}
	.btn-success:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.btn-success svg {
		width: 14px;
		height: 14px;
	}
	.spinner {
		animation: spin 0.8s linear infinite;
	}

	/* ─── Tree Panel (Add to Project Modal) ─── */
	.tree-panel,
	.preview-panel {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 1.25rem;
	}
	.tree-panel h4,
	.preview-panel h4 {
		font-size: 0.875rem;
		font-weight: 700;
		margin-bottom: 1rem;
	}
	.tree-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}
	.tree-header h4 {
		margin-bottom: 0;
	}
	.new-folder-form {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.new-folder-form label {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-secondary);
	}
	.new-folder-form input,
	.new-folder-form select {
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		font-size: 0.8125rem;
		font-family: var(--font-sans);
	}
	.new-folder-form input:focus,
	.new-folder-form select:focus {
		outline: none;
		border-color: var(--accent);
	}
	.form-actions {
		display: flex;
		gap: 0.5rem;
		justify-content: flex-end;
		margin-top: 0.25rem;
	}
	.tree-list {
		max-height: 300px;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}
	.tree-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 2rem;
		text-align: center;
		color: var(--text-muted);
		font-size: 0.8125rem;
	}
	.tree-empty svg {
		width: 32px;
		height: 32px;
		margin-bottom: 0.75rem;
	}
	.tree-empty small {
		font-size: 0.75rem;
		margin-top: 0.25rem;
	}
	.folder-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
		background: none;
		border: 1px solid transparent;
		cursor: pointer;
		transition: all 0.15s;
		width: 100%;
		text-align: left;
		color: var(--text-primary);
		font-size: 0.8125rem;
	}
	.folder-item:hover {
		background: var(--bg-surface);
		border-color: var(--border);
	}
	.folder-item.selected {
		background: var(--accent-soft);
		border-color: var(--accent);
		color: var(--accent);
	}
	.folder-item svg {
		width: 16px;
		height: 16px;
		flex-shrink: 0;
		color: var(--text-muted);
	}
	.folder-item.selected svg {
		color: var(--accent);
	}
	.folder-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.folder-name {
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.folder-count {
		font-size: 0.65rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
	}
	.check-icon {
		width: 16px;
		height: 16px;
		color: var(--accent);
		flex-shrink: 0;
	}

	/* ─── Preview Panel ─── */
	.workflow-preview,
	.repo-preview {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.preview-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.preview-icon {
		width: 32px;
		height: 32px;
		border-radius: 6px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.preview-icon svg {
		width: 16px;
		height: 16px;
		color: var(--text-muted);
	}
	.preview-icon-primary {
		border-color: var(--accent);
	}
	.preview-icon-primary svg {
		color: var(--accent);
	}
	.preview-name {
		font-weight: 600;
		font-size: 0.875rem;
	}
	.preview-repo,
	.preview-desc {
		font-size: 0.75rem;
		color: var(--text-secondary);
	}
	.preview-details {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 0.75rem;
		background: var(--bg-surface);
		border-radius: 6px;
		border: 1px solid var(--border);
	}
	.detail-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 0.8125rem;
	}
	.detail-item > span:first-child {
		color: var(--text-muted);
		font-size: 0.75rem;
	}
	.triggers-preview {
		display: flex;
		gap: 0.375rem;
		flex-wrap: wrap;
	}
	.status-message {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.75rem;
		border-radius: 8px;
		font-size: 0.8125rem;
	}
	.status-message svg {
		width: 18px;
		height: 18px;
		flex-shrink: 0;
		margin-top: 2px;
	}
	.status-message p {
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin-top: 0.125rem;
	}
	.status-message.success {
		background: rgba(16, 185, 129, 0.05);
		border: 1px solid rgba(16, 185, 129, 0.15);
		color: var(--success);
	}
	.status-message.warning {
		background: rgba(245, 158, 11, 0.05);
		border: 1px solid rgba(245, 158, 11, 0.15);
		color: var(--warning);
	}

	/* ─── Responsive ─── */
	@media (max-width: 1024px) {
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}
		.repositories-grid {
			grid-template-columns: 1fr;
		}
		.modal-grid {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 768px) {
		.nav-menu {
			display: none;
		}
		.workspace-sidebar {
			display: none;
		}
		.workspace-main {
			padding: 1.5rem 1rem;
		}
		.stats-grid {
			grid-template-columns: 1fr;
		}
		.header-content {
			padding: 0 1rem;
		}
		.technical-bar {
			padding: 0 1rem;
		}
		.modal-content-large {
			max-height: 95vh;
		}
		.tree-panel,
		.preview-panel {
			padding: 1rem;
		}
	}
</style>
