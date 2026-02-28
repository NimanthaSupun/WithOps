<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isDarkMode } from '$lib/stores.js';

	const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

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

			const response = await fetch(`${API_BASE_URL}/api/github/workspace/${orgName}`, {
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

			const response = await fetch(`${API_BASE_URL}/api/threat-modeling/models`, {
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

			const response = await fetch(`${API_BASE_URL}/api/threat-modeling/dashboard`, {
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

			const response = await fetch(`${API_BASE_URL}/api/threat-modeling/models`, {
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
				`${API_BASE_URL}/api/threat-modeling/models/${modelToDelete.id}`,
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

			const response = await fetch(`${API_BASE_URL}/api/threat-modeling/models`, {
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

<div class="threat-page {darkMode ? 'dark' : 'light'}">
	<!-- Header Navigation -->
	<nav class="dashboard-header">
		<div class="header-content">
			<a href="/" class="nav-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
				<span class="brand-name">WithOps</span>
			</a>

			<div class="nav-menu">
				<a href="/dashboard" class="nav-link">Overview</a>
				<a href="/organizations" class="nav-link">Organizations</a>
				<a href="/github/workspace/{orgName}" class="nav-link">{orgName}</a>
				<a href="/github/workspace/{orgName}/threat-modeling" class="nav-link active"
					>Threat Modeling</a
				>
			</div>

			<div class="nav-actions">
				<button onclick={toggleTheme} class="theme-toggle" title="Toggle theme">
					{#if darkMode}
						<svg
							class="theme-icon"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							stroke-width="2"
						>
							<circle cx="12" cy="12" r="5" /><path
								d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
							/>
						</svg>
					{:else}
						<svg
							class="theme-icon"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
						</svg>
					{/if}
				</button>
			</div>
		</div>
	</nav>

	<!-- Technical Breadcrumb Bar -->
	<div class="technical-bar">
		<div class="breadcrumb">
			<span class="breadcrumb-item">WithOps</span>
			<span class="breadcrumb-sep">/</span>
			<span class="breadcrumb-item">{orgName}</span>
			<span class="breadcrumb-sep">/</span>
			<span class="breadcrumb-item active">Threat Modeling</span>
		</div>
		<div class="system-status">
			<div class="status-pulse"></div>
			THREAT ENGINE: ACTIVE
		</div>
	</div>

	<div class="page-layout">
		<!-- Sidebar -->
		<aside class="sidebar">
			<button
				onclick={() => goto(`/github/workspace/${orgName}`)}
				class="btn btn-outline btn-full btn-sm"
			>
				<svg
					width="14"
					height="14"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					stroke-width="2"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
				</svg>
				Back to Workspace
			</button>

			<!-- Stats -->
			<div class="sidebar-section">
				<h4 class="section-label">STATISTICS</h4>
				<div class="stats-grid">
					<div class="stat-cell">
						<span class="stat-val">{dashboardData?.statistics.total_threat_models || 0}</span>
						<span class="stat-lbl">Models</span>
					</div>
					<div class="stat-cell">
						<span class="stat-val">{dashboardData?.statistics.user_threat_models || 0}</span>
						<span class="stat-lbl">Yours</span>
					</div>
					<div class="stat-cell">
						<span class="stat-val">{dashboardData?.statistics.total_assessments || 0}</span>
						<span class="stat-lbl">Assessments</span>
					</div>
					<div class="stat-cell">
						<span class="stat-val">{dashboardData?.statistics.recent_models || 0}</span>
						<span class="stat-lbl">Recent (7d)</span>
					</div>
				</div>
			</div>

			<!-- Actions -->
			<div class="sidebar-section">
				<h4 class="section-label">ACTIONS</h4>
				<div class="sidebar-actions">
					<button onclick={openCreateModal} class="btn btn-primary btn-full btn-sm">
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
						</svg>
						New Model
					</button>
					<button
						onclick={triggerImport}
						class="btn btn-secondary btn-full btn-sm"
						disabled={importing}
					>
						<svg
							width="14"
							height="14"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="2"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
							/>
						</svg>
						{#if importing}Importing...{:else}Import JSON{/if}
					</button>
				</div>
			</div>
		</aside>

		<!-- Main Content -->
		<main class="page-main">
			{#if loading}
				<div class="center-state">
					<img src="/icons/excellence_17274210.png" alt="" class="loader-icon" />
					<div class="loader-text">SCANNING THREAT MODELS...</div>
				</div>
			{:else}
				<!-- Content States -->
				{#if error}
					<div class="empty-view">
						<p class="error-text">{error}</p>
						<button onclick={loadThreatModels} class="btn btn-primary">Retry Connection</button>
					</div>
				{:else if threatModels.length === 0}
					<div class="empty-view">
						<svg
							class="empty-icon"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							stroke-width="1.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
							/>
						</svg>
						<h3>No threat models yet</h3>
						<p>Create your first threat model or import an existing one to get started.</p>
						<div class="empty-actions">
							<button onclick={openCreateModal} class="btn btn-primary">
								Create Your First Model
								<span class="button-arrow">→</span>
							</button>
							<button onclick={triggerImport} class="btn btn-secondary">Import JSON</button>
						</div>
					</div>
				{:else}
					<!-- Models Grid -->
					<div class="models-grid">
						{#each threatModels as model}
							<div class="model-card">
								<div class="model-card-top">
									<div class="model-meta">
										<h3 class="model-name">{model.name}</h3>
										{#if model.description}
											<p class="model-desc">{model.description}</p>
										{/if}
									</div>
									<div class="model-badges">
										<span class="tag methodology {model.methodology.toLowerCase()}"
											>{model.methodology}</span
										>
										<span class="tag status {model.status}">{model.status}</span>
									</div>
								</div>

								<div class="model-stats-row">
									<div class="m-stat">
										<span class="m-stat-label">Elements</span>
										<span class="m-stat-value">{model.element_count || 0}</span>
									</div>
									<div class="m-stat">
										<span class="m-stat-label">Threats</span>
										<span class="m-stat-value">{model.assessment_count || 0}</span>
									</div>
									<div class="m-stat">
										<span class="m-stat-label">Created</span>
										<span class="m-stat-value">{formatDate(model.created_at)}</span>
									</div>
								</div>

								<div class="model-actions">
									<button
										onclick={() => goto(`/github/workspace/${orgName}/threat-modeling/${model.id}`)}
										class="btn btn-primary btn-full"
									>
										<span>Open Canvas</span>
										<span class="button-arrow">→</span>
									</button>
									<button
										onclick={() => confirmDeleteThreatModel(model)}
										class="btn btn-outline btn-icon-only"
										title="Delete threat model"
										aria-label="Delete threat model"
									>
										<svg
											width="14"
											height="14"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
										>
											<path
												d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
											/>
										</svg>
									</button>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			{/if}
		</main>
	</div>
</div>

<!-- Notification Toast -->
{#if showNotificationFlag}
	<div class="toast {notificationType}">
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
			class="modal-container {darkMode ? 'dark' : 'light'}"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title">Create New Threat Model</h3>
					<p class="modal-subtitle">Define your security threat analysis scope</p>
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
					<label for="modelName" class="form-label">Model Name *</label>
					<input
						id="modelName"
						type="text"
						bind:value={newModelName}
						placeholder="e.g., API Security Model"
						class="form-input"
						onkeypress={(e) => e.key === 'Enter' && createThreatModel()}
					/>
				</div>

				<div class="form-group">
					<label for="modelDescription" class="form-label">Description</label>
					<textarea
						id="modelDescription"
						bind:value={newModelDescription}
						rows="3"
						placeholder="Brief description of what this threat model covers..."
						class="form-input"
					></textarea>
				</div>

				<div class="form-group">
					<label for="methodology" class="form-label">Methodology</label>
					<select id="methodology" bind:value={newModelMethodology} class="form-input">
						<option value="STRIDE"
							>STRIDE - Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation</option
						>
						<option value="LINDDUN">LINDDUN - Privacy-focused threat modeling</option>
						<option value="CIA">CIA Triad - Confidentiality, Integrity, Availability</option>
						<option value="CUSTOM">Custom - Define your own methodology</option>
					</select>
				</div>

				<div class="info-box">
					<svg
						class="info-icon"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						stroke-width="2"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
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
				<button onclick={closeCreateModal} class="btn btn-secondary" disabled={creating}
					>Cancel</button
				>
				<button
					onclick={createThreatModel}
					disabled={creating || !newModelName.trim()}
					class="btn btn-primary"
				>
					{#if creating}
						<span class="btn-spinner"></span>
						Creating...
					{:else}
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
			class="modal-container {darkMode ? 'dark' : 'light'}"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="modal-header">
				<div>
					<h3 class="modal-title">Delete Threat Model</h3>
					<p class="modal-subtitle">This action cannot be undone</p>
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
					<div class="warning-icon-wrap">
						<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
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
								<li>The threat model and all its data</li>
								<li>All threat assessments ({modelToDelete.assessment_count || 0} threats)</li>
								<li>All canvas diagrams and components</li>
								<li>All analysis results and history</li>
							</ul>
						</div>
					</div>
				</div>
			</div>

			<div class="modal-footer">
				<button onclick={cancelDelete} class="btn btn-secondary">Cancel</button>
				<button onclick={deleteThreatModel} class="btn btn-danger">
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path
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
	/* ============================================
	   PROFESSIONAL DESIGN SYSTEM (MATTE ENGINEERING)
	   ============================================ */
	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
		--nav-height: 64px;
	}

	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	/* ---- Theme Variables ---- */
	.threat-page.dark {
		--bg-app: #000000;
		--bg-surface: #020202;
		--bg-surface-alt: #050505;
		--border: rgba(255, 255, 255, 0.03);
		--border-focus: rgba(255, 255, 255, 0.08);
		--text-primary: #f8fafc;
		--text-secondary: #94a3b8;
		--text-muted: #475569;
		--accent: #00adef;
		--accent-soft: rgba(0, 173, 239, 0.05);
		--success: #10b981;
		--error: #ef4444;
		--card-shadow: none;
	}

	.threat-page.light {
		--bg-app: #ffffff;
		--bg-surface: #f8fafc;
		--bg-surface-alt: #f1f5f9;
		--border: rgba(0, 0, 0, 0.06);
		--border-focus: rgba(0, 173, 239, 0.2);
		--text-primary: #0f172a;
		--text-secondary: #475569;
		--text-muted: #94a3b8;
		--accent: #0082b4;
		--accent-soft: rgba(0, 130, 180, 0.08);
		--success: #059669;
		--error: #dc2626;
		--card-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
	}

	.threat-page {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		transition: background 0.3s ease;
		position: relative;
		overflow-x: hidden;
	}

	/* Blueprint Grid Backdrop */
	.threat-page::before {
		content: '';
		position: fixed;
		inset: 0;
		background-image:
			linear-gradient(var(--border) 1px, transparent 1px),
			linear-gradient(90deg, var(--border) 1px, transparent 1px);
		background-size: 40px 40px;
		mask-image: radial-gradient(circle at 50% 50%, black, transparent 80%);
		pointer-events: none;
		z-index: 0;
		opacity: 0.5;
	}

	/* ---- Layout ---- */
	.page-layout {
		display: flex;
		max-width: 1440px;
		margin: 0 auto;
		padding: 0 2rem;
		gap: 2rem;
		position: relative;
		z-index: 10;
	}

	/* ---- Sidebar ---- */
	.sidebar {
		width: 240px;
		flex-shrink: 0;
		padding: 1.5rem 0;
		position: sticky;
		top: calc(var(--nav-height) + 40px);
		height: fit-content;
		max-height: calc(100vh - var(--nav-height) - 40px);
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.sidebar-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.section-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.5rem;
	}

	.stat-cell {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.625rem 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}
	.stat-val {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
		color: var(--text-primary);
	}
	.stat-lbl {
		font-size: 0.6rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.sidebar-actions {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	/* ---- Loading (center-state) ---- */
	.center-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 6rem 2rem;
		text-align: center;
		gap: 1rem;
	}
	.loader-icon {
		width: 40px;
		height: 40px;
		animation: pulse 2s ease-in-out infinite;
	}
	@keyframes pulse {
		0%,
		100% {
			opacity: 0.5;
			transform: scale(0.95);
		}
		50% {
			opacity: 1;
			transform: scale(1);
		}
	}
	.loader-text {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
	}

	/* ---- Header Navigation ---- */
	.dashboard-header {
		height: var(--nav-height);
		background: rgba(var(--bg-app), 0.8);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		position: sticky;
		top: 0;
		z-index: 100;
	}
	.header-content {
		max-width: 1440px;
		width: 100%;
		margin: 0 auto;
		padding: 0 2rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		text-decoration: none;
		color: var(--text-primary);
	}
	.brand-icon {
		width: 28px;
		height: 28px;
	}
	.brand-name {
		font-weight: 700;
		font-size: 1rem;
		letter-spacing: -0.02em;
	}
	.nav-menu {
		display: flex;
		gap: 1.5rem;
		margin-left: 3rem;
	}
	.nav-link {
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
		padding: 0.5rem 0;
		position: relative;
	}
	.nav-link:hover,
	.nav-link.active {
		color: var(--text-primary);
	}
	.nav-link.active::after {
		content: '';
		position: absolute;
		bottom: -1px;
		left: 0;
		right: 0;
		height: 2px;
		background: var(--accent);
	}
	.nav-actions {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}
	.theme-toggle {
		background: none;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 8px;
		transition: all 0.15s;
		display: flex;
	}
	.theme-toggle:hover {
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		border-color: var(--border-focus);
	}
	.theme-icon {
		width: 18px;
		height: 18px;
	}

	/* ---- Technical Bar ---- */
	.technical-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 0 2rem;
		display: flex;
		align-items: center;
		height: 40px;
	}
	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.breadcrumb-sep {
		color: var(--border-focus);
	}
	.breadcrumb-item.active {
		color: var(--accent);
	}
	.system-status {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--success);
		opacity: 0.8;
	}
	.status-pulse {
		width: 4px;
		height: 4px;
		background: currentColor;
		border-radius: 50%;
		animation: blink 2s infinite;
	}
	@keyframes blink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.3;
		}
	}

	/* ---- Main Content ---- */
	.page-main {
		flex: 1;
		min-width: 0;
		padding: 1.5rem 0;
	}

	/* View Header */
	.view-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		margin-bottom: 2rem;
	}
	/* Empty / Error View */
	.empty-view {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 8rem 2rem;
		text-align: center;
		gap: 1rem;
	}
	.empty-view h3 {
		font-size: 1.25rem;
		font-weight: 700;
	}
	.empty-view p {
		color: var(--text-secondary);
		font-size: 0.875rem;
		max-width: 400px;
		line-height: 1.5;
	}
	.empty-icon {
		width: 48px;
		height: 48px;
		color: var(--text-muted);
		margin-bottom: 0.5rem;
	}
	.empty-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: 1rem;
	}
	.error-text {
		color: var(--error);
		font-size: 0.875rem;
		max-width: 400px;
	}

	/* ---- Models Grid ---- */
	.models-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
		gap: 1.5rem;
	}

	.model-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		transition: all 0.2s var(--ease-premium);
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		box-shadow: var(--card-shadow);
	}
	.model-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-2px);
		box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
	}

	.model-card-top {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.model-name {
		font-weight: 700;
		font-size: 1rem;
		margin-bottom: 0.25rem;
	}
	.model-desc {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}
	.model-badges {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	/* Tags / Badges */
	.tag {
		display: inline-flex;
		align-items: center;
		padding: 0.25rem 0.625rem;
		border-radius: 6px;
		font-size: 0.6875rem;
		font-weight: 600;
		font-family: var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border: 1px solid;
	}
	.tag.methodology.stride {
		color: var(--accent);
		border-color: rgba(0, 173, 239, 0.15);
	}
	.tag.methodology.linddun {
		color: #8b5cf6;
		border-color: rgba(139, 92, 246, 0.15);
	}
	.tag.methodology.cia {
		color: #ec4899;
		border-color: rgba(236, 72, 153, 0.15);
	}
	.tag.methodology.custom {
		color: var(--text-muted);
		border-color: var(--border);
	}
	.tag.status.draft {
		color: #f59e0b;
		border-color: rgba(245, 158, 11, 0.15);
	}
	.tag.status.review {
		color: #ec4899;
		border-color: rgba(236, 72, 153, 0.15);
	}
	.tag.status.approved {
		color: var(--success);
		border-color: rgba(16, 185, 129, 0.15);
	}
	.tag.status.archived {
		color: var(--text-muted);
		border-color: var(--border);
	}

	/* Model Stats Row */
	.model-stats-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1rem;
		padding: 0.875rem 0;
		border-top: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
	}
	.m-stat {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}
	.m-stat-label {
		font-size: 0.6rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.m-stat-value {
		font-family: var(--font-mono);
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	/* Model Actions */
	.model-actions {
		display: flex;
		gap: 0.5rem;
	}

	/* ---- Buttons ---- */
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.6875rem 1.125rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
		font-family: var(--font-sans);
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--text-primary);
		white-space: nowrap;
	}
	.btn:hover:not(:disabled) {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
		transform: translateY(-1px);
	}
	.btn-primary {
		background: var(--text-primary);
		color: var(--bg-app);
		border-color: var(--text-primary);
	}
	.btn-primary:hover:not(:disabled) {
		opacity: 0.9;
		transform: translateY(-1px);
	}
	.btn-primary:disabled {
		opacity: 0.4;
		cursor: not-allowed;
		transform: none;
	}
	.btn-secondary {
		background: var(--bg-surface-alt);
		border-color: var(--border);
		color: var(--text-primary);
	}
	.btn-outline {
		background: transparent;
		border-color: var(--border);
		color: var(--text-secondary);
	}
	.btn-outline:hover:not(:disabled) {
		border-color: var(--border-focus);
		color: var(--text-primary);
		background: var(--bg-surface-alt);
		transform: translateY(-1px);
	}
	.btn-danger {
		background: rgba(239, 68, 68, 0.08);
		border-color: rgba(239, 68, 68, 0.15);
		color: var(--error);
	}
	.btn-danger:hover:not(:disabled) {
		background: rgba(239, 68, 68, 0.15);
		border-color: var(--error);
		transform: translateY(-1px);
	}
	.btn-full {
		width: 100%;
	}
	.btn-sm {
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
	}
	.btn-icon-only {
		padding: 0.6875rem;
		flex-shrink: 0;
	}

	.button-arrow {
		font-size: 1.1rem;
		transition: transform 0.2s var(--ease-premium);
	}
	.btn:hover .button-arrow {
		transform: translateX(4px);
	}

	.btn-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ---- Modal ---- */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 9999;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(6px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		animation: fadeIn 0.15s ease;
	}
	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.modal-container {
		background: var(--bg-surface, #f8fafc);
		border: 1px solid var(--border, rgba(0, 0, 0, 0.06));
		border-radius: 12px;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
		width: 100%;
		max-width: 480px;
		max-height: 90vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		animation: modalIn 0.2s var(--ease-premium);
	}
	.modal-container.dark {
		--bg-surface: #020202;
		--bg-surface-alt: #050505;
		--border: rgba(255, 255, 255, 0.03);
		--border-focus: rgba(255, 255, 255, 0.08);
		--text-primary: #f8fafc;
		--text-secondary: #94a3b8;
		--text-muted: #475569;
		--accent: #00adef;
		--error: #ef4444;
	}
	.modal-container.light {
		--bg-surface: #f8fafc;
		--bg-surface-alt: #f1f5f9;
		--border: rgba(0, 0, 0, 0.06);
		--border-focus: rgba(0, 173, 239, 0.2);
		--text-primary: #0f172a;
		--text-secondary: #475569;
		--text-muted: #94a3b8;
		--accent: #0082b4;
		--error: #dc2626;
	}
	@keyframes modalIn {
		from {
			opacity: 0;
			transform: translateY(-12px) scale(0.97);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.modal-header {
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.modal-title {
		font-size: 1.125rem;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0;
	}
	.modal-subtitle {
		font-size: 0.75rem;
		color: var(--text-muted);
		margin-top: 0.125rem;
	}
	.modal-close {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-muted);
		padding: 0.375rem;
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.15s;
		display: flex;
	}
	.modal-close:hover {
		border-color: var(--error);
		color: var(--error);
		background: rgba(239, 68, 68, 0.06);
	}
	.modal-close svg {
		width: 16px;
		height: 16px;
	}

	.modal-body {
		padding: 1.5rem;
		overflow-y: auto;
		flex: 1;
	}
	.form-group {
		margin-bottom: 1.25rem;
	}
	.form-label {
		display: block;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-secondary);
		margin-bottom: 0.375rem;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}
	.form-input {
		width: 100%;
		padding: 0.625rem 0.875rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		color: var(--text-primary);
		font-size: 0.875rem;
		transition: border-color 0.15s;
		font-family: var(--font-sans);
	}
	.form-input:focus {
		outline: none;
		border-color: var(--accent);
	}
	.form-input::placeholder {
		color: var(--text-muted);
	}
	select.form-input {
		cursor: pointer;
	}

	.info-box {
		display: flex;
		align-items: flex-start;
		gap: 0.625rem;
		padding: 0.75rem;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
	}
	.info-icon {
		width: 16px;
		height: 16px;
		color: var(--accent);
		flex-shrink: 0;
		margin-top: 1px;
	}
	.info-text {
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.5;
	}

	.modal-footer {
		padding: 1rem 1.5rem;
		border-top: 1px solid var(--border);
		display: flex;
		gap: 0.75rem;
		justify-content: flex-end;
	}

	/* ---- Delete Warning ---- */
	.delete-warning {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		align-items: center;
	}
	.warning-icon-wrap {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		background: rgba(239, 68, 68, 0.08);
		border: 1px solid rgba(239, 68, 68, 0.12);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.warning-icon-wrap svg {
		width: 24px;
		height: 24px;
		color: var(--error);
	}
	.warning-content {
		text-align: center;
	}
	.warning-title {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		margin-bottom: 0.375rem;
	}
	.warning-model-name {
		font-size: 1rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 1rem;
	}
	.warning-details {
		background: rgba(239, 68, 68, 0.05);
		border: 1px solid rgba(239, 68, 68, 0.1);
		border-radius: 8px;
		padding: 0.875rem;
		text-align: left;
	}
	.warning-subtitle {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--error);
		margin-bottom: 0.375rem;
	}
	.warning-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.warning-list li {
		font-size: 0.8125rem;
		color: var(--text-secondary);
		line-height: 1.7;
		padding-left: 0.75rem;
		position: relative;
	}
	.warning-list li::before {
		content: '';
		width: 3px;
		height: 3px;
		background: var(--text-muted);
		border-radius: 50%;
		position: absolute;
		left: 0;
		top: 0.6em;
	}

	/* ---- Notification Toast ---- */
	.toast {
		position: fixed;
		bottom: 2rem;
		right: 2rem;
		padding: 0.75rem 1.25rem;
		background: var(--bg-surface, #020202);
		border: 1px solid var(--border, rgba(255, 255, 255, 0.03));
		border-radius: 8px;
		box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
		color: var(--text-primary, #f8fafc);
		font-size: 0.8125rem;
		font-weight: 500;
		z-index: 10000;
		animation: slideInRight 0.25s ease;
		max-width: 380px;
	}
	.toast.success {
		border-left: 3px solid var(--success, #10b981);
	}
	.toast.error {
		border-left: 3px solid var(--error, #ef4444);
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

	/* ---- Responsive ---- */
	@media (max-width: 1024px) {
		.page-layout {
			flex-direction: column;
		}
		.sidebar {
			width: 100%;
			position: relative;
			top: 0;
			max-height: none;
		}
		.stats-grid {
			grid-template-columns: repeat(4, 1fr);
		}
		.models-grid {
			grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		}
	}
	@media (max-width: 768px) {
		.view-header {
			flex-direction: column;
			align-items: flex-start;
			gap: 1.5rem;
		}
		.nav-menu {
			display: none;
		}
		.page-layout {
			padding: 0 1rem;
		}
		.models-grid {
			grid-template-columns: 1fr;
		}
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}
		.empty-actions {
			flex-direction: column;
			width: 100%;
		}
		.empty-actions .btn {
			width: 100%;
		}
		.modal-container {
			max-width: 100%;
		}
		.toast {
			bottom: 1rem;
			right: 1rem;
			left: 1rem;
			max-width: none;
		}
	}
</style>
