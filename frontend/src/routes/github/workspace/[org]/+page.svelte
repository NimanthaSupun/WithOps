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
    isDarkMode.subscribe(value => {
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
                
                error = orgsResult.error || "Authentication failed. Please try logging in again.";
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
            
            if (err.error_type === 'app_not_installed' ||
                (errorMessage.includes('app_not_installed') && !errorMessage.includes('network')) ||
                (errorMessage.includes('not installed') && errorMessage.includes('organization'))) {
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
                    result.push(...getFlattenedFolders(folder.children.filter(child => child.type === 'folder'), depth + 1));
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
            
            const workflowContentResult = await githubClient.getWorkflowContent(orgName, selectedWorkflowToAdd.repository, selectedWorkflowToAdd.path);
            
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
                const workflowContentResult = await githubClient.getWorkflowContent(orgName, selectedRepoToAdd.name, workflow.path);
                
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
            
            console.log(`✅ Repository "${selectedRepoToAdd.name}" with ${repoWorkflows.length} workflows added successfully!`);
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
    <!-- Professional Header -->
    <header class="workspace-header">
        <div class="header-content">
            <!-- Left side - Brand & Workspace -->
            <div class="header-left">
                <button 
                    onclick={toggleSidebar}
                    class="sidebar-toggle"
                    title="Toggle sidebar"
                    aria-label="Toggle sidebar navigation"
                >
                    <svg class="toggle-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                    </svg>
                </button>
                
                <div class="brand-section">
                    <div class="brand-icon-wrapper">
                        <img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
                        <div class="brand-glow"></div>
                    </div>
                    <div class="brand-text">
                        <span class="brand-name">WithOps</span>
                        <span class="brand-subtitle">DevSecOps Platform</span>
                    </div>
                </div>
                
                <div class="workspace-info">
                    <span class="workspace-label">Workspace:</span>
                    <span class="workspace-name">{orgName}</span>
                </div>
            </div>
            
            <!-- Right side - Status & Theme -->
            <div class="header-right">
                <!-- Live Status Indicator -->
                {#if workspaceData && !loading}
                    <div class="live-status">
                        <span class="status-dot"></span>
                        <span class="status-text">Live</span>
                        {#if lastSyncTime}
                            <span class="status-time">{lastSyncTime.toLocaleTimeString()}</span>
                        {/if}
                    </div>
                {/if}
                
                <!-- Theme Toggle -->
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
    </header>

    <!-- Sidebar Navigation -->
    <aside class="workspace-sidebar {sidebarCollapsed ? 'collapsed' : ''}">
        <nav class="sidebar-nav">
            <a 
                href="/dashboard"
                class="nav-item"
                title="Dashboard"
            >
                <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
                </svg>
                {#if !sidebarCollapsed}
                    <span class="nav-text">Dashboard</span>
                {/if}
            </a>
            
            <a 
                href="/organizations"
                class="nav-item"
                title="Organizations"
            >
                <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                </svg>
                {#if !sidebarCollapsed}
                    <span class="nav-text">Organizations</span>
                {/if}
            </a>
            
            <div class="nav-divider"></div>
               
            <a 
                href="/github/workspace/{orgName}/repo-treeview"
                class="nav-item"
                title="Repository Treeview"
            >
                <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"/>
                </svg>
                {#if !sidebarCollapsed}
                    <span class="nav-text">Repository Treeview</span>
                {/if}
            </a>
            
             <a 
                href="/github/workspace/{orgName}/threat-modeling"
                class="nav-item nav-item-danger"
                title="Threat Modeling"
            >
                <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                </svg>
                {#if !sidebarCollapsed}
                    <span class="nav-text">Threat Modeling</span>
                {/if}
            </a>

            <a 
                href="/github/workspace/{orgName}/audit"
                class="nav-item"
                title="Actions Audit"
            >
                <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                {#if !sidebarCollapsed}
                    <span class="nav-text">Actions Audit</span>
                {/if}
            </a>
            
            <a 
                href="/github/workspace/{orgName}/canvas"
                class="nav-item"
                title="Workflow Canvas"
            >
                <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>
                </svg>
                {#if !sidebarCollapsed}
                    <span class="nav-text">Workflow Canvas</span>
                {/if}
            </a>
            
           
              <a 
                href="/github/workspace/{orgName}/treeview"
                class="nav-item"
                title="Workflow Treeview"
            >
                <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z"/>
                </svg>
                {#if !sidebarCollapsed}
                    <span class="nav-text">Workflow Treeview</span>
                {/if}
            </a>


        </nav>
        
        {#if !sidebarCollapsed}
            <div class="sidebar-footer">
                <button 
                    onclick={forceRefresh}
                    disabled={refreshing}
                    class="refresh-button"
                >
                    <svg class="refresh-icon {refreshing ? 'spinning' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    <span>Refresh Data</span>
                </button>
            </div>
        {/if}
    </aside>

    <!-- Main Content Area -->
    <main class="workspace-main {sidebarCollapsed ? 'expanded' : ''}">
        {#if loading}
            <!-- Professional Loading State -->
            <div class="loading-state">
                <div class="loading-content">
                    <div class="loading-spinner"></div>
                    <h2 class="loading-title">Loading Workspace</h2>
                    <p class="loading-text">{loadingStage}</p>
                    <div class="loading-progress">
                        <div class="progress-bar"></div>
                    </div>
                </div>
            </div>
        {:else if error}
            <!-- Professional Error State -->
            <div class="error-state">
                <div class="error-content">
                    <div class="error-icon">
                        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                        </svg>
                    </div>
                    <h3 class="error-title">Unable to Load Workspace</h3>
                    <p class="error-message">{error}</p>
                    <div class="error-actions">
                        <button onclick={loadWorkspaceData} class="retry-button">
                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
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
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"/>
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
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
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
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
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
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
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
                        onclick={() => activeTab = 'repositories'}
                        class="tab-button {activeTab === 'repositories' ? 'active' : ''}"
                    >
                        <svg class="tab-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"/>
                        </svg>
                        <span>Repositories</span>
                        <span class="tab-badge">{workspaceData.repository_count || 0}</span>
                    </button>
                    <button
                        onclick={switchToWorkflowsTab}
                        class="tab-button {activeTab === 'workflows' ? 'active' : ''}"
                    >
                        <svg class="tab-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
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
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3.382a1 1 0 00-.894.553l-.448.894a1 1 0 01-.894.553H9a1 1 0 01-.894-.553l-.448-.894A1 1 0 006.764 7H3z"/>
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
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"/>
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
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
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
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
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
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                            </svg>
                                                            <span>Add Repository to Project</span>
                                                        </button>
                                                        
                                                        <a 
                                                            href={repo.html_url} 
                                                            target="_blank"
                                                            onclick={() => activeRepoMenu = null}
                                                            class="dropdown-item"
                                                        >
                                                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
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
                                                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                                                </svg>
                                                <span>{repo.stargazers_count}</span>
                                            </div>
                                            <div class="meta-item">
                                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"/>
                                                </svg>
                                                <span>{repo.forks_count}</span>
                                            </div>
                                            <div class="meta-item">
                                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
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
                                                                <span class="workflow-badge {workflow.state}">{workflow.state}</span>
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
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"/>
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
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
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
                                                        <span class="last-run-time">{formatRelativeTime(workflow.last_run.created_at)}</span>
                                                    {:else}
                                                        <span class="last-run-never">Never</span>
                                                    {/if}
                                                </td>
                                                <td>
                                                    {#if workflow.last_successful_run && workflow.last_successful_run.created_at}
                                                        <span class="last-run-time">{formatRelativeTime(workflow.last_successful_run.created_at)}</span>
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
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
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
                                                            onclick={() => toggleWorkflowActionMenu(`${workflow.id}-${workflow.repository}`)}
                                                            class="table-action-button"
                                                            aria-label="Workflow actions"
                                                        >
                                                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"/>
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
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                                                                    </svg>
                                                                    <span>View YAML</span>
                                                                </button>
                                                                <button 
                                                                    onclick={() => {
                                                                        goto(`/github/workspace/${orgName}/canvas?repo=${workflow.repository}&workflow=${encodeURIComponent(workflow.name)}`);
                                                                        activeWorkflowMenu = null;
                                                                    }}
                                                                    class="dropdown-item"
                                                                >
                                                                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
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
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                                    </svg>
                                                                    <span>Add to Project</span>
                                                                </button>
                                                                {#if workflow.html_url}
                                                                    <a 
                                                                        href={workflow.html_url} 
                                                                        target="_blank"
                                                                        onclick={() => activeWorkflowMenu = null}
                                                                        class="dropdown-item"
                                                                    >
                                                                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
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
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                                </svg>
                                <h3 class="empty-title">No Workflows Found</h3>
                                <p class="empty-message">No GitHub Actions workflows configured in this organization.</p>
                            </div>
                        {/if}
                    {/if}
                </div>
            </div>
        {/if}
    </main>
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
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
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
                        <p>Adding: <strong>{selectedWorkflowToAdd.name}</strong> from <strong>{selectedWorkflowToAdd.repository}</strong></p>
                    {/if}
                </div>
                <button onclick={closeAddToProjectModal} class="modal-close" aria-label="Close modal">
                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            
            <div class="modal-body modal-grid">
                <!-- Project Tree Structure -->
                <div class="tree-panel">
                    <div class="tree-header">
                        <h4>🌲 Project Structure</h4>
                        <button 
                            onclick={() => showNewFolderInput = !showNewFolderInput}
                            class="btn-primary-small"
                        >
                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
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
                            
                            {#if projectTreeData.filter(f => f.type === 'folder').length > 0}
                                <label for="workflow-parent-folder">Parent Folder (Optional)</label>
                                <select 
                                    bind:value={selectedParentFolder}
                                    id="workflow-parent-folder"
                                >
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
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                </svg>
                                <p>No folders yet</p>
                                <small>Create a folder to organize your workflows</small>
                            </div>
                        {:else}
                            {#each getFlattenedFolders(projectTreeData) as folder}
                                <button 
                                    class="folder-item {selectedProjectFolder?.id === folder.id ? 'selected' : ''}"
                                    onclick={() => selectedProjectFolder = folder}
                                    style="padding-left: {folder.depth * 16 + 16}px"
                                >
                                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                    </svg>
                                    <div class="folder-info">
                                        <span class="folder-name">{folder.name}</span>
                                        <span class="folder-count">{countWorkflowsInFolder(folder)} items</span>
                                    </div>
                                    {#if selectedProjectFolder?.id === folder.id}
                                        <svg class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
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
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
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
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <div>
                                    <strong>Ready to add</strong>
                                    <p>This workflow will be added to the "<strong>{selectedProjectFolder.name}</strong>" folder.</p>
                                </div>
                            </div>
                        {:else}
                            <div class="status-message warning">
                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                </svg>
                                <div>
                                    <strong>Select a folder</strong>
                                    <p>Please select a folder where you want to add this workflow, or create a new one.</p>
                                </div>
                            </div>
                        {/if}
                    {/if}
                </div>
            </div>
            
            <div class="modal-footer">
                <button
                    onclick={closeAddToProjectModal}
                    class="btn-secondary"
                >
                    Cancel
                </button>
                <button
                    onclick={addWorkflowToProject}
                    disabled={!selectedProjectFolder || !selectedWorkflowToAdd || addingWorkflowToProject}
                    class="btn-success"
                >
                    {#if addingWorkflowToProject}
                        <svg class="spinner" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Adding...</span>
                    {:else}
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
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
                        <p>Adding: <strong>{selectedRepoToAdd.name}</strong>
                            {#if selectedRepoToAdd.workflow_count}
                                with <strong>{selectedRepoToAdd.workflow_count} workflows</strong>
                            {/if}
                        </p>
                    {/if}
                </div>
                <button onclick={closeAddRepoToProjectModal} class="modal-close" aria-label="Close modal">
                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            
            <div class="modal-body modal-grid">
                <!-- Repository Tree Structure -->
                <div class="tree-panel">
                    <div class="tree-header">
                        <h4>🌲 Repository Structure</h4>
                        <button 
                            onclick={() => showNewFolderInput = !showNewFolderInput}
                            class="btn-primary-small"
                        >
                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
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
                            
                            {#if repoTreeData.filter(f => f.type === 'folder').length > 0}
                                <label for="repo-parent-folder">Parent Folder (Optional)</label>
                                <select 
                                    bind:value={selectedParentFolder}
                                    id="repo-parent-folder"
                                >
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
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                </svg>
                                <p>No folders yet</p>
                                <small>Create a folder to organize your repositories</small>
                            </div>
                        {:else}
                            {#each getFlattenedFolders(repoTreeData) as folder}
                                <button 
                                    class="folder-item {selectedRepoFolder?.id === folder.id ? 'selected' : ''}"
                                    onclick={() => selectedRepoFolder = folder}
                                    style="padding-left: {folder.depth * 16 + 16}px"
                                >
                                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                    </svg>
                                    <div class="folder-info">
                                        <span class="folder-name">{folder.name}</span>
                                        <span class="folder-count">{countWorkflowsInFolder(folder)} items</span>
                                    </div>
                                    {#if selectedRepoFolder?.id === folder.id}
                                        <svg class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
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
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3.382a1 1 0 00-.894.553l-.448.894a1 1 0 01-.894.553H9a1 1 0 01-.894-.553l-.448-.894A1 1 0 006.764 7H3z"/>
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
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <div>
                                    <strong>Ready to add</strong>
                                    <p>This repository will be added to the "<strong>{selectedRepoFolder.name}</strong>" folder.</p>
                                </div>
                            </div>
                        {:else}
                            <div class="status-message warning">
                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                </svg>
                                <div>
                                    <strong>Select a folder</strong>
                                    <p>Please select a folder where you want to add this repository, or create a new one.</p>
                                </div>
                            </div>
                        {/if}
                    {/if}
                </div>
            </div>
            
            <div class="modal-footer">
                <button
                    onclick={closeAddRepoToProjectModal}
                    class="btn-secondary"
                >
                    Cancel
                </button>
                <button
                    onclick={addRepositoryToProject}
                    disabled={!selectedRepoFolder || !selectedRepoToAdd || addingRepoToProject}
                    class="btn-success"
                >
                    {#if addingRepoToProject}
                        <svg class="spinner" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Adding...</span>
                    {:else}
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                        </svg>
                        <span>Add Repository</span>
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Global Workspace Variables */
    .workspace-container {
        position: relative;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: var(--bg-primary);
        color: var(--text-primary);
        
        /* Dark Theme (Default) */
        --bg-primary: #000000;
        --bg-secondary: #0A0A0A;
        --bg-tertiary: #151515;
        --text-primary: #FFFFFF;
        --text-secondary: #CCCCCC;
        --text-muted: #888888;
        --border-color: rgba(74, 158, 255, 0.2);
        --card-bg: rgba(255, 255, 255, 0.05);
        --card-bg-hover: rgba(255, 255, 255, 0.08);
        --primary-color: #4A9EFF;
        --accent-color: #FF8B4A;
        --success-color: #00FF66;
        --warning-color: #FFC107;
        --error-color: #FF4757;
        --sidebar-bg: rgba(10, 10, 10, 0.95);
        --sidebar-width: 280px;
        --sidebar-collapsed-width: 80px;
        --header-height: 80px;
    }

    .workspace-container.light {
        --bg-primary: #ffffff;
        --bg-secondary: #f8fafc;
        --bg-tertiary: #f1f5f9;
        --text-primary: #1a1a1a;
        --text-secondary: #2d3748;
        --text-muted: #718096;
        --border-color: rgba(9, 105, 218, 0.2);
        --card-bg: rgba(0, 0, 0, 0.03);
        --card-bg-hover: rgba(0, 0, 0, 0.06);
        --primary-color: #0969da;
        --accent-color: #d73a49;
        --success-color: #16a34a;
        --warning-color: #f59e0b;
        --error-color: #dc2626;
        --sidebar-bg: rgba(248, 250, 252, 0.95);
    }

    /* Professional Header */
    .workspace-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: var(--header-height);
        background: var(--bg-secondary);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid var(--border-color);
        z-index: 100;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }

    .header-content {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 2rem;
        max-width: none;
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 2rem;
    }

    .sidebar-toggle {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .sidebar-toggle:hover {
        background: var(--card-bg-hover);
        transform: scale(1.05);
    }

    .toggle-icon {
        width: 20px;
        height: 20px;
        color: var(--text-primary);
    }

    .brand-section {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .brand-icon-wrapper {
        position: relative;
        width: 48px;
        height: 48px;
    }

    .brand-icon {
        width: 100%;
        height: 100%;
        border-radius: 12px;
        filter: drop-shadow(0 4px 12px rgba(74, 158, 255, 0.3));
    }

    .brand-glow {
        position: absolute;
        inset: -8px;
        background: radial-gradient(circle, rgba(74, 158, 255, 0.3) 0%, transparent 70%);
        filter: blur(12px);
        z-index: -1;
    }

    .brand-text {
        display: flex;
        flex-direction: column;
    }

    .brand-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .brand-subtitle {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-weight: 500;
    }

    .workspace-info {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1.25rem;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
    }

    .workspace-label {
        font-size: 0.85rem;
        color: var(--text-muted);
        font-weight: 500;
    }

    .workspace-name {
        font-size: 1rem;
        color: var(--text-primary);
        font-weight: 700;
    }

    .header-right {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }

    .live-status {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1.25rem;
        background: rgba(0, 255, 102, 0.1);
        border: 1px solid rgba(0, 255, 102, 0.3);
        border-radius: 12px;
    }

    .status-dot {
        width: 12px;
        height: 12px;
        background: var(--success-color);
        border-radius: 50%;
        animation: pulse 2s ease-in-out infinite;
        box-shadow: 0 0 12px var(--success-color);
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.2); opacity: 0.8; }
    }

    .status-text {
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--success-color);
    }

    .status-time {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    .theme-toggle {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .theme-toggle:hover {
        background: var(--card-bg-hover);
        transform: translateY(-2px);
    }

    .theme-icon {
        width: 20px;
        height: 20px;
        color: var(--text-primary);
    }

    /* Professional Sidebar */
    .workspace-sidebar {
        position: fixed;
        left: 0;
        top: var(--header-height);
        width: var(--sidebar-width);
        height: calc(100vh - var(--header-height));
        background: var(--sidebar-bg);
        backdrop-filter: blur(20px);
        border-right: 1px solid var(--border-color);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 90;
        display: flex;
        flex-direction: column;
        overflow-y: auto;
    }

    .workspace-sidebar.collapsed {
        width: var(--sidebar-collapsed-width);
    }

    .sidebar-nav {
        flex: 1;
        padding: 1.5rem 0;
    }

    .nav-item {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.5rem;
        margin: 0.5rem 1rem;
        color: var(--text-secondary);
        text-decoration: none;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        border-radius: 12px;
        position: relative;
        overflow: hidden;
        background: transparent;
    }

    .nav-item::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(180deg, #4A9EFF 0%, #7B61FF 100%);
        transform: scaleY(0);
        transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        border-radius: 0 4px 4px 0;
    }

    .nav-item::after {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.08), rgba(123, 97, 255, 0.08));
        opacity: 0;
        transition: opacity 0.35s ease;
        border-radius: 12px;
    }

    .nav-item:hover {
        color: #4A9EFF;
        transform: translateX(4px);
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.12), rgba(123, 97, 255, 0.12));
        box-shadow: 0 4px 16px rgba(74, 158, 255, 0.15);
    }

    .nav-item:hover::before {
        transform: scaleY(1);
    }

    .nav-item:hover::after {
        opacity: 1;
    }

    .nav-item:hover .nav-icon {
        filter: drop-shadow(0 0 8px rgba(74, 158, 255, 0.6));
        transform: scale(1.1) rotate(5deg);
    }

    .nav-item.nav-item-danger:hover {
        color: #FF6B6B;
        background: linear-gradient(135deg, rgba(255, 107, 107, 0.12), rgba(255, 139, 74, 0.12));
        box-shadow: 0 4px 16px rgba(255, 107, 107, 0.15);
    }

    .nav-item.nav-item-danger::before {
        background: linear-gradient(180deg, #FF6B6B 0%, #FF8B4A 100%);
    }

    .nav-item.nav-item-danger:hover::after {
        background: linear-gradient(135deg, rgba(255, 107, 107, 0.08), rgba(255, 139, 74, 0.08));
    }

    .nav-item.nav-item-danger:hover .nav-icon {
        filter: drop-shadow(0 0 8px rgba(255, 107, 107, 0.6));
    }

    .nav-icon {
        width: 24px;
        height: 24px;
        flex-shrink: 0;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        z-index: 1;
    }

    .nav-text {
        font-size: 0.95rem;
        font-weight: 600;
        white-space: nowrap;
        position: relative;
        z-index: 1;
        letter-spacing: 0.3px;
        transition: all 0.35s ease;
    }

    .workspace-sidebar.collapsed .nav-text {
        display: none;
    }

    .workspace-sidebar.collapsed .nav-item {
        justify-content: center;
        padding: 1rem;
    }

    .nav-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(74, 158, 255, 0.3) 50%, transparent 100%);
        margin: 1.5rem 1rem;
        position: relative;
    }

    .nav-divider::after {
        content: '';
        position: absolute;
        top: -1px;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(123, 97, 255, 0.2) 50%, transparent 100%);
    }

    .sidebar-footer {
        padding: 1.5rem;
        border-top: 1px solid var(--border-color);
    }

    .refresh-button {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        padding: 0.875rem 1rem;
        background: linear-gradient(135deg, #4A9EFF 0%, #7B61FF 50%, #00D9FF 100%);
        color: white;
        border: none;
        border-radius: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(74, 158, 255, 0.25);
    }

    .refresh-button::before {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.2), transparent);
        opacity: 0;
        transition: opacity 0.4s ease;
    }

    .refresh-button:hover:not(:disabled) {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 12px 32px rgba(74, 158, 255, 0.45), 0 0 0 1px rgba(74, 158, 255, 0.3);
    }

    .refresh-button:hover:not(:disabled)::before {
        opacity: 1;
    }

    .refresh-button:active:not(:disabled) {
        transform: translateY(-1px) scale(1.01);
    }

    .refresh-button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .refresh-icon {
        width: 18px;
        height: 18px;
    }

    .refresh-icon.spinning {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    /* Main Content Area */
    .workspace-main {
        margin-left: var(--sidebar-width);
        margin-top: var(--header-height);
        min-height: calc(100vh - var(--header-height));
        padding: 2rem;
        transition: margin-left 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .workspace-main.expanded {
        margin-left: var(--sidebar-collapsed-width);
    }

    /* Loading State */
    .loading-state {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: calc(100vh - var(--header-height) - 4rem);
    }

    .loading-content {
        text-align: center;
    }

    .loading-spinner {
        width: 60px;
        height: 60px;
        border: 3px solid rgba(74, 158, 255, 0.2);
        border-radius: 50%;
        border-top-color: var(--primary-color);
        animation: spin 1s ease-in-out infinite;
        margin: 0 auto 2rem;
    }

    .loading-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .loading-text {
        color: var(--text-secondary);
        margin-bottom: 1.5rem;
    }

    .loading-progress {
        width: 200px;
        height: 4px;
        background: var(--card-bg);
        border-radius: 2px;
        margin: 0 auto;
        overflow: hidden;
    }

    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        animation: progress 2s ease-in-out infinite;
    }

    @keyframes progress {
        0% { width: 0%; }
        50% { width: 70%; }
        100% { width: 100%; }
    }

    /* Error State */
    .error-state {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: calc(100vh - var(--header-height) - 4rem);
    }

    .error-content {
        text-align: center;
        max-width: 500px;
    }

    .error-icon {
        width: 80px;
        height: 80px;
        margin: 0 auto 1.5rem;
        color: var(--error-color);
        background: rgba(255, 71, 87, 0.1);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .error-icon svg {
        width: 40px;
        height: 40px;
    }

    .error-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 1rem;
    }

    .error-message {
        color: var(--text-secondary);
        margin-bottom: 2rem;
        line-height: 1.6;
    }

    .error-actions {
        display: flex;
        gap: 1rem;
        justify-content: center;
    }

    .retry-button,
    .back-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .retry-button {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
        color: white;
        border: none;
    }

    .retry-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(74, 158, 255, 0.4);
    }

    .retry-button svg {
        width: 18px;
        height: 18px;
    }

    .back-button {
        background: var(--card-bg);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }

    .back-button:hover {
        background: var(--card-bg-hover);
    }

    /* Stats Grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }

    .stat-card {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .stat-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px rgba(74, 158, 255, 0.2);
        border-color: var(--primary-color);
    }

    .stat-card:hover::before {
        opacity: 1;
    }

    .stat-icon {
        width: 56px;
        height: 56px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .stat-icon svg {
        width: 28px;
        height: 28px;
    }

    .stat-icon-blue {
        background: rgba(74, 158, 255, 0.15);
        color: var(--primary-color);
    }

    .stat-icon-purple {
        background: rgba(139, 92, 246, 0.15);
        color: #8B5CF6;
    }

    .stat-icon-green {
        background: rgba(0, 255, 102, 0.15);
        color: var(--success-color);
    }

    .stat-icon-orange {
        background: rgba(255, 139, 74, 0.15);
        color: var(--accent-color);
    }

    .stat-content {
        flex: 1;
    }

    .stat-label {
        font-size: 0.85rem;
        color: var(--text-muted);
        font-weight: 500;
        margin-bottom: 0.25rem;
    }

    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1;
    }

    .stat-value-small {
        font-size: 1.25rem;
        text-transform: capitalize;
    }

    .stat-trend {
        font-size: 0.75rem;
    }

    .trend-up {
        color: var(--success-color);
        font-weight: 600;
    }

    .trend-neutral {
        color: var(--text-muted);
        font-weight: 500;
    }

    /* Tabs */
    .content-tabs {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        overflow: hidden;
    }

    .tabs-header {
        display: flex;
        gap: 0;
        background: var(--bg-tertiary);
        border-bottom: 1px solid var(--border-color);
        padding: 0.5rem;
    }

    .tab-button {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        padding: 1rem 1.5rem;
        background: transparent;
        border: none;
        border-radius: 12px;
        color: var(--text-secondary);
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .tab-button:hover {
        background: var(--card-bg-hover);
        color: var(--text-primary);
    }

    .tab-button.active {
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.2) 0%, rgba(255, 139, 74, 0.2) 100%);
        color: var(--primary-color);
        box-shadow: 0 4px 12px rgba(74, 158, 255, 0.2);
    }

    .tab-icon {
        width: 20px;
        height: 20px;
    }

    .tab-badge {
        padding: 0.25rem 0.75rem;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .tab-button.active .tab-badge {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: white;
    }

    .tabs-content {
        padding: 2rem;
    }

    /* Repositories Grid */
    .repositories-grid {
        display: grid;
        gap: 1.5rem;
    }

    .repository-card {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        transition: all 0.3s ease;
    }

    .repository-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(74, 158, 255, 0.15);
        border-color: var(--primary-color);
    }

    .repo-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }

    .repo-info {
        display: flex;
        gap: 1rem;
        flex: 1;
    }

    .repo-icon {
        width: 40px;
        height: 40px;
        background: rgba(74, 158, 255, 0.15);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--primary-color);
        flex-shrink: 0;
    }

    .repo-icon svg {
        width: 20px;
        height: 20px;
    }

    .repo-title-section {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-wrap: wrap;
    }

    .repo-name {
        font-size: 1.125rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0;
    }

    .repo-name a {
        color: var(--text-primary);
        text-decoration: none;
        transition: color 0.2s ease;
    }

    .repo-name a:hover {
        color: var(--primary-color);
    }

    .repo-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .repo-badge.private {
        background: rgba(255, 139, 74, 0.15);
        color: var(--accent-color);
        border: 1px solid rgba(255, 139, 74, 0.3);
    }

    .repo-badge.public {
        background: rgba(0, 255, 102, 0.15);
        color: var(--success-color);
        border: 1px solid rgba(0, 255, 102, 0.3);
    }

    .repo-menu-button {
        width: 32px;
        height: 32px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: var(--text-muted);
        transition: all 0.2s ease;
    }

    .repo-menu-button:hover {
        background: var(--card-bg-hover);
        color: var(--text-primary);
    }

    .repo-menu-button svg {
        width: 16px;
        height: 16px;
    }

    .repo-description {
        color: var(--text-secondary);
        margin-bottom: 1rem;
        line-height: 1.6;
    }

    .repo-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
        margin-bottom: 1rem;
    }

    .meta-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--text-muted);
        font-size: 0.875rem;
    }

    .meta-item svg {
        width: 16px;
        height: 16px;
    }

    .language-dot {
        width: 12px;
        height: 12px;
        background: var(--primary-color);
        border-radius: 50%;
    }

    .repo-workflows {
        border-top: 1px solid var(--border-color);
        padding-top: 1rem;
        margin-top: 1rem;
    }

    .workflows-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.75rem;
    }

    .workflows-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .workflow-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        transition: all 0.2s ease;
    }

    .workflow-item:hover {
        background: var(--card-bg-hover);
    }

    .workflow-info {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex: 1;
    }

    .workflow-name {
        font-size: 0.875rem;
        color: var(--text-primary);
        font-weight: 500;
    }

    .workflow-badge {
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .workflow-badge.active {
        background: rgba(0, 255, 102, 0.15);
        color: var(--success-color);
    }

    .workflow-badge.inactive {
        background: var(--card-bg);
        color: var(--text-muted);
    }

    .view-workflow-button {
        padding: 0.5rem 1rem;
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .view-workflow-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(74, 158, 255, 0.3);
    }

    /* Workflows Table */
    .workflows-loading {
        text-align: center;
        padding: 3rem;
    }

    .workflows-loading p {
        color: var(--text-secondary);
        margin-top: 1rem;
    }

    .workflows-table-container {
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid var(--border-color);
    }

    .workflows-table {
        width: 100%;
        border-collapse: collapse;
    }

    .workflows-table thead {
        background: var(--bg-tertiary);
    }

    .workflows-table th {
        padding: 1rem 1.5rem;
        text-align: left;
        font-size: 0.75rem;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid var(--border-color);
    }

    .workflows-table tbody tr {
        border-bottom: 1px solid var(--border-color);
        transition: background 0.2s ease;
    }

    .workflows-table tbody tr:hover {
        background: var(--card-bg-hover);
    }

    .workflows-table td {
        padding: 1rem 1.5rem;
    }

    .workflow-cell {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .workflow-icon-wrapper {
        width: 40px;
        height: 40px;
        background: rgba(74, 158, 255, 0.15);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--primary-color);
        flex-shrink: 0;
    }

    .workflow-icon-wrapper svg {
        width: 20px;
        height: 20px;
    }

    .workflow-details {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .workflow-table-name {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .workflow-repo-name {
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    .triggers-cell {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .trigger-badge {
        padding: 0.25rem 0.75rem;
        background: rgba(74, 158, 255, 0.15);
        color: var(--primary-color);
        border: 1px solid rgba(74, 158, 255, 0.3);
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .trigger-more {
        padding: 0.25rem 0.75rem;
        background: var(--card-bg);
        color: var(--text-muted);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        font-size: 0.75rem;
    }

    .trigger-unknown {
        color: var(--text-muted);
        font-size: 0.875rem;
    }

    .last-run-time {
        color: var(--text-primary);
        font-size: 0.875rem;
    }

    .last-run-never {
        color: var(--text-muted);
        font-size: 0.875rem;
    }

    .status-badge {
        padding: 0.35rem 0.75rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: capitalize;
        display: inline-block;
    }

    .status-badge.active {
        background: rgba(0, 255, 102, 0.15);
        color: var(--success-color);
        border: 1px solid rgba(0, 255, 102, 0.3);
    }

    .status-badge.inactive,
    .status-badge.unknown {
        background: var(--card-bg);
        color: var(--text-muted);
        border: 1px solid var(--border-color);
    }

    .table-action-button {
        width: 36px;
        height: 36px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: var(--text-muted);
        transition: all 0.2s ease;
    }

    .table-action-button:hover {
        background: var(--card-bg-hover);
        color: var(--text-primary);
        transform: scale(1.05);
    }

    .table-action-button svg {
        width: 18px;
        height: 18px;
    }

    /* Dropdown Menus */
    .dropdown-menu {
        position: absolute;
        right: 0;
        top: calc(100% + 4px);
        min-width: 220px;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(20px);
        z-index: 1000;
        padding: 0.5rem;
        animation: dropdownFadeIn 0.2s ease-out;
    }

    .dropdown-menu-right {
        right: 0;
        left: auto;
    }

    @keyframes dropdownFadeIn {
        from {
            opacity: 0;
            transform: translateY(-8px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .dropdown-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
        padding: 0.75rem 1rem;
        background: transparent;
        border: none;
        border-radius: 8px;
        color: var(--text-secondary);
        font-size: 0.9rem;
        font-weight: 500;
        text-align: left;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .dropdown-item:hover {
        background: var(--card-bg-hover);
        color: var(--text-primary);
    }

    .dropdown-item svg {
        width: 18px;
        height: 18px;
        flex-shrink: 0;
    }

    .dropdown-item-primary {
        color: var(--success-color);
    }

    .dropdown-item-primary:hover {
        background: rgba(0, 255, 102, 0.1);
        color: var(--success-color);
    }

    .dropdown-divider {
        height: 1px;
        background: var(--border-color);
        margin: 0.5rem 0;
    }

    /* Enhanced Table Columns */
    .uses-cell {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        max-width: 300px;
    }

    .uses-action {
        padding: 0.4rem 0.75rem;
        background: rgba(74, 158, 255, 0.1);
        border: 1px solid rgba(74, 158, 255, 0.3);
        border-radius: 6px;
        color: var(--primary-color);
        font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
        font-size: 0.75rem;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .workspace-container.light .uses-action {
        background: rgba(9, 105, 218, 0.1);
        border-color: rgba(9, 105, 218, 0.3);
    }

    .uses-more {
        color: var(--text-muted);
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        background: var(--card-bg);
        border-radius: 4px;
        align-self: flex-start;
    }

    .uses-none {
        color: var(--text-muted);
        font-style: italic;
    }

    .author-cell {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .author-avatar {
        width: 32px;
        height: 32px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--primary-color);
        flex-shrink: 0;
    }

    .author-avatar svg {
        width: 16px;
        height: 16px;
        color: var(--text-muted);
    }

    .author-name {
        font-size: 0.9rem;
        color: var(--text-secondary);
        font-weight: 500;
    }

    .author-unknown {
        color: var(--text-muted);
        font-style: italic;
    }

    /* Responsive Dropdown */
    @media (max-width: 768px) {
        .dropdown-menu {
            min-width: 200px;
            right: -20px;
        }
    }


    /* Empty State */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
    }

    .empty-icon {
        width: 80px;
        height: 80px;
        margin: 0 auto 1.5rem;
        color: var(--text-muted);
        opacity: 0.5;
    }

    .empty-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .empty-message {
        color: var(--text-secondary);
        font-size: 0.95rem;
    }

    /* Modal */
    .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        animation: fadeIn 0.2s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    .modal-content {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        width: 90%;
        max-width: 900px;
        max-height: 90vh;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        animation: slideUp 0.3s ease;
    }

    @keyframes slideUp {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 2rem;
        border-bottom: 1px solid var(--border-color);
    }

    .modal-title h3 {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0 0 0.5rem 0;
    }

    .modal-title p {
        font-size: 0.85rem;
        color: var(--text-muted);
        margin: 0;
    }

    .modal-close {
        width: 36px;
        height: 36px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: var(--text-muted);
        transition: all 0.2s ease;
    }

    .modal-close:hover {
        background: var(--error-color);
        color: white;
        border-color: var(--error-color);
    }

    .modal-close svg {
        width: 20px;
        height: 20px;
    }

    .modal-body {
        padding: 2rem;
        max-height: calc(90vh - 140px);
        overflow-y: auto;
    }

    .modal-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        padding: 3rem;
    }

    .modal-loading span {
        color: var(--text-secondary);
    }

    .code-viewer {
        background: #1a1a1a;
        border: 1px solid var(--border-color);
        border-radius: 12px;
        overflow: hidden;
    }

    .code-viewer pre {
        margin: 0;
        padding: 1.5rem;
        overflow-x: auto;
    }

    .code-viewer code {
        font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
        font-size: 0.875rem;
        line-height: 1.6;
        color: #00FF66;
    }

    /* Responsive Design */
    @media (max-width: 1200px) {
        .stats-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    @media (max-width: 768px) {
        .workspace-sidebar {
            transform: translateX(-100%);
        }

        .workspace-sidebar.collapsed {
            transform: translateX(0);
        }

        .workspace-main {
            margin-left: 0;
        }

        .workspace-main.expanded {
            margin-left: 0;
        }

        .header-content {
            padding: 0 1rem;
        }

        .workspace-info {
            display: none;
        }

        .stats-grid {
            grid-template-columns: 1fr;
        }

        .workflows-table {
            font-size: 0.875rem;
        }

        .workflows-table th,
        .workflows-table td {
            padding: 0.75rem 1rem;
        }

        .modal-content {
            width: 95%;
        }
    }

    @media (max-width: 480px) {
        .brand-text {
            display: none;
        }

        .tab-button span {
            display: none;
        }

        .stat-value {
            font-size: 1.5rem;
        }
    }

    /* Modal Large Content */
    .modal-content-large {
        max-width: 1200px;
        width: 90%;
        max-height: 90vh;
        display: flex;
        flex-direction: column;
    }

    .modal-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        flex: 1;
        overflow: hidden;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 1rem;
        padding: 1.5rem;
        border-top: 1px solid var(--border-color);
        background: var(--bg-tertiary);
    }

    /* Tree Panel */
    .tree-panel,
    .preview-panel {
        display: flex;
        flex-direction: column;
        background: var(--bg-tertiary);
        border-radius: 12px;
        padding: 1.5rem;
        overflow: hidden;
    }

    .tree-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
    }

    .tree-header h4,
    .preview-panel > h4 {
        font-size: 1.125rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0;
    }

    .btn-primary-small {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-primary-small:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(74, 158, 255, 0.3);
    }

    .btn-primary-small svg {
        width: 16px;
        height: 16px;
    }

    /* New Folder Form */
    .new-folder-form {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }

    .new-folder-form label {
        display: block;
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .new-folder-form input,
    .new-folder-form select {
        width: 100%;
        padding: 0.75rem;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary);
        font-size: 0.9rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }

    .new-folder-form input:focus,
    .new-folder-form select:focus {
        outline: none;
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1);
    }

    .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        margin-top: 1rem;
    }

    .btn-primary,
    .btn-secondary,
    .btn-success {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        border: none;
    }

    .btn-primary {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
        color: white;
    }

    .btn-primary:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(74, 158, 255, 0.3);
    }

    .btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-secondary {
        background: var(--card-bg);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }

    .btn-secondary:hover {
        background: var(--card-bg-hover);
    }

    .btn-success {
        background: linear-gradient(135deg, var(--success-color) 0%, #00CC52 100%);
        color: #000000;
    }

    .btn-success:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(0, 255, 102, 0.3);
    }

    .btn-success:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-success svg {
        width: 18px;
        height: 18px;
    }

    .spinner {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    /* Tree List */
    .tree-list {
        flex: 1;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .tree-empty {
        text-align: center;
        padding: 3rem 1rem;
    }

    .tree-empty svg {
        width: 60px;
        height: 60px;
        color: var(--text-muted);
        opacity: 0.5;
        margin: 0 auto 1rem;
    }

    .tree-empty p {
        font-size: 0.95rem;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
    }

    .tree-empty small {
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    .folder-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
        padding: 1.25rem 1.5rem;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        border: 2px solid rgba(74, 158, 255, 0.35);
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: left;
        position: relative;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }

    .folder-item::before {
        content: '';
        position: absolute;
        inset: -2px;
        border-radius: 12px;
        padding: 2px;
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.5), rgba(255, 139, 74, 0.5));
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        mask-composite: exclude;
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .folder-item:hover {
        background: rgba(74, 158, 255, 0.12);
        border-color: rgba(74, 158, 255, 0.6);
        transform: translateY(-3px);
        box-shadow: 0 12px 32px rgba(74, 158, 255, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }

    .folder-item:hover::before {
        opacity: 1;
    }

    .folder-item.selected {
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.25) 0%, rgba(255, 139, 74, 0.18) 100%);
        border-color: var(--primary-color);
        border-width: 3px;
        box-shadow: 0 12px 32px rgba(74, 158, 255, 0.4), 
                    inset 0 2px 4px rgba(74, 158, 255, 0.2),
                    0 0 0 1px rgba(74, 158, 255, 0.6);
        transform: scale(1.02);
    }

    .folder-item.selected::before {
        opacity: 1;
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.7), rgba(255, 139, 74, 0.7));
    }

    .workspace-container.light .folder-item {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid rgba(9, 105, 218, 0.4);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.9);
    }

    .workspace-container.light .folder-item:hover {
        background: rgba(9, 105, 218, 0.12);
        border-color: rgba(9, 105, 218, 0.7);
        box-shadow: 0 12px 32px rgba(9, 105, 218, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.95);
    }

    .workspace-container.light .folder-item.selected {
        background: linear-gradient(135deg, rgba(9, 105, 218, 0.2) 0%, rgba(217, 58, 73, 0.12) 100%);
        border-color: #0969da;
        border-width: 3px;
        box-shadow: 0 12px 32px rgba(9, 105, 218, 0.35), 
                    inset 0 2px 4px rgba(9, 105, 218, 0.15),
                    0 0 0 1px rgba(9, 105, 218, 0.5);
    }

    .folder-item svg:first-child {
        width: 28px;
        height: 28px;
        color: var(--primary-color);
        flex-shrink: 0;
        filter: drop-shadow(0 2px 4px rgba(74, 158, 255, 0.3));
    }

    .folder-item.selected svg:first-child {
        color: var(--primary-color);
        filter: drop-shadow(0 4px 8px rgba(74, 158, 255, 0.5));
    }

    .folder-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
    }

    .folder-name {
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary);
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    .folder-item.selected .folder-name {
        color: var(--primary-color);
        text-shadow: 0 2px 4px rgba(74, 158, 255, 0.3);
    }

    .folder-count {
        font-size: 0.85rem;
        color: var(--text-muted);
        font-weight: 600;
    }

    .folder-item.selected .folder-count {
        color: var(--text-secondary);
    }

    .check-icon {
        width: 24px;
        height: 24px;
        color: var(--primary-color);
        flex-shrink: 0;
        filter: drop-shadow(0 2px 6px rgba(74, 158, 255, 0.5));
    }

    /* Preview Panel */
    .preview-panel {
        overflow-y: auto;
    }

    .preview-panel > h4 {
        margin-bottom: 1.5rem;
    }

    .workflow-preview,
    .repo-preview {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .preview-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .preview-icon {
        width: 48px;
        height: 48px;
        background: rgba(0, 255, 102, 0.15);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .preview-icon-primary {
        background: rgba(74, 158, 255, 0.15);
    }

    .preview-icon svg {
        width: 24px;
        height: 24px;
        color: var(--success-color);
    }

    .preview-icon-primary svg {
        color: var(--primary-color);
    }

    .preview-name {
        font-size: 1.125rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }

    .preview-repo,
    .preview-desc {
        font-size: 0.875rem;
        color: var(--text-muted);
    }

    .preview-details {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .detail-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.9rem;
    }

    .detail-item > span:first-child {
        color: var(--text-muted);
        font-weight: 600;
    }

    .detail-item > span:last-child {
        color: var(--text-secondary);
        font-weight: 500;
    }

    .triggers-preview {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    /* Status Messages */
    .status-message {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        padding: 1rem;
        border-radius: 12px;
        margin-top: 1.5rem;
    }

    .status-message svg {
        width: 24px;
        height: 24px;
        flex-shrink: 0;
        margin-top: 2px;
    }

    .status-message.success {
        background: rgba(0, 255, 102, 0.1);
        border: 1px solid rgba(0, 255, 102, 0.3);
    }

    .status-message.success svg {
        color: var(--success-color);
    }

    .status-message.success strong {
        color: var(--success-color);
    }

    .status-message.warning {
        background: rgba(255, 193, 7, 0.1);
        border: 1px solid rgba(255, 193, 7, 0.3);
    }

    .status-message.warning svg {
        color: var(--warning-color);
    }

    .status-message.warning strong {
        color: var(--warning-color);
    }

    .status-message p {
        margin: 0.5rem 0 0;
        font-size: 0.875rem;
        color: var(--text-secondary);
        line-height: 1.5;
    }

    .status-message strong {
        display: block;
        font-size: 0.95rem;
        font-weight: 700;
    }

    /* Modal Responsive */
    @media (max-width: 1024px) {
        .modal-grid {
            grid-template-columns: 1fr;
        }

        .modal-content-large {
            width: 95%;
        }
    }

    @media (max-width: 768px) {
        .modal-content-large {
            max-height: 95vh;
        }

        .tree-panel,
        .preview-panel {
            padding: 1rem;
        }
    }
</style>


