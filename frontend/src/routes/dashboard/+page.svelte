<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import { getAuthClient } from '$lib/auth';
    import { githubClient } from '$lib/github.js';
    import { isDarkMode } from '$lib/stores.js';
    
    let user = $state(null);
    let loading = $state(true);
    let dashboardData = $state(null);
    let isGitHubConnected = $state(false);
    let isDiscovering = $state(false);
    let profilePictureError = $state(false);
    let pictureRetryCount = $state(0);
    
    // Subscribe to the global theme store
    let darkMode = $state(false);
    isDarkMode.subscribe(value => {
        darkMode = value;
    });

    // Helper function to get a working profile picture URL
    function getProfilePictureUrl(picture, retryCount = 0) {
        if (!picture) return null;
        
        // If it's a Google profile picture, try different formats
        if (picture.includes('googleusercontent.com')) {
            const baseUrl = picture.split('=')[0];
            
            switch(retryCount) {
                case 0:
                    // Original format with size parameter
                    return `${baseUrl}=s96-c`;
                case 1:
                    // Without size parameter
                    return baseUrl;
                case 2:
                    // With different size
                    return `${baseUrl}=s64-c`;
                default:
                    return picture; // Original as last resort
            }
        }
        
        return picture;
    }

    // Function to handle picture loading errors with retry
    function handlePictureError(e) {
        pictureRetryCount++;
        console.warn(`Profile picture failed to load (attempt ${pictureRetryCount}):`, getProfilePictureUrl(user.picture, pictureRetryCount - 1));
        
        if (pictureRetryCount < 4) {
            // Try again with different URL format
            e.target.src = getProfilePictureUrl(user.picture, pictureRetryCount);
            console.log('Retrying with URL:', e.target.src);
        } else {
            // Give up and show initials
            console.warn('All profile picture attempts failed, showing initials');
            profilePictureError = true;
        }
    }

    onMount(async () => {
        try {
            // Initialize theme
            isDarkMode.init();
            
            const client = await getAuthClient();
            const isAuthenticated = await client.isAuthenticated();
            
            if (!isAuthenticated) {
                // Redirect unauthenticated users to home
                goto('/');
                return;
            }
            
            user = await client.getUser();
            console.log('✅ User authenticated on dashboard:', user.name);
            console.log('👤 User profile data:', $state.snapshot(user)); // Use $state.snapshot for proper logging
            console.log('🖼️ Profile picture URL:', user.picture); // Debug the picture URL specifically
            
            // Reset profile picture error state when user changes
            profilePictureError = false;
            pictureRetryCount = 0;
            
            // Check URL parameters for GitHub OAuth callback
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('github_connected') === 'true') {
                isGitHubConnected = true;
            }
            
            await loadDashboardData();
        } catch (error) {
            console.error('Dashboard auth check failed:', error);
            goto('/');
        } finally {
            loading = false;
        }
    });

    async function loadDashboardData() {
        try {
            const client = await getAuthClient();
            const token = await client.getTokenSilently();
            
            const response = await fetch('http://localhost:8000/api/auth/dashboard', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                dashboardData = await response.json();
                // Check if GitHub is connected based on dashboard data
                if (dashboardData && (dashboardData.github_connected || dashboardData.github_token || dashboardData.organizations)) {
                    isGitHubConnected = true;
                }
            }
            
            // Also check GitHub connection status via dedicated endpoint
            await checkGitHubConnection();
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    async function checkGitHubConnection() {
        try {
            const client = await getAuthClient();
            const token = await client.getTokenSilently();
            
            const response = await fetch('http://localhost:8000/api/github/my-organizations', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                // User is connected if they have any organizations
                isGitHubConnected = data.organizations && data.organizations.length > 0;
                console.log('GitHub connection status:', isGitHubConnected);
                console.log('User organizations:', data.organizations);
            }
        } catch (error) {
            console.error('Failed to check GitHub connection status:', error);
            // Don't throw error, just leave isGitHubConnected as false
        }
    }

    async function logout() {
        const client = await getAuthClient();
        await client.logout({ returnTo: window.location.origin });
    }

    async function connectToGitHub() {
        try {
            const result = await githubClient.startOrganizationDiscovery();
            
            if (result.success) {
                // Redirect to GitHub OAuth for organization discovery
                window.location.href = result.oauth_url;
            } else {
                console.error('Failed to start GitHub connection:', result.error);
                alert('Failed to start GitHub connection. Please try again.');
            }
        } catch (error) {
            console.error('GitHub connection error:', error);
            alert('Failed to connect to GitHub. Please try again.');
        }
    }

    function toggleTheme() {
        isDarkMode.toggle();
    }

    async function connectGitHub() {
        await connectToGitHub();
    }

    async function discoverOrganizations() {
        isDiscovering = true;
        try {
            const result = await githubClient.startOrganizationDiscovery();
            
            if (result.success) {
                // Redirect to GitHub OAuth for organization discovery
                window.location.href = result.oauth_url;
            } else {
                console.error('Failed to start organization discovery:', result.error);
                alert('Failed to start organization discovery. Please try again.');
            }
        } catch (error) {
            console.error('Organization discovery error:', error);
            alert('Failed to discover organizations. Please try again.');
        } finally {
            isDiscovering = false;
        }
    }
</script>

<svelte:head>
    <title>Dashboard - WithOps DevSecOps Platform</title>
</svelte:head>

{#if loading}
    <div class="loading-screen">
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <h2 class="loading-title">WithOps DevSecOps Platform</h2>
            <p class="loading-text">Initializing your secure development environment...</p>
        </div>
    </div>
{:else}
    <div class="dashboard-container {darkMode ? 'dark' : 'light'}">        
        <!-- Enhanced Navigation Header -->
        <nav class="dashboard-header">
            <div class="header-content">
                <!-- Left side - Brand & Navigation -->
                <div class="header-left">
                    <div class="brand-section">
                        <div class="brand-icon-wrapper">
                            <img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
                            <div class="brand-glow"></div>
                        </div>
                        <div class="brand-text">
                            <span class="brand-name">WithOps</span>
                            <span class="brand-subtitle">DevSecOps Platform</span>
                        </div>
                    </div>
                    
                    <!-- Navigation Links -->
                    <nav class="nav-links">
                        <a 
                            href="/dashboard" 
                            class="nav-link active"
                        >
                            <span class="nav-icon">🏠</span>
                            Dashboard
                        </a>
                    </nav>
                </div>
                
                <!-- Right side - User Profile & Actions -->
                <div class="header-right">
                    <!-- Theme Toggle -->
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
                    
                    <!-- User Profile Section -->
                    <div class="user-profile">
                        <div class="user-avatar">
                            {#if user?.picture && !profilePictureError}
                                <img 
                                    src={getProfilePictureUrl(user.picture, pictureRetryCount)} 
                                    alt={user.name || 'User'} 
                                    class="avatar-image"
                                    loading="lazy"
                                    crossorigin="anonymous"
                                    referrerpolicy="no-referrer"
                                    onerror={handlePictureError}
                                />
                            {:else}
                                <span class="avatar-text">
                                    {user?.name?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || 'U'}
                                </span>
                            {/if}
                            <div class="avatar-status"></div>
                        </div>
                        <div class="user-info">
                            <p class="user-name">{user?.name || 'User'}</p>
                            <p class="user-email">{user?.email || ''}</p>
                        </div>
                    </div>
                    
                    <!-- Logout Button -->
                    <button 
                        onclick={logout}
                        class="logout-button"
                    >
                        <span class="logout-icon">🚪</span>
                        Logout
                    </button>
                </div>
            </div>
        </nav>

        <!-- Hero Section with Platform Description -->
        <section class="hero-section">
            <div class="hero-content">
                <div class="hero-text">
                    <h1 class="hero-title">
                        Welcome to <span class="title-highlight">WithOps</span>
                    </h1>
                    <p class="hero-description">
                        Your comprehensive DevSecOps platform for secure development workflows. 
                        Connect your GitHub repositories and organizations to enhance your 
                        development pipeline with enterprise-grade security built-in.
                    </p>
                </div>
            </div>
        </section>

        <!-- Main Dashboard Content -->
        <main class="dashboard-main">
            <div class="dashboard-grid">
                <!-- GitHub Connection Section -->
                <div class="dashboard-card github-card">
                    <div class="card-header">
                        <div class="card-icon-wrapper">
                            <svg class="card-icon" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                            </svg>
                            <div class="icon-glow"></div>
                        </div>
                        <div class="card-title-section">
                            <h2 class="card-title">GitHub Integration</h2>
                            <p class="card-subtitle">Connect your repositories for automated security scanning</p>
                        </div>
                    </div>
                    
                    <div class="card-content">
                        {#if !isGitHubConnected}
                            <div class="connection-status">
                                <div class="status-indicator disconnected">
                                    <div class="status-dot"></div>
                                    <span class="status-text">Not Connected</span>
                                </div>
                                <p class="status-description">
                                    Integrate with GitHub to enable automated vulnerability scanning, 
                                    compliance checks, and security workflow automation across your repositories.
                                </p>
                                <button 
                                    onclick={connectToGitHub}
                                    class="primary-button"
                                >
                                    <span class="button-icon">🔗</span>
                                    Connect GitHub Account
                                </button>
                            </div>
                        {:else}
                            <div class="connection-status">
                                <div class="status-indicator connected">
                                    <div class="status-dot"></div>
                                    <span class="status-text">Connected</span>
                                </div>
                                
                                <div class="connection-details">
                                    <div class="detail-item">
                                        <span class="detail-icon"></span>
                                        <div class="detail-content">
                                            <h4>GitHub Account Linked</h4>
                                            <p>Ready to discover and manage organizations</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <button 
                                    onclick={discoverOrganizations}
                                    disabled={isDiscovering}
                                    class="secondary-button"
                                >
                                    {#if isDiscovering}
                                        <span class="loading-spinner small"></span>
                                        Discovering...
                                    {:else}
                                        <span class="button-icon">🔍</span>
                                        Discover Organizations
                                    {/if}
                                </button>
                            </div>
                        {/if}
                    </div>
                </div>

                <!-- Organization Workspaces Section -->
                <div class="dashboard-card workspace-card">
                    <div class="card-header">
                        <div class="card-icon-wrapper">
                            <svg class="card-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                            </svg>
                            <div class="icon-glow"></div>
                        </div>
                        <div class="card-title-section">
                            <h2 class="card-title">Organization Workspaces</h2>
                            <p class="card-subtitle">Manage your DevSecOps pipelines and security workflows</p>
                        </div>
                    </div>
                    
                    <div class="card-content">
                        <div class="workspace-overview">
                            <p class="workspace-description">
                                Access your connected GitHub organizations and manage repository-level 
                                security policies, automated scanning, and compliance monitoring.
                            </p>
                            
                            <button 
                                onclick={() => goto('/organizations')}
                                class="tertiary-button"
                            >
                                <span class="button-icon">🏢</span>
                                View Workspaces
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
{/if}

<style>
    /* Global Reset and Dark Theme Variables */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    :global(body) {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Dashboard Container */
    .dashboard-container {
        position: relative;
        min-height: 100vh;
        background: var(--bg-primary);
        overflow-x: hidden;
        --bg-primary: #000000;
        --bg-secondary: #0A0A0A;
        --text-primary: #FFFFFF;
        --text-secondary: #CCCCCC;
        --border-color: rgba(74, 158, 255, 0.2);
        --card-bg: rgba(255, 255, 255, 0.05);
        --card-bg-hover: rgba(255, 255, 255, 0.1);
        --primary-color: #4A9EFF;
        --accent-color: #FF8B4A;
        --github-bg: #24292f;
        --github-text: #f0f6ff;
    }

    .dashboard-container.light {
        --bg-primary: #ffffff;
        --bg-secondary: #f8fafc;
        --text-primary: #1a1a1a;
        --text-secondary: #2d3748;
        --border-color: rgba(9, 105, 218, 0.2);
        --card-bg: rgba(0, 0, 0, 0.08);
        --card-bg-hover: rgba(0, 0, 0, 0.12);
        --primary-color: #0969da;
        --accent-color: #d73a49;
        --github-bg: #f0f6ff;
        --github-text: #24292f;
    }

    /* Loading Screen */
    .loading-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, #000000 0%, #1A1A2E 50%, #000000 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }

    .loading-content {
        text-align: center;
        color: #CCCCCC;
    }

    .loading-spinner {
        width: 60px;
        height: 60px;
        border: 3px solid rgba(74, 158, 255, 0.1);
        border-radius: 50%;
        border-top-color: #4A9EFF;
        animation: spin 1s ease-in-out infinite;
        margin: 0 auto 2rem;
    }

    .loading-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .loading-text {
        font-size: 1rem;
        opacity: 0.8;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    /* Dashboard Header */
    .dashboard-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 1000;
        background: rgba(0, 0, 0, 0.95);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid var(--border-color);
        padding: 1rem 0;
        transition: all 0.3s ease;
    }

    .dashboard-container.light .dashboard-header {
        background: rgba(255, 255, 255, 0.95);
    }

    .header-content {
        width: 100%;
        margin: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 1rem;
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 3rem;
    }

    /* Brand Section */
    .brand-section {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .brand-icon-wrapper {
        position: relative;
        width: 40px;
        height: 40px;
    }

    .brand-icon {
        width: 40px;
        height: 40px;
        filter: drop-shadow(0 0 15px #4A9EFF);
        transition: all 0.3s ease;
    }

    .brand-icon:hover {
        filter: drop-shadow(0 0 20px #4A9EFF);
        transform: scale(1.05);
    }

    .brand-glow {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 60px;
        height: 60px;
        background: radial-gradient(circle, rgba(74, 158, 255, 0.2) 0%, transparent 70%);
        border-radius: 50%;
        animation: pulse-glow 3s ease-in-out infinite;
    }

    @keyframes pulse-glow {
        0%, 100% { opacity: 0.4; transform: translate(-50%, -50%) scale(1); }
        50% { opacity: 0.8; transform: translate(-50%, -50%) scale(1.2); }
    }

    .brand-text {
        display: flex;
        flex-direction: column;
    }

    .brand-name {
        font-size: 1.5rem;
        font-weight: 700;
        color: #4A9EFF;
        line-height: 1;
    }

    .brand-subtitle {
        font-size: 0.75rem;
        color: var(--text-secondary);
        opacity: 0.8;
        margin-top: 0.2rem;
        letter-spacing: 0.1em;
    }

    /* Navigation Links */
    .nav-links {
        display: flex;
        gap: 2rem;
        align-items: center;
    }

    .nav-link {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--text-secondary);
        text-decoration: none;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .nav-link::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(74, 158, 255, 0.1), transparent);
        transition: left 0.5s ease;
    }

    .nav-link:hover::before {
        left: 100%;
    }

    .nav-link:hover,
    .nav-link.active {
        color: #4A9EFF;
        background: rgba(74, 158, 255, 0.1);
        transform: translateY(-1px);
    }

    .nav-icon {
        font-size: 1rem;
    }

    /* Header Right Section */
    .header-right {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }

    .theme-toggle {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(74, 158, 255, 0.2);
        color: #4A9EFF;
        padding: 0.75rem;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }

    .theme-toggle:hover {
        background: rgba(74, 158, 255, 0.2);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(74, 158, 255, 0.3);
    }

    .theme-icon {
        width: 20px;
        height: 20px;
    }

    /* User Profile */
    .user-profile {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(74, 158, 255, 0.2);
        padding: 0.75rem 1rem;
        border-radius: 12px;
        transition: all 0.3s ease;
    }

    .user-profile:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(74, 158, 255, 0.4);
    }

    .user-avatar {
        position: relative;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        overflow: hidden;
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .avatar-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .avatar-text {
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
    }

    .avatar-status {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 12px;
        height: 12px;
        background: #00FF66;
        border: 2px solid #000000;
        border-radius: 50%;
    }

    .user-info {
        color: var(--text-secondary);
    }

    .user-name {
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.2rem;
    }

    .user-email {
        font-size: 0.75rem;
        opacity: 0.7;
    }

    /* Logout Button */
    .logout-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.9) 0%, rgba(220, 38, 38, 0.9) 100%);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 0.65rem 1.25rem;
        border-radius: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
            0 2px 8px rgba(239, 68, 68, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        font-size: 0.9rem;
        position: relative;
        overflow: hidden;
    }

    .dashboard-container.light .logout-button {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.85) 0%, rgba(220, 38, 38, 0.85) 100%);
        border: 1px solid rgba(239, 68, 68, 0.2);
        box-shadow: 
            0 2px 8px rgba(239, 68, 68, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }

    .logout-button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
        transition: left 0.5s ease;
    }

    .logout-button:hover::before {
        left: 100%;
    }

    .logout-button:hover {
        transform: translateY(-1px);
        box-shadow: 
            0 4px 12px rgba(239, 68, 68, 0.25),
            inset 0 1px 0 rgba(255, 255, 255, 0.15);
        background: linear-gradient(135deg, rgba(248, 113, 113, 0.9) 0%, rgba(239, 68, 68, 0.9) 100%);
        border-color: rgba(255, 255, 255, 0.2);
    }

    .dashboard-container.light .logout-button:hover {
        box-shadow: 
            0 4px 12px rgba(239, 68, 68, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.25);
        background: linear-gradient(135deg, rgba(248, 113, 113, 0.85) 0%, rgba(239, 68, 68, 0.85) 100%);
    }

    .logout-icon {
        font-size: 0.9rem;
        opacity: 0.9;
        transition: opacity 0.3s ease;
    }

    .logout-button:hover .logout-icon {
        opacity: 1;
    }

    /* Hero Section */
    .hero-section {
        margin-top: 100px;
        padding: 4rem 2rem 2rem;
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.3) 0%, rgba(74, 158, 255, 0.1) 100%);
        position: relative;
        z-index: 2;
    }

    .hero-content {
        width: 100%;
        margin: 0;
        text-align: center;
        padding: 0 1rem;
    }

    .hero-title {
        font-size: clamp(2.5rem, 6vw, 4rem);
        font-weight: 700;
        margin-bottom: 1.5rem;
        color: var(--text-primary);
        line-height: 1.1;
    }

    .title-highlight {
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .hero-description {
        font-size: 1.25rem;
        color: var(--text-secondary);
        max-width: 800px;
        margin: 0 auto 2rem;
        line-height: 1.6;
    }

    /* Main Dashboard Content */
    .dashboard-main {
        padding: 4rem 0;
        position: relative;
        z-index: 2;
    }

    .dashboard-grid {
        width: 100%;
        margin: 0;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 3rem;
        padding: 0 2rem;
        max-width: 1400px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Dashboard Cards */
    .dashboard-card {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
        backdrop-filter: blur(25px);
        border: 1px solid rgba(74, 158, 255, 0.25);
        border-radius: 24px;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.1),
            0 4px 16px rgba(74, 158, 255, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }

    .dashboard-container.light .dashboard-card {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.8) 100%);
        border: 1px solid rgba(9, 105, 218, 0.15);
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.04),
            0 4px 16px rgba(9, 105, 218, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.8);
    }

    .dashboard-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(74, 158, 255, 0.08), transparent);
        transition: left 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .dashboard-card:hover::before {
        left: 100%;
    }

    .dashboard-card:hover {
        transform: translateY(-12px) scale(1.02);
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.06) 100%);
        border-color: rgba(74, 158, 255, 0.5);
        box-shadow: 
            0 24px 48px rgba(0, 0, 0, 0.15),
            0 12px 24px rgba(74, 158, 255, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }

    .dashboard-container.light .dashboard-card:hover {
        background: linear-gradient(145deg, rgba(255, 255, 255, 1) 0%, rgba(248, 250, 252, 0.95) 100%);
        border-color: rgba(9, 105, 218, 0.3);
        box-shadow: 
            0 24px 48px rgba(0, 0, 0, 0.08),
            0 12px 24px rgba(9, 105, 218, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 1);
    }

    /* Card Headers */
    .card-header {
        display: flex;
        align-items: center;
        gap: 1.5rem;
        padding: 2rem 2.5rem 1rem;
        position: relative;
    }

    .card-icon-wrapper {
        position: relative;
        width: 80px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.15) 0%, rgba(255, 139, 74, 0.15) 100%);
        border-radius: 20px;
        border: 2px solid rgba(74, 158, 255, 0.3);
        backdrop-filter: blur(10px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .dashboard-container.light .card-icon-wrapper {
        background: linear-gradient(135deg, rgba(9, 105, 218, 0.12) 0%, rgba(215, 58, 73, 0.12) 100%);
        border: 2px solid rgba(9, 105, 218, 0.2);
    }

    .card-icon-wrapper:hover {
        transform: scale(1.1) rotate(5deg);
        border-color: rgba(74, 158, 255, 0.6);
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.25) 0%, rgba(255, 139, 74, 0.25) 100%);
    }

    .dashboard-container.light .card-icon-wrapper:hover {
        border-color: rgba(9, 105, 218, 0.4);
        background: linear-gradient(135deg, rgba(9, 105, 218, 0.2) 0%, rgba(215, 58, 73, 0.2) 100%);
    }

    .card-icon {
        width: 48px;
        height: 48px;
        color: #4A9EFF;
        z-index: 2;
        position: relative;
        filter: drop-shadow(0 4px 8px rgba(74, 158, 255, 0.3));
        transition: all 0.3s ease;
    }

    .dashboard-container.light .card-icon {
        color: #0969da;
        filter: drop-shadow(0 4px 8px rgba(9, 105, 218, 0.2));
    }

    .icon-glow {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 100px;
        height: 100px;
        background: radial-gradient(circle, rgba(74, 158, 255, 0.4) 0%, transparent 70%);
        border-radius: 50%;
        animation: pulse-enhanced 3s ease-in-out infinite;
        z-index: 1;
    }

    .dashboard-container.light .icon-glow {
        background: radial-gradient(circle, rgba(9, 105, 218, 0.3) 0%, transparent 70%);
    }

    @keyframes pulse-enhanced {
        0%, 100% { 
            opacity: 0.6; 
            transform: translate(-50%, -50%) scale(1);
        }
        50% { 
            opacity: 1; 
            transform: translate(-50%, -50%) scale(1.3);
        }
    }

    .card-title-section {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .card-title {
        font-size: 1.75rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4A9EFF 0%, #66D9FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        line-height: 1.2;
        letter-spacing: -0.02em;
    }

    .dashboard-container.light .card-title {
        background: linear-gradient(135deg, #0969da 0%, #0550ae 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .card-subtitle {
        font-size: 1rem;
        color: var(--text-secondary);
        opacity: 0.85;
        line-height: 1.5;
        font-weight: 500;
    }

    /* Card Content */
    .card-content {
        padding: 1rem 2.5rem 2rem;
    }

    /* Status Indicators */
    .connection-status,
    .workspace-overview {
        text-align: center;
    }

    .status-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        padding: 0.75rem 1.25rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        border: 1px solid rgba(74, 158, 255, 0.1);
        transition: all 0.3s ease;
    }

    .dashboard-container.light .status-indicator {
        background: rgba(9, 105, 218, 0.05);
        border: 1px solid rgba(9, 105, 218, 0.1);
    }

    .status-indicator:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(74, 158, 255, 0.2);
        transform: translateY(-2px);
    }

    .dashboard-container.light .status-indicator:hover {
        background: rgba(9, 105, 218, 0.08);
        border-color: rgba(9, 105, 218, 0.2);
    }

    .status-dot {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        position: relative;
        animation: pulse-dot 2s ease-in-out infinite;
    }

    @keyframes pulse-dot {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.2); }
    }

    .status-indicator.connected .status-dot {
        background: linear-gradient(135deg, #00FF66 0%, #00CC52 100%);
        box-shadow: 
            0 0 20px rgba(0, 255, 102, 0.6),
            0 0 40px rgba(0, 255, 102, 0.3);
    }

    .status-indicator.connected .status-dot::after {
        content: '';
        position: absolute;
        top: -4px;
        left: -4px;
        right: -4px;
        bottom: -4px;
        border: 2px solid rgba(0, 255, 102, 0.3);
        border-radius: 50%;
        animation: pulse-ring 2s ease-in-out infinite;
    }

    .status-indicator.disconnected .status-dot {
        background: linear-gradient(135deg, #ff4757 0%, #ff3742 100%);
        box-shadow: 
            0 0 20px rgba(255, 71, 87, 0.6),
            0 0 40px rgba(255, 71, 87, 0.3);
    }

    .status-indicator.disconnected .status-dot::after {
        content: '';
        position: absolute;
        top: -4px;
        left: -4px;
        right: -4px;
        bottom: -4px;
        border: 2px solid rgba(255, 71, 87, 0.3);
        border-radius: 50%;
        animation: pulse-ring 2s ease-in-out infinite;
    }

    @keyframes pulse-ring {
        0%, 100% { 
            transform: scale(1);
            opacity: 1;
        }
        50% { 
            transform: scale(1.3);
            opacity: 0.7;
        }
    }

    .status-text {
        font-weight: 700;
        color: var(--text-primary);
        font-size: 1.125rem;
        letter-spacing: -0.01em;
    }

    .status-description {
        color: var(--text-secondary);
        line-height: 1.7;
        margin-bottom: 1.75rem;
        opacity: 0.9;
        font-size: 1rem;
        max-width: 90%;
        margin-left: auto;
        margin-right: auto;
    }

    /* Buttons */
    .primary-button,
    .secondary-button,
    .tertiary-button {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        padding: 1rem 2rem;
        border: none;
        border-radius: 16px;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        text-decoration: none;
        font-size: 1rem;
        width: 100%;
        margin-top: 1rem;
        position: relative;
        overflow: hidden;
        letter-spacing: -0.01em;
    }

    .primary-button::before,
    .secondary-button::before,
    .tertiary-button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.6s ease;
    }

    .primary-button:hover::before,
    .secondary-button:hover::before,
    .tertiary-button:hover::before {
        left: 100%;
    }

    .primary-button {
        background: linear-gradient(135deg, #4A9EFF 0%, #0969da 100%);
        color: white;
        box-shadow: 
            0 8px 25px rgba(74, 158, 255, 0.4),
            0 4px 12px rgba(74, 158, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .dashboard-container.light .primary-button {
        background: linear-gradient(135deg, #0969da 0%, #0550ae 100%);
        box-shadow: 
            0 8px 25px rgba(9, 105, 218, 0.3),
            0 4px 12px rgba(9, 105, 218, 0.15);
    }

    .primary-button:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 
            0 16px 40px rgba(74, 158, 255, 0.5),
            0 8px 20px rgba(74, 158, 255, 0.3);
        background: linear-gradient(135deg, #5AB0FF 0%, #1A7BEA 100%);
    }

    .dashboard-container.light .primary-button:hover {
        box-shadow: 
            0 16px 40px rgba(9, 105, 218, 0.4),
            0 8px 20px rgba(9, 105, 218, 0.25);
        background: linear-gradient(135deg, #1A7BEA 0%, #0660C7 100%);
    }

    .secondary-button {
        background: linear-gradient(135deg, rgba(102, 217, 255, 0.15) 0%, rgba(74, 158, 255, 0.1) 100%);
        color: #66D9FF;
        border: 2px solid rgba(102, 217, 255, 0.4);
        backdrop-filter: blur(10px);
        box-shadow: 
            0 6px 20px rgba(102, 217, 255, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }

    .dashboard-container.light .secondary-button {
        background: linear-gradient(135deg, rgba(9, 105, 218, 0.12) 0%, rgba(79, 172, 254, 0.08) 100%);
        color: #0969da;
        border: 2px solid rgba(9, 105, 218, 0.3);
        box-shadow: 
            0 6px 20px rgba(9, 105, 218, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.8);
    }

    .secondary-button:hover {
        background: linear-gradient(135deg, #66D9FF 0%, #4A9EFF 100%);
        color: #000000;
        transform: translateY(-4px) scale(1.02);
        border-color: #66D9FF;
        box-shadow: 
            0 16px 40px rgba(102, 217, 255, 0.4),
            0 8px 20px rgba(102, 217, 255, 0.25);
    }

    .dashboard-container.light .secondary-button:hover {
        background: linear-gradient(135deg, #0969da 0%, #0550ae 100%);
        color: #ffffff;
        border-color: #0969da;
        box-shadow: 
            0 16px 40px rgba(9, 105, 218, 0.3),
            0 8px 20px rgba(9, 105, 218, 0.2);
    }

    .tertiary-button {
        background: linear-gradient(135deg, rgba(0, 255, 102, 0.15) 0%, rgba(0, 204, 82, 0.1) 100%);
        color: #00FF66;
        border: 2px solid rgba(0, 255, 102, 0.4);
        backdrop-filter: blur(10px);
        box-shadow: 
            0 6px 20px rgba(0, 255, 102, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }

    .dashboard-container.light .tertiary-button {
        background: linear-gradient(135deg, rgba(22, 163, 74, 0.12) 0%, rgba(34, 197, 94, 0.08) 100%);
        color: #16a34a;
        border: 2px solid rgba(22, 163, 74, 0.3);
        box-shadow: 
            0 6px 20px rgba(22, 163, 74, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.8);
    }

    .tertiary-button:hover {
        background: linear-gradient(135deg, #00FF66 0%, #00CC52 100%);
        color: #000000;
        transform: translateY(-4px) scale(1.02);
        border-color: #00FF66;
        box-shadow: 
            0 16px 40px rgba(0, 255, 102, 0.4),
            0 8px 20px rgba(0, 255, 102, 0.25);
    }

    .dashboard-container.light .tertiary-button:hover {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
        color: #ffffff;
        border-color: #16a34a;
        box-shadow: 
            0 16px 40px rgba(22, 163, 74, 0.3),
            0 8px 20px rgba(22, 163, 74, 0.2);
    }

    .button-icon {
        font-size: 1.25rem;
        filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
        transition: transform 0.3s ease;
    }

    .primary-button:hover .button-icon,
    .secondary-button:hover .button-icon,
    .tertiary-button:hover .button-icon {
        transform: scale(1.1);
    }

    /* Connection Details */
    .connection-details {
        margin: 2.5rem 0;
    }

    .detail-item {
        display: flex;
        align-items: center;
        gap: 1.25rem;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(74, 158, 255, 0.15);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .dashboard-container.light .detail-item {
        background: linear-gradient(135deg, rgba(9, 105, 218, 0.08) 0%, rgba(248, 250, 252, 0.8) 100%);
        border: 1px solid rgba(9, 105, 218, 0.12);
    }

    .detail-item::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(74, 158, 255, 0.1), transparent);
        transition: left 0.6s ease;
    }

    .detail-item:hover::before {
        left: 100%;
    }

    .detail-item:hover {
        transform: translateY(-4px);
        border-color: rgba(74, 158, 255, 0.3);
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.04) 100%);
        box-shadow: 0 12px 24px rgba(74, 158, 255, 0.15);
    }

    .dashboard-container.light .detail-item:hover {
        border-color: rgba(9, 105, 218, 0.25);
        background: linear-gradient(135deg, rgba(9, 105, 218, 0.12) 0%, rgba(248, 250, 252, 0.95) 100%);
        box-shadow: 0 12px 24px rgba(9, 105, 218, 0.12);
    }

    .detail-icon {
        font-size: 2rem;
        filter: drop-shadow(0 2px 4px rgba(0, 255, 102, 0.3));
    }

    .detail-content {
        flex: 1;
    }

    .detail-content h4 {
        color: #4A9EFF;
        font-weight: 700;
        margin-bottom: 0.5rem;
        font-size: 1.125rem;
        letter-spacing: -0.01em;
    }

    .dashboard-container.light .detail-content h4 {
        color: #0969da;
    }

    .detail-content p {
        color: var(--text-secondary);
        font-size: 0.95rem;
        opacity: 0.9;
        line-height: 1.6;
    }

    .workspace-description {
        color: var(--text-secondary);
        line-height: 1.7;
        margin-bottom: 2.5rem;
        opacity: 0.9;
        font-size: 1rem;
        max-width: 90%;
        margin-left: auto;
        margin-right: auto;
    }

    /* Loading Spinner */
    .loading-spinner.small {
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: white;
        animation: spin 1s linear infinite;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .header-content {
            padding: 0 1rem;
        }

        .header-left {
            gap: 1rem;
        }

        .nav-links {
            display: none;
        }

        .hero-section {
            padding: 3rem 1rem 1rem;
        }

        .dashboard-main {
            padding: 2rem 1rem;
        }

        .dashboard-grid {
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }

        .card-header {
            padding: 1.5rem 1.5rem 1rem;
        }

        .card-content {
            padding: 1rem 1.5rem 1.5rem;
        }

        .user-info {
            display: none;
        }
    }

    @media (max-width: 480px) {
        .brand-name {
            font-size: 1.2rem;
        }

        .brand-subtitle {
            display: none;
        }

        .hero-title {
            font-size: 2rem;
        }

        .hero-description {
            font-size: 1rem;
        }

        .dashboard-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
        }
    }

    /* Animations for better UX */
    .dashboard-card,
    .primary-button,
    .secondary-button,
    .tertiary-button,
    .nav-link,
    .theme-toggle,
    .user-profile,
    .logout-button {
        transform-origin: center;
    }

    /* Disabled state */
    .primary-button:disabled,
    .secondary-button:disabled,
    .tertiary-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none;
    }

    .primary-button:disabled:hover,
    .secondary-button:disabled:hover,
    .tertiary-button:disabled:hover {
        transform: none;
        box-shadow: initial;
    }
</style>
