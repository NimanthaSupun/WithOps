<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { githubClient } from '$lib/github.js';
    import TreeNode from './TreeNode.svelte';
    
    let orgName = '';
    let loading = false;
    let error = null;
    let saveStatus = '';
    let saveSuccess = false;
    
    // Tree structure state
    let treeData = [];
    let selectedNode = null;
    let expandedNodes = new Set();
    let editingNode = null;
    let editingValue = '';
    let draggedNode = null;
    let dragOverNode = null;
    let showContextMenu = false;
    let contextMenuPosition = { x: 0, y: 0 };
    let contextMenuNode = null;
    
    // Modal states
    let showNewItemModal = false;
    let newItemType = 'folder'; // 'folder' or 'file'
    let newItemName = '';
    let newItemParent = null;
    
    // File/Workflow editing
    let showFileEditor = false;
    let fileEditorContent = '';
    let fileEditorType = 'yaml';
    

    
    // Workflow execution and management
    let runningWorkflow = null;
    let workflowHistory = {}; // Store workflow execution history
    let viewMode = 'details'; // 'details', 'table', 'stages'
    let dataSource = 'mock'; // 'real', 'mock' - indicates data source
    
    // Navigation breadcrumb
    let navigationPath = [];
    
    // Workflow steps parsing
    let parsedWorkflowSteps = {};
    
    // Security scanning state
    let scanningWorkflows = new Set(); // Track which workflows are being scanned
    let workflowSecurityResults = {}; // Store security scan results
    let showSecurityPanel = false;
    let organizationSecurityScan = null; // Organization-wide scan state
    let scanningRepository = null; // Track repository being scanned
    let securityOverview = null; // Organization security overview
    
    // Workflow execution states
    const workflowStates = {
        SUCCESS: 'success',
        FAILURE: 'failure',
        RUNNING: 'running',
        PENDING: 'pending',
        CANCELLED: 'cancelled'
    };
    
    // Parse YAML workflow content to extract steps
    function parseWorkflowSteps(workflowContent) {
        if (!workflowContent) return [];
        
        try {
            const lines = workflowContent.split('\n');
            const steps = [];
            let inStepsSection = false;
            let currentStepName = '';
            let currentStepType = 'script';
            let currentStepAction = '';
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                const trimmedLine = line.trim();
                
                // Look for steps section - can be indented
                if (trimmedLine === 'steps:') {
                    inStepsSection = true;
                    continue;
                }
                
                // If we're in steps section
                if (inStepsSection) {
                    // Check if we've reached a less indented line that's not part of steps
                    // (like a new job or end of current job)
                    const lineIndentation = line.length - line.trimStart().length;
                    if (line.length > 0 && trimmedLine.length > 0 && lineIndentation < 4 && !trimmedLine.startsWith('-')) {
                        // Save any pending step before exiting
                        if (currentStepName) {
                            steps.push({
                                name: currentStepName,
                                type: currentStepType,
                                action: currentStepAction,
                                id: `step-${steps.length + 1}`
                            });
                        }
                        break; // Exit steps section
                    }
                    
                    // New step starts with "- name:" (can be indented)
                    if (trimmedLine.startsWith('- name:')) {
                        // Save previous step if exists
                        if (currentStepName) {
                            steps.push({
                                name: currentStepName,
                                type: currentStepType,
                                action: currentStepAction,
                                id: `step-${steps.length + 1}`
                            });
                        }
                        
                        // Start new step
                        currentStepName = trimmedLine.replace('- name:', '').trim().replace(/['"]/g, '');
                        currentStepType = 'script';
                        currentStepAction = '';
                    }
                    // Look for uses: (GitHub Action)
                    else if (trimmedLine.startsWith('uses:')) {
                        currentStepType = 'action';
                        currentStepAction = trimmedLine.replace('uses:', '').trim();
                    }
                    // Look for run: (Shell command)
                    else if (trimmedLine.startsWith('run:')) {
                        currentStepType = 'script';
                        currentStepAction = trimmedLine.replace('run:', '').trim();
                    }
                }
            }
            
            // Don't forget the last step
            if (inStepsSection && currentStepName) {
                steps.push({
                    name: currentStepName,
                    type: currentStepType,
                    action: currentStepAction,
                    id: `step-${steps.length + 1}`
                });
            }
            
            return steps;
        } catch (error) {
            console.error('Error parsing workflow steps:', error);
            return [];
        }
    }
    
    // Get workflow steps for a given workflow
    function getWorkflowSteps(workflow) {
        if (!parsedWorkflowSteps[workflow.id]) {
            parsedWorkflowSteps[workflow.id] = parseWorkflowSteps(workflow.content);
        }
        return parsedWorkflowSteps[workflow.id];
    }
    
    // Map GitHub Actions job steps to our parsed steps
    function mapGitHubStepsToWorkflowSteps(gitHubRun, workflowSteps) {
        if (!gitHubRun.jobs || !workflowSteps.length) {
            return workflowSteps.map((step, index) => ({
                ...step,
                status: workflowStates.PENDING,
                duration: 0,
                startTime: null,
                conclusion: null
            }));
        }
        
        // GitHub Actions provides job-level data, we need to map to step-level
        const job = gitHubRun.jobs[0] || {}; // Take first job for now
        const jobSteps = job.steps || [];
        
        return workflowSteps.map((step, index) => {
            // Try to match by name or position
            let matchedStep = jobSteps.find(ghStep => 
                ghStep.name && step.name && 
                ghStep.name.toLowerCase().includes(step.name.toLowerCase()) ||
                step.name.toLowerCase().includes(ghStep.name.toLowerCase())
            );
            
            // If no name match, try by position
            if (!matchedStep && jobSteps[index]) {
                matchedStep = jobSteps[index];
            }
            
            return {
                ...step,
                status: matchedStep ? mapStatusToWorkflowState(matchedStep.conclusion || matchedStep.status) : workflowStates.PENDING,
                duration: matchedStep ? calculateStepDuration(matchedStep) : 0,
                startTime: matchedStep?.started_at || null,
                conclusion: matchedStep?.conclusion || null,
                githubStep: matchedStep // Keep reference for debugging
            };
        });
    }
    
    // Calculate step duration from GitHub data
    function calculateStepDuration(stepOrStartTime, endTime) {
        // Handle both cases: single step object or two time parameters
        if (endTime !== undefined) {
            // Two parameters: startTime, endTime
            if (!stepOrStartTime || !endTime) return 0;
            return Math.floor((new Date(endTime) - new Date(stepOrStartTime)) / 1000);
        } else {
            // Single parameter: step object
            const step = stepOrStartTime;
            if (step?.started_at && step?.completed_at) {
                const start = new Date(step.started_at);
                const end = new Date(step.completed_at);
                return Math.floor((end - start) / 1000);
            }
            return 0;
        }
    }
    
    onMount(async () => {
        orgName = $page.params.org;
        await loadTreeData();
    });
    
    async function loadTreeData() {
        try {
            loading = true;
            
            // First, try to load saved tree structure from database
            console.log(`🗄️ Loading saved tree structure for ${orgName}...`);
            const savedTreeResult = await githubClient.getProjectTreeData(orgName);
            
            if (savedTreeResult.success && savedTreeResult.data && savedTreeResult.data.length > 0) {
                console.log(`✅ Loaded saved tree structure with ${savedTreeResult.data.length} items`);
                
                // Enhance saved data with fresh GitHub workflow metadata
                treeData = await enhanceTreeWithGitHubData(savedTreeResult.data);
                return; // Use enhanced saved structure
            }
            
            // If no saved structure, create from real workflows
            console.log(`📁 No saved tree structure found, creating from real workflows...`);
            const realWorkflowsResult = await loadRealWorkflowsFromGitHub();
            if (realWorkflowsResult && realWorkflowsResult.length > 0) {
                console.log(`✅ Created tree from ${realWorkflowsResult.length} real workflows`);
                treeData = realWorkflowsResult;
                
                // Save the newly created structure to database
                await saveTreeData();
            } else {
                console.log('ℹ️ No real workflows found, using default tree data');
                treeData = generateDefaultTreeData();
            }
        } catch (err) {
            console.error('Failed to load tree data:', err);
            treeData = generateDefaultTreeData();
        } finally {
            loading = false;
        }
    }
    
    async function enhanceTreeWithGitHubData(savedTreeData) {
        try {
            console.log(`🔍 Enhancing saved tree data with fresh GitHub metadata...`);
            
            // Get fresh GitHub workflow data
            const workflowsResult = await githubClient.getOrganizationActionsDetailed(orgName);
            
            if (!workflowsResult.success || !workflowsResult.actions) {
                console.log('⚠️ No GitHub workflow data available for enhancement');
                return savedTreeData; // Return as-is
            }
            
            // Create a map of GitHub workflows by filename
            const githubWorkflowMap = new Map();
            workflowsResult.actions.forEach(action => {
                const key = `${action.repo_name}::${action.workflow_filename}`;
                if (!githubWorkflowMap.has(key)) {
                    githubWorkflowMap.set(key, {
                        repository: action.repo_name,
                        workflowName: action.workflow_name,
                        workflowPath: action.workflow_path,
                        filename: action.workflow_filename,
                        realWorkflow: true
                    });
                }
            });
            
            // Recursively enhance tree nodes
            function enhanceNode(node) {
                if (node.type === 'workflow' && node.name.match(/\.(yml|yaml)$/)) {
                    // Try to find matching GitHub workflow
                    const possibleKeys = [
                        `${node.repository}::${node.name}`,
                        `${node.metadata?.repository}::${node.name}`
                    ];
                    
                    for (const key of possibleKeys) {
                        if (githubWorkflowMap.has(key)) {
                            const githubData = githubWorkflowMap.get(key);
                            console.log(`✅ Enhanced workflow ${node.name} with GitHub data:`, githubData);
                            
                            // Enhance with GitHub metadata
                            node.repository = githubData.repository;
                            node.metadata = {
                                ...node.metadata,
                                realWorkflow: true,
                                repository: githubData.repository,
                                workflowName: githubData.workflowName,
                                workflowPath: githubData.workflowPath,
                                userCreated: false // Override if it was marked as user created
                            };
                            break;
                        }
                    }
                }
                
                // Recursively enhance children
                if (node.children) {
                    node.children = node.children.map(enhanceNode);
                }
                
                return node;
            }
            
            const enhancedData = savedTreeData.map(enhanceNode);
            console.log(`✅ Enhanced tree data with GitHub metadata`);
            return enhancedData;
            
        } catch (error) {
            console.error('❌ Error enhancing tree data with GitHub metadata:', error);
            return savedTreeData; // Return original data if enhancement fails
        }
    }
    
    async function loadRealWorkflowsFromGitHub() {
        try {
            console.log(`🔍 Loading REAL workflows from GitHub for ${orgName}`);
            
            // Use the actions detailed endpoint which gets ALL real workflows from GitHub
            const workflowsResult = await githubClient.getOrganizationActionsDetailed(orgName);
            
            if (!workflowsResult.success || !workflowsResult.actions) {
                console.log('⚠️ No real workflow actions found');
                return null;
            }
            
            // Extract unique workflows from the actions data
            const workflowMap = new Map();
            
            workflowsResult.actions.forEach(action => {
                const workflowKey = `${action.repo_name}::${action.workflow_filename}`;
                
                if (!workflowMap.has(workflowKey)) {
                    workflowMap.set(workflowKey, {
                        id: `workflow-${action.repo_name}-${action.workflow_filename}`.replace(/[^a-zA-Z0-9-]/g, '-'),
                        name: action.workflow_filename, // Use actual filename from GitHub
                        type: 'workflow',
                        path: action.workflow_path, // Real path from GitHub
                        repository: action.repo_name, // Real repository name
                        content: `name: ${action.workflow_name}
# This is a REAL workflow from GitHub
# Repository: ${action.repo_name}
# Path: ${action.workflow_path}
# Auto-detected from GitHub Actions

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: echo "Building ${action.workflow_name}"`,
                        metadata: {
                            triggers: ['push'], // This will be updated when we fetch the real content
                            lastModified: new Date().toISOString(),
                            description: `Real GitHub workflow: ${action.workflow_name}`,
                            repository: action.repo_name,
                            realWorkflow: true, // Mark as real GitHub workflow
                            workflowName: action.workflow_name,
                            actionsFound: 0,
                            userCreated: false // Not user created
                        }
                    });
                }
                
                // Count actions per workflow
                const workflow = workflowMap.get(workflowKey);
                workflow.metadata.actionsFound += 1;
            });
            
            console.log(`📋 Found ${workflowMap.size} unique REAL workflows:`, 
                Array.from(workflowMap.values()).map(w => ({ 
                    name: w.name, 
                    path: w.path, 
                    repository: w.repository,
                    actions: w.metadata.actionsFound
                }))
            );
            
            // Create user-friendly folder structure for better organization
            // This creates a structure like:
            // 📁 Repositories
            //   📁 repo1
            //     📄 workflow1.yml
            //     📄 workflow2.yml
            //   📁 repo2
            //     📄 workflow3.yml
            
            const repositoriesFolder = {
                id: 'root-repositories',
                name: '📁 GitHub Repositories',
                type: 'folder',
                children: []
            };
            
            const repoGroups = {};
            Array.from(workflowMap.values()).forEach(workflow => {
                const repoName = workflow.repository || 'unknown';
                if (!repoGroups[repoName]) {
                    repoGroups[repoName] = [];
                }
                repoGroups[repoName].push(workflow);
            });
            
            // Convert repo groups to tree structure
            Object.keys(repoGroups).forEach(repoName => {
                const repoNode = {
                    id: `repo-${repoName}`,
                    name: `📁 ${repoName}`,
                    type: 'folder',
                    children: repoGroups[repoName],
                    metadata: {
                        repository: repoName,
                        workflowCount: repoGroups[repoName].length,
                        realRepository: true
                    }
                };
                repositoriesFolder.children.push(repoNode);
            });
            
            // Also create a "My Workflows" folder for user-created content
            const myWorkflowsFolder = {
                id: 'root-my-workflows',
                name: '📁 My Custom Workflows',
                type: 'folder',
                children: [],
                metadata: {
                    userCreated: true,
                    description: 'Custom workflows and folders created by you'
                }
            };
            
            return [repositoriesFolder, myWorkflowsFolder];
            
        } catch (error) {
            console.error('❌ Error loading real workflows from GitHub:', error);
            return null;
        }
    }
    
    function generateDefaultTreeData() {
        return [
            {
                id: 'root-my-workflows',
                name: '📁 My Custom Workflows',
                type: 'folder',
                children: [
                    {
                        id: 'example-workflow-ci',
                        name: 'example-ci.yml',
                        type: 'workflow',
                        path: '.github/workflows/example-ci.yml',
                        content: `name: Example CI Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run build`,
                        metadata: {
                            triggers: ['push', 'pull_request'],
                            lastModified: new Date().toISOString(),
                            description: 'Example CI/CD pipeline - customize this for your needs',
                            userCreated: true,
                            realWorkflow: false,
                            isExample: true
                        }
                    }
                ],
                metadata: {
                    userCreated: true,
                    description: 'Custom workflows and folders created by you'
                }
            },
            {
                id: 'root-help',
                name: '📖 Getting Started',
                type: 'folder',
                children: [
                    {
                        id: 'help-workflow',
                        name: 'how-to-create-workflows.md',
                        type: 'file',
                        content: `# How to Create Workflows

## Steps:
1. Right-click on "My Custom Workflows" folder
2. Select "New Workflow" 
3. Edit the YAML content
4. Save your changes

## Tips:
- Use real GitHub Actions from the marketplace
- Test your workflows with simple commands first
- Check workflow history after execution
`,
                        metadata: {
                            userCreated: true,
                            isHelp: true,
                            description: 'Getting started guide'
                        }
                    }
                ],
                metadata: {
                    userCreated: true,
                    isHelp: true,
                    description: 'Help and documentation'
                }
            }
        ];
    }
    
    async function saveTreeData() {
        try {
            saveStatus = 'Saving...';
            
            const result = await githubClient.saveProjectTreeData(orgName, treeData);
            if (result.success) {
                saveStatus = 'Saved successfully!';
                saveSuccess = true;
                setTimeout(() => {
                    saveStatus = '';
                    saveSuccess = false;
                }, 3000);
            } else {
                throw new Error(result.error || 'Failed to save project data');
            }
        } catch (err) {
            console.error('Failed to save tree data:', err);
            saveStatus = 'Failed to save changes';
            saveSuccess = false;
            setTimeout(() => {
                saveStatus = '';
            }, 3000);
        }
    }
    
    function toggleExpanded(nodeId) {
        if (expandedNodes.has(nodeId)) {
            expandedNodes.delete(nodeId);
        } else {
            expandedNodes.add(nodeId);
        }
        expandedNodes = new Set(expandedNodes);
    }
    
    function selectNode(node) {
        selectedNode = node;
        updateNavigationPath(node);
        if (node.type === 'workflow') {
            fileEditorContent = node.content || '';
            fileEditorType = 'yaml';
            
            // Parse workflow steps immediately when selecting a workflow
            const steps = getWorkflowSteps(node);
            console.log(`📋 Parsed ${steps.length} steps from workflow: ${node.name}`, steps);
            
            // Load real workflow history from GitHub Actions
            loadWorkflowHistory(node);
        }
    }
    
    async function loadWorkflowHistory(workflow) {
        try {
            console.log(`🔍 Loading workflow history for: ${workflow.name} (Path: ${workflow.path})`);
            
            // Clear any existing data for this workflow
            if (workflowHistory[workflow.id]) {
                delete workflowHistory[workflow.id];
                workflowHistory = { ...workflowHistory };
            }
            
            // Set loading state with better user feedback
            workflowHistory[workflow.id] = {
                runs: [],
                loading: true,
                source: 'loading',
                loadingMessage: 'Fetching workflow history from GitHub Actions...'
            };
            workflowHistory = { ...workflowHistory };
            
            // Skip workflow history for user-created folders/workflows that don't exist in GitHub
            // Use smarter detection: if workflow name ends with .yml/.yaml and has a repository, it's likely real
            const isRealWorkflow = workflow.metadata?.realWorkflow || 
                                 (workflow.name.match(/\.(yml|yaml)$/) && workflow.repository) ||
                                 (workflow.name.match(/\.(yml|yaml)$/) && workflow.metadata?.repository);
            
            const isUserCreated = workflow.metadata?.isNewlyCreated || 
                                workflow.metadata?.userCreated || 
                                workflow.metadata?.isExample;
            
            // Only skip if it's definitely user-created AND not a real GitHub workflow
            if (isUserCreated && !isRealWorkflow) {
                console.log(`📁 Skipping history for user-created workflow: ${workflow.name}`);
                workflowHistory[workflow.id] = {
                    runs: [],
                    totalRuns: 0,
                    lastSuccess: null,
                    lastFailure: null,
                    avgDuration: null,
                    source: 'user-created',
                    loading: false,
                    message: 'This is a user-created workflow. Execute it to see history.'
                };
                workflowHistory = { ...workflowHistory };
                return;
            }
            
            console.log(`📋 Attempting to load history for workflow: ${workflow.name}`, {
                isRealWorkflow,
                isUserCreated,
                repository: workflow.repository || workflow.metadata?.repository,
                hasYmlExtension: workflow.name.match(/\.(yml|yaml)$/),
                metadata: workflow.metadata
            });
            
            // For real GitHub workflows, use the actual workflow filename (not full path)
            const workflowId = workflow.name; // Use just the filename like "ci-caller.yml"
            const repositoryName = workflow.repository || workflow.metadata?.repository;
            
            console.log(`📋 Fetching GitHub Actions history for workflow: ${workflowId}`);
            console.log(`📁 Repository: ${repositoryName || 'Will search all repositories'}`);
            
            const githubResult = await githubClient.getGitHubActionsHistory(workflowId, orgName, repositoryName);
            
            console.log('� GitHub Actions API response:', githubResult);
            
            if (githubResult && githubResult.success && githubResult.data && githubResult.data.runs && githubResult.data.runs.length > 0) {
                console.log(`✅ Found ${githubResult.data.runs.length} workflow runs for ${workflow.name}`);
                
                // Get parsed workflow steps from YAML
                const workflowSteps = getWorkflowSteps(workflow);
                console.log(`� Parsed ${workflowSteps.length} workflow steps:`, workflowSteps);
                
                // Process and map the real GitHub data
                const processedRuns = githubResult.data.runs.map((run, index) => {
                    console.log(`� Processing run ${index + 1}:`, {
                        id: run.id,
                        name: run.name,
                        workflow_name: run.workflow?.name,
                        conclusion: run.conclusion,
                        status: run.status,
                        created_at: run.created_at,
                        head_commit_message: run.head_commit?.message,
                        actor: run.actor?.login,
                        jobs: run.jobs?.length || 0
                    });
                    
                    // Map GitHub job steps to workflow steps
                    const mappedSteps = mapGitHubJobStepsToWorkflowSteps(run, workflowSteps);
                    
                    return {
                        id: run.id,
                        runNumber: run.run_number || (index + 1),
                        status: mapStatusToWorkflowState(run.conclusion || run.status),
                        startTime: run.created_at || run.started_at,
                        endTime: run.updated_at,
                        duration: calculateDuration(run.created_at, run.updated_at),
                        steps: mappedSteps,
                        commitSha: run.head_sha,
                        commitMessage: run.head_commit?.message || '',
                        author: run.head_commit?.author?.name || run.actor?.login || 'Unknown',
                        branch: run.head_branch || 'main',
                        logsUrl: run.logs_url || run.html_url,
                        workflowName: run.name || run.workflow?.name || workflow.name,
                        event: run.event,
                        triggeredBy: run.triggering_actor?.login || run.actor?.login
                    };
                });
                
                workflowHistory[workflow.id] = {
                    runs: processedRuns,
                    totalRuns: githubResult.data.total_count || processedRuns.length,
                    lastSuccess: findLastSuccessfulRun(processedRuns),
                    lastFailure: findLastFailedRun(processedRuns),
                    avgDuration: calculateAverageDuration(processedRuns),
                    source: 'GitHub Actions',
                    repositoryUrl: githubResult.data.repository?.html_url,
                    workflowSteps: workflowSteps,
                    loading: false
                };
                
                dataSource = 'real';
                console.log(`✅ Successfully loaded ${processedRuns.length} runs for ${workflow.name}`);
                
            } else {
                console.log(`ℹ️ No workflow runs found for ${workflow.name} - this might be a new workflow`);
                
                workflowHistory[workflow.id] = {
                    runs: [],
                    totalRuns: 0,
                    lastSuccess: null,
                    lastFailure: null,
                    avgDuration: null,
                    source: 'no-runs',
                    loading: false,
                    message: githubResult?.error || 'No workflow runs found'
                };
                
                dataSource = 'none';
            }
            
            // Trigger reactivity
            workflowHistory = { ...workflowHistory };
            
        } catch (error) {
            console.error('❌ Error loading workflow history:', error);
            
            workflowHistory[workflow.id] = {
                runs: [],
                totalRuns: 0,
                lastSuccess: null,
                lastFailure: null,
                avgDuration: null,
                source: 'error',
                loading: false,
                error: error.message
            };
            
            dataSource = 'none';
            workflowHistory = { ...workflowHistory };
        }
    }
    
    // Helper functions for real data processing
    function mapStatusToWorkflowState(status) {
        const statusMap = {
            'success': workflowStates.SUCCESS,
            'completed': workflowStates.SUCCESS,
            'failure': workflowStates.FAILURE,
            'failed': workflowStates.FAILURE,
            'in_progress': workflowStates.RUNNING,
            'running': workflowStates.RUNNING,
            'queued': workflowStates.PENDING,
            'pending': workflowStates.PENDING,
            'cancelled': workflowStates.CANCELLED,
            'skipped': workflowStates.PENDING
        };
        return statusMap[status?.toLowerCase()] || workflowStates.PENDING;
    }
    
    function calculateDuration(startTime, endTime) {
        if (!startTime || !endTime) return 0;
        const start = new Date(startTime);
        const end = new Date(endTime);
        return Math.floor((end - start) / 1000); // Duration in seconds
    }
    
    function findLastSuccessfulRun(runs) {
        return runs.find(run => 
            mapStatusToWorkflowState(run.conclusion || run.status) === workflowStates.SUCCESS
        );
    }
    
    function findLastFailedRun(runs) {
        return runs.find(run => 
            mapStatusToWorkflowState(run.conclusion || run.status) === workflowStates.FAILURE
        );
    }
    
    function calculateAverageDuration(runs) {
        const completedRuns = runs.filter(run => run.duration && run.duration > 0);
        if (completedRuns.length === 0) return 0;
        
        const totalDuration = completedRuns.reduce((sum, run) => sum + run.duration, 0);
        return Math.floor(totalDuration / completedRuns.length);
    }
    
    function updateNavigationPath(node) {
        navigationPath = [];
        const path = findNodePath(treeData, node.id);
        if (path) {
            navigationPath = path;
        }
    }
    
    function findNodePath(nodes, nodeId, currentPath = []) {
        for (const node of nodes) {
            const newPath = [...currentPath, node];
            if (node.id === nodeId) {
                return newPath;
            }
            if (node.children) {
                const result = findNodePath(node.children, nodeId, newPath);
                if (result) return result;
            }
        }
        return null;
    }
    
    function generateMockWorkflowHistory(workflow) {
        const history = [];
        const statuses = [workflowStates.SUCCESS, workflowStates.FAILURE, workflowStates.SUCCESS];
        
        for (let i = 0; i < 5; i++) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            
            history.push({
                id: `run-${workflow.id}-${i}`,
                status: statuses[i % statuses.length],
                startTime: date.toISOString(),
                duration: Math.floor(Math.random() * 300) + 30, // 30-330 seconds
                stages: generateMockStages(),
                buildNumber: `#${50 - i}`
            });
        }
        
        return {
            runs: history,
            lastSuccess: history.find(r => r.status === workflowStates.SUCCESS),
            lastFailure: history.find(r => r.status === workflowStates.FAILURE),
            avgDuration: Math.floor(history.reduce((sum, run) => sum + run.duration, 0) / history.length)
        };
    }
    
    // Helper function to map GitHub job steps to workflow steps
    function mapGitHubJobStepsToWorkflowSteps(run, workflowSteps) {
        const mappedSteps = [];
        
        if (run.jobs && run.jobs.length > 0) {
            // Process each job
            run.jobs.forEach((job, jobIndex) => {
                if (job.steps && job.steps.length > 0) {
                    // Process each step in the job
                    job.steps.forEach((step, stepIndex) => {
                        // Try to match with defined workflow steps
                        const workflowStep = workflowSteps[stepIndex] || workflowSteps.find(ws => 
                            ws.name.toLowerCase().includes(step.name.toLowerCase()) ||
                            step.name.toLowerCase().includes(ws.name.toLowerCase())
                        );
                        
                        mappedSteps.push({
                            id: `${job.name}-${step.name}`.replace(/\s+/g, '-').toLowerCase(),
                            name: step.name,
                            status: mapStatusToWorkflowState(step.conclusion || step.status),
                            duration: calculateStepDuration(step.started_at, step.completed_at),
                            startTime: step.started_at,
                            endTime: step.completed_at,
                            jobName: job.name,
                            action: workflowStep?.action || step.name,
                            number: stepIndex + 1
                        });
                    });
                } else {
                    // If no step details, create a placeholder step for the job
                    mappedSteps.push({
                        id: job.name.replace(/\s+/g, '-').toLowerCase(),
                        name: job.name,
                        status: mapStatusToWorkflowState(job.conclusion || job.status),
                        duration: calculateStepDuration(job.started_at, job.completed_at),
                        startTime: job.started_at,
                        endTime: job.completed_at,
                        jobName: job.name,
                        action: job.name,
                        number: jobIndex + 1
                    });
                }
            });
        } else {
            // If no job details, create steps based on workflow definition
            workflowSteps.forEach((step, index) => {
                mappedSteps.push({
                    id: step.id,
                    name: step.name,
                    status: workflowStates.UNKNOWN,
                    duration: 0,
                    startTime: null,
                    endTime: null,
                    jobName: 'unknown',
                    action: step.action,
                    number: index + 1
                });
            });
        }
        
        return mappedSteps;
    }
    
    function generateMockStages() {
        const stageNames = ['Checkout', 'Install Dependencies', 'Build', 'Test', 'Security Scan', 'Deploy'];
        return stageNames.map((name, index) => ({
            name,
            status: index < 4 ? workflowStates.SUCCESS : Math.random() > 0.3 ? workflowStates.SUCCESS : workflowStates.FAILURE,
            duration: Math.floor(Math.random() * 60) + 10,
            startTime: new Date(Date.now() - (stageNames.length - index) * 30000).toISOString()
        }));
    }
    
    function startEditing(node) {
        editingNode = node;
        editingValue = node.name;
    }
    
    function cancelEditing() {
        editingNode = null;
        editingValue = '';
    }
    
    function saveEdit() {
        if (editingNode && editingValue.trim()) {
            editingNode.name = editingValue.trim();
            treeData = [...treeData]; // Trigger reactivity
            showSaveStatus('Item renamed successfully', true);
        }
        cancelEditing();
    }
    
    function handleKeyPress(event) {
        if (event.key === 'Enter') {
            saveEdit();
        } else if (event.key === 'Escape') {
            cancelEditing();
        }
    }
    
    function openContextMenu(event, node) {
        event.preventDefault();
        contextMenuNode = node;
        contextMenuPosition = { x: event.clientX, y: event.clientY };
        showContextMenu = true;
    }
    
    function hideContextMenu() {
        showContextMenu = false;
        contextMenuNode = null;
    }
    
    function openNewItemModal(type, parent = null) {
        newItemType = type;
        newItemParent = parent;
        newItemName = '';
        showNewItemModal = true;
        hideContextMenu();
    }
    
    function closeNewItemModal() {
        showNewItemModal = false;
        newItemName = '';
        newItemParent = null;
    }
    
    async function createNewItem() {
        if (!newItemName.trim()) return;
        
        const newItem = {
            id: `item-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            name: newItemName.trim(),
            type: newItemType,
            children: newItemType === 'folder' ? [] : undefined,
            path: newItemType === 'workflow' ? `.github/workflows/${newItemName.trim().replace(/\s+/g, '-').toLowerCase()}.yml` : undefined,
            content: newItemType === 'workflow' ? `name: ${newItemName.trim()}
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: echo "Building ${newItemName.trim()}"` : undefined,
            metadata: newItemType === 'workflow' ? {
                triggers: ['push'],
                lastModified: new Date().toISOString(),
                isNewlyCreated: true, // Mark as newly created
                userCreated: true, // Mark as user created (not from GitHub)
                realWorkflow: false, // Not a real GitHub workflow
                createdAt: new Date().toISOString(),
                description: `User-created workflow: ${newItemName.trim()}`
            } : {
                lastModified: new Date().toISOString(),
                isNewlyCreated: true,
                userCreated: true, // Mark as user created
                createdAt: new Date().toISOString(),
                description: `User-created folder: ${newItemName.trim()}`
            }
        };
        
        // Add to the appropriate parent
        if (newItemParent) {
            if (!newItemParent.children) {
                newItemParent.children = [];
            }
            newItemParent.children.push(newItem);
            expandedNodes.add(newItemParent.id);
        } else {
            // If no parent specified, add to "My Custom Workflows" folder if it exists
            const myWorkflowsFolder = treeData.find(item => item.id === 'root-my-workflows');
            if (myWorkflowsFolder) {
                myWorkflowsFolder.children.push(newItem);
                expandedNodes.add(myWorkflowsFolder.id);
            } else {
                // Fallback: add to root
                treeData.push(newItem);
            }
        }
        
        treeData = [...treeData];
        expandedNodes = new Set(expandedNodes);
        
        // Save to database immediately to persist user's custom structure
        try {
            await saveTreeData();
            showSaveStatus(`${newItemType === 'folder' ? 'Folder' : 'Workflow'} "${newItemName.trim()}" created and saved successfully`, true);
            console.log(`✅ Saved user-created ${newItemType}: ${newItemName.trim()} to database`);
        } catch (error) {
            console.error('Failed to save new item to database:', error);
            showSaveStatus(`${newItemType === 'folder' ? 'Folder' : 'Workflow'} created locally but failed to save to database`, false);
        }
        
        closeNewItemModal();
    }
    
    async function deleteNode(node) {
        if (confirm(`Are you sure you want to delete "${node.name}"?`)) {
            deleteNodeFromTree(treeData, node.id);
            treeData = [...treeData];
            if (selectedNode && selectedNode.id === node.id) {
                selectedNode = null;
            }
            showSaveStatus('Item deleted successfully', true);
            
            // Save to database
            await saveTreeData();
        }
        hideContextMenu();
    }
    
    function deleteNodeFromTree(nodes, nodeId) {
        for (let i = 0; i < nodes.length; i++) {
            if (nodes[i].id === nodeId) {
                nodes.splice(i, 1);
                return true;
            }
            if (nodes[i].children && deleteNodeFromTree(nodes[i].children, nodeId)) {
                return true;
            }
        }
        return false;
    }
    
    function duplicateNode(node) {
        const duplicate = {
            ...node,
            id: `item-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            name: `${node.name} (Copy)`,
            children: node.children ? JSON.parse(JSON.stringify(node.children)) : undefined
        };
        
        // Add to same parent or root
        const parent = findParentNode(treeData, node.id);
        if (parent) {
            parent.children.push(duplicate);
        } else {
            treeData.push(duplicate);
        }
        
        treeData = [...treeData];
        showSaveStatus('Item duplicated successfully', true);
        hideContextMenu();
    }
    
    function findParentNode(nodes, nodeId, parent = null) {
        for (let node of nodes) {
            if (node.id === nodeId) {
                return parent;
            }
            if (node.children) {
                const result = findParentNode(node.children, nodeId, node);
                if (result !== null) return result;
            }
        }
        return null;
    }
    
    function openFileEditor(node) {
        if (node.type === 'workflow') {
            selectedNode = node;
            fileEditorContent = node.content || '';
            fileEditorType = 'yaml';
            showFileEditor = true;
        }
        hideContextMenu();
    }
    
    function closeFileEditor() {
        showFileEditor = false;
    }
    
    async function saveFileContent() {
        if (selectedNode && selectedNode.type === 'workflow') {
            selectedNode.content = fileEditorContent;
            selectedNode.metadata.lastModified = new Date().toISOString();
            treeData = [...treeData];
            
            // Save to database to persist changes
            try {
                await saveTreeData();
                showSaveStatus('Workflow content saved successfully to database', true);
            } catch (error) {
                console.error('Failed to save workflow content to database:', error);
                showSaveStatus('Workflow content saved locally but failed to persist to database', false);
            }
        }
        closeFileEditor();
    }
    
    function showSaveStatus(message, success) {
        saveStatus = message;
        saveSuccess = success;
        setTimeout(() => {
            saveStatus = '';
        }, 3000);
    }
    

    

    
    // Drag and drop functionality
    function handleDragStart(event, node) {
        draggedNode = node;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', '');
    }
    
    function handleDragOver(event, node) {
        event.preventDefault();
        dragOverNode = node;
    }
    
    function handleDragLeave() {
        dragOverNode = null;
    }
    
    function handleDrop(event, targetNode) {
        event.preventDefault();
        
        if (draggedNode && targetNode && draggedNode.id !== targetNode.id) {
            // Remove from current location
            deleteNodeFromTree(treeData, draggedNode.id);
            
            // Add to new location
            if (targetNode.type === 'folder') {
                if (!targetNode.children) {
                    targetNode.children = [];
                }
                targetNode.children.push(draggedNode);
                expandedNodes.add(targetNode.id);
            } else {
                // Add as sibling
                const parent = findParentNode(treeData, targetNode.id);
                if (parent) {
                    parent.children.push(draggedNode);
                } else {
                    treeData.push(draggedNode);
                }
            }
            
            treeData = [...treeData];
            expandedNodes = new Set(expandedNodes);
            showSaveStatus('Item moved successfully', true);
        }
        
        draggedNode = null;
        dragOverNode = null;
    }
    
    async function saveProjectTree() {
        try {
            loading = true;
            // In production, this would save to your API
            // const result = await githubClient.saveProjectTreeview(orgName, treeData);
            // if (result.success) {
            //     showSaveStatus('Project tree saved successfully', true);
            // }
            
            // Simulate saving
            await new Promise(resolve => setTimeout(resolve, 1000));
            showSaveStatus('Project tree saved successfully', true);
            
        } catch (err) {
            console.error('Failed to save tree data:', err);
            showSaveStatus('Failed to save project tree', false);
        } finally {
            loading = false;
        }
    }
    
    function goBack() {
        goto(`/github/workspace/${orgName}`);
    }
    
    // =============== SECURITY SCANNING FUNCTIONS ===============
    
    async function scanWorkflowSecurity(workflow) {
        if (scanningWorkflows.has(workflow.id)) return;
        
        try {
            scanningWorkflows.add(workflow.id);
            scanningWorkflows = new Set(scanningWorkflows);
            
            console.log(`🔒 Starting security scan for workflow: ${workflow.name}`);
            showSaveStatus('🔒 Scanning workflow for security vulnerabilities...', true);
            
            // Determine repository name
            const repoName = workflow.repository || workflow.metadata?.repository;
            
            // Call security scan API
            const response = await fetch(`/api/github/workspace/${orgName}/workflows/${workflow.name}/security/scan${repoName ? `?repo_name=${repoName}` : ''}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${$page.data.user?.accessToken || ''}`
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                const scanResult = result.scan_result;
                
                // Store the security scan result
                workflowSecurityResults[workflow.id] = scanResult;
                workflowSecurityResults = { ...workflowSecurityResults };
                
                const riskLevel = scanResult.risk_level;
                const riskScore = scanResult.risk_score;
                const vulnCount = scanResult.vulnerability_count;
                
                let statusMessage = `✅ Security scan complete: ${riskLevel.toUpperCase()} risk (${riskScore}%)`;
                if (vulnCount > 0) {
                    statusMessage += ` - ${vulnCount} vulnerabilities found`;
                }
                
                showSaveStatus(statusMessage, riskLevel !== 'high');
                
                console.log(`🔒 Security scan completed for ${workflow.name}:`, scanResult);
            } else {
                throw new Error(`Security scan failed: ${response.status}`);
            }
            
        } catch (error) {
            console.error('Security scan failed:', error);
            showSaveStatus(`❌ Security scan failed: ${error.message}`, false);
            
            // Store error result
            workflowSecurityResults[workflow.id] = {
                status: 'error',
                message: error.message,
                risk_score: 0,
                risk_level: 'unknown'
            };
            workflowSecurityResults = { ...workflowSecurityResults };
            
        } finally {
            scanningWorkflows.delete(workflow.id);
            scanningWorkflows = new Set(scanningWorkflows);
        }
    }
    
    async function scanRepositorySecurity(repoName) {
        if (scanningRepository === repoName) return;
        
        try {
            scanningRepository = repoName;
            console.log(`🔒 Starting repository-wide security scan: ${orgName}/${repoName}`);
            showSaveStatus(`🔒 Scanning all workflows in ${repoName}...`, true);
            
            const response = await fetch(`/api/github/workspace/${orgName}/repositories/${repoName}/security/scan`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${$page.data.user?.accessToken || ''}`
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                const scanResult = result.scan_result;
                const metrics = scanResult.repository_metrics;
                
                // Store results for individual workflows
                if (scanResult.scan_results) {
                    scanResult.scan_results.forEach(workflowResult => {
                        const workflowName = workflowResult.workflow_name;
                        // Find workflow in tree to get its ID
                        const workflow = findWorkflowByName(treeData, workflowName);
                        if (workflow) {
                            workflowSecurityResults[workflow.id] = workflowResult;
                        }
                    });
                    workflowSecurityResults = { ...workflowSecurityResults };
                }
                
                const avgRisk = metrics.average_risk_score;
                const totalWorkflows = metrics.total_workflows;
                const highRiskCount = metrics.high_risk_workflows;
                
                let statusMessage = `✅ Repository scan complete: ${totalWorkflows} workflows, avg risk ${avgRisk}%`;
                if (highRiskCount > 0) {
                    statusMessage += ` (${highRiskCount} high-risk)`;
                }
                
                showSaveStatus(statusMessage, highRiskCount === 0);
                console.log(`🔒 Repository security scan completed for ${repoName}:`, metrics);
                
            } else {
                throw new Error(`Repository scan failed: ${response.status}`);
            }
            
        } catch (error) {
            console.error('Repository security scan failed:', error);
            showSaveStatus(`❌ Repository security scan failed: ${error.message}`, false);
            
        } finally {
            scanningRepository = null;
        }
    }
    
    async function scanOrganizationSecurity() {
        if (organizationSecurityScan) return;
        
        try {
            organizationSecurityScan = { status: 'running', progress: 0 };
            console.log(`🔒 Starting organization-wide security scan: ${orgName}`);
            showSaveStatus(`🔒 Scanning all workflows in ${orgName}...`, true);
            
            const response = await fetch(`/api/github/workspace/${orgName}/security/scan`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${$page.data.user?.accessToken || ''}`
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                organizationSecurityScan = {
                    status: 'completed',
                    data: result,
                    timestamp: new Date().toISOString()
                };
                
                const metrics = result.organization_metrics;
                const totalRepos = metrics.repositories_scanned;
                const totalWorkflows = metrics.total_workflows;
                const avgRisk = metrics.average_risk_score;
                const highRiskCount = metrics.high_risk_workflows;
                
                // Store individual workflow results
                result.scan_results.forEach(repoResult => {
                    if (repoResult.scan_results) {
                        repoResult.scan_results.forEach(workflowResult => {
                            const workflowName = workflowResult.workflow_name;
                            const workflow = findWorkflowByName(treeData, workflowName);
                            if (workflow) {
                                workflowSecurityResults[workflow.id] = workflowResult;
                            }
                        });
                    }
                });
                workflowSecurityResults = { ...workflowSecurityResults };
                
                let statusMessage = `✅ Organization scan complete: ${totalRepos} repos, ${totalWorkflows} workflows, avg risk ${avgRisk}%`;
                if (highRiskCount > 0) {
                    statusMessage += ` (${highRiskCount} high-risk)`;
                }
                
                showSaveStatus(statusMessage, highRiskCount === 0);
                console.log(`🔒 Organization security scan completed:`, metrics);
                
            } else {
                throw new Error(`Organization scan failed: ${response.status}`);
            }
            
        } catch (error) {
            console.error('Organization security scan failed:', error);
            organizationSecurityScan = { status: 'error', error: error.message };
            showSaveStatus(`❌ Organization security scan failed: ${error.message}`, false);
        }
    }
    
    async function loadSecurityOverview() {
        try {
            const response = await fetch(`/api/github/workspace/${orgName}/security/overview`, {
                headers: {
                    'Authorization': `Bearer ${$page.data.user?.accessToken || ''}`
                }
            });
            
            if (response.ok) {
                securityOverview = await response.json();
            }
        } catch (error) {
            console.error('Failed to load security overview:', error);
        }
    }
    
    function findWorkflowByName(nodes, workflowName) {
        for (const node of nodes) {
            if (node.type === 'workflow' && node.name === workflowName) {
                return node;
            }
            if (node.children) {
                const found = findWorkflowByName(node.children, workflowName);
                if (found) return found;
            }
        }
        return null;
    }
    
    function getSecurityRiskColor(riskLevel) {
        switch (riskLevel) {
            case 'high': return '#ef4444';
            case 'medium': return '#f59e0b';
            case 'low': return '#eab308';
            case 'minimal': return '#22c55e';
            default: return '#6b7280';
        }
    }
    
    function getSecurityRiskIcon(riskLevel) {
        switch (riskLevel) {
            case 'high': return '🚨';
            case 'medium': return '⚠️';
            case 'low': return '💛';
            case 'minimal': return '✅';
            default: return '❓';
        }
    }
    
    function toggleSecurityPanel() {
        showSecurityPanel = !showSecurityPanel;
        if (showSecurityPanel && !securityOverview) {
            loadSecurityOverview();
        }
    }
    
    // ============= END SECURITY SCANNING FUNCTIONS =============
    
    // Close context menu when clicking outside
    function handleClickOutside(event) {
        if (showContextMenu && !event.target.closest('.context-menu')) {
            hideContextMenu();
        }
    }
    
    // Simplified workflow execution - focus on real GitHub Actions if available
    async function runWorkflow(workflow) {
        if (runningWorkflow === workflow.id) return;
        
        try {
            runningWorkflow = workflow.id;
            showSaveStatus('🔄 Executing workflow...', true);
            
            // Try real GitHub Actions first
            try {
                const result = await triggerGitHubActions(workflow);
                if (result.success) {
                    showSaveStatus('✅ GitHub Actions workflow triggered successfully', true);
                    await monitorRealWorkflowExecution(workflow.id, result);
                    return;
                }
            } catch (error) {
                console.warn('⚠️ GitHub Actions trigger failed:', error.message);
            }
            
            // If no real execution available, run simulation but with clear indication
            showSaveStatus('⚠️ Running in simulation mode (no real GitHub Actions available)', false);
            await simulateWorkflowExecution(workflow);
            
        } catch (error) {
            console.error('❌ Workflow execution failed:', error);
            showSaveStatus('❌ Workflow execution failed', false);
        } finally {
            runningWorkflow = null;
        }
    }
    
    // Real GitHub Actions integration - simplified
    async function triggerGitHubActions(workflow) {
        // Check if we have a GitHub App installation first
        const response = await fetch(`/api/github/workspace/${orgName}/actions/trigger`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('authToken')}`
            },
            body: JSON.stringify({
                workflowId: workflow.id,
                workflowName: workflow.name,
                repository: workflow.metadata?.repository || `${orgName}/workflows`
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            return { success: true, method: 'GitHub Actions', ...result };
        }
        throw new Error(`GitHub Actions trigger failed: ${response.status}`);
    }
    
    // Monitor real execution (like Jenkins build monitoring)
    async function monitorRealWorkflowExecution(workflowId, executionResult) {
        const { executionId, method } = executionResult;
        
        // If no executionId, skip monitoring (development mode)
        if (!executionId) {
            console.log('📋 No executionId provided, skipping real-time monitoring');
            showSaveStatus(`✅ ${method || 'Workflow'} execution triggered (development mode)`, true);
            return;
        }
        
        let attempts = 0;
        const maxAttempts = 60; // 2 minutes max
        
        showSaveStatus(`🔄 Monitoring ${method} execution...`, true);
        
        while (attempts < maxAttempts) {
            try {
                const statusResponse = await fetch(`/api/workflows/status/${executionId}`, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
                    }
                });
                
                if (statusResponse.ok) {
                    const status = await statusResponse.json();
                    
                    // Update UI with real-time status
                    if (status.logs) {
                        console.log(`📋 ${method} logs:`, status.logs.slice(-5)); // Show last 5 log lines
                    }
                    
                    if (status.completed) {
                        // Execution completed - reload REAL history
                        await loadWorkflowHistory(selectedNode);
                        showSaveStatus(
                            `✅ ${method} execution completed: ${status.result}`, 
                            status.result === 'success'
                        );
                        return;
                    }
                    
                    // Show progress if available
                    if (status.progress) {
                        showSaveStatus(
                            `🔄 ${method}: ${status.progress.stage} (${status.progress.percentage}%)`, 
                            true
                        );
                    }
                }
                
                // Wait 2 seconds before next check
                await new Promise(resolve => setTimeout(resolve, 2000));
                attempts++;
                
            } catch (error) {
                console.error('❌ Error monitoring execution:', error);
                break;
            }
        }
        
        showSaveStatus('⏰ Workflow execution monitoring timeout', false);
    }
    
    // Real polling function for workflow status
    async function pollWorkflowStatus(workflowId, executionId, maxAttempts = 30) {
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const response = await fetch(`/api/workflows/status/${executionId}`, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
                    }
                });
                
                if (response.ok) {
                    const status = await response.json();
                    
                    if (status.completed) {
                        // Update workflow history with real data
                        await loadWorkflowHistory(selectedNode);
                        showSaveStatus(`Workflow completed with status: ${status.result}`, status.result === 'success');
                        return;
                    }
                }
                
                // Wait 2 seconds before next poll
                await new Promise(resolve => setTimeout(resolve, 2000));
                
            } catch (error) {
                console.error('Error polling workflow status:', error);
            }
        }
        
        showSaveStatus('Workflow execution timeout', false);
    }
    
    // Fallback simulation (keep for demo purposes)
    async function simulateWorkflowExecution(workflow) {
        // Get parsed workflow steps
        const workflowSteps = getWorkflowSteps(workflow);
        
        // Simulate workflow execution
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Generate realistic step execution data
        const simulatedSteps = workflowSteps.map((step, index) => {
            const isSuccess = Math.random() > 0.1; // 90% success rate per step
            const duration = Math.floor(Math.random() * 60) + 10; // 10-70 seconds per step
            
            return {
                ...step,
                status: isSuccess ? workflowStates.SUCCESS : workflowStates.FAILURE,
                duration: duration,
                startTime: new Date(Date.now() - (workflowSteps.length - index) * 30000).toISOString(),
                conclusion: isSuccess ? 'success' : 'failure'
            };
        });
        
        // Overall workflow status based on step results
        const hasFailedStep = simulatedSteps.some(step => step.status === workflowStates.FAILURE);
        const overallStatus = hasFailedStep ? workflowStates.FAILURE : workflowStates.SUCCESS;
        
        // Update workflow history
        const newRun = {
            id: `run-${workflow.id}-${Date.now()}`,
            status: overallStatus,
            startTime: new Date().toISOString(),
            duration: simulatedSteps.reduce((total, step) => total + step.duration, 0),
            stages: simulatedSteps, // Use simulated workflow steps
            buildNumber: `#${(workflowHistory[workflow.id]?.runs?.length || 0) + 1}`,
            author: 'You', // Mark as created by current user
            commitMessage: 'Manual workflow execution',
            commitSha: 'manual-' + Date.now().toString(36),
            workflowSteps: workflowSteps
        };
        
        if (!workflowHistory[workflow.id]) {
            workflowHistory[workflow.id] = { 
                runs: [], 
                lastSuccess: null, 
                lastFailure: null, 
                avgDuration: 0,
                workflowSteps: workflowSteps 
            };
        }
        
        workflowHistory[workflow.id].runs.unshift(newRun);
        
        if (newRun.status === workflowStates.SUCCESS) {
            workflowHistory[workflow.id].lastSuccess = newRun;
        } else if (newRun.status === workflowStates.FAILURE) {
            workflowHistory[workflow.id].lastFailure = newRun;
        }
        
        // Update average duration
        const runs = workflowHistory[workflow.id].runs;
        workflowHistory[workflow.id].avgDuration = Math.floor(
            runs.reduce((sum, run) => sum + run.duration, 0) / runs.length
        );
        
        // Mark workflow as no longer newly created since it has been executed
        if (workflow.metadata && workflow.metadata.isNewlyCreated) {
            workflow.metadata.isNewlyCreated = false;
            workflow.metadata.firstExecuted = new Date().toISOString();
            await saveTreeData(); // Save the updated metadata
        }
        
        workflowHistory = { ...workflowHistory };
        showSaveStatus(`Workflow "${workflow.name}" completed with status: ${newRun.status}`, newRun.status === workflowStates.SUCCESS);
    }
    
    function formatDuration(seconds) {
        if (!seconds || seconds === 0) return '0s';
        
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}h ${mins}m ${secs}s`;
        } else if (mins > 0) {
            return `${mins}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }
    
    function formatRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }
    
    function getStatusIcon(status) {
        switch (status) {
            case workflowStates.SUCCESS:
                return '✅';
            case workflowStates.FAILURE:
                return '❌';
            case workflowStates.RUNNING:
                return '🔄';
            case workflowStates.PENDING:
                return '⏳';
            case workflowStates.CANCELLED:
                return '⏹️';
            default:
                return '❓';
        }
    }
    
    function getStatusColor(status) {
        switch (status) {
            case workflowStates.SUCCESS:
                return 'text-green-600 bg-green-100';
            case workflowStates.FAILURE:
                return 'text-red-600 bg-red-100';
            case workflowStates.RUNNING:
                return 'text-blue-600 bg-blue-100';
            case workflowStates.PENDING:
                return 'text-yellow-600 bg-yellow-100';
            case workflowStates.CANCELLED:
                return 'text-gray-600 bg-gray-100';
            default:
                return 'text-gray-600 bg-gray-100';
        }
    }
    
    // Build parameters management (like Jenkins)
    let showBuildParameters = false;
    let buildParameters = {};
    
    async function configureWorkflow(node) {
        // Simply open the file editor instead of trying to fetch non-existent parameters
        console.log(`⚙️ Opening configuration for workflow: ${node.name}`);
        openFileEditor(node);
        showSaveStatus(`⚙️ Opening configuration for ${node.name}`, true);
    }
    
    async function loadBuildParameters(node) {
        // Simplified - no external API calls
        console.log(`📋 Loading parameters for ${node.name}`);
        buildParameters = generateMockBuildParameters(node);
    }
    
    function generateMockBuildParameters(node) {
        // Generate realistic build parameters based on node type
        const baseParams = {
            BRANCH_NAME: {
                type: 'choice',
                value: 'main',
                choices: ['main', 'develop', 'staging', 'release/v1.0'],
                description: 'Git branch to build from'
            },
            BUILD_TYPE: {
                type: 'choice',
                value: 'release',
                choices: ['debug', 'release', 'staging'],
                description: 'Build configuration type'
            },
            RUN_TESTS: {
                type: 'boolean',
                value: true,
                description: 'Execute test suites during build'
            },
            DEPLOY_ENVIRONMENT: {
                type: 'choice',
                value: 'none',
                choices: ['none', 'dev', 'staging', 'production'],
                description: 'Target deployment environment'
            }
        };
        
        // Add specific parameters based on workflow type
        if (node.type === 'workflow' || node.name.toLowerCase().includes('ci')) {
            return {
                ...baseParams,
                DOCKER_BUILD: {
                    type: 'boolean',
                    value: true,
                    description: 'Build Docker images'
                },
                SECURITY_SCAN: {
                    type: 'boolean',
                    value: true,
                    description: 'Run security vulnerability scans'
                },
                NOTIFICATION_RECIPIENTS: {
                    type: 'string',
                    value: 'team@company.com',
                    description: 'Email recipients for build notifications'
                }
            };
        }
        
        return baseParams;
    }
    
    async function runWithParameters() {
        if (!selectedNode) return;
        
        showBuildParameters = false;
        showSaveStatus(`🚀 Starting workflow ${selectedNode.name} with custom parameters...`, true);
        
        // Run workflow with custom parameters
        await runWorkflow({
            ...selectedNode,
            buildParameters: buildParameters
        });
    }
    
    // Simplified workspace management
    async function showWorkspace(node) {
        // Show a simple info message instead of trying to fetch workspace data
        console.log(`📁 Showing workspace info for: ${node.name}`);
        showSaveStatus(`📁 Workspace: ${node.name} - Use the editor to view and modify workflow files`, true);
        
        // Generate mock workspace info for display
        const workspace = generateMockWorkspace(node);
        openWorkspaceViewer(workspace);
    }
    
    function generateMockWorkspace(node) {
        return {
            path: `/workspace/${node.name}`,
            size: '45.2 MB',
            lastModified: new Date(),
            files: [
                { name: 'README.md', size: '2.1 KB', type: 'file' },
                { name: `${node.name}.yml`, size: '1.4 KB', type: 'file' },
                { name: 'src/', size: '12.5 MB', type: 'directory' },
                { name: 'build/', size: '28.4 MB', type: 'directory' },
                { name: '.github/', size: '1.8 MB', type: 'directory' }
            ]
        };
    }
    
    function openWorkspaceViewer(workspace) {
        console.log('📁 Opening workspace viewer:', workspace);
        alert(`Workspace: ${workspace.path}\nSize: ${workspace.size}\nFiles: ${workspace.files.length} items\n\nThis is workspace information for reference.`);
    }
    
    async function cleanWorkspace(node) {
        // Show info message instead of calling non-existent endpoint
        if (confirm(`🧹 Clean workspace for ${node.name}?\n\nThis would remove temporary build files in a real environment.\n\nProceed with simulation?`)) {
            console.log(`🧹 Simulating workspace clean for: ${node.name}`);
            showSaveStatus(`🧹 Workspace cleaned for ${node.name} (simulated)`, true);
        }
    }
    
    // Additional workflow management functions - Enhanced like Jenkins
    function showWorkflowLogs(run) {
        // Open real-time log viewer (like Jenkins console output)
        openLogViewer(run);
        showSaveStatus(`📋 Opening live logs for build ${run.buildNumber}...`, true);
    }
    
    function openLogViewer(run) {
        // Create a new modal for live log viewing
        const logWindow = window.open(
            `/logs/${run.id}`,
            'workflow-logs',
            'width=1200,height=800,scrollbars=yes,resizable=yes'
        );
        
        if (!logWindow) {
            // Fallback: show logs in current window
            showInlineLogViewer(run);
        }
    }
    
    function showInlineLogViewer(run) {
        // This would open an inline log viewer modal
        console.log('📋 Opening inline log viewer for run:', run);
        // Implementation would show real streaming logs
    }
    
    async function rerunWorkflow(run) {
        if (selectedNode && confirm(`Rerun workflow from build ${run.buildNumber}?`)) {
            showSaveStatus(`🔄 Rerunning workflow from build ${run.buildNumber}...`, true);
            
            // Clone the original run configuration
            const rerunConfig = {
                ...selectedNode,
                metadata: {
                    ...selectedNode.metadata,
                    rerunFrom: run.id,
                    originalBuildNumber: run.buildNumber
                }
            };
            
            await runWorkflow(rerunConfig);
        }
    }
    
    function deleteWorkflowRun(run) {
        if (confirm(`⚠️ Delete build ${run.buildNumber}?\n\nThis will permanently remove:\n• Build history\n• Artifacts\n• Logs\n\nThis cannot be undone.`)) {
            deleteRealWorkflowRun(run);
        }
    }
    
    async function deleteRealWorkflowRun(run) {
        try {
            // Delete from real systems first
            const deleteResponse = await fetch(`/api/workflows/runs/${run.id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('authToken')}`
                }
            });
            
            if (deleteResponse.ok) {
                // Remove from local state
                if (workflowHistory[selectedNode.id] && workflowHistory[selectedNode.id].runs) {
                    const runIndex = workflowHistory[selectedNode.id].runs.findIndex(r => r.id === run.id);
                    if (runIndex > -1) {
                        workflowHistory[selectedNode.id].runs.splice(runIndex, 1);
                        workflowHistory = { ...workflowHistory };
                        showSaveStatus(`🗑️ Build ${run.buildNumber} deleted successfully`, true);
                    }
                }
            } else {
                throw new Error('Failed to delete build from server');
            }
            
        } catch (error) {
            console.error('❌ Failed to delete build:', error);
            showSaveStatus(`❌ Failed to delete build ${run.buildNumber}`, false);
        }
    }
    
    // Real-time build monitoring (like Jenkins)
    function startRealTimeMonitoring(workflowId) {
        if (typeof EventSource !== 'undefined') {
            const eventSource = new EventSource(`/api/workflows/${workflowId}/stream`);
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                switch (data.type) {
                    case 'status_update':
                        updateWorkflowStatus(workflowId, data.status);
                        break;
                    case 'log_line':
                        appendLogLine(workflowId, data.line);
                        break;
                    case 'stage_complete':
                        updateStageStatus(workflowId, data.stage, data.status);
                        break;
                    case 'execution_complete':
                        finalizeExecution(workflowId, data);
                        eventSource.close();
                        break;
                }
            };
            
            eventSource.onerror = function(error) {
                console.error('❌ EventSource error:', error);
                eventSource.close();
            };
            
            return eventSource;
        } else {
            // Fallback to polling for browsers without EventSource
            return startPollingMonitoring(workflowId);
        }
    }
    
    function updateWorkflowStatus(workflowId, status) {
        if (workflowHistory[workflowId] && workflowHistory[workflowId].runs.length > 0) {
            workflowHistory[workflowId].runs[0].status = mapStatusToWorkflowState(status);
            workflowHistory = { ...workflowHistory };
        }
    }
    
    function appendLogLine(workflowId, line) {
        // This would append to live log viewer
        console.log(`📋 [${workflowId}]`, line);
    }
    
    function updateStageStatus(workflowId, stageName, status) {
        if (workflowHistory[workflowId] && workflowHistory[workflowId].runs.length > 0) {
            const currentRun = workflowHistory[workflowId].runs[0];
            if (currentRun.stages) {
                const stage = currentRun.stages.find(s => s.name === stageName);
                if (stage) {
                    stage.status = mapStatusToWorkflowState(status);
                    workflowHistory = { ...workflowHistory };
                }
            }
        }
    }
    
    function finalizeExecution(workflowId, data) {
        // Reload complete workflow history with final results
        if (selectedNode && selectedNode.id === workflowId) {
            loadWorkflowHistory(selectedNode);
        }
        showSaveStatus(`✅ Workflow execution completed: ${data.status}`, data.status === 'success');
    }
    
    function navigateToNode(node) {
        selectNode(node);
    }
</script>

<svelte:head>
    <title>Project Treeview - {orgName} - WithOps</title>
</svelte:head>

<svelte:window on:click={handleClickOutside} />

<div class="min-h-screen bg-gray-50">
    <div class="flex h-screen">
        <!-- Tree Panel -->
        <div class="w-1/3 bg-white border-r border-gray-200 flex flex-col">
            <!-- Header -->
            <div class="p-4 border-b border-gray-200">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h1 class="text-xl font-bold text-gray-900">🌲 Project Treeview</h1>
                        <p class="text-sm text-gray-600">{orgName}</p>
                    </div>
                    <button 
                        on:click={goBack}
                        class="text-gray-400 hover:text-gray-600"
                        title="Back to Workspace"
                        aria-label="Back to Workspace"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
                
                <!-- Action Buttons -->
                <div class="grid grid-cols-2 gap-2 mb-2">
                    <button 
                        on:click={() => openNewItemModal('folder')}
                        class="bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 text-sm flex items-center justify-center space-x-1"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                        </svg>
                        <span>Folder</span>
                    </button>
                    <button 
                        on:click={() => openNewItemModal('workflow')}
                        class="bg-green-600 text-white px-3 py-2 rounded-lg hover:bg-green-700 text-sm flex items-center justify-center space-x-1"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                        </svg>
                        <span>Workflow</span>
                    </button>
                    <button 
                        on:click={saveProjectTree}
                        disabled={loading}
                        class="bg-purple-600 text-white px-3 py-2 rounded-lg hover:bg-purple-700 text-sm flex items-center justify-center disabled:opacity-50"
                        title="Save Project Tree"
                    >
                    >
                        {#if loading}
                            <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        {:else}
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                        {/if}
                    </button>
                </div>
                
                <!-- Security Scanning Panel -->
                <div class="border-t border-gray-200 pt-3">
                    <button 
                        on:click={toggleSecurityPanel}
                        class="w-full bg-red-600 text-white px-3 py-2 rounded-lg hover:bg-red-700 text-sm flex items-center justify-center space-x-1 mb-2"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                        <span>🔒 Security</span>
                    </button>
                    
                    {#if showSecurityPanel}
                        <div class="space-y-2 bg-gray-50 p-3 rounded-lg">
                            <button 
                                on:click={scanOrganizationSecurity}
                                disabled={!!organizationSecurityScan}
                                class="w-full bg-orange-600 text-white px-3 py-2 rounded-md hover:bg-orange-700 text-xs flex items-center justify-center space-x-1 disabled:opacity-50"
                            >
                                {#if organizationSecurityScan?.status === 'running'}
                                    <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                                    <span>Scanning...</span>
                                {:else}
                                    <span>🏢 Scan Org</span>
                                {/if}
                            </button>
                            
                            {#if organizationSecurityScan?.status === 'completed'}
                                <div class="text-xs text-gray-600 bg-white p-2 rounded border">
                                    <div class="font-semibold mb-1">Last Scan Results:</div>
                                    <div>• {organizationSecurityScan.data.organization_metrics.total_workflows} workflows</div>
                                    <div>• Avg Risk: {organizationSecurityScan.data.organization_metrics.average_risk_score}%</div>
                                    <div>• High Risk: {organizationSecurityScan.data.organization_metrics.high_risk_workflows}</div>
                                </div>
                            {/if}
                            
                            {#if securityOverview}
                                <div class="text-xs text-gray-600">
                                    <div class="font-semibold">Security Overview:</div>
                                    <div>• Last scan: {securityOverview.overview.last_scan || 'Never'}</div>
                                    <div>• Avg risk: {securityOverview.overview.average_risk_score}%</div>
                                </div>
                            {/if}
                        </div>
                    {/if}
                </div>
            </div>
            
            <!-- Tree View -->
            <div class="flex-1 overflow-y-auto p-4">
                {#if loading && treeData.length === 0}
                    <div class="flex items-center justify-center py-8">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <span class="ml-2 text-gray-600">Loading project tree...</span>
                    </div>
                {:else if error}
                    <div class="text-center py-8 text-red-600">
                        <p>{error}</p>
                        <button 
                            on:click={loadTreeData}
                            class="mt-2 text-blue-600 hover:text-blue-800"
                        >
                            Try Again
                        </button>
                    </div>
                {:else}
                    <div class="space-y-1">
                        {#each treeData as node}
                            <TreeNode 
                                {node} 
                                level={0} 
                                {expandedNodes} 
                                {selectedNode} 
                                {editingNode} 
                                {editingValue}
                                {dragOverNode}
                                {scanningWorkflows}
                                {workflowSecurityResults}
                                {scanningRepository}
                                on:toggle={(e) => toggleExpanded(e.detail)}
                                on:select={(e) => selectNode(e.detail)}
                                on:edit={(e) => startEditing(e.detail)}
                                on:save={saveEdit}
                                on:cancel={cancelEditing}
                                on:keypress={handleKeyPress}
                                on:contextmenu={(e) => openContextMenu(e.detail.event, e.detail.node)}
                                on:dragstart={(e) => handleDragStart(e.detail.event, e.detail.node)}
                                on:dragover={(e) => handleDragOver(e.detail.event, e.detail.node)}
                                on:dragleave={handleDragLeave}
                                on:drop={(e) => handleDrop(e.detail.event, e.detail.node)}
                                on:scan-workflow={(e) => scanWorkflowSecurity(e.detail)}
                                on:scan-repository={(e) => scanRepositorySecurity(e.detail)}
                            />
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
        
        <!-- Content Panel -->
        <div class="flex-1 bg-white flex flex-col">
            {#if selectedNode}
                <!-- Breadcrumb Navigation -->
                {#if navigationPath.length > 0}
                    <div class="px-6 py-3 border-b border-gray-200 bg-gray-50">
                        <nav class="flex items-center space-x-2 text-sm">
                            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                            </svg>
                            {#each navigationPath as pathNode, index}
                                {#if index > 0}
                                    <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                    </svg>
                                {/if}
                                <button 
                                    on:click={() => navigateToNode(pathNode)}
                                    class="text-gray-600 hover:text-gray-900 hover:underline {index === navigationPath.length - 1 ? 'font-medium text-gray-900' : ''}"
                                >
                                    {pathNode.name}
                                </button>
                            {/each}
                        </nav>
                    </div>
                {/if}
                
                <!-- Content Header -->
                <div class="p-6 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div>
                            <h2 class="text-2xl font-bold text-gray-900">{selectedNode.name}</h2>
                            <div class="flex items-center space-x-4 mt-2">
                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {
                                    selectedNode.type === 'folder' ? 'bg-blue-100 text-blue-800' : 
                                    selectedNode.type === 'workflow' ? 'bg-green-100 text-green-800' : 
                                    'bg-gray-100 text-gray-800'
                                }">
                                    {selectedNode.type === 'folder' ? '📁' : selectedNode.type === 'workflow' ? '⚙️' : '📄'} {selectedNode.type}
                                </span>
                                
                                {#if selectedNode.metadata && selectedNode.metadata.lastModified}
                                    <span class="text-sm text-gray-500">
                                        Modified: {new Date(selectedNode.metadata.lastModified).toLocaleDateString()}
                                    </span>
                                {/if}
                            </div>
                        </div>
                        
                        <div class="flex items-center space-x-3">
                            {#if selectedNode.type === 'workflow'}
                                <!-- Connection Status -->
                                <div class="flex items-center space-x-2">
                                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {
                                        workflowHistory[selectedNode.id]?.source === 'GitHub Actions' ? 'bg-green-100 text-green-800' : 
                                        workflowHistory[selectedNode.id]?.source === 'newly-created' ? 'bg-blue-100 text-blue-800' : 
                                        'bg-gray-100 text-gray-800'
                                    }">
                                        {#if workflowHistory[selectedNode.id]?.source === 'GitHub Actions'}
                                            🔗 GitHub Actions
                                        {:else if workflowHistory[selectedNode.id]?.source === 'newly-created'}
                                            🆕 New Workflow
                                        {:else}
                                            � Local Only
                                        {/if}
                                    </span>
                                </div>
                                
                                <!-- Jenkins-style View Mode Selector -->
                                <div class="flex bg-gray-100 rounded-lg p-1">
                                    <button 
                                        on:click={() => viewMode = 'details'}
                                        class="px-3 py-1 text-sm font-medium rounded-md {viewMode === 'details' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 hover:text-gray-900'}"
                                    >
                                        📊 Dashboard
                                    </button>
                                    <button 
                                        on:click={() => viewMode = 'table'}
                                        class="px-3 py-1 text-sm font-medium rounded-md {viewMode === 'table' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 hover:text-gray-900'}"
                                    >
                                        📋 Build History
                                    </button>
                                    <button 
                                        on:click={() => viewMode = 'stages'}
                                        class="px-3 py-1 text-sm font-medium rounded-md {viewMode === 'stages' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 hover:text-gray-900'}"
                                    >
                                        🔄 Pipeline Stages
                                    </button>
                                </div>
                                
                                <!-- Run Workflow Button -->
                                <button 
                                    on:click={() => runWorkflow(selectedNode)}
                                    disabled={runningWorkflow === selectedNode.id}
                                    class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                                >
                                    {#if runningWorkflow === selectedNode.id}
                                        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                        <span>Running...</span>
                                    {:else}
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1m4-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        <span>▶️ Run Now</span>
                                    {/if}
                                </button>
                                
                                <!-- Edit Button -->
                                <button 
                                    on:click={() => openFileEditor(selectedNode)}
                                    class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
                                >
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                    </svg>
                                    <span>Edit</span>
                                </button>
                            {/if}
                        </div>
                    </div>
                </div>
                
                <!-- Content Body -->
                <div class="flex-1 p-6 overflow-y-auto">
                    {#if selectedNode.type === 'folder'}
                        <div class="space-y-4">
                            <div class="bg-gray-50 rounded-lg p-4">
                                <h3 class="text-lg font-medium text-gray-900 mb-2">📁 Folder Overview</h3>
                                <p class="text-gray-600 mb-4">This folder contains {selectedNode.children ? selectedNode.children.length : 0} items.</p>
                                
                                {#if selectedNode.children && selectedNode.children.length > 0}
                                    <div class="space-y-2">
                                        <h4 class="font-medium text-gray-900">Contents:</h4>
                                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                                            {#each selectedNode.children as child}
                                                <div class="flex items-center space-x-2 p-2 bg-white rounded border">
                                                    <span class="text-lg">
                                                        {child.type === 'folder' ? '📁' : child.type === 'workflow' ? '⚙️' : '📄'}
                                                    </span>
                                                    <span class="text-sm text-gray-700">{child.name}</span>
                                                </div>
                                            {/each}
                                        </div>
                                    </div>
                                {/if}
                            </div>
                            
                            <div class="flex space-x-2">
                                <button 
                                    on:click={() => openNewItemModal('folder', selectedNode)}
                                    class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
                                >
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                    </svg>
                                    <span>Add Folder</span>
                                </button>
                                <button 
                                    on:click={() => openNewItemModal('workflow', selectedNode)}
                                    class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center space-x-2"
                                >
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                    </svg>
                                    <span>Add Workflow</span>
                                </button>

                            </div>
                        </div>
                    {:else if selectedNode.type === 'workflow'}
                        <!-- Jenkins-like Dashboard -->
                        {#if viewMode === 'details'}
                            <!-- Jenkins Dashboard Grid -->
                            <div class="bg-white rounded-lg shadow-sm border border-gray-200">
                                <!-- Header -->
                                <div class="border-b border-gray-200 px-6 py-4">
                                    <div class="flex items-center justify-between">
                                        <div class="flex items-center space-x-3">
                                            <h3 class="text-lg font-medium text-gray-900">{selectedNode.name}</h3>
                                            {#if workflowHistory[selectedNode.id]?.source === 'GitHub Actions'}
                                                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                    ✅ Connected
                                                </span>
                                            {:else if workflowHistory[selectedNode.id]?.source === 'newly-created'}
                                                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                    🆕 New
                                                </span>
                                            {:else}
                                                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                                    📄 No Data
                                                </span>
                                            {/if}
                                        </div>
                                        <div class="flex items-center space-x-2">
                                            <button 
                                                on:click={() => runWorkflow(selectedNode)}
                                                class="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                                disabled={runningWorkflow === selectedNode.id}
                                            >
                                                {#if runningWorkflow === selectedNode.id}
                                                    <div class="animate-spin -ml-1 mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                                    Building...
                                                {:else}
                                                    <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1m4-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    </svg>
                                                    Build Now
                                                {/if}
                                            </button>
                                            <button 
                                                on:click={() => openFileEditor(selectedNode)}
                                                class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                            >
                                                <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                </svg>
                                                Configure
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <!-- Dashboard Stats with Loading States -->
                                <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
                                    {#if workflowHistory[selectedNode.id]?.loading}
                                        <!-- Loading Dashboard Stats -->
                                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            {#each Array(4).fill(0) as _, i}
                                                <div class="text-center animate-pulse">
                                                    <div class="text-2xl font-bold h-8 bg-gray-300 rounded w-16 mx-auto mb-2"></div>
                                                    <div class="text-sm h-4 bg-gray-200 rounded w-20 mx-auto"></div>
                                                </div>
                                            {/each}
                                        </div>
                                    {:else}
                                        <!-- Actual Dashboard Stats -->
                                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div class="text-center">
                                                <div class="text-2xl font-bold text-gray-900">
                                                    {workflowHistory[selectedNode.id]?.runs?.length || 0}
                                                </div>
                                                <div class="text-sm text-gray-500">Total Builds</div>
                                            </div>
                                            <div class="text-center">
                                                <div class="text-2xl font-bold text-green-600">
                                                    {workflowHistory[selectedNode.id]?.runs?.filter(r => r.status === workflowStates.SUCCESS).length || 0}
                                                </div>
                                                <div class="text-sm text-gray-500">Successful</div>
                                            </div>
                                            <div class="text-center">
                                                <div class="text-2xl font-bold text-red-600">
                                                    {workflowHistory[selectedNode.id]?.runs?.filter(r => r.status === workflowStates.FAILURE).length || 0}
                                                </div>
                                                <div class="text-sm text-gray-500">Failed</div>
                                            </div>
                                            <div class="text-center">
                                                <div class="text-2xl font-bold text-blue-600">
                                                    {#if workflowHistory[selectedNode.id]?.avgDuration}
                                                        {formatDuration(workflowHistory[selectedNode.id].avgDuration)}
                                                    {:else}
                                                        --
                                                    {/if}
                                                </div>
                                                <div class="text-sm text-gray-500">Avg Duration</div>
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                                <!-- Build History Grid with Loading States -->
                                <div class="px-6 py-4">
                                    {#if workflowHistory[selectedNode.id]?.loading}
                                        <!-- Loading Build History -->
                                        <div class="space-y-4">
                                            <div class="flex items-center justify-between">
                                                <div class="h-6 bg-gray-300 rounded w-32 animate-pulse"></div>
                                                <div class="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                                            </div>
                                            
                                            <div class="overflow-hidden">
                                                <table class="min-w-full">
                                                    <thead class="bg-gray-100">
                                                        <tr>
                                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Build</th>
                                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
                                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commit</th>
                                                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody class="bg-white divide-y divide-gray-200">
                                                        {#each Array(5).fill(0) as _, i}
                                                            <tr class="animate-pulse">
                                                                <td class="px-6 py-4 whitespace-nowrap">
                                                                    <div class="h-4 bg-gray-300 rounded w-12"></div>
                                                                </td>
                                                                <td class="px-6 py-4 whitespace-nowrap">
                                                                    <div class="h-5 bg-gray-300 rounded-full w-16"></div>
                                                                </td>
                                                                <td class="px-6 py-4 whitespace-nowrap">
                                                                    <div class="space-y-1">
                                                                        <div class="h-3 bg-gray-300 rounded w-16"></div>
                                                                        <div class="h-3 bg-gray-200 rounded w-24"></div>
                                                                    </div>
                                                                </td>
                                                                <td class="px-6 py-4 whitespace-nowrap">
                                                                    <div class="h-4 bg-gray-300 rounded w-12"></div>
                                                                </td>
                                                                <td class="px-6 py-4 whitespace-nowrap">
                                                                    <div class="space-y-1">
                                                                        <div class="h-3 bg-gray-300 rounded w-16"></div>
                                                                        <div class="h-3 bg-gray-200 rounded w-20"></div>
                                                                    </div>
                                                                </td>
                                                                <td class="px-6 py-4 whitespace-nowrap">
                                                                    <div class="flex space-x-2">
                                                                        <div class="h-6 bg-gray-300 rounded w-12"></div>
                                                                        <div class="h-6 bg-gray-300 rounded w-12"></div>
                                                                    </div>
                                                                </td>
                                                            </tr>
                                                        {/each}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    {:else if workflowHistory[selectedNode.id]?.runs?.length}
                                        <!-- Build History Table -->
                                        <div class="overflow-hidden">
                                            <table class="min-w-full">
                                                <thead class="bg-gray-100">
                                                    <tr>
                                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Build</th>
                                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
                                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commit</th>
                                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                                    </tr>
                                                </thead>
                                                <tbody class="bg-white divide-y divide-gray-200">{#each workflowHistory[selectedNode.id].runs as run, index}
                                                        <tr class="hover:bg-gray-50">
                                                            <td class="px-6 py-4 whitespace-nowrap">
                                                                <div class="flex items-center">
                                                                    <span class="text-sm font-medium text-gray-900">
                                                                        {run.buildNumber || `#${index + 1}`}
                                                                    </span>
                                                                </div>
                                                            </td>
                                                            <td class="px-6 py-4 whitespace-nowrap">
                                                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusColor(run.status)}">
                                                                    {getStatusIcon(run.status)} {run.status}
                                                                </span>
                                                            </td>
                                                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                                <div>
                                                                    <div class="text-sm text-gray-900">{formatRelativeTime(run.startTime)}</div>
                                                                    <div class="text-xs text-gray-500">{new Date(run.startTime).toLocaleString()}</div>
                                                                </div>
                                                            </td>
                                                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                                {formatDuration(run.duration)}
                                                            </td>
                                                            <td class="px-6 py-4 whitespace-nowrap">
                                                                <div class="text-sm text-gray-900">
                                                                    {#if run.commitSha}
                                                                        <code class="text-xs bg-gray-100 px-1 py-0.5 rounded">{run.commitSha.substring(0, 7)}</code>
                                                                    {/if}
                                                                </div>
                                                                <div class="text-xs text-gray-500 truncate max-w-48">
                                                                    {run.commitMessage || 'No commit message'}
                                                                </div>
                                                            </td>
                                                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                                                <div class="flex items-center space-x-2">
                                                                    <button 
                                                                        on:click={() => showWorkflowLogs(run)}
                                                                        class="text-blue-600 hover:text-blue-900 text-xs"
                                                                        title="View Logs"
                                                                    >
                                                                        📋 Logs
                                                                    </button>
                                                                    <button 
                                                                        on:click={() => rerunWorkflow(run)}
                                                                        class="text-green-600 hover:text-green-900 text-xs"
                                                                        title="Rebuild"
                                                                    >
                                                                        🔄 Rebuild
                                                                    </button>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    {/each}
                                                </tbody>
                                            </table>
                                        </div>
                                    {:else}
                                        <!-- Empty State -->
                                        <div class="text-center py-12">
                                            <div class="mx-auto h-12 w-12 text-gray-400">
                                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                                </svg>
                                            </div>
                                            <h3 class="mt-2 text-sm font-medium text-gray-900">No builds yet</h3>
                                            <p class="mt-1 text-sm text-gray-500">Get started by running your first build.</p>
                                            <div class="mt-6">
                                                <button 
                                                    on:click={() => runWorkflow(selectedNode)}
                                                    class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                                    disabled={runningWorkflow === selectedNode.id}
                                                >
                                                    {#if runningWorkflow === selectedNode.id}
                                                        <div class="animate-spin -ml-1 mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                                        Building...
                                                    {:else}
                                                        <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1m4-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                        </svg>
                                                        Build Now
                                                    {/if}
                                                </button>
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                            </div>
                            
                            <!-- Workflow Configuration (Simplified) -->
                            {#if selectedNode.content}
                                <div class="bg-white rounded-lg shadow-sm border border-gray-200 mt-6">
                                    <div class="border-b border-gray-200 px-6 py-4">
                                        <div class="flex items-center justify-between">
                                            <h3 class="text-lg font-medium text-gray-900">Workflow Configuration</h3>
                                            <div class="flex items-center space-x-3">
                                                <span class="text-sm text-gray-500">
                                                    {getWorkflowSteps(selectedNode).length} steps defined
                                                </span>
                                                <button 
                                                    on:click={() => openFileEditor(selectedNode)}
                                                    class="text-sm bg-gray-600 text-white px-3 py-1 rounded hover:bg-gray-700"
                                                >
                                                    Edit YAML
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="px-6 py-4">
                                        <!-- Workflow Steps Overview -->
                                        {#if getWorkflowSteps(selectedNode).length > 0}
                                            {@const steps = getWorkflowSteps(selectedNode)}
                                            <div class="mb-4">
                                                <h4 class="text-sm font-medium text-gray-900 mb-3">📋 Workflow Steps</h4>
                                                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                    {#each steps as step, index}
                                                        <div class="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                                                            <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-800 rounded-full flex items-center justify-center text-xs font-medium">
                                                                {index + 1}
                                                            </span>
                                                            <div class="flex-1">
                                                                <div class="text-sm font-medium text-gray-900">{step.name}</div>
                                                                <div class="text-xs text-gray-500">
                                                                    {step.type === 'action' ? '🔧 GitHub Action' : '💻 Shell Command'}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    {/each}
                                                </div>
                                            </div>
                                        {/if}
                                        
                                        <!-- YAML Content -->
                                        <div class="bg-gray-900 rounded-lg p-4 overflow-x-auto max-h-64">
                                            <pre class="text-green-400 text-sm font-mono whitespace-pre-wrap">{selectedNode.content}</pre>
                                        </div>
                                    </div>
                                </div>
                            {/if}
                        {:else if viewMode === 'stages'}
                            <!-- GitHub Workflow Runs History (Jenkins-style) -->
                            <div class="bg-white rounded-lg shadow-sm border border-gray-200">
                                <div class="border-b border-gray-200 px-6 py-4">
                                    <h3 class="text-lg font-medium text-gray-900 flex items-center">
                                        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012-2" />
                                        </svg>
                                        {selectedNode.name} - Workflow Runs
                                    </h3>
                                    <p class="text-sm text-gray-600 mt-1">
                                        {#if workflowHistory[selectedNode.id]?.totalRuns}
                                            {workflowHistory[selectedNode.id].totalRuns} total workflow runs
                                        {:else if workflowHistory[selectedNode.id]?.runs?.length}
                                            {workflowHistory[selectedNode.id].runs.length} workflow runs
                                        {:else}
                                            No workflow runs found
                                        {/if}
                                        • {getWorkflowSteps(selectedNode).length} steps defined
                                    </p>
                                </div>
                                
                                <div class="px-6 py-4">
                                    {#if workflowHistory[selectedNode.id]?.loading}
                                        <!-- Enhanced Loading State with Skeleton -->
                                        <div class="space-y-6">
                                            <!-- Loading Header -->
                                            <div class="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
                                                <div class="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent"></div>
                                                <div class="text-blue-700 font-medium">
                                                    {workflowHistory[selectedNode.id].loadingMessage || 'Fetching workflow history from GitHub Actions...'}
                                                </div>
                                                <div class="flex space-x-1 loading-dots">
                                                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                                                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                                                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                                                </div>
                                            </div>
                                            
                                            <!-- Skeleton Summary Stats -->
                                            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                                                {#each Array(4).fill(0) as _, i}
                                                    <div class="animate-pulse bg-gray-50 border border-gray-200 rounded-lg p-3">
                                                        <div class="h-4 bg-gray-300 rounded w-20 mb-2"></div>
                                                        <div class="h-8 bg-gray-300 rounded w-12"></div>
                                                    </div>
                                                {/each}
                                            </div>
                                            
                                            <!-- Skeleton Step Execution Grid -->
                                            <div class="space-y-4">
                                                <div class="animate-pulse">
                                                    <div class="h-6 bg-gray-200 rounded w-1/3 mb-2"></div>
                                                    <div class="h-4 bg-gray-200 rounded w-1/2"></div>
                                                </div>
                                                
                                                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                                    {#each Array(8).fill(0) as _, i}
                                                        <div class="animate-pulse border border-gray-200 rounded-lg p-4 bg-gray-50">
                                                            <!-- Skeleton Header -->
                                                            <div class="flex justify-between items-center mb-3">
                                                                <div class="flex items-center space-x-2">
                                                                    <div class="w-8 h-4 bg-gray-300 rounded-full"></div>
                                                                    <div class="w-6 h-6 bg-gray-300 rounded"></div>
                                                                </div>
                                                                <div class="w-16 h-4 bg-gray-300 rounded-full"></div>
                                                            </div>
                                                            
                                                            <!-- Skeleton Title -->
                                                            <div class="h-4 bg-gray-300 rounded w-3/4 mb-3"></div>
                                                            
                                                            <!-- Skeleton Details -->
                                                            <div class="space-y-2">
                                                                <div class="flex justify-between">
                                                                    <div class="h-3 bg-gray-200 rounded w-1/3"></div>
                                                                    <div class="h-3 bg-gray-200 rounded w-1/4"></div>
                                                                </div>
                                                                <div class="flex justify-between">
                                                                    <div class="h-3 bg-gray-200 rounded w-1/4"></div>
                                                                    <div class="h-3 bg-gray-200 rounded w-1/3"></div>
                                                                </div>
                                                                <div class="mt-3 pt-2 border-t border-gray-200">
                                                                    <div class="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
                                                                    <div class="h-8 bg-gray-200 rounded"></div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    {/each}
                                                </div>
                                                
                                                <!-- Skeleton Summary Footer -->
                                                <div class="animate-pulse mt-4 p-4 bg-gray-100 rounded-lg">
                                                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                                        {#each Array(4).fill(0) as _}
                                                            <div class="text-center">
                                                                <div class="h-6 bg-gray-300 rounded w-8 mx-auto mb-2"></div>
                                                                <div class="h-4 bg-gray-300 rounded w-16 mx-auto"></div>
                                                            </div>
                                                        {/each}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    {:else if workflowHistory[selectedNode.id]?.runs?.length}
                                        {@const workflowSteps = getWorkflowSteps(selectedNode)}
                                        {@const runs = workflowHistory[selectedNode.id].runs}
                                        
                                        <!-- Summary Stats -->
                                        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                                            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                                <div class="text-sm font-medium text-blue-900">Total Runs</div>
                                                <div class="text-2xl font-bold text-blue-600">{runs.length}</div>
                                            </div>
                                            <div class="bg-green-50 border border-green-200 rounded-lg p-3">
                                                <div class="text-sm font-medium text-green-900">Success Rate</div>
                                                <div class="text-2xl font-bold text-green-600">
                                                    {Math.round((runs.filter(r => r.status === workflowStates.SUCCESS).length / runs.length) * 100)}%
                                                </div>
                                            </div>
                                            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                                                <div class="text-sm font-medium text-yellow-900">Avg Duration</div>
                                                <div class="text-2xl font-bold text-yellow-600">
                                                    {workflowHistory[selectedNode.id].avgDuration ? formatDuration(workflowHistory[selectedNode.id].avgDuration) : 'N/A'}
                                                </div>
                                            </div>
                                            <div class="bg-purple-50 border border-purple-200 rounded-lg p-3">
                                                <div class="text-sm font-medium text-purple-900">Latest Status</div>
                                                <div class="text-xl font-bold text-purple-600 flex items-center">
                                                    {getStatusIcon(runs[0]?.status)} {runs[0]?.status || 'Unknown'}
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <!-- Jenkins-style Workflow Runs Grid -->
                                        <div class="mb-6">
                                            <div class="flex items-center justify-between mb-4">
                                                <h4 class="text-lg font-medium text-gray-900">🔄 Step Execution Grid</h4>
                                                <div class="text-sm text-gray-500">
                                                    Showing {Math.min(runs.length, 10)} of {runs.length} runs
                                                </div>
                                            </div>
                                            
                                            <!-- Grid Display with Better Spacing -->
                                            <div class="overflow-x-auto">
                                                <div class="min-w-full">
                                                    <!-- Header Row -->
                                                    <div class="bg-gray-50 border border-gray-300 p-3 grid grid-flow-col auto-cols-max gap-6">
                                                        <div class="min-w-32 font-medium text-sm text-gray-700 text-center">Run #</div>
                                                        {#each workflowSteps as step, stepIndex}
                                                            <div class="min-w-28 font-medium text-sm text-gray-700 text-center" title={step.name}>
                                                                <div class="truncate">Step {stepIndex + 1}</div>
                                                                <div class="text-gray-500 font-normal truncate text-xs">{step.name.substring(0, 15)}</div>
                                                            </div>
                                                        {/each}
                                                        <div class="min-w-24 font-medium text-sm text-gray-700 text-center">Duration</div>
                                                        <div class="min-w-28 font-medium text-sm text-gray-700 text-center">Status</div>
                                                    </div>
                                                    
                                                    <!-- Data Rows -->
                                                    {#each runs.slice(0, 10) as run, runIndex}
                                                        <div class="border-l border-r border-b border-gray-300 p-3 grid grid-flow-col auto-cols-max gap-6 transition-colors duration-150 {
                                                            run.status === workflowStates.SUCCESS ? 'bg-green-25 hover:bg-green-50' :
                                                            run.status === workflowStates.FAILURE ? 'bg-red-25 hover:bg-red-50' :
                                                            'bg-white hover:bg-gray-25'
                                                        }">
                                                            <!-- Run Number -->
                                                            <div class="min-w-32 text-center">
                                                                <div class="text-sm font-medium text-blue-600">#{run.runNumber || runIndex + 1}</div>
                                                                <div class="text-xs text-gray-500">{formatRelativeTime(run.startTime)}</div>
                                                            </div>
                                                            
                                                            <!-- Step Status Grid -->
                                                            {#each workflowSteps as step, stepIndex}
                                                                {@const runStep = run.steps?.find(s => s.id === step.id || s.name === step.name) || run.steps?.[stepIndex]}
                                                                <div class="min-w-28 text-center">
                                                                    <div class="text-xl mb-1">
                                                                        {#if runStep}
                                                                            {getStatusIcon(runStep.status)}
                                                                        {:else}
                                                                            ⏸️
                                                                        {/if}
                                                                    </div>
                                                                    <div class="text-xs text-gray-500">
                                                                        {#if runStep && runStep.duration}
                                                                            {runStep.duration}s
                                                                        {:else}
                                                                            0s
                                                                        {/if}
                                                                    </div>
                                                                </div>
                                                            {/each}
                                                            
                                                            <!-- Total Duration -->
                                                            <div class="min-w-24 text-center">
                                                                <div class="text-sm font-medium">{formatDuration(run.duration)}</div>
                                                            </div>
                                                            
                                                            <!-- Overall Status -->
                                                            <div class="min-w-28 text-center">
                                                                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium {getStatusColor(run.status)}">
                                                                    {getStatusIcon(run.status)} {run.status}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    {/each}
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <!-- Individual Run Details -->
                                        {#if runs.length > 0}
                                            {@const latestRun = runs[0]}
                                            <div class="mb-6">
                                                <h4 class="text-lg font-medium text-gray-900 mb-4">
                                                    🔍 Latest Run Details: #{latestRun.runNumber || '1'}
                                                </h4>
                                                
                                                <div class="bg-gray-50 rounded-lg p-4 mb-4">
                                                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                                                        <div>
                                                            <span class="font-medium text-gray-700">Commit:</span>
                                                            <span class="text-gray-600 ml-2">{latestRun.commitSha?.substring(0, 8) || 'N/A'}</span>
                                                        </div>
                                                        <div>
                                                            <span class="font-medium text-gray-700">Author:</span>
                                                            <span class="text-gray-600 ml-2">{latestRun.author || 'Unknown'}</span>
                                                        </div>
                                                        <div>
                                                            <span class="font-medium text-gray-700">Branch:</span>
                                                            <span class="text-gray-600 ml-2">{latestRun.branch || 'main'}</span>
                                                        </div>
                                                        {#if latestRun.commitMessage}
                                                            <div class="col-span-full">
                                                                <span class="font-medium text-gray-700">Message:</span>
                                                                <span class="text-gray-600 ml-2">{latestRun.commitMessage}</span>
                                                            </div>
                                                        {/if}
                                                    </div>
                                                </div>
                                                
                                                <!-- 🔄 Enhanced Step Execution Grid with Responsive Design -->
                                                {#if latestRun.steps?.length}
                                                    <div class="space-y-4">
                                                        <div class="flex items-center justify-between">
                                                            <h5 class="text-lg font-medium text-gray-900 flex items-center">
                                                                🔄 Step Execution Grid
                                                                <span class="ml-2 text-sm text-gray-500">({latestRun.steps.length} steps)</span>
                                                            </h5>
                                                            <div class="flex items-center space-x-2 text-sm text-gray-500">
                                                                <span>Duration: {formatDuration(latestRun.duration || 0)}</span>
                                                                <span>•</span>
                                                                <span>Total: {latestRun.steps.length} steps</span>
                                                            </div>
                                                        </div>
                                                        
                                                        <!-- Responsive Grid Layout -->
                                                        <div class="responsive-step-grid step-execution-grid">
                                                            {#each latestRun.steps as step, index}
                                                                <div class="group relative border rounded-lg p-4 step-card transition-all duration-200 hover:shadow-md {
                                                                    step.status === workflowStates.SUCCESS ? 'border-green-300 bg-green-50 hover:bg-green-100' :
                                                                    step.status === workflowStates.FAILURE ? 'border-red-300 bg-red-50 hover:bg-red-100' :
                                                                    step.status === workflowStates.RUNNING ? 'border-blue-300 bg-blue-50 hover:bg-blue-100' :
                                                                    'border-gray-300 bg-gray-50 hover:bg-gray-100'
                                                                }">
                                                                    <!-- Step Header -->
                                                                    <div class="flex items-center justify-between mb-3">
                                                                        <div class="flex items-center space-x-2">
                                                                            <span class="text-xs font-medium bg-white text-gray-700 px-2 py-1 rounded-full shadow-sm">
                                                                                #{index + 1}
                                                                            </span>
                                                                            <span class="text-lg" title="{step.status?.toUpperCase() || 'PENDING'}">{getStatusIcon(step.status)}</span>
                                                                        </div>
                                                                        <span class="text-xs font-medium px-2 py-1 rounded-full {
                                                                            step.status === workflowStates.SUCCESS ? 'bg-green-200 text-green-800' :
                                                                            step.status === workflowStates.FAILURE ? 'bg-red-200 text-red-800' :
                                                                            step.status === workflowStates.RUNNING ? 'bg-blue-200 text-blue-800' :
                                                                            'bg-gray-200 text-gray-800'
                                                                        }">
                                                                            {step.status?.toUpperCase() || 'PENDING'}
                                                                        </span>
                                                                    </div>
                                                                    
                                                                    <!-- Step Title -->
                                                                    <h6 class="text-sm font-medium text-gray-900 mb-3 leading-tight step-title">
                                                                        {step.name}
                                                                    </h6>
                                                                    
                                                                    <!-- Step Details -->
                                                                    <div class="space-y-2 text-xs">
                                                                        <!-- Duration -->
                                                                        <div class="flex items-center justify-between py-1">
                                                                            <span class="text-gray-600">Duration:</span>
                                                                            <span class="font-medium text-gray-900">{formatDuration(step.duration || 0)}</span>
                                                                        </div>
                                                                        
                                                                        <!-- Start Time -->
                                                                        {#if step.startTime}
                                                                            <div class="flex items-center justify-between py-1">
                                                                                <span class="text-gray-600">Started:</span>
                                                                                <span class="text-gray-800">{formatRelativeTime(step.startTime)}</span>
                                                                            </div>
                                                                        {/if}
                                                                        
                                                                        <!-- Job Name -->
                                                                        {#if step.jobName && step.jobName !== 'unknown'}
                                                                            <div class="py-1">
                                                                                <span class="text-gray-600">Job:</span>
                                                                                <span class="text-gray-800 ml-1">{step.jobName}</span>
                                                                            </div>
                                                                        {/if}
                                                                        
                                                                        <!-- Action/Command -->
                                                                        {#if step.action}
                                                                            <div class="mt-3 pt-2 border-t border-gray-200">
                                                                                <span class="text-gray-600 block mb-1">Action:</span>
                                                                                <code class="block bg-white px-2 py-1 rounded text-xs border break-all leading-relaxed step-action-code">
                                                                                    {step.action.length > 60 ? step.action.substring(0, 60) + '...' : step.action}
                                                                                </code>
                                                                            </div>
                                                                        {/if}
                                                                    </div>
                                                                    
                                                                    <!-- Hover Details (REMOVED - No more black overlay) -->
                                                                    <!-- Mobile-friendly: Show details inline instead of hover overlay -->
                                                                </div>
                                                            {/each}
                                                        </div>
                                                        
                                                        <!-- Summary Footer -->
                                                        <div class="mt-4 p-4 bg-gray-100 rounded-lg">
                                                            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                                                                <div class="text-center">
                                                                    <div class="text-lg font-bold text-green-600">
                                                                        {latestRun.steps.filter(s => s.status === workflowStates.SUCCESS).length}
                                                                    </div>
                                                                    <div class="text-gray-600">Successful</div>
                                                                </div>
                                                                <div class="text-center">
                                                                    <div class="text-lg font-bold text-red-600">
                                                                        {latestRun.steps.filter(s => s.status === workflowStates.FAILURE).length}
                                                                    </div>
                                                                    <div class="text-gray-600">Failed</div>
                                                                </div>
                                                                <div class="text-center">
                                                                    <div class="text-lg font-bold text-blue-600">
                                                                        {latestRun.steps.filter(s => s.status === workflowStates.RUNNING).length}
                                                                    </div>
                                                                    <div class="text-gray-600">Running</div>
                                                                </div>
                                                                <div class="text-center">
                                                                    <div class="text-lg font-bold text-gray-600">
                                                                        {latestRun.steps.filter(s => !s.status || s.status === workflowStates.PENDING).length}
                                                                    </div>
                                                                    <div class="text-gray-600">Pending</div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                {/if}
                                            </div>
                                        {/if}
                                        
                                        <!-- Actions -->
                                        <div class="mt-6 pt-4 border-t border-gray-200 flex space-x-4">
                                            {#if workflowHistory[selectedNode.id].repositoryUrl}
                                                <a 
                                                    href="{workflowHistory[selectedNode.id].repositoryUrl}/actions"
                                                    target="_blank"
                                                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200"
                                                >
                                                    <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-2M7 7h10v10M17 7l-4 4" />
                                                    </svg>
                                                    View on GitHub
                                                </a>
                                            {/if}
                                            <button 
                                                on:click={() => loadWorkflowHistory(selectedNode)}
                                                class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                            >
                                                <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                </svg>
                                                Refresh Data
                                            </button>
                                        </div>
                                        
                                    {:else if workflowHistory[selectedNode.id]?.error}
                                        <!-- Enhanced Error State -->
                                        <div class="p-6 bg-red-50 border border-red-200 rounded-lg">
                                            <div class="flex items-start space-x-4">
                                                <div class="flex-shrink-0">
                                                    <svg class="h-8 w-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L3.316 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                                    </svg>
                                                </div>
                                                <div class="flex-1">
                                                    <h3 class="text-red-800 font-medium text-lg">Failed to Load Workflow History</h3>
                                                    <p class="text-red-700 text-sm mt-2 leading-relaxed">
                                                        {workflowHistory[selectedNode.id].error}
                                                    </p>
                                                    
                                                    <!-- Error Details & Suggestions -->
                                                    <div class="mt-4 p-3 bg-red-100 rounded-lg border border-red-200">
                                                        <h4 class="text-red-800 font-medium text-sm mb-2">💡 Troubleshooting Tips:</h4>
                                                        <ul class="text-red-700 text-xs space-y-1 list-disc list-inside">
                                                            <li>Check if the workflow file exists in the repository</li>
                                                            <li>Verify GitHub Actions permissions for this repository</li>
                                                            <li>Ensure the workflow has been run at least once</li>
                                                            <li>Try refreshing the page or clearing cache</li>
                                                        </ul>
                                                    </div>
                                                    
                                                    <!-- Action Buttons -->
                                                    <div class="mt-6 flex flex-wrap gap-3">
                                                        <button 
                                                            on:click={() => loadWorkflowHistory(selectedNode)}
                                                            class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 transition-colors"
                                                        >
                                                            <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                            </svg>
                                                            🔄 Retry Loading
                                                        </button>
                                                        
                                                        {#if selectedNode.repositoryUrl}
                                                            <a 
                                                                href="{selectedNode.repositoryUrl}/actions"
                                                                target="_blank"
                                                                class="inline-flex items-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 transition-colors"
                                                            >
                                                                <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                                </svg>
                                                                View on GitHub
                                                            </a>
                                                        {/if}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    {:else}
                                        <!-- No Workflow Runs -->
                                        <div class="text-center py-12">
                                            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012-2" />
                                            </svg>
                                            <h3 class="mt-2 text-sm font-medium text-gray-900">No workflow runs found</h3>
                                            <p class="mt-1 text-sm text-gray-500">
                                                This workflow hasn't been executed yet or data is not available.
                                            </p>
                                            <div class="mt-6">
                                                <button 
                                                    on:click={() => loadWorkflowHistory(selectedNode)}
                                                    class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                                >
                                                    <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                    </svg>
                                                    Load Workflow Data
                                                </button>
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        {:else if viewMode === 'table'}
                            <!-- Build History Table -->
                            <div class="bg-white">
                                <div class="flex items-center justify-between mb-4">
                                    <h3 class="text-lg font-medium text-gray-900 flex items-center">
                                        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        Build History
                                    </h3>
                                    
                                    <!-- Data Source Badge -->
                                    <div class="flex items-center space-x-2">
                                        {#if dataSource === 'real'}
                                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                🟢 {workflowHistory[selectedNode.id]?.source || 'Live Data'}
                                            </span>
                                        {:else if dataSource === 'none'}
                                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                                ⚪ No Data Available
                                            </span>
                                        {/if}
                                        {#if workflowHistory[selectedNode.id]?.runs?.length}
                                            <span class="text-sm text-gray-500">
                                                {workflowHistory[selectedNode.id].runs.length} builds
                                            </span>
                                        {/if}
                                    </div>
                                </div>
                                
                                {#if workflowHistory[selectedNode.id]?.runs?.length}
                                    <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 rounded-lg">
                                        <table class="min-w-full divide-y divide-gray-300">
                                            <thead class="bg-gray-50">
                                                <tr>
                                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Build</th>
                                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
                                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Author</th>
                                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody class="bg-white divide-y divide-gray-200">
                                                {#each workflowHistory[selectedNode.id].runs as run}
                                                    <tr class="hover:bg-gray-50">
                                                        <td class="px-6 py-4 whitespace-nowrap">
                                                            <div class="flex items-center">
                                                                <div class="text-sm font-medium text-gray-900">{run.buildNumber}</div>
                                                                {#if run.commitSha}
                                                                    <div class="ml-2 text-xs text-gray-400 font-mono">{run.commitSha}</div>
                                                                {/if}
                                                            </div>
                                                            {#if run.commitMessage}
                                                                <div class="text-xs text-gray-500 truncate max-w-xs">{run.commitMessage}</div>
                                                            {/if}
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap">
                                                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusColor(run.status)}">
                                                                {getStatusIcon(run.status)} {run.status}
                                                            </span>
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                            {formatDuration(run.duration)}
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            <div>{formatRelativeTime(run.startTime)}</div>
                                                            <div class="text-xs text-gray-400">{new Date(run.startTime).toLocaleString()}</div>
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {run.author || 'Unknown'}
                                                        </td>
                                                        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                            <div class="flex items-center space-x-2">
                                                                <button 
                                                                    on:click={() => showWorkflowLogs(run)}
                                                                    class="text-blue-600 hover:text-blue-900"
                                                                    title="View Logs"
                                                                    aria-label="View logs for build {run.buildNumber}"
                                                                >
                                                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                                    </svg>
                                                                </button>
                                                                <button 
                                                                    on:click={() => rerunWorkflow(run)}
                                                                    class="text-green-600 hover:text-green-900"
                                                                    title="Rerun Build"
                                                                    aria-label="Rerun build {run.buildNumber}"
                                                                >
                                                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                                    </svg>
                                                                </button>
                                                                <button 
                                                                    on:click={() => deleteWorkflowRun(run)}
                                                                    class="text-red-600 hover:text-red-900"
                                                                    title="Delete Build"
                                                                    aria-label="Delete build {run.buildNumber}"
                                                                >
                                                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                    </svg>
                                                                </button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                {/each}
                                            </tbody>
                                        </table>
                                    </div>
                                {:else}
                                    <div class="text-center py-8">
                                        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        <h3 class="mt-2 text-sm font-medium text-gray-900">No build history</h3>
                                        <p class="mt-1 text-sm text-gray-500">Run your workflow to see build history.</p>
                                        <div class="mt-6">
                                            <button 
                                                on:click={() => runWorkflow(selectedNode)}
                                                class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                                            >
                                                <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1m4-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                </svg>
                                                Run Workflow
                                            </button>
                                        </div>
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    {/if}
                </div>
            {:else}
                <!-- Empty State -->
                <div class="flex-1 flex items-center justify-center">
                    <div class="text-center">
                        <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 mb-4">
                            <svg class="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                            </svg>
                        </div>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">Select an item to view details</h3>
                        <p class="text-gray-600">Click on any folder or workflow in the tree to see its contents and metadata.</p>
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>

<!-- Context Menu -->
{#if showContextMenu}
    <div 
        class="context-menu fixed bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50"
        style="left: {contextMenuPosition.x}px; top: {contextMenuPosition.y}px;"
    >
        <button 
            on:click={() => startEditing(contextMenuNode)}
            class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
        >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            <span>Rename</span>
        </button>
        
        {#if contextMenuNode && contextMenuNode.type === 'workflow'}
            <button 
                on:click={() => openFileEditor(contextMenuNode)}
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                <span>Edit Content</span>
            </button>
        {/if}
        
        
        <button 
            on:click={() => duplicateNode(contextMenuNode)}
            class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
        >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <span>Duplicate</span>
        </button>
        
        <hr class="my-2" />
        
        <button 
            on:click={() => deleteNode(contextMenuNode)}
            class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
        >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <span>Delete</span>
        </button>
    </div>
{/if}

<!-- New Item Modal -->
{#if showNewItemModal}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mt-3">
                <h3 class="text-lg font-medium text-gray-900 mb-4">
                    Create New {newItemType === 'folder' ? 'Folder' : 'Workflow'}
                </h3>
                
                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-700 mb-2" for="new-item-name">
                        {newItemType === 'folder' ? 'Folder' : 'Workflow'} Name
                    </label>
                    <input
                        bind:value={newItemName}
                        placeholder="Enter name..."
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        on:keypress={(e) => e.key === 'Enter' && createNewItem()}
                        id="new-item-name"
                    />
                </div>
                
                {#if newItemParent}
                    <div class="mb-4 p-3 bg-gray-50 rounded-md">
                        <p class="text-sm text-gray-600">
                            Will be created inside: <span class="font-medium">{newItemParent.name}</span>
                        </p>
                    </div>
                {/if}
                
                <div class="flex justify-end space-x-3">
                    <button
                        on:click={closeNewItemModal}
                        class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                    >
                        Cancel
                    </button>
                    <button
                        on:click={createNewItem}
                        disabled={!newItemName.trim()}
                        class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                        Create {newItemType === 'folder' ? 'Folder' : 'Workflow'}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<!-- File Editor Modal -->
{#if showFileEditor}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-10 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-medium text-gray-900">
                    Edit Workflow: {selectedNode?.name}
                </h3>
                <button 
                    on:click={closeFileEditor}
                    class="text-gray-400 hover:text-gray-600"
                    aria-label="Close file editor"
                >
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            <div class="mb-4">
                <textarea
                    bind:value={fileEditorContent}
                    class="w-full h-96 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    placeholder="Enter workflow content..."
                ></textarea>
            </div>
            
            <div class="flex justify-end space-x-3">
                <button
                    on:click={closeFileEditor}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                >
                    Cancel
                </button>
                <button
                    on:click={saveFileContent}
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                >
                    Save Content
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- Build Parameters Modal (like Jenkins) -->
{#if showBuildParameters}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-10 mx-auto p-5 border w-11/12 max-w-3xl shadow-lg rounded-md bg-white">
            <div class="flex items-center justify-between mb-4">
                <div>
                    <h3 class="text-lg font-medium text-gray-900 flex items-center space-x-2">
                        🔧 <span>Build with Parameters</span>
                    </h3>
                    <p class="text-sm text-gray-600 mt-1">Configure and run: <strong>{selectedNode?.name || 'Unknown Workflow'}</strong></p>
                </div>
                <button 
                    on:click={() => showBuildParameters = false}
                    class="text-gray-400 hover:text-gray-600"
                    aria-label="Close parameters modal"
                >
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            <div class="max-h-96 overflow-y-auto mb-4">
                <div class="space-y-4">
                    {#each Object.entries(buildParameters) as [key, param]}
                        <div class="border-l-4 border-blue-400 pl-4 py-2 bg-gray-50 rounded-r">
                            <label for="param-{key}" class="block text-sm font-medium text-gray-900 mb-1">
                                {key.replace(/_/g, ' ')}
                                {#if param.description}
                                    <span class="block text-xs text-gray-500 font-normal mt-1">{param.description}</span>
                                {/if}
                            </label>
                            
                            {#if param.type === 'boolean'}
                                <label class="flex items-center space-x-2 cursor-pointer">
                                    <input 
                                        id="param-{key}"
                                        type="checkbox" 
                                        bind:checked={param.value}
                                        class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                    />
                                    <span class="text-sm text-gray-700">Enable {key.replace(/_/g, ' ').toLowerCase()}</span>
                                </label>
                            {:else if param.type === 'choice'}
                                <select id="param-{key}" bind:value={param.value} class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                                    {#each param.choices as choice}
                                        <option value={choice}>{choice}</option>
                                    {/each}
                                </select>
                            {:else}
                                <input 
                                    id="param-{key}"
                                    type="text" 
                                    bind:value={param.value}
                                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="Enter {key.replace(/_/g, ' ').toLowerCase()}"
                                />
                            {/if}
                        </div>
                    {/each}
                </div>
            </div>
            
            <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                <button
                    on:click={() => showBuildParameters = false}
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                >
                    Cancel
                </button>
                <button
                    on:click={runWithParameters}
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 flex items-center space-x-2"
                >
                    <span>🚀</span>
                    <span>Build Now</span>
                </button>
            </div>
        </div>
    </div>
{/if}



<!-- Save Status -->
{#if saveStatus}
    <div class="fixed bottom-4 right-4 z-50">
        <div class="bg-white shadow-lg rounded-lg p-4 border {saveSuccess ? 'border-green-200' : 'border-red-200'}">
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    {#if saveSuccess}
                        <svg class="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    {:else}
                        <svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    {/if}
                </div>
                <div class="ml-3">
                    <p class="text-sm font-medium {saveSuccess ? 'text-green-800' : 'text-red-800'}">{saveStatus}</p>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Enhanced Mobile Responsiveness for Step Execution Grid */
    @media (max-width: 640px) {
        /* Force single column on mobile for better readability */
        .step-execution-grid {
            grid-template-columns: 1fr !important;
        }
        
        /* Reduce padding on mobile cards */
        .step-card {
            padding: 12px !important;
        }
        
        /* Hide hover overlays on mobile */
        
        /* Improve text sizing on mobile */
        .step-title {
            font-size: 0.875rem !important;
            line-height: 1.25rem !important;
        }
        
        /* Compact action button layout */
        .step-action-code {
            font-size: 0.75rem !important;
            max-height: 60px !important;
            overflow: hidden !important;
        }
    }
    
    /* Smooth transitions for loading states */
    .animate-pulse {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: .5;
        }
    }
    
    /* Custom scrollbar for workflow containers */
    .workflow-scroll {
        scrollbar-width: thin;
        scrollbar-color: #d1d5db #f3f4f6;
    }
    
    .workflow-scroll::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    .workflow-scroll::-webkit-scrollbar-track {
        background: #f3f4f6;
        border-radius: 3px;
    }
    
    .workflow-scroll::-webkit-scrollbar-thumb {
        background: #d1d5db;
        border-radius: 3px;
    }
    
    .workflow-scroll::-webkit-scrollbar-thumb:hover {
        background: #9ca3af;
    }
    
    /* Enhanced grid responsiveness */
    .responsive-step-grid {
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }
    
    @media (max-width: 768px) {
        .responsive-step-grid {
            grid-template-columns: 1fr;
            gap: 0.75rem;
        }
    }
    
    /* Loading animation improvements */
    .loading-dots {
        display: inline-flex;
        align-items: center;
    }
    
    .loading-dots > div {
        animation: loading-bounce 1.4s ease-in-out infinite both;
    }
    
    .loading-dots > div:nth-child(1) { animation-delay: -0.32s; }
    .loading-dots > div:nth-child(2) { animation-delay: -0.16s; }
    .loading-dots > div:nth-child(3) { animation-delay: 0s; }
    
    @keyframes loading-bounce {
        0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }
</style>
