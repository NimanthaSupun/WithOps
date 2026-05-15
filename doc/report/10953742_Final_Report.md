# PUSL3190 Computing Project — Final Report

**DevSecOps Intelligence Platform for GitHub Workflow Security and Threat Modeling**

---

**Name:** Ilukwaththe Ariyarathne

**Plymouth Index Number:** 10953742

**Degree Programme:** BSc (Hons) Data Science

**Supervisor:** Prof. Chaminda Wijesinghe

**Submission Date:** May 2026

---

## Table of Contents

- Chapter 01 — Introduction
  - 1.1 Introduction
  - 1.2 Problem Definition
  - 1.3 Project Objectives
- Chapter 02 — Background, Objectives and Deliverables
  - 2.1 Background and Context
  - 2.2 Literature Review
  - 2.3 Objectives and Deliverables Summary
- Chapter 03 — The OWASP DevSecOps Maturity Model
  - 3.1 Overview of DSOMM
  - 3.2 The Five DSOMM Dimensions
  - 3.3 Maturity Levels
  - 3.4 Automated Scoring Methodology
- Chapter 04 — Method of Approach
  - 4.1 Research Design
  - 4.2 Development Methodology
  - 4.3 Data Sources and Collection
  - 4.4 Evaluation Strategy
- Chapter 05 — Requirements
  - 5.1 Functional Requirements
  - 5.2 Non-Functional Requirements
  - 5.3 Hardware and Software Requirements
- Chapter 06 — System Design and Architecture
  - 6.1 High-Level Architecture
  - 6.2 Microservices Design
  - 6.3 Database Design
  - 6.4 Frontend Architecture
- Chapter 07 — Implementation
  - 7.1 Core Platform Features
  - 7.2 DORA Metrics Dashboard
  - 7.3 Pipeline Prediction Service
  - 7.4 AI and RAG Integration
  - 7.5 Key Implementation Challenges
  - 7.6 Observability and Monitoring
- Chapter 08 — End-Project Report
  - 8.1 Project Summary
  - 8.2 Objectives Evaluation
  - 8.3 Changes During the Project
- Chapter 09 — Project Post-Mortem
  - 9.1 Were the Objectives Right?
  - 9.2 Technology Evaluation
  - 9.3 Process Evaluation
  - 9.4 Personal Performance
  - 9.5 Lessons Learned
- Chapter 10 — Conclusions
- Reference List
- Bibliography
- Appendices

---

## Chapter 01 — Introduction

### 1.1 Introduction

Modern software development relies extensively on Continuous Integration and Continuous Deployment (CI/CD) pipelines to automate build, test, and deployment processes. Platforms such as GitHub Actions have become the de facto standard for CI/CD automation, enabling development teams to define complex workflows using YAML configuration files. While this automation has dramatically accelerated software delivery, it has simultaneously introduced a new and largely unaddressed category of security vulnerabilities. Research by Pan et al. (2024) reveals that over 60% of CI/CD pipelines contain critical misconfigurations, transforming them into attractive targets for supply chain attacks. The March 2025 compromise of the tj-actions/changed-files GitHub Action demonstrated the catastrophic potential of such vulnerabilities, where a single compromised component affected thousands of dependent projects across the software ecosystem (Unit42, 2025).

DevSecOps — the integration of security practices into every phase of the software development lifecycle — has emerged as the industry response to these challenges. The OWASP DevSecOps Maturity Model (DSOMM) provides a structured framework for organisations to assess and improve their security posture across five critical dimensions: Build and Deployment, Implementation, Test and Verification, Information Gathering, and Culture and Organization. However, a significant gap persists between theoretical frameworks and practical implementation. Organisations understand the importance of DevSecOps maturity but lack automated tools to continuously assess their posture, detect workflow vulnerabilities, and model threats within their development infrastructure.

This project, named **WithOps**, addresses this gap by delivering an intelligent DevSecOps platform that unifies five critical capabilities: automated GitHub Actions workflow security analysis, DSOMM-based maturity scoring, AI-assisted threat modelling, CI/CD pipeline outcome prediction, and DORA (DevOps Research and Assessment) performance metrics. By integrating these capabilities into a single, developer-friendly platform built on a production-grade microservices architecture, WithOps enables organisations to proactively identify vulnerabilities, objectively measure security improvements, predict pipeline outcomes, and quantify delivery performance — all without sacrificing development velocity. The platform is publicly accessible at **https://app.withops.com/**.

The platform was designed as a comprehensive intelligence layer that sits atop existing GitHub infrastructure, providing organisation-wide visibility into CI/CD security posture and delivery performance. It leverages multiple AI providers — including Anthropic Claude, Meta Llama 3 via Groq, and locally hosted models through Ollama — to deliver intelligent threat analysis, automated remediation recommendations, and conversational security insights through a Retrieval-Augmented Generation (RAG) system.

### 1.2 Problem Definition

Organisations face five critical, interconnected challenges in securing and optimising their CI/CD workflows that the current tooling landscape fails to address comprehensively.

**First, workflow misconfigurations remain undetected until exploited.** GitHub Actions workflows frequently contain unpinned dependencies referencing mutable tags rather than immutable commit SHAs, excessive permissions granting unnecessary access, insecure triggers vulnerable to code injection, and leaked credentials embedded in configuration files. Traditional security tools focus on application source code analysis and entirely miss these workflow-level vulnerabilities. Pan et al. (2024) found that 73% of actions are pinned to mutable tags, 41% have excessive permissions, and 15% contain hardcoded secrets.

**Second, organisations cannot objectively measure their DevSecOps maturity.** While OWASP DSOMM provides a theoretical framework defining maturity levels from basic awareness (Level 0) to advanced automation (Level 4), manual assessment requires 40–80 hours per evaluation cycle (Jit, 2024). This makes continuous monitoring impractical and prevents organisations from demonstrating security improvements to stakeholders or regulatory auditors.

**Third, threat modelling remains disconnected from development workflows.** Traditional threat modelling tools require separate processes, specialised security expertise, and significant time investment — Shevchenko et al. (2018) report that moderately complex system assessments require 40–60 hours. This leads many development teams to skip threat modelling entirely.

**Fourth, CI/CD pipeline failures waste developer time.** Saroar and Nayebi (2023) found that workflow debugging consumes an average of 6.3 hours per developer monthly. Without predictive capabilities, teams repeatedly trigger pipelines that are likely to fail, wasting computational resources and development time.

**Fifth, organisations lack quantitative delivery performance measurement.** The DORA research programme (Forsgren, Humble and Kim, 2018) established that Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Mean Time to Recovery are the four key metrics that predict software delivery performance. Yet most organisations lack automated tooling to compute these metrics from their existing CI/CD data, preventing evidence-based process improvement.

These challenges collectively manifest as increased supply chain attack risk, compliance failures, wasted developer productivity, and an inability to demonstrate measurable security and delivery improvements to stakeholders.

### 1.3 Project Objectives

The WithOps platform defines eight specific, measurable project objectives:

1. **Develop a GitHub Workflow Security Analysis Engine** — Analyse GitHub Actions YAML files to detect 25+ vulnerability patterns including unpinned actions, outdated versions, insecure triggers, hardcoded secrets, and excessive permissions.

2. **Implement a DSOMM Maturity Assessment System** — Automatically map detected security practices to all five DSOMM dimensions, computing maturity scores from Level 0 through Level 4 and tracking progression over time.

3. **Build an AI-Powered Threat Modelling Canvas** — Provide an interactive visual canvas enabling system architecture diagram creation, with AI analysing diagrams using STRIDE, CIA triad, and LINDDUN privacy frameworks.

4. **Develop a RAG-Based Learning System** — Implement a Retrieval-Augmented Generation system using Qdrant vector database to enhance AI responses with contextual DevSecOps security knowledge.

5. **Create a Production-Grade Microservices Architecture** — Deploy nine independent microservices communicating via Redis event bus and Kong API gateway, tolerating individual service failure with graceful degradation.

6. **Build a Production-Ready Frontend Application** — Deliver a modern SvelteKit web application with interactive dashboards, visual workflow representation, and collaborative threat modelling with real-time multi-user support.

7. **Implement a Pipeline Prediction Service** — Develop a machine learning-based system that predicts CI/CD pipeline outcomes before execution, reducing wasted build time and enabling proactive failure prevention.

8. **Deliver a DORA Metrics Dashboard** — Compute and visualise the four DORA performance metrics (Deployment Frequency, Lead Time, Change Failure Rate, MTTR) from GitHub webhook events, with correlation analysis against DSOMM security maturity scores.

---

## Chapter 02 — Background, Objectives and Deliverables

### 2.1 Background and Context

Software supply chain attacks increased by 742% between 2019 and 2024, with CI/CD pipelines becoming prime targets (Sonatype, 2024). Attackers compromise build infrastructure rather than application code, affecting thousands of downstream organisations simultaneously. The March 2025 tj-actions/changed-files compromise demonstrated this pattern, where attackers exfiltrated GitHub tokens from thousands of repositories through a single compromised CI/CD component (Unit42, 2025).

Regulatory compliance requirements have intensified in response. The EU Cyber Resilience Act, Executive Order 14028, and industry standards (SOC 2, ISO 27001) now mandate demonstrable secure development practices. Organisations must prove DevSecOps maturity through documented controls and continuous monitoring. Google's DORA research further established that elite-performing teams deploy multiple times per day with change failure rates below 5%, while low performers deploy less than monthly with failure rates exceeding 30% (Forsgren, Humble and Kim, 2018).

Despite these pressures, the tooling landscape remains fragmented. GitHub Dependabot addresses dependency vulnerabilities but ignores workflow configurations. Harness provides CI/CD orchestration without security analysis. StepSecurity monitors runtime behaviour but lacks static analysis. Snyk offers application security testing but does not target GitHub Actions patterns. No existing platform unifies workflow security analysis, maturity assessment, threat modelling, pipeline prediction, and delivery performance metrics into a single integrated system.

### 2.2 Literature Review

The WithOps platform addresses gaps across five research domains.

**DSOMM Maturity Assessment.** The OWASP DevSecOps Maturity Model (DSOMM) provides a comprehensive framework for assessing security integration across five dimensions (OWASP Foundation, 2024). However, a significant "theory-to-practice gap" exists where organisations struggle to operationalise the framework manually. No existing tool automatically derives maturity scores from observable repository artifacts. A detailed examination of the DSOMM framework and its application in this project is provided in Chapter 03.

**CI/CD Pipeline Security.** Pan et al. (2024) analysed 16,000 repositories, finding 62.3% contained at least one high-severity workflow misconfiguration. Common vulnerabilities include actions pinned to mutable tags (73%), excessive permissions (41%), insecure triggers (28%), and hardcoded secrets (15%). Ayala and Garcia (2023) found only 14% of repositories implement adequate dependency pinning. Existing tools provide fragmented coverage focused on application code rather than workflow security.

**Threat Modelling Automation.** Traditional methodologies (STRIDE, LINDDUN) remain manual processes requiring 40–60 hours for moderately complex systems (Shevchenko et al., 2018). Yılmaz and Gönen (2023) demonstrated LLM-generated threats achieving 73% recall versus expert analysis, but no existing tool combines visual diagram analysis with multi-framework AI-powered threat identification.

**DORA Performance Metrics.** The Accelerate State of DevOps research (Forsgren, Humble and Kim, 2018) established four key metrics — Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Mean Time to Recovery — as predictors of software delivery performance. While commercial platforms such as LinearB and Jellyfish offer DORA dashboards, none correlate delivery performance with security maturity (DSOMM), leaving organisations unable to quantify the impact of security investments on delivery velocity.

**Pipeline Outcome Prediction.** Research into CI/CD build prediction has explored machine learning approaches to forecast pipeline success or failure. Hassan and Zhang (2006) demonstrated that historical build metadata can predict outcomes with reasonable accuracy. However, integration of prediction services into DevSecOps platforms — correlating security posture with pipeline reliability — remains unexplored.

**Integrated Gap Analysis.** Research consistently identifies isolated solutions addressing individual DevSecOps aspects without integration. WithOps uniquely combines automated DSOMM scoring, comprehensive workflow security scanning, AI-powered threat modelling, DORA delivery metrics, and pipeline prediction into a unified intelligence platform — with the novel capability of correlating security maturity against delivery performance.

### 2.3 Objectives and Deliverables Summary

The project delivers the following tangible artifacts:

1. **Nine-service microservices backend** — Events Hub, GitHub Service, AI Service, Threat Modeling Service, Workspace Intelligence Service, Collaboration Service, Auth Service, Workflow Orchestration Service, and AI RAG Service.
2. **SvelteKit 5 frontend application** — Interactive dashboards, threat modelling canvas, pipeline predictor, DORA metrics dashboard, and in-app documentation.
3. **Kong API Gateway configuration** — Declarative routing, CORS enforcement, and rate limiting.
4. **Docker Compose orchestration** — 16+ container deployment with observability stack (Prometheus, Grafana, Jaeger, Loki).
5. **Kubernetes deployment manifests** — Production-ready container orchestration configuration.
6. **Comprehensive documentation** — User guide, API reference, deployment guide, and architecture documentation.

---

## Chapter 03 — The OWASP DevSecOps Maturity Model

### 3.1 Overview of DSOMM

The OWASP DevSecOps Maturity Model (DSOMM) is an open-source framework published by the OWASP Foundation that provides a structured, repeatable methodology for assessing how deeply security practices are integrated into an organisation's software development lifecycle (OWASP Foundation, 2024). Unlike compliance checklists that produce binary pass/fail outcomes, DSOMM defines a progressive maturity scale that recognises security integration as a continuum — from organisations with no formal security practices to those with fully automated, continuously monitored security operations.

### 3.2 The Five DSOMM Dimensions

DSOMM organises security practices into five distinct dimensions, each representing a critical domain of DevSecOps capability:

1. **Build and Deployment** — This dimension evaluates the security of the CI/CD pipeline infrastructure itself: whether build processes are reproducible and tamper-proof, whether deployment pipelines enforce security gates (e.g., blocking deployments with critical vulnerabilities), whether container images are signed and verified, whether infrastructure-as-code is scanned for misconfigurations, and whether artifact integrity is maintained throughout the supply chain. In WithOps, this dimension is assessed by analysing GitHub Actions workflow definitions for security controls such as pinned action versions, restricted permissions, and deployment approval gates.

2. **Implementation** — This dimension measures the security of the application code and its dependencies: whether secure coding standards are enforced, whether dependencies are managed and regularly updated, whether secrets management follows best practices (e.g., using GitHub Secrets rather than hardcoded credentials), and whether security-focused code review processes are in place. WithOps assesses this dimension by inspecting dependency management configurations (Dependabot, Renovate), secret scanning settings, and branch protection rules requiring code review approvals.

3. **Test and Verification** — This dimension evaluates the breadth and depth of security testing: whether static application security testing (SAST) is integrated into CI/CD pipelines, whether dynamic testing (DAST) is performed, whether software composition analysis (SCA) identifies vulnerable dependencies, and whether penetration testing occurs regularly. WithOps detects the presence of security testing tools within workflow definitions — scanning for steps invoking tools such as Snyk, Trivy, CodeQL, or OWASP ZAP — and scores the dimension based on coverage breadth and automation level.

4. **Information Gathering** — This dimension assesses the organisation's ability to collect, aggregate, and act upon security intelligence: whether security findings are centralised and tracked, whether vulnerability databases are monitored, whether threat intelligence feeds are consumed, and whether security metrics are reported to stakeholders. WithOps evaluates this dimension by detecting enabled GitHub security features (Dependabot alerts, secret scanning alerts, code scanning alerts) and checking for centralised logging and monitoring configurations.

5. **Culture and Organization** — This dimension measures the human and organisational factors: whether security responsibilities are defined and assigned, whether developers receive security training, whether incident response procedures exist, whether security champions are designated within teams, and whether security is considered in architectural decision-making. This is the most challenging dimension to assess automatically; WithOps approximates it by analysing repository governance indicators such as CODEOWNERS files, security policy documents (SECURITY.md), contribution guidelines, and branch protection enforcement.

### 3.3 Maturity Levels

For each dimension, DSOMM defines five maturity levels representing progressive stages of security integration:

| Level | Name | Description |
|:---:|---|---|
| **Level 0** | Not Performed | No evidence of security practices in this dimension. The organisation has not begun addressing security in this area. |
| **Level 1** | Initial | Basic, ad-hoc security practices exist but are inconsistent and not formally defined. Security activities occur reactively rather than proactively. |
| **Level 2** | Managed | Security practices are defined and documented. Processes are repeatable but may not be fully automated. Basic tooling is in place. |
| **Level 3** | Defined | Security practices are standardised across the organisation, integrated into development workflows, and consistently enforced through automation. |
| **Level 4** | Advanced | Security practices are fully automated, continuously monitored, and proactively improved. Advanced capabilities such as threat intelligence integration and automated remediation are operational. |

### 3.4 Automated Scoring Methodology

The platform's maturity assessment algorithm operates by programmatically analysing observable repository artifacts — workflow definitions, configuration files, branch protection rules, and enabled security features — and mapping detected practices to the corresponding DSOMM dimension and maturity level. For each dimension, the algorithm assigns a score from 0 to 4 based on the highest level of practice detected. The overall maturity score is computed as a weighted average across all five dimensions, providing a single numeric indicator of the organisation's DevSecOps maturity posture. Results are stored temporally, enabling the platform to track maturity progression over time and demonstrate measurable security improvement to stakeholders.

---

## Chapter 04 — Method of Approach

### 4.1 Research Design

This project adopted a design science research approach with elements of experimental, prototype-driven, and case study-based research. The primary outcome was a functional software artifact — the WithOps DevSecOps Intelligence Platform — designed to address real-world challenges in CI/CD security and DevSecOps maturity assessment.

The research was prototype-driven, where the platform was incrementally designed, implemented, and refined through multiple iterations. Experimental elements were introduced by evaluating automated security detection, AI-assisted threat modelling, DORA metrics computation, and pipeline prediction against defined metrics. A case-study approach was used by applying the platform to multiple GitHub organisations, enabling observation of security posture and delivery performance in realistic environments.

### 4.2 Development Methodology

The project followed an Agile development methodology integrated with DevOps practices, using structured two-week sprint cycles.

**Sprint Structure:**
- **Week 1:** Feature development, unit testing, and service integration. New microservice features were developed in feature branches following Git feature-branch workflow.
- **Week 2:** Integration testing, user acceptance testing, performance optimisation, documentation, and sprint review.
- **Continuous Activities:** CI/CD pipeline execution, monitoring review, logging analysis, and feedback collection occurred throughout each sprint.

Version control was managed using Git with a feature-branch workflow. All changes went through pull request reviews before merging. The repository included CI/CD workflow definitions enforcing automated testing, security scanning (Gitleaks for secret detection, TruffleHog for PR enforcement), and quality gates.

### 4.3 Data Sources and Collection

**Primary Data Source — GitHub Ecosystem:** Repository metadata, CI/CD workflow definitions (.github/workflows/*.yml), GitHub Actions usage and version information, and webhook events (push, pull request, workflow_run) were collected through the GitHub REST API (v3) and GitHub App installation flows.

**DORA Metrics Data Collection:** Deployment data was collected automatically and in real-time through GitHub Webhooks. When a GitHub Actions workflow completed (success or failure), GitHub dispatched a `workflow_run.completed` webhook to the platform's GitHub Service, which published the event to the Redis event bus. The Workspace Intelligence Service's DORA Event Handler subscribed to these events, extracting deployment timestamps, repository identifiers, and outcome status, then persisting them as `DeploymentEvent` records in PostgreSQL. The DORA Calculator then computed metrics on-demand from these stored events.

**Pipeline Prediction Data:** Historical workflow run data — including repository metadata, workflow configuration patterns, and execution outcomes — was collected via GitHub webhooks and stored for training the pipeline prediction model.

### 4.4 Evaluation Strategy

System effectiveness was evaluated using quantitative metrics:
- **Security Accuracy:** Precision, recall, and F1-score of workflow vulnerability detection against manually verified datasets.
- **Maturity Assessment Consistency:** Variance between repeated automated DSOMM evaluations on unchanged repositories.
- **DORA Metrics Accuracy:** Comparison of computed deployment frequency, lead time, change failure rate, and MTTR against manually counted GitHub Actions logs.
- **Pipeline Prediction Accuracy:** Classification accuracy, precision, and recall of the pipeline outcome prediction model.
- **Performance:** API response latency at 95th percentile, organisation-wide analysis completion time.
- **Usability:** Task completion rate for core workflows.

---

## Chapter 05 — Requirements

### 5.1 Functional Requirements

The WithOps platform specifies the following functional requirements, organised by feature module:

**FR-01: GitHub Integration** — The system shall authenticate users via GitHub OAuth 2.0 and GitHub App installation flows, retrieve and display all accessible organisations and repositories, parse GitHub Actions workflow YAML files, receive and process webhook events for push, pull request, and workflow run events, and cache data in Redis with configurable TTL.

**FR-02: Workflow Security Analysis** — The system shall detect unpinned GitHub Actions, identify outdated action versions, detect insecure workflow triggers, identify excessive permission scopes, detect potential credential exposure through entropy-based and pattern-matching algorithms, and categorise findings by severity using CVSS v3.1 scoring.

**FR-03: DSOMM Maturity Assessment** — The system shall automatically assess repositories against all five DSOMM dimensions, compute maturity levels (L0–L4) for each dimension, generate unified maturity scores, and track maturity progression over time.

**FR-04: Threat Modelling** — The system shall provide an interactive visual canvas for architecture diagram creation, support multi-framework threat analysis (STRIDE, CIA, LINDDUN), generate AI-powered threat identifications, provide real-time multi-user collaboration, and generate structured threat reports.

**FR-05: AI RAG System** — The system shall provide conversational AI interaction with context-aware responses, index workspace analysis data into vector embeddings for semantic retrieval, and maintain conversation history with per-user access controls.

**FR-06: Canvas Builder** — The system shall provide a visual drag-and-drop interface for CI/CD pipeline construction, generate valid GitHub Actions YAML from visual representations, and create pull requests with generated workflow files.

**FR-07: Action Audit** — The system shall monitor all GitHub Actions across an organisation for version governance, classify action versions by update status, support automated remediation via pull requests, and perform anti-typosquatting verification.

**FR-08: Pipeline Prediction** — The system shall predict CI/CD pipeline outcomes (pass/fail) based on historical workflow data, display prediction confidence scores, and track prediction accuracy over time against actual outcomes.

**FR-09: DORA Metrics** — The system shall automatically compute Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Mean Time to Recovery from GitHub webhook events. The system shall classify organisation performance against Google DORA benchmarks (Elite, High, Medium, Low), display weekly performance trends, provide per-repository metric breakdowns, and correlate DORA performance with DSOMM security maturity scores.

### 5.2 Non-Functional Requirements

**Performance:** API response latency shall not exceed 200ms for 95th percentile requests. Organisation-wide security analysis for up to 200 repositories shall complete within 3 minutes. Frontend first contentful paint shall be under 1.5 seconds.

**Security:** All data in transit shall be encrypted using TLS 1.3. Authentication shall use Auth0 with JWT tokens validated at the API gateway level. Webhook payloads shall be verified using HMAC-SHA256 signatures. API rate limiting shall enforce 100 requests per minute per client.

**Scalability:** The microservices architecture shall support horizontal scaling of individual services. The system shall handle concurrent analysis of multiple organisations without performance degradation.

**Availability:** The system shall target 99% uptime for critical paths. Individual service failures shall not cascade to other services.

**Usability:** The interface shall follow a consistent "Matte Engineering" design language with dark and light theme support. Task completion rate for core workflows shall exceed 85%.

**Observability:** All services shall expose Prometheus metrics, OpenTelemetry distributed traces, and structured logs. Centralised monitoring dashboards shall be available via Grafana.

### 5.3 Hardware and Software Requirements

**Server-Side Requirements:**

| Component | Specification |
|---|---|
| Operating System | Linux (Ubuntu 22.04+), macOS, or Windows with WSL2 |
| CPU | 4+ cores (8+ recommended for AI workloads) |
| RAM | 8 GB minimum, 16 GB recommended |
| Storage | 20 GB minimum available disk space |
| Docker | Docker Engine 24.0+ with Docker Compose v2 |
| Python | Python 3.11+ |
| Node.js | Node.js 18+ or 20+ (LTS) |

**Key Software Dependencies:**

| Component | Technology | Version |
|---|---|---|
| Frontend Framework | SvelteKit | 2.16.0 |
| UI Framework | Svelte | 5.x (Runes API) |
| Backend Framework | FastAPI | 0.104.1 |
| Database | PostgreSQL (Supabase) | 15.x |
| Cache / Message Broker | Redis | 7.x |
| Vector Database | Qdrant | 1.7+ |
| API Gateway | Kong | 3.x |
| Containerisation | Docker + Docker Compose | 24.0+ |

---

## Chapter 06 — System Design and Architecture

### 6.1 High-Level Architecture

The WithOps platform implements a microservices architecture with an event-driven communication backbone. The architecture comprises five layers:

**Layer 1 — Client Layer:** The SvelteKit 5 frontend application communicates with the backend exclusively through the Kong API Gateway. It maintains persistent WebSocket connections to the Events Hub for real-time notifications and DORA metric updates.

**Layer 2 — API Gateway Layer:** Kong Gateway serves as the single entry point on port 9000, providing request routing to appropriate microservices, CORS enforcement, rate limiting, and request transformation. Routes are configured declaratively using `kong.yml`.

**Layer 3 — Microservices Layer:** Nine independently deployable FastAPI microservices, each responsible for a specific domain:

| Service | Port | Responsibility |
|---|---|---|
| Events Hub | 8000 / 9100 | WebSocket gateway, Redis event bus, real-time notifications |
| AI Service | 8001 / 9101 | AI/ML analysis, PR description generation, threat analysis |
| GitHub Service | 8002 / 9102 | GitHub API integration, webhook handling, repository caching |
| Threat Modeling | 8003 / 9103 | STRIDE/CIA/LINDDUN analysis, threat model CRUD |
| Workspace Intelligence | 8004 / 9104 | DSOMM scoring, DORA metrics, pipeline prediction |
| Collaboration | 8105 / 9105 | Multi-user sessions, organisation membership management |
| Auth Service | 8006 / 9106 | Auth0 JWT validation, RBAC, user profile management |
| Workflow Orchestration | 8007 / 9107 | CI/CD workflow management, Canvas Builder, security scanning |
| AI RAG Service | 8008 / 9108 | Conversational AI, vector search, auto-indexing |

**Layer 4 — Data Layer:** PostgreSQL 15 (Supabase) serves as the primary relational data store. Redis 7 provides caching, pub/sub event bus communication, and session management. Qdrant stores vector embeddings for RAG semantic search.

**Layer 5 — Observability Layer:** Prometheus collects metrics from all service `/metrics` endpoints. Grafana provides visualisation dashboards. Jaeger receives distributed traces via OpenTelemetry. Loki aggregates logs from all containers.

**Container Orchestration.** The entire platform is orchestrated using Docker Compose, defining 16+ containers with explicit service dependency management, health check configurations, volume mounts for data persistence, and network isolation. All microservices, databases, caches, and observability tools are defined in a single `docker-compose.yml` file, enabling one-command deployment of the complete platform. Each service container is built from a dedicated Dockerfile specifying Python 3.11 base images with multi-stage builds to minimise image sizes. Environment variables are injected from a shared `.env` file, enabling configuration to be varied across development, staging, and production environments without code changes. For production deployment, a separate `docker-compose.prod.yml` provides optimised configurations including resource limits, restart policies, and external network configurations suitable for Kubernetes migration.

### 6.2 Microservices Design

Inter-service communication follows two patterns:

**Synchronous (HTTP/REST):** Services communicate via httpx async HTTP client for request-response operations. Docker DNS resolution enables service discovery using container names.

**Asynchronous (Redis Pub/Sub):** The Redis event bus provides decoupled, event-driven communication across three primary channels: `github_events`, `threat_modeling_events`, and `workspace_intelligence_events`. This pattern was critical for the DORA metrics feature, where the GitHub Service publishes `workflow_run.completed` events that the Workspace Intelligence Service's DORA Event Handler consumes asynchronously.

Each microservice follows a consistent internal structure: `main.py` (FastAPI application entry point), `api/routes/` (REST endpoint definitions), `core/` (business logic and domain services), `database/` (SQLAlchemy models and migrations), and `config.py` (environment-based configuration).

**Resilience Patterns.** The microservices architecture implements several resilience patterns to ensure fault tolerance. The tenacity library provides retry logic with exponential backoff for all inter-service HTTP calls, preventing transient network failures from causing user-visible errors. Docker Compose health checks with `depends_on` conditions ensure proper service startup ordering — services that depend on Redis or PostgreSQL wait for those dependencies to become healthy before accepting requests. Each service exposes a `/health` endpoint that returns service status, version, and dependency connectivity, enabling the Kong gateway and Docker orchestrator to make informed routing and restart decisions.

**Observability Instrumentation.** Every microservice is instrumented with three observability pillars. Prometheus metrics are exposed via a `/metrics` endpoint, tracking HTTP request counts, request latency histograms, and active connection gauges using the `prometheus-client` library. OpenTelemetry distributed tracing instruments request flows across service boundaries, enabling end-to-end latency analysis through the Jaeger UI — critical for identifying bottlenecks in multi-service operations such as organisation-wide security analysis. Structured logging using Python's standard logging module with JSON formatting enables log aggregation via Loki, with correlation IDs propagated across services to trace individual request chains.

**DORA Event Pipeline Architecture.** The DORA metrics data pipeline exemplifies the event-driven architecture's strengths. When a GitHub Actions workflow completes, GitHub dispatches a webhook to the GitHub Service (port 9102). The GitHub Service validates the webhook signature using HMAC-SHA256, extracts the relevant payload fields, and publishes a structured event to the `github_events` Redis channel. The Workspace Intelligence Service's DORA Event Handler, running as a background async task initialised during service startup, receives this event within milliseconds. The handler creates a `DeploymentEvent` database record and optionally triggers metric recalculation. This fully decoupled architecture means the GitHub Service has no knowledge of DORA metrics — it simply publishes events — while the DORA subsystem can evolve independently.

### 6.3 Database Design

The platform uses Supabase PostgreSQL as the primary relational database. Key entities include:

- **users** — Auth0 identity, email, role, and session data.
- **organizations** — GitHub organisation metadata linked to users.
- **repositories** — Repository metadata with security scores.
- **workflows** — GitHub Actions YAML content and trigger configurations.
- **security_findings** — Detected vulnerabilities with severity and remediation.
- **threat_models** — Canvas data stored as JSONB with analysis results.
- **maturity_assessments** — DSOMM dimensional scores tracked temporally.
- **deployment_events** — GitHub workflow run outcomes with timestamps, used for DORA metric computation. Fields include repository name, workflow name, event type (deployment/failure/recovery), duration in seconds, and commit SHA.
- **dora_metric_snapshots** — Periodic DORA metric computations storing deployment frequency, lead time, change failure rate, MTTR, and overall classification.
- **conversations** — AI RAG chat histories with per-user access control.

### 6.4 Frontend Architecture

The frontend was built with SvelteKit 2 and Svelte 5, leveraging the Runes API ($state, $derived, $effect) for compile-time reactive programming. The application follows a consistent "Matte Engineering" design language featuring:

- **CSS Variable System:** Theme-aware variables (--bg-app, --bg-surface, --text-primary, --accent) supporting dark and light modes via a single class toggle.
- **Typography:** Inter for UI text and JetBrains Mono for data and metrics display.
- **Layout Pattern:** Collapsible sidebar navigation, top navigation bar, breadcrumb trail, and main content area — consistent across all workspace pages.
- **Component Pattern:** Stat cards with classification badges, filter navigation tabs, and responsive grid layouts.

Each workspace page (Intelligence, Predictor, DORA Metrics) follows the same structural template: loading screen → header with breadcrumbs → page title with action buttons → tab navigation → content panels. This ensures users experience consistent interaction patterns regardless of which feature they access.

Figure 1 illustrates the WithOps landing page, which serves as the public-facing entry point of the platform. The design employs a dark-themed hero section with a prominent headline communicating the platform's core value proposition — "AI for Secure CI/CD Pipelines." An embedded code preview on the right demonstrates the platform's configuration structure, reinforcing the developer-focused identity. The top navigation bar provides access to Documentation, Security, Analytics, and Pricing sections, while an authenticated user greeting and Dashboard button indicate the Auth0 integration. The landing page was designed to establish immediate credibility and communicate the platform's technical sophistication to prospective users.

![Figure 1 — WithOps Landing Page](./screenshots/fig1_landing_page.png)
*Figure 1: The WithOps landing page featuring the hero section with code preview, navigation bar, and call-to-action button.*

---

## Chapter 07 — Implementation

### 7.1 Core Platform Features

The following features were fully implemented and deployed:

| Feature | Description |
|---|---|
| Auth0 Authentication | OAuth 2.0 + PKCE login flow with JWT validation and session management |
| GitHub OAuth/App Integration | OAuth App and GitHub App installation flows for repository access |
| Workflow Security Analysis | YAML parsing and vulnerability detection for 25+ patterns |
| DSOMM Maturity Assessment | Automated maturity scoring across all five DSOMM dimensions |
| Threat Modeling Canvas | Interactive visual canvas with STRIDE/CIA/LINDDUN AI analysis |
| Real-Time Collaboration | Multi-user cursor presence and shape sharing via Yjs and Liveblocks |
| AI RAG System | Context-aware AI chat with Qdrant vector-based semantic retrieval |
| Action Audit | Organisation-wide GitHub Actions version governance with auto-remediation |
| Canvas Builder | Visual CI/CD pipeline editor with YAML generation and PR creation |
| WebSocket Events | Live notification system via Events Hub with Redis pub/sub |
| In-App Documentation | Getting started guides, feature docs, API reference, deployment guides |
| Repository Tree View | File tree browser for connected repositories |
| Pipeline Prediction | ML-based CI/CD outcome prediction with accuracy tracking |
| DORA Metrics Dashboard | Four-metric delivery performance tracking with DSOMM correlation |

**GitHub Integration and Onboarding Flow.** The platform's onboarding process begins with GitHub App installation. When a user selects an organisation to connect, the platform redirects them to the GitHub App permissions consent screen (Figure 2), which requests the precise set of read and write permissions required for workflow analysis, webhook registration, and automated pull request creation. This granular permission model follows the principle of least privilege, requesting only the access necessary for platform functionality.

![Figure 2 — GitHub App Installation Permissions](./screenshots/fig2_github_app_install.png)
*Figure 2: The GitHub App installation consent screen showing the granular permissions requested by the WithOps platform, including read access to organisation metadata and read/write access to actions, workflows, and pull requests.*

After granting permissions, the user is returned to the WithOps Organisation Discovery page (Figure 3), which displays all GitHub organisations accessible to the authenticated user. Each organisation card indicates its installation status — "Installed" with an "Open Workspace" action, or "Not Installed" with an "Install GitHub App" action and step-by-step instructions. This two-state card design provides clear visual feedback about which organisations are connected and which require setup.

![Figure 3 — Organisation Discovery Page](./screenshots/fig3_org_discovery.png)
*Figure 3: The Organisation Discovery page displaying connected and available GitHub organisations with installation status indicators and action buttons.*

Once an organisation is connected, the user enters the Workspace Dashboard (Figure 4), which serves as the central command interface for the platform. The dashboard displays four stat cards summarising the organisation's repository count, total workflows, connection status, and last synchronisation time. Below, a tabbed interface switches between Repositories and Workflows views, with the Workflows tab presenting a table listing each CI/CD workflow with its trigger type, last run timestamp, success status, dependencies, author, and active status. The left sidebar provides navigation to all platform modules — Repo Tree, Threats, Audit, Canvas, Treeview, Predictor, and DORA — demonstrating the breadth of integrated functionality accessible from a single workspace.

![Figure 4 — Workspace Dashboard](./screenshots/fig4_workspace_dashboard.png)
*Figure 4: The Workspace Dashboard showing organisation stat cards, workflow listing with trigger types and execution history, and sidebar navigation to all platform modules.*

**Workflow Security Analysis Engine.** The security analysis engine parses GitHub Actions YAML files into structured representations and traverses them to detect vulnerability patterns. The detection system covers five major categories: unpinned action references (detecting mutable tag usage versus immutable commit SHA pinning), outdated action versions (comparing against GitHub Marketplace latest releases using semantic versioning), insecure workflow triggers (identifying `pull_request_target` and `workflow_dispatch` triggers vulnerable to code injection), excessive permissions (flagging `write-all` or overly broad permission scopes), and credential exposure (using both regex pattern matching against 150+ known secret formats and Shannon entropy calculation for detecting high-entropy strings). Each finding was categorised by severity (Critical, High, Medium, Low) using CVSS v3.1 scoring principles, with detailed remediation guidance generated for each vulnerability type.

**DSOMM Maturity Assessment System.** The automated maturity assessment system analyses repository artifacts to detect security practice indicators and maps them to the five OWASP DSOMM dimensions. The assessment algorithm inspects repository configurations including branch protection rules, CI/CD workflow definitions, dependency management configurations, secret scanning settings, and code review policies. For each dimension — Build and Deployment, Implementation, Test and Verification, Information Gathering, and Culture and Organization — the system assigns a maturity level from Level 0 (no practices detected) to Level 4 (advanced automation). The overall maturity score was computed as a weighted average across all dimensions, with results stored temporally to enable progression tracking over time. The Intelligence dashboard visualises dimensional scores using radar charts and provides trend analysis showing maturity improvement trajectories.

**Threat Modelling Canvas.** The interactive threat modelling canvas provides a visual drawing environment where users create system architecture diagrams using data flow diagram notation. Users place components representing processes, data stores, external entities, and trust boundaries, then connect them with data flow arrows. The canvas supports real-time multi-user collaboration through Yjs CRDT (Conflict-Free Replicated Data Types) for state synchronisation and Liveblocks for cursor presence tracking. When the user triggers AI analysis, the canvas is captured as an image and sent to Anthropic Claude's vision API, which identifies system components and generates threat analyses across three frameworks simultaneously: STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege), CIA triad (Confidentiality, Integrity, Availability), and LINDDUN (Linkability, Identifiability, Non-repudiation, Detectability, Disclosure of information, Unawareness, Non-compliance). The generated threats include severity classifications and specific mitigation recommendations.

**Action Audit.** The Action Audit module performs organisation-wide governance of GitHub Actions versions. It scans all workflow files across every repository in an organisation, extracting action references and comparing them against the latest available versions from the GitHub Marketplace. Each action was classified as "Up to Date," "Minor Update Available," "Major Upgrade Needed," or "Outdated." The module also performs anti-typosquatting verification by checking action names against the official GitHub Marketplace registry to detect potentially malicious look-alike actions. For outdated actions, the system generates automated pull requests that update action version references to the latest SHA-pinned versions, enabling one-click remediation across the organisation.

**Canvas Builder.** The Canvas Builder provides a visual drag-and-drop interface for constructing CI/CD pipelines. Users create pipeline stages by dragging pre-configured workflow step blocks (checkout, setup-node, install dependencies, run tests, build, deploy) onto a canvas and connecting them in execution order. The visual representation was then transformed into valid GitHub Actions YAML through a code generation algorithm that maps visual block properties to YAML configuration syntax. Users could preview the generated YAML, customise it, and create a pull request directly from the interface, eliminating the need for manual YAML authoring and reducing the error-prone nature of indentation-sensitive configuration.

### 7.2 DORA Metrics Dashboard

The DORA Metrics Dashboard represents a significant addition to the platform, providing quantitative delivery performance measurement based on the Google DORA research programme.

**Backend Implementation:**

The DORA subsystem was implemented within the Workspace Intelligence Service and comprises four components:

1. **Database Models** (`database/dora_models.py`): Two SQLAlchemy models were created. `DeploymentEvent` records individual GitHub workflow completions with fields for organisation, repository, event type (deployment, failure, recovery), duration, and commit SHA. `DORAMetricSnapshot` stores periodic metric computations for trend analysis.

2. **DORA Calculator** (`core/dora_calculator.py`): The calculator queries `DeploymentEvent` records within a configurable time window and computes all four DORA metrics:
   - *Deployment Frequency*: Total successful deployments divided by the period in days.
   - *Lead Time for Changes*: Median duration of successful deployment events in seconds.
   - *Change Failure Rate*: Ratio of failed deployments to total deployments.
   - *Mean Time to Recovery*: Average time between a failure event and the next successful deployment on the same repository.

   Each metric is independently classified against Google's DORA benchmarks (Elite, High, Medium, Low), and an overall classification is derived from the lowest individual classification — reflecting that delivery performance is constrained by the weakest metric.

3. **Event Handler** (`core/dora_event_handler.py`): A Redis subscriber listens to the `github_events` channel for `github.workflow_run.completed` messages. Upon receiving an event, it extracts the repository name, workflow outcome (success or failure), and execution duration, then persists a `DeploymentEvent` to the database. This enables fully automated, real-time data collection without manual intervention.

4. **API Router** (`api/routes/dora_metrics.py`): Five RESTful endpoints were implemented:
   - `GET /metrics` — Raw DORA metric values for a given period.
   - `GET /summary` — Formatted summary with classification badges and trend indicators.
   - `GET /trends` — Time-series data (weekly or monthly) for historical trend analysis.
   - `GET /repos` — Per-repository metric breakdowns.
   - `GET /correlation` — DORA performance correlated with DSOMM security maturity scores.

**Frontend Implementation:**

The DORA dashboard page (`dora/+page.svelte`) was built to strictly adhere to the established "Matte Engineering" design language, ensuring visual consistency with existing pages. The dashboard provides four navigable tabs:

- **Overview Tab:** Four stat cards displaying each DORA metric with its classification badge and trend arrow, a Google DORA benchmarks reference table, and a deployment summary.
- **Trends Tab:** A 12-week performance timeline showing per-week metrics, classification badges, and deployment activity bars.
- **Repositories Tab:** A per-repository breakdown table displaying all four metrics, classification level, and deployment count for each repository.
- **DORA × DSOMM Tab:** A correlation analysis panel displaying DSOMM maturity score alongside DORA performance classification, with an AI-generated insight describing the relationship between security maturity and delivery velocity.

**DORA × DSOMM Correlation — Novel Contribution:**

The correlation between DORA delivery metrics and DSOMM security maturity scores represents a novel analytical capability. The `/correlation` endpoint retrieves the organisation's latest DSOMM assessment (average maturity score across all assessed projects) and its current DORA performance classification, then generates an AI-derived insight describing whether higher security maturity correlates with improved delivery performance. This addresses the common misconception that "security slows development down" by providing empirical evidence within the organisation's own data.

### 7.3 Pipeline Prediction Service

The Pipeline Prediction Service provides ML-based forecasting of CI/CD pipeline outcomes. The service analyses historical workflow run data — including repository metadata, workflow configuration patterns, and past execution outcomes — to predict whether a forthcoming pipeline run will succeed or fail.

The prediction model was trained on historical GitHub Actions workflow data and deployed within the Workspace Intelligence Service. The frontend Predictor page displays prediction confidence scores and tracks accuracy over time by comparing predictions against actual outcomes received via webhook events.

### 7.4 AI and RAG Integration

The platform integrates AI capabilities through a multi-provider strategy:

- **Anthropic Claude:** Used for vision-based threat analysis of canvas diagrams and complex security reasoning.
- **Meta Llama 3 via Groq:** Used for faster inference on latency-sensitive operations.
- **Ollama (Local):** Used for embedding generation and local LLM inference at zero cost.

The RAG pipeline follows three stages: (1) workspace analysis data is chunked and embedded using Ollama's embedding models, with vectors stored in Qdrant collections; (2) user queries trigger semantic similarity search to retrieve relevant context; (3) retrieved context is combined with the query for Claude API inference, producing contextually grounded responses.

### 7.5 Key Implementation Challenges

**Challenge 1: DORA Data Collection Without Deployment Infrastructure.** The DORA metrics system required deployment event data, but many development organisations do not have formal deployment workflows. The solution was to treat any completed GitHub Actions workflow as a deployment proxy, which aligns with the DORA research definition that measures "code changes that result in software being built and tested."

**Challenge 2: Real-Time Event Pipeline Reliability.** The DORA Event Handler needed to reliably capture every `workflow_run.completed` event. Redis pub/sub was chosen over polling because it provides immediate event delivery. Error handling with retry logic ensured no events were lost during transient service disruptions.

**Challenge 3: Svelte 5 Runes API Migration.** The frontend was built using Svelte 5's new Runes API ($state, $derived, $effect), which replaced the legacy reactivity model. Several compiler errors were encountered, notably the `const_tag_invalid_placement` restriction where `{@const}` declarations could only appear as immediate children of block elements, requiring inline expression refactoring.

**Challenge 4: Windows Port Conflicts.** Default port numbers (8000–8008) conflicted with Windows reserved ports. All external port mappings were shifted to the 9100–9108 range while maintaining internal ports unchanged.

**Challenge 5: GitHub API Rate Limiting.** GitHub enforces 5,000 authenticated requests per hour. A multi-layered caching strategy was implemented using Redis with 24-hour TTL, intelligent request batching, and exponential backoff retry logic via the tenacity library.

**Challenge 6: Multi-Provider AI Orchestration.** Integrating three AI providers (Anthropic Claude, Groq/Llama 3, and Ollama) required a unified provider abstraction layer. Each provider exposed different API interfaces, authentication mechanisms, and response formats. A strategy pattern was implemented in the AI Service, where a provider factory selected the appropriate client based on the operation type — Claude for vision analysis, Groq for fast text inference, and Ollama for embedding generation. This abstraction enabled transparent provider switching and fallback behaviour without modifying calling code throughout the platform.

### 7.6 Observability and Monitoring

The WithOps platform implements a comprehensive observability stack to ensure the reliability and performance of its distributed microservices architecture. This is achieved through the integration of Prometheus for metric collection and Grafana for real-time visualization and alerting.

**Metric Collection with Prometheus.** Every microservice in the platform exposes a `/metrics` endpoint instrumented with Prometheus client libraries. The Prometheus server is configured to perform service discovery via Docker DNS, automatically scraping metrics from all 12+ backend components, including microservices, databases (PostgreSQL/Supabase), and caches (Redis). Figure 5 illustrates the Prometheus targets dashboard, confirming that all system components are "UP" and actively being monitored. This centralized health check capability was critical for debugging inter-service connectivity during development.

![Figure 5 — Prometheus Targets and Service Health](./screenshots/fig5_prometheus_targets.png)
*Figure 5: The Prometheus status dashboard showing all microservices, databases, and gateway components in a healthy "UP" state.*

**Visualization with Grafana.** For real-time monitoring and performance analysis, the platform uses Grafana dashboards connected to the Prometheus data source. Each microservice has a dedicated monitoring dashboard (Figure 6) that visualizes critical signals:
- **Traffic:** HTTP request rates (requests/sec) broken down by endpoint and status code.
- **Latency:** Request duration tracking, specifically focusing on the 95th percentile (P95) to identify slow responses that impact user experience.
- **Saturation:** Real-time memory and CPU usage per container, enabling early detection of resource leaks.
- **Uptime:** Continuous monitoring of service availability.

![Figure 6 — Service Performance Monitoring Dashboard](./screenshots/fig6_grafana_service_dashboard.png)
*Figure 6: A Grafana dashboard for the GitHub Service visualizing request rates, P95 latency (under 10ms), and memory usage (115 MiB).*

The platform maintains a centralized directory of dashboards (Figure 7), providing an "at-a-glance" overview of the entire organization's technical health. This unified observability layer allows for rapid incident response and performance tuning, ensuring that the platform remains responsive even under heavy concurrent analysis loads.

![Figure 7 — Centralized Monitoring Dashboard Directory](./screenshots/fig7_grafana_dashboard_list.png)
*Figure 7: The Grafana dashboard index showing dedicated monitoring configurations for AI, Auth, Collaboration, and Intelligence services.*

---

## Chapter 08 — End-Project Report

### 8.1 Project Summary

The WithOps DevSecOps Intelligence Platform was successfully designed, implemented, and deployed as a comprehensive system addressing critical gaps in CI/CD workflow security analysis, DevSecOps maturity assessment, AI-assisted threat modelling, pipeline outcome prediction, and delivery performance measurement. The platform comprises nine independently deployable FastAPI microservices, a SvelteKit 5 frontend application, a Kong API gateway, and a full observability stack, all orchestrated through Docker Compose and deployable on Kubernetes. The completed system is publicly accessible at https://app.withops.com/.

### 8.2 Objectives Evaluation

Each project objective is evaluated below with an honest assessment of achievement:

**Objective 1: GitHub Workflow Security Analysis Engine — Achieved.** The security analysis engine successfully detects 25+ vulnerability patterns across GitHub Actions workflows, including unpinned actions, outdated versions, insecure triggers, hardcoded secrets, and excessive permissions. The engine parses valid workflows reliably and completes organisation-wide analysis within acceptable time bounds. However, the false positive rate was not formally measured against the target of below 5%, which would require a larger manually-verified ground truth dataset than was available.

**Objective 2: DSOMM Maturity Assessment System — Achieved.** The system automatically maps detected security practices to all five DSOMM dimensions and computes maturity levels from Level 0 through Level 4. Maturity progression is tracked over time. The correlation with DORA metrics provides an additional analytical dimension not originally specified. Assessment consistency was observed to be stable on repeated evaluations, though formal variance measurement against independent auditor assessments was not conducted.

**Objective 3: AI-Powered Threat Modelling Canvas — Achieved.** The interactive visual canvas supports system architecture diagram creation with multi-framework threat analysis (STRIDE, CIA, LINDDUN). Real-time multi-user collaboration was implemented using Yjs CRDTs and Liveblocks cursor presence. AI-generated threat analyses cover relevant threat categories, though accuracy measurement against a 90% target would require structured expert evaluation.

**Objective 4: RAG-Based Learning System — Achieved.** The Retrieval-Augmented Generation system using Qdrant vector database enhances AI responses with workspace-specific security context. Semantic search retrieves relevant context effectively, and RAG-enhanced responses demonstrate improved accuracy over base model responses in informal evaluation. Formal measurement against the 85% retrieval accuracy target was not completed.

**Objective 5: Production-Grade Microservices Architecture — Achieved.** Nine independent microservices were deployed, communicating via Redis event bus and Kong API gateway. Services deploy independently and the system tolerates individual service failure with graceful degradation. The architecture exceeded the original specification of eight services by adding the AI RAG Service as a dedicated component.

**Objective 6: Production-Ready Frontend Application — Achieved.** The SvelteKit application provides interactive dashboards, visual workflow representation, collaborative threat modelling, pipeline prediction, DORA metrics, and comprehensive in-app documentation. The "Matte Engineering" design language provides a consistent, professional user experience across all features.

**Objective 7: Pipeline Prediction Service — Achieved.** The ML-based pipeline prediction system was implemented, providing outcome forecasting with confidence scores. The Predictor dashboard tracks accuracy over time by reconciling predictions against actual webhook outcomes.

**Objective 8: DORA Metrics Dashboard — Achieved.** The DORA metrics system automatically computes all four metrics from GitHub webhook events, classifies performance against Google benchmarks, provides weekly trend analysis, per-repository breakdowns, and the novel DORA × DSOMM correlation analysis. This objective was added during the project lifecycle and was fully delivered.

### 8.3 Changes During the Project

Several significant changes were made during the project:

**Architecture Evolution:** The original specification included eight microservices. A ninth service — the AI RAG Service — was separated from the AI Service to provide dedicated conversational AI and vector search capabilities, improving separation of concerns and independent scalability.

**DORA Metrics Addition:** The DORA Metrics Dashboard was added as a new feature during the later stages of the project. This addition was motivated by the recognition that quantitative delivery performance measurement would strengthen the platform's value proposition and provide a unique research contribution through DORA × DSOMM correlation analysis.

**Pipeline Prediction Addition:** The Pipeline Prediction Service was added to provide proactive CI/CD failure prevention, complementing the existing reactive security analysis capabilities.

**Frontend Framework Version:** The frontend was built with Svelte 5's Runes API rather than the originally planned Svelte 4 syntax, representing a more modern approach leveraging compile-time reactivity.

**AI Provider Expansion:** Groq (Meta Llama 3) was added as a third AI provider beyond the originally planned Claude and Ollama, enabling faster inference for latency-sensitive operations.

---

## Chapter 09 — Project Post-Mortem

### 9.1 Were the Objectives Right?

The original six objectives proved to be well-chosen foundations for the platform. The subsequent addition of Pipeline Prediction and DORA Metrics objectives strengthened the project by providing quantitative measurement capabilities that transformed the platform from a purely analytical tool into a comprehensive intelligence system.

In retrospect, the DORA Metrics objective should have been included from the initial specification. The ability to measure delivery performance and correlate it with security maturity is central to the platform's value proposition and represents the strongest research contribution. Its late addition, while successfully delivered, meant less time was available for comprehensive testing and user evaluation of this feature.

### 9.2 Technology Evaluation

**SvelteKit 5 and Svelte 5 Runes API:** This technology choice proved excellent. The compile-time reactivity model produced smaller bundle sizes and faster rendering than alternatives. However, the Runes API was relatively new, resulting in limited community documentation and occasional compiler quirks (e.g., the `const_tag_invalid_placement` restriction). The benefits of early adoption outweighed these minor difficulties.

**FastAPI:** An excellent choice for the microservices backend. Native async/await support, automatic OpenAPI documentation, and Python compatibility with AI/ML libraries made it the ideal framework. Performance was consistently within acceptable bounds.

**Redis Pub/Sub:** Effective for the event-driven architecture but presented a limitation: if a subscriber service is temporarily offline, published messages are lost. For production deployment, a message queue with persistence (such as RabbitMQ or Apache Kafka) would provide better durability guarantees.

**Kong API Gateway:** Production-proven and reliable. The declarative YAML configuration simplified route management. Rate limiting and CORS enforcement worked as expected.

**Docker Compose:** Essential for managing the 16+ container development environment. However, the resource consumption on development machines (particularly RAM) was substantial and occasionally problematic on machines with less than 16 GB RAM.

### 9.3 Process Evaluation

The Agile methodology with two-week sprints proved appropriate for the project scope. Sprint structure provided regular checkpoints and forced prioritisation. However, several process observations emerged:

The feature-branch Git workflow ensured code quality through pull request reviews, though as a single-developer project, the review process was necessarily self-directed. More rigorous peer review would have been beneficial.

Sprint planning was occasionally disrupted by the discovery of blocking technical challenges (e.g., GitHub API rate limiting, Windows port conflicts) that consumed sprint capacity. Building more buffer time into sprint estimates would have improved delivery predictability.

### 9.4 Personal Performance

Technical skills in full-stack development, microservices architecture, and AI integration were significantly strengthened through this project. Key areas of growth included:

- **Distributed systems design:** Practical experience with event-driven architecture, service orchestration, and fault tolerance.
- **AI/ML integration:** Hands-on implementation of RAG systems, multi-provider AI strategies, and pipeline prediction models.
- **DevSecOps domain knowledge:** Deep understanding of DSOMM frameworks, DORA metrics, CI/CD security patterns, and threat modelling methodologies.

Areas requiring improvement include automated testing discipline (the target 80% coverage was not achieved) and documentation completeness during active development phases.

### 9.5 Lessons Learned

1. **Start with observability.** Implementing the Prometheus/Grafana/Jaeger/Loki stack early proved invaluable for debugging inter-service communication issues. Future projects should establish observability infrastructure before feature development begins.

2. **Design for data collection from day one.** The DORA Metrics feature required historical deployment event data. Because the webhook event pipeline was already operational, retroactive data collection was possible. Features that depend on historical data should be planned early to maximise the data collection window.

3. **Automated testing is non-negotiable.** The project's testing coverage fell below target, creating uncertainty about edge case behaviour in production. Future projects should enforce minimum coverage gates in CI/CD pipelines.

4. **Security maturity and delivery velocity are not opposed.** The DORA × DSOMM correlation analysis provides early evidence that investing in security practices does not necessarily reduce delivery speed — a finding with significant implications for the industry.

5. **Microservices complexity must be justified.** Nine services provided excellent separation of concerns and independent scalability, but significantly increased operational complexity. For smaller teams, a modular monolith with clear domain boundaries might achieve similar benefits with reduced overhead.

6. **Event-driven architecture enables extensibility.** The Redis pub/sub event bus proved critical for adding new features without modifying existing services. The DORA Event Handler was added to the Workspace Intelligence Service without any changes to the GitHub Service — it simply subscribed to existing events. This pattern demonstrates how event-driven architecture supports organic feature growth in complex systems.

7. **Design language consistency improves user trust.** The "Matte Engineering" design system — with its consistent CSS variables, typography, layout patterns, and interaction models — meant that new pages (Predictor, DORA) felt immediately familiar to users already accustomed to the Intelligence page. This consistency significantly reduced the perceived learning curve for new features and reinforced the professional quality of the platform.

8. **AI provider diversity is essential.** Relying on a single AI provider introduces both availability and cost risks. The multi-provider strategy (Claude for vision analysis, Groq for speed, Ollama for zero-cost local inference) provided resilience and cost optimisation. When one provider experienced latency spikes, requests could be routed to alternatives without service disruption.

---

## Chapter 10 — Conclusions

The WithOps DevSecOps Intelligence Platform was successfully designed, implemented, and deployed as a comprehensive system that addresses five critical challenges facing modern software development organisations: CI/CD workflow security vulnerabilities, DevSecOps maturity measurement, disconnected threat modelling, CI/CD pipeline reliability, and delivery performance quantification.

The platform's nine-microservice architecture demonstrates that production-grade distributed systems can be developed within an academic project scope when supported by appropriate tooling (Docker, Kong, Redis) and development practices (Agile sprints, feature-branch workflow, CI/CD automation). All eight project objectives were achieved, with the DORA Metrics and Pipeline Prediction features representing additions that exceeded the original project scope.

The most significant contribution of this project is the DORA × DSOMM correlation capability — the ability to quantitatively measure the relationship between an organisation's security maturity and its delivery performance within a single integrated platform. This addresses a gap in both academic literature and commercial tooling, where security assessment and delivery metrics have traditionally been treated as separate concerns. Early evidence from the platform suggests that security investment and delivery velocity are complementary rather than antagonistic, though this finding requires validation with larger datasets and longitudinal studies.

**Recommendations for Future Work:**

Several enhancements would strengthen the platform for production deployment. First, extending CI/CD platform support beyond GitHub Actions to include GitLab CI, Jenkins, and Azure DevOps pipelines would broaden the platform's applicability. Second, implementing runtime workflow monitoring alongside the existing static analysis would provide a more comprehensive security assessment. Third, adding exportable compliance reports formatted for SOC 2 Type II, ISO 27001, and EU Cyber Resilience Act audits would enhance the platform's value for regulated organisations. Fourth, conducting a longitudinal study with a larger sample of organisations to validate the DORA × DSOMM correlation hypothesis would strengthen the academic contribution. Finally, comprehensive load testing and performance benchmarking under realistic production loads would provide confidence in the platform's scalability claims.

The platform's current limitations — including GitHub-only support, static analysis focus, and incomplete automated testing coverage — present clear directions for future work. Extension to GitLab CI and Jenkins pipelines, implementation of runtime workflow monitoring, and comprehensive load testing would strengthen the platform's production readiness. The addition of exportable compliance reports for SOC 2 and ISO 27001 audits would enhance the platform's commercial viability.

WithOps demonstrates that a unified, AI-enhanced DevSecOps intelligence platform can substantially automate security assessment processes that previously demanded significant manual effort, while simultaneously providing the quantitative delivery metrics that enable evidence-based process improvement.

---

## Reference List

- Ayala, C. and Garcia, J. (2023) *An empirical study of security practices in GitHub repositories*, arXiv preprint arXiv:2305.16120. Available at: https://arxiv.org/abs/2305.16120 (Accessed: 3 January 2026).

- Forsgren, N., Humble, J. and Kim, G. (2018) *Accelerate: The Science of Lean Software and DevOps*. Portland, OR: IT Revolution Press.

- Hassan, A.E. and Zhang, K. (2006) 'Using decision trees to predict the certification result of a build', in *Proceedings of the 21st IEEE/ACM International Conference on Automated Software Engineering*. IEEE, pp. 189–198.

- IBM Security (2023) *Cost of a Data Breach Report 2023*. IBM Corporation. Available at: https://www.ibm.com/reports/data-breach (Accessed: 15 January 2026).

- Jit (2024) *From DSOMM theory to practical enforcement: A DevSecOps journey*. Available at: https://www.jit.io/resources/devsecops/from-dsomm-theory-to-practical-enforcement-a-devsecops-journey (Accessed: 3 January 2026).

- OWASP Foundation (2024) *DevSecOps Maturity Model (DSOMM)*. Available at: https://owasp.org/www-project-devsecops-maturity-model/ (Accessed: 3 January 2026).

- Pan, X., Liu, Y., Zhang, Y. and Wang, X. (2024) *CI/CD under the hood: Vulnerabilities and threats in modern pipelines*, arXiv preprint arXiv:2401.17606. Available at: https://arxiv.org/abs/2401.17606 (Accessed: 3 January 2026).

- Saroar, M. and Nayebi, M. (2023) *Practitioners' perceptions of GitHub Actions and workflow automation*, arXiv preprint arXiv:2303.04084. Available at: https://arxiv.org/abs/2303.04084 (Accessed: 3 January 2026).

- Shevchenko, N., Chick, T.A., O'Riordan, P., Scanlon, T.P. and Woody, C. (2018) *Threat Modeling: A Summary of Available Methods*. Technical Report CMU/SEI-2018-TR-001. Software Engineering Institute, Carnegie Mellon University.

- Sonatype (2024) *State of the Software Supply Chain Report 2024*. Available at: https://www.sonatype.com/state-of-the-software-supply-chain (Accessed: 10 February 2026).

- Unit42 (2025) *GitHub Actions supply chain attack analysis: tj-actions/changed-files compromise*. Palo Alto Networks Unit 42. Available at: https://unit42.paloaltonetworks.com/github-actions-supply-chain-attack/ (Accessed: 3 January 2026).

- Yampolskiy, M., King, W.E., Gatlin, J., Belikovetsky, S., Brown, A., Skjellum, A. and Elovici, Y. (2022) 'Security of additive manufacturing: Attack taxonomy and survey', *Additive Manufacturing*, 21, pp. 431–457.

- Yılmaz, İ. and Gönen, S. (2023) 'LLM-assisted threat modeling for software systems', *Journal of Information Security and Applications*, 78, 103614.

---

## Bibliography

- Bass, L., Weber, I. and Zhu, L. (2015) *DevOps: A Software Architect's Perspective*. Boston, MA: Addison-Wesley Professional.

- Kim, G., Humble, J., Debois, P. and Willis, J. (2016) *The DevOps Handbook*. Portland, OR: IT Revolution Press.

- Newman, S. (2021) *Building Microservices*. 2nd edn. Sebastopol, CA: O'Reilly Media.

- Richardson, C. (2018) *Microservices Patterns*. Shelter Island, NY: Manning Publications.

- Shostack, A. (2014) *Threat Modeling: Designing for Security*. Indianapolis, IN: Wiley.

- OWASP Foundation (2021) *OWASP Top Ten 2021*. Available at: https://owasp.org/www-project-top-ten/ (Accessed: 10 January 2026).

- Docker, Inc. (2024) *Docker Documentation*. Available at: https://docs.docker.com/ (Accessed: 15 January 2026).

- Kong Inc. (2024) *Kong Gateway Documentation*. Available at: https://docs.konghq.com/ (Accessed: 20 January 2026).

---

## Appendices

### Appendix A — User Guide

**Installation and Demonstration**

The WithOps platform can be installed for demonstration using the following steps:

**Minimum Platform Specification:**
- Operating System: Windows 10+ (with WSL2), macOS 12+, or Ubuntu 22.04+
- CPU: 4 cores
- RAM: 8 GB (16 GB recommended)
- Storage: 20 GB available
- Docker Desktop 24.0+ with Docker Compose v2
- Node.js 18+ LTS

**Installation Steps:**

1. Clone the repository: `git clone https://github.com/NimanthaSupun/WithOps.git`
2. Copy `.env.example` to `.env` and configure environment variables (Auth0 credentials, GitHub App credentials, API keys for Claude/Groq).
3. Start all services: `docker compose up -d`
4. Start the frontend: `cd frontend && npm install && npm run dev`
5. Access the application at `http://localhost:5173`
6. Access Kong API Gateway at `http://localhost:9000`

**System Operation:**

- **Authentication:** Users authenticate via Auth0 login. After authentication, they connect their GitHub organisation through OAuth or GitHub App installation.
- **Workspace Dashboard:** Displays organisation overview with repository count, security posture, and navigation to all features.
- **Security Analysis:** Select a repository to run workflow security analysis. Results display vulnerability findings categorised by severity.
- **DSOMM Assessment:** Navigate to Intelligence page to run maturity assessments across all connected repositories.
- **Threat Modelling:** Access the Threat Modeling canvas to draw system architecture diagrams and run AI-powered threat analysis.
- **DORA Metrics:** Navigate to the DORA page to view delivery performance metrics. Data populates automatically as GitHub Actions workflows complete.
- **Pipeline Predictor:** Access the Predictor page to view pipeline outcome predictions and accuracy tracking.

### Appendix B — Microservices Port Mapping

| Service | Internal Port | External Port | Kong Route |
|---|:---:|:---:|---|
| Kong Gateway | 8000 | 9000 | — (Entry Point) |
| Events Hub | 8000 | 9100 | /api/events/* |
| AI Service | 8001 | 9101 | /api/ai/* |
| GitHub Service | 8002 | 9102 | /api/github/* |
| Threat Modeling | 8003 | 9103 | /api/threat-modeling/* |
| Workspace Intelligence | 8004 | 9104 | /api/workspace-intelligence/*, /api/dora/* |
| Collaboration | 8105 | 9105 | /api/collaboration/* |
| Auth Service | 8006 | 9106 | /api/auth/* |
| Workflow Orchestration | 8007 | 9107 | /api/workflows/*, /api/canvas/* |
| AI RAG Service | 8008 | 9108 | /api/rag/*, /api/conversations/* |

### Appendix C — DORA Metrics Classification Thresholds

| Metric | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deployment Frequency | Multiple/day | Weekly–Daily | Monthly–Weekly | < Monthly |
| Lead Time for Changes | < 1 hour | < 1 day | < 1 week | > 1 week |
| Change Failure Rate | 0–5% | 5–15% | 15–30% | > 30% |
| Mean Time to Recovery | < 1 hour | < 1 day | < 1 week | > 1 week |

*Source: Forsgren, Humble and Kim (2018) and Google DORA team research.*

### Appendix D — CI/CD Workflow Configurations

The project repository includes the following CI/CD workflow definitions:

- **ci-caller.yml** — Triggers the reusable CI pipeline on push to main branch.
- **reusable-ci.yml** — Reusable workflow with checkout, Node.js setup, install, test, and build stages.
- **test.yml** — Basic CI pipeline for push and PR events.
- **gitleaks.yaml** — Organisation-wide secret scanning across all repositories.
- **trufflehog.yaml** — PR enforcement with JIRA ticket validation.
