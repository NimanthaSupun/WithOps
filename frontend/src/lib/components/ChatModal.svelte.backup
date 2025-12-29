<script>
	import { createEventDispatcher, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { ragAPI } from '$lib/api/rag';
	import { conversationsAPI } from '$lib/api/conversations';
	import { fly, fade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	
	export let isOpen = false;
	export let orgName = '';
	export let repoName = null;
	export let projectName = null;
	export let folderPath = null;
	export let analysisScope = 'unified';
	export let analysisId = null;
	
	const dispatch = createEventDispatcher();
	
	// State
	let question = '';
	let messages = [];
	let conversations = [];
	let currentConversation = null;
	let isLoading = false;
	let errorMessage = '';
	let authToken = null;
	let showSidebar = true;
	let renamingConversationId = null;
	let renameTitle = '';
	let messagesEndRef;
	
	// Get auth token and load conversations when modal opens
	$: if (isOpen && analysisId) {
		initializeChat();
	}
	
	async function initializeChat() {
		authToken = $page.data.user?.accessToken || localStorage.getItem('auth_token');
		if (!authToken) {
			errorMessage = 'Please log in to use the AI Assistant';
			return;
		}
		
		// Load existing conversations
		await loadConversations();
	}
	
	async function loadConversations() {
		try {
			conversations = await conversationsAPI.listConversations({
				analysisId,
				organizationName: orgName,
				token: authToken
			});
		} catch (error) {
			console.error('Failed to load conversations:', error);
		}
	}
	
	async function createNewConversation() {
		messages = [];
		currentConversation = null;
		errorMessage = '';
	}
	
	async function selectConversation(conversation) {
		try {
			currentConversation = conversation;
			errorMessage = '';
			
			// Load conversation messages
			const data = await conversationsAPI.getConversationWithMessages(
				conversation.id,
				authToken
			);
			
			messages = data.messages.map(msg => ({
				role: msg.role,
				content: msg.content,
				sources: msg.sources,
				metadata: msg.metadata,
				timestamp: new Date(msg.created_at)
			}));
			
			scrollToBottom();
		} catch (error) {
			console.error('Failed to load conversation:', error);
			errorMessage = 'Failed to load conversation history';
		}
	}
	
	async function deleteConversation(conversationId, event) {
		event.stopPropagation();
		
		if (!confirm('Are you sure you want to delete this conversation?')) {
			return;
		}
		
		try {
			await conversationsAPI.deleteConversation(conversationId, authToken);
			
			// Remove from list
			conversations = conversations.filter(c => c.id !== conversationId);
			
			// Clear current if deleted
			if (currentConversation?.id === conversationId) {
				createNewConversation();
			}
		} catch (error) {
			console.error('Failed to delete conversation:', error);
			errorMessage = 'Failed to delete conversation';
		}
	}
	
	function startRename(conversation, event) {
		event.stopPropagation();
		renamingConversationId = conversation.id;
		renameTitle = conversation.title;
	}
	
	function focusInput(node) {
		node.focus();
	}
	
	async function saveRename(conversationId) {
		if (!renameTitle.trim()) {
			renamingConversationId = null;
			return;
		}
		
		try {
			await conversationsAPI.updateConversation(
				conversationId,
				{ title: renameTitle.trim() },
				authToken
			);
			
			// Update local list
			conversations = conversations.map(c =>
				c.id === conversationId ? { ...c, title: renameTitle.trim() } : c
			);
			
			if (currentConversation?.id === conversationId) {
				currentConversation = { ...currentConversation, title: renameTitle.trim() };
			}
			
			renamingConversationId = null;
		} catch (error) {
			console.error('Failed to rename conversation:', error);
			errorMessage = 'Failed to rename conversation';
		}
	}
	
	function cancelRename() {
		renamingConversationId = null;
		renameTitle = '';
	}
	
	async function sendMessage() {
		if (!question.trim() || isLoading) return;
		
		if (!authToken) {
			errorMessage = 'Please log in to use the AI Assistant';
			return;
		}
		
		const userMessage = question.trim();
		question = '';
		errorMessage = '';
		
		// Add user message to UI
		messages = [...messages, {
			role: 'user',
			content: userMessage,
			timestamp: new Date()
		}];
		
		isLoading = true;
		scrollToBottom();
		
		try {
			const response = await ragAPI.chat({
				question: userMessage,
				org_name: orgName,
				repo_name: repoName,
				project_name: projectName,
				folder_path: folderPath,
				analysis_scope: analysisScope,
				analysis_id: analysisId,
				conversation_id: currentConversation?.id,
				auto_create_conversation: !currentConversation,
				token: authToken
			});
			
			// If new conversation was created, update state
			if (!currentConversation && response.conversation_id) {
				await loadConversations();
				const newConv = conversations.find(c => c.id === response.conversation_id);
				if (newConv) {
					currentConversation = newConv;
				}
			}
			
			// Add AI response to UI
			messages = [...messages, {
				role: 'assistant',
				content: response.answer,
				sources: response.sources,
				confidence: response.confidence,
				contexts_used: response.contexts_used,
				timestamp: new Date()
			}];
			
			scrollToBottom();
			
		} catch (error) {
			console.error('Chat error:', error);
			errorMessage = error.message || 'Failed to get response. Please try again.';
			
			if (error.message.includes('Authentication')) {
				localStorage.removeItem('auth_token');
				authToken = null;
			}
		} finally {
			isLoading = false;
		}
	}
	
	function scrollToBottom() {
		setTimeout(() => {
			messagesEndRef?.scrollIntoView({ behavior: 'smooth' });
		}, 100);
	}
	
	function handleKeyPress(event) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}
	
	function closeModal() {
		dispatch('close');
	}
	
	function toggleSidebar() {
		showSidebar = !showSidebar;
	}
	
	// Suggested questions
	const suggestedQuestions = [
		"What security practices are implemented in our workflows?",
		"What are the main security findings from the analysis?",
		"How can we improve our DevSecOps maturity score?",
		"What SAST tools are being used?",
		"Are there any security vulnerabilities in our CI/CD pipeline?",
		"What's our current security scanning coverage?"
	];
	
	function useSuggestedQuestion(suggested) {
		question = suggested;
		sendMessage();
	}
</script>

{#if isOpen}
	<div 
		class="modal-backdrop" 
		on:click={closeModal} 
		on:keydown={(e) => e.key === 'Escape' && closeModal()} 
		role="button" 
		tabindex="0"
		transition:fade={{ duration: 200 }}
	>
		<div 
			class="chat-container" 
			class:sidebar-hidden={!showSidebar}
			on:click|stopPropagation 
			on:keydown|stopPropagation 
			role="dialog" 
			tabindex="-1"
			transition:fly={{ y: 50, duration: 300, easing: cubicOut }}
		>
			<!-- Sidebar - Conversation List -->
			<aside class="sidebar" class:hidden={!showSidebar}>
				<div class="sidebar-header">
						<h3>💬 Conversations</h3>
						<button class="btn-new" on:click={createNewConversation} title="New Chat" aria-label="New Chat">
							<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M12 5v14M5 12h14"/>
							</svg>
						</button>
					</div>
					
					<div class="conversations-list">
						{#each conversations as conversation}
							<div 
								class="conversation-item" 
								class:active={currentConversation?.id === conversation.id}
								on:click={() => selectConversation(conversation)}
								on:keydown={(e) => e.key === 'Enter' && selectConversation(conversation)}
								role="button"
								tabindex="0"
							>
								{#if renamingConversationId === conversation.id}
									<input
										type="text"
										bind:value={renameTitle}
										on:click|stopPropagation
										on:keydown={(e) => {
											e.stopPropagation();
											if (e.key === 'Enter') saveRename(conversation.id);
											if (e.key === 'Escape') cancelRename();
										}}
										on:blur={() => saveRename(conversation.id)}
										class="rename-input"
										use:focusInput
									/>
								{:else}
									<div class="conversation-content">
										<div class="conversation-title">{conversation.title}</div>
										<div class="conversation-meta">
											<span class="message-count">{conversation.message_count} messages</span>
											<span class="timestamp">{new Date(conversation.updated_at).toLocaleDateString()}</span>
										</div>
									</div>
									<div class="conversation-actions">
										<button 
											class="action-btn" 
											on:click={(e) => startRename(conversation, e)}
											title="Rename"
											aria-label="Rename conversation"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
												<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
											</svg>
										</button>
										<button 
											class="action-btn delete" 
											on:click={(e) => deleteConversation(conversation.id, e)}
											title="Delete"
											aria-label="Delete conversation"
										>
											<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
											</svg>
										</button>
									</div>
								{/if}
							</div>
						{/each}
						
						{#if conversations.length === 0}
							<div class="empty-conversations">
								<p>No conversations yet</p>
								<p class="hint">Start a new chat to begin</p>
							</div>
						{/if}
					</div>
				</aside>
			
			<!-- Main Chat Area -->
			<main class="chat-main">
				<!-- Header -->
				<header class="chat-header">
					<div class="header-left">
						<button class="btn-toggle" on:click={toggleSidebar} title="Toggle Sidebar" aria-label="Toggle Sidebar">
							<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M3 12h18M3 6h18M3 18h18"/>
							</svg>
						</button>
						<div class="header-info">
							<h2>
								{#if currentConversation}
									{currentConversation.title}
								{:else}
									🤖 AI Assistant
								{/if}
							</h2>
							<div class="context-badges">
								{#if orgName}
									<span class="badge">{orgName}</span>
								{/if}
								{#if repoName}
									<span class="badge">{repoName}</span>
								{/if}
								{#if folderPath}
									<span class="badge">📁 {folderPath}</span>
								{/if}
								<span class="badge scope">{analysisScope}</span>
							</div>
						</div>
					</div>
					<button class="btn-close" on:click={closeModal} title="Close" aria-label="Close">
						<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M18 6L6 18M6 6l12 12"/>
						</svg>
					</button>
				</header>
				
				<!-- Messages Area -->
				<div class="messages-area">
					{#if messages.length === 0}
						<div class="empty-state">
							<div class="welcome-icon">🚀</div>
							<h3>Welcome to DevSecOps AI Assistant</h3>
							<p>I can help you understand your security analysis, workflows, and DevSecOps practices.</p>
							
							<div class="suggested-questions">
								<p class="section-label">Quick Start Questions:</p>
								<div class="suggestions-grid">
									{#each suggestedQuestions as suggested}
										<button 
											class="suggestion-chip" 
											on:click={() => useSuggestedQuestion(suggested)}
										>
											<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<circle cx="12" cy="12" r="10"/>
												<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
												<path d="M12 17h.01"/>
											</svg>
											{suggested}
										</button>
									{/each}
								</div>
							</div>
						</div>
					{:else}
						<div class="messages-list">
							{#each messages as message, i}
								<div 
									class="message-wrapper {message.role}"
									in:fly={{ y: 20, duration: 300, delay: 50 }}
								>
									<div class="message-avatar">
										{#if message.role === 'user'}
											<div class="avatar user-avatar">
												<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
													<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
													<circle cx="12" cy="7" r="4"/>
												</svg>
											</div>
										{:else}
											<div class="avatar ai-avatar">
												<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
													<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
												</svg>
											</div>
										{/if}
									</div>
									
									<div class="message-bubble">
										<div class="message-header">
											<span class="sender-name">
												{message.role === 'user' ? 'You' : 'AI Assistant'}
											</span>
											<span class="message-time">
												{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
											</span>
										</div>
										
										<div class="message-content">
											{message.content}
										</div>
										
										{#if message.role === 'assistant'}
											<div class="message-footer">
												{#if message.confidence}
													<span class="confidence-badge {message.confidence}">
														<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
															<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
														</svg>
														{message.confidence}
													</span>
												{/if}
												{#if message.contexts_used}
													<span class="sources-badge">
														<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
															<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
															<polyline points="14 2 14 8 20 8"/>
														</svg>
														{message.contexts_used} sources
													</span>
												{/if}
												
												{#if message.sources && message.sources.length > 0}
													<details class="sources-details">
														<summary>View Sources ({message.sources.length})</summary>
														<div class="sources-list">
															{#each message.sources as source}
																<div class="source-item">
																	{#if source.type === 'workflow'}
																		<div class="source-icon">📄</div>
																		<div class="source-info">
																			<div class="source-title">{source.file}</div>
																			<div class="source-subtitle">{source.repo}</div>
																			<div class="source-relevance">Relevance: {(source.relevance * 100).toFixed(0)}%</div>
																		</div>
																	{:else if source.type === 'analysis'}
																		<div class="source-icon">📊</div>
																		<div class="source-info">
																			<div class="source-title">{source.analysis_type}</div>
																			<div class="source-subtitle">{source.organization}</div>
																			<div class="source-relevance">Relevance: {(source.relevance * 100).toFixed(0)}%</div>
																		</div>
																	{/if}
																</div>
															{/each}
														</div>
													</details>
												{/if}
											</div>
										{/if}
									</div>
								</div>
							{/each}
							
							{#if isLoading}
								<div class="message-wrapper assistant loading" in:fly={{ y: 20, duration: 300 }}>
									<div class="message-avatar">
										<div class="avatar ai-avatar">
											<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
												<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
											</svg>
										</div>
									</div>
									<div class="message-bubble">
										<div class="typing-indicator">
											<span></span>
											<span></span>
											<span></span>
										</div>
									</div>
								</div>
							{/if}
							
							<div bind:this={messagesEndRef}></div>
						</div>
					{/if}
				</div>
				
				<!-- Error Banner -->
				{#if errorMessage}
					<div class="error-banner" transition:fly={{ y: -20, duration: 300 }}>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
							<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
						</svg>
						{errorMessage}
					</div>
				{/if}
				
				<!-- Input Area -->
				<div class="input-container">
					<div class="input-wrapper">
						<textarea
							bind:value={question}
							on:keydown={handleKeyPress}
							placeholder="Ask anything about your security analysis..."
							disabled={isLoading}
							rows="1"
						></textarea>
						<button 
							class="btn-send" 
							on:click={sendMessage}
							disabled={!question.trim() || isLoading}
							title="Send message"
						>
							{#if isLoading}
								<svg class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M21 12a9 9 0 1 1-6.219-8.56"/>
								</svg>
							{:else}
								<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
									<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
								</svg>
							{/if}
						</button>
					</div>
					<div class="input-hint">
						Press <kbd>Enter</kbd> to send, <kbd>Shift + Enter</kbd> for new line
					</div>
				</div>
			</main>
		</div>
	</div>
{/if}

<style>
	/* Modern Reset */
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}
	
	/* Modal Backdrop */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(8px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 9999;
		padding: 20px;
	}
	
	/* Main Container */
	.chat-container {
		background: #ffffff;
		border-radius: 24px;
		box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
		width: 100%;
		max-width: 1400px;
		height: 90vh;
		display: grid;
		grid-template-columns: 320px 1fr;
		overflow: hidden;
		transition: grid-template-columns 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}
	
	.chat-container.sidebar-hidden {
		grid-template-columns: 0 1fr;
	}
	
	/* Sidebar */
	.sidebar {
		background: linear-gradient(180deg, #f8f9fc 0%, #f1f3f9 100%);
		border-right: 1px solid #e5e7eb;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s;
		transform: translateX(0);
		opacity: 1;
	}
	
	.sidebar.hidden {
		transform: translateX(-100%);
		opacity: 0;
		pointer-events: none;
	}
	
	.sidebar-header {
		padding: 24px 20px;
		border-bottom: 1px solid #e5e7eb;
		display: flex;
		justify-content: space-between;
		align-items: center;
		background: white;
	}
	
	.sidebar-header h3 {
		font-size: 18px;
		font-weight: 700;
		color: #1f2937;
		display: flex;
		align-items: center;
		gap: 8px;
	}
	
	.btn-new {
		width: 36px;
		height: 36px;
		border-radius: 12px;
		border: none;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
	}
	
	.btn-new:hover {
		transform: scale(1.05);
		box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
	}
	
	.conversations-list {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 12px;
		min-height: 0; /* Important for flex scrolling */
	}
	
	.conversations-list::-webkit-scrollbar {
		width: 6px;
	}
	
	.conversations-list::-webkit-scrollbar-track {
		background: transparent;
	}
	
	.conversations-list::-webkit-scrollbar-thumb {
		background: #cbd5e1;
		border-radius: 10px;
	}
	
	.conversations-list::-webkit-scrollbar-thumb:hover {
		background: #94a3b8;
	}
	
	.conversation-item {
		background: white;
		border: 2px solid transparent;
		border-radius: 12px;
		padding: 14px;
		margin-bottom: 8px;
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
	}
	
	.conversation-item:hover {
		background: #f9fafb;
		border-color: #e5e7eb;
		transform: translateX(4px);
	}
	
	.conversation-item.active {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		border-color: #667eea;
	}
	
	.conversation-content {
		flex: 1;
		min-width: 0;
	}
	
	.conversation-title {
		font-weight: 600;
		font-size: 14px;
		margin-bottom: 4px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	
	.conversation-meta {
		display: flex;
		gap: 12px;
		font-size: 12px;
		opacity: 0.7;
	}
	
	.conversation-item.active .conversation-meta {
		opacity: 0.9;
	}
	
	.conversation-actions {
		display: flex;
		gap: 4px;
		opacity: 0;
		transition: opacity 0.2s;
	}
	
	.conversation-item:hover .conversation-actions {
		opacity: 1;
	}
	
	.conversation-item.active .conversation-actions {
		opacity: 0.9;
	}
	
	.action-btn {
		width: 28px;
		height: 28px;
		border: none;
		background: rgba(0, 0, 0, 0.05);
		border-radius: 6px;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
		color: inherit;
	}
	
	.conversation-item.active .action-btn {
		background: rgba(255, 255, 255, 0.2);
	}
	
	.action-btn:hover {
		background: rgba(0, 0, 0, 0.1);
		transform: scale(1.1);
	}
	
	.action-btn.delete:hover {
		background: #fee2e2;
		color: #dc2626;
	}
	
	.rename-input {
		width: 100%;
		padding: 8px;
		border: 2px solid #667eea;
		border-radius: 6px;
		font-size: 14px;
		font-weight: 600;
		font-family: inherit;
	}
	
	.rename-input:focus {
		outline: none;
	}
	
	.empty-conversations {
		text-align: center;
		padding: 48px 20px;
		color: #9ca3af;
	}
	
	.empty-conversations p {
		margin-bottom: 4px;
	}
	
	.empty-conversations .hint {
		font-size: 13px;
		opacity: 0.7;
	}
	
	/* Main Chat Area */
	.chat-main {
		display: flex;
		flex-direction: column;
		background: #fafafa;
		min-height: 0; /* Important for flex scrolling */
		height: 100%;
	}
	
	/* Header */
	.chat-header {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		padding: 20px 28px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		border-bottom: 1px solid rgba(255, 255, 255, 0.1);
	}
	
	.header-left {
		display: flex;
		align-items: center;
		gap: 16px;
		flex: 1;
		min-width: 0;
	}
	
	.btn-toggle {
		width: 40px;
		height: 40px;
		border: none;
		background: rgba(255, 255, 255, 0.15);
		border-radius: 10px;
		color: white;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
		flex-shrink: 0;
	}
	
	.btn-toggle:hover {
		background: rgba(255, 255, 255, 0.25);
	}
	
	.header-info {
		flex: 1;
		min-width: 0;
	}
	
	.header-info h2 {
		font-size: 20px;
		font-weight: 700;
		margin-bottom: 6px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	
	.context-badges {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}
	
	.badge {
		background: rgba(255, 255, 255, 0.2);
		backdrop-filter: blur(10px);
		padding: 4px 12px;
		border-radius: 8px;
		font-size: 12px;
		font-weight: 500;
		border: 1px solid rgba(255, 255, 255, 0.1);
	}
	
	.badge.scope {
		background: rgba(255, 255, 255, 0.3);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}
	
	.btn-close {
		width: 40px;
		height: 40px;
		border: none;
		background: rgba(255, 255, 255, 0.15);
		border-radius: 10px;
		color: white;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
		flex-shrink: 0;
	}
	
	.btn-close:hover {
		background: rgba(255, 255, 255, 0.25);
		transform: rotate(90deg);
	}
	
	/* Messages Area */
	.messages-area {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 24px;
		scroll-behavior: smooth;
		min-height: 0; /* Important for flex scrolling */
		position: relative;
	}
	
	.messages-area::-webkit-scrollbar {
		width: 10px;
	}
	
	.messages-area::-webkit-scrollbar-track {
		background: #f3f4f6;
		border-radius: 10px;
	}
	
	.messages-area::-webkit-scrollbar-thumb {
		background: #cbd5e1;
		border-radius: 10px;
		border: 2px solid #f3f4f6;
	}
	
	.messages-area::-webkit-scrollbar-thumb:hover {
		background: #94a3b8;
	}
	
	/* Empty State */
	.empty-state {
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 32px;
		text-align: center;
		max-width: 800px;
		margin: 0 auto;
		padding: 40px;
	}
	
	.welcome-icon {
		font-size: 64px;
		animation: float 3s ease-in-out infinite;
	}
	
	@keyframes float {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-10px); }
	}
	
	.empty-state h3 {
		font-size: 28px;
		color: #1f2937;
		margin-bottom: 8px;
	}
	
	.empty-state p {
		font-size: 16px;
		color: #6b7280;
		line-height: 1.6;
	}
	
	.suggested-questions {
		width: 100%;
	}
	
	.section-label {
		font-weight: 600;
		color: #4b5563;
		margin-bottom: 16px;
		font-size: 15px;
	}
	
	.suggestions-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 12px;
	}
	
	.suggestion-chip {
		background: white;
		border: 2px solid #e5e7eb;
		border-radius: 12px;
		padding: 16px 20px;
		text-align: left;
		cursor: pointer;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		font-size: 14px;
		color: #374151;
		line-height: 1.5;
		display: flex;
		align-items: flex-start;
		gap: 12px;
		font-family: inherit;
	}
	
	.suggestion-chip svg {
		flex-shrink: 0;
		margin-top: 2px;
		color: #667eea;
	}
	
	.suggestion-chip:hover {
		border-color: #667eea;
		background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%);
		transform: translateY(-4px);
		box-shadow: 0 12px 24px -10px rgba(102, 126, 234, 0.3);
	}
	
	/* Messages List */
	.messages-list {
		max-width: 900px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 24px;
		padding-bottom: 20px; /* Extra space at bottom for better scroll */
		min-height: min-content;
	}
	
	.message-wrapper {
		display: flex;
		gap: 12px;
		animation: slideIn 0.3s ease-out;
	}
	
	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
	
	.message-wrapper.user {
		flex-direction: row-reverse;
	}
	
	.message-avatar {
		flex-shrink: 0;
	}
	
	.avatar {
		width: 40px;
		height: 40px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 20px;
	}
	
	.user-avatar {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}
	
	.ai-avatar {
		background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
		color: white;
	}
	
	.message-bubble {
		flex: 1;
		max-width: 75%;
		animation: bubbleIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
	}
	
	@keyframes bubbleIn {
		from {
			opacity: 0;
			transform: scale(0.8);
		}
		to {
			opacity: 1;
			transform: scale(1);
		}
	}
	
	.message-wrapper.user .message-bubble {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		border-radius: 18px 18px 4px 18px;
		padding: 14px 18px;
	}
	
	.message-wrapper.assistant .message-bubble {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 18px 18px 18px 4px;
		padding: 14px 18px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
	}
	
	.message-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 8px;
	}
	
	.sender-name {
		font-weight: 700;
		font-size: 13px;
	}
	
	.message-wrapper.user .sender-name {
		opacity: 0.9;
	}
	
	.message-wrapper.assistant .sender-name {
		color: #6b7280;
	}
	
	.message-time {
		font-size: 11px;
		opacity: 0.6;
	}
	
	.message-content {
		line-height: 1.6;
		white-space: pre-wrap;
		word-wrap: break-word;
		font-size: 15px;
	}
	
	.message-footer {
		margin-top: 12px;
		padding-top: 12px;
		border-top: 1px solid #f3f4f6;
		display: flex;
		gap: 12px;
		align-items: center;
		flex-wrap: wrap;
		font-size: 12px;
	}
	
	.confidence-badge {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 10px;
		border-radius: 8px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}
	
	.confidence-badge.high {
		background: #d1fae5;
		color: #065f46;
	}
	
	.confidence-badge.medium {
		background: #fef3c7;
		color: #92400e;
	}
	
	.confidence-badge.low {
		background: #fee2e2;
		color: #991b1b;
	}
	
	.sources-badge {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: #6b7280;
	}
	
	.sources-details {
		width: 100%;
		margin-top: 8px;
	}
	
	.sources-details summary {
		cursor: pointer;
		color: #667eea;
		font-weight: 600;
		padding: 6px 0;
		list-style: none;
		display: flex;
		align-items: center;
		gap: 6px;
	}
	
	.sources-details summary::-webkit-details-marker {
		display: none;
	}
	
	.sources-details summary::before {
		content: '▶';
		font-size: 10px;
		transition: transform 0.2s;
	}
	
	.sources-details[open] summary::before {
		transform: rotate(90deg);
	}
	
	.sources-list {
		margin-top: 8px;
		display: grid;
		gap: 8px;
	}
	
	.source-item {
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 10px;
		display: flex;
		gap: 10px;
		align-items: flex-start;
	}
	
	.source-icon {
		font-size: 16px;
		flex-shrink: 0;
	}
	
	.source-info {
		flex: 1;
		min-width: 0;
	}
	
	.source-title {
		font-weight: 600;
		font-size: 13px;
		color: #1f2937;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	
	.source-subtitle {
		font-size: 12px;
		color: #6b7280;
		margin-top: 2px;
	}
	
	.source-relevance {
		font-size: 11px;
		color: #9ca3af;
		margin-top: 2px;
	}
	
	/* Typing Indicator */
	.typing-indicator {
		display: flex;
		gap: 6px;
		padding: 8px 0;
	}
	
	.typing-indicator span {
		width: 8px;
		height: 8px;
		background: #667eea;
		border-radius: 50%;
		animation: typing 1.4s infinite;
	}
	
	.typing-indicator span:nth-child(1) { animation-delay: 0s; }
	.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
	.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
	
	@keyframes typing {
		0%, 60%, 100% {
			transform: translateY(0);
			opacity: 0.4;
		}
		30% {
			transform: translateY(-10px);
			opacity: 1;
		}
	}
	
	/* Error Banner */
	.error-banner {
		background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
		color: #991b1b;
		padding: 14px 24px;
		display: flex;
		align-items: center;
		gap: 10px;
		font-weight: 500;
		font-size: 14px;
		border-top: 1px solid #fecaca;
	}
	
	/* Input Area */
	.input-container {
		padding: 20px 24px;
		background: white;
		border-top: 1px solid #e5e7eb;
	}
	
	.input-wrapper {
		display: flex;
		gap: 12px;
		align-items: flex-end;
		background: #f9fafb;
		border: 2px solid #e5e7eb;
		border-radius: 16px;
		padding: 12px;
		transition: all 0.2s;
	}
	
	.input-wrapper:focus-within {
		border-color: #667eea;
		background: white;
		box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
	}
	
	textarea {
		flex: 1;
		border: none;
		background: transparent;
		font-family: inherit;
		font-size: 15px;
		resize: none;
		max-height: 200px;
		line-height: 1.5;
		color: #1f2937;
	}
	
	textarea:focus {
		outline: none;
	}
	
	textarea::placeholder {
		color: #9ca3af;
	}
	
	textarea:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	
	.btn-send {
		width: 44px;
		height: 44px;
		border: none;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		border-radius: 12px;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		flex-shrink: 0;
	}
	
	.btn-send:hover:not(:disabled) {
		transform: scale(1.05);
		box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
	}
	
	.btn-send:active:not(:disabled) {
		transform: scale(0.95);
	}
	
	.btn-send:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	
	.spinner {
		animation: spin 1s linear infinite;
	}
	
	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}
	
	.input-hint {
		margin-top: 8px;
		font-size: 12px;
		color: #9ca3af;
		text-align: center;
	}
	
	.input-hint kbd {
		background: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		padding: 2px 6px;
		font-family: monospace;
		font-size: 11px;
		color: #6b7280;
	}
	
	/* Scrollbar Styling */
	::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}
	
	::-webkit-scrollbar-track {
		background: transparent;
	}
	
	::-webkit-scrollbar-thumb {
		background: #d1d5db;
		border-radius: 10px;
	}
	
	::-webkit-scrollbar-thumb:hover {
		background: #9ca3af;
	}
	
	/* Responsive */
	@media (max-width: 1024px) {
		.chat-container {
			max-width: 100%;
			height: 100vh;
			border-radius: 0;
		}
		
		.message-bubble {
			max-width: 85%;
		}
	}
	
	@media (max-width: 768px) {
		.chat-container {
			grid-template-columns: 280px 1fr;
		}
		
		.suggestions-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
