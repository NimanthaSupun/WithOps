<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isDarkMode } from '$lib/stores.js';

	let { children } = $props();

	let darkMode = $state(false);
	let sidebarOpen = $state(true);
	let mobileSidebarOpen = $state(false);
	let searchQuery = $state('');
	let searchFocused = $state(false);
	let activeSection = $state('');
	let tocItems = $state([]);
	let scrollY = $state(0);

	isDarkMode.subscribe((value) => {
		darkMode = value;
	});

	onMount(() => {
		isDarkMode.init();
		updateActiveSection();
		buildToc();
		window.addEventListener('scroll', handleScroll);
		return () => window.removeEventListener('scroll', handleScroll);
	});

	function handleScroll() {
		scrollY = window.scrollY;
		updateActiveSection();
	}

	function updateActiveSection() {
		const headings = document.querySelectorAll('.doc-content h2, .doc-content h3');
		let current = '';
		headings.forEach((h) => {
			if (h.getBoundingClientRect().top <= 100) {
				current = h.id;
			}
		});
		activeSection = current;
	}

	function buildToc() {
		// TOC is built by child pages via event
		setTimeout(() => {
			const headings = document.querySelectorAll('.doc-content h2, .doc-content h3');
			tocItems = Array.from(headings).map((h) => ({
				id: h.id,
				text: h.textContent,
				level: h.tagName === 'H2' ? 2 : 3
			}));
		}, 100);
	}

	// Rebuild TOC when route changes
	$effect(() => {
		if ($page.url.pathname) {
			setTimeout(buildToc, 200);
		}
	});

	function toggleTheme() {
		isDarkMode.toggle();
	}

	const currentPath = $derived($page.url.pathname);

	// Navigation structure — Getting Started only
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

	function isActive(href) {
		return currentPath === href;
	}

	function isGroupActive(group) {
		return group.items.some((item) => currentPath === item.href);
	}

	function scrollToHeading(id) {
		const el = document.getElementById(id);
		if (el) {
			el.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}

	// Find prev/next pages for bottom nav
	const allPages = $derived(navigation.flatMap((g) => g.items));
	const currentIndex = $derived(allPages.findIndex((p) => p.href === currentPath));
	const prevPage = $derived(currentIndex > 0 ? allPages[currentIndex - 1] : null);
	const nextPage = $derived(currentIndex < allPages.length - 1 ? allPages[currentIndex + 1] : null);
</script>

<svelte:head>
	<title>Documentation - WithOps</title>
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Source+Serif+4:ital,wght@0,400;0,600;0,700;1,400&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<div class="docs-shell {darkMode ? 'dark' : 'light'}">
	<!-- Top Navigation Bar -->
	<header class="docs-topbar">
		<div class="topbar-inner">
			<div class="topbar-left">
				<a href="/" class="docs-brand">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<span class="brand-name">WithOps</span>
				</a>
				<span class="brand-separator"></span>
				<a href="/docs/getting-started" class="docs-label">Docs</a>
			</div>

			<div class="topbar-center">
				<div class="search-container {searchFocused ? 'focused' : ''}">
					<svg
						class="search-icon"
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
					</svg>
					<input
						type="text"
						placeholder="Search documentation..."
						class="search-input"
						bind:value={searchQuery}
						onfocus={() => (searchFocused = true)}
						onblur={() => (searchFocused = false)}
					/>
					<kbd class="search-shortcut">⌘K</kbd>
				</div>
			</div>

			<div class="topbar-right">
				<a href="/dashboard" class="topbar-link">Dashboard</a>
				<button onclick={toggleTheme} class="theme-toggle" title="Toggle theme">
					{#if darkMode}
						<svg
							width="16"
							height="16"
							viewBox="0 0 24 24"
							fill="none"
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
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
						</svg>
					{/if}
				</button>

				<!-- Mobile menu toggle -->
				<button class="mobile-menu-btn" onclick={() => (mobileSidebarOpen = !mobileSidebarOpen)}>
					<svg
						width="18"
						height="18"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						{#if mobileSidebarOpen}
							<path d="M18 6L6 18M6 6l12 12" />
						{:else}
							<path d="M3 12h18M3 6h18M3 18h18" />
						{/if}
					</svg>
				</button>
			</div>
		</div>
	</header>

	<div class="docs-body">
		<!-- Sidebar -->
		<aside class="docs-sidebar {mobileSidebarOpen ? 'mobile-open' : ''}">
			<nav class="sidebar-nav">
				{#each navigation as group}
					<div class="nav-group {isGroupActive(group) ? 'active' : ''}">
						<div class="nav-group-label">
							{#if group.icon === 'rocket'}
								<svg
									width="14"
									height="14"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
								>
									<path
										d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"
									/>
									<path
										d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"
									/>
									<path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
									<path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
								</svg>
							{/if}
							<span>{group.title}</span>
						</div>
						<ul class="nav-items">
							{#each group.items as item}
								<li>
									<a
										href={item.href}
										class="nav-item {isActive(item.href) ? 'active' : ''}"
										onclick={() => (mobileSidebarOpen = false)}
									>
										<span class="nav-item-indicator"></span>
										{item.title}
									</a>
								</li>
							{/each}
						</ul>
					</div>
				{/each}

				<!-- Coming soon sections - visually muted -->
				<div class="nav-group coming-soon">
					<div class="nav-group-label muted">
						<svg
							width="14"
							height="14"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" />
						</svg>
						<span>Platform Overview</span>
						<span class="soon-badge">Soon</span>
					</div>
				</div>
				<div class="nav-group coming-soon">
					<div class="nav-group-label muted">
						<svg
							width="14"
							height="14"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<polygon
								points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"
							/>
						</svg>
						<span>Features</span>
						<span class="soon-badge">Soon</span>
					</div>
				</div>
				<div class="nav-group coming-soon">
					<div class="nav-group-label muted">
						<svg
							width="14"
							height="14"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline
								points="14 2 14 8 20 8"
							/><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
						</svg>
						<span>API Reference</span>
						<span class="soon-badge">Soon</span>
					</div>
				</div>
				<div class="nav-group coming-soon">
					<div class="nav-group-label muted">
						<svg
							width="14"
							height="14"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<rect x="2" y="2" width="20" height="8" rx="2" ry="2" /><rect
								x="2"
								y="14"
								width="20"
								height="8"
								rx="2"
								ry="2"
							/><line x1="6" y1="6" x2="6.01" y2="6" /><line x1="6" y1="18" x2="6.01" y2="18" />
						</svg>
						<span>Deployment</span>
						<span class="soon-badge">Soon</span>
					</div>
				</div>
			</nav>
		</aside>

		<!-- Main Content Area -->
		<main class="docs-main">
			<article class="doc-content">
				{@render children()}
			</article>

			<!-- Prev / Next Navigation -->
			{#if prevPage || nextPage}
				<nav class="page-nav">
					{#if prevPage}
						<a href={prevPage.href} class="page-nav-link prev">
							<span class="page-nav-direction">
								<svg
									width="14"
									height="14"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"><polyline points="15 18 9 12 15 6" /></svg
								>
								Previous
							</span>
							<span class="page-nav-title">{prevPage.title}</span>
						</a>
					{:else}
						<div></div>
					{/if}
					{#if nextPage}
						<a href={nextPage.href} class="page-nav-link next">
							<span class="page-nav-direction">
								Next
								<svg
									width="14"
									height="14"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"><polyline points="9 18 15 12 9 6" /></svg
								>
							</span>
							<span class="page-nav-title">{nextPage.title}</span>
						</a>
					{/if}
				</nav>
			{/if}
		</main>

		<!-- Right Rail: On This Page -->
		{#if tocItems.length > 0}
			<aside class="docs-toc">
				<div class="toc-inner">
					<p class="toc-title">On this page</p>
					<ul class="toc-list">
						{#each tocItems as item}
							<li>
								<button
									class="toc-link {item.level === 3 ? 'indent' : ''} {activeSection === item.id
										? 'active'
										: ''}"
									onclick={() => scrollToHeading(item.id)}
								>
									{item.text}
								</button>
							</li>
						{/each}
					</ul>
				</div>
			</aside>
		{/if}
	</div>
</div>

<style>
	/* ═══════════════════════════════════════════
	   WITHOPS DOCS — SOPHISTICATED NOTEBOOK STYLE
	   ═══════════════════════════════════════════ */

	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-serif: 'Source Serif 4', Georgia, 'Times New Roman', serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease: cubic-bezier(0.2, 0, 0, 1);
		--topbar-h: 56px;
		--sidebar-w: 260px;
		--toc-w: 200px;
	}

	/* ── Theme Tokens ── */
	.docs-shell.dark {
		--bg-page: #09090b;
		--bg-surface: #0f0f12;
		--bg-surface-2: #16161a;
		--bg-surface-3: #1c1c22;
		--bg-hover: #1e1e24;
		--border: rgba(255, 255, 255, 0.06);
		--border-strong: rgba(255, 255, 255, 0.1);
		--text-primary: #f0f0f3;
		--text-secondary: #8b8b97;
		--text-muted: #53535e;
		--accent: #a78bfa;
		--accent-soft: rgba(167, 139, 250, 0.08);
		--accent-border: rgba(167, 139, 250, 0.2);
		--callout-info-bg: rgba(59, 130, 246, 0.06);
		--callout-info-border: rgba(59, 130, 246, 0.15);
		--callout-info-text: #93c5fd;
		--callout-tip-bg: rgba(16, 185, 129, 0.06);
		--callout-tip-border: rgba(16, 185, 129, 0.15);
		--callout-tip-text: #6ee7b7;
		--callout-warn-bg: rgba(245, 158, 11, 0.06);
		--callout-warn-border: rgba(245, 158, 11, 0.15);
		--callout-warn-text: #fcd34d;
		--code-bg: #141418;
		--code-border: rgba(255, 255, 255, 0.05);
		--notebook-line: rgba(255, 255, 255, 0.025);
		--notebook-margin: rgba(167, 139, 250, 0.08);
		--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
		--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
	}

	.docs-shell.light {
		--bg-page: #fafaf9;
		--bg-surface: #ffffff;
		--bg-surface-2: #f5f5f4;
		--bg-surface-3: #e7e5e4;
		--bg-hover: #f5f5f4;
		--border: rgba(0, 0, 0, 0.06);
		--border-strong: rgba(0, 0, 0, 0.1);
		--text-primary: #1c1917;
		--text-secondary: #78716c;
		--text-muted: #a8a29e;
		--accent: #7c3aed;
		--accent-soft: rgba(124, 58, 237, 0.06);
		--accent-border: rgba(124, 58, 237, 0.2);
		--callout-info-bg: rgba(59, 130, 246, 0.05);
		--callout-info-border: rgba(59, 130, 246, 0.15);
		--callout-info-text: #2563eb;
		--callout-tip-bg: rgba(16, 185, 129, 0.05);
		--callout-tip-border: rgba(16, 185, 129, 0.15);
		--callout-tip-text: #059669;
		--callout-warn-bg: rgba(245, 158, 11, 0.05);
		--callout-warn-border: rgba(245, 158, 11, 0.15);
		--callout-warn-text: #d97706;
		--code-bg: #f5f5f4;
		--code-border: rgba(0, 0, 0, 0.06);
		--notebook-line: rgba(0, 0, 0, 0.03);
		--notebook-margin: rgba(124, 58, 237, 0.06);
		--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
		--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
	}

	/* ── Global Reset ── */
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	.docs-shell {
		min-height: 100vh;
		background: var(--bg-page);
		color: var(--text-primary);
		font-family: var(--font-sans);
	}

	/* ══════════════════════
	   TOP BAR
	   ══════════════════════ */
	.docs-topbar {
		position: sticky;
		top: 0;
		z-index: 100;
		height: var(--topbar-h);
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		backdrop-filter: blur(16px);
	}

	.topbar-inner {
		max-width: 1440px;
		margin: 0 auto;
		height: 100%;
		padding: 0 1.5rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.topbar-left {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-shrink: 0;
	}

	.docs-brand {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		text-decoration: none;
		color: var(--text-primary);
	}

	.brand-icon {
		width: 24px;
		height: 24px;
	}

	.brand-name {
		font-weight: 700;
		font-size: 0.9rem;
		letter-spacing: -0.02em;
	}

	.brand-separator {
		width: 1px;
		height: 20px;
		background: var(--border-strong);
	}

	.docs-label {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--accent);
		text-decoration: none;
		letter-spacing: -0.01em;
	}

	/* Search */
	.topbar-center {
		flex: 1;
		max-width: 400px;
	}

	.search-container {
		position: relative;
		display: flex;
		align-items: center;
		background: var(--bg-surface-2);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0 0.75rem;
		transition: all 0.15s var(--ease);
	}

	.search-container.focused {
		border-color: var(--accent-border);
		background: var(--bg-surface);
		box-shadow: 0 0 0 3px var(--accent-soft);
	}

	.search-icon {
		color: var(--text-muted);
		flex-shrink: 0;
	}

	.search-input {
		width: 100%;
		padding: 0.5rem 0.5rem;
		background: transparent;
		border: none;
		outline: none;
		font-size: 0.8rem;
		color: var(--text-primary);
		font-family: var(--font-sans);
	}

	.search-input::placeholder {
		color: var(--text-muted);
	}

	.search-shortcut {
		font-family: var(--font-sans);
		font-size: 0.65rem;
		color: var(--text-muted);
		background: var(--bg-surface-3);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 0.125rem 0.375rem;
		flex-shrink: 0;
	}

	.topbar-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-shrink: 0;
	}

	.topbar-link {
		font-size: 0.8rem;
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
		padding: 0.375rem;
		border-radius: 6px;
		cursor: pointer;
		display: flex;
		transition: all 0.15s;
	}

	.theme-toggle:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
		border-color: var(--border-strong);
	}

	.mobile-menu-btn {
		display: none;
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		padding: 0.375rem;
		border-radius: 6px;
		cursor: pointer;
	}

	/* ══════════════════════
	   MAIN BODY LAYOUT
	   ══════════════════════ */
	.docs-body {
		display: flex;
		max-width: 1440px;
		margin: 0 auto;
		min-height: calc(100vh - var(--topbar-h));
	}

	/* ══════════════════════
	   SIDEBAR
	   ══════════════════════ */
	.docs-sidebar {
		position: sticky;
		top: var(--topbar-h);
		width: var(--sidebar-w);
		height: calc(100vh - var(--topbar-h));
		overflow-y: auto;
		border-right: 1px solid var(--border);
		padding: 1.5rem 0;
		flex-shrink: 0;
		scrollbar-width: thin;
		scrollbar-color: var(--border-strong) transparent;
	}

	.sidebar-nav {
		padding: 0 1rem;
	}

	.nav-group {
		margin-bottom: 1.75rem;
	}

	.nav-group-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-secondary);
		padding: 0 0.5rem;
		margin-bottom: 0.5rem;
	}

	.nav-group-label.muted {
		color: var(--text-muted);
	}

	.soon-badge {
		font-size: 0.55rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text-muted);
		background: var(--bg-surface-3);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 0.05rem 0.35rem;
		margin-left: auto;
	}

	.nav-items {
		list-style: none;
		padding: 0;
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.4rem 0.5rem 0.4rem 0.75rem;
		border-radius: 6px;
		font-size: 0.8rem;
		font-weight: 450;
		color: var(--text-secondary);
		text-decoration: none;
		transition: all 0.12s var(--ease);
		position: relative;
	}

	.nav-item:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.nav-item-indicator {
		width: 3px;
		height: 0;
		border-radius: 2px;
		background: var(--accent);
		position: absolute;
		left: 0;
		top: 50%;
		transform: translateY(-50%);
		transition: height 0.2s var(--ease);
	}

	.nav-item.active {
		color: var(--accent);
		background: var(--accent-soft);
		font-weight: 550;
	}

	.nav-item.active .nav-item-indicator {
		height: 16px;
	}

	.coming-soon {
		opacity: 0.5;
		pointer-events: none;
	}

	/* ══════════════════════
	   MAIN CONTENT — "NOTEBOOK" STYLE
	   ══════════════════════ */
	.docs-main {
		flex: 1;
		min-width: 0;
		padding: 2.5rem 3rem 4rem;
		/* Notebook ruled-line background */
		background-image: linear-gradient(var(--notebook-line) 1px, transparent 1px);
		background-size: 100% 2rem;
		background-position: 0 0.5rem;
		/* Subtle left margin line (notebook binding) */
		border-left: none;
		position: relative;
	}

	.docs-main::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 3px;
		background: var(--notebook-margin);
	}

	/* ══════════════════════
	   RIGHT RAIL (TOC)
	   ══════════════════════ */
	.docs-toc {
		position: sticky;
		top: var(--topbar-h);
		width: var(--toc-w);
		height: calc(100vh - var(--topbar-h));
		overflow-y: auto;
		flex-shrink: 0;
		padding: 2rem 1rem 2rem 0;
	}

	.toc-inner {
		padding-left: 1rem;
		border-left: 1px solid var(--border);
	}

	.toc-title {
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-muted);
		margin-bottom: 0.75rem;
	}

	.toc-list {
		list-style: none;
		padding: 0;
	}

	.toc-link {
		display: block;
		width: 100%;
		text-align: left;
		background: none;
		border: none;
		padding: 0.25rem 0;
		font-size: 0.75rem;
		font-family: var(--font-sans);
		color: var(--text-muted);
		cursor: pointer;
		transition: color 0.15s;
		line-height: 1.4;
	}

	.toc-link:hover {
		color: var(--text-primary);
	}

	.toc-link.active {
		color: var(--accent);
		font-weight: 500;
	}

	.toc-link.indent {
		padding-left: 0.75rem;
	}

	/* ══════════════════════
	   PAGE NAVIGATION (prev/next)
	   ══════════════════════ */
	.page-nav {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		margin-top: 4rem;
		padding-top: 2rem;
		border-top: 1px solid var(--border);
	}

	.page-nav-link {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 1rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: 10px;
		text-decoration: none;
		transition: all 0.15s var(--ease);
		min-width: 160px;
	}

	.page-nav-link:hover {
		border-color: var(--accent-border);
		background: var(--accent-soft);
	}

	.page-nav-link.next {
		text-align: right;
		margin-left: auto;
	}

	.page-nav-direction {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.7rem;
		font-weight: 500;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.page-nav-link.next .page-nav-direction {
		justify-content: flex-end;
	}

	.page-nav-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--accent);
	}

	/* ══════════════════════
	   RESPONSIVE
	   ══════════════════════ */
	@media (max-width: 1200px) {
		.docs-toc {
			display: none;
		}
	}

	@media (max-width: 768px) {
		.mobile-menu-btn {
			display: flex;
		}

		.topbar-center {
			display: none;
		}

		.topbar-link {
			display: none;
		}

		.docs-sidebar {
			position: fixed;
			top: var(--topbar-h);
			left: 0;
			z-index: 90;
			background: var(--bg-surface);
			transform: translateX(-100%);
			transition: transform 0.25s var(--ease);
			box-shadow: var(--shadow-md);
		}

		.docs-sidebar.mobile-open {
			transform: translateX(0);
		}

		.docs-main {
			padding: 1.5rem 1.25rem 3rem;
		}

		.docs-main::before {
			display: none;
		}
	}
</style>
