<script>
	import { page } from '$app/stores';
	import { isDarkMode } from '$lib/stores.js';
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';

	let { children } = $props();

	let darkMode = $state(false);
	let sidebarOpen = $state(false);
	let tocHeadings = $state([]);
	let activeHeadingId = $state('');
	let searchOpen = $state(false);
	let searchQuery = $state('');

	isDarkMode.subscribe((v) => (darkMode = v));

	// Navigation structure — engineer's field notebook index
	const navSections = [
		{
			label: '01 / OVERVIEW',
			items: [{ title: 'Introduction', href: '/docs/getting-started', icon: 'book' }]
		},
		{
			label: '02 / SETUP',
			items: [
				{ title: 'Quick Start', href: '/docs/getting-started/quick-start', icon: 'zap' },
				{
					title: 'Connecting GitHub',
					href: '/docs/getting-started/connecting-github',
					icon: 'link'
				},
				{
					title: 'First Security Scan',
					href: '/docs/getting-started/first-security-scan',
					icon: 'shield'
				}
			]
		}
	];

	// Flatten for prev/next
	const allPages = navSections.flatMap((s) => s.items);

	let currentPath = $derived($page.url.pathname);
	let currentIdx = $derived(allPages.findIndex((p) => currentPath === p.href));
	let prevPage = $derived(currentIdx > 0 ? allPages[currentIdx - 1] : null);
	let nextPage = $derived(currentIdx < allPages.length - 1 ? allPages[currentIdx + 1] : null);
	let currentPageTitle = $derived(allPages[currentIdx]?.title || 'Documentation');

	// Breadcrumb from path
	let breadcrumbs = $derived.by(() => {
		const segs = currentPath.replace('/docs/', '').split('/').filter(Boolean);
		return segs.map((s) => s.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()));
	});

	// TOC: scan headings from content
	function scanHeadings() {
		if (!browser) return;
		const content = document.querySelector('.docs-content');
		if (!content) return;
		const hEls = content.querySelectorAll('h2[id], h3[id]');
		tocHeadings = Array.from(hEls).map((el) => ({
			id: el.id,
			text: el.textContent,
			level: el.tagName === 'H3' ? 3 : 2
		}));
	}

	// Scroll spy for TOC
	function onScroll() {
		if (!browser) return;
		const hEls = document.querySelectorAll('.docs-content h2[id], .docs-content h3[id]');
		let current = '';
		for (const el of hEls) {
			if (el.getBoundingClientRect().top <= 120) current = el.id;
		}
		activeHeadingId = current;
	}

	onMount(() => {
		isDarkMode.init();
		scanHeadings();
		window.addEventListener('scroll', onScroll, { passive: true });

		// Keyboard shortcut: Ctrl+K for search
		function onKeydown(e) {
			if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
				e.preventDefault();
				searchOpen = !searchOpen;
			}
			if (e.key === 'Escape') {
				searchOpen = false;
				sidebarOpen = false;
			}
		}
		window.addEventListener('keydown', onKeydown);

		return () => {
			window.removeEventListener('scroll', onScroll);
			window.removeEventListener('keydown', onKeydown);
		};
	});

	// Re-scan headings on page navigation
	$effect(() => {
		currentPath;
		tick().then(() => scanHeadings());
	});

	function closeSidebar() {
		sidebarOpen = false;
	}
	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
	function toggleTheme() {
		isDarkMode.toggle();
	}
</script>

<svelte:head>
	<title>{currentPageTitle} — WithOps Docs</title>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<div class="docs-shell" class:dark={darkMode}>
	<!-- ═══ TOPBAR ═══ -->
	<header class="docs-topbar">
		<div class="topbar-left">
			<button class="mobile-menu-btn" onclick={toggleSidebar} aria-label="Toggle menu">
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					{#if sidebarOpen}
						<path d="M18 6L6 18M6 6l12 12" />
					{:else}
						<path d="M3 12h18M3 6h18M3 18h18" />
					{/if}
				</svg>
			</button>
			<a href="/dashboard" class="topbar-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="topbar-logo" />
				<span class="topbar-brand-name">WithOps</span>
			</a>
			<span class="topbar-sep">/</span>
			<a href="/docs/getting-started" class="topbar-docs-label">Docs</a>
			{#each breadcrumbs as crumb, i}
				<span class="topbar-sep">/</span>
				<span class="topbar-crumb" class:active={i === breadcrumbs.length - 1}>{crumb}</span>
			{/each}
		</div>
		<div class="topbar-right">
			<button class="topbar-search-btn" onclick={() => (searchOpen = !searchOpen)}>
				<svg
					width="14"
					height="14"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
				</svg>
				<span class="search-label">Search</span>
				<kbd class="search-kbd">Ctrl K</kbd>
			</button>
			<button class="topbar-theme-btn" onclick={toggleTheme} title="Toggle theme">
				{#if darkMode}
					<svg
						width="16"
						height="16"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="2"
					>
						<circle cx="12" cy="12" r="5" /><path
							d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
						/>
					</svg>
				{:else}
					<svg
						width="16"
						height="16"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="2"
					>
						<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
					</svg>
				{/if}
			</button>
		</div>
	</header>

	<!-- ═══ SEARCH OVERLAY ═══ -->
	{#if searchOpen}
		<div class="search-overlay" onclick={() => (searchOpen = false)} role="presentation">
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<div
				class="search-dialog"
				onclick={(e) => e.stopPropagation()}
				onkeydown={(e) => {
					if (e.key === 'Escape') searchOpen = false;
				}}
				role="dialog"
				tabindex="0"
			>
				<div class="search-input-wrap">
					<svg
						width="16"
						height="16"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
					</svg>
					<!-- svelte-ignore a11y_autofocus -->
					<input
						type="text"
						class="search-input"
						placeholder="Search documentation..."
						bind:value={searchQuery}
						autofocus
					/>
					<kbd class="search-esc">Esc</kbd>
				</div>
				<div class="search-results">
					<p class="search-placeholder-text">
						Start typing to search across all documentation pages.
					</p>
				</div>
			</div>
		</div>
	{/if}

	<div class="docs-body">
		<!-- ═══ SIDEBAR ═══ -->
		{#if sidebarOpen}
			<div class="sidebar-backdrop" onclick={closeSidebar} role="presentation"></div>
		{/if}
		<aside class="docs-sidebar" class:open={sidebarOpen}>
			<nav class="sidebar-nav">
				{#each navSections as section, secIdx}
					<div class="nav-group">
						<div class="nav-group-label">{section.label}</div>
						<ul class="nav-group-items">
							{#each section.items as item, itemIdx}
								{@const isActive = currentPath === item.href}
								<li class="nav-item" class:active={isActive}>
									<a href={item.href} class="nav-item-link" onclick={closeSidebar}>
										<span class="nav-marker" class:filled={isActive}></span>
										<span class="nav-item-text">{item.title}</span>
									</a>
								</li>
							{/each}
						</ul>
					</div>
				{/each}
			</nav>
			<div class="sidebar-footer">
				<div class="sidebar-footer-line">
					<span class="footer-label">FIELD REF</span>
					<span class="footer-value">v1.0</span>
				</div>
			</div>
		</aside>

		<!-- ═══ MAIN CONTENT ═══ -->
		<main class="docs-main">
			<div class="docs-content-wrap">
				<article class="docs-content">
					{@render children()}
				</article>

				<!-- ═══ TABLE OF CONTENTS ═══ -->
				{#if tocHeadings.length > 0}
					<aside class="docs-toc">
						<div class="toc-header">ON THIS PAGE</div>
						<ul class="toc-list">
							{#each tocHeadings as h}
								<li
									class="toc-item"
									class:depth-3={h.level === 3}
									class:active={activeHeadingId === h.id}
								>
									<a href="#{h.id}" class="toc-link">{h.text}</a>
								</li>
							{/each}
						</ul>
					</aside>
				{/if}
			</div>

			<!-- ═══ PREV / NEXT NAV ═══ -->
			{#if prevPage || nextPage}
				<nav class="page-nav">
					{#if prevPage}
						<a href={prevPage.href} class="page-nav-card prev">
							<span class="page-nav-direction">← PREVIOUS</span>
							<span class="page-nav-title">{prevPage.title}</span>
						</a>
					{:else}
						<div></div>
					{/if}
					{#if nextPage}
						<a href={nextPage.href} class="page-nav-card next">
							<span class="page-nav-direction">NEXT →</span>
							<span class="page-nav-title">{nextPage.title}</span>
						</a>
					{/if}
				</nav>
			{/if}
		</main>
	</div>
</div>

<style>
	/* ═══════════════════════════════════════════════
	   ENGINEER'S FIELD NOTEBOOK — DESIGN SYSTEM
	   ═══════════════════════════════════════════════ */

	/* ── Dark Mode Tokens ── */
	.docs-shell.dark {
		--bg-app: #000000;
		--bg-surface: #0a0a0a;
		--bg-surface-alt: #111111;
		--bg-elevated: #161616;
		--border: rgba(255, 255, 255, 0.06);
		--border-strong: rgba(255, 255, 255, 0.1);
		--border-sketch: rgba(255, 255, 255, 0.03);
		--text-primary: #e8e6e3;
		--text-secondary: #8b8685;
		--text-muted: #504d4a;
		--accent: #00adef;
		--accent-soft: rgba(0, 173, 239, 0.06);
		--accent-border: rgba(0, 173, 239, 0.15);
		--accent-glow: rgba(0, 173, 239, 0.03);
		--complement: #d4a054;
		--complement-soft: rgba(212, 160, 84, 0.06);
		--complement-border: rgba(212, 160, 84, 0.15);
		--pencil: rgba(255, 255, 255, 0.025);
		--margin-line: rgba(0, 173, 239, 0.07);
		--grid-line: rgba(255, 255, 255, 0.025);
		--success: #10b981;
		--warn: #f59e0b;
		--error: #ef4444;
		--card-shadow: none;
		--topbar-bg: rgba(0, 0, 0, 0.85);
	}

	/* ── Light Mode Tokens ── */
	.docs-shell:not(.dark) {
		--bg-app: #fafaf8;
		--bg-surface: #ffffff;
		--bg-surface-alt: #f5f4f1;
		--bg-elevated: #ffffff;
		--border: rgba(0, 0, 0, 0.07);
		--border-strong: rgba(0, 0, 0, 0.12);
		--border-sketch: rgba(0, 0, 0, 0.035);
		--text-primary: #1c1917;
		--text-secondary: #57534e;
		--text-muted: #a8a29e;
		--accent: #0082b4;
		--accent-soft: rgba(0, 130, 180, 0.06);
		--accent-border: rgba(0, 130, 180, 0.15);
		--accent-glow: rgba(0, 130, 180, 0.03);
		--complement: #a07328;
		--complement-soft: rgba(160, 115, 40, 0.06);
		--complement-border: rgba(160, 115, 40, 0.15);
		--pencil: rgba(120, 113, 108, 0.05);
		--margin-line: rgba(0, 130, 180, 0.1);
		--grid-line: rgba(0, 0, 0, 0.025);
		--success: #059669;
		--warn: #d97706;
		--error: #dc2626;
		--card-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
		--topbar-bg: rgba(250, 250, 248, 0.88);
	}

	/* ── Shared Tokens ── */
	.docs-shell {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
		--sidebar-w: 256px;
		--toc-w: 196px;
		--topbar-h: 48px;
		--radius-sm: 4px;
		--radius-md: 8px;
	}

	/* ── Shell ── */
	.docs-shell {
		min-height: 100vh;
		background: var(--bg-app);
		color: var(--text-primary);
		font-family: var(--font-sans);
		position: relative;
	}

	/* Engineering Grid Background */
	.docs-shell::before {
		content: '';
		position: fixed;
		inset: 0;
		background-image:
			linear-gradient(var(--grid-line) 1px, transparent 1px),
			linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
		background-size: 40px 40px;
		mask-image: radial-gradient(circle at 50% 30%, black, transparent 80%);
		pointer-events: none;
		z-index: 0;
	}

	/* Accent Radial Glow */
	.docs-shell::after {
		content: '';
		position: fixed;
		inset: 0;
		background: radial-gradient(ellipse 80% 50% at 50% -10%, var(--accent-glow), transparent);
		pointer-events: none;
		z-index: 0;
	}

	/* ═══════════════════
	   TOPBAR
	   ═══════════════════ */
	.docs-topbar {
		position: sticky;
		top: 0;
		z-index: 200;
		height: var(--topbar-h);
		background: var(--topbar-bg);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.25rem;
	}

	.topbar-left {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
	}

	.topbar-brand {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		text-decoration: none;
		color: var(--text-primary);
		flex-shrink: 0;
	}

	.topbar-logo {
		width: 22px;
		height: 22px;
	}

	.topbar-brand-name {
		font-weight: 700;
		font-size: 0.875rem;
		letter-spacing: -0.01em;
	}

	.topbar-sep {
		color: var(--text-muted);
		font-size: 0.75rem;
		user-select: none;
		flex-shrink: 0;
	}

	.topbar-docs-label {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--accent);
		text-decoration: none;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		flex-shrink: 0;
	}

	.topbar-crumb {
		font-size: 0.75rem;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.topbar-crumb.active {
		color: var(--text-secondary);
	}

	.topbar-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	/* Search Button */
	.topbar-search-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-surface);
		color: var(--text-muted);
		font-size: 0.8rem;
		cursor: pointer;
		transition: all 0.15s;
		font-family: var(--font-sans);
	}

	.topbar-search-btn:hover {
		border-color: var(--border-strong);
		color: var(--text-secondary);
	}

	.search-label {
		font-size: 0.75rem;
	}

	.search-kbd {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		padding: 0.1rem 0.35rem;
		border: 1px solid var(--border);
		border-radius: 3px;
		background: var(--bg-surface-alt);
		color: var(--text-muted);
		line-height: 1;
	}

	/* Theme Button */
	.topbar-theme-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: transparent;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}

	.topbar-theme-btn:hover {
		border-color: var(--border-strong);
		background: var(--bg-surface);
		color: var(--text-primary);
	}

	/* Mobile Menu */
	.mobile-menu-btn {
		display: none;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: transparent;
		color: var(--text-secondary);
		cursor: pointer;
		flex-shrink: 0;
	}

	/* ═══════════════════
	   SEARCH OVERLAY
	   ═══════════════════ */
	.search-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 500;
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding-top: 15vh;
		backdrop-filter: blur(4px);
	}

	.search-dialog {
		width: 90%;
		max-width: 560px;
		background: var(--bg-surface);
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-md);
		overflow: hidden;
		box-shadow: 0 24px 48px rgba(0, 0, 0, 0.3);
	}

	.search-input-wrap {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem 1rem;
		border-bottom: 1px solid var(--border);
		color: var(--text-muted);
	}

	.search-input {
		flex: 1;
		background: none;
		border: none;
		outline: none;
		color: var(--text-primary);
		font-size: 0.9rem;
		font-family: var(--font-sans);
	}

	.search-input::placeholder {
		color: var(--text-muted);
	}

	.search-esc {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		padding: 0.15rem 0.4rem;
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--text-muted);
		background: var(--bg-surface-alt);
	}

	.search-results {
		padding: 2rem 1.25rem;
	}

	.search-placeholder-text {
		color: var(--text-muted);
		font-size: 0.8rem;
		text-align: center;
	}

	/* ═══════════════════
	   LAYOUT BODY
	   ═══════════════════ */
	.docs-body {
		display: flex;
		position: relative;
		z-index: 1;
	}

	/* ═══════════════════
	   SIDEBAR
	   ═══════════════════ */
	.docs-sidebar {
		position: sticky;
		top: var(--topbar-h);
		width: var(--sidebar-w);
		height: calc(100vh - var(--topbar-h));
		overflow-y: auto;
		flex-shrink: 0;
		border-right: 1px solid var(--border);
		background: var(--bg-app);
		display: flex;
		flex-direction: column;
		scrollbar-width: thin;
		scrollbar-color: var(--border) transparent;
	}

	.sidebar-nav {
		flex: 1;
		padding: 1.25rem 0;
	}

	/* Navigation Groups */
	.nav-group {
		margin-bottom: 1.75rem;
	}

	.nav-group-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		padding: 0 1.25rem;
		margin-bottom: 0.625rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.nav-group-label::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--border);
	}

	.nav-group-items {
		list-style: none;
		padding: 0;
		margin: 0;
		position: relative;
	}

	/* Connecting pencil line */
	.nav-group-items::before {
		content: '';
		position: absolute;
		left: 1.625rem;
		top: 6px;
		bottom: 6px;
		width: 1px;
		background: var(--border);
	}

	/* Nav Items — path/timeline style */
	.nav-item {
		position: relative;
	}

	.nav-item-link {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 1.25rem;
		text-decoration: none;
		color: var(--text-secondary);
		font-size: 0.825rem;
		font-weight: 500;
		transition: all 0.15s var(--ease-premium);
		position: relative;
	}

	.nav-item-link:hover {
		color: var(--text-primary);
		background: var(--accent-soft);
	}

	/* Dot marker on the connection line */
	.nav-marker {
		position: relative;
		z-index: 2;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		border: 1.5px solid var(--border-strong);
		background: var(--bg-app);
		flex-shrink: 0;
		transition: all 0.2s var(--ease-premium);
	}

	.nav-marker.filled {
		border-color: var(--accent);
		background: var(--accent);
		box-shadow: 0 0 0 3px var(--accent-soft);
	}

	.nav-item.active .nav-item-link {
		color: var(--accent);
	}

	.nav-item.active .nav-item-text {
		font-weight: 600;
	}

	/* Sidebar Footer */
	.sidebar-footer {
		padding: 1rem 1.25rem;
		border-top: 1px solid var(--border);
	}

	.sidebar-footer-line {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.footer-label {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	.footer-value {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text-muted);
	}

	/* ═══════════════════
	   MAIN CONTENT
	   ═══════════════════ */
	.docs-main {
		flex: 1;
		min-width: 0;
		padding: 2rem 2.5rem 4rem;
		position: relative;
	}

	/* Notebook margin line */
	.docs-main::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		left: 0;
		width: 1px;
		background: var(--margin-line);
		pointer-events: none;
	}

	.docs-content-wrap {
		display: flex;
		gap: 2.5rem;
		max-width: 960px;
	}

	.docs-content {
		flex: 1;
		min-width: 0;
	}

	/* ═══════════════════
	   TABLE OF CONTENTS
	   ═══════════════════ */
	.docs-toc {
		position: sticky;
		top: calc(var(--topbar-h) + 2rem);
		width: var(--toc-w);
		max-height: calc(100vh - var(--topbar-h) - 4rem);
		overflow-y: auto;
		flex-shrink: 0;
		scrollbar-width: none;
	}

	.docs-toc::-webkit-scrollbar {
		display: none;
	}

	.toc-header {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.12em;
		margin-bottom: 0.75rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px dashed var(--border);
	}

	.toc-list {
		list-style: none;
		padding: 0;
		margin: 0;
		border-left: 1px solid var(--border);
	}

	.toc-item {
		position: relative;
	}

	.toc-link {
		display: block;
		padding: 0.3rem 0 0.3rem 0.875rem;
		font-size: 0.725rem;
		color: var(--text-muted);
		text-decoration: none;
		line-height: 1.4;
		transition: color 0.15s;
		border-left: 2px solid transparent;
		margin-left: -1px;
	}

	.toc-link:hover {
		color: var(--text-secondary);
	}

	.toc-item.depth-3 .toc-link {
		padding-left: 1.5rem;
		font-size: 0.7rem;
	}

	.toc-item.active .toc-link {
		color: var(--accent);
		border-left-color: var(--accent);
	}

	/* ═══════════════════
	   PREV / NEXT NAV
	   ═══════════════════ */
	.page-nav {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		margin-top: 4rem;
		padding-top: 2rem;
		border-top: 1px dashed var(--border);
		max-width: 720px;
	}

	.page-nav-card {
		padding: 1rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		text-decoration: none;
		transition: all 0.2s var(--ease-premium);
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.page-nav-card:hover {
		border-color: var(--accent-border);
		background: var(--accent-soft);
	}

	.page-nav-card.next {
		text-align: right;
		grid-column: 2;
	}

	.page-nav-direction {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.page-nav-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	/* ═══════════════════
	   SIDEBAR BACKDROP (MOBILE)
	   ═══════════════════ */
	.sidebar-backdrop {
		display: none;
	}

	/* ═══════════════════
	   RESPONSIVE
	   ═══════════════════ */
	@media (max-width: 1100px) {
		.docs-toc {
			display: none;
		}
	}

	@media (max-width: 860px) {
		.mobile-menu-btn {
			display: flex;
		}

		.docs-sidebar {
			position: fixed;
			top: var(--topbar-h);
			left: 0;
			bottom: 0;
			z-index: 300;
			transform: translateX(-100%);
			transition: transform 0.25s var(--ease-premium);
			background: var(--bg-app);
			border-right: 1px solid var(--border);
			box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
		}

		.docs-sidebar.open {
			transform: translateX(0);
		}

		.sidebar-backdrop {
			display: block;
			position: fixed;
			inset: 0;
			top: var(--topbar-h);
			z-index: 250;
			background: rgba(0, 0, 0, 0.4);
			backdrop-filter: blur(2px);
		}

		.docs-main {
			padding: 1.5rem 1.25rem 3rem;
		}

		.docs-main::before {
			display: none;
		}

		.search-label {
			display: none;
		}

		.search-kbd {
			display: none;
		}

		.topbar-crumb {
			display: none;
		}

		.page-nav {
			grid-template-columns: 1fr;
		}

		.page-nav-card.next {
			text-align: left;
			grid-column: 1;
		}
	}
</style>
