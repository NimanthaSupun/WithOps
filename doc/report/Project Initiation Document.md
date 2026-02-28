<img src="./m4khe2ui.png"
style="width:2.5743in;height:1.42986in" />

> **PUSL3190** **Computing** **Project**
>
> **Project** **Initiation** **Document** **(PID)**
>
> DevSecOps Intelligence Platform for GitHub Workflow Security and
> Threat Modeling
>
> Supervisor: Prof. Chaminda Wijesinghe
>
> Name: Ilukwaththe Ariyarathne
>
> Plymouth Index Number: 10953742 Degree Program: BSc (Hons) Data
> Science

Table of Contents

**Introduction**..............................................................................................................................2
Background and
Context........................................................................................................2
Problem
Statement.................................................................................................................2
Scope and
Limitations............................................................................................................3
Expected Impact and
Stakeholders........................................................................................3
**Business**
**Case**............................................................................................................................3
2.1 Business
Need..................................................................................................................3
2.2 Business
Objectives.........................................................................................................4
**Project**
**Objectives**....................................................................................................................4
**Literature** **Review**
....................................................................................................................5
DSOMM Maturity
Assessment..............................................................................................5
CI/CD Pipeline Security
Vulnerabilities................................................................................6
GitHub Actions
Complexity..................................................................................................6
Threat Modeling Automation
................................................................................................6
Integrated Gap
Analysis.........................................................................................................7
**Method** **of**
**Approach**................................................................................................................7
Research
Design.....................................................................................................................7
Data Sources and Collection
Plan..........................................................................................7
Algorithms and Tools
............................................................................................................8
Evaluation Metrics and Validation
Strategy..........................................................................9
Project Management
Methodology........................................................................................9
Project Management
Methodology......................................................................................10
**Conceptual**
**Diagram**..............................................................................................................10
Component
Responsibilities................................................................................................12
**Initial** **Project**
**Plan**.................................................................................................................12
**Risk**
**Analysis**..........................................................................................................................13
Technical
Risks....................................................................................................................13
Operational
Risks.................................................................................................................13
Project Management Risks
..................................................................................................13
**References**...............................................................................................................................14

> **1** **\|** Page

**Introduction**

Background and Context

Modern software development relies heavily on CI/CD pipelines like
GitHub Actions to automate build, test, and deployment processes. While
this automation accelerates delivery, it has created new security
vulnerabilities. Research by Pan et al. (2024) reveals that over 60% of
CI/CD pipelines contain critical misconfigurations, making them
attractivetargets forsupply chain attacks. The March 2025 compromise of
the tj-actions/changed-files GitHub Action demonstrated how a single
vulnerable component can affect thousands of dependent projects (Unit42,
2025).

Despite growing awareness of DevSecOps principles, organizations lack
practical tools to assess their security maturity, analyze workflow
vulnerabilities, and model threats within their development processes.
Existing solutions like GitHub Dependabot focus narrowly on
dependencies, while platforms like Harness address orchestration without
comprehensive security analysis. No current tool integrates workflow
security scanning, automated maturity assessment against frameworks like
OWASP DSOMM, and AI-powered threat modeling into a unified platform.

This project addresses this gap by providing an intelligent DevSecOps
platform that combines automated GitHub Actions workflow analysis,
DSOMM-based maturity scoring, and AI-assisted threat modeling. By
integrating these capabilities, organizations can proactively identify
vulnerabilities, measure security improvements, and maintain secure
development practices without sacrificing delivery speed.

Problem Statement

Organizations face four critical challenges in securing their CI/CD
workflows

> ❖First, workflow misconfigurations remain undetected until exploited.
> Unpinned dependencies, excessive permissions, insecure triggers, and
> leaked credentials create vulnerabilities that traditional security
> tools miss because they analyze application code rather than workflow
> infrastructure.
>
> ❖Second, organizations cannot objectively measure their DevSecOps
> maturity. While OWASP DSOMM provides a theoretical framework, manual
> assessment is time-consuming and inconsistent, preventing continuous
> monitoring of security posture.
>
> ❖Third, threat modeling remains disconnected from development
> workflows. Traditional tools require separate processes and
> specialized expertise, leading many teams to skip this critical
> security step entirely.
>
> ❖Fourth, GitHub Actions YAML complexity creates barriers to secure
> workflow development. Saroar and Nayebi (2023) found that 60.87% of
> developers find YAML error-prone, resulting in workflows that are
> difficult to understand, review, and secure.

These challenges manifest as increased supply chain attack risk,
compliance failures, wasted developer productivity, and inability to
demonstrate security improvements to stakeholders

> **2** **\|** Page

Scope and Limitations

WithOps(This project) will provide automated analysis of GitHub Actions
workflows to detect security vulnerabilities including outdated actions,
unpinned dependencies, insecure triggers, and credential exposure. The
platform will integrate with GitHub via OAuth to retrieve organization
and repository data, automatically assess DevSecOps maturity using DSOMM
framework, and provide AI-powered threat modeling through an interactive
visual canvas.

The project scope includes workflow security analysis, DSOMM maturity
scoring, threat modeling with STRIDE/LINDDUN frameworks, real-time
notifications, interactive dashboards, and automated remediation
recommendations. The platform will support multi-user collaboration and
provide exportable compliance reports.

**Out** **of** **scope**: The platform will analyze but not execute
workflows, will focus exclusively on GitHub Actions (not GitLab CI or
Jenkins), will not perform real-time code scanning during development,
and will not include penetration testing or active vulnerability
exploitation.

Expected Impact and Stakeholders

Primary stakeholders include development teams who will receive
automated security feedback, security engineers who gain comprehensive
CI/CD visibility, DevOps engineers who obtain actionable workflow
improvement insights, and engineering managers who access objective
security metrics.

Expected impacts include reducing workflow security issue detection from
weeks to minutes, achieving 95%+ detection accuracy for common
misconfigurations, enabling organizations to progress at least oneDSOMM
maturity level within 12 months, and decreasing security-related
workflow failures by 40% through proactive identification.

**Business** **Case**

2.1 Business Need

> ❖The need for WithOps stems from three converging industry trends.
> First, software supply chain attacks have increased by 742% between
> 2019 and 2024, with CI/CD pipelines becoming prime targets. Attackers
> compromise build infrastructure rather than application code,
> affecting thousands of downstream organizations simultaneously.
> Current defensive measures focus on post-deployment security while
> failing to secure the workflows themselves.
>
> ❖Second, regulatory compliancerequirements areintensifying. TheEUCyber
> Resilience Act, Executive Order 14028, and industry standards (SOC 2,
> ISO 27001) now mandate demonstrable secure development practices.
> Organizations must prove DevSecOps maturity through documented
> controls and continuous monitoring, yet translating frameworks like
> OWASP DSOMM into operational practice remains challenging without
> automated tools.
>
> **3** **\|** Page
>
> ❖Third, security excellence has become a competitive differentiator.
> Customers require security attestations before vendor engagement, and
> security-conscious engineers prefer employers who provide modern
> security tooling. Organizations demonstrating superior security
> practices gain advantages in enterprisesales, customer trust, and
> talent acquisition.

WithOps addresses these needs by providing automated workflow security
monitoring that scales without proportional security staff increase,
objective DSOMM maturity scoring providing auditable compliance
evidence, AI-powered threat modeling reducing expertise barriers, and
developer-friendly integration improving security without degrading
velocity.

2.2 Business Objectives

The platform pursues six measurable business objectives aligned with
organizational security goals

> ❖Objective 2: Achieve DSOMM Level 3 maturity across all five
> dimensions within 18 months, progressing organizations from typical
> Level 1-2 baseline to comprehensive integration acceptable to
> enterprise customers and regulatory auditors.
>
> ❖Objective 3: Decrease threat modeling time by 60% from current 40-60
> hours to 15-25 hours through AI-assisted analysis, enabling security
> review for more projects without increasing team size.
>
> ❖Objective 4: Improve developer security engagement by 50%, measured
> through security issue remediation participation and average time to
> resolution, fostering cultural transformation where developers own
> security.
>
> ❖Objective 5: Generate compliance reports with 95% accuracy acceptable
> to external auditors with minimal manual correction, reducing audit
> preparation time from 120-200 hours per cycle.
>
> ❖Objective 6: Achieve 95%+ user adoption within development teams to
> maximize platform ROI and ensure security insights reach developers
> during decision-making.

**Project** **Objectives**

WithOps defines specific project objectives focusing on deliverables and
acceptance criteria

> ❖**Objective** **1:** **Develop** **GitHub** **Workflow** **Security**
> **Analysis** **Engine**
>
> The platform will analyze GitHub Actions YAML files to detect 25+
> vulnerability patterns including unpinned actions, outdated versions,
> insecure triggers, hardcoded secrets, and excessive permissions.
> Success criteria include parsing 99%+ of valid workflows without
> errors, completing organization analysis (\<200 repositories) within 3
> minutes, and maintaining false positive rate below 5% for critical
> findings.
>
> **4** **\|** Page
>
> ❖**Objective** **2:** **Implement** **DSOMM** **Maturity**
> **Assessment** **System**
>
> The system will map detected security practices to all five DSOMM
> dimensions **(Build** **&** **Deployment,** **Implementation,**
> **Culture** **&** **Organization,** **Information** **Gathering,**
> **Test** **&** **Verification)**, tracking maturity progression over
> time. Success criteria include assessment consistency within 2%
> varianceon repeated evaluations and maturity scores correlating with
> independent auditor assessments at r \> 0.85.
>
> ❖**Objective** **3:** **Build** **AI-Powered** **Threat** **Modeling**
> **Canvas**
>
> An interactive visual canvas will enable system architecture diagram
> creation, with AI analyzing diagrams using STRIDE, CIA, and LINDDUN
> frameworks. Success criteria include AI identifying system components
> with 90%+ accuracy, generating threat analyses covering relevant
> categories, and completing analysis for medium-complexity systems
> within 10 minutes.
>
> ❖**Objective** **4:** **Develop** **RAG** **Learning** **System**
>
> A Retrieval-Augmented Generation system using vector database will
> enhance AI responses with DevSecOps security knowledge. Success
> criteria include semantic search retrieving relevant context in top 5
> results with 85%+ accuracy, query response latency under 2 seconds for
> 95th percentile, and RAG-enhanced responses rated more accurate than
> base model in 70%+ of comparisons.
>
> ❖**Objective** **5:** **Create** **Microservices** **Architecture**
>
> Eight independent microservices (Events Hub, GitHub Service, AI
> Service, Threat Modeling Service, Workspace Intelligence Service, Auth
> Service, Collaboration Service, Workflow Orchestration Service) will
> communicate via event bus and API gateway. Success criteria include
> services deploying independently without coordinated releases, system
> tolerating individual service failure with graceful degradation, and
> 99% uptime for critical paths.
>
> ❖**Objective** **6:** **Build** **Production-Ready** **Frontend**
> **Application**
>
> A modern web application will provide interactive dashboards, visual
> workflow representation, and collaborative threat modeling. Success
> criteria include first contentful paint under 1.5 seconds, task
> completion rate \>85% for core workflows, and System Usability Scale
> score \>75.

**Literature** **Review**

The WithOps platform addresses gaps across four research domains:
DevSecOps maturity modeling, CI/CD security, threat modeling automation,
and AI-augmented security analysis.

DSOMM Maturity Assessment

The OWASP DevSecOps Maturity Model provides a comprehensive framework
for assessing security integration across five dimensions, defining
maturity levels from basic awareness to advanced automation (OWASP
Foundation, 2024). However, Jit (2024) identifies a "theory-to-practice
gap" where organizations understand DSOMM conceptually but struggle with
operationalization. Manual evaluation requires 40-80 hours per
assessment, making continuous monitoring impractical. Existing tools do
not automatically map observable development artifacts to DSOMM
dimensions.

> **5** **\|** Page

**Research** **Gap**: While DSOMM provides theoretical structure,
practical automated assessment tools deriving maturity scores from
repository analysis are absent. WithOps addresses this by
programmatically analyzing repositories to detect security practice
indicators and automatically mapping them to DSOMM dimensions.

CI/CD Pipeline Security Vulnerabilities

Pan et al. (2024) analyzed 16,000 repositories, finding 62.3% contained
at least one high-severity workflow misconfiguration. Common
vulnerabilities include actions pinned to mutable tags (73%), excessive
permissions (41%), insecure triggers (28%), and hardcoded secrets (15%).
The March 2025 tj-actions compromise demonstrated practical impact, with
attackers exfiltrating GitHub tokens from thousands of repositories
(Unit42, 2025). Ayala and Garcia (2023) found only 14% of repositories
implement adequate dependency pinning, and existing tools provide
fragmented coverage focused on application code rather than workflow
security.

**Research** **Gap**: Comprehensive automated security analysis
specifically targeting CI/CD workflows is absent. WithOps provides
dedicated workflow security analysis detecting 25+ vulnerability
patterns with automated remediation recommendations.

GitHub Actions Complexity

Saroar and Nayebi (2023) surveyed 394 practitioners, finding 60.87%
consider YAML syntax error-prone, with workflow debugging consuming 6.3
hours per developer monthly. The cognitive load of indentation-sensitive
syntax combined with domain-specific language creates barriers to secure
development. Research indicates 71% of workflows derive from templates,
amplifying insecure pattern propagation (Yampolskiy et al., 2022).

**Research** **Gap**: Tools reducing YAML complexity through
visualization and providing security-focused guidance are limited.
WithOps transforms YAML workflows into visual structured representations
with AI-generated security recommendations.

Threat Modeling Automation

Traditional methodologies (STRIDE, LINDDUN) remain manual processes
requiring 40-60 hours for moderately complex systems, creating
bottlenecks preventing comprehensive coverage(Shevchenko et al., 2018).
Recent research explores AIassistance: Yılmazand Gönen (2023)
demonstrated LLM-generated threats achieving 73% recall versus expert
analysis. However, existing tools require manual threat entry with
minimal AI integration and lack development workflow integration.

**Research** **Gap**: No tools combine visual diagram analysis,
multi-framework threat identification, AI suggestions, and development
workflow integration. WithOps integrates vision-based diagram analysis
with AI-powered multi-framework threat generation and continuous
learning from user feedback.

> **6** **\|** Page

Integrated Gap Analysis

Research consistently identifies isolated solutions addressing
individual DevSecOps aspects without integration. WithOps uniquely
combines automated DSOMM scoring, comprehensive workflow security
scanning, visual workflow representation, and AI-powered threat modeling
into a unified intelligence platform, transforming reactive fragmented
practices into proactive integrated security operations.

**Method** **of** **Approach**

Research Design

This project adopts a design science research approach with elements of
experimental, prototype driven, and case study-based research. The
primary outcome of the research is a functional software artifact the
WithOps DevSecOps Intelligence Platform designed to address real-world
challenges in CI/CD security and DevSecOps maturity assessment.

The research is prototype driven, where the platform is incrementally
designed, implemented, and refined through multiple iterations.
Experimental elements are introduced by evaluating automated security
detection, AI-assisted threat modeling, and DevSecOps maturity scoring
against defined metrics. Additionally, a case-study approach is used by
applying the platform to multiple GitHub organizations and repositories,
enabling observation of security posture and maturity progression in
realistic environments.

This combined research design allows the project to generate both
practical engineering outcomes and validated insights into the
effectiveness of DevSecOps automation.

Data Sources and Collection Plan

**Primary** **Data** **Sources**

The primary data source for the platform is the GitHub ecosystem,
accessed through ❖ GitHub REST API (v3)

> ❖ GitHub GraphQL API (v4)

Data collected includes

> ❖ Organization metadata (name, size, plan type) ❖ Repository structure
> and metadata
>
> ❖ CI/CD workflow definitions (.github/workflows/\*.yml) ❖ GitHub
> Actions usage and version information
>
> ❖ Available security alerts such as Dependabot findings

**User** **Interaction** **Data**

To support AI improvement through Retrieval-Augmented Generation (RAG),
the system collects anonymized user interaction data, including

> **7** **\|** Page
>
> ❖ Threat modeling canvas structures
>
> ❖ User feedback on AI-generated threats
>
> ❖ Corrections and refinements made by users

These data are stored as vector embeddings rather than raw content,
preserving privacy while enabling semantic learning.

**Sample** **Size**

The planned dataset includes

> ❖ At least 100 GitHub organizations
>
> ❖ A minimum of 1,000 CI/CD workflow files ❖ At least 50 active users
> providing feedback
>
> ❖ Approximately 20 organizations tracked longitudinally for maturity
> progression

**Privacy** **and** **Ethical** **Considerations**

All data collection strictly follows GitHub’s terms of service and user
consent principles. The platform only accesses repositories explicitly
authorized by users. Sensitive credentials are encrypted using
**AES-256** **at** **rest** and **TLS** **1.3** **in** **transit**.
Repository source code is not permanently stored; analysis is performed
in-memory, and users may request data deletion at any time.

Algorithms and Tools

The platform is implemented using **microservices** **architecture**

**Backend**

> ❖ FastAPI (Python 3.11)
>
> ❖ PostgreSQL 15 (Supabase)
>
> ❖ Redis 7.x (cache and pub/sub) ❖ Qdrant 1.7+ (vector database) ❖ Kong
> 3.x (API gateway)

❖ Docker for containerization **Frontend**

> ❖ SvelteKit 5
>
> ❖ Tailwind CSS 4
>
> ❖ D3.js for visualization
>
> ❖ WebSockets for real-time updates

**Microservices** **Architecture**

The system is composed of multiple independent microservices, each
responsible for a specific domain such as GitHub integration, AI
processing, threat modeling, workspace intelligence, collaboration,
authentication, and workflow orchestration. This approach improves
scalability, fault isolation, and maintainability while aligning with
DevSecOps principles.

> **8** **\|** Page

**Algorithms**

> ❖ YAML parsing and AST traversal for workflow security detection ❖
> Regex and entropy-based secret detection
>
> ❖ Semantic version comparison for outdated action detection ❖ Weighted
> DSOMM maturity scoring algorithm
>
> ❖ AI-assisted threat modeling using STRIDE and LINDDUN frameworks ❖
> Retrieval-Augmented Generation (RAG) using vector similarity search

**AI** **Models**

> ❖ Claude API for vision-based diagram analysis
>
> ❖ Ollama for local LLM inference and embeddings

Evaluation Metrics and Validation Strategy

System effectiveness is evaluated using quantitative and qualitative
metrics

> ❖ **Security** **Accuracy:** Precision, recall, and F1-score of
> workflowvulnerability detection ❖ **Maturity** **Assessment:**
> Consistency between automated DSOMM scores and expert
>
> assessments
>
> ❖ **AI** **Quality:** Threat relevance ratings, false positive rates,
> and RAG response improvement
>
> ❖ **Performance:** API latency, throughput, uptime, and scalability
> under load
>
> ❖ **Usability:** Task completion rate, time-on-task, System Usability
> Scale (SUS)
>
> ❖ **Business** **Impact:** Maturity progression, incident reduction,
> developer productivity gains

Validation includes alpha testing with synthetic datasets, beta testing
with real organizations, comparative analysis against manual audits and
existing tools, longitudinal studies, and expert security reviews.

Project Management Methodology

The platform is evaluated using a combination of technical, security,
user experience, and business impact metrics.

**Technical** **Evaluation**

> ❖ Precision, recall, and F1-score for workflow vulnerability detection
>
> ❖ Consistency of automated DSOMM maturity scoring compared to expert
> assessments ❖ API latency, throughput, and error rates

**AI** **and** **Security** **Evaluation**

> ❖ Relevance and accuracy of AI-generated threats ❖ False positive and
> false negative rates
>
> ❖ Effectiveness of RAG compared to baseline LLM outputs

**User-Centered** **Evaluation** ❖ Task completion rate

> ❖ Time required to complete key workflows
>
> ❖ User satisfaction measured using SUS and NPS scores
>
> **9** **\|** Page

**Validation** **Approach**

Validation is conducted through

> ❖ Alpha testing using synthetic datasets
>
> ❖ Beta testing with early adopter organizations ❖ Comparative analysis
> of manual security audits
>
> ❖ Longitudinal studies tracking maturity progression ❖ Expert review
> by security professionals

Project Management Methodology

The project follows an Agile development methodology integrated with
DevOps practices, using two-week sprint cycles.

Sprint Structure

> ❖ Week 1**:** Feature development, unit testing, service integration
>
> ❖ Week 2: User testing, optimization, documentation, sprint review
>
> ❖ Continuous: CI/CD execution, monitoring, logging, and feedback
> collection

**Version** **Control** **and** **CI/CD**

Development is managed using Git with a feature-branch workflow, pull
request reviews, and automated CI/CD pipelines. These pipelines enforce
testing, security scanning, and quality gates before code integration.

**Quality** **Assurance** Quality is ensured through

> ❖ Test-driven development with \>80% coverage ❖ Automated integration
> and end-to-end testing ❖ Security scanning and dependency analysis
>
> ❖ Structured documentation and sprint retrospectives

This methodology ensures timely delivery, high software quality, and
alignment with both academic research standards and industry DevSecOps
practices.

**Conceptual** **Diagram**

> **10** **\|** Page

<img src="./guq3ykyx.png" style="width:6.0875in;height:9.55in" />

> **11** **\|** Page

<img src="./xksduw2f.png" style="width:7.54167in;height:4.25in" />Component
Responsibilities

> ❖**Frontend** **Layer:** User interface providing dashboards, workflow
> visualization, and threat modeling canvas with real-time WebSocket
> updates.
>
> ❖**API** **Gateway:** Single entry point routing requests to
> appropriate microservices, enforcing rate limiting and authentication.
>
> ❖**Microservices:** Eight independent services handling GitHub
> integration, AI analysis, threat modeling, workspace intelligence,
> authentication, collaboration, events coordination, and workflow
> orchestration.
>
> ❖**Data** **Layer:** PostgreSQL for relational data, Qdrant for vector
> embeddings and semantic search, Redis for caching and pub/sub
> messaging.
>
> ❖**External** **Services**: GitHub API for repository data, Auth0 for
> identity management, Claude AI for vision analysis, Ollama for local
> LLM inference.

This architecture enables horizontal scaling of services, resilience
through fault isolation, and maintainability through clear service
boundaries.

**Initial** **Project** **Plan**

> **12** **\|** Page

**Risk** **Analysis**

Technical Risks

> ❖Risk T1: GitHub API Rate Limiting (Likelihood: High \| Impact: High)
>
> GitHub enforces rate limits (5,000 requests/hour) that could prevent
> analysis of large organizations. Mitigation strategies include
> implementing intelligent request batching, deploying Redis caching
> with 24-hour TTL, using exponential backoff retry logic, requesting
> academic rate limit increases, and designing incremental analysis
> allowing partial results.
>
> ❖Risk T2: AI Service Dependency on External APIs (Likelihood: Medium
> \| Impact: High)
>
> Claude API represents a single point of failure for threat modeling.
> Mitigation includes implementing fallback to Ollama-only analysis,
> caching APIresponses, designing text-based alternatives to visual
> analysis, establishing API usage monitoring with budget limits, and
> maintaining relationships with multiple AI providers (OpenAI as
> backup).
>
> ❖Risk T3: Database Performance Degradation (Likelihood: Medium \|
> Impact: Medium) Query performance may degrade with large-scale data.
> Mitigation includes designing schema with appropriate indexes,
> implementing query performance monitoring, using connection pooling,
> implementing pagination, leveraging read replicas, and catching
> expensive queries in Redis.

Operational Risks

> ❖Risk O1: Inadequate Testing Coverage (Likelihood: Medium \| Impact:
> High) Complex architecture increases likelihood of production bugs.
> Mitigation includes maintaining \>80% code coverage, implementing
> comprehensive integration tests, conducting manual exploratory
> testing, deploying staged rollout (canary deployment), implementing
> error tracking, and maintaining detailed logging.
>
> ❖Risk O2: Security Vulnerability in Platform (Likelihood: Low \|
> Impact: Critical) Security breaches would catastrophically damage
> credibility. Mitigation includes implementing OWASP Top 10 prevention,
> using Auth0 for authentication, encrypting data at rest and in
> transit, conducting dependency scanning with automatic updates,
> performing SAST in CI/CD, engaging third-party security audit, and
> maintaining incident response plan.

Project Management Risks

> ❖Risk P1: Scope Creep (Likelihood: High \| Impact: Medium)
>
> Feature additions could delay critical functionality. Mitigation
> includes maintaining strict prioritization using MoSCoW method,
> implementing timeboxing, conducting weekly progress reviews,
> supervisor oversight ensuring scope alignment, and documenting
> deferred features transparently.
>
> ❖Risk P2: External Dependency Changes (Likelihood: Medium \| Impact:
> Medium)
>
> **13** **\|** Page
>
> External services could introduce breaking changes or pricing changes.
> Mitigation includes pinning dependency versions, monitoring
> changelogs, implementing adapters abstracting integrations,
> maintaining test suites, establishing fallback providers, and
> budgeting for cost increases.
>
> ❖Risk P3: Key Person Risk (Likelihood: Medium \| Impact: High)
>
> Project relies on single developers. Mitigation includes maintaining
> comprehensive documentation, regular supervisormeetings, frequent
> codecommitting with descriptive messages, writing clean commented
> code, maintaining project management artifacts, and identifying backup
> developers for emergencies.

All high-priority risks will be monitored monthly with risk status
reported to supervisor. The project accepts reasonable technical risk
for innovation while maintaining zero tolerance for security, data
integrity, and deadline compliance risks.

**References**

> ❖Ayala, C. and Garcia, J. (2023) *An* *empirical* *study* *of*
> *security* *practices* *in* *GitHub* *repositories*, arXiv preprint
> arXiv:2305.16120. Available at:
> [<u>https://arxiv.org/abs/2305.16120</u>](https://arxiv.org/abs/2305.16120)
> (Accessed: 3 January 2026).
>
> ❖Jit (2024) *From* *DSOMM* *theory* *to* *practical* *enforcement:*
> *A* *DevSecOps* *journey*. Available at:
> [<u>https://www.jit.io/resources/devsecops/from-dsomm-theory-to-practical-enforcement-a-devsecops-journey</u>](https://www.jit.io/resources/devsecops/from-dsomm-theory-to-practical-enforcement-a-devsecops-journey)
> (Accessed: 3 January 2026).
>
> ❖OWASP Foundation (2024) *DevSecOps* *Maturity* *Model* *(DSOMM)*.
> Available at:
> [<u>https://owasp.org/www-project-devsecops-maturity-model/</u>](https://owasp.org/www-project-devsecops-maturity-model/)
> (Accessed: 3 January 2026).
>
> ❖Pan, X., Liu, Y., Zhang, Y. and Wang, X. (2024) *CI/CD* *under* *the*
> *hood:Vulnerabilities* *and* *threats* *in* *modern* *pipelines*,
> arXiv preprint arXiv:2401.17606. Available at:
> [<u>https://arxiv.org/abs/2401.17606</u>](https://arxiv.org/abs/2401.17606)
> (Accessed: 3 January 2026).
>
> ❖Saroar, M. and Nayebi, M. (2023) *Practitioners’* *perceptions* *of*
> *GitHub* *Actions* *and* *workflow* *automation*, arXiv preprint
> arXiv:2303.04084. Available at:
> [<u>https://arxiv.org/abs/2303.04084</u>](https://arxiv.org/abs/2303.04084)
> (Accessed: 3 January 2026).
>
> ❖Shevchenko, N., Chick, T.A., O’Riordan, P., Scanlon, T.P. and Woody,
> C. (2018) *Threat* *Modeling:* *A* *Summary* *of* *Available*
> *Methods*. Technical Report CMU/SEI-2018-TR-001. Software Engineering
> Institute, Carnegie Mellon University.
>
> ❖Unit42 (2025) *GitHub* *Actions* *supply* *chain* *attack*
> *analysis:* *tj-actions/changed-files* *compromise*. Palo Alto
> Networks Unit 42. Available at:
> [<u>https://unit42.paloaltonetworks.com/github-actions-supply-chain-attack/</u>](https://unit42.paloaltonetworks.com/github-actions-supply-chain-attack/)
> (Accessed: 3 January 2026).
>
> **14** **\|** Page
