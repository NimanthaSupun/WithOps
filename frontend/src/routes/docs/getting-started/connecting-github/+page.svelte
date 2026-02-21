<script>
	import { isDarkMode } from '$lib/stores.js';

	let darkMode = $state(false);
	isDarkMode.subscribe((v) => (darkMode = v));

	let openFaq = $state(-1);

	function toggleFaq(idx) {
		openFaq = openFaq === idx ? -1 : idx;
	}

	const methods = [
		{
			id: 'oauth',
			label: 'OAuth App',
			badge: 'QUICK SETUP',
			badgeColor: 'accent',
			description:
				'Authenticate with your personal GitHub account. Ideal for individual developers or quick evaluations.',
			pros: ['Fast setup (< 2 min)', 'No admin approval needed', 'Works with personal accounts'],
			cons: [
				'Limited to personal token scope',
				'Manual repository selection',
				'No webhook auto-configuration'
			]
		},
		{
			id: 'app',
			label: 'GitHub App',
			badge: 'RECOMMENDED',
			badgeColor: 'complement',
			description:
				'Install a dedicated GitHub App on your organization. Provides fine-grained permissions and automatic webhook management.',
			pros: [
				'Fine-grained permissions',
				'Automatic webhook setup',
				'Organization-wide coverage',
				'Audit trail for access'
			],
			cons: ['Requires org admin access', 'Initial setup takes ~5 min']
		}
	];

	const permissions = [
		{
			scope: 'Repository contents',
			access: 'Read',
			purpose: 'Code scanning and dependency analysis'
		},
		{ scope: 'Pull requests', access: 'Read & Write', purpose: 'Post scan results as PR comments' },
		{ scope: 'Issues', access: 'Write', purpose: 'Create issues for critical vulnerabilities' },
		{ scope: 'Webhooks', access: 'Read & Write', purpose: 'Receive push and PR events' },
		{ scope: 'Checks', access: 'Read & Write', purpose: 'Report scan status on commits' },
		{ scope: 'Metadata', access: 'Read', purpose: 'Repository and organization metadata' }
	];

	const oauthSteps = [
		{
			num: '01',
			title: 'Navigate to integrations',
			desc: 'Open your WithOps dashboard and go to Settings → Integrations → GitHub.'
		},
		{
			num: '02',
			title: 'Click "Connect with GitHub"',
			desc: "You'll be redirected to GitHub's OAuth authorization page."
		},
		{
			num: '03',
			title: 'Authorize WithOps',
			desc: 'Review the requested permissions and click "Authorize". Your account will be linked immediately.'
		},
		{
			num: '04',
			title: 'Select repositories',
			desc: 'Choose which repositories to monitor from the repository picker in your dashboard.'
		}
	];

	const appSteps = [
		{
			num: '01',
			title: 'Navigate to GitHub App setup',
			desc: 'Open your WithOps dashboard and go to Settings → Integrations → GitHub App.'
		},
		{
			num: '02',
			title: 'Click "Install GitHub App"',
			desc: "You'll be redirected to the GitHub App installation page on GitHub."
		},
		{
			num: '03',
			title: 'Choose organization',
			desc: 'Select the GitHub organization where you want to install the WithOps app.'
		},
		{
			num: '04',
			title: 'Configure repository access',
			desc: 'Choose "All repositories" for full coverage or select specific repositories to monitor.'
		},
		{
			num: '05',
			title: 'Confirm installation',
			desc: 'Review permissions and click "Install". Webhooks will be configured automatically.'
		}
	];

	const faqs = [
		{
			q: "I don't see my organization in the installation page",
			a: 'You need organization admin permissions to install GitHub Apps. Ask your org admin to install it, or request admin access in your GitHub organization settings.'
		},
		{
			q: 'Can I switch from OAuth to GitHub App later?',
			a: 'Yes. Go to Settings → Integrations, disconnect your OAuth connection, then follow the GitHub App installation flow. Your scan history will be preserved.'
		},
		{
			q: 'What happens if I revoke access?',
			a: 'WithOps will immediately lose access to your repositories. Existing scan data will be retained but no new scans will run until access is restored.'
		},
		{
			q: 'Do I need to re-authorize when adding new repos?',
			a: 'With GitHub App: No, if you selected "All repositories." Otherwise, update the installation settings on GitHub. With OAuth: you\'ll need to add new repos manually in the dashboard.'
		}
	];

	let activeMethod = $state('app');
	let activeSetupSteps = $derived(activeMethod === 'oauth' ? oauthSteps : appSteps);
</script>

<div class="github-page">
	<!-- Header -->
	<header class="page-header">
		<div class="page-badge">INTEGRATION GUIDE</div>
		<h1 class="page-title">Connecting GitHub</h1>
		<p class="page-desc">
			Link your GitHub repositories to enable continuous security scanning, automated vulnerability
			detection, and PR-level security feedback.
		</p>
	</header>

	<!-- Integration Methods -->
	<section class="methods-section" id="methods-section">
		<h2 id="integration-methods" class="section-heading">
			<span class="heading-marker">§</span>
			Integration Methods
		</h2>
		<p class="section-intro">Two approaches for connecting your GitHub repositories.</p>

		<div class="methods-grid">
			{#each methods as method}
				<button
					class="method-card"
					class:selected={activeMethod === method.id}
					onclick={() => (activeMethod = method.id)}
				>
					<div class="method-top">
						<span
							class="method-badge"
							class:accent={method.badgeColor === 'accent'}
							class:complement={method.badgeColor === 'complement'}
						>
							{method.badge}
						</span>
					</div>
					<h3 class="method-title">{method.label}</h3>
					<p class="method-desc">{method.description}</p>

					<div class="method-pros">
						{#each method.pros as pro}
							<div class="pro-item">
								<svg
									width="12"
									height="12"
									viewBox="0 0 24 24"
									fill="none"
									stroke="var(--success)"
									stroke-width="2.5"
								>
									<path d="M20 6L9 17l-5-5" />
								</svg>
								<span>{pro}</span>
							</div>
						{/each}
					</div>

					{#if method.cons.length > 0}
						<div class="method-cons">
							{#each method.cons as con}
								<div class="con-item">
									<svg
										width="10"
										height="10"
										viewBox="0 0 24 24"
										fill="none"
										stroke="var(--text-muted)"
										stroke-width="2"
									>
										<circle cx="12" cy="12" r="10" />
										<path d="M8 12h8" />
									</svg>
									<span>{con}</span>
								</div>
							{/each}
						</div>
					{/if}

					<div class="method-select-indicator">
						<span class="select-dot" class:active={activeMethod === method.id}></span>
						{activeMethod === method.id ? 'Selected' : 'Select'}
					</div>
				</button>
			{/each}
		</div>
	</section>

	<!-- Setup Steps -->
	<section class="setup-section" id="setup-section">
		<h2 id="setup-steps" class="section-heading">
			<span class="heading-marker">§</span>
			Setup — {activeMethod === 'oauth' ? 'OAuth' : 'GitHub App'}
		</h2>

		<div class="setup-steps">
			{#each activeSetupSteps as step, i}
				<div class="setup-step">
					<div class="setup-rail">
						<div class="setup-num">{step.num}</div>
						{#if i < activeSetupSteps.length - 1}
							<div class="setup-line"></div>
						{/if}
					</div>
					<div class="setup-body">
						<h3 class="setup-title">{step.title}</h3>
						<p class="setup-desc">{step.desc}</p>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Permissions -->
	<section class="perms-section" id="perms-section">
		<h2 id="permissions" class="section-heading">
			<span class="heading-marker">§</span>
			Required Permissions
		</h2>
		<p class="section-intro">Review what access WithOps requires and why.</p>

		<div class="perms-table">
			<div class="perms-header">
				<span class="perms-col-scope">Scope</span>
				<span class="perms-col-access">Access</span>
				<span class="perms-col-purpose">Purpose</span>
			</div>
			{#each permissions as perm}
				<div class="perms-row">
					<span class="perms-scope">
						<code>{perm.scope}</code>
					</span>
					<span class="perms-access">
						<span class="access-tag" class:write={perm.access.includes('Write')}>{perm.access}</span
						>
					</span>
					<span class="perms-purpose">{perm.purpose}</span>
				</div>
			{/each}
		</div>
	</section>

	<!-- Security Note -->
	<section class="security-note-section">
		<div class="security-note">
			<div class="note-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
				</svg>
			</div>
			<div class="note-body">
				<strong>Security Commitment</strong> — WithOps operates on a least-privilege model. We only request
				permissions essential for security scanning. Your source code is analyzed in-memory and never
				stored on our servers. All communication is encrypted via TLS 1.3.
			</div>
		</div>
	</section>

	<!-- FAQ -->
	<section class="faq-section" id="faq-section">
		<h2 id="troubleshooting" class="section-heading">
			<span class="heading-marker">§</span>
			Troubleshooting
		</h2>

		<div class="faq-list">
			{#each faqs as faq, i}
				<div class="faq-item" class:open={openFaq === i}>
					<button class="faq-question" onclick={() => toggleFaq(i)}>
						<span>{faq.q}</span>
						<span class="faq-chevron">
							<svg
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
							>
								<path d="M6 9l6 6 6-6" />
							</svg>
						</span>
					</button>
					{#if openFaq === i}
						<div class="faq-answer">
							<p>{faq.a}</p>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</section>
</div>

<style>
	.github-page {
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
		margin-bottom: 0.5rem;
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

	.section-intro {
		font-size: 0.875rem;
		color: var(--text-secondary);
		margin-bottom: 1.5rem;
		line-height: 1.6;
	}

	/* ── Method Cards ── */
	.methods-section {
		margin-bottom: 2.5rem;
	}

	.methods-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.875rem;
	}

	.method-card {
		text-align: left;
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-surface);
		cursor: pointer;
		transition: all 0.2s var(--ease-premium);
		display: flex;
		flex-direction: column;
		font-family: var(--font-sans);
		box-shadow: var(--card-shadow);
	}

	.method-card:hover {
		border-color: var(--border-strong);
	}

	.method-card.selected {
		border-color: var(--accent-border);
		background: var(--accent-soft);
	}

	.method-top {
		margin-bottom: 0.75rem;
	}

	.method-badge {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 700;
		letter-spacing: 0.1em;
		padding: 0.15rem 0.45rem;
		border-radius: 3px;
	}

	.method-badge.accent {
		color: var(--accent);
		background: var(--accent-soft);
	}

	.method-badge.complement {
		color: var(--complement);
		background: var(--complement-soft);
	}

	.method-title {
		font-size: 0.95rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.5rem;
	}

	.method-desc {
		font-size: 0.775rem;
		color: var(--text-secondary);
		line-height: 1.55;
		margin-bottom: 1rem;
	}

	.method-pros {
		margin-bottom: 0.625rem;
	}

	.pro-item,
	.con-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.725rem;
		color: var(--text-secondary);
		margin-bottom: 0.3rem;
	}

	.method-cons {
		margin-bottom: 0.75rem;
	}

	.method-select-indicator {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: auto;
		padding-top: 0.75rem;
		border-top: 1px solid var(--border);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.06em;
	}

	.select-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		border: 1.5px solid var(--border-strong);
		transition: all 0.15s;
	}

	.select-dot.active {
		border-color: var(--accent);
		background: var(--accent);
		box-shadow: 0 0 0 2px var(--accent-soft);
	}

	/* ── Setup Steps ── */
	.setup-section {
		margin-bottom: 2.5rem;
	}

	.setup-steps {
		display: flex;
		flex-direction: column;
	}

	.setup-step {
		display: flex;
		gap: 1.25rem;
	}

	.setup-rail {
		display: flex;
		flex-direction: column;
		align-items: center;
		flex-shrink: 0;
		width: 28px;
	}

	.setup-num {
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

	.setup-line {
		flex: 1;
		width: 1px;
		background: var(--border);
		min-height: 16px;
	}

	.setup-body {
		flex: 1;
		padding-bottom: 1.5rem;
	}

	.setup-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.3rem;
		line-height: 28px;
	}

	.setup-desc {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	/* ── Permissions Table ── */
	.perms-section {
		margin-bottom: 2.5rem;
	}

	.perms-table {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
	}

	.perms-header {
		display: grid;
		grid-template-columns: 1.2fr 0.8fr 1.5fr;
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

	.perms-row {
		display: grid;
		grid-template-columns: 1.2fr 0.8fr 1.5fr;
		padding: 0.65rem 1.25rem;
		border-bottom: 1px solid var(--border);
		font-size: 0.8rem;
		align-items: center;
		transition: background 0.1s;
	}

	.perms-row:last-child {
		border-bottom: none;
	}

	.perms-row:hover {
		background: var(--accent-soft);
	}

	.perms-scope code {
		font-family: var(--font-mono);
		font-size: 0.73rem;
		color: var(--text-primary);
		background: var(--bg-surface-alt);
		padding: 0.1rem 0.35rem;
		border-radius: 3px;
		border: 1px solid var(--border);
	}

	.access-tag {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		padding: 0.15rem 0.4rem;
		border-radius: 3px;
		color: var(--text-muted);
		background: var(--bg-surface-alt);
		letter-spacing: 0.04em;
	}

	.access-tag.write {
		color: var(--complement);
		background: var(--complement-soft);
	}

	.perms-purpose {
		color: var(--text-secondary);
		font-size: 0.775rem;
	}

	/* ── Security Note ── */
	.security-note-section {
		margin-bottom: 2.5rem;
	}

	.security-note {
		display: flex;
		gap: 0.875rem;
		padding: 1.125rem 1.25rem;
		border: 1px solid var(--accent-border);
		border-radius: var(--radius-sm);
		background: var(--accent-soft);
	}

	.note-icon {
		color: var(--accent);
		flex-shrink: 0;
		margin-top: 1px;
	}

	.note-body {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.6;
	}

	.note-body strong {
		color: var(--accent);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		letter-spacing: 0.02em;
	}

	/* ── FAQ ── */
	.faq-section {
		margin-bottom: 1rem;
	}

	.faq-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.faq-item {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
		transition: border-color 0.15s;
	}

	.faq-item.open {
		border-color: var(--border-strong);
	}

	.faq-question {
		width: 100%;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.875rem 1.25rem;
		background: var(--bg-surface);
		border: none;
		cursor: pointer;
		font-size: 0.825rem;
		font-weight: 600;
		font-family: var(--font-sans);
		color: var(--text-primary);
		text-align: left;
		gap: 0.75rem;
		transition: background 0.1s;
	}

	.faq-question:hover {
		background: var(--bg-surface-alt);
	}

	.faq-chevron {
		color: var(--text-muted);
		transition: transform 0.2s var(--ease-premium);
		flex-shrink: 0;
	}

	.faq-item.open .faq-chevron {
		transform: rotate(180deg);
	}

	.faq-answer {
		padding: 0 1.25rem 1rem;
		background: var(--bg-surface);
		border-top: 1px dashed var(--border);
	}

	.faq-answer p {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.6;
		padding-top: 0.875rem;
	}

	/* ── Responsive ── */
	@media (max-width: 640px) {
		.page-title {
			font-size: 1.35rem;
		}

		.methods-grid {
			grid-template-columns: 1fr;
		}

		.perms-header,
		.perms-row {
			grid-template-columns: 1fr 0.6fr;
			font-size: 0.7rem;
		}

		.perms-col-purpose,
		.perms-purpose {
			display: none;
		}
	}
</style>
