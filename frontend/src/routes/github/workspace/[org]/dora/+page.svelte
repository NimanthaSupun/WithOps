<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isDarkMode } from '$lib/stores';
	import { onMount } from 'svelte';

	const org = $page.params.org;
	const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';

	function getToken() {
		return localStorage.getItem('auth0_token') || localStorage.getItem('auth_token');
	}

	let loading = $state(true);
	let error = $state(null);
	let summary = $state(null);
	let repoData = $state(null);
	let trendsData = $state(null);
	let correlationData = $state(null);
	let activeTab = $state('overview');
	let selectedDays = $state(30);

	const classColors = {
		elite: { bg: 'rgba(16,185,129,0.1)', color: '#10b981', label: 'Elite' },
		high: { bg: 'rgba(0,173,239,0.1)', color: '#00adef', label: 'High' },
		medium: { bg: 'rgba(245,158,11,0.1)', color: '#f59e0b', label: 'Medium' },
		low: { bg: 'rgba(239,68,68,0.1)', color: '#ef4444', label: 'Low' }
	};

	const trendIcons = { improving: '↑', declining: '↓', stable: '→', neutral: '—' };
	const trendColors = { improving: '#10b981', declining: '#ef4444', stable: '#94a3b8', neutral: '#475569' };

	onMount(async () => { await fetchData(); });

	async function fetchData() {
		loading = true; error = null;
		try {
			const token = getToken();
			if (!token) { error = 'Authentication required.'; loading = false; return; }
			const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

			const [sumRes, repoRes, trendRes, corrRes] = await Promise.all([
				fetch(`${API}/api/dora/${org}/summary?days=${selectedDays}`, { headers }),
				fetch(`${API}/api/dora/${org}/repos?days=${selectedDays}`, { headers }),
				fetch(`${API}/api/dora/${org}/trends?period=weekly&count=12`, { headers }),
				fetch(`${API}/api/dora/${org}/correlation`, { headers })
			]);

			if (sumRes.ok) summary = await sumRes.json();
			else throw new Error(`Failed to fetch DORA metrics: ${sumRes.statusText}`);

			if (repoRes.ok) repoData = await repoRes.json();
			if (trendRes.ok) trendsData = await trendRes.json();
			if (corrRes.ok) correlationData = await corrRes.json();
		} catch (err) {
			console.error('DORA fetch error:', err);
			error = err.message;
		} finally { loading = false; }
	}

	function formatDuration(s) {
		if (!s || s <= 0) return 'N/A';
		if (s < 60) return `${Math.round(s)}s`;
		if (s < 3600) return `${Math.round(s/60)}m`;
		if (s < 86400) { const h=Math.floor(s/3600), m=Math.round((s%3600)/60); return m>0?`${h}h ${m}m`:`${h}h`; }
		return `${(s/86400).toFixed(1)}d`;
	}
</script>

<svelte:head><title>DORA Metrics - {org}</title></svelte:head>

{#if loading && !summary}
<div class="loading-screen">
	<div class="loading-content">
		<img src="/icons/excellence_17274210.png" alt="WithOps" class="loading-icon" />
		<div class="status-message">COMPUTING DORA METRICS...</div>
	</div>
</div>
{:else}
<div class="dora-page {$isDarkMode ? 'dark' : 'light'}">
	<!-- Header -->
	<nav class="dashboard-header">
		<div class="header-content">
			<a href="/dashboard" class="nav-brand">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
				<span class="brand-name">WithOps</span>
			</a>
			<div class="nav-menu">
				<a href="/dashboard" class="nav-link">Overview</a>
				<a href="/organizations" class="nav-link">Organizations</a>
				<a href="/github/workspace/{org}" class="nav-link">Workspace</a>
				<a href="/github/workspace/{org}/intelligence" class="nav-link">Intelligence</a>
				<a href="/github/workspace/{org}/dora" class="nav-link active">DORA</a>
				<button onclick={() => isDarkMode.set(!$isDarkMode)} class="theme-toggle" title="Toggle theme">
					{#if $isDarkMode}
						<svg class="theme-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
					{:else}
						<svg class="theme-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
					{/if}
				</button>
			</div>
		</div>
	</nav>

	<!-- Breadcrumb -->
	<div class="technical-bar">
		<a href="/" class="bc-node">WithOps</a><span class="bc-sep">/</span>
		<a href="/organizations" class="bc-node">Organizations</a><span class="bc-sep">/</span>
		<a href="/github/workspace/{org}" class="bc-node">{org}</a><span class="bc-sep">/</span>
		<span class="bc-node active">DORA Metrics</span>
		<div class="system-status"><div class="status-pulse"></div>DORA: ACTIVE</div>
	</div>

	<div class="page-content">
		<main class="page-main">
			{#if error}
				<div class="state-card">
					<div class="state-icon">⚠️</div>
					<h3 class="state-title">Error Loading DORA Metrics</h3>
					<p class="state-message">{error}</p>
					<button onclick={fetchData} class="btn btn-primary">Try Again</button>
				</div>
			{:else if summary}
				<!-- Page Header -->
				<header class="view-header">
					<div class="title-group">
						<h1>DORA Metrics</h1>
						<p>DevOps Research & Assessment performance for <strong>{org}</strong></p>
					</div>
					<div class="header-cta">
						<div class="score-pill" style="background:{classColors[summary.classification]?.bg}; border-color:{classColors[summary.classification]?.color}">
							<span class="score-lbl">PERFORMANCE</span>
							<span class="score-num" style="color:{classColors[summary.classification]?.color}">{classColors[summary.classification]?.label || 'N/A'}</span>
						</div>
						<select class="period-select" bind:value={selectedDays} onchange={fetchData}>
							<option value={7}>7 Days</option>
							<option value={30}>30 Days</option>
							<option value={90}>90 Days</option>
						</select>
						<button onclick={fetchData} class="btn btn-primary" disabled={loading}>
							{loading ? 'Loading...' : 'Refresh ↻'}
						</button>
					</div>
				</header>

				<!-- Tab Navigation -->
				<div class="filter-nav">
					{#each [{key:'overview',label:'OVERVIEW'},{key:'trends',label:'TRENDS'},{key:'repos',label:'REPOSITORIES'},{key:'correlation',label:'DORA × DSOMM'}] as tab}
						<button class="filter-btn {activeTab===tab.key?'active':''}" onclick={()=>activeTab=tab.key}>{tab.label}</button>
					{/each}
				</div>

				{#if activeTab === 'overview'}
					<!-- 4 DORA Metric Cards -->
					<div class="stats-grid">
						{#each summary.cards || [] as card, i}
							{@const cls = classColors[card.classification] || classColors.low}
							<div class="stat-card">
								<div class="stat-icon" style="background:{cls.bg};color:{cls.color}">
									{#if i===0}<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
									{:else if i===1}<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
									{:else if i===2}<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-2.5L13.73 4c-.77-1.33-2.69-1.33-3.46 0L3.34 16.5C2.57 17.33 3.53 19 5.07 19z"/></svg>
									{:else}<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M4 4v5h.58m15.36 2A8 8 0 004.58 9m0 0H9m11 11v-5h-.58m0 0a8 8 0 01-15.36-2m15.36 2H15"/></svg>
									{/if}
								</div>
								<div class="stat-content">
									<p class="stat-label">{card.metric}</p>
									<p class="stat-value">{card.formatted}</p>
								</div>
								<div class="stat-trend">
									<span class="trend-badge" style="color:{trendColors[card.trend]}">
										{trendIcons[card.trend] || '—'} {card.classification?.toUpperCase()}
									</span>
								</div>
							</div>
						{/each}
					</div>

					<!-- DORA Benchmark Reference -->
					<div class="intel-card">
						<h2 class="card-heading">Google DORA Benchmarks</h2>
						<div class="benchmark-table">
							<table>
								<thead><tr><th>Metric</th><th>Elite</th><th>High</th><th>Medium</th><th>Low</th></tr></thead>
								<tbody>
									<tr><td>Deploy Frequency</td><td>Multiple/day</td><td>Weekly</td><td>Monthly</td><td>&lt; Monthly</td></tr>
									<tr><td>Lead Time</td><td>&lt; 1 hour</td><td>&lt; 1 day</td><td>&lt; 1 week</td><td>&gt; 1 week</td></tr>
									<tr><td>Change Failure Rate</td><td>0-5%</td><td>5-15%</td><td>15-30%</td><td>&gt; 30%</td></tr>
									<tr><td>MTTR</td><td>&lt; 1 hour</td><td>&lt; 1 day</td><td>&lt; 1 week</td><td>&gt; 1 week</td></tr>
								</tbody>
							</table>
						</div>
					</div>

					<!-- Deployment Summary -->
					<div class="intel-card">
						<h2 class="card-heading">Deployment Summary</h2>
						<div class="deploy-summary">
							<div class="deploy-stat"><span class="deploy-label">Total Deployments</span><span class="deploy-val">{summary.total_deployments || 0}</span></div>
							<div class="deploy-stat"><span class="deploy-label">Period</span><span class="deploy-val">{summary.period_days} days</span></div>
						</div>
					</div>
				{/if}

				{#if activeTab === 'repos'}
					<div class="intel-card">
						<h2 class="card-heading">Repository Performance</h2>
						{#if repoData?.repositories?.length > 0}
							<div class="repo-table-wrap">
								<table class="repo-table">
									<thead><tr><th>Repository</th><th>Deploy Freq</th><th>Lead Time</th><th>Failure Rate</th><th>MTTR</th><th>Level</th><th>Deploys</th></tr></thead>
									<tbody>
										{#each repoData.repositories as repo}
											{@const cls = classColors[repo.classification] || classColors.low}
											<tr>
												<td class="repo-name-cell">{repo.repo_name}</td>
												<td class="mono">{repo.deployment_frequency.toFixed(2)}/day</td>
												<td class="mono">{formatDuration(repo.lead_time_seconds)}</td>
												<td class="mono">{(repo.change_failure_rate * 100).toFixed(0)}%</td>
												<td class="mono">{formatDuration(repo.mttr_seconds)}</td>
												<td><span class="level-badge" style="background:{cls.bg};color:{cls.color}">{cls.label}</span></td>
												<td class="mono">{repo.total_deployments}</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{:else}
							<div class="empty-msg">No deployment data found. Connect repositories and trigger CI/CD pipelines to start tracking.</div>
						{/if}
					</div>
				{/if}

				{#if activeTab === 'trends'}
					<div class="intel-card">
						<h2 class="card-heading">Performance Trends (12 Weeks)</h2>
						{#if trendsData?.trends?.length > 0}
							<div class="trends-grid">
								{#each trendsData.trends as point, idx}
									{@const cls = classColors[point.classification] || classColors.low}
									<div class="trend-row">
										<div class="trend-period">
											<span class="trend-week">W{idx + 1}</span>
											<span class="trend-date">{new Date(point.period_end).toLocaleDateString('en-US',{month:'short',day:'numeric'})}</span>
										</div>
										<div class="trend-metrics">
											<span class="trend-metric" title="Deploy Freq">{point.deployment_frequency.toFixed(2)}/d</span>
											<span class="trend-metric" title="Lead Time">{formatDuration(point.lead_time_seconds)}</span>
											<span class="trend-metric" title="Failure Rate">{(point.change_failure_rate*100).toFixed(0)}%</span>
											<span class="trend-metric" title="MTTR">{formatDuration(point.mttr_seconds)}</span>
										</div>
										<span class="level-badge" style="background:{cls.bg};color:{cls.color}">{cls.label}</span>
										<div class="trend-bar-wrap">
											<div class="trend-bar" style="width:{Math.min(point.total_deployments * 8, 100)}%;background:{cls.color}"></div>
										</div>
										<span class="trend-deploys">{point.total_deployments}</span>
									</div>
								{/each}
							</div>
						{:else}
							<div class="empty-msg">No trend data available yet. Deployment events will populate trends over time.</div>
						{/if}
					</div>
				{/if}

				{#if activeTab === 'correlation'}
					<div class="intel-card">
						<h2 class="card-heading">DORA × DSOMM Correlation Analysis</h2>
						<p class="card-subtitle">Measuring the relationship between security maturity and delivery performance</p>
						{#if correlationData?.has_data}
							<div class="correlation-grid">
								<div class="corr-card">
									<div class="corr-label">DSOMM MATURITY</div>
									<div class="corr-value">{correlationData.dsomm_data?.average_maturity_score?.toFixed(1) || 'N/A'}<span class="corr-unit">/100</span></div>
									<div class="corr-detail">{correlationData.dsomm_data?.total_assessments || 0} assessments</div>
								</div>
								<div class="corr-card">
									<div class="corr-label">DORA PERFORMANCE</div>
									<div class="corr-value" style="color:{(classColors[correlationData.dora_metrics?.classification] || classColors.low).color}">{(classColors[correlationData.dora_metrics?.classification] || classColors.low).label}</div>
									<div class="corr-detail">{correlationData.dora_metrics?.total_deployments || 0} deployments</div>
								</div>
							</div>
							<div class="insight-box">
								<div class="insight-icon">💡</div>
								<div class="insight-text">{correlationData.correlation_insight}</div>
							</div>
							{#if correlationData.dsomm_data?.assessments?.length > 0}
								<h3 class="sub-heading">Maturity Assessments</h3>
								<div class="assessments-list">
									{#each correlationData.dsomm_data.assessments as a}
										<div class="assessment-row">
											<span class="assessment-name">{a.project_name}</span>
											<span class="assessment-score">{a.maturity_score?.toFixed(1)}</span>
											<span class="assessment-level">{a.maturity_level || '—'}</span>
										</div>
									{/each}
								</div>
							{/if}
						{:else}
							<div class="empty-msg">Run a DSOMM maturity assessment from the <a href="/github/workspace/{org}/intelligence">Intelligence</a> page to enable correlation analysis.</div>
						{/if}
					</div>
				{/if}
			{/if}
		</main>
	</div>
</div>
{/if}

<style>
	:root { --font-sans:'Inter',system-ui,sans-serif; --font-mono:'JetBrains Mono','Fira Code',monospace; --ease-premium:cubic-bezier(.2,0,0,1); --nav-height:64px; }
	.dora-page.dark { --bg-app:#000; --bg-surface:#020202; --bg-surface-alt:#050505; --border:rgba(255,255,255,.03); --border-focus:rgba(255,255,255,.08); --text-primary:#f8fafc; --text-secondary:#94a3b8; --text-muted:#475569; --accent:#00adef; --accent-soft:rgba(0,173,239,.05); --success:#10b981; --warning:#f59e0b; --error:#ef4444; --card-shadow:none; }
	.dora-page.light { --bg-app:#fff; --bg-surface:#f8fafc; --bg-surface-alt:#f1f5f9; --border:rgba(0,0,0,.06); --border-focus:rgba(0,173,239,.2); --text-primary:#0f172a; --text-secondary:#475569; --text-muted:#94a3b8; --accent:#0082b4; --accent-soft:rgba(0,130,180,.08); --success:#059669; --warning:#d97706; --error:#dc2626; --card-shadow:0 4px 12px rgba(0,0,0,.03); }
	.dora-page { min-height:100vh; background:var(--bg-app); color:var(--text-primary); font-family:var(--font-sans); transition:background .3s ease; }
	.dora-page::before { content:''; position:fixed; inset:0; background-image:linear-gradient(var(--border) 1px,transparent 1px),linear-gradient(90deg,var(--border) 1px,transparent 1px); background-size:40px 40px; mask-image:radial-gradient(circle at 50% 50%,black,transparent 80%); pointer-events:none; z-index:0; opacity:.5; }

	/* Loading */
	.loading-screen { display:flex; align-items:center; justify-content:center; min-height:100vh; background:#000; }
	.loading-content { text-align:center; }
	.loading-icon { width:40px; height:40px; margin-bottom:1.5rem; animation:pulse 2s infinite; }
	.status-message { font-family:var(--font-mono); font-size:.7rem; color:#475569; letter-spacing:.1em; }
	@keyframes pulse { 0%,100%{opacity:.5;transform:scale(.95)} 50%{opacity:1;transform:scale(1)} }

	/* Header */
	.dashboard-header { height:var(--nav-height); background:var(--bg-surface); backdrop-filter:blur(12px); border-bottom:1px solid var(--border); display:flex; align-items:center; position:sticky; top:0; z-index:100; }
	.header-content { max-width:1400px; margin:0 auto; padding:0 2rem; display:flex; align-items:center; justify-content:space-between; width:100%; }
	.nav-brand { display:flex; align-items:center; gap:.5rem; text-decoration:none; color:var(--text-primary); }
	.brand-icon { width:24px; height:24px; }
	.brand-name { font-size:.875rem; font-weight:700; letter-spacing:-.02em; }
	.nav-menu { display:flex; align-items:center; gap:.25rem; }
	.nav-link { font-size:.75rem; font-weight:600; color:var(--text-muted); text-decoration:none; padding:.5rem .75rem; border-radius:6px; transition:all .15s; }
	.nav-link:hover { color:var(--text-primary); }
	.nav-link.active { color:var(--accent); background:var(--accent-soft); }
	.theme-toggle { background:none; border:none; color:var(--text-muted); cursor:pointer; padding:.5rem; border-radius:8px; display:flex; align-items:center; }
	.theme-toggle:hover { color:var(--text-primary); }
	.theme-icon { width:16px; height:16px; }

	/* Breadcrumb */
	.technical-bar { display:flex; align-items:center; gap:.5rem; padding:.5rem 2rem; background:var(--bg-surface-alt); border-bottom:1px solid var(--border); font-family:var(--font-mono); font-size:.65rem; color:var(--text-muted); max-width:100%; }
	.bc-node { color:var(--text-muted); text-decoration:none; }
	.bc-node:hover { color:var(--text-primary); }
	.bc-node.active { color:var(--accent); }
	.bc-sep { opacity:.3; }
	.system-status { margin-left:auto; display:flex; align-items:center; gap:.5rem; font-size:.6rem; letter-spacing:.08em; }
	.status-pulse { width:6px; height:6px; border-radius:50%; background:var(--success); animation:pulse 2s infinite; }

	/* Content */
	.page-content { max-width:1400px; margin:0 auto; padding:2rem; position:relative; z-index:1; }
	.page-main { width:100%; }

	/* State card */
	.state-card { text-align:center; padding:6rem 2rem; }
	.state-icon { font-size:2rem; margin-bottom:1rem; }
	.state-title { font-size:1.125rem; font-weight:700; margin-bottom:.5rem; }
	.state-message { color:var(--text-secondary); font-size:.875rem; margin-bottom:1.5rem; line-height:1.5; }

	/* View Header */
	.view-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:2rem; gap:1rem; flex-wrap:wrap; }
	.title-group h1 { font-size:1.5rem; font-weight:800; letter-spacing:-.03em; margin-bottom:.25rem; }
	.title-group p { font-size:.8rem; color:var(--text-secondary); }
	.header-cta { display:flex; align-items:center; gap:.75rem; }
	.score-pill { display:flex; flex-direction:column; align-items:center; padding:.5rem 1rem; border-radius:8px; border:1px solid; }
	.score-lbl { font-family:var(--font-mono); font-size:.55rem; letter-spacing:.1em; color:var(--text-muted); }
	.score-num { font-family:var(--font-mono); font-size:1rem; font-weight:800; }
	.period-select { background:var(--bg-surface); color:var(--text-primary); border:1px solid var(--border); border-radius:6px; padding:.5rem .75rem; font-size:.75rem; font-family:var(--font-mono); cursor:pointer; }

	/* Buttons */
	.btn { padding:.5rem 1rem; border-radius:8px; font-size:.8rem; font-weight:600; cursor:pointer; border:1px solid var(--border); transition:all .15s; display:inline-flex; align-items:center; gap:.5rem; }
	.btn-primary { background:var(--text-primary); color:var(--bg-app); border-color:var(--text-primary); }
	.btn-primary:hover { opacity:.9; }
	.btn-primary:disabled { opacity:.5; cursor:not-allowed; }

	/* Filter Nav */
	.filter-nav { display:flex; gap:.25rem; background:var(--bg-surface-alt); padding:.25rem; border-radius:8px; border:1px solid var(--border); width:fit-content; margin-bottom:1.5rem; }
	.filter-btn { background:none; border:none; padding:.5rem 1rem; border-radius:6px; font-size:.7rem; font-weight:700; color:var(--text-muted); cursor:pointer; font-family:var(--font-mono); letter-spacing:.05em; transition:all .15s; }
	.filter-btn:hover { color:var(--text-primary); }
	.filter-btn.active { background:var(--bg-surface); color:var(--accent); box-shadow:0 1px 3px rgba(0,0,0,.1); }

	/* Stats Grid */
	.stats-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:2rem; }
	.stat-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:12px; padding:1.25rem; display:flex; align-items:center; gap:1rem; transition:all .2s var(--ease-premium); box-shadow:var(--card-shadow); }
	.stat-card:hover { border-color:var(--border-focus); }
	.stat-icon { width:36px; height:36px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
	.stat-icon svg { width:18px; height:18px; }
	.stat-content { flex:1; min-width:0; }
	.stat-label { font-size:.6rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:.05em; font-family:var(--font-mono); margin-bottom:.25rem; }
	.stat-value { font-family:var(--font-mono); font-size:1.25rem; font-weight:700; }
	.stat-trend { flex-shrink:0; }
	.trend-badge { font-size:.6rem; font-family:var(--font-mono); padding:.25rem .5rem; border-radius:4px; border:1px solid var(--border); }

	/* Intel Card */
	.intel-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:12px; padding:1.5rem; margin-bottom:1.5rem; box-shadow:var(--card-shadow); }
	.card-heading { font-size:.875rem; font-weight:700; margin-bottom:1rem; letter-spacing:-.01em; }

	/* Benchmark Table */
	.benchmark-table { overflow-x:auto; }
	.benchmark-table table { width:100%; border-collapse:collapse; font-size:.75rem; }
	.benchmark-table th { text-align:left; padding:.5rem .75rem; font-family:var(--font-mono); font-size:.6rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:.05em; border-bottom:1px solid var(--border); }
	.benchmark-table td { padding:.5rem .75rem; border-bottom:1px solid var(--border); color:var(--text-secondary); }
	.benchmark-table tbody tr:hover { background:var(--bg-surface-alt); }

	/* Deploy Summary */
	.deploy-summary { display:flex; gap:2rem; }
	.deploy-stat { display:flex; flex-direction:column; gap:.25rem; }
	.deploy-label { font-family:var(--font-mono); font-size:.6rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:.05em; }
	.deploy-val { font-family:var(--font-mono); font-size:1.25rem; font-weight:700; }

	/* Repo Table */
	.repo-table-wrap { overflow-x:auto; }
	.repo-table { width:100%; border-collapse:collapse; font-size:.8rem; }
	.repo-table th { text-align:left; padding:.625rem .75rem; font-family:var(--font-mono); font-size:.6rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:.05em; border-bottom:1px solid var(--border); }
	.repo-table td { padding:.625rem .75rem; border-bottom:1px solid var(--border); }
	.repo-table tbody tr:hover { background:var(--bg-surface-alt); }
	.repo-name-cell { font-weight:600; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
	.mono { font-family:var(--font-mono); font-size:.75rem; }
	.level-badge { font-family:var(--font-mono); font-size:.6rem; font-weight:700; padding:.2rem .5rem; border-radius:4px; text-transform:uppercase; letter-spacing:.05em; }
	.empty-msg { text-align:center; padding:3rem; color:var(--text-muted); font-size:.875rem; }

	/* Trends */
	.trends-grid { display:flex; flex-direction:column; gap:.5rem; }
	.trend-row { display:flex; align-items:center; gap:1rem; padding:.625rem .75rem; border-radius:8px; border:1px solid var(--border); transition:all .15s; }
	.trend-row:hover { border-color:var(--border-focus); background:var(--bg-surface-alt); }
	.trend-period { display:flex; flex-direction:column; min-width:60px; }
	.trend-week { font-family:var(--font-mono); font-size:.7rem; font-weight:700; }
	.trend-date { font-family:var(--font-mono); font-size:.55rem; color:var(--text-muted); }
	.trend-metrics { display:flex; gap:.75rem; flex:1; }
	.trend-metric { font-family:var(--font-mono); font-size:.7rem; color:var(--text-secondary); min-width:50px; }
	.trend-bar-wrap { width:80px; height:6px; background:var(--border); border-radius:3px; overflow:hidden; }
	.trend-bar { height:100%; border-radius:3px; transition:width .3s var(--ease-premium); }
	.trend-deploys { font-family:var(--font-mono); font-size:.65rem; color:var(--text-muted); min-width:20px; text-align:right; }

	/* Correlation */
	.card-subtitle { font-size:.8rem; color:var(--text-secondary); margin-bottom:1.5rem; margin-top:-.5rem; }
	.correlation-grid { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1.5rem; }
	.corr-card { background:var(--bg-surface-alt); border:1px solid var(--border); border-radius:10px; padding:1.25rem; text-align:center; }
	.corr-label { font-family:var(--font-mono); font-size:.55rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:.5rem; }
	.corr-value { font-family:var(--font-mono); font-size:1.5rem; font-weight:800; }
	.corr-unit { font-size:.75rem; font-weight:400; color:var(--text-muted); }
	.corr-detail { font-size:.7rem; color:var(--text-muted); margin-top:.25rem; }
	.insight-box { display:flex; gap:1rem; padding:1rem; background:var(--accent-soft); border:1px solid var(--border-focus); border-radius:10px; margin-bottom:1.5rem; }
	.insight-icon { font-size:1.25rem; flex-shrink:0; }
	.insight-text { font-size:.8rem; color:var(--text-secondary); line-height:1.6; }
	.sub-heading { font-size:.8rem; font-weight:700; margin-bottom:.75rem; }
	.assessments-list { display:flex; flex-direction:column; gap:.5rem; }
	.assessment-row { display:flex; align-items:center; gap:1rem; padding:.5rem .75rem; border:1px solid var(--border); border-radius:6px; font-size:.8rem; }
	.assessment-name { flex:1; font-weight:600; }
	.assessment-score { font-family:var(--font-mono); font-weight:700; color:var(--accent); }
	.assessment-level { font-family:var(--font-mono); font-size:.65rem; color:var(--text-muted); text-transform:uppercase; }

	/* Responsive */
	@media(max-width:900px) { .stats-grid{grid-template-columns:repeat(2,1fr)} .view-header{flex-direction:column} .correlation-grid{grid-template-columns:1fr} .trend-metrics{display:none} }
	@media(max-width:600px) { .stats-grid{grid-template-columns:1fr} }
</style>
