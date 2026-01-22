<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { githubClient } from '$lib/github.js';
	import { repositoryTreeClient } from '$lib/repositoryTree.js';
	import { isDarkMode } from '$lib/stores.js';

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

			const response = await fetch(
				'http://localhost:8000/api/workspace-intelligence/analyze-folder',
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
						folder_id: folderToAnalyze.id,
						folder_path: folderPath,
						include_subfolders: includeSubfolders
					})
				}
			);

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
				'http://localhost:8000/api/workspace-intelligence/analyze-workspace-unified',
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
				`http://localhost:8000/api/workspace-intelligence/analysis/${orgName}`,
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
				`http://localhost:8000/api/workspace-intelligence/analysis/${orgName}`,
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

<div class="treeview-container {darkMode ? 'dark' : 'light'}">
	<!-- Top Navigation Bar -->
	<nav class="top-navbar">
		<div class="navbar-content">
			<!-- Left: Brand & Breadcrumb -->
			<div class="navbar-left">
				<div class="brand-section">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<div class="brand-text">
						<span class="brand-name">WithOps</span>
						<span class="brand-subtitle">Repository Treeview</span>
					</div>
				</div>

				<!-- Breadcrumb -->
				<nav class="breadcrumb">
					<a href="/dashboard" class="breadcrumb-link">Dashboard</a>
					<span class="breadcrumb-separator">/</span>
					<a href="/organizations" class="breadcrumb-link">Organizations</a>
					<span class="breadcrumb-separator">/</span>
					<a href="/github/workspace/{orgName}" class="breadcrumb-link">{orgName}</a>
					<span class="breadcrumb-separator">/</span>
					<span class="breadcrumb-current">Treeview</span>
				</nav>
			</div>
		</div>
	</nav>

	<!-- Main Layout: Sidebar + Content -->
	<div class="main-layout">
		<!-- Left Sidebar -->
		<aside class="left-sidebar">
			<!-- Back to Workspace Button -->
			<button onclick={() => goto(`/github/workspace/${orgName}`)} class="back-button">
				<svg class="back-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M10 19l-7-7m0 0l7-7m-7 7h18"
					/>
				</svg>
				Back to Workspace
			</button>

			<!-- Statistics Section -->
			<div class="sidebar-section">
				<h3 class="section-title">STATISTICS</h3>

				<div class="stat-cards">
					<!-- Folders -->
					<div class="stat-card folders">
						<div class="stat-icon">📁</div>
						<div class="stat-content">
							<div class="stat-value">{statistics.totalFolders}</div>
							<div class="stat-label">Folders</div>
						</div>
					</div>

					<!-- Repositories -->
					<div class="stat-card repos">
						<div class="stat-icon">📦</div>
						<div class="stat-content">
							<div class="stat-value">{statistics.totalRepos}</div>
							<div class="stat-label">Repositories</div>
						</div>
					</div>

					<!-- Workflows -->
					<div class="stat-card workflows">
						<div class="stat-icon">⚙️</div>
						<div class="stat-content">
							<div class="stat-value">{statistics.totalWorkflows}</div>
							<div class="stat-label">Workflows</div>
						</div>
					</div>

					<!-- Private -->
					<div class="stat-card private">
						<div class="stat-icon">🔒</div>
						<div class="stat-content">
							<div class="stat-value">{statistics.privateRepos}</div>
							<div class="stat-label">Private</div>
						</div>
					</div>

					<!-- Public -->
					<div class="stat-card public">
						<div class="stat-icon">🌐</div>
						<div class="stat-content">
							<div class="stat-value">{statistics.publicRepos}</div>
							<div class="stat-label">Public</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Action Buttons -->
			<div class="sidebar-actions">
				<button onclick={checkAndNavigateToIntelligence} class="action-button intelligence">
					<div class="button-content">
						<svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
							/>
						</svg>
						<div class="button-text">
							<span class="button-label">Workspace Intelligence</span>
							<span class="button-desc">AI-powered insights</span>
						</div>
					</div>
				</button>

				{#if hasPastAnalysis}
					<button onclick={navigateToDashboard} class="action-button dashboard">
						<div class="button-content">
							<svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
								/>
							</svg>
							<div class="button-text">
								<span class="button-label">Intelligence Dashboard</span>
								<span class="button-desc">View past analysis</span>
							</div>
						</div>
					</button>
				{/if}

				<button onclick={openNewFolderModal} class="action-button new-folder">
					<div class="button-content">
						<svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
							/>
						</svg>
						<div class="button-text">
							<span class="button-label">New Folder</span>
							<span class="button-desc">Organize repositories</span>
						</div>
					</div>
				</button>

				<button onclick={openAddRepoModal} class="action-button add-repo">
					<div class="button-content">
						<svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<div class="button-text">
							<span class="button-label">Add Repository</span>
							<span class="button-desc">Import from GitHub</span>
						</div>
					</div>
				</button>
			</div>

			<!-- Save Status -->
			{#if saveStatus}
				<div class="save-status {saveSuccess ? 'success' : 'error'}">
					{saveStatus}
				</div>
			{/if}
		</aside>

		<!-- Main Content Area -->
		<main class="main-content">
			<!-- SVG Background -->
			<div class="svg-background"></div>

			<!-- Content Overlay -->
			<div class="content-overlay">
				{#if loading}
					<div class="loading-state">
						<div class="loading-spinner"></div>
						<span class="loading-text">Loading repository tree...</span>
					</div>
				{:else if error}
					<div class="error-state">
						<svg class="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<p class="error-message">{error}</p>
					</div>
				{:else if repoTreeData.length === 0}
					<div class="empty-state">
						<div class="empty-icon">
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
						</div>
						<h3 class="empty-title">No repositories organized yet</h3>
						<p class="empty-description">
							Start by creating a folder and adding repositories from your organization
						</p>
						<div class="empty-actions">
							<button onclick={openNewFolderModal} class="empty-button primary">
								Create First Folder
							</button>
							<button onclick={openAddRepoModal} class="empty-button secondary">
								Add Repository
							</button>
						</div>
					</div>
				{:else}
					<!-- Folder Cards Grid -->
					<div class="folders-grid">
						{#each repoTreeData as node}
							{#if node.type === 'folder'}
								<div class="folder-card">
									<div class="folder-header">
										<button
											onclick={(e) => toggleNode(e, node)}
											class="expand-button"
											aria-label={expandedNodes.has(node.id) ? 'Collapse folder' : 'Expand folder'}
										>
											{#if expandedNodes.has(node.id)}
												<svg
													class="expand-icon"
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
											{:else}
												<svg
													class="expand-icon"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M9 5l7 7-7 7"
													/>
												</svg>
											{/if}
										</button>

										<svg class="folder-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

										{#if editingNode?.id === node.id}
											<input
												bind:value={editingValue}
												onblur={saveEdit}
												onkeydown={(e) => e.key === 'Enter' && saveEdit()}
												class="folder-name-input"
											/>
										{:else}
											<h3 class="folder-name">{node.name}</h3>
										{/if}

										<span class="item-count">({countItemsInNode(node)} items)</span>

										<div class="folder-actions">
											<button
												onclick={() => openAnalyzeFolderModal(node)}
												class="action-icon analyze"
												title="Analyze Folder"
												aria-label="Analyze folder maturity"
											>
												<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
													/>
												</svg>
											</button>
											<button
												onclick={() => startEditing(node)}
												class="action-icon"
												title="Rename"
												aria-label="Rename folder"
											>
												<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
													/>
												</svg>
											</button>
											<button
												onclick={() => openNewFolderModal(node)}
												class="action-icon"
												title="Add subfolder"
												aria-label="Add subfolder"
											>
												<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M12 4v16m8-8H4"
													/>
												</svg>
											</button>
											<button
												onclick={() => deleteNode(node)}
												class="action-icon delete"
												title="Delete"
												aria-label="Delete folder"
											>
												<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
													/>
												</svg>
											</button>
										</div>
									</div>

									{#if expandedNodes.has(node.id) && node.children}
										<div class="folder-children">
											{#each node.children as child}
												{#if child.type === 'folder'}
													<!-- Nested Folder -->
													<div class="nested-folder-item">
														<div class="nested-folder-header">
															<button
																onclick={(e) => toggleNode(e, child)}
																class="expand-button small"
																aria-label={expandedNodes.has(child.id)
																	? 'Collapse folder'
																	: 'Expand folder'}
															>
																{#if expandedNodes.has(child.id)}
																	<svg
																		class="expand-icon"
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
																{:else}
																	<svg
																		class="expand-icon"
																		fill="none"
																		stroke="currentColor"
																		viewBox="0 0 24 24"
																	>
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			stroke-width="2"
																			d="M9 5l7 7-7 7"
																		/>
																	</svg>
																{/if}
															</button>

															<svg
																class="folder-icon small"
																fill="none"
																stroke="currentColor"
																viewBox="0 0 24 24"
															>
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

															{#if editingNode?.id === child.id}
																<input
																	bind:value={editingValue}
																	onblur={saveEdit}
																	onkeydown={(e) => e.key === 'Enter' && saveEdit()}
																	class="folder-name-input small"
																/>
															{:else}
																<span class="nested-folder-name">{child.name}</span>
															{/if}

															<span class="item-count small">({countItemsInNode(child)} items)</span
															>

															<div class="folder-actions">
																<button
																	onclick={() => openAnalyzeFolderModal(child)}
																	class="action-icon analyze small"
																	title="Analyze Folder"
																	aria-label="Analyze folder maturity"
																>
																	<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			stroke-width="2"
																			d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
																		/>
																	</svg>
																</button>
																<button
																	onclick={() => startEditing(child)}
																	class="action-icon small"
																	title="Rename"
																	aria-label="Rename folder"
																>
																	<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			stroke-width="2"
																			d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
																		/>
																	</svg>
																</button>
																<button
																	onclick={() => openNewFolderModal(child)}
																	class="action-icon small"
																	title="Add subfolder"
																	aria-label="Add subfolder"
																>
																	<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			stroke-width="2"
																			d="M12 4v16m8-8H4"
																		/>
																	</svg>
																</button>
																<button
																	onclick={() => deleteNode(child)}
																	class="action-icon delete small"
																	title="Delete"
																	aria-label="Delete folder"
																>
																	<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			stroke-width="2"
																			d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
																		/>
																	</svg>
																</button>
															</div>
														</div>

														<!-- Nested folder's children (recursive display) -->
														{#if expandedNodes.has(child.id) && child.children}
															<div class="nested-folder-children">
																{#each child.children as nestedChild}
																	{#if nestedChild.type === 'folder'}
																		<!-- Further nested folders can be added here - you may want to create a recursive component for deeper nesting -->
																		<div class="nested-folder-item deeper">
																			<div class="nested-folder-header">
																				<button
																					onclick={(e) => toggleNode(e, nestedChild)}
																					class="expand-button small"
																				>
																					{#if expandedNodes.has(nestedChild.id)}
																						<svg
																							class="expand-icon"
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
																					{:else}
																						<svg
																							class="expand-icon"
																							fill="none"
																							stroke="currentColor"
																							viewBox="0 0 24 24"
																						>
																							<path
																								stroke-linecap="round"
																								stroke-linejoin="round"
																								stroke-width="2"
																								d="M9 5l7 7-7 7"
																							/>
																						</svg>
																					{/if}
																				</button>
																				<svg
																					class="folder-icon small"
																					fill="none"
																					stroke="currentColor"
																					viewBox="0 0 24 24"
																				>
																					<path
																						stroke-linecap="round"
																						stroke-linejoin="round"
																						stroke-width="2"
																						d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
																					/>
																				</svg>
																				<span class="nested-folder-name">{nestedChild.name}</span>
																				<span class="item-count small"
																					>({countItemsInNode(nestedChild)} items)</span
																				>
																				<div class="folder-actions">
																					<button
																						onclick={() => openAnalyzeFolderModal(nestedChild)}
																						class="action-icon analyze small"
																						title="Analyze"
																						aria-label="Analyze folder maturity"
																					>
																						<svg
																							fill="none"
																							stroke="currentColor"
																							viewBox="0 0 24 24"
																						>
																							<path
																								stroke-linecap="round"
																								stroke-linejoin="round"
																								stroke-width="2"
																								d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
																							/>
																						</svg>
																					</button>
																					<button
																						onclick={() => startEditing(nestedChild)}
																						class="action-icon small"
																						title="Rename"
																						aria-label="Rename folder"
																					>
																						<svg
																							fill="none"
																							stroke="currentColor"
																							viewBox="0 0 24 24"
																						>
																							<path
																								stroke-linecap="round"
																								stroke-linejoin="round"
																								stroke-width="2"
																								d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
																							/>
																						</svg>
																					</button>
																					<button
																						onclick={() => openNewFolderModal(nestedChild)}
																						class="action-icon small"
																						title="Add subfolder"
																						aria-label="Add subfolder"
																					>
																						<svg
																							fill="none"
																							stroke="currentColor"
																							viewBox="0 0 24 24"
																						>
																							<path
																								stroke-linecap="round"
																								stroke-linejoin="round"
																								stroke-width="2"
																								d="M12 4v16m8-8H4"
																							/>
																						</svg>
																					</button>
																					<button
																						onclick={() => deleteNode(nestedChild)}
																						class="action-icon delete small"
																						title="Delete"
																						aria-label="Delete folder"
																					>
																						<svg
																							fill="none"
																							stroke="currentColor"
																							viewBox="0 0 24 24"
																						>
																							<path
																								stroke-linecap="round"
																								stroke-linejoin="round"
																								stroke-width="2"
																								d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
																							/>
																						</svg>
																					</button>
																				</div>
																			</div>

																			{#if expandedNodes.has(nestedChild.id) && nestedChild.children}
																				<div class="nested-folder-children deeper">
																					{#each nestedChild.children as deepChild}
																						{#if deepChild.type === 'repository'}
																							<div class="repo-item">
																								<svg
																									class="repo-icon"
																									fill="none"
																									stroke="currentColor"
																									viewBox="0 0 24 24"
																								>
																									<path
																										stroke-linecap="round"
																										stroke-linejoin="round"
																										stroke-width="2"
																										d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
																									/>
																								</svg>
																								<span class="repo-name">{deepChild.name}</span>
																								{#if deepChild.metadata?.private}
																									<span class="repo-badge private">Private</span>
																								{/if}
																								{#if deepChild.children}
																									<span class="workflow-count"
																										>({deepChild.children.length} workflows)</span
																									>
																								{/if}
																								<div class="repo-actions">
																									{#if deepChild.metadata?.html_url}
																										<a
																											href={deepChild.metadata.html_url}
																											target="_blank"
																											class="action-icon"
																											title="Open in GitHub"
																											aria-label="Open repository in GitHub"
																										>
																											<svg
																												fill="none"
																												stroke="currentColor"
																												viewBox="0 0 24 24"
																											>
																												<path
																													stroke-linecap="round"
																													stroke-linejoin="round"
																													stroke-width="2"
																													d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
																												/>
																											</svg>
																										</a>
																									{/if}
																									<button
																										onclick={() => deleteNode(deepChild)}
																										class="action-icon delete"
																										title="Remove"
																										aria-label="Remove repository from folder"
																									>
																										<svg
																											fill="none"
																											stroke="currentColor"
																											viewBox="0 0 24 24"
																										>
																											<path
																												stroke-linecap="round"
																												stroke-linejoin="round"
																												stroke-width="2"
																												d="M6 18L18 6M6 6l12 12"
																											/>
																										</svg>
																									</button>
																								</div>
																							</div>
																						{/if}
																					{/each}
																				</div>
																			{/if}
																		</div>
																	{:else if nestedChild.type === 'repository'}
																		<div class="repo-item">
																			<svg
																				class="repo-icon"
																				fill="none"
																				stroke="currentColor"
																				viewBox="0 0 24 24"
																			>
																				<path
																					stroke-linecap="round"
																					stroke-linejoin="round"
																					stroke-width="2"
																					d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
																				/>
																			</svg>
																			<span class="repo-name">{nestedChild.name}</span>
																			{#if nestedChild.metadata?.private}
																				<span class="repo-badge private">Private</span>
																			{/if}
																			{#if nestedChild.children}
																				<span class="workflow-count"
																					>({nestedChild.children.length} workflows)</span
																				>
																			{/if}

																			<div class="repo-actions">
																				{#if nestedChild.metadata?.html_url}
																					<a
																						href={nestedChild.metadata.html_url}
																						target="_blank"
																						class="action-icon"
																						title="Open in GitHub"
																						aria-label="Open repository in GitHub"
																					>
																						<svg
																							fill="none"
																							stroke="currentColor"
																							viewBox="0 0 24 24"
																						>
																							<path
																								stroke-linecap="round"
																								stroke-linejoin="round"
																								stroke-width="2"
																								d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
																							/>
																						</svg>
																					</a>
																				{/if}
																				<button
																					onclick={() => deleteNode(nestedChild)}
																					class="action-icon delete"
																					title="Remove"
																					aria-label="Remove repository from folder"
																				>
																					<svg
																						fill="none"
																						stroke="currentColor"
																						viewBox="0 0 24 24"
																					>
																						<path
																							stroke-linecap="round"
																							stroke-linejoin="round"
																							stroke-width="2"
																							d="M6 18L18 6M6 6l12 12"
																						/>
																					</svg>
																				</button>
																			</div>
																		</div>
																	{/if}
																{/each}
															</div>
														{/if}
													</div>
												{:else if child.type === 'repository'}
													<div class="repo-item">
														<svg
															class="repo-icon"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
															/>
														</svg>
														<span class="repo-name">{child.name}</span>
														{#if child.metadata?.private}
															<span class="repo-badge private">Private</span>
														{/if}
														{#if child.children}
															<span class="workflow-count">({child.children.length} workflows)</span
															>
														{/if}

														<div class="repo-actions">
															{#if child.metadata?.html_url}
																<a
																	href={child.metadata.html_url}
																	target="_blank"
																	class="action-icon"
																	title="Open in GitHub"
																	aria-label="Open repository in GitHub"
																>
																	<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			stroke-width="2"
																			d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
																		/>
																	</svg>
																</a>
															{/if}
															<button
																onclick={() => deleteNode(child)}
																class="action-icon delete"
																title="Remove"
																aria-label="Remove repository from folder"
															>
																<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
																	<path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		stroke-width="2"
																		d="M6 18L18 6M6 6l12 12"
																	/>
																</svg>
															</button>
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
			</div>
		</main>
	</div>
</div>

<!-- New Folder Modal -->
{#if showNewFolderModal}
	<div
		class="modal-backdrop"
		onclick={closeNewFolderModal}
		onkeydown={(e) => e.key === 'Escape' && closeNewFolderModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			tabindex="-1"
		>
			<div class="modal-header">
				<h3 class="modal-title">Create New Folder</h3>
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
					<label for="folder-name" class="form-label">Folder Name</label>
					<input
						id="folder-name"
						bind:value={newFolderName}
						placeholder="Enter folder name..."
						class="form-input"
						onkeypress={(e) => e.key === 'Enter' && createNewFolder()}
					/>
				</div>

				{#if newFolderParent}
					<div class="info-box">
						<svg class="info-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<p class="info-text">
							Creating subfolder in: <span class="highlight">{newFolderParent.name}</span>
						</p>
					</div>
				{/if}
			</div>

			<div class="modal-footer">
				<button onclick={closeNewFolderModal} class="btn-secondary"> Cancel </button>
				<button onclick={createNewFolder} disabled={!newFolderName.trim()} class="btn-primary">
					<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 4v16m8-8H4"
						/>
					</svg>
					Create Folder
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Add Repository Modal -->
{#if showAddRepoModal}
	<div
		class="modal-backdrop"
		onclick={closeAddRepoModal}
		onkeydown={(e) => e.key === 'Escape' && closeAddRepoModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container large"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title">Add Repository to Tree</h3>
					<p class="modal-subtitle">Select a repository and a folder to organize it</p>
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
				<div class="selection-grid">
					<!-- Available Repositories -->
					<div class="selection-panel">
						<h4 class="panel-title">
							<span class="panel-icon">📦</span>
							Available Repositories
						</h4>

						{#if loadingRepos}
							<div class="panel-loading">
								<div class="loading-spinner small"></div>
								<span>Loading repositories...</span>
							</div>
						{:else if availableRepos.length === 0}
							<p class="panel-empty">No repositories available</p>
						{:else}
							<div class="selection-list">
								{#each availableRepos as repo}
									<button
										onclick={() => (selectedRepoToAdd = repo)}
										class="selection-item {selectedRepoToAdd?.name === repo.name ? 'selected' : ''}"
									>
										<div class="item-content">
											<div class="item-header">
												<span class="item-name">{repo.name}</span>
												{#if selectedRepoToAdd?.name === repo.name}
													<svg
														class="check-icon"
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
												{/if}
											</div>
											{#if repo.description}
												<p class="item-description">{repo.description}</p>
											{/if}
											<div class="item-meta">
												{#if repo.language}
													<span class="meta-item">
														<span class="language-dot"></span>
														{repo.language}
													</span>
												{/if}
												<span class="meta-item">{repo.workflow_count || 0} workflows</span>
												{#if repo.private}
													<span class="meta-badge">Private</span>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							</div>
						{/if}
					</div>

					<!-- Folder Selection -->
					<div class="selection-panel">
						<h4 class="panel-title">
							<span class="panel-icon">📁</span>
							Select Folder
						</h4>

						{#if repoTreeData.length === 0}
							<div class="panel-empty-state">
								<p>No folders created yet</p>
								<button
									onclick={() => {
										closeAddRepoModal();
										openNewFolderModal();
									}}
									class="link-button"
								>
									Create your first folder
								</button>
							</div>
						{:else}
							<div class="selection-list">
								{#each getFlattenedFolders(repoTreeData) as folder}
									<button
										onclick={() => (selectedNode = folder)}
										class="selection-item {selectedNode?.id === folder.id ? 'selected' : ''}"
										style="padding-left: {0.75 + folder.depth * 1}rem"
									>
										<svg
											class="folder-icon-small"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
											/>
										</svg>
										<span class="item-name">{folder.name}</span>
										{#if selectedNode?.id === folder.id}
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
							</div>
						{/if}

						{#if selectedRepoToAdd && selectedNode}
							<div class="selection-summary">
								<svg class="summary-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
									/>
								</svg>
								<p class="summary-text">
									<span class="highlight">{selectedRepoToAdd.name}</span> will be added to
									<span class="highlight">{selectedNode.name}</span>
								</p>
							</div>
						{/if}
					</div>
				</div>
			</div>

			<div class="modal-footer">
				<button onclick={closeAddRepoModal} class="btn-secondary"> Cancel </button>
				<button
					onclick={addRepositoryToTree}
					disabled={!selectedRepoToAdd || !selectedNode || addingRepo}
					class="btn-primary"
				>
					{#if addingRepo}
						<div class="loading-spinner small"></div>
						<span>Adding...</span>
					{:else}
						<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6v6m0 0v6m0-6h6m-6 0H6"
							/>
						</svg>
						<span>Add Repository</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Analyze Folder Modal -->
{#if showAnalyzeFolderModal}
	<div class="modal-overlay">
		<div class="modal">
			<div class="modal-header">
				<h3>Analyze Folder</h3>
				<button class="close-btn" onclick={closeAnalyzeFolderModal} aria-label="Close modal">
					<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
					<div class="folder-info">
						<div class="info-row">
							<svg class="folder-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
								/>
							</svg>
							<div class="info-text">
								<span class="label">Folder Name:</span>
								<span class="value">{folderToAnalyze.name}</span>
							</div>
						</div>

						<div class="info-row">
							<svg class="path-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
								/>
							</svg>
							<div class="info-text">
								<span class="label">Path:</span>
								<span class="value">{getFolderPath(folderToAnalyze)}</span>
							</div>
						</div>

						<div class="info-row">
							<svg class="repo-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"
								/>
							</svg>
							<div class="info-text">
								<span class="label">Repositories:</span>
								<span class="value badge">{countRepositoriesInFolder(folderToAnalyze)}</span>
							</div>
						</div>
					</div>

					<div class="options">
						<label class="checkbox-label">
							<input type="checkbox" bind:checked={includeSubfolders} disabled={analyzingFolder} />
							<span>Include all subfolders and their repositories</span>
						</label>
					</div>

					{#if analyzingFolder}
						<div class="progress-section">
							<div class="loading-spinner"></div>
							<p class="progress-text">{analysisProgress}</p>
						</div>
					{/if}

					{#if !analyzingFolder}
						<div class="info-notice">
							<svg class="notice-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							<span
								>This will analyze {includeSubfolders
									? 'this folder and all subfolders'
									: 'only repositories directly in this folder'} using the OWASP DSOMM framework.</span
							>
						</div>
					{/if}
				{/if}
			</div>

			<div class="modal-footer">
				<button onclick={closeAnalyzeFolderModal} disabled={analyzingFolder} class="btn-secondary">
					Cancel
				</button>
				<button
					onclick={() => triggerFolderAnalysis()}
					disabled={analyzingFolder}
					class="btn-primary"
				>
					{#if analyzingFolder}
						<div class="loading-spinner small"></div>
						<span>Analyzing...</span>
					{:else}
						<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
							/>
						</svg>
						<span>Start Analysis</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Analysis Options Modal -->
{#if showAnalysisOptionsModal}
	<div
		class="modal-backdrop"
		onclick={closeAnalysisOptionsModal}
		onkeydown={(e) => e.key === 'Escape' && closeAnalysisOptionsModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container analysis-options-modal"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			tabindex="-1"
		>
			<div class="modal-header">
				<h3 class="modal-title">Choose Analysis Approach</h3>
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

			<div class="modal-body analysis-options-body">
				<!-- Option 1: Unified Workspace Analysis -->
				<div
					class="analysis-option {analysisMode === 'unified' ? 'selected' : ''}"
					onclick={() => (analysisMode = 'unified')}
					onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (analysisMode = 'unified')}
					role="button"
					tabindex="0"
				>
					<div class="option-header">
						<input type="radio" name="analysis-mode" checked={analysisMode === 'unified'} />
						<div class="option-title-wrapper">
							<span class="option-name">Unified Workspace Analysis</span>
							<span class="recommended-badge">Recommended</span>
						</div>
					</div>

					<p class="option-description">
						Analyze all folders and repositories in one comprehensive assessment. Perfect for
						executive dashboards and organization-wide visibility.
					</p>

					<ul class="option-benefits">
						<li>✓ Organization-wide maturity score</li>
						<li>✓ Complete security posture assessment</li>
						<li>✓ Cross-team comparison built-in</li>
						<li>✓ Executive-ready dashboards</li>
					</ul>

					<div class="option-stats">
						<span class="stat">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2"
								/>
							</svg>
							{statistics.totalRepos} repos
						</span>
						<span class="stat">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
								/>
							</svg>
							{statistics.totalFolders} folders
						</span>
						<span class="stat">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							~{Math.ceil(statistics.totalRepos / 20)} min
						</span>
					</div>
				</div>

				<!-- Option 2: Folder-Specific Analysis -->
				<div
					class="analysis-option {analysisMode === 'folder' ? 'selected' : ''}"
					onclick={() => (analysisMode = 'folder')}
					onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (analysisMode = 'folder')}
					role="button"
					tabindex="0"
				>
					<div class="option-header">
						<input type="radio" name="analysis-mode" checked={analysisMode === 'folder'} />
						<div class="option-title-wrapper">
							<span class="option-name">Folder-Specific Analysis</span>
						</div>
					</div>

					<p class="option-description">
						Analyze a specific team or product folder for focused assessment. Ideal for team
						retrospectives and targeted improvements.
					</p>

					<ul class="option-benefits">
						<li>✓ Focused team maturity assessment</li>
						<li>✓ Faster analysis for subset</li>
						<li>✓ Track team-level improvements</li>
						<li>✓ Drill down into specific areas</li>
					</ul>

					{#if analysisMode === 'folder'}
						<div class="folder-selector">
							<label for="folder-analysis-select">Select folder to analyze:</label>
							<select
								id="folder-analysis-select"
								bind:value={folderForFolderAnalysis}
								class="folder-dropdown"
							>
								<option value={null}>Choose a folder...</option>
								{#each repoTreeData as folder}
									{#if folder.type === 'folder'}
										<option value={folder}
											>{folder.name} ({countRepositoriesInFolder(folder)} repos)</option
										>
									{/if}
								{/each}
							</select>

							<label class="checkbox-label">
								<input type="checkbox" bind:checked={includeSubfoldersInModal} />
								Include nested subfolders
							</label>
						</div>
					{/if}
				</div>
			</div>

			<div class="modal-footer">
				<button onclick={closeAnalysisOptionsModal} class="btn-secondary"> Cancel </button>
				{#if analysisMode === 'unified'}
					<button onclick={startUnifiedAnalysis} class="btn-primary">
						<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
							/>
						</svg>
						<span>Start Unified Analysis</span>
					</button>
				{:else}
					<button
						onclick={startFolderAnalysisFromModal}
						disabled={!folderForFolderAnalysis}
						class="btn-primary"
					>
						<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
							/>
						</svg>
						<span>Start Folder Analysis</span>
					</button>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Analysis Options Modal -->
{#if showAnalysisOptionsModal}
	<div
		class="modal-backdrop"
		onclick={closeAnalysisOptionsModal}
		onkeydown={(e) => e.key === 'Escape' && closeAnalysisOptionsModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container analysis-options-modal"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			tabindex="-1"
		>
			<div class="modal-header">
				<h3 class="modal-title">Choose Analysis Approach</h3>
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

			<div class="modal-body analysis-options-body">
				<!-- Option 1: Unified Workspace Analysis -->
				<div
					class="analysis-option {analysisMode === 'unified' ? 'selected' : ''}"
					onclick={() => (analysisMode = 'unified')}
					onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (analysisMode = 'unified')}
					role="button"
					tabindex="0"
				>
					<div class="option-header">
						<input
							type="radio"
							name="analysis-mode"
							checked={analysisMode === 'unified'}
							onchange={() => (analysisMode = 'unified')}
						/>
						<div class="option-title-wrapper">
							<span class="option-name">Unified Workspace Analysis</span>
							<span class="recommended-badge">Recommended</span>
						</div>
					</div>

					<p class="option-description">
						Analyze all folders and repositories in one comprehensive assessment. Perfect for
						executive dashboards and organization-wide visibility.
					</p>

					<ul class="option-benefits">
						<li>Organization-wide maturity score</li>
						<li>Complete security posture assessment</li>
						<li>Cross-team comparison built-in</li>
						<li>Executive-ready dashboards</li>
					</ul>

					<div class="option-stats">
						<span class="stat">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
								/>
							</svg>
							{statistics.totalRepos} repos
						</span>
						<span class="stat">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
								/>
							</svg>
							{statistics.totalFolders} folders
						</span>
						<span class="stat">
							<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							~{Math.ceil(statistics.totalRepos / 20)} min
						</span>
					</div>

					{#if analysisMode === 'unified'}
						<button
							class="btn-primary"
							onclick={startUnifiedAnalysis}
							style="margin-top: 1rem; width: 100%;"
						>
							<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
								/>
							</svg>
							<span>Start Unified Analysis</span>
						</button>
					{/if}
				</div>

				<!-- Option 2: Folder-Specific Analysis -->
				<div
					class="analysis-option {analysisMode === 'folder' ? 'selected' : ''}"
					onclick={() => (analysisMode = 'folder')}
					onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (analysisMode = 'folder')}
					role="button"
					tabindex="0"
				>
					<div class="option-header">
						<input
							type="radio"
							name="analysis-mode"
							checked={analysisMode === 'folder'}
							onchange={() => (analysisMode = 'folder')}
						/>
						<div class="option-title-wrapper">
							<span class="option-name">Folder-Specific Analysis</span>
						</div>
					</div>

					<p class="option-description">
						Analyze a specific team or product folder for focused assessment. Ideal for team
						retrospectives and targeted improvements.
					</p>

					<ul class="option-benefits">
						<li>Focused team maturity assessment</li>
						<li>Faster analysis for subset</li>
						<li>Track team-level improvements</li>
						<li>Drill down into specific areas</li>
					</ul>

					{#if analysisMode === 'folder'}
						<div class="folder-selector">
							<label for="folder-analysis-select-2">Select folder to analyze:</label>
							<select
								id="folder-analysis-select-2"
								bind:value={folderForFolderAnalysis}
								class="folder-dropdown"
							>
								<option value={null}>Choose a folder...</option>
								{#each getFlattenedFolders(repoTreeData) as folder}
									<option value={folder}>
										{'  '.repeat(folder.depth)}📁 {folder.name} ({countRepositoriesInFolder(folder)}
										repos)
									</option>
								{/each}
							</select>

							<label class="checkbox-label">
								<input type="checkbox" bind:checked={includeSubfoldersInModal} />
								Include nested subfolders
							</label>
						</div>

						<button
							class="btn-primary"
							disabled={!folderForFolderAnalysis}
							onclick={startFolderAnalysisFromModal}
							style="margin-top: 1rem; width: 100%;"
						>
							<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
								/>
							</svg>
							<span>Start Folder Analysis</span>
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	/* ============================================
	   PROFESSIONAL UI/UX DESIGN SYSTEM
	   Based on Landing Page & Dashboard Pattern
	   ============================================ */

	/* Global Variables - Professional Design System */
	.treeview-container {
		--bg-primary: #000000;
		--bg-secondary: #0a0a0a;
		--text-primary: #ffffff;
		--text-secondary: #b8b8b8;
		--text-muted: #666666;
		--border-color: rgba(0, 217, 255, 0.3);
		--card-bg: rgba(0, 0, 0, 0.4);
		--card-bg-hover: rgba(0, 0, 0, 0.6);
		--primary-color: #00d9ff;
		--accent-color: #00d9ff;
		--success-color: #10b981;
		--error-color: #ef4444;
		--warning-color: #ffc107;

		min-height: 100vh;
		background: var(--bg-primary);
		color: var(--text-primary);
		position: relative;
		font-family:
			'Inter',
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			Roboto,
			sans-serif;
	}

	.treeview-container.light {
		--bg-primary: #ffffff;
		--bg-secondary: #f8fafc;
		--text-primary: #1a1a1a;
		--text-secondary: #666666;
		--text-muted: #888888;
		--border-color: rgba(0, 217, 255, 0.4);
		--card-bg: rgba(255, 255, 255, 0.95);
		--card-bg-hover: rgba(255, 255, 255, 1);
		--primary-color: #00d9ff;
		--accent-color: #00b8d4;
	}

	/* ============================================
	   NAVIGATION BAR - Professional Pattern
	   ============================================ */
	.top-navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 1000;
		background: rgba(0, 0, 0, 0.95);
		backdrop-filter: blur(20px);
		border-bottom: 1px solid rgba(0, 217, 255, 0.3);
		padding: 1rem 2rem;
		transition: all 0.3s ease;
	}

	:global(.treeview-container.light) .top-navbar {
		background: rgba(255, 255, 255, 0.95);
		border-bottom: 1px solid rgba(0, 217, 255, 0.2);
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

	/* Brand Section - Matching Landing Page */
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
		color: #ffffff;
		line-height: 1;
		letter-spacing: -0.02em;
	}

	:global(.treeview-container.light) .brand-name {
		color: #000000;
	}

	.brand-subtitle {
		font-size: 0.7rem;
		color: var(--text-secondary);
		opacity: 0.8;
		margin-top: 0.2rem;
		letter-spacing: 0.05em;
	}

	/* Breadcrumb - Professional Navigation */
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

	/* ============================================
	   SIDEBAR - Professional Button Pattern
	   ============================================ */
	.main-layout {
		display: flex;
		margin-top: 80px;
		min-height: calc(100vh - 80px);
	}

	.left-sidebar {
		position: fixed;
		left: 0;
		top: 80px;
		width: 320px;
		height: calc(100vh - 80px);
		background: rgba(0, 0, 0, 0.95);
		border-right: 1px solid rgba(0, 217, 255, 0.3);
		backdrop-filter: blur(20px);
		padding: 1.5rem;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	:global(.treeview-container.light) .left-sidebar {
		background: rgba(255, 255, 255, 0.95);
		border-right: 1px solid rgba(0, 217, 255, 0.2);
	}

	/* Back Button - Professional Design */
	.back-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: transparent;
		border: 1px solid rgba(0, 217, 255, 0.3);
		border-radius: 8px;
		color: var(--text-primary);
		cursor: pointer;
		transition: all 0.3s ease;
		font-size: 0.9rem;
		font-weight: 500;
	}

	.back-button:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: #00d9ff;
		transform: translateX(-4px);
		box-shadow: 0 4px 12px rgba(0, 217, 255, 0.2);
	}

	.back-icon {
		width: 18px;
		height: 18px;
		color: #00d9ff;
	}

	/* Sidebar Section */
	.sidebar-section {
		flex: 1;
	}

	.section-title {
		font-size: 0.75rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		margin-bottom: 1rem;
	}

	/* ============================================
	   STAT CARDS - Professional Clean Design
	   ============================================ */
	.stat-cards {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.stat-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
	}

	/* Shimmer effect on hover */
	.stat-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		transition: left 0.6s;
	}

	.stat-card:hover::before {
		left: 100%;
	}

	.stat-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 8px 20px rgba(0, 217, 255, 0.15);
		border-color: rgba(0, 217, 255, 0.5);
		background: rgba(0, 0, 0, 0.6);
	}

	.treeview-container.light .stat-card {
		background: rgba(255, 255, 255, 0.95);
		border: 1px solid rgba(0, 217, 255, 0.15);
	}

	.treeview-container.light .stat-card:hover {
		background: rgba(255, 255, 255, 1);
		border-color: rgba(0, 217, 255, 0.3);
		box-shadow: 0 8px 20px rgba(0, 217, 255, 0.12);
	}

	.stat-icon {
		font-size: 1.75rem;
	}

	.stat-content {
		display: flex;
		flex-direction: column;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 700;
		color: #00d9ff;
		line-height: 1;
	}

	.stat-label {
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin-top: 0.25rem;
	}

	/* ============================================
	   ACTION BUTTONS - Professional Pattern
	   Matching Landing Page Button Design
	   ============================================ */
	.sidebar-actions {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.action-button {
		padding: 0;
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
		background: rgba(0, 0, 0, 0.4);
	}

	/* Shimmer effect on hover */
	.action-button::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		transition: left 0.6s;
	}

	.action-button:hover::before {
		left: 100%;
	}

	.action-button:hover {
		transform: translateY(-2px);
		border-color: rgba(0, 217, 255, 0.5);
		box-shadow: 0 8px 20px rgba(0, 217, 255, 0.2);
		background: rgba(0, 0, 0, 0.6);
	}

	.action-button:active {
		transform: translateY(0);
	}

	.treeview-container.light .action-button {
		background: rgba(255, 255, 255, 0.95);
		border: 1px solid rgba(0, 217, 255, 0.15);
	}

	.treeview-container.light .action-button:hover {
		background: rgba(255, 255, 255, 1);
		border-color: rgba(0, 217, 255, 0.3);
		box-shadow: 0 8px 20px rgba(0, 217, 255, 0.15);
	}

	.button-content {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem 1.25rem;
		position: relative;
		z-index: 1;
	}

	.button-icon {
		width: 20px;
		height: 20px;
		flex-shrink: 0;
		color: #00d9ff;
		transition: transform 0.3s ease;
	}

	.action-button:hover .button-icon {
		transform: scale(1.1);
	}

	.button-text {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
		flex: 1;
	}

	.button-label {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
		line-height: 1.2;
	}

	.button-desc {
		font-size: 0.75rem;
		color: var(--text-muted);
		line-height: 1.2;
		opacity: 0.8;
	}

	.action-button:hover .button-desc {
		opacity: 1;
	}

	/* Specific button color variants */
	.action-button.add-repo .button-icon {
		color: #10b981;
	}

	/* Save Status */
	.save-status {
		padding: 0.75rem;
		border-radius: 8px;
		font-size: 0.875rem;
		text-align: center;
	}

	.save-status.success {
		background: rgba(16, 185, 129, 0.1);
		color: var(--success-color);
		border: 1px solid rgba(16, 185, 129, 0.3);
	}

	.save-status.error {
		background: rgba(239, 68, 68, 0.1);
		color: var(--error-color);
		border: 1px solid rgba(239, 68, 68, 0.3);
	}

	/* ============================================
	   MAIN CONTENT AREA
	   ============================================ */
	.main-content {
		margin-left: 320px;
		flex: 1;
		position: relative;
		min-height: calc(100vh - 80px);
	}

	.svg-background {
		position: absolute;
		inset: 0;
		pointer-events: none;
		opacity: 0.05;
		overflow: hidden;
	}

	.content-overlay {
		position: relative;
		z-index: 1;
		padding: 2rem;
	}

	/* Loading State */
	.loading-state {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 4rem;
	}

	.loading-spinner {
		width: 40px;
		height: 40px;
		border: 4px solid rgba(0, 217, 255, 0.2);
		border-radius: 50%;
		border-top-color: var(--primary-color);
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-text {
		font-size: 1rem;
		color: var(--text-secondary);
	}

	/* Error State */
	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 4rem;
	}

	.error-icon {
		width: 64px;
		height: 64px;
		color: var(--error-color);
	}

	.error-message {
		color: var(--error-color);
		font-size: 1.1rem;
	}

	/* Empty State - Professional Design */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.5rem;
		padding: 4rem;
		text-align: center;
	}

	.empty-icon {
		width: 100px;
		height: 100px;
		background: rgba(0, 217, 255, 0.1);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid rgba(0, 217, 255, 0.2);
	}

	.empty-icon svg {
		width: 50px;
		height: 50px;
		color: #00d9ff;
	}

	.empty-title {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.empty-description {
		font-size: 1.1rem;
		color: var(--text-secondary);
		max-width: 500px;
		line-height: 1.6;
	}

	.empty-actions {
		display: flex;
		gap: 1rem;
	}

	.empty-button {
		padding: 1rem 2rem;
		border-radius: 8px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		font-size: 1rem;
	}

	.empty-button.primary {
		background: #ffffff;
		color: #000000;
		border: none;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
	}

	.empty-button.primary:hover {
		transform: translateY(-3px);
		box-shadow: 0 15px 35px rgba(0, 217, 255, 0.4);
		background: #00d9ff;
		color: #000000;
	}

	.empty-button.secondary {
		background: rgba(0, 0, 0, 0.3);
		color: #00d9ff;
		border: 2px solid #00d9ff;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
	}

	.empty-button.secondary:hover {
		background: #00d9ff;
		color: #000000;
		transform: translateY(-3px);
		box-shadow: 0 15px 35px rgba(0, 217, 255, 0.5);
	}

	/* ============================================
	   FOLDER CARDS - Professional Pattern
	   Matching Landing Page Feature Cards
	   ============================================ */
	.folders-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
		gap: 1.5rem;
	}

	.folder-card {
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		backdrop-filter: blur(20px);
		padding: 1.5rem;
		transition: all 0.4s ease;
		max-height: 600px;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		position: relative;
	}

	/* Shimmer effect on hover */
	.folder-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		transition: left 0.6s;
	}

	.folder-card:hover::before {
		left: 100%;
	}

	.folder-card:hover {
		transform: translateY(-5px);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.15);
		border-color: rgba(0, 217, 255, 0.5);
		background: rgba(0, 0, 0, 0.6);
	}

	.treeview-container.light .folder-card {
		background: rgba(255, 255, 255, 0.95);
		border: 1px solid rgba(0, 217, 255, 0.15);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
	}

	.treeview-container.light .folder-card:hover {
		background: rgba(255, 255, 255, 1);
		border-color: rgba(0, 217, 255, 0.3);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.12);
	}

	.folder-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.expand-button {
		background: transparent;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.25rem;
		transition: all 0.3s ease;
	}

	.expand-button:hover {
		color: var(--primary-color);
	}

	.expand-icon {
		width: 20px;
		height: 20px;
	}

	.folder-icon {
		width: 24px;
		height: 24px;
		color: var(--primary-color);
	}

	.folder-name {
		font-size: 1.1rem;
		font-weight: 600;
		color: var(--text-primary);
		flex: 1;
	}

	.folder-name-input {
		padding: 0.5rem;
		background: rgba(0, 217, 255, 0.1);
		border: 1px solid var(--border-color);
		border-radius: 6px;
		color: var(--text-primary);
		font-size: 1.1rem;
		font-weight: 600;
		flex: 1;
	}

	.folder-name-input:focus {
		outline: none;
		border-color: var(--primary-color);
		box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1);
	}

	.item-count {
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.folder-actions {
		display: flex;
		gap: 0.5rem;
		margin-left: auto;
	}

	.action-icon {
		background: transparent;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.25rem;
		transition: all 0.3s ease;
	}

	.action-icon:hover {
		color: var(--primary-color);
	}

	.action-icon.analyze {
		color: #00d9ff;
	}

	.action-icon.analyze:hover {
		color: #00d9ff;
		opacity: 0.8;
	}

	.action-icon.delete:hover {
		color: var(--error-color);
	}

	.action-icon svg {
		width: 18px;
		height: 18px;
	}

	/* Folder Children */
	.folder-children {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border-color);
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		overflow-y: auto; /* Add scroll for nested content */
		max-height: 450px; /* Limit children height */
		padding-right: 0.5rem;
	}

	/* Custom scrollbar for folder children */
	.folder-children::-webkit-scrollbar {
		width: 6px;
	}

	.folder-children::-webkit-scrollbar-track {
		background: rgba(0, 217, 255, 0.05);
		border-radius: 3px;
	}

	.folder-children::-webkit-scrollbar-thumb {
		background: rgba(0, 217, 255, 0.3);
		border-radius: 3px;
	}

	.folder-children::-webkit-scrollbar-thumb:hover {
		background: rgba(0, 217, 255, 0.5);
	}

	/* Nested Folder Item */
	.nested-folder-item {
		background: rgba(0, 217, 255, 0.03);
		border: 1px solid rgba(0, 217, 255, 0.15);
		border-radius: 10px;
		padding: 0.75rem;
		transition: all 0.3s ease;
	}

	.nested-folder-item:hover {
		background: rgba(0, 217, 255, 0.08);
		border-color: rgba(0, 217, 255, 0.3);
	}

	.nested-folder-item.deeper {
		margin-left: 1rem;
		background: rgba(0, 217, 255, 0.02);
		border-color: rgba(0, 217, 255, 0.1);
	}

	/* Visual depth indicator line */
	.nested-folder-children::before {
		content: '';
		position: absolute;
		left: -8px;
		top: 0;
		bottom: 0;
		width: 2px;
		background: linear-gradient(to bottom, rgba(74, 158, 255, 0.3), rgba(74, 158, 255, 0.1));
		border-radius: 2px;
	}

	.nested-folder-children.deeper {
		margin-left: 1rem;
	}

	.nested-folder-children.deeper::before {
		background: linear-gradient(to bottom, rgba(147, 51, 234, 0.3), rgba(147, 51, 234, 0.1)) er;
		gap: 0.5rem;
	}

	.nested-folder-name {
		font-weight: 600;
		color: var(--text-primary);
		flex: 1;
		font-size: 0.95rem;
	}

	.nested-folder-children {
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid rgba(0, 217, 255, 0.1);
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-left: 0.5rem;
	}

	.nested-folder-children.deeper {
		margin-left: 1rem;
	}

	/* Small variants for nested elements */
	.expand-button.small {
		padding: 0.2rem;
	}

	.expand-button.small .expand-icon {
		width: 16px;
		height: 16px;
	}

	.folder-icon.small {
		width: 20px;
		height: 20px;
	}

	.folder-name-input.small {
		font-size: 0.95rem;
	}

	.item-count.small {
		font-size: 0.75rem;
	}

	.action-icon.small svg {
		width: 16px;
		height: 16px;
	}

	.action-icon.analyze {
		color: #00d9ff;
	}

	.action-icon.analyze:hover {
		color: #00d9ff;
		opacity: 0.8;
	}

	/* Repo Item */
	.repo-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 8px;
		transition: all 0.3s ease;
	}

	.repo-item:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: #00d9ff;
	}

	.repo-icon {
		width: 20px;
		height: 20px;
		color: #00d9ff;
	}

	.repo-name {
		font-weight: 500;
		color: var(--text-primary);
		flex: 1;
	}

	.repo-badge {
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.repo-badge.private {
		background: rgba(136, 136, 136, 0.2);
		color: var(--text-secondary);
	}

	.workflow-count {
		font-size: 0.8rem;
		color: var(--text-muted);
	}

	.repo-actions {
		display: flex;
		gap: 0.5rem;
	}

	/* Notifications */
	:global(.notification) {
		position: fixed;
		top: 100px;
		right: 2rem;
		z-index: 9999;
		padding: 1rem 1.5rem;
		background: var(--card-bg);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		backdrop-filter: blur(20px);
		box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
		color: var(--text-primary);
		animation: slideIn 0.3s ease;
	}

	:global(.notification.success) {
		border-color: var(--success-color);
		background: rgba(22, 163, 74, 0.1);
	}

	:global(.notification.error) {
		border-color: var(--error-color);
		background: rgba(255, 71, 87, 0.1);
	}

	:global(.notification.fade-out) {
		animation: fadeOut 0.3s ease;
		opacity: 0;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	@keyframes fadeOut {
		to {
			opacity: 0;
			transform: translateY(-10px);
		}
	}

	/* ============================================
	   MODAL STYLES - Professional Clean Design
	   ============================================ */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 9999;
		background: rgba(0, 0, 0, 0.7);
		backdrop-filter: blur(8px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		animation: backdropFadeIn 0.2s ease;
	}

	/* Keep modal backdrop dark in light theme */
	:global(.treeview-container.light) .modal-backdrop {
		background: rgba(0, 0, 0, 0.5);
	}

	@keyframes backdropFadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.modal-container {
		background: rgba(0, 0, 0, 0.95);
		border: 1px solid rgba(0, 217, 255, 0.3);
		border-radius: 16px;
		backdrop-filter: blur(30px);
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
		width: 100%;
		max-width: 500px;
		max-height: 90vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		animation: modalSlideIn 0.3s ease;
	}
	.modal-container.large {
		max-width: 900px;
	}

	/* Keep modals dark in light theme for consistency */
	:global(.treeview-container.light) .modal-container {
		background: rgba(0, 0, 0, 0.95);
		border: 1px solid rgba(0, 217, 255, 0.4);
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
	}
	@keyframes modalSlideIn {
		from {
			opacity: 0;
			transform: translateY(-20px) scale(0.95);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.modal-header {
		padding: 1.5rem 2rem;
		border-bottom: 1px solid rgba(0, 217, 255, 0.2);
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.modal-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: #ffffff !important;
		margin: 0;
	}
	.modal-subtitle {
		font-size: 0.875rem;
		color: rgba(255, 255, 255, 0.85) !important;
		margin-top: 0.25rem;
		opacity: 0.9;
	}
	.modal-close {
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.2);
		color: var(--error-color);
		padding: 0.5rem;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.modal-close:hover {
		background: rgba(239, 68, 68, 0.2);
		transform: rotate(90deg);
	}

	.modal-close svg {
		width: 20px;
		height: 20px;
		display: block;
	}

	.modal-body {
		padding: 2rem;
		overflow-y: auto;
		flex: 1;
	}

	.form-group {
		margin-bottom: 1.5rem;
	}

	.form-label {
		display: block;
		font-size: 0.875rem;
		font-weight: 600;
		color: #ffffff !important;
		margin-bottom: 0.5rem;
	}

	.form-input {
		width: 100%;
		padding: 0.875rem 1rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid rgba(0, 217, 255, 0.3);
		border-radius: 10px;
		color: #ffffff !important;
		font-size: 1rem;
		transition: all 0.3s ease;
	}

	.form-input:focus {
		outline: none;
		border-color: var(--primary-color);
		background: rgba(0, 217, 255, 0.1);
		box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1);
	}

	.info-box {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		background: rgba(0, 217, 255, 0.1);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 10px;
	}

	.info-icon {
		width: 20px;
		height: 20px;
		color: var(--primary-color);
		flex-shrink: 0;
	}

	.info-text {
		font-size: 0.875rem;
		color: rgba(255, 255, 255, 0.85) !important;
		margin: 0;
	}

	.highlight {
		font-weight: 600;
		color: var(--primary-color);
	}

	.modal-footer {
		padding: 1.5rem 2rem;
		border-top: 1px solid rgba(0, 217, 255, 0.2);
		display: flex;
		gap: 1rem;
		justify-content: flex-end;
	}
	/* ============================================
	   BUTTONS - Professional Pattern
	   Matching Landing Page Button Design
	   ============================================ */
	.btn-primary,
	.btn-secondary {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 1rem 1.5rem;
		border-radius: 8px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		font-size: 0.95rem;
	}

	.btn-primary {
		background: #ffffff;
		color: #000000;
		border: none;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
	}

	.btn-primary:hover:not(:disabled) {
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
		background: #00d9ff;
		color: #000000;
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		transform: none;
	}

	.btn-secondary {
		background: rgba(0, 0, 0, 0.3);
		color: #00d9ff;
		border: 2px solid #00d9ff;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.4),
			0 0 20px rgba(0, 217, 255, 0.2);
	}

	.btn-secondary:hover {
		background: #00d9ff;
		color: #000000;
		transform: translateY(-3px);
		border-color: #00d9ff;
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.5),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}
	.btn-icon {
		width: 18px;
		height: 18px;
	}
	/* Folder Analysis Modal Specific Styles */
	.modal-overlay {
		position: fixed;
		inset: 0;
		z-index: 9999;
		background: rgba(0, 0, 0, 0.7);
		backdrop-filter: blur(8px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		animation: backdropFadeIn 0.2s ease;
	}

	.modal {
		background: rgba(0, 0, 0, 0.95);
		border: 1px solid var(--border-color);
		border-radius: 20px;
		backdrop-filter: blur(30px);
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
		width: 100%;
		max-width: 600px;
		max-height: 90vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		animation: modalSlideIn 0.3s ease;
	}

	.modal-header h3 {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0;
	}

	.close-btn {
		background: rgba(255, 71, 87, 0.1);
		border: 1px solid rgba(255, 71, 87, 0.2);
		color: var(--error-color);
		padding: 0.5rem;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.close-btn:hover {
		background: rgba(255, 71, 87, 0.2);
		transform: rotate(90deg);
	}

	.close-btn svg {
		width: 20px;
		height: 20px;
		display: block;
	}

	.folder-info {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.info-row {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid var(--border-color);
		border-radius: 10px;
		transition: all 0.3s ease;
	}
	.info-row:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: var(--primary-color);
	}

	.folder-icon,
	.path-icon,
	.repo-icon {
		width: 24px;
		height: 24px;
		color: var(--primary-color);
		flex-shrink: 0;
	}

	.info-text {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		flex: 1;
	}

	.info-text .label {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.info-text .value {
		font-size: 1rem;
		font-weight: 600;
		color: #ffffff;
	}

	:global(.treeview-container.light) .info-text .label {
		color: rgba(255, 255, 255, 0.6);
	}

	.badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.25rem 0.75rem;
		background: #00d9ff;
		color: #000000;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 700;
		box-shadow: 0 2px 8px rgba(0, 217, 255, 0.3);
	}

	.options {
		margin-bottom: 1.5rem;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid var(--border-color);
		border-radius: 10px;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.checkbox-label:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: var(--primary-color);
	}

	.checkbox-label input[type='checkbox'] {
		width: 20px;
		height: 20px;
		cursor: pointer;
		accent-color: var(--primary-color);
	}

	.checkbox-label span {
		font-size: 0.95rem;
		color: rgba(255, 255, 255, 0.85);
		flex: 1;
	}

	.progress-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 2rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		margin-bottom: 1.5rem;
	}

	.progress-text {
		font-size: 0.95rem;
		color: rgba(255, 255, 255, 0.85);
		text-align: center;
		margin: 0;
	}

	.info-notice {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 1rem;
		background: rgba(0, 217, 255, 0.1);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 10px;
	}

	.notice-icon {
		width: 20px;
		height: 20px;
		color: var(--primary-color);
		flex-shrink: 0;
		margin-top: 2px;
	}

	.info-notice span {
		font-size: 0.875rem;
		color: rgba(255, 255, 255, 0.85);
		line-height: 1.5;
	}

	/* Analysis Options Modal Styles */
	.analysis-options-modal {
		max-width: 800px;
		width: 100%;
	}

	.analysis-options-body {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		max-height: 70vh;
		overflow-y: auto;
	}

	.analysis-option {
		padding: 1.5rem;
		border: 2px solid var(--border-color);
		border-radius: 12px;
		background: rgba(255, 255, 255, 0.02);
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.analysis-option:hover {
		background: rgba(0, 217, 255, 0.05);
		border-color: var(--primary-color);
	}

	.analysis-option.selected {
		border-color: var(--primary-color);
		background: rgba(0, 217, 255, 0.1);
		box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1);
	}
	.option-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.option-header input[type='radio'] {
		width: 20px;
		height: 20px;
		cursor: pointer;
	}

	.option-title-wrapper {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex: 1;
	}

	.option-name {
		font-size: 1.1rem;
		font-weight: 700;
		color: #ffffff !important;
	}
	.recommended-badge {
		padding: 0.25rem 0.75rem;
		background: linear-gradient(135deg, #16a34a, #10b981);
		color: white;
		border-radius: 6px;
		font-size: 0.75rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.option-description {
		font-size: 0.95rem;
		color: rgba(255, 255, 255, 0.8) !important;
		line-height: 1.6;
		margin: 0 0 1rem 0;
	}

	.option-benefits {
		list-style: none;
		padding: 0;
		margin: 0 0 1rem 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.option-benefits li {
		font-size: 0.875rem;
		color: rgba(255, 255, 255, 0.8) !important;
		padding-left: 1.5rem;
		position: relative;
	}

	.option-benefits li::before {
		content: '✓';
		position: absolute;
		left: 0;
		color: var(--success-color);
		font-weight: 700;
	}

	.option-stats {
		display: flex;
		gap: 1.5rem;
		flex-wrap: wrap;
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border-color);
	}

	.option-stats .stat {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: rgba(255, 255, 255, 0.75);
	}
	.option-stats .stat svg {
		width: 16px;
		height: 16px;
		color: var(--primary-color);
	}

	.folder-selector {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border-color);
	}

	.folder-selector label {
		font-size: 0.875rem;
		font-weight: 600;
		color: #ffffff !important;
	}

	.folder-dropdown {
		padding: 0.875rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid rgba(0, 217, 255, 0.3);
		border-radius: 8px;
		color: #ffffff !important;
		font-size: 0.95rem;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.folder-dropdown:focus {
		outline: none;
		border-color: var(--primary-color);
		background: rgba(0, 217, 255, 0.1);
		box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1);
	}

	.folder-dropdown option {
		background: #000000;
		color: #ffffff;
	}
	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: rgba(255, 255, 255, 0.8);
		cursor: pointer;
	}

	.checkbox-label input[type='checkbox'] {
		width: 18px;
		height: 18px;
		cursor: pointer;
	}

	/* Selection Grid */
	.selection-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
	}

	.selection-panel {
		background: rgba(0, 217, 255, 0.02);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.panel-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		color: #ffffff !important;
		margin: 0;
	}

	.panel-icon {
		font-size: 1.25rem;
	}

	.panel-loading,
	.panel-empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 2rem;
		text-align: center;
	}

	.panel-empty {
		text-align: center;
		padding: 2rem;
		color: rgba(255, 255, 255, 0.6);
		font-size: 0.875rem;
	}

	.link-button {
		background: transparent;
		border: none;
		color: var(--primary-color);
		cursor: pointer;
		font-size: 0.875rem;
		text-decoration: underline;
	}

	.link-button:hover {
		color: var(--accent-color);
	}

	.selection-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-height: 400px;
		overflow-y: auto;
	}

	.selection-item {
		background: rgba(255, 255, 255, 0.02);
		border: 1px solid var(--border-color);
		border-radius: 8px;
		padding: 0.75rem;
		cursor: pointer;
		transition: all 0.3s ease;
		text-align: left;
		width: 100%;
	}

	.selection-item:hover {
		background: rgba(0, 217, 255, 0.1);
		border-color: var(--primary-color);
	}

	.selection-item.selected {
		background: rgba(0, 217, 255, 0.15);
		border-color: var(--primary-color);
		box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1);
	}

	.item-content {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.item-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.item-name {
		font-weight: 600;
		color: var(--text-primary);
		font-size: 0.95rem;
	}

	:global(.treeview-container.light) .item-name {
		color: #ffffff;
	}

	.item-description {
		font-size: 0.8rem;
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.4;
	}

	:global(.treeview-container.light) .item-description {
		color: rgba(255, 255, 255, 0.75);
	}

	.item-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.meta-item {
		font-size: 0.75rem;
		color: var(--text-muted);
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	:global(.treeview-container.light) .meta-item {
		color: rgba(255, 255, 255, 0.65);
	}
	.language-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--primary-color);
	}

	.meta-badge {
		padding: 0.125rem 0.5rem;
		background: rgba(136, 136, 136, 0.2);
		border-radius: 4px;
		font-size: 0.7rem;
		font-weight: 600;
	}

	.check-icon {
		width: 20px;
		height: 20px;
		color: var(--primary-color);
		flex-shrink: 0;
	}

	.folder-icon-small {
		width: 16px;
		height: 16px;
		color: var(--primary-color);
		flex-shrink: 0;
	}

	.selection-summary {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		background: rgba(22, 163, 74, 0.1);
		border: 1px solid rgba(22, 163, 74, 0.2);
		border-radius: 8px;
		margin-top: 1rem;
	}

	.summary-icon {
		width: 20px;
		height: 20px;
		color: var(--success-color);
		flex-shrink: 0;
	}

	.summary-text {
		font-size: 0.875rem;
		color: var(--text-secondary);
		margin: 0;
	}

	.loading-spinner.small {
		width: 16px;
		height: 16px;
		border-width: 2px;
	}

	/* Responsive */
	@media (max-width: 1200px) {
		.left-sidebar {
			width: 280px;
		}

		.main-content {
			margin-left: 280px;
		}
	}

	@media (max-width: 768px) {
		.main-layout {
			flex-direction: column;
		}

		.left-sidebar {
			position: relative;
			width: 100%;
			height: auto;
			top: 0;
		}

		.main-content {
			margin-left: 0;
		}

		.folders-grid {
			grid-template-columns: 1fr;
		}

		.navbar-left {
			gap: 1rem;
		}

		.breadcrumb {
			display: none;
		}

		.brand-icon {
			width: 36px;
			height: 36px;
		}

		.brand-name {
			font-size: 1.2rem;
		}
	}

	@media (max-width: 480px) {
		.top-navbar {
			padding: 0.75rem 1rem;
		}

		.folders-grid {
			grid-template-columns: 1fr;
			gap: 1rem;
		}

		.modal-container {
			max-width: 95%;
		}
	}
</style>
