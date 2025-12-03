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
        const unsubscribe = isDarkMode.subscribe(value => {
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
    
    // Repository Tree ID for analysis
    let currentRepositoryTreeId = $state(null);
    
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
                console.log('✅ Repository tree data loaded:', repoTreeData, 'Tree ID:', currentRepositoryTreeId, 'Metadata:', result.metadata);
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
                        workflows += node.children.filter(child => child.type === 'workflow').length;
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
            
            showNotification(`Repository "${selectedRepoToAdd.name}" added with ${workflows.length} workflows!`, 'success');
            closeAddRepoModal();
            
        } catch (err) {
            console.error('Failed to add repository:', err);
            showNotification('Failed to add repository', 'error');
        } finally {
            addingRepo = false;
        }
    }
    
    // Node operations
    function toggleNode(node) {
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
            const token = localStorage.getItem('auth_token') || 
                         sessionStorage.getItem('auth_token') || 
                         localStorage.getItem('github_token');
            
            if (!token) {
                throw new Error('Authentication required. Please login first.');
            }
            
            const response = await fetch('http://localhost:8000/api/workspace-intelligence/analyze-folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
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
            
            <!-- Right: Theme Toggle -->
            <div class="navbar-right">
                <button 
                    onclick={toggleTheme}
                    class="theme-toggle"
                    title="Toggle theme"
                >
                    {#if darkMode}
                        <svg class="theme-icon" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z"/>
                        </svg>
                    {:else}
                        <svg class="theme-icon" fill="currentColor" viewBox="0 0 24 24">
                            <path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z" clip-rule="evenodd"/>
                        </svg>
                    {/if}
                </button>
            </div>
        </div>
    </nav>

    <!-- Main Layout: Sidebar + Content -->
    <div class="main-layout">
        <!-- Left Sidebar -->
        <aside class="left-sidebar">
            <!-- Back to Workspace Button -->
            <button 
                onclick={() => goto(`/github/workspace/${orgName}`)}
                class="back-button"
            >
                <svg class="back-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
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
                <button 
                    onclick={() => goto(`/github/workspace/${orgName}/intelligence`)}
                    class="action-button intelligence"
                >
                    <div class="button-content">
                        <svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <div class="button-text">
                            <span class="button-label">Workspace Intelligence</span>
                            <span class="button-desc">AI-powered insights</span>
                        </div>
                    </div>
                </button>

                <button 
                    onclick={openNewFolderModal}
                    class="action-button new-folder"
                >
                    <div class="button-content">
                        <svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                        </svg>
                        <div class="button-text">
                            <span class="button-label">New Folder</span>
                            <span class="button-desc">Organize repositories</span>
                        </div>
                    </div>
                </button>

                <button 
                    onclick={openAddRepoModal}
                    class="action-button add-repo"
                >
                    <div class="button-content">
                        <svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
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
            <div class="svg-background">
                <svg viewBox="0 0 2000 1000" xmlns="http://www.w3.org/2000/svg" class="bg-svg">
                    <defs>
                        <linearGradient id="pipelineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" class="gradient-start" />
                            <stop offset="50%" class="gradient-mid" />
                            <stop offset="100%" class="gradient-end" />
                        </linearGradient>
                        
                        <linearGradient id="pipelineHighlight" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" class="highlight-start" />
                            <stop offset="100%" class="highlight-end" />
                        </linearGradient>
                        
                        <linearGradient id="platformGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" class="platform-gradient-start" />
                            <stop offset="100%" class="platform-gradient-end" />
                        </linearGradient>
                        
                        <linearGradient id="blueBoxGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" class="blue-box-start" />
                            <stop offset="100%" class="blue-box-end" />
                        </linearGradient>
                        
                        <linearGradient id="greenGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" class="green-start" />
                            <stop offset="100%" class="green-end" />
                        </linearGradient>
                        
                        <linearGradient id="yellowGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" class="yellow-start" />
                            <stop offset="100%" class="yellow-end" />
                        </linearGradient>
                        
                        <radialGradient id="glowGradient">
                            <stop offset="0%" class="glow-start" />
                            <stop offset="100%" class="glow-end" />
                        </radialGradient>
                        
                        <filter id="softShadow" x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur in="SourceAlpha" stdDeviation="4"/>
                            <feOffset dx="3" dy="5" result="offsetblur"/>
                            <feComponentTransfer>
                                <feFuncA type="linear" slope="0.25"/>
                            </feComponentTransfer>
                            <feMerge>
                                <feMergeNode/>
                                <feMergeNode in="SourceGraphic"/>
                            </feMerge>
                        </filter>
                        
                        <filter id="heavyShadow" x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur in="SourceAlpha" stdDeviation="8"/>
                            <feOffset dx="0" dy="10" result="offsetblur"/>
                            <feComponentTransfer>
                                <feFuncA type="linear" slope="0.3"/>
                            </feComponentTransfer>
                            <feMerge>
                                <feMergeNode/>
                                <feMergeNode in="SourceGraphic"/>
                            </feMerge>
                        </filter>
                        
                        <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
                            <polygon points="0 0, 10 3, 0 6" class="arrow-fill"/>
                        </marker>
                    </defs>
                    
                    <!-- Background blobs -->
                    <ellipse cx="200" cy="300" rx="220" ry="180" fill="url(#glowGradient)" opacity="0.4"/>
                    <ellipse cx="1000" cy="200" rx="280" ry="200" fill="url(#glowGradient)" opacity="0.3"/>
                    <ellipse cx="1700" cy="400" rx="250" ry="190" fill="url(#glowGradient)" opacity="0.35"/>
                    <ellipse cx="600" cy="700" rx="180" ry="140" fill="url(#glowGradient)" opacity="0.25"/>
                    <ellipse cx="1400" cy="750" rx="200" ry="150" fill="url(#glowGradient)" opacity="0.3"/>

                    <!-- Main 3D ribbon pipeline -->
                    <g id="mainPipeline">
                        <!-- Pipeline shadow -->
                        <path d="M 120,750 Q 200,700 280,670 T 440,620 Q 560,600 680,590 T 920,575 Q 1080,570 1200,550 T 1420,510 Q 1560,480 1680,430 T 1850,320" fill="none" class="pipeline-shadow" stroke-width="35" stroke-linecap="round" opacity="0.2" transform="translate(5, 8)"/>
                        
                        <!-- Pipeline main body -->
                        <path d="M 120,750 Q 200,700 280,670 T 440,620 Q 560,600 680,590 T 920,575 Q 1080,570 1200,550 T 1420,510 Q 1560,480 1680,430 T 1850,320" fill="none" stroke="url(#pipelineGradient)" stroke-width="32" stroke-linecap="round" stroke-linejoin="round"/>
                        
                        <!-- Pipeline top highlight -->
                        <path d="M 120,750 Q 200,700 280,670 T 440,620 Q 560,600 680,590 T 920,575 Q 1080,570 1200,550 T 1420,510 Q 1560,480 1680,430 T 1850,320" fill="none" stroke="url(#pipelineHighlight)" stroke-width="12" stroke-linecap="round" opacity="0.7" transform="translate(0, -8)"/>
                        
                        <!-- Pipeline edge outline -->
                        <path d="M 120,750 Q 200,700 280,670 T 440,620 Q 560,600 680,590 T 920,575 Q 1080,570 1200,550 T 1420,510 Q 1560,480 1680,430 T 1850,320" fill="none" class="pipeline-outline" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
                        
                        <!-- Dotted flow animation lines -->
                        <path d="M 150,745 Q 220,700 300,675" fill="none" class="flow-line" stroke-width="2" stroke-dasharray="4 8" opacity="0.5"/>
                        <path d="M 500,615 Q 600,600 700,592" fill="none" class="flow-line" stroke-width="2" stroke-dasharray="4 8" opacity="0.5"/>
                        <path d="M 1000,565 Q 1100,560 1200,550" fill="none" class="flow-line" stroke-width="2" stroke-dasharray="4 8" opacity="0.5"/>
                        <path d="M 1500,495 Q 1600,465 1700,425" fill="none" class="flow-line" stroke-width="2" stroke-dasharray="4 8" opacity="0.5"/>
                    </g>

                    <!-- SECTION 1: Repository Tree View -->
                    <g id="section1" filter="url(#heavyShadow)">
                        <g transform="translate(70, 650)">
                            <!-- Platform shadows and base -->
                            <ellipse cx="100" cy="95" rx="95" ry="25" class="platform-shadow-dark" opacity="0.6"/>
                            <ellipse cx="100" cy="90" rx="100" ry="28" fill="url(#platformGradient)" class="platform-stroke" stroke-width="2.5"/>
                            <path d="M 5,90 Q 5,105 100,120 Q 195,105 195,90" class="platform-side" stroke-width="2"/>
                            
                            <!-- 3D Folder boxes -->
                            <g transform="translate(20, 30)">
                                <!-- Frontend folder -->
                                <rect x="0" y="0" width="45" height="38" class="folder-box-1" stroke-width="2" rx="3"/>
                                <path d="M 0,0 L 5,-5 L 50,-5 L 45,0 Z" class="folder-top-1" stroke-width="2"/>
                                <path d="M 45,0 L 50,-5 L 50,33 L 45,38 Z" class="folder-right-1" stroke-width="2"/>
                                <text x="22" y="24" font-size="12" class="folder-text" font-family="Arial" text-anchor="middle">FE</text>
                                
                                <!-- Backend folder -->
                                <rect x="55" y="0" width="45" height="38" class="folder-box-2" stroke-width="2" rx="3"/>
                                <path d="M 55,0 L 60,-5 L 105,-5 L 100,0 Z" class="folder-top-2" stroke-width="2"/>
                                <path d="M 100,0 L 105,-5 L 105,33 L 100,38 Z" class="folder-right-2" stroke-width="2"/>
                                <text x="77" y="24" font-size="12" class="folder-text" font-family="Arial" text-anchor="middle">BE</text>
                                
                                <!-- Infrastructure folder -->
                                <rect x="110" y="0" width="50" height="38" class="folder-box-3" stroke-width="2" rx="3"/>
                                <path d="M 110,0 L 115,-5 L 165,-5 L 160,0 Z" class="folder-top-3" stroke-width="2"/>
                                <path d="M 160,0 L 165,-5 L 165,33 L 160,38 Z" class="folder-right-3" stroke-width="2"/>
                                <text x="135" y="24" font-size="11" class="folder-text" font-family="Arial" text-anchor="middle">Infra</text>
                            </g>
                        </g>
                        
                        <!-- GitHub & GitLab logos -->
                        <g transform="translate(50, 580)">
                            <circle cx="30" cy="30" r="22" fill="#fff" class="platform-stroke" stroke-width="2.5"/>
                            <circle cx="30" cy="28" r="18" class="folder-text"/>
                            <circle cx="24" cy="25" r="3" fill="#fff"/>
                            <circle cx="36" cy="25" r="3" fill="#fff"/>
                        </g>
                        
                        <g transform="translate(220, 580)">
                            <circle cx="30" cy="30" r="22" fill="#fff" class="platform-stroke" stroke-width="2.5"/>
                            <path d="M 30,18 L 36,28 L 42,38 L 30,46 L 18,38 L 24,28 Z" fill="#fc6d26" class="platform-stroke" stroke-width="2"/>
                        </g>
                        
                        <!-- Stick figure dragging repo -->
                        <g transform="translate(140, 710)">
                            <circle cx="0" cy="0" r="6" class="folder-text" stroke-width="1.5"/>
                            <line x1="0" y1="6" x2="0" y2="20" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="10" x2="-8" y2="16" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="10" x2="8" y2="14" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="20" x2="-5" y2="30" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="20" x2="5" y2="30" class="folder-text" stroke-width="2"/>
                            
                            <rect x="10" y="10" width="20" height="20" class="stat-box-1" stroke-width="2" rx="2"/>
                            <line x1="13" y1="15" x2="27" y2="15" class="gear-stroke-1" stroke-width="1.5"/>
                            <line x1="13" y1="20" x2="27" y2="20" class="gear-stroke-1" stroke-width="1.5"/>
                        </g>
                        
                        <!-- Label -->
                        <text x="90" y="820" font-size="14" class="stat-label" font-family="Comic Sans MS, cursive" font-style="italic">Organize repositories into tree</text>
                    </g>

                    <!-- SECTION 2: Auto-Fetch Machine -->
                    <g id="section2" filter="url(#heavyShadow)">
                        <ellipse cx="420" cy="625" rx="85" ry="22" class="platform-shadow-light" opacity="0.5"/>
                        
                        <g transform="translate(350, 510)">
                            <!-- 3D Machine Box -->
                            <rect x="0" y="0" width="140" height="100" fill="url(#blueBoxGradient)" class="machine-stroke" stroke-width="3" rx="8"/>
                            <path d="M 0,0 L 12,-10 L 152,-10 L 140,0 Z" class="machine-top-face" stroke-width="3"/>
                            <path d="M 140,0 L 152,-10 L 152,90 L 140,100 Z" class="machine-right-face" stroke-width="3"/>
                            
                            <!-- Highlight shine -->
                            <rect x="8" y="8" width="50" height="70" fill="#fff" opacity="0.15" rx="4"/>
                            
                            <!-- Animated gears -->
                            <g transform="translate(40, 50)">
                                <circle cx="0" cy="0" r="18" fill="none" class="gear-stroke-1" stroke-width="3"/>
                                <circle cx="0" cy="0" r="10" class="gear-fill-1"/>
                                <line x1="0" y1="-10" x2="0" y2="-18" class="gear-stroke-1" stroke-width="4"/>
                                <line x1="7.07" y1="-7.07" x2="12.73" y2="-12.73" class="gear-stroke-1" stroke-width="4"/>
                                <line x1="10" y1="0" x2="18" y2="0" class="gear-stroke-1" stroke-width="4"/>
                                <line x1="7.07" y1="7.07" x2="12.73" y2="12.73" class="gear-stroke-1" stroke-width="4"/>
                                <line x1="0" y1="10" x2="0" y2="18" class="gear-stroke-1" stroke-width="4"/>
                                <line x1="-7.07" y1="7.07" x2="-12.73" y2="12.73" class="gear-stroke-1" stroke-width="4"/>
                                <line x1="-10" y1="0" x2="-18" y2="0" class="gear-stroke-1" stroke-width="4"/>
                                <line x1="-7.07" y1="-7.07" x2="-12.73" y2="-12.73" class="gear-stroke-1" stroke-width="4"/>
                            </g>
                            
                            <g transform="translate(100, 50)">
                                <circle cx="0" cy="0" r="15" fill="none" class="gear-stroke-2" stroke-width="2.5"/>
                                <circle cx="0" cy="0" r="8" class="gear-fill-2"/>
                                <line x1="0" y1="-8" x2="0" y2="-15" class="gear-stroke-2" stroke-width="3"/>
                                <line x1="6.93" y1="-4" x2="12.99" y2="-7.5" class="gear-stroke-2" stroke-width="3"/>
                                <line x1="6.93" y1="4" x2="12.99" y2="7.5" class="gear-stroke-2" stroke-width="3"/>
                                <line x1="0" y1="8" x2="0" y2="15" class="gear-stroke-2" stroke-width="3"/>
                                <line x1="-6.93" y1="4" x2="-12.99" y2="7.5" class="gear-stroke-2" stroke-width="3"/>
                                <line x1="-6.93" y1="-4" x2="-12.99" y2="-7.5" class="gear-stroke-2" stroke-width="3"/>
                            </g>
                            
                            <!-- Scanning beams -->
                            <line x1="145" y1="30" x2="170" y2="20" class="scan-beam" stroke-width="2.5" stroke-dasharray="3 3" opacity="0.7"/>
                            <line x1="145" y1="50" x2="175" y2="50" class="scan-beam" stroke-width="2.5" stroke-dasharray="3 3" opacity="0.7"/>
                            <line x1="145" y1="70" x2="170" y2="80" class="scan-beam" stroke-width="2.5" stroke-dasharray="3 3" opacity="0.7"/>
                        </g>
                        
                        <!-- YAML Workflow sheets flying out -->
                        <g transform="translate(540, 490)">
                            <g transform="rotate(-5 20 25)">
                                <rect x="0" y="0" width="38" height="48" fill="#fff" class="platform-stroke" stroke-width="2.5" rx="3"/>
                                <circle cx="19" cy="28" r="10" fill="url(#yellowGradient)" class="platform-stroke" stroke-width="2"/>
                                <text x="19" y="33" font-size="12" class="folder-text" text-anchor="middle">⚙</text>
                            </g>
                        </g>
                        
                        <!-- DevOps Tool Icons -->
                        <g transform="translate(360, 630)">
                            <!-- Docker -->
                            <g>
                                <circle cx="20" cy="20" r="18" fill="#fff" class="platform-stroke" stroke-width="2.5"/>
                                <rect x="10" y="16" width="20" height="12" fill="#2496ed" class="platform-stroke" stroke-width="1.5" rx="2"/>
                            </g>
                            
                            <!-- Kubernetes -->
                            <g transform="translate(50, 0)">
                                <circle cx="20" cy="20" r="18" fill="#fff" class="platform-stroke" stroke-width="2.5"/>
                                <polygon points="20,12 25,20 20,28 15,20" fill="#326ce5" class="platform-stroke" stroke-width="1.5"/>
                            </g>
                            
                            <!-- Jenkins -->
                            <g transform="translate(100, 0)">
                                <circle cx="20" cy="20" r="18" fill="#fff" class="platform-stroke" stroke-width="2.5"/>
                                <circle cx="20" cy="22" r="10" fill="#d24939" class="platform-stroke" stroke-width="1.5"/>
                            </g>
                        </g>
                        
                        <!-- Labels -->
                        <text x="340" y="760" font-size="13" class="stat-label" font-family="Comic Sans MS, cursive" font-style="italic">Auto-fetch GitHub Actions workflows</text>
                    </g>

                    <!-- SECTION 3: Analyze Now -->
                    <g id="section3" filter="url(#heavyShadow)">
                        <ellipse cx="820" cy="595" rx="100" ry="25" class="platform-shadow-light" opacity="0.5"/>
                        
                        <!-- Big 3D "Analyze Now" Button -->
                        <g transform="translate(740, 520)">
                            <rect x="0" y="0" width="160" height="60" fill="url(#pipelineGradient)" class="platform-stroke" stroke-width="4" rx="12"/>
                            <rect x="10" y="0" width="70" height="45" fill="#fff" opacity="0.25" rx="8"/>
                            <text x="80" y="38" font-size="20" fill="#fff" font-family="Arial Black" text-anchor="middle">Analyze Now</text>
                            
                            <!-- Motion lines -->
                            <line x1="-20" y1="10" x2="-8" y2="10" class="folder-text" stroke-width="3" stroke-linecap="round"/>
                            <line x1="-20" y1="30" x2="-8" y2="30" class="folder-text" stroke-width="3" stroke-linecap="round"/>
                            <line x1="-20" y1="50" x2="-8" y2="50" class="folder-text" stroke-width="3" stroke-linecap="round"/>
                        </g>
                        
                        <!-- Processing engine layers -->
                        <g transform="translate(750, 400)">
                            <g>
                                <rect x="20" y="0" width="130" height="28" class="stat-box-1" stroke-width="2.5" rx="5"/>
                                <text x="85" y="18" font-size="11" class="folder-text" font-family="Arial" text-anchor="middle">📄 Parse YAMLs</text>
                            </g>
                            <g transform="translate(-10, 35)">
                                <rect x="20" y="0" width="130" height="28" class="stat-box-1" stroke-width="2.5" rx="5"/>
                                <text x="85" y="18" font-size="11" class="folder-text" font-family="Arial" text-anchor="middle">🔍 Detect tools</text>
                            </g>
                            <g transform="translate(-20, 70)">
                                <rect x="20" y="0" width="130" height="28" class="stat-box-1" stroke-width="2.5" rx="5"/>
                                <text x="85" y="18" font-size="11" class="folder-text" font-family="Arial" text-anchor="middle">🛡️ Check protection</text>
                            </g>
                        </g>
                        
                        <text x="960" y="440" font-size="11" class="stat-label" font-family="Comic Sans MS, cursive" font-style="italic">Calculate DSOMM</text>
                    </g>

                    <!-- SECTION 4: Results Dashboard -->
                    <g id="section4" filter="url(#heavyShadow)">
                        <ellipse cx="1180" cy="555" rx="140" ry="30" class="platform-shadow-light" opacity="0.5"/>
                        
                        <g transform="translate(1050, 350)">
                            <!-- Dashboard 3D window -->
                            <rect x="0" y="0" width="260" height="190" class="dashboard-box" stroke-width="4" rx="10"/>
                            <path d="M 0,0 L 10,-10 L 270,-10 L 260,0 Z" class="dashboard-top" stroke-width="4"/>
                            <path d="M 260,0 L 270,-10 L 270,180 L 260,190 Z" class="dashboard-side" stroke-width="4"/>
                            
                            <!-- Shine highlight -->
                            <rect x="8" y="8" width="80" height="130" fill="#fff" opacity="0.1" rx="6"/>
                            
                            <!-- Header bar -->
                            <rect x="10" y="10" width="240" height="32" fill="url(#pipelineGradient)" class="dashboard-header-stroke" stroke-width="2" rx="6"/>
                            <circle cx="22" cy="26" r="4" fill="#fff" opacity="0.8"/>
                            <circle cx="34" cy="26" r="4" fill="#fff" opacity="0.8"/>
                            <circle cx="46" cy="26" r="4" fill="#fff" opacity="0.8"/>
                            <text x="130" y="32" font-size="14" fill="#fff" font-family="Arial" text-anchor="middle">Results Dashboard</text>
                            
                            <!-- Stats cards -->
                            <g transform="translate(15, 52)">
                                <rect x="0" y="0" width="70" height="52" class="stat-box-1" stroke-width="2" rx="6"/>
                                <rect x="0" y="0" width="70" height="5" class="stat-top-1" stroke-width="2" rx="6"/>
                                <text x="35" y="30" font-size="22" class="stat-text" font-family="Arial Black" text-anchor="middle">23</text>
                                <text x="35" y="46" font-size="10" class="stat-label" font-family="Arial" text-anchor="middle">repos</text>
                                
                                <g transform="translate(80, 0)">
                                    <rect x="0" y="0" width="70" height="52" class="stat-box-2" stroke-width="2" rx="6"/>
                                    <rect x="0" y="0" width="70" height="5" class="stat-top-2" stroke-width="2" rx="6"/>
                                    <text x="35" y="30" font-size="22" class="stat-text" font-family="Arial Black" text-anchor="middle">142</text>
                                    <text x="35" y="46" font-size="10" class="stat-label" font-family="Arial" text-anchor="middle">findings</text>
                                </g>
                                
                                <g transform="translate(160, 0)">
                                    <rect x="0" y="0" width="70" height="52" class="stat-box-3" stroke-width="2" rx="6"/>
                                    <rect x="0" y="0" width="70" height="5" class="stat-top-3" stroke-width="2" rx="6"/>
                                    <text x="35" y="30" font-size="22" class="stat-text" font-family="Arial Black" text-anchor="middle">8</text>
                                    <text x="35" y="46" font-size="10" class="stat-label" font-family="Arial" text-anchor="middle">tools</text>
                                </g>
                            </g>
                            
                            <!-- DSOMM Radar -->
                            <g transform="translate(45, 125)">
                                <polygon points="25,5 38,20 25,35 12,20" fill="none" class="platform-stroke" stroke-width="1.5"/>
                                <polygon points="25,10 33,20 25,30 17,20" class="stat-box-1" opacity="0.8"/>
                                <text x="25" y="48" font-size="9" class="stat-label" font-family="Arial" text-anchor="middle">DSOMM</text>
                            </g>
                            
                            <!-- Repository list -->
                            <g transform="translate(100, 118)">
                                <rect x="0" y="0" width="135" height="12" class="dashboard-top" stroke-width="1.5" rx="3"/>
                                <circle cx="6" cy="6" r="3" fill="#fbbf24"/>
                                
                                <rect x="0" y="16" width="135" height="12" class="dashboard-top" stroke-width="1.5" rx="3"/>
                                <circle cx="6" cy="22" r="3" fill="#ef4444"/>
                                
                                <rect x="0" y="32" width="135" height="12" class="dashboard-top" stroke-width="1.5" rx="3"/>
                                <circle cx="6" cy="38" r="3" fill="#22c55e"/>
                            </g>
                        </g>
                        
                        <!-- Stick figure pointing -->
                        <g transform="translate(1020, 470)">
                            <circle cx="0" cy="0" r="6" class="folder-text"/>
                            <line x1="0" y1="6" x2="0" y2="20" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="10" x2="-7" y2="15" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="10" x2="12" y2="8" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="20" x2="-5" y2="32" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="20" x2="5" y2="32" class="folder-text" stroke-width="2"/>
                        </g>
                        
                        <text x="1060" y="570" font-size="13" class="stat-label" font-family="Comic Sans MS, cursive" font-style="italic">• Overview  • DSOMM Levels</text>
                    </g>

                    <!-- SECTION 5: Action Cards -->
                    <g id="section5" filter="url(#heavyShadow)">
                        <ellipse cx="1480" cy="575" rx="120" ry="28" class="platform-shadow-light" opacity="0.5"/>
                        
                        <g transform="translate(1380, 440)">
                            <!-- Card 1: Add CodeQL -->
                            <g transform="rotate(-4 55 50)">
                                <rect x="0" y="0" width="105" height="85" fill="#fef08a" class="platform-stroke" stroke-width="3" rx="3"/>
                                <rect x="45" y="-8" width="15" height="12" fill="#94a3b8" opacity="0.6" rx="2"/>
                                <text x="52" y="28" font-size="13" class="folder-text" font-family="Comic Sans MS, cursive" text-anchor="middle">Add CodeQL</text>
                                <text x="52" y="45" font-size="13" class="folder-text" font-family="Comic Sans MS, cursive" text-anchor="middle">to 15 repos</text>
                                <text x="52" y="68" font-size="10" fill="#dc2626" font-family="Comic Sans MS, cursive" text-anchor="middle">✓ Priority: High</text>
                            </g>
                            
                            <!-- Card 2: Branch protection -->
                            <g transform="translate(115, -5) rotate(3 55 50)">
                                <rect x="0" y="0" width="105" height="85" fill="#bfdbfe" class="platform-stroke" stroke-width="3" rx="3"/>
                                <rect x="45" y="-8" width="15" height="12" fill="#94a3b8" opacity="0.6" rx="2"/>
                                <text x="52" y="28" font-size="12" class="folder-text" font-family="Comic Sans MS, cursive" text-anchor="middle">Enable branch</text>
                                <text x="52" y="45" font-size="12" class="folder-text" font-family="Comic Sans MS, cursive" text-anchor="middle">protection</text>
                            </g>
                            
                            <!-- Card 3: Pin versions -->
                            <g transform="translate(0, 95) rotate(2 55 50)">
                                <rect x="0" y="0" width="105" height="85" fill="#d9f99d" class="platform-stroke" stroke-width="3" rx="3"/>
                                <rect x="45" y="-8" width="15" height="12" fill="#94a3b8" opacity="0.6" rx="2"/>
                                <text x="52" y="26" font-size="11" class="folder-text" font-family="Comic Sans MS, cursive" text-anchor="middle">Pin GitHub</text>
                                <text x="52" y="41" font-size="11" class="folder-text" font-family="Comic Sans MS, cursive" text-anchor="middle">Actions versions</text>
                            </g>
                            
                            <!-- Card 4: Reusable workflows -->
                            <g transform="translate(115, 95) rotate(-3 55 50)">
                                <rect x="0" y="0" width="105" height="85" fill="#fecaca" class="platform-stroke" stroke-width="3" rx="3"/>
                                <rect x="45" y="-8" width="15" height="12" fill="#94a3b8" opacity="0.6" rx="2"/>
                                <text x="52" y="26" font-size="11" class="folder-text" font-family="Comic Sans MS, cursive" text-anchor="middle">Create reusable</text>
                                <text x="52" y="41" font-size="11" class="folder-text" font-family="Comic Sans MS, cursive" text-anchor="middle">workflows</text>
                            </g>
                        </g>
                        
                        <text x="1410" y="400" font-size="15" class="stat-label" font-family="Comic Sans MS, cursive" font-style="italic">Taking Action</text>
                    </g>

                    <!-- SECTION 6: Transformation Trophy -->
                    <g id="section6" filter="url(#heavyShadow)">
                        <ellipse cx="1820" cy="370" rx="100" ry="25" class="platform-shadow-light" opacity="0.5"/>
                        
                        <g transform="translate(1770, 240)">
                            <!-- 3D Trophy -->
                            <rect x="35" y="70" width="40" height="12" fill="url(#yellowGradient)" class="trophy-stroke" stroke-width="2.5" rx="2"/>
                            <path d="M 30,70 L 80,70 L 75,82 L 35,82 Z" class="trophy-base-side" stroke-width="2.5"/>
                            <rect x="40" y="82" width="30" height="8" class="trophy-base-bottom" stroke-width="2.5"/>
                            
                            <!-- Trophy cup body -->
                            <path d="M 42,32 L 37,70 L 73,70 L 68,32 Z" fill="url(#yellowGradient)" class="trophy-stroke" stroke-width="3"/>
                            <ellipse cx="55" cy="32" rx="13" ry="7" class="trophy-top" stroke-width="3"/>
                            
                            <!-- Trophy handles -->
                            <path d="M 37,42 Q 20,42 20,52 Q 20,58 26,58 L 37,56" fill="none" class="trophy-stroke" stroke-width="3"/>
                            <path d="M 73,42 Q 90,42 90,52 Q 90,58 84,58 L 73,56" fill="none" class="trophy-stroke" stroke-width="3"/>
                            
                            <!-- Shine -->
                            <ellipse cx="50" cy="50" rx="8" ry="15" fill="#fff" opacity="0.3"/>
                            <text x="55" y="56" font-size="22" fill="#fff" text-anchor="middle">⭐</text>
                        </g>
                        
                        <!-- DSOMM Score improvement bars -->
                        <g transform="translate(1760, 130)">
                            <!-- Before bar -->
                            <g>
                                <rect x="0" y="50" width="28" height="50" fill="#fee2e2" class="platform-stroke" stroke-width="3" rx="4"/>
                                <text x="14" y="112" font-size="13" class="folder-text" font-family="Arial Black" text-anchor="middle">47</text>
                            </g>
                            
                            <!-- Arrow -->
                            <text x="50" y="78" font-size="16" class="folder-text" text-anchor="middle">→</text>
                            
                            <!-- After bar (taller, green) -->
                            <g transform="translate(70, 0)">
                                <rect x="0" y="20" width="28" height="80" fill="url(#greenGradient)" class="platform-stroke" stroke-width="3" rx="4"/>
                                <text x="14" y="112" font-size="13" class="folder-text" font-family="Arial Black" text-anchor="middle">73</text>
                                
                                <!-- Level badge -->
                                <rect x="-8" y="0" width="44" height="14" fill="#22c55e" class="platform-stroke" stroke-width="2" rx="7"/>
                                <text x="14" y="10" font-size="9" fill="#fff" font-family="Arial Black" text-anchor="middle">Lvl 2-3</text>
                            </g>
                        </g>
                        
                        <!-- Celebration elements -->
                        <g transform="translate(1750, 200)">
                            <text x="0" y="0" font-size="26" fill="#fbbf24">✨</text>
                            <text x="140" y="10" font-size="26" fill="#fbbf24">✨</text>
                            <text x="50" y="-20" font-size="22" fill="#f59e0b">🎉</text>
                            <text x="100" y="70" font-size="22" fill="#f59e0b">🎉</text>
                            
                            <!-- Confetti particles -->
                            <circle cx="20" cy="30" r="4" fill="#ef4444"/>
                            <circle cx="120" cy="20" r="4" fill="#3b82f6"/>
                            <circle cx="40" cy="80" r="4" fill="#22c55e"/>
                            <circle cx="130" cy="60" r="4" fill="#fbbf24"/>
                            <circle cx="70" cy="40" r="4" fill="#a855f7"/>
                            <circle cx="90" cy="85" r="4" fill="#ec4899"/>
                        </g>
                        
                        <!-- Stick figure celebrating -->
                        <g transform="translate(1740, 340)">
                            <circle cx="0" cy="0" r="6" class="folder-text"/>
                            <line x1="0" y1="6" x2="0" y2="20" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="10" x2="-10" y2="2" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="10" x2="10" y2="2" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="20" x2="-6" y2="32" class="folder-text" stroke-width="2"/>
                            <line x1="0" y1="20" x2="6" y2="32" class="folder-text" stroke-width="2"/>
                        </g>
                        
                        <!-- Labels -->
                        <text x="1760" y="390" font-size="15" fill="#16a34a" font-family="Comic Sans MS, cursive" font-style="italic">Score improved from 47 → 73</text>
                        <text x="1780" y="410" font-size="13" fill="#22c55e" font-family="Comic Sans MS, cursive" font-style="italic">Security posture enhanced! 🎯</text>
                    </g>

                    <!-- Connecting arrows -->
                    <path d="M 280,685 Q 310,670 340,650" class="connector-arrow" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#arrow)" opacity="0.6"/>
                    <path d="M 650,590 Q 700,580 740,570" class="connector-arrow" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#arrow)" opacity="0.6"/>
                    <path d="M 920,545 L 1040,530" class="connector-arrow" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#arrow)" opacity="0.6"/>
                    <path d="M 1310,490 Q 1350,480 1380,475" class="connector-arrow" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#arrow)" opacity="0.6"/>
                    <path d="M 1340,505 L 1390,490" class="connector-arrow" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#arrow)" opacity="0.6"/>
                    <path d="M 1540,510 Q 1640,440 1720,380" class="connector-arrow" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#arrow)" opacity="0.6"/>
                    
                    <!-- Additional motion lines -->
                    <path d="M 180,730 Q 250,690 320,665" class="flow-line" stroke-width="1.5" stroke-dasharray="4 8" opacity="0.4"/>
                    <path d="M 520,615 Q 620,595 720,585" class="flow-line" stroke-width="1.5" stroke-dasharray="4 8" opacity="0.4"/>
                    <path d="M 1050,560 Q 1150,550 1250,535" class="flow-line" stroke-width="1.5" stroke-dasharray="4 8" opacity="0.4"/>
                    <path d="M 1550,495 Q 1650,455 1750,405" class="flow-line" stroke-width="1.5" stroke-dasharray="4 8" opacity="0.4"/>
                </svg>
            </div>

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
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p class="error-message">{error}</p>
                    </div>
                {:else if repoTreeData.length === 0}
                    <div class="empty-state">
                        <div class="empty-icon">
                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                            </svg>
                        </div>
                        <h3 class="empty-title">No repositories organized yet</h3>
                        <p class="empty-description">Start by creating a folder and adding repositories from your organization</p>
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
                                            onclick={() => toggleNode(node)}
                                            class="expand-button"
                                            aria-label={expandedNodes.has(node.id) ? 'Collapse folder' : 'Expand folder'}
                                        >
                                            {#if expandedNodes.has(node.id)}
                                                <svg class="expand-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                                </svg>
                                            {:else}
                                                <svg class="expand-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                                </svg>
                                            {/if}
                                        </button>
                                        
                                        <svg class="folder-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
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
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                                </svg>
                                            </button>
                                            <button
                                                onclick={() => startEditing(node)}
                                                class="action-icon"
                                                title="Rename"
                                                aria-label="Rename folder"
                                            >
                                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                </svg>
                                            </button>
                                            <button
                                                onclick={() => openNewFolderModal(node)}
                                                class="action-icon"
                                                title="Add subfolder"
                                                aria-label="Add subfolder"
                                            >
                                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                </svg>
                                            </button>
                                            <button
                                                onclick={() => deleteNode(node)}
                                                class="action-icon delete"
                                                title="Delete"
                                                aria-label="Delete folder"
                                            >
                                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                    
                                    {#if expandedNodes.has(node.id) && node.children}
                                        <div class="folder-children">
                                            {#each node.children as child}
                                                {#if child.type === 'repository'}
                                                    <div class="repo-item">
                                                        <svg class="repo-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                                                        </svg>
                                                        <span class="repo-name">{child.name}</span>
                                                        {#if child.metadata?.private}
                                                            <span class="repo-badge private">Private</span>
                                                        {/if}
                                                        {#if child.children}
                                                            <span class="workflow-count">({child.children.length} workflows)</span>
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
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
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
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
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
    <div class="modal-backdrop" onclick={closeNewFolderModal} onkeydown={(e) => e.key === 'Escape' && closeNewFolderModal()} role="button" tabindex="0">
        <div class="modal-container" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" tabindex="-1">
            <div class="modal-header">
                <h3 class="modal-title">Create New Folder</h3>
                <button onclick={closeNewFolderModal} class="modal-close" aria-label="Close modal">
                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
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
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p class="info-text">
                            Creating subfolder in: <span class="highlight">{newFolderParent.name}</span>
                        </p>
                    </div>
                {/if}
            </div>
            
            <div class="modal-footer">
                <button onclick={closeNewFolderModal} class="btn-secondary">
                    Cancel
                </button>
                <button
                    onclick={createNewFolder}
                    disabled={!newFolderName.trim()}
                    class="btn-primary"
                >
                    <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                    Create Folder
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- Add Repository Modal -->
{#if showAddRepoModal}
    <div class="modal-backdrop" onclick={closeAddRepoModal} onkeydown={(e) => e.key === 'Escape' && closeAddRepoModal()} role="button" tabindex="0">
        <div class="modal-container large" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" tabindex="-1">
            <div class="modal-header">
                <div>
                    <h3 class="modal-title">Add Repository to Tree</h3>
                    <p class="modal-subtitle">Select a repository and a folder to organize it</p>
                </div>
                <button onclick={closeAddRepoModal} class="modal-close" aria-label="Close modal">
                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
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
                                        onclick={() => selectedRepoToAdd = repo}
                                        class="selection-item {selectedRepoToAdd?.name === repo.name ? 'selected' : ''}"
                                    >
                                        <div class="item-content">
                                            <div class="item-header">
                                                <span class="item-name">{repo.name}</span>
                                                {#if selectedRepoToAdd?.name === repo.name}
                                                    <svg class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
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
                                        onclick={() => selectedNode = folder}
                                        class="selection-item {selectedNode?.id === folder.id ? 'selected' : ''}"
                                        style="padding-left: {0.75 + folder.depth * 1}rem"
                                    >
                                        <svg class="folder-icon-small" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                        </svg>
                                        <span class="item-name">{folder.name}</span>
                                        {#if selectedNode?.id === folder.id}
                                            <svg class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                            </svg>
                                        {/if}
                                    </button>
                                {/each}
                            </div>
                        {/if}
                        
                        {#if selectedRepoToAdd && selectedNode}
                            <div class="selection-summary">
                                <svg class="summary-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
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
                <button onclick={closeAddRepoModal} class="btn-secondary">
                    Cancel
                </button>
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
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
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
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <div class="modal-body">
                {#if folderToAnalyze}
                    <div class="folder-info">
                        <div class="info-row">
                            <svg class="folder-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                            </svg>
                            <div class="info-text">
                                <span class="label">Folder Name:</span>
                                <span class="value">{folderToAnalyze.name}</span>
                            </div>
                        </div>
                        
                        <div class="info-row">
                            <svg class="path-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <div class="info-text">
                                <span class="label">Path:</span>
                                <span class="value">{getFolderPath(folderToAnalyze)}</span>
                            </div>
                        </div>
                        
                        <div class="info-row">
                            <svg class="repo-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
                            </svg>
                            <div class="info-text">
                                <span class="label">Repositories:</span>
                                <span class="value badge">{countRepositoriesInFolder(folderToAnalyze)}</span>
                            </div>
                        </div>
                    </div>

                    <div class="options">
                        <label class="checkbox-label">
                            <input
                                type="checkbox"
                                bind:checked={includeSubfolders}
                                disabled={analyzingFolder}
                            />
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
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>This will analyze {includeSubfolders ? 'this folder and all subfolders' : 'only repositories directly in this folder'} using the OWASP DSOMM framework.</span>
                        </div>
                    {/if}
                {/if}
            </div>

            <div class="modal-footer">
                <button
                    onclick={closeAnalyzeFolderModal}
                    disabled={analyzingFolder}
                    class="btn-secondary"
                >
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
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        <span>Start Analysis</span>
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Global Variables */
    .treeview-container {
        --bg-primary: #000000;
        --bg-secondary: #0A0A0A;
        --text-primary: #FFFFFF;
        --text-secondary: #CCCCCC;
        --text-muted: #888888;
        --border-color: rgba(74, 158, 255, 0.2);
        --card-bg: rgba(15, 15, 15, 0.8);
        --primary-color: #4A9EFF;
        --accent-color: #FF8B4A;
        --success-color: #16A34A;
        --error-color: #FF4757;
        --warning-color: #F59E0B;
        
        min-height: 100vh;
        background: var(--bg-primary);
        color: var(--text-primary);
        position: relative;
    }

    .treeview-container.light {
        --bg-primary: #F8FAFC;
        --bg-secondary: #FFFFFF;
        --text-primary: #1E293B;
        --text-secondary: #475569;
        --text-muted: #94A3B8;
        --border-color: rgba(9, 105, 218, 0.2);
        --card-bg: rgba(255, 255, 255, 0.8);
        --primary-color: #0969DA;
        --accent-color: #D97706;
    }

    /* Top Navigation Bar */
    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 1000;
        background: rgba(0, 0, 0, 0.95);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid var(--border-color);
        padding: 1rem 2rem;
        transition: all 0.3s ease;
    }

    .treeview-container.light .top-navbar {
        background: rgba(255, 255, 255, 0.95);
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

    /* Brand Section */
    .brand-section {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .brand-icon {
        width: 36px;
        height: 36px;
        filter: drop-shadow(0 0 15px var(--primary-color));
    }

    .brand-text {
        display: flex;
        flex-direction: column;
    }

    .brand-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--primary-color);
        line-height: 1;
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
    }

    .breadcrumb-link:hover {
        color: var(--primary-color);
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
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid var(--border-color);
        color: var(--primary-color);
        padding: 0.75rem;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }

    .theme-toggle:hover {
        background: rgba(74, 158, 255, 0.2);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3);
    }

    .theme-icon {
        width: 20px;
        height: 20px;
        display: block;
    }

    /* Main Layout */
    .main-layout {
        display: flex;
        margin-top: 80px;
        min-height: calc(100vh - 80px);
    }

    /* Left Sidebar */
    .left-sidebar {
        position: fixed;
        left: 0;
        top: 80px;
        width: 280px;
        height: calc(100vh - 80px);
        background: linear-gradient(145deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%);
        border-right: 1px solid var(--border-color);
        backdrop-filter: blur(20px);
        padding: 1.5rem;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    /* Back Button */
    .back-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        background: rgba(74, 158, 255, 0.1);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        color: var(--text-primary);
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 0.9rem;
        font-weight: 500;
    }

    .back-button:hover {
        background: rgba(74, 158, 255, 0.2);
        transform: translateX(-4px);
    }

    .back-icon {
        width: 18px;
        height: 18px;
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

    /* Stat Cards */
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
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.05) 0%, rgba(255, 139, 74, 0.02) 100%);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        transition: all 0.3s ease;
    }

    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(74, 158, 255, 0.15);
        border-color: var(--primary-color);
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
        color: var(--primary-color);
        line-height: 1;
    }

    .stat-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
    }

    /* Action Buttons */
    .sidebar-actions {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .action-button {
        padding: 0;
        border: 1px solid transparent;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        background: transparent;
    }

    .action-button::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 12px;
        padding: 1px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        mask-composite: exclude;
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .action-button:hover::before {
        opacity: 1;
    }

    .button-content {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        position: relative;
        z-index: 1;
    }

    .action-button.intelligence {
        background: linear-gradient(135deg, 
            rgba(147, 51, 234, 0.15) 0%, 
            rgba(124, 58, 237, 0.1) 100%
        );
        border-color: rgba(147, 51, 234, 0.3);
    }

    .action-button.intelligence:hover {
        background: linear-gradient(135deg, 
            rgba(147, 51, 234, 0.25) 0%, 
            rgba(124, 58, 237, 0.15) 100%
        );
        border-color: rgba(147, 51, 234, 0.5);
        box-shadow: 0 8px 24px rgba(147, 51, 234, 0.25), 
                    0 0 0 1px rgba(147, 51, 234, 0.1);
    }

    .action-button.new-folder {
        background: linear-gradient(135deg, 
            rgba(74, 158, 255, 0.15) 0%, 
            rgba(255, 139, 74, 0.1) 100%
        );
        border-color: rgba(74, 158, 255, 0.3);
    }

    .action-button.new-folder:hover {
        background: linear-gradient(135deg, 
            rgba(74, 158, 255, 0.25) 0%, 
            rgba(255, 139, 74, 0.15) 100%
        );
        border-color: rgba(74, 158, 255, 0.5);
        box-shadow: 0 8px 24px rgba(74, 158, 255, 0.25), 
                    0 0 0 1px rgba(74, 158, 255, 0.1);
    }

    .action-button.add-repo {
        background: linear-gradient(135deg, 
            rgba(22, 163, 74, 0.15) 0%, 
            rgba(16, 185, 129, 0.1) 100%
        );
        border-color: rgba(22, 163, 74, 0.3);
    }

    .action-button.add-repo:hover {
        background: linear-gradient(135deg, 
            rgba(22, 163, 74, 0.25) 0%, 
            rgba(16, 185, 129, 0.15) 100%
        );
        border-color: rgba(22, 163, 74, 0.5);
        box-shadow: 0 8px 24px rgba(22, 163, 74, 0.25), 
                    0 0 0 1px rgba(22, 163, 74, 0.1);
    }

    .action-button:hover {
        transform: translateY(-2px);
    }

    .action-button:active {
        transform: translateY(0);
    }

    .button-icon {
        width: 20px;
        height: 20px;
        flex-shrink: 0;
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .action-button.intelligence .button-icon {
        color: #C084FC;
    }

    .action-button.new-folder .button-icon {
        color: var(--primary-color);
    }

    .action-button.add-repo .button-icon {
        color: #4ADE80;
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

    /* Save Status */
    .save-status {
        padding: 0.75rem;
        border-radius: 8px;
        font-size: 0.875rem;
        text-align: center;
    }

    .save-status.success {
        background: rgba(22, 163, 74, 0.1);
        color: var(--success-color);
        border: 1px solid rgba(22, 163, 74, 0.3);
    }

    .save-status.error {
        background: rgba(255, 71, 87, 0.1);
        color: var(--error-color);
        border: 1px solid rgba(255, 71, 87, 0.3);
    }

    /* Main Content */
    .main-content {
        margin-left: 280px;
        flex: 1;
        position: relative;
        min-height: calc(100vh - 80px);
    }

    .svg-background {
        position: absolute;
        inset: 0;
        pointer-events: none;
        opacity: 0.25;
        overflow: hidden;
    }

    .bg-svg {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    /* SVG Theme Styling */
    .treeview-container.dark .gradient-start { stop-color: #60a5fa; stop-opacity: 1; }
    .treeview-container.dark .gradient-mid { stop-color: #3b82f6; stop-opacity: 1; }
    .treeview-container.dark .gradient-end { stop-color: #2563eb; stop-opacity: 1; }
    .treeview-container.dark .highlight-start { stop-color: #93c5fd; stop-opacity: 0.9; }
    .treeview-container.dark .highlight-end { stop-color: #3b82f6; stop-opacity: 0; }
    .treeview-container.dark .platform-gradient-start { stop-color: #e2e8f0; stop-opacity: 1; }
    .treeview-container.dark .platform-gradient-end { stop-color: #cbd5e1; stop-opacity: 1; }
    .treeview-container.dark .blue-box-start { stop-color: #bfdbfe; stop-opacity: 1; }
    .treeview-container.dark .blue-box-end { stop-color: #93c5fd; stop-opacity: 1; }
    .treeview-container.dark .green-start { stop-color: #dcfce7; stop-opacity: 1; }
    .treeview-container.dark .green-end { stop-color: #bbf7d0; stop-opacity: 1; }
    .treeview-container.dark .yellow-start { stop-color: #fde68a; stop-opacity: 1; }
    .treeview-container.dark .yellow-end { stop-color: #fbbf24; stop-opacity: 1; }
    .treeview-container.dark .glow-start { stop-color: #93c5fd; stop-opacity: 0.6; }
    .treeview-container.dark .glow-end { stop-color: #3b82f6; stop-opacity: 0; }
    .treeview-container.dark .flow-line { stroke: #60a5fa; }
    .treeview-container.dark .pipeline-shadow { stroke: #1e293b; }
    .treeview-container.dark .pipeline-outline { stroke: #1e293b; }
    .treeview-container.dark .platform-shadow-dark { fill: #475569; }
    .treeview-container.dark .platform-shadow-light { fill: #64748b; }
    .treeview-container.dark .platform-stroke { stroke: #1e293b; }
    .treeview-container.dark .platform-side { fill: #cbd5e1; stroke: #1e293b; }
    .treeview-container.dark .folder-box-1 { fill: #93c5fd; stroke: #1e293b; }
    .treeview-container.dark .folder-box-2 { fill: #a5b4fc; stroke: #1e293b; }
    .treeview-container.dark .folder-box-3 { fill: #c4b5fd; stroke: #1e293b; }
    .treeview-container.dark .folder-top-1 { fill: #bfdbfe; stroke: #1e293b; }
    .treeview-container.dark .folder-top-2 { fill: #c7d2fe; stroke: #1e293b; }
    .treeview-container.dark .folder-top-3 { fill: #ddd6fe; stroke: #1e293b; }
    .treeview-container.dark .folder-right-1 { fill: #60a5fa; stroke: #1e293b; }
    .treeview-container.dark .folder-right-2 { fill: #818cf8; stroke: #1e293b; }
    .treeview-container.dark .folder-right-3 { fill: #a78bfa; stroke: #1e293b; }
    .treeview-container.dark .folder-text { fill: #1e293b; }
    .treeview-container.dark .machine-stroke { stroke: #1e293b; }
    .treeview-container.dark .machine-top-face { fill: #93c5fd; stroke: #1e293b; }
    .treeview-container.dark .machine-right-face { fill: #60a5fa; stroke: #1e293b; }
    .treeview-container.dark .gear-stroke-1 { stroke: #3b82f6; }
    .treeview-container.dark .gear-stroke-2 { stroke: #2563eb; }
    .treeview-container.dark .gear-fill-1 { fill: #3b82f6; }
    .treeview-container.dark .gear-fill-2 { fill: #2563eb; }
    .treeview-container.dark .scan-beam { stroke: #60a5fa; }
    .treeview-container.dark .dashboard-box { fill: #ffffff; stroke: #1e293b; }
    .treeview-container.dark .dashboard-top { fill: #f8fafc; stroke: #1e293b; }
    .treeview-container.dark .dashboard-side { fill: #e2e8f0; stroke: #1e293b; }
    .treeview-container.dark .dashboard-header-stroke { stroke: #1e293b; }
    .treeview-container.dark .stat-box-1 { fill: #dbeafe; stroke: #1e293b; }
    .treeview-container.dark .stat-box-2 { fill: #fee2e2; stroke: #1e293b; }
    .treeview-container.dark .stat-box-3 { fill: #dcfce7; stroke: #1e293b; }
    .treeview-container.dark .stat-top-1 { fill: #60a5fa; stroke: #1e293b; }
    .treeview-container.dark .stat-top-2 { fill: #ef4444; stroke: #1e293b; }
    .treeview-container.dark .stat-top-3 { fill: #16a34a; stroke: #1e293b; }
    .treeview-container.dark .stat-text { fill: #1e293b; }
    .treeview-container.dark .stat-label { fill: #475569; }
    .treeview-container.dark .trophy-stroke { stroke: #1e293b; }
    .treeview-container.dark .trophy-base-side { fill: #d97706; stroke: #1e293b; }
    .treeview-container.dark .trophy-base-bottom { fill: #b45309; stroke: #1e293b; }
    .treeview-container.dark .trophy-top { fill: #fde68a; stroke: #1e293b; }
    .treeview-container.dark .connector-arrow { stroke: #1e293b; }
    .treeview-container.dark .arrow-fill { fill: #1e293b; }

    /* Light mode SVG */
    .treeview-container.light .gradient-start { stop-color: #0969da; stop-opacity: 0.6; }
    .treeview-container.light .gradient-mid { stop-color: #0969da; stop-opacity: 0.8; }
    .treeview-container.light .gradient-end { stop-color: #0969da; stop-opacity: 0.6; }
    .treeview-container.light .highlight-start { stop-color: #60a5fa; stop-opacity: 0.5; }
    .treeview-container.light .highlight-end { stop-color: #0969da; stop-opacity: 0; }
    .treeview-container.light .platform-gradient-start { stop-color: #f1f5f9; stop-opacity: 1; }
    .treeview-container.light .platform-gradient-end { stop-color: #e2e8f0; stop-opacity: 1; }
    .treeview-container.light .blue-box-start { stop-color: #e0f2fe; stop-opacity: 1; }
    .treeview-container.light .blue-box-end { stop-color: #bfdbfe; stop-opacity: 1; }
    .treeview-container.light .green-start { stop-color: #dcfce7; stop-opacity: 1; }
    .treeview-container.light .green-end { stop-color: #bbf7d0; stop-opacity: 1; }
    .treeview-container.light .yellow-start { stop-color: #fde68a; stop-opacity: 1; }
    .treeview-container.light .yellow-end { stop-color: #fbbf24; stop-opacity: 1; }
    .treeview-container.light .glow-start { stop-color: #60a5fa; stop-opacity: 0.3; }
    .treeview-container.light .glow-end { stop-color: #0969da; stop-opacity: 0; }
    .treeview-container.light .flow-line { stroke: #0969da; }
    .treeview-container.light .pipeline-shadow { stroke: #64748b; }
    .treeview-container.light .pipeline-outline { stroke: #64748b; }
    .treeview-container.light .platform-shadow-dark { fill: #cbd5e1; }
    .treeview-container.light .platform-shadow-light { fill: #cbd5e1; }
    .treeview-container.light .platform-stroke { stroke: #64748b; }
    .treeview-container.light .platform-side { fill: #e2e8f0; stroke: #64748b; }
    .treeview-container.light .folder-box-1 { fill: #bfdbfe; stroke: #64748b; }
    .treeview-container.light .folder-box-2 { fill: #c7d2fe; stroke: #64748b; }
    .treeview-container.light .folder-box-3 { fill: #ddd6fe; stroke: #64748b; }
    .treeview-container.light .folder-top-1 { fill: #dbeafe; stroke: #64748b; }
    .treeview-container.light .folder-top-2 { fill: #e0e7ff; stroke: #64748b; }
    .treeview-container.light .folder-top-3 { fill: #ede9fe; stroke: #64748b; }
    .treeview-container.light .folder-right-1 { fill: #93c5fd; stroke: #64748b; }
    .treeview-container.light .folder-right-2 { fill: #a5b4fc; stroke: #64748b; }
    .treeview-container.light .folder-right-3 { fill: #c4b5fd; stroke: #64748b; }
    .treeview-container.light .folder-text { fill: #1e293b; }
    .treeview-container.light .machine-stroke { stroke: #64748b; }
    .treeview-container.light .machine-top-face { fill: #bfdbfe; stroke: #64748b; }
    .treeview-container.light .machine-right-face { fill: #93c5fd; stroke: #64748b; }
    .treeview-container.light .gear-stroke-1 { stroke: #0969da; }
    .treeview-container.light .gear-stroke-2 { stroke: #0969da; }
    .treeview-container.light .gear-fill-1 { fill: #0969da; }
    .treeview-container.light .gear-fill-2 { fill: #0969da; }
    .treeview-container.light .scan-beam { stroke: #60a5fa; }
    .treeview-container.light .dashboard-box { fill: #ffffff; stroke: #64748b; }
    .treeview-container.light .dashboard-top { fill: #f8fafc; stroke: #64748b; }
    .treeview-container.light .dashboard-side { fill: #e2e8f0; stroke: #64748b; }
    .treeview-container.light .dashboard-header-stroke { stroke: #64748b; }
    .treeview-container.light .stat-box-1 { fill: #dbeafe; stroke: #64748b; }
    .treeview-container.light .stat-box-2 { fill: #fee2e2; stroke: #64748b; }
    .treeview-container.light .stat-box-3 { fill: #dcfce7; stroke: #64748b; }
    .treeview-container.light .stat-top-1 { fill: #3b82f6; stroke: #64748b; }
    .treeview-container.light .stat-top-2 { fill: #dc2626; stroke: #64748b; }
    .treeview-container.light .stat-top-3 { fill: #16a34a; stroke: #64748b; }
    .treeview-container.light .stat-text { fill: #1e293b; }
    .treeview-container.light .stat-label { fill: #475569; }
    .treeview-container.light .trophy-stroke { stroke: #64748b; }
    .treeview-container.light .trophy-base-side { fill: #d97706; stroke: #64748b; }
    .treeview-container.light .trophy-base-bottom { fill: #b45309; stroke: #64748b; }
    .treeview-container.light .trophy-top { fill: #fde68a; stroke: #64748b; }
    .treeview-container.light .connector-arrow { stroke: #64748b; }
    .treeview-container.light .arrow-fill { fill: #64748b; }

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
        border: 4px solid rgba(74, 158, 255, 0.2);
        border-radius: 50%;
        border-top-color: var(--primary-color);
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
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

    /* Empty State */
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
        background: rgba(74, 158, 255, 0.1);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .empty-icon svg {
        width: 50px;
        height: 50px;
        color: var(--text-muted);
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
    }

    .empty-actions {
        display: flex;
        gap: 1rem;
    }

    .empty-button {
        padding: 1rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .empty-button.primary {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(74, 158, 255, 0.3);
    }

    .empty-button.secondary {
        background: transparent;
        color: var(--primary-color);
        border: 1px solid var(--border-color);
    }

    .empty-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(74, 158, 255, 0.4);
    }

    /* Folders Grid */
    .folders-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
        gap: 1.5rem;
    }

    /* Folder Card */
    .folder-card {
        background: linear-gradient(145deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        backdrop-filter: blur(20px);
        padding: 1.5rem;
        transition: all 0.3s ease;
    }

    .folder-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 35px rgba(74, 158, 255, 0.2);
        border-color: var(--primary-color);
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
        background: rgba(74, 158, 255, 0.1);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        color: var(--text-primary);
        font-size: 1.1rem;
        font-weight: 600;
        flex: 1;
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
    }

    /* Repo Item */
    .repo-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        background: rgba(147, 51, 234, 0.05);
        border: 1px solid rgba(147, 51, 234, 0.2);
        border-radius: 8px;
        transition: all 0.3s ease;
    }

    .repo-item:hover {
        background: rgba(147, 51, 234, 0.1);
        border-color: #9333EA;
    }

    .repo-icon {
        width: 20px;
        height: 20px;
        color: #9333EA;
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

    /* Modal Styles */
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

    @keyframes backdropFadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    .modal-container {
        background: linear-gradient(145deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid var(--border-color);
        border-radius: 20px;
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
        border-bottom: 1px solid var(--border-color);
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
        color: #ffffff !important;
        margin-top: 0.25rem;
        opacity: 0.9;
    }

    .modal-close {
        background: rgba(255, 71, 87, 0.1);
        border: 1px solid rgba(255, 71, 87, 0.2);
        color: var(--error-color);
        padding: 0.5rem;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .modal-close:hover {
        background: rgba(255, 71, 87, 0.2);
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
        background: rgba(74, 158, 255, 0.05);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        color: #ffffff !important;
        font-size: 1rem;
        transition: all 0.3s ease;
    }

    .form-input:focus {
        outline: none;
        border-color: var(--primary-color);
        background: rgba(74, 158, 255, 0.1);
        box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1);
    }

    .info-box {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        background: rgba(74, 158, 255, 0.1);
        border: 1px solid rgba(74, 158, 255, 0.2);
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
        color: var(--text-secondary);
        margin: 0;
    }

    .highlight {
        font-weight: 600;
        color: var(--primary-color);
    }

    .modal-footer {
        padding: 1.5rem 2rem;
        border-top: 1px solid var(--border-color);
        display: flex;
        gap: 1rem;
        justify-content: flex-end;
    }

    .btn-primary,
    .btn-secondary {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.875rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 0.95rem;
    }

    .btn-primary {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(74, 158, 255, 0.3);
    }

    .btn-primary:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(74, 158, 255, 0.4);
    }

    .btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-secondary {
        background: transparent;
        color: var(--text-secondary);
        border: 1px solid var(--border-color);
    }

    .btn-secondary:hover {
        background: rgba(74, 158, 255, 0.1);
        border-color: var(--primary-color);
        color: var(--primary-color);
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
        background: linear-gradient(145deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%);
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
        background: rgba(74, 158, 255, 0.05);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        transition: all 0.3s ease;
    }

    .info-row:hover {
        background: rgba(74, 158, 255, 0.1);
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
        color: var(--text-primary);
    }

    .badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.25rem 0.75rem;
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
        color: white;
        border-radius: 6px;
        font-size: 0.875rem;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(74, 158, 255, 0.3);
    }

    .options {
        margin-bottom: 1.5rem;
    }

    .checkbox-label {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        background: rgba(74, 158, 255, 0.05);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .checkbox-label:hover {
        background: rgba(74, 158, 255, 0.1);
        border-color: var(--primary-color);
    }

    .checkbox-label input[type="checkbox"] {
        width: 20px;
        height: 20px;
        cursor: pointer;
        accent-color: var(--primary-color);
    }

    .checkbox-label span {
        font-size: 0.95rem;
        color: var(--text-secondary);
        flex: 1;
    }

    .progress-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        padding: 2rem;
        background: rgba(74, 158, 255, 0.05);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }

    .progress-text {
        font-size: 0.95rem;
        color: var(--text-secondary);
        text-align: center;
        margin: 0;
    }

    .info-notice {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 1rem;
        background: rgba(74, 158, 255, 0.1);
        border: 1px solid rgba(74, 158, 255, 0.2);
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
        color: var(--text-secondary);
        line-height: 1.5;
    }

    /* Selection Grid */
    .selection-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
    }

    .selection-panel {
        background: rgba(74, 158, 255, 0.02);
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
        color: var(--text-primary);
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
        color: var(--text-muted);
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
        background: rgba(74, 158, 255, 0.1);
        border-color: var(--primary-color);
    }

    .selection-item.selected {
        background: rgba(74, 158, 255, 0.15);
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1);
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

    .item-description {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin: 0;
        line-height: 1.4;
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
    }
</style>
