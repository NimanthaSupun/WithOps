<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { githubClient } from '$lib/github.js';

	let loading = true;
	let error = null;
	let message = 'Processing GitHub callback...';
	let organizations = [];
	let selectedOrg = null;
	let installingApp = false;

	onMount(async () => {
		await handleGitHubCallback();
	});

	async function handleGitHubCallback() {
		try {
			loading = true;
			error = null;

			// Get URL parameters from GitHub redirect
			const params = $page.url.searchParams;
			const code = params.get('code');
			const state = params.get('state');
			const installation_id = params.get('installation_id');
			const setup_action = params.get('setup_action');

			console.log('GitHub callback params:', {
				code: code ? 'present' : 'missing',
				state: state,
				installation_id,
				setup_action
			});

			if (installation_id && setup_action) {
				// This is a GitHub App installation callback
				message = 'Processing GitHub App installation...';

				const result = await githubClient.processInstallationCallback(
					installation_id,
					setup_action,
					state
				);

				if (result.success) {
					message = `🎉 Successfully connected to ${result.organization.login}!`;

					// Auto-redirect after 3 seconds to let user see success message
					setTimeout(() => {
						goto(`/organizations`);
					}, 3000);
				} else {
					throw new Error(result.error);
				}
			} else if (code && state) {
				// This is OAuth callback for organization discovery
				message = 'Discovering your GitHub organizations...';

				const result = await githubClient.processOrganizationCallback(code, state);

				if (result.success) {
					organizations = result.organizations;
					message = `Found ${result.total_count} organizations where you can install the app`;
				} else {
					throw new Error(result.error);
				}
			} else {
				throw new Error('Missing required parameters from GitHub');
			}
		} catch (err) {
			console.error('GitHub callback error:', err);
			error = err.message || 'Failed to process GitHub callback';
			message = 'Error occurred during GitHub integration';
		} finally {
			loading = false;
		}
	}

	async function installAppInOrganization(org) {
		try {
			installingApp = true;
			selectedOrg = org;

			const result = await githubClient.generateInstallationUrl(org.login, org.id);

			if (result.success) {
				// Redirect to GitHub App installation page
				window.location.href = result.installation_url;
			} else {
				throw new Error(result.error);
			}
		} catch (err) {
			console.error('App installation error:', err);
			error = err.message || 'Failed to start app installation';
			installingApp = false;
		}
	}

	function goToDashboard() {
		goto('/');
	}
</script>

<svelte:head>
	<title>GitHub Integration - WithOps</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-gray-50">
	<div class="mx-4 w-full max-w-2xl">
		{#if loading}
			<div class="rounded-lg bg-white p-8 text-center shadow-lg">
				<div
					class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"
				></div>
				<h2 class="mb-2 text-xl font-semibold text-gray-800">🔗 Connecting GitHub</h2>
				<p class="text-gray-600">{message}</p>
			</div>
		{:else if error}
			<div class="rounded-lg bg-white p-8 text-center shadow-lg">
				<div
					class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100"
				>
					<svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</div>
				<h2 class="mb-2 text-xl font-semibold text-gray-800">Connection Error ❌</h2>
				<p class="mb-6 text-red-600">{error}</p>

				<div class="space-y-3">
					<button
						on:click={handleGitHubCallback}
						class="w-full rounded-lg bg-red-600 px-4 py-2 font-medium text-white hover:bg-red-700"
					>
						Try Again
					</button>
					<button
						on:click={goToDashboard}
						class="w-full rounded-lg bg-gray-600 px-4 py-2 text-white hover:bg-gray-700"
					>
						Back to Dashboard
					</button>
				</div>
			</div>
		{:else if organizations.length > 0}
			<!-- Organization Selection -->
			<div class="rounded-lg bg-white p-8 shadow-lg">
				<h2 class="mb-4 text-2xl font-semibold text-gray-800">🏢 Select Organization</h2>
				<p class="mb-6 text-gray-600">{message}</p>

				<div class="space-y-4">
					{#each organizations as org}
						<div class="rounded-lg border p-4 transition-colors hover:border-blue-500">
							<div class="flex items-center justify-between">
								<div class="flex items-center space-x-3">
									<img
										src={org.avatar_url}
										alt="{org.login} avatar"
										class="h-12 w-12 rounded-full"
									/>
									<div>
										<h3 class="font-semibold text-gray-900">{org.login}</h3>
										<p class="text-sm text-gray-600">
											{org.app_installed ? '✅ App installed' : '📦 App not installed'}
										</p>
									</div>
								</div>

								<div>
									{#if org.app_installed}
										<button
											on:click={() => goto('/organizations')}
											class="rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700"
										>
											View Workspace
										</button>
									{:else}
										<button
											on:click={() => installAppInOrganization(org)}
											disabled={installingApp && selectedOrg?.login === org.login}
											class="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
										>
											{installingApp && selectedOrg?.login === org.login
												? 'Installing...'
												: 'Install App'}
										</button>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>

				<div class="mt-6 text-center">
					<button on:click={goToDashboard} class="text-gray-600 hover:text-gray-800">
						← Back to Dashboard
					</button>
				</div>
			</div>
		{:else}
			<!-- Success Message -->
			<div class="rounded-lg bg-white p-8 text-center shadow-lg">
				<div
					class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100"
				>
					<svg class="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M5 13l4 4L19 7"
						/>
					</svg>
				</div>
				<h2 class="mb-2 text-xl font-semibold text-gray-800">GitHub Integration Complete! ✅</h2>
				<p class="mb-6 text-gray-600">{message}</p>

				<div class="space-y-3">
					<button
						on:click={() => goto('/organizations')}
						class="w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
					>
						View Organizations
					</button>
					<p class="text-xs text-gray-500">Redirecting automatically in a few seconds...</p>
				</div>
			</div>
		{/if}
	</div>
</div>
