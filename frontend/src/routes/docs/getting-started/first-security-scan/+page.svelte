<script>
	import { onMount } from 'svelte';

	let visible = $state(false);

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});
</script>

<div class="gs-page {visible ? 'visible' : ''}">
	<!-- Page Header -->
	<div class="page-header">
		<div class="breadcrumb">
			<span class="bc-muted">Docs</span>
			<span class="bc-sep">/</span>
			<a href="/docs/getting-started" class="bc-link">Getting Started</a>
			<span class="bc-sep">/</span>
			<span class="bc-current">First Security Scan</span>
		</div>
		<h1 class="page-title" id="first-security-scan">First Security Scan</h1>
		<p class="page-lead">
			Run your first AI-powered security analysis and learn how to interpret the results to improve
			your security posture.
		</p>
	</div>

	<!-- Overview -->
	<h2 id="what-gets-scanned">What Gets Scanned</h2>
	<p class="body-text">
		When you initiate a security scan, WithOps analyzes your repository across multiple dimensions
		simultaneously:
	</p>

	<div class="scan-dimensions">
		<div class="scan-dim">
			<div class="dim-indicator purple"></div>
			<div class="dim-content">
				<h4>Static Analysis (SAST)</h4>
				<p>
					Source code scanning for vulnerabilities, insecure patterns, and code quality issues using
					AST parsing
				</p>
			</div>
		</div>
		<div class="scan-dim">
			<div class="dim-indicator blue"></div>
			<div class="dim-content">
				<h4>Dependency Audit</h4>
				<p>
					Third-party package vulnerability detection with CVE database matching and exploitability
					scoring
				</p>
			</div>
		</div>
		<div class="scan-dim">
			<div class="dim-indicator amber"></div>
			<div class="dim-content">
				<h4>Secret Detection</h4>
				<p>
					Scans for leaked API keys, tokens, credentials, and sensitive data using Gitleaks and
					TruffleHog
				</p>
			</div>
		</div>
		<div class="scan-dim">
			<div class="dim-indicator green"></div>
			<div class="dim-content">
				<h4>CI/CD Workflow Analysis</h4>
				<p>
					GitHub Actions YAML validation, security tool coverage assessment, and pipeline
					optimization
				</p>
			</div>
		</div>
		<div class="scan-dim">
			<div class="dim-indicator red"></div>
			<div class="dim-content">
				<h4>AI Threat Assessment</h4>
				<p>
					AI-powered risk evaluation using STRIDE methodology with automated remediation suggestions
				</p>
			</div>
		</div>
	</div>

	<!-- Running the scan -->
	<h2 id="run-your-scan">Running Your First Scan</h2>

	<div class="instruction-block">
		<div class="instruction-number">1</div>
		<div class="instruction-content">
			<p>
				Navigate to <strong>Organizations</strong> and select a repository from your connected organizations.
			</p>
		</div>
	</div>

	<div class="instruction-block">
		<div class="instruction-number">2</div>
		<div class="instruction-content">
			<p>
				Click <strong>"Run Security Analysis"</strong> on the repository detail page. The scan begins
				immediately.
			</p>
			<div class="callout callout-info">
				<div class="callout-icon">
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						><circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line
							x1="12"
							y1="8"
							x2="12.01"
							y2="8"
						/></svg
					>
				</div>
				<div class="callout-content">
					<strong>Scan duration</strong>
					<p>
						Initial scans typically complete in 30-90 seconds depending on repository size.
						Subsequent scans are faster due to caching.
					</p>
				</div>
			</div>
		</div>
	</div>

	<div class="instruction-block">
		<div class="instruction-number">3</div>
		<div class="instruction-content">
			<p>
				Monitor progress in real-time. WithOps uses <strong>WebSocket</strong> connections to stream
				scan status updates live to your browser.
			</p>
			<div class="progress-demo">
				<div class="progress-stage completed">
					<div class="stage-dot"></div>
					<span>Repository cloned</span>
				</div>
				<div class="progress-stage completed">
					<div class="stage-dot"></div>
					<span>Dependencies analyzed</span>
				</div>
				<div class="progress-stage completed">
					<div class="stage-dot"></div>
					<span>Static analysis complete</span>
				</div>
				<div class="progress-stage active">
					<div class="stage-dot"></div>
					<span>AI threat assessment</span>
				</div>
				<div class="progress-stage pending">
					<div class="stage-dot"></div>
					<span>Report generation</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Reading Results -->
	<h2 id="reading-results">Understanding Your Results</h2>
	<p class="body-text">
		The scan report is organized into severity-ranked findings with actionable remediation guidance.
	</p>

	<!-- Severity Levels -->
	<h3 id="severity-levels">Severity Levels</h3>
	<div class="severity-table">
		<div class="sev-row critical">
			<div class="sev-badge">Critical</div>
			<div class="sev-score">9.0 – 10.0</div>
			<div class="sev-desc">Actively exploitable vulnerabilities requiring immediate attention</div>
		</div>
		<div class="sev-row high">
			<div class="sev-badge">High</div>
			<div class="sev-score">7.0 – 8.9</div>
			<div class="sev-desc">Significant risk — should be resolved within the current sprint</div>
		</div>
		<div class="sev-row medium">
			<div class="sev-badge">Medium</div>
			<div class="sev-score">4.0 – 6.9</div>
			<div class="sev-desc">Moderate risk with conditional exploitability</div>
		</div>
		<div class="sev-row low">
			<div class="sev-badge">Low</div>
			<div class="sev-score">0.1 – 3.9</div>
			<div class="sev-desc">Informational findings and best-practice suggestions</div>
		</div>
	</div>

	<!-- Example Finding -->
	<h3 id="example-finding">Example Finding</h3>
	<p class="body-text">Here's what a typical finding looks like in the scan results:</p>

	<div class="finding-example">
		<div class="finding-header">
			<div class="finding-severity high">HIGH</div>
			<div class="finding-title">Hardcoded API Key in Configuration</div>
		</div>
		<div class="finding-body">
			<div class="finding-meta">
				<div class="meta-item">
					<span class="meta-label">File</span>
					<code>src/config/api.js:42</code>
				</div>
				<div class="meta-item">
					<span class="meta-label">Rule</span>
					<code>SEC-001</code>
				</div>
				<div class="meta-item">
					<span class="meta-label">CVSS</span>
					<span class="cvss-score">7.5</span>
				</div>
			</div>
			<div class="finding-code">
				<div class="code-header">
					<span class="code-lang">JavaScript</span>
				</div>
				<pre><code
						><span class="code-line-num">41</span>  const config = {'{'}
<span class="code-line-num">42</span>    <span class="code-highlight"
							>apiKey: "sk-live-a1b2c3d4e5f6..."</span
						>  <span class="code-comment">// ← Detected</span>
<span class="code-line-num">43</span>  {'}'}</code
					></pre>
			</div>
			<div class="finding-remediation">
				<div class="remediation-label">
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline
							points="14 2 14 8 20 8"
						/></svg
					>
					AI-Generated Fix
				</div>
				<p>
					Move the API key to an environment variable and reference it via <code
						>process.env.API_KEY</code
					>. Add <code>.env</code> to your <code>.gitignore</code>.
				</p>
			</div>
		</div>
	</div>

	<!-- DevSecOps Maturity -->
	<h2 id="maturity-score">DevSecOps Maturity Score</h2>
	<p class="body-text">
		Beyond individual findings, WithOps generates a comprehensive maturity score for your repository
		based on:
	</p>

	<div class="maturity-factors">
		<div class="maturity-item">
			<div class="maturity-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg
				>
			</div>
			<div>
				<strong>Security Tool Coverage</strong>
				<p>Which security tools are integrated in your CI/CD pipeline</p>
			</div>
		</div>
		<div class="maturity-item">
			<div class="maturity-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg
				>
			</div>
			<div>
				<strong>Vulnerability Trend</strong>
				<p>How findings are trending over time — improving or degrading</p>
			</div>
		</div>
		<div class="maturity-item">
			<div class="maturity-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" /></svg
				>
			</div>
			<div>
				<strong>Best Practices Adoption</strong>
				<p>Branch protection, code review policies, and dependency management</p>
			</div>
		</div>
		<div class="maturity-item">
			<div class="maturity-icon">
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg
				>
			</div>
			<div>
				<strong>Remediation Velocity</strong>
				<p>How quickly your team addresses identified vulnerabilities</p>
			</div>
		</div>
	</div>

	<!-- Congratulations -->
	<div class="completion-card">
		<div class="completion-icon">
			<svg
				width="28"
				height="28"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
			>
				<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
			</svg>
		</div>
		<div class="completion-text">
			<h3>Getting Started Complete</h3>
			<p>
				You've connected your GitHub account, discovered your organizations, and run your first
				security scan. You're now equipped to continuously monitor and improve your security posture
				with WithOps.
			</p>
		</div>
	</div>

	<!-- What's Next -->
	<h2 id="continue-learning">Continue Learning</h2>
	<p class="body-text">Explore more of the platform's capabilities:</p>

	<div class="continue-grid">
		<div class="continue-card disabled">
			<span class="continue-badge">Coming Soon</span>
			<h4>Threat Modeling</h4>
			<p>Deep-dive into STRIDE analysis and attack surface mapping</p>
		</div>
		<div class="continue-card disabled">
			<span class="continue-badge">Coming Soon</span>
			<h4>API Reference</h4>
			<p>Full REST API documentation for all 8 microservices</p>
		</div>
		<div class="continue-card disabled">
			<span class="continue-badge">Coming Soon</span>
			<h4>Self-Hosting Guide</h4>
			<p>Deploy WithOps on your infrastructure with Docker or Kubernetes</p>
		</div>
	</div>
</div>

<style>
	.gs-page {
		opacity: 0;
		transform: translateY(8px);
		transition: all 0.4s cubic-bezier(0.2, 0, 0, 1);
	}
	.gs-page.visible {
		opacity: 1;
		transform: translateY(0);
	}

	.page-header {
		margin-bottom: 2.5rem;
		padding-bottom: 2rem;
		border-bottom: 1px solid var(--border);
	}

	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		margin-bottom: 1rem;
		font-size: 0.75rem;
		font-family: var(--font-mono);
	}

	.bc-muted {
		color: var(--text-muted);
	}
	.bc-sep {
		color: var(--text-muted);
	}
	.bc-current {
		color: var(--text-secondary);
	}
	.bc-link {
		color: var(--text-muted);
		text-decoration: none;
	}
	.bc-link:hover {
		color: var(--accent);
	}

	.page-title {
		font-family: var(--font-serif);
		font-size: 2.25rem;
		font-weight: 700;
		letter-spacing: -0.03em;
		line-height: 1.2;
		margin-bottom: 0.75rem;
		color: var(--text-primary);
	}

	.page-lead {
		font-size: 1.05rem;
		color: var(--text-secondary);
		line-height: 1.7;
		max-width: 640px;
		font-family: var(--font-serif);
	}

	h2 {
		font-family: var(--font-serif);
		font-size: 1.375rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		margin-top: 3rem;
		margin-bottom: 0.75rem;
		color: var(--text-primary);
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--border);
	}

	h3 {
		font-family: var(--font-serif);
		font-size: 1.1rem;
		font-weight: 600;
		margin-top: 2rem;
		margin-bottom: 0.5rem;
		color: var(--text-primary);
	}

	.body-text {
		font-size: 0.9rem;
		line-height: 1.75;
		color: var(--text-secondary);
		margin-bottom: 1.25rem;
		max-width: 640px;
	}

	/* ── Scan Dimensions ── */
	.scan-dimensions {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.scan-dim {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-surface);
		transition: border-color 0.15s;
	}

	.scan-dim:hover {
		border-color: var(--border-strong);
	}

	.dim-indicator {
		width: 4px;
		height: 100%;
		min-height: 36px;
		border-radius: 2px;
		flex-shrink: 0;
	}

	.dim-indicator.purple {
		background: #a78bfa;
	}
	.dim-indicator.blue {
		background: #60a5fa;
	}
	.dim-indicator.amber {
		background: #fbbf24;
	}
	.dim-indicator.green {
		background: #34d399;
	}
	.dim-indicator.red {
		background: #f87171;
	}

	.dim-content h4 {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.25rem;
	}

	.dim-content p {
		font-size: 0.775rem;
		color: var(--text-muted);
		line-height: 1.5;
	}

	/* ── Instruction Blocks ── */
	.instruction-block {
		display: flex;
		gap: 1rem;
		padding: 1.25rem 0;
		border-bottom: 1px solid var(--border);
	}

	.instruction-block:last-of-type {
		border-bottom: none;
	}

	.instruction-number {
		flex-shrink: 0;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--accent-soft);
		border: 1px solid var(--accent-border);
		color: var(--accent);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.instruction-content {
		flex: 1;
		min-width: 0;
	}

	.instruction-content > p {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.6;
		margin-bottom: 0.75rem;
	}

	.instruction-content > p strong {
		color: var(--text-primary);
		font-weight: 600;
	}

	/* ── Progress Demo ── */
	.progress-demo {
		display: flex;
		flex-direction: column;
		gap: 0;
		padding: 1rem 1.25rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-surface);
	}

	.progress-stage {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 0;
		font-size: 0.8rem;
		position: relative;
	}

	.progress-stage:not(:last-child)::before {
		content: '';
		position: absolute;
		left: 5px;
		top: 24px;
		bottom: -4px;
		width: 1px;
		background: var(--border);
	}

	.stage-dot {
		width: 11px;
		height: 11px;
		border-radius: 50%;
		flex-shrink: 0;
		border: 2px solid;
	}

	.progress-stage.completed .stage-dot {
		background: var(--callout-tip-text);
		border-color: var(--callout-tip-text);
	}

	.progress-stage.completed span {
		color: var(--text-secondary);
	}
	.progress-stage.completed:not(:last-child)::before {
		background: var(--callout-tip-text);
	}

	.progress-stage.active .stage-dot {
		background: var(--accent);
		border-color: var(--accent);
		animation: pulse-dot 1.5s ease-in-out infinite;
	}

	.progress-stage.active span {
		color: var(--accent);
		font-weight: 500;
	}

	.progress-stage.pending .stage-dot {
		background: transparent;
		border-color: var(--text-muted);
	}

	.progress-stage.pending span {
		color: var(--text-muted);
	}

	@keyframes pulse-dot {
		0%,
		100% {
			box-shadow: 0 0 0 0 rgba(167, 139, 250, 0.3);
		}
		50% {
			box-shadow: 0 0 0 4px rgba(167, 139, 250, 0);
		}
	}

	/* ── Callouts ── */
	.callout {
		display: flex;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		border-radius: 8px;
		margin: 1rem 0;
		border: 1px solid;
	}

	.callout-info {
		background: var(--callout-info-bg);
		border-color: var(--callout-info-border);
	}
	.callout-info .callout-icon {
		color: var(--callout-info-text);
	}

	.callout-icon {
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.callout-content strong {
		display: block;
		font-size: 0.825rem;
		color: var(--text-primary);
		margin-bottom: 0.25rem;
	}

	.callout-content p {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	/* ── Severity Table ── */
	.severity-table {
		border: 1px solid var(--border);
		border-radius: 10px;
		overflow: hidden;
		margin: 1rem 0;
	}

	.sev-row {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.75rem 1.25rem;
		border-bottom: 1px solid var(--border);
	}

	.sev-row:last-child {
		border-bottom: none;
	}

	.sev-badge {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 0.2rem 0.625rem;
		border-radius: 4px;
		min-width: 62px;
		text-align: center;
	}

	.sev-row.critical .sev-badge {
		background: rgba(239, 68, 68, 0.1);
		color: #f87171;
		border: 1px solid rgba(239, 68, 68, 0.2);
	}
	.sev-row.high .sev-badge {
		background: rgba(251, 146, 60, 0.1);
		color: #fb923c;
		border: 1px solid rgba(251, 146, 60, 0.2);
	}
	.sev-row.medium .sev-badge {
		background: rgba(250, 204, 21, 0.1);
		color: #facc15;
		border: 1px solid rgba(250, 204, 21, 0.2);
	}
	.sev-row.low .sev-badge {
		background: rgba(96, 165, 250, 0.1);
		color: #60a5fa;
		border: 1px solid rgba(96, 165, 250, 0.2);
	}

	.sev-score {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text-muted);
		min-width: 70px;
	}

	.sev-desc {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.4;
	}

	/* ── Finding Example ── */
	.finding-example {
		border: 1px solid var(--border);
		border-radius: 10px;
		overflow: hidden;
		background: var(--bg-surface);
		margin: 1rem 0;
	}

	.finding-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem 1.25rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface-2);
	}

	.finding-severity {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: 0.2rem 0.5rem;
		border-radius: 3px;
	}

	.finding-severity.high {
		background: rgba(251, 146, 60, 0.12);
		color: #fb923c;
		border: 1px solid rgba(251, 146, 60, 0.2);
	}

	.finding-title {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.finding-body {
		padding: 1.25rem;
	}

	.finding-meta {
		display: flex;
		gap: 1.5rem;
		margin-bottom: 1rem;
		flex-wrap: wrap;
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.775rem;
	}

	.meta-label {
		color: var(--text-muted);
		font-weight: 500;
	}

	.meta-item code {
		font-family: var(--font-mono);
		font-size: 0.725rem;
		color: var(--accent);
		background: var(--accent-soft);
		padding: 0.1rem 0.375rem;
		border-radius: 3px;
	}

	.cvss-score {
		font-family: var(--font-mono);
		font-weight: 700;
		color: #fb923c;
	}

	.finding-code {
		border: 1px solid var(--code-border);
		border-radius: 6px;
		overflow: hidden;
		margin-bottom: 1rem;
	}

	.code-header {
		display: flex;
		justify-content: space-between;
		padding: 0.4rem 0.75rem;
		border-bottom: 1px solid var(--code-border);
		background: var(--bg-surface-2);
	}

	.code-lang {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	pre {
		padding: 0.75rem;
		margin: 0;
		overflow-x: auto;
	}

	code {
		font-family: var(--font-mono);
		font-size: 0.775rem;
		line-height: 1.7;
		color: var(--text-primary);
	}

	.code-line-num {
		color: var(--text-muted);
		margin-right: 1rem;
		user-select: none;
	}

	.code-highlight {
		background: rgba(251, 146, 60, 0.1);
		padding: 0.1rem 0.25rem;
		border-radius: 2px;
		color: #fb923c;
	}

	.code-comment {
		color: var(--text-muted);
		font-style: italic;
	}

	.finding-remediation {
		padding: 0.875rem 1rem;
		background: var(--callout-tip-bg);
		border: 1px solid var(--callout-tip-border);
		border-radius: 6px;
	}

	.remediation-label {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.725rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--callout-tip-text);
		margin-bottom: 0.375rem;
	}

	.finding-remediation p {
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	.finding-remediation code {
		font-size: 0.75rem;
		background: var(--accent-soft);
		color: var(--accent);
		padding: 0.1rem 0.375rem;
		border-radius: 3px;
	}

	/* ── Maturity Factors ── */
	.maturity-factors {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.maturity-item {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.875rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-surface);
	}

	.maturity-icon {
		flex-shrink: 0;
		width: 30px;
		height: 30px;
		border-radius: 6px;
		background: var(--accent-soft);
		border: 1px solid var(--accent-border);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--accent);
	}

	.maturity-item strong {
		display: block;
		font-size: 0.825rem;
		color: var(--text-primary);
		margin-bottom: 0.125rem;
	}

	.maturity-item p {
		font-size: 0.775rem;
		color: var(--text-muted);
		line-height: 1.4;
	}

	/* ── Completion Card ── */
	.completion-card {
		display: flex;
		gap: 1.25rem;
		padding: 1.75rem 2rem;
		border: 1px solid var(--callout-tip-border);
		border-radius: 12px;
		background: var(--callout-tip-bg);
		margin: 2.5rem 0;
		align-items: flex-start;
	}

	.completion-icon {
		flex-shrink: 0;
		width: 48px;
		height: 48px;
		border-radius: 50%;
		background: rgba(16, 185, 129, 0.1);
		border: 1px solid rgba(16, 185, 129, 0.2);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--callout-tip-text);
	}

	.completion-text h3 {
		font-family: var(--font-serif);
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.375rem;
	}

	.completion-text p {
		font-size: 0.85rem;
		color: var(--text-secondary);
		line-height: 1.65;
	}

	/* ── Continue Grid ── */
	.continue-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.75rem;
	}

	.continue-card {
		padding: 1.25rem;
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--bg-surface);
		transition: border-color 0.15s;
	}

	.continue-card.disabled {
		opacity: 0.5;
	}

	.continue-badge {
		display: inline-block;
		font-family: var(--font-mono);
		font-size: 0.55rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text-muted);
		background: var(--bg-surface-3);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 0.1rem 0.4rem;
		margin-bottom: 0.75rem;
	}

	.continue-card h4 {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 0.25rem;
	}

	.continue-card p {
		font-size: 0.775rem;
		color: var(--text-muted);
		line-height: 1.5;
	}

	@media (max-width: 768px) {
		.page-title {
			font-size: 1.75rem;
		}
		.sev-row {
			flex-wrap: wrap;
		}
		.finding-meta {
			flex-direction: column;
			gap: 0.5rem;
		}
		.continue-grid {
			grid-template-columns: 1fr;
		}
		.completion-card {
			flex-direction: column;
		}
	}
</style>
