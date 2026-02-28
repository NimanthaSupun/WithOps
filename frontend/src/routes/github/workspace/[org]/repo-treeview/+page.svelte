<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { githubClient } from '$lib/github.js';
	import { repositoryTreeClient } from '$lib/repositoryTree.js';
	import { isDarkMode } from '$lib/stores.js';

	const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

	let orgName = $state('');
	let loading = $state(false);
	let error = $state(null);
	let saveStatus = $state('');
	let saveSuccess = $state(false);

	// Subscribe to dark mode
	let darkMode = $state(false);

	$effect(() => {
		const unsubscribe = isDarkMode.subscribe((value) => {
			darkMode = value;
		});
		return unsubscribe;
	});

	// Repository tree structure state
	let repoTreeData = $state([]);
	let selectedNode = $state(null);
	let expandedNodes = $state(new Set());
	let editingNode = $state(null);
	let editingValue = $state('');

	// Modal states
	let showNewFolderModal = $state(false);
	let newFolderName = $state('');
	let newFolderParent = $state(null);

	// Add Repository Modal
	let showAddRepoModal = $state(false);
	let availableRepos = $state([]);
	let selectedRepoToAdd = $state(null);
	let addingRepo = $state(false);
	let loadingRepos = $state(false);

	// Folder Analysis Modal
	let showAnalyzeFolderModal = $state(false);
	let folderToAnalyze = $state(null);
	let analyzingFolder = $state(false);
	let includeSubfolders = $state(true);
	let analysisProgress = $state(null);

	// Analysis Options Modal
	let showAnalysisOptionsModal = $state(false);
	let analysisMode = $state('unified'); // 'unified' | 'folder'
	let folderForFolderAnalysis = $state(null);
	let includeSubfoldersInModal = $state(true);

	// Repository Tree ID for analysis
	let currentRepositoryTreeId = $state(null);

	// Past analysis state
	let hasPastAnalysis = $state(false);
	let checkingAnalysis = $state(false);

	// Statistics
	let statistics = $state({
		totalFolders: 0,
		totalRepos: 0,
		totalWorkflows: 0,
		privateRepos: 0,
		publicRepos: 0
	});

	onMount(async () => {
		orgName = $page.params.org;
		console.log(`🌲 Loading Repository Treeview for organization: ${orgName}`);

		// Initialize theme
		isDarkMode.init();

		await loadRepoTreeData();
		await loadAvailableRepositories();
		await checkForPastAnalysis();
	});

	function toggleTheme() {
		isDarkMode.toggle();
	}

	async function loadRepoTreeData() {
		try {
			loading = true;
			error = null;

			const result = await repositoryTreeClient.getRepositoryTree(orgName);

			if (result.success) {
				repoTreeData = result.data || [];
				// The API returns 'id' in metadata, not 'tree_id'
				currentRepositoryTreeId = result.metadata?.id || result.metadata?.tree_id || null;
				updateStatistics();
				console.log(
					'✅ Repository tree data loaded:',
					repoTreeData,
					'Tree ID:',
					currentRepositoryTreeId,
					'Metadata:',
					result.metadata
				);
			} else {
				console.warn('No existing repository tree data found, starting fresh');
				repoTreeData = [];
				currentRepositoryTreeId = null;
			}
		} catch (err) {
			console.error('Failed to load repository tree:', err);
			error = `Failed to load repository tree: ${err.message}`;
		} finally {
			loading = false;
		}
	}

	async function loadAvailableRepositories() {
		try {
			loadingRepos = true;
			const result = await githubClient.getOrganizationWorkspace(orgName);

			if (result.success && result.repositories) {
				availableRepos = result.repositories;
				console.log(`✅ Loaded ${availableRepos.length} available repositories`);
			}
		} catch (err) {
			console.error('Failed to load available repositories:', err);
		} finally {
			loadingRepos = false;
		}
	}

	async function saveRepoTreeData() {
		try {
			console.log('💾 Saving repository tree...', { org: orgName, itemCount: repoTreeData.length });
			saveStatus = 'Saving...';
			saveSuccess = false;

			const result = await repositoryTreeClient.saveRepositoryTree(orgName, repoTreeData);

			if (result.success && result.tree_id) {
				currentRepositoryTreeId = result.tree_id;
				console.log('✅ Tree ID updated:', currentRepositoryTreeId);
			}

			console.log('📊 Save result:', result);

			if (result.success) {
				saveStatus = 'Saved successfully!';
				saveSuccess = true;
				console.log('✅ Repository tree saved:', result);
				setTimeout(() => {
					saveStatus = '';
					saveSuccess = false;
				}, 3000);
			} else {
				console.error('❌ Save failed:', result.error);
				throw new Error(result.error || 'Failed to save');
			}
		} catch (err) {
			console.error('❌ Failed to save repository tree:', err);
			saveStatus = `Error: ${err.message}`;
			saveSuccess = false;
			showNotification(`Failed to save: ${err.message}`, 'error');
		}
	}

	function updateStatistics() {
		let folders = 0;
		let repos = 0;
		let workflows = 0;
		let privateCount = 0;
		let publicCount = 0;

		function traverse(nodes) {
			for (const node of nodes) {
				if (node.type === 'folder') {
					folders++;
					if (node.children) traverse(node.children);
				} else if (node.type === 'repository') {
					repos++;
					if (node.metadata?.private) privateCount++;
					else publicCount++;
					if (node.children) {
						workflows += node.children.filter((child) => child.type === 'workflow').length;
						traverse(node.children);
					}
				} else if (node.type === 'workflow') {
					workflows++;
				}
			}
		}

		traverse(repoTreeData);

		statistics = {
			totalFolders: folders,
			totalRepos: repos,
			totalWorkflows: workflows,
			privateRepos: privateCount,
			publicRepos: publicCount
		};
	}

	// Create new folder
	function openNewFolderModal(parentNode = null) {
		newFolderParent = parentNode;
		newFolderName = '';
		showNewFolderModal = true;
	}

	function closeNewFolderModal() {
		showNewFolderModal = false;
		newFolderName = '';
		newFolderParent = null;
	}

	async function createNewFolder() {
		if (!newFolderName.trim()) {
			console.warn('❌ Folder name is empty');
			return;
		}

		console.log('📁 Creating new folder:', newFolderName.trim());
		console.log('📁 Parent folder:', newFolderParent ? newFolderParent.name : 'ROOT');

		const newFolder = {
			id: `folder-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
			name: newFolderName.trim(),
			type: 'folder',
			children: [],
			created_at: new Date().toISOString()
		};

		if (newFolderParent && newFolderParent.id) {
			console.log('📂 Adding folder to parent:', newFolderParent.name);

			// Find the actual parent in the tree (in case reference is stale)
			const findAndAddToParent = (nodes) => {
				for (let node of nodes) {
					if (node.id === newFolderParent.id) {
						if (!node.children) {
							node.children = [];
						}
						node.children.push(newFolder);
						return true;
					}
					if (node.children && findAndAddToParent(node.children)) {
						return true;
					}
				}
				return false;
			};

			if (!findAndAddToParent(repoTreeData)) {
				console.error('❌ Parent folder not found in tree, adding to root instead');
				repoTreeData.push(newFolder);
			}
		} else {
			console.log('📂 Adding folder to root');
			repoTreeData.push(newFolder);
		}

		// Trigger reactivity
		repoTreeData = [...repoTreeData];
		updateStatistics();

		console.log('📊 Tree data after adding folder:', repoTreeData);
		console.log('💾 Saving tree data with new folder...');

		await saveRepoTreeData();

		console.log('✅ Folder created successfully');
		showNotification(`Folder "${newFolderName.trim()}" created successfully!`, 'success');
		closeNewFolderModal();
	}

	// Add Repository to tree
	function openAddRepoModal() {
		showAddRepoModal = true;
		selectedRepoToAdd = null;
	}

	function closeAddRepoModal() {
		showAddRepoModal = false;
		selectedRepoToAdd = null;
	}

	async function addRepositoryToTree() {
		if (!selectedRepoToAdd || !selectedNode) return;

		if (selectedNode.type !== 'folder') {
			alert('Please select a folder to add the repository to');
			return;
		}

		try {
			addingRepo = true;

			// Create repository folder item
			const repoItem = {
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
					addedFrom: 'repo-treeview'
				},
				children: []
			};

			// Fetch all workflows from the repository
			const workflows = selectedRepoToAdd.workflows || [];

			for (const workflow of workflows) {
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
					repoItem.children.push(workflowItem);
				}
			}

			// Add to selected folder
			if (!selectedNode.children) {
				selectedNode.children = [];
			}
			selectedNode.children.push(repoItem);

			repoTreeData = [...repoTreeData];
			updateStatistics();
			await saveRepoTreeData();

			showNotification(
				`Repository "${selectedRepoToAdd.name}" added with ${workflows.length} workflows!`,
				'success'
			);
			closeAddRepoModal();
		} catch (err) {
			console.error('Failed to add repository:', err);
			showNotification('Failed to add repository', 'error');
		} finally {
			addingRepo = false;
		}
	}

	// Node operations
	function toggleNode(event, node) {
		event?.stopPropagation();
		if (expandedNodes.has(node.id)) {
			expandedNodes.delete(node.id);
		} else {
			expandedNodes.add(node.id);
		}
		expandedNodes = new Set(expandedNodes);
	}

	function selectNode(node) {
		selectedNode = node;
	}

	function deleteNode(nodeToDelete) {
		if (!confirm(`Are you sure you want to delete "${nodeToDelete.name}"?`)) {
			return;
		}

		function removeFromTree(nodes, targetId) {
			for (let i = 0; i < nodes.length; i++) {
				if (nodes[i].id === targetId) {
					nodes.splice(i, 1);
					return true;
				}
				if (nodes[i].children) {
					if (removeFromTree(nodes[i].children, targetId)) {
						return true;
					}
				}
			}
			return false;
		}

		removeFromTree(repoTreeData, nodeToDelete.id);
		repoTreeData = [...repoTreeData];
		updateStatistics();
		saveRepoTreeData();
	}

	function startEditing(node) {
		editingNode = node;
		editingValue = node.name;
	}

	function saveEdit() {
		if (editingNode && editingValue.trim()) {
			editingNode.name = editingValue.trim();
			repoTreeData = [...repoTreeData];
			saveRepoTreeData();
		}
		editingNode = null;
		editingValue = '';
	}

	function cancelEdit() {
		editingNode = null;
		editingValue = '';
	}

	function showNotification(message, type = 'info') {
		const notification = document.createElement('div');
		notification.className = `notification ${type}`;
		notification.textContent = message;

		document.body.appendChild(notification);

		setTimeout(() => {
			notification.classList.add('fade-out');
			setTimeout(() => notification.remove(), 300);
		}, 3000);
	}

	// Get flattened folder list for selection
	function getFlattenedFolders(nodes, depth = 0) {
		let result = [];
		for (const node of nodes) {
			if (node.type === 'folder') {
				result.push({ ...node, depth });
				if (node.children) {
					result.push(...getFlattenedFolders(node.children, depth + 1));
				}
			}
		}
		return result;
	}

	// Helper to count items in node
	function countItemsInNode(node) {
		if (!node || !node.children) return 0;
		let count = 0;
		for (const child of node.children) {
			count++;
			if (child.children) {
				count += countItemsInNode(child);
			}
		}
		return count;
	}

	// Folder Analysis Functions
	function openAnalyzeFolderModal(node) {
		folderToAnalyze = node;
		showAnalyzeFolderModal = true;
		includeSubfolders = true;
		analysisProgress = null;
	}

	function closeAnalyzeFolderModal() {
		showAnalyzeFolderModal = false;
		folderToAnalyze = null;
		analyzingFolder = false;
		analysisProgress = null;
	}

	async function triggerFolderAnalysis() {
		if (!folderToAnalyze || !currentRepositoryTreeId) {
			console.error('❌ Missing folder or repository tree ID');
			return;
		}

		analyzingFolder = true;
		analysisProgress = 'Preparing folder analysis...';

		try {
			const folderPath = getFolderPath(folderToAnalyze);
			const repoCount = countRepositoriesInFolder(folderToAnalyze);

			analysisProgress = `Analyzing ${repoCount} repositories in ${folderPath}...`;

			// Get authentication token (same logic as repositoryTreeClient)
			const token =
				localStorage.getItem('auth_token') ||
				sessionStorage.getItem('auth_token') ||
				localStorage.getItem('github_token');

			if (!token) {
				throw new Error('Authentication required. Please login first.');
			}

			const response = await fetch(`${API_BASE_URL}/api/workspace-intelligence/analyze-folder`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					organization_name: orgName,
					tree_data: repoTreeData,
					repository_tree_id: currentRepositoryTreeId,
					folder_id: folderToAnalyze.id,
					folder_path: folderPath,
					include_subfolders: includeSubfolders
				})
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || 'Failed to start folder analysis');
			}

			const result = await response.json();
			console.log('✅ Folder analysis started:', result);

			analysisProgress = 'Analysis started successfully! Redirecting...';

			// Close modal and redirect to intelligence dashboard
			setTimeout(() => {
				closeAnalyzeFolderModal();
				goto(`/github/workspace/${orgName}/intelligence`);
			}, 1500);
		} catch (error) {
			console.error('❌ Error triggering folder analysis:', error);
			analysisProgress = null;
			analyzingFolder = false;
			alert(`Failed to start folder analysis: ${error.message}`);
		}
	}

	function getFolderPath(node) {
		if (!node) return '';
		const path = [];
		let current = node;

		while (current) {
			if (current.name) path.unshift(current.name);
			current = current.parent;
		}

		return path.join('/') || node.name;
	}

	function countRepositoriesInFolder(node) {
		if (!node) return 0;
		let count = 0;

		function traverse(n) {
			if (!n) return;
			if (n.type === 'repository') {
				count++;
			}
			if (n.children) {
				for (const child of n.children) {
					traverse(child);
				}
			}
		}

		traverse(node);
		return count;
	}

	// Analysis Options Modal Functions
	function openAnalysisOptionsModal() {
		if (!currentRepositoryTreeId) {
			alert('Please save your repository tree first before running analysis');
			return;
		}
		showAnalysisOptionsModal = true;
		analysisMode = 'unified';
		folderForFolderAnalysis = null;
	}

	function closeAnalysisOptionsModal() {
		showAnalysisOptionsModal = false;
	}

	async function startUnifiedAnalysis() {
		if (!currentRepositoryTreeId) {
			alert('Please save your repository tree first');
			return;
		}

		closeAnalysisOptionsModal();
		loading = true;

		try {
			const token =
				localStorage.getItem('auth_token') ||
				sessionStorage.getItem('auth_token') ||
				localStorage.getItem('github_token');

			if (!token) {
				throw new Error('Authentication required. Please login first.');
			}

			const response = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/analyze-workspace-unified`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${token}`
					},
					body: JSON.stringify({
						organization_name: orgName,
						tree_data: repoTreeData,
						repository_tree_id: currentRepositoryTreeId,
						fetch_github_data: true
					})
				}
			);

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || 'Failed to start unified analysis');
			}

			const result = await response.json();
			console.log('✅ Unified analysis started:', result);

			showNotification('Unified workspace analysis started! Redirecting...', 'success');

			setTimeout(() => {
				goto(`/github/workspace/${orgName}/intelligence`);
			}, 2000);
		} catch (error) {
			console.error('❌ Error starting unified analysis:', error);
			alert(`Failed to start analysis: ${error.message}`);
		} finally {
			loading = false;
		}
	}

	async function startFolderAnalysisFromModal() {
		if (!folderForFolderAnalysis || !currentRepositoryTreeId) {
			alert('Please select a folder');
			return;
		}

		closeAnalysisOptionsModal();

		// Use existing folder analysis logic
		folderToAnalyze = folderForFolderAnalysis;
		includeSubfolders = includeSubfoldersInModal;
		await triggerFolderAnalysis();
	}

	// Check if past analysis exists (for button display)
	async function checkForPastAnalysis() {
		try {
			checkingAnalysis = true;
			const token =
				localStorage.getItem('auth_token') ||
				sessionStorage.getItem('auth_token') ||
				localStorage.getItem('github_token');

			if (!token) {
				hasPastAnalysis = false;
				return;
			}

			const response = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/analysis/${orgName}`,
				{
					method: 'GET',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${token}`
					}
				}
			);

			if (response.ok) {
				const result = await response.json();
				hasPastAnalysis = result && (result.analyses?.length > 0 || result.analysis);
				console.log('✅ Past analysis check:', hasPastAnalysis);
			} else {
				hasPastAnalysis = false;
			}
		} catch (error) {
			console.error('❌ Error checking for past analysis:', error);
			hasPastAnalysis = false;
		} finally {
			checkingAnalysis = false;
		}
	}

	// Navigate directly to intelligence dashboard
	function navigateToDashboard() {
		goto(`/github/workspace/${orgName}/intelligence`);
	}

	// Check if analysis exists and navigate to intelligence page
	async function checkAndNavigateToIntelligence() {
		try {
			const token =
				localStorage.getItem('auth_token') ||
				sessionStorage.getItem('auth_token') ||
				localStorage.getItem('github_token');

			if (!token) {
				// If no auth, just show the modal to run new analysis
				openAnalysisOptionsModal();
				return;
			}

			// Check if there's existing analysis data
			const response = await fetch(
				`${API_BASE_URL}/api/workspace-intelligence/analysis/${orgName}`,
				{
					method: 'GET',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${token}`
					}
				}
			);

			if (response.ok) {
				const result = await response.json();
				// If we have existing analysis, navigate directly to intelligence page
				if (result && (result.analyses?.length > 0 || result.analysis)) {
					console.log('✅ Found existing analysis, navigating to intelligence page...');
					goto(`/github/workspace/${orgName}/intelligence`);
					return;
				}
			}

			// If no existing analysis or error fetching, show the modal
			console.log('ℹ️ No existing analysis found, showing analysis options...');
			openAnalysisOptionsModal();
		} catch (error) {
			console.error('❌ Error checking for existing analysis:', error);
			// On error, default to showing the modal
			openAnalysisOptionsModal();
		}
	}
</script>

<svelte:head>
	<title>Repository Treeview - {orgName} - WithOps</title>
</svelte:head>

<div class="page {darkMode ? 'dark' : 'light'}">
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
				<a href="/github/workspace/{orgName}/repo-treeview" class="nav-link active">Treeview</a>
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
		<a href="/dashboard" class="bc-node">WithOps</a>
		<span class="bc-sep">/</span>
		<a href="/organizations" class="bc-node">Organizations</a>
		<span class="bc-sep">/</span>
		<a href="/github/workspace/{orgName}" class="bc-node">{orgName}</a>
		<span class="bc-sep">/</span>
		<span class="bc-node active">Treeview</span>
		<div class="system-status">
			<div class="status-pulse"></div>
			TREE: ACTIVE
		</div>
	</div>

	<!-- Main Layout -->
	<div class="page-layout">
		<!-- Sidebar -->
		<aside class="sidebar">
			<button
				onclick={() => goto(`/github/workspace/${orgName}`)}
				class="btn btn-outline btn-full btn-sm"
			>
				<svg
					width="14"
					height="14"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					stroke-width="2"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
				</svg>
				Back to Workspace
			</button>

			<!-- Stats -->
			<div class="sidebar-section">
				<h4 class="section-label">STATISTICS</h4>
				<div class="stats-grid">
					<div class="stat-cell">
						<span class="stat-val">{statistics.totalFolders}</span>
						<span class="stat-lbl">Folders</span>
					</div>
					<div class="stat-cell">
						<span class="stat-val">{statistics.totalRepos}</span>
						<span class="stat-lbl">Repos</span>
					</div>
					<div class="stat-cell">
						<span class="stat-val">{statistics.totalWorkflows}</span>
						<span class="stat-lbl">Flows</span>
					</div>
					<div class="stat-cell">
						<span class="stat-val">{statistics.privateRepos}</span>
						<span class="stat-lbl">Private</span>
					</div>
					<div class="stat-cell">
						<span class="stat-val">{statistics.publicRepos}</span>
						<span class="stat-lbl">Public</span>
					</div>
				</div>
			</div>

			<!-- Actions -->
			<div class="sidebar-section">
				<h4 class="section-label">ACTIONS</h4>
				<div class="sidebar-actions">
					<button onclick={checkAndNavigateToIntelligence} class="btn btn-primary btn-full btn-sm">
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
							/>
						</svg>
						Workspace Intelligence
					</button>

					{#if hasPastAnalysis}
						<button onclick={navigateToDashboard} class="btn btn-secondary btn-full btn-sm">
							<svg
								width="14"
								height="14"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								stroke-width="2"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
								/>
							</svg>
							Intelligence Dashboard
						</button>
					{/if}

					<button onclick={openNewFolderModal} class="btn btn-secondary btn-full btn-sm">
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
							/>
						</svg>
						New Folder
					</button>

					<button onclick={openAddRepoModal} class="btn btn-secondary btn-full btn-sm">
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						Add Repository
					</button>

					<button onclick={() => goto(`/github/workspace/${orgName}/intelligence`)} class="btn btn-primary btn-full btn-sm">
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
							/>
						</svg>
						Dashboard
					</button>
				</div>
			</div>

			<!-- Save Status -->
			{#if saveStatus}
				<div class="save-indicator {saveSuccess ? 'success' : 'error'}">
					{saveStatus}
				</div>
			{/if}
		</aside>

		<!-- Main Content -->
		<main class="page-main">
			{#if loading}
				<div class="center-state">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="loader-text">SCANNING REPOSITORIES...</div>
				</div>
			{:else if error}
				<div class="center-state">
					<p class="error-text">{error}</p>
					<button onclick={loadRepoTreeData} class="btn btn-primary">Retry</button>
				</div>
			{:else if repoTreeData.length === 0}
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
							d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z"
						/>
					</svg>
					<h3>No repositories organized yet</h3>
					<p class="empty-desc">
						Start by creating a folder and adding repositories from your organization.
					</p>
					<div class="empty-actions">
						<button onclick={openNewFolderModal} class="btn btn-primary">Create First Folder</button
						>
						<button onclick={openAddRepoModal} class="btn btn-secondary">Add Repository</button>
					</div>
				</div>
			{:else}
				<!-- Folder Cards Grid -->
				<div class="tree-grid">
					{#each repoTreeData as node}
						{#if node.type === 'folder'}
							<div class="tree-card">
								<div class="tree-card-header">
									<button
										onclick={(e) => toggleNode(e, node)}
										class="expand-toggle"
										aria-label={expandedNodes.has(node.id) ? 'Collapse' : 'Expand'}
									>
										<svg
											class="expand-chevron {expandedNodes.has(node.id) ? 'open' : ''}"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
											stroke-width="2"
										>
											<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
										</svg>
									</button>
									<svg
										class="node-icon folder"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
										stroke-width="2"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
										/>
									</svg>
									{#if editingNode?.id === node.id}
										<input
											bind:value={editingValue}
											onblur={saveEdit}
											onkeydown={(e) => e.key === 'Enter' && saveEdit()}
											class="inline-edit"
										/>
									{:else}
										<span class="node-name">{node.name}</span>
									{/if}
									<span class="node-meta">{countItemsInNode(node)} items</span>
									<div class="node-actions">
										<button
											onclick={() => openAnalyzeFolderModal(node)}
											class="icon-btn"
											title="Analyze"
											aria-label="Analyze"
											><svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
												><path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
												/></svg
											></button
										>
										<button
											onclick={() => startEditing(node)}
											class="icon-btn"
											title="Rename"
											aria-label="Rename"
											><svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
												><path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
												/></svg
											></button
										>
										<button
											onclick={() => openNewFolderModal(node)}
											class="icon-btn"
											title="Add subfolder"
											aria-label="Add subfolder"
											><svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
												><path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M12 4v16m8-8H4"
												/></svg
											></button
										>
										<button
											onclick={() => deleteNode(node)}
											class="icon-btn danger"
											title="Delete"
											aria-label="Delete"
											><svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
												><path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
												/></svg
											></button
										>
									</div>
								</div>

								{#if expandedNodes.has(node.id) && node.children}
									<div class="tree-children">
										{#each node.children as child}
											{#if child.type === 'folder'}
												<!-- Nested Folder -->
												<div class="nested-folder">
													<div class="tree-row">
														<button
															onclick={(e) => toggleNode(e, child)}
															class="expand-toggle sm"
															aria-label={expandedNodes.has(child.id) ? 'Collapse' : 'Expand'}
														>
															<svg
																class="expand-chevron {expandedNodes.has(child.id) ? 'open' : ''}"
																fill="none"
																stroke="currentColor"
																viewBox="0 0 24 24"
																stroke-width="2"
																><path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="M9 5l7 7-7 7"
																/></svg
															>
														</button>
														<svg
															class="node-icon folder sm"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
															stroke-width="2"
															><path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
															/></svg
														>
														{#if editingNode?.id === child.id}
															<input
																bind:value={editingValue}
																onblur={saveEdit}
																onkeydown={(e) => e.key === 'Enter' && saveEdit()}
																class="inline-edit sm"
															/>
														{:else}
															<span class="node-name">{child.name}</span>
														{/if}
														<span class="node-meta">{countItemsInNode(child)} items</span>
														<div class="node-actions">
															<button
																onclick={() => openAnalyzeFolderModal(child)}
																class="icon-btn sm"
																title="Analyze"
																aria-label="Analyze"
																><svg
																	fill="none"
																	stroke="currentColor"
																	viewBox="0 0 24 24"
																	stroke-width="2"
																	><path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
																	/></svg
																></button
															>
															<button
																onclick={() => startEditing(child)}
																class="icon-btn sm"
																title="Rename"
																aria-label="Rename"
																><svg
																	fill="none"
																	stroke="currentColor"
																	viewBox="0 0 24 24"
																	stroke-width="2"
																	><path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
																	/></svg
																></button
															>
															<button
																onclick={() => openNewFolderModal(child)}
																class="icon-btn sm"
																title="Add subfolder"
																aria-label="Add subfolder"
																><svg
																	fill="none"
																	stroke="currentColor"
																	viewBox="0 0 24 24"
																	stroke-width="2"
																	><path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		d="M12 4v16m8-8H4"
																	/></svg
																></button
															>
															<button
																onclick={() => deleteNode(child)}
																class="icon-btn danger sm"
																title="Delete"
																aria-label="Delete"
																><svg
																	fill="none"
																	stroke="currentColor"
																	viewBox="0 0 24 24"
																	stroke-width="2"
																	><path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
																	/></svg
																></button
															>
														</div>
													</div>

													{#if expandedNodes.has(child.id) && child.children}
														<div class="tree-children nested">
															{#each child.children as nestedChild}
																{#if nestedChild.type === 'folder'}
																	<div class="nested-folder deeper">
																		<div class="tree-row">
																			<button
																				onclick={(e) => toggleNode(e, nestedChild)}
																				class="expand-toggle sm"
																				aria-label="Toggle"
																			>
																				<svg
																					class="expand-chevron {expandedNodes.has(nestedChild.id)
																						? 'open'
																						: ''}"
																					fill="none"
																					stroke="currentColor"
																					viewBox="0 0 24 24"
																					stroke-width="2"
																					><path
																						stroke-linecap="round"
																						stroke-linejoin="round"
																						d="M9 5l7 7-7 7"
																					/></svg
																				>
																			</button>
																			<svg
																				class="node-icon folder sm"
																				fill="none"
																				stroke="currentColor"
																				viewBox="0 0 24 24"
																				stroke-width="2"
																				><path
																					stroke-linecap="round"
																					stroke-linejoin="round"
																					d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
																				/></svg
																			>
																			<span class="node-name">{nestedChild.name}</span>
																			<span class="node-meta"
																				>{countItemsInNode(nestedChild)} items</span
																			>
																			<div class="node-actions">
																				<button
																					onclick={() => openAnalyzeFolderModal(nestedChild)}
																					class="icon-btn sm"
																					title="Analyze"
																					aria-label="Analyze"
																					><svg
																						fill="none"
																						stroke="currentColor"
																						viewBox="0 0 24 24"
																						stroke-width="2"
																						><path
																							stroke-linecap="round"
																							stroke-linejoin="round"
																							d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
																						/></svg
																					></button
																				>
																				<button
																					onclick={() => startEditing(nestedChild)}
																					class="icon-btn sm"
																					title="Rename"
																					aria-label="Rename"
																					><svg
																						fill="none"
																						stroke="currentColor"
																						viewBox="0 0 24 24"
																						stroke-width="2"
																						><path
																							stroke-linecap="round"
																							stroke-linejoin="round"
																							d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
																						/></svg
																					></button
																				>
																				<button
																					onclick={() => openNewFolderModal(nestedChild)}
																					class="icon-btn sm"
																					title="Subfolder"
																					aria-label="Subfolder"
																					><svg
																						fill="none"
																						stroke="currentColor"
																						viewBox="0 0 24 24"
																						stroke-width="2"
																						><path
																							stroke-linecap="round"
																							stroke-linejoin="round"
																							d="M12 4v16m8-8H4"
																						/></svg
																					></button
																				>
																				<button
																					onclick={() => deleteNode(nestedChild)}
																					class="icon-btn danger sm"
																					title="Delete"
																					aria-label="Delete"
																					><svg
																						fill="none"
																						stroke="currentColor"
																						viewBox="0 0 24 24"
																						stroke-width="2"
																						><path
																							stroke-linecap="round"
																							stroke-linejoin="round"
																							d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
																						/></svg
																					></button
																				>
																			</div>
																		</div>
																		{#if expandedNodes.has(nestedChild.id) && nestedChild.children}
																			<div class="tree-children nested deeper">
																				{#each nestedChild.children as deepChild}
																					{#if deepChild.type === 'repository'}
																						<div class="repo-row">
																							<svg
																								class="node-icon repo"
																								fill="none"
																								stroke="currentColor"
																								viewBox="0 0 24 24"
																								stroke-width="2"
																								><path
																									stroke-linecap="round"
																									stroke-linejoin="round"
																									d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
																								/></svg
																							>
																							<span class="node-name">{deepChild.name}</span>
																							{#if deepChild.metadata?.private}<span
																									class="tag private">Private</span
																								>{/if}
																							{#if deepChild.children}<span class="node-meta"
																									>{deepChild.children.length} workflows</span
																								>{/if}
																							<div class="node-actions">
																								{#if deepChild.metadata?.html_url}<a
																										href={deepChild.metadata.html_url}
																										target="_blank"
																										class="icon-btn sm"
																										title="Open in GitHub"
																										aria-label="Open in GitHub"
																										><svg
																											fill="none"
																											stroke="currentColor"
																											viewBox="0 0 24 24"
																											stroke-width="2"
																											><path
																												stroke-linecap="round"
																												stroke-linejoin="round"
																												d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
																											/></svg
																										></a
																									>{/if}
																								<button
																									onclick={() => deleteNode(deepChild)}
																									class="icon-btn danger sm"
																									title="Remove"
																									aria-label="Remove"
																									><svg
																										fill="none"
																										stroke="currentColor"
																										viewBox="0 0 24 24"
																										stroke-width="2"
																										><path
																											stroke-linecap="round"
																											stroke-linejoin="round"
																											d="M6 18L18 6M6 6l12 12"
																										/></svg
																									></button
																								>
																							</div>
																						</div>
																					{/if}
																				{/each}
																			</div>
																		{/if}
																	</div>
																{:else if nestedChild.type === 'repository'}
																	<div class="repo-row">
																		<svg
																			class="node-icon repo"
																			fill="none"
																			stroke="currentColor"
																			viewBox="0 0 24 24"
																			stroke-width="2"
																			><path
																				stroke-linecap="round"
																				stroke-linejoin="round"
																				d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
																			/></svg
																		>
																		<span class="node-name">{nestedChild.name}</span>
																		{#if nestedChild.metadata?.private}<span class="tag private"
																				>Private</span
																			>{/if}
																		{#if nestedChild.children}<span class="node-meta"
																				>{nestedChild.children.length} workflows</span
																			>{/if}
																		<div class="node-actions">
																			{#if nestedChild.metadata?.html_url}<a
																					href={nestedChild.metadata.html_url}
																					target="_blank"
																					class="icon-btn sm"
																					title="Open in GitHub"
																					aria-label="Open in GitHub"
																					><svg
																						fill="none"
																						stroke="currentColor"
																						viewBox="0 0 24 24"
																						stroke-width="2"
																						><path
																							stroke-linecap="round"
																							stroke-linejoin="round"
																							d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
																						/></svg
																					></a
																				>{/if}
																			<button
																				onclick={() => deleteNode(nestedChild)}
																				class="icon-btn danger sm"
																				title="Remove"
																				aria-label="Remove"
																				><svg
																					fill="none"
																					stroke="currentColor"
																					viewBox="0 0 24 24"
																					stroke-width="2"
																					><path
																						stroke-linecap="round"
																						stroke-linejoin="round"
																						d="M6 18L18 6M6 6l12 12"
																					/></svg
																				></button
																			>
																		</div>
																	</div>
																{/if}
															{/each}
														</div>
													{/if}
												</div>
											{:else if child.type === 'repository'}
												<div class="repo-row">
													<svg
														class="node-icon repo"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
														stroke-width="2"
														><path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
														/></svg
													>
													<span class="node-name">{child.name}</span>
													{#if child.metadata?.private}<span class="tag private">Private</span>{/if}
													{#if child.children}<span class="node-meta"
															>{child.children.length} workflows</span
														>{/if}
													<div class="node-actions">
														{#if child.metadata?.html_url}<a
																href={child.metadata.html_url}
																target="_blank"
																class="icon-btn sm"
																title="Open in GitHub"
																aria-label="Open in GitHub"
																><svg
																	fill="none"
																	stroke="currentColor"
																	viewBox="0 0 24 24"
																	stroke-width="2"
																	><path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
																	/></svg
																></a
															>{/if}
														<button
															onclick={() => deleteNode(child)}
															class="icon-btn danger sm"
															title="Remove"
															aria-label="Remove"
															><svg
																fill="none"
																stroke="currentColor"
																viewBox="0 0 24 24"
																stroke-width="2"
																><path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="M6 18L18 6M6 6l12 12"
																/></svg
															></button
														>
													</div>
												</div>
											{/if}
										{/each}
									</div>
								{/if}
							</div>
						{/if}
					{/each}
				</div>
			{/if}
		</main>
	</div>
</div>

<!-- ═══════════════════════════════════════════
     MODAL: Create New Folder
     ═══════════════════════════════════════════ -->
{#if showNewFolderModal}
	<div
		class="modal-backdrop"
		onclick={closeNewFolderModal}
		onkeydown={(e) => e.key === 'Escape' && closeNewFolderModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container {darkMode ? 'dark' : 'light'}"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title">Create New Folder</h3>
					<p class="modal-subtitle">Organize your repositories into logical groups</p>
				</div>
				<button onclick={closeNewFolderModal} class="modal-close" aria-label="Close modal">
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
				<div class="form-group">
					<label for="new-folder-name" class="form-label">Folder Name *</label>
					<input
						id="new-folder-name"
						type="text"
						bind:value={newFolderName}
						placeholder="e.g. Frontend Services"
						class="form-input"
						onkeypress={(e) => e.key === 'Enter' && createNewFolder()}
					/>
				</div>
				{#if newFolderParent}
					<div class="info-box">
						<svg
							class="info-icon"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<p class="info-text">
							Creating inside <strong>{newFolderParent.name}</strong>
						</p>
					</div>
				{/if}
			</div>

			<div class="modal-footer">
				<button onclick={closeNewFolderModal} class="btn btn-secondary">Cancel</button>
				<button onclick={createNewFolder} disabled={!newFolderName.trim()} class="btn btn-primary"
					>Create Folder</button
				>
			</div>
		</div>
	</div>
{/if}

<!-- ═══════════════════════════════════════════
     MODAL: Add Repository to Tree
     ═══════════════════════════════════════════ -->
{#if showAddRepoModal}
	<div
		class="modal-backdrop"
		onclick={closeAddRepoModal}
		onkeydown={(e) => e.key === 'Escape' && closeAddRepoModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container modal-wide {darkMode ? 'dark' : 'light'}"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title">Add Repository to Tree</h3>
					<p class="modal-subtitle">Select a repository and choose the target folder</p>
				</div>
				<button onclick={closeAddRepoModal} class="modal-close" aria-label="Close modal">
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
				<div class="dlg-columns">
					<!-- Left: Repositories -->
					<div class="dlg-col">
						<div class="dlg-col-head">
							<span class="dlg-col-title">Repositories</span>
							<span class="dlg-col-count">{availableRepos.length}</span>
						</div>
						<div class="dlg-col-list">
							{#if loadingRepos}
								<div class="dlg-empty-state">
									<div class="spinner"></div>
									<span>Loading repositories...</span>
								</div>
							{:else if availableRepos.length === 0}
								<div class="dlg-empty-state">No repositories available</div>
							{:else}
								{#each availableRepos as repo}
									<button
										class="dlg-list-item {selectedRepoToAdd?.name === repo.name ? 'active' : ''}"
										onclick={() => (selectedRepoToAdd = repo)}
									>
										<div class="dlg-item-top-row">
											<span class="dlg-item-name">{repo.name}</span>
											{#if selectedRepoToAdd?.name === repo.name}
												<svg
													class="dlg-check"
													width="16"
													height="16"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
													stroke-width="2.5"
													><path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M5 13l4 4L19 7"
													/></svg
												>
											{/if}
										</div>
										{#if repo.description}
											<p class="dlg-item-desc">{repo.description}</p>
										{/if}
										<div class="dlg-item-tags">
											{#if repo.language}
												<span class="dlg-tag"
													><span class="dlg-lang-dot"></span>{repo.language}</span
												>
											{/if}
											<span class="dlg-tag">{repo.workflow_count || 0} workflows</span>
											{#if repo.private}<span class="dlg-tag dim">Private</span>{/if}
										</div>
									</button>
								{/each}
							{/if}
						</div>
					</div>

					<!-- Right: Folders -->
					<div class="dlg-col">
						<div class="dlg-col-head">
							<span class="dlg-col-title">Target Folder</span>
						</div>
						<div class="dlg-col-list">
							{#if repoTreeData.length === 0}
								<div class="dlg-empty-state">
									<p>No folders created yet</p>
									<button
										class="dlg-link"
										onclick={() => {
											closeAddRepoModal();
											openNewFolderModal();
										}}>Create your first folder</button
									>
								</div>
							{:else}
								{#each getFlattenedFolders(repoTreeData) as folder}
									<button
										class="dlg-list-item {selectedNode?.id === folder.id ? 'active' : ''}"
										onclick={() => (selectedNode = folder)}
										style="padding-left: {12 + folder.depth * 16}px"
									>
										<svg
											class="dlg-folder-icon"
											width="16"
											height="16"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
											stroke-width="2"
											style="flex-shrink:0"
											><path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
											/></svg
										>
										<span class="dlg-item-name">{folder.name}</span>
										{#if selectedNode?.id === folder.id}
											<svg
												class="dlg-check"
												width="16"
												height="16"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
												stroke-width="2.5"
												><path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M5 13l4 4L19 7"
												/></svg
											>
										{/if}
									</button>
								{/each}
							{/if}
						</div>
						{#if selectedRepoToAdd && selectedNode}
							<div class="dlg-confirm-bar">
								<svg
									width="14"
									height="14"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
									stroke-width="2"
									><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg
								>
								<span
									><strong>{selectedRepoToAdd.name}</strong> &rarr;
									<strong>{selectedNode.name}</strong></span
								>
							</div>
						{/if}
					</div>
				</div>
			</div>

			<div class="modal-footer">
				<button onclick={closeAddRepoModal} class="btn btn-secondary">Cancel</button>
				<button
					onclick={addRepositoryToTree}
					disabled={!selectedRepoToAdd || !selectedNode || addingRepo}
					class="btn btn-primary"
				>
					{#if addingRepo}<span class="btn-spinner"></span> Adding...{:else}Add Repository{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- ═══════════════════════════════════════════
     MODAL: Analyze Folder
     ═══════════════════════════════════════════ -->
{#if showAnalyzeFolderModal}
	<div
		class="modal-backdrop"
		onclick={closeAnalyzeFolderModal}
		onkeydown={(e) => e.key === 'Escape' && closeAnalyzeFolderModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container {darkMode ? 'dark' : 'light'}"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title">Analyze Folder</h3>
					<p class="modal-subtitle">Run OWASP DSOMM security analysis on this folder</p>
				</div>
				<button onclick={closeAnalyzeFolderModal} class="modal-close" aria-label="Close modal">
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
				{#if folderToAnalyze}
					<!-- Folder Info Card -->
					<div class="dlg-info-card">
						<div class="dlg-info-row">
							<span class="dlg-info-key">Folder</span>
							<span class="dlg-info-val">{folderToAnalyze.name}</span>
						</div>
						<div class="dlg-info-row">
							<span class="dlg-info-key">Path</span>
							<span class="dlg-info-val">{getFolderPath(folderToAnalyze)}</span>
						</div>
						<div class="dlg-info-row">
							<span class="dlg-info-key">Repositories</span>
							<span class="dlg-info-val highlight"
								>{countRepositoriesInFolder(folderToAnalyze)}</span
							>
						</div>
					</div>

					<!-- Subfolder Toggle -->
					<label class="dlg-toggle-row">
						<input type="checkbox" bind:checked={includeSubfolders} disabled={analyzingFolder} />
						<div class="dlg-toggle-text">
							<span class="dlg-toggle-label">Include subfolders</span>
							<span class="dlg-toggle-hint"
								>Analyze all nested subfolders and their repositories</span
							>
						</div>
					</label>

					{#if analyzingFolder}
						<div class="dlg-progress">
							<div class="spinner"></div>
							<p>{analysisProgress}</p>
						</div>
					{:else}
						<div class="info-box">
							<svg
								class="info-icon"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								stroke-width="2"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							<p class="info-text">
								This will analyze {includeSubfolders
									? 'this folder and all subfolders'
									: 'only direct repositories'} using the OWASP DSOMM framework.
							</p>
						</div>
					{/if}
				{/if}
			</div>

			<div class="modal-footer">
				<button
					onclick={closeAnalyzeFolderModal}
					class="btn btn-secondary"
					disabled={analyzingFolder}>Cancel</button
				>
				<button
					onclick={() => triggerFolderAnalysis()}
					disabled={analyzingFolder}
					class="btn btn-primary"
				>
					{#if analyzingFolder}<span class="btn-spinner"></span> Analyzing...{:else}Start Analysis{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- ═══════════════════════════════════════════
     MODAL: Choose Analysis Approach
     ═══════════════════════════════════════════ -->
{#if showAnalysisOptionsModal}
	<div
		class="modal-backdrop"
		onclick={closeAnalysisOptionsModal}
		onkeydown={(e) => e.key === 'Escape' && closeAnalysisOptionsModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container modal-wide {darkMode ? 'dark' : 'light'}"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title">Choose Analysis Approach</h3>
					<p class="modal-subtitle">Select how you want to analyze your workspace</p>
				</div>
				<button onclick={closeAnalysisOptionsModal} class="modal-close" aria-label="Close modal">
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
				<div class="dlg-option-grid">
					<!-- Unified Analysis Card -->
					<div
						class="dlg-option-card {analysisMode === 'unified' ? 'active' : ''}"
						onclick={() => (analysisMode = 'unified')}
						onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (analysisMode = 'unified')}
						role="button"
						tabindex="0"
					>
						<div class="dlg-option-top">
							<input
								type="radio"
								name="analysis-mode-dlg"
								checked={analysisMode === 'unified'}
								onchange={() => (analysisMode = 'unified')}
							/>
							<span class="dlg-option-name">Unified Workspace Analysis</span>
							<span class="dlg-badge green">Recommended</span>
						</div>
						<p class="dlg-option-desc">
							Analyze all folders and repositories in one comprehensive assessment. Perfect for
							executive dashboards and organization-wide visibility.
						</p>
						<ul class="dlg-feature-list">
							<li>Organization-wide maturity score</li>
							<li>Complete security posture assessment</li>
							<li>Cross-team comparison built-in</li>
							<li>Executive-ready dashboards</li>
						</ul>
						<div class="dlg-option-stats">
							<span>{statistics.totalRepos} repos</span>
							<span>{statistics.totalFolders} folders</span>
							<span>~{Math.ceil(statistics.totalRepos / 20)} min</span>
						</div>
						{#if analysisMode === 'unified'}
							<button class="btn btn-primary btn-full mt" onclick={startUnifiedAnalysis}
								>Start Unified Analysis</button
							>
						{/if}
					</div>

					<!-- Folder Analysis Card -->
					<div
						class="dlg-option-card {analysisMode === 'folder' ? 'active' : ''}"
						onclick={() => (analysisMode = 'folder')}
						onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (analysisMode = 'folder')}
						role="button"
						tabindex="0"
					>
						<div class="dlg-option-top">
							<input
								type="radio"
								name="analysis-mode-dlg"
								checked={analysisMode === 'folder'}
								onchange={() => (analysisMode = 'folder')}
							/>
							<span class="dlg-option-name">Folder-Specific Analysis</span>
						</div>
						<p class="dlg-option-desc">
							Analyze a specific team or product folder for focused assessment. Ideal for team
							retrospectives and targeted improvements.
						</p>
						<ul class="dlg-feature-list">
							<li>Focused team maturity assessment</li>
							<li>Faster analysis for subset</li>
							<li>Track team-level improvements</li>
							<li>Drill down into specific areas</li>
						</ul>
						{#if analysisMode === 'folder'}
							<div class="dlg-folder-picker">
								<label class="form-label" for="folder-picker-select">Select folder to analyze</label
								>
								<select
									id="folder-picker-select"
									class="form-input"
									bind:value={folderForFolderAnalysis}
								>
									<option value={null}>Choose a folder...</option>
									{#each getFlattenedFolders(repoTreeData) as folder}
										<option value={folder}
											>{'— '.repeat(folder.depth)}{folder.name} ({countRepositoriesInFolder(folder)}
											repos)</option
										>
									{/each}
								</select>
								<label class="dlg-toggle-row compact">
									<input type="checkbox" bind:checked={includeSubfoldersInModal} />
									<span class="dlg-toggle-label">Include nested subfolders</span>
								</label>
							</div>
							<button
								class="btn btn-primary btn-full mt"
								disabled={!folderForFolderAnalysis}
								onclick={startFolderAnalysisFromModal}>Start Folder Analysis</button
							>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	/* ============================================
	   MATTE ENGINEERING DESIGN SYSTEM
	   ============================================ */
	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
		--nav-height: 64px;
	}

	.page.dark {
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
		--card-shadow: none;
	}

	.page.light {
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
		--card-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
	}

	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	.page {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
		overflow-x: hidden;
	}

	/* Architectural Grid Backdrop */
	.page::before {
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

	/* ── Navigation ── */
	.dashboard-header {
		position: sticky;
		top: 0;
		z-index: 100;
		height: var(--nav-height);
		background: rgba(0, 0, 0, 0.8);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
	}
	.page.light .dashboard-header {
		background: rgba(255, 255, 255, 0.8);
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

	/* ── Technical Bar ── */
	.technical-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 0 2rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		height: 40px;
		position: relative;
		z-index: 10;
	}

	.bc-node {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		text-decoration: none;
		transition: color 0.15s;
	}
	.bc-node:hover {
		color: var(--text-secondary);
	}
	.bc-node.active {
		color: var(--accent);
	}
	.bc-sep {
		color: var(--border-focus);
		font-size: 0.65rem;
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

	/* ── Layout ── */
	.page-layout {
		display: flex;
		max-width: 1440px;
		margin: 0 auto;
		padding: 0 2rem;
		gap: 2rem;
		position: relative;
		z-index: 10;
	}

	/* ── Sidebar ── */
	.sidebar {
		width: 240px;
		flex-shrink: 0;
		padding: 1.5rem 0;
		position: sticky;
		top: calc(var(--nav-height) + 40px);
		height: fit-content;
		max-height: calc(100vh - var(--nav-height) - 40px);
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.sidebar-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.section-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.5rem;
	}
	.stats-grid .stat-cell:last-child:nth-child(odd) {
		grid-column: 1 / -1;
	}

	.stat-cell {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.625rem 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}
	.stat-val {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
		color: var(--text-primary);
	}
	.stat-lbl {
		font-size: 0.6rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.sidebar-actions {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.save-indicator {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
		text-align: center;
		letter-spacing: 0.02em;
	}
	.save-indicator.success {
		color: var(--success);
		background: rgba(16, 185, 129, 0.06);
		border: 1px solid rgba(16, 185, 129, 0.1);
	}
	.save-indicator.error {
		color: var(--error);
		background: rgba(239, 68, 68, 0.06);
		border: 1px solid rgba(239, 68, 68, 0.1);
	}

	/* ── Main Content ── */
	.page-main {
		flex: 1;
		min-width: 0;
		padding: 1.5rem 0;
	}

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
	.error-text {
		color: var(--error);
		font-size: 0.875rem;
	}
	.empty-icon {
		width: 48px;
		height: 48px;
		color: var(--text-muted);
		margin-bottom: 0.5rem;
	}
	.center-state h3 {
		font-size: 1.125rem;
		font-weight: 700;
	}
	.empty-desc {
		color: var(--text-secondary);
		font-size: 0.875rem;
		max-width: 400px;
		line-height: 1.5;
	}
	.empty-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	/* ── Tree Grid ── */
	.tree-grid {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.tree-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1rem 1.25rem;
		transition: all 0.2s var(--ease-premium);
		box-shadow: var(--card-shadow);
	}
	.tree-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-1px);
	}

	.tree-card-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.expand-toggle {
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		padding: 0.2rem;
		display: flex;
		transition: color 0.15s;
	}
	.expand-toggle:hover {
		color: var(--text-primary);
	}
	.expand-toggle.sm {
		padding: 0.125rem;
	}

	.expand-chevron {
		width: 14px;
		height: 14px;
		transition: transform 0.2s var(--ease-premium);
	}
	.expand-chevron.open {
		transform: rotate(90deg);
	}

	.node-icon {
		width: 16px;
		height: 16px;
		flex-shrink: 0;
	}
	.node-icon.folder {
		color: var(--accent);
	}
	.node-icon.repo {
		color: var(--text-muted);
	}
	.node-icon.sm {
		width: 14px;
		height: 14px;
	}

	.node-name {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--text-primary);
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.node-meta {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		white-space: nowrap;
	}

	.node-actions {
		display: flex;
		gap: 0.25rem;
		margin-left: auto;
		flex-shrink: 0;
	}

	.icon-btn {
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		padding: 0.25rem;
		border-radius: 4px;
		display: flex;
		transition: all 0.15s;
		text-decoration: none;
	}
	.icon-btn:hover {
		color: var(--accent);
		background: var(--accent-soft);
	}
	.icon-btn.danger:hover {
		color: var(--error);
		background: rgba(239, 68, 68, 0.06);
	}
	.icon-btn svg {
		width: 14px;
		height: 14px;
	}
	.icon-btn.sm svg {
		width: 12px;
		height: 12px;
	}
	.icon-btn.sm {
		padding: 0.2rem;
	}

	.inline-edit {
		padding: 0.25rem 0.5rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border-focus);
		border-radius: 4px;
		color: var(--text-primary);
		font-size: 0.8125rem;
		font-weight: 600;
		flex: 1;
		min-width: 0;
		outline: none;
	}
	.inline-edit.sm {
		font-size: 0.75rem;
	}

	.tag {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}
	.tag.private {
		color: var(--text-muted);
		border: 1px solid var(--border);
	}

	/* Tree Children */
	.tree-children {
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
		max-height: 500px;
		overflow-y: auto;
		padding-right: 0.25rem;
	}
	.tree-children::-webkit-scrollbar {
		width: 4px;
	}
	.tree-children::-webkit-scrollbar-track {
		background: transparent;
	}
	.tree-children::-webkit-scrollbar-thumb {
		background: var(--border-focus);
		border-radius: 2px;
	}

	.tree-children.nested {
		margin-left: 1rem;
		border-top: none;
		margin-top: 0.5rem;
		padding-top: 0.5rem;
	}
	.tree-children.nested.deeper {
		margin-left: 1.25rem;
	}

	.nested-folder {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.625rem 0.75rem;
	}
	.nested-folder.deeper {
		margin-left: 0.5rem;
	}

	.tree-row {
		display: flex;
		align-items: center;
		gap: 0.375rem;
	}

	.repo-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.625rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 6px;
		transition: border-color 0.15s;
	}
	.repo-row:hover {
		border-color: var(--border-focus);
	}

	/* ── Buttons ── */
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
		text-decoration: none;
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
		color: var(--text-primary);
	}

	.btn-outline {
		background: transparent;
		border-color: var(--border);
		color: var(--text-secondary);
	}
	.btn-outline:hover:not(:disabled) {
		border-color: var(--border-focus);
		color: var(--text-primary);
		background: var(--bg-surface-alt);
		transform: none;
	}

	.btn-full {
		width: 100%;
	}
	.btn-sm {
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
	}

	/* ── Spinner ── */
	.spinner {
		width: 20px;
		height: 20px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ══════════════════════════════════════════════
	   MODAL SYSTEM (Matching Threat-Modeling Design)
	   ══════════════════════════════════════════════ */

	/* Backdrop */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 9999;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(6px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		animation: fadeIn 0.15s ease;
	}
	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	/* Container */
	.modal-container {
		background: var(--bg-surface, #f8fafc);
		border: 1px solid var(--border, rgba(0, 0, 0, 0.06));
		border-radius: 12px;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
		width: 100%;
		max-width: 480px;
		max-height: 90vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		animation: modalIn 0.2s var(--ease-premium);
	}
	.modal-container.modal-wide {
		max-width: 820px;
	}
	.modal-container.dark {
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
	}
	.modal-container.light {
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
	}
	@keyframes modalIn {
		from {
			opacity: 0;
			transform: translateY(-12px) scale(0.97);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	/* Header */
	.modal-header {
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.modal-title {
		font-size: 1.125rem;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0;
	}
	.modal-subtitle {
		font-size: 0.75rem;
		color: var(--text-muted);
		margin-top: 0.125rem;
	}

	/* Close Button */
	.modal-close {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-muted);
		padding: 0.375rem;
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.15s;
		display: flex;
	}
	.modal-close:hover {
		border-color: var(--error);
		color: var(--error);
		background: rgba(239, 68, 68, 0.06);
	}
	.modal-close svg {
		width: 16px;
		height: 16px;
	}

	/* Body */
	.modal-body {
		padding: 1.5rem;
		overflow-y: auto;
		flex: 1;
	}

	/* Footer */
	.modal-footer {
		padding: 1rem 1.5rem;
		border-top: 1px solid var(--border);
		display: flex;
		gap: 0.75rem;
		justify-content: flex-end;
	}

	/* ── Form Elements ── */
	.form-group {
		margin-bottom: 1.25rem;
	}
	.form-label {
		display: block;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-secondary);
		margin-bottom: 0.375rem;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}
	.form-input {
		width: 100%;
		padding: 0.625rem 0.875rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		color: var(--text-primary);
		font-size: 0.875rem;
		transition: border-color 0.15s;
		font-family: var(--font-sans);
	}
	.form-input:focus {
		outline: none;
		border-color: var(--accent);
	}
	.form-input::placeholder {
		color: var(--text-muted);
	}
	select.form-input {
		cursor: pointer;
	}

	/* ── Info Box ── */
	.info-box {
		display: flex;
		align-items: flex-start;
		gap: 0.625rem;
		padding: 0.75rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
	}
	.info-icon {
		width: 16px;
		height: 16px;
		color: var(--accent);
		flex-shrink: 0;
		margin-top: 1px;
	}
	.info-text {
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.5;
	}

	/* ── Button Spinner ── */
	.btn-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	/* ── Margin Top Utility ── */
	.mt {
		margin-top: 0.75rem;
	}

	/* ── Info Card (Analyze Folder) ── */
	.dlg-info-card {
		display: flex;
		flex-direction: column;
		gap: 1px;
		border-radius: 10px;
		overflow: hidden;
		margin-bottom: 1rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
	}
	.dlg-info-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		background: var(--bg-surface-alt);
	}
	.dlg-info-key {
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
	}
	.dlg-info-val {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--text-primary);
	}
	.dlg-info-val.highlight {
		color: var(--accent);
	}

	/* ── Toggle Row ── */
	.dlg-toggle-row {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.875rem 1rem;
		border-radius: 8px;
		cursor: pointer;
		margin-bottom: 1rem;
		transition: border-color 0.15s;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
	}
	.dlg-toggle-row:hover {
		border-color: var(--border-focus);
	}
	.dlg-toggle-row.compact {
		padding: 0.5rem 0;
		background: none !important;
		border: none !important;
		margin-bottom: 0;
	}
	.dlg-toggle-row input[type='checkbox'] {
		accent-color: var(--accent);
		width: 16px;
		height: 16px;
		margin-top: 2px;
		cursor: pointer;
		flex-shrink: 0;
	}
	.dlg-toggle-text {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}
	.dlg-toggle-label {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--text-primary);
	}
	.dlg-toggle-hint {
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	/* ── Progress ── */
	.dlg-progress {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		padding: 2rem;
		border-radius: 10px;
		text-align: center;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
	}
	.dlg-progress p {
		font-size: 0.8125rem;
		color: var(--text-secondary);
	}

	/* ── Two Column Layout ── */
	.dlg-columns {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}
	.dlg-col {
		border-radius: 10px;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
	}
	.dlg-col-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--border);
	}
	.dlg-col-title {
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-secondary);
	}
	.dlg-col-count {
		font-size: 0.65rem;
		font-weight: 700;
		padding: 0.125rem 0.5rem;
		border-radius: 10px;
		background: var(--accent-soft);
		color: var(--accent);
	}
	.dlg-col-list {
		flex: 1;
		padding: 0.5rem;
		max-height: 320px;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	/* ── List Items ── */
	.dlg-list-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.12s;
		text-align: left;
		width: 100%;
		border: 1px solid var(--border);
		background: var(--bg-surface);
		color: var(--text-secondary);
		font-family: inherit;
	}
	.dlg-list-item:hover {
		border-color: var(--border-focus);
		background: var(--bg-surface-alt);
	}
	.dlg-list-item.active {
		background: var(--accent-soft);
		border-color: var(--accent);
	}
	.dlg-item-top-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.dlg-item-name {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--text-primary);
	}
	.dlg-item-desc {
		font-size: 0.7rem;
		line-height: 1.4;
		margin: 0;
		color: var(--text-muted);
	}
	.dlg-item-tags {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-top: 0.125rem;
	}
	.dlg-tag {
		font-size: 0.65rem;
		display: flex;
		align-items: center;
		gap: 0.2rem;
		color: var(--text-muted);
	}
	.dlg-tag.dim {
		opacity: 0.7;
	}
	.dlg-lang-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--accent);
	}
	.dlg-check {
		flex-shrink: 0;
		color: var(--accent);
	}

	/* ── Folder Icon ── */
	.dlg-folder-icon {
		flex-shrink: 0;
		color: var(--accent);
	}

	/* ── Empty State ── */
	.dlg-empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 2rem 1rem;
		text-align: center;
		font-size: 0.8125rem;
		color: var(--text-muted);
	}
	.dlg-link {
		background: none;
		border: none;
		color: var(--accent);
		cursor: pointer;
		font-size: 0.8125rem;
		text-decoration: underline;
		font-family: inherit;
	}

	/* ── Confirm Bar ── */
	.dlg-confirm-bar {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 0.75rem;
		margin: 0.5rem;
		border-radius: 6px;
		font-size: 0.75rem;
		background: rgba(16, 185, 129, 0.06);
		border: 1px solid rgba(16, 185, 129, 0.12);
		color: var(--text-secondary);
	}
	.dlg-confirm-bar strong {
		color: var(--text-primary);
	}
	.dlg-confirm-bar svg {
		color: var(--success);
	}

	/* ══════════════════════════════════════════════
	   Analysis Options Cards
	   ══════════════════════════════════════════════ */
	.dlg-option-grid {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.dlg-option-card {
		padding: 1.25rem;
		border-radius: 10px;
		cursor: pointer;
		transition: all 0.15s;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
	}
	.dlg-option-card:hover {
		border-color: var(--border-focus);
	}
	.dlg-option-card.active {
		border-color: var(--accent);
		background: var(--accent-soft);
	}
	.dlg-option-top {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}
	.dlg-option-top input[type='radio'] {
		width: 16px;
		height: 16px;
		accent-color: var(--accent);
		cursor: pointer;
	}
	.dlg-option-name {
		font-size: 0.875rem;
		font-weight: 700;
		color: var(--text-primary);
	}
	.dlg-badge {
		font-size: 0.6rem;
		font-weight: 700;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-family: var(--font-mono, monospace);
	}
	.dlg-badge.green {
		background: rgba(16, 185, 129, 0.12);
		color: #10b981;
	}
	.dlg-option-desc {
		font-size: 0.8125rem;
		line-height: 1.5;
		margin-bottom: 0.75rem;
		color: var(--text-secondary);
	}
	.dlg-feature-list {
		list-style: none;
		padding: 0;
		margin: 0 0 0.75rem 0;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.dlg-feature-list li {
		font-size: 0.75rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--text-secondary);
	}
	.dlg-feature-list li::before {
		content: '';
		width: 5px;
		height: 5px;
		background: var(--success);
		border-radius: 50%;
		flex-shrink: 0;
	}
	.dlg-option-stats {
		display: flex;
		gap: 1rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--border);
	}
	.dlg-option-stats span {
		font-family: var(--font-mono, monospace);
		font-size: 0.65rem;
		color: var(--text-muted);
	}

	/* ── Folder Picker ── */
	.dlg-folder-picker {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--border);
	}

	/* ── Notifications ── */
	:global(.notification) {
		position: fixed;
		top: 80px;
		right: 2rem;
		z-index: 99999;
		padding: 0.75rem 1.25rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		animation: dlgSlideIn 0.2s ease;
	}
	:global(.dark) :global(.notification) {
		background: #111111;
		border: 1px solid rgba(255, 255, 255, 0.06);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
		color: #f1f5f9;
	}
	:global(.light) :global(.notification) {
		background: #ffffff;
		border: 1px solid rgba(0, 0, 0, 0.08);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
		color: #1e293b;
	}
	:global(.notification.success) {
		border-color: rgba(16, 185, 129, 0.25);
	}
	:global(.notification.error) {
		border-color: rgba(239, 68, 68, 0.25);
	}
	:global(.notification.fade-out) {
		animation: dlgFadeOut 0.3s ease forwards;
	}
	@keyframes dlgSlideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}
	@keyframes dlgFadeOut {
		to {
			opacity: 0;
			transform: translateY(-8px);
		}
	}

	/* ── Responsive ── */
	@media (max-width: 1024px) {
		.page-layout {
			flex-direction: column;
		}
		.sidebar {
			width: 100%;
			position: relative;
			top: 0;
			max-height: none;
		}
		.stats-grid {
			grid-template-columns: repeat(5, 1fr);
		}
		.stats-grid .stat-cell:last-child:nth-child(odd) {
			grid-column: auto;
		}
	}
	@media (max-width: 768px) {
		.nav-menu {
			display: none;
		}
		.header-content {
			padding: 0 1rem;
		}
		.page-layout {
			padding: 0 1rem;
		}
		.dlg-columns {
			grid-template-columns: 1fr;
		}
		.stats-grid {
			grid-template-columns: repeat(3, 1fr);
		}
		.modal-container {
			max-width: 100%;
		}
	}
</style>
