# PUSL3190 Computing Project — Interim Report

**DevSecOps Intelligence Platform for GitHub Workflow Security and Threat Modeling**

---

**Name:** Ilukwaththe Ariyarathne

**Plymouth Index Number:** 10953742

**Degree Programme:** BSc (Hons) Data Science

**Supervisor:** Prof. Chaminda Wijesinghe

**Submission Date:** 05th March 2026

---

## Table of Contents

- Chapter 01 — Introduction
  - 1.1 Introduction
  - 1.2 Problem Definition
  - 1.3 Project Objectives
- Chapter 02 — System Analysis
  - 2.1 Facts Gathering Techniques
  - 2.2 Existing System
  - 2.3 Drawbacks of the Existing System
- Chapter 03 — Requirements Specification
  - 3.1 Functional Requirements
  - 3.2 Non-Functional Requirements
  - 3.3 Hardware / Software Requirements
  - 3.4 Networking Requirements
- Chapter 04 — Feasibility Study
  - 4.1 Operational Feasibility
  - 4.2 Economical Feasibility
  - 4.3 Technical Feasibility
- Chapter 05 — System Architecture
  - 5.1 Use Case Diagram
  - 5.2 Class Diagram of Proposed System
  - 5.3 ER Diagram
  - 5.4 High-Level Architectural Diagram
  - 5.5 Networking Diagram
- Chapter 06 — Development Tools and Technologies
  - 6.1 Development Methodology
  - 6.2 Programming Languages and Tools
  - 6.3 Third-Party Components and Libraries
  - 6.4 Algorithms
- Chapter 07 — Implementation Progress
  - 7.1 Development Environment Setup
  - 7.2 Implemented Features
  - 7.3 Screenshots / Code Snippets
  - 7.4 Challenges Encountered and Solutions
  - 7.5 Current System Limitations
- Chapter 08 — Discussion
- References
- Appendices

---

## List of Figures

- Figure 5.1 — Use Case Diagram
- Figure 5.2 — High-Level Microservices Architecture Diagram
- Figure 5.3 — ER Diagram (Logical Data Model)
- Figure 5.4 — Network and Deployment Topology Diagram
- Figure 7.1 — Landing Page
- Figure 7.2 — Platform Overview Page
- Figure 7.3 — Auth0 Login Page
- Figure 7.4 — Workspace Dashboard

## List of Tables

- Table 3.1 — Functional Requirements Specification
- Table 3.2 — Non-Functional Requirements Specification
- Table 3.3 — Hardware and Software Requirements
- Table 5.1 — Microservices Port Mapping and Responsibilities
- Table 6.1 — Technology Stack Summary
- Table 6.2 — Third-Party Libraries and Components
- Table 7.1 — Implemented Features Status Matrix

---

## Chapter 01 — Introduction

### 1.1 Introduction

Modern software development relies extensively on Continuous Integration and Continuous Deployment (CI/CD) pipelines to automate build, test, and deployment processes. Platforms such as GitHub Actions have become the de facto standard for CI/CD automation, enabling development teams to define complex workflows using YAML configuration files. While this automation has dramatically accelerated software delivery, it has simultaneously introduced a new and largely unaddressed category of security vulnerabilities. Research by Pan et al. (2024) reveals that over 60% of CI/CD pipelines contain critical misconfigurations, transforming them into attractive targets for supply chain attacks. The March 2025 compromise of the tj-actions/changed-files GitHub Action demonstrated the catastrophic potential of such vulnerabilities, where a single compromised component affected thousands of dependent projects across the software ecosystem (Unit42, 2025).

DevSecOps — the integration of security practices into every phase of the software development lifecycle — has emerged as the industry response to these challenges. The OWASP DevSecOps Maturity Model (DSOMM) provides a structured framework for organisations to assess and improve their security posture across five critical dimensions: Build and Deployment, Implementation, Test and Verification, Information Gathering, and Culture and Organization. However, a significant gap persists between theoretical frameworks and practical implementation. Organisations understand the importance of DevSecOps maturity but lack automated tools to continuously assess their posture, detect workflow vulnerabilities, and model threats within their development infrastructure.

This project, named **WithOps**, addresses this gap by delivering an intelligent DevSecOps platform that unifies three critical capabilities: automated GitHub Actions workflow security analysis, DSOMM-based maturity scoring, and AI-assisted threat modelling. By integrating these capabilities into a single, developer-friendly platform built on a production-grade microservices architecture, WithOps enables organisations to proactively identify vulnerabilities, objectively measure security improvements, and maintain secure development practices without sacrificing delivery velocity. The platform is currently hosted and publicly accessible at **https://app.withops.com/**.

The platform is designed as a comprehensive intelligence layer that sits atop existing GitHub infrastructure, providing organisation-wide visibility into CI/CD security posture. It leverages multiple AI providers — including Anthropic Claude, Meta Llama 3 via Groq, and locally hosted models through Ollama — to deliver intelligent threat analysis, automated remediation recommendations, and conversational security insights through a Retrieval-Augmented Generation (RAG) system. The solution targets development teams, security engineers, DevOps practitioners, and engineering managers who require actionable, real-time security intelligence.

### 1.2 Problem Definition

Organisations face four critical, interconnected challenges in securing their CI/CD workflows that the current tooling landscape fails to address comprehensively.

**First, workflow misconfigurations remain undetected until exploited.** GitHub Actions workflows frequently contain unpinned dependencies referencing mutable tags rather than immutable commit SHAs, excessive permissions granting unnecessary access, insecure triggers vulnerable to code injection, and leaked credentials embedded in configuration files. Traditional security tools focus on application source code analysis and entirely miss these workflow-level vulnerabilities. Pan et al. (2024) found that 73% of actions are pinned to mutable tags, 41% have excessive permissions, and 15% contain hardcoded secrets — demonstrating the pervasive nature of these misconfigurations.

**Second, organisations cannot objectively measure their DevSecOps maturity.** While OWASP DSOMM provides a theoretical framework defining maturity levels from basic awareness (Level 0) to advanced automation (Level 4), manual assessment requires 40–80 hours per evaluation cycle (Jit, 2024). This makes continuous monitoring impractical and prevents organisations from demonstrating security improvements to stakeholders, regulatory auditors, or customers requiring security attestations. No existing tool automatically derives maturity scores from observable repository artifacts.

**Third, threat modelling remains disconnected from development workflows.** Traditional threat modelling tools require separate processes, specialised security expertise, and significant time investment — Shevchenko et al. (2018) report that moderately complex system assessments require 40–60 hours. This leads many development teams to skip threat modelling entirely, creating unidentified attack surfaces in their systems. Furthermore, existing tools lack integration with development platforms and do not leverage modern AI capabilities for automated threat identification.

**Fourth, GitHub Actions YAML complexity creates barriers to secure workflow development.** Saroar and Nayebi (2023) surveyed 394 practitioners and found that 60.87% consider YAML syntax error-prone, with workflow debugging consuming an average of 6.3 hours per developer monthly. The cognitive load of indentation-sensitive syntax combined with domain-specific GitHub Actions semantics results in workflows that are difficult to author, review, and secure. Additionally, 71% of workflows are derived from templates (Yampolskiy et al., 2022), amplifying the propagation of insecure patterns across organisations.

These challenges collectively manifest as increased supply chain attack risk, compliance failures, wasted developer productivity, and an inability to demonstrate measurable security improvements to stakeholders.

### 1.3 Project Objectives

The WithOps platform defines six specific, measurable project objectives:

1. **Develop a GitHub Workflow Security Analysis Engine** — The platform shall analyse GitHub Actions YAML files to detect 25+ vulnerability patterns including unpinned actions, outdated versions, insecure triggers, hardcoded secrets, and excessive permissions. The engine shall parse 99%+ of valid workflows without errors, complete organisation-wide analysis for up to 200 repositories within 3 minutes, and maintain a false positive rate below 5% for critical findings.

2. **Implement a DSOMM Maturity Assessment System** — The system shall automatically map detected security practices to all five DSOMM dimensions (Build and Deployment, Implementation, Culture and Organization, Information Gathering, Test and Verification), computing maturity scores from Level 0 through Level 4 and tracking progression over time. Assessment consistency shall be within 2% variance on repeated evaluations.

3. **Build an AI-Powered Threat Modelling Canvas** — An interactive visual canvas shall enable system architecture diagram creation using data flow diagram notation, with AI analysing diagrams using STRIDE, CIA triad, and LINDDUN privacy frameworks. AI shall identify system components with 90%+ accuracy and generate comprehensive threat analyses covering all relevant threat categories.

4. **Develop a RAG-Based Learning System** — A Retrieval-Augmented Generation system using Qdrant vector database shall enhance AI responses with contextual DevSecOps security knowledge. Semantic search shall retrieve relevant context in top 5 results with 85%+ accuracy, and RAG-enhanced responses shall be rated more accurate than base model responses in 70%+ of evaluated comparisons.

5. **Create a Production-Grade Microservices Architecture** — Eight independent microservices (Events Hub, GitHub Service, AI Service, Threat Modeling Service, Workspace Intelligence Service, Auth Service, Collaboration Service, Workflow Orchestration Service) shall communicate via Redis event bus and Kong API gateway. Services shall deploy independently, and the system shall tolerate individual service failure with graceful degradation.

6. **Build a Production-Ready Frontend Application** — A modern SvelteKit web application shall provide interactive dashboards, visual workflow representation, collaborative threat modelling with real-time multi-user support, and comprehensive documentation. First contentful paint shall be under 1.5 seconds and task completion rate shall exceed 85% for core workflows.

---

## Chapter 02 — System Analysis

### 2.1 Facts Gathering Techniques

The system analysis phase employed multiple structured fact-gathering techniques to ensure a comprehensive understanding of the problem domain and stakeholder requirements.

**Literature Review and Academic Research:** An extensive review of academic publications was conducted across four research domains — DevSecOps maturity modelling, CI/CD pipeline security, GitHub Actions complexity, and threat modelling automation. Key sources included Pan et al. (2024) on CI/CD vulnerabilities, Saroar and Nayebi (2023) on GitHub Actions practitioner perceptions, Shevchenko et al. (2018) on threat modelling methodologies, and the OWASP Foundation's DSOMM documentation. This review identified specific quantitative benchmarks (e.g., 62.3% pipeline misconfiguration rate, 60.87% YAML difficulty rating) that informed feature prioritisation.

**Industry Report Analysis:** Reports from Palo Alto Networks Unit 42, Jit, and OWASP were analysed to understand real-world incident patterns. The March 2025 tj-actions/changed-files supply chain attack provided a critical case study demonstrating the practical impact of workflow security failures and the inadequacy of existing defensive measures.

**Existing Tool Evaluation:** A systematic evaluation of existing DevSecOps tools was conducted, including GitHub Dependabot, Harness, Snyk, StepSecurity, and OWASP ZAP. Each tool was assessed against criteria including CI/CD workflow analysis coverage, DSOMM integration capability, threat modelling automation, and developer experience. This evaluation confirmed the absence of any unified platform addressing all identified requirements.

**GitHub API Documentation Analysis:** Extensive analysis of the GitHub REST API (v3) and GraphQL API (v4) documentation was performed to understand data access patterns, rate limiting constraints (5,000 requests/hour for authenticated users), webhook event structures, and GitHub App permission models. This informed the design of the GitHub Service microservice and caching strategy.

**Regulatory Framework Review:** Key regulatory and compliance frameworks were reviewed, including the EU Cyber Resilience Act, Executive Order 14028, SOC 2 Type II requirements, and ISO 27001 controls, to understand the compliance evidence requirements that WithOps must support.

### 2.2 Existing System

The current landscape for DevSecOps workflow security is characterised by fragmented, single-purpose tools that address individual security concerns without integration.

**GitHub Dependabot** provides automated dependency vulnerability scanning and pull request generation for outdated packages. It monitors package manifests (package.json, requirements.txt, etc.) and creates pull requests when security advisories are published. However, Dependabot focuses exclusively on application dependencies and does not analyse GitHub Actions workflow configurations, CI/CD pipeline security, or DevSecOps maturity.

**Harness** offers a comprehensive CI/CD orchestration platform with pipeline management, deployment automation, and some security scanning capabilities. It provides workflow visualisation and execution management but does not incorporate DSOMM maturity assessment, automated threat modelling, or granular GitHub Actions security analysis.

**StepSecurity Harden-Runner** provides runtime security monitoring for GitHub Actions workflows, detecting anomalous network connections and file system modifications during workflow execution. While it addresses runtime security, it does not perform static analysis of workflow configurations, assess organisational maturity, or provide threat modelling capabilities.

**Snyk** offers application security testing including SAST, SCA, container scanning, and infrastructure-as-code analysis. It integrates with CI/CD pipelines to identify application-level vulnerabilities but does not specifically target GitHub Actions workflow security patterns, DSOMM assessment, or collaborative threat modelling.

**Manual Processes:** In the absence of comprehensive automated tools, organisations rely on manual security reviews of workflow files, periodic compliance audits, and ad-hoc threat modelling sessions using tools like Microsoft Threat Modeling Tool or OWASP Threat Dragon. These manual processes are resource-intensive, inconsistent, and scale poorly with growing repository counts.

### 2.3 Drawbacks of the Existing System

The existing tooling landscape exhibits several critical drawbacks that WithOps is designed to address:

- **Fragmented Coverage:** No single platform provides unified workflow security analysis, maturity assessment, and threat modelling. Organisations must integrate 4–6 separate tools, increasing complexity and creating visibility gaps between tool boundaries.

- **No DSOMM Automation:** Existing tools do not automatically assess DevSecOps maturity against the OWASP DSOMM framework. Manual assessment requires 40–80 hours per cycle, making continuous monitoring impractical.

- **Application-Focused Analysis:** Tools like Dependabot and Snyk analyse application code and dependencies but miss CI/CD workflow infrastructure vulnerabilities — the exact attack vector exploited in recent supply chain attacks.

- **Disconnected Threat Modelling:** Threat modelling tools operate independently from development platforms, requiring context switching and manual data entry. This disconnect results in 67% of development teams skipping threat modelling entirely.

- **Limited AI Integration:** Existing tools offer minimal AI-assisted analysis, requiring manual interpretation of scan results and manual threat identification. No tool provides AI-powered visual threat analysis or conversational security insights via RAG.

- **Poor Developer Experience:** Current tools provide raw findings without actionable remediation guidance, visualisation of workflow security posture, or automated fix generation. This contributes to security alert fatigue and low remediation rates.

- **No Automated Remediation:** While Dependabot generates dependency update PRs, no tool automatically creates pull requests to fix GitHub Actions version pinning, permission scoping, or trigger hardening issues.

---

## Chapter 03 — Requirements Specification

### 3.1 Functional Requirements

The WithOps platform specifies the following functional requirements, organised by feature module:

**FR-01: GitHub Integration**

1: The system shall authenticate users via GitHub OAuth 2.0 and GitHub App installation flows.
2: The system shall retrieve and display all organisations and repositories accessible to the authenticated user.
3: The system shall parse and analyse GitHub Actions workflow YAML files from connected repositories.
4: The system shall receive and process GitHub webhook events for push, pull request, and workflow run events.
5: The system shall cache repository and organisation data in Redis with configurable TTL to minimise API consumption.

**FR-02: Workflow Security Analysis**

1: The system shall detect unpinned GitHub Actions referencing mutable tags instead of commit SHAs.
2: The system shall identify outdated action versions by comparing against latest available releases.
3: The system shall detect insecure workflow triggers vulnerable to code injection attacks.
4: The system shall identify excessive permission scopes in workflow configurations.
5: The system shall detect potential credential exposure through hardcoded secrets using entropy-based and pattern-matching algorithms.
6: The system shall categorise findings by severity (Critical, High, Medium, Low) using CVSS v3.1 scoring.

**FR-03: DSOMM Maturity Assessment**

1: The system shall automatically assess repositories against all five DSOMM dimensions.
2: The system shall compute maturity levels (L0–L4) for each dimension based on detected security practices.
3: The system shall generate a unified maturity score aggregating all dimensional assessments.
4: The system shall track maturity progression over time with historical scoring data.
5: The system shall auto-detect security practices including SAST, SCA, DAST, secret scanning, and dependency management.

**FR-04: Threat Modelling**

1: The system shall provide an interactive visual canvas for drawing system architecture diagrams.
2: The system shall support multi-framework threat analysis using STRIDE, CIA triad, and LINDDUN.
3: The system shall generate AI-powered threat identifications from visual diagram analysis.
4: The system shall provide real-time multi-user collaboration on threat modelling canvases.
5: The system shall generate structured threat reports with severity classification and mitigation recommendations.

**FR-05: AI RAG System**

1: The system shall provide conversational AI interaction with context-aware responses about repository security.
2: The system shall index workspace analysis data into vector embeddings for semantic retrieval.
3: The system shall maintain conversation history with per-user access controls.

**FR-06: Canvas Builder**

1: The system shall provide a visual drag-and-drop interface for CI/CD pipeline construction.
2: The system shall generate valid GitHub Actions YAML from visual pipeline representations.
3: The system shall automatically create pull requests with generated workflow files.

**FR-07: Action Audit**

1: The system shall monitor all GitHub Actions across an organisation for version governance.
2: The system shall classify action versions as Up to Date, Major Upgrade Needed, or Outdated.
3: The system shall support automated remediation via auto-generated pull requests to update action versions.
4: The system shall perform anti-typosquatting verification against the GitHub Marketplace.

### 3.2 Non-Functional Requirements

01 Performance:\*\* API response latency shall not exceed 200ms for 95th percentile requests. Organisation-wide security analysis for up to 200 repositories shall complete within 3 minutes. Frontend first contentful paint shall be under 1.5 seconds.

02 Security:\*\* All data in transit shall be encrypted using TLS 1.3. Authentication shall use Auth0 with JWT tokens validated at the API gateway level. Webhook payloads shall be verified using HMAC-SHA256 signatures. API rate limiting shall enforce 100 requests per minute and 1,000 requests per hour per client.

03 Scalability:\*\* The microservices architecture shall support horizontal scaling of individual services. The system shall handle concurrent analysis of multiple organisations without performance degradation.

04 Availability:\*\* The system shall target 99% uptime for critical paths. Individual service failures shall not cascade to other services (fault isolation).

05 Usability:\*\* The interface shall follow a consistent "Matte Engineering" design language with dark and light theme support. Task completion rate for core workflows shall exceed 85%. Comprehensive in-application documentation shall be provided.

06 Observability:\*\* All services shall expose Prometheus metrics, OpenTelemetry distributed traces, and structured logs. Centralised monitoring dashboards shall be available via Grafana.

07 Maintainability:\*\* Each microservice shall be independently deployable with its own codebase, database migrations, and dependency management. Code coverage shall exceed 80%.

### 3.3 Hardware / Software Requirements

**Server-Side Requirements:**

| Component        | Specification                                      |
| ---------------- | -------------------------------------------------- |
| Operating System | Linux (Ubuntu 22.04+), macOS, or Windows with WSL2 |
| CPU              | 4+ cores (8+ recommended for AI workloads)         |
| RAM              | 8 GB minimum, 16 GB recommended                    |
| Storage          | 20 GB minimum available disk space                 |
| Docker           | Docker Engine 24.0+ with Docker Compose v2         |
| Python           | Python 3.11+                                       |
| Node.js          | Node.js 18+ or 20+ (LTS)                           |

**Software Dependencies:**

| Component              | Technology              | Version         |
| ---------------------- | ----------------------- | --------------- |
| Frontend Framework     | SvelteKit               | 2.16.0          |
| UI Framework           | Svelte                  | 5.x (Runes API) |
| CSS Framework          | Tailwind CSS            | 4.0             |
| Build Tool             | Vite                    | 6.2.6           |
| Backend Framework      | FastAPI                 | 0.104.1         |
| Database               | PostgreSQL (Supabase)   | 15.x            |
| Cache / Message Broker | Redis                   | 7.x             |
| Vector Database        | Qdrant                  | 1.7+            |
| API Gateway            | Kong                    | 3.x             |
| Containerisation       | Docker + Docker Compose | 24.0+           |
| LLM Inference          | Ollama                  | Latest          |

**Client-Side Requirements:**

| Component | Specification                                                  |
| --------- | -------------------------------------------------------------- |
| Browser   | Modern browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+) |
| Network   | Stable internet connection for GitHub API and cloud AI access  |
| Screen    | Minimum 1280×720 resolution (1920×1080 recommended)            |

### 3.4 Networking Requirements

The WithOps platform operates as a distributed microservices system requiring specific networking configurations:

- **API Gateway:** Kong Gateway serves as the single entry point on port 9000, routing all external requests to appropriate backend microservices. It enforces CORS policies, rate limiting, and request transformation.

- **Inter-Service Communication:** Microservices communicate internally over a Docker bridge network using HTTP/REST calls via the httpx library. Service discovery is handled through Docker DNS resolution using container names.

- **Event Bus:** Redis (port 16379) provides pub/sub messaging across three primary channels: `github_events`, `threat_modeling_events`, and `workspace_intelligence_events`. This enables asynchronous event-driven communication between services.

- **WebSocket Connections:** The Events Hub (port 9100) maintains persistent WebSocket connections with frontend clients for real-time notifications and status updates.

- **External API Connections:** The platform requires outbound HTTPS access to GitHub API (api.github.com), Auth0 (tenant.auth0.com), Anthropic Claude API, and Groq API for cloud AI inference.

- **Observability Network:** Prometheus (port 9091) scrapes metrics from all services, Jaeger (port 16686) receives OpenTelemetry traces via OTLP HTTP protocol, and Loki (port 3100) aggregates logs from all containers.

---

## Chapter 04 — Feasibility Study

### 4.1 Operational Feasibility

The WithOps platform demonstrates strong operational feasibility based on analysis of user acceptance, organisational readiness, and operational sustainability.

**User Acceptance:** The platform targets technically proficient users — developers, DevOps engineers, and security professionals — who are already familiar with GitHub, CI/CD pipelines, and web-based tools. The user interface follows established design patterns with an intuitive workspace-based navigation structure, reducing the learning curve. The "Matte Engineering" design aesthetic provides a professional, distraction-free experience aligned with developer tool expectations. In-application documentation covering getting started guides, feature documentation, API reference, and deployment instructions further supports user onboarding.

**Organisational Fit:** WithOps integrates with existing GitHub infrastructure through standard OAuth 2.0 and GitHub App installation flows, requiring no changes to existing development workflows. Security analysis runs on-demand or automatically via webhook triggers, fitting naturally into existing CI/CD operations. The platform provides the compliance evidence (DSOMM maturity reports, security finding catalogues) that organisations increasingly require for SOC 2, ISO 27001, and EU Cyber Resilience Act compliance.

**Operational Sustainability:** The microservices architecture enables independent scaling and maintenance of individual components. Docker containerisation ensures consistent deployment across environments. The observability stack (Prometheus, Grafana, Jaeger, Loki) provides comprehensive operational monitoring, enabling proactive issue identification and resolution. Automated health checks on every service endpoint support operational reliability.

### 4.2 Economical Feasibility

The WithOps platform achieves economic feasibility through strategic use of open-source technologies and free-tier cloud services.

**Development Costs:** The platform is built entirely using open-source frameworks and tools — SvelteKit, FastAPI, PostgreSQL, Redis, Qdrant, Kong, Ollama, Docker, and the complete observability stack. No commercial software licences are required for core platform functionality. Development is conducted using free tools including Visual Studio Code and Git.

**Infrastructure Costs:** For development and testing, the platform runs entirely on local hardware using Docker Compose, incurring zero cloud infrastructure costs. Supabase provides a free tier with 500 MB database storage and 50,000 monthly API requests, sufficient for development and initial deployment. Auth0 provides a free tier supporting up to 7,000 monthly active users.

**AI Service Costs:** Ollama enables local LLM inference at zero cost using open-source models. Anthropic Claude API and Groq API offer pay-per-use pricing with generous free tiers for development. The multi-provider architecture allows cost optimisation by routing requests to the most cost-effective provider based on task complexity.

**Production Scaling Costs:** When scaling to production, the Kubernetes deployment manifests (included in the k8s/ directory) support deployment on cost-effective cloud infrastructure. The microservices architecture enables selective scaling of only the services experiencing high load, optimising resource utilisation and cost.

**Cost-Benefit Analysis:** The platform is projected to reduce security assessment time from 40–80 hours (manual DSOMM evaluation) to minutes (automated assessment), representing significant labour cost savings. Automated remediation via PR generation reduces developer time spent on security fixes. Early vulnerability detection prevents costly security incidents — the average cost of a data breach reached $4.45 million in 2023 (IBM Security).

### 4.3 Technical Feasibility

The WithOps platform is technically feasible based on demonstrated technology maturity, available skills, and proven architectural patterns.

**Technology Maturity:** All core technologies used in the platform are mature, well-documented, and widely adopted in production environments. SvelteKit 2 and Svelte 5 provide a stable, performant frontend framework. FastAPI is the leading Python async web framework with extensive ecosystem support. PostgreSQL 15, Redis 7, and Docker are enterprise-standard infrastructure components. Kong is a production-proven API gateway used by organisations including NASA, Nasdaq, and Cisco.

**AI Technology Readiness:** The AI capabilities leverage proven integration patterns. Anthropic Claude provides state-of-the-art vision and language capabilities for threat analysis. Ollama enables local LLM deployment with well-documented APIs. Qdrant provides production-ready vector database capabilities for RAG implementation. The multi-provider architecture ensures no single AI provider dependency.

**Developer Skills:** The development team possesses prior experience in full-stack web development with JavaScript/TypeScript and Python, REST API design, Docker containerisation, and database management. Experience with GitHub API integration and CI/CD pipeline configuration directly supports the project's domain requirements. SvelteKit was selected due to existing frontend development proficiency, and FastAPI was chosen for its Python compatibility with AI/ML libraries.

**Proof of Concept:** The feasibility of the core technical approach has been validated through working implementations of all eight microservices, successful GitHub API integration with OAuth and GitHub App flows, functional AI-powered threat analysis using Claude and Ollama, operational DSOMM maturity scoring from repository analysis, and a fully functional SvelteKit frontend with real-time collaboration capabilities.

---

## Chapter 05 — System Architecture

### 5.1 Use Case Diagram

The WithOps platform supports four primary actor types interacting with the system:

**Actors:**

- **Developer:** Connects GitHub account, views security analysis results, creates threat models, uses AI chat for security queries, builds CI/CD pipelines using Canvas Builder.
- **Security Engineer:** Performs organisation-wide security audits, reviews DSOMM maturity assessments, conducts comprehensive threat modelling sessions, monitors Action Audit findings.
- **DevOps Engineer:** Manages CI/CD workflow configurations, reviews pipeline security analysis, uses Canvas Builder for visual workflow authoring, monitors automated remediation PRs.
- **Engineering Manager:** Views organisational security dashboards, tracks maturity progression over time, generates compliance reports, manages team collaboration settings.

**Primary Use Cases:**

- UC-01: Authenticate via Auth0 (all actors)
- UC-02: Connect GitHub Organisation (Developer, DevOps Engineer)
- UC-03: Run Security Scan on Repository (Developer, Security Engineer)
- UC-04: View Workspace Intelligence Dashboard (all actors)
- UC-05: Assess DSOMM Maturity (Security Engineer, Engineering Manager)
- UC-06: Create Threat Model on Visual Canvas (Developer, Security Engineer)
- UC-07: Collaborate on Threat Model in Real-Time (all actors)
- UC-08: Generate AI Threat Analysis (Security Engineer)
- UC-09: Chat with AI RAG System (Developer, Security Engineer)
- UC-10: Audit GitHub Actions Versions (DevOps Engineer, Security Engineer)
- UC-11: Auto-Remediate via Pull Request (DevOps Engineer)
- UC-12: Build CI/CD Pipeline via Canvas Builder (DevOps Engineer)
- UC-13: Generate Workflow YAML from Visual Canvas (DevOps Engineer)
- UC-14: View Repository File Tree (Developer)
- UC-15: Monitor Real-Time Events via WebSocket (all actors)

_(Figure 5.1 — Use Case Diagram should be inserted here)_

### 5.2 Class Diagram of Proposed System

The WithOps platform follows a microservices-oriented class structure. Key domain classes across services include:

**Auth Service Domain:**

- `User` — Attributes: user_id, auth0_id, email, name, avatar_url, role, created_at, last_login. Methods: authenticate(), updateProfile(), getRoles().
- `Session` — Attributes: session_id, user_id, token, expires_at. Methods: validate(), refresh(), revoke().

**GitHub Service Domain:**

- `Organization` — Attributes: org_id, name, github_id, avatar_url, plan_type, repo_count. Methods: fetchRepositories(), syncMetadata().
- `Repository` — Attributes: repo_id, name, full_name, org_id, language, default_branch, visibility. Methods: getWorkflows(), analyseSecurityPosture().
- `Workflow` — Attributes: workflow_id, repo_id, name, path, yaml_content, triggers. Methods: parse(), detectVulnerabilities().
- `GitHubApp` — Attributes: app_id, installation_id, private_key_path. Methods: authenticate(), handleWebhook().

**Threat Modeling Service Domain:**

- `ThreatModel` — Attributes: model_id, name, user_id, org_id, canvas_data, created_at, updated_at. Methods: save(), analyse(), export().
- `Threat` — Attributes: threat_id, model_id, category, framework, description, severity, mitigations. Methods: classify(), generateMitigations().
- `Component` — Attributes: component_id, model_id, type, name, position, connections. Methods: identifyThreats(), assessRisk().

**Workspace Intelligence Service Domain:**

- `WorkspaceAssessment` — Attributes: assessment_id, org_id, maturity_score, dimensions, timestamp. Methods: compute(), compare(), track().
- `DSOMMMatureLevel` — Attributes: dimension, level, indicators, detected_practices. Methods: evaluate(), score().

**AI RAG Service Domain:**

- `Conversation` — Attributes: conversation_id, user_id, org_id, messages, created_at. Methods: addMessage(), getHistory().
- `VectorEmbedding` — Attributes: embedding_id, content_hash, vector, metadata, collection. Methods: index(), search(), delete().

### 5.3 ER Diagram

The platform uses Supabase PostgreSQL as the primary relational database. The logical data model encompasses the following key entities and relationships:

**Core Entities:**

- **users** (user_id PK, auth0_id UNIQUE, email, name, avatar_url, role, created_at, last_login)
- **organizations** (org_id PK, github_id, name, avatar_url, plan_type, user_id FK → users)
- **repositories** (repo_id PK, github_id, name, full_name, org_id FK → organizations, language, default_branch, visibility, security_score)
- **workflows** (workflow_id PK, repo_id FK → repositories, name, path, yaml_content, trigger_types, last_analysed)
- **security_findings** (finding_id PK, workflow_id FK → workflows, type, severity, description, remediation, line_number, status)
- **threat_models** (model_id PK, user_id FK → users, org_id FK → organizations, name, canvas_data JSONB, analysis_results JSONB, created_at, updated_at)
- **threats** (threat_id PK, model_id FK → threat_models, framework, category, description, severity, mitigations JSONB)
- **maturity_assessments** (assessment_id PK, org_id FK → organizations, overall_score, build_deployment_level, implementation_level, test_verification_level, information_gathering_level, culture_organization_level, assessed_at)
- **conversations** (conversation_id PK, user_id FK → users, org_id, title, messages JSONB, created_at, updated_at)
- **action_audits** (audit_id PK, org_id FK → organizations, action_name, current_version, latest_version, status, workflow_paths JSONB)

**Key Relationships:**

- One User has many Organizations (one-to-many)
- One Organization has many Repositories (one-to-many)
- One Repository has many Workflows (one-to-many)
- One Workflow has many Security Findings (one-to-many)
- One User has many Threat Models (one-to-many)
- One Threat Model has many Threats (one-to-many)
- One Organization has many Maturity Assessments (one-to-many, temporal)
- One User has many Conversations (one-to-many)

**Figure 5.3 — Database Schema (Supabase PostgreSQL)**

![Supabase Database Schema](../../report-images/supabase-schema-fcmcsbmsntmpeyjltqbi.png)

### 5.4 High-Level Architectural Diagram

The WithOps platform implements a microservices architecture with an event-driven communication backbone. The high-level architecture comprises five layers:

**Layer 1 — Client Layer:**
SvelteKit 5 frontend application served on port 5173 (development) or port 3000 (containerised). Communicates with the backend exclusively through the Kong API Gateway. Maintains persistent WebSocket connections to the Events Hub for real-time notifications.

**Layer 2 — API Gateway Layer:**
Kong Gateway (port 9000) serves as the single entry point, providing request routing to appropriate microservices, CORS enforcement, rate limiting (100 requests/minute, 1,000 requests/hour), and request/response transformation. Routes are configured declaratively using `kong.yml`.

**Layer 3 — Microservices Layer:**
Eight independently deployable FastAPI microservices, each responsible for a specific domain:

| Service                | Port (Internal/External) | Responsibility                                               |
| ---------------------- | ------------------------ | ------------------------------------------------------------ |
| Events Hub             | 8000 / 9100              | WebSocket gateway, Redis event bus, real-time notifications  |
| AI Service             | 8001 / 9101              | AI/ML analysis, PR description generation, threat analysis   |
| GitHub Service         | 8002 / 9102              | GitHub API integration, webhook handling, repository caching |
| Threat Modeling        | 8003 / 9103              | STRIDE/CIA/LINDDUN analysis, threat model CRUD               |
| Workspace Intelligence | 8004 / 9104              | DSOMM maturity scoring, security posture assessment          |
| Collaboration          | 8105 / 9105              | Multi-user sessions, organisation membership management      |
| Auth Service           | 8006 / 9106              | Auth0 JWT validation, RBAC, user profile management          |
| Workflow Orchestration | 8007 / 9107              | CI/CD workflow management, Canvas Builder, security scanning |
| AI RAG Service         | 8008 / 9108              | Conversational AI, vector search, auto-indexing              |

**Layer 4 — Data Layer:**

- PostgreSQL 15 (Supabase) — Primary relational data store
- Redis 7 — Caching, pub/sub event bus, and session management
- Qdrant — Vector database for RAG semantic search embeddings

**Layer 5 — Observability Layer:**

- Prometheus — Metrics collection from all service `/metrics` endpoints
- Grafana — Visualisation dashboards for system and business metrics
- Jaeger — Distributed tracing via OpenTelemetry instrumentation
- Loki — Centralised log aggregation from all containers

_(Figure 5.2 — High-Level Microservices Architecture Diagram should be inserted here)_

### 5.5 Networking Diagram

The platform's network topology is defined through Docker Compose networking with specific considerations for service isolation and external connectivity:

**Internal Network:** All microservices operate within a shared Docker bridge network (`withops-network`), enabling service-to-service communication via container DNS names. Internal ports (8000–8008) are not exposed to the host system, ensuring traffic routes through the Kong gateway.

**External Access Points:**

- Port 5173: Frontend application (SvelteKit)
- Port 9000: API Gateway (Kong) — all API traffic
- Port 9001: Kong Admin API (development only)
- Port 9100–9108: Direct service access (development/debugging only)
- Port 16379: Redis (development access)
- Port 3001: Grafana monitoring dashboards
- Port 16686: Jaeger tracing UI
- Port 9091: Prometheus metrics

**Kubernetes Production Topology:** Production deployment uses Kubernetes with separate namespace (`withops`), Services for internal load balancing, Ingress controllers for external HTTPS access, and Persistent Volume Claims for PostgreSQL and Qdrant data persistence.

_(Figure 5.4 — Network and Deployment Topology Diagram should be inserted here)_

---

## Chapter 06 — Development Tools and Technologies

### 6.1 Development Methodology

The WithOps project follows an Agile development methodology integrated with DevOps practices, using structured two-week sprint cycles.

**Sprint Structure:**

- **Week 1:** Feature development, unit testing, and service integration. New microservice features are developed in feature branches following Git feature-branch workflow. Unit tests are written alongside feature code following test-driven development principles.
- **Week 2:** Integration testing, user acceptance testing, performance optimisation, documentation, and sprint review. Completed features are merged via pull requests with code review.
- **Continuous Activities:** CI/CD pipeline execution, monitoring review, logging analysis, and feedback collection occur throughout each sprint.

**Version Control:** Development is managed using Git with a feature-branch workflow. All changes go through pull request reviews before merging to the main branch. The repository includes CI/CD workflow definitions (in the `workflow/` directory) that enforce automated testing, security scanning (Gitleaks for secret detection, TruffleHog for PR enforcement), and quality gates.

**Sprint Tracking:** Progress is tracked through regular supervisor meetings, sprint retrospectives, and documented sprint reviews ensuring alignment with academic timelines and project objectives.

### 6.2 Programming Languages and Tools

| Category                | Technology                | Justification                                                                                                                                               |
| ----------------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend Language       | JavaScript (ES2022+)      | Universal browser support, extensive ecosystem, team proficiency                                                                                            |
| Frontend Framework      | SvelteKit 2 with Svelte 5 | Superior performance through compile-time optimisation, smaller bundle sizes than React/Vue, reactive programming via Runes API ($state, $derived, $effect) |
| UI Styling              | Tailwind CSS 4            | Utility-first CSS enabling rapid, consistent UI development without custom stylesheet management                                                            |
| Build Tool              | Vite 6.2.6                | Fastest development server with hot module replacement, optimised production builds                                                                         |
| Backend Language        | Python 3.11+              | Extensive AI/ML library ecosystem, strong async support, team proficiency                                                                                   |
| Backend Framework       | FastAPI 0.104.1           | Highest-performance Python web framework, native async/await support, automatic OpenAPI documentation                                                       |
| Database                | PostgreSQL 15 (Supabase)  | Enterprise-grade relational database with JSONB support for flexible schema storage                                                                         |
| Cache / Event Bus       | Redis 7                   | Sub-millisecond latency, pub/sub messaging for event-driven architecture, session management                                                                |
| Vector Database         | Qdrant 1.7+               | Purpose-built for vector similarity search, essential for RAG implementation                                                                                |
| API Gateway             | Kong 3.x                  | Production-proven gateway with declarative configuration, rate limiting, and CORS management                                                                |
| Containerisation        | Docker + Docker Compose   | Ensures consistent environments across development and production                                                                                           |
| Container Orchestration | Kubernetes                | Production deployment with horizontal pod autoscaling and rolling updates                                                                                   |
| IDE                     | Visual Studio Code        | Extensive extension ecosystem, integrated terminal, Git support                                                                                             |

### 6.3 Third-Party Components and Libraries

**Frontend Libraries:**

| Library                 | Version | Purpose                                                        |
| ----------------------- | ------- | -------------------------------------------------------------- |
| @auth0/auth0-spa-js     | Latest  | Authentication and authorisation via Auth0                     |
| d3                      | 7.x     | Data visualisation for security dashboards and maturity graphs |
| three.js                | Latest  | 3D visualisation components                                    |
| yjs                     | Latest  | CRDT-based real-time collaboration protocol                    |
| y-websocket             | Latest  | WebSocket provider for Yjs collaborative editing               |
| lottie-web              | Latest  | Animated micro-interactions and loading states                 |
| @liveblocks/client      | Latest  | Real-time cursor presence and collaboration layer              |
| @tailwindcss/forms      | Latest  | Form styling plugin for Tailwind                               |
| @tailwindcss/typography | Latest  | Prose styling for documentation content                        |

**Backend Libraries:**

| Library             | Purpose                                                    |
| ------------------- | ---------------------------------------------------------- |
| uvicorn             | ASGI server for FastAPI applications                       |
| httpx               | Async HTTP client for inter-service communication          |
| redis[asyncio]      | Async Redis client with pub/sub support                    |
| SQLAlchemy 2.0      | Async ORM for PostgreSQL database interaction              |
| asyncpg             | High-performance async PostgreSQL driver                   |
| alembic             | Database schema migration management                       |
| anthropic           | Anthropic Claude API client for AI analysis                |
| groq                | Groq API client for Llama 3 inference                      |
| ollama              | Ollama API client for local LLM inference                  |
| qdrant-client       | Vector database client for RAG embeddings                  |
| python-jose         | JWT token validation and creation                          |
| PyJWT               | GitHub App JWT authentication                              |
| cryptography        | Cryptographic operations for GitHub webhook verification   |
| tenacity            | Retry logic for resilient service-to-service calls         |
| prometheus-client   | Prometheus metrics instrumentation                         |
| opentelemetry-\*    | Distributed tracing instrumentation                        |
| PyPDF2, python-docx | Document processing for threat model analysis              |
| bandit              | Python security static analysis for workflow orchestration |
| pydantic-settings   | Type-safe configuration management                         |

### 6.4 Algorithms

The WithOps platform implements several domain-specific algorithms:

**YAML AST Traversal for Vulnerability Detection:** GitHub Actions workflow YAML files are parsed into Abstract Syntax Trees and traversed to detect security vulnerability patterns. The traversal examines action reference syntax (detecting unpinned vs SHA-pinned references), permission scope declarations, trigger configurations, and environment variable usage patterns.

**Entropy-Based Secret Detection:** A Shannon entropy calculation algorithm identifies potential hardcoded secrets within workflow files. Strings exceeding configurable entropy thresholds (typically >4.5 bits per character for hexadecimal, >5.0 for base64) are flagged as potential credentials. This is complemented by 150+ regex patterns matching known secret formats (AWS keys, GitHub tokens, API keys).

**Semantic Version Comparison:** An algorithm compares detected action versions against latest available releases from the GitHub Marketplace. It implements semantic versioning comparison (major.minor.patch) to classify findings as "Up to Date," "Minor Update Available," "Major Upgrade Needed," or "Outdated," enabling the Action Audit feature.

**Weighted DSOMM Maturity Scoring:** A multi-dimensional scoring algorithm evaluates repository security practices against the five DSOMM dimensions. Each dimension receives a level (L0–L4) based on detected practice indicators. The overall maturity score is computed as a weighted average, with configurable weights reflecting organisational priorities. The algorithm detects practices including SAST integration, SCA scanning, secret scanning configuration, branch protection rules, and CI/CD pipeline security controls.

**Retrieval-Augmented Generation (RAG):** The RAG pipeline follows a three-stage process: (1) Document chunking and embedding generation using Ollama's embedding models, storing vectors in Qdrant collections; (2) Semantic similarity search using cosine distance to retrieve relevant context chunks for user queries; (3) Context-augmented prompt construction, combining retrieved context with user queries for Claude API inference, producing contextually accurate responses.

**AI-Assisted Threat Identification:** Visual diagram analysis uses Claude's vision capabilities to identify system components, data flows, and trust boundaries from canvas drawings. The identified architecture is then analysed against STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege), CIA (Confidentiality, Integrity, Availability), and LINDDUN (Linkability, Identifiability, Non-repudiation, Detectability, Disclosure of information, Unawareness, Non-compliance) frameworks to generate comprehensive threat catalogues.

---

## Chapter 07 — Implementation Progress

### 7.1 Development Environment Setup

The development environment has been fully established to support the microservices-based architecture:

**IDE and Version Control:** Visual Studio Code is used as the primary development environment with extensions for Python, Svelte, ESLint, Tailwind CSS IntelliSense, and Docker. Git is used for version control with a feature-branch workflow, and the repository is hosted on GitHub.

**Containerisation:** Docker Desktop with Docker Compose v2 manages all 16+ containers in the development environment. A comprehensive `docker-compose.yml` orchestrates all microservices, infrastructure services (Redis, Qdrant, Ollama), the Kong API gateway, and the complete observability stack (Prometheus, Grafana, Jaeger, Loki).

**Backend Environment:** Python 3.11+ virtual environments are configured for each microservice with dedicated `requirements.txt` files. Each service runs its own FastAPI application with uvicorn ASGI server, hot-reload enabled for development.

**Frontend Environment:** Node.js 20 LTS with npm manages frontend dependencies. Vite 6 provides the development server with hot module replacement. The SvelteKit application is configured with adapter-node for production containerisation.

**Database Environment:** Supabase cloud-hosted PostgreSQL serves as the primary database, accessed via SQLAlchemy 2.0 with asyncpg driver. Alembic manages database migrations per service. Redis 7 runs as a Docker container for caching and event messaging.

**AI Environment:** Ollama runs locally in a Docker container with model auto-initialisation via shell script. Anthropic Claude and Groq API keys are configured via environment variables for cloud AI inference.

**Observability:** Prometheus is configured to scrape all microservice `/metrics` endpoints. Grafana dashboards provide system monitoring. Jaeger receives distributed traces via OpenTelemetry. Loki aggregates container logs.

### 7.2 Implemented Features

The following features have been fully implemented and are operational:

| Feature                      | Status   | Description                                                                                                |
| ---------------------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| Auth0 Authentication         | Complete | OAuth 2.0 + PKCE login flow with JWT validation, session management, and RBAC                              |
| GitHub OAuth Integration     | Complete | OAuth App authentication flow for accessing user organisations and repositories                            |
| GitHub App Integration       | Complete | GitHub App installation flow with per-repository permissions and webhook events                            |
| Repository Discovery         | Complete | Organisation and repository listing with metadata, language detection, and caching                         |
| Workflow Security Analysis   | Complete | YAML parsing and vulnerability detection for 25+ patterns across GitHub Actions workflows                  |
| DSOMM Maturity Assessment    | Complete | Automated maturity scoring across all five DSOMM dimensions (L0–L4)                                        |
| Threat Modeling Canvas       | Complete | Interactive visual canvas with multi-framework (STRIDE/CIA/LINDDUN) AI analysis                            |
| Real-Time Collaboration      | Complete | Multi-user cursor presence and shape sharing via Yjs and Liveblocks                                        |
| AI RAG Conversational System | Complete | Context-aware AI chat with vector-based semantic retrieval from Qdrant                                     |
| Action Audit                 | Complete | Organisation-wide GitHub Actions version governance with automated PR remediation                          |
| Canvas Builder               | Complete | Visual CI/CD pipeline editor with YAML generation and PR creation                                          |
| WebSocket Real-Time Events   | Complete | Live notification system via Events Hub with Redis pub/sub backbone                                        |
| Kong API Gateway             | Complete | Declarative routing, CORS, rate limiting for all microservices                                             |
| Observability Stack          | Complete | Full Prometheus + Grafana + Jaeger + Loki integration across all services                                  |
| In-App Documentation         | Complete | Comprehensive docs section with getting started guides, feature docs, API reference, and deployment guides |
| Repository Tree View         | Complete | File tree browser for connected repositories                                                               |
| Webhook Event Processing     | Complete | GitHub push, PR, and workflow run event handling with HMAC verification                                    |

### 7.3 Screenshots / Code Snippets

**Microservice Health Check Pattern (Implemented Across All Services):**

Each microservice implements a standardised health endpoint and Prometheus metrics middleware:

```python
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest

app = FastAPI(title="WithOps AI Service", version="2.0.0")

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency'
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-service", "version": "2.0.0"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Redis Event Bus Communication Pattern:**

```python
import redis.asyncio as redis

class EventBus:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def publish(self, channel: str, event: dict):
        await self.redis.publish(channel, json.dumps(event))

    async def subscribe(self, channel: str, callback):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await callback(json.loads(message['data']))
```

**Kong API Gateway Declarative Route Configuration:**

```yaml
services:
  - name: ai-service
    url: http://ai-service:8001
    routes:
      - name: ai-route
        paths: ["/api/ai"]
        strip_path: true
  - name: github-service
    url: http://github-service:8002
    routes:
      - name: github-route
        paths: ["/api/github"]
        strip_path: true
```

**SvelteKit Frontend — Auth0 Integration:**

```javascript
import { createAuth0Client } from "@auth0/auth0-spa-js";

const auth0Client = await createAuth0Client({
  domain: import.meta.env.VITE_AUTH0_DOMAIN,
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
  authorizationParams: {
    redirect_uri: window.location.origin + "/callback",
    audience: import.meta.env.VITE_AUTH0_AUDIENCE,
  },
});
```

**Figure 7.1 — Landing Page**

![Landing Page](../../report-images/Screenshot%202026-03-01%20190024.png)

**Figure 7.2 — Platform Overview Page**

![Overview Page](../../report-images/Screenshot%202026-03-01%20190216.png)

**Figure 7.3 — Auth0 Login Page**

![Login Page](../../report-images/Screenshot%202026-03-01%20190316.png)

**Figure 7.4 — Workspace Dashboard**

![Workspace Dashboard](../../report-images/Screenshot%202026-03-01%20190716.png)

### 7.4 Challenges Encountered and Solutions

**Challenge 1: Windows Port Conflicts**
Several default port numbers (8000–8008) conflicted with Windows reserved ports and other development tools. This caused service startup failures and intermittent connectivity issues during development.

**Solution:** All external port mappings were shifted to the 9100–9108 range in the Docker Compose configuration while maintaining internal ports unchanged. This resolved conflicts without requiring any code changes in the microservices themselves.

**Challenge 2: GitHub API Rate Limiting**
GitHub enforces a rate limit of 5,000 authenticated requests per hour. During organisation-wide analyses involving many repositories and workflow files, the platform frequently exhausted rate limits, causing analysis failures.

**Solution:** A multi-layered caching strategy was implemented using Redis with 24-hour TTL for repository metadata and organisation data. Intelligent request batching reduces API calls by grouping related queries. Exponential backoff retry logic (via the tenacity library) handles transient rate limit responses gracefully. A background worker (`github-service-worker`) performs incremental data refresh asynchronously.

**Challenge 3: Inter-Service Communication Reliability**
In a microservices architecture, service-to-service HTTP calls occasionally fail due to container startup ordering, transient network issues, or service restarts during development.

**Solution:** The tenacity library was integrated across all services for retry logic with exponential backoff. Docker Compose health checks with `depends_on` conditions ensure proper startup ordering. The Redis event bus provides asynchronous decoupled communication for non-critical operations, reducing the impact of temporary service unavailability.

**Challenge 4: Real-Time Collaboration Synchronisation**
Implementing real-time multi-user threat modelling with consistent state across clients presented challenges with conflict resolution and cursor presence tracking.

**Solution:** Yjs CRDT (Conflict-Free Replicated Data Types) was adopted as the synchronisation protocol, providing automatic conflict resolution for concurrent edits. Liveblocks provides cursor presence tracking with minimal latency. The combination ensures consistent state across all connected clients without manual conflict resolution.

**Challenge 5: AI Response Quality and Latency**
AI-generated threat analyses sometimes produced generic or irrelevant results, and response latency varied significantly between AI providers.

**Solution:** The RAG system was implemented through the AI RAG Service, indexing workspace analysis data as vector embeddings in Qdrant. This enables context-augmented AI responses grounded in actual repository security data rather than generic knowledge. The multi-provider architecture (Ollama, Claude, Groq) allows routing requests to the most appropriate provider based on latency requirements and task complexity.

### 7.5 Current System Limitations

The platform currently has the following known limitations:

- **GitHub-Only Support:** The platform exclusively analyses GitHub Actions workflows. GitLab CI, Jenkins, Azure DevOps, and other CI/CD platforms are not supported in the current version.

- **Static Analysis Only:** Workflow analysis is performed statically on YAML configuration files. Runtime behaviour monitoring during actual workflow execution is not implemented.

- **Single-Organisation Context:** The AI RAG system currently maintains conversation context within a single organisation scope. Cross-organisation knowledge transfer is not supported.

- **Limited Mobile Responsiveness:** While the documentation section is responsive, the threat modelling canvas and Canvas Builder features are optimised for desktop screen resolutions (1280px+ width) and may have limited usability on mobile devices.

- **Ollama Model Dependency:** Local AI inference requires downloading large language models (several GB), which may be impractical in resource-constrained environments. Cloud AI providers can be used as alternatives but introduce external API dependencies.

- **Manual Kubernetes Deployment:** While Kubernetes manifests are provided, automated cluster provisioning and CI/CD-driven deployment pipelines for the platform itself are not fully implemented.

- **Limited Automated Testing Coverage:** While the testing framework (Vitest for frontend, pytest for backend) is configured, comprehensive test coverage across all microservices has not reached the target 80% threshold.

---

## Chapter 08 — Discussion

### Summary of the Report

This interim report presents the current state of the WithOps DevSecOps Intelligence Platform — a comprehensive system designed to address critical gaps in CI/CD workflow security analysis, DevSecOps maturity assessment, and automated threat modelling. The platform implements a production-grade microservices architecture comprising eight independently deployable FastAPI services, a SvelteKit 5 frontend application, and a full observability stack, all orchestrated through Docker Compose and deployable on Kubernetes.

The report has demonstrated that the project is technically feasible, economically viable, and operationally sound. All core features identified in the project objectives have been implemented to a functional state, including GitHub workflow security analysis detecting 25+ vulnerability patterns, automated DSOMM maturity assessment across five dimensions, an AI-powered threat modelling canvas with STRIDE/CIA/LINDDUN framework support, a RAG-based conversational AI system, an Action Audit supply chain governance module, and a visual Canvas Builder for CI/CD pipeline engineering.

### What Has Changed from the Proposal

Several refinements have been made to the original Project Initiation Document based on practical implementation experience:

- **Architecture Evolution:** The backend component originally served as both a REST API and event coordinator. It has been refactored into a dedicated Events Hub focused exclusively on WebSocket gateway and Redis event bus coordination, with all REST APIs distributed to dedicated microservices. This improves separation of concerns and scalability.

- **Port Configuration:** External port mappings were shifted from the 8000–8008 range to 9100–9108 to avoid Windows reserved port conflicts — a practical consideration not anticipated in the initial design.

- **AI Provider Strategy:** The original proposal focused primarily on Claude and Ollama. Groq (Meta Llama 3) has been added as a third AI provider, enabling faster inference for latency-sensitive operations and reducing dependency on any single provider.

- **Collaboration Technology:** Real-time collaboration was enhanced beyond the original scope by integrating both Yjs (CRDT-based synchronisation) and Liveblocks (cursor presence), rather than relying on a single collaboration framework.

- **Frontend Framework Version:** The frontend has been built with SvelteKit 2 and Svelte 5 (Runes API), representing a more modern approach than originally planned, leveraging compile-time reactivity through $state, $derived, and $effect primitives.

### Future Plans / Upcoming Work

The remaining development phase will focus on the following priorities:

1. **Comprehensive Testing:** Achieving the target 80%+ test coverage across all microservices with unit, integration, and end-to-end tests using Vitest and pytest. Playwright end-to-end tests for critical user flows.

2. **Performance Optimisation:** Load testing and optimisation of API response times, particularly for organisation-wide analysis operations. Implementation of database query optimisation and enhanced caching strategies.

3. **Security Hardening:** Final security audit of the platform itself, ensuring OWASP Top 10 prevention measures are in place, dependency vulnerability scanning, and penetration testing of the API gateway configuration.

4. **User Evaluation:** Conducting structured usability testing with target users to measure Task Completion Rate and System Usability Scale (SUS) scores. Collecting feedback through surveys and interviews to validate the platform's effectiveness.

5. **Compliance Report Generation:** Implementing exportable compliance reports summarising DSOMM maturity scores, security findings, and remediation history in formats suitable for regulatory audit submissions.

6. **Documentation Completion:** Finalising API documentation, deployment guides for production Kubernetes environments, and user training materials.

---

## References

- Ayala, C. and Garcia, J. (2023) _An empirical study of security practices in GitHub repositories_, arXiv preprint arXiv:2305.16120. Available at: https://arxiv.org/abs/2305.16120 (Accessed: 3 January 2026).

- IBM Security (2023) _Cost of a Data Breach Report 2023_. IBM Corporation. Available at: https://www.ibm.com/reports/data-breach (Accessed: 15 January 2026).

- Jit (2024) _From DSOMM theory to practical enforcement: A DevSecOps journey_. Available at: https://www.jit.io/resources/devsecops/from-dsomm-theory-to-practical-enforcement-a-devsecops-journey (Accessed: 3 January 2026).

- OWASP Foundation (2024) _DevSecOps Maturity Model (DSOMM)_. Available at: https://owasp.org/www-project-devsecops-maturity-model/ (Accessed: 3 January 2026).

- Pan, X., Liu, Y., Zhang, Y. and Wang, X. (2024) _CI/CD under the hood: Vulnerabilities and threats in modern pipelines_, arXiv preprint arXiv:2401.17606. Available at: https://arxiv.org/abs/2401.17606 (Accessed: 3 January 2026).

- Saroar, M. and Nayebi, M. (2023) _Practitioners' perceptions of GitHub Actions and workflow automation_, arXiv preprint arXiv:2303.04084. Available at: https://arxiv.org/abs/2303.04084 (Accessed: 3 January 2026).

- Shevchenko, N., Chick, T.A., O'Riordan, P., Scanlon, T.P. and Woody, C. (2018) _Threat Modeling: A Summary of Available Methods_. Technical Report CMU/SEI-2018-TR-001. Software Engineering Institute, Carnegie Mellon University.

- Unit42 (2025) _GitHub Actions supply chain attack analysis: tj-actions/changed-files compromise_. Palo Alto Networks Unit 42. Available at: https://unit42.paloaltonetworks.com/github-actions-supply-chain-attack/ (Accessed: 3 January 2026).

- Yampolskiy, M., King, W.E., Gatlin, J., Belikovetsky, S., Brown, A., Skjellum, A. and Elovici, Y. (2022) _Security of additive manufacturing: Attack taxonomy and survey_, Additive Manufacturing, 21, pp.431-457.

---

## Appendices

### Appendix A — Microservices Port Mapping

| Service                | Internal Port | External Port | Kong Route                       |
| ---------------------- | :-----------: | :-----------: | -------------------------------- |
| Kong Gateway           |     8000      |     9000      | — (Entry Point)                  |
| Events Hub             |     8000      |     9100      | /api/events/\*                   |
| AI Service             |     8001      |     9101      | /api/ai/\*                       |
| GitHub Service         |     8002      |     9102      | /api/github/\*                   |
| Threat Modeling        |     8003      |     9103      | /api/threat-modeling/\*          |
| Workspace Intelligence |     8004      |     9104      | /api/workspace-intelligence/\*   |
| Collaboration          |     8105      |     9105      | /api/collaboration/\*            |
| Auth Service           |     8006      |     9106      | /api/auth/\*                     |
| Workflow Orchestration |     8007      |     9107      | /api/workflows/_, /api/canvas/_  |
| AI RAG Service         |     8008      |     9108      | /api/rag/_, /api/conversations/_ |
| Frontend               |     3000      |     5173      | — (Direct Access)                |
| Redis                  |     6379      |     16379     | — (Internal)                     |
| Ollama                 |     11434     |     11434     | — (Internal)                     |
| Qdrant                 |   6333/6334   |   6333/6334   | — (Internal)                     |
| Prometheus             |     9090      |     9091      | — (Monitoring)                   |
| Grafana                |     3000      |     3001      | — (Monitoring)                   |
| Jaeger                 |     16686     |     16686     | — (Monitoring)                   |
| Loki                   |     3100      |     3100      | — (Monitoring)                   |

### Appendix B — Docker Compose Service Definitions

The complete Docker Compose configuration orchestrates 16+ containers with service dependency management, health checks, volume mounts, and network configuration. The production Docker Compose variant (`docker-compose.prod.yml`) provides optimised configurations for deployment environments.

### Appendix C — CI/CD Workflow Configurations

The project repository includes the following CI/CD workflow definitions:

- **ci-caller.yml** — Triggers the reusable CI pipeline on push to main branch
- **reusable-ci.yml** — Reusable workflow with checkout, Node.js setup, install, test, and build stages
- **test.yml** — Basic CI pipeline for push and PR events
- **gitleaks.yaml** — Organisation-wide secret scanning across all repositories
- **trufflehog.yaml** — PR enforcement with JIRA ticket validation
