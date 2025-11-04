<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { githubClient } from '$lib/github.js';
    import { repositoryTreeClient } from '$lib/repositoryTree.js';
    import { writable } from 'svelte/store';
    
    let orgName = '';
    let loading = false;
    let error = null;
    let saveStatus = '';
    let saveSuccess = false;
    
    // Dark mode state
    let isDarkMode = false;
    
    // Repository tree structure state
    let repoTreeData = [];
    let selectedNode = null;
    let expandedNodes = new Set();
    let editingNode = null;
    let editingValue = '';
    
    // Modal states
    let showNewFolderModal = false;
    let newFolderName = '';
    let newFolderParent = null;
    
    // Add Repository Modal
    let showAddRepoModal = false;
    let availableRepos = [];
    let selectedRepoToAdd = null;
    let addingRepo = false;
    let loadingRepos = false;
    
    // Statistics
    let statistics = {
        totalFolders: 0,
        totalRepos: 0,
        totalWorkflows: 0,
        privateRepos: 0,
        publicRepos: 0
    };
    
    onMount(async () => {
        orgName = $page.params.org;
        console.log(`🌲 Loading Repository Treeview for organization: ${orgName}`);
        
        // Check for saved theme preference
        isDarkMode = localStorage.getItem('theme') === 'dark';
        
        await loadRepoTreeData();
        await loadAvailableRepositories();
    });
    
    function toggleDarkMode() {
        isDarkMode = !isDarkMode;
        localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
    }
    
    async function loadRepoTreeData() {
        try {
            loading = true;
            error = null;
            
            const result = await repositoryTreeClient.getRepositoryTree(orgName);
            
            if (result.success) {
                repoTreeData = result.data || [];
                updateStatistics();
                console.log('✅ Repository tree data loaded:', repoTreeData);
            } else {
                console.warn('No existing repository tree data found, starting fresh');
                repoTreeData = [];
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
            saveStatus = 'Saving...';
            saveSuccess = false;
            
            const result = await repositoryTreeClient.saveRepositoryTree(orgName, repoTreeData);
            
            if (result.success) {
                saveStatus = 'Saved successfully!';
                saveSuccess = true;
                setTimeout(() => {
                    saveStatus = '';
                    saveSuccess = false;
                }, 3000);
            } else {
                throw new Error(result.error || 'Failed to save');
            }
        } catch (err) {
            console.error('Failed to save repository tree:', err);
            saveStatus = `Error: ${err.message}`;
            saveSuccess = false;
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
    
    function createNewFolder() {
        if (!newFolderName.trim()) return;
        
        const newFolder = {
            id: `folder-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            name: newFolderName.trim(),
            type: 'folder',
            children: [],
            created_at: new Date().toISOString()
        };
        
        if (newFolderParent) {
            if (!newFolderParent.children) {
                newFolderParent.children = [];
            }
            newFolderParent.children.push(newFolder);
        } else {
            repoTreeData.push(newFolder);
        }
        
        repoTreeData = [...repoTreeData];
        updateStatistics();
        saveRepoTreeData();
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
        notification.className = `fixed top-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg text-white ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 
            'bg-blue-500'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
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
</script>

<svelte:head>
    <title>Repository Treeview - {orgName} - WithOps</title>
</svelte:head>

<div class="min-h-screen bg-gray-50">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <header class="mb-8">
            <nav class="flex items-center space-x-2 text-sm text-gray-500 mb-4">
                <a href="/" class="hover:text-gray-700">Dashboard</a>
                <span>/</span>
                <a href="/organizations" class="hover:text-gray-700">Organizations</a>
                <span>/</span>
                <a href="/github/workspace/{orgName}" class="hover:text-gray-700">{orgName}</a>
                <span>/</span>
                <span class="text-gray-900">Repository Treeview</span>
            </nav>
            
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold text-gray-900 flex items-center space-x-3">
                        <span>📦 Repository Treeview</span>
                    </h1>
                    <p class="text-gray-600 mt-1">Organize and manage repositories with their workflows</p>
                </div>
                
                <div class="flex space-x-3">
                    <button 
                        on:click={() => goto(`/github/workspace/${orgName}`)}
                        class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 font-medium"
                    >
                        ← Back to Workspace
                    </button>
                   
                    <button 
                        on:click={openNewFolderModal}
                        class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
                    >
                        + New Folder
                    </button>
                    <button 
                        on:click={openAddRepoModal}
                        class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 font-medium"
                    >
                        + Add Repository
                    </button>
                </div>
            </div>
        </header>
        
        <!-- Statistics Dashboard -->
        <div class="bg-white shadow rounded-lg p-6 mb-6">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">Repository Overview</h2>
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div class="bg-blue-50 p-4 rounded-lg">
                    <h3 class="text-sm font-medium text-blue-900">Folders</h3>
                    <p class="text-2xl font-bold text-blue-600">{statistics.totalFolders}</p>
                </div>
                
                <div class="bg-purple-50 p-4 rounded-lg">
                    <h3 class="text-sm font-medium text-purple-900">Repositories</h3>
                    <p class="text-2xl font-bold text-purple-600">{statistics.totalRepos}</p>
                </div>
                
                <div class="bg-green-50 p-4 rounded-lg">
                    <h3 class="text-sm font-medium text-green-900">Workflows</h3>
                    <p class="text-2xl font-bold text-green-600">{statistics.totalWorkflows}</p>
                </div>
                
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h3 class="text-sm font-medium text-gray-900">Private</h3>
                    <p class="text-2xl font-bold text-gray-600">{statistics.privateRepos}</p>
                </div>
                
                <div class="bg-emerald-50 p-4 rounded-lg">
                    <h3 class="text-sm font-medium text-emerald-900">Public</h3>
                    <p class="text-2xl font-bold text-emerald-600">{statistics.publicRepos}</p>
                </div>
            </div>
            
            {#if saveStatus}
                <div class="mt-4 p-3 rounded {saveSuccess ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}">
                    {saveStatus}
                </div>
            {/if}
        </div>
        
        <!-- Main Content -->
        <div class="bg-white shadow rounded-lg p-6">
            {#if loading}
                <div class="flex items-center justify-center py-12">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span class="ml-3 text-gray-600">Loading repository tree...</span>
                </div>
            {:else if error}
                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p class="text-red-800">{error}</p>
                </div>
            {:else if repoTreeData.length === 0}
                <div class="text-center py-12">
                    <svg class="mx-auto h-16 w-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                    </svg>
                    <h3 class="mt-4 text-lg font-medium text-gray-900">No repositories organized yet</h3>
                    <p class="mt-2 text-sm text-gray-500">Start by creating a folder and adding repositories from your organization</p>
                    <div class="mt-6 flex justify-center space-x-3">
                        <button 
                            on:click={openNewFolderModal}
                            class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                        >
                            Create First Folder
                        </button>
                        <button 
                            on:click={openAddRepoModal}
                            class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                        >
                            Add Repository
                        </button>
                    </div>
                </div>
            {:else}
                <div class="space-y-2">
                    {#each repoTreeData as node}
                        <div class="border-b border-gray-100 last:border-0">
                            {#if node.type === 'folder'}
                                <div class="flex items-center py-2 px-3 hover:bg-gray-50 rounded {selectedNode?.id === node.id ? 'bg-blue-50' : ''}">
                                    <button 
                                        on:click={() => toggleNode(node)}
                                        class="mr-2 text-gray-500 hover:text-gray-700"
                                        aria-label={expandedNodes.has(node.id) ? 'Collapse folder' : 'Expand folder'}
                                    >
                                        {#if expandedNodes.has(node.id)}
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                            </svg>
                                        {:else}
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                            </svg>
                                        {/if}
                                    </button>
                                    
                                    <svg class="w-5 h-5 text-blue-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                    </svg>
                                    
                                    <button 
                                        on:click={() => selectNode(node)}
                                        class="flex-1 text-left"
                                    >
                                        {#if editingNode?.id === node.id}
                                            <input
                                                bind:value={editingValue}
                                                on:blur={saveEdit}
                                                on:keydown={(e) => e.key === 'Enter' && saveEdit()}
                                                class="px-2 py-1 border rounded"
                                            />
                                        {:else}
                                            <span class="font-medium text-gray-900">{node.name}</span>
                                            <span class="text-xs text-gray-500 ml-2">
                                                ({countItemsInNode(node)} items)
                                            </span>
                                        {/if}
                                    </button>
                                    
                                    <div class="flex space-x-2">
                                        <button
                                            on:click={() => startEditing(node)}
                                            class="text-gray-400 hover:text-gray-600"
                                            title="Rename"
                                            aria-label="Rename folder"
                                        >
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                            </svg>
                                        </button>
                                        <button
                                            on:click={() => openNewFolderModal(node)}
                                            class="text-blue-400 hover:text-blue-600"
                                            title="Add subfolder"
                                            aria-label="Add subfolder"
                                        >
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                            </svg>
                                        </button>
                                        <button
                                            on:click={() => deleteNode(node)}
                                            class="text-red-400 hover:text-red-600"
                                            title="Delete"
                                            aria-label="Delete folder"
                                        >
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                                
                                {#if expandedNodes.has(node.id) && node.children}
                                    <div class="ml-8">
                                        {#each node.children as child}
                                            {#if child.type === 'repository'}
                                                <div class="flex items-center py-2 px-3 hover:bg-gray-50 rounded border-l-2 border-purple-200">
                                                    <svg class="w-5 h-5 text-purple-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                                                    </svg>
                                                    <span class="font-medium text-gray-900">{child.name}</span>
                                                    {#if child.metadata?.private}
                                                        <span class="ml-2 px-2 py-0.5 text-xs bg-gray-100 text-gray-800 rounded">Private</span>
                                                    {/if}
                                                    {#if child.children}
                                                        <span class="ml-2 text-xs text-gray-500">
                                                            ({child.children.length} workflows)
                                                        </span>
                                                    {/if}
                                                    
                                                    <div class="ml-auto flex space-x-2">
                                                        {#if child.metadata?.html_url}
                                                            <a 
                                                                href={child.metadata.html_url} 
                                                                target="_blank"
                                                                class="text-gray-400 hover:text-gray-600"
                                                                title="Open in GitHub"
                                                                aria-label="Open repository in GitHub"
                                                            >
                                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                                </svg>
                                                            </a>
                                                        {/if}
                                                        <button
                                                            on:click={() => deleteNode(child)}
                                                            class="text-red-400 hover:text-red-600"
                                                            title="Remove"
                                                            aria-label="Remove repository"
                                                        >
                                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                            </svg>
                                                        </button>
                                                    </div>
                                                </div>
                                            {/if}
                                        {/each}
                                    </div>
                                {/if}
                            {/if}
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
</div>

<!-- New Folder Modal -->
{#if showNewFolderModal}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
        <div class="relative mx-auto p-6 border w-full max-w-md shadow-lg rounded-md bg-white">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-medium text-gray-900">Create New Folder</h3>
                <button 
                    on:click={closeNewFolderModal}
                    class="text-gray-400 hover:text-gray-600"
                    aria-label="Close modal"
                >
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            <div class="mb-4">
                <label for="folder-name" class="block text-sm font-medium text-gray-700 mb-2">
                    Folder Name
                </label>
                <input
                    id="folder-name"
                    bind:value={newFolderName}
                    placeholder="Enter folder name..."
                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    on:keypress={(e) => e.key === 'Enter' && createNewFolder()}
                />
            </div>
            
            {#if newFolderParent}
                <div class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded">
                    <p class="text-sm text-blue-800">
                        Creating subfolder in: <span class="font-medium">{newFolderParent.name}</span>
                    </p>
                </div>
            {/if}
            
            <div class="flex justify-end space-x-3">
                <button
                    on:click={closeNewFolderModal}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                >
                    Cancel
                </button>
                <button
                    on:click={createNewFolder}
                    disabled={!newFolderName.trim()}
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                    Create Folder
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- Add Repository Modal -->
{#if showAddRepoModal}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-10 mx-auto p-6 border w-full max-w-4xl shadow-lg rounded-md bg-white">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h3 class="text-lg font-medium text-gray-900">Add Repository to Tree</h3>
                    <p class="text-sm text-gray-600 mt-1">Select a repository and a folder to organize it</p>
                </div>
                <button 
                    on:click={closeAddRepoModal}
                    class="text-gray-400 hover:text-gray-600"
                    aria-label="Close modal"
                >
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Available Repositories -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h4 class="text-md font-medium text-gray-900 mb-4">📦 Available Repositories</h4>
                    
                    {#if loadingRepos}
                        <div class="flex items-center justify-center py-8">
                            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                            <span class="ml-2 text-gray-600">Loading repositories...</span>
                        </div>
                    {:else if availableRepos.length === 0}
                        <p class="text-sm text-gray-500">No repositories available</p>
                    {:else}
                        <div class="space-y-2 max-h-96 overflow-y-auto">
                            {#each availableRepos as repo}
                                <button
                                    on:click={() => selectedRepoToAdd = repo}
                                    class="w-full text-left p-3 border rounded hover:bg-white transition-colors {
                                        selectedRepoToAdd?.name === repo.name ? 'bg-blue-50 border-blue-500' : 'bg-white border-gray-200'
                                    }"
                                >
                                    <div class="flex items-center justify-between">
                                        <div class="flex-1">
                                            <div class="font-medium text-gray-900">{repo.name}</div>
                                            {#if repo.description}
                                                <p class="text-xs text-gray-500 mt-1">{repo.description}</p>
                                            {/if}
                                            <div class="flex items-center space-x-3 mt-2 text-xs text-gray-500">
                                                {#if repo.language}
                                                    <span class="flex items-center">
                                                        <span class="w-2 h-2 rounded-full bg-blue-500 mr-1"></span>
                                                        {repo.language}
                                                    </span>
                                                {/if}
                                                <span>{repo.workflow_count || 0} workflows</span>
                                                {#if repo.private}
                                                    <span class="px-2 py-0.5 bg-gray-100 text-gray-800 rounded">Private</span>
                                                {/if}
                                            </div>
                                        </div>
                                        {#if selectedRepoToAdd?.name === repo.name}
                                            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                            </svg>
                                        {/if}
                                    </div>
                                </button>
                            {/each}
                        </div>
                    {/if}
                </div>
                
                <!-- Folder Selection -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h4 class="text-md font-medium text-gray-900 mb-4">📁 Select Folder</h4>
                    
                    {#if repoTreeData.length === 0}
                        <div class="text-center py-8">
                            <p class="text-sm text-gray-500 mb-3">No folders created yet</p>
                            <button
                                on:click={() => {
                                    closeAddRepoModal();
                                    openNewFolderModal();
                                }}
                                class="text-sm text-blue-600 hover:text-blue-700"
                            >
                                Create your first folder
                            </button>
                        </div>
                    {:else}
                        <div class="space-y-2 max-h-96 overflow-y-auto">
                            {#each getFlattenedFolders(repoTreeData) as folder}
                                <button
                                    on:click={() => selectedNode = folder}
                                    class="w-full text-left p-3 border rounded hover:bg-white transition-colors {
                                        selectedNode?.id === folder.id ? 'bg-blue-50 border-blue-500' : 'bg-white border-gray-200'
                                    }"
                                >
                                    <div class="flex items-center" style="padding-left: {folder.depth * 16}px">
                                        <svg class="w-4 h-4 text-blue-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                        </svg>
                                        <span class="flex-1">{folder.name}</span>
                                        {#if selectedNode?.id === folder.id}
                                            <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                            </svg>
                                        {/if}
                                    </div>
                                </button>
                            {/each}
                        </div>
                    {/if}
                    
                    {#if selectedRepoToAdd && selectedNode}
                        <div class="mt-4 p-3 bg-green-50 border border-green-200 rounded">
                            <p class="text-sm text-green-800">
                                <span class="font-medium">{selectedRepoToAdd.name}</span> will be added to 
                                <span class="font-medium">{selectedNode.name}</span>
                            </p>
                        </div>
                    {/if}
                </div>
            </div>
            
            <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-200">
                <button
                    on:click={closeAddRepoModal}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                >
                    Cancel
                </button>
                <button
                    on:click={addRepositoryToTree}
                    disabled={!selectedRepoToAdd || !selectedNode || addingRepo}
                    class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
                >
                    {#if addingRepo}
                        <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Adding...</span>
                    {:else}
                        <span>Add Repository</span>
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}
