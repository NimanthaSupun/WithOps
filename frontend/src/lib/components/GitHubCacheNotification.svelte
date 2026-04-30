<script>
	import { onMount, onDestroy } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import { browser } from '$app/environment';

	export let organization = '';

	let notifications = [];
	let notificationId = 0;

	// Auto-dismiss timeout
	const AUTO_DISMISS_DELAY = 5000;

	function addNotification(type, message, data = {}) {
		const id = notificationId++;
		const notification = {
			id,
			type, // 'workspace', 'actions', 'workflows'
			message,
			data,
			timestamp: new Date()
		};

		notifications = [...notifications, notification];

		// Auto-dismiss after delay
		setTimeout(() => {
			dismissNotification(id);
		}, AUTO_DISMISS_DELAY);
	}

	function dismissNotification(id) {
		notifications = notifications.filter((n) => n.id !== id);
	}

	function handleWorkspaceRefreshed(event) {
		const data = event.detail;
		if (organization && data.organization !== organization) return;

		addNotification(
			'workspace',
			`Workspace refreshed: ${data.repositories_count || 0} repositories`,
			data
		);
	}

	function handleActionsRefreshed(event) {
		const data = event.detail;
		if (organization && data.organization !== organization) return;

		addNotification('actions', `Actions updated: ${data.actions_count || 0} actions`, data);
	}

	function handleWorkflowsRefreshed(event) {
		const data = event.detail;
		if (organization && data.organization !== organization) return;

		addNotification('workflows', `Workflows updated: ${data.workflows_count || 0} workflows`, data);
	}

	onMount(() => {
		// Only run in browser, not during SSR
		if (!browser) return;

		// Listen for GitHub cache refresh events
		window.addEventListener('github-github_workspace_refreshed', handleWorkspaceRefreshed);
		window.addEventListener('github-github_actions_refreshed', handleActionsRefreshed);
		window.addEventListener('github-github_workflows_refreshed', handleWorkflowsRefreshed);

		console.log('🔔 GitHub cache notification listener mounted');
	});

	onDestroy(() => {
		// Only run in browser
		if (!browser) return;

		window.removeEventListener('github-github_workspace_refreshed', handleWorkspaceRefreshed);
		window.removeEventListener('github-github_actions_refreshed', handleActionsRefreshed);
		window.removeEventListener('github-github_workflows_refreshed', handleWorkflowsRefreshed);
	});
</script>

<!-- Notification Container -->
<div class="notification-container">
	{#each notifications as notification (notification.id)}
		<div
			class="notification notification-{notification.type}"
			in:fly={{ y: -20, duration: 300 }}
			out:fade={{ duration: 200 }}
		>
			<div class="notification-icon">
				{#if notification.type === 'workspace'}
					📦
				{:else if notification.type === 'actions'}
					⚡
				{:else if notification.type === 'workflows'}
					🔄
				{/if}
			</div>

			<div class="notification-content">
				<div class="notification-message">{notification.message}</div>
				<div class="notification-time">
					{notification.timestamp.toLocaleTimeString()}
				</div>
			</div>

			<button
				class="notification-close"
				on:click={() => dismissNotification(notification.id)}
				aria-label="Dismiss notification"
			>
				×
			</button>
		</div>
	{/each}
</div>

<!-- test -->

<style>
	.notification-container {
		position: fixed;
		top: 20px;
		right: 20px;
		z-index: 10000;
		display: flex;
		flex-direction: column;
		gap: 12px;
		pointer-events: none;
	}

	.notification {
		display: flex;
		align-items: center;
		gap: 12px;
		min-width: 300px;
		max-width: 400px;
		padding: 16px;
		background: white;
		border-radius: 12px;
		box-shadow:
			0 10px 40px rgba(0, 0, 0, 0.15),
			0 2px 8px rgba(0, 0, 0, 0.1);
		pointer-events: auto;
		border-left: 4px solid;
		transition: all 0.3s ease;
	}

	.notification:hover {
		transform: translateY(-2px);
		box-shadow:
			0 12px 45px rgba(0, 0, 0, 0.18),
			0 4px 12px rgba(0, 0, 0, 0.12);
	}

	.notification-workspace {
		border-left-color: #4a9eff;
	}

	.notification-actions {
		border-left-color: #10b981;
	}

	.notification-workflows {
		border-left-color: #8b5cf6;
	}

	.notification-icon {
		font-size: 24px;
		flex-shrink: 0;
		animation: bounce 0.6s ease;
	}

	@keyframes bounce {
		0%,
		100% {
			transform: translateY(0);
		}
		50% {
			transform: translateY(-5px);
		}
	}

	.notification-content {
		flex: 1;
		min-width: 0;
	}

	.notification-message {
		font-size: 14px;
		font-weight: 600;
		color: #1f2937;
		margin-bottom: 4px;
		line-height: 1.4;
	}

	.notification-time {
		font-size: 12px;
		color: #6b7280;
	}

	.notification-close {
		flex-shrink: 0;
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: transparent;
		color: #9ca3af;
		font-size: 20px;
		cursor: pointer;
		border-radius: 4px;
		transition: all 0.2s ease;
	}

	.notification-close:hover {
		background: #f3f4f6;
		color: #374151;
	}

	/* Mobile responsive */
	@media (max-width: 768px) {
		.notification-container {
			top: 10px;
			right: 10px;
			left: 10px;
		}

		.notification {
			min-width: unset;
			max-width: unset;
		}
	}
</style>
