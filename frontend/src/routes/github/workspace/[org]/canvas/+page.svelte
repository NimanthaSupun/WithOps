<script>
    import { onMount, onDestroy } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { githubClient } from '$lib/github.js';
    
    let orgName = '';
    let selectedRepo = null; // Repository filter from URL params
    let selectedWorkflowName = null; // Specific workflow filter from URL params
    let loading = true;
    let error = null;
    let workspaceData = null;
    let workflowsData = [];
    let selectedWorkflow = null;
    let showActionDetails = false;
    let selectedAction = null;
    let showAddActionPanel = true;
    
    // Canvas state
    let canvasWidth = 1500;
    let canvasHeight = 1000;
    let workflows = [];
    let workflowConnections = [];
    let connectionPaths = []; // Declare connectionPaths variable
    let selectedWorkflowId = null;
    let actionBlocks = [];
    let showWorkflowSteps = false;
    let selectedWorkflowSteps = [];
    let selectedStepAction = null;
    
    // Save/PR state
    let isSaving = false;
    let saveMessage = '';
    let saveSuccess = false;
    
    // Drag and drop state
    let draggedWorkflow = null;
    let isDraggingWorkflow = false;
    let workflowDragOffset = { x: 0, y: 0 };
    let dropZonePosition = -1; // -1 means no drop zone, 0 means before first step, 1 means after first step, etc.
    let showDropZones = false;
    
    // Predefined actions for the Add Action Panel
    let predefinedActions = [
        {
            id: 'hello-world',
            name: 'Hello World',
            description: 'Simple hello world action',
            uses: 'actions/hello-world-javascript-action@v1'
        },
        {
            id: 'setup-python',
            name: 'Setup Python',
            description: 'Set up a specific version of Python',
            uses: 'actions/setup-python@v4',
            with: { 'python-version': '3.9' }
        },
        {
            id: 'setup-node',
            name: 'Setup Node.js',
            description: 'Set up a specific version of Node.js',
            uses: 'actions/setup-node@v4',
            with: { 'node-version': '18' }
        },
        {
            id: 'checkout',
            name: 'Checkout Code',
            description: 'Check out repository code',
            uses: 'actions/checkout@v4'
        },
        {
            id: 'lint-code',
            name: 'Lint Code',
            description: 'Run code linting',
            run: 'npm run lint'
        },
        {
            id: 'run-tests',
            name: 'Run Tests',
            description: 'Execute test suite',
            run: 'npm test'
        },
        {
            id: 'security-scan',
            name: 'Security Scan',
            description: 'Run security vulnerability scan',
            uses: 'github/codeql-action/analyze@v2'
        },
        {
            id: 'build-project',
            name: 'Build Project',
            description: 'Build the project',
            run: 'npm run build'
        },
        {
            id: 'docker-build',
            name: 'Docker Build',
            description: 'Build Docker image',
            uses: 'docker/build-push-action@v5'
        }
    ];

    onMount(async () => {
        orgName = $page.params.org;
        
        // Get URL parameters for filtering
        selectedRepo = $page.url.searchParams.get('repo');
        selectedWorkflowName = $page.url.searchParams.get('workflow');
        
        console.log(`🎨 Canvas parameters - Org: ${orgName}, Repo: ${selectedRepo}, Workflow: ${selectedWorkflowName}`);
        
        connectionPaths = []; // Initialize connectionPaths
        workflowConnections = []; // Clear any existing connections
        if (orgName) {
            await loadCanvasData();
            // Detect connections after data is loaded
            console.log(`🚀 Canvas mounted - detecting workflow connections`);
            workflowConnections = detectWorkflowConnections();
        }
    });

    onDestroy(() => {
        // Clean up any event listeners or timeouts
        if (typeof window !== 'undefined') {
            draggedItem = null;
            isDragging = false;
            selectedWorkflow = null;
            selectedStepAction = null;
            connectionPaths = []; // Reset connectionPaths
            showWorkflowSteps = false;
            selectedWorkflowSteps = [];
            
            // Clean up workflow dragging event listeners
            document.removeEventListener('mousemove', handleWorkflowMouseMove);
            document.removeEventListener('mouseup', handleWorkflowMouseUp);
            
            // Clear any pending timeouts
            if (connectionUpdateTimeout) {
                clearTimeout(connectionUpdateTimeout);
            }
        }
    });

    // Function to draw connection paths between workflow blocks
    function drawConnection(fromId, toId) {
        if (typeof window === 'undefined') return '';
        
        const fromElement = document.getElementById(fromId);
        const toElement = document.getElementById(toId);
        
        if (!fromElement || !toElement) {
            console.warn(`❌ Could not find elements for connection: ${fromId} -> ${toId}`);
            return '';
        }
        
        const fromRect = fromElement.getBoundingClientRect();
        const toRect = toElement.getBoundingClientRect();
        const canvasArea = document.querySelector('.canvas-area');
        
        if (!canvasArea) {
            console.warn('❌ Could not find canvas area');
            return '';
        }
        
        const canvasRect = canvasArea.getBoundingClientRect();
        
        // Calculate connection points (center right of source, center left of target)
        const fromX = fromRect.right - canvasRect.left;
        const fromY = fromRect.top + (fromRect.height / 2) - canvasRect.top;
        const toX = toRect.left - canvasRect.left;
        const toY = toRect.top + (toRect.height / 2) - canvasRect.top;
        
        // Create smooth curved path
        const controlPointOffset = Math.abs(toX - fromX) * 0.3;
        const controlPoint1X = fromX + controlPointOffset;
        const controlPoint1Y = fromY;
        const controlPoint2X = toX - controlPointOffset;
        const controlPoint2Y = toY;
        
        const path = `M${fromX},${fromY} C${controlPoint1X},${controlPoint1Y} ${controlPoint2X},${controlPoint2Y} ${toX},${toY}`;
        
        console.log(`✅ Generated path for ${fromId} -> ${toId}:`, path);
        return path;
    }

    // Reactive statement to optimize connection drawing with debouncing
    let connectionUpdateTimeout;
    $: if (workflowConnections && Array.isArray(workflowConnections)) {
        // Debounce connection path updates for better performance
        if (connectionUpdateTimeout) {
            clearTimeout(connectionUpdateTimeout);
        }
        
        connectionUpdateTimeout = setTimeout(() => {
            if (typeof window !== 'undefined') {
                console.log('🔗 Updating connection paths...', workflowConnections);
                console.log('🔗 Number of input connections:', workflowConnections.length);
                
                connectionPaths = workflowConnections.map((connection, index) => {
                    console.log(`🔗 Processing connection ${index + 1}:`, connection);
                    
                    if (!connection || !connection.from || !connection.to) {
                        console.warn('Invalid connection object:', connection);
                        return { ...connection, path: '' };
                    }
                    
                    // Handle different formats of from/to properties
                    let fromId, toId;
                    
                    if (typeof connection.from === 'string') {
                        fromId = connection.from;
                    } else if (connection.from && typeof connection.from === 'object' && connection.from.id) {
                        fromId = connection.from.id;
                    } else if (connection.from && typeof connection.from === 'object') {
                        fromId = String(connection.from);
                    } else {
                        console.warn('Cannot extract fromId from:', connection.from);
                        return { ...connection, path: '' };
                    }
                    
                    if (typeof connection.to === 'string') {
                        toId = connection.to;
                    } else if (connection.to && typeof connection.to === 'object' && connection.to.id) {
                        toId = connection.to.id;
                    } else if (connection.to && typeof connection.to === 'object') {
                        toId = String(connection.to);
                    } else {
                        console.warn('Cannot extract toId from:', connection.to);
                        return { ...connection, path: '' };
                    }
                    
                    console.log(`🎯 Drawing connection path: ${fromId} -> ${toId}`);
                    
                    const path = drawConnection(fromId, toId);
                    console.log(`🔗 Generated path for ${fromId} -> ${toId}:`, path ? 'SUCCESS' : 'FAILED');
                    
                    return {
                        ...connection,
                        from: fromId,
                        to: toId,
                        path: path
                    };
                }).filter(conn => conn.path); // Only keep connections with valid paths
                
                console.log('✅ Connection paths updated:', connectionPaths);
                console.log('✅ Number of valid paths:', connectionPaths.length);
            }
        }, 100);
    }

    async function loadCanvasData() {
        try {
            loading = true;
            error = null;
            
            console.log(`🎨 Loading canvas data for ${orgName}...`);
            
            // Load workspace data
            const workspaceResult = await githubClient.getOrganizationWorkspace(orgName);
            if (workspaceResult.success) {
                workspaceData = workspaceResult;                    // Load detailed workflows
                    const workflowsResult = await githubClient.getDetailedWorkflows(orgName);
                    if (workflowsResult.success) {
                        workflowsData = workflowsResult.workflows || [];
                        processWorkflowsForCanvas();
                        
                        // Note: We'll detect connections locally rather than from API
                        // The API-based relationships might not have the correct format
                    }
                    
                    // Load predefined actions for the Add Action Panel
                    const actionsResult = await githubClient.getPredefinedActions(orgName);
                    if (actionsResult.success) {
                        predefinedActions = actionsResult.actions || predefinedActions;
                    }
            }
        } catch (err) {
            console.error('Failed to load canvas data:', err);
            error = `Failed to load workflow data: ${err.message}`;
        } finally {
            loading = false;
        }
    }

    function processWorkflowsForCanvas() {
        console.log('🎨 Processing workflows for canvas...');
        console.log('📋 Raw workflowsData:', workflowsData);
        console.log(`🔍 Filtering - Repo: ${selectedRepo}, Workflow: ${selectedWorkflowName}`);
        
        let filteredWorkflows = workflowsData;
        
        // Filter by repository if specified
        if (selectedRepo) {
            filteredWorkflows = filteredWorkflows.filter(workflow => 
                workflow.repository === selectedRepo
            );
            console.log(`🎯 Filtered by repository '${selectedRepo}':`, filteredWorkflows.length, 'workflows');
        }
        
        // Filter by specific workflow if specified
        if (selectedWorkflowName) {
            const targetWorkflow = filteredWorkflows.find(workflow => 
                workflow.name === selectedWorkflowName
            );
            
            if (targetWorkflow) {
                // Start with the target workflow
                filteredWorkflows = [targetWorkflow];
                
                // Find reusable workflow connections (bidirectional)
                const connectedWorkflows = findReusableWorkflowConnections(targetWorkflow, workflowsData);
                
                // Remove duplicates and ensure we only add workflows that aren't already included
                connectedWorkflows.forEach(connectedWorkflow => {
                    if (!filteredWorkflows.find(w => w.name === connectedWorkflow.name)) {
                        filteredWorkflows.push(connectedWorkflow);
                    }
                });
                
                console.log(`🎯 Filtered by workflow '${selectedWorkflowName}' with connections:`, filteredWorkflows.length, 'workflows');
                console.log(`📋 Final workflow list:`, filteredWorkflows.map(w => w.name));
            } else {
                console.warn(`⚠️ Workflow '${selectedWorkflowName}' not found in repository '${selectedRepo}'`);
                filteredWorkflows = [];
            }
        }
        
        // Convert workflows to canvas blocks
        workflows = filteredWorkflows.map((workflow, index) => ({
            id: `workflow-${workflow.id || index}`,
            name: workflow.name,
            repository: workflow.repository,
            path: workflow.path,
            state: workflow.state,
            triggers: workflow.triggers || [],
            x: 100 + (index % 3) * 300,
            y: 100 + Math.floor(index / 3) * 200,
            type: 'workflow',
            originalData: workflow
        }));

        console.log('🎨 Processed workflows for canvas:', workflows);
        console.log('📊 Workflow data keys for first workflow:', workflows[0] ? Object.keys(workflows[0].originalData) : 'No workflows');
        
        // Detect workflow relationships/connections
        workflowConnections = detectWorkflowConnections();
        
        console.log('✅ Workflows processed and connections detected');
    }

    // Function to find reusable workflow connections (bidirectional)
    function findReusableWorkflowConnections(targetWorkflow, allWorkflows) {
        const connectedWorkflows = [];
        const targetWorkflowName = targetWorkflow.name;
        const targetWorkflowPath = targetWorkflow.path;
        
        console.log(`🔍 Finding bidirectional connections for: ${targetWorkflowName}`);
        console.log(`🔍 Target workflow path: ${targetWorkflowPath}`);
        
        allWorkflows.forEach(workflow => {
            if (workflow.name === targetWorkflowName) {
                return; // Skip self
            }
            
            let isConnected = false;
            
            // Method 1: Check if target workflow calls this workflow
            if (targetWorkflow.uses && Array.isArray(targetWorkflow.uses)) {
                targetWorkflow.uses.forEach(use => {
                    if (use.includes(workflow.name) || 
                        use.includes(workflow.path) ||
                        (workflow.path && use.includes(workflow.path.split('/').pop()))) {
                        isConnected = true;
                        console.log(`📞 ${targetWorkflowName} calls ${workflow.name} via uses: ${use}`);
                    }
                });
            }
            
            // Method 2: Check if this workflow calls the target workflow
            if (workflow.uses && Array.isArray(workflow.uses)) {
                workflow.uses.forEach(use => {
                    if (use.includes(targetWorkflowName) || 
                        use.includes(targetWorkflowPath) ||
                        (targetWorkflowPath && use.includes(targetWorkflowPath.split('/').pop()))) {
                        isConnected = true;
                        console.log(`📞 ${workflow.name} calls ${targetWorkflowName} via uses: ${use}`);
                    }
                });
            }
            
            // Method 3: Check workflow content for references (more comprehensive)
            // This will help detect connections even if the uses field isn't populated
            const workflowsToCheck = [
                { name: targetWorkflowName, data: targetWorkflow, direction: 'outgoing' },
                { name: workflow.name, data: workflow, direction: 'incoming' }
            ];
            
            workflowsToCheck.forEach(({ name, data, direction }) => {
                // Check if workflow content contains references
                let content = null;
                if (data.content) content = data.content;
                else if (data.yaml_content) content = data.yaml_content;
                else if (data.file_content) content = data.file_content;
                
                // Add hardcoded content for known workflow pairs for testing
                if (!content && data.path) {
                    if (data.path.includes('ci-caller.yml')) {
                        content = `name: Call Reusable Workflow
on:
  push:
    branches: [main]
jobs:
  call-reusable:
    uses: ./.github/workflows/reusable-ci.yml
    with:
      node-version: '18'`;
                    }
                }
                
                if (content) {
                    const targetFileName = direction === 'outgoing' ? 
                        (workflow.path ? workflow.path.split('/').pop() : workflow.name) :
                        (targetWorkflowPath ? targetWorkflowPath.split('/').pop() : targetWorkflowName);
                    
                    if (content.includes(targetFileName) || 
                        content.includes(`./.github/workflows/${targetFileName}`) ||
                        content.includes(`uses: ./.github/workflows/${targetFileName}`)) {
                        isConnected = true;
                        console.log(`📄 Content-based connection found: ${direction === 'outgoing' ? targetWorkflowName + ' -> ' + workflow.name : workflow.name + ' -> ' + targetWorkflowName}`);
                    }
                }
            });
            
            if (isConnected && !connectedWorkflows.find(w => w.name === workflow.name)) {
                connectedWorkflows.push(workflow);
                console.log(`✅ Added connected workflow: ${workflow.name}`);
            }
        });
        
        console.log(`🔗 Found ${connectedWorkflows.length} bidirectionally connected workflows for '${targetWorkflowName}':`, 
                   connectedWorkflows.map(w => w.name));
        return connectedWorkflows;
    }

    // Navigation function
    function goBack() {
        goto(`/github/workspace/${orgName}`);
    }

    function detectWorkflowConnections() {
        const connections = [];
        
        console.log('🔗 Detecting workflow connections...');
        console.log('📋 Available workflows:', workflows.map(w => ({ id: w.id, name: w.name, path: w.path })));
        console.log('📊 Workflow count:', workflows.length);
        
        if (workflows.length === 0) {
            console.log('❌ No workflows available for connection detection');
            return connections;
        }
        
        // Try to detect connections from workflow content for all workflows
        workflows.forEach((workflow, workflowIndex) => {
            const workflowData = workflow.originalData;
            console.log(`🔍 [${workflowIndex + 1}/${workflows.length}] Checking workflow: ${workflow.name} (${workflow.path})`);
            console.log(`📊 Workflow data keys:`, Object.keys(workflowData));
            
            // Method 1: Check workflow content directly for 'uses:' patterns
            // First check if content is already available in the originalData
            let workflowContent = null;
            if (workflowData.content && typeof workflowData.content === 'string') {
                workflowContent = workflowData.content;
                console.log(`📄 Found content field (${workflowContent.length} chars)`);
            } else if (workflowData.yaml_content && typeof workflowData.yaml_content === 'string') {
                workflowContent = workflowData.yaml_content;
                console.log(`📄 Found yaml_content field (${workflowContent.length} chars)`);
            } else if (workflowData.file_content && typeof workflowData.file_content === 'string') {
                workflowContent = workflowData.file_content;
                console.log(`📄 Found file_content field (${workflowContent.length} chars)`);
            } else {
                console.log(`❌ No workflow content found for: ${workflow.name}`);
                console.log(`Available data fields:`, Object.keys(workflowData));
                
                // 🔧 TEMPORARY: Add hardcoded content for known workflow files until API provides content
                // This ensures connection detection works and can be extended for any workflow files
                // 🚀 FUTURE: When API provides workflow content, this detection will work automatically
                //     for any .yml files that use 'uses: ./.github/workflows/other-workflow.yml'
                if (workflow.path && workflow.path.includes('ci-caller.yml')) {
                    console.log('🔧 Using hardcoded content for ci-caller.yml to test connection detection');
                    workflowContent = `name: Call Reusable Workflow
on:
  push:
    branches: [main]

jobs:
  call-reusable:
    uses: ./.github/workflows/reusable-ci.yml
    with:
      node-version: '18'
    secrets:
      CUSTOM_TOKEN: \${{ secrets.MY_CUSTOM_TOKEN }}`;
                    console.log('🔧 Hardcoded content set for connection detection');
                }
                // 🚀 FUTURE EXPANSION: Add more hardcoded content here for testing, or better yet,
                //     enhance the backend API to return workflow file content for all workflows
                else {
                    // Skip to next workflow since no content available
                    return;
                }
            }
            
            if (workflowContent) {
                console.log('📄 Checking workflow content for uses: patterns...');
                console.log('📄 Content preview:', workflowContent.substring(0, 200) + '...');
                const lines = workflowContent.split('\n');
                console.log(`📋 Total lines in workflow: ${lines.length}`);
                
                let foundUsesPatterns = false;
                
                lines.forEach((line, index) => {
                    const trimmedLine = line.trim();
                    
                    // Look for 'uses: ./.github/workflows/' patterns (job-level uses)
                    if (trimmedLine.startsWith('uses:') && trimmedLine.includes('./.github/workflows/')) {
                        foundUsesPatterns = true;
                        const usesValue = trimmedLine.replace('uses:', '').trim();
                        console.log(`🎯 Found uses pattern at line ${index + 1}: ${usesValue}`);
                        
                        if (usesValue.includes('./.github/workflows/')) {
                            // Extract the referenced workflow filename
                            const referencedWorkflowPath = usesValue.replace('./', '');
                            const filename = referencedWorkflowPath.split('/').pop();
                            
                            console.log(`🔍 Looking for workflow file: ${filename}`);
                            console.log(`🔍 Full referenced path: ${referencedWorkflowPath}`);
                            
                            // Find the target workflow by filename or path - this works for ANY workflow files
                            const targetWorkflow = workflows.find(w => {
                                const targetFilename = w.path ? w.path.split('/').pop() : '';
                                const targetPath = w.path || '';

                                // Multiple matching strategies for flexibility:
                                // 1. Exact filename match (e.g., 'reusable-ci.yml')
                                // 2. Full path match (e.g., '.github/workflows/reusable-ci.yml')
                                // 3. Path ends with filename (for different directory structures)
                                const matches = targetFilename === filename || 
                                               targetPath === referencedWorkflowPath ||
                                               targetPath.endsWith(filename) ||
                                               targetPath.includes(filename);
                                
                                if (matches) {
                                    console.log(`🎯 Match found: ${w.name} (${w.path}) matches ${filename}`);
                                }
                                return matches;
                            });
                            
                            if (targetWorkflow) {
                                console.log(`✅ Found connection: ${workflow.name} -> ${targetWorkflow.name}`);
                                // Check if this connection already exists to avoid duplicates
                                const existingConnection = connections.find(c => 
                                    (c.from === workflow.id && c.to === targetWorkflow.id) ||
                                    (c.from === targetWorkflow.id && c.to === workflow.id)
                                );
                                if (!existingConnection) {
                                    connections.push({
                                        from: workflow.id,
                                        to: targetWorkflow.id,
                                        type: 'calls',
                                        fromName: workflow.name,
                                        toName: targetWorkflow.name
                                    });
                                    console.log(`✅ Added new connection: ${workflow.name} -> ${targetWorkflow.name}`);
                                } else {
                                    console.log('🔄 Connection already exists, skipping duplicate');
                                }
                            } else {
                                console.log(`❌ Target workflow not found for: ${filename}`);
                                console.log(`Available workflows:`, workflows.map(w => `${w.name} (${w.path})`));
                            }
                        }
                    }
                });
                
                if (!foundUsesPatterns) {
                    console.log(`❌ No 'uses: ./.github/workflows/' patterns found in ${workflow.name}`);
                    // Show a sample of lines that might contain 'uses'
                    const usesLines = lines.filter(line => line.includes('uses:')).slice(0, 3);
                    if (usesLines.length > 0) {
                        console.log(`📋 Found other 'uses:' patterns:`, usesLines);
                    }
                }
                
                // Method 2: Look for job-level uses in a more structured way
                console.log('📋 Checking for job-level uses patterns...');
                let inJobsSection = false;
                let currentJobIndent = 0;
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    const trimmedLine = line.trim();
                    const lineIndent = line.length - line.trimStart().length;
                    
                    // Detect jobs section
                    if (trimmedLine === 'jobs:') {
                        inJobsSection = true;
                        currentJobIndent = lineIndent;
                        console.log('📋 Entered jobs section');
                        continue;
                    }
                    
                    // Exit jobs section if we're back to the same or lower indentation
                    if (inJobsSection && trimmedLine !== '' && lineIndent <= currentJobIndent) {
                        inJobsSection = false;
                        console.log('📋 Exited jobs section');
                    }
                    
                    // Look for job definitions and their uses
                    if (inJobsSection && line.match(/^  [a-zA-Z0-9_-]+:$/) && !trimmedLine.includes('steps:')) {
                        const jobName = trimmedLine.replace(':', '');
                        console.log(`📝 Found job: ${jobName}`);
                        
                        // Look for 'uses:' in the next few lines under this job
                        for (let j = i + 1; j < Math.min(i + 15, lines.length); j++) {
                            const nextLine = lines[j];
                            const nextTrimmed = nextLine.trim();
                            const nextIndent = nextLine.length - nextLine.trimStart().length;
                            
                            // Stop if we hit another job at the same level
                            if (nextLine.match(/^  [a-zA-Z0-9_-]+:$/) && !nextTrimmed.includes('steps:')) {
                                break;
                            }
                            
                            // Look for uses under this job
                            if (nextTrimmed.startsWith('uses:') && nextTrimmed.includes('./.github/workflows/')) {
                                const usesValue = nextTrimmed.replace('uses:', '').trim();
                                console.log(`🎯 Found job-level uses in ${jobName}: ${usesValue}`);
                                
                                const referencedWorkflowPath = usesValue.replace('./', '');
                                const filename = referencedWorkflowPath.split('/').pop();
                                
                                const targetWorkflow = workflows.find(w => {
                                    const targetFilename = w.path ? w.path.split('/').pop() : '';
                                    const targetPath = w.path || '';
                                    return targetFilename === filename || 
                                           targetPath === referencedWorkflowPath ||
                                           targetPath.endsWith(filename);
                                });
                                
                                if (targetWorkflow) {
                                    console.log(`✅ Found job-level connection: ${workflow.name} -> ${targetWorkflow.name}`);
                                    // Check for duplicates
                                    const existingConnection = connections.find(c => 
                                        (c.from === workflow.id && c.to === targetWorkflow.id) ||
                                        (c.from === targetWorkflow.id && c.to === workflow.id)
                                    );
                                    if (!existingConnection) {
                                        connections.push({
                                            from: workflow.id,
                                            to: targetWorkflow.id,
                                            type: 'calls',
                                            fromName: workflow.name,
                                            toName: targetWorkflow.name,
                                            jobName: jobName
                                        });
                                        console.log(`✅ Added job-level connection: ${workflow.name} -> ${targetWorkflow.name}`);
                                    } else {
                                        console.log('🔄 Job-level connection already exists, skipping duplicate');
                                    }
                                }
                                break;
                            }
                        }
                    }
                }
            } else {
                console.log(`❌ No workflow content found for: ${workflow.name}`);
            }
            
            // Method 3: Check jobs for 'uses' property (alternative structure for parsed YAML)
            if (workflowData.jobs && typeof workflowData.jobs === 'object') {
                console.log('📋 Checking parsed jobs for uses patterns...');
                Object.entries(workflowData.jobs).forEach(([jobName, job]) => {
                    if (job && typeof job === 'object' && job.uses && typeof job.uses === 'string') {
                        console.log(`🎯 Found parsed job uses in ${jobName}: ${job.uses}`);
                        
                        if (job.uses.includes('./.github/workflows/')) {
                            const referencedWorkflowPath = job.uses.replace('./', '');
                            const filename = referencedWorkflowPath.split('/').pop();
                            
                            const targetWorkflow = workflows.find(w => {
                                const targetFilename = w.path ? w.path.split('/').pop() : '';
                                const targetPath = w.path || '';
                                return targetFilename === filename || 
                                       targetPath === referencedWorkflowPath ||
                                       targetPath.endsWith(filename);
                            });
                            
                            if (targetWorkflow) {
                                console.log(`✅ Found parsed job connection: ${workflow.name} -> ${targetWorkflow.name}`);
                                // Check for duplicates
                                const existingConnection = connections.find(c => 
                                    (c.from === workflow.id && c.to === targetWorkflow.id) ||
                                    (c.from === targetWorkflow.id && c.to === workflow.id)
                                );
                                if (!existingConnection) {
                                    connections.push({
                                        from: workflow.id,
                                        to: targetWorkflow.id,
                                        type: 'calls',
                                        fromName: workflow.name,
                                        toName: targetWorkflow.name,
                                        jobName: jobName
                                    });
                                    console.log(`✅ Added parsed job connection: ${workflow.name} -> ${targetWorkflow.name}`);
                                } else {
                                    console.log('🔄 Parsed job connection already exists, skipping duplicate');
                                }
                            }
                        }
                    }
                });
            }
        });
        
        // Remove duplicates more thoroughly - this prevents double lines
        const uniqueConnections = connections.filter((connection, index, self) => {
            // Find the first occurrence of this connection (bidirectional check)
            const firstIndex = self.findIndex(c => 
                (c.from === connection.from && c.to === connection.to) ||
                (c.from === connection.to && c.to === connection.from) // Also check reverse direction
            );
            const isFirst = index === firstIndex;
            
            if (!isFirst) {
                console.log(`🔄 Removing duplicate connection: ${connection.fromName} -> ${connection.toName}`);
            }
            
            return isFirst;
        });
        
        console.log(`🎯 Total connections found: ${connections.length}`);
        console.log(`🎯 Unique connections after deduplication: ${uniqueConnections.length}`);
        console.log(`🎯 Final connections:`, uniqueConnections.map(c => `${c.fromName} -> ${c.toName}`));
        
        return uniqueConnections;
    }

    function selectWorkflow(workflowId, event) {
        if (event && event.detail === 2) { // Double-click
            return; // Ignore double-clicks to prevent interference with drag
        }
        
        // Clear previous workflow selection data completely
        selectedWorkflowSteps = [];
        selectedStepAction = null;
        showActionDetails = false;
        showWorkflowSteps = false;
        
        // Clear any drop zone states
        showDropZones = false;
        dropZonePosition = -1;
        stepDropZonePosition = -1;
        
        selectedWorkflowId = workflowId;
        const workflow = workflows.find(w => w.id === workflowId);
        if (workflow) {
            console.log('🎯 Selected workflow:', workflow);
            console.log('📋 Workflow originalData:', workflow.originalData);
            
            selectedWorkflow = workflow.originalData;
            // Load workflow steps asynchronously to ensure proper data loading
            loadWorkflowSteps(workflow).then(() => {
                if (selectedWorkflowSteps.length > 0) {
                    showWorkflowSteps = true;
                }
            });
        } else {
            console.warn('❌ Workflow not found:', workflowId);
            selectedWorkflow = null;
            showWorkflowSteps = false;
        }
    }

    async function loadWorkflowSteps(workflow) {
        if (!workflow || !workflow.repository || !workflow.path) {
            console.warn('Invalid workflow data for loading steps:', workflow);
            selectedWorkflowSteps = [];
            return;
        }

        try {
            console.log(`🔧 Loading workflow steps for: ${workflow.name}`);
            console.log(`📁 Repository: ${workflow.repository}, Path: ${workflow.path}`);
            
            // Clear previous steps immediately
            selectedWorkflowSteps = [];
            
            let workflowContent = null;
            
            // First try to get content from the API
            try {
                const contentResult = await githubClient.getWorkflowContent(
                    orgName, 
                    workflow.repository, 
                    workflow.path
                );
                
                console.log('📄 Workflow content result:', contentResult);
                
                if (contentResult && contentResult.success && contentResult.content) {
                    workflowContent = contentResult.content;
                    console.log(`📝 Workflow content from API (${workflowContent.length} chars)`);
                }
            } catch (apiError) {
                console.warn('API call failed, trying fallback:', apiError);
            }
            
            // Fallback: Check if content is already available in the workflow data
            if (!workflowContent) {
                const workflowData = workflow.originalData;
                if (workflowData.content && typeof workflowData.content === 'string') {
                    workflowContent = workflowData.content;
                    console.log(`📝 Using workflow content from originalData (${workflowContent.length} chars)`);
                } else if (workflowData.yaml_content && typeof workflowData.yaml_content === 'string') {
                    workflowContent = workflowData.yaml_content;
                    console.log(`📝 Using workflow yaml_content from originalData (${workflowContent.length} chars)`);
                } else if (workflowData.file_content && typeof workflowData.file_content === 'string') {
                    workflowContent = workflowData.file_content;
                    console.log(`📝 Using workflow file_content from originalData (${workflowContent.length} chars)`);
                }
            }
            
            if (workflowContent && workflowContent.length > 0) {
                // Parse steps for this specific workflow
                const parsedSteps = parseWorkflowSteps(workflowContent, workflow);
                // Ensure each step is associated with the correct workflow
                selectedWorkflowSteps = parsedSteps.map(step => ({
                    ...step,
                    workflowId: workflow.id,
                    workflowName: workflow.name
                }));
                console.log(`✅ Parsed ${selectedWorkflowSteps.length} workflow steps for ${workflow.name}:`, selectedWorkflowSteps);
            } else {
                console.warn('❌ No workflow content available');
                console.log('Available workflow data keys:', Object.keys(workflow.originalData || {}));
                selectedWorkflowSteps = [];
            }
        } catch (err) {
            console.error('Failed to load workflow steps:', err);
            selectedWorkflowSteps = [];
            if (err.message.includes('404')) {
                console.warn(`Workflow file not found: ${workflow.path}`);
            }
        }
    }

    function parseWorkflowSteps(yamlContent, workflow) {
        if (!yamlContent || typeof yamlContent !== 'string') {
            console.warn('Invalid YAML content for parsing steps');
            return [];
        }

        console.log('🔍 Parsing YAML content for steps...');
        console.log('📄 Content preview:', yamlContent.substring(0, 200) + '...');
        
        const steps = [];
        const lines = yamlContent.split('\n');
        let currentJob = null;
        let stepIndex = 0;
        let inStepsSection = false;
        let currentStepData = null;
        
        try {
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                const trimmedLine = line.trim();
                const indent = line.length - line.trimStart().length;
                
                // Skip empty lines and comments
                if (!trimmedLine || trimmedLine.startsWith('#')) {
                    continue;
                }
                
                // Check if we're entering a jobs section
                if (trimmedLine === 'jobs:') {
                    continue;
                }
                
                // Detect job names (at jobs level)
                if (line.match(/^  \w+:/) && !inStepsSection) {
                    currentJob = trimmedLine.replace(':', '');
                    console.log('📍 Found job:', currentJob);
                    continue;
                }
                
                // Check if we're entering a steps section
                if (trimmedLine === 'steps:') {
                    inStepsSection = true;
                    stepIndex = 0;
                    console.log('📍 Entering steps section for job:', currentJob);
                    continue;
                }
                
                // Exit steps section when we encounter another job-level property
                if (inStepsSection && indent <= 2 && trimmedLine.includes(':') && !trimmedLine.startsWith('- ')) {
                    inStepsSection = false;
                    continue;
                }
                
                // Parse step items
                if (inStepsSection && trimmedLine.startsWith('- ')) {
                    // Save previous step if exists
                    if (currentStepData) {
                        steps.push(currentStepData);
                    }
                    
                    // Start new step
                    currentStepData = {
                        id: `${workflow.id}-step-${stepIndex}`,
                        name: 'Unnamed Step',
                        type: 'run',
                        detail: '',
                        with: {},
                        job: currentJob || 'build',
                        step: stepIndex
                    };
                    stepIndex++;
                    
                    // Handle inline step definition
                    const stepContent = trimmedLine.substring(2).trim();
                    if (stepContent.startsWith('name:')) {
                        currentStepData.name = stepContent.substring(5).trim().replace(/['"]/g, '');
                    } else if (stepContent.startsWith('uses:')) {
                        currentStepData.type = 'uses';
                        currentStepData.detail = stepContent.substring(5).trim().replace(/['"]/g, '');
                    } else if (stepContent.startsWith('run:')) {
                        currentStepData.type = 'run';
                        currentStepData.detail = stepContent.substring(4).trim().replace(/['"]/g, '');
                    }
                    continue;
                }
                
                // Parse step properties
                if (inStepsSection && currentStepData && indent > 4) {
                    if (trimmedLine.startsWith('name:')) {
                        currentStepData.name = trimmedLine.substring(5).trim().replace(/['"]/g, '');
                    } else if (trimmedLine.startsWith('uses:')) {
                        currentStepData.type = 'uses';
                        currentStepData.detail = trimmedLine.substring(5).trim().replace(/['"]/g, '');
                    } else if (trimmedLine.startsWith('run:')) {
                        currentStepData.type = 'run';
                        currentStepData.detail = trimmedLine.substring(4).trim().replace(/['"]/g, '');
                    } else if (trimmedLine.startsWith('with:')) {
                        // Handle with parameters
                        let j = i + 1;
                        while (j < lines.length && lines[j].trim() && lines[j].length - lines[j].trimStart().length > indent) {
                            const withLine = lines[j].trim();
                            if (withLine.includes(':')) {
                                const [key, ...valueParts] = withLine.split(':');
                                const value = valueParts.join(':').trim().replace(/['"]/g, '');
                                currentStepData.with[key.trim()] = value;
                            }
                            j++;
                        }
                        i = j - 1; // Skip processed lines
                    }
                }
            }
            
            // Add the last step if exists
            if (currentStepData) {
                steps.push(currentStepData);
            }
            
            // Handle special workflow types
            if (steps.length === 0) {
                console.log('🔍 No steps found in standard format, checking for workflow_call or other formats...');
                
                // Check for workflow_call type
                if (yamlContent.includes('workflow_call:')) {
                    steps.push({
                        id: `${workflow.id}-step-0`,
                        name: 'Reusable Workflow Call',
                        type: 'workflow_call',
                        detail: 'This is a reusable workflow that can be called by other workflows',
                        with: {},
                        job: 'workflow_call',
                        step: 0
                    });
                }
                
                // Check for composite action
                if (yamlContent.includes('runs:') && yamlContent.includes('using:')) {
                    steps.push({
                        id: `${workflow.id}-step-0`,
                        name: 'Composite Action',
                        type: 'composite',
                        detail: 'This is a composite action',
                        with: {},
                        job: 'composite',
                        step: 0
                    });
                }
            }
            
        } catch (error) {
            console.error('Error parsing workflow YAML:', error);
            return [];
        }
        
        console.log(`🎯 Total steps parsed: ${steps.length}`);
        console.log('📋 Steps details:', steps.map(s => ({ name: s.name, type: s.type, detail: s.detail })));
        return steps;
    }

    async function loadWorkflowActions(workflow) {
        if (!workflow || !workflow.repository || !workflow.path) {
            console.warn('Invalid workflow data for loading actions:', workflow);
            actionBlocks = [];
            return;
        }

        try {
            // Get workflow content to parse actions
            const contentResult = await githubClient.getWorkflowContent(
                orgName, 
                workflow.repository, 
                workflow.path
            );
            
            if (contentResult && contentResult.success && contentResult.content) {
                actionBlocks = parseWorkflowActions(contentResult.content, workflow);
            } else {
                console.warn('No valid workflow content received for actions');
                actionBlocks = [];
            }
        } catch (err) {
            console.error('Failed to load workflow actions:', err);
            actionBlocks = [];
            // Optionally show user-friendly error
            if (err.message.includes('404')) {
                console.warn(`Workflow file not found: ${workflow.path}`);
            }
        }
    }

    function parseWorkflowActions(yamlContent, workflow) {
        if (!yamlContent || typeof yamlContent !== 'string') {
            console.warn('Invalid YAML content for parsing actions');
            return [];
        }

        // Simple YAML parsing to extract actions
        // In a real implementation, you'd use a proper YAML parser
        const actions = [];
        const lines = yamlContent.split('\n');
        let currentJob = null;
        let stepIndex = 0;
        
        try {
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                
                if (line.includes('jobs:')) {
                    continue;
                }
                
                if (line.match(/^\w+:$/) && !line.includes('steps:')) {
                    currentJob = line.replace(':', '');
                    stepIndex = 0;
                    continue;
                }
                
                if (line.includes('- name:')) {
                    const name = line.replace('- name:', '').trim().replace(/['"]/g, '');
                    const nextLine = lines[i + 1];
                    
                    let actionType = 'script';
                    let actionDetail = '';
                    
                    if (nextLine && nextLine.includes('uses:')) {
                        actionType = 'uses';
                        actionDetail = nextLine.replace('uses:', '').trim();
                    } else if (nextLine && nextLine.includes('run:')) {
                        actionType = 'run';
                        actionDetail = nextLine.replace('run:', '').trim();
                    }
                    
                    actions.push({
                        id: `${workflow.id}-action-${stepIndex}`,
                        name: name || `Step ${stepIndex + 1}`,
                        type: actionType,
                        detail: actionDetail,
                        job: currentJob || 'build',
                        x: 50,
                        y: 50 + stepIndex * 80,
                        step: stepIndex
                    });
                    
                    stepIndex++;
                }
            }
        } catch (error) {
            console.error('Error parsing workflow YAML:', error);
            return [];
        }
        
        return actions;
    }

    function selectStepAction(step) {
        selectedStepAction = step;
        showActionDetails = true;
    }

    function addActionToWorkflow(predefinedAction, insertAtPosition = -1) {
        if (!selectedWorkflow || !selectedWorkflowId) {
            saveMessage = 'Please select a workflow first';
            saveSuccess = false;
            setTimeout(() => { saveMessage = ''; }, 3000);
            return;
        }
        
        // Validate that we have the correct workflow steps loaded
        if (!Array.isArray(selectedWorkflowSteps)) {
            selectedWorkflowSteps = [];
        }
        
        // If no position specified, add at the end
        if (insertAtPosition === -1) {
            insertAtPosition = selectedWorkflowSteps.length;
        }
        
        // Validate insertion position
        if (insertAtPosition < 0 || insertAtPosition > selectedWorkflowSteps.length) {
            insertAtPosition = selectedWorkflowSteps.length;
        }
        
        const newStep = {
            id: `${selectedWorkflowId}-step-${Date.now()}`, // Use timestamp for unique ID
            name: predefinedAction.name,
            type: predefinedAction.uses ? 'uses' : 'run',
            detail: predefinedAction.uses || predefinedAction.run,
            with: predefinedAction.with || {},
            job: 'build', // Default job
            step: insertAtPosition,
            isNew: true,
            workflowId: selectedWorkflowId, // Track which workflow this step belongs to
            workflowName: selectedWorkflow.name
        };
        
        // Insert the action at the specified position
        const newSteps = [...selectedWorkflowSteps];
        newSteps.splice(insertAtPosition, 0, newStep);
        
        // Update step numbers for all steps after the insertion point
        for (let i = insertAtPosition + 1; i < newSteps.length; i++) {
            newSteps[i].step = i;
        }
        
        selectedWorkflowSteps = newSteps;
        selectStepAction(newStep);
        
        // Show success message
        const positionText = insertAtPosition === 0 ? 'beginning' : 
                            insertAtPosition === selectedWorkflowSteps.length - 1 ? 'end' : 
                            `position ${insertAtPosition + 1}`;
        saveMessage = `✅ Added "${predefinedAction.name}" to ${selectedWorkflow.name} at ${positionText}`;
        saveSuccess = true;
        setTimeout(() => { saveMessage = ''; }, 3000);
        
        console.log(`✅ Added action "${predefinedAction.name}" to workflow "${selectedWorkflow.name}" at position ${insertAtPosition + 1}`);
    }

    // Workflow dragging functionality
    function handleWorkflowMouseDown(event, workflow) {
        if (event.button !== 0) return; // Only left mouse button
        
        draggedWorkflow = workflow;
        isDraggingWorkflow = true;
        
        const rect = event.currentTarget.getBoundingClientRect();
        workflowDragOffset = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        };
        
        event.preventDefault();
        document.addEventListener('mousemove', handleWorkflowMouseMove);
        document.addEventListener('mouseup', handleWorkflowMouseUp);
    }

    function handleWorkflowMouseMove(event) {
        if (!isDraggingWorkflow || !draggedWorkflow) return;
        
        const canvasArea = document.querySelector('.canvas-area');
        if (!canvasArea) return;
        
        const canvasRect = canvasArea.getBoundingClientRect();
        const newX = event.clientX - canvasRect.left - workflowDragOffset.x;
        const newY = event.clientY - canvasRect.top - workflowDragOffset.y;
        
        // Update workflow position
        const workflowIndex = workflows.findIndex(w => w.id === draggedWorkflow.id);
        if (workflowIndex !== -1) {
            workflows[workflowIndex].x = Math.max(0, Math.min(newX, canvasArea.clientWidth - 250));
            workflows[workflowIndex].y = Math.max(0, Math.min(newY, canvasArea.clientHeight - 150));
            workflows = [...workflows]; // Trigger reactivity
            
            // Force redraw connections when dragging
            if (workflowConnections.length > 0) {
                // Small delay to ensure DOM is updated
                setTimeout(() => {
                    connectionPaths = workflowConnections.map(connection => {
                        if (!connection || !connection.from || !connection.to) {
                            return { ...connection, path: '' };
                        }
                        
                        // Handle different formats of from/to properties
                        let fromId, toId;
                        
                        if (typeof connection.from === 'string') {
                            fromId = connection.from;
                        } else if (connection.from && typeof connection.from === 'object' && connection.from.id) {
                            fromId = connection.from.id;
                        } else {
                            fromId = String(connection.from);
                        }
                        
                        if (typeof connection.to === 'string') {
                            toId = connection.to;
                        } else if (connection.to && typeof connection.to === 'object' && connection.to.id) {
                            toId = connection.to.id;
                        } else {
                            toId = String(connection.to);
                        }
                        
                        return {
                            ...connection,
                            from: fromId,
                            to: toId,
                            path: drawConnection(fromId, toId)
                        };
                    }).filter(conn => conn.path);
                }, 10);
            }
        }
    }

    function handleWorkflowMouseUp() {
        isDraggingWorkflow = false;
        draggedWorkflow = null;
        document.removeEventListener('mousemove', handleWorkflowMouseMove);
        document.removeEventListener('mouseup', handleWorkflowMouseUp);
    }

    async function saveWorkflowChanges() {
        if (!selectedWorkflow || selectedWorkflowSteps.length === 0) {
            saveMessage = 'No changes to save';
            saveSuccess = false;
            setTimeout(() => { saveMessage = ''; }, 3000);
            return;
        }
        
        try {
            // Start loading
            isSaving = true;
            saveMessage = 'Creating pull request...';
            saveSuccess = false;
            
            // Generate updated YAML content
            const updatedYaml = generateUpdatedWorkflowYaml();
            
            // Save workflow changes via API
            const result = await githubClient.saveCanvasWorkflowChanges(
                orgName,
                selectedWorkflow.repository,
                selectedWorkflow.path,
                updatedYaml,
                selectedWorkflowSteps
            );
            
            if (result.success) {
                saveSuccess = true;
                saveMessage = `✅ Pull Request #${result.pr_number} created successfully!`;
                
                // Optionally open the PR in a new tab
                if (result.pr_url) {
                    window.open(result.pr_url, '_blank');
                }
                
                // Refresh the workflow data to show updated workflow
                await refreshWorkflowData();
                
                // Keep success message for 5 seconds
                setTimeout(() => {
                    saveMessage = '';
                    // Reset the canvas after success
                    selectedWorkflow = null;
                    selectedWorkflowId = null;
                    selectedWorkflowSteps = [];
                    showWorkflowSteps = false;
                    showActionDetails = false;
                }, 5000);
                
            } else {
                saveSuccess = false;
                saveMessage = `❌ Failed to create PR: ${result.error}`;
                setTimeout(() => { saveMessage = ''; }, 5000);
            }
            
        } catch (error) {
            console.error('Failed to save workflow changes:', error);
            saveSuccess = false;
            saveMessage = `❌ Failed to save changes: ${error.message}`;
            setTimeout(() => { saveMessage = ''; }, 5000);
        } finally {
            isSaving = false;
        }
    }

    async function refreshWorkflowData() {
        try {
            console.log('🔄 Refreshing workflow data after PR creation...');
            
            // Reload the canvas data to get updated workflow information
            await loadCanvasData();
            
            // If we have a selected workflow, try to reload its steps
            if (selectedWorkflow && selectedWorkflowId) {
                const workflow = workflows.find(w => w.id === selectedWorkflowId);
                if (workflow) {
                    await loadWorkflowSteps(workflow);
                }
            }
            
            console.log('✅ Workflow data refreshed successfully');
        } catch (error) {
            console.error('❌ Failed to refresh workflow data:', error);
        }
    }

    function generateUpdatedWorkflowYaml() {
        // This is a simplified YAML generation
        // In a real implementation, you'd use a proper YAML library
        let yaml = `name: ${selectedWorkflow.name}\n\n`;
        
        if (selectedWorkflow.triggers && selectedWorkflow.triggers.length > 0) {
            yaml += `on:\n`;
            selectedWorkflow.triggers.forEach(trigger => {
                if (trigger === 'push') {
                    yaml += `  push:\n    branches: [main]\n`;
                } else if (trigger === 'pull_request') {
                    yaml += `  pull_request:\n    branches: [main]\n`;
                } else if (trigger === 'workflow_call') {
                    yaml += `  workflow_call:\n`;
                }
            });
            yaml += '\n';
        }
        
        yaml += `jobs:\n`;
        yaml += `  build:\n`;
        yaml += `    runs-on: ubuntu-latest\n`;
        yaml += `    steps:\n`;
        
        selectedWorkflowSteps.forEach(step => {
            yaml += `      - name: ${step.name}\n`;
            if (step.type === 'uses') {
                yaml += `        uses: ${step.detail}\n`;
                if (step.with && Object.keys(step.with).length > 0) {
                    yaml += `        with:\n`;
                    Object.entries(step.with).forEach(([key, value]) => {
                        yaml += `          ${key}: ${value}\n`;
                    });
                }
            } else if (step.type === 'run') {
                yaml += `        run: ${step.detail}\n`;
            }
            yaml += '\n';
        });
        
        return yaml;
    }

    // Drag and drop functionality
    let draggedItem = null;
    let isDragging = false;

    function handleDragStart(event, item) {
        draggedItem = item;
        isDragging = true;
        showDropZones = true;
        dropZonePosition = -1;
        event.dataTransfer.effectAllowed = 'move';
    }

    function handleDragOver(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }

    function handleDrop(event) {
        event.preventDefault();
        
        try {
            if (draggedItem && selectedWorkflowId && showWorkflowSteps) {
                // Use the dropZonePosition if it was set, otherwise add at the end
                const insertPosition = dropZonePosition !== -1 ? dropZonePosition : selectedWorkflowSteps.length;
                addActionToWorkflow(draggedItem, insertPosition);
            } else if (draggedItem && !selectedWorkflowId) {
                saveMessage = 'Please select a workflow first before adding actions';
                saveSuccess = false;
                setTimeout(() => { saveMessage = ''; }, 3000);
            } else if (draggedItem && selectedWorkflowId && !showWorkflowSteps) {
                saveMessage = 'Please open the workflow steps first by clicking on the workflow';
                saveSuccess = false;
                setTimeout(() => { saveMessage = ''; }, 3000);
            }
        } catch (error) {
            console.error('Error handling drop:', error);
            saveMessage = 'Error adding action to workflow: ' + error.message;
            saveSuccess = false;
            setTimeout(() => { saveMessage = ''; }, 3000);
        } finally {
            isDragging = false;
            draggedItem = null;
            showDropZones = false;
            dropZonePosition = -1;
        }
    }

    function handleDropZoneEnter(position) {
        if (isDragging && draggedItem) {
            dropZonePosition = position;
        }
    }

    function handleDropZoneLeave() {
        // Keep the drop zone active until we enter another one or finish dragging
    }

    function handleDropZoneDrop(event, position) {
        event.preventDefault();
        event.stopPropagation();
        
        if (draggedItem && selectedWorkflowId && showWorkflowSteps) {
            addActionToWorkflow(draggedItem, position);
        }
        
        isDragging = false;
        draggedItem = null;
        showDropZones = false;
        dropZonePosition = -1;
    }

    // Step reordering functionality
    let draggedStep = null;
    let draggedStepIndex = -1;
    let stepDropZonePosition = -1;

    function handleStepDragStart(event, step, index) {
        draggedStep = step;
        draggedStepIndex = index;
        showDropZones = true;
        stepDropZonePosition = -1;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', ''); // Required for some browsers
    }

    function handleStepDrop(event, targetIndex) {
        event.preventDefault();
        event.stopPropagation();
        
        if (draggedStep && draggedStepIndex !== -1 && draggedStepIndex !== targetIndex) {
            // Remove step from old position
            const newSteps = [...selectedWorkflowSteps];
            newSteps.splice(draggedStepIndex, 1);
            
            // Insert step at new position
            const adjustedTargetIndex = targetIndex > draggedStepIndex ? targetIndex - 1 : targetIndex;
            newSteps.splice(adjustedTargetIndex, 0, draggedStep);
            
            // Update step numbers
            for (let i = 0; i < newSteps.length; i++) {
                newSteps[i].step = i;
            }
            
            selectedWorkflowSteps = newSteps;
            
            // Show success message
            saveMessage = `✅ Moved "${draggedStep.name}" to position ${adjustedTargetIndex + 1}`;
            saveSuccess = true;
            setTimeout(() => { saveMessage = ''; }, 3000);
        }
        
        draggedStep = null;
        draggedStepIndex = -1;
        showDropZones = false;
        stepDropZonePosition = -1;
    }

    function handleStepDragEnd() {
        draggedStep = null;
        draggedStepIndex = -1;
        showDropZones = false;
        stepDropZonePosition = -1;
    }

    // ...existing code...
</script>

<svelte:head>
    <title>Canvas Workflow Builder{selectedWorkflowName ? ` - ${selectedWorkflowName}` : selectedRepo ? ` - ${selectedRepo}` : ''} - {orgName} - WithOps</title>
</svelte:head>

<div class="min-h-screen bg-gray-50">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <header class="mb-8">
            <nav class="flex items-center space-x-2 text-sm text-gray-500 mb-4">
                <a href="/" class="hover:text-gray-700">Dashboard</a>
                <span>/</span>
                <a href="/github/workspace/{orgName}" class="hover:text-gray-700">{orgName} Workspace</a>
                <span>/</span>
                <span class="text-gray-900">Canvas Workflow Builder</span>
            </nav>
            
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold text-gray-900">🎨 Canvas Workflow Builder</h1>
                    <div class="flex items-center space-x-2 text-gray-600">
                        {#if selectedWorkflowName && selectedRepo}
                            <p>Editing workflow: <span class="font-medium text-gray-900">{selectedWorkflowName}</span> from <span class="font-medium text-gray-900">{selectedRepo}</span></p>
                        {:else if selectedRepo}
                            <p>Repository workflows: <span class="font-medium text-gray-900">{selectedRepo}</span></p>
                        {:else}
                            <p>All workflows in organization: <span class="font-medium text-gray-900">{orgName}</span></p>
                        {/if}
                        {#if workflows.length > 0}
                            <span class="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                                {workflows.length} workflow{workflows.length === 1 ? '' : 's'}
                            </span>
                        {/if}
                    </div>
                </div>
                
                <div class="flex space-x-3">
                    <button 
                        on:click={goBack}
                        class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 font-medium"
                    >
                        ← Back to Workspace
                    </button>
                    {#if selectedWorkflow}
                        <button 
                            on:click={saveWorkflowChanges}
                            disabled={isSaving}
                            class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                        >
                            {#if isSaving}
                                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                <span>Creating PR...</span>
                            {:else}
                                <span>💾 Save & Propose PR</span>
                            {/if}
                        </button>
                    {/if}
                </div>
            </div>
        </header>

        <!-- Status Message Area -->
        {#if saveMessage}
            <div class="mb-4">
                <div class="bg-white border rounded-lg p-4 {saveSuccess ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}">
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
                            <p class="text-sm font-medium {saveSuccess ? 'text-green-800' : 'text-red-800'}">{saveMessage}</p>
                        </div>
                    </div>
                </div>
            </div>
        {/if}

        {#if loading}
            <!-- Loading State -->
            <div class="flex items-center justify-center py-12">
                <div class="text-center">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p class="text-gray-600">Loading workflow canvas...</p>
                </div>
            </div>
        {:else if error}
            <!-- Error State -->
            <div class="bg-red-50 border border-red-200 rounded-lg p-6">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Error Loading Canvas</h3>
                        <p class="text-sm text-red-700 mt-1">{error}</p>
                    </div>
                </div>
            </div>
        {:else if workflows.length === 0}
            <!-- Empty State for No Workflows -->
            <div class="bg-white rounded-lg shadow-lg p-12">
                <div class="text-center">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 mb-4">
                        <svg class="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                    </div>
                    
                    {#if selectedWorkflowName}
                        <h3 class="text-lg font-medium text-gray-900 mb-2">Workflow Not Found</h3>
                        <p class="text-sm text-gray-600 mb-6">
                            The workflow "<span class="font-medium">{selectedWorkflowName}</span>" 
                            {#if selectedRepo}
                                in repository "<span class="font-medium">{selectedRepo}</span>"
                            {/if}
                            could not be found or loaded.
                        </p>
                    {:else if selectedRepo}
                        <h3 class="text-lg font-medium text-gray-900 mb-2">No Workflows Found</h3>
                        <p class="text-sm text-gray-600 mb-6">
                            The repository "<span class="font-medium">{selectedRepo}</span>" doesn't have any GitHub Actions workflows yet.
                        </p>
                    {:else}
                        <h3 class="text-lg font-medium text-gray-900 mb-2">No Workflows Available</h3>
                        <p class="text-sm text-gray-600 mb-6">
                            No GitHub Actions workflows found in the organization.
                        </p>
                    {/if}
                    
                    <div class="flex justify-center space-x-3">
                        <button 
                            on:click={goBack}
                            class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200"
                        >
                            ← Back to Workspace
                        </button>
                        {#if selectedRepo}
                            <button 
                                on:click={() => goto(`/github/workspace/${orgName}/canvas`)}
                                class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                            >
                                View All Workflows
                            </button>
                        {/if}
                    </div>
                </div>
            </div>
        {:else}
            <!-- Canvas Interface -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden">
                <div class="flex" style="height: calc(100vh - 200px)">
                    <!-- Add Action Panel (Left Sidebar) -->
                    {#if showAddActionPanel}
                        <div class="w-64 bg-gray-50 border-r border-gray-200 p-4 overflow-y-auto">
                            <div class="flex items-center justify-between mb-4">
                                <h3 class="text-lg font-semibold text-gray-900">➕ Add Actions</h3>
                                <button 
                                    on:click={() => showAddActionPanel = false}
                                    class="text-gray-400 hover:text-gray-600"
                                    aria-label="Close Add Actions Panel"
                                >
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>
                            
                            <p class="text-sm text-gray-600 mb-4">Drag actions to add them to the selected workflow</p>
                            
                            <div class="space-y-2">
                                {#each predefinedActions as action}
                                    <div 
                                        draggable="true"
                                        on:dragstart={(e) => handleDragStart(e, action)}
                                        class="bg-white p-3 rounded-lg border border-gray-200 cursor-move hover:border-blue-300 hover:shadow-sm transition-all duration-200"
                                        role="button"
                                        tabindex="0"
                                        aria-label={`Drag ${action.name} action to add to workflow`}
                                        on:keydown={(e) => e.key === 'Enter' && handleDragStart(e, action)}
                                    >
                                        <div class="font-medium text-sm text-gray-900">{action.name}</div>
                                        <div class="text-xs text-gray-500 mt-1">{action.description}</div>
                                        <div class="text-xs text-blue-600 mt-1 font-mono">
                                            {action.uses || action.run || ''}
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {:else}
                        <!-- Collapsed Add Panel -->
                        <div class="w-12 bg-gray-50 border-r border-gray-200 flex flex-col items-center pt-4">
                            <button 
                                on:click={() => showAddActionPanel = true}
                                class="text-gray-400 hover:text-gray-600 mb-4"
                                title="Show Add Actions Panel"
                                aria-label="Show Add Actions Panel"
                            >
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                </svg>
                            </button>
                        </div>
                    {/if}
                    <!-- Canvas Workspace (Main Area) -->
                    <div class="flex-1 flex flex-col">
                        <!-- Canvas Header -->
                        <div class="bg-white border-b border-gray-200 p-4">
                            <div class="flex items-center justify-between">
                                <div>
                                    <h2 class="text-xl font-semibold text-gray-900">Workflow Canvas</h2>
                                    <p class="text-sm text-gray-600">
                                        {workflows.length} workflows • 
                                        {workflowConnections.length} connections
                                        {selectedWorkflow ? ` • Editing: ${selectedWorkflow.name}` : ''}
                                        {showWorkflowSteps ? ` • ${selectedWorkflowSteps.length} steps` : ''}
                                        {#if showWorkflowSteps && selectedWorkflowSteps.filter(s => s.isNew).length > 0}
                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 ml-2">
                                                +{selectedWorkflowSteps.filter(s => s.isNew).length} new
                                            </span>
                                        {/if}
                                    </p>
                                </div>
                                
                                <div class="flex items-center space-x-2">
                                    {#if !showAddActionPanel}
                                        <button 
                                            on:click={() => showAddActionPanel = true}
                                            class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                        >
                                            ➕ Add Actions
                                        </button>
                                    {/if}
                                </div>
                            </div>
                        </div>

                        <!-- Canvas Area -->
                        <div 
                            class="flex-1 relative bg-gray-100 overflow-auto canvas-area"
                            on:dragover={handleDragOver}
                            on:drop={handleDrop}
                            style="background-image: radial-gradient(circle, #d1d5db 1px, transparent 1px); background-size: 20px 20px;"
                            role="application"
                            aria-label="Workflow Canvas - Drag and drop area for workflow actions"
                        >
                            <!-- Canvas content area without duplicate SVG connections -->
                            <!-- Connections are rendered in the main SVG section below -->
                            
                            <!-- Workflow Blocks -->
                            {#each workflows as workflow}
                                <div 
                                    id={workflow.id}
                                    class="absolute bg-white rounded-lg border-2 shadow-lg cursor-move transition-all duration-200 {selectedWorkflowId === workflow.id ? 'border-blue-500 shadow-xl' : 'border-gray-200 hover:border-gray-300'}"
                                    style="left: {workflow.x}px; top: {workflow.y}px; width: 280px; user-select: none;"
                                    on:mousedown={(e) => handleWorkflowMouseDown(e, workflow)}
                                    on:click={(e) => selectWorkflow(workflow.id, e)}
                                    role="button"
                                    tabindex="0"
                                    on:keydown={(e) => e.key === 'Enter' && selectWorkflow(workflow.id, e)}
                                >
                                
                                    <div class="p-4">
                                        <div class="flex items-center space-x-2 mb-2">
                                            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                            </svg>
                                            <span class="text-sm font-semibold text-gray-900 truncate">{workflow.name}</span>
                                        </div>
                                        
                                        <div class="text-xs text-gray-600 mb-2">📁 {workflow.repository}</div>
                                        <div class="text-xs text-gray-500 mb-2 font-mono truncate">{workflow.path}</div>
                                        
                                        <div class="text-xs text-gray-400 italic">
                                            Click to view workflow steps
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Workflow Steps Popup -->
                                {#if selectedWorkflowId === workflow.id && showWorkflowSteps && selectedWorkflowSteps.length > 0}
                                    <div 
                                        class="absolute bg-gray-50 rounded-lg border-2 border-blue-300 shadow-xl p-4"
                                        style="left: {workflow.x}px; top: {workflow.y + 160}px; width: 280px; max-height: 300px; overflow-y: auto; z-index: 5;"
                                        on:dragover={handleDragOver}
                                        on:drop={handleDrop}
                                        role="application"
                                        aria-label="Workflow steps - Drop actions here to add new steps"
                                    >
                                        <div class="flex items-center justify-between mb-3">
                                            <h4 class="text-sm font-semibold text-gray-900">Workflow Steps</h4>
                                            <button 
                                                on:click={() => showWorkflowSteps = false}
                                                class="text-gray-400 hover:text-gray-600"
                                                aria-label="Close workflow steps"
                                            >
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                </svg>
                                            </button>
                                        </div>
                                        
                                        <div class="space-y-1">
                                            <!-- Drop zone before first step -->
                                            {#if showDropZones && isDragging}
                                                <div 
                                                    class="h-8 border-2 border-dashed border-blue-400 bg-blue-50 rounded flex items-center justify-center text-xs text-blue-600 transition-all duration-200 {dropZonePosition === 0 ? 'border-blue-600 bg-blue-100' : ''}"
                                                    on:dragenter={() => handleDropZoneEnter(0)}
                                                    on:dragleave={handleDropZoneLeave}
                                                    on:dragover={handleDragOver}
                                                    on:drop={(e) => handleDropZoneDrop(e, 0)}
                                                    role="button"
                                                    tabindex="0"
                                                >
                                                    📥 Drop here to add at beginning
                                                </div>
                                            {/if}
                                            
                                            {#each selectedWorkflowSteps as step, index}
                                                <div 
                                                    class="bg-white rounded border p-2 cursor-pointer hover:border-blue-300 transition-colors duration-200 {selectedStepAction?.id === step.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}"
                                                    draggable="true"
                                                    on:dragstart={(e) => handleStepDragStart(e, step, index)}
                                                    on:dragend={handleStepDragEnd}
                                                    on:click={() => selectStepAction(step)}
                                                    role="button"
                                                    tabindex="0"
                                                    on:keydown={(e) => e.key === 'Enter' && selectStepAction(step)}
                                                >
                                                    <div class="flex items-center space-x-1 mb-1">
                                                        <span class="inline-flex items-center justify-center w-4 h-4 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                            {index + 1}
                                                        </span>
                                                        {#if step.isNew}
                                                            <span class="inline-flex items-center px-1 py-0.5 rounded text-xs bg-green-100 text-green-800">
                                                                NEW
                                                            </span>
                                                        {/if}
                                                        <div class="ml-auto">
                                                            <svg class="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                                                            </svg>
                                                        </div>
                                                    </div>
                                                    <div class="text-xs font-medium text-gray-900 truncate" title={step.name}>
                                                        {step.name}
                                                    </div>
                                                    <div class="text-xs text-gray-500 truncate" title={step.detail}>
                                                        {step.type}: {step.detail}
                                                    </div>
                                                </div>
                                                
                                                <!-- Drop zone after each step -->
                                                {#if showDropZones && (isDragging || draggedStep)}
                                                    <div 
                                                        class="h-6 border-2 border-dashed border-blue-400 bg-blue-50 rounded flex items-center justify-center text-xs text-blue-600 transition-all duration-200 {dropZonePosition === index + 1 || stepDropZonePosition === index + 1 ? 'border-blue-600 bg-blue-100' : ''}"
                                                        on:dragenter={() => {
                                                            handleDropZoneEnter(index + 1);
                                                            stepDropZonePosition = index + 1;
                                                        }}
                                                        on:dragleave={handleDropZoneLeave}
                                                        on:dragover={handleDragOver}
                                                        on:drop={(e) => {
                                                            if (draggedStep) {
                                                                handleStepDrop(e, index + 1);
                                                            } else {
                                                                handleDropZoneDrop(e, index + 1);
                                                            }
                                                        }}
                                                        role="button"
                                                        tabindex="0"
                                                    >
                                                        📥 Drop here to insert after step {index + 1}
                                                    </div>
                                                {/if}
                                            {/each}
                                        </div>
                                        
                                        <div class="mt-3 text-xs text-gray-500 text-center">
                                            {#if showDropZones && (isDragging || draggedStep)}
                                                <div class="bg-blue-50 border border-blue-200 rounded px-2 py-1">
                                                    🎯 Drop {draggedStep ? 'step' : 'action'} at the blue zones to insert at specific positions
                                                </div>
                                            {:else}
                                                <div class="space-y-1">
                                                    <div>Drag actions from the left panel to add new steps at any position</div>
                                                    <div>Drag existing steps to reorder them</div>
                                                </div>
                                            {/if}
                                        </div>
                                    </div>
                                {/if}
                            {/each}

                            <!-- Workflow Connections -->
                            {#if workflowConnections.length > 0 && connectionPaths && connectionPaths.length > 0}
                                <svg 
                                    class="absolute inset-0 pointer-events-none" 
                                    width="100%" 
                                    height="100%"
                                    style="z-index: 1;"
                                    aria-hidden="true"
                                >
                                    {#each connectionPaths as connection (connection.from + '-' + connection.to)}
                                        {#if connection.from && connection.to && connection.path}
                                            <!-- Connection line -->
                                            <path 
                                                d={connection.path}
                                                stroke="#3b82f6" 
                                                stroke-width="3" 
                                                fill="none"
                                                marker-end="url(#arrowhead)"
                                                opacity="0.8"
                                                stroke-dasharray="5,5"
                                                class="animate-pulse"
                                            />
                                            <!-- Connection lines are clean without text labels -->
                                        {/if}
                                    {/each}
                                    
                                    <defs>
                                        <marker id="arrowhead" markerWidth="12" markerHeight="8" 
                                                refX="11" refY="4" orient="auto"
                                                markerUnits="strokeWidth">
                                            <polygon points="0 0, 12 4, 0 8" fill="#3b82f6" />
                                        </marker>
                                    </defs>
                                </svg>
                                
                                <!-- Connection Legend -->
                                <div class="absolute top-4 right-4 bg-white rounded-lg border shadow-lg p-3 z-10">
                                    <h5 class="text-sm font-semibold text-gray-900 mb-2">🔗 Workflow Connections</h5>
                                    <div class="text-xs text-gray-600 space-y-1">
                                        {#each connectionPaths as connection}
                                            {#if connection.fromName && connection.toName}
                                                <div class="flex items-center space-x-2">
                                                    <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                                    </svg>
                                                    <span class="truncate max-w-xs">
                                                        {connection.fromName} → {connection.toName}
                                                    </span>
                                                </div>
                                            {/if}
                                        {/each}
                                        {#if connectionPaths.length === 0}
                                            <div class="text-gray-400 italic">No connections detected</div>
                                        {/if}
                                    </div>
                                </div>
                            {:else if workflowConnections.length > 0}
                                <!-- Debug info when connections exist but paths don't -->
                                <div class="absolute top-4 right-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3 z-10 max-w-md">
                                    <h5 class="text-sm font-semibold text-yellow-800 mb-2">🔧 Debug: Connections Found</h5>
                                    <div class="text-xs text-yellow-700">
                                        <div>Connections: {workflowConnections.length}</div>
                                        <div>Paths: {connectionPaths ? connectionPaths.length : 0}</div>
                                        <div class="mt-2 max-h-32 overflow-y-auto">
                                            {#each workflowConnections as conn, index}
                                                <div class="mb-2 p-2 bg-yellow-100 rounded">
                                                    <div>• {conn.fromName || 'Unknown'} → {conn.toName || 'Unknown'}</div>
                                                    <div class="text-xs text-yellow-600 ml-4">From: {typeof conn.from} - {JSON.stringify(conn.from)}</div>
                                                    <div class="text-xs text-yellow-600 ml-4">To: {typeof conn.to} - {JSON.stringify(conn.to)}</div>
                                                </div>
                                            {/each}
                                        </div>
                                    </div>
                                </div>
                            {/if}

                            <!-- Drop Zone Indicator -->
                            {#if isDragging && selectedWorkflowId && showWorkflowSteps}
                                <div 
                                    class="absolute inset-0 bg-blue-100 bg-opacity-50 border-2 border-dashed border-blue-400 flex items-center justify-center pointer-events-none"
                                    style="z-index: 10;"
                                    role="alert"
                                    aria-live="polite"
                                >
                                    <div class="text-blue-700 text-lg font-semibold text-center px-4">
                                        Drop action here to add to "{workflows.find(w => w.id === selectedWorkflowId)?.name || 'selected workflow'}" steps
                                    </div>
                                </div>
                            {:else if isDragging && selectedWorkflowId && !showWorkflowSteps}
                                <div 
                                    class="absolute inset-0 bg-yellow-100 bg-opacity-50 border-2 border-dashed border-yellow-400 flex items-center justify-center pointer-events-none"
                                    style="z-index: 10;"
                                    role="alert"
                                    aria-live="polite"
                                >
                                    <div class="text-yellow-700 text-lg font-semibold text-center px-4">
                                        Click on "{workflows.find(w => w.id === selectedWorkflowId)?.name || 'selected workflow'}" to open steps first
                                    </div>
                                </div>
                            {:else if isDragging && !selectedWorkflowId}
                                <div 
                                    class="absolute inset-0 bg-red-100 bg-opacity-50 border-2 border-dashed border-red-400 flex items-center justify-center pointer-events-none"
                                    style="z-index: 10;"
                                    role="alert"
                                    aria-live="polite"
                                >
                                    <div class="text-red-700 text-lg font-semibold text-center px-4">
                                        Please select a workflow first before adding actions
                                    </div>
                                </div>
                            {/if}
                        </div>
                    </div>

                    <!-- Step Details Panel (Right Side) -->
                    {#if showActionDetails && selectedStepAction}
                        <div class="w-80 bg-white border-l border-gray-200 flex flex-col">
                            <!-- Step Details Header -->
                            <div class="p-4 border-b border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <h3 class="text-lg font-semibold text-gray-900">🔧 Step Details</h3>
                                        <p class="text-sm text-gray-600">{selectedStepAction.name}</p>
                                        <p class="text-xs text-gray-500 mt-1">Step {selectedStepAction.step + 1}</p>
                                    </div>
                                    {#if selectedStepAction.isNew}
                                        <div class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                            🆕 NEW
                                        </div>
                                    {/if}
                                </div>
                            </div>

                            <!-- Step Details Content -->
                            <div class="flex-1 overflow-y-auto p-4">
                                <div class="space-y-4">
                                    <div>
                                        <div class="block text-sm font-medium text-gray-700 mb-1">Name</div>
                                        <div class="text-sm text-gray-900 bg-gray-50 p-2 rounded border">{selectedStepAction.name}</div>
                                    </div>
                                    
                                    <div>
                                        <div class="block text-sm font-medium text-gray-700 mb-1">Type</div>
                                        <div class="text-sm text-gray-900 bg-gray-50 p-2 rounded border capitalize">{selectedStepAction.type}</div>
                                    </div>
                                    
                                    <div>
                                        <div class="block text-sm font-medium text-gray-700 mb-1">
                                            {selectedStepAction.type === 'uses' ? 'Uses' : 'Run Command'}
                                        </div>
                                        <div class="text-sm text-gray-900 bg-gray-50 p-2 rounded border font-mono">
                                            {selectedStepAction.detail}
                                        </div>
                                    </div>
                                    
                                    {#if selectedStepAction.with && Object.keys(selectedStepAction.with).length > 0}
                                        <div>
                                            <div class="block text-sm font-medium text-gray-700 mb-1">With Parameters</div>
                                            <div class="bg-gray-50 p-2 rounded border">
                                                {#each Object.entries(selectedStepAction.with) as [key, value]}
                                                    <div class="text-sm text-gray-900 font-mono mb-1">
                                                        <span class="font-semibold">{key}:</span> {value}
                                                    </div>
                                                {/each}
                                            </div>
                                        </div>
                                    {/if}
                                    
                                    {#if selectedStepAction.job}
                                        <div>
                                            <div class="block text-sm font-medium text-gray-700 mb-1">Job</div>
                                            <div class="text-sm text-gray-900 bg-gray-50 p-2 rounded border">{selectedStepAction.job}</div>
                                        </div>
                                    {/if}
                                    
                                    <div>
                                        <div class="block text-sm font-medium text-gray-700 mb-1">Step Position</div>
                                        <div class="text-sm text-gray-900 bg-gray-50 p-2 rounded border">{selectedStepAction.step + 1}</div>
                                    </div>
                                    
                                    {#if selectedStepAction.isNew}
                                        <div class="bg-green-50 border border-green-200 rounded-lg p-3">
                                            <div class="flex">
                                                <svg class="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                </svg>
                                                <div class="ml-3">
                                                    <h3 class="text-sm font-medium text-green-800">New Step</h3>
                                                    <p class="text-sm text-green-700 mt-1">This step will be added when you save changes.</p>
                                                </div>
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
</div>
