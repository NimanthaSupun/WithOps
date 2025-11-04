<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { githubClient } from '$lib/github.js';
    
    let loading = true;
    let error = null;
    let message = 'Processing GitHub App installation...';
    let installationResult = null;

    onMount(async () => {
        await handleInstallationCallback();
    });

    async function handleInstallationCallback() {
        try {
            loading = true;
            error = null;
            
            // Get URL parameters from GitHub App installation redirect
            const params = $page.url.searchParams;
            const installation_id = params.get('installation_id');
            const setup_action = params.get('setup_action');
            const state = params.get('state');
            
            console.log('GitHub App installation callback params:', { 
                installation_id,
                setup_action,
                state
            });

            if (installation_id && setup_action) {
                message = 'Completing GitHub App installation...';
                
                const result = await githubClient.processInstallationCallback(
                    installation_id, 
                    setup_action, 
                    state
                );
                
                if (result.success) {
                    installationResult = result;
                    message = `✅ GitHub App successfully installed in ${result.organization.login}!`;
                    loading = false;
                    
                    // Immediately start prefetching workspace data for instant access
                    console.log('🚀 Prefetching workspace data for instant navigation');
                    githubClient.preloadOrganizationWorkspace(result.organization.login);
                    
                    // Reduce redirect delay since workspace is being prefetched
                    setTimeout(() => {
                        goto(`/github/workspace/${result.organization.login}`);
                    }, 1500); // Reduced from 2000ms
                } else {
                    throw new Error(result.error);
                }
            } else {
                throw new Error('Missing required parameters from GitHub App installation');
            }
            
        } catch (err) {
            console.error('Installation callback error:', err);
            error = err.message || 'Failed to process GitHub App installation';
            loading = false;
        }
    }

    function goBack() {
        goto('/');
    }
</script>

<svelte:head>
    <title>GitHub App Installation - WithOps</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 flex items-center justify-center px-4">
    <div class="max-w-md w-full space-y-8">
        <div class="text-center">
            <h1 class="text-3xl font-bold text-gray-900">GitHub App Installation</h1>
            <p class="mt-2 text-gray-600">Setting up your organization workspace...</p>
        </div>

        <div class="bg-white shadow rounded-lg p-6">
            {#if loading}
                <div class="text-center">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p class="text-lg font-medium text-gray-900">{message}</p>
                    <p class="text-sm text-gray-500 mt-2">Please wait while we configure your workspace...</p>
                </div>
            {:else if error}
                <div class="text-center">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                        <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">Installation Failed</h3>
                    <p class="text-sm text-red-600 mb-4">{error}</p>
                    <button 
                        on:click={goBack}
                        class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                    >
                        Go Back to Dashboard
                    </button>
                </div>
            {:else if installationResult}
                <div class="text-center">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                        <svg class="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">Installation Successful!</h3>
                    <p class="text-sm text-gray-600 mb-4">{message}</p>
                    
                    <div class="bg-gray-50 rounded-lg p-4 mb-4">
                        <div class="flex items-center space-x-3">
                            <img 
                                src={installationResult.organization.avatar_url} 
                                alt={installationResult.organization.login}
                                class="h-10 w-10 rounded-full"
                            />
                            <div class="text-left">
                                <p class="font-medium text-gray-900">{installationResult.organization.login}</p>
                                <p class="text-sm text-gray-500">Installation ID: {installationResult.installation_id}</p>
                            </div>
                        </div>
                    </div>
                    
                    <p class="text-sm text-gray-500">Redirecting to your organization workspace...</p>
                </div>
            {/if}
        </div>
    </div>
</div>
