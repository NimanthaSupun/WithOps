<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { githubClient } from '$lib/github.js';
    import { repositoryTreeClient } from '$lib/repositoryTree.js';
    import { userOrganizations, appStore } from '$lib/stores.js';
    
    let loading = true;
    let error = null;
    let orgName = '';
    let workspaceData = null;
    let selectedWorkflow = null;
    let showWorkflowModal = false;
    let workflowContent = '';
    let loadingWorkflow = false;
    let loadingStage = 'Initializing...';
    let authorizationChecked = false;
    let userAuthorized = false;
    let refreshing = false;
    
    // Tab management
    let activeTab = 'repositories'; // 'repositories' or 'workflows'
    let detailedWorkflows = [];
    let loadingDetailedWorkflows = false;

    // Real-time updates
    let realTimeEnabled = true;
    let lastSyncTime = null;
    let realtimeUpdateCount = 0;
    
    // Workflow action menu
    let activeWorkflowMenu = null;
    
    // Repository action menu
    let activeRepoMenu = null;
    
    // Add to Project modal
    let showAddToProjectModal = false;
    let selectedWorkflowToAdd = null;
    let projectTreeData = [];
    let selectedProjectFolder = null;
    let newFolderName = '';
    let showNewFolderInput = false;
    let addingWorkflowToProject = false;
    let selectedParentFolder = null;
    
    // Add Repository to Project modal
    let showAddRepoToProjectModal = false;
    let selectedRepoToAdd = null;
    let addingRepoToProject = false;
    let repoTreeData = []; // Separate data for repository tree
    let selectedRepoFolder = null; // Separate selection for repository tree

    onMount(async () => {
        orgName = $page.params.org;
        console.log(`🚀 Loading workspace for organization: ${orgName}`);
        
        // Simple approach: Just try to load the data
        // If we're on this page, the user should already be authenticated
        loadingStage = 'Checking authentication...';
        
        try {
            // Quick authentication check - if we can get user orgs, we're authenticated
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
                
                // If authentication failed because user isn't logged in, redirect to main page
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

    async function checkAuthorization() {
        try {
            loadingStage = 'Checking authorization...';
            
            // Ensure we're authenticated before proceeding
            if (!await githubClient.isAuthenticated()) {
                throw new Error('Not authenticated');
            }
            
            // First check if we have user organizations in store
            const currentUserOrgs = $userOrganizations;
            
            if (currentUserOrgs.length === 0) {
                // Load user organizations if not already loaded
                const result = await githubClient.getMyOrganizations();
                if (result.success) {
                    appStore.setUserOrganizations(result.organizations);
                    userAuthorized = appStore.isUserAuthorizedForOrg(orgName, result.organizations);
                } else {
                    throw new Error(result.error || 'Failed to load user organizations');
                }
            } else {
                userAuthorized = appStore.isUserAuthorizedForOrg(orgName, currentUserOrgs);
            }
            
            authorizationChecked = true;
            
            if (!userAuthorized) {
                error = `Access denied. You don't have permission to access organization '${orgName}'. This organization may have been installed by another user or the app may not be installed.`;
                loading = false;
                return;
            }
            
        } catch (err) {
            console.error('Authorization check failed:', err);
            error = `Failed to verify access permissions: ${err.message}`;
            loading = false;
            authorizationChecked = true;
        }
    }

    async function loadWorkspaceData() {
        try {
            loading = true;
            error = null;
            
            console.log(`Loading workspace data for organization: ${orgName}`);
            
            // Check cache first for instant loading
            const cached = githubClient.getCachedData(`workspace_${orgName}`);
            if (cached) {
                console.log('🚀 Loading from cache instantly');
                workspaceData = cached;
                loading = false;
                return;
            }
            
            loadingStage = 'Connecting to GitHub...';
            
            // Simple approach: try to load workspace data directly since backend is working
            // The backend logs show successful API calls, so trust the backend
            console.log(`🔍 Loading workspace data directly for ${orgName}...`);
            
            loadingStage = 'Fetching repositories and workflows...';
            const result = await githubClient.getOrganizationWorkspace(orgName);
            
            if (result.success) {
                loadingStage = 'Processing data...';
                workspaceData = result;  // Use the entire result object
                console.log('Workspace data loaded:', workspaceData);
                console.log('Repository count:', workspaceData.repository_count);
                console.log('Total workflows:', workspaceData.total_workflows);
                console.log('Repositories array:', workspaceData.repositories);
                
                // Batch prefetch the most common workflows for instant access
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
            
            // 🔧 FIX: Improved error handling - only show "app not installed" for specific backend responses
            const errorMessage = err.message || err.toString();
            
            // Only treat as installation error if backend specifically says so
            if (err.error_type === 'app_not_installed' ||
                (errorMessage.includes('app_not_installed') && !errorMessage.includes('network')) ||
                (errorMessage.includes('not installed') && errorMessage.includes('organization'))) {
                error = `GitHub App is no longer installed in ${orgName}. Please reinstall the app to access the workspace.`;
            } else if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
                error = `Access denied to ${orgName}. You may not have permission to access this organization.`;
            } else if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
                error = `Network error: Unable to connect to server. Please check your connection and try again.`;
            } else {
                // Generic error - don't assume it's an installation issue
                error = `Failed to load workspace: ${errorMessage}`;
            }
            
            loadingStage = 'Error occurred';
        } finally {
            loading = false;
        }
    }

    function connectAnotherOrg() {
        goto('/');
    }

    function viewRepository(repo) {
        // In future, could open repo details or redirect to GitHub
        window.open(repo.html_url, '_blank');
    }

    async function viewWorkflowContent(workflow, repo) {
        try {
            // Defensive check to ensure repo has required properties
            if (!repo || !repo.name) {
                console.error('❌ Invalid repo object:', repo);
                workflowContent = `# Error loading workflow content\n# Repository information is missing or invalid`;
                showWorkflowModal = true;
                loadingWorkflow = false;
                return;
            }

            selectedWorkflow = { ...workflow, repo: repo.name };
            showWorkflowModal = true;
            
            // Check cache first for instant display
            const cacheKey = `workflow_${orgName}_${repo.name}_${workflow.path}`;
            const cached = githubClient.getCachedData(cacheKey);
            
            if (cached) {
                console.log('🚀 Displaying cached YAML instantly');
                workflowContent = cached.content;
                loadingWorkflow = false;
                
                // Smart prefetch: preload other workflows in the same repo
                githubClient.smartPrefetch(orgName, repo.name, workflow.path);
                return;
            }
            
            // If not cached, show loading and fetch
            loadingWorkflow = true;
            
            // Fetch workflow content from backend
            const result = await githubClient.getWorkflowContent(orgName, repo.name, workflow.path);
            
            if (result.success) {
                workflowContent = result.content;
                console.log('📄 YAML content loaded');
                
                // Smart prefetch: preload other workflows in the same repo
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
        
        // Load detailed workflows if not already loaded
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
                console.log('Sample workflow data:', detailedWorkflows[0]);
            } else {
                console.error('Failed to load detailed workflows:', result.error);
                // Fall back to basic workflow info from workspace data
                detailedWorkflows = workspaceData.workflows || [];
            }
            
        } catch (err) {
            console.error('Error loading detailed workflows:', err);
            // Fall back to basic workflow info from workspace data
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
    
    function formatTriggers(triggers) {
        if (!triggers || triggers.length === 0) return 'Unknown';
        return triggers.join(', ');
    }
    
    function formatUses(uses) {
        if (!uses || uses.length === 0) return 'None';
        return uses.slice(0, 2).join(', ') + (uses.length > 2 ? ` +${uses.length - 2} more` : '');
    }

    // Enhanced error handling for workflow operations
    function handleWorkflowError(error, operation) {
        console.error(`❌ Error in ${operation}:`, error);
        const errorMessage = error.message || `Failed to ${operation}`;
        
        // Show user-friendly error message
        if (errorMessage.includes('403') || errorMessage.includes('Access denied')) {
            error = `Access denied. You may not have permission to view this workflow data.`;
        } else if (errorMessage.includes('404') || errorMessage.includes('not found')) {
            error = `Workflow not found. It may have been deleted or moved.`;
        } else {
            error = `Failed to ${operation}: ${errorMessage}`;
        }
    }
    
    // Enhanced workflow viewing with better error handling
    async function viewWorkflowContentEnhanced(workflow, repo) {
        try {
            await viewWorkflowContent(workflow, repo);
        } catch (err) {
            handleWorkflowError(err, 'load workflow content');
        }
    }
    
    // Add sorting capability for workflows table
    let sortColumn = 'name';
    let sortDirection = 'asc';
    
    function sortWorkflows(column) {
        if (sortColumn === column) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortColumn = column;
            sortDirection = 'asc';
        }
        
        detailedWorkflows = [...detailedWorkflows].sort((a, b) => {
            let aValue = a[column];
            let bValue = b[column];
            
            // Handle special cases
            if (column === 'last_run' || column === 'last_successful') {
                aValue = aValue ? new Date(aValue.created_at) : new Date(0);
                bValue = bValue ? new Date(bValue.created_at) : new Date(0);
            } else if (column === 'triggers') {
                aValue = (aValue || []).join(', ');
                bValue = (bValue || []).join(', ');
            } else if (typeof aValue === 'string') {
                aValue = aValue.toLowerCase();
                bValue = (bValue || '').toLowerCase();
            }
            
            if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
            if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
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
            
            // Force refresh organization data (bypasses all caches)
            const result = await githubClient.forceRefreshOrganization(orgName);
            
            if (result.success) {
                workspaceData = result;
                console.log('✅ Organization data refreshed successfully');
                
                // Also clear detailed workflows to force reload
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
        // Listen for real-time workspace updates
        window.addEventListener('github-workspace_updated', (event) => {
            const { organization, changes, timestamp } = event.detail;
            
            if (organization === orgName) {
                console.log('🔄 Real-time workspace update received:', changes);
                realtimeUpdateCount++;
                lastSyncTime = new Date(timestamp);
                
                // Show notification about changes
                if (changes.repositories.added.length > 0) {
                    showNotification(`${changes.repositories.added.length} new repositories detected`, 'success');
                }
                if (changes.repositories.removed.length > 0) {
                    showNotification(`${changes.repositories.removed.length} repositories removed`, 'warning');
                }
                if (changes.workflows.added.length > 0) {
                    showNotification(`${changes.workflows.added.length} new workflows detected`, 'success');
                }
                if (changes.workflows.removed.length > 0) {
                    showNotification(`${changes.workflows.removed.length} workflows removed`, 'warning');
                }
                
                // Refresh workspace data
                loadWorkspaceData();
            }
        });
    }

    function startAutoSync() {
        if (!realTimeEnabled) return;
        
        setInterval(async () => {
            try {
                await githubClient.syncOrganizationRealtime(orgName);
            } catch (error) {
                console.warn('⚠️ Auto-sync failed:', error);
            }
        }, 30000); // Every 30 seconds
    }

    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg text-white ${
            type === 'success' ? 'bg-green-500' : 
            type === 'warning' ? 'bg-yellow-500' : 
            'bg-blue-500'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    async function toggleRealtimeUpdates() {
        realTimeEnabled = !realTimeEnabled;
        
        if (realTimeEnabled) {
            startAutoSync();
            showNotification('Real-time updates enabled', 'success');
        } else {
            showNotification('Real-time updates disabled', 'warning');
        }
    }

    async function manualSync() {
        try {
            loadingStage = 'Syncing with GitHub...';
            loading = true;
            
            const result = await githubClient.syncOrganizationRealtime(orgName);
            
            if (result.has_changes) {
                showNotification(`Sync completed: ${result.total_changes} changes detected`, 'success');
                // Refresh will happen automatically via WebSocket
            } else {
                showNotification('No changes detected', 'info');
            }
            
            lastSyncTime = new Date();
        } catch (error) {
            console.error('Manual sync failed:', error);
            showNotification('Sync failed', 'error');
        } finally {
            loading = false;
        }
    }
    
    // Workflow action menu functions
    function toggleWorkflowActionMenu(workflowId) {
        if (activeWorkflowMenu === workflowId) {
            activeWorkflowMenu = null;
        } else {
            activeWorkflowMenu = workflowId;
        }
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
            // Load existing project tree from database
            const result = await githubClient.getProjectTreeData(orgName);
            if (result.success) {
                projectTreeData = result.data || [];
            } else {
                // Initialize empty tree if no data exists
                projectTreeData = [];
            }
        } catch (err) {
            console.error('Failed to load project tree data:', err);
            projectTreeData = [];
        }
    }
    
    async function loadRepositoryTreeData() {
        try {
            // Load existing repository tree from database
            const result = await repositoryTreeClient.getRepositoryTree(orgName);
            if (result.success) {
                repoTreeData = result.data || [];
            } else {
                // Initialize empty tree if no data exists
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
        
        // Determine which modal is open and use appropriate data
        const isRepoModal = showAddRepoToProjectModal;
        const targetTreeData = isRepoModal ? repoTreeData : projectTreeData;
        
        if (selectedParentFolder) {
            // Add to parent folder
            if (!selectedParentFolder.children) {
                selectedParentFolder.children = [];
            }
            selectedParentFolder.children.push(newFolder);
        } else {
            // Add to root level
            targetTreeData.push(newFolder);
        }
        
        // Set the appropriate selected folder
        if (isRepoModal) {
            selectedRepoFolder = newFolder;
            repoTreeData = [...repoTreeData]; // Trigger reactivity
        } else {
            selectedProjectFolder = newFolder;
            projectTreeData = [...projectTreeData]; // Trigger reactivity
        }
        
        newFolderName = '';
        showNewFolderInput = false;
        selectedParentFolder = null;
    }

    // Helper function to flatten folder structure for selection
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

    // Helper function to count total workflows in a folder (including nested)
    function countWorkflowsInFolder(folder) {
        if (!folder.children) return 0;
        let count = 0;
        for (const child of folder.children) {
            if (child.type === 'workflow') {
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
            
            // Get workflow content
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
            
            // Add to selected folder
            if (!selectedProjectFolder.children) {
                selectedProjectFolder.children = [];
            }
            selectedProjectFolder.children.push(newWorkflowItem);
            
            // Save to database
            await saveProjectTreeData();
            
            showNotification(`Workflow "${selectedWorkflowToAdd.name}" added to project successfully!`, 'success');
            closeAddToProjectModal();
            
        } catch (err) {
            console.error('Failed to add workflow to project:', err);
            showNotification('Failed to add workflow to project', 'error');
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
    
    // Close dropdown when clicking outside
    function handleGlobalClick(event) {
        if (!event.target.closest('.relative')) {
            activeWorkflowMenu = null;
            activeRepoMenu = null;
        }
    }
    
    // Repository menu functions
    function toggleRepoActionMenu(repoId) {
        if (activeRepoMenu === repoId) {
            activeRepoMenu = null;
        } else {
            activeRepoMenu = repoId;
        }
    }
    
    async function openAddRepoToProjectModal(repo) {
        selectedRepoToAdd = repo;
        await loadRepositoryTreeData(); // Load repository tree, not project tree
        showAddRepoToProjectModal = true;
    }
    
    function closeAddRepoToProjectModal() {
        showAddRepoToProjectModal = false;
        selectedRepoToAdd = null;
        selectedRepoFolder = null; // Use selectedRepoFolder
        newFolderName = '';
        showNewFolderInput = false;
        selectedParentFolder = null;
    }
    
    async function addRepositoryToProject() {
        if (!selectedRepoToAdd || !selectedRepoFolder) return; // Use selectedRepoFolder
        
        try {
            addingRepoToProject = true;
            
            // Fetch all workflows from the repository
            const repoWorkflows = selectedRepoToAdd.workflows || [];
            
            // Create repository folder item
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
            
            // Add all workflows from the repository as children
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
            
            // Add repository folder to selected folder in REPOSITORY TREE
            if (!selectedRepoFolder.children) {
                selectedRepoFolder.children = [];
            }
            selectedRepoFolder.children.push(repoFolderItem);
            
            // Save to REPOSITORY TREE database (not project tree)
            await saveRepositoryTreeData();
            
            showNotification(`Repository "${selectedRepoToAdd.name}" with ${repoWorkflows.length} workflows added to repository tree successfully!`, 'success');
            closeAddRepoToProjectModal();
            
        } catch (err) {
            console.error('Failed to add repository to tree:', err);
            showNotification('Failed to add repository to tree', 'error');
        } finally {
            addingRepoToProject = false;
        }
    }

</script>

<svelte:head>
    <title>{orgName} Workspace - WithOps</title>
</svelte:head>

<svelte:window on:click={handleGlobalClick} />

<div class="min-h-screen bg-gray-50">
    <div class="container mx-auto px-4 py-8">
        <header class="mb-8">
            <nav class="flex items-center space-x-2 text-sm text-gray-500 mb-4">
                <a href="/" class="hover:text-gray-700">Dashboard</a>
                <span>/</span>
                <span class="text-gray-900">{orgName} Workspace</span>
            </nav>
            
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold text-gray-900">{orgName}</h1>
                    <p class="text-gray-600">Organization Workspace</p>
                </div>

                <div class="flex space-x-3">
                    <button 
                        on:click={() => goto('/organizations')}
                        class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 font-medium"
                    >
                        ← Back to Organizations
                    </button>
                    <button 
                        on:click={connectAnotherOrg}
                        class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                    >
                        Connect Another Organization
                    </button>
                    <button
                        on:click={() => goto(`/github/workspace/${orgName}/audit`)}
                        class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 font-medium"
                    >
                        Actions Version Audit Table
                    </button>
                    <button
                        on:click={() => goto(`/github/workspace/${orgName}/treeview`)}
                        class="bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700 font-medium flex items-center space-x-2"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                        </svg>
                        <span>🗂️ Workflow Treeview</span>
                    </button>
                    
                    <button
                        on:click={() => goto(`/github/workspace/${orgName}/repo-treeview`)}
                        class="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 font-medium flex items-center space-x-2"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                        </svg>
                        <span>📦 Repository Treeview</span>
                    </button>

                    <button
                        on:click={() => goto(`/github/workspace/${orgName}/threat-modeling`)}
                        class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 font-medium flex items-center space-x-2"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                        <span>🛡️ Threat Modeling</span>
                    </button>

                    <!-- <button
                        on:click={() => goto(`/github/workspace/${orgName}/canvas`)}
                        class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 font-medium"
                    >
                        🎨 Canvas Workflow Builder
                    </button> -->
                    
                </div>
            </div>
        </header>
``
        {#if loading}
            <!-- Skeleton Loading for Instant UI Response -->
            <div class="space-y-6">
                <!-- Skeleton Workspace Overview -->
                <div class="bg-white shadow rounded-lg p-6">
                    <div class="h-6 bg-gray-200 rounded w-48 mb-4 animate-pulse"></div>
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                        {#each Array(4) as _}
                            <div class="bg-gray-50 p-4 rounded-lg animate-pulse">
                                <div class="h-4 bg-gray-200 rounded w-24 mb-2"></div>
                                <div class="h-8 bg-gray-300 rounded w-16"></div>
                            </div>
                        {/each}
                    </div>
                </div>
                
                <!-- Skeleton Repositories -->
                <div class="bg-white shadow rounded-lg p-6">
                    <div class="h-6 bg-gray-200 rounded w-32 mb-4 animate-pulse"></div>
                    <div class="space-y-4">
                        {#each Array(2) as _}
                            <div class="border border-gray-200 rounded-lg p-6 animate-pulse">
                                <div class="h-5 bg-gray-200 rounded w-48 mb-2"></div>
                                <div class="h-4 bg-gray-100 rounded w-full mb-3"></div>
                                <div class="flex space-x-4">
                                    {#each Array(4) as _}
                                        <div class="h-3 bg-gray-200 rounded w-16"></div>
                                    {/each}
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            </div>
            
            <!-- Loading Status -->
            <div class="fixed bottom-4 right-4 bg-white shadow-lg rounded-lg p-4 border">
                <div class="flex items-center space-x-3">
                    <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                    <div>
                        <p class="text-sm font-medium text-gray-900">{loadingStage}</p>
                        <div class="text-xs text-gray-500">
                            {#if loadingStage === 'Fetching repositories and workflows...'}
                                <span>⚡ Using parallel processing for faster loading</span>
                            {:else if loadingStage === 'Connecting to GitHub...'}
                                <span>🔗 Establishing secure connection</span>
                            {:else if loadingStage === 'Processing data...'}
                                <span>📊 Organizing workspace data</span>
                            {/if}
                        </div>
                    </div>
                </div>
            </div>
        {:else if error}
            <div class="bg-white shadow rounded-lg p-6">
                <div class="text-center">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                        {#if error.includes('Access denied') || error.includes('permission')}
                            <!-- Security/Authorization Error Icon -->
                            <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        {:else}
                            <!-- General Error Icon -->
                            <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        {/if}
                    </div>
                    
                    {#if error.includes('Access denied') || error.includes('permission')}
                        <h3 class="text-lg font-medium text-gray-900 mb-2">🔐 Access Denied</h3>
                        <p class="text-sm text-red-600 mb-6">{error}</p>
                        
                        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                            <div class="flex items-start">
                                <svg class="h-5 w-5 text-yellow-400 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                                </svg>
                                <div class="text-sm">
                                    <p class="text-yellow-800 font-medium">Data Privacy Protection</p>
                                    <p class="text-yellow-700 mt-1">This organization's data is protected and can only be accessed by the user who installed the GitHub App.</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="space-y-3">
                            <button 
                                on:click={() => goto('/organizations')}
                                class="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 font-medium"
                            >
                                View Your Organizations
                            </button>
                            <button 
                                on:click={() => goto('/')}
                                class="w-full bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400"
                            >
                                Go to Dashboard
                            </button>
                        </div>
                    {:else}
                        <h3 class="text-lg font-medium text-gray-900 mb-2">Failed to Load Workspace</h3>
                        <p class="text-sm text-red-600 mb-6">{error}</p>
                        
                        <div class="space-y-3">
                            {#if error.includes('not installed') || error.includes('404')}
                                <!-- Show reinstall option for installation-related errors -->
                                <button 
                                    on:click={async () => {
                                        const result = await githubClient.generateInstallationUrl(orgName);
                                        if (result.success) {
                                            window.location.href = result.installation_url;
                                        }
                                    }}
                                    class="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 font-medium"
                                >
                                    🧩 Reinstall GitHub App
                                </button>
                                <div class="text-xs text-gray-500 mb-4">
                                    <p>💡 The GitHub App was removed from this organization.</p>
                                    <p>Click above to reinstall it and regain access to your workspace.</p>
                                </div>
                            {/if}
                            
                            <div class="flex space-x-3">
                                <button 
                                    on:click={loadWorkspaceData}
                                    class="flex-1 bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700"
                                >
                                    Retry
                                </button>
                                <button 
                                    on:click={() => goto('/organizations')}
                                    class="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400"
                                >
                                    Go Back
                                </button>
                            </div>
                        </div>
                    {/if}
                </div>
            </div>
        {:else if workspaceData}
            <div class="space-y-6">
                <!-- Workspace Overview -->
                <div class="bg-white shadow rounded-lg p-6">
                    <h2 class="text-xl font-semibold text-gray-900 mb-4">Workspace Overview</h2>
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div class="bg-blue-50 p-4 rounded-lg">
                            <h3 class="text-lg font-medium text-blue-900">Repositories</h3>
                            <p class="text-2xl font-bold text-blue-600">{workspaceData.repository_count || 0}</p>
                        </div>
                        
                        <div class="bg-purple-50 p-4 rounded-lg">
                            <h3 class="text-lg font-medium text-purple-900">Workflows</h3>
                            <p class="text-2xl font-bold text-purple-600">{workspaceData.total_workflows || 0}</p>
                        </div>
                        
                        <div class="bg-green-50 p-4 rounded-lg">
                            <h3 class="text-lg font-medium text-green-900">Status</h3>
                            <p class="text-lg font-semibold text-green-600 capitalize">{workspaceData.status || 'connected'}</p>
                        </div>
                        
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h3 class="text-lg font-medium text-gray-900">Organization</h3>
                            <p class="text-sm font-mono text-gray-600">{workspaceData.organization?.login || orgName}</p>
                        </div>
                    </div>
                    
                    {#if workspaceData.last_updated}
                        <div class="mt-4 p-4 bg-gray-50 rounded-lg">
                            <h4 class="font-medium text-gray-900 mb-2">Last Updated</h4>
                            <p class="text-sm text-gray-600">{new Date(workspaceData.last_updated).toLocaleString()}</p>
                        </div>
                    {/if}
                    
                    <!-- Quick Actions -->
                    <div class="mt-6 border-t pt-6">
                        <h4 class="font-medium text-gray-900 mb-4">Quick Actions</h4>
                        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <a 
                                href="/github/workspace/{orgName}/treeview"
                                class="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                <div class="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center">
                                    <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-900">Workflow Treeview</p>
                                    <p class="text-xs text-gray-500">Organize workflows</p>
                                </div>
                            </a>
                            
                            <a 
                                href="/github/workspace/{orgName}/repo-treeview"
                                class="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                <div class="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
                                    <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-900">Repository Treeview</p>
                                    <p class="text-xs text-gray-500">Organize repositories</p>
                                </div>
                            </a>
                            
                            <a 
                                href="/github/workspace/{orgName}/canvas"
                                class="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                <div class="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                                    <svg class="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-900">Workflow Canvas</p>
                                    <p class="text-xs text-gray-500">Visual workflow builder</p>
                                </div>
                            </a>
                            
                            <a 
                                href="/github/workspace/{orgName}/security"
                                class="flex items-center space-x-3 p-3 border border-red-200 rounded-lg hover:bg-red-50 transition-colors bg-red-50"
                            >
                                <div class="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                                    <svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-900">🔒 Security Dashboard</p>
                                    <p class="text-xs text-gray-500">AI-powered security scanning</p>
                                </div>
                            </a>
                        </div>
                    </div>
                </div>

                <!-- Real-time Status Panel -->
                {#if workspaceData}
                    <div class="bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg p-4 mb-6">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-4">
                                <div class="flex items-center space-x-2">
                                    <span class="text-sm font-medium text-gray-700">Status:</span>
                                    <span class="flex items-center space-x-1">
                                        <span class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                                        <span class="text-sm text-green-700 font-medium">Live</span>
                                    </span>
                                </div>
                                
                                {#if lastSyncTime}
                                    <div class="flex items-center space-x-2">
                                        <span class="text-sm text-gray-500">Last sync:</span>
                                        <span class="text-sm text-gray-700">{lastSyncTime.toLocaleTimeString()}</span>
                                    </div>
                                {/if}
                                
                                {#if realtimeUpdateCount > 0}
                                    <div class="flex items-center space-x-2">
                                        <span class="text-sm text-gray-500">Updates received:</span>
                                        <span class="text-sm font-medium text-blue-700">{realtimeUpdateCount}</span>
                                    </div>
                                {/if}
                            </div>
                            
                            <div class="flex items-center space-x-2 text-sm text-gray-600">
                                <span>🚀 Real-time workspace monitoring active</span>
                            </div>
                        </div>
                    </div>
                {/if}

                <!-- Tabbed Interface for Repositories and Workflows -->
                <div class="bg-white shadow rounded-lg overflow-hidden">
                    <!-- Tab Navigation -->
                    <div class="border-b border-gray-200">
                        <nav class="-mb-px flex" aria-label="Tabs">
                            <button
                                on:click={() => activeTab = 'repositories'}
                                class="w-1/2 py-4 px-6 border-b-2 font-medium text-sm focus:outline-none transition-colors duration-200 {activeTab === 'repositories' 
                                    ? 'border-blue-500 text-blue-600 bg-blue-50' 
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
                            >
                                <div class="flex items-center justify-center space-x-2">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                                    </svg>
                                    <span>Repositories</span>
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                        {workspaceData.repository_count || 0}
                                    </span>
                                </div>
                            </button>
                            <button
                                on:click={switchToWorkflowsTab}
                                class="w-1/2 py-4 px-6 border-b-2 font-medium text-sm focus:outline-none transition-colors duration-200 {activeTab === 'workflows' 
                                    ? 'border-blue-500 text-blue-600 bg-blue-50' 
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
                            >
                                <div class="flex items-center justify-center space-x-2">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                    </svg>
                                    <span>Workflows</span>
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                        {workspaceData.total_workflows || 0}
                                    </span>
                                </div>
                            </button>
                        </nav>
                    </div>

                    <!-- Tab Content -->
                    <div class="p-6">
                        {#if activeTab === 'repositories'}
                            <!-- Repositories Tab Content -->
                            <div class="space-y-1 mb-4">
                                <h2 class="text-xl font-semibold text-gray-900">Repositories</h2>
                                <p class="text-sm text-gray-600">Browse repositories and their associated workflows</p>
                            </div>
                            
                            {#if workspaceData.repositories && workspaceData.repositories.length > 0}
                                <div class="space-y-6">
                                    {#each workspaceData.repositories as repo}
                                        <div class="border border-gray-200 rounded-lg p-6 hover:bg-gray-50 transition-colors duration-200">
                                            <div class="flex items-start justify-between mb-4">
                                                <div class="flex-1">
                                                    <h3 class="text-lg font-medium text-gray-900">
                                                        <a href={repo.html_url} target="_blank" class="hover:text-blue-600 transition-colors duration-200">
                                                            {repo.name}
                                                        </a>
                                                        {#if repo.private}
                                                            <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                                                Private
                                                            </span>
                                                        {/if}
                                                    </h3>
                                                    {#if repo.description}
                                                        <p class="text-gray-600 text-sm mt-1">{repo.description}</p>
                                                    {/if}
                                                    <div class="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                                                        {#if repo.language}
                                                            <span class="flex items-center">
                                                                <span class="w-3 h-3 rounded-full bg-blue-500 mr-2"></span>
                                                                {repo.language}
                                                            </span>
                                                        {/if}
                                                        <span class="flex items-center">
                                                            <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                                            </svg>
                                                            {repo.stargazers_count}
                                                        </span>
                                                        <span class="flex items-center">
                                                            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
                                                            </svg>
                                                            {repo.forks_count}
                                                        </span>
                                                        <span class="flex items-center">
                                                            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                            </svg>
                                                            {repo.workflow_count} workflows
                                                        </span>
                                                        <span class="flex items-center">
                                                            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                            </svg>
                                                            Updated {new Date(repo.updated_at).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                </div>
                                                
                                                <div class="relative">
                                                    <button 
                                                        on:click={() => toggleRepoActionMenu(repo.id || repo.name)}
                                                        class="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-gray-100 transition-colors duration-200"
                                                        aria-label="More actions"
                                                    >
                                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                                                        </svg>
                                                    </button>
                                                    
                                                    {#if activeRepoMenu === (repo.id || repo.name)}
                                                        <div class="absolute right-0 top-10 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-10">
                                                            <div class="py-1">
                                                                <button 
                                                                    on:click={() => {
                                                                        viewRepository(repo);
                                                                        activeRepoMenu = null;
                                                                    }}
                                                                    class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                                                >
                                                                    <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                                                    </svg>
                                                                    View Details
                                                                </button>
                                                                
                                                                <button 
                                                                    on:click={() => {
                                                                        goto(`/github/workspace/${orgName}/canvas?repo=${repo.name}`);
                                                                        activeRepoMenu = null;
                                                                    }}
                                                                    class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                                                >
                                                                    <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                                                                    </svg>
                                                                    🎨 Canvas Builder
                                                                </button>
                                                                
                                                                <div class="border-t border-gray-100"></div>
                                                                
                                                                <button 
                                                                    on:click={() => {
                                                                        openAddRepoToProjectModal(repo);
                                                                        activeRepoMenu = null;
                                                                    }}
                                                                    class="flex items-center w-full px-4 py-2 text-sm text-green-700 hover:bg-green-50 hover:text-green-900"
                                                                >
                                                                    <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                                    </svg>
                                                                    Add Repository to Project
                                                                </button>
                                                                
                                                                <a 
                                                                    href={repo.html_url} 
                                                                    target="_blank"
                                                                    on:click={() => activeRepoMenu = null}
                                                                    class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                                                >
                                                                    <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                                    </svg>
                                                                    Open in GitHub
                                                                </a>
                                                            </div>
                                                        </div>
                                                    {/if}
                                                </div>
                                            </div>
                                            
                                            <!-- Workflows Section -->
                                            {#if repo.workflows && repo.workflows.length > 0}
                                                <div class="border-t border-gray-100 pt-4">
                                                    <h4 class="text-sm font-medium text-gray-900 mb-3">GitHub Actions Workflows ({repo.workflow_count})</h4>
                                                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                                        {#each repo.workflows as workflow}
                                                            <div class="bg-gray-50 rounded-lg p-3 hover:bg-gray-100 transition-colors duration-200">
                                                                <div class="flex items-center justify-between">
                                                                    <div class="flex-1">
                                                                        <h5 class="text-sm font-medium text-gray-900">{workflow.name}</h5>
                                                                        <p class="text-xs text-gray-500 mt-1">{workflow.path}</p>
                                                                        <div class="flex items-center space-x-2 mt-2">
                                                                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {workflow.state === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                                                                                {workflow.state}
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                    <div class="flex flex-col space-y-1">
                                                                        <button 
                                                                            on:click={() => viewWorkflowContent(workflow, repo)}
                                                                            on:mouseenter={() => {
                                                                                if (repo && repo.name) {
                                                                                    githubClient.preloadWorkflowContent(orgName, repo.name, workflow.path);
                                                                                }
                                                                            }}
                                                                            class="text-blue-600 hover:text-blue-800 text-xs px-2 py-1 rounded bg-blue-50 hover:bg-blue-100 transition-colors duration-200"
                                                                        >
                                                                            View YAML
                                                                        </button>
                                                                        {#if workflow.html_url}
                                                                            <a 
                                                                                href={workflow.html_url} 
                                                                                target="_blank"
                                                                                class="text-gray-600 hover:text-gray-800 text-xs px-2 py-1 rounded bg-gray-50 hover:bg-gray-100 text-center transition-colors duration-200"
                                                                            >
                                                                                GitHub →
                                                                            </a>
                                                                        {/if}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        {/each}
                                                    </div>
                                                </div>
                                            {:else}
                                                <div class="border-t border-gray-100 pt-4">
                                                    <p class="text-sm text-gray-500">No GitHub Actions workflows found in this repository.</p>
                                                </div>
                                            {/if}
                                        </div>
                                    {/each}
                                </div>
                            {:else}
                                <div class="text-center py-12">
                                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                                    </svg>
                                    <h3 class="mt-2 text-sm font-medium text-gray-900">No repositories found</h3>
                                    <p class="mt-1 text-sm text-gray-500">This organization doesn't have any repositories yet.</p>
                                </div>
                            {/if}
                        {:else if activeTab === 'workflows'}
                            <!-- Workflows Tab Content -->
                            <div class="space-y-1 mb-6">
                                <h2 class="text-xl font-semibold text-gray-900">Workflows Overview</h2>
                                <p class="text-sm text-gray-600">Comprehensive view of all workflows across repositories with detailed metadata</p>
                            </div>   
                            {#if loadingDetailedWorkflows}
                                <!-- Loading state for workflows table -->
                                <div class="flex items-center justify-center py-12">
                                    <div class="flex items-center space-x-3">
                                        <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                                        <span class="text-gray-600">Loading detailed workflow information...</span>
                                    </div>
                                </div>
                            {:else if detailedWorkflows.length > 0}
                            
                                <!-- Advanced Workflows Table -->
                                <div class="bg-white border border-gray-200 rounded-lg overflow-hidden">
                                    <div class="overflow-x-auto">
                                        <table class="min-w-full divide-y divide-gray-200">
                                            <thead class="bg-gray-50">
                                                <tr>
                                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Repository / Workflow
                                                    </th>
                                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Trigger
                                                    </th>
                                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Last Run
                                                    </th>
                                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Last Successful
                                                    </th>
                                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Uses
                                                    </th>
                                                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Author
                                                    </th>
                                                    <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Actions
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody class="bg-white divide-y divide-gray-200">
                                                {#each detailedWorkflows as workflow}
                                                    <tr class="hover:bg-gray-50 transition-colors duration-200">
                                                        <td class="px-6 py-4 whitespace-nowrap">
                                                            <div class="flex items-center">
                                                                <div class="flex-shrink-0 h-10 w-10">
                                                                    <div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                                                                        <svg class="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                                        </svg>
                                                                    </div>
                                                                </div>
                                                                <div class="ml-4">
                                                                    <div class="text-sm font-medium text-gray-900">
                                                                        {workflow.name}
                                                                    </div>
                                                                    <div class="text-sm text-gray-500 flex items-center space-x-2">
                                                                        <span>{workflow.repository}</span>
                                                                        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {workflow.state === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                                                                            {workflow.state}
                                                                        </span>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                            <div class="flex flex-wrap gap-1">
                                                                {#if workflow.triggers && workflow.triggers.length > 0 && workflow.triggers[0] !== 'Unknown'}
                                                                    {#each workflow.triggers.slice(0, 2) as trigger}
                                                                        <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800">
                                                                            {trigger}
                                                                        </span>
                                                                    {/each}
                                                                    {#if workflow.triggers.length > 2}
                                                                        <span 
                                                                            class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800 cursor-help"
                                                                            title="All triggers: {formatTriggers(workflow.triggers)}"
                                                                        >
                                                                            +{workflow.triggers.length - 2}
                                                                        </span>
                                                                    {/if}
                                                                {:else}
                                                                    <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                                                                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                        </svg>
                                                                        Not parsed
                                                                    </span>
                                                                {/if}
                                                            </div>
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {#if workflow.last_run && workflow.last_run.created_at}
                                                                <div>
                                                                    <div class="text-sm text-gray-900">{formatRelativeTime(workflow.last_run.created_at)}</div>
                                                                    <div class="text-xs text-gray-500 flex items-center space-x-1">
                                                                        <span class="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium {
                                                                            workflow.last_run.conclusion === 'success' ? 'bg-green-100 text-green-800' :
                                                                            workflow.last_run.conclusion === 'failure' ? 'bg-red-100 text-red-800' :
                                                                            workflow.last_run.conclusion === 'cancelled' ? 'bg-yellow-100 text-yellow-800' :
                                                                            'bg-gray-100 text-gray-800'
                                                                        }">
                                                                            {workflow.last_run.conclusion || workflow.last_run.status}
                                                                        </span>
                                                                    </div>
                                                                </div>
                                                            {:else}
                                                                <div class="flex items-center text-gray-400">
                                                                    <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                    </svg>
                                                                    <span class="text-sm">Not available</span>
                                                                </div>
                                                            {/if}
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {#if workflow.last_successful && workflow.last_successful.created_at}
                                                                <div>
                                                                    <div class="text-sm text-gray-900">{formatRelativeTime(workflow.last_successful.created_at)}</div>
                                                                    <div class="text-xs text-green-600">✓ Success</div>
                                                                </div>
                                                            {:else}
                                                                <div class="flex items-center text-gray-400">
                                                                    <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                    </svg>
                                                                    <span class="text-sm">Not available</span>
                                                                </div>
                                                            {/if}
                                                        </td>
                                                        <td class="px-6 py-4 text-sm text-gray-500">
                                                            {#if workflow.uses && workflow.uses.length > 0}
                                                                <div class="max-w-xs">
                                                                    {#each workflow.uses.slice(0, 2) as use}
                                                                        <div class="text-xs text-gray-600 truncate">{use}</div>
                                                                    {/each}
                                                                    {#if workflow.uses.length > 2}
                                                                        <div class="text-xs text-gray-400">+{workflow.uses.length - 2} more</div>
                                                                    {/if}
                                                                </div>
                                                            {:else}
                                                                <div class="flex items-center text-gray-400">
                                                                    <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                                                                    </svg>
                                                                    <span class="text-sm">Not parsed</span>
                                                                </div>
                                                            {/if}
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            <div class="flex items-center">
                                                                <div class="flex-shrink-0 h-6 w-6">
                                                                    <div class="h-6 w-6 rounded-full bg-gray-200 flex items-center justify-center">
                                                                        <span class="text-xs font-medium text-gray-600">
                                                                            {#if workflow.author && workflow.author !== 'Unknown'}
                                                                                {workflow.author.charAt(0).toUpperCase()}
                                                                            {:else}
                                                                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                                                                </svg>
                                                                            {/if}
                                                                        </span>
                                                                    </div>
                                                                </div>
                                                                <div class="ml-2">
                                                                    <div class="text-sm text-gray-900">
                                                                        {#if workflow.author && workflow.author !== 'Unknown'}
                                                                            {workflow.author}
                                                                        {:else}
                                                                            <span class="text-gray-400">Not available</span>
                                                                        {/if}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                            <div class="relative">
                                                                <button 
                                                                    on:click={() => toggleWorkflowActionMenu(`${workflow.id}-${workflow.repository}`)}
                                                                    class="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-gray-100 transition-colors duration-200"
                                                                    aria-label="More actions"
                                                                >
                                                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                                                                    </svg>
                                                                </button>
                                                                
                                                                {#if activeWorkflowMenu === `${workflow.id}-${workflow.repository}`}
                                                                    <div class="absolute right-0 top-10 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-10">
                                                                        <div class="py-1">
                                                                            <button 
                                                                                on:click={() => {
                                                                                    viewWorkflowContent(workflow, { name: workflow.repository });
                                                                                    activeWorkflowMenu = null;
                                                                                }}
                                                                                class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                                                            >
                                                                                <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                                                                                </svg>
                                                                                View YAML
                                                                            </button>
                                                                            <button 
                                                                                on:click={() => {
                                                                                    goto(`/github/workspace/${orgName}/canvas?repo=${workflow.repository}&workflow=${encodeURIComponent(workflow.name)}`);
                                                                                    activeWorkflowMenu = null;
                                                                                }}
                                                                                class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                                                            >
                                                                                <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                                                                                </svg>
                                                                                Open Canvas
                                                                            </button>
                                                                            <div class="border-t border-gray-100"></div>

                                                                            <button 
                                                                                on:click={() => {
                                                                                    openAddToProjectModal(workflow);
                                                                                    activeWorkflowMenu = null;
                                                                                }}
                                                                                class="flex items-center w-full px-4 py-2 text-sm text-green-700 hover:bg-green-50 hover:text-green-900"
                                                                            >
                                                                                <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                                                </svg>
                                                                                Add to Project
                                                                            </button>
                                                                            {#if workflow.html_url}
                                                                                <a 
                                                                                    href={workflow.html_url} 
                                                                                    target="_blank"
                                                                                    on:click={() => activeWorkflowMenu = null}
                                                                                    class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                                                                >
                                                                                    <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                                                    </svg>
                                                                                    Open in GitHub
                                                                                </a>
                                                                            {/if}
                                                                        </div>
                                                                    </div>
                                                                {/if}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                {/each}
                                            </tbody>
                                        </table>
                                    </div>
                                    
                                    <!-- Table Footer with Stats -->
                                    <div class="bg-gray-50 px-6 py-3 border-t border-gray-200">
                                        <div class="flex items-center justify-between text-sm text-gray-500">
                                            <div>
                                                Showing {detailedWorkflows.length} workflows across {workspaceData.repository_count} repositories
                                            </div>
                                            <div class="flex items-center space-x-4">
                                                <span class="flex items-center">
                                                    <span class="w-2 h-2 bg-green-500 rounded-full mr-1"></span>
                                                    Active: {detailedWorkflows.filter(w => w.state === 'active').length}
                                                </span>
                                                <span class="flex items-center">
                                                    <span class="w-2 h-2 bg-gray-400 rounded-full mr-1"></span>
                                                    Inactive: {detailedWorkflows.filter(w => w.state !== 'active').length}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            {:else}
                                <!-- Empty state for workflows -->
                                <div class="text-center py-12">
                                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                    </svg>
                                    <h3 class="mt-2 text-sm font-medium text-gray-900">No workflows found</h3>
                                    <p class="mt-1 text-sm text-gray-500">No GitHub Actions workflows have been configured in this organization.</p>
                                </div>
                            {/if}
                        {/if}
                    </div>
                </div>
            </div>
        {/if}
    </div>
</div>

<!-- Workflow Content Modal -->
{#if showWorkflowModal && selectedWorkflow}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" on:click={closeWorkflowModal}>
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white" on:click|stopPropagation>
            <div class="flex items-center justify-between mb-4">
                <div>
                    <h3 class="text-lg font-medium text-gray-900">{selectedWorkflow.name}</h3>
                    <p class="text-sm text-gray-600">{selectedWorkflow.repo}/{selectedWorkflow.path}</p>
                </div>
                <button 
                    on:click={closeWorkflowModal}
                    class="text-gray-400 hover:text-gray-600"
                    aria-label="Close workflow modal"
                >
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            <div class="mt-4">
                {#if loadingWorkflow}
                    <div class="flex items-center justify-center py-8">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <span class="ml-2 text-gray-600">Loading workflow content...</span>
                    </div>
                {:else}
                    <div class="bg-gray-900 rounded-lg p-4 overflow-auto max-h-96">
                        <pre class="text-green-400 text-sm font-mono whitespace-pre-wrap">{workflowContent}</pre>
                    </div>
                    
                    <div class="mt-4 flex justify-end space-x-3">
                        <button 
                            on:click={closeWorkflowModal}
                            class="bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400"
                        >
                            Close
                        </button>
                        {#if selectedWorkflow.html_url}
                            <a 
                                href={selectedWorkflow.html_url} 
                                target="_blank"
                                class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                            >
                                View on GitHub
                            </a>
                        {/if}
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

<!-- Add to Project Modal -->
{#if showAddToProjectModal}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h3 class="text-lg font-medium text-gray-900">Add Workflow to Project Treeview</h3>
                    {#if selectedWorkflowToAdd}
                        <p class="text-sm text-gray-600 mt-1">
                            Adding: <span class="font-medium">{selectedWorkflowToAdd.name}</span> from <span class="font-medium">{selectedWorkflowToAdd.repository}</span>
                        </p>
                    {/if}
                </div>
                <button 
                    on:click={closeAddToProjectModal}
                    class="text-gray-400 hover:text-gray-600"
                    aria-label="Close modal"
                >
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Project Tree Structure -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-4">
                        <h4 class="text-md font-medium text-gray-900">🌲 Project Structure</h4>
                        <button 
                            on:click={() => showNewFolderInput = !showNewFolderInput}
                            class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 flex items-center space-x-1"
                        >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                            </svg>
                            <span>New Folder</span>
                        </button>
                    </div>
                    
                    {#if showNewFolderInput}
                        <div class="mb-4 p-3 bg-white rounded border">
                            <div class="mb-3">
                                <label for="folder-name" class="block text-sm font-medium text-gray-700 mb-2">
                                    Folder Name
                                </label>
                                <input
                                    bind:value={newFolderName}
                                    placeholder="Enter folder name..."
                                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    on:keypress={(e) => e.key === 'Enter' && createNewFolderInModal()}
                                    id="folder-name"
                                />
                            </div>
                            
                            {#if projectTreeData.filter(f => f.type === 'folder').length > 0}
                                <div class="mb-3">
                                    <label for="parent-folder-select" class="block text-sm font-medium text-gray-700 mb-2">
                                        Parent Folder (Optional)
                                    </label>
                                    <select 
                                        bind:value={selectedParentFolder}
                                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                        id="parent-folder-select"
                                    >
                                        <option value={null}>None (Create at root level)</option>
                                        {#each getFlattenedFolders(projectTreeData) as folder}
                                            <option value={folder}>
                                                {'  '.repeat(folder.depth)}📁 {folder.name}
                                            </option>
                                        {/each}
                                    </select>
                                </div>
                            {/if}
                            
                            <div class="flex justify-end space-x-2">
                                <button
                                    on:click={() => { 
                                        showNewFolderInput = false; 
                                        newFolderName = ''; 
                                        selectedParentFolder = null;
                                    }}
                                    class="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                                >
                                    Cancel
                                </button>
                                <button
                                    on:click={createNewFolderInModal}
                                    disabled={!newFolderName.trim()}
                                    class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                >
                                    Create
                                </button>
                            </div>
                        </div>
                    {/if}
                    
                    <div class="max-h-64 overflow-y-auto space-y-2">
                        {#if projectTreeData.length === 0}
                            <div class="text-center py-8 text-gray-500">
                                <svg class="w-12 h-12 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                </svg>
                                <p class="text-sm">No folders yet</p>
                                <p class="text-xs text-gray-400 mt-1">Create a folder to organize your workflows</p>
                            </div>
                        {:else}
                            {#each getFlattenedFolders(projectTreeData) as folder}
                                <button 
                                    class="w-full p-3 border rounded cursor-pointer transition-colors duration-200 text-left {
                                        selectedProjectFolder?.id === folder.id 
                                        ? 'bg-blue-100 border-blue-500 text-blue-900' 
                                        : 'bg-white border-gray-200 hover:bg-gray-50'
                                    }"
                                    on:click={() => selectedProjectFolder = folder}
                                >
                                    <div class="flex items-center space-x-2">
                                        <div style="margin-left: {folder.depth * 16}px" class="flex items-center space-x-2">
                                            <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                            </svg>
                                            <span class="text-sm font-medium">{folder.name}</span>
                                            {#if selectedRepoFolder?.id === folder.id}
                                                <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                                </svg>
                                            {/if}
                                        </div>
                                    </div>
                                    <div class="text-xs text-gray-500 mt-1" style="margin-left: {folder.depth * 16 + 28}px">
                                        {countWorkflowsInFolder(folder)} items
                                    </div>
                                </button>
                            {/each}
                        {/if}
                    </div>
                </div>
                
                <!-- Workflow Preview -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h4 class="text-md font-medium text-gray-900 mb-4">📄 Workflow Preview</h4>
                    {#if selectedWorkflowToAdd}
                        <div class="bg-white rounded border p-4">
                            <div class="flex items-center space-x-3 mb-3">
                                <div class="flex-shrink-0 h-10 w-10">
                                    <div class="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                                        <svg class="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                        </svg>
                                    </div>
                                </div>
                                <div>
                                    <div class="text-sm font-medium text-gray-900">{selectedWorkflowToAdd.name}</div>
                                    <div class="text-sm text-gray-500">{selectedWorkflowToAdd.repository}</div>
                                </div>
                            </div>
                            
                            <div class="space-y-2">
                                <div class="text-xs text-gray-600">
                                    <span class="font-medium">Path:</span> {selectedWorkflowToAdd.path || 'N/A'}
                                </div>
                                <div class="text-xs text-gray-600">
                                    <span class="font-medium">State:</span> 
                                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {selectedWorkflowToAdd.state === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                                        {selectedWorkflowToAdd.state || 'Unknown'}
                                    </span>
                                </div>
                                {#if selectedWorkflowToAdd.triggers && selectedWorkflowToAdd.triggers.length > 0}
                                    <div class="text-xs text-gray-600">
                                        <span class="font-medium">Triggers:</span>
                                        <div class="flex flex-wrap gap-1 mt-1">
                                            {#each selectedWorkflowToAdd.triggers as trigger}
                                                <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800">
                                                    {trigger}
                                                </span>
                                            {/each}
                                        </div>
                                    </div>
                                {/if}
                            </div>
                        </div>
                        
                        {#if selectedProjectFolder}
                            <div class="mt-4 p-3 bg-green-50 border border-green-200 rounded">
                                <div class="flex items-center text-green-800">
                                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <span class="text-sm font-medium">Ready to add</span>
                                </div>
                                <p class="text-sm text-green-700 mt-1">
                                    This workflow will be added to the "<span class="font-medium">{selectedProjectFolder.name}</span>" folder.
                                </p>
                            </div>
                        {:else}
                            <div class="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                                <div class="flex items-center text-yellow-800">
                                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                    </svg>
                                    <span class="text-sm font-medium">Select a folder</span>
                                </div>
                                <p class="text-sm text-yellow-700 mt-1">
                                    Please select a folder where you want to add this workflow, or create a new one.
                                </p>
                            </div>
                        {/if}
                    {/if}
                </div>
            </div>
            
            <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-200">
                <button
                    on:click={closeAddToProjectModal}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                >
                    Cancel
                </button>
                <button
                    on:click={addWorkflowToProject}
                    disabled={!selectedProjectFolder || !selectedWorkflowToAdd || addingWorkflowToProject}
                    class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                    {#if addingWorkflowToProject}
                        <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Adding...</span>
                    {:else}
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h3 class="text-lg font-medium text-gray-900">Add Repository to Project Treeview</h3>
                    {#if selectedRepoToAdd}
                        <p class="text-sm text-gray-600 mt-1">
                            Adding: <span class="font-medium">{selectedRepoToAdd.name}</span>
                            {#if selectedRepoToAdd.workflow_count}
                                with <span class="font-medium">{selectedRepoToAdd.workflow_count} workflows</span>
                            {/if}
                        </p>
                    {/if}
                </div>
                <button 
                    on:click={closeAddRepoToProjectModal}
                    class="text-gray-400 hover:text-gray-600"
                    aria-label="Close modal"
                >
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Project Tree Structure -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-4">
                        <h4 class="text-md font-medium text-gray-900">🌲 Project Structure</h4>
                        <button 
                            on:click={() => showNewFolderInput = !showNewFolderInput}
                            class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 flex items-center space-x-1"
                        >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                            </svg>
                            <span>New Folder</span>
                        </button>
                    </div>
                    
                    {#if showNewFolderInput}
                        <div class="mb-4 p-3 bg-white rounded border">
                            <div class="mb-3">
                                <label for="repo-folder-name" class="block text-sm font-medium text-gray-700 mb-2">
                                    Folder Name
                                </label>
                                <input
                                    bind:value={newFolderName}
                                    placeholder="Enter folder name..."
                                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    on:keypress={(e) => e.key === 'Enter' && createNewFolderInModal()}
                                    id="repo-folder-name"
                                />
                            </div>
                            
                            {#if projectTreeData.filter(f => f.type === 'folder').length > 0}
                                <div class="mb-3">
                                    <label for="repo-parent-folder-select" class="block text-sm font-medium text-gray-700 mb-2">
                                        Parent Folder (Optional)
                                    </label>
                                    <select 
                                        bind:value={selectedParentFolder}
                                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                        id="repo-parent-folder-select"
                                    >
                                        <option value={null}>None (Create at root level)</option>
                                        {#each getFlattenedFolders(repoTreeData) as folder}
                                            <option value={folder}>
                                                {'  '.repeat(folder.depth)}📁 {folder.name}
                                            </option>
                                        {/each}
                                    </select>
                                </div>
                            {/if}
                            
                            <div class="flex justify-end space-x-2">
                                <button
                                    on:click={() => { 
                                        showNewFolderInput = false; 
                                        newFolderName = ''; 
                                        selectedParentFolder = null;
                                    }}
                                    class="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                                >
                                    Cancel
                                </button>
                                <button
                                    on:click={createNewFolderInModal}
                                    disabled={!newFolderName.trim()}
                                    class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                >
                                    Create
                                </button>
                            </div>
                        </div>
                    {/if}
                    
                    <div class="max-h-64 overflow-y-auto space-y-2">
                        {#if repoTreeData.length === 0}
                            <div class="text-center py-8 text-gray-500">
                                <svg class="w-12 h-12 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                </svg>
                                <p class="text-sm">No folders yet</p>
                                <p class="text-xs text-gray-400 mt-1">Create a folder to organize your repositories</p>
                            </div>
                        {:else}
                            {#each getFlattenedFolders(repoTreeData) as folder}
                                <button 
                                    class="w-full p-3 border rounded cursor-pointer transition-colors duration-200 text-left {
                                        selectedRepoFolder?.id === folder.id 
                                        ? 'bg-blue-100 border-blue-500 text-blue-900' 
                                        : 'bg-white border-gray-200 hover:bg-gray-50'
                                    }"
                                    on:click={() => selectedRepoFolder = folder}
                                >
                                    <div class="flex items-center space-x-2">
                                        <div style="margin-left: {folder.depth * 16}px" class="flex items-center space-x-2">
                                            <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                                            </svg>
                                            <span class="text-sm font-medium">{folder.name}</span>
                                            {#if selectedProjectFolder?.id === folder.id}
                                                <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                                </svg>
                                            {/if}
                                        </div>
                                    </div>
                                    <div class="text-xs text-gray-500 mt-1" style="margin-left: {folder.depth * 16 + 28}px">
                                        {countWorkflowsInFolder(folder)} items
                                    </div>
                                </button>
                            {/each}
                        {/if}
                    </div>
                </div>
                
                <!-- Repository Preview -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h4 class="text-md font-medium text-gray-900 mb-4">📦 Repository Preview</h4>
                    {#if selectedRepoToAdd}
                        <div class="bg-white rounded border p-4">
                            <div class="flex items-center space-x-3 mb-3">
                                <div class="flex-shrink-0 h-10 w-10">
                                    <div class="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                                        <svg class="h-5 w-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                                        </svg>
                                    </div>
                                </div>
                                <div class="flex-1">
                                    <div class="text-sm font-medium text-gray-900">{selectedRepoToAdd.name}</div>
                                    {#if selectedRepoToAdd.private}
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                            Private
                                        </span>
                                    {:else}
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                            Public
                                        </span>
                                    {/if}
                                </div>
                            </div>
                            
                            {#if selectedRepoToAdd.description}
                                <p class="text-sm text-gray-600 mb-3">{selectedRepoToAdd.description}</p>
                            {/if}
                            
                            <div class="space-y-2">
                                {#if selectedRepoToAdd.language}
                                    <div class="text-xs text-gray-600 flex items-center">
                                        <span class="w-3 h-3 rounded-full bg-blue-500 mr-2"></span>
                                        <span class="font-medium">Language:</span>
                                        <span class="ml-1">{selectedRepoToAdd.language}</span>
                                    </div>
                                {/if}
                                
                                <div class="text-xs text-gray-600">
                                    <span class="font-medium">⭐ Stars:</span> {selectedRepoToAdd.stargazers_count || 0}
                                    <span class="ml-3 font-medium">🍴 Forks:</span> {selectedRepoToAdd.forks_count || 0}
                                </div>
                                
                                <div class="text-xs text-gray-600">
                                    <span class="font-medium">Workflows:</span> 
                                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 ml-1">
                                        {selectedRepoToAdd.workflow_count || 0} workflows
                                    </span>
                                </div>
                                
                                {#if selectedRepoToAdd.updated_at}
                                    <div class="text-xs text-gray-600">
                                        <span class="font-medium">Last updated:</span>
                                        <span class="ml-1">{new Date(selectedRepoToAdd.updated_at).toLocaleDateString()}</span>
                                    </div>
                                {/if}
                            </div>
                            
                            <div class="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                                <div class="flex items-start text-blue-800">
                                    <svg class="w-4 h-4 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <div>
                                        <p class="text-sm font-medium">What will be added?</p>
                                        <p class="text-xs mt-1">
                                            The entire repository folder structure will be created, including all {selectedRepoToAdd.workflow_count || 0} workflows as children.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        {#if selectedRepoFolder}
                            <div class="mt-4 p-3 bg-green-50 border border-green-200 rounded">
                                <div class="flex items-center text-green-800">
                                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <span class="text-sm font-medium">Ready to add</span>
                                </div>
                                <p class="text-sm text-green-700 mt-1">
                                    This repository will be added to the "<span class="font-medium">{selectedRepoFolder.name}</span>" folder.
                                </p>
                            </div>
                        {:else}
                            <div class="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                                <div class="flex items-center text-yellow-800">
                                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                    </svg>
                                    <span class="text-sm font-medium">Select a folder</span>
                                </div>
                                <p class="text-sm text-yellow-700 mt-1">
                                    Please select a folder where you want to add this repository, or create a new one.
                                </p>
                            </div>
                        {/if}
                    {/if}
                </div>
            </div>
            
            <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-200">
                <button
                    on:click={closeAddRepoToProjectModal}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                >
                    Cancel
                </button>
                <button
                    on:click={addRepositoryToProject}
                    disabled={!selectedRepoFolder || !selectedRepoToAdd || addingRepoToProject}
                    class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                    {#if addingRepoToProject}
                        <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Adding Repository...</span>
                    {:else}
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                        </svg>
                        <span>Add Repository to Project</span>
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}
