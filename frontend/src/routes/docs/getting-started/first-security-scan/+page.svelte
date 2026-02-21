<script>
	import { onMount } from 'svelte';

	let visible = $state(false);
	let copiedStates = $state({});

	onMount(() => {
		setTimeout(() => (visible = true), 50);
	});

	function copyCode(id, text) {
		navigator.clipboard.writeText(text).then(() => {
			copiedStates[id] = true;
			setTimeout(() => {
				copiedStates[id] = false;
			}, 1800);
		});
	}
</script>

<svelte:head>
	<title>First Security Scan — WithOps Documentation</title>
	<meta name="description" content="Run your first comprehensive security scan with WithOps — covering SAST, dependency audit, secret detection, STRIDE/CIA/LINDDUN threat modeling, and CI/CD pipeline analysis." />
</svelte:head>

<div class="getting-started {visible ? 'visible' : ''}">
	<div class="breadcrumb">
		<a href="/docs/getting-started" class="bc-link">Getting Started</a>
		<span class="bc-sep">/</span>
		<span class="bc-current">First Security Scan</span>
	</div>

	<div class="chapter-tag">
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
		</svg>
		Chapter IV
	</div>

	<h1 class="page-title" id="first-security-scan">First Security Scan</h1>
	<p class="page-subtitle">
		Run a comprehensive scan covering SAST, dependency audit, secret detection, and CI/CD analysis, unified by OWASP DSOMM intelligence.
	</p>

	<hr class="divider" />

	<div class="meta-row">
		<span class="meta-reading">
			<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
			</svg>
			7 min read
		</span>
		<span class="meta-tag">Security</span>
		<span class="meta-tag">SAST</span>
		<span class="meta-tag">AI</span>
	</div>

	<!-- Launching a scan -->
	<h2 class="section-heading" id="launching-a-scan">Launching a Scan</h2>
	<div class="prose">
		<p>
			Once your GitHub account is connected and repositories are visible in the dashboard, you're ready to run your first security analysis. WithOps performs multiple scan types in parallel, delivering a comprehensive report in 30–90 seconds.
		</p>
	</div>

	<div class="steps">
		<div class="step-card">
			<div class="step-num">1</div>
			<div class="step-body">
				<h4>Open an Organization Workspace</h4>
				<p>Navigate to <strong>Dashboard → Organizations</strong> and select the organization you want to scan. This opens the organization's Workspace view.</p>
			</div>
		</div>

		<div class="step-card">
			<div class="step-num">2</div>
			<div class="step-body">
				<h4>Select a repository</h4>
				<p>Within the Workspace, choose a repository. Click <strong>"Run Scan"</strong> and select the scan types you want to include — or leave all enabled for a full analysis.</p>
			</div>
		</div>

		<div class="step-card">
			<div class="step-num">3</div>
			<div class="step-body">
				<h4>Start the analysis</h4>
				<p>Click <strong>"Start Scan"</strong>. You'll see a real-time progress indicator as each scan module runs in parallel across the AI pipeline.</p>
			</div>
		</div>

		<div class="step-card">
			<div class="step-num">4</div>
			<div class="step-body">
				<h4>Intelligence & Maturity</h4>
				<p>Navigate to the <strong>Intelligence</strong> tab to view your <strong>OWASP DSOMM</strong> maturity score (Levels 0-4) and organization-wide security posture.</p>
			</div>
		</div>
	</div>

	<!-- Scan Types -->
	<h2 class="section-heading" id="scan-types">Scan Types Explained</h2>
	<p class="prose-text">
		WithOps runs five distinct security analysis modules. Each module is AI-powered and produces actionable findings with severity ratings.
	</p>

	<div class="scan-grid">
		<div class="scan-card">
			<div class="scan-header">
				<div class="scan-icon blue">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
						<polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
					</svg>
				</div>
				<div>
					<h4>SAST — Static Analysis</h4>
					<span class="scan-badge">AI-Powered</span>
				</div>
			</div>
			<p>Analyses source code for vulnerabilities without executing it. Detects SQL injection, XSS, buffer overflows, insecure cryptography, hardcoded credentials, and more.</p>
			<div class="scan-details">
				<span><strong>Engine:</strong> Advanced LLMs (GPT-4, Claude 3, Llama 3) + pattern matching</span>
				<span><strong>Languages:</strong> Python, JavaScript, TypeScript, Rust, Go, Java, C/C++</span>
				<span><strong>Speed:</strong> ~10 seconds per 10K LOC</span>
			</div>
		</div>

		<div class="scan-card">
			<div class="scan-header">
				<div class="scan-icon amber">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
						<path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
						<polyline points="3.27 6.96 12 12.01 20.73 6.96" />
						<line x1="12" y1="22.08" x2="12" y2="12" />
					</svg>
				</div>
				<div>
					<h4>Dependency Audit</h4>
					<span class="scan-badge">CVE Database</span>
				</div>
			</div>
			<p>Scans <code>package.json</code>, <code>requirements.txt</code>, <code>Cargo.toml</code>, and other dependency manifests against known vulnerability databases (NVD, OSV, GitHub Advisory).</p>
			<div class="scan-details">
				<span><strong>Databases:</strong> NVD, OSV, GitHub Advisory DB</span>
				<span><strong>Formats:</strong> npm, pip, cargo, go.mod, Maven, Gradle</span>
				<span><strong>Scoring:</strong> CVSS v3.1</span>
			</div>
		</div>

		<div class="scan-card">
			<div class="scan-header">
				<div class="scan-icon red">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
						<rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0110 0v4" />
					</svg>
				</div>
				<div>
					<h4>Secret Detection</h4>
					<span class="scan-badge">Entropy + AI</span>
				</div>
			</div>
			<p>Detects leaked API keys, tokens, passwords, private keys, and connection strings using entropy analysis and pattern-based detection augmented by AI classification.</p>
			<div class="scan-details">
				<span><strong>Patterns:</strong> 150+ provider-specific patterns</span>
				<span><strong>Coverage:</strong> Code, configs, CI/CD, Dockerfiles</span>
				<span><strong>False positive rate:</strong> &lt;2% with AI filtering</span>
			</div>
		</div>

		<div class="scan-card">
			<div class="scan-header">
				<div class="scan-icon green">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
						<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
						<line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
					</svg>
				</div>
				<div>
					<h4>Multi-Framework Threat Model</h4>
					<span class="scan-badge">AI Analysis</span>
				</div>
			</div>
			<p>Applies multiple security frameworks — STRIDE, CIA, LINDDUN, and OWASP — to analyze your architecture for spoofing, privacy risks, and common web vulnerabilities.</p>
			<div class="scan-details">
				<span><strong>Frameworks:</strong> STRIDE, CIA, LINDDUN, OWASP</span>
				<span><strong>Engine:</strong> GPT-4 / Claude 3 / Llama 3 (Groq)</span>
				<span><strong>Output:</strong> Threat matrix, attack surface map</span>
			</div>
		</div>

		<div class="scan-card full-width">
			<div class="scan-header">
				<div class="scan-icon purple">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
						<path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2v-4M9 21H5a2 2 0 01-2-2v-4m0-4h18" />
					</svg>
				</div>
				<div>
					<h4>CI/CD Pipeline Analysis</h4>
					<span class="scan-badge">Workflow Scan</span>
				</div>
			</div>
			<p>Validates GitHub Actions workflows, Docker configurations, and CI/CD pipelines for security misconfigurations, overly permissive permissions, and missing security steps.</p>
			<div class="scan-details">
				<span><strong>Files:</strong> .github/workflows/*.yml, Dockerfile, docker-compose.yml</span>
				<span><strong>Checks:</strong> Permissions, pinning, secrets usage, image scanning</span>
			</div>
		</div>
	</div>

	<!-- Workspace Intelligence -->
	<h2 class="section-heading" id="workspace-intelligence">Workspace Intelligence</h2>
	<div class="prose">
		<p>
			Beyond individual scans, WithOps provides <strong>Workspace Intelligence</strong> — a high-level view of your entire organization's security maturity based on the <strong>OWASP DSOMM</strong> (DevSecOps Maturity Model) framework.
		</p>
	</div>

	<div class="intel-box">
		<div class="intel-stat">
			<span class="intel-val">DSOMM</span>
			<span class="intel-label">Framework</span>
		</div>
		<div class="intel-stat">
			<span class="intel-val">L0 — L4</span>
			<span class="intel-label">Maturity Scale</span>
		</div>
		<div class="intel-stat">
			<span class="intel-val">5</span>
			<span class="intel-label">Dimensions</span>
		</div>
	</div>

	<div class="prose">
		<p>The Intelligence module assesses five core dimensions of your DevSecOps practice:</p>
		<ul>
			<li><strong>Build & Deployment:</strong> CI/CD security and automated pipeline health.</li>
			<li><strong>Implementation:</strong> Secure coding and secret management.</li>
			<li><strong>Test & Verification:</strong> Analysis coverage (SAST/DAST/SCA).</li>
			<li><strong>Information Gathering:</strong> Logging, monitoring, and vulnerability tracking.</li>
			<li><strong>Culture & Organization:</strong> Security champions and collaborative governance.</li>
		</ul>
	</div>

	<!-- Understanding Results -->
	<h2 class="section-heading" id="reading-results">Understanding Scan Results</h2>
	<p class="prose-text">
		The scan report organises findings by severity using the CVSS v3.1 scoring system. Each finding includes AI-generated context and remediation guidance.
	</p>

	<div class="severity-grid">
		<div class="severity-item critical">
			<div class="severity-badge">Critical</div>
			<div class="severity-range">9.0 – 10.0</div>
			<div class="severity-desc">Exploitable with no user interaction. Immediate remediation required.</div>
		</div>
		<div class="severity-item high">
			<div class="severity-badge">High</div>
			<div class="severity-range">7.0 – 8.9</div>
			<div class="severity-desc">Significant risk with realistic attack vectors. Fix within 24 hours.</div>
		</div>
		<div class="severity-item medium">
			<div class="severity-badge">Medium</div>
			<div class="severity-range">4.0 – 6.9</div>
			<div class="severity-desc">Exploitable under specific conditions. Schedule fix within 1 week.</div>
		</div>
		<div class="severity-item low">
			<div class="severity-badge">Low</div>
			<div class="severity-range">0.1 – 3.9</div>
			<div class="severity-desc">Limited risk. Address in next release cycle or accept risk.</div>
		</div>
	</div>

	<!-- Finding anatomy -->
	<h2 class="section-heading" id="finding-anatomy">Anatomy of a Finding</h2>
	<p class="prose-text">
		Each vulnerability finding in the report includes these fields:
	</p>

	<div class="finding-demo">
		<div class="finding-header">
			<span class="finding-severity high-badge">High</span>
			<span class="finding-type">SAST</span>
			<span class="finding-title">SQL Injection in User Query</span>
		</div>
		<div class="finding-body">
			<div class="finding-field">
				<span class="field-label">File</span>
				<code>src/services/user-service.py:47</code>
			</div>
			<div class="finding-field">
				<span class="field-label">CVSS</span>
				<span class="cvss-score">8.6</span>
			</div>
			<div class="finding-field">
				<span class="field-label">Description</span>
				<p>User-supplied input is concatenated directly into a SQL query string without parameterisation. An attacker could inject arbitrary SQL to read, modify, or delete database records.</p>
			</div>
			<div class="finding-field">
				<span class="field-label">AI Remediation</span>
				<div class="code-block">
					<div class="code-header">
						<span class="code-lang">python — fix</span>
						<button class="copy-btn" onclick={() => copyCode('fix', "# Before (vulnerable)\ncursor.execute(f\"SELECT * FROM users WHERE id = '{user_id}'\")\n\n# After (parameterised)\ncursor.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,))")}>
							{copiedStates['fix'] ? '✓ Copied' : 'Copy'}
						</button>
					</div>
					<pre><code><span class="cm"># Before (vulnerable)</span>
cursor.execute(<span class="str">f"SELECT * FROM users WHERE id = '</span>{'{'}user_id{'}'}<span class="str">'"</span>)

<span class="cm"># After (parameterised)</span>
cursor.execute(<span class="str">"SELECT * FROM users WHERE id = %s"</span>, (user_id,))</code></pre>
				</div>
			</div>
		</div>
	</div>

	<!-- Automated Scanning -->
	<h2 class="section-heading" id="automated-scanning">Automated Scanning</h2>
	<p class="prose-text">
		Configure automated scans to run whenever code changes are pushed to your repository.
	</p>

	<div class="auto-features">
		<div class="auto-item">
			<div class="auto-icon">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
				</svg>
			</div>
			<div>
				<strong>Push-triggered scans</strong>
				<p>Automatically run scans on every push to main/master or configured branches.</p>
			</div>
		</div>
		<div class="auto-item">
			<div class="auto-icon">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
				</svg>
			</div>
			<div>
				<strong>Scheduled scans</strong>
				<p>Run daily or weekly full scans to catch newly disclosed vulnerabilities in existing dependencies.</p>
			</div>
		</div>
		<div class="auto-item">
			<div class="auto-icon">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
				</svg>
			</div>
			<div>
				<strong>PR comments</strong>
				<p>WithOps adds inline security comments to pull requests with vulnerability findings and suggested fixes.</p>
			</div>
		</div>
		<div class="auto-item">
			<div class="auto-icon">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" />
				</svg>
			</div>
			<div>
				<strong>Alert channels</strong>
				<p>Receive notifications via email, Slack, or webhooks when critical vulnerabilities are detected.</p>
			</div>
		</div>
	</div>

	<div class="callout tip">
		<div class="callout-icon">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
			</svg>
		</div>
		<div class="callout-content">
			<div class="callout-label">Pro tip</div>
			<p>Enable <strong>"Block on Critical"</strong> in your scan policy to prevent merging PRs that contain critical severity vulnerabilities. Combine with GitHub branch protection for enterprise-grade security gates.</p>
		</div>
	</div>

	<!-- What's Next -->
	<h2 class="section-heading" id="whats-next">What's Next</h2>
	<div class="prose">
		<p>
			You've completed the Getting Started guide! You now have a connected workspace with automated security scanning. Here are some next steps to explore:
		</p>
	</div>

	<div class="next-grid">
		<div class="next-item">
			<span class="next-icon">📊</span>
			<div>
				<strong>Workspace Analytics</strong>
				<p>Explore the full security dashboard with trend charts, vulnerability timelines, and maturity tracking in the Intelligence tab.</p>
			</div>
		</div>
		<div class="next-item">
			<span class="next-icon">🤖</span>
			<div>
				<strong>AI RAG Chat</strong>
				<p>Use the conversational AI assistant to ask questions about your codebase, vulnerabilities, and best practices.</p>
			</div>
		</div>
		<div class="next-item">
			<span class="next-icon">📋</span>
			<div>
				<strong>Governance & Compliance</strong>
				<p>Review organization-wide policies, branch protection status, and generated compliance matrix in the workspace view.</p>
			</div>
		</div>
		<div class="next-item">
			<span class="next-icon">👥</span>
			<div>
				<strong>Team Collaboration</strong>
				<p>Invite team members, assign vulnerability remediation tasks, and track progress across your organisation.</p>
			</div>
		</div>
	</div>

	<!-- Completion badge -->
	<div class="completion-card">
		<div class="completion-icon">
			<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
				<path d="M22 11.08V12a10 10 0 11-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
			</svg>
		</div>
		<div class="completion-content">
			<h3>Getting Started Complete! 🎉</h3>
			<p>You've successfully set up WithOps, connected GitHub, and run your first security scan. Explore the platform to discover more powerful features.</p>
		</div>
	</div>

</div>

<style>
	.getting-started { opacity: 0; transform: translateY(10px); transition: all 0.5s ease; }
	.getting-started.visible { opacity: 1; transform: translateY(0); }

	.breadcrumb { display: flex; align-items: center; gap: 8px; font-family: 'DM Mono', monospace; font-size: 11px; margin-bottom: 24px; }
	.bc-link { color: var(--text-muted); text-decoration: none; transition: color 0.15s; }
	.bc-link:hover { color: var(--accent); }
	.bc-sep { color: var(--border-focus); }
	.bc-current { color: var(--accent); }

	.intel-box { display: flex; gap: 12px; margin: 24px 0; }
	.intel-stat { flex: 1; padding: 16px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; text-align: center; }
	.intel-val { display: block; font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 700; color: var(--accent); margin-bottom: 4px; }
	.intel-label { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; }

	.prose ul { list-style: none; padding: 0; margin: 16px 0; display: flex; flex-direction: column; gap: 8px; }
	.prose li { position: relative; padding-left: 20px; font-family: 'Lora', serif; font-size: 14.5px; color: var(--text-secondary); line-height: 1.6; }
	.prose li::before { content: '→'; position: absolute; left: 0; color: var(--accent); font-family: 'DM Mono', monospace; }

	.chapter-tag { font-family: 'DM Mono', monospace; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
	.chapter-tag::after { content: ''; flex: 1; height: 1px; background: var(--accent); opacity: 0.2; max-width: 50px; }

	.page-title { font-family: 'Playfair Display', serif; font-size: 38px; font-weight: 700; line-height: 1.15; color: var(--text-primary); margin-bottom: 10px; }
	.page-subtitle { font-family: 'Lora', serif; font-style: italic; font-size: 15px; color: var(--text-secondary); line-height: 1.6; }
	.divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; }

	.meta-row { display: flex; align-items: center; gap: 12px; margin-bottom: 28px; font-family: 'DM Mono', monospace; font-size: 11px; color: var(--text-muted); }
	.meta-reading { display: flex; align-items: center; gap: 4px; }
	.meta-tag { padding: 2px 8px; background: var(--bg-surface-2); border: 1px solid var(--border); border-radius: 3px; color: var(--text-secondary); font-size: 10px; }

	.section-heading { font-family: 'Playfair Display', serif; font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 40px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }

	.prose p, .prose-text { font-family: 'Lora', serif; font-size: 15px; line-height: 1.85; color: var(--text-primary); margin-bottom: 16px; }
	.prose strong { font-weight: 600; }

	/* Steps */
	.steps { display: flex; flex-direction: column; gap: 12px; margin: 20px 0 32px; }
	.step-card { display: flex; gap: 16px; padding: 18px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; box-shadow: var(--card-shadow); }
	.step-num { width: 30px; height: 30px; background: var(--bg-surface-2); border: 1px solid var(--border); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'Playfair Display', serif; font-size: 14px; color: var(--accent); flex-shrink: 0; }
	.step-body h4 { font-family: 'Lora', serif; font-weight: 600; font-size: 14px; color: var(--text-primary); margin-bottom: 4px; }
	.step-body p { font-family: 'Lora', serif; font-size: 13px; line-height: 1.65; color: var(--text-secondary); margin: 0; }
	.step-body strong { font-weight: 600; color: var(--text-primary); }

	/* Scan Grid */
	.scan-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0 32px; }
	.scan-card { padding: 20px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; box-shadow: var(--card-shadow); }
	.scan-card.full-width { grid-column: 1 / -1; }
	.scan-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
	.scan-icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
	.scan-icon.blue { background: rgba(0, 173, 239, 0.08); color: var(--accent); }
	.scan-icon.green { background: rgba(16, 185, 129, 0.08); color: var(--success); }
	.scan-icon.amber { background: rgba(245, 158, 11, 0.08); color: var(--warn); }
	.scan-icon.purple { background: rgba(139, 92, 246, 0.08); color: #8b5cf6; }
	.scan-icon.red { background: rgba(239, 68, 68, 0.08); color: var(--error); }
	.scan-header h4 { font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; }
	.scan-badge { font-family: 'DM Mono', monospace; font-size: 9px; padding: 2px 6px; border-radius: 3px; background: var(--accent-subtle); color: var(--accent); text-transform: uppercase; letter-spacing: 0.06em; }
	.scan-card > p { font-family: 'Lora', serif; font-size: 12.5px; line-height: 1.65; color: var(--text-secondary); margin: 0 0 12px; }
	.scan-card > p code { font-family: 'DM Mono', monospace; font-size: 11px; background: var(--bg-surface-2); border: 1px solid var(--border); padding: 1px 4px; border-radius: 3px; color: var(--accent); }
	.scan-details { display: flex; flex-direction: column; gap: 3px; }
	.scan-details span { font-family: 'DM Mono', monospace; font-size: 10.5px; color: var(--text-muted); line-height: 1.5; }
	.scan-details strong { color: var(--text-secondary); font-weight: 500; }

	/* Severity Grid */
	.severity-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 16px 0 32px; }
	.severity-item { padding: 14px 16px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-surface); }
	.severity-badge { font-family: 'DM Mono', monospace; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
	.severity-range { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--text-muted); margin-bottom: 6px; }
	.severity-desc { font-family: 'Lora', serif; font-size: 12px; line-height: 1.5; color: var(--text-secondary); }
	.severity-item.critical .severity-badge { color: #ef4444; }
	.severity-item.high .severity-badge { color: #f97316; }
	.severity-item.medium .severity-badge { color: #eab308; }
	.severity-item.low .severity-badge { color: #22c55e; }

	/* Finding Demo */
	.finding-demo { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; margin: 16px 0 32px; }
	.finding-header { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: var(--bg-surface-2); border-bottom: 1px solid var(--border); }
	.finding-severity { font-family: 'DM Mono', monospace; font-size: 10px; padding: 3px 8px; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
	.high-badge { background: rgba(249, 115, 22, 0.1); color: #f97316; }
	.finding-type { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--text-muted); }
	.finding-title { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; color: var(--text-primary); }
	.finding-body { padding: 16px; }
	.finding-field { margin-bottom: 12px; }
	.finding-field:last-child { margin-bottom: 0; }
	.field-label { font-family: 'DM Mono', monospace; font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; display: block; margin-bottom: 4px; }
	.finding-field code { font-family: 'DM Mono', monospace; font-size: 12px; color: var(--accent); }
	.finding-field p { font-family: 'Lora', serif; font-size: 13px; line-height: 1.65; color: var(--text-secondary); margin: 0; }
	.cvss-score { font-family: 'DM Mono', monospace; font-size: 14px; font-weight: 600; color: #f97316; }

	/* Code Block */
	.code-block { background: var(--code-bg); border-radius: 6px; margin: 8px 0; overflow: hidden; border: 1px solid var(--code-border); }
	.code-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid var(--code-border); }
	.code-lang { font-family: 'DM Mono', monospace; font-size: 11px; color: #6b7a5e; }
	.copy-btn { font-family: 'DM Mono', monospace; font-size: 11px; color: #6b7a5e; background: none; border: none; cursor: pointer; padding: 2px 8px; border-radius: 3px; transition: all 0.15s; }
	.copy-btn:hover { background: rgba(255, 255, 255, 0.06); color: #b5c9a0; }
	pre { padding: 14px 18px; overflow-x: auto; font-family: 'DM Mono', monospace; font-size: 12px; line-height: 1.7; color: var(--code-text); margin: 0; }
	.cm { color: #5a6e4a; }
	.str { color: #a5c985; }

	/* Automated Features */
	.auto-features { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 16px 0 24px; }
	.auto-item { display: flex; gap: 12px; padding: 16px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; align-items: flex-start; }
	.auto-icon { width: 32px; height: 32px; background: var(--accent-subtle); border-radius: 6px; display: flex; align-items: center; justify-content: center; color: var(--accent); flex-shrink: 0; }
	.auto-item strong { font-family: 'Inter', sans-serif; font-size: 12.5px; font-weight: 600; color: var(--text-primary); display: block; margin-bottom: 3px; }
	.auto-item p { font-family: 'Lora', serif; font-size: 12px; line-height: 1.55; color: var(--text-secondary); margin: 0; }

	/* Next Grid */
	.next-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 16px 0 32px; }
	.next-item { display: flex; gap: 12px; padding: 16px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 6px; align-items: flex-start; transition: border-color 0.15s; }
	.next-item:hover { border-color: var(--border-focus); }
	.next-icon { font-size: 20px; flex-shrink: 0; }
	.next-item strong { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; color: var(--text-primary); display: block; margin-bottom: 3px; }
	.next-item p { font-family: 'Lora', serif; font-size: 12px; line-height: 1.55; color: var(--text-secondary); margin: 0; }

	/* Completion Card */
	.completion-card { display: flex; gap: 18px; padding: 24px; background: var(--bg-surface); border: 2px solid var(--success); border-radius: 8px; margin: 32px 0; align-items: center; }
	.completion-icon { color: var(--success); flex-shrink: 0; }
	.completion-content h3 { font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; }
	.completion-content p { font-family: 'Lora', serif; font-size: 13px; line-height: 1.6; color: var(--text-secondary); margin: 0; }

	/* Callouts */
	.callout { display: flex; gap: 14px; padding: 16px 20px; border-radius: 0 6px 6px 0; margin: 20px 0; border-left: 3px solid; }
	.callout.tip { background: var(--callout-tip-bg); border-left-color: var(--callout-tip-border); }
	.callout-icon { flex-shrink: 0; margin-top: 2px; color: var(--callout-tip-text); }
	.callout-label { font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 4px; color: var(--callout-tip-text); }
	.callout-content p { font-family: 'Lora', serif; font-size: 13.5px; line-height: 1.7; color: var(--text-secondary); margin: 0; }
	.callout-content strong { font-weight: 600; color: var(--text-primary); }

	@media (max-width: 768px) {
		.page-title { font-size: 28px; }
		.scan-grid, .severity-grid, .auto-features, .next-grid { grid-template-columns: 1fr; }
		.scan-card.full-width { grid-column: auto; }
		.finding-header { flex-wrap: wrap; }
	}
</style>
