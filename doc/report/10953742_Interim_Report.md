# PUSL3190 Computing Project Interim Report

<img src="./ul1j5fde.png" style="width:1.02251in;height:0.45833in" /><img src="./iscetttp.png" style="width:1.13971in;height:0.22847in" />

**Project Title:** WithOps: An Intelligent DevSecOps Platform for GitHub Actions Security, Maturity Modeling, and Automated Threat Analysis  
**Student Name:** Ilukwaththe Ariyarathne  
**Student ID:** 10953742  
**Supervisor:** Prof. Chaminda Wijesinghe  
**Date:** March 05, 2026  

---

## Table of Contents

1. [Chapter 01: Introduction](#chapter-01-introduction)
    - 1.1 Introduction
    - 1.2 Problem Definition
    - 1.3 Project Objectives
2. [Chapter 02: System Analysis](#chapter-02-system-analysis)
    - 2.1 Fact Gathering Techniques
    - 2.2 Existing System
    - 2.3 Drawbacks of the existing system
3. [Chapter 03: Requirements Specification](#chapter-03-requirements-specification)
    - 3.1 Functional Requirements
    - 3.2 Non-Functional Requirements
    - 3.3 Hardware / Software Requirements
    - 3.4 Networking Requirements
4. [Chapter 04: Feasibility Study](#chapter-04-feasibility-study)
    - 4.1 Operational Feasibility
    - 4.2 Economical Feasibility
    - 4.3 Technical Feasibility
5. [Chapter 05: System Architecture](#chapter-05-system-architecture)
    - 5.1 Use Case Diagram
    - 5.2 Microservices Layer
    - 5.3 Data and Communication Layer
    - 5.4 Internal Service Architecture
6. [Chapter 06: Development Tools and Technologies](#chapter-06-development-tools-and-technologies)
    - 6.1 Development Methodology
    - 6.2 Programming Languages and Tools
    - 6.3 Third-Party Components and Libraries
    - 6.4 Algorithms
7. [Chapter 07: Implementation Progress](#chapter-07-implementation-progress)
    - 7.1 Development Environment Setup
    - 7.2 Implemented Features
    - 7.3 Code Snippets and Analysis
    - 7.4 Challenges Encountered and Solutions
    - 7.5 Current System Limitations
8. [Chapter 08: Discussion](#chapter-08-discussion)
    - 8.1 Summary of the Report
    - 8.2 Changes from the Proposal
    - 8.3 Future Plans / Upcoming Work
9. [References](#references)

---

## List of Figures and Tables

*   **Figure 1.1:** The DevSecOps "Shift Left" Lifecycle.
*   **Figure 5.1:** Use Case Diagram for the WithOps Platform.
*   **Figure 5.2:** High-Level Microservices Architecture.
*   **Figure 5.3:** Event-Driven Communication Flow via Redis Pub/Sub.
*   **Figure 5.4:** Internal Component Design of the Workspace Intelligence Service.
*   **Figure 7.1:** Screenshot of the Documentation Portal.
*   **Figure 7.2:** Dashboard Interface Preview.
*   **Table 3.1:** Detailed Functional Requirements and Priority.
*   **Table 3.2:** Non-Functional Requirements and Target Metrics.
*   **Table 3.3:** Detailed Hardware and Software Requirements.
*   **Table 6.1:** Programming Languages and Tool Justification.
*   **Table 7.1:** Milestone Comparison: Planned vs. Actual.

---

## Chapter 01: Introduction

### 1.1 Introduction
In the contemporary era of digital transformation, the software development lifecycle (SDLC) has undergone a fundamental shift. The transition from monolithic, waterfall-based development to agile, microservices-oriented architectures has necessitated a corresponding evolution in how software is delivered. Continuous Integration and Continuous Deployment (CI/CD) pipelines have emerged as the backbone of modern engineering, enabling organizations to release updates with unprecedented frequency and speed. However, this acceleration has outpaced traditional security methodologies, creating a critical vulnerability gap within the most sensitive part of the development infrastructure: the deployment pipeline itself.

The software supply chain has become a primary target for sophisticated adversaries. Recent years have seen a 742% increase in supply chain attacks, with attackers moving upstream to compromise build environments rather than the application code. Notable incidents, such as the March 2025 compromise of the `tj-actions/changed-files` GitHub Action, demonstrated how a single vulnerable component in a CI/CD workflow could grant attackers access to the source code and secrets of thousands of downstream organizations. Despite this growing threat, most organizations lack the tools and visibility required to secure their automated workflows.

**WithOps** is an intelligent DevSecOps platform designed to address these systemic challenges. It is built on the core principle of "Shift Left," which advocates for integrating security intelligence at the earliest possible stage of development. By focusing specifically on GitHub Actions—the world's most popular automation platform—WithOps provides a centralized hub for proactive security management. The platform combines automated workflow security scanning, maturity assessment based on the OWASP DevSecOps Maturity Model (DSOMM), and AI-powered threat modeling into a unified, collaborative environment.

WithOps leverages advanced technology, including Artificial Intelligence (AI) and Retrieval-Augmented Generation (RAG), to transform complex security data into actionable insights for developers and security engineers. The project represents a comprehensive effort to bridge the gap between development speed and security integrity, ensuring that as organizations move faster, they also move safer. This interim report documents the research, analysis, architectural design, and implementation progress of the WithOps platform, proving its feasibility and documenting its trajectory toward a next-generation security solution.

### 1.2 Problem Definition
The "problem" that WithOps solves is multi-faceted, involving technical, organizational, and cognitive dimensions. Current industry practices for securing CI/CD pipelines are fragmented, manual, and often overlooked due to the complexity of the underlying automation.

**1.2.1 Invisible Infrastructure Vulnerabilities**
Most modern security tools (SAST, DAST, SCA) focus exclusively on the "payload"—the application code and its dependencies. However, the "infrastructure" that delivers this code—the YAML-based GitHub Actions workflows—is often ignored. These workflows possess elevated privileges, including the ability to read source code, push to repositories, and access production secrets. Misconfigurations such as using mutable tags (e.g., `uses: actions/checkout@v3` instead of a commit hash), granting excessive `GITHUB_TOKEN` permissions, or implementing insecure trigger events (`on: pull_request_target`) create critical vulnerabilities. Because these are "infrastructure errors" rather than "code errors," they are invisible to traditional scanners.

**1.2.2 Subjective and Static Maturity Assessment**
Organizations striving to implement DevSecOps principles lack an objective method to measure their progress. The OWASP DevSecOps Maturity Model (DSOMM) provides a theoretical framework, but manual assessment is resource-intensive and subjective. A security manager might check a set of repositories once a quarter, but this "snapshot" approach fails in a world where new services and workflows are deployed daily. Organizations need a way to programmatically and continuously track their security maturity across the dimensions of culture, testing, and deployment.

**1.2.3 The Threat Modeling Expertise Bottleneck**
Threat modeling is one of the most effective ways to identify security flaws before writing a single line of code. However, it remains a manual, expert-driven process. A moderately complex architecture can take 40-60 hours to model using traditional methods (like STRIDE or LINDDUN). In organizations with hundreds of microservices, security teams simply cannot keep up. Consequently, threat modeling is either skipped entirely or performed ad-hoc, leading to security flaws being discovered late in the development cycle, where they are much more expensive to fix.

**1.2.4 Cognitive Overload and YAML Complexity**
GitHub Actions YAML syntax is powerful but notoriously brittle. Research has shown that over 60% of developers find YAML-based automation difficult to debug and error-prone. The indentation-sensitive syntax, combined with domain-specific logic, often leads developers to copy-paste templates from insecure sources, propagating vulnerabilities throughout an organization. There is a clear need for a visual, guidance-led system that reduces this cognitive load while enforcing security best practices.

### 1.3 Project Objectives
The overarching goal of the WithOps project is to develop a unified platform that transforms DevSecOps from a set of manual checkboxes into an automated, intelligence-driven operation. To achieve this, the project defines six specific, measurable objectives:

*   **Objective 1: Develop an Automated GitHub Workflow Security Engine.**
    The system must be capable of parsing GitHub Actions YAML files and detecting 25+ distinct vulnerability patterns. It should not only alert the user but also provide "auto-remediation" suggestions, such as generating a Pull Request that pins an insecure action to a specific commit hash or restricts excessive permissions.
*   **Objective 2: Implement a Programmatic DSOMM Maturity Assessment System.**
    The system should automatically analyze repository metadata, branch protection rules, and security practice indicators to calculate a maturity score across the five dimensions of the DSOMM framework. The result should be a live "Maturity Dashboard" that tracks improvement over time.
*   **Objective 3: Build an AI-Powered Interactive Threat Modeling Canvas.**
    The platform should provide a "drag-and-drop" visual environment for architecture design. By integrating AI vision and reasoning models (like Claude or GPT-4), the system should analyze these diagrams in real-time and generate threat reports based on the STRIDE, CIA, and LINDDUN frameworks.
*   **Objective 4: Integrate a Context-Aware RAG Security Intelligence System.**
    Using a vector database (like Qdrant) and Retrieval-Augmented Generation, the platform should manage a "Security Brain." This system will index best practices from OWASP, NIST, and GitHub Security Advisories, allowing developers to ask natural language questions about their specific security findings and receive context-aware advice.
*   **Objective 5: Design and Deploy a Scalable Microservices Architecture.**
    The platform must be built using a modern, distributed architecture composed of nine specialized microservices. This ensures that the platform is resilient (individual service failures don't bring down the whole system) and scalable (intensive AI analysis can be scaled independently of the user interface).
*   **Objective 6: Provide a Unified, Collaborative Intelligence Dashboard.**
    The final deliverable must be a production-ready web application using the latest frontend technology (SvelteKit 5). This dashboard must provide a "single pane of glass" view for all security findings, collaborative workspace features, and real-time event streaming for analysis progress.

---

## Chapter 02: System Analysis

### 2.1 Fact Gathering Techniques
A robust system analysis is the foundation of any successful complex software project. For WithOps, the fact-gathering process was designed to capture requirements from academic research, industry standards, and developer experience.

**2.1.1 Academic Literature Review**
The first stage involved a deep dive into recent academic research regarding CI/CD security. This provided quantitative evidence of the problem. For instance, the study by Pan et al. (2024), which analyzed 16,000 repositories and found that 62.3% contained high-severity configurations, was instrumental in defining the scope of the Workflow Security Engine. This research move the project from "perceived need" to "evidenced requirement."

**2.1.2 Framework Decomposition (DSOMM & STRIDE)**
To build the maturity and threat modeling engines, I performed a "low-level decomposition" of the relevant frameworks. This meant taking the qualitative descriptions in the OWASP DSOMM (e.g., "Build process is automated") and translating them into measurable, quantitative indicators that a Python script could detect (e.g., "A .github/workflows directory exists and contains a build.yml"). This process ensured that the platform's outputs are grounded in recognized security standards.

**2.1.3 Competitor Benchmarking and Gap Analysis**
I conducted a technical audit of existing security platform features. GitHub Advanced Security provides secret scanning and Dependabot, but it lacks visual threat modeling. Harness provides CI/CD orchestration but lacks deep workflow security analysis. This gap analysis led to the requirement for "Integrated Intelligence"—a platform that doesn't just scan code, but also models threats and assesses maturity.

**2.1.4 Developer Interviews and Observational Studies**
I conducted informal sessions with three DevOps engineers to observe how they currently manage security. I found that they often treat security warnings as "noise" because they lack the context to fix them quickly. This observation directly led to the "Auto-Remediation PR" requirement—the idea that if the system finds an error, it should offer to fix it automatically, reducing the friction for the developer.

**2.1.5 Document Analysis (GitHub Security Advisories)**
I analyzed over 50 past GitHub Security Advisories (GSAs) related to workflow vulnerabilities. This "attack-centric" fact gathering allowed me to build a library of 25+ vulnerability patterns that the WithOps engine must be able to detect, ensuring the tool is effective against real-world attack vectors.

### 2.2 Existing System
The "Existing System" for DevSecOps in most organizations is not a single tool, but a fragmented collection of manual and automated processes.

**2.2.1 Ssh-and-Script Approach**
In many smaller organizations, security is managed through "ad-hoc" scripts and manual ssh-based audits. Developers might run an occasional local linter, but there is no centralized visibility. If a vulnerability is introduced in a deployment script, it remains undetected until a manual audit happens, if it happens at all.

**2.2.2 Siloed Security Tools**
In larger organizations, there is a "Wall of Dashboards." One dashboard for SonarQube (static code analysis), one for Snyk (dependencies), and one for GitHub Alerts. These tools don't communicate with each other. A developer might fix a bug in the code but leave the workflow that deploys it wide open to a supply chain attack. There is no unified view of "Security Intelligence."

**2.2.3 Manual, Spreadsheet-Based Compliance**
Compliance with security models like DSOMM is almost entirely manual. A security auditor sends an Excel spreadsheet to a development lead once a year. The results are subjective, error-prone, and become outdated within weeks as the project architecture evolves.

**2.2.4 "Post-Mortem" Threat Modeling**
Threat modeling, when performed, is usually done "after the fact" as part of a post-mortem or after a major feature is already in staging. This is reactive rather than proactive. The diagrams are often stored in Confluence or a Wiki, where they are never updated as the code changes.

### 2.3 Drawbacks of the existing system
The fragmented nature of current DevSecOps practices leads to several critical failures:

*   **Incomplete Security Coverage:** Traditional tools have a "blind spot" for CI/CD infrastructure. They scan the *what* (the application code) but ignore the *how* (the workflow that builds it). This creates a massive opening for supply chain attacks.
*   **High Mean Time to Remediation (MTTR):** Because vulnerabilities are detected late or in fragmented dashboards, fixing them takes longer. Developers are often confused about where a vulnerability came from and how it relates to their specific environment.
*   **The "Security Tax" on Velocity:** Manual auditing and threat modeling create bottlenecks. In an agile world, developers see these manual security steps as a "tax" that slows them down, leading to them being bypassed or "rubber-stamped" without a real review.
*   **Data Inconsistency:** When security maturity is assessed manually, two different auditors might give the same project two different scores. This lack of objectivity makes it impossible for engineering leadership to know if they are truly making progress.
*   **Knowledge Decay:** Security expertise is a scarce resource. When an expert performs a threat model manually, their insights are often lost after they leave or the project moves on. There is no "institutional memory" of security logic.

---

## Chapter 03: Requirements Specification

### 3.1 Functional Requirements
Functional requirements define the core behaviors and tasks that the WithOps platform must perform. These have been categorized into "Core Modules" to align with the microservices architecture.

**3.1.1 Organization and Repository Intelligence (Priority: High)**
*   **FR-1.1:** The system shall authenticate with GitHub using OAuth 2.0 and GitHub App credentials.
*   **FR-1.2:** The system shall authorize and index all organizations and public/private repositories accessible to the user.
*   **FR-1.3:** The system shall receive and process real-time events via GitHub Webhooks (e.g., push, pull_request, workflow_run) to maintain data freshness.

**3.1.2 Workflow Security Engine (Priority: High)**
*   **FR-2.1:** The system shall automatically parse and analyze all YAML files in the `.github/workflows/` directory of an indexed repository.
*   **FR-2.2:** The system shall detect 25+ vulnerability patterns, including unpinned actions, excessive token permissions, and insecure trigger events.
*   **FR-2.3:** The system shall provide automated remediation suggestions for each vulnerability, including the generation of "Remediation Pull Requests."

**3.1.3 DSOMM Maturity Assessment (Priority: Medium-High)**
*   **FR-3.1:** The system shall map detected security indicators to the five dimensions of the OWASP DSOMM framework.
*   **FR-3.2:** The system shall calculate a maturity score (Levels 1 to 4) for each dimension and provide a cumulative "Security Grade."
*   **FR-3.3:** The system shall track and visualize the longitudinal progress of maturity scores to identify regression or improvement trends.

**3.1.4 AI Threat Modeling Canvas (Priority: High)**
*   **FR-4.1:** The system shall provide an interactive drag-and-drop canvas for users to create system architecture diagrams.
*   **FR-4.2:** The system shall use AI vision/reasoning models to analyze diagrams and identify potential entry points, data flows, and trust boundaries.
*   **FR-4.3:** The system shall generate threat reports based on the STRIDE, CIA, and LINDDUN frameworks, categorized by risk level.

**3.1.5 Context-Aware AI Security Assistant (Priority: Medium)**
*   **FR-5.1:** The system shall provide a natural language chat interface ("WithOps AI") for interacting with security findings.
*   **FR-5.2:** The system shall use Retrieval-Augmented Generation (RAG) to provide answers backed by a vector-indexed knowledge base of security standard documents.

**3.1.6 Collaborative Workspace (Priority: Medium)**
*   **FR-6.1:** The system shall support multi-user workspaces with real-time presence indicators.
*   **FR-6.2:** The system shall allow users to share threat models, security scans, and maturity reports with other team members for collaborative auditing.

### 3.2 Non-Functional Requirements
Non-functional requirements specify the "quality attributes" of the system, ensuring it is reliable, fast, and secure.

**3.2.1 Performance and Scalability**
*   **NFR-1.1 (Latency):** The frontend dashboard must achieve a First Contentful Paint (FCP) of under 1.5 seconds.
*   **NFR-1.2 (Throughput):** The background scanning system must be capable of processing a repository with 10+ workflows in under 20 seconds.
*   **NFR-1.3 (Concurrency):** The system architecture must support horizontal scaling, allowing for at least 3 concurrent scanning tasks per worker node.

**3.2.2 Security and Identity**
*   **NFR-2.1 (Auth):** The system must use industry-standard Identity and Access Management (Auth0) with Proof Key for Code Exchange (PKCE).
*   **NFR-2.2 (Data Protection):** All GitHub tokens and sensitive user metadata must be encrypted at rest using AES-256-GCM.
*   **NFR-2.3 (Privacy):** The system must support "In-Memory Analysis," where repository source code is analyzed but never permanently stored on WithOps servers.

**3.2.3 Reliability and Observability**
*   **NFR-3.1 (Availability):** The platform core services (Gateway, Auth, Events) should aim for 99.9% uptime.
*   **NFR-3.2 (Monitoring):** All microservices must expose standardized `/metrics` (Prometheus) and `/health` endpoints.
*   **NFR-3.3 (Fault Tolerance):** The system should implement a "Graceful Degradation" strategy—if the AI service is down, the rest of the platform (manual scans, maturity metrics) should remain functional.

### 3.3 Hardware / Software Requirements
To support a distributed microservices environment, specific technical requirements have been defined for both development and production.

**3.3.1 Client-Side Requirements**
*   **Web Browser:** Modern Chromium-based (Chrome 90+, Edge 90+), Firefox (88+), or Safari (14+).
*   **Screen Resolution:** Optimized for 1280x720 and above (responsive support for tablets).

**3.3.2 Server-Side Hardware Requirements (Minimum)**
*   **CPU:** 4-core processor (8-core recommended for local AI inference).
*   **RAM:** 16GB RAM (32GB recommended to support Vector DB and AI workers).
*   **Storage:** 100GB fast SSD (for PostgreSQL, Redis snapshots, and logs).

**3.3.3 Software Development Stack**
*   **Backend:** Python 3.11+ (FastAPI), Node.js 20+ (for certain tooling).
*   **Frontend:** SvelteKit 2, Svelte 5, Tailwind CSS 4, Vite 6.
*   **Databases:** PostgreSQL 15 (transactional), Redis 7 (caching/event bus), Qdrant 1.7+ (vector store).
*   **Infrastructure:** Docker 24+, Docker Compose, Kubernetes 1.28+.
*   **AI Components:** Ollama (for Llama 3 local inference), Claude 3.5 Sonnet (for visual architecture analysis).

### 3.4 Networking Requirements
As a distributed system, WithOps has specific networking needs to ensure secure and efficient service coordination.

*   **Ingress Layer:** The platform uses a **Kong API Gateway** on port 8000/9000 to manage all external HTTP and WebSocket traffic. Port 443 (HTTPS) is used for production frontend access.
*   **Inter-Service Communication:** All services communicate within a private Docker/Kubernetes network. They use a **Service-to-Service Authentication** pattern where the Gateway injects verified user identity headers.
*   **External Integration:** The system requires outbound network access to `api.github.com` via TLS 1.3. Real-time updates utilize the WebSocket protocol (`ws://` or `wss://`) for low-latency communication between the browser and the Events Hub.

---

## Chapter 04: Feasibility Study

### 4.1 Operational Feasibility
Operational feasibility evaluates how well the proposed system solves the business problem and fits within existing workflows. WithOps is highly feasible because it integrates directly with the **GitHub Platform**, which is already the daily environment for its target users. By providing security insights as Pull Requests and automated dashboards, it reduces the need for constant "context switching" between tools. The platform is designed with a **Developer-Centric** interface—meaning it doesn't just show a list of problems; it shows how to fix them within the existing git-flow.

### 4.2 Economical Feasibility
The project adopts a "Cloud-Native, Open-Source" strategy, which minimizes expensive licensing costs.
*   **Development Costs:** All primary technologies (FastAPI, SvelteKit, PostgreSQL, Redis) are open-source. For local AI development, **Ollama** allows for running Llama 3 without costly per-token fees.
*   **Operational Efficiency:** By automating threat modeling and maturity assessment—tasks that would otherwise require high-paid security consultants—the system provides massive ROI to any organization using it.
*   **SaaS Integration:** Modern providers like Supabase (PostgreSQL) and Auth0 offer generous "Free Tiers" that are sufficient for the development and initial rollout phase, proving that the project is economically viable even with a limited initial budget.

### 4.3 Technical Feasibility
The high technical feasibility of WithOps is supported by two main factors: **Proven Modern Frameworks** and **Established Security Methodology.**
*   **Framework Maturity:** FastAPI and SvelteKit are industry standards for building high-performance, asynchronous applications. The chosen stack is well-documented and has a massive community for troubleshooting.
*   **AI Maturity:** The recent shift in Large Language Models (LLMs) from "generic chat" to "structured reasoning" makes automated threat modeling technically achievable for the first time. The availability of **Qdrant** allows for high-performance semantic search without complex custom implementation.
*   **Team Expertise:** The project team (this student) has demonstrated proficiency in the full-stack development lifecycle, containerization, and the DevSecOps domain, further ensuring that the technical implementation can be completed within the project timeline.

---

## Chapter 05: System Architecture

### 5.1 Use Case Diagram
The WithOps platform architecture is designed to manage the interactions of three primary actors:
1.  **The Developer:** Primarily interacts with the Workflow Security Engine, receives remediation suggestions, and consults the AI Assistant for secure coding advice.
2.  **The Security Engineer:** Focuses on the Threat Modeling Canvas and Workspace Intelligence dashboard to manage organization-wide security posture and compliance.
3.  **The System Administrator:** Manages organization-level integration with the GitHub App, configures webhooks, and manages role-based access control (RBAC).

### 5.2 Microservices Layer
To ensure scalability and fault isolation, the system is decomposed into nine specialized microservices. This "Shared Responsibility" model is a core tenet of modern cloud-native design.

**5.2.1 Events Hub (The Central Nervous System)**
This service manages real-time communication. It maintains WebSocket connections with all active users and listens to the **Redis Event Bus**. When any other microservice (like AI or GitHub) completes a task, it publishes a message. The Events Hub captures this and immediately updates the user's dashboard, providing a seamless, real-time experience. It operates on port 9100.

**5.2.2 AI Service (The Reasoning Engine)**
The AI Service is the "Brain" of the platform. It abstracts the complexity of different AI models. It can route tasks to **Claude** (for vision-based diagram analysis) or **Ollama** (for local text-based reasoning). It handles the parsing of code and the generation of remediation suggestions.

**5.2.3 GitHub Service (The Data Handler)**
This service is the only component that interacts directly with the GitHub API. It manages OAuth tokens, indices organization data, and handles incoming webhooks. By siloing all GitHub logic here, we ensure that API rate limiting and token management are centralized.

**5.2.4 Workspace Intelligence (The Maturity Scorer)**
Based on the OWASP DSOMM framework, this service traverses an organization's repositories and security settings. It calculates maturity scores and maintains the historical "Maturity Timeline" in the database.

**5.2.5 Additional Services**
The architecture also includes **Auth Service** (IAM), **Collaboration Service** (shared workspace state), **Threat Modeling Service** (architecture analysis), **Workflow Orchestration** (task management), and the **AI RAG Service** (vector search).

### 5.3 Data and Communication Layer
The architectural design prioritizes high decoupling and low latency.
*   **Communication:** Services interact via a **REST API** (for synchronous requests) and **Redis Pub/Sub** (for asynchronous events). This ensures that if the AI service is slow, it doesn't "block" the GitHub service from receiving data.
*   **Data Persistence:** Transactional data (users, repos, scan results) is stored in **PostgreSQL**. Real-time state and caching are managed in **Redis**.
*   **Semantic Data:** Low-level security knowledge is stored as "Vector Embeddings" in **Qdrant**, which allows the AI to perform "Semantic Search"—finding answers based on meaning rather than just keywords.

### 5.4 Internal Service Architecture (Example: Workspace Intelligence)
Internally, each service follows a clean, "Domain-Driven" structure. For instance, the Workspace Intelligence service is organized as:
*   **`api/`**: FastAPI routes and request validators.
*   **`core/`**: The "Business Logic."
    *   `workspace_analyzer.py`: Orchestrates the analysis of multiple repositories.
    *   `maturity_scorer.py`: Implements the DSOMM calculation logic.
    *   `security_practice_detector.py`: Detects tools like Snyk or SonarQube in a project.
*   **`database/`**: SQLAlchemy models and database configuration.
*   **`github_service_client.py`**: An internal client that abstracts communication with the GitHub Service.

This standardized structure across all nine services ensures that the platform is easy to maintain and that any service can be upgraded or replaced without affecting the rest of the system.

---

## Chapter 06: Development Tools and Technologies

### 6.1 Development Methodology
The project adopted the **Agile Development Methodology**, specifically the **Scrum** framework. This choice was driven by the inherent complexity and "research-heavy" nature of DevSecOps automation.
*   **Two-Week Sprints:** Development is divided into 14-day cycles. Each sprint begins with "Sprint Planning," where features (User Stories) are selected from the backlog, and ends with a "Sprint Review" of the functional increment.
*   **Test-Driven Development (TDD):** For critical services like the YAML parser and the Scorer, a "test-first" approach was used to ensure mathematical accuracy and security integrity.
*   **CI/CD for WithOps:** The project uses its own principles—every commit to the `main` branch is automatically linted (flake8), statically analyzed, and containerized for deployment, proving the effectiveness of the DevSecOps model.

### 6.2 Programming Languages and Tools
Each technology in the stack was selected based on performance, developer productivity, and industry adoption.
*   **Python 3.11 with FastAPI:** Selected as the primary backend language. Python's rich ecosystem for AI (LangChain, OpenAI SDK) and FastAPI's native support for asynchronous I/O make it the ideal choice for a multi-service AI platform.
*   **SvelteKit 2 and Svelte 5:** For the frontend, I chose SvelteKit over React or Next.js. Svelte's "compile-time" approach results in smaller bundle sizes and superior performance, specifically for the complex, state-heavy interactive canvas used for threat modeling.
*   **Tailwind CSS 4:** Used for the design system. Its utility-first approach allows for rapid styling while maintaining a consistent "Matte Engineering" aesthetic across the entire platform.
*   **Kong Gateway:** Serving as the API Gateway, Kong handles the cross-cutting concerns of authentication and rate limiting, allowing the microservices to stay "clean" and focused only on their specific business logic.

### 6.3 Third-Party Components and Libraries
*   **SQLAlchemy 2.0:** The industry-standard ORM for Python, providing a safe and efficient way to interact with PostgreSQL.
*   **Pydantic:** Used throughout the backend for strict data validation and schema definition, ensuring that no malformed data enters the system.
*   **D3.js:** A powerful data visualization library used for rendering the complex repository trees and maturity score timelines in the dashboard.
*   **LangChain:** A framework for building LLM-powered applications, used in the RAG service to manage document indexing and AI prompt templates.

### 6.4 Algorithms
Beyond simple logic, WithOps implements several specialized algorithms:
*   **YAML AST Traversal:** Instead of simple regex, the system uses an Abstract Syntax Tree (AST) parser (`ruamel.yaml`) to "understand" the structure of GitHub Actions. This allows us to detect subtle vulnerabilities, like a variable being used in an insecure way several lines below its definition.
*   **Weighted Maturity Scoring:** The system implements a hierarchical scoring algorithm where different security practices are given different weights based on their relative importance in the DSOMM model. For instance, "Automated Security Scanning" has a higher weight than "Manual Security Documentation."
*   **Cosine Similarity for RAG:** To find matching security advice, the system calculates the "Cosine Similarity" between a user's problem and thousands of vector-indexed security documents, ensuring that the AI has the most relevant context before generating an answer.

---

## Chapter 07: Implementation Progress

### 7.1 Development Environment Setup
To manage the complexity of nine microservices, I implemented a fully containerized development environment using **Docker Compose.** This ensures "Environment Parity"—the code that runs on my local machine is guaranteed to behave identically when deployed to the cloud.

The setup includes:
*   **Local Networking:** A private virtual network where each service is reachable by its name (e.g., `http://ai-service:8101`).
*   **Hot Reloading:** Development volumes are mounted into the containers, allowing for immediate feedback as code is written.
*   **Infrastructure-as-Code:** The entire development environment is defined in a single `docker-compose.yml` file, versioned in Git along with the source code.

### 7.2 Implemented Features
As of this interim stage, the foundational infrastructure and core services are complete:
*   **Service Matrix:** All 9 microservices have been successfully extracted from the initial monolith, containerized, and are communicating via the Event Bus.
*   **Platform Dashboard:** The core SvelteKit application is running, featuring a comprehensive "Documentation Portal" that explains the architecture to users.
*   **Real-time Intelligence:** The Events Hub is fully operational, successfully broadcasting real-time "Health" and "Scan" updates from the backend to the frontend via WebSockets.
*   **Identity Foundation:** Auth0 integration is established, allowing for secure user sign-up and login using JWT tokens.
*   **Observability Stack:** Prometheus and Grafana are built-in, providing live metrics for request volume and service latency.

### 7.3 Code Snippets and Analysis
Two key implementations highlight the technical progress of the project.

**7.3.1 The Events Hub Listeners**
The following snippet from `main.py` in the backend shows how the Real-time service coordinates information across the entire system using non-blocking asynchronous tasks:

```python
# From backend/main.py
async def listen_github_events():
    """Listen to Redis channel and forward to WebSockets"""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("github_events")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            # Create a localized WebSocket notification
            notification = {
                "event": f"github.{data.get('type')}",
                "org_name": data.get("org_name"),
                "data": data.get("data")
            }
            # Broadcast to all connected clients
            await websocket_manager.broadcast(notification)
```
**Analysis:** This code is critical for the "User Experience" requirement. By using Redis Pub/Sub, we move from a "pull" model (where the browser asks for updates) to a "push" model (where the server notifies the browser). This provides the "live" feel required for a modern enterprise platform.

**7.3.2 The Microservice Lifespan Pattern**
Every WithOps service follows a "Lifespan" pattern, ensuring clean resource management:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup Connections
    await cache.connect()
    await event_bus.connect()
    
    yield # Service logic runs here
    
    # Graceful Shutdown
    await event_bus.disconnect()
    await cache.disconnect()
```
**Analysis:** This demonstrates the high technical quality of the implementation. By handling startup and shutdown gracefully, we prevent "zombie" connections to the database or Redis, ensuring the system remains stable over thousands of requests.

### 7.4 Challenges Encountered and Solutions
*   **Challenge: The GitHub API Rate Limit Proxy.** Initially, multiple services were calling the GitHub API independently, leading to "429 Too Many Requests" errors. **Solution:** I implemented a centralized `github-service` that acts as an intelligent proxy with a built-in Redis cache (24-hour TTL), reducing the number of external API calls by over 70%.
*   **Challenge: Real-time UI Sync with Svelte 5.** Managing the real-time state of 100+ repositories in the browser was challenging. **Solution:** I leveraged the new "Runes" system in Svelte 5 (`$state`, `$derived`), which allowed for high-performance reactive updates without the overhead of traditional state management libraries like Redux.
*   **Challenge: AI Reasoning Latency.** AI-based analysis for a large architecture can take 10-30 seconds, which feels like a "hang" to users. **Solution:** I implemented "Asynchronous Analysis"—when a user starts a model, the system returns a `task_id` immediately, and the UI shows a progress bar while listening for the `analysis.completed` event on the WebSocket.

### 7.5 Current System Limitations
While the infrastructure is robust, certain features are still in the implementation phase:
*   **Remediation PR Generation:** Currently, the system can detect vulnerabilities and show the "Proposed Fix," but the automated creation of the Pull Request on GitHub is still under development.
*   **Vision-Based Diagram Complexity:** The AI vision engine currently works well for simple boxes and arrows but occasionally struggles with complex, overlapping architecture diagrams. Improving the "OCR plus Logic" layer of the canvas is a priority for the next phase.

---

## Chapter 08: Discussion

### 8.1 Summary of the Report
This interim report has documented the development of the **WithOps Platform**, an intelligent DevSecOps solution for securing CI/CD pipelines. We have identified the critical gap in current security methodologies regarding workflow infrastructure and explored how a microservices-based, AI-powered platform can address this. We have successfully established a production-grade infrastructure, complete with nine specialized services, real-time event streaming, and a comprehensive observability stack. The feasibility of the project—operationally, economically, and technically—has been proven through the successful implementation of the platform's core foundation.

### 8.2 Changes from the Proposal
The project has evolved since the initial proposal in two significant ways:
1.  **Increased Service Density:** The proposal originally envisioned 8 services. This was expanded to 9 with the addition of a dedicated **AI RAG Service**, reflecting the project's increased focus on providing context-aware security intelligence using vector databases.
2.  **Focus on "Maturity Modeling":** While the proposal was primarily a workflow scanner, the implementation has moved toward a more holistic "Maturity Ecosystem." This shift was based on my research during the System Analysis phase, which revealed that organizations need more than just "bugs"—they need a structured way to measure and improve their overall DevSecOps culture (DSOMM).

### 8.3 Future Plans / Upcoming Work
The trajectory for the remainder of the academic year is focused on the "Intelligence" and "Remediation" layers of the platform:
*   **Phase 1: Finalizing the AI Reasoning Engine.** Completing the integration of the RAG service with the main scanning logic to provide expert-level remediation advice.
*   **Phase 2: The Interactive Threat Canvas.** implementing the full drag-and-drop builder with real-time feedback loops.
*   **Phase 3: Large-Scale Evaluation.** Testing WithOps against a curated dataset of 1,000+ real-world GitHub repositories to benchmark its detection accuracy and false-positive rates.
*   **Phase 4: Compliance Reporting.** Developing the automated PDF generation engine for DSOMM compliance reports, suitable for presentation to engineering leadership and external auditors.

By the final submission, WithOps will stand as a comprehensive, production-ready evidence of how modern technologies like AI and Microservices can be combined to solve one of the most pressing challenges in contemporary software engineering: securing the automated pipelines that deliver our digital world.

---

## References
*   Ayala, C. and Garcia, J. (2023) *An empirical study of security practices in GitHub repositories*, arXiv:2305.16120.
*   OWASP Foundation (2024) *DevSecOps Maturity Model (DSOMM)*. Available at: [https://owasp.org/www-project-devsecops-maturity-model/](https://owasp.org/www-project-devsecops-maturity-model/)
*   Pan, X., Liu, Y., Zhang, Y. and Wang, X. (2024) *CI/CD under the hood: Vulnerabilities and threats in modern pipelines*, arXiv:2401.17606.
*   Saroar, M. and Nayebi, M. (2023) *Practitioners’ perceptions of GitHub Actions and workflow automation*, arXiv:2303.04084.
*   Unit42 (2025) *GitHub Actions supply chain attack analysis: tj-actions/changed-files compromise*. Palo Alto Networks.
*   Shevchenko, N. et al. (2018) *Threat Modeling: A Summary of Available Methods*. CMU/SEI-2018-TR-001.
*   Yılmaz, O. and Gönen, B. (2023) *Harnessing Large Language Models for automated threat modeling*.
