<script>
	import { createEventDispatcher } from 'svelte';
	import { page } from '$app/stores';
	import { ragAPI } from '$lib/api/rag';
	import { conversationsAPI } from '$lib/api/conversations';
	import { fly, fade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { isDarkMode } from '$lib/stores.js';

	let {
		isOpen = $bindable(false),
		orgName = '',
		repoName = null,
		projectName = null,
		folderPath = null,
		analysisScope = 'unified',
		analysisId = null
	} = $props();

	const dispatch = createEventDispatcher();

	// State
	let question = $state('');
	let messages = $state([]);
	let conversations = $state([]);
	let currentConversation = $state(null);
	let isLoading = $state(false);
	let errorMessage = $state('');
	let authToken = $state(null);
	let showSidebar = $state(true);
	let renamingConversationId = $state(null);
	let renameTitle = $state('');
	let messagesEndRef = $state();
	let darkMode = $state(false);

	// Subscribe to the global theme store
	isDarkMode.subscribe((value) => {
		darkMode = value;
	});

	// Get auth token and load conversations when modal opens
	$effect(() => {
		if (isOpen && analysisId) {
			initializeChat();
		}
	});

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
			const data = await conversationsAPI.getConversationWithMessages(conversation.id, authToken);

			messages = data.messages.map((msg) => ({
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
			conversations = conversations.filter((c) => c.id !== conversationId);

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
			conversations = conversations.map((c) =>
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
		messages = [
			...messages,
			{
				role: 'user',
				content: userMessage,
				timestamp: new Date()
			}
		];

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
				const newConv = conversations.find((c) => c.id === response.conversation_id);
				if (newConv) {
					currentConversation = newConv;
				}
			}

			// Add AI response to UI
			messages = [
				...messages,
				{
					role: 'assistant',
					content: response.answer,
					sources: response.sources,
					confidence: response.confidence,
					contexts_used: response.contexts_used,
					timestamp: new Date()
				}
			];

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
		'What security practices are implemented in our workflows?',
		'What are the main security findings from the analysis?',
		'How can we improve our DevSecOps maturity score?',
		'What SAST tools are being used?',
		'Are there any security vulnerabilities in our CI/CD pipeline?',
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
		onclick={closeModal}
		onkeydown={(e) => e.key === 'Escape' && closeModal()}
		role="button"
		tabindex="0"
		transition:fade={{ duration: 200 }}
	>
		<div
			class="chat-container {darkMode ? 'dark' : 'light'}"
			class:sidebar-hidden={!showSidebar}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			tabindex="-1"
			transition:fly={{ y: 50, duration: 300, easing: cubicOut }}
		>
			<!-- Sidebar - Conversation History -->
			<aside class="sidebar" class:hidden={!showSidebar}>
				<div class="sidebar-header">
					<h3>
						<svg
							class="header-icon"
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
						</svg>
						Conversations
					</h3>
					<button
						class="btn-new"
						onclick={createNewConversation}
						title="New Chat"
						aria-label="New Chat"
					>
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2.5"
						>
							<path d="M12 5v14M5 12h14" />
						</svg>
					</button>
				</div>

				<div class="conversations-list">
					{#each conversations as conversation (conversation.id)}
						<div
							class="conversation-item"
							class:active={currentConversation?.id === conversation.id}
							onclick={() => selectConversation(conversation)}
							onkeydown={(e) => e.key === 'Enter' && selectConversation(conversation)}
							role="button"
							tabindex="0"
						>
							{#if renamingConversationId === conversation.id}
								<input
									type="text"
									bind:value={renameTitle}
									onclick={(e) => e.stopPropagation()}
									onkeydown={(e) => {
										e.stopPropagation();
										if (e.key === 'Enter') saveRename(conversation.id);
										if (e.key === 'Escape') cancelRename();
									}}
									onblur={() => saveRename(conversation.id)}
									class="rename-input"
									use:focusInput
								/>
							{:else}
								<div class="conversation-content">
									<svg
										class="conversation-icon"
										width="16"
										height="16"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
									>
										<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
									</svg>
									<div class="conversation-info">
										<div class="conversation-title">{conversation.title}</div>
										<div class="conversation-meta">
											<span class="message-count">{conversation.message_count} messages</span>
											<span class="separator">•</span>
											<span class="timestamp"
												>{new Date(conversation.updated_at).toLocaleDateString()}</span
											>
										</div>
									</div>
								</div>
								<div class="conversation-actions">
									<button
										class="action-btn"
										onclick={(e) => startRename(conversation, e)}
										title="Rename"
										aria-label="Rename conversation"
									>
										<svg
											width="14"
											height="14"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
										>
											<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
											<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
										</svg>
									</button>
									<button
										class="action-btn delete"
										onclick={(e) => deleteConversation(conversation.id, e)}
										title="Delete"
										aria-label="Delete conversation"
									>
										<svg
											width="14"
											height="14"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
										>
											<path
												d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
											/>
										</svg>
									</button>
								</div>
							{/if}
						</div>
					{/each}

					{#if conversations.length === 0}
						<div class="empty-conversations">
							<svg
								class="empty-icon"
								width="48"
								height="48"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.5"
							>
								<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
							</svg>
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
						<button
							class="btn-toggle"
							onclick={toggleSidebar}
							title="Toggle Sidebar"
							aria-label="Toggle Sidebar"
						>
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
							>
								<path d="M3 12h18M3 6h18M3 18h18" />
							</svg>
						</button>
						<div class="header-info">
							<h2>
								{#if currentConversation}
									{currentConversation.title}
								{:else}
									<svg
										class="title-icon"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="currentColor"
									>
										<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
									</svg>
									AI Assistant
								{/if}
							</h2>
							<div class="context-badges">
								{#if orgName}
									<span class="badge badge-org">
										<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
											<path
												d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
											/>
										</svg>
										{orgName}
									</span>
								{/if}
								{#if repoName}
									<span class="badge badge-repo">
										<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
											<path
												d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
											/>
										</svg>
										{repoName}
									</span>
								{/if}
								{#if folderPath}
									<span class="badge badge-folder">
										<svg
											width="12"
											height="12"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
										>
											<path
												d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
											/>
										</svg>
										{folderPath}
									</span>
								{/if}
								<span class="badge badge-scope">
									<svg
										width="12"
										height="12"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
									>
										<circle cx="12" cy="12" r="10" />
										<path d="M2 12h20" />
									</svg>
									{analysisScope}
								</span>
							</div>
						</div>
					</div>
					<button class="btn-close" onclick={closeModal} title="Close" aria-label="Close">
						<svg
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M18 6L6 18M6 6l12 12" />
						</svg>
					</button>
				</header>

				<!-- Messages Area -->
				<div class="messages-area">
					{#if messages.length === 0}
						<div class="empty-state">
							<div class="welcome-visual">
								<div class="ai-orb">
									<div class="orb-ring ring-1"></div>
									<div class="orb-ring ring-2"></div>
									<div class="orb-ring ring-3"></div>
									<svg
										class="orb-icon"
										width="48"
										height="48"
										viewBox="0 0 24 24"
										fill="currentColor"
									>
										<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
									</svg>
								</div>
							</div>
							<h3>Welcome to DevSecOps AI Assistant</h3>
							<p>
								I can help you understand your security analysis, workflows, and DevSecOps
								practices.
							</p>

							<div class="suggested-questions">
								<p class="section-label">Quick Start Questions:</p>
								<div class="suggestions-grid">
									{#each suggestedQuestions as suggested (suggested)}
										<button class="suggestion-chip" onclick={() => useSuggestedQuestion(suggested)}>
											<svg
												width="16"
												height="16"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
											>
												<circle cx="12" cy="12" r="10" />
												<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
												<path d="M12 17h.01" />
											</svg>
											{suggested}
										</button>
									{/each}
								</div>
							</div>
						</div>
					{:else}
						<div class="messages-list">
							{#each messages as message (message.timestamp)}
								<div
									class="message-wrapper {message.role}"
									in:fly={{ y: 20, duration: 300, delay: 50 }}
								>
									<div class="message-avatar">
										{#if message.role === 'user'}
											<div class="avatar user-avatar">
												<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
													<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
													<circle cx="12" cy="7" r="4" />
												</svg>
											</div>
										{:else}
											<div class="avatar ai-avatar">
												<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
													<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
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
												{message.timestamp.toLocaleTimeString([], {
													hour: '2-digit',
													minute: '2-digit'
												})}
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
															<path
																d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
															/>
														</svg>
														{message.confidence}
													</span>
												{/if}
												{#if message.contexts_used}
													<span class="sources-badge">
														<svg
															width="12"
															height="12"
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="2"
														>
															<path
																d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
															/>
															<polyline points="14 2 14 8 20 8" />
														</svg>
														{message.contexts_used} sources
													</span>
												{/if}

												{#if message.sources && message.sources.length > 0}
													<details class="sources-details">
														<summary>
															<svg
																width="14"
																height="14"
																viewBox="0 0 24 24"
																fill="none"
																stroke="currentColor"
																stroke-width="2"
															>
																<path d="M9 18l6-6-6-6" />
															</svg>
															View Sources ({message.sources.length})
														</summary>
														<div class="sources-list">
															{#each message.sources as source (source.file ?? source.analysis_type)}
																<div class="source-item">
																	{#if source.type === 'workflow'}
																		<div class="source-icon">
																			<svg
																				width="16"
																				height="16"
																				viewBox="0 0 24 24"
																				fill="none"
																				stroke="currentColor"
																				stroke-width="2"
																			>
																				<path
																					d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
																				/>
																				<polyline points="14 2 14 8 20 8" />
																			</svg>
																		</div>
																		<div class="source-info">
																			<div class="source-title">{source.file}</div>
																			<div class="source-subtitle">{source.repo}</div>
																			<div class="source-relevance">
																				<div class="relevance-bar">
																					<div
																						class="relevance-fill"
																						style="width: {source.relevance * 100}%"
																					></div>
																				</div>
																				<span>{(source.relevance * 100).toFixed(0)}%</span>
																			</div>
																		</div>
																	{:else if source.type === 'analysis'}
																		<div class="source-icon">
																			<svg
																				width="16"
																				height="16"
																				viewBox="0 0 24 24"
																				fill="none"
																				stroke="currentColor"
																				stroke-width="2"
																			>
																				<path
																					d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
																				/>
																			</svg>
																		</div>
																		<div class="source-info">
																			<div class="source-title">{source.analysis_type}</div>
																			<div class="source-subtitle">{source.organization}</div>
																			<div class="source-relevance">
																				<div class="relevance-bar">
																					<div
																						class="relevance-fill"
																						style="width: {source.relevance * 100}%"
																					></div>
																				</div>
																				<span>{(source.relevance * 100).toFixed(0)}%</span>
																			</div>
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
											<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
												<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
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
						<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
							<path
								d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"
							/>
						</svg>
						<span>{errorMessage}</span>
					</div>
				{/if}

				<!-- Input Area -->
				<div class="input-container">
					<div class="input-wrapper">
						<textarea
							bind:value={question}
							onkeydown={handleKeyPress}
							placeholder="Ask anything about your security analysis..."
							disabled={isLoading}
							rows="1"
						></textarea>
						<button
							class="btn-send"
							onclick={sendMessage}
							disabled={!question.trim() || isLoading}
							title="Send message"
							aria-label="Send message"
						>
							{#if isLoading}
								<svg
									class="spinner"
									width="20"
									height="20"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2.5"
								>
									<path d="M21 12a9 9 0 1 1-6.219-8.56" />
								</svg>
							{:else}
								<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
									<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
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
	/* ================================================
	   WITHOPS PROFESSIONAL DESIGN SYSTEM — CHAT MODAL
	   Matte Engineering Pattern | Inter + JetBrains Mono
	   ================================================ */

	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	/* ---------- THEME VARIABLES ---------- */

	.chat-container {
		--bg-app: #000000;
		--bg-surface: #020202;
		--bg-surface-alt: #050505;
		--bg-elevated: #0a0a0a;
		--accent: #00adef;
		--accent-hover: #00c4ff;
		--text-primary: #f8fafc;
		--text-secondary: #94a3b8;
		--text-muted: #475569;
		--border: rgba(255, 255, 255, 0.06);
		--border-accent: rgba(0, 173, 239, 0.25);
		--success: #10b981;
		--error: #ef4444;
		--warning: #f59e0b;
		--shadow: rgba(0, 0, 0, 0.4);
		--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
	}

	.chat-container.light {
		--bg-app: #ffffff;
		--bg-surface: #f8fafc;
		--bg-surface-alt: #f1f5f9;
		--bg-elevated: #ffffff;
		--accent: #0082b4;
		--accent-hover: #006a94;
		--text-primary: #0f172a;
		--text-secondary: #475569;
		--text-muted: #94a3b8;
		--border: rgba(0, 0, 0, 0.08);
		--border-accent: rgba(0, 130, 180, 0.25);
		--shadow: rgba(0, 0, 0, 0.06);
	}

	/* ---------- MODAL BACKDROP ---------- */

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.7);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 9999;
		padding: 24px;
	}

	/* ---------- MAIN CONTAINER ---------- */

	.chat-container {
		background: var(--bg-app);
		border: 1px solid var(--border);
		border-radius: 16px;
		width: 100%;
		max-width: 1300px;
		height: 88vh;
		max-height: 860px;
		display: grid;
		grid-template-columns: 300px 1fr;
		overflow: hidden;
		transition: grid-template-columns 0.25s ease;
		font-family: var(--font-sans);
		color: var(--text-primary);
	}

	.chat-container.sidebar-hidden {
		grid-template-columns: 0 1fr;
	}

	/* ---------- SIDEBAR ---------- */

	.sidebar {
		background: var(--bg-surface);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		transition:
			transform 0.25s ease,
			opacity 0.2s ease;
	}

	.sidebar.hidden {
		transform: translateX(-100%);
		opacity: 0;
		pointer-events: none;
	}

	.sidebar-header {
		padding: 16px;
		border-bottom: 1px solid var(--border);
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.sidebar-header h3 {
		font-size: 0.8125rem;
		font-weight: 600;
		font-family: var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text-secondary);
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.sidebar-header .header-icon {
		color: var(--accent);
		flex-shrink: 0;
		width: 16px;
		height: 16px;
	}

	.btn-new {
		width: 32px;
		height: 32px;
		border-radius: 8px;
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		color: var(--accent);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
	}

	.btn-new:hover {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
		transform: translateY(-1px);
	}

	/* Conversations List */

	.conversations-list {
		flex: 1;
		overflow-y: auto;
		padding: 8px;
		min-height: 0;
	}

	.conversations-list::-webkit-scrollbar {
		width: 4px;
	}

	.conversations-list::-webkit-scrollbar-track {
		background: transparent;
	}

	.conversations-list::-webkit-scrollbar-thumb {
		background: var(--border);
		border-radius: 4px;
	}

	.conversation-item {
		background: transparent;
		border: 1px solid transparent;
		border-radius: 8px;
		padding: 10px 12px;
		margin-bottom: 2px;
		cursor: pointer;
		transition: all 0.15s ease;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
	}

	.conversation-item:hover {
		background: var(--bg-surface-alt);
		border-color: var(--border);
	}

	.conversation-item.active {
		background: var(--bg-surface-alt);
		border-color: var(--border-accent);
	}

	.conversation-content {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.conversation-icon {
		flex-shrink: 0;
		opacity: 0.4;
		width: 14px;
		height: 14px;
		color: var(--text-muted);
	}

	.conversation-item.active .conversation-icon {
		opacity: 0.8;
		color: var(--accent);
	}

	.conversation-info {
		flex: 1;
		min-width: 0;
	}

	.conversation-title {
		font-weight: 500;
		font-size: 0.8125rem;
		color: var(--text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		line-height: 1.4;
	}

	.conversation-meta {
		display: flex;
		gap: 6px;
		align-items: center;
		font-size: 0.6875rem;
		font-family: var(--font-mono);
		color: var(--text-muted);
		margin-top: 2px;
	}

	.conversation-item.active .conversation-title {
		color: var(--accent);
	}

	.separator {
		opacity: 0.4;
	}

	.conversation-actions {
		display: flex;
		gap: 2px;
		opacity: 0;
		transition: opacity 0.15s;
	}

	.conversation-item:hover .conversation-actions {
		opacity: 1;
	}

	.conversation-item.active .conversation-actions {
		opacity: 0.8;
	}

	.action-btn {
		width: 26px;
		height: 26px;
		border: none;
		background: transparent;
		border-radius: 6px;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
		color: var(--text-muted);
	}

	.action-btn:hover {
		background: var(--bg-surface-alt);
		color: var(--text-secondary);
	}

	.action-btn.delete:hover {
		background: rgba(239, 68, 68, 0.1);
		color: var(--error);
	}

	.rename-input {
		width: 100%;
		padding: 6px 8px;
		border: 1px solid var(--accent);
		border-radius: 6px;
		font-size: 0.8125rem;
		font-family: var(--font-sans);
		background: var(--bg-app);
		color: var(--text-primary);
		outline: none;
	}

	.empty-conversations {
		text-align: center;
		padding: 48px 16px;
		color: var(--text-muted);
	}

	.empty-icon {
		margin: 0 auto 12px;
		opacity: 0.25;
		color: var(--text-muted);
		width: 40px;
		height: 40px;
	}

	.empty-conversations p {
		margin-bottom: 4px;
		font-size: 0.8125rem;
		color: var(--text-secondary);
	}

	.empty-conversations .hint {
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	/* ---------- MAIN CHAT AREA ---------- */

	.chat-main {
		display: flex;
		flex-direction: column;
		background: var(--bg-app);
		min-height: 0;
		height: 100%;
	}

	/* Header */

	.chat-header {
		background: var(--bg-surface);
		color: var(--text-primary);
		padding: 12px 20px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		border-bottom: 1px solid var(--border);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 12px;
		flex: 1;
		min-width: 0;
	}

	.btn-toggle {
		width: 34px;
		height: 34px;
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		border-radius: 8px;
		color: var(--text-secondary);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s ease;
		flex-shrink: 0;
	}

	.btn-toggle:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.header-info {
		flex: 1;
		min-width: 0;
	}

	.header-info h2 {
		font-size: 0.9375rem;
		font-weight: 600;
		margin-bottom: 6px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		display: flex;
		align-items: center;
		gap: 8px;
		color: var(--text-primary);
	}

	.title-icon {
		color: var(--accent);
		flex-shrink: 0;
		width: 20px;
		height: 20px;
	}

	.context-badges {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}

	.badge {
		background: var(--bg-surface-alt);
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 0.6875rem;
		font-family: var(--font-mono);
		font-weight: 500;
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		gap: 4px;
		color: var(--text-muted);
	}

	.badge svg {
		opacity: 0.5;
		flex-shrink: 0;
	}

	.badge-scope {
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--accent);
		border-color: var(--border-accent);
	}

	.btn-close {
		width: 34px;
		height: 34px;
		border: 1px solid var(--border);
		background: var(--bg-surface-alt);
		border-radius: 8px;
		color: var(--text-secondary);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s ease;
		flex-shrink: 0;
	}

	.btn-close:hover {
		background: rgba(239, 68, 68, 0.1);
		border-color: var(--error);
		color: var(--error);
	}

	/* ---------- MESSAGES AREA ---------- */

	.messages-area {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 20px;
		scroll-behavior: smooth;
		min-height: 0;
	}

	.messages-area::-webkit-scrollbar {
		width: 4px;
	}

	.messages-area::-webkit-scrollbar-track {
		background: transparent;
	}

	.messages-area::-webkit-scrollbar-thumb {
		background: var(--border);
		border-radius: 4px;
	}

	/* Empty State */

	.empty-state {
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 24px;
		text-align: center;
		max-width: 720px;
		margin: 0 auto;
		padding: 32px;
	}

	.welcome-visual {
		position: relative;
	}

	.ai-orb {
		position: relative;
		width: 80px;
		height: 80px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.orb-ring {
		position: absolute;
		border: 1px solid var(--border);
		border-radius: 50%;
	}

	.ring-1 {
		width: 80px;
		height: 80px;
		border-color: var(--border-accent);
	}

	.ring-2 {
		width: 64px;
		height: 64px;
		border-color: var(--border);
	}

	.ring-3 {
		width: 48px;
		height: 48px;
		border-color: var(--border);
	}

	.orb-icon {
		color: var(--accent);
		width: 32px;
		height: 32px;
	}

	.empty-state h3 {
		font-size: 1.25rem;
		color: var(--text-primary);
		font-weight: 600;
		letter-spacing: -0.01em;
	}

	.empty-state > p {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.6;
		max-width: 440px;
	}

	.suggested-questions {
		width: 100%;
	}

	.section-label {
		font-weight: 600;
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-muted);
		margin-bottom: 12px;
	}

	.suggestions-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: 8px;
	}

	.suggestion-chip {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 12px 14px;
		text-align: left;
		cursor: pointer;
		transition: all 0.15s ease;
		font-size: 0.8125rem;
		color: var(--text-primary);
		line-height: 1.5;
		display: flex;
		align-items: flex-start;
		gap: 10px;
		font-family: var(--font-sans);
	}

	.suggestion-chip svg {
		flex-shrink: 0;
		margin-top: 2px;
		color: var(--accent);
		width: 14px;
		height: 14px;
	}

	.suggestion-chip:hover {
		border-color: var(--border-accent);
		background: var(--bg-surface-alt);
		transform: translateY(-1px);
	}

	/* ---------- MESSAGES ---------- */

	.messages-list {
		max-width: 800px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 16px;
		padding-bottom: 16px;
		min-height: min-content;
	}

	.message-wrapper {
		display: flex;
		gap: 10px;
	}

	.message-wrapper.user {
		flex-direction: row-reverse;
	}

	.message-avatar {
		flex-shrink: 0;
	}

	.avatar {
		width: 32px;
		height: 32px;
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.user-avatar {
		background: var(--accent);
		color: #000;
	}

	.ai-avatar {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		color: var(--accent);
	}

	.message-bubble {
		flex: 1;
		max-width: 75%;
	}

	.message-wrapper.user .message-bubble {
		background: var(--accent);
		color: #000;
		border-radius: 12px 12px 4px 12px;
		padding: 10px 14px;
	}

	.message-wrapper.assistant .message-bubble {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px 12px 12px 4px;
		padding: 10px 14px;
		color: var(--text-primary);
	}

	.message-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 6px;
	}

	.sender-name {
		font-weight: 600;
		font-size: 0.75rem;
		font-family: var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.message-wrapper.user .sender-name {
		opacity: 0.7;
	}

	.message-wrapper.assistant .sender-name {
		color: var(--text-muted);
	}

	.message-time {
		font-size: 0.625rem;
		font-family: var(--font-mono);
		color: var(--text-muted);
		opacity: 0.7;
	}

	.message-wrapper.user .message-time {
		color: rgba(0, 0, 0, 0.5);
	}

	.message-content {
		line-height: 1.6;
		white-space: pre-wrap;
		word-wrap: break-word;
		font-size: 0.875rem;
	}

	.message-footer {
		margin-top: 10px;
		padding-top: 10px;
		border-top: 1px solid var(--border);
		display: flex;
		gap: 8px;
		align-items: center;
		flex-wrap: wrap;
		font-size: 0.6875rem;
	}

	.message-wrapper.user .message-footer {
		border-top-color: rgba(0, 0, 0, 0.15);
	}

	.confidence-badge {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		border-radius: 4px;
		font-weight: 600;
		font-family: var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		font-size: 0.625rem;
	}

	.confidence-badge.high {
		background: rgba(16, 185, 129, 0.1);
		color: var(--success);
	}

	.confidence-badge.medium {
		background: rgba(245, 158, 11, 0.1);
		color: var(--warning);
	}

	.confidence-badge.low {
		background: rgba(239, 68, 68, 0.1);
		color: var(--error);
	}

	.sources-badge {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--text-muted);
		padding: 2px 8px;
		background: var(--bg-surface-alt);
		border-radius: 4px;
		font-family: var(--font-mono);
		font-size: 0.625rem;
	}

	.sources-details {
		width: 100%;
		margin-top: 8px;
	}

	.sources-details summary {
		cursor: pointer;
		color: var(--accent);
		font-weight: 600;
		font-size: 0.75rem;
		font-family: var(--font-mono);
		padding: 6px 10px;
		list-style: none;
		display: flex;
		align-items: center;
		gap: 6px;
		background: var(--bg-surface-alt);
		border-radius: 6px;
		border: 1px solid var(--border);
		transition: all 0.15s;
	}

	.sources-details summary:hover {
		border-color: var(--border-accent);
	}

	.sources-details summary::-webkit-details-marker {
		display: none;
	}

	.sources-details summary svg {
		transition: transform 0.2s;
	}

	.sources-details[open] summary svg {
		transform: rotate(90deg);
	}

	.sources-list {
		margin-top: 6px;
		display: grid;
		gap: 4px;
	}

	.source-item {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 10px;
		display: flex;
		gap: 10px;
		align-items: flex-start;
		transition: border-color 0.15s;
	}

	.source-item:hover {
		border-color: var(--border-accent);
	}

	.source-icon {
		flex-shrink: 0;
		color: var(--accent);
	}

	.source-info {
		flex: 1;
		min-width: 0;
	}

	.source-title {
		font-weight: 600;
		font-size: 0.75rem;
		color: var(--text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		margin-bottom: 2px;
	}

	.source-subtitle {
		font-size: 0.6875rem;
		font-family: var(--font-mono);
		color: var(--text-muted);
		margin-bottom: 4px;
	}

	.source-relevance {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.625rem;
		font-family: var(--font-mono);
		color: var(--text-muted);
	}

	.relevance-bar {
		flex: 1;
		height: 3px;
		background: var(--border);
		border-radius: 2px;
		overflow: hidden;
	}

	.relevance-fill {
		height: 100%;
		background: var(--accent);
		border-radius: 2px;
		transition: width 0.3s ease;
	}

	/* Typing Indicator */

	.typing-indicator {
		display: flex;
		gap: 5px;
		padding: 6px 0;
	}

	.typing-indicator span {
		width: 6px;
		height: 6px;
		background: var(--accent);
		border-radius: 50%;
		animation: typing 1.4s infinite;
	}

	.typing-indicator span:nth-child(1) {
		animation-delay: 0s;
	}
	.typing-indicator span:nth-child(2) {
		animation-delay: 0.2s;
	}
	.typing-indicator span:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes typing {
		0%,
		60%,
		100% {
			transform: translateY(0);
			opacity: 0.3;
		}
		30% {
			transform: translateY(-6px);
			opacity: 1;
		}
	}

	/* ---------- ERROR BANNER ---------- */

	.error-banner {
		background: rgba(239, 68, 68, 0.08);
		color: var(--error);
		padding: 10px 20px;
		display: flex;
		align-items: center;
		gap: 10px;
		font-weight: 500;
		font-size: 0.8125rem;
		border-top: 1px solid rgba(239, 68, 68, 0.2);
		border-bottom: 1px solid rgba(239, 68, 68, 0.2);
	}

	.error-banner svg {
		flex-shrink: 0;
	}

	/* ---------- INPUT AREA ---------- */

	.input-container {
		padding: 16px 20px;
		background: var(--bg-surface);
		border-top: 1px solid var(--border);
	}

	.input-wrapper {
		display: flex;
		gap: 10px;
		align-items: flex-end;
		background: var(--bg-app);
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 10px;
		transition: border-color 0.15s ease;
	}

	.input-wrapper:focus-within {
		border-color: var(--accent);
	}

	textarea {
		flex: 1;
		border: none;
		background: transparent;
		font-family: var(--font-sans);
		font-size: 0.875rem;
		resize: none;
		max-height: 160px;
		line-height: 1.5;
		color: var(--text-primary);
		outline: none;
	}

	textarea::placeholder {
		color: var(--text-muted);
	}

	textarea:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-send {
		width: 36px;
		height: 36px;
		border: none;
		background: var(--accent);
		color: #000;
		border-radius: 8px;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s ease;
		flex-shrink: 0;
	}

	.btn-send:hover:not(:disabled) {
		background: var(--accent-hover);
		transform: translateY(-1px);
	}

	.btn-send:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.spinner {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.input-hint {
		margin-top: 8px;
		font-size: 0.6875rem;
		font-family: var(--font-mono);
		color: var(--text-muted);
		text-align: center;
	}

	.input-hint kbd {
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 1px 5px;
		font-family: var(--font-mono);
		font-size: 0.625rem;
		color: var(--text-secondary);
	}

	/* ---------- RESPONSIVE ---------- */

	@media (max-width: 1024px) {
		.chat-container {
			max-width: 100%;
			height: 100vh;
			max-height: none;
			border-radius: 0;
		}

		.message-bubble {
			max-width: 85%;
		}
	}

	@media (max-width: 768px) {
		.modal-backdrop {
			padding: 0;
		}

		.chat-container {
			grid-template-columns: 260px 1fr;
			border-radius: 0;
		}

		.suggestions-grid {
			grid-template-columns: 1fr;
		}

		.ai-orb {
			width: 64px;
			height: 64px;
		}

		.ring-1 {
			width: 64px;
			height: 64px;
		}
		.ring-2 {
			width: 52px;
			height: 52px;
		}
		.ring-3 {
			width: 40px;
			height: 40px;
		}

		.orb-icon {
			width: 24px;
			height: 24px;
		}
	}

	@media (max-width: 480px) {
		.chat-container {
			grid-template-columns: 220px 1fr;
		}

		.sidebar-header {
			padding: 12px;
		}

		.chat-header {
			padding: 10px 14px;
		}

		.messages-area {
			padding: 12px;
		}

		.input-container {
			padding: 12px;
		}

		.message-bubble {
			max-width: 90%;
		}
	}
</style>
