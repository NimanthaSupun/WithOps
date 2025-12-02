<script>
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { githubClient } from '$lib/github.js';
    import { isDarkMode } from '$lib/stores.js';

    // Get org name from route params
    let orgName = $derived($page.params.org);
    
    // State
    let loading = $state(true);
    let error = $state(null);
    let organization = $state(null);
    let members = $state([]);
    let invitations = $state([]);
    
    // Invite form state
    let inviteEmail = $state('');
    let inviteRole = $state('member');
    let isInviting = $state(false);
    let inviteError = $state(null);
    let inviteSuccess = $state(null);
    
    // Remove member state
    let removingMemberId = $state(null);
    
    // Cancel invitation state
    let cancellingInvitationId = $state(null);
    
    // Dark mode
    let darkMode = $state(false);
    
    $effect(() => {
        const unsubscribe = isDarkMode.subscribe(value => {
            darkMode = value;
        });
        return unsubscribe;
    });

    onMount(async () => {
        await loadTeamData();
    });

    async function loadTeamData() {
        try {
            loading = true;
            error = null;
            
            const result = await githubClient.getOrganizationInvitations(orgName);
            
            if (result.error) {
                if (result.error.includes('not the owner')) {
                    error = 'Only the organization owner can manage team members.';
                } else {
                    error = result.error;
                }
                loading = false;
                return;
            }
            
            organization = result.organization;
            members = result.members || [];
            invitations = result.invitations || [];
            loading = false;
            
        } catch (err) {
            console.error('Error loading team data:', err);
            error = err.message || 'Failed to load team data';
            loading = false;
        }
    }

    async function handleInvite() {
        if (!inviteEmail.trim()) {
            inviteError = 'Please enter an email address';
            return;
        }
        
        // Basic email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(inviteEmail)) {
            inviteError = 'Please enter a valid email address';
            return;
        }
        
        try {
            isInviting = true;
            inviteError = null;
            inviteSuccess = null;
            
            const result = await githubClient.createInvitation(orgName, inviteEmail.trim(), inviteRole);
            
            if (result.success) {
                inviteSuccess = `Invitation sent to ${inviteEmail}`;
                inviteEmail = '';
                inviteRole = 'member';
                
                // Reload data to show new invitation
                await loadTeamData();
                
                // Clear success message after 5 seconds
                setTimeout(() => {
                    inviteSuccess = null;
                }, 5000);
            } else {
                inviteError = result.error || 'Failed to send invitation';
            }
        } catch (err) {
            console.error('Error sending invitation:', err);
            inviteError = err.message || 'Failed to send invitation';
        } finally {
            isInviting = false;
        }
    }

    async function handleCancelInvitation(invitationId) {
        try {
            cancellingInvitationId = invitationId;
            
            const result = await githubClient.cancelInvitation(orgName, invitationId);
            
            if (result.success) {
                await loadTeamData();
            } else {
                error = result.error || 'Failed to cancel invitation';
            }
        } catch (err) {
            console.error('Error cancelling invitation:', err);
            error = err.message || 'Failed to cancel invitation';
        } finally {
            cancellingInvitationId = null;
        }
    }

    async function handleRemoveMember(memberId, memberName) {
        if (!confirm(`Are you sure you want to remove ${memberName} from ${orgName}?`)) {
            return;
        }
        
        try {
            removingMemberId = memberId;
            
            const result = await githubClient.removeMember(orgName, memberId);
            
            if (result.success) {
                await loadTeamData();
            } else {
                error = result.error || 'Failed to remove member';
            }
        } catch (err) {
            console.error('Error removing member:', err);
            error = err.message || 'Failed to remove member';
        } finally {
            removingMemberId = null;
        }
    }

    function getStatusBadgeClass(status) {
        switch (status) {
            case 'pending':
                return 'badge-pending';
            case 'accepted':
                return 'badge-success';
            case 'declined':
                return 'badge-error';
            case 'expired':
                return 'badge-expired';
            case 'cancelled':
                return 'badge-cancelled';
            default:
                return 'badge-default';
        }
    }

    function formatDate(dateString) {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function getTimeUntilExpiry(expiresAt) {
        const now = new Date();
        const expiry = new Date(expiresAt);
        const diff = expiry - now;
        
        if (diff <= 0) return 'Expired';
        
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        
        if (days > 0) return `${days}d ${hours}h remaining`;
        return `${hours}h remaining`;
    }
</script>

<svelte:head>
    <title>Team Management - {orgName} | WithOps</title>
</svelte:head>

<div class="team-page" class:dark={darkMode}>
    <!-- Header -->
    <div class="page-header">
        <button class="back-button" onclick={() => goto('/organizations')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Back to Organizations
        </button>
        
        {#if organization}
            <div class="org-header">
                <img src={organization.avatar_url || '/default-org.png'} alt={organization.name} class="org-avatar" />
                <div class="org-info">
                    <h1>{organization.name || organization.login}</h1>
                    <p class="org-login">@{organization.login}</p>
                </div>
            </div>
        {/if}
    </div>

    {#if loading}
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Loading team data...</p>
        </div>
    {:else if error}
        <div class="error-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <h3>Access Denied</h3>
            <p>{error}</p>
            <button class="btn-secondary" onclick={() => goto('/organizations')}>
                Return to Organizations
            </button>
        </div>
    {:else}
        <div class="team-content">
            <!-- Invite Section -->
            <section class="invite-section">
                <h2>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="8.5" cy="7" r="4"/>
                        <line x1="20" y1="8" x2="20" y2="14"/>
                        <line x1="23" y1="11" x2="17" y2="11"/>
                    </svg>
                    Invite Team Member
                </h2>
                
                <div class="invite-form">
                    <div class="form-row">
                        <div class="form-group email-input">
                            <label for="invite-email">Email Address</label>
                            <input 
                                type="email" 
                                id="invite-email"
                                bind:value={inviteEmail}
                                placeholder="colleague@company.com"
                                disabled={isInviting}
                            />
                        </div>
                        
                        <div class="form-group role-select">
                            <label for="invite-role">Role</label>
                            <select id="invite-role" bind:value={inviteRole} disabled={isInviting}>
                                <option value="member">Member</option>
                                <option value="owner">Owner</option>
                            </select>
                        </div>
                        
                        <button 
                            class="btn-primary invite-btn"
                            onclick={handleInvite}
                            disabled={isInviting || !inviteEmail.trim()}
                        >
                            {#if isInviting}
                                <span class="btn-spinner"></span>
                                Sending...
                            {:else}
                                Send Invitation
                            {/if}
                        </button>
                    </div>
                    
                    {#if inviteError}
                        <div class="form-message error">{inviteError}</div>
                    {/if}
                    
                    {#if inviteSuccess}
                        <div class="form-message success">{inviteSuccess}</div>
                    {/if}
                </div>
                
                <p class="invite-note">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="16" x2="12" y2="12"/>
                        <line x1="12" y1="8" x2="12.01" y2="8"/>
                    </svg>
                    The invited user will see a notification when they log in with the same email address. Invitations expire after 7 days.
                </p>
            </section>

            <!-- Pending Invitations -->
            {#if invitations.filter(i => i.status === 'pending').length > 0}
                <section class="invitations-section">
                    <h2>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <polyline points="12,6 12,12 16,14"/>
                        </svg>
                        Pending Invitations
                    </h2>
                    
                    <div class="invitations-list">
                        {#each invitations.filter(i => i.status === 'pending') as invitation}
                            <div class="invitation-card">
                                <div class="invitation-info">
                                    <span class="invitation-email">{invitation.invited_email}</span>
                                    <span class="invitation-meta">
                                        Invited by {invitation.invited_by_name} • {getTimeUntilExpiry(invitation.expires_at)}
                                    </span>
                                </div>
                                <div class="invitation-actions">
                                    <span class="badge {getStatusBadgeClass(invitation.status)}">{invitation.status}</span>
                                    <button 
                                        class="btn-danger-small"
                                        onclick={() => handleCancelInvitation(invitation.id)}
                                        disabled={cancellingInvitationId === invitation.id}
                                    >
                                        {cancellingInvitationId === invitation.id ? 'Cancelling...' : 'Cancel'}
                                    </button>
                                </div>
                            </div>
                        {/each}
                    </div>
                </section>
            {/if}

            <!-- Team Members -->
            <section class="members-section">
                <h2>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="9" cy="7" r="4"/>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                    </svg>
                    Team Members ({members.length})
                </h2>
                
                <div class="members-list">
                    {#each members as member}
                        <div class="member-card">
                            <div class="member-avatar">
                                {#if member.avatar_url}
                                    <img src={member.avatar_url} alt={member.name || member.email} />
                                {:else}
                                    <div class="avatar-placeholder">
                                        {(member.name || member.email || '?').charAt(0).toUpperCase()}
                                    </div>
                                {/if}
                            </div>
                            <div class="member-info">
                                <span class="member-name">{member.name || member.email}</span>
                                <span class="member-email">{member.email}</span>
                            </div>
                            <div class="member-role">
                                <span class="badge badge-role-{member.role}">{member.role}</span>
                            </div>
                            <div class="member-actions">
                                {#if member.role !== 'owner'}
                                    <button 
                                        class="btn-danger-small"
                                        onclick={() => handleRemoveMember(member.id, member.name || member.email)}
                                        disabled={removingMemberId === member.id}
                                    >
                                        {removingMemberId === member.id ? 'Removing...' : 'Remove'}
                                    </button>
                                {:else}
                                    <span class="owner-badge">Organization Owner</span>
                                {/if}
                            </div>
                        </div>
                    {/each}
                </div>
            </section>

            <!-- Invitation History -->
            {#if invitations.filter(i => i.status !== 'pending').length > 0}
                <section class="history-section">
                    <h2>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 20h9"/>
                            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                        </svg>
                        Invitation History
                    </h2>
                    
                    <div class="history-list">
                        {#each invitations.filter(i => i.status !== 'pending') as invitation}
                            <div class="history-item">
                                <span class="history-email">{invitation.invited_email}</span>
                                <span class="badge {getStatusBadgeClass(invitation.status)}">{invitation.status}</span>
                                <span class="history-date">{formatDate(invitation.accepted_at || invitation.created_at)}</span>
                            </div>
                        {/each}
                    </div>
                </section>
            {/if}
        </div>
    {/if}
</div>

<style>
    .team-page {
        min-height: 100vh;
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        padding: 2rem;
    }
    
    .team-page.dark {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e4e6eb;
    }
    
    .page-header {
        max-width: 1000px;
        margin: 0 auto 2rem;
    }
    
    .back-button {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: transparent;
        border: 1px solid #ddd;
        border-radius: 8px;
        cursor: pointer;
        color: #666;
        margin-bottom: 1.5rem;
        transition: all 0.2s ease;
    }
    
    .dark .back-button {
        border-color: #444;
        color: #aaa;
    }
    
    .back-button:hover {
        background: #f5f5f5;
        border-color: #ccc;
    }
    
    .dark .back-button:hover {
        background: #333;
        border-color: #555;
    }
    
    .org-header {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .org-avatar {
        width: 64px;
        height: 64px;
        border-radius: 12px;
        object-fit: cover;
    }
    
    .org-info h1 {
        margin: 0;
        font-size: 1.75rem;
        font-weight: 600;
    }
    
    .org-login {
        margin: 0.25rem 0 0;
        color: #666;
        font-size: 0.9rem;
    }
    
    .dark .org-login {
        color: #999;
    }
    
    .loading-state,
    .error-state {
        max-width: 1000px;
        margin: 0 auto;
        text-align: center;
        padding: 4rem 2rem;
    }
    
    .error-state svg {
        color: #ef4444;
        margin-bottom: 1rem;
    }
    
    .error-state h3 {
        margin: 0 0 0.5rem;
        color: #ef4444;
    }
    
    .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid #e5e7eb;
        border-top-color: #3b82f6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 1rem;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    .team-content {
        max-width: 1000px;
        margin: 0 auto;
    }
    
    section {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    
    .dark section {
        background: #242442;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    section h2 {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 0 0 1.25rem;
        font-size: 1.25rem;
        font-weight: 600;
    }
    
    section h2 svg {
        color: #3b82f6;
    }
    
    /* Invite Form */
    .invite-form {
        margin-bottom: 1rem;
    }
    
    .form-row {
        display: flex;
        gap: 1rem;
        align-items: flex-end;
        flex-wrap: wrap;
    }
    
    .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .form-group label {
        font-size: 0.875rem;
        font-weight: 500;
        color: #666;
    }
    
    .dark .form-group label {
        color: #aaa;
    }
    
    .email-input {
        flex: 1;
        min-width: 250px;
    }
    
    .role-select {
        min-width: 120px;
    }
    
    input, select {
        padding: 0.75rem 1rem;
        border: 1px solid #ddd;
        border-radius: 8px;
        font-size: 1rem;
        background: white;
        transition: all 0.2s ease;
    }
    
    .dark input, .dark select {
        background: #1a1a2e;
        border-color: #444;
        color: #e4e6eb;
    }
    
    input:focus, select:focus {
        outline: none;
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .btn-primary {
        padding: 0.75rem 1.5rem;
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        transition: all 0.2s ease;
    }
    
    .btn-primary:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    .btn-primary:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
    
    .btn-secondary {
        padding: 0.75rem 1.5rem;
        background: #f5f5f5;
        color: #333;
        border: 1px solid #ddd;
        border-radius: 8px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .dark .btn-secondary {
        background: #333;
        color: #e4e6eb;
        border-color: #444;
    }
    
    .btn-danger-small {
        padding: 0.5rem 1rem;
        background: transparent;
        color: #ef4444;
        border: 1px solid #ef4444;
        border-radius: 6px;
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .btn-danger-small:hover:not(:disabled) {
        background: #ef4444;
        color: white;
    }
    
    .btn-danger-small:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
    
    .btn-spinner {
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-top-color: white;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    .form-message {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin-top: 1rem;
        font-size: 0.9rem;
    }
    
    .form-message.error {
        background: #fef2f2;
        color: #dc2626;
        border: 1px solid #fecaca;
    }
    
    .dark .form-message.error {
        background: rgba(220, 38, 38, 0.1);
        border-color: rgba(220, 38, 38, 0.3);
    }
    
    .form-message.success {
        background: #f0fdf4;
        color: #16a34a;
        border: 1px solid #bbf7d0;
    }
    
    .dark .form-message.success {
        background: rgba(22, 163, 74, 0.1);
        border-color: rgba(22, 163, 74, 0.3);
    }
    
    .invite-note {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #666;
        font-size: 0.875rem;
        margin: 0;
    }
    
    .dark .invite-note {
        color: #999;
    }
    
    .invite-note svg {
        color: #3b82f6;
        flex-shrink: 0;
    }
    
    /* Invitations List */
    .invitations-list,
    .members-list {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    
    .invitation-card,
    .member-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem;
        background: #f9fafb;
        border-radius: 10px;
        flex-wrap: wrap;
        gap: 1rem;
    }
    
    .dark .invitation-card,
    .dark .member-card {
        background: #1a1a2e;
    }
    
    .invitation-info {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    
    .invitation-email {
        font-weight: 500;
    }
    
    .invitation-meta {
        font-size: 0.8rem;
        color: #666;
    }
    
    .dark .invitation-meta {
        color: #999;
    }
    
    .invitation-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    /* Members List */
    .member-card {
        display: grid;
        grid-template-columns: auto 1fr auto auto;
        gap: 1rem;
        align-items: center;
    }
    
    @media (max-width: 768px) {
        .member-card {
            grid-template-columns: auto 1fr;
        }
        
        .member-role,
        .member-actions {
            grid-column: 2;
        }
    }
    
    .member-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        overflow: hidden;
    }
    
    .member-avatar img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    .avatar-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        font-weight: 600;
        font-size: 1.25rem;
    }
    
    .member-info {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    
    .member-name {
        font-weight: 500;
    }
    
    .member-email {
        font-size: 0.85rem;
        color: #666;
    }
    
    .dark .member-email {
        color: #999;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: capitalize;
    }
    
    .badge-pending {
        background: #fef3c7;
        color: #d97706;
    }
    
    .badge-success {
        background: #d1fae5;
        color: #059669;
    }
    
    .badge-error,
    .badge-cancelled {
        background: #fee2e2;
        color: #dc2626;
    }
    
    .badge-expired {
        background: #f3f4f6;
        color: #6b7280;
    }
    
    .badge-role-owner {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: white;
    }
    
    .badge-role-member {
        background: #dbeafe;
        color: #2563eb;
    }
    
    .owner-badge {
        font-size: 0.8rem;
        color: #666;
        font-style: italic;
    }
    
    .dark .owner-badge {
        color: #999;
    }
    
    /* History */
    .history-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .history-item {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.75rem;
        background: #f9fafb;
        border-radius: 8px;
        font-size: 0.9rem;
    }
    
    .dark .history-item {
        background: #1a1a2e;
    }
    
    .history-email {
        flex: 1;
    }
    
    .history-date {
        color: #666;
        font-size: 0.8rem;
    }
    
    .dark .history-date {
        color: #999;
    }
</style>
