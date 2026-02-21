<script>
	import { onMount } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import { goto } from '$app/navigation';

	let { isOpen = $bindable(false), navigation = [] } = $props();

	let searchQuery = $state('');
	let selectedIndex = $state(0);
	let inputEl = $state(null);

	// Flatten navigation for searching
	const searchableItems = $derived.by(() => {
		const items = [];
		navigation.forEach(section => {
			section.items.forEach(item => {
				items.push({
					...item,
					section: section.title,
					type: 'page'
				});
			});
		});

		// Add common actions
		items.push({
			title: 'Toggle Dark Mode',
			action: 'toggle-theme',
			type: 'action',
			section: 'Settings',
			icon: 'moon'
		});

		return items;
	});

	const filteredItems = $derived.by(() => {
		if (!searchQuery) return searchableItems.slice(0, 8); // Show recent or first 8

		const query = searchQuery.toLowerCase();
		return searchableItems.filter(item => 
			item.title.toLowerCase().includes(query) || 
			(item.section && item.section.toLowerCase().includes(query))
		).slice(0, 10);
	});

	$effect(() => {
		if (isOpen) {
			searchQuery = '';
			selectedIndex = 0;
			setTimeout(() => {
				inputEl?.focus();
			}, 50);
		}
	});

	function handleKeydown(e) {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			selectedIndex = (selectedIndex + 1) % filteredItems.length;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			selectedIndex = (selectedIndex - 1 + filteredItems.length) % filteredItems.length;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			selectItem(filteredItems[selectedIndex]);
		} else if (e.key === 'Escape') {
			isOpen = false;
		}
	}

	function selectItem(item) {
		if (!item) return;
		
		if (item.href) {
			goto(item.href);
			isOpen = false;
		} else if (item.action === 'toggle-theme') {
			// Handle theme toggle via custom event or similar
			window.dispatchEvent(new CustomEvent('toggle-theme'));
			isOpen = false;
		}
	}
</script>

{#if isOpen}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div 
		class="cmd-backdrop" 
		transition:fade={{ duration: 150 }}
		onclick={() => isOpen = false}
		role="dialog"
		aria-modal="true"
	>
		<div 
			class="cmd-container" 
			transition:fly={{ y: -20, duration: 250 }}
			onclick={(e) => e.stopPropagation()}
			role="document"
		>
			<div class="cmd-input-wrap">
				<svg class="cmd-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
				</svg>
				<input 
					bind:this={inputEl}
					bind:value={searchQuery}
					onkeydown={handleKeydown}
					type="text" 
					class="cmd-input" 
					placeholder="Type a command or search docs..."
				/>
				<div class="cmd-esc-badge">ESC</div>
			</div>

			<div class="cmd-results">
				{#if filteredItems.length > 0}
					<div class="cmd-group-label">
						{searchQuery ? 'Search Results' : 'Quick Actions'}
					</div>
					{#each filteredItems as item, i}
						<button 
							class="cmd-item {i === selectedIndex ? 'selected' : ''}"
							onclick={() => selectItem(item)}
							onmouseenter={() => selectedIndex = i}
						>
							<div class="cmd-item-icon">
								{#if item.type === 'action'}
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
									</svg>
								{:else}
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" />
									</svg>
								{/if}
							</div>
							<div class="cmd-item-meta">
								<span class="cmd-item-title">{item.title}</span>
								{#if item.section}
									<span class="cmd-item-section">{item.section}</span>
								{/if}
							</div>
							{#if i === selectedIndex}
								<div class="cmd-item-enter" in:fade>
									<span>Enter</span>
									<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<polyline points="9 10 4 15 9 20" /><path d="M20 4v7a4 4 0 01-4 4H4" />
									</svg>
								</div>
							{/if}
						</button>
					{/each}
				{:else}
					<div class="cmd-empty">
						<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
							<circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" /><line x1="8" y1="8" x2="14" y2="14" /><line x1="14" y1="8" x2="8" y2="14" />
						</svg>
						<p>No results found for "{searchQuery}"</p>
					</div>
				{/if}
			</div>

			<div class="cmd-footer">
				<div class="cmd-kbd-help">
					<kbd>↑↓</kbd> to navigate
					<kbd>↵</kbd> to select
					<kbd>ESC</kbd> to close
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.cmd-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		backdrop-filter: blur(4px);
		z-index: 9999;
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding-top: 15vh;
	}

	.cmd-container {
		width: 100%;
		max-width: 600px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.cmd-input-wrap {
		display: flex;
		align-items: center;
		padding: 16px 20px;
		border-bottom: 1px solid var(--border);
		gap: 12px;
	}

	.cmd-search-icon {
		color: var(--text-muted);
	}

	.cmd-input {
		flex: 1;
		background: none;
		border: none;
		outline: none;
		color: var(--text-primary);
		font-family: 'Inter', sans-serif;
		font-size: 16px;
	}

	.cmd-esc-badge {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		padding: 4px 8px;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-muted);
	}

	.cmd-results {
		max-height: 400px;
		overflow-y: auto;
		padding: 8px;
	}

	.cmd-group-label {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		padding: 12px 12px 8px;
	}

	.cmd-item {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 12px;
		border-radius: 8px;
		border: none;
		background: none;
		cursor: pointer;
		text-align: left;
		transition: all 0.1s ease;
	}

	.cmd-item.selected {
		background: var(--accent-subtle);
	}

	.cmd-item-icon {
		width: 28px;
		height: 28px;
		background: var(--bg-surface-2);
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-secondary);
		transition: all 0.15s;
	}

	.cmd-item.selected .cmd-item-icon {
		background: var(--accent);
		color: white;
	}

	.cmd-item-meta {
		display: flex;
		flex-direction: column;
		flex: 1;
	}

	.cmd-item-title {
		font-family: 'Inter', sans-serif;
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
	}

	.cmd-item-section {
		font-size: 11px;
		color: var(--text-muted);
	}

	.cmd-item-enter {
		display: flex;
		align-items: center;
		gap: 4px;
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		color: var(--accent);
		opacity: 0.8;
	}

	.cmd-footer {
		padding: 10px 20px;
		background: var(--bg-surface-2);
		border-top: 1px solid var(--border);
	}

	.cmd-kbd-help {
		font-family: 'DM Mono', monospace;
		font-size: 10px;
		color: var(--text-muted);
		display: flex;
		gap: 12px;
	}

	kbd {
		padding: 2px 4px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--text-secondary);
	}

	.cmd-empty {
		padding: 40px 20px;
		text-align: center;
		color: var(--text-muted);
	}

	.cmd-empty p {
		margin-top: 12px;
		font-size: 14px;
	}

	/* Dark mode specifics if needed */
	:global(.dark) .cmd-container {
		background: #1a1a1a;
		box-shadow: 0 20px 80px rgba(0, 0, 0, 0.6);
	}
</style>
