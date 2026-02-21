<script>
	import { isDarkMode } from '$lib/stores.js';

	let darkMode = $state(false);
	isDarkMode.subscribe((v) => (darkMode = v));

	let activeTab = $state('cloud');
	let copiedIdx = $state(-1);

	const cloudSteps = [
		{
			num: '01',
			title: 'Create your account',
			desc: 'Sign up at withops.dev using your organization email or GitHub account.',
			code: null
		},
		{
			num: '02',
			title: 'Install the GitHub App',
			desc: 'Navigate to Settings → Integrations and install the WithOps GitHub App on your target organizations.',
			code: null
		},
		{
			num: '03',
			title: 'Select repositories',
			desc: 'Choose which repositories to monitor. You can start with a single repository and expand later.',
			code: null
		},
		{
			num: '04',
			title: 'Trigger your first scan',
			desc: 'Push a commit or manually trigger a scan from the dashboard to see results.',
			code: null
		}
	];

	const selfHostedSteps = [
		{
			num: '01',
			title: 'Clone the repository',
			desc: 'Pull the WithOps platform source code to your local machine.',
			code: 'git clone https://github.com/withops/devsecops-platform.git\ncd devsecops-platform'
		},
		{
			num: '02',
			title: 'Configure environment',
			desc: 'Copy the example configuration and fill in your API keys and database credentials.',
			code: 'cp .env.example .env\n# Edit .env with your configuration\nnano .env'
		},
		{
			num: '03',
			title: 'Start services',
			desc: 'Launch all services using Docker Compose. This will start the backend, frontend, and all supporting services.',
			code: 'docker-compose up -d\n\n# Verify all services are running\ndocker-compose ps'
		},
		{
			num: '04',
			title: 'Access the platform',
			desc: 'Open your browser and navigate to the local instance. Default port is 3000.',
			code: '# Frontend:  http://localhost:3000\n# Backend:   http://localhost:9000\n# API Docs:  http://localhost:9000/docs'
		}
	];

	const features = [
		{ feature: 'Setup Time', cloud: '< 5 minutes', selfHosted: '15-30 minutes' },
		{ feature: 'Infrastructure', cloud: 'Managed', selfHosted: 'Self-managed' },
		{ feature: 'Data Residency', cloud: 'Cloud (US/EU)', selfHosted: 'Your infrastructure' },
		{ feature: 'Scaling', cloud: 'Automatic', selfHosted: 'Manual' },
		{ feature: 'Updates', cloud: 'Automatic', selfHosted: 'Manual pull' },
		{ feature: 'Cost', cloud: 'Subscription', selfHosted: 'Infrastructure only' }
	];

	let activeSteps = $derived(activeTab === 'cloud' ? cloudSteps : selfHostedSteps);

	function copyCode(code, idx) {
		if (!code) return;
		navigator.clipboard.writeText(code);
		copiedIdx = idx;
		setTimeout(() => (copiedIdx = -1), 2000);
	}
</script>

<div class="qs-page">
	<!-- Header -->
	<header class="page-header">
		<div class="page-badge">PROCEDURE</div>
		<h1 class="page-title">Quick Start</h1>
		<p class="page-desc">
			Get the WithOps platform running and connected to your repositories. Choose between
			cloud-hosted or self-hosted deployment.
		</p>
	</header>

	<!-- Deployment Toggle -->
	<section class="deploy-section" id="deploy-section">
		<h2 id="deployment" class="section-heading">
			<span class="heading-marker">§</span>
			Choose Deployment
		</h2>

		<div class="tab-switcher">
			<button
				class="tab-btn"
				class:active={activeTab === 'cloud'}
				onclick={() => (activeTab = 'cloud')}
			>
				<svg
					width="14"
					height="14"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
				</svg>
				Cloud Hosted
			</button>
			<button
				class="tab-btn"
				class:active={activeTab === 'self'}
				onclick={() => (activeTab = 'self')}
			>
				<svg
					width="14"
					height="14"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<rect x="2" y="2" width="20" height="8" rx="2" /><rect
						x="2"
						y="14"
						width="20"
						height="8"
						rx="2"
					/>
					<circle cx="6" cy="6" r="1" /><circle cx="6" cy="18" r="1" />
				</svg>
				Self-Hosted
			</button>
		</div>
	</section>

	<!-- Steps -->
	<section class="steps-section" id="steps-section">
		<h2 id="installation-steps" class="section-heading">
			<span class="heading-marker">§</span>
			Installation Steps
		</h2>

		<div class="steps-list">
			{#each activeSteps as step, i}
				<div class="step-item">
					<div class="step-rail">
						<div class="step-num">{step.num}</div>
						{#if i < activeSteps.length - 1}
							<div class="step-line"></div>
						{/if}
					</div>
					<div class="step-body">
						<h3 class="step-title">{step.title}</h3>
						<p class="step-desc">{step.desc}</p>
						{#if step.code}
							<div class="code-block">
								<div class="code-header">
									<span class="code-lang">terminal</span>
									<button class="code-copy" onclick={() => copyCode(step.code, i)}>
										{#if copiedIdx === i}
											<svg
												width="12"
												height="12"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
											>
												<path d="M20 6L9 17l-5-5" />
											</svg>
											Copied
										{:else}
											<svg
												width="12"
												height="12"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
											>
												<rect x="9" y="9" width="13" height="13" rx="2" /><path
													d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
												/>
											</svg>
											Copy
										{/if}
									</button>
								</div>
								<pre class="code-content">{step.code}</pre>
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Feature Comparison -->
	<section class="compare-section" id="compare-section">
		<h2 id="comparison" class="section-heading">
			<span class="heading-marker">§</span>
			Deployment Comparison
		</h2>

		<div class="compare-table">
			<div class="compare-header">
				<span class="compare-col-feature">Feature</span>
				<span class="compare-col">Cloud</span>
				<span class="compare-col">Self-Hosted</span>
			</div>
			{#each features as f}
				<div class="compare-row">
					<span class="compare-feature">{f.feature}</span>
					<span class="compare-value">{f.cloud}</span>
					<span class="compare-value">{f.selfHosted}</span>
				</div>
			{/each}
		</div>
	</section>

	<!-- Annotation Note -->
	<section class="note-section">
		<div class="field-note">
			<div class="note-marker">
				<svg
					width="14"
					height="14"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
				</svg>
			</div>
			<div class="note-content">
				<strong>Field Note</strong> — If you encounter port conflicts during local development, use
				<code>--port 3000</code>
				flag or modify the <code>.env</code> file to change default ports. See the troubleshooting section
				for common setup issues.
			</div>
		</div>
	</section>
</div>

<style>
	.qs-page {
		max-width: 720px;
	}

	/* ── Header ── */
	.page-header {
		margin-bottom: 2.5rem;
		padding-bottom: 1.75rem;
		border-bottom: 1px dashed var(--border);
	}

	.page-badge {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 700;
		color: var(--complement);
		letter-spacing: 0.12em;
		margin-bottom: 0.75rem;
	}

	.page-title {
		font-size: 1.75rem;
		font-weight: 800;
		letter-spacing: -0.03em;
		color: var(--text-primary);
		margin-bottom: 0.625rem;
	}

	.page-desc {
		font-size: 0.9rem;
		color: var(--text-secondary);
		line-height: 1.65;
		max-width: 540px;
	}

	/* ── Section Heading ── */
	.section-heading {
		font-size: 1.1rem;
		font-weight: 700;
		letter-spacing: -0.01em;
		margin-bottom: 1rem;
		color: var(--text-primary);
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.heading-marker {
		color: var(--complement);
		font-weight: 400;
		font-size: 1.05rem;
		opacity: 0.6;
	}

	/* ── Tab Switcher ── */
	.deploy-section {
		margin-bottom: 2.5rem;
	}

	.tab-switcher {
		display: flex;
		gap: 0.5rem;
		padding: 0.25rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		width: fit-content;
	}

	.tab-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		font-size: 0.8rem;
		font-weight: 600;
		font-family: var(--font-sans);
		color: var(--text-secondary);
		background: transparent;
		border: 1px solid transparent;
		border-radius: 3px;
		cursor: pointer;
		transition: all 0.15s var(--ease-premium);
	}

	.tab-btn:hover {
		color: var(--text-primary);
	}

	.tab-btn.active {
		color: var(--accent);
		background: var(--accent-soft);
		border-color: var(--accent-border);
	}

	/* ── Steps ── */
	.steps-section {
		margin-bottom: 2.5rem;
	}

	.steps-list {
		display: flex;
		flex-direction: column;
	}

	.step-item {
		display: flex;
		gap: 1.25rem;
	}

	.step-rail {
		display: flex;
		flex-direction: column;
		align-items: center;
		flex-shrink: 0;
		width: 28px;
	}

	.step-num {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 700;
		color: var(--accent);
		border: 1.5px solid var(--accent-border);
		border-radius: 50%;
		background: var(--accent-soft);
		flex-shrink: 0;
	}

	.step-line {
		flex: 1;
		width: 1px;
		background: var(--border);
		min-height: 20px;
	}

	.step-body {
		flex: 1;
		padding-bottom: 1.75rem;
		min-width: 0;
	}

	.step-title {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.375rem;
		line-height: 28px;
	}

	.step-desc {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.55;
		margin-bottom: 0.75rem;
	}

	/* ── Code Block ── */
	.code-block {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
		background: var(--bg-surface);
	}

	.code-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.4rem 0.75rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface-alt);
	}

	.code-lang {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}

	.code-copy {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.2rem 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text-muted);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: 3px;
		cursor: pointer;
		transition: all 0.15s;
	}

	.code-copy:hover {
		color: var(--text-secondary);
		border-color: var(--border-strong);
	}

	.code-content {
		padding: 0.875rem 1rem;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		line-height: 1.65;
		color: var(--text-primary);
		overflow-x: auto;
		margin: 0;
		white-space: pre;
	}

	/* ── Comparison Table ── */
	.compare-section {
		margin-bottom: 2.5rem;
	}

	.compare-table {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
	}

	.compare-header {
		display: grid;
		grid-template-columns: 1.5fr 1fr 1fr;
		padding: 0.625rem 1.25rem;
		background: var(--bg-surface-alt);
		border-bottom: 1px solid var(--border);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	.compare-row {
		display: grid;
		grid-template-columns: 1.5fr 1fr 1fr;
		padding: 0.65rem 1.25rem;
		border-bottom: 1px solid var(--border);
		font-size: 0.8rem;
		transition: background 0.1s;
	}

	.compare-row:last-child {
		border-bottom: none;
	}

	.compare-row:hover {
		background: var(--accent-soft);
	}

	.compare-feature {
		color: var(--text-primary);
		font-weight: 500;
	}

	.compare-value {
		color: var(--text-secondary);
	}

	/* ── Field Note ── */
	.note-section {
		margin-bottom: 1rem;
	}

	.field-note {
		display: flex;
		gap: 0.875rem;
		padding: 1rem 1.25rem;
		border: 1px dashed var(--complement-border);
		border-radius: var(--radius-sm);
		background: var(--complement-soft);
	}

	.note-marker {
		color: var(--complement);
		flex-shrink: 0;
		margin-top: 2px;
	}

	.note-content {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.6;
	}

	.note-content strong {
		color: var(--complement);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		letter-spacing: 0.02em;
	}

	.note-content code {
		font-family: var(--font-mono);
		font-size: 0.73rem;
		padding: 0.1rem 0.35rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--accent);
	}

	/* ── Responsive ── */
	@media (max-width: 640px) {
		.page-title {
			font-size: 1.35rem;
		}

		.tab-switcher {
			width: 100%;
		}

		.tab-btn {
			flex: 1;
			justify-content: center;
		}

		.compare-header,
		.compare-row {
			grid-template-columns: 1fr 1fr 1fr;
			font-size: 0.7rem;
			padding: 0.5rem 0.75rem;
		}
	}
</style>
