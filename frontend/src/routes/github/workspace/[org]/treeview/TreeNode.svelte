<script>
    import { createEventDispatcher } from 'svelte';
    
    export let node;
    export let level = 0;
    export let expandedNodes = new Set();
    export let selectedNode = null;
    export let editingNode = null;
    export let editingValue = '';
    export let dragOverNode = null;
    
    // Security scanning props
    export let scanningWorkflows = new Set();
    export let workflowSecurityResults = {};
    export let scanningRepository = null;
    
    const dispatch = createEventDispatcher();
    
    $: isExpanded = expandedNodes.has(node.id);
    $: isSelected = selectedNode && selectedNode.id === node.id;
    $: isEditing = editingNode && editingNode.id === node.id;
    $: isDragOver = dragOverNode && dragOverNode.id === node.id;
    $: hasChildren = node.children && node.children.length > 0;
    
    // Security scanning computed properties
    $: isScanning = scanningWorkflows.has(node.id);
    $: securityResult = workflowSecurityResults[node.id];
    $: isRepositoryScanning = scanningRepository === (node.repository || node.metadata?.repository);
    $: hasSecurityResult = !!securityResult;
    $: securityRiskLevel = securityResult?.risk_level || 'unknown';
    $: securityRiskScore = securityResult?.risk_score || 0;
    
    function handleToggle() {
        if (hasChildren) {
            dispatch('toggle', node.id);
        }
    }
    
    function handleSelect() {
        if (!isEditing) {
            dispatch('select', node);
        }
    }
    
    function handleEdit() {
        dispatch('edit', node);
    }
    
    function handleKeyPress(event) {
        dispatch('keypress', event);
    }
    
    function handleSave() {
        dispatch('save');
    }
    
    function handleCancel() {
        dispatch('cancel');
    }
    
    function handleContextMenu(event) {
        dispatch('contextmenu', { event, node });
    }
    
    function handleScanWorkflow(event) {
        event.stopPropagation();
        dispatch('scan-workflow', node);
    }
    
    function handleScanRepository(event) {
        event.stopPropagation();
        const repoName = node.repository || node.metadata?.repository;
        if (repoName) {
            dispatch('scan-repository', repoName);
        }
    }
    
    function getSecurityRiskColor(riskLevel) {
        switch (riskLevel) {
            case 'high': return 'text-red-600 bg-red-100';
            case 'medium': return 'text-orange-600 bg-orange-100';
            case 'low': return 'text-yellow-600 bg-yellow-100';
            case 'minimal': return 'text-green-600 bg-green-100';
            default: return 'text-gray-600 bg-gray-100';
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
    
    function handleDragStart(event) {
        dispatch('dragstart', { event, node });
    }
    
    function handleDragOver(event) {
        event.preventDefault();
        dispatch('dragover', { event, node });
    }
    
    function handleDragLeave(event) {
        dispatch('dragleave', { event, node });
    }
    
    function handleDrop(event) {
        event.preventDefault();
        dispatch('drop', { event, node });
    }
    
    function getIcon(nodeType) {
        switch (nodeType) {
            case 'folder':
                return '📁';
            case 'workflow':
                return '⚙️';
            default:
                return '📄';
        }
    }
    
    function getNodeColor(nodeType) {
        switch (nodeType) {
            case 'folder':
                return 'text-blue-600';
            case 'workflow':
                return 'text-green-600';
            default:
                return 'text-gray-600';
        }
    }
</script>

<div class="select-none">
    <!-- Current Node -->
    <div 
        class="flex items-center space-x-1 py-1 px-2 rounded-md cursor-pointer group relative {
            isSelected ? 'bg-blue-100 text-blue-900' : 'hover:bg-gray-100'
        } {isDragOver ? 'bg-yellow-100 border-2 border-dashed border-yellow-400' : ''}"
        style="margin-left: {level * 16}px;"
        on:click={handleSelect}
        on:contextmenu={handleContextMenu}
        draggable="true"
        on:dragstart={handleDragStart}
        on:dragover={handleDragOver}
        on:dragleave={handleDragLeave}
        on:drop={handleDrop}
        role="button"
        tabindex="0"
        on:keydown={(e) => e.key === 'Enter' && handleSelect()}
    >
        <!-- Expand/Collapse Button -->
        <button 
            class="w-4 h-4 flex items-center justify-center rounded hover:bg-gray-200 {
                hasChildren ? 'text-gray-600' : 'text-transparent'
            }"
            on:click|stopPropagation={handleToggle}
        >
            {#if hasChildren}
                {#if isExpanded}
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                {:else}
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                {/if}
            {/if}
        </button>
        
        <!-- Icon -->
        <span class="text-sm">{getIcon(node.type)}</span>
        
        <!-- Name -->
        <div class="flex-1 min-w-0">
            {#if isEditing}
                <input
                    bind:value={editingValue}
                    class="w-full px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    on:keypress={handleKeyPress}
                    on:blur={handleCancel}
                    on:click|stopPropagation
                    use:focus
                />
            {:else}
                <span class="text-sm font-medium {getNodeColor(node.type)} truncate block">
                    {node.name}
                </span>
            {/if}
        </div>
        
        <!-- Actions -->
        <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {#if !isEditing}
                <!-- Security scan button for workflows -->
                {#if node.type === 'workflow'}
                    <button 
                        class="w-5 h-5 flex items-center justify-center rounded hover:bg-red-100 text-red-500 hover:text-red-700"
                        on:click={handleScanWorkflow}
                        disabled={isScanning}
                        title="Scan workflow for security vulnerabilities"
                        aria-label="Scan {node.name} for security"
                    >
                        {#if isScanning}
                            <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-red-500"></div>
                        {:else}
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        {/if}
                    </button>
                {/if}
                
                <!-- Repository scan button for folders -->
                {#if node.type === 'folder' && (node.repository || node.metadata?.repository)}
                    <button 
                        class="w-5 h-5 flex items-center justify-center rounded hover:bg-orange-100 text-orange-500 hover:text-orange-700"
                        on:click={handleScanRepository}
                        disabled={isRepositoryScanning}
                        title="Scan all workflows in repository"
                        aria-label="Scan repository {node.repository || node.metadata?.repository}"
                    >
                        {#if isRepositoryScanning}
                            <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-orange-500"></div>
                        {:else}
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                            </svg>
                        {/if}
                    </button>
                {/if}
                
                <button 
                    class="w-5 h-5 flex items-center justify-center rounded hover:bg-gray-200 text-gray-500 hover:text-gray-700"
                    on:click|stopPropagation={handleEdit}
                    title="Rename"
                    aria-label="Rename {node.name}"
                >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                </button>
            {/if}
        </div>
        
        <!-- Security Status Indicator -->
        {#if node.type === 'workflow' && hasSecurityResult}
            <div class="flex items-center space-x-1 ml-2">
                <span 
                    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {getSecurityRiskColor(securityRiskLevel)}"
                    title="Security Risk: {securityRiskLevel} ({securityRiskScore}%)"
                >
                    <span class="mr-1">{getSecurityRiskIcon(securityRiskLevel)}</span>
                    <span>{securityRiskScore}%</span>
                </span>
                {#if securityResult.vulnerability_count > 0}
                    <span class="text-xs text-red-600" title="{securityResult.vulnerability_count} vulnerabilities found">
                        🚨{securityResult.vulnerability_count}
                    </span>
                {/if}
            </div>
        {/if}
        
        <!-- Metadata indicators -->
        {#if node.metadata && node.metadata.triggers}
            <div class="flex items-center space-x-1">
                {#each node.metadata.triggers.slice(0, 2) as trigger}
                    <span class="inline-flex items-center px-1 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                        {trigger}
                    </span>
                {/each}
                {#if node.metadata.triggers.length > 2}
                    <span class="text-xs text-gray-400">+{node.metadata.triggers.length - 2}</span>
                {/if}
            </div>
        {/if}
    </div>
    
    <!-- Children -->
    {#if hasChildren && isExpanded}
        <div class="ml-2">
            {#each node.children as child}
                <svelte:self 
                    node={child} 
                    level={level + 1} 
                    {expandedNodes} 
                    {selectedNode} 
                    {editingNode} 
                    {editingValue}
                    {dragOverNode}
                    {scanningWorkflows}
                    {workflowSecurityResults}
                    {scanningRepository}
                    on:toggle
                    on:select
                    on:edit
                    on:save
                    on:cancel
                    on:keypress
                    on:contextmenu
                    on:dragstart
                    on:dragover
                    on:dragleave
                    on:drop
                    on:scan-workflow
                    on:scan-repository
                />
            {/each}
        </div>
    {/if}
</div>

<style>
    .select-none {
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
    }
</style>
