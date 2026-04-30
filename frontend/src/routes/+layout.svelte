<script>
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { isDarkMode } from '$lib/stores.js';

	let { children } = $props();

	// Subscribe to dark mode using $state for reactivity
	let darkMode = $state(false);

	$effect(() => {
		const unsubscribe = isDarkMode.subscribe((value) => {
			darkMode = value;
		});
		return unsubscribe;
	});

	onMount(() => {
		// Initialize theme on app load
		isDarkMode.init();
	});

	// Check if current page is home page
	const isHomePage = $derived($page.route.id === '/');
</script>

<!-- Apply dark mode class to body for all pages except home -->
<svelte:head>
	{#if !isHomePage}
		<style>
			body {
				background-color: {
					darkmode?'#111827': '#f9fafb';
				}
				color: {
					darkmode?'#f3f4f6': '#111827';
				}
				transition:
					background-color 0.3s ease,
					color 0.3s ease;
			}
		</style>
	{/if}
</svelte:head>

<div class={!isHomePage && darkMode ? 'dark' : ''}>
	{@render children()}
</div>
