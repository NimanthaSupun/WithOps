<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isDarkMode } from '$lib/stores.js';

	// State variables
	let loading = $state(true);
	let error = $state(null);
	let orgName = $state('');
	let organizationId = $state(null);
	let threatModels = $state([]);
	let dashboardData = $state(null);
	let showCreateModal = $state(false);
	let showDeleteModal = $state(false);
	let selectedModel = $state(null);
	let modelToDelete = $state(null);

	// Create new threat model form
	let newModelName = $state('');
	let newModelDescription = $state('');
	let newModelMethodology = $state('STRIDE');
	let newModelRepository = $state(null);
	let repositories = $state([]);
	let creating = $state(false);

	// Import functionality
	let importing = $state(false);
	let importFileInput;

	// Theme
	let darkMode = $state(false);

	$effect(() => {
		const unsubscribe = isDarkMode.subscribe((value) => {
			darkMode = value;
		});
		return unsubscribe;
	});

	function toggleTheme() {
		isDarkMode.toggle();
	}

	onMount(async () => {
		orgName = $page.params.org;
		console.log(`🛡️ Loading threat modeling for organization: ${orgName}`);

		// Initialize theme
		isDarkMode.init();

		await fetchOrganizationId();
		await loadThreatModels();
		await loadDashboard();
	});

	async function fetchOrganizationId() {
		try {
			const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
			if (!authToken) return;

			const response = await fetch(`http://localhost:8000/api/github/workspace/${orgName}`, {
				headers: {
					Authorization: `Bearer ${authToken}`
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

			const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
			if (!authToken) {
				throw new Error('Authentication required. Please log in.');
			}

			const response = await fetch(`http://localhost:8000/api/threat-modeling/models`, {
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${authToken}`
				}
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			const result = await response.json();
			threatModels = Array.isArray(result) ? result : [];
			console.log(`✅ Loaded ${threatModels.length} threat models`);

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

			const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
			if (!authToken) {
				console.warn('No auth token - skipping dashboard load');
				return;
			}

			const response = await fetch(`http://localhost:8000/api/threat-modeling/dashboard`, {
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${authToken}`
				}
			});

			if (response.ok) {
				const result = await response.json();

				dashboardData = {
					statistics: {
						total_threat_models: result.total_models || 0,
						user_threat_models: result.total_models || 0,
						total_assessments: 0,
						recent_models: result.recent_activity?.length || 0
					}
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

			const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
			if (!authToken) {
				throw new Error('Authentication required. Please log in.');
			}

			if (!organizationId) {
				throw new Error('Organization ID not found. Please refresh the page.');
			}

			const requestData = {
				name: newModelName.trim(),
				description: newModelDescription.trim() || '',
				methodology: newModelMethodology,
				organization_id: organizationId,
				repository_id: newModelRepository || null,
				metadata: {
					created_via: 'frontend',
					created_at: new Date().toISOString()
				}
			};

			const response = await fetch(`http://localhost:8000/api/threat-modeling/models`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${authToken}`
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
			await loadThreatModels();

			showNotification(`Threat model "${result.name}" created successfully!`, 'success');
		} catch (err) {
			console.error('Failed to create threat model:', err);
			error = `Failed to create threat model: ${err.message}`;
			showNotification(err.message, 'error');
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

			const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
			if (!authToken) {
				throw new Error('Authentication required. Please log in.');
			}

			const response = await fetch(
				`http://localhost:8000/api/threat-modeling/models/${modelToDelete.id}`,
				{
					method: 'DELETE',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${authToken}`
					}
				}
			);

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`HTTP ${response.status}: ${errorText}`);
			}

			const result = await response.json();
			console.log('✅ Threat model deleted successfully:', result);

			showDeleteModal = false;
			const deletedModelName = modelToDelete.name;
			modelToDelete = null;

			await loadThreatModels();

			showNotification(
				`Threat model "${deletedModelName}" has been deleted successfully.`,
				'success'
			);
		} catch (err) {
			console.error('Failed to delete threat model:', err);
			showNotification(`Failed to delete threat model: ${err.message}`, 'error');
		}
	}

	function triggerImport() {
		importFileInput.click();
	}

	async function handleJSONImport(event) {
		const file = event.target.files[0];
		if (!file) return;

		try {
			importing = true;

			if (!file.name.toLowerCase().endsWith('.json')) {
				showNotification('Please select a valid JSON file', 'error');
				return;
			}

			const text = await file.text();
			const importData = JSON.parse(text);

			if (!importData.metadata || !importData.metadata.name || !importData.metadata.methodology) {
				showNotification('Invalid threat model file format', 'error');
				return;
			}

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
			};

			const authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
			if (!authToken) {
				throw new Error('Authentication required. Please log in.');
			}

			const response = await fetch(`http://localhost:8000/api/threat-modeling/models`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${authToken}`
				},
				body: JSON.stringify(requestData)
			});

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`HTTP ${response.status}: ${errorText}`);
			}

			const result = await response.json();
			console.log('✅ Threat model imported successfully:', result);

			await loadThreatModels();

			showNotification(`Threat model "${result.name}" imported successfully!`, 'success');
		} catch (err) {
			console.error('Failed to import threat model:', err);
			showNotification(`Failed to import threat model: ${err.message}`, 'error');
		} finally {
			importing = false;
			event.target.value = '';
		}
	}

	// Notification system
	let notificationMessage = $state('');
	let notificationType = $state('success'); // 'success' or 'error'
	let showNotificationFlag = $state(false);

	function showNotification(message, type = 'success') {
		notificationMessage = message;
		notificationType = type;
		showNotificationFlag = true;

		setTimeout(() => {
			showNotificationFlag = false;
		}, 3000);
	}
</script>

<svelte:head>
	<title>Threat Modeling - {orgName} - WithOps</title>
</svelte:head>

<div class="threat-modeling-container {darkMode ? 'dark' : 'light'}">
	<!-- Top Navigation Bar -->
	<nav class="top-navbar">
		<div class="navbar-content">
			<!-- Left: Brand & Breadcrumb -->
			<div class="navbar-left">
				<div class="brand-section">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<div class="brand-text">
						<span class="brand-name">WithOps</span>
						<span class="brand-subtitle">Threat Modeling</span>
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
					<span class="breadcrumb-current">Threat Modeling</span>
				</nav>
			</div>

			<!--todo:-- Right: Theme Toggle -->
			<!-- <div class="navbar-right">
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
            </div> -->
		</div>
	</nav>

	<!-- Main Layout: Sidebar + Content -->
	<div class="main-layout">
		<!-- Left Sidebar -->
		<aside class="left-sidebar">
			<!-- Back Button -->
			<a href="/github/workspace/{orgName}" class="back-button">
				<svg class="back-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M10 19l-7-7m0 0l7-7m-7 7h18"
					/>
				</svg>
				<span>Back to Workspace</span>
			</a>

			<!-- Statistics Section -->
			<div class="sidebar-section">
				<h3 class="section-title">OVERVIEW</h3>

				<div class="stat-cards">
					<!-- Total Models -->
					<div class="stat-card total-models">
						<div class="stat-icon">🛡️</div>
						<div class="stat-content">
							<div class="stat-value">{dashboardData?.statistics.total_threat_models || 0}</div>
							<div class="stat-label">Total Models</div>
						</div>
					</div>

					<!-- Your Models -->
					<div class="stat-card your-models">
						<div class="stat-icon">👤</div>
						<div class="stat-content">
							<div class="stat-value">{dashboardData?.statistics.user_threat_models || 0}</div>
							<div class="stat-label">Your Models</div>
						</div>
					</div>

					<!-- Assessments -->
					<div class="stat-card assessments">
						<div class="stat-icon">📊</div>
						<div class="stat-content">
							<div class="stat-value">{dashboardData?.statistics.total_assessments || 0}</div>
							<div class="stat-label">Assessments</div>
						</div>
					</div>

					<!-- Recent -->
					<div class="stat-card recent">
						<div class="stat-icon">🕒</div>
						<div class="stat-content">
							<div class="stat-value">{dashboardData?.statistics.recent_models || 0}</div>
							<div class="stat-label">Recent (7d)</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Action Buttons Section -->
			<div class="sidebar-actions">
				<button onclick={openCreateModal} class="action-button create-button">
					<div class="button-content">
						<svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6v6m0 0v6m0-6h6m-6 0H6"
							/>
						</svg>
						<div class="button-text">
							<span class="button-label">Create Threat Model</span>
							<span class="button-desc">Start new analysis</span>
						</div>
					</div>
				</button>

				<button onclick={triggerImport} class="action-button import-button" disabled={importing}>
					<div class="button-content">
						<svg class="button-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
							/>
						</svg>
						<div class="button-text">
							<span class="button-label">
								{#if importing}
									Importing...
								{:else}
									Import Existing
								{/if}
							</span>
							<span class="button-desc">Upload JSON file</span>
						</div>
					</div>
				</button>
			</div>
		</aside>

		<!-- Main Content Area -->
		<main class="main-content">
			{#if loading}
				<!-- Loading State -->
				<div class="loading-state">
					<div class="loading-spinner"></div>
					<span class="loading-text">Loading threat models...</span>
				</div>
			{:else if error}
				<!-- Error State -->
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
					<button onclick={loadThreatModels} class="retry-button"> Try Again </button>
				</div>
			{:else if threatModels.length === 0}
				<!-- Empty State -->
				<div class="empty-state">
					<div class="empty-icon">
						<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
							/>
						</svg>
					</div>
					<h3 class="empty-title">No threat models yet</h3>
					<p class="empty-description">
						Get started by creating your first threat model or importing an existing one.
					</p>
					<div class="empty-actions">
						<button onclick={openCreateModal} class="empty-button primary">
							<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 6v6m0 0v6m0-6h6m-6 0H6"
								/>
							</svg>
							Create Your First Model
						</button>
						<button onclick={triggerImport} class="empty-button secondary">
							<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
								/>
							</svg>
							Import Existing
						</button>
					</div>
				</div>
			{:else}
				<!-- Threat Models Grid -->
				<div class="content-header">
					<h2 class="content-title">Your Threat Models</h2>
					<span class="content-count"
						>{threatModels.length} {threatModels.length === 1 ? 'model' : 'models'}</span
					>
				</div>

				<div class="models-grid">
					{#each threatModels as model}
						<div class="model-card">
							<div class="model-header">
								<div class="model-info">
									<h3 class="model-name">{model.name}</h3>
									{#if model.description}
										<p class="model-description">{model.description}</p>
									{/if}
								</div>

								<div class="model-badges">
									<span class="badge methodology-badge {model.methodology.toLowerCase()}">
										{model.methodology}
									</span>
									<span class="badge status-badge {model.status}">
										{model.status}
									</span>
								</div>
							</div>

							<div class="model-stats">
								<div class="stat-item">
									<svg class="stat-item-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2H7a2 2 0 00-2 2v2M7 7h10"
										/>
									</svg>
									<span>{model.element_count || 0} elements</span>
								</div>

								<div class="stat-item">
									<svg class="stat-item-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
										/>
									</svg>
									<span>{model.assessment_count || 0} threats</span>
								</div>

								<div class="stat-item">
									<svg class="stat-item-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
										/>
									</svg>
									<span>{formatDate(model.created_at)}</span>
								</div>
							</div>

							<div class="model-actions">
								<button
									onclick={() => goto(`/github/workspace/${orgName}/threat-modeling/${model.id}`)}
									class="model-button primary"
								>
									<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
										/>
									</svg>
									Open Canvas
								</button>

								<button
									onclick={() => confirmDeleteThreatModel(model)}
									class="model-button danger"
									title="Delete threat model"
								>
									<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
										/>
									</svg>
									Delete
								</button>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</main>
	</div>
</div>

<!-- Notification Toast -->
{#if showNotificationFlag}
	<div class="notification {notificationType}">
		{notificationMessage}
	</div>
{/if}

<!-- Hidden File Input for Import -->
<input
	type="file"
	accept=".json"
	bind:this={importFileInput}
	onchange={handleJSONImport}
	style="display: none"
/>

<!-- Create Threat Model Modal -->
{#if showCreateModal}
	<div
		class="modal-backdrop"
		onclick={closeCreateModal}
		onkeydown={(e) => e.key === 'Escape' && closeCreateModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title" style="color: #FFFFFF !important;">Create New Threat Model</h3>
					<p class="modal-subtitle" style="color: rgba(255, 255, 255, 0.8) !important;">
						Start your security threat analysis
					</p>
				</div>
				<button onclick={closeCreateModal} class="modal-close" aria-label="Close modal">
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
					<label for="modelName" class="form-label" style="color: #FFFFFF !important;"
						>Model Name *</label
					>
					<input
						id="modelName"
						type="text"
						bind:value={newModelName}
						placeholder="e.g., API Security Model"
						class="form-input"
						style="color: #FFFFFF !important;"
						onkeypress={(e) => e.key === 'Enter' && createThreatModel()}
					/>
				</div>

				<div class="form-group">
					<label for="modelDescription" class="form-label" style="color: #FFFFFF !important;"
						>Description</label
					>
					<textarea
						id="modelDescription"
						bind:value={newModelDescription}
						rows="3"
						placeholder="Brief description of what this threat model covers..."
						class="form-input"
						style="color: #FFFFFF !important;"
					></textarea>
				</div>

				<div class="form-group">
					<label for="methodology" class="form-label" style="color: #FFFFFF !important;"
						>Methodology</label
					>
					<select
						id="methodology"
						bind:value={newModelMethodology}
						class="form-input"
						style={darkMode
							? 'background: #FFFFFF !important; color: #000000 !important;'
							: 'background: #FFFFFF !important; color: #000000 !important;'}
					>
						<option value="STRIDE"
							>STRIDE - Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation</option
						>
						<option value="LINDDUN">LINDDUN - Privacy-focused threat modeling</option>
						<option value="CIA">CIA Triad - Confidentiality, Integrity, Availability</option>
						<option value="CUSTOM">Custom - Define your own methodology</option>
					</select>
				</div>

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
						After creating the model, you'll be able to design your system architecture and identify
						potential threats.
					</p>
				</div>
			</div>

			<div class="modal-footer">
				<button onclick={closeCreateModal} class="btn-secondary" disabled={creating}>
					Cancel
				</button>
				<button
					onclick={createThreatModel}
					disabled={creating || !newModelName.trim()}
					class="btn-primary"
				>
					{#if creating}
						<svg
							class="btn-icon animate-spin"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<circle
								class="opacity-25"
								cx="12"
								cy="12"
								r="10"
								stroke="currentColor"
								stroke-width="4"
							></circle>
							<path
								class="opacity-75"
								fill="currentColor"
								d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
							></path>
						</svg>
						Creating...
					{:else}
						<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6v6m0 0v6m0-6h6m-6 0H6"
							/>
						</svg>
						Create Model
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteModal && modelToDelete}
	<div
		class="modal-backdrop"
		onclick={cancelDelete}
		onkeydown={(e) => e.key === 'Escape' && cancelDelete()}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-container"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title" style="color: #FFFFFF !important;">Delete Threat Model</h3>
					<p class="modal-subtitle" style="color: rgba(255, 255, 255, 0.8) !important;">
						This action cannot be undone
					</p>
				</div>
				<button onclick={cancelDelete} class="modal-close" aria-label="Close modal">
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
				<div class="delete-warning">
					<div class="warning-icon">
						<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
							/>
						</svg>
					</div>
					<div class="warning-content">
						<p class="warning-title">Are you sure you want to delete:</p>
						<p class="warning-model-name">"{modelToDelete.name}"</p>
						<div class="warning-details">
							<p class="warning-subtitle">This will permanently remove:</p>
							<ul class="warning-list">
								<li>• The threat model and all its data</li>
								<li>• All threat assessments ({modelToDelete.assessment_count || 0} threats)</li>
								<li>• All canvas diagrams and components</li>
								<li>• All analysis results and history</li>
							</ul>
						</div>
					</div>
				</div>
			</div>

			<div class="modal-footer">
				<button onclick={cancelDelete} class="btn-secondary"> Cancel </button>
				<button onclick={deleteThreatModel} class="btn-danger">
					<svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
						/>
					</svg>
					Delete Permanently
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Root Container */
	.threat-modeling-container {
		min-height: 100vh;
		background: var(--bg-primary);
		transition: background-color 0.3s ease;
	}

	/* CSS Variables - Light Mode */
	.threat-modeling-container.light {
		--bg-primary: #ffffff;
		--bg-secondary: #f8fafc;
		--text-primary: #1a1a1a;
		--text-secondary: #666666;
		--text-muted: #999999;
		--border-color: rgba(0, 217, 255, 0.3);
		--primary-color: #00d9ff;
		--primary-hover: #00b8d4;
		--card-bg: rgba(0, 217, 255, 0.05);
		--success-color: #16a34a;
		--error-color: #ef4444;
	}

	/* CSS Variables - Dark Mode */
	.threat-modeling-container.dark {
		--bg-primary: #000000;
		--bg-secondary: #0a0a0a;
		--text-primary: #ffffff;
		--text-secondary: #b8b8b8;
		--text-muted: #888888;
		--border-color: rgba(0, 217, 255, 0.3);
		--primary-color: #00d9ff;
		--primary-hover: #00b8d4;
		--card-bg: rgba(255, 255, 255, 0.05);
		--success-color: #22c55e;
		--error-color: #ef4444;
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
		border-bottom: 1px solid rgba(0, 217, 255, 0.3);
		padding: 1rem 2rem;
		transition: all 0.3s ease;
	}

	.threat-modeling-container.light .top-navbar {
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
		object-fit: contain;
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
		color: var(--text-primary);
		line-height: 1;
		letter-spacing: -0.02em;
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

	/* Theme Toggle */
	.navbar-right {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.theme-toggle {
		background: transparent;
		border: 1px solid var(--border-color);
		color: var(--text-secondary);
		padding: 0.625rem;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.3s ease;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.theme-toggle:hover {
		background: var(--card-bg);
		border-color: var(--primary-color);
		color: var(--primary-color);
		transform: scale(1.05);
	}

	.theme-icon {
		width: 20px;
		height: 20px;
	}

	/* Main Layout */
	.main-layout {
		margin-top: 80px;
		min-height: calc(100vh - 80px);
		display: flex;
	}

	/* Left Sidebar */
	.left-sidebar {
		position: fixed;
		left: 0;
		top: 80px;
		width: 280px;
		height: calc(100vh - 80px);
		background: rgba(0, 0, 0, 0.95);
		border-right: 1px solid rgba(0, 217, 255, 0.3);
		backdrop-filter: blur(20px);
		padding: 1.5rem;
		overflow-y: auto;
		z-index: 900;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.threat-modeling-container.light .left-sidebar {
		background: rgba(255, 255, 255, 0.95);
		border-right: 1px solid rgba(0, 217, 255, 0.2);
	}

	/* Back Button */
	.back-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: transparent;
		border: 1px solid rgba(0, 217, 255, 0.3);
		border-radius: 8px;
		color: var(--text-primary);
		text-decoration: none;
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
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: 1rem;
		text-transform: uppercase;
	}

	/* Statistics Cards */
	.stat-cards {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.stat-card {
		background: var(--card-bg);
		border: 1px solid var(--border-color);
		border-radius: 8px;
		padding: 1rem;
		display: flex;
		align-items: center;
		gap: 1rem;
		transition: all 0.3s ease;
		cursor: default;
	}

	.stat-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 8px 20px rgba(0, 217, 255, 0.15);
		border-color: var(--primary-color);
	}

	.threat-modeling-container.light .stat-card {
		background: rgba(255, 255, 255, 0.9);
		border-color: rgba(0, 217, 255, 0.2);
	}

	.threat-modeling-container.light .stat-card:hover {
		background: rgba(255, 255, 255, 1);
		box-shadow: 0 8px 20px rgba(0, 217, 255, 0.12);
	}

	.stat-icon {
		font-size: 1.75rem;
		line-height: 1;
		flex-shrink: 0;
	}

	.stat-content {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		flex: 1;
	}

	.stat-value {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1;
	}

	.stat-label {
		font-size: 0.75rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: 600;
	}

	/* Sidebar Actions */
	.sidebar-actions {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.action-button {
		background: var(--card-bg);
		border: 1px solid var(--border-color);
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
		text-align: left;
	}

	.action-button:hover {
		transform: translateY(-2px);
		box-shadow: 0 8px 20px rgba(0, 217, 255, 0.15);
		border-color: var(--primary-color);
		background: rgba(0, 217, 255, 0.08);
	}

	.threat-modeling-container.light .action-button {
		background: rgba(255, 255, 255, 0.9);
		border-color: rgba(0, 217, 255, 0.2);
	}

	.threat-modeling-container.light .action-button:hover {
		background: rgba(255, 255, 255, 1);
		border-color: rgba(0, 217, 255, 0.3);
		box-shadow: 0 8px 20px rgba(0, 217, 255, 0.12);
	}

	.action-button:active {
		transform: translateY(0);
	}

	.action-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		transform: none;
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
		color: var(--primary-color);
		transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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

	/* Main Content */
	.main-content {
		margin-left: 280px;
		flex: 1;
		padding: 2rem;
		min-height: calc(100vh - 80px);
	}

	/* Content Header */
	.content-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 2rem;
	}

	.content-title {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.content-count {
		font-size: 0.875rem;
		color: var(--text-muted);
		background: var(--card-bg);
		padding: 0.5rem 1rem;
		border-radius: 20px;
		border: 1px solid var(--border-color);
	}

	/* Loading State */
	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1.5rem;
		padding: 4rem;
	}

	.loading-spinner {
		width: 50px;
		height: 50px;
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
		font-weight: 500;
	}

	/* Error State */
	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.5rem;
		padding: 4rem;
		text-align: center;
	}

	.error-icon {
		width: 64px;
		height: 64px;
		color: var(--error-color);
	}

	.error-message {
		color: var(--error-color);
		font-size: 1.1rem;
		max-width: 500px;
	}

	.retry-button {
		padding: 0.75rem 1.5rem;
		background: #ffffff;
		color: #000000;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
	}

	.retry-button:hover {
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
		background: #00d9ff;
		color: #000000;
	}

	.threat-modeling-container.light .retry-button {
		background: #00d9ff;
		color: #000000;
		box-shadow:
			0 10px 30px rgba(0, 217, 255, 0.25),
			0 5px 15px rgba(0, 217, 255, 0.15);
	}

	.threat-modeling-container.light .retry-button:hover {
		background: #00b8d4;
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.35),
			0 8px 20px rgba(0, 217, 255, 0.25);
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
		width: 120px;
		height: 120px;
		background: var(--card-bg);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--border-color);
	}

	.empty-icon svg {
		width: 60px;
		height: 60px;
		color: var(--primary-color);
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
		margin-top: 1rem;
	}

	.empty-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 1rem 2rem;
		border-radius: 12px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		font-size: 0.95rem;
	}

	.empty-button.primary {
		background: #ffffff;
		color: #000000;
		border: none;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
	}

	.empty-button.primary:hover {
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
		background: #00d9ff;
		color: #000000;
	}

	.threat-modeling-container.light .empty-button.primary {
		background: #00d9ff;
		color: #000000;
		box-shadow:
			0 10px 30px rgba(0, 217, 255, 0.25),
			0 5px 15px rgba(0, 217, 255, 0.15);
	}

	.threat-modeling-container.light .empty-button.primary:hover {
		background: #00b8d4;
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.35),
			0 8px 20px rgba(0, 217, 255, 0.25);
	}

	.empty-button.secondary {
		background: rgba(0, 0, 0, 0.3);
		color: #00d9ff;
		border: 2px solid #00d9ff;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.4),
			0 0 20px rgba(0, 217, 255, 0.2);
	}

	.empty-button.secondary:hover {
		background: #00d9ff;
		color: #000000;
		transform: translateY(-3px);
		border-color: #00d9ff;
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.5),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}

	.threat-modeling-container.light .empty-button.secondary {
		background: rgba(255, 255, 255, 0.9);
		color: #00d9ff;
		border: 2px solid #00d9ff;
		box-shadow:
			0 10px 30px rgba(0, 217, 255, 0.15),
			0 0 20px rgba(0, 217, 255, 0.1);
	}

	.threat-modeling-container.light .empty-button.secondary:hover {
		background: #00d9ff;
		color: #000000;
	}

	/* Models Grid */
	.models-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
		gap: 1.5rem;
	}

	/* Model Card */
	.model-card {
		background: var(--card-bg);
		border: 1px solid var(--border-color);
		border-radius: 12px;
		backdrop-filter: blur(20px);
		padding: 1.5rem;
		transition: all 0.3s ease;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.model-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.15);
		border-color: var(--primary-color);
		background: rgba(0, 217, 255, 0.08);
	}

	.threat-modeling-container.light .model-card {
		background: rgba(255, 255, 255, 0.9);
		border-color: rgba(0, 217, 255, 0.2);
	}

	.threat-modeling-container.light .model-card:hover {
		background: rgba(255, 255, 255, 1);
		border-color: rgba(0, 217, 255, 0.3);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.12);
	}

	.model-header {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.model-info {
		flex: 1;
	}

	.model-name {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
		line-height: 1.3;
	}

	.model-description {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.5;
		margin: 0;
	}

	.model-badges {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.badge {
		padding: 0.375rem 0.75rem;
		border-radius: 6px;
		font-size: 0.75rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.methodology-badge.stride {
		background: rgba(0, 217, 255, 0.1);
		color: #00d9ff;
		border: 1px solid rgba(0, 217, 255, 0.3);
	}

	.methodology-badge.linddun {
		background: rgba(139, 92, 246, 0.1);
		color: #8b5cf6;
		border: 1px solid rgba(139, 92, 246, 0.3);
	}

	.methodology-badge.cia {
		background: rgba(236, 72, 153, 0.1);
		color: #ec4899;
		border: 1px solid rgba(236, 72, 153, 0.3);
	}

	.methodology-badge.custom {
		background: rgba(184, 184, 184, 0.1);
		color: #b8b8b8;
		border: 1px solid rgba(184, 184, 184, 0.3);
	}

	.status-badge.draft {
		background: rgba(251, 191, 36, 0.1);
		color: #fbcf24;
		border: 1px solid rgba(251, 191, 36, 0.3);
	}

	.status-badge.review {
		background: rgba(236, 72, 153, 0.1);
		color: #ec4899;
		border: 1px solid rgba(236, 72, 153, 0.3);
	}

	.status-badge.approved {
		background: rgba(34, 197, 94, 0.1);
		color: #22c55e;
		border: 1px solid rgba(34, 197, 94, 0.3);
	}

	.status-badge.archived {
		background: rgba(184, 184, 184, 0.1);
		color: #b8b8b8;
		border: 1px solid rgba(184, 184, 184, 0.3);
	}

	/* Model Stats */
	.model-stats {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		padding: 1rem 0;
		border-top: 1px solid var(--border-color);
		border-bottom: 1px solid var(--border-color);
	}

	.stat-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--text-secondary);
	}

	.stat-item-icon {
		width: 16px;
		height: 16px;
		color: var(--text-muted);
	}

	/* Model Actions */
	.model-actions {
		display: flex;
		gap: 0.75rem;
	}

	.model-button {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		border-radius: 10px;
		font-weight: 600;
		font-size: 0.875rem;
		cursor: pointer;
		transition: all 0.3s ease;
		border: 1px solid var(--border-color);
	}

	.model-button.primary {
		background: #ffffff;
		color: #000000;
		border: none;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
	}

	.model-button.primary:hover {
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
		background: #00d9ff;
		color: #000000;
	}

	.threat-modeling-container.light .model-button.primary {
		background: #00d9ff;
		color: #000000;
		box-shadow:
			0 10px 30px rgba(0, 217, 255, 0.25),
			0 5px 15px rgba(0, 217, 255, 0.15);
	}

	.threat-modeling-container.light .model-button.primary:hover {
		background: #00b8d4;
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.35),
			0 8px 20px rgba(0, 217, 255, 0.25);
	}

	.model-button.danger {
		background: transparent;
		color: var(--error-color);
		border-color: rgba(239, 68, 68, 0.3);
	}

	.model-button.danger:hover {
		background: rgba(239, 68, 68, 0.1);
		border-color: var(--error-color);
		transform: translateY(-2px);
		box-shadow: 0 4px 15px rgba(239, 68, 68, 0.2);
	}

	.btn-icon {
		width: 18px;
		height: 18px;
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

	.threat-modeling-container.light .modal-backdrop {
		background: rgba(0, 0, 0, 0.3);
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
		border: 1px solid var(--border-color);
		border-radius: 16px;
		backdrop-filter: blur(10px);
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
		width: 100%;
		max-width: 500px;
		max-height: 90vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		animation: modalSlideIn 0.3s ease;
	}

	.threat-modeling-container.light .modal-container {
		background: rgba(0, 0, 0, 0.95);
		border: 1px solid rgba(0, 217, 255, 0.35);
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
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
		color: var(--text-primary);
		margin: 0;
		color: #ffffff;
	}

	.threat-modeling-container.light .modal-title {
		color: #ffffff;
	}

	.modal-subtitle {
		font-size: 0.875rem;
		color: var(--text-muted);
		margin-top: 0.25rem;
		color: rgba(255, 255, 255, 0.8);
	}

	.threat-modeling-container.light .modal-subtitle {
		color: rgba(255, 255, 255, 0.8);
	}

	.modal-close {
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.2);
		color: var(--error-color);
		padding: 0.5rem;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.3s ease;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.modal-close:hover {
		background: rgba(239, 68, 68, 0.2);
		transform: rotate(90deg);
	}

	.modal-close svg {
		width: 20px;
		height: 20px;
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
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	:global(.threat-modeling-container.light) .form-label {
		color: #ffffff !important;
	}

	.form-input {
		width: 100%;
		padding: 0.875rem 1rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid var(--border-color);
		border-radius: 10px;
		color: var(--text-primary);
		font-size: 1rem;
		transition: all 0.3s ease;
		font-family: inherit;
	}

	/* Light mode: All form inputs white text */
	:global(.threat-modeling-container.light) .form-input {
		color: #ffffff !important;
	}

	/* Light mode: Select dropdown also white text */
	:global(.threat-modeling-container.light) select.form-input {
		color: #ffffff !important;
	}

	/* Dark mode: Select dropdown black text on white background */
	:global(.threat-modeling-container.dark) select.form-input {
		background: #ffffff !important;
		color: #000000 !important;
	}

	:global(.threat-modeling-container.dark) select.form-input option {
		background: #ffffff !important;
		color: #000000 !important;
	}

	.form-input:focus {
		outline: none;
		border-color: var(--primary-color);
		background: rgba(0, 217, 255, 0.1);
		box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1);
	}

	/* Light mode: Focus state */
	:global(.threat-modeling-container.light) .form-input:focus {
		background: rgba(0, 217, 255, 0.1) !important;
	}

	/* Dark mode: Keep white background when select is focused */
	:global(.threat-modeling-container.dark) select.form-input:focus {
		background: #ffffff !important;
		color: #000000 !important;
	}

	.form-input::placeholder {
		color: var(--text-muted);
	}

	:global(.threat-modeling-container.light) .form-input::placeholder {
		color: rgba(255, 255, 255, 0.6) !important;
	}

	.info-box {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 1rem;
		background: rgba(0, 217, 255, 0.05);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 8px;
	}

	.info-icon {
		width: 20px;
		height: 20px;
		color: var(--primary-color);
		flex-shrink: 0;
		margin-top: 2px;
	}

	.info-text {
		font-size: 0.875rem;
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.5;
	}

	.threat-modeling-container.light .info-text {
		color: rgba(255, 255, 255, 0.8);
	}

	.threat-modeling-container.light .info-text {
		color: rgba(255, 255, 255, 0.8);
	}

	.modal-footer {
		padding: 1.5rem 2rem;
		border-top: 1px solid var(--border-color);
		display: flex;
		gap: 1rem;
		justify-content: flex-end;
	}

	.btn-primary,
	.btn-secondary,
	.btn-danger {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.875rem 1.5rem;
		border-radius: 10px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		font-size: 0.95rem;
		border: none;
	}

	.btn-primary {
		background: #ffffff;
		color: #000000;
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

	.threat-modeling-container.light .btn-primary {
		background: #00d9ff;
		color: #000000;
		box-shadow:
			0 10px 30px rgba(0, 217, 255, 0.25),
			0 5px 15px rgba(0, 217, 255, 0.15);
	}

	.threat-modeling-container.light .btn-primary:hover:not(:disabled) {
		background: #00b8d4;
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.35),
			0 8px 20px rgba(0, 217, 255, 0.25);
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

	.btn-secondary:hover:not(:disabled) {
		background: #00d9ff;
		color: #000000;
		transform: translateY(-3px);
		border-color: #00d9ff;
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.5),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}

	.threat-modeling-container.light .btn-secondary {
		background: rgba(255, 255, 255, 0.9);
		color: #00d9ff;
		border: 2px solid #00d9ff;
		box-shadow:
			0 10px 30px rgba(0, 217, 255, 0.15),
			0 0 20px rgba(0, 217, 255, 0.1);
	}

	.threat-modeling-container.light .btn-secondary:hover:not(:disabled) {
		background: #00d9ff;
		color: #000000;
	}

	.btn-danger {
		background: rgba(239, 68, 68, 0.1);
		color: var(--error-color);
		border: 1px solid rgba(239, 68, 68, 0.3);
	}

	.btn-danger:hover {
		background: rgba(239, 68, 68, 0.2);
		border-color: var(--error-color);
		transform: translateY(-2px);
		box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
	}

	.animate-spin {
		animation: spin 1s linear infinite;
	}

	/* Delete Warning */
	.delete-warning {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.warning-icon {
		width: 64px;
		height: 64px;
		margin: 0 auto;
		background: rgba(239, 68, 68, 0.1);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid rgba(239, 68, 68, 0.2);
	}

	.warning-icon svg {
		width: 32px;
		height: 32px;
		color: var(--error-color);
	}

	.warning-content {
		text-align: center;
	}

	.warning-title {
		font-size: 0.875rem;
		color: var(--text-secondary);
		margin-bottom: 0.5rem;
	}

	.warning-model-name {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 1rem;
	}

	.warning-details {
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.2);
		border-radius: 10px;
		padding: 1rem;
		text-align: left;
	}

	.warning-subtitle {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--error-color);
		margin-bottom: 0.5rem;
	}

	.warning-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.warning-list li {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.8;
	}

	/* Notification Toast */
	.notification {
		position: fixed;
		bottom: 2rem;
		right: 2rem;
		padding: 1rem 1.5rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border-color);
		border-radius: 8px;
		box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
		color: var(--text-primary);
		font-weight: 500;
		z-index: 10000;
		animation:
			slideInRight 0.3s ease,
			fadeOut 0.3s ease 2.7s;
		max-width: 400px;
	}

	.notification.success {
		border-left: 4px solid var(--success-color);
	}

	.notification.error {
		border-left: 4px solid var(--error-color);
	}

	@keyframes slideInRight {
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
		from {
			opacity: 1;
		}
		to {
			opacity: 0;
		}
	}

	/* Responsive Design */
	@media (max-width: 1024px) {
		.models-grid {
			grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		}
	}

	@media (max-width: 768px) {
		.navbar-content {
			padding: 0 1rem;
		}

		.breadcrumb {
			display: none;
		}

		.brand-name {
			font-size: 1.25rem;
		}

		.left-sidebar {
			position: relative;
			width: 100%;
			height: auto;
			top: 0;
			border-right: none;
			border-bottom: 1px solid var(--border-color);
		}

		.main-content {
			margin-left: 0;
			padding: 1rem;
		}

		.models-grid {
			grid-template-columns: 1fr;
		}

		.modal-container {
			max-width: 100%;
			margin: 1rem;
		}

		.empty-actions {
			flex-direction: column;
		}

		.empty-button {
			width: 100%;
			justify-content: center;
		}

		.notification {
			bottom: 1rem;
			right: 1rem;
			left: 1rem;
			max-width: none;
		}
	}
</style>
