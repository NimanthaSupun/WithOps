<script>
  import { onMount, onDestroy } from 'svelte';
  import { 
    others, 
    myPresence, 
    isConnected, 
    onlineUsersCount,
    userColors,
    updatePresence,
    addComment 
  } from '$lib/stores/collaboration-yjs.js';
  
  // Props
  export const modelId = ''; // For external reference only
  export let currentUser = { name: 'Anonymous', avatar: '', color: '#000000' };
  
  // Component state
  let showUsersList = false;
  let showCommentDialog = false;
  let commentText = '';
  let commentPosition = { x: 0, y: 0 };
  
  // Track mouse movement for cursor presence
  let mouseMoveTimeout;
  
  function handleMouseMove(event) {
    clearTimeout(mouseMoveTimeout);
    
    // Update presence with cursor position
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    updatePresence({
      cursor: { x, y }
    });
    
    // Clear cursor after 1 second of no movement
    mouseMoveTimeout = setTimeout(() => {
      updatePresence({ cursor: null });
    }, 1000);
  }
  
  function handleRightClick(event) {
    event.preventDefault();
    commentPosition = {
      x: event.clientX,
      y: event.clientY
    };
    showCommentDialog = true;
  }
  
  function submitComment() {
    if (commentText.trim()) {
      addComment({
        text: commentText.trim(),
        author: currentUser.name,
        position: commentPosition,
        type: 'general'
      });
      commentText = '';
      showCommentDialog = false;
    }
  }
  
  function generateInitials(name) {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .substring(0, 2) || 'AN';
  }
  
  onDestroy(() => {
    clearTimeout(mouseMoveTimeout);
  });
</script>

<!-- Collaboration Status Bar -->
<div class="collaboration-status-bar">
  <!-- Connection Status -->
  <div class="connection-status" class:connected={$isConnected}>
    <div class="status-indicator" class:online={$isConnected}></div>
    <span class="status-text">
      {$isConnected ? 'Connected' : 'Offline'}
    </span>
  </div>
  
  <!-- Online Users Counter -->
  <button class="users-counter" 
          on:click={() => showUsersList = !showUsersList}
          aria-label="Toggle online users list">
    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
    </svg>
    <span>{$onlineUsersCount} online</span>
  </button>
  
  <!-- Online Users List -->
  {#if showUsersList}
    <div class="users-list-dropdown">
      <div class="users-list-header">
        <h3>Online Users ({$onlineUsersCount})</h3>
      </div>
      
      <!-- Current User -->
      <div class="user-item current-user">
        <div class="user-avatar" style="background-color: {currentUser.color}">
          {generateInitials(currentUser.name)}
        </div>
        <span class="user-name">{currentUser.name} (You)</span>
      </div>
      
      <!-- Other Users -->
      {#each $others as user}
        {#if user.presence?.userInfo}
          <div class="user-item">
            <div class="user-avatar" style="background-color: {user.presence.userInfo.color}">
              {generateInitials(user.presence.userInfo.name)}
            </div>
            <span class="user-name">{user.presence.userInfo.name}</span>
            {#if user.presence.selection}
              <span class="user-activity">editing</span>
            {/if}
          </div>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<!-- Live Cursors Overlay -->
<div class="live-cursors-overlay" 
     role="presentation"
     on:mousemove={handleMouseMove}
     on:contextmenu={handleRightClick}>
  {#each $others as user}
    {#if user.presence?.cursor && user.presence?.userInfo}
      <div class="live-cursor" 
           style="left: {user.presence.cursor.x}px; top: {user.presence.cursor.y}px;">
        <svg class="cursor-icon" style="color: {user.presence.userInfo.color}" 
             viewBox="0 0 24 24" fill="currentColor">
          <path d="M7.4 2.5c-.8 0-1.1.9-.5 1.4l6.5 5.7-3.5 1.4c-.4.2-.5.7-.2 1l2.8 3.5c.3.4.9.4 1.2 0l.9-1.2 2.8.7c.5.1.9-.3.8-.8l-1.2-15.1c-.1-.6-.8-.9-1.3-.5L7.4 2.5z"/>
        </svg>
        <div class="cursor-label" style="background-color: {user.presence.userInfo.color}">
          {user.presence.userInfo.name}
        </div>
      </div>
    {/if}
  {/each}
</div>

<!-- Comment Dialog -->
{#if showCommentDialog}
  <div class="comment-dialog-overlay" 
       role="dialog" 
       aria-label="Add comment dialog"
       tabindex="-1"
       on:click={() => showCommentDialog = false}
       on:keydown={(e) => e.key === 'Escape' && (showCommentDialog = false)}>
    <div class="comment-dialog" 
         role="presentation"
         style="left: {commentPosition.x}px; top: {commentPosition.y}px;"
         on:click|stopPropagation
         on:keydown|stopPropagation>
      <div class="comment-header">
        <h3>Add Comment</h3>
        <button on:click={() => showCommentDialog = false}>×</button>
      </div>
      <textarea 
        bind:value={commentText} 
        placeholder="Type your comment here..."
        rows="3"></textarea>
      <div class="comment-actions">
        <button class="cancel-btn" on:click={() => showCommentDialog = false}>
          Cancel
        </button>
        <button class="submit-btn" on:click={submitComment} disabled={!commentText.trim()}>
          Add Comment
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .collaboration-status-bar {
    position: fixed;
    top: 20px;
    left: 900px;
    z-index: 1000;
    display: flex;
    align-items: center;
    gap: 12px;
    background: white;
    padding: 8px 16px;
    border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    border: 1px solid #e5e7eb;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    color: #6b7280;
  }

  .status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #ef4444;
    transition: background-color 0.2s;
  }

  .status-indicator.online {
    background-color: #22c55e;
  }

  .users-counter {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    color: #374151;
    transition: background-color 0.2s;
    position: relative;
    background: none;
    border: none;
    font-family: inherit;
  }

  .users-counter:hover {
    background-color: #f3f4f6;
  }

  .users-list-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    margin-top: 8px;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    min-width: 200px;
    max-height: 300px;
    overflow-y: auto;
    z-index: 1001;
  }

  .users-list-header {
    padding: 12px 16px;
    border-bottom: 1px solid #e5e7eb;
  }

  .users-list-header h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }

  .user-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-bottom: 1px solid #f3f4f6;
  }

  .user-item:last-child {
    border-bottom: none;
  }

  .user-item.current-user {
    background-color: #f9fafb;
  }

  .user-avatar {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 10px;
    font-weight: 600;
    overflow: hidden;
  }

  .user-name {
    font-size: 14px;
    color: #374151;
    flex: 1;
  }

  .user-activity {
    font-size: 12px;
    color: #6b7280;
    font-style: italic;
  }

  .live-cursors-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 999;
  }

  .live-cursor {
    position: absolute;
    pointer-events: none;
    z-index: 999;
    transform: translate(-2px, -2px);
  }

  .cursor-icon {
    width: 20px;
    height: 20px;
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
  }

  .cursor-label {
    position: absolute;
    top: 20px;
    left: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    color: white;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .comment-dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .comment-dialog {
    position: fixed;
    background: white;
    border-radius: 8px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    width: 300px;
    transform: translate(-150px, -50px);
  }

  .comment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
  }

  .comment-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #374151;
  }

  .comment-header button {
    background: none;
    border: none;
    font-size: 20px;
    color: #6b7280;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .comment-dialog textarea {
    width: 100%;
    padding: 16px;
    border: none;
    resize: vertical;
    font-family: inherit;
    font-size: 14px;
    outline: none;
  }

  .comment-actions {
    display: flex;
    gap: 8px;
    padding: 16px;
    justify-content: flex-end;
  }

  .cancel-btn, .submit-btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .cancel-btn {
    background: white;
    border: 1px solid #d1d5db;
    color: #374151;
  }

  .cancel-btn:hover {
    background: #f9fafb;
  }

  .submit-btn {
    background: #3b82f6;
    border: 1px solid #3b82f6;
    color: white;
  }

  .submit-btn:hover:not(:disabled) {
    background: #2563eb;
  }

  .submit-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
