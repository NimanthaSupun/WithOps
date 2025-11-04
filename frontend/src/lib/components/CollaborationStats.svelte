<script>
  import { onMount } from 'svelte';
  import { 
    isConnected, 
    onlineUsersCount, 
    others, 
    liveComments 
  } from '$lib/stores/collaboration-yjs.js';
  
  // Props
  export const modelId = ''; // For external reference
  
  // Stats
  let collaborationStats = {
    totalUsers: 0,
    activeUsers: 0,
    commentsCount: 0,
    connectionStatus: 'Disconnected'
  };
  
  // Update stats reactively
  $: {
    collaborationStats = {
      totalUsers: $onlineUsersCount,
      activeUsers: $others.filter(user => 
        user.presence?.cursor || user.presence?.selection
      ).length,
      commentsCount: $liveComments.length,
      connectionStatus: $isConnected ? 'Connected' : 'Disconnected'
    };
  }
  
  let showStats = false;
</script>

<!-- Collaboration Stats Toggle -->
<div class="collaboration-stats-widget">
  <button 
    class="stats-toggle"
    class:connected={$isConnected}
    on:click={() => showStats = !showStats}
    title="Collaboration Statistics">
    🤝 {$onlineUsersCount}
  </button>
  
  {#if showStats}
    <div class="stats-panel">
      <div class="stats-header">
        <h3>Collaboration Stats</h3>
        <button on:click={() => showStats = false}>×</button>
      </div>
      
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-value">{collaborationStats.totalUsers}</div>
          <div class="stat-label">Online Users</div>
        </div>
        
        <div class="stat-item">
          <div class="stat-value">{collaborationStats.activeUsers}</div>
          <div class="stat-label">Active Now</div>
        </div>
        
        <div class="stat-item">
          <div class="stat-value">{collaborationStats.commentsCount}</div>
          <div class="stat-label">Comments</div>
        </div>
        
        <div class="stat-item">
          <div class="stat-value" class:connected={$isConnected}>
            {collaborationStats.connectionStatus}
          </div>
          <div class="stat-label">Status</div>
        </div>
      </div>
      
      <!-- Active Users List -->
      {#if $others.length > 0}
        <div class="active-users-section">
          <h4>Active Users</h4>
          <div class="active-users-list">
            {#each $others as user}
              <div class="active-user">
                <div 
                  class="user-indicator" 
                  style="background-color: {user.presence?.userInfo?.color || '#gray'}">
                </div>
                <span class="user-name">{user.presence?.userInfo?.name || 'Unknown'}</span>
                {#if user.presence?.selection}
                  <span class="user-activity">editing</span>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}
      
      <!-- Collaboration Tips -->
      <div class="collaboration-tips">
        <h4>💡 Collaboration Tips</h4>
        <ul>
          <li>Move your mouse to show your cursor to others</li>
          <li>Right-click to add contextual comments</li>
          <li>See real-time updates from other users</li>
          <li>Multiple users can edit simultaneously</li>
        </ul>
      </div>
    </div>
  {/if}
</div>

<style>
  .collaboration-stats-widget {
    position: relative;
    z-index: 1000;
  }

  .stats-toggle {
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .stats-toggle:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  }

  .stats-toggle.connected {
    border-color: #22c55e;
    background: #f0fdf4;
  }

  .stats-panel {
    position: absolute;
    top: 100%;
    left: 0;
    margin-top: 8px;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
    width: 320px;
    overflow: hidden;
    z-index: 1001;
  }

  .stats-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
  }

  .stats-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #374151;
  }

  .stats-header button {
    background: none;
    border: none;
    font-size: 18px;
    color: #6b7280;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 20px;
  }

  .stat-item {
    text-align: center;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #374151;
    margin-bottom: 4px;
  }

  .stat-value.connected {
    color: #22c55e;
  }

  .stat-label {
    font-size: 12px;
    color: #6b7280;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .active-users-section {
    padding: 0 20px 20px;
    border-top: 1px solid #f3f4f6;
    margin-top: 0;
  }

  .active-users-section h4 {
    margin: 16px 0 12px 0;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }

  .active-users-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .active-user {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
  }

  .user-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .user-name {
    color: #374151;
    font-weight: 500;
    flex: 1;
  }

  .user-activity {
    font-size: 12px;
    color: #6b7280;
    font-style: italic;
  }

  .collaboration-tips {
    background: #f9fafb;
    padding: 16px 20px;
    border-top: 1px solid #e5e7eb;
  }

  .collaboration-tips h4 {
    margin: 0 0 12px 0;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }

  .collaboration-tips ul {
    margin: 0;
    padding-left: 16px;
    font-size: 13px;
    color: #6b7280;
    line-height: 1.5;
  }

  .collaboration-tips li {
    margin-bottom: 4px;
  }
</style>
