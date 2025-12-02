<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    
    let loading = true;
    let error = null;
    let orgName = '';
    let organizationId = null; // Store org ID
    let threatModels = [];
    let dashboardData = null;
    let showCreateModal = false;
    let showDeleteModal = false;
    let selectedModel = null;
    let modelToDelete = null;
    
    // Create new threat model form
    let newModelName = '';
    let newModelDescription = '';
    let newModelMethodology = 'STRIDE';
    let newModelRepository = null;
    let repositories = [];
    let creating = false;
    
    // Import functionality
    let importing = false;
    let importFileInput;
    
    onMount(async () => {
        orgName = $page.params.org;
        console.log(`🛡️ Loading threat modeling for organization: ${orgName}`);
        
        await fetchOrganizationId();
        await loadThreatModels();
        await loadDashboard();
    });
    
    async function fetchOrganizationId() {
        try {
            const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
            if (!authToken) return;
            
            // Fetch organization data to get ID
            const response = await fetch(`http://localhost:8000/api/github/workspace/${orgName}`, {
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                organizationId = data.organization?.id;
                console.log(`✅ Organization ID: ${organizationId}`);
            }
        } catch (err) {
            console.error('Failed to fetch organization ID:', err);
        }
    }
    
    async function loadThreatModels() {
        try {
            loading = true;
            error = null;
            
            console.log(`🔍 Loading threat models for ${orgName}...`);
            
            // Get auth token (stored as 'auth_token' in localStorage)
            const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
            if (!authToken) {
                throw new Error('Authentication required. Please log in.');
            }
            
            // Use the authenticated endpoint
            const response = await fetch(`http://localhost:8000/api/threat-modeling/models`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // The simplified API returns the models directly, not wrapped in a success object
            threatModels = Array.isArray(result) ? result : [];
            console.log(`✅ Loaded ${threatModels.length} threat models`);
            
            // Extract organization_id from existing models if available
            if (threatModels.length > 0 && !organizationId) {
                organizationId = threatModels[0].organization_id;
                console.log(`✅ Using organization ID from existing model: ${organizationId}`);
            }
            
        } catch (err) {
            console.error('Failed to load threat models:', err);
            error = `Failed to load threat models: ${err.message}`;
        } finally {
            loading = false;
        }
    }
    
    async function loadDashboard() {
        try {
            console.log(`📊 Loading threat modeling dashboard for ${orgName}...`);
            
            // Get auth token for user-specific dashboard
            const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
            if (!authToken) {
                console.warn('No auth token - skipping dashboard load');
                return;
            }
            
            const response = await fetch(`http://localhost:8000/api/threat-modeling/dashboard`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Create a mock dashboard structure to match the frontend expectations
                dashboardData = {
                    statistics: {
                        total_threat_models: result.total_models || 0,
                        user_threat_models: result.total_models || 0, // Same as total for now
                        total_assessments: 0,
                        recent_models: result.recent_activity?.length || 0
                    },
                    quick_actions: [
                        {
                            icon: "🛡️",
                            title: "Create STRIDE Model",
                            description: "Start with STRIDE methodology",
                            action: "create_model"
                        },
                        {
                            icon: "🔍",
                            title: "Import Existing",
                            description: "Upload threat model file",
                            action: "import_model"
                        },
                        {
                            icon: "📚",
                            title: "Browse Templates",
                            description: "Use pre-built templates",
                            action: "browse_templates"
                        }
                    ]
                };
                console.log('✅ Dashboard data loaded');
            }
            
        } catch (err) {
            console.error('Failed to load dashboard:', err);
        }
    }
    
    async function createThreatModel() {
        try {
            creating = true;
            
            // Get auth token (stored as 'auth_token' in localStorage)
            const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
            if (!authToken) {
                throw new Error('Authentication required. Please log in.');
            }
            
            // Validate organization_id
            if (!organizationId) {
                throw new Error('Organization ID not found. Please refresh the page or ensure you have existing threat models.');
            }
            
            const requestData = {
                name: newModelName.trim(),
                description: newModelDescription.trim() || "",
                methodology: newModelMethodology,
                organization_id: organizationId,
                repository_id: newModelRepository || null,
                metadata: {
                    created_via: "frontend",
                    created_at: new Date().toISOString()
                }
            };
            
            const response = await fetch(`http://localhost:8000/api/threat-modeling/models`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const result = await response.json();
            
            console.log('✅ Threat model created successfully:', result);
            showCreateModal = false;
            resetCreateForm();
            await loadThreatModels(); // Refresh list
            
            // For now, just show success message since we don't have individual model pages yet
            alert(`✅ Threat model "${result.name}" created successfully!`);
            
        } catch (err) {
            console.error('Failed to create threat model:', err);
            error = `Failed to create threat model: ${err.message}`;
        } finally {
            creating = false;
        }
    }
    
    function resetCreateForm() {
        newModelName = '';
        newModelDescription = '';
        newModelMethodology = 'STRIDE';
        newModelRepository = null;
    }
    
    function openCreateModal() {
        resetCreateForm();
        showCreateModal = true;
    }
    
    function closeCreateModal() {
        showCreateModal = false;
        resetCreateForm();
    }
    
    function formatDate(dateString) {
        if (!dateString) return 'Never';
        return new Date(dateString).toLocaleDateString();
    }
    
    function getMethodologyColor(methodology) {
        const colors = {
            'STRIDE': 'bg-blue-100 text-blue-800',
            'LINDDUN': 'bg-purple-100 text-purple-800',
            'CIA': 'bg-green-100 text-green-800',
            'CUSTOM': 'bg-gray-100 text-gray-800'
        };
        return colors[methodology] || colors['CUSTOM'];
    }
    
    function getStatusColor(status) {
        const colors = {
            'draft': 'bg-yellow-100 text-yellow-800',
            'review': 'bg-orange-100 text-orange-800',
            'approved': 'bg-green-100 text-green-800',
            'archived': 'bg-gray-100 text-gray-800'
        };
        return colors[status] || colors['draft'];
    }
    
    function confirmDeleteThreatModel(model) {
        modelToDelete = model;
        showDeleteModal = true;
    }
    
    function cancelDelete() {
        modelToDelete = null;
        showDeleteModal = false;
    }
    
    async function deleteThreatModel() {
        if (!modelToDelete) return;
        
        try {
            console.log(`🗑️ Deleting threat model: ${modelToDelete.name} (ID: ${modelToDelete.id})`);
            
            // Get auth token (stored as 'auth_token' in localStorage)
            const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
            if (!authToken) {
                throw new Error('Authentication required. Please log in.');
            }
            
            const response = await fetch(`http://localhost:8000/api/threat-modeling/models/${modelToDelete.id}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                }
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const result = await response.json();
            console.log('✅ Threat model deleted successfully:', result);
            
            // Close modal and reset
            showDeleteModal = false;
            const deletedModelName = modelToDelete.name;
            modelToDelete = null;
            
            // Refresh the list
            await loadThreatModels();
            
            // Show success message
            console.log(`✅ Threat model "${deletedModelName}" has been deleted successfully.`);
            
        } catch (err) {
            console.error('Failed to delete threat model:', err);
            alert(`❌ Failed to delete threat model: ${err.message}`);
        }
    }
    
    // Import functionality
    function triggerImport() {
        importFileInput.click();
    }
    
    async function handleJSONImport(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        try {
            importing = true;
            
            // Validate file type
            if (!file.name.toLowerCase().endsWith('.json')) {
                alert('❌ Please select a valid JSON file');
                return;
            }
            
            // Read file content
            const text = await file.text();
            const importData = JSON.parse(text);
            
            // Validate JSON structure
            if (!importData.metadata || !importData.metadata.name || !importData.metadata.methodology) {
                alert('❌ Invalid threat model file format. Expected structure: metadata.name, metadata.methodology, canvas');
                return;
            }
            
            // Confirm import
            const confirmMessage = `Import threat model "${importData.metadata.name}"?\n\nMethodology: ${importData.metadata.methodology}\nElements: ${importData.canvas?.elements?.length || 0}\nThreats: ${importData.canvas?.threats?.length || 0}`;
            
            if (!confirm(confirmMessage)) {
                return;
            }
            
            // Create new threat model with imported data
            const requestData = {
                name: importData.metadata.name,
                description: importData.metadata.description || `Imported from ${file.name}`,
                methodology: importData.metadata.methodology,
                repository_id: null,
                metadata: {
                    ...importData.metadata,
                    imported_from: file.name,
                    imported_at: new Date().toISOString(),
                    original_export_date: importData.metadata.exportDate
                },
                canvas_data: importData.canvas || {}
                // Remove separate threats field since it's already in canvas_data.threats
            };
            
            console.log('🔍 Sending request data to API:', requestData);
            console.log('🔍 Canvas data being sent:', requestData.canvas_data);
            console.log('🔍 Elements count:', requestData.canvas_data.elements?.length || 0);
            console.log('🔍 Connections count:', requestData.canvas_data.connections?.length || 0);
            console.log('🔍 Threats count:', requestData.canvas_data.threats?.length || 0);
            
            // Get auth token (stored as 'auth_token' in localStorage)
            const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
            if (!authToken) {
                throw new Error('Authentication required. Please log in.');
            }
            
            const response = await fetch(`http://localhost:8000/api/threat-modeling/models`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ API Error Response:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const result = await response.json();
            console.log('✅ Threat model imported successfully:', result);
            console.log('✅ Returned canvas_data:', result.canvas_data);
            
            // Check if canvas_data was actually stored
            if (!result.canvas_data || Object.keys(result.canvas_data).length === 0) {
                console.warn('⚠️ WARNING: API did not return canvas_data! Canvas will be empty.');
                console.warn('⚠️ This suggests the backend API is not properly storing canvas_data.');
            }
            
            // Refresh the list
            await loadThreatModels();
            
            // Show success message
            alert(`✅ Threat model "${result.name}" imported successfully!`);
            
        } catch (err) {
            console.error('Failed to import threat model:', err);
            alert(`❌ Failed to import threat model: ${err.message}`);
        } finally {
            importing = false;
            // Reset file input
            event.target.value = '';
        }
    }

    // Document Upload Functionality
    async function handleDocumentUpload(event, modelId) {
        const file = event.target.files[0];
        if (!file) return;

        console.log(`📄 Uploading document for model ${modelId}: ${file.name}`);

        try {
            // Update model status to show processing
            const modelIndex = threatModels.findIndex(m => m.id === modelId);
            if (modelIndex >= 0) {
                threatModels[modelIndex].document_status = 'processing';
                threatModels[modelIndex].document_file_name = file.name;
                threatModels = [...threatModels]; // Trigger reactivity
            }

            // Create FormData for file upload
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`http://localhost:8000/api/threat-modeling/models/${modelId}/upload-document`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log('✅ Document uploaded successfully:', result);

            // Update model with successful analysis
            if (modelIndex >= 0) {
                threatModels[modelIndex].document_status = 'completed';
                threatModels[modelIndex].document_analysis = result.analysis;
                threatModels[modelIndex].document_file_name = result.analysis.filename;
                threatModels = [...threatModels]; // Trigger reactivity
            }

            // Show success notification
            console.log(`✅ Document "${file.name}" analyzed successfully for threat model`);

        } catch (error) {
            console.error('Failed to upload document:', error);
            
            // Update model status to show error
            if (modelIndex >= 0) {
                threatModels[modelIndex].document_status = 'failed';
                threatModels = [...threatModels]; // Trigger reactivity
            }
            
            alert(`❌ Failed to upload document: ${error.message}`);
        } finally {
            // Reset file input
            event.target.value = '';
        }
    }
</script>

<svelte:head>
    <title>Threat Modeling - {orgName} - WithOps</title>
</svelte:head>

<div class="min-h-screen bg-gray-50">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <header class="mb-8">
            <nav class="flex items-center space-x-2 text-sm text-gray-500 mb-4">
                <a href="/" class="hover:text-gray-700">Dashboard</a>
                <span>/</span>
                <a href={`/github/workspace/${orgName}`} class="hover:text-gray-700">{orgName} Workspace</a>
                <span>/</span>
                <span class="text-gray-900">Threat Modeling</span>
            </nav>
            
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold text-gray-900 flex items-center space-x-3">
                        <span>🛡️</span>
                        <span>Threat Modeling</span>
                    </h1>
                    <p class="text-gray-600">Create and manage threat models for {orgName}</p>
                </div>

                <div class="flex space-x-3">
                    <button 
                        on:click={() => goto(`/github/workspace/${orgName}`)}
                        class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 font-medium"
                    >
                        ← Back to Workspace
                    </button>
                    <button
                        on:click={openCreateModal}
                        class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 font-medium flex items-center space-x-2"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                        <span>Create Threat Model</span>
                    </button>
                </div>
            </div>
        </header>

        {#if loading}
            <!-- Loading State -->
            <div class="space-y-6">
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
                
                <div class="bg-white shadow rounded-lg p-6">
                    <div class="h-6 bg-gray-200 rounded w-32 mb-4 animate-pulse"></div>
                    <div class="space-y-4">
                        {#each Array(3) as _}
                            <div class="border border-gray-200 rounded-lg p-6 animate-pulse">
                                <div class="h-5 bg-gray-200 rounded w-48 mb-2"></div>
                                <div class="h-4 bg-gray-100 rounded w-full mb-3"></div>
                                <div class="flex space-x-4">
                                    {#each Array(3) as _}
                                        <div class="h-3 bg-gray-200 rounded w-16"></div>
                                    {/each}
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            </div>
        {:else if error}
            <!-- Error State -->
            <div class="bg-white shadow rounded-lg p-6">
                <div class="text-center">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                        <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </div>
                    
                    <h3 class="text-lg font-medium text-gray-900 mb-2">Failed to Load Threat Models</h3>
                    <p class="text-sm text-red-600 mb-6">{error}</p>
                    
                    <div class="space-y-3">
                        <button 
                            on:click={loadThreatModels}
                            class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
                        >
                            Retry
                        </button>
                        <button 
                            on:click={() => goto(`/github/workspace/${orgName}`)}
                            class="bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 ml-3"
                        >
                            Go Back
                        </button>
                    </div>
                </div>
            </div>
        {:else}
            <!-- Main Content -->
            <div class="space-y-6">
                <!-- Dashboard Overview -->
                {#if dashboardData}
                    <div class="bg-white shadow rounded-lg p-6">
                        <h2 class="text-xl font-semibold text-gray-900 mb-4">Overview</h2>
                        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <div class="bg-red-50 p-4 rounded-lg">
                                <h3 class="text-lg font-medium text-red-900">Total Models</h3>
                                <p class="text-2xl font-bold text-red-600">{dashboardData.statistics.total_threat_models}</p>
                            </div>
                            
                            <div class="bg-blue-50 p-4 rounded-lg">
                                <h3 class="text-lg font-medium text-blue-900">Your Models</h3>
                                <p class="text-2xl font-bold text-blue-600">{dashboardData.statistics.user_threat_models}</p>
                            </div>
                            
                            <div class="bg-purple-50 p-4 rounded-lg">
                                <h3 class="text-lg font-medium text-purple-900">Assessments</h3>
                                <p class="text-2xl font-bold text-purple-600">{dashboardData.statistics.total_assessments}</p>
                            </div>
                            
                            <div class="bg-green-50 p-4 rounded-lg">
                                <h3 class="text-lg font-medium text-green-900">Recent (7d)</h3>
                                <p class="text-2xl font-bold text-green-600">{dashboardData.statistics.recent_models}</p>
                            </div>
                        </div>
                        
                        <!-- Quick Actions -->
                        <div class="mt-6">
                            <h3 class="text-lg font-medium text-gray-900 mb-3">Quick Actions</h3>
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {#each dashboardData.quick_actions as action}
                                    <button type="button" 
                                            class="w-full border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors duration-200 text-left"
                                            disabled={importing}
                                            on:click={() => {
                                                 if (action.action === 'create_model') openCreateModal();
                                                 else if (action.action === 'import_model') triggerImport();
                                             }}>
                                        <div class="flex items-center space-x-3">
                                            <span class="text-2xl">{action.icon}</span>
                                            <div>
                                                <h4 class="font-medium text-gray-900">{action.title}</h4>
                                                <p class="text-sm text-gray-600">
                                                    {#if importing && action.action === 'import_model'}
                                                        Importing...
                                                    {:else}
                                                        {action.description}
                                                    {/if}
                                                </p>
                                            </div>
                                        </div>
                                    </button>
                                {/each}
                            </div>
                        </div>
                    </div>
                {/if}

                <!-- Threat Models List -->
                <div class="bg-white shadow rounded-lg p-6">
                    <div class="flex items-center justify-between mb-6">
                        <h2 class="text-xl font-semibold text-gray-900">Threat Models</h2>
                        <span class="text-sm text-gray-500">{threatModels.length} models</span>
                    </div>
                    
                    {#if threatModels.length > 0}
                        <div class="space-y-4">
                            {#each threatModels as model}
                                <div class="border border-gray-200 rounded-lg p-6 hover:bg-gray-50 transition-colors duration-200">
                                    <div class="flex items-start justify-between">
                                        <div class="flex-1">
                                            <h3 class="text-lg font-medium text-gray-900 mb-2">
                                                <span class="hover:text-red-600 transition-colors duration-200">
                                                    {model.name}
                                                </span>
                                            </h3>
                                            
                                            {#if model.description}
                                                <p class="text-gray-600 text-sm mb-3">{model.description}</p>
                                            {/if}
                                            
                                            
                                            <div class="flex items-center space-x-4 text-sm text-gray-500">
                                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getMethodologyColor(model.methodology)}">
                                                    {model.methodology}
                                                </span>
                                                
                                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusColor(model.status)}">
                                                    {model.status}
                                                </span>
                                                
                                                <span class="flex items-center">
                                                    <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10" />
                                                    </svg>
                                                    {model.element_count || 0} elements
                                                </span>
                                                
                                                <span class="flex items-center">
                                                    <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    </svg>
                                                    {model.assessment_count || 0} threats
                                                </span>
                                                
                                                <span>Created {formatDate(model.created_at)}</span>
                                            </div>
                                            
                                            {#if model.repository}
                                                <div class="mt-2">
                                                    <span class="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700">
                                                        📁 {model.repository.name}
                                                    </span>
                                                </div>
                                            {/if}
                                        </div>
                                        
                                        <div class="flex space-x-2">
                                            <button
                                               class="bg-red-100 text-red-700 px-3 py-1 rounded-lg hover:bg-red-200 text-sm transition-colors duration-200"
                                               on:click={() => goto(`/github/workspace/${orgName}/threat-modeling/${model.id}`)}
                                            >
                                                📝 Open Canvas
                                            </button>
                                            
                                            <button
                                               class="bg-gray-100 text-red-600 px-3 py-1 rounded-lg hover:bg-red-100 text-sm transition-colors duration-200"
                                               on:click|stopPropagation={() => confirmDeleteThreatModel(model)}
                                               title="Delete threat model"
                                            >
                                                🗑️ Delete
                                            </button>
                                            
                                            {#if model.last_ai_analysis}
                                                <span class="bg-purple-100 text-purple-700 px-3 py-1 rounded-lg text-sm">
                                                    🤖 AI Analyzed
                                                </span>
                                            {/if}
                                        </div>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {:else}
                        <!-- Empty State -->
                        <div class="text-center py-12">
                            <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                                <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                            </div>
                            <h3 class="mt-2 text-sm font-medium text-gray-900">No threat models yet</h3>
                            <p class="mt-1 text-sm text-gray-500">Get started by creating your first threat model.</p>
                            <div class="mt-6">
                                <button
                                    on:click={openCreateModal}
                                    class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 font-medium"
                                >
                                    Create Your First Threat Model
                                </button>
                            </div>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
</div>

<!-- Create Threat Model Modal -->
{#if showCreateModal}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-medium text-gray-900">Create New Threat Model</h3>
                <button
                    on:click={closeCreateModal}
                    class="text-gray-400 hover:text-gray-600"
                    aria-label="Close modal"
                >
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            
            <form on:submit|preventDefault={createThreatModel} class="space-y-4">
                <div>
                    <label for="modelName" class="block text-sm font-medium text-gray-700 mb-1">
                        Model Name *
                    </label>
                    <input
                        id="modelName"
                        type="text"
                        bind:value={newModelName}
                        required
                        placeholder="e.g., API Security Model"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    />
                </div>
                
                <div>
                    <label for="modelDescription" class="block text-sm font-medium text-gray-700 mb-1">
                        Description
                    </label>
                    <textarea
                        id="modelDescription"
                        bind:value={newModelDescription}
                        rows="3"
                        placeholder="Brief description of what this threat model covers..."
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    ></textarea>
                </div>
                
                <div>
                    <label for="methodology" class="block text-sm font-medium text-gray-700 mb-1">
                        Methodology
                    </label>
                    <select
                        id="methodology"
                        bind:value={newModelMethodology}
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    >
                        <option value="STRIDE">STRIDE (Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation)</option>
                        <option value="LINDDUN">LINDDUN (Privacy-focused)</option>
                        <option value="CIA">CIA Triad (Confidentiality, Integrity, Availability)</option>
                        <option value="CUSTOM">Custom</option>
                    </select>
                </div>
                
                <div class="flex space-x-3 pt-4">
                    <button
                        type="button"
                        on:click={closeCreateModal}
                        class="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400"
                        disabled={creating}
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        class="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={creating || !newModelName.trim()}
                    >
                        {#if creating}
                            <span class="flex items-center justify-center">
                                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Creating...
                            </span>
                        {:else}
                            Create Model
                        {/if}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteModal && modelToDelete}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mt-3">
                <!-- Icon -->
                <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                    <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                </div>
                
                <!-- Title -->
                <h3 class="text-lg font-medium text-gray-900 text-center mb-2">
                    Delete Threat Model
                </h3>
                
                <!-- Content -->
                <div class="text-center mb-6">
                    <p class="text-sm text-gray-600 mb-3">
                        Are you sure you want to delete the threat model:
                    </p>
                    <p class="font-medium text-gray-900 mb-3">
                        "{modelToDelete.name}"
                    </p>
                    <div class="bg-red-50 border border-red-200 rounded-lg p-3 text-left">
                        <p class="text-sm text-red-700 font-medium mb-2">This action cannot be undone and will permanently remove:</p>
                        <ul class="text-sm text-red-600 space-y-1">
                            <li>• The threat model and all its data</li>
                            <li>• All threat assessments ({modelToDelete.assessment_count || 0} threats)</li>
                            <li>• All canvas diagrams and components</li>
                            <li>• All analysis results and history</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Buttons -->
                <div class="flex space-x-3">
                    <button
                        type="button"
                        on:click={cancelDelete}
                        class="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 transition-colors duration-200"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        on:click={deleteThreatModel}
                        class="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors duration-200"
                    >
                        🗑️ Delete Permanently
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<!-- Hidden File Input for Import -->
<input 
    type="file" 
    accept=".json"
    bind:this={importFileInput}
    on:change={handleJSONImport}
    style="display: none"
/>
