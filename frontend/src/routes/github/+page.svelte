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

<div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="max-w-2xl w-full mx-4">
        {#if loading}
            <div class="bg-white rounded-lg shadow-lg p-8 text-center">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <h2 class="text-xl font-semibold text-gray-800 mb-2">🔗 Connecting GitHub</h2>
                <p class="text-gray-600">{message}</p>
            </div>
        {:else if error}
            <div class="bg-white rounded-lg shadow-lg p-8 text-center">
                <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                    <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </div>
                <h2 class="text-xl font-semibold text-gray-800 mb-2">Connection Error ❌</h2>
                <p class="text-red-600 mb-6">{error}</p>
                
                <div class="space-y-3">
                    <button 
                        on:click={handleGitHubCallback}
                        class="w-full bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 font-medium"
                    >
                        Try Again
                    </button>
                    <button 
                        on:click={goToDashboard}
                        class="w-full bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700"
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        {:else if organizations.length > 0}
            <!-- Organization Selection -->
            <div class="bg-white rounded-lg shadow-lg p-8">
                <h2 class="text-2xl font-semibold text-gray-800 mb-4">🏢 Select Organization</h2>
                <p class="text-gray-600 mb-6">{message}</p>
                
                <div class="space-y-4">
                    {#each organizations as org}
                        <div class="border rounded-lg p-4 hover:border-blue-500 transition-colors">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center space-x-3">
                                    <img 
                                        src={org.avatar_url} 
                                        alt="{org.login} avatar" 
                                        class="w-12 h-12 rounded-full"
                                    >
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
                                            class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                                        >
                                            View Workspace
                                        </button>
                                    {:else}
                                        <button 
                                            on:click={() => installAppInOrganization(org)}
                                            disabled={installingApp && selectedOrg?.login === org.login}
                                            class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {installingApp && selectedOrg?.login === org.login ? 'Installing...' : 'Install App'}
                                        </button>
                                    {/if}
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>
                
                <div class="mt-6 text-center">
                    <button 
                        on:click={goToDashboard}
                        class="text-gray-600 hover:text-gray-800"
                    >
                        ← Back to Dashboard
                    </button>
                </div>
            </div>
        {:else}
            <!-- Success Message -->
            <div class="bg-white rounded-lg shadow-lg p-8 text-center">
                <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                    <svg class="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <h2 class="text-xl font-semibold text-gray-800 mb-2">GitHub Integration Complete! ✅</h2>
                <p class="text-gray-600 mb-6">{message}</p>
                
                <div class="space-y-3">
                    <button 
                        on:click={() => goto('/organizations')}
                        class="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
                    >
                        View Organizations
                    </button>
                    <p class="text-xs text-gray-500">Redirecting automatically in a few seconds...</p>
                </div>
            </div>
        {/if}
    </div>
</div>
