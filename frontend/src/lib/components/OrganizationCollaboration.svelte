<script>
    import { onMount, createEventDispatcher } from 'svelte';
    import { page } from '$app/stores';
    import { writable } from 'svelte/store';
    import { getAuthClient } from '$lib/auth.js';
    
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9060';
    
    export let isOpen = false;
    export let currentUser = null;
    
    const dispatch = createEventDispatcher();
    
    // Stores
    const organizationMembers = writable([]);
    const selectedMembers = writable(new Set());
    const isLoading = writable(false);
    const error = writable(null);
    
    // Get organization from URL
    $: organization = $page.params.org;
    $: modelId = $page.params.model_id;
    
    // Component state
    let inviteMessage = '';
    let searchQuery = '';
    
    // Reactive filtered members
    $: filteredMembers = $organizationMembers.filter(member => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            member.name?.toLowerCase().includes(query) ||
            member.email?.toLowerCase().includes(query) ||
            member.github_username?.toLowerCase().includes(query)
        );
    });
    
    // Load organization members when component opens
    $: if (isOpen && organization) {
        loadOrganizationMembers();
    }
    
    async function loadOrganizationMembers() {
        if (!organization) return;
        
        isLoading.set(true);
        error.set(null);
        
        try {
            // Get Auth0 client and token
            const authClient = await getAuthClient();
            const token = await authClient.getTokenSilently();
            
            const response = await fetch(`${API_BASE_URL}/api/collaboration/organization/${organization}/members`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load organization members: ${response.statusText}`);
            }
            
            const members = await response.json();
            
            // Filter out current user from the list
            const filteredMembers = members.filter(member => member.user_id !== currentUser?.sub);
            
            organizationMembers.set(filteredMembers);
        } catch (err) {
            console.error('❌ Failed to load organization members:', err);
            error.set(err.message);
        } finally {
            isLoading.set(false);
        }
    }
    
    function toggleMemberSelection(memberId) {
        selectedMembers.update(selected => {
            const newSelected = new Set(selected);
            if (newSelected.has(memberId)) {
                newSelected.delete(memberId);
            } else {
                newSelected.add(memberId);
            }
            return newSelected;
        });
    }
    
    async function sendInvitations() {
        if ($selectedMembers.size === 0) {
            error.set('Please select at least one member to invite');
            return;
        }
        
        isLoading.set(true);
        error.set(null);
        
        try {
            const inviteData = {
                organization,
                model_id: modelId,
                invited_user_ids: Array.from($selectedMembers),
                message: inviteMessage || undefined
            };
            
            const response = await fetch(`${API_BASE_URL}/api/collaboration/invite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify(inviteData)
            });
            
            if (!response.ok) {
                throw new Error(`Failed to send invitations: ${response.statusText}`);
            }
            
            const session = await response.json();
            
            // Dispatch success event
            dispatch('invitationsSent', {
                session,
                invitedCount: $selectedMembers.size
            });
            
            // Reset form
            selectedMembers.set(new Set());
            inviteMessage = '';
            isOpen = false;
            
        } catch (err) {
            console.error('❌ Failed to send invitations:', err);
            error.set(err.message);
        } finally {
            isLoading.set(false);
        }
    }
    
    function closeModal() {
        isOpen = false;
        selectedMembers.set(new Set());
        inviteMessage = '';
        error.set(null);
    }
    
    // Format last login time
    function formatLastLogin(lastLogin) {
        if (!lastLogin) return 'Never';
        const date = new Date(lastLogin);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        return date.toLocaleDateString();
    }
</script>

<!-- Modal backdrop -->
{#if isOpen}
    <div 
        class="collaboration-modal-backdrop" 
        role="button" 
        tabindex="0"
        on:click={closeModal}
        on:keydown={(e) => e.key === 'Escape' && closeModal()}
    >
        <div 
            class="collaboration-modal" 
            role="dialog"
            tabindex="-1"
            aria-labelledby="modal-title"
            on:click|stopPropagation
            on:keydown|stopPropagation
        >
            <!-- Modal Header -->
            <div class="modal-header">
                <h2 id="modal-title">🤝 Invite Organization Members</h2>
                <button class="close-btn" on:click={closeModal}>&times;</button>
            </div>
            
            <!-- Organization Info -->
            <div class="organization-info">
                <span class="org-badge">🏢 {organization}</span>
                <span class="model-badge">📊 Model: {modelId}</span>
            </div>
            
            <!-- Error Display -->
            {#if $error}
                <div class="error-message">
                    ⚠️ {$error}
                </div>
            {/if}
            
            <!-- Loading State -->
            {#if $isLoading}
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>Loading organization members...</p>
                </div>
            {:else}
                <!-- Search Bar -->
                <div class="search-bar">
                    <input
                        type="text"
                        placeholder="🔍 Search members..."
                        bind:value={searchQuery}
                        class="search-input"
                    />
                </div>
                
                <!-- Members List -->
                <div class="members-list">
                    <h3>Select Members to Invite ({$selectedMembers.size} selected)</h3>
                    
                    {#if filteredMembers.length === 0}
                        <div class="no-members">
                            {#if $organizationMembers.length === 0}
                                No other members found in this organization.
                            {:else}
                                No members match your search.
                            {/if}
                        </div>
                    {:else}
                        <div class="members-grid">
                            {#each filteredMembers as member (member.user_id)}
                                <button 
                                    class="member-card"
                                    class:selected={$selectedMembers.has(member.user_id)}
                                    on:click={() => toggleMemberSelection(member.user_id)}
                                    type="button"
                                    aria-pressed={$selectedMembers.has(member.user_id)}
                                >
                                    <div class="member-avatar">
                                        {#if member.avatar_url}
                                            <img src={member.avatar_url} alt={member.name || member.email} />
                                        {:else}
                                            <div class="default-avatar">
                                                {(member.name || member.email).charAt(0).toUpperCase()}
                                            </div>
                                        {/if}
                                        
                                        {#if member.is_online}
                                            <div class="online-indicator"></div>
                                        {/if}
                                    </div>
                                    
                                    <div class="member-info">
                                        <div class="member-name">
                                            {member.name || member.email.split('@')[0]}
                                        </div>
                                        <div class="member-email">{member.email}</div>
                                        {#if member.github_username}
                                            <div class="member-github">@{member.github_username}</div>
                                        {/if}
                                        <div class="member-last-login">
                                            Last login: {formatLastLogin(member.last_login)}
                                        </div>
                                    </div>
                                    
                                    <div class="selection-indicator">
                                        {#if $selectedMembers.has(member.user_id)}
                                            ✓
                                        {/if}
                                    </div>
                                </button>
                            {/each}
                        </div>
                    {/if}
                </div>
                
                <!-- Invitation Message -->
                <div class="invitation-message">
                    <label for="invite-message">Optional Message:</label>
                    <textarea
                        id="invite-message"
                        bind:value={inviteMessage}
                        placeholder="Add a personal message to your invitation..."
                        rows="3"
                    ></textarea>
                </div>
                
                <!-- Action Buttons -->
                <div class="modal-actions">
                    <button 
                        class="btn-secondary" 
                        on:click={closeModal}
                        disabled={$isLoading}
                    >
                        Cancel
                    </button>
                    <button 
                        class="btn-primary" 
                        on:click={sendInvitations}
                        disabled={$selectedMembers.size === 0 || $isLoading}
                    >
                        {#if $isLoading}
                            Sending...
                        {:else}
                            Send Invitations ({$selectedMembers.size})
                        {/if}
                    </button>
                </div>
            {/if}
        </div>
    </div>
{/if}

<style>
    .collaboration-modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
        backdrop-filter: blur(4px);
    }
    
    .collaboration-modal {
        background: var(--surface-1, #ffffff);
        border-radius: 12px;
        width: 90%;
        max-width: 800px;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
        border: 1px solid var(--border-color, #e1e5e9);
    }
    
    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 24px;
        border-bottom: 1px solid var(--border-color, #e1e5e9);
        background: var(--surface-2, #f8f9fa);
        border-radius: 12px 12px 0 0;
    }
    
    .modal-header h2 {
        margin: 0;
        color: var(--text-1, #1f2937);
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    .close-btn {
        background: none;
        border: none;
        font-size: 2rem;
        cursor: pointer;
        color: var(--text-2, #6b7280);
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        transition: all 0.2s ease;
    }
    
    .close-btn:hover {
        background: var(--surface-3, #f3f4f6);
        color: var(--text-1, #1f2937);
    }
    
    .organization-info {
        padding: 16px 24px;
        display: flex;
        gap: 12px;
        background: var(--surface-1, #ffffff);
        border-bottom: 1px solid var(--border-color, #e1e5e9);
    }
    
    .org-badge, .model-badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .org-badge {
        background: var(--primary-100, #dbeafe);
        color: var(--primary-700, #1d4ed8);
    }
    
    .model-badge {
        background: var(--success-100, #dcfce7);
        color: var(--success-700, #15803d);
    }
    
    .error-message {
        margin: 16px 24px;
        padding: 12px 16px;
        background: var(--error-100, #fee2e2);
        color: var(--error-700, #b91c1c);
        border-radius: 8px;
        border-left: 4px solid var(--error-500, #ef4444);
    }
    
    .loading-state {
        padding: 48px 24px;
        text-align: center;
        color: var(--text-2, #6b7280);
    }
    
    .spinner {
        width: 32px;
        height: 32px;
        border: 3px solid var(--border-color, #e1e5e9);
        border-top: 3px solid var(--primary-500, #3b82f6);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 16px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .search-bar {
        padding: 16px 24px;
        border-bottom: 1px solid var(--border-color, #e1e5e9);
    }
    
    .search-input {
        width: 100%;
        padding: 10px 16px;
        border: 1px solid var(--border-color, #e1e5e9);
        border-radius: 8px;
        font-size: 0.875rem;
        background: var(--surface-1, #ffffff);
        color: var(--text-1, #1f2937);
    }
    
    .search-input:focus {
        outline: none;
        border-color: var(--primary-500, #3b82f6);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .members-list {
        padding: 24px;
    }
    
    .members-list h3 {
        margin: 0 0 16px 0;
        color: var(--text-1, #1f2937);
        font-size: 1.125rem;
        font-weight: 600;
    }
    
    .no-members {
        padding: 32px;
        text-align: center;
        color: var(--text-2, #6b7280);
        font-style: italic;
    }
    
    .members-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 12px;
    }
    
    .member-card {
        display: flex;
        align-items: center;
        padding: 16px;
        border: 2px solid var(--border-color, #e1e5e9);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        background: var(--surface-1, #ffffff);
        width: 100%;
        text-align: left;
        font-family: inherit;
        font-size: inherit;
    }
    
    .member-card:hover {
        border-color: var(--primary-300, #93c5fd);
        background: var(--primary-50, #eff6ff);
    }
    
    .member-card.selected {
        border-color: var(--primary-500, #3b82f6);
        background: var(--primary-100, #dbeafe);
    }
    
    .member-avatar {
        position: relative;
        margin-right: 12px;
        flex-shrink: 0;
    }
    
    .member-avatar img {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        object-fit: cover;
    }
    
    .default-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: var(--primary-500, #3b82f6);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 1.25rem;
    }
    
    .online-indicator {
        position: absolute;
        bottom: 2px;
        right: 2px;
        width: 12px;
        height: 12px;
        background: var(--success-500, #10b981);
        border: 2px solid white;
        border-radius: 50%;
    }
    
    .member-info {
        flex: 1;
        min-width: 0;
    }
    
    .member-name {
        font-weight: 600;
        color: var(--text-1, #1f2937);
        margin-bottom: 2px;
    }
    
    .member-email {
        font-size: 0.875rem;
        color: var(--text-2, #6b7280);
        margin-bottom: 2px;
    }
    
    .member-github {
        font-size: 0.875rem;
        color: var(--primary-600, #2563eb);
        margin-bottom: 2px;
    }
    
    .member-last-login {
        font-size: 0.75rem;
        color: var(--text-3, #9ca3af);
    }
    
    .selection-indicator {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: var(--primary-500, #3b82f6);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        opacity: 0;
        transition: opacity 0.2s ease;
    }
    
    .member-card.selected .selection-indicator {
        opacity: 1;
    }
    
    .invitation-message {
        padding: 0 24px 24px;
    }
    
    .invitation-message label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: var(--text-1, #1f2937);
    }
    
    .invitation-message textarea {
        width: 100%;
        padding: 12px 16px;
        border: 1px solid var(--border-color, #e1e5e9);
        border-radius: 8px;
        font-size: 0.875rem;
        font-family: inherit;
        resize: vertical;
        min-height: 80px;
        background: var(--surface-1, #ffffff);
        color: var(--text-1, #1f2937);
    }
    
    .invitation-message textarea:focus {
        outline: none;
        border-color: var(--primary-500, #3b82f6);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .modal-actions {
        display: flex;
        gap: 12px;
        justify-content: flex-end;
        padding: 24px;
        border-top: 1px solid var(--border-color, #e1e5e9);
        background: var(--surface-2, #f8f9fa);
        border-radius: 0 0 12px 12px;
    }
    
    .btn-secondary {
        padding: 10px 20px;
        border: 1px solid var(--border-color, #e1e5e9);
        border-radius: 8px;
        background: var(--surface-1, #ffffff);
        color: var(--text-1, #1f2937);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .btn-secondary:hover:not(:disabled) {
        background: var(--surface-3, #f3f4f6);
        border-color: var(--text-3, #9ca3af);
    }
    
    .btn-primary {
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        background: var(--primary-500, #3b82f6);
        color: white;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .btn-primary:hover:not(:disabled) {
        background: var(--primary-600, #2563eb);
    }
    
    .btn-primary:disabled,
    .btn-secondary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
</style>
