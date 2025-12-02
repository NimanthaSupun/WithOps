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
    let isProfileDropdownOpen = $state(false);
    
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
            
            // Add click outside listener for dropdown
            document.addEventListener('click', handleClickOutside);
            
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
        
        // Cleanup listener on unmount
        return () => {
            document.removeEventListener('click', handleClickOutside);
        };
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
            // First check GitHub connection status via dedicated endpoint
            const connectionStatus = await githubClient.getGitHubConnectionStatus();
            
            if (connectionStatus.success && connectionStatus.github_connected) {
                isGitHubConnected = true;
                console.log('✅ GitHub connected:', connectionStatus.github_username);
                return;
            }
            
            // Fallback: check if user has organizations
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
            // Use the new GitHub connection endpoint
            const result = await githubClient.startGitHubConnection();
            
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

    function toggleProfileDropdown() {
        isProfileDropdownOpen = !isProfileDropdownOpen;
    }

    function closeProfileDropdown() {
        isProfileDropdownOpen = false;
    }

    // Close dropdown when clicking outside
    function handleClickOutside(event) {
        const dropdown = document.querySelector('.profile-dropdown-container');
        if (dropdown && !dropdown.contains(event.target)) {
            closeProfileDropdown();
        }
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
        <!-- Animated Particle Background -->
        <div class="particles">
            {#each Array(20) as _, i}
                <div class="particle" style="--delay: {i * 0.3}s; --x: {Math.random() * 100}%; --y: {Math.random() * 100}%;"></div>
            {/each}
        </div>
        
        <!-- Animated Grid Background -->
        <div class="grid-background">
            <div class="grid-lines"></div>
        </div>
        
        <!-- Main Loading Content -->
        <div class="loading-content">
            <!-- 3D Icon Container with Advanced Effects -->
            <div class="loading-icon-container">
                <!-- Orbiting Rings -->
                <div class="orbit-ring orbit-1"></div>
                <div class="orbit-ring orbit-2"></div>
                <div class="orbit-ring orbit-3"></div>
                
                <!-- Hexagon Frame -->
                <div class="hexagon-frame">
                    <div class="hex-side"></div>
                    <div class="hex-side"></div>
                    <div class="hex-side"></div>
                    <div class="hex-side"></div>
                    <div class="hex-side"></div>
                    <div class="hex-side"></div>
                </div>
                
                <!-- Central Icon with Glow -->
                <div class="icon-wrapper">
                    <div class="icon-glow-layer glow-1"></div>
                    <div class="icon-glow-layer glow-2"></div>
                    <div class="icon-glow-layer glow-3"></div>
                    <img src="/icons/excellence_17274210.png" alt="WithOps" class="loading-icon" />
                </div>
                
                <!-- Energy Pulses -->
                <div class="energy-pulse pulse-1"></div>
                <div class="energy-pulse pulse-2"></div>
                <div class="energy-pulse pulse-3"></div>
            </div>
            
            <!-- Professional Info Section -->
            <div class="info-section">
                <!-- Brand -->
                <h1 class="loading-title">WithOps</h1>
                <p class="loading-subtitle">DevSecOps Platform</p>
                
                <!-- Progress Bar -->
                <div class="progress-section">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                </div>
                
                <!-- Status Message -->
                <div class="status-message">
                    <div class="status-dot"></div>
                    <span>Initializing your secure development environment</span>
                </div>
            </div>
            
            <!-- Floating Elements -->
            <div class="floating-elements">
                <div class="float-element element-1">◆</div>
                <div class="float-element element-2">●</div>
                <div class="float-element element-3">▲</div>
                <div class="float-element element-4">■</div>
            </div>
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
                    
                    <!-- User Profile Dropdown -->
                    <div class="profile-dropdown-container">
                        <button 
                            class="user-profile-trigger"
                            onclick={toggleProfileDropdown}
                            aria-expanded={isProfileDropdownOpen}
                            aria-haspopup="true"
                        >
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
                            <span class="user-name-compact">{user?.name || 'User'}</span>
                            <svg class="dropdown-arrow" class:open={isProfileDropdownOpen} width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M4.427 6.427l3.396 3.396a.25.25 0 00.354 0l3.396-3.396A.25.25 0 0011.396 6H4.604a.25.25 0 00-.177.427z"/>
                            </svg>
                        </button>
                        
                        {#if isProfileDropdownOpen}
                            <div class="profile-dropdown-menu">
                                <div class="dropdown-user-info">
                                    <div class="dropdown-avatar">
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
                                    </div>
                                    <div class="dropdown-user-details">
                                        <p class="dropdown-name">{user?.name || 'User'}</p>
                                        <p class="dropdown-email">{user?.email || ''}</p>
                                    </div>
                                </div>
                                
                                <div class="dropdown-divider"></div>
                                
                                <button 
                                    onclick={logout}
                                    class="dropdown-logout-button"
                                >
                                    <svg class="logout-icon-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                                        <polyline points="16 17 21 12 16 7"></polyline>
                                        <line x1="21" y1="12" x2="9" y2="12"></line>
                                    </svg>
                                    Sign Out
                                </button>
                            </div>
                        {/if}
                    </div>
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
        
        <!-- SVG Workflow Art Section -->
        <section class="workflow-art-section">
            <svg class="workflow-svg" viewBox="0 0 1400 900" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
                <defs>
                    <!-- Gradient for the main flow path -->
                    <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" class="flow-gradient-start" />
                        <stop offset="50%" class="flow-gradient-mid" />
                        <stop offset="100%" class="flow-gradient-end" />
                    </linearGradient>
                    
                    <!-- Shadow filter -->
                    <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
                        <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
                        <feOffset dx="2" dy="2" result="offsetblur"/>
                        <feComponentTransfer>
                            <feFuncA type="linear" slope="0.3"/>
                        </feComponentTransfer>
                        <feMerge>
                            <feMergeNode/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                    
                    <!-- Arrow markers -->
                    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                        <polygon points="0 0, 10 3, 0 6" class="arrow-fill" />
                    </marker>
                    <marker id="arrow2" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                        <polygon points="0 0, 8 3, 0 6" class="arrow-fill-small" />
                    </marker>
                </defs>

                <!-- Main flow path - 3D ribbon effect -->
                <path d="M 100,450 Q 200,350 350,400 T 650,500 T 950,400 T 1200,500" 
                    stroke="url(#flowGradient)" 
                    stroke-width="80" 
                    fill="none" 
                    opacity="0.4"/>
                
                <path d="M 100,450 Q 200,350 350,400 T 650,500 T 950,400 T 1200,500" 
                    class="flow-path-main" 
                    stroke-width="60" 
                    fill="none" 
                    opacity="0.8"/>
                
                <path d="M 100,450 Q 200,350 350,400 T 650,500 T 950,400 T 1200,500" 
                    class="flow-path-bright" 
                    stroke-width="40" 
                    fill="none" 
                    opacity="1"/>

                <!-- Step 1: Connect GitHub Account -->
                <g transform="translate(150, 380)" class="workflow-step">
                    <!-- 3D Platform base -->
                    <ellipse cx="0" cy="80" rx="70" ry="15" class="platform-shadow" opacity="0.5"/>
                    <rect x="-70" y="30" width="140" height="50" class="platform-side" stroke-width="2"/>
                    <path d="M -70,30 L -50,15 L 90,15 L 70,30 Z" class="platform-top" stroke-width="2"/>
                    <path d="M 70,30 L 90,15 L 90,65 L 70,80 Z" class="platform-right" stroke-width="2"/>
                    
                    <!-- GitHub Icon (Octocat style) -->
                    <circle cx="0" cy="0" r="35" class="github-bg" filter="url(#shadow)"/>
                    <path d="M 0,-20 C -15,-20 -25,-10 -25,5 C -25,17 -17,25 -5,28 C -3,28 -2,27 -2,25 L -2,20 C -10,22 -12,16 -12,16 C -13,13 -15,12 -15,12 C -18,10 -15,10 -15,10 C -12,10 -10,13 -10,13 C -7,18 -3,16 -2,15 C -2,13 -1,12 0,11 C -7,10 -15,7 -15,0 C -15,-3 -14,-6 -12,-8 C -12,-9 -14,-12 -11,-15 C -11,-15 -9,-16 -2,-11 C 0,-12 3,-12 5,-11 C 12,-16 14,-15 14,-15 C 17,-12 15,-9 15,-8 C 17,-6 18,-3 18,0 C 18,7 10,10 3,11 C 4,12 5,14 5,16 L 5,25 C 5,27 6,28 8,28 C 20,25 28,17 28,5 C 28,-10 18,-20 0,-20 Z" class="github-icon"/>
                    
                    <!-- Magnifying glass -->
                    <g transform="translate(45, -30)">
                        <circle cx="0" cy="0" r="18" fill="none" class="magnify-circle" stroke-width="3"/>
                        <line x1="13" y1="13" x2="28" y2="28" class="magnify-handle" stroke-width="3" stroke-linecap="round"/>
                        <circle cx="0" cy="0" r="12" class="magnify-fill"/>
                    </g>
                </g>
                
                <!-- Annotation for Step 1 -->
                <text x="150" y="520" class="step-title" text-anchor="middle">Connect GitHub</text>
                <text x="150" y="545" class="step-subtitle" text-anchor="middle">Account</text>
                
                <!-- Dashed connector line -->
                <path d="M 220,420 Q 280,380 340,420" class="connector-line" stroke-width="2" stroke-dasharray="8,5" fill="none" opacity="0.6"/>

                <!-- Step 2: Discover Organizations -->
                <g transform="translate(450, 450)" class="workflow-step">
                    <!-- 3D Server/Database stack -->
                    <g>
                        <!-- Bottom layer -->
                        <ellipse cx="0" cy="50" rx="65" ry="18" class="server-layer-1" opacity="0.6"/>
                        <rect x="-65" y="32" width="130" height="18" class="server-mid-1"/>
                        <ellipse cx="0" cy="32" rx="65" ry="18" class="server-top-1"/>
                        
                        <!-- Middle layer -->
                        <ellipse cx="0" cy="20" rx="65" ry="18" class="server-layer-2" opacity="0.7"/>
                        <rect x="-65" y="2" width="130" height="18" class="server-mid-2"/>
                        <ellipse cx="0" cy="2" rx="65" ry="18" class="server-top-2"/>
                        
                        <!-- Top layer -->
                        <ellipse cx="0" cy="-10" rx="65" ry="18" class="server-layer-3" opacity="0.8"/>
                        <rect x="-65" y="-28" width="130" height="18" class="server-mid-3"/>
                        <ellipse cx="0" cy="-28" rx="65" ry="18" class="server-top-3"/>
                    </g>
                    
                    <!-- Organization icons -->
                    <g transform="translate(-30, -20)">
                        <circle cx="0" cy="0" r="8" class="org-circle" stroke-width="2"/>
                        <path d="M 0,-3 L -3,3 L 3,3 Z" class="org-icon"/>
                    </g>
                    <g transform="translate(0, -15)">
                        <circle cx="0" cy="0" r="8" class="org-circle" stroke-width="2"/>
                        <path d="M 0,-3 L -3,3 L 3,3 Z" class="org-icon"/>
                    </g>
                    <g transform="translate(30, -20)">
                        <circle cx="0" cy="0" r="8" class="org-circle" stroke-width="2"/>
                        <path d="M 0,-3 L -3,3 L 3,3 Z" class="org-icon"/>
                    </g>
                    
                    <!-- Scanning beam effect -->
                    <line x1="-50" y1="-50" x2="50" y2="-50" class="scan-line" stroke-width="3" opacity="0.7">
                        <animate attributeName="y1" values="-50;50;-50" dur="3s" repeatCount="indefinite"/>
                        <animate attributeName="y2" values="-50;50;-50" dur="3s" repeatCount="indefinite"/>
                    </line>
                </g>
                
                <!-- Annotation for Step 2 -->
                <text x="450" y="590" class="step-title" text-anchor="middle">Discover</text>
                <text x="450" y="615" class="step-subtitle" text-anchor="middle">Organizations</text>
                
                <!-- Sketch arrows with labels -->
                <g>
                    <path d="M 520,480 Q 600,450 680,420" class="connector-line" stroke-width="2" stroke-dasharray="8,5" fill="none" opacity="0.6"/>
                    <text x="600" y="445" class="sketch-note">Scan & Import</text>
                </g>

                <!-- Step 3: Navigate to Workspaces -->
                <g transform="translate(850, 350)" class="workflow-step">
                    <!-- 3D Dashboard/Monitor -->
                    <g>
                        <!-- Monitor stand -->
                        <rect x="-8" y="85" width="16" height="30" class="monitor-stand" rx="2"/>
                        <ellipse cx="0" cy="120" rx="40" ry="8" class="monitor-base"/>
                        
                        <!-- Monitor frame -->
                        <rect x="-90" y="-60" width="180" height="140" class="monitor-frame" rx="8" filter="url(#shadow)"/>
                        <rect x="-80" y="-50" width="160" height="120" class="monitor-screen" stroke-width="2"/>
                        
                        <!-- Dashboard content -->
                        <g transform="translate(0, -10)">
                            <!-- Header bar -->
                            <rect x="-75" y="-45" width="150" height="15" class="dashboard-header" rx="2"/>
                            <circle cx="-65" cy="-37.5" r="3" class="window-dot"/>
                            <circle cx="-55" cy="-37.5" r="3" class="windw-dot"/>
                            <circle cx="-45" cy="-37.5" r="3" class="window-dot"/>
                            
                            <!-- Security shield icon -->
                            <g transform="translate(-35, -10)">
                                <path d="M 0,-15 L -12,-10 L -12,0 C -12,8 -6,14 0,16 C 6,14 12,8 12,0 L 12,-10 Z" class="security-shield" stroke-width="1.5"/>
                                <path d="M 0,-8 L -5,0 L -2,0 L -2,6 L 2,6 L 2,0 L 5,0 Z" class="shield-check"/>
                            </g>
                            
                            <!-- Chart elements -->
                            <rect x="5" y="-5" width="12" height="25" class="chart-bar-1" opacity="0.7" rx="1"/>
                            <rect x="20" y="5" width="12" height="15" class="chart-bar-2" opacity="0.7" rx="1"/>
                            <rect x="35" y="-10" width="12" height="30" class="chart-bar-3" opacity="0.7" rx="1"/>
                            <rect x="50" y="0" width="12" height="20" class="chart-bar-4" opacity="0.7" rx="1"/>
                            
                            <!-- Status indicators -->
                            <circle cx="-55" cy="30" r="5" class="status-green"/>
                            <circle cx="-35" cy="30" r="5" class="status-green"/>
                            <circle cx="-15" cy="30" r="5" class="status-yellow"/>
                        </g>
                    </g>
                    
                    <!-- Floating security badges -->
                    <g transform="translate(110, -20)">
                        <circle cx="0" cy="0" r="20" class="badge-blue" opacity="0.9" filter="url(#shadow)">
                            <animate attributeName="cy" values="-20;-15;-20" dur="2.5s" repeatCount="indefinite"/>
                        </circle>
                        <path d="M -8,0 L -3,8 L 10,-8" class="badge-check" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                    </g>
                    
                    <g transform="translate(120, 40)">
                        <circle cx="0" cy="0" r="18" class="badge-green" opacity="0.9" filter="url(#shadow)">
                            <animate attributeName="cy" values="40;45;40" dur="2.8s" repeatCount="indefinite"/>
                        </circle>
                        <text x="0" y="7" class="checkmark-text" text-anchor="middle">✓</text>
                    </g>
                </g>
                
                <!-- Annotation for Step 3 -->
                <text x="850" y="520" class="step-title" text-anchor="middle">Navigate to</text>
                <text x="850" y="545" class="step-subtitle" text-anchor="middle">Workspaces</text>
                
                <!-- DevSecOps Activities callout -->
                <g transform="translate(1050, 380)" class="workflow-step">
                    <!-- Sketchy box -->
                    <rect x="0" y="0" width="280" height="180" class="callout-box" rx="5" stroke-width="2" stroke-dasharray="5,3" filter="url(#shadow)"/>
                    
                    <text x="140" y="30" class="callout-title" text-anchor="middle">DevSecOps Activities</text>
                    
                    <!-- Activity items -->
                    <g transform="translate(20, 50)">
                        <circle cx="0" cy="0" r="6" class="activity-dot-1"/>
                        <text x="15" y="5" class="activity-text">Repository Scanning</text>
                    </g>
                    
                    <g transform="translate(20, 85)">
                        <circle cx="0" cy="0" r="6" class="activity-dot-2"/>
                        <text x="15" y="5" class="activity-text">Threat Modeling</text>
                    </g>
                    
                    <g transform="translate(20, 120)">
                        <circle cx="0" cy="0" r="6" class="activity-dot-3"/>
                        <text x="15" y="5" class="activity-text">Security Checks</text>
                    </g>
                    
                    <g transform="translate(20, 155)">
                        <circle cx="0" cy="0" r="6" class="activity-dot-4"/>
                        <text x="15" y="5" class="activity-text">Compliance Reports</text>
                    </g>
                </g>
                
                <!-- Connecting arrow to callout -->
                <path d="M 950,400 Q 1000,390 1050,390" class="connector-line" stroke-width="2" stroke-dasharray="8,5" fill="none" opacity="0.6" marker-end="url(#arrowhead)"/>
                
                <!-- Handwritten style notes -->
                <g>
                    <text x="280" y="300" class="sketch-note" transform="rotate(-5 280 300)">Link your account</text>
                    <path d="M 250,310 Q 200,340 180,370" class="sketch-arrow" stroke-width="1.5" fill="none" marker-end="url(#arrow2)"/>
                </g>
                
                <g>
                    <text x="600" y="640" class="sketch-note" transform="rotate(3 600 640)">Find all repos</text>
                    <path d="M 520,630 Q 480,600 460,560" class="sketch-arrow" stroke-width="1.5" fill="none" marker-end="url(#arrow2)"/>
                </g>
            </svg>
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

    /* ============================================
       ADVANCED LOADING SCREEN - MODERN UI
       ============================================ */
    
    .loading-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(ellipse at top, #0A0A14 0%, #000000 50%, #000508 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        overflow: hidden;
        perspective: 1000px;
    }

    /* Animated Particles Background */
    .particles {
        position: absolute;
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    .particle {
        position: absolute;
        width: 4px;
        height: 4px;
        background: radial-gradient(circle, rgba(74, 158, 255, 0.8), transparent);
        border-radius: 50%;
        left: var(--x);
        top: var(--y);
        animation: particleFloat calc(10s + var(--delay)) linear infinite;
        opacity: 0;
    }

    @keyframes particleFloat {
        0% {
            transform: translateY(100vh) scale(0);
            opacity: 0;
        }
        10% { opacity: 1; }
        90% { opacity: 1; }
        100% {
            transform: translateY(-100vh) scale(1);
            opacity: 0;
        }
    }

    .grid-background {
        position: absolute;
        width: 100%;
        height: 100%;
        background-image: 
            linear-gradient(rgba(74, 158, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(74, 158, 255, 0.03) 1px, transparent 1px);
        background-size: 50px 50px;
        transform: perspective(500px) rotateX(60deg) scale(2);
        transform-origin: center center;
        animation: gridMove 20s linear infinite;
        opacity: 0.5;
    }

    @keyframes gridMove {
        0% { background-position: 0 0; }
        100% { background-position: 50px 50px; }
    }

    .loading-content {
        position: relative;
        text-align: center;
        z-index: 1;
        animation: contentFadeIn 1s ease-out;
    }

    @keyframes contentFadeIn {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* 3D Icon Container */
    .loading-icon-container {
        position: relative;
        width: 200px;
        height: 200px;
        margin: 0 auto 3rem;
        display: flex;
        align-items: center;
        justify-content: center;
        transform-style: preserve-3d;
        animation: containerFloat 6s ease-in-out infinite;
    }

    @keyframes containerFloat {
        0%, 100% { transform: translateY(0px) rotateX(0deg); }
        50% { transform: translateY(-15px) rotateX(5deg); }
    }

    .orbit-ring {
        position: absolute;
        border: 2px solid;
        border-radius: 50%;
        border-color: transparent;
        box-shadow: 0 0 20px rgba(74, 158, 255, 0.3);
    }

    .orbit-1 {
        width: 180px;
        height: 180px;
        border-top-color: #4A9EFF;
        border-right-color: #4A9EFF;
        animation: orbitRotate1 4s linear infinite;
    }

    .orbit-2 {
        width: 160px;
        height: 160px;
        border-bottom-color: #FF8B4A;
        border-left-color: #FF8B4A;
        animation: orbitRotate2 3s linear infinite reverse;
    }

    .orbit-3 {
        width: 140px;
        height: 140px;
        border-top-color: rgba(74, 158, 255, 0.5);
        border-bottom-color: rgba(255, 139, 74, 0.5);
        animation: orbitRotate3 5s linear infinite;
    }

    @keyframes orbitRotate1 {
        0% { transform: rotate(0deg) rotateY(60deg); }
        100% { transform: rotate(360deg) rotateY(60deg); }
    }

    @keyframes orbitRotate2 {
        0% { transform: rotate(0deg) rotateX(60deg); }
        100% { transform: rotate(360deg) rotateX(60deg); }
    }

    @keyframes orbitRotate3 {
        0% { transform: rotate(0deg) rotateZ(45deg); }
        100% { transform: rotate(360deg) rotateZ(45deg); }
    }

    .hexagon-frame {
        position: absolute;
        width: 120px;
        height: 120px;
        animation: hexRotate 8s linear infinite;
    }

    .hex-side {
        position: absolute;
        width: 60px;
        height: 2px;
        background: linear-gradient(90deg, transparent, #4A9EFF, transparent);
        top: 50%;
        left: 50%;
        transform-origin: center;
        box-shadow: 0 0 10px #4A9EFF;
    }

    .hex-side:nth-child(1) { transform: translate(-50%, -50%) rotate(0deg) translateX(60px); }
    .hex-side:nth-child(2) { transform: translate(-50%, -50%) rotate(60deg) translateX(60px); }
    .hex-side:nth-child(3) { transform: translate(-50%, -50%) rotate(120deg) translateX(60px); }
    .hex-side:nth-child(4) { transform: translate(-50%, -50%) rotate(180deg) translateX(60px); }
    .hex-side:nth-child(5) { transform: translate(-50%, -50%) rotate(240deg) translateX(60px); }
    .hex-side:nth-child(6) { transform: translate(-50%, -50%) rotate(300deg) translateX(60px); }

    @keyframes hexRotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .icon-wrapper {
        position: relative;
        z-index: 10;
        animation: iconPulse 3s ease-in-out infinite;
    }

    .loading-icon {
        width: 90px;
        height: 90px;
        filter: drop-shadow(0 0 30px rgba(74, 158, 255, 1));
        animation: iconSpin 10s linear infinite;
    }

    @keyframes iconSpin {
        0%, 100% { transform: rotate(0deg) scale(1); }
        50% { transform: rotate(180deg) scale(1.1); }
    }

    @keyframes iconPulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    .icon-glow-layer {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        border-radius: 50%;
        pointer-events: none;
    }

    .glow-1 {
        width: 140px;
        height: 140px;
        background: radial-gradient(circle, rgba(74, 158, 255, 0.4), transparent 70%);
        animation: glowPulse1 2s ease-in-out infinite;
    }

    .glow-2 {
        width: 180px;
        height: 180px;
        background: radial-gradient(circle, rgba(255, 139, 74, 0.3), transparent 70%);
        animation: glowPulse2 3s ease-in-out infinite;
    }

    .glow-3 {
        width: 220px;
        height: 220px;
        background: radial-gradient(circle, rgba(74, 158, 255, 0.2), transparent 70%);
        animation: glowPulse3 4s ease-in-out infinite;
    }

    @keyframes glowPulse1 {
        0%, 100% { opacity: 0.4; transform: translate(-50%, -50%) scale(1); }
        50% { opacity: 0.8; transform: translate(-50%, -50%) scale(1.2); }
    }

    @keyframes glowPulse2 {
        0%, 100% { opacity: 0.3; transform: translate(-50%, -50%) scale(1); }
        50% { opacity: 0.6; transform: translate(-50%, -50%) scale(1.3); }
    }

    @keyframes glowPulse3 {
        0%, 100% { opacity: 0.2; transform: translate(-50%, -50%) scale(1); }
        50% { opacity: 0.5; transform: translate(-50%, -50%) scale(1.4); }
    }

    .energy-pulse {
        position: absolute;
        width: 200px;
        height: 200px;
        border: 2px solid;
        border-radius: 50%;
        opacity: 0;
    }

    .pulse-1 {
        border-color: rgba(74, 158, 255, 0.8);
        animation: energyExpand 2s ease-out infinite;
    }

    .pulse-2 {
        border-color: rgba(255, 139, 74, 0.6);
        animation: energyExpand 2s ease-out 0.6s infinite;
    }

    .pulse-3 {
        border-color: rgba(74, 158, 255, 0.4);
        animation: energyExpand 2s ease-out 1.2s infinite;
    }

    @keyframes energyExpand {
        0% { transform: scale(0.5); opacity: 1; }
        100% { transform: scale(1.5); opacity: 0; }
    }

    /* Professional Info Section */
    .info-section {
        max-width: 420px;
        margin: 0 auto;
        text-align: center;
        animation: infoFadeIn 0.8s ease-out 0.3s backwards;
    }

    @keyframes infoFadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .loading-title {
        font-size: 2.75rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 0.02em;
    }

    .loading-subtitle {
        font-size: 0.875rem;
        color: rgba(255, 255, 255, 0.5);
        letter-spacing: 0.15em;
        text-transform: uppercase;
        font-weight: 500;
        margin-bottom: 2.5rem;
    }

    /* Progress Section */
    .progress-section {
        margin-bottom: 2rem;
    }

    .progress-bar {
        width: 100%;
        height: 3px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        overflow: hidden;
        position: relative;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #4A9EFF 0%, #FF8B4A 50%, #4A9EFF 100%);
        background-size: 200% 100%;
        border-radius: 10px;
        animation: progressFlow 2s ease-in-out infinite;
        box-shadow: 0 0 10px rgba(74, 158, 255, 0.4);
    }

    @keyframes progressFlow {
        0% { width: 0%; background-position: 0% 0%; }
        50% { width: 75%; background-position: 100% 0%; }
        100% { width: 100%; background-position: 200% 0%; }
    }

    /* Status Message */
    .status-message {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background: #4A9EFF;
        border-radius: 50%;
        box-shadow: 0 0 10px rgba(74, 158, 255, 0.6);
        animation: statusPulse 2s ease-in-out infinite;
    }

    @keyframes statusPulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(1.2); }
    }

    .status-message span {
        font-size: 0.875rem;
        color: rgba(255, 255, 255, 0.5);
        font-weight: 400;
        letter-spacing: 0.01em;
    }

    /* Floating Elements */
    .floating-elements {
        position: fixed;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        pointer-events: none;
        z-index: 0;
    }

    .float-element {
        position: absolute;
        font-size: 2rem;
        color: rgba(74, 158, 255, 0.15);
        animation: floatAround 20s ease-in-out infinite;
    }

    .element-1 {
        top: 10%;
        left: 10%;
        animation-delay: 0s;
    }

    .element-2 {
        top: 20%;
        right: 15%;
        animation-delay: 2s;
    }

    .element-3 {
        bottom: 20%;
        left: 15%;
        animation-delay: 4s;
    }

    .element-4 {
        bottom: 15%;
        right: 10%;
        animation-delay: 6s;
    }

    @keyframes floatAround {
        0%, 100% { transform: translate(0, 0) rotate(0deg); opacity: 0.1; }
        25% { transform: translate(50px, -50px) rotate(90deg); opacity: 0.3; }
        50% { transform: translate(0, -100px) rotate(180deg); opacity: 0.1; }
        75% { transform: translate(-50px, -50px) rotate(270deg); opacity: 0.3; }
    }

    /* Legacy spinner for backward compatibility */
    .loading-spinner {
        width: 60px;
        height: 60px;
        border: 3px solid rgba(74, 158, 255, 0.1);
        border-radius: 50%;
        border-top-color: #4A9EFF;
        animation: spin 1s ease-in-out infinite;
        margin: 0 auto 2rem;
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

    /* Profile Dropdown Container */
    .profile-dropdown-container {
        position: relative;
    }

    .user-profile-trigger {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(74, 158, 255, 0.2);
        padding: 0.5rem 1rem;
        border-radius: 12px;
        transition: all 0.3s ease;
        cursor: pointer;
        color: var(--text-primary);
    }

    .user-profile-trigger:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(74, 158, 255, 0.4);
        transform: translateY(-1px);
    }

    .user-profile-trigger[aria-expanded="true"] {
        background: rgba(255, 255, 255, 0.12);
        border-color: rgba(74, 158, 255, 0.5);
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
        flex-shrink: 0;
    }

    .avatar-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .avatar-text {
        color: white;
        font-weight: 600;
        font-size: 1rem;
    }

    .avatar-status {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 10px;
        height: 10px;
        background: #00FF66;
        border: 2px solid var(--bg-primary);
        border-radius: 50%;
        box-shadow: 0 0 0 2px rgba(0, 255, 102, 0.3);
    }

    .user-name-compact {
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text-primary);
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .dropdown-arrow {
        transition: transform 0.3s ease;
        color: var(--text-secondary);
        flex-shrink: 0;
    }

    .dropdown-arrow.open {
        transform: rotate(180deg);
    }

    /* Profile Dropdown Menu */
    .profile-dropdown-menu {
        position: absolute;
        top: calc(100% + 0.5rem);
        right: 0;
        min-width: 280px;
        background: var(--card-bg);
        border: 1px solid rgba(74, 158, 255, 0.2);
        border-radius: 12px;
        box-shadow: 
            0 10px 40px rgba(0, 0, 0, 0.3),
            0 0 0 1px rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        padding: 0.5rem;
        z-index: 1000;
        animation: dropdownSlideIn 0.2s ease-out;
    }

    @keyframes dropdownSlideIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .dropdown-user-info {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.75rem;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.03);
    }

    .dropdown-avatar {
        position: relative;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        overflow: hidden;
        background: linear-gradient(135deg, #4A9EFF 0%, #FF8B4A 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(74, 158, 255, 0.3);
    }

    .dropdown-user-details {
        flex: 1;
        min-width: 0;
    }

    .dropdown-name {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .dropdown-email {
        font-size: 0.8rem;
        color: var(--text-secondary);
        opacity: 0.8;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .dropdown-divider {
        height: 1px;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(74, 158, 255, 0.3),
            transparent
        );
        margin: 0.5rem 0;
    }

    .dropdown-logout-button {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
        background: rgba(239, 68, 68, 0.1);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.2);
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 0.9rem;
        text-align: left;
    }

    .dropdown-logout-button:hover {
        background: rgba(239, 68, 68, 0.2);
        border-color: rgba(239, 68, 68, 0.4);
        transform: translateX(4px);
    }

    .dashboard-container.light .dropdown-logout-button {
        background: rgba(239, 68, 68, 0.08);
        color: #DC2626;
        border-color: rgba(239, 68, 68, 0.15);
    }

    .dashboard-container.light .dropdown-logout-button:hover {
        background: rgba(239, 68, 68, 0.15);
        border-color: rgba(239, 68, 68, 0.3);
    }

    .logout-icon-svg {
        flex-shrink: 0;
        opacity: 0.9;
    }

    .dropdown-logout-button:hover .logout-icon-svg {
        opacity: 1;
    }

    /* Hero Section */
    .hero-section {
        margin-top: 100px;
        padding: 2rem 2rem 1.5rem;
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.3) 0%, rgba(74, 158, 255, 0.1) 100%);
        position: relative;
        z-index: 2;
        margin-bottom: 90px;
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

    /* SVG Workflow Art Section */
    .workflow-art-section {
        padding: 0;
        position: relative;
        z-index: 1;
        min-height: 600px;
        height: calc(100vh - 500px);
        width: 100%;
        display: flex;
        align-items: stretch;
        justify-content: stretch;
        overflow: visible;
    }

    .workflow-svg {
        width: 100%;
        height: 100%;
        min-height: 600px;
        opacity: 0.9;
        transition: opacity 0.3s ease;
    }

    .workflow-svg:hover {
        opacity: 1;
    }

    /* SVG Element Styles - Dark Mode */
    .workflow-svg .flow-gradient-start {
        stop-color: #4A9EFF;
        stop-opacity: 0.3;
    }

    .workflow-svg .flow-gradient-mid {
        stop-color: #5BA3F5;
        stop-opacity: 0.5;
    }

    .workflow-svg .flow-gradient-end {
        stop-color: #4A9EFF;
        stop-opacity: 0.3;
    }

    .workflow-svg .flow-path-main {
        stroke: #4A9EFF;
    }

    .workflow-svg .flow-path-bright {
        stroke: #5BA3F5;
    }

    .workflow-svg .platform-shadow {
        fill: rgba(208, 208, 208, 0.3);
    }

    .workflow-svg .platform-side {
        fill: rgba(232, 232, 232, 0.15);
        stroke: rgba(153, 153, 153, 0.3);
        stroke-width: 1;
    }

    .workflow-svg .platform-top {
        fill: rgba(245, 245, 245, 0.2);
        stroke: rgba(153, 153, 153, 0.3);
        stroke-width: 1;
    }

    .workflow-svg .platform-right {
        fill: rgba(216, 216, 216, 0.15);
        stroke: rgba(153, 153, 153, 0.3);
        stroke-width: 1;
    }

    .workflow-svg .github-bg {
        fill: #24292e;
    }

    .workflow-svg .github-icon {
        fill: #fff;
    }

    .workflow-svg .magnify-circle {
        stroke: var(--text-primary);
    }

    .workflow-svg .magnify-handle {
        stroke: var(--text-primary);
    }

    .workflow-svg .magnify-fill {
        fill: rgba(74, 158, 255, 0.2);
    }

    .workflow-svg .server-layer-1,
    .workflow-svg .server-layer-2,
    .workflow-svg .server-layer-3 {
        fill: #4CAF50;
    }

    .workflow-svg .server-top-1,
    .workflow-svg .server-top-2,
    .workflow-svg .server-top-3 {
        fill: #81C784;
    }

    .workflow-svg .server-mid-1,
    .workflow-svg .server-mid-2,
    .workflow-svg .server-mid-3 {
        fill: #66BB6A;
    }

    .workflow-svg .org-circle {
        fill: #fff;
        stroke: #4CAF50;
    }

    .workflow-svg .org-icon {
        fill: #4CAF50;
    }

    .workflow-svg .window-dot {
        fill: #fff;
    }

    .workflow-svg .scan-line {
        stroke: #81C784;
    }

    .workflow-svg .monitor-stand {
        fill: #757575;
    }

    .workflow-svg .monitor-base {
        fill: #9E9E9E;
    }

    .workflow-svg .monitor-frame {
        fill: #424242;
    }

    .workflow-svg .monitor-screen {
        fill: rgba(255, 255, 255, 0.95);
        stroke: rgba(51, 51, 51, 0.5);
        stroke-width: 1;
    }

    .workflow-svg .dashboard-header {
        fill: #5BA3F5;
    }

    .workflow-svg .security-shield {
        fill: #4CAF50;
        stroke: #2E7D32;
        stroke-width: 1;
    }

    .workflow-svg .shield-check {
        fill: #fff;
    }

    .workflow-svg .chart-bar-1 {
        fill: #4CAF50;
    }

    .workflow-svg .chart-bar-2 {
        fill: #FFC107;
    }

    .workflow-svg .chart-bar-3 {
        fill: #2196F3;
    }

    .workflow-svg .chart-bar-4 {
        fill: #FF5722;
    }

    .workflow-svg .status-green {
        fill: #4CAF50;
    }

    .workflow-svg .status-yellow {
        fill: #FFC107;
    }

    .workflow-svg .badge-blue {
        fill: #2196F3;
    }

    .workflow-svg .badge-green {
        fill: #4CAF50;
    }

    .workflow-svg .badge-check {
        stroke: #fff;
    }

    .workflow-svg .checkmark-text {
        fill: #fff;
        font-size: 20px;
        font-weight: bold;
        font-family: Arial, sans-serif;
    }

    .workflow-svg .sketch-note {
        font-family: 'Comic Sans MS', cursive;
        font-size: 14px;
        fill: var(--text-secondary);
        font-style: italic;
    }

    .workflow-svg .sketch-arrow {
        stroke: var(--text-secondary);
    }

    .workflow-svg .arrow-fill-small {
        fill: var(--text-secondary);
    }

    .workflow-svg .callout-box {
        fill: rgba(255, 255, 255, 0.05);
        stroke: rgba(153, 153, 153, 0.4);
        stroke-width: 1.5;
    }

    .workflow-svg .connector-line {
        stroke: rgba(153, 153, 153, 0.5);
        stroke-width: 2;
    }

    .workflow-svg .arrow-fill {
        fill: rgba(153, 153, 153, 0.6);
    }

    .workflow-svg .step-title {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 18px;
        fill: var(--text-primary);
        font-weight: 600;
    }

    .workflow-svg .step-subtitle {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
        fill: var(--text-secondary);
    }

    .workflow-svg .callout-title {
        font-family: 'Comic Sans MS', cursive;
        font-size: 16px;
        fill: var(--text-primary);
        font-weight: 600;
    }

    .workflow-svg .activity-text {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
        fill: var(--text-secondary);
    }

    .workflow-svg .activity-dot-1 {
        fill: #2196F3;
    }

    .workflow-svg .activity-dot-2 {
        fill: #FF9800;
    }

    .workflow-svg .activity-dot-3 {
        fill: #4CAF50;
    }

    .workflow-svg .activity-dot-4 {
        fill: #9C27B0;
    }

    /* Light Mode SVG Adjustments */
    .dashboard-container.light .workflow-svg .platform-shadow {
        fill: rgba(180, 180, 180, 0.4);
    }

    .dashboard-container.light .workflow-svg .platform-side {
        fill: rgba(232, 232, 232, 0.8);
        stroke: rgba(153, 153, 153, 0.5);
    }

    .dashboard-container.light .workflow-svg .platform-top {
        fill: rgba(245, 245, 245, 0.9);
    }

    .dashboard-container.light .workflow-svg .platform-right {
        fill: rgba(216, 216, 216, 0.8);
    }

    .dashboard-container.light .workflow-svg .monitor-screen {
        fill: rgba(255, 255, 255, 1);
        stroke: rgba(51, 51, 51, 0.3);
    }

    .dashboard-container.light .workflow-svg .callout-box {
        fill: rgba(255, 255, 255, 0.8);
        stroke: rgba(153, 153, 153, 0.5);
    }

    .dashboard-container.light .workflow-svg .connector-line {
        stroke: rgba(100, 100, 100, 0.6);
    }

    .dashboard-container.light .workflow-svg .arrow-fill {
        fill: rgba(100, 100, 100, 0.7);
    }

    .dashboard-container.light .workflow-svg .flow-gradient-start {
        stop-color: #0969da;
        stop-opacity: 0.3;
    }

    .dashboard-container.light .workflow-svg .flow-gradient-mid {
        stop-color: #0969da;
        stop-opacity: 0.5;
    }

    .dashboard-container.light .workflow-svg .flow-gradient-end {
        stop-color: #0969da;
        stop-opacity: 0.3;
    }

    .dashboard-container.light .workflow-svg .flow-path-main {
        stroke: #0969da;
    }

    .dashboard-container.light .workflow-svg .flow-path-bright {
        stroke: #0969da;
    }

    /* Main Dashboard Content */
    .dashboard-main {
        padding: 2rem 0 4rem;
        position: relative;
        z-index: 2;
        margin-bottom: 100px;
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
        margin-top: 100px;
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

        .user-name-compact {
            display: none;
        }

        .profile-dropdown-menu {
            min-width: 260px;
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
    .user-profile-trigger {
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
