<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getAuthClient } from '$lib/auth';
	import '../app.css';

	let isAuthenticated = false;
	let user = null;
	let typedCode = '';
	let yamlBody;
	let lineCount = 0;

	// Spotlight effect for cards
	function spotlight(node) {
		const handleMouseMove = (e) => {
			const { left, top } = node.getBoundingClientRect();
			node.style.setProperty('--mouse-x', `${e.clientX - left}px`);
			node.style.setProperty('--mouse-y', `${e.clientY - top}px`);
		};
		node.addEventListener('mousemove', handleMouseMove);
		return {
			destroy() {
				node.removeEventListener('mousemove', handleMouseMove);
			}
		};
	}

	const yamlCode = `# WithOps DevSecOps Platform - Complete Architecture Specification
apiVersion: v1
kind: Platform
metadata:
  name: withops-devsecops-platform
  version: "2.0.1"
  description: Enterprise-grade AI-powered security automation and continuous integration platform designed for modern development teams
  maintainer: WithOps Engineering Team
  license: Proprietary
  documentation: https://docs.withops.io

platform:
  name: WithOps DevSecOps Platform
  type: Integrated Security Automation
  mission: "Everything After Code - Intelligent AI-driven security automation that empowers development teams to ship code faster, safer, and smarter"
  tagline: "Advanced security automation meets continuous integration with real-time AI-powered threat detection and intelligent monitoring capabilities"
  
architecture:
  frontend:
    framework: SvelteKit
    language: JavaScript ES2023
    description: "Modern reactive frontend built with SvelteKit providing real-time updates, seamless navigation, and exceptional user experience"
    features:
      - "Real-time security dashboard with live metrics and threat visualization"
      - "Interactive analytics engine with customizable charts and data exploration"
      - "Seamless GitHub integration UI for repository management and PR reviews"
      - "Advanced threat visualization with 3D dependency graphs and attack vectors"
      - "Live monitoring console with WebSocket-powered real-time updates"
      - "Responsive design optimized for desktop, tablet, and mobile devices"
    port: 5173
    build: "npm run build"
    bundle: "vite with code-splitting and tree-shaking"
    
  backend:
    framework: FastAPI
    language: Python 3.11+
    version: "3.11.7"
    description: "High-performance asynchronous backend API built with FastAPI, delivering sub-millisecond response times and handling thousands of concurrent connections"
    features:
      - "RESTful API with automatic OpenAPI documentation and interactive API explorer"
      - "WebSocket support for real-time bidirectional communication and live updates"
      - "Advanced background task processing with Celery and Redis queue management"
      - "Intelligent rate limiting with Redis-backed token bucket algorithm"
      - "Secure JWT authentication with Auth0 integration and refresh token rotation"
      - "Comprehensive logging and monitoring with structured log aggregation"
    port: 8000
    server: "uvicorn with auto-reload and graceful shutdown"
    performance: "Handles 10,000+ requests per second with 99.9% uptime"
    
microservices:
  ai-service:
    purpose: "AI-powered threat analysis and intelligent security assessment"
    technology: "OpenAI GPT-4 with custom fine-tuned models for security analysis"
    description: "Advanced machine learning service that analyzes code vulnerabilities, detects security threats, and provides automated remediation suggestions using state-of-the-art AI models"
    capabilities:
      - "Deep code vulnerability detection using static and dynamic analysis techniques"
      - "Comprehensive security risk assessment with CVSS scoring and priority ranking"
      - "Automated remediation suggestions with code snippets and implementation guides"
      - "Natural language queries for security insights and threat investigation"
      - "Continuous learning from historical data to improve detection accuracy"
    models:
      - "GPT-4 for natural language processing and code understanding"
      - "Custom BERT model for vulnerability pattern recognition"
      - "Ensemble models for false positive reduction"
    
  github-service:
    purpose: "Comprehensive GitHub repository integration and management"
    api: "GitHub REST API v3 with GraphQL support for complex queries"
    description: "Seamless integration with GitHub providing automated pull request analysis, workflow monitoring, security scanning, and dependency tracking across all repositories"
    features:
      - "Automated pull request security analysis with inline code comments and suggestions"
      - "Real-time GitHub Actions workflow monitoring with status notifications and logs"
      - "Comprehensive code scanning using CodeQL, Trivy, and custom security rules"
      - "Intelligent dependency tracking with automated vulnerability alerts and update recommendations"
      - "Branch protection enforcement and security policy compliance checking"
    integrations:
      - "GitHub Apps with fine-grained permissions for enhanced security"
      - "Webhook handlers for real-time event processing"
      - "GraphQL queries for optimized data fetching"
    
  threat-modeling:
    purpose: "Advanced security threat modeling and attack surface analysis"
    engine: "Custom AI-powered threat modeling engine with industry best practices"
    description: "Sophisticated threat modeling service that identifies potential security vulnerabilities, maps attack vectors, generates comprehensive threat models, and provides strategic mitigation recommendations"
    capabilities:
      - "STRIDE threat analysis covering Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege"
      - "Comprehensive attack vector mapping with visual dependency graphs and threat paths"
      - "Industry-standard mitigation strategies aligned with OWASP Top 10 and CWE guidelines"
      - "Dynamic risk scoring based on exploitability, impact, and business context"
      - "Automated threat model generation from architecture diagrams and code analysis"
    methodologies:
      - "STRIDE threat modeling framework"
      - "PASTA risk-centric threat modeling"
      - "Attack tree analysis"
    
  workspace-intelligence:
    purpose: "Intelligent code analysis and workspace optimization engine"
    description: "Advanced code intelligence service that performs semantic analysis, detects code patterns, enforces best practices, and tracks technical debt across entire codebase"
    features:
      - "Deep semantic analysis using abstract syntax trees and control flow graphs"
      - "Intelligent pattern detection for security anti-patterns and code smells"
      - "Automated best practice enforcement with customizable rule sets"
      - "Comprehensive technical debt tracking with prioritized remediation roadmap"
      - "Code quality metrics and trend analysis over time"
    analysis:
      - "Cyclomatic complexity calculation"
      - "Code duplication detection"
      - "Dead code identification"

security:
  authentication:
    provider: Auth0
    description: "Enterprise-grade authentication powered by Auth0 with multi-factor authentication, single sign-on, and advanced security features"
    methods:
      - "OAuth 2.0 with PKCE for secure authorization flows"
      - "JWT tokens with RSA-256 signing and automatic rotation"
      - "Single Sign-On (SSO) integration with SAML 2.0 and OpenID Connect"
      - "Social login providers including Google, GitHub, and Microsoft"
    features:
      - "Multi-factor authentication with TOTP, SMS, and biometric options"
      - "Role-based access control with fine-grained permissions and custom roles"
      - "Advanced session management with device tracking and remote logout"
      - "Anomaly detection for suspicious login attempts and account takeover prevention"
      
  scanning:
    description: "Multi-layered security scanning with industry-leading tools"
    tools:
      - name: Trivy
        type: "Container and filesystem vulnerability scanner"
        description: "Comprehensive vulnerability scanning for containers, filesystems, and Git repositories"
        severity: [CRITICAL, HIGH, MEDIUM, LOW]
        coverage: "OS packages, application dependencies, IaC misconfigurations"
      - name: CodeQL
        type: "Semantic code analysis engine"
        description: "Advanced static analysis using semantic code queries to find security vulnerabilities"
        languages: [JavaScript, TypeScript, Python, Java, C, C++, C#, Go]
        queries: "Standard security queries plus custom rule sets"
      - name: Snyk
        type: "Developer-first security platform"
        description: "Real-time dependency scanning with automated fix pull requests"
        realtime: true
        coverage: "Open source dependencies, container images, IaC configurations"

database:
  primary:
    type: Supabase
    engine: "PostgreSQL 15 with PostGIS and pg_vector extensions"
    description: "Fully managed PostgreSQL database with real-time subscriptions, row-level security, and auto-generated REST APIs"
    features:
      - "Real-time subscriptions for live data updates using WebSocket connections"
      - "Row-level security policies for fine-grained access control at database level"
      - "Auto-generated REST APIs with built-in authentication and authorization"
      - "Full-text search with trigram similarity and ranking algorithms"
      - "Vector search for AI embeddings and semantic similarity queries"
    performance:
      - "Read replicas for load distribution"
      - "Connection pooling with pgBouncer"
      - "Automated backups with point-in-time recovery"
  
  cache:
    type: Redis
    version: "7.2"
    description: "High-performance in-memory data store used for caching, session management, and real-time features"
    use-cases:
      - "Session storage with automatic expiration and distributed locking"
      - "Rate limiting using sliding window algorithm with token buckets"
      - "Real-time data caching for frequently accessed queries and computed results"
      - "Background job queue management with Celery integration"
      - "Pub/Sub messaging for inter-service communication"

deployment:
  containers:
    runtime: "Docker with multi-stage builds for optimized image sizes"
    orchestration: "Kubernetes with automated scaling and self-healing"
    registry: "GitHub Container Registry (ghcr.io) with automated image scanning"
    strategy: "Blue-green deployments with automatic rollback on failure"
    
  ci-cd:
    platform: "GitHub Actions with reusable workflows"
    description: "Fully automated CI/CD pipeline with comprehensive testing, security scanning, and deployment automation"
    stages:
      - "Security Scan: Trivy filesystem scan, CodeQL analysis, dependency checking"
      - "Unit Tests: Parallel test execution with coverage reporting"
      - "Integration Tests: End-to-end testing with real service dependencies"
      - "Build: Multi-stage Docker builds with layer caching"
      - "Container Scan: Image vulnerability scanning and policy enforcement"
      - "Deploy: Kubernetes rolling update with health checks"
      - "Smoke Tests: Production environment validation and monitoring"
    automation:
      - "Automated dependency updates with Dependabot"
      - "Security vulnerability alerts with auto-fix PRs"
      - "Performance regression testing"
    
  infrastructure:
    provider: "Multi-cloud architecture with AWS, Azure, and GCP support"
    scaling: "Horizontal auto-scaling based on CPU, memory, and custom metrics"
    monitoring: "Real-time observability with distributed tracing and log aggregation"
    alerts: "Integrated alerting with PagerDuty and Slack notifications"
    disaster-recovery: "Multi-region deployment with automated failover"

monitoring:
  logging:
    framework: "Structured logging with Python's logging module"
    levels: [DEBUG, INFO, WARNING, ERROR, CRITICAL]
    format: "JSON-formatted logs for easy parsing and analysis"
    rotation: "Daily rotation with 30-day retention and compression"
    aggregation: "Centralized log aggregation with Elasticsearch and Kibana"
    
  metrics:
    description: "Comprehensive metrics collection and visualization"
    tracked:
      - "API response time with p50, p95, and p99 percentiles"
      - "Threat detection rate and false positive ratio"
      - "Security score trends and compliance metrics"
      - "User activity patterns and feature adoption"
      - "System health including CPU, memory, disk, and network"
    visualization: "Grafana dashboards with real-time updates"

integrations:
  - name: GitHub
    type: "Version Control System"
    status: active
    description: "Deep integration for repository management and code analysis"
  - name: OpenAI
    type: "Artificial Intelligence"
    status: active  
    description: "GPT-4 powered threat analysis and code understanding"
  - name: Auth0
    type: "Authentication Provider"
    status: active
    description: "Enterprise authentication and authorization"
  - name: Supabase
    type: "Database Platform"
    status: active
    description: "PostgreSQL database with real-time capabilities"
  - name: Slack
    type: "Communication"
    status: active
    description: "Real-time notifications and team collaboration"

features:
  core:
    - "AI-powered threat analysis with automated vulnerability detection and risk assessment"
    - "Automated security scanning across code, containers, and infrastructure"
    - "Real-time monitoring dashboard with live metrics and threat intelligence"
    - "Collaborative workflows with role-based access and team management"
    - "Comprehensive security reporting with executive summaries and detailed findings"
    - "Threat intelligence database with historical trends and pattern analysis"
  
  advanced:
    - "Custom machine learning models trained on your codebase"
    - "Predictive analytics for proactive security posture management"
    - "Custom integrations via REST API and webhook support"
    - "API-first architecture enabling seamless third-party integrations"
    - "Webhook support for real-time event notifications"
    - "Multi-tenant support with data isolation and tenant-specific configurations"`;

	// Function to add YAML syntax highlighting with matching color scheme
	function highlightYAML(code) {
		return code
			.split('\n')
			.map((line) => {
				// Comments (light gray)
				if (line.trim().startsWith('#')) {
					return `<span style="color: #B8B8B8; font-style: italic;">${line}</span>`;
				}

				// Key-value pairs
				const keyValueMatch = line.match(/^(\s*)([a-zA-Z_][\w-]*):(.*)$/);
				if (keyValueMatch) {
					const [, indent, key, value] = keyValueMatch;
					let coloredValue = value;

					// Quoted strings (light gray)
					if (value.includes('"')) {
						coloredValue = value.replace(/"([^"]*)"/g, '<span style="color: #e2e8f0;">"$1"</span>');
					}
					// Numbers (bright blue)
					else if (value.trim().match(/^\d+$/)) {
						coloredValue = ` <span style="color: #60a5fa;">${value.trim()}</span>`;
					}
					// Boolean values (bright blue)
					else if (value.trim().match(/^(true|false|active|yes|no)$/i)) {
						coloredValue = ` <span style="color: #60a5fa;">${value.trim()}</span>`;
					}
					// URLs (bright blue)
					else if (value.includes('http')) {
						coloredValue = value.replace(
							/(https?:\/\/[^\s,"]+)/g,
							'<span style="color: #60a5fa;">$1</span>'
						);
					}
					// Other string values (muted gray)
					else if (value.trim()) {
						coloredValue = ` <span style="color: #94a3b8;">${value.trim()}</span>`;
					}

					return `${indent}<span style="color: #60a5fa;">${key}</span><span style="color: #f1f5f9;">:</span>${coloredValue}`;
				}

				// Array items with dash
				const arrayMatch = line.match(/^(\s*)- (.*)$/);
				if (arrayMatch) {
					const [, indent, value] = arrayMatch;
					let coloredValue = value;

					if (value.includes('"')) {
						coloredValue = value.replace(/"([^"]*)"/g, '<span style="color: #FFFFFF;">"$1"</span>');
					} else {
						coloredValue = `<span style="color: #B8B8B8;">${value}</span>`;
					}

					return `${indent}<span style="color: #FFFFFF;">-</span> ${coloredValue}`;
				}

				// Default: return line as is with light gray
				return `<span style="color: #B8B8B8;">${line}</span>`;
			})
			.join('\n');
	}

	// Auth functions
	async function handleSignIn() {
		try {
			const client = await getAuthClient();
			await client.loginWithRedirect();
		} catch (error) {
			console.error('Sign in failed:', error);
		}
	}

	async function handleGetStarted() {
		try {
			const client = await getAuthClient();
			const authenticated = await client.isAuthenticated();

			if (authenticated) {
				goto('/dashboard');
			} else {
				await client.loginWithRedirect();
			}
		} catch (error) {
			console.error('Get started failed:', error);
		}
	}

	// Check authentication status and start typing animation
	onMount(async () => {
		try {
			const client = await getAuthClient();
			isAuthenticated = await client.isAuthenticated();
			if (isAuthenticated) {
				user = await client.getUser();
			}
		} catch (error) {
			console.error('Auth check failed:', error);
		}

		// Typing animation - character by character at AI-agent speed
		const lines = yamlCode.split('\n');
		const highlighted = lines.map((l) => highlightYAML(l));
		let lineIdx = 0;
		let charIdx = 0;
		let completedLines = [];
		let paused = false;
		let pauseTimer = null;
		const CHARS_PER_TICK = 2;
		const TICK_MS = 22; // natural AI typing feel
		const LINE_PAUSE = 60; // brief pause between lines (ms)
		const RESTART_PAUSE = 3000; // pause before restart (ms)

		const interval = setInterval(() => {
			if (paused) return;

			if (lineIdx >= lines.length) {
				// All done — pause then restart
				paused = true;
				pauseTimer = setTimeout(() => {
					lineIdx = 0;
					charIdx = 0;
					completedLines = [];
					typedCode = '';
					paused = false;
					if (yamlBody) yamlBody.scrollTop = 0;
				}, RESTART_PAUSE);
				return;
			}

			const currentLine = lines[lineIdx];
			charIdx = Math.min(charIdx + CHARS_PER_TICK, currentLine.length);

			if (charIdx >= currentLine.length) {
				// Line finished — use pre-highlighted version
				completedLines.push(highlighted[lineIdx]);
				typedCode = completedLines.join('\n');
				lineCount = completedLines.length;
				lineIdx++;
				charIdx = 0;
				// Brief pause between lines for natural feel
				paused = true;
				setTimeout(() => {
					paused = false;
				}, LINE_PAUSE);
			} else {
				// Partially typed line
				const partial = highlightYAML(currentLine.slice(0, charIdx));
				typedCode = [...completedLines, partial].join('\n');
			}

			// Auto-scroll
			if (yamlBody) yamlBody.scrollTop = yamlBody.scrollHeight;
		}, TICK_MS);

		return () => {
			clearInterval(interval);
			if (pauseTimer) clearTimeout(pauseTimer);
		};
	});
	// Magnetic button logic for luxury interaction
	function magnetic(node) {
		const move = (e) => {
			const rect = node.getBoundingClientRect();
			const centerX = rect.left + rect.width / 2;
			const centerY = rect.top + rect.height / 2;
			const x = (e.clientX - centerX) * 0.35;
			const y = (e.clientY - centerY) * 0.35;
			node.style.transform = `translate(${x}px, ${y}px)`;
		};
		const reset = () => {
			node.style.transform = `translate(0, 0)`;
		};
		node.addEventListener('mousemove', move);
		node.addEventListener('mouseleave', reset);
		return {
			destroy() {
				node.removeEventListener('mousemove', move);
				node.removeEventListener('mouseleave', reset);
			}
		};
	}

	function reveal(node, options = {}) {
		const { threshold = 0.15, delay = 0, direction = 'up' } = options;
		const dirMap = {
			up: 'reveal-up',
			down: 'reveal-down',
			left: 'reveal-left',
			right: 'reveal-right',
			scale: 'reveal-scale',
			none: 'reveal-fade'
		};
		node.classList.add('reveal', dirMap[direction] || 'reveal-up');
		if (delay) node.style.transitionDelay = `${delay}ms`;
		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						node.classList.add('revealed');
						observer.unobserve(node);
					}
				});
			},
			{ threshold }
		);
		observer.observe(node);
		return {
			destroy() {
				observer.disconnect();
			}
		};
	}
</script>

<!-- Navigation Bar -->
<nav class="navbar">
	<div class="nav-container">
		<div class="nav-brand">
			<div class="nav-brand-icon">
				<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
			</div>
			<span class="brand-name">WithOps</span>
		</div>
		<div class="nav-menu">
			<a href="#home" class="nav-link">Product</a>
			<a href="#security" class="nav-link">Security</a>
			<a href="#analytics" class="nav-link">Analytics</a>
			<a href="#docs" class="nav-link">Docs</a>
			<a href="#contact" class="nav-link">Pricing</a>
		</div>
		<div class="nav-actions">
			{#if isAuthenticated}
				<span class="user-welcome">Welcome, {user?.name}</span>
				<button class="nav-btn-primary" on:click={() => goto('/dashboard')}>Dashboard</button>
			{:else}
				<button class="nav-btn-secondary" on:click={handleSignIn}>Login</button>
				<button class="nav-btn-primary" on:click={handleGetStarted}>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"
						><path
							d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
						/></svg
					>
					Connect GitHub
				</button>
			{/if}
		</div>
	</div>
</nav>

<!-- Hero Section -->
<section class="hero" id="home">
	<!-- Background -->
	<div class="hero-bg">
		<div class="hero-bg-base"></div>
		<div class="hero-bg-grid"></div>
	</div>
	<!-- 3D Depth layers -->
	<div class="hero-depth-fog"></div>
	<div class="hero-vignette"></div>
	<div class="hero-particles">
		<div class="particle p1"></div>
		<div class="particle p2"></div>
		<div class="particle p3"></div>
		<div class="particle p4"></div>
		<div class="particle p5"></div>
	</div>

	<div class="hero-container">
		<!-- Left: Text Content -->
		<div class="hero-left" use:reveal={{ direction: 'left', threshold: 0.1 }}>
			<h1 class="hero-title">
				AI for<br />
				<span class="hero-title-accent">Secure CI/CD Pipelines</span>
			</h1>

			<p class="hero-description">
				Automatically assess DevSecOps maturity, detect security tool gaps, and perform AI-driven
				threat modeling grounded in industry standards like OWASP DSOMM.
			</p>

			<div class="hero-buttons">
				{#if isAuthenticated}
					<button class="btn-primary" on:click={() => goto('/dashboard')}>
						<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"
							><path
								d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
							/></svg
						>
						Go to Dashboard
					</button>
				{:else}
					<button class="btn-primary" use:magnetic on:click={handleGetStarted}>
						<span>Get Started</span>
						<svg
							width="16"
							height="16"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="3"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<polyline points="9 18 15 12 9 6"></polyline>
						</svg>
					</button>
					<button class="btn-secondary" on:click={handleSignIn}>
						<!--  -->
						SIGN IN
					</button>
				{/if}
			</div>
		</div>

		<!-- Right: YAML Animation -->
		<div class="hero-right" use:reveal={{ direction: 'right', delay: 300, threshold: 0.1 }}>
			<div class="yaml-panel-container">
				<div class="yaml-panel">
					<div class="yaml-panel-header">
						<div class="yaml-dots">
							<div class="dot dot-red"></div>
							<div class="dot dot-yellow"></div>
							<div class="dot dot-green"></div>
						</div>
						<div class="yaml-breadcrumbs">
							<span class="breadcrumb-item">withops</span>
							<span class="breadcrumb-separator">/</span>
							<span class="breadcrumb-item">pipelines</span>
							<span class="breadcrumb-separator">/</span>
							<span class="breadcrumb-item active">secure-deploy.yml</span>
						</div>
						<div class="yaml-actions-ui">
							<button class="yaml-copy-btn">
								<svg
									width="14"
									height="14"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path
										d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
									></path></svg
								>
								Copy
							</button>
						</div>
						<div class="yaml-tabs">
							<div class="yaml-tab yaml-tab-active">YAML</div>
							<div class="yaml-tab">Output</div>
						</div>
					</div>
					<div class="yaml-panel-body" bind:this={yamlBody}>
						<div class="yaml-line-numbers">
							{#each Array(lineCount + 1) as _, i}
								<span>{i + 1}</span>
							{/each}
						</div>
						<pre class="yaml-pre"><code class="yaml-code"
								>{@html typedCode}<span class="cursor"></span></code
							></pre>
					</div>
					<div class="yaml-status-bar">
						<span>YAML</span>
						<span>UTF-8</span>
						<span>Ln {lineCount + 1}</span>
						<span>WithOps Platform</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<!-- Trust Section -->
<section class="trust-section" use:reveal={{ direction: 'up' }}>
	<div class="container">
		<p class="trust-label">Trusted by Modern Engineering Teams</p>
		<div class="trust-logos">
			<div class="trust-logo">
				<div class="trust-logo-box">
					<svg width="24" height="24" viewBox="0 0 24 24" fill="#ffffff"
						><path
							d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
						/></svg
					>
				</div>
				<span class="trust-logo-name">GitHub</span>
			</div>
			<div class="trust-logo">
				<div class="trust-logo-box">
					<svg width="24" height="24" viewBox="0 0 24 24" fill="#2496ED"
						><path
							d="M13.983 11.078h2.119a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.119a.185.185 0 00-.185.185v1.888c0 .102.083.185.185.185m-2.954-5.43h2.118a.186.186 0 00.186-.186V3.574a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.185m0 2.716h2.118a.187.187 0 00.186-.186V6.29a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.887c0 .102.082.185.185.186m-2.93 0h2.12a.186.186 0 00.184-.186V6.29a.185.185 0 00-.185-.185H8.1a.185.185 0 00-.185.185v1.887c0 .102.083.185.185.186m-2.964 0h2.119a.186.186 0 00.185-.186V6.29a.185.185 0 00-.185-.185H5.136a.186.186 0 00-.186.185v1.887c0 .102.084.185.186.186m5.893 2.715h2.118a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.185m-2.93 0h2.12a.185.185 0 00.184-.185V9.006a.185.185 0 00-.184-.186h-2.12a.185.185 0 00-.184.185v1.888c0 .102.083.185.185.185m-2.964 0h2.119a.185.185 0 00.185-.185V9.006a.185.185 0 00-.184-.186h-2.12a.186.186 0 00-.186.186v1.887c0 .102.084.185.186.185m-2.92 0h2.12a.185.185 0 00.184-.185V9.006a.185.185 0 00-.184-.186h-2.12a.185.185 0 00-.184.185v1.888c0 .102.082.185.185.185M23.763 9.89c-.065-.051-.672-.51-1.954-.51-.338.001-.676.03-1.01.087-.248-1.7-1.653-2.53-1.716-2.566l-.344-.199-.226.327c-.284.438-.49.922-.612 1.43-.23.97-.09 1.882.403 2.661-.595.332-1.55.413-1.744.42H.751a.751.751 0 00-.75.748 11.376 11.376 0 00.692 4.062c.545 1.428 1.355 2.48 2.41 3.124 1.18.723 3.1 1.137 5.275 1.137.983.003 1.963-.086 2.93-.266a12.248 12.248 0 003.823-1.389c.98-.567 1.86-1.288 2.61-2.136 1.252-1.418 1.998-2.997 2.553-4.4h.221c1.372 0 2.215-.549 2.68-1.009.309-.293.55-.65.707-1.046l.098-.288Z"
						/></svg
					>
				</div>
				<span class="trust-logo-name">Docker</span>
			</div>

			<div class="trust-logo">
				<div class="trust-logo-box">
					<img
						src="/logos/Kubernetes_logo_without_workmark.svg"
						alt="Kubernetes"
						width="32"
						height="32"
					/>
				</div>
				<span class="trust-logo-name">Kubernetes</span>
			</div>

			<div class="trust-logo">
				<div class="trust-logo-box">
					<img
						src="/logos/Terraform_Logo.svg"
						alt="Terraform"
						width="80"
						height="20"
						style="object-fit: contain;"
					/>
				</div>
				<span class="trust-logo-name">Terraform</span>
			</div>

			<div class="trust-logo">
				<div class="trust-logo-box">
					<img
						src="/logos/Harness_Logo.svg"
						alt="Harness"
						width="32"
						height="32"
					/>
				</div>
				<span class="trust-logo-name">Harness</span>
			</div>

			<div class="trust-logo">
				<div class="trust-logo-box">
					<svg width="24" height="24" viewBox="0 0 24 24" fill="#FC6D26"
						><path
							d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0118.6 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.51L23 13.45a.84.84 0 01-.35.94z"
						/></svg
					>
				</div>
				<span class="trust-logo-name">GitLab</span>
			</div>
		</div>
	</div>
</section>

<!-- Problem Section -->
<section class="problem-section" id="security">
	<div class="problem-bg-grid"></div>
	<div class="relative container">
		<div class="section-header" use:reveal={{ direction: 'up' }}>
			<p class="section-overline">The Problem</p>
			<h2 class="section-title">Most CI/CD Pipelines Lack<br />Security Visibility</h2>
			<p class="section-subtitle">
				Without automated analysis, organizations remain blind to critical security gaps
			</p>
		</div>
		<div class="problem-grid" use:reveal={{ direction: 'up', delay: 200 }}>
			<!-- Problem 1: Coverage -->
			<div class="problem-card" use:spotlight>
				<div class="problem-header-row">
					<div class="problem-icon problem-icon-red">
						<svg
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							><path
								d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
							/><line x1="12" y1="9" x2="12" y2="13" /><line
								x1="12"
								y1="17"
								x2="12.01"
								y2="17"
							/></svg
						>
					</div>
					<div class="problem-badge">HIGH RISK</div>
				</div>
				<h3>Critical Visibility Gaps</h3>
				<p>
					Organizations remain blind to risk: **70% miss SAST**, **85% lack DAST**, and **55% have
					incomplete SCA** configurations.
				</p>
				<div class="problem-data-box">
					<div class="data-row">
						<span>SAST_CORE</span> <span class="data-status status-null">NULL</span>
					</div>
					<div class="data-row">
						<span>DAST_PROD</span> <span class="data-status status-null">NULL</span>
					</div>
					<div class="data-row">
						<span>SCA_DEP</span> <span class="data-status status-fail">FAILED</span>
					</div>
				</div>
			</div>

			<!-- Problem 2: Inconsistency -->
			<div class="problem-card">
				<div class="problem-header-row">
					<div class="problem-icon problem-icon-amber">
						<svg
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18" /><path
								d="M9 21V9"
							/></svg
						>
					</div>
					<div class="problem-badge badge-amber">MISMATCH</div>
				</div>
				<h3>Fragmented Workflow Policies</h3>
				<p>
					Different teams implement varying security standards, creating holes in branch protection
					and code review processes.
				</p>
				<div class="problem-data-box">
					<div class="data-row"><span>BR_PROT</span> <span class="data-status">BYPASSED</span></div>
					<div class="data-row"><span>REQ_REV</span> <span class="data-status">DISABLED</span></div>
					<div class="data-row">
						<span>CI_VAL</span> <span class="data-status status-fail">FAILING</span>
					</div>
				</div>
			</div>

			<!-- Problem 3: Maturity -->
			<div class="problem-card">
				<div class="problem-header-row">
					<div class="problem-icon problem-icon-red">
						<svg
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg
						>
					</div>
					<div class="problem-badge">STAGNANT</div>
				</div>
				<h3>Stagnant Security Maturity</h3>
				<p>
					Most teams lack a structured roadmap for reaching higher **OWASP DSOMM** levels, with no
					baseline to measure improvements.
				</p>
				<div class="problem-data-box">
					<div class="maturity-bar-container">
						<div class="m-bar m-active"></div>
						<div class="m-bar"></div>
						<div class="m-bar"></div>
						<div class="m-bar"></div>
					</div>
					<div class="maturity-label">BASELINE: LEVEL 1</div>
				</div>
			</div>
		</div>
	</div>
</section>

<!-- Solution Section -->
<section class="solution-section" id="analytics">
	<div class="container">
		<div class="section-header" use:reveal={{ direction: 'up' }}>
			<div class="section-badge section-badge-blue">
				<span>The Solution</span>
			</div>
			<h2 class="section-title">One Unified Platform for<br />DevSecOps Intelligence</h2>
			<p class="section-subtitle">
				Comprehensive security visibility and AI-driven insights for your entire CI/CD pipeline
			</p>
		</div>
		<div class="solution-list">
			{#each [{ title: 'Workflow & Security Analysis', desc: 'Detect centralized reusable workflows and verify integration of SAST (CodeQL/SonarQube), DAST (ZAP/Burp), and SCA tools (Snyk/Dependabot).', highlights: ['Centralized Workflow Detection', 'Branch Protection Validation', 'SAST/DAST/SCA Verification', 'Automated Tool Recommendations'], gradient: 'blue-cyan' }, { title: 'DSOMM Maturity Assessment', desc: 'Automatically map security practices to the five dimensions of the OWASP DSOMM framework with a prioritized roadmap for improvement.', highlights: ['Dynamic Maturity Scoring', '5-Dimension Assessment', 'Gap Analysis & Roadmapping', 'Executive Security Reporting'], gradient: 'green-cyan' }, { title: 'AI-Powered Threat Modeling', desc: 'Utilize Claude Vision API to analyze architecture diagrams on an interactive canvas with STRIDE, LINDDUN, and CIA Triad frameworks.', highlights: ['Vision-based Architecture Analysis', 'STRIDE/LINDDUN Frameworks', 'Fact-grounded RAG fixes (Qdrant)', 'Automated Attack Vector Mapping'], gradient: 'amber-red' }] as feature, idx}
				<div
					class="solution-row"
					class:solution-row-reverse={idx % 2 === 1}
					use:reveal={{ direction: idx % 2 === 0 ? 'left' : 'right', delay: 100 }}
				>
					<div class="solution-text">
						<div class="solution-icon-box solution-gradient-{feature.gradient}">
							{#if idx === 0}
								<svg
									width="28"
									height="28"
									viewBox="0 0 24 24"
									fill="none"
									stroke="white"
									stroke-width="2"
									><line x1="6" y1="3" x2="6" y2="15" /><circle cx="18" cy="6" r="3" /><circle
										cx="6"
										cy="18"
										r="3"
									/><path d="M18 9a9 9 0 0 1-9 9" /></svg
								>
							{:else if idx === 1}
								<svg
									width="28"
									height="28"
									viewBox="0 0 24 24"
									fill="none"
									stroke="white"
									stroke-width="2"
									><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline
										points="17 6 23 6 23 12"
									/></svg
								>
							{:else}
								<svg
									width="28"
									height="28"
									viewBox="0 0 24 24"
									fill="none"
									stroke="white"
									stroke-width="2"
									><path
										d="M12 2a8 8 0 0 1 8 8c0 5.4-8 12-8 12S4 15.4 4 10a8 8 0 0 1 8-8z"
									/><circle cx="12" cy="10" r="3" /></svg
								>
							{/if}
						</div>
						<h3>{feature.title}</h3>
						<p>{feature.desc}</p>
						<ul class="check-list">
							{#each feature.highlights as h}
								<li>
									<svg
										width="18"
										height="18"
										viewBox="0 0 24 24"
										fill="none"
										stroke="#10B981"
										stroke-width="2.5"><polyline points="20 6 9 17 4 12" /></svg
									>
									<span>{h}</span>
								</li>
							{/each}
						</ul>
					</div>
					<div class="solution-visual">
						<div class="solution-visual-glow solution-gradient-{feature.gradient}"></div>
						<div class="solution-mockup">
							<div class="mockup-chrome">
								<div class="mockup-dots">
									<span class="dot dot-red"></span>
									<span class="dot dot-yellow"></span>
									<span class="dot dot-green"></span>
								</div>
								<div class="mockup-url">
									withops.ai/{idx === 0 ? 'workflow' : idx === 1 ? 'maturity' : 'threat'}
								</div>
							</div>
							<div class="mockup-body technical-view">
								{#if idx === 0}
									<!-- Workflow Intelligence: Technical Audit View -->
									<div class="audit-log">
										<div class="log-header">SEC-SCAN CORE v2.4.0</div>
										<div class="log-content">
											<div class="log-entry">
												<span class="timestamp">[14:22:01]</span>
												<span class="action">SCANNING</span> .github/workflows/main.yml
											</div>
											<div class="log-entry info">
												<span class="timestamp">[14:22:03]</span>
												<span class="tool">SONARQUBE:</span> <span class="res">PASSED (0.12s)</span>
											</div>
											<div class="log-entry warn">
												<span class="timestamp">[14:22:04]</span> <span class="tool">SNYK:</span>
												<span class="res">2 VULNERABILITIES DETECTED</span>
											</div>
											<div class="log-entry info">
												<span class="timestamp">[14:22:05]</span>
												<span class="tool">DEP-CHECK:</span> <span class="res">UP TO DATE</span>
											</div>
											<div class="log-cursor">_</div>
										</div>
									</div>
								{:else if idx === 1}
									<!-- DSOMM: Maturity Matrix View -->
									<div class="maturity-matrix">
										<div class="matrix-grid">
											{#each Array(20) as _, i}
												<div class="matrix-cell" class:cell-active={i < 12}></div>
											{/each}
										</div>
										<div class="matrix-stats">
											<div class="stat-group">
												<div class="stat-label">TOTAL COVERAGE</div>
												<div class="stat-val">68.4%</div>
											</div>
											<div class="stat-group">
												<div class="stat-label">DSOMM LEVEL</div>
												<div class="stat-val val-active">III</div>
											</div>
										</div>
									</div>
								{:else}
									<!-- Threat Modeling: Blueprint View -->
									<div class="blueprint-view">
										<div class="blueprint-canvas">
											<div class="bp-box">LB:NGINX</div>
											<div class="bp-line"></div>
											<div class="bp-box bp-active">SRV:FASTAPI</div>
											<div class="bp-line"></div>
											<div class="bp-box">DB:POSTGRES</div>

											<!-- Technical annotations -->
											<div class="bp-label top-right">TRUST BRUNDARY [EXT/INT]</div>
											<div class="bp-label bottom-left">STRIDE ANALYSIS ACTIVE</div>
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- How It Works Section -->
<section class="how-section" id="docs">
	<div class="how-bg-grid"></div>
	<div class="relative container">
		<div class="section-header" use:reveal={{ direction: 'up' }}>
			<h2 class="section-title">How It Works</h2>
			<p class="section-subtitle">Get from zero to full security visibility in under 5 minutes</p>
		</div>
		<div class="steps-wrapper">
			<!-- Animated connecting line -->
			<div class="steps-connector">
				<div class="steps-connector-track"></div>
				<div
					class="steps-connector-progress"
					use:reveal={{ direction: 'none', threshold: 0.3 }}
				></div>
			</div>
			<div class="steps-grid">
				<!-- Step 1 -->
				<div
					class="step-card step-card-purple"
					use:reveal={{ direction: 'up', delay: 0, threshold: 0.2 }}
				>
					<div class="step-header">
						<div class="step-number step-number-purple">01</div>
						<div class="step-icon step-icon-purple">
							<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"
								><path
									d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
								/></svg
							>
						</div>
					</div>
					<h4>Connect Hub</h4>
					<p>
						Technical handshaking via Auth0 and GitHub OAuth. Sub-millisecond credential securement.
					</p>
					<div class="step-visual">
						<div class="code-line">AUTH0: OAUTH2_TOKEN_SUCCESS</div>
						<div class="code-line">HANDSHAKE: WITH_OPS_V3</div>
					</div>
				</div>

				<!-- Step 2 -->
				<div
					class="step-card step-card-blue"
					use:reveal={{ direction: 'up', delay: 150, threshold: 0.2 }}
				>
					<div class="step-header">
						<div class="step-number step-number-blue">02</div>
						<div class="step-icon step-icon-blue">
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg
							>
						</div>
					</div>
					<h4>Recursive Analysis</h4>
					<p>
						Automated traversal of CI/CD structures. Deep tool detection via signature matching.
					</p>
					<div class="step-visual v-blue">
						<div class="scan-tree">
							<div class="tree-node">./workflows</div>
							<div class="tree-node depth-1">-- main.yml (SAST)</div>
							<div class="tree-node depth-1">-- prod.yml (DAST)</div>
						</div>
					</div>
				</div>

				<!-- Step 3 -->
				<div
					class="step-card step-card-amber"
					use:reveal={{ direction: 'up', delay: 300, threshold: 0.2 }}
				>
					<div class="step-header">
						<div class="step-number step-number-amber">03</div>
						<div class="step-icon step-icon-amber">
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								><path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path
									d="M2 12l10 5 10-5"
								/></svg
							>
						</div>
					</div>
					<h4>Neural Evaluation</h4>
					<p>RAG-enhanced risk assessments grounded in Qdrant vector database intelligence.</p>
					<div class="step-visual v-amber">
						<div class="eval-grid">
							<div class="grid-dot active"></div>
							<div class="grid-dot"></div>
							<div class="grid-dot active"></div>
							<div class="grid-dot"></div>
						</div>
						<div class="eval-text">P(THREAT) = 0.084</div>
					</div>
				</div>

				<!-- Step 4 -->
				<div
					class="step-card step-card-green"
					use:reveal={{ direction: 'up', delay: 450, threshold: 0.2 }}
				>
					<div class="step-header">
						<div class="step-number step-number-green">04</div>
						<div class="step-icon step-icon-green">
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								><path d="M22 11.08V12a10 10 0 11-5.93-9.14" /><polyline
									points="22 4 12 14.01 9 11.01"
								/></svg
							>
						</div>
					</div>
					<h4>Maturity Scaling</h4>
					<p>Finalized DSOMM roadmap with prioritized remediation and executive reporting.</p>
					<div class="step-visual v-green">
						<div class="report-bar"></div>
						<div class="report-bar w-70"></div>
						<div class="report-bar w-40"></div>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<!-- Why Choose WithOps (Bento Grid) -->
<section class="why-section" id="why">
	<div class="container">
		<div class="section-header" use:reveal={{ direction: 'up' }}>
			<p class="section-overline">Platform Strength</p>
			<h2 class="section-title">Why Choose WithOps</h2>
			<p class="section-subtitle">
				A sophisticated engine designed for high-scale security automation
			</p>
		</div>

		<div class="bento-grid">
			<!-- Large Feature: AI Core -->
			<div class="bento-item bento-large" use:reveal={{ direction: 'up' }} use:spotlight>
				<div class="bento-content">
					<div class="bento-tag">Hybrid AI Core</div>
					<h3>Multi-Model Intelligence</h3>
					<p>
						Engineered with Claude 3.5 Vision for architecture analysis and Ollama for local
						inference. Our RAG system uses Qdrant vector embeddings to ensure every security fix is
						fact-grounded in industry best practices.
					</p>
					<div class="bento-visual">
						<div class="ai-signal-lines">
							{#each Array(5) as _}
								<div class="ai-line"></div>
							{/each}
						</div>
					</div>
				</div>
			</div>

			<!-- Feature: DSOMM -->
			<div
				class="bento-item bento-medium"
				use:reveal={{ direction: 'up', delay: 100 }}
				use:spotlight
			>
				<div class="bento-content">
					<div class="bento-tag">Compliance</div>
					<h3>OWASP DSOMM Standard</h3>
					<p>
						Quantify your DevSecOps journey. Native mapping to the complete DSOMM framework ensures
						your security posture is industry-validated and measurable.
					</p>
					<div class="maturity-meter">
						<div class="meter-bar"></div>
						<div class="meter-value">Level 4</div>
					</div>
				</div>
			</div>

			<!-- Feature: Real-time -->
			<div
				class="bento-item bento-medium"
				use:reveal={{ direction: 'up', delay: 200 }}
				use:spotlight
			>
				<div class="bento-content">
					<div class="bento-tag">Observability</div>
					<h3>Full-Stack Monitoring</h3>
					<p>
						Technical transparency through Prometheus & Grafana. We use Jaeger distributed tracing
						to monitor requests across all 8 microservices, ensuring sub-millisecond reliability.
					</p>
					<div class="live-indicator-tray">
						<div class="pulse-dot"></div>
						<span class="live-text">DISTRIBUTED TRACING ACTIVE</span>
					</div>
				</div>
			</div>

			<!-- Feature: GitHub Native -->
			<div class="bento-item bento-wide" use:reveal={{ direction: 'up', delay: 300 }} use:spotlight>
				<div class="bento-content bento-content-row">
					<div class="bento-text-side">
						<div class="bento-tag">Centralization</div>
						<h3>Reusable Workflow Adoption</h3>
						<p>
							We don't just find bugs; we promote architecture. WithOps automatically detects and
							converts fragmented CI steps into centralized, reusable GitHub workflows for
							enterprise-wide consistency.
						</p>
					</div>
					<div class="github-visual-mini">
						<svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor"
							><path
								d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
							/></svg
						>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<!-- Final CTA Section -->
<section class="final-cta" id="contact">
	<div class="final-cta-bg"></div>
	<div class="final-cta-grid-bg"></div>
	<div
		class="final-cta-inner relative container"
		use:reveal={{ direction: 'scale', threshold: 0.2 }}
	>
		<h2>
			Start Measuring Your<br /><span class="final-cta-accent">DevSecOps Maturity</span><br />Today
		</h2>
		<p>
			Join forward-thinking teams already securing their CI/CD pipelines with AI-powered
			intelligence
		</p>
		<div class="hero-buttons final-cta-buttons">
			{#if isAuthenticated}
				<button class="btn-primary" on:click={() => goto('/dashboard')}>Go to Dashboard</button>
			{:else}
				<button class="btn-primary" on:click={handleGetStarted}>
					<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"
						><path
							d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
						/></svg
					>
					Connect GitHub Organization
				</button>
				<button class="btn-secondary" on:click={handleSignIn}>Request Demo</button>
			{/if}
		</div>
	</div>
</section>

<!-- Footer -->
<footer class="footer">
	<div class="container">
		<div class="footer-grid">
			<div class="footer-brand">
				<div class="footer-logo">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<span class="brand-name footer-brand-name">WithOps</span>
				</div>
				<p class="footer-desc">AI-powered DevSecOps intelligence for modern engineering teams</p>
				<div class="footer-social">
					<a
						href="https://github.com"
						class="social-link"
						target="_blank"
						rel="noopener noreferrer"
						aria-label="GitHub"
						><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"
							><path
								d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
							/></svg
						></a
					>
					<a
						href="https://twitter.com"
						class="social-link"
						target="_blank"
						rel="noopener noreferrer"
						aria-label="Twitter"
						><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"
							><path
								d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"
							/></svg
						></a
					>
					<a
						href="https://linkedin.com"
						class="social-link"
						target="_blank"
						rel="noopener noreferrer"
						aria-label="LinkedIn"
						><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"
							><path
								d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"
							/></svg
						></a
					>
				</div>
			</div>
			{#each [{ title: 'Product', links: ['Features', 'Security', 'Analytics', 'Pricing', 'Changelog'] }, { title: 'Resources', links: ['Documentation', 'API Reference', 'Guides', 'Blog', 'Community'] }, { title: 'Company', links: ['About', 'Careers', 'Contact', 'Partners', 'Press Kit'] }, { title: 'Legal', links: ['Privacy Policy', 'Terms of Service', 'Security', 'Compliance', 'GDPR'] }] as group}
				<div class="footer-link-col">
					<h4>{group.title}</h4>
					{#each group.links as link}
						<a href="#{link.toLowerCase().replace(/ /g, '-')}">{link}</a>
					{/each}
				</div>
			{/each}
		</div>
		<div class="footer-bottom">
			<span>&copy; 2026 WithOps. All rights reserved.</span>
			<div class="footer-bottom-links">
				<a href="#status">Status</a>
				<a href="#privacy">Privacy</a>
				<a href="#terms">Terms</a>
			</div>
		</div>
	</div>
</footer>

<style>
	/* ============================================
	   PROFESSIONAL DESIGN SYSTEM (MATTE ENGINEERING)
	   Dark-only landing page — unified with dashboard/organizations
	   ============================================ */
	:root {
		--font-sans: 'Inter', system-ui, -apple-system, sans-serif;
		--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
		--ease-premium: cubic-bezier(0.2, 0, 0, 1);

		/* Palette */
		--bg-app: #000000;
		--bg-surface: #020202;
		--bg-surface-alt: #050505;
		--border: rgba(255, 255, 255, 0.03);
		--border-focus: rgba(255, 255, 255, 0.08);
		--text-primary: #f8fafc;
		--text-secondary: #94a3b8;
		--text-muted: #475569;
		--accent: #00adef;
		--accent-soft: rgba(0, 173, 239, 0.05);
		--success: #10b981;
		--error: #ef4444;
		--warning: #f59e0b;
	}

	/* ===== GLOBAL RESET ===== */
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	:global(body) {
		font-family: var(--font-sans);
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
		background: var(--bg-app);
		color: var(--text-primary);
		scroll-behavior: smooth;
		position: relative;
	}

	.container {
		max-width: 1440px;
		margin: 0 auto;
		padding: 0 2rem;
	}
	.relative {
		position: relative;
	}

	/* ============================================
	   NAVBAR
	   ============================================ */
	.navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 1000;
		height: 64px;
		background: rgba(0, 0, 0, 0.85);
		backdrop-filter: blur(16px) saturate(180%);
		-webkit-backdrop-filter: blur(16px) saturate(180%);
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		transition: background 0.3s ease;
	}
	/* Cyan accent bar at very top of page */
	.navbar::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		background: linear-gradient(90deg, transparent, var(--accent), transparent);
		z-index: 10;
	}
	.nav-container {
		max-width: 1440px;
		margin: 0 auto;
		padding: 0 2rem;
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		cursor: pointer;
		text-decoration: none;
	}
	.nav-brand-icon {
		width: 28px;
		height: 28px;
	}
	.brand-icon {
		width: 28px;
		height: 28px;
	}
	.brand-name {
		font-weight: 700;
		font-size: 1rem;
		color: var(--text-primary);
		letter-spacing: -0.02em;
		font-family: var(--font-mono);
	}
	.nav-menu {
		display: flex;
		gap: 1.5rem;
		margin-left: 3rem;
		align-items: center;
	}
	.nav-link {
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
		padding: 0.5rem 0;
		position: relative;
	}
	.nav-link:hover {
		color: var(--text-primary);
	}
	.nav-link::after {
		content: '';
		position: absolute;
		bottom: -1px;
		left: 0;
		width: 0;
		height: 2px;
		background: var(--accent);
		transition: width 0.2s var(--ease-premium);
	}
	.nav-link:hover::after {
		width: 100%;
	}
	.nav-actions {
		display: flex;
		gap: 0.75rem;
		align-items: center;
	}
	.user-welcome {
		color: var(--text-secondary);
		font-size: 0.8125rem;
		margin-right: 0.5rem;
	}
	.nav-btn-secondary {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid rgba(255, 255, 255, 0.1);
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 600;
		padding: 0.5rem 1.25rem;
		border-radius: 8px;
		transition: all 0.2s var(--ease-premium);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.nav-btn-secondary:hover {
		color: var(--accent);
		border-color: var(--accent);
		background: rgba(0, 173, 239, 0.05);
		transform: translateY(-1px);
	}
	.nav-btn-primary {
		background: var(--accent);
		color: #fff;
		border: 1px solid var(--accent);
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.5rem 1.25rem;
		border-radius: 8px;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		transition: all 0.2s var(--ease-premium);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		box-shadow: 0 0 16px rgba(0, 173, 239, 0.2);
	}
	.nav-btn-primary:hover {
		background: #0095cc;
		box-shadow: 0 4px 20px rgba(0, 173, 239, 0.35);
		transform: translateY(-1px);
	}

	/* ============================================
	   HERO
	   ============================================ */
	.hero {
		position: relative;
		min-height: 100vh;
		overflow: hidden;
		padding: 7rem 0 5rem;
		display: flex;
		align-items: center;
		background: var(--bg-app);
	}
	/* 3D perspective grid floor — vanishing point depth */
	.hero::before {
		content: '';
		position: absolute;
		bottom: 0;
		left: -50%;
		width: 200%;
		height: 70%;
		background-image:
			linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
		background-size: 20px 20px;
		transform: perspective(500px) rotateX(65deg);
		transform-origin: center top;
		mask-image: linear-gradient(
			to top,
			rgba(0, 0, 0, 0.8) 0%,
			rgba(0, 0, 0, 0.3) 40%,
			transparent 75%
		);
		-webkit-mask-image: linear-gradient(
			to top,
			rgba(0, 0, 0, 0.8) 0%,
			rgba(0, 0, 0, 0.3) 40%,
			transparent 75%
		);
		pointer-events: none;
		z-index: 0;
	}
	/* Ambient accent glow — stronger cyan wash */
	.hero::after {
		content: '';
		position: absolute;
		top: -30%;
		left: 20%;
		width: 60%;
		height: 60%;
		background: radial-gradient(circle, rgba(0, 173, 239, 0.08) 0%, transparent 70%);
		pointer-events: none;
		z-index: 0;
		filter: blur(60px);
	}
	.hero-bg {
		position: absolute;
		inset: 0;
	}
	.hero-bg-base {
		position: absolute;
		inset: 0;
		background: transparent;
	}
	.hero-bg-grid {
		display: none;
	}

	/* Depth fog — atmospheric haze near the floor */
	.hero-depth-fog {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		height: 40%;
		background: linear-gradient(
			to top,
			rgba(0, 0, 0, 0.5) 0%,
			rgba(0, 0, 0, 0.15) 40%,
			transparent 100%
		);
		pointer-events: none;
		z-index: 0;
	}

	/* Vignette — cinematic edge darkening */
	.hero-vignette {
		position: absolute;
		inset: 0;
		background: radial-gradient(
			ellipse 70% 60% at 50% 45%,
			transparent 50%,
			rgba(0, 0, 0, 0.4) 100%
		);
		pointer-events: none;
		z-index: 1;
	}

	/* Floating depth particles */
	.hero-particles {
		position: absolute;
		inset: 0;
		pointer-events: none;
		z-index: 0;
		overflow: hidden;
	}
	.particle {
		position: absolute;
		border-radius: 50%;
		background: rgba(0, 173, 239, 0.15);
		filter: blur(1px);
		animation: particleFloat 20s ease-in-out infinite;
	}
	.p1 {
		width: 3px;
		height: 3px;
		top: 25%;
		left: 15%;
		opacity: 0.6;
		animation-duration: 18s;
	}
	.p2 {
		width: 2px;
		height: 2px;
		top: 40%;
		left: 75%;
		opacity: 0.4;
		animation-duration: 24s;
		animation-delay: -5s;
	}
	.p3 {
		width: 4px;
		height: 4px;
		top: 60%;
		left: 45%;
		opacity: 0.3;
		filter: blur(2px);
		animation-duration: 22s;
		animation-delay: -8s;
	}
	.p4 {
		width: 2px;
		height: 2px;
		top: 35%;
		left: 55%;
		opacity: 0.5;
		animation-duration: 26s;
		animation-delay: -12s;
	}
	.p5 {
		width: 3px;
		height: 3px;
		top: 70%;
		left: 25%;
		opacity: 0.25;
		filter: blur(2px);
		animation-duration: 20s;
		animation-delay: -3s;
	}
	@keyframes particleFloat {
		0%,
		100% {
			transform: translate(0, 0) scale(1);
			opacity: var(--p-opacity, 0.4);
		}
		25% {
			transform: translate(15px, -20px) scale(1.2);
			opacity: calc(var(--p-opacity, 0.4) * 1.3);
		}
		50% {
			transform: translate(-10px, -35px) scale(0.8);
			opacity: calc(var(--p-opacity, 0.4) * 0.7);
		}
		75% {
			transform: translate(20px, -15px) scale(1.1);
			opacity: var(--p-opacity, 0.4);
		}
	}

	.hero-container {
		position: relative;
		z-index: 2;
		max-width: 1440px;
		margin: 0 auto;
		padding: 0 2rem;
		display: grid;
		grid-template-columns: 4.5fr 7.5fr;
		gap: 3rem;
		align-items: center;
	}
	@media (min-width: 769px) {
		.hero-container {
			padding: 0 3rem;
		}
	}

	/* Hero Left */
	.hero-left {
		position: relative;
		z-index: 5;
	}
	.hero-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.625rem;
		background: rgba(0, 173, 239, 0.06);
		border: 1px solid rgba(0, 173, 239, 0.2);
		border-radius: 6px;
		padding: 0.5rem 1.125rem;
		margin-bottom: 2rem;
		box-shadow: 0 0 20px rgba(0, 173, 239, 0.08);
	}
	.badge-dot {
		width: 8px;
		height: 8px;
		background: var(--success);
		border-radius: 50%;
		animation: statusBlink 2s infinite;
		box-shadow:
			0 0 6px rgba(16, 185, 129, 0.5),
			0 0 12px rgba(16, 185, 129, 0.2);
	}
	.badge-text {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-secondary);
		font-weight: 600;
		letter-spacing: 0.05em;
		text-transform: uppercase;
	}

	.hero-title {
		font-size: clamp(2.5rem, 5vw, 3.75rem);
		font-weight: 800;
		color: var(--text-primary);
		line-height: 1.05;
		margin-bottom: 1.5rem;
		letter-spacing: -0.04em;
	}
	.hero-title-accent {
		background: linear-gradient(135deg, var(--accent) 0%, #3dc7f6 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		display: block;
	}
	.hero-description {
		font-size: 1rem;
		color: var(--text-secondary);
		line-height: 1.6;
		margin-bottom: 2.5rem;
		max-width: 480px;
	}
	.hero-buttons {
		display: flex;
		gap: 0.75rem;
		flex-wrap: wrap;
		margin-bottom: 3rem;
	}

	/* ===== BUTTONS (Matte Engineering System) ===== */
	.btn-primary {
		background: var(--text-primary);
		color: var(--bg-app);
		border: 1px solid var(--text-primary);
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: 0.8125rem;
		font-weight: 700;
		padding: 0.8125rem 1.75rem;
		border-radius: 8px;
		display: inline-flex;
		align-items: center;
		gap: 0.625rem;
		transition: all 0.2s var(--ease-premium);
		position: relative;
		overflow: hidden;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.btn-primary::before {
		display: none;
	}
	.btn-primary:hover {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
		transform: translateY(-2px);
		box-shadow: 0 8px 24px rgba(0, 173, 239, 0.25);
	}
	.btn-primary:active {
		transform: translateY(0);
		box-shadow: none;
	}
	.btn-secondary {
		background: transparent;
		color: var(--text-primary);
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: 0.8125rem;
		font-weight: 700;
		padding: 0.8125rem 1.75rem;
		border-radius: 8px;
		border: 1px solid rgba(255, 255, 255, 0.12);
		display: inline-flex;
		align-items: center;
		gap: 0.625rem;
		transition: all 0.2s var(--ease-premium);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.btn-secondary:hover {
		background: rgba(255, 255, 255, 0.06);
		border-color: var(--accent);
		color: var(--accent);
		transform: translateY(-2px);
		box-shadow: 0 8px 24px rgba(0, 173, 239, 0.1);
	}
	.btn-secondary:active {
		transform: translateY(0);
	}
	.btn-sm {
		padding: 0.5625rem 1.125rem;
		font-size: 0.8125rem;
	}

	/* Hero Stats */
	.hero-stats {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 2rem;
		padding-top: 2rem;
		margin-top: 2rem;
		border-top: 1px solid var(--border);
	}
	.hero-stat {
		display: flex;
		flex-direction: column;
		padding-left: 1rem;
		border-left: 2px solid rgba(0, 173, 239, 0.2);
	}
	.stat-value {
		display: block;
		font-family: var(--font-mono);
		font-size: 1.75rem;
		font-weight: 800;
		color: var(--accent);
		margin-bottom: 0.25rem;
		letter-spacing: -0.03em;
	}
	.stat-label {
		display: block;
		font-size: 0.65rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		font-family: var(--font-mono);
	}

	/* ============================================
	   YAML CODE PANEL
	   ============================================ */
	.hero-right {
		position: relative;
		z-index: 3;
		perspective: 2000px;
	}
	.yaml-panel-container {
		position: relative;
		transform: rotateY(-18deg) rotateX(8deg) rotateZ(2deg);
		transform-style: preserve-3d;
		transition: transform 0.8s var(--ease-premium);
	}
	.hero-right:hover .yaml-panel-container {
		transform: rotateY(-8deg) rotateX(4deg) rotateZ(0deg);
	}
	.yaml-panel {
		background: #0d0f14;
		border: 1px solid rgba(255, 255, 255, 0.08);
		border-radius: 12px;
		overflow: hidden;
		box-shadow:
			-20px 20px 60px rgba(0, 0, 0, 0.5),
			-5px 5px 20px rgba(59, 130, 246, 0.1);
		position: relative;
		backface-visibility: hidden;
	}
	.yaml-panel::before {
		content: '';
		position: absolute;
		top: -1px;
		left: -1px;
		right: -1px;
		height: 3px;
		background: #3b82f6;
		border-radius: 12px 12px 0 0;
		z-index: 10;
	}
	.yaml-panel-header {
		display: flex;
		align-items: center;
		padding: 0.625rem 1rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.05);
		background: #11141d;
		gap: 1.5rem;
	}
	.yaml-breadcrumbs {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-family: 'Inter', sans-serif;
		font-size: 0.7rem;
		color: #475569;
	}
	.breadcrumb-item.active {
		color: #94a3b8;
	}
	.breadcrumb-separator {
		color: #334155;
	}
	.yaml-dots {
		display: flex;
		gap: 6px;
		flex-shrink: 0;
	}
	.yaml-actions-ui {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.yaml-copy-btn {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: #64748b;
		font-size: 0.65rem;
		padding: 0.25rem 0.625rem;
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.2s;
	}
	.yaml-copy-btn:hover {
		background: rgba(255, 255, 255, 0.08);
		color: #f1f5f9;
		border-color: rgba(255, 255, 255, 0.2);
	}
	.yaml-tabs {
		display: flex;
		gap: 0.25rem;
	}
	.yaml-tab {
		color: #475569;
		font-size: 0.65rem;
		font-weight: 500;
		padding: 0.2rem 0.6rem;
		border-radius: 4px;
		cursor: default;
		transition: all 0.2s;
	}
	.yaml-tab-active {
		color: #ffffff;
		background: rgba(255, 255, 255, 0.05);
	}
	.dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}
	.dot-red {
		background: #eb5757;
	}
	.dot-yellow {
		background: #f2c94c;
	}
	.dot-green {
		background: #27ae60;
	}

	.yaml-panel-title {
		color: #475569;
		font-size: 0.75rem;
		font-family: 'Consolas', 'SF Mono', 'Fira Code', monospace;
		letter-spacing: 0.02em;
	}
	.yaml-panel-body {
		display: flex;
		max-height: 520px;
		overflow-y: hidden;
		padding: 1rem 0;
		background: #0d0f14;
	}
	.yaml-panel-body::-webkit-scrollbar {
		display: none;
	}
	.yaml-line-numbers {
		display: flex;
		flex-direction: column;
		padding: 1rem 0;
		padding-left: 1rem;
		padding-right: 0.75rem;
		border-right: 1px solid rgba(255, 255, 255, 0.04);
		user-select: none;
		flex-shrink: 0;
		min-width: 32px;
		text-align: right;
	}
	.yaml-line-numbers span {
		font-family: 'Consolas', 'SF Mono', 'Fira Code', monospace;
		font-size: 0.7rem;
		line-height: 1.65;
		color: #334155;
		height: calc(0.75rem * 1.65);
	}
	.yaml-pre {
		margin: 0;
		padding: 1rem 1rem;
		font-family: 'Consolas', 'SF Mono', 'Fira Code', monospace;
		font-size: 0.75rem;
		line-height: 1.65;
		white-space: pre-wrap;
		word-wrap: break-word;
		color: #cbd5e1;
		user-select: none;
		background: transparent;
		flex: 1;
		min-width: 0;
	}
	.yaml-code {
		font-family: inherit;
		font-size: inherit;
	}
	.yaml-code span {
		font-family: inherit;
	}
	.cursor {
		display: inline-block;
		width: 7px;
		height: 15px;
		background: #f9fafb;
		margin-left: 1px;
		vertical-align: text-bottom;
		animation: blink 1s infinite;
	}
	/* Scanning Beam */
	.yaml-panel-body::after {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 120px;
		background: linear-gradient(to bottom, transparent, rgba(0, 173, 239, 0.03), transparent);
		animation: scanLine 8s linear infinite;
		pointer-events: none;
		z-index: 10;
	}
	@keyframes scanLine {
		0% {
			transform: translateY(-100%);
		}
		100% {
			transform: translateY(500px);
		}
	}
	@keyframes blink {
		0%,
		100% {
			opacity: 1;
			box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
		}
		51% {
			opacity: 0;
		}
	}
	.yaml-status-bar {
		display: flex;
		align-items: center;
		gap: 1.25rem;
		padding: 0.375rem 1rem;
		border-top: 1px solid rgba(255, 255, 255, 0.04);
		background: rgba(0, 0, 0, 0.2);
		font-family: 'Consolas', 'SF Mono', 'Fira Code', monospace;
		font-size: 0.65rem;
		color: #475569;
	}

	/* Floating Annotations */
	.yaml-annotation {
		position: absolute;
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.3rem 0.625rem;
		border-radius: 6px;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		color: var(--success);
		background: rgba(16, 185, 129, 0.08);
		border: 1px solid rgba(16, 185, 129, 0.15);
		pointer-events: none;
		z-index: 5;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.yaml-annotation-top {
		top: 30%;
		right: -14px;
		transform: translateX(50%);
	}
	.yaml-annotation-bottom {
		bottom: 20%;
		right: -14px;
		transform: translateX(50%);
		color: var(--warning);
		background: rgba(245, 158, 11, 0.08);
		border-color: rgba(245, 158, 11, 0.15);
	}
	.floating-badge {
		position: absolute;
		top: -12px;
		right: -12px;
		background: var(--bg-surface-alt);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.5rem 0.75rem;
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	/* ============================================
	   TRUST SECTION
	   ============================================ */
	.trust-section {
		padding: 3.5rem 0;
		background: var(--bg-app);
		border-top: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
		position: relative;
	}
	.trust-section::before,
	.trust-section::after {
		display: none;
	}
	.trust-label {
		text-align: center;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.15em;
		color: var(--text-muted);
		margin-bottom: 1.5rem;
		font-weight: 600;
	}
	.trust-logos {
		display: grid;
		grid-template-columns: repeat(6, 1fr);
		gap: 2rem;
		align-items: center;
		justify-items: center;
	}
	.trust-logo {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		opacity: 0.4;
		transition: opacity 0.2s var(--ease-premium);
		cursor: default;
	}
	.trust-logo:hover {
		opacity: 1;
	}
	.trust-logo-box {
		width: 48px;
		height: 48px;
		border-radius: 12px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s var(--ease-premium);
	}
	.trust-logo:hover .trust-logo-box {
		border-color: var(--border-focus);
		transform: translateY(-2px);
	}
	.trust-logo-name {
		color: var(--text-muted);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	/* ============================================
	   PROBLEM SECTION
	   ============================================ */
	.problem-section {
		padding: 10rem 0 8rem;
		position: relative;
		overflow: hidden;
		background: var(--bg-app);
	}
	/* Subtle grid backdrop for problem section */
	.problem-section::before {
		content: '';
		position: absolute;
		inset: 0;
		background-image:
			linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
		background-size: 40px 40px;
		mask-image: radial-gradient(circle at 30% 50%, black 10%, transparent 60%);
		pointer-events: none;
		z-index: 0;
	}
	.problem-bg-grid {
		display: none;
	}

	/* Section Header (shared across sections) */
	.section-header {
		text-align: center;
		margin-bottom: 4rem;
		position: relative;
		z-index: 1;
	}
	.section-overline {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.15em;
		color: var(--accent);
		font-weight: 700;
		margin-bottom: 0.75rem;
	}
	.section-overline::before {
		content: '\25B8';
		margin-right: 0.5rem;
		vertical-align: middle;
		font-size: 0.7rem;
	}
	.section-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		border-radius: 6px;
		padding: 0.375rem 0.75rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		margin-bottom: 1.5rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.section-badge-red {
		background: rgba(239, 68, 68, 0.05);
		border: 1px solid rgba(239, 68, 68, 0.1);
		color: var(--error);
	}
	.section-badge-blue {
		background: var(--accent-soft);
		border: 1px solid rgba(0, 173, 239, 0.1);
		color: var(--accent);
	}
	.section-title {
		font-size: clamp(1.75rem, 3.5vw, 2.75rem);
		font-weight: 800;
		color: var(--text-primary);
		margin-bottom: 1rem;
		line-height: 1.15;
		letter-spacing: -0.04em;
	}
	.section-subtitle {
		font-size: 1rem;
		color: var(--text-secondary);
		max-width: 600px;
		margin: 0 auto;
		line-height: 1.6;
	}

	/* Problem Grid */
	.problem-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1.5rem;
		margin-top: 3rem;
		position: relative;
		z-index: 1;
	}
	.problem-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2rem;
		position: relative;
		overflow: hidden;
		transition: all 0.2s var(--ease-premium);
		display: flex;
		flex-direction: column;
		border-left: 2px solid rgba(239, 68, 68, 0.3);
	}
	.problem-card:hover {
		border-color: var(--border-focus);
		border-left-color: var(--error);
		transform: translateY(-4px);
		box-shadow:
			0 16px 32px rgba(0, 0, 0, 0.4),
			0 0 0 1px rgba(239, 68, 68, 0.1);
	}
	.problem-header-row {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1.5rem;
	}
	.problem-badge {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		padding: 0.25rem 0.6rem;
		border-radius: 6px;
		background: rgba(239, 68, 68, 0.05);
		color: var(--error);
		border: 1px solid rgba(239, 68, 68, 0.1);
		letter-spacing: 0.05em;
		text-transform: uppercase;
	}
	.badge-amber {
		background: rgba(245, 158, 11, 0.05);
		color: var(--warning);
		border-color: rgba(245, 158, 11, 0.1);
	}
	.problem-icon {
		width: 48px;
		height: 48px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: transform 0.2s var(--ease-premium);
	}
	.problem-icon-red {
		background: rgba(239, 68, 68, 0.05);
		color: var(--error);
		border: 1px solid rgba(239, 68, 68, 0.08);
	}
	.problem-icon-amber {
		background: rgba(245, 158, 11, 0.05);
		color: var(--warning);
		border: 1px solid rgba(245, 158, 11, 0.08);
	}
	.problem-card h3 {
		color: var(--text-primary);
		font-size: 1.125rem;
		font-weight: 700;
		margin-bottom: 0.75rem;
		letter-spacing: -0.01em;
	}
	.problem-card p {
		color: var(--text-secondary);
		font-size: 0.875rem;
		line-height: 1.6;
		margin-bottom: 2rem;
		flex-grow: 1;
	}

	/* Diagnostic Data Box */
	.problem-data-box {
		background: var(--bg-app);
		border: 1px solid var(--border);
		border-left: 2px solid rgba(239, 68, 68, 0.25);
		border-radius: 8px;
		padding: 1.25rem;
		font-family: var(--font-mono);
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.data-row {
		display: flex;
		justify-content: space-between;
		font-size: 0.6rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.data-status {
		color: var(--error);
		font-weight: 700;
	}
	.status-null {
		color: var(--text-muted);
	}
	.status-fail {
		color: var(--error);
		text-decoration: underline;
	}
	.maturity-bar-container {
		display: flex;
		gap: 4px;
		height: 3px;
		margin-bottom: 0.5rem;
	}
	.m-bar {
		flex: 1;
		background: var(--border-focus);
		border-radius: 2px;
	}
	.m-bar.m-active {
		background: var(--error);
		opacity: 0.6;
	}
	.maturity-label {
		font-size: 0.55rem;
		color: var(--text-muted);
		text-align: right;
		font-weight: 700;
		letter-spacing: 0.05em;
	}

	/* ============================================
	   SOLUTION SECTION
	   ============================================ */
	.solution-section {
		padding: 8rem 0;
		background: var(--bg-surface);
		position: relative;
	}
	.solution-section::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 1px;
		background: linear-gradient(90deg, transparent, var(--border-focus), transparent);
	}
	.solution-list {
		display: flex;
		flex-direction: column;
		gap: 6rem;
	}
	.solution-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 3rem;
		align-items: center;
	}
	.solution-row-reverse .solution-text {
		order: 2;
	}
	.solution-row-reverse .solution-visual {
		order: 1;
	}

	.solution-icon-box {
		width: 48px;
		height: 48px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 1.5rem;
		transition: transform 0.2s var(--ease-premium);
	}
	.solution-icon-box:hover {
		transform: scale(1.05);
	}
	.solution-gradient-blue-cyan {
		background: linear-gradient(135deg, var(--accent) 0%, #0082b4 100%);
	}
	.solution-gradient-green-cyan {
		background: linear-gradient(135deg, var(--success) 0%, #059669 100%);
	}
	.solution-gradient-amber-red {
		background: linear-gradient(135deg, var(--warning) 0%, #d97706 100%);
	}
	.solution-text h3 {
		color: var(--text-primary);
		font-size: 1.5rem;
		font-weight: 700;
		margin-bottom: 0.75rem;
		letter-spacing: -0.02em;
	}
	.solution-text p {
		color: var(--text-secondary);
		font-size: 0.9375rem;
		line-height: 1.75;
		margin-bottom: 1.5rem;
	}
	.check-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
	}
	.check-list li {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		color: var(--text-secondary);
		font-size: 0.875rem;
	}
	.check-list li::before {
		display: none;
	}
	.check-list li svg {
		flex-shrink: 0;
		margin-top: 2px;
	}
	.solution-visual {
		position: relative;
	}
	.solution-visual-glow {
		display: none;
	}
	.solution-mockup {
		position: relative;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
		transition: all 0.3s var(--ease-premium);
	}
	.solution-mockup::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		background: linear-gradient(90deg, var(--accent), transparent);
		opacity: 0;
		transition: opacity 0.3s;
		z-index: 5;
	}
	.solution-mockup:hover {
		border-color: var(--border-focus);
		transform: translateY(-4px);
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
	}
	.solution-mockup:hover::before {
		opacity: 1;
	}
	.mockup-chrome {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface-alt);
	}
	.mockup-dots {
		display: flex;
		gap: 6px;
	}
	.mockup-url {
		flex: 1;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 0.25rem 0.75rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.02em;
	}
	.mockup-body {
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.mockup-line {
		height: 8px;
		border-radius: 4px;
	}
	.mockup-body.technical-view {
		padding: 1.5rem;
		background: var(--bg-app);
		font-family: var(--font-mono);
	}

	/* Technical Audit Log */
	.audit-log {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.log-header {
		font-size: 0.6rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		border-bottom: 1px solid var(--border);
		padding-bottom: 0.5rem;
		margin-bottom: 0.25rem;
		text-transform: uppercase;
	}
	.log-content {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.log-entry {
		font-size: 0.65rem;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
	}
	.log-entry .timestamp {
		color: var(--text-muted);
		margin-right: 0.5rem;
	}
	.log-entry .action {
		color: var(--accent);
		font-weight: 700;
	}
	.log-entry.info .tool {
		color: var(--text-primary);
	}
	.log-entry.info .res {
		color: var(--success);
	}
	.log-entry.warn .tool {
		color: var(--error);
	}
	.log-entry.warn .res {
		color: var(--error);
		font-weight: 700;
	}
	.log-cursor {
		width: 6px;
		height: 12px;
		background: var(--accent);
		animation: cursorBlink 1s step-end infinite;
		margin-top: 0.25rem;
	}

	/* Maturity Matrix */
	.maturity-matrix {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}
	.matrix-grid {
		display: grid;
		grid-template-columns: repeat(10, 1fr);
		gap: 4px;
	}
	.matrix-cell {
		aspect-ratio: 1;
		background: var(--border-focus);
		border-radius: 2px;
	}
	.matrix-cell.cell-active {
		background: var(--success);
		opacity: 0.4;
	}
	.matrix-stats {
		display: flex;
		gap: 2rem;
		border-top: 1px solid var(--border);
		padding-top: 1rem;
	}
	.stat-group .stat-label {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		color: var(--text-muted);
		font-weight: 700;
		margin-bottom: 0.25rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.stat-group .stat-val {
		font-family: var(--font-mono);
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--text-primary);
	}
	.stat-group .val-active {
		color: var(--success);
	}

	/* Architecture Blueprint */
	.blueprint-view {
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.blueprint-canvas {
		width: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		position: relative;
	}
	.bp-box {
		border: 1px solid var(--border-focus);
		padding: 0.5rem 1rem;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text-secondary);
		background: var(--bg-surface);
		width: 140px;
		text-align: center;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.bp-box.bp-active {
		border-color: var(--accent);
		color: var(--accent);
		background: var(--accent-soft);
	}
	.bp-line {
		width: 1px;
		height: 12px;
		background: var(--border-focus);
	}
	.bp-label {
		position: absolute;
		font-family: var(--font-mono);
		font-size: 0.45rem;
		color: var(--text-muted);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}
	.bp-label.top-right {
		top: 0;
		right: 0;
	}
	.bp-label.bottom-left {
		bottom: 0;
		left: 0;
	}

	/* ============================================
	   HOW IT WORKS
	   ============================================ */
	.how-section {
		padding: 10rem 0;
		position: relative;
		overflow: hidden;
		background: var(--bg-surface);
		border-top: 1px solid var(--border);
	}
	/* Subtle vertical accent line */
	.how-section::before {
		content: '';
		position: absolute;
		top: 0;
		left: 50%;
		transform: translateX(-50%);
		width: 1px;
		height: 150px;
		background: linear-gradient(to bottom, var(--accent), transparent);
	}
	/* Grid backdrop — more visible */
	.how-section::after {
		content: '';
		position: absolute;
		inset: 0;
		background-image:
			linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
		background-size: 40px 40px;
		mask-image: radial-gradient(circle at 50% 100%, black, transparent 70%);
		pointer-events: none;
		z-index: 0;
	}
	.how-bg-grid {
		display: none;
	}
	.steps-wrapper {
		position: relative;
		margin-top: 4rem;
		z-index: 1;
	}

	/* Connecting line */
	.steps-connector {
		display: none;
		position: absolute;
		top: 28px;
		left: 8%;
		right: 8%;
		height: 2px;
		z-index: 1;
	}
	@media (min-width: 769px) {
		.steps-connector {
			display: block;
		}
	}
	.steps-connector-track {
		position: absolute;
		inset: 0;
		background: var(--border);
		border-radius: 2px;
	}
	.steps-connector-progress {
		position: absolute;
		top: 0;
		left: 0;
		height: 100%;
		width: 0;
		background: linear-gradient(90deg, var(--accent), #3dc7f6, #0082b4);
		border-radius: 2px;
		transition: none;
	}
	.steps-connector-progress.revealed {
		width: 100% !important;
		transition: width 1.8s cubic-bezier(0.16, 1, 0.3, 1) !important;
	}
	.steps-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1.5rem;
		position: relative;
		z-index: 2;
	}

	/* Step cards */
	.step-card {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2rem 1.5rem;
		transition: all 0.3s var(--ease-premium);
		position: relative;
	}
	.step-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		background: transparent;
		transition: background 0.3s var(--ease-premium);
		border-radius: 12px 12px 0 0;
	}
	.step-card::after {
		content: '';
		position: absolute;
		bottom: 0;
		left: 1.5rem;
		right: 1.5rem;
		height: 0;
		background: transparent;
		transition: all 0.3s var(--ease-premium);
		border-radius: 2px;
	}
	.step-card:hover {
		border-color: var(--border-focus);
		transform: translateY(-6px);
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
	}
	.step-card:hover::before {
		background: var(--accent);
	}
	.step-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1.25rem;
	}
	.step-number {
		font-family: var(--font-mono);
		font-size: 2.5rem;
		font-weight: 800;
		letter-spacing: -0.04em;
		color: var(--border-focus);
		line-height: 1;
	}
	.step-number-purple {
		color: rgba(167, 139, 250, 0.25);
	}
	.step-number-blue {
		color: rgba(0, 173, 239, 0.25);
	}
	.step-number-amber {
		color: rgba(245, 158, 11, 0.25);
	}
	.step-number-green {
		color: rgba(16, 185, 129, 0.25);
	}
	.step-icon {
		width: 40px;
		height: 40px;
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.step-icon-purple {
		background: rgba(167, 139, 250, 0.08);
		color: #a78bfa;
	}
	.step-icon-blue {
		background: rgba(0, 173, 239, 0.08);
		color: var(--accent);
	}
	.step-icon-amber {
		background: rgba(245, 158, 11, 0.08);
		color: var(--warning);
	}
	.step-icon-green {
		background: rgba(16, 185, 129, 0.08);
		color: var(--success);
	}
	.step-card h4 {
		color: var(--text-primary);
		font-size: 1rem;
		font-weight: 700;
		margin-bottom: 0.5rem;
		letter-spacing: -0.01em;
	}
	.step-card p {
		color: var(--text-muted);
		font-size: 0.8125rem;
		line-height: 1.6;
		margin-bottom: 1.5rem;
	}

	/* Technical Step Visuals */
	.step-visual {
		background: var(--bg-app);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 1rem;
		font-family: var(--font-mono);
		height: 100px;
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 0.4rem;
		overflow: hidden;
	}
	.code-line {
		font-size: 0.55rem;
		color: #a78bfa;
		white-space: nowrap;
		letter-spacing: 0.02em;
	}
	.scan-tree {
		font-size: 0.55rem;
		color: var(--accent);
	}
	.tree-node.depth-1 {
		padding-left: 1rem;
		color: var(--text-secondary);
	}
	.eval-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 4px;
		width: 40px;
	}
	.grid-dot {
		width: 4px;
		height: 4px;
		background: var(--border-focus);
		border-radius: 50%;
	}
	.grid-dot.active {
		background: var(--warning);
		box-shadow: 0 0 8px var(--warning);
	}
	.eval-text {
		font-size: 0.65rem;
		color: var(--warning);
		font-weight: 700;
		margin-top: 0.5rem;
	}
	.report-bar {
		height: 3px;
		background: rgba(16, 185, 129, 0.15);
		border-radius: 2px;
		width: 100%;
	}
	.report-bar.w-70 {
		width: 70%;
	}
	.report-bar.w-40 {
		width: 40%;
	}
	.step-icon-ring,
	.step-icon-pulse,
	.step-num,
	.step-status {
		display: none;
	}

	/* ============================================
	   WHY CHOOSE WITHOPS (BENTO GRID)
	   ============================================ */
	.why-section {
		padding: 8rem 0;
		background: var(--bg-app);
		position: relative;
		border-top: 1px solid var(--border);
	}
	.bento-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1.5rem;
		margin-top: 3rem;
	}
	.bento-item {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2rem;
		position: relative;
		overflow: hidden;
		transition: all 0.3s var(--ease-premium);
		display: flex;
		flex-direction: column;
	}
	/* Subtle gradient shimmer on bento hover */
	.bento-item::after {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		background: linear-gradient(90deg, transparent, var(--accent), transparent);
		opacity: 0;
		transition: opacity 0.3s;
	}
	.bento-item:hover {
		border-color: rgba(0, 173, 239, 0.15);
		transform: translateY(-6px);
		box-shadow:
			0 24px 48px rgba(0, 0, 0, 0.4),
			0 0 40px rgba(0, 173, 239, 0.05);
	}
	.bento-item:hover::after {
		opacity: 1;
	}
	.bento-large {
		grid-column: span 2;
	}
	.bento-medium {
		grid-column: span 1;
	}
	.bento-wide {
		grid-column: span 3;
	}
	.bento-tag {
		display: inline-block;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--accent);
		margin-bottom: 1rem;
		background: rgba(0, 173, 239, 0.06);
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		border: 1px solid rgba(0, 173, 239, 0.12);
	}
	.bento-tag::before {
		content: '\25CF';
		margin-right: 0.5rem;
		font-size: 0.4rem;
		vertical-align: middle;
	}
	.bento-content h3 {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 0.75rem;
		letter-spacing: -0.02em;
	}
	.bento-content p {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.6;
		max-width: 500px;
	}
	.bento-content-row {
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		height: 100%;
	}

	/* Visual Elements */
	.bento-visual {
		margin-top: auto;
		padding-top: 2rem;
		height: 100px;
		display: flex;
		align-items: flex-end;
	}
	.ai-signal-lines {
		display: flex;
		gap: 0.5rem;
		align-items: flex-end;
	}
	.ai-line {
		width: 3px;
		background: linear-gradient(to top, var(--accent), transparent);
		border-radius: 2px;
		animation: aiPulse var(--d, 2s) ease-in-out infinite;
	}
	.ai-line:nth-child(1) {
		height: 40px;
		--d: 1.5s;
	}
	.ai-line:nth-child(2) {
		height: 70px;
		--d: 2.2s;
	}
	.ai-line:nth-child(3) {
		height: 50px;
		--d: 1.8s;
	}
	.ai-line:nth-child(4) {
		height: 90px;
		--d: 2.5s;
	}
	.ai-line:nth-child(5) {
		height: 60px;
		--d: 2s;
	}
	@keyframes aiPulse {
		0%,
		100% {
			opacity: 0.3;
			transform: scaleY(0.8);
		}
		50% {
			opacity: 1;
			transform: scaleY(1.2);
		}
	}
	.maturity-meter {
		margin-top: auto;
		padding-top: 2rem;
	}
	.meter-bar {
		height: 4px;
		background: var(--border-focus);
		border-radius: 2px;
		position: relative;
		overflow: hidden;
	}
	.meter-bar::after {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		height: 100%;
		width: 75%;
		background: linear-gradient(90deg, var(--accent), #3dc7f6);
	}
	.meter-value {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--accent);
		font-weight: 700;
		margin-top: 0.5rem;
	}
	.live-indicator-tray {
		margin-top: auto;
		padding-top: 2rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.pulse-dot {
		width: 6px;
		height: 6px;
		background: var(--success);
		border-radius: 50%;
		animation: statusBlink 2s infinite;
	}
	.live-text {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text-secondary);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}
	@keyframes statusBlink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.3;
		}
	}
	.github-visual-mini {
		opacity: 0.06;
		transform: rotate(15deg) scale(1.5);
		color: var(--text-primary);
	}

	/* ============================================
	   FINAL CTA
	   ============================================ */
	.final-cta {
		padding: 10rem 0;
		position: relative;
		overflow: hidden;
		background: var(--bg-surface);
	}
	/* Ambient glow — stronger cyan */
	.final-cta::before {
		content: '';
		position: absolute;
		inset: 0;
		background: radial-gradient(circle at 50% 40%, rgba(0, 173, 239, 0.06) 0%, transparent 60%);
		pointer-events: none;
	}
	/* Grid backdrop — more visible */
	.final-cta::after {
		content: '';
		position: absolute;
		inset: 0;
		background-image:
			linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
		background-size: 40px 40px;
		mask-image: radial-gradient(circle at 50% 50%, black, transparent 70%);
		pointer-events: none;
		z-index: 0;
	}
	.final-cta-bg,
	.final-cta-grid-bg {
		display: none;
	}
	.cta-orb {
		position: absolute;
		border-radius: 50%;
		filter: blur(50px);
		pointer-events: none;
	}
	.cta-orb-1 {
		width: 300px;
		height: 300px;
		top: 10%;
		left: 5%;
		background: radial-gradient(circle, rgba(0, 173, 239, 0.08) 0%, transparent 70%);
		animation: orbFloat1 16s ease-in-out infinite;
	}
	.cta-orb-2 {
		width: 250px;
		height: 250px;
		bottom: 10%;
		right: 5%;
		background: radial-gradient(circle, rgba(0, 173, 239, 0.05) 0%, transparent 70%);
		animation: orbFloat2 20s ease-in-out infinite;
	}
	@keyframes orbFloat1 {
		0%,
		100% {
			transform: translate(0, 0) scale(1);
		}
		33% {
			transform: translate(30px, -20px) scale(1.05);
		}
		66% {
			transform: translate(-15px, 15px) scale(0.95);
		}
	}
	@keyframes orbFloat2 {
		0%,
		100% {
			transform: translate(0, 0) scale(1);
		}
		33% {
			transform: translate(-25px, 20px) scale(1.08);
		}
		66% {
			transform: translate(20px, -10px) scale(0.97);
		}
	}
	.final-cta-inner {
		text-align: center;
		z-index: 2;
		position: relative;
	}
	.final-cta-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.75rem;
		background: var(--accent-soft);
		border: 1px solid rgba(0, 173, 239, 0.1);
		border-radius: 6px;
		padding: 0.375rem 0.75rem;
		margin-bottom: 2rem;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--accent);
	}
	.final-cta h2 {
		font-size: clamp(2rem, 4vw, 2.75rem);
		font-weight: 800;
		color: var(--text-primary);
		line-height: 1.2;
		margin-bottom: 1.25rem;
		letter-spacing: -0.04em;
	}
	.final-cta-accent {
		background: linear-gradient(135deg, var(--accent), #3dc7f6);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}
	.final-cta p {
		font-size: 1rem;
		color: var(--text-secondary);
		margin-bottom: 2rem;
		max-width: 560px;
		margin-left: auto;
		margin-right: auto;
		line-height: 1.6;
	}
	.final-cta-buttons {
		justify-content: center;
		margin-bottom: 2.5rem;
	}
	.final-cta .btn-secondary {
		color: var(--text-primary);
		border-color: rgba(255, 255, 255, 0.1);
		background: transparent;
	}
	.final-cta .btn-secondary:hover {
		color: var(--accent);
		background: rgba(0, 173, 239, 0.05);
		border-color: var(--accent);
	}
	.trust-indicators {
		display: flex;
		justify-content: center;
		gap: 2rem;
		flex-wrap: wrap;
	}
	.trust-check {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--text-secondary);
		font-size: 0.8125rem;
	}
	.trust-check-icon {
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: rgba(16, 185, 129, 0.1);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	/* ============================================
	   FOOTER
	   ============================================ */
	.footer {
		background: var(--bg-surface);
		border-top: 1px solid var(--border);
		padding: 3.5rem 0 2rem;
		position: relative;
	}
	.footer::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		background: linear-gradient(90deg, transparent, var(--accent), transparent);
	}
	.footer-grid {
		display: grid;
		grid-template-columns: 1.5fr repeat(4, 1fr);
		gap: 3rem;
		margin-bottom: 3rem;
	}
	.footer-brand {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.footer-logo {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.footer-brand-name {
		color: var(--text-primary) !important;
	}
	.footer-desc {
		color: var(--text-secondary);
		font-size: 0.875rem;
		line-height: 1.6;
		max-width: 280px;
	}
	.footer-social {
		display: flex;
		gap: 0.5rem;
	}
	.social-link {
		width: 36px;
		height: 36px;
		border-radius: 8px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-muted);
		text-decoration: none;
		transition: all 0.15s;
	}
	.social-link:hover {
		border-color: var(--border-focus);
		color: var(--text-primary);
		transform: translateY(-2px);
	}
	.footer-link-col h4 {
		color: var(--text-primary);
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		margin-bottom: 1rem;
	}
	.footer-link-col a {
		display: block;
		color: var(--text-secondary);
		text-decoration: none;
		font-size: 0.8125rem;
		margin-bottom: 0.625rem;
		transition: color 0.15s;
	}
	.footer-link-col a:hover {
		color: var(--text-primary);
	}
	.footer-bottom {
		padding-top: 2rem;
		border-top: 1px solid var(--border);
		display: flex;
		justify-content: space-between;
		align-items: center;
		color: var(--text-muted);
		font-size: 0.75rem;
	}
	.footer-bottom-links {
		display: flex;
		gap: 1.5rem;
	}
	.footer-bottom-links a {
		color: var(--text-muted);
		text-decoration: none;
		transition: color 0.15s;
	}
	.footer-bottom-links a:hover {
		color: var(--text-primary);
	}

	/* ============================================
	   RESPONSIVE
	   ============================================ */
	@media (max-width: 1024px) {
		.hero-container {
			grid-template-columns: 1fr;
			gap: 4rem;
			text-align: center;
		}
		.hero-left {
			display: flex;
			flex-direction: column;
			align-items: center;
		}
		.hero-description {
			max-width: 100%;
		}
		.hero-buttons {
			justify-content: center;
		}
		.hero-right {
			max-width: 100%;
			width: 100%;
		}
		.yaml-panel-container {
			transform: none !important;
		}
		.yaml-annotation {
			display: none;
		}
		.solution-row,
		.solution-row-reverse {
			grid-template-columns: 1fr;
			gap: 2rem;
		}
		.solution-row-reverse .solution-text {
			order: 1;
		}
		.solution-row-reverse .solution-visual {
			order: 2;
		}
		.bento-grid {
			grid-template-columns: 1fr;
		}
		.bento-large,
		.bento-medium,
		.bento-wide {
			grid-column: span 1;
		}
	}

	@media (max-width: 768px) {
		.nav-menu {
			display: none;
		}
		.hero {
			padding: 5rem 0 3rem;
		}
		.hero-title {
			font-size: clamp(2rem, 8vw, 3rem);
		}
		.hero-stats {
			grid-template-columns: repeat(3, 1fr);
			gap: 1rem;
		}
		.yaml-panel-header {
			gap: 0.5rem;
			padding: 0.5rem;
		}
		.yaml-breadcrumbs,
		.yaml-tabs {
			display: none;
		}
		.yaml-panel-body {
			max-height: 400px;
		}
		.yaml-pre {
			font-size: 0.7rem;
			padding: 1rem 0.5rem;
		}
		.problem-grid {
			grid-template-columns: 1fr;
		}
		.steps-grid {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}
		.trust-logos {
			grid-template-columns: repeat(3, 1fr);
			gap: 1.5rem;
		}
		.footer-grid {
			grid-template-columns: 1fr 1fr;
			gap: 2.5rem;
		}
		.footer-bottom {
			flex-direction: column;
			text-align: center;
			gap: 1.5rem;
		}
	}

	@media (max-width: 480px) {
		.hero-buttons {
			width: 100%;
		}
		.btn-primary,
		.btn-secondary {
			width: 100%;
			justify-content: center;
		}
		.hero-stats {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}
		.yaml-line-numbers {
			display: none;
		}
		.yaml-pre {
			padding-left: 1rem;
		}
		.trust-logos {
			grid-template-columns: repeat(2, 1fr);
		}
		.footer-grid {
			grid-template-columns: 1fr;
		}
		.final-cta-buttons {
			flex-direction: column;
			gap: 1rem;
		}
		.final-cta-buttons .btn-primary,
		.final-cta-buttons .btn-secondary {
			width: 100%;
		}
	}

	/* ============================================
	   SCROLL REVEAL ANIMATIONS
	   ============================================ */
	.reveal {
		opacity: 0;
		filter: blur(8px);
		transition:
			opacity 1s var(--ease-premium),
			filter 1s var(--ease-premium),
			transform 1s var(--ease-premium);
		will-change: opacity, transform, filter;
	}
	.reveal-up {
		transform: translateY(24px);
	}
	.reveal-down {
		transform: translateY(-24px);
	}
	.reveal-left {
		transform: translateX(-24px);
	}
	.reveal-right {
		transform: translateX(24px);
	}
	.reveal-scale {
		transform: scale(0.96);
	}
	.reveal-fade {
		transform: none;
	}
	.revealed {
		opacity: 1 !important;
		transform: none !important;
		filter: blur(0) !important;
	}

	/* Stagger children */
	:global(.revealed .problem-card),
	:global(.revealed .trust-logo) {
		animation: staggerIn 0.6s var(--ease-premium) both;
	}
	:global(.revealed .problem-card:nth-child(1)),
	:global(.revealed .trust-logo:nth-child(1)) {
		animation-delay: 0ms;
	}
	:global(.revealed .problem-card:nth-child(2)),
	:global(.revealed .trust-logo:nth-child(2)) {
		animation-delay: 100ms;
	}
	:global(.revealed .problem-card:nth-child(3)),
	:global(.revealed .trust-logo:nth-child(3)) {
		animation-delay: 200ms;
	}
	:global(.revealed .trust-logo:nth-child(4)) {
		animation-delay: 300ms;
	}
	:global(.revealed .trust-logo:nth-child(5)) {
		animation-delay: 400ms;
	}
	:global(.revealed .trust-logo:nth-child(6)) {
		animation-delay: 500ms;
	}

	@keyframes staggerIn {
		from {
			opacity: 0;
			transform: translateY(16px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
