<script>
	import { onMount, tick } from 'svelte';
	import { page } from '$app/stores';
	import { isDarkMode } from '$lib/stores.js';

	let { children } = $props();

	let darkMode = $state(false);
	let sidebarOpen = $state(false);

	// TOC state
	let tocItems = $state([]);
	let activeTocId = $state('');
	let contentWrapEl = $state(null);
	let observer = null;

	// Subscribe to dark mode store
	$effect(() => {
		const unsub = isDarkMode.subscribe((v) => {
			darkMode = v;
		});
		return unsub;
	});

	// Re-build TOC when page changes
	$effect(() => {
		// Track page path to re-run
		const _path = $page.url.pathname;
		// Use tick to wait for child content to render
		tick().then(() => buildToc());
	});

	function buildToc() {
		if (!contentWrapEl) return;
		const headings = contentWrapEl.querySelectorAll('h2[id], h3[id]');
		const items = [];
		headings.forEach((h) => {
			items.push({
				id: h.id,
				text: h.textContent.trim(),
				level: h.tagName === 'H3' ? 3 : 2
			});
		});
		tocItems = items;
		if (items.length > 0 && !activeTocId) {
			activeTocId = items[0].id;
		}
		setupObserver();
	}

	function setupObserver() {
		if (observer) observer.disconnect();
		if (!contentWrapEl) return;

		observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting) {
						activeTocId = entry.target.id;
					}
				}
			},
			{
				root: contentWrapEl,
				rootMargin: '-10% 0px -75% 0px',
				threshold: 0
			}
		);

		const headings = contentWrapEl.querySelectorAll('h2[id], h3[id]');
		headings.forEach((h) => observer.observe(h));
	}

	function scrollToHeading(id) {
		if (!contentWrapEl) return;
		const el = contentWrapEl.querySelector(`#${id}`);
		if (el) {
			el.scrollIntoView({ behavior: 'smooth', block: 'start' });
			activeTocId = id;
		}
	}

	onMount(() => {
		isDarkMode.init();
		return () => {
			if (observer) observer.disconnect();
		};
	});

	function toggleTheme() {
		isDarkMode.toggle();
	}

	// Navigation structure
	const navigation = [
		{
			title: 'Getting Started',
			icon: 'rocket',
			items: [
				{ title: 'Introduction', href: '/docs/getting-started' },
				{ title: 'Quick Start', href: '/docs/getting-started/quick-start' },
				{ title: 'Connecting GitHub', href: '/docs/getting-started/connecting-github' },
				{ title: 'First Security Scan', href: '/docs/getting-started/first-security-scan' }
			]
		}
	];

	const placeholderSections = [
		{ title: 'Platform Overview', icon: 'layers' },
		{ title: 'Features & Tools', icon: 'cpu' },
		{ title: 'API Reference', icon: 'code' },
		{ title: 'Deployment Guide', icon: 'server' }
	];

	function isActive(href) {
		return $page.url.pathname === href;
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function closeSidebar() {
		sidebarOpen = false;
	}
</script>

<svelte:head>
	<link
		href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=DM+Mono:ital,wght@0,400;0,500;1,400&family=Playfair+Display:ital,wght@0,700;1,400&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<div class="docs-shell {darkMode ? 'dark' : 'light'}">
	<!-- Topbar -->
	<header class="docs-topbar">
		<div class="topbar-left">
			<button class="mobile-menu-btn" onclick={toggleSidebar} aria-label="Toggle navigation menu">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
					><path d="M3 12h18M3 6h18M3 18h18" /></svg
				>
			</button>
			<a href="/" class="topbar-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="topbar-brand-icon" />
				<span class="topbar-brand-name">WithOps</span>
			</a>
			<span class="topbar-divider"></span>
			<span class="topbar-label">Documentation</span>
		</div>
		<div class="topbar-right">
			<a href="/dashboard" class="topbar-link">Dashboard</a>
			<button onclick={toggleTheme} class="theme-toggle" title="Toggle theme">
				{#if darkMode}
					<svg class="theme-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="5" /><path
							d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
						/>
					</svg>
				{:else}
					<svg class="theme-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
					</svg>
				{/if}
			</button>
			<a href="https://github.com" target="_blank" rel="noopener" class="topbar-github" aria-label="GitHub repository">
				<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
					<path
						d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
					/>
				</svg>
			</a>
		</div>
	</header>

	<div class="docs-body">
		<!-- Sidebar -->
		<aside class="docs-sidebar {sidebarOpen ? 'open' : ''}">
			<!-- Spine texture -->
			<div class="sidebar-spine"></div>

			<div class="sidebar-header">
				<div class="brand-badge">
					<span class="brand-badge-letter">W</span>
				</div>
				<div>
					<div class="sidebar-brand-name">WithOps Docs</div>
					<div class="sidebar-version">v2.0.1</div>
				</div>
			</div>

			<div class="sidebar-search">
				<div class="search-wrap">
					<svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
					</svg>
					<input type="text" class="search-input" placeholder="Search docs…" />
					<span class="search-shortcut">⌘K</span>
				</div>
			</div>

			<nav class="sidebar-nav">
				{#each navigation as section}
					<div class="nav-section">
						<div class="nav-section-label">
							{#if section.icon === 'rocket'}
								<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path
										d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09zM12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z"
									/>
								</svg>
							{/if}
							{section.title}
						</div>
						{#each section.items as item}
							<a href={item.href} class="nav-item {isActive(item.href) ? 'active' : ''}" onclick={closeSidebar}>
								<div class="nav-dot"></div>
								{item.title}
							</a>
						{/each}
					</div>
				{/each}

				<!-- Placeholder sections -->
				{#each placeholderSections as section}
					<div class="nav-section muted">
						<div class="nav-section-label">
							{section.title}
							<span class="coming-soon-badge">Soon</span>
						</div>
					</div>
				{/each}
			</nav>
		</aside>

		<!-- Mobile overlay -->
		{#if sidebarOpen}
			<div class="sidebar-overlay" onclick={closeSidebar} role="presentation"></div>
		{/if}

		<!-- Main content area -->
		<main class="docs-main">
			<!-- Notebook ruling lines -->
			<div class="notebook-rules"></div>
			<!-- Margin line -->
			<div class="notebook-margin"></div>

			<div class="docs-content-wrap" bind:this={contentWrapEl}>
				<div class="doc-content">
					{@render children()}
				</div>
			</div>

			<!-- TOC Rail -->
			{#if tocItems.length > 0}
				<aside class="toc-rail">
					<div class="toc-label">
						<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="3" y1="6" x2="21" y2="6" />
							<line x1="3" y1="12" x2="15" y2="12" />
							<line x1="3" y1="18" x2="18" y2="18" />
						</svg>
						On this page
					</div>
					<nav class="toc-nav">
						{#each tocItems as item}
							<button
								class="toc-item {item.level === 3 ? 'h3' : ''} {activeTocId === item.id ? 'active' : ''}"
								onclick={() => scrollToHeading(item.id)}
							>
								{item.text}
							</button>
						{/each}
					</nav>
				</aside>
			{/if}
		</main>
	</div>
</div>

<style>
	/* ============================================
	   WITHOPS DOCS — NOTEBOOK + MATTE ENGINEERING
	   ============================================ */

	/* ── Fonts ── */
	:root {
		--font-serif: 'Playfair Display', 'Georgia', serif;
		--font-body: 'Lora', 'Georgia', serif;
		--font-sans: 'Inter', system-ui, sans-serif;
		--font-mono: 'DM Mono', 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);
	}

	/* ── DARK MODE ── */
	.docs-shell.dark {
		--bg-page: #000000;
		--bg-sidebar: #050508;
		--bg-surface: #0a0a0f;
		--bg-surface-2: #111118;
		--bg-surface-3: #18181f;
		--border: rgba(255, 255, 255, 0.04);
		--border-focus: rgba(255, 255, 255, 0.08);
		--text-primary: #f0f0f4;
		--text-secondary: #94a3b8;
		--text-muted: #475569;
		--accent: #00adef;
		--accent-hover: #33c0f5;
		--accent-subtle: rgba(0, 173, 239, 0.06);
		--success: #10b981;
		--warn: #f59e0b;
		--error: #ef4444;
		--notebook-line: rgba(255, 255, 255, 0.07);
		--notebook-margin: rgba(200, 75, 47, 0.25);
		--code-bg: #0c0c12;
		--code-text: #e2e8f0;
		--code-border: rgba(255, 255, 255, 0.04);
		--callout-info-bg: rgba(0, 173, 239, 0.04);
		--callout-info-border: rgba(0, 173, 239, 0.15);
		--callout-info-text: #38bdf8;
		--callout-tip-bg: rgba(16, 185, 129, 0.04);
		--callout-tip-border: rgba(16, 185, 129, 0.15);
		--callout-tip-text: #6ee7b7;
		--callout-warn-bg: rgba(245, 158, 11, 0.04);
		--callout-warn-border: rgba(245, 158, 11, 0.15);
		--callout-warn-text: #fcd34d;
		--spine: repeating-linear-gradient(180deg, #0a0a0f 0px, #050508 8px);
		--card-shadow: none;
	}

	/* ── LIGHT MODE ── */
	.docs-shell.light {
		--bg-page: #faf9f7;
		--bg-sidebar: #0f0e0c;
		--bg-surface: #ffffff;
		--bg-surface-2: #f5f4f1;
		--bg-surface-3: #eeedea;
		--border: rgba(0, 0, 0, 0.06);
		--border-focus: rgba(0, 130, 180, 0.2);
		--text-primary: #1a1a2e;
		--text-secondary: #5a5a72;
		--text-muted: #9a9ab0;
		--accent: #0082b4;
		--accent-hover: #006d99;
		--accent-subtle: rgba(0, 130, 180, 0.06);
		--success: #059669;
		--warn: #d97706;
		--error: #dc2626;
		--notebook-line: rgba(0, 0, 0, 0.09);
		--notebook-margin: rgba(200, 75, 47, 0.25);
		--code-bg: #1e1b18;
		--code-text: #e8dfd0;
		--code-border: rgba(255, 255, 255, 0.05);
		--callout-info-bg: rgba(0, 130, 180, 0.05);
		--callout-info-border: rgba(0, 130, 180, 0.2);
		--callout-info-text: #0082b4;
		--callout-tip-bg: rgba(16, 185, 129, 0.05);
		--callout-tip-border: rgba(16, 185, 129, 0.2);
		--callout-tip-text: #059669;
		--callout-warn-bg: rgba(245, 158, 11, 0.05);
		--callout-warn-border: rgba(245, 158, 11, 0.2);
		--callout-warn-text: #d97706;
		--spine: repeating-linear-gradient(180deg, #1a1710 0px, #0f0e0c 8px);
		--card-shadow: 0 1px 4px rgba(26, 20, 16, 0.06);
	}

	/* ── Shell ── */
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	.docs-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
		background: var(--bg-page);
		color: var(--text-primary);
		font-family: var(--font-body);
	}

	/* ── TOPBAR ── */
	.docs-topbar {
		height: 56px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 24px;
		border-bottom: 1px solid var(--border);
		background: var(--bg-page);
		z-index: 200;
		flex-shrink: 0;
	}

	.topbar-left {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.topbar-brand {
		display: flex;
		align-items: center;
		gap: 8px;
		text-decoration: none;
	}

	.topbar-brand-icon {
		width: 24px;
		height: 24px;
	}

	.topbar-brand-name {
		font-family: var(--font-sans);
		font-weight: 700;
		font-size: 14px;
		color: var(--text-primary);
		letter-spacing: -0.02em;
	}

	.topbar-divider {
		width: 1px;
		height: 20px;
		background: var(--border);
	}

	.topbar-label {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.topbar-right {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	.topbar-link {
		font-family: var(--font-sans);
		font-size: 13px;
		font-weight: 500;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
	}
	.topbar-link:hover {
		color: var(--text-primary);
	}

	.theme-toggle {
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		padding: 6px;
		border-radius: 6px;
		cursor: pointer;
		display: flex;
		transition: all 0.15s;
	}
	.theme-toggle:hover {
		background: var(--bg-surface-2);
		color: var(--text-primary);
		border-color: var(--border-focus);
	}
	.theme-icon {
		width: 16px;
		height: 16px;
	}

	.topbar-github {
		color: var(--text-secondary);
		transition: color 0.15s;
		display: flex;
	}
	.topbar-github:hover {
		color: var(--text-primary);
	}

	.mobile-menu-btn {
		display: none;
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 4px;
	}

	/* ── BODY ── */
	.docs-body {
		display: flex;
		flex: 1;
		overflow: hidden;
	}

	/* ── SIDEBAR ── */
	.docs-sidebar {
		width: 260px;
		background: var(--bg-sidebar);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		position: relative;
		flex-shrink: 0;
		border-right: 1px solid var(--border);
	}

	.sidebar-spine {
		position: absolute;
		top: 0;
		right: 0;
		width: 3px;
		height: 100%;
		background: var(--spine);
		z-index: 10;
	}

	.sidebar-header {
		padding: 24px 20px 16px;
		border-bottom: 1px solid rgba(255, 255, 255, 0.04);
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.brand-badge {
		width: 28px;
		height: 28px;
		background: var(--accent);
		border-radius: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.brand-badge-letter {
		font-family: var(--font-serif);
		font-size: 15px;
		color: white;
		font-style: italic;
		font-weight: 700;
	}

	.sidebar-brand-name {
		font-family: var(--font-sans);
		font-size: 14px;
		color: #e8dfd0;
		font-weight: 600;
		letter-spacing: 0.01em;
	}

	.sidebar-version {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #6b5e4e;
		letter-spacing: 0.08em;
	}

	.sidebar-search {
		padding: 14px 16px;
		border-bottom: 1px solid rgba(255, 255, 255, 0.04);
	}

	.search-wrap {
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-icon {
		position: absolute;
		left: 10px;
		color: #6b5e4e;
		pointer-events: none;
	}

	.search-input {
		width: 100%;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.06);
		border-radius: 4px;
		padding: 8px 50px 8px 32px;
		color: #e8dfd0;
		font-family: var(--font-mono);
		font-size: 11px;
		outline: none;
		transition: border-color 0.2s;
	}
	.search-input::placeholder {
		color: #6b5e4e;
	}
	.search-input:focus {
		border-color: var(--accent);
	}

	.search-shortcut {
		position: absolute;
		right: 8px;
		font-family: var(--font-mono);
		font-size: 10px;
		color: #4a4238;
		background: rgba(255, 255, 255, 0.04);
		padding: 2px 6px;
		border-radius: 3px;
		border: 1px solid rgba(255, 255, 255, 0.06);
		pointer-events: none;
	}

	.sidebar-nav {
		flex: 1;
		overflow-y: auto;
		padding: 14px 0 24px;
		scrollbar-width: thin;
		scrollbar-color: #2a2318 transparent;
	}

	.nav-section {
		margin-bottom: 8px;
	}

	.nav-section-label {
		font-family: var(--font-mono);
		font-size: 10px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #8a7d6e;
		padding: 8px 20px 6px;
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.nav-section-label svg {
		opacity: 0.6;
	}

	.nav-section.muted .nav-section-label {
		opacity: 0.4;
	}

	.coming-soon-badge {
		font-size: 8px;
		color: var(--accent);
		background: rgba(0, 173, 239, 0.1);
		padding: 1px 5px;
		border-radius: 3px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-left: auto;
	}

	.docs-shell.light .coming-soon-badge {
		background: rgba(0, 130, 180, 0.08);
		color: var(--accent);
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 20px;
		cursor: pointer;
		font-family: var(--font-body);
		font-size: 13px;
		color: #d4c9b8;
		opacity: 0.65;
		transition: all 0.15s;
		position: relative;
		text-decoration: none;
	}

	.nav-item:hover {
		background: rgba(255, 255, 255, 0.03);
		opacity: 1;
	}

	.nav-item.active {
		opacity: 1;
		color: #ffffff;
		background: rgba(0, 173, 239, 0.08);
	}

	.nav-item.active::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		width: 3px;
		height: 100%;
		background: var(--accent);
	}

	.nav-dot {
		width: 4px;
		height: 4px;
		border-radius: 50%;
		background: currentColor;
		opacity: 0.3;
		flex-shrink: 0;
	}

	.nav-item.active .nav-dot {
		opacity: 1;
		background: var(--accent);
	}

	/* ── MAIN CONTENT ── */
	.docs-main {
		flex: 1;
		display: flex;
		overflow: hidden;
		position: relative;
		background: var(--bg-page);
	}

	/* Notebook rulings — visible like real notebook paper */
	.notebook-rules {
		position: absolute;
		inset: 0;
		background-image: repeating-linear-gradient(
			180deg,
			transparent 0px,
			transparent 31px,
			var(--notebook-line) 31px,
			var(--notebook-line) 32px
		);
		background-position: 0 8px;
		pointer-events: none;
		z-index: 0;
		opacity: 1;
	}

	/* Red margin line — like a real notebook margin */
	.notebook-margin {
		position: absolute;
		top: 0;
		left: 48px;
		width: 2px;
		height: 100%;
		background: var(--notebook-margin);
		pointer-events: none;
		z-index: 0;
	}

	.docs-content-wrap {
		flex: 1;
		overflow-y: auto;
		position: relative;
		z-index: 1;
		scrollbar-width: thin;
		scrollbar-color: var(--border) transparent;
	}

	.doc-content {
		max-width: 780px;
		padding: 40px 48px 80px 72px;
	}

	/* ── TOC RAIL ── */
	.toc-rail {
		width: 200px;
		flex-shrink: 0;
		padding: 40px 16px 40px 0;
		position: sticky;
		top: 0;
		align-self: flex-start;
		max-height: calc(100vh - 56px);
		overflow-y: auto;
		scrollbar-width: none;
		z-index: 2;
	}
	.toc-rail::-webkit-scrollbar {
		display: none;
	}

	.toc-label {
		font-family: var(--font-mono);
		font-size: 10px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
		margin-bottom: 12px;
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.toc-nav {
		display: flex;
		flex-direction: column;
		gap: 1px;
		border-left: 1px solid var(--border);
	}

	.toc-item {
		background: none;
		border: none;
		text-align: left;
		cursor: pointer;
		font-family: var(--font-sans);
		font-size: 11.5px;
		color: var(--text-muted);
		padding: 5px 12px;
		line-height: 1.45;
		border-left: 2px solid transparent;
		margin-left: -1px;
		transition: all 0.15s;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.toc-item:hover {
		color: var(--text-secondary);
	}

	.toc-item.active {
		color: var(--accent);
		border-left-color: var(--accent);
	}

	.toc-item.h3 {
		padding-left: 24px;
		font-size: 11px;
	}

	/* ── Sidebar overlay for mobile ── */
	.sidebar-overlay {
		display: none;
	}

	/* ── Responsive ── */
	@media (max-width: 1200px) {
		.toc-rail {
			display: none;
		}
	}

	@media (max-width: 900px) {
		.docs-sidebar {
			position: fixed;
			top: 56px;
			left: 0;
			bottom: 0;
			z-index: 300;
			transform: translateX(-100%);
			transition: transform 0.25s var(--ease-premium);
		}

		.docs-sidebar.open {
			transform: translateX(0);
		}

		.sidebar-overlay {
			display: block;
			position: fixed;
			inset: 0;
			top: 56px;
			background: rgba(0, 0, 0, 0.5);
			z-index: 299;
		}

		.mobile-menu-btn {
			display: flex;
		}

		.doc-content {
			padding: 32px 24px 80px 24px;
		}

		.notebook-margin {
			display: none;
		}
	}

	@media (max-width: 640px) {
		.topbar-link,
		.topbar-github {
			display: none;
		}

		.doc-content {
			padding: 24px 16px 60px 16px;
		}
	}

	/* Scrollbar */
	::-webkit-scrollbar {
		width: 5px;
		height: 5px;
	}
	::-webkit-scrollbar-track {
		background: transparent;
	}
	::-webkit-scrollbar-thumb {
		background: var(--border);
		border-radius: 3px;
	}
</style>
