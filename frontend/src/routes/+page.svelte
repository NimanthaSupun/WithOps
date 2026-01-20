<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getAuthClient } from '$lib/auth';
	import '../app.css';

	let isAuthenticated = false;
	let user = null;
	let typedCode = '';

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

					// Quoted strings (white)
					if (value.includes('"')) {
						coloredValue = value.replace(/"([^"]*)"/g, '<span style="color: #FFFFFF;">"$1"</span>');
					}
					// Numbers (bright cyan)
					else if (value.trim().match(/^\d+$/)) {
						coloredValue = ` <span style="color: #00D9FF;">${value.trim()}</span>`;
					}
					// Boolean values (bright cyan)
					else if (value.trim().match(/^(true|false|active|yes|no)$/i)) {
						coloredValue = ` <span style="color: #00D9FF;">${value.trim()}</span>`;
					}
					// URLs (bright cyan)
					else if (value.includes('http')) {
						coloredValue = value.replace(
							/(https?:\/\/[^\s,"]+)/g,
							'<span style="color: #00D9FF;">$1</span>'
						);
					}
					// Other string values (light gray)
					else if (value.trim()) {
						coloredValue = ` <span style="color: #B8B8B8;">${value.trim()}</span>`;
					}

					return `${indent}<span style="color: #00D9FF;">${key}</span><span style="color: #FFFFFF;">:</span>${coloredValue}`;
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

		// Typing animation effect with VS Code-style syntax highlighting
		let index = 0;
		const interval = setInterval(() => {
			if (index <= yamlCode.length) {
				const currentCode = yamlCode.slice(0, index);
				typedCode = highlightYAML(currentCode);
				index += 3; // Faster typing
			} else {
				// Restart animation after pause
				setTimeout(() => {
					typedCode = '';
					index = 0;
				}, 4000);
			}
		}, 15); // Smoother animation

		return () => clearInterval(interval);
	});
</script>

<!-- Navigation Bar -->
<nav class="navbar">
	<div class="nav-container">
		<div class="nav-brand">
			<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
			<span class="brand-name">WithOps</span>
		</div>
		<div class="nav-menu">
			<a href="#home" class="nav-link active">Home</a>
			<a href="#features" class="nav-link">Features</a>
			<a href="#security" class="nav-link">Security</a>
			<a href="#analytics" class="nav-link">Analytics</a>
			<a href="#docs" class="nav-link">Docs</a>
			<a href="#contact" class="nav-link">Contact</a>
		</div>
		<div class="nav-actions">
			{#if isAuthenticated}
				<span class="user-welcome">Welcome, {user?.name}</span>
				<button class="nav-btn-primary" on:click={() => goto('/dashboard')}>Dashboard</button>
			{:else}
				<button class="nav-btn-secondary" on:click={handleSignIn}>Sign In</button>
				<button class="nav-btn-primary" on:click={handleGetStarted}>Get Started</button>
			{/if}
		</div>
	</div>
</nav>

<!-- Hero Section with 3D Layered Background -->
<main class="hero-dashboard" id="home">
	<!-- YAML Code Background with Typing Effect (Full Width) -->
	<div class="yaml-background">
		<div class="yaml-gradient"></div>

		<!-- Main YAML Display (Positioned Right) -->
		<div class="yaml-display">
			<pre class="yaml-pre"><code class="yaml-code"
					>{@html typedCode}<span class="cursor"></span></code
				></pre>
		</div>

		<!-- Scanline Effect -->
		<div class="scanline"></div>

		<!-- Grid Overlay -->
		<div class="grid-overlay"></div>

		<!-- Atmospheric Effects -->
		<div class="fog-layer fog-layer-1"></div>
		<div class="fog-layer fog-layer-2"></div>
		<div class="light-rays"></div>
	</div>

	<!-- Hero Content (Left Aligned) -->
	<div class="hero-content">
		<!-- Main Heading -->
		<h1 class="main-title">
			<span class="title-highlight">WithOps</span>
			<span class="title-subtitle">DevSecOps Platform</span>
		</h1>

		<!-- Description -->
		<p class="hero-description">
			Advanced security automation and continuous integration platform with AI-powered threat
			detection and real-time monitoring capabilities.
		</p>

		<!-- CTA Buttons -->
		<div class="cta-buttons">
			{#if isAuthenticated}
				<button class="btn-primary" on:click={() => goto('/dashboard')}>Go to Dashboard</button>
				<button class="btn-secondary">Learn More</button>
			{:else}
				<button class="btn-primary" on:click={handleGetStarted}>Get Started</button>
				<button class="btn-secondary" on:click={handleSignIn}>Sign In</button>
			{/if}
		</div>
	</div>
</main>

<!-- Features Section -->
<section class="features-section" id="features">
	<div class="features-container">
		<header class="section-header">
			<h2 class="section-title">Everything After Code</h2>
			<p class="section-description">
				Intelligent AI-driven security automation that empowers development teams to ship code
				faster, safer, and smarter
			</p>
		</header>

		<div class="features-grid">
			<div class="feature-card">
				<div class="feature-number">01</div>
				<h3>AI-Powered Security Analysis</h3>
				<p>
					Advanced threat detection using GPT-4 and custom ML models. Automatically identify
					vulnerabilities, assess risks, and get instant remediation suggestions with 99.9%
					accuracy.
				</p>
				<ul class="feature-list">
					<li>Conversational AI assistant for DevSecOps guidance</li>
					<li>Automated vulnerability detection & code analysis</li>
					<li>Real-time security recommendations</li>
				</ul>
			</div>

			<div class="feature-card">
				<div class="feature-number">02</div>
				<h3>Threat Modeling & Risk Assessment</h3>
				<p>
					Automated STRIDE threat analysis with intelligent attack surface mapping. Generate
					comprehensive threat models and strategic mitigation recommendations aligned with OWASP
					Top 10.
				</p>
				<ul class="feature-list">
					<li>STRIDE framework implementation</li>
					<li>Attack vector visualization with dependency graphs</li>
					<li>Dynamic risk scoring & prioritization</li>
				</ul>
			</div>

			<div class="feature-card">
				<div class="feature-number">03</div>
				<h3>GitHub Integration & Automation</h3>
				<p>
					Seamless GitHub integration with automated PR analysis, workflow monitoring, and
					dependency tracking. Security scanning with inline code comments and suggestions.
				</p>
				<ul class="feature-list">
					<li>Automated pull request security analysis</li>
					<li>Real-time GitHub Actions monitoring</li>
					<li>Intelligent dependency vulnerability alerts</li>
				</ul>
			</div>

			<div class="feature-card">
				<div class="feature-number">04</div>
				<h3>Workspace Intelligence</h3>
				<p>
					Deep semantic code analysis with pattern detection and best practice enforcement. Track
					technical debt and get DevSecOps maturity scoring across your entire codebase.
				</p>
				<ul class="feature-list">
					<li>Repository structure analysis & insights</li>
					<li>Code quality metrics & trend analysis</li>
					<li>Security posture assessment</li>
				</ul>
			</div>

			<div class="feature-card">
				<div class="feature-number">05</div>
				<h3>Real-Time Collaboration</h3>
				<p>
					Enterprise-grade authentication with Auth0, role-based access control, and real-time
					WebSocket communication for distributed teams working on security initiatives.
				</p>
				<ul class="feature-list">
					<li>Multi-factor authentication & SSO</li>
					<li>Team workspace sharing & collaboration</li>
					<li>Live notifications & activity tracking</li>
				</ul>
			</div>

			<div class="feature-card">
				<div class="feature-number">06</div>
				<h3>Comprehensive Monitoring</h3>
				<p>
					Full observability stack with Prometheus, Grafana, and Jaeger. Distributed tracing,
					metrics collection, and real-time dashboards for all microservices.
				</p>
				<ul class="feature-list">
					<li>Distributed tracing with OpenTelemetry</li>
					<li>Custom metrics & alerting</li>
					<li>Real-time performance dashboards</li>
				</ul>
			</div>
		</div>
	</div>
</section>

<!-- Footer -->
<footer class="footer">
	<div class="footer-container">
		<div class="footer-content">
			<div class="footer-brand">
				<div class="footer-logo">
					<img src="/icons/excellence_17274210.png" alt="WithOps" class="brand-icon" />
					<span class="brand-name">WithOps</span>
				</div>
				<p class="brand-description">
					Next-generation DevSecOps platform empowering modern development teams with AI-powered
					security, intelligent automation, and comprehensive monitoring.
				</p>
				<div class="footer-social">
					<a
						href="https://github.com"
						class="social-link"
						target="_blank"
						rel="noopener noreferrer"
						aria-label="GitHub"
						><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"
							><path
								d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
							/></svg
						></a
					>
					<a
						href="https://linkedin.com"
						class="social-link"
						target="_blank"
						rel="noopener noreferrer"
						aria-label="LinkedIn"
						><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"
							><path
								d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"
							/></svg
						></a
					>
					<a
						href="https://twitter.com"
						class="social-link"
						target="_blank"
						rel="noopener noreferrer"
						aria-label="Twitter"
						><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"
							><path
								d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"
							/></svg
						></a
					>
				</div>
			</div>

			<div class="footer-links">
				<div class="link-group">
					<h4>Platform</h4>
					<a href="#security">AI Security Analysis</a>
					<a href="#threat">Threat Modeling</a>
					<a href="#github">GitHub Integration</a>
					<a href="#intelligence">Workspace Intelligence</a>
				</div>

				<div class="link-group">
					<h4>Resources</h4>
					<a href="#docs">Documentation</a>
					<a href="#api">API Reference</a>
					<a href="#guides">Getting Started</a>
					<a href="#support">Support Center</a>
				</div>

				<div class="link-group">
					<h4>Company</h4>
					<a href="#about">About Us</a>
					<a href="#blog">Blog</a>
					<a href="#careers">Careers</a>
					<a href="#contact">Contact</a>
				</div>
			</div>
		</div>

		<div class="footer-divider"></div>

		<div class="footer-bottom">
			<p class="copyright">&copy; 2026 WithOps Platform. All rights reserved.</p>
			<div class="footer-legal">
				<a href="#privacy">Privacy Policy</a>
				<span class="separator">•</span>
				<a href="#terms">Terms of Service</a>
				<span class="separator">•</span>
				<a href="#security">Security</a>
			</div>
		</div>
	</div>
</footer>

<style>
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	/* Navigation Bar */
	.navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 1000;
		background: rgba(0, 0, 0, 0.95);
		backdrop-filter: blur(20px);
		border-bottom: 1px solid rgba(0, 217, 255, 0.3);
		padding: 1rem 0;
		transition: all 0.3s ease;
	}

	.nav-container {
		max-width: 1200px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 2rem;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		cursor: pointer;
		transition: transform 0.3s ease;
	}

	.nav-brand:hover {
		transform: translateY(-1px);
	}

	.brand-icon {
		width: 48px;
		height: 48px;
		filter: drop-shadow(0 0 10px rgba(0, 217, 255, 0.5));
		transition: filter 0.3s ease;
	}

	.nav-brand:hover .brand-icon {
		filter: drop-shadow(0 0 15px rgba(0, 217, 255, 0.7));
	}

	.brand-name {
		font-size: 1.5rem;
		font-weight: 700;
		color: #ffffff;
		letter-spacing: -0.02em;
	}

	.user-welcome {
		color: #b8b8b8;
		margin-right: 1rem;
		font-size: 0.9rem;
	}

	.nav-menu {
		display: flex;
		gap: 2rem;
		align-items: center;
	}

	.nav-link {
		color: #b8b8b8;
		text-decoration: none;
		font-weight: 500;
		transition: color 0.3s ease;
		position: relative;
	}

	.nav-link:hover,
	.nav-link.active {
		color: #00d9ff;
	}

	.nav-link::after {
		content: '';
		position: absolute;
		bottom: -5px;
		left: 0;
		width: 0;
		height: 2px;
		background: #00d9ff;
		transition: width 0.3s ease;
	}

	.nav-link:hover::after,
	.nav-link.active::after {
		width: 100%;
	}

	.nav-actions {
		display: flex;
		gap: 1rem;
		align-items: center;
	}

	.nav-btn-secondary,
	.nav-btn-primary {
		padding: 0.5rem 1.2rem;
		border: none;
		border-radius: 6px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.3s ease;
		text-decoration: none;
	}

	.nav-btn-secondary {
		background: transparent;
		color: #00d9ff;
		border: 1px solid rgba(0, 217, 255, 0.4);
		border-radius: 8px;
	}

	.nav-btn-secondary:hover {
		background: rgba(0, 217, 255, 0.1);
		color: #00d9ff;
		border-color: #00d9ff;
	}

	.nav-btn-primary {
		background: #ffffff;
		color: #000000;
		font-weight: 600;
		border-radius: 8px;
	}

	.nav-btn-primary:hover {
		transform: translateY(-1px);
		box-shadow: 0 4px 15px rgba(0, 217, 255, 0.3);
		background: #00d9ff;
		color: #000000;
	}

	/* Hero Dashboard with 3D Layered Background */
	.hero-dashboard {
		position: relative;
		min-height: 100vh;
		overflow: hidden;
		background: #000000;
		display: flex;
		align-items: center;
		justify-content: flex-start;
		padding-top: 128px;
		padding-bottom: 80px;
		padding-left: 280px;
		padding-right: 200px;

		/* Strong 3D perspective */
		perspective: 2000px;
		perspective-origin: center center;
		transform-style: preserve-3d;
	}

	/* YAML Background - Full Width with 3D Effect */
	.yaml-background {
		position: absolute;
		inset: 0;
		overflow: hidden;
		transform-style: preserve-3d;
	}

	.yaml-gradient {
		position: absolute;
		inset: 0;
		background: #000000;
	}

	/* Main YAML Display - Deep inside the panel */
	.yaml-display {
		position: absolute;
		top: 0;
		right: 0;
		bottom: 0;
		left: 0;
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: flex-end;
		padding-right: 18%;

		/* Push deep inside - behind the text */
		transform: translateZ(-300px) scale(1.15);
		transform-style: preserve-3d;
		z-index: 1;
	}

	.yaml-pre {
		width: 100%;
		max-width: 55rem;
		margin: 0;
		padding: 0;
		text-align: left;
		font-family: 'Consolas', 'Courier New', monospace;
		font-size: 0.9rem;
		line-height: 1.6;
		white-space: pre-wrap;
		word-wrap: break-word;
		overflow-x: hidden;
		overflow-y: hidden;
		opacity: 0.75;
		user-select: none;
		color: #d4d4d4;
		position: relative;
		background: transparent;
		/* Vertical indentation guide lines at meaningful levels */
		background-image:
			linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
		background-size: 100% 100%;
		background-position:
			2ch 0,
			4ch 0,
			6ch 0,
			8ch 0,
			10ch 0;
		background-repeat: no-repeat;
	}

	.yaml-code {
		color: #d4d4d4;
		font-family: 'Consolas', 'Courier New', monospace;
		font-weight: 400;
		letter-spacing: 0;
		font-size: 0.9rem;
	}

	/* YAML Syntax Highlighting - Allow inline styles to override */
	.yaml-code span {
		font-family: inherit;
	}

	.cursor {
		display: inline-block;
		width: 8px;
		height: 20px;
		background-color: #ffffff;
		margin-left: 2px;
		animation: blink 1s infinite;
		vertical-align: text-bottom;
	}

	@keyframes blink {
		0%,
		50% {
			opacity: 1;
		}
		51%,
		100% {
			opacity: 0;
		}
	}

	/* Scanline Effect */
	.scanline {
		position: absolute;
		inset: 0;
		background: linear-gradient(to bottom, transparent, rgba(0, 217, 255, 0.05), transparent);
		height: 200px;
		animation: scan 8s linear infinite;
		pointer-events: none;
	}

	@keyframes scan {
		0% {
			transform: translateY(-100%);
		}
		100% {
			transform: translateY(100vh);
		}
	}

	/* Grid Overlay */
	.grid-overlay {
		position: absolute;
		inset: 0;
		opacity: 0.03;
		pointer-events: none;
		background-image:
			linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
		background-size: 50px 50px;
	}

	/* Atmospheric Fog Layers */
	.fog-layer {
		position: absolute;
		inset: 0;
		pointer-events: none !important;
		opacity: 0.15;
		z-index: 1;
	}

	.fog-layer-1 {
		background: radial-gradient(ellipse at 30% 50%, rgba(0, 217, 255, 0.15) 0%, transparent 50%);
		transform: translateZ(-200px) scale(1.1);
		animation: fogDrift1 20s ease-in-out infinite alternate;
	}

	.fog-layer-2 {
		background: radial-gradient(ellipse at 70% 60%, rgba(255, 255, 255, 0.08) 0%, transparent 60%);
		transform: translateZ(-250px) scale(1.15);
		animation: fogDrift2 25s ease-in-out infinite alternate;
	}

	@keyframes fogDrift1 {
		0% {
			transform: translateZ(-200px) scale(1.1) translateX(0);
		}
		100% {
			transform: translateZ(-200px) scale(1.1) translateX(50px);
		}
	}

	@keyframes fogDrift2 {
		0% {
			transform: translateZ(-250px) scale(1.15) translateX(0);
		}
		100% {
			transform: translateZ(-250px) scale(1.15) translateX(-40px);
		}
	}

	/* Light Rays Effect */
	.light-rays {
		position: absolute;
		inset: 0;
		pointer-events: none !important;
		background: radial-gradient(ellipse at 80% 20%, rgba(0, 217, 255, 0.1) 0%, transparent 40%);
		transform: translateZ(-150px);
		opacity: 0.6;
		animation: lightPulse 8s ease-in-out infinite;
		z-index: 1;
	}

	@keyframes lightPulse {
		0%,
		100% {
			opacity: 0.4;
		}
		50% {
			opacity: 0.7;
		}
	}

	/* Hero Content - Front Layer (Text on surface) */
	.hero-content {
		position: relative;
		z-index: 100;
		max-width: 650px;
		margin: 0;
		text-align: left;

		/* Bring text to front surface */
		transform: translateZ(200px);
		transform-style: preserve-3d;
	}

	/* Main Title */
	.main-title {
		font-size: clamp(2.5rem, 6vw, 4.5rem);
		font-weight: 700;
		line-height: 1.2;
		margin-bottom: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.title-highlight {
		color: #ffffff;
		font-size: 1em;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
	}

	.title-subtitle {
		color: #00d9ff;
		font-size: 0.6em;
		font-weight: 700;
		letter-spacing: 0.05em;
		opacity: 1;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
	}

	/* Legacy heading styles for compatibility */

	/* Description */
	.hero-description {
		font-size: 1.2rem;
		color: #b8b8b8;
		line-height: 1.7;
		margin-bottom: 3rem;
		max-width: 500px;
		text-align: left;
		font-weight: 400;
	}

	/* CTA Buttons */
	.cta-buttons {
		display: flex;
		gap: 1.5rem;
		justify-content: flex-start;
		flex-wrap: wrap;
		position: relative;
		z-index: 10;
	}

	.btn-primary,
	.btn-secondary {
		padding: 1.2rem 2.5rem;
		border: none;
		border-radius: 10px;
		font-size: 1.1rem;
		font-weight: 600;
		cursor: pointer !important;
		transition: all 0.3s ease;
		text-decoration: none;
		display: inline-block;
		position: relative;
		z-index: 10;
		pointer-events: auto;
	}

	.btn-primary {
		background: #ffffff;
		color: #000000;
		font-weight: 600;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.5),
			0 5px 15px rgba(0, 0, 0, 0.3);
		border-radius: 8px;
	}

	.btn-primary:hover {
		transform: translateY(-3px);
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.4),
			0 8px 20px rgba(0, 0, 0, 0.6);
		background: #00d9ff;
		color: #000000;
	}

	.btn-secondary {
		background: rgba(0, 0, 0, 0.3);
		color: #00d9ff;
		border: 2px solid #00d9ff;
		border-radius: 8px;
		box-shadow:
			0 10px 30px rgba(0, 0, 0, 0.4),
			0 0 20px rgba(0, 217, 255, 0.2);
	}

	.btn-secondary:hover {
		background: #00d9ff;
		color: #000000;
		font-weight: 600;
		transform: translateY(-3px);
		border-color: #00d9ff;
		box-shadow:
			0 15px 35px rgba(0, 217, 255, 0.5),
			0 8px 20px rgba(0, 0, 0, 0.6);
	}

	/* CTA Button (legacy) */

	/* Responsive adjustments */
	@media (min-width: 768px) {
		.hero-description {
			font-size: 1.5rem;
		}

		.yaml-pre {
			font-size: 1rem;
		}
	}

	/* Features Section */
	.features-section {
		background: #000000;
		padding: 8rem 0;
		position: relative;
	}

	.features-container {
		max-width: 1400px;
		margin: 0 auto;
		padding: 0 2rem;
	}

	.section-header {
		text-align: center;
		margin-bottom: 5rem;
	}

	.section-title {
		font-size: clamp(2.5rem, 5vw, 3.5rem);
		font-weight: 700;
		color: #00d9ff;
		margin-bottom: 1.5rem;
		letter-spacing: -0.02em;
	}

	.section-description {
		font-size: 1.3rem;
		color: #b8b8b8;
		max-width: 800px;
		margin: 0 auto;
		line-height: 1.7;
		font-weight: 400;
	}

	.features-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
		gap: 2.5rem;
		margin-top: 4rem;
	}

	.feature-card {
		background: rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(0, 217, 255, 0.2);
		border-radius: 12px;
		padding: 2.5rem;
		transition: all 0.4s ease;
		position: relative;
		overflow: hidden;
	}

	.feature-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.05), transparent);
		transition: left 0.6s;
	}

	.feature-card:hover::before {
		left: 100%;
	}

	.feature-card:hover {
		transform: translateY(-5px);
		border-color: rgba(0, 217, 255, 0.5);
		box-shadow: 0 20px 40px rgba(0, 217, 255, 0.15);
		background: rgba(0, 0, 0, 0.6);
	}

	.feature-number {
		font-size: 0.9rem;
		font-weight: 700;
		color: #00d9ff;
		margin-bottom: 1.5rem;
		letter-spacing: 0.1em;
	}

	.feature-card h3 {
		color: #ffffff;
		font-size: 1.5rem;
		font-weight: 600;
		margin-bottom: 1rem;
		line-height: 1.3;
	}

	.feature-card p {
		color: #b8b8b8;
		line-height: 1.7;
		margin-bottom: 1.5rem;
		font-size: 1rem;
	}

	.feature-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.feature-list li {
		color: #b8b8b8;
		padding: 0.5rem 0;
		padding-left: 1.5rem;
		position: relative;
		font-size: 0.95rem;
		line-height: 1.6;
	}

	.feature-list li::before {
		content: '→';
		position: absolute;
		left: 0;
		color: #00d9ff;
		font-weight: 700;
	}

	/* Responsive Design */
	@media (max-width: 1024px) {
	}

	@media (max-width: 768px) {
		.feature-card {
			padding: 1.5rem;
		}

		.feature-number {
			width: 45px;
			height: 45px;
			font-size: 0.85rem;
		}

		.feature-card h3 {
			font-size: 1.25rem;
		}
	}

	/* Footer */
	.footer {
		background: #000000;
		border-top: 1px solid rgba(0, 217, 255, 0.2);
		padding: 4rem 0 2rem;
		position: relative;
	}

	.footer::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 1px;
		background: linear-gradient(90deg, transparent 0%, #00d9ff 50%, transparent 100%);
		opacity: 0.5;
	}

	.footer-container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 0 2rem;
	}

	.footer-content {
		display: grid;
		grid-template-columns: 1.5fr 2fr;
		gap: 4rem;
		margin-bottom: 3rem;
	}

	.footer-brand {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.footer-logo {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.footer-brand .brand-icon {
		width: 40px;
		height: 40px;
		filter: drop-shadow(0 0 8px rgba(0, 217, 255, 0.4));
		transition: filter 0.3s ease;
	}

	.footer-brand .brand-icon:hover {
		filter: drop-shadow(0 0 12px rgba(0, 217, 255, 0.6));
	}

	.footer-brand .brand-name {
		font-size: 1.5rem;
		font-weight: 700;
		color: #ffffff;
		letter-spacing: -0.02em;
	}

	.brand-description {
		color: #b8b8b8;
		line-height: 1.6;
		font-size: 0.95rem;
		max-width: 350px;
	}

	.footer-social {
		display: flex;
		gap: 0.75rem;
	}

	.social-link {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		color: #b8b8b8;
		text-decoration: none;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		transition: all 0.3s ease;
	}

	.social-link:hover {
		color: #00d9ff;
		border-color: #00d9ff;
		background: rgba(0, 217, 255, 0.1);
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 217, 255, 0.2);
	}

	.footer-links {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 2.5rem;
	}

	.link-group h4 {
		color: #ffffff;
		margin-bottom: 1.25rem;
		font-weight: 600;
		font-size: 0.95rem;
		letter-spacing: 0.05em;
		text-transform: uppercase;
	}

	.link-group a {
		color: #b8b8b8;
		text-decoration: none;
		display: block;
		margin-bottom: 0.75rem;
		font-size: 0.95rem;
		transition: all 0.2s ease;
		position: relative;
		padding-left: 0;
	}

	.link-group a::before {
		content: '';
		position: absolute;
		left: -12px;
		top: 50%;
		transform: translateY(-50%);
		width: 0;
		height: 1px;
		background: #00d9ff;
		transition: width 0.2s ease;
	}

	.link-group a:hover {
		color: #00d9ff;
		padding-left: 16px;
	}

	.link-group a:hover::before {
		width: 8px;
	}

	.footer-divider {
		height: 1px;
		background: rgba(255, 255, 255, 0.05);
		margin: 2rem 0;
	}

	.footer-bottom {
		display: flex;
		justify-content: space-between;
		align-items: center;
		color: #666;
		font-size: 0.9rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.copyright {
		color: #666;
	}

	.footer-legal {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.footer-legal a {
		color: #888;
		text-decoration: none;
		transition: color 0.2s ease;
	}

	.footer-legal a:hover {
		color: #00d9ff;
	}

	.footer-legal .separator {
		color: #444;
	}

	/* Responsive Design */
	@media (max-width: 768px) {
		.nav-container {
			padding: 0 1rem;
			flex-wrap: wrap;
		}

		.nav-menu {
			display: none;
		}

		.nav-actions {
			gap: 0.5rem;
		}

		.user-welcome {
			display: none;
		}

		.hero-dashboard {
			padding: 100px 24px 60px 24px;
			justify-content: center;
		}

		.yaml-display {
			width: 100%;
			padding-left: 0;
			justify-content: center;
			transform: translateZ(-50px) rotateY(0deg);
		}

		.yaml-pre {
			font-size: 0.7rem;
			line-height: 1.4;
			opacity: 0.4;
			padding: 0;
		}

		.hero-content {
			max-width: 100%;
			text-align: center;
			transform: translateZ(20px);
		}

		.main-title {
			font-size: clamp(2rem, 10vw, 3rem);
		}

		.hero-description {
			text-align: center;
			max-width: 100%;
			font-size: 1rem;
		}

		.cta-buttons {
			justify-content: center;
			flex-direction: column;
			align-items: center;
		}

		.btn-primary,
		.btn-secondary {
			width: 100%;
			max-width: 280px;
		}

		.features-grid {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}

		.footer {
			padding: 3rem 0 1.5rem;
		}

		.footer-content {
			grid-template-columns: 1fr;
			gap: 2.5rem;
		}

		.footer-brand {
			text-align: center;
			align-items: center;
		}

		.brand-description {
			max-width: 100%;
		}

		.footer-social {
			justify-content: center;
		}

		.footer-links {
			grid-template-columns: 1fr;
			gap: 2rem;
			text-align: center;
		}

		.link-group a::before {
			display: none;
		}

		.link-group a:hover {
			padding-left: 0;
		}

		.footer-bottom {
			flex-direction: column;
			gap: 1rem;
			text-align: center;
		}

		.footer-legal {
			flex-wrap: wrap;
			justify-content: center;
		}
	}

	@media (max-width: 480px) {
		.navbar {
			padding: 0.5rem 0;
		}

		.nav-container {
			padding: 0 0.5rem;
		}

		.nav-actions {
			gap: 0.25rem;
		}

		.nav-btn-secondary,
		.nav-btn-primary {
			padding: 0.4rem 0.8rem;
			font-size: 0.85rem;
		}

		.brand-name {
			font-size: 1rem;
		}

		.brand-icon {
			width: 24px;
			height: 24px;
		}

		.hero-description {
			font-size: 0.9rem;
			line-height: 1.5;
		}

		.section-title {
			font-size: clamp(1.8rem, 8vw, 2.5rem);
		}

		.section-description {
			font-size: 1rem;
		}

		.features-container {
			padding: 0 1rem;
		}
	}

	/* Tablet optimizations */
	@media (min-width: 481px) and (max-width: 768px) {
		.features-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	/* Large screen optimizations */
	@media (min-width: 1200px) {
		.features-grid {
			grid-template-columns: repeat(3, 1fr);
			max-width: 1400px;
			margin: 3rem auto 0;
		}

		.hero-description {
			font-size: 1.4rem;
			max-width: 700px;
		}
	}
</style>
