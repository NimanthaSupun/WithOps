# Workspace Intelligence: DSOMM-Powered Security Maturity Assessment

## What is Workspace Intelligence?
Workspace Intelligence is the strategic "command center" of the WithOps platform. It provides a high-level, yet deeply technical, analysis of an entire organization's security posture. By scanning every repository, workflow, and policy, it determines the overall "Maturity Level" of your DevSecOps practices.

Unlike traditional scanners that just list vulnerabilities, Workspace Intelligence evaluates **governance and process**. It tells you not just *if* you have a bug, but *how* well you are equipped to prevent, find, and fix bugs across your entire fleet.

## Who is it for?
*   **CISOs and Security Directors:** To get a bird's-eye view of organization-wide security compliance.
*   **DevSecOps Engineers:** To identify gaps in CI/CD pipelines and security tool coverage.
*   **Team Leads:** To compare their project's security maturity against the organization's standards.

## How it Works: The OWASP DSOMM Framework
Workspace Intelligence is built on the **OWASP DSOMM (DevSecOps Maturity Model)** framework. This is a real-world, industry-standard model for measuring how integrated security is within a development lifecycle.

The platform analyzes your workspace across **5 Core Dimensions**:
1.  **Build & Deployment:** Analyzes CI/CD pipeline security, automated testing, and deployment practices (e.g., "Are you using centralized, trusted workflows?").
2.  **Implementation:** Focuses on secure coding practices, dependency management (SCA), and secret management (e.g., "Are you scanning for API keys in your code?").
3.  **Test & Verification:** Measures the coverage of security testing tools like SAST, DAST, and Container Scanning.
4.  **Information Gathering:** Evaluates vulnerability management, logging, monitoring, and repository policies (e.g., "Is Branch Protection enabled?").
5.  **Culture & Organization:** Tracks human-centric security practices like the use of `CODEOWNERS` and required peer reviews.

## Maturity Levels (L0 - L4)
The platform assigns a level to each dimension based on detected practices:
*   **L0 (None):** No security practices detected.
*   **L1 (Basic):** Occasional use of security tools or manual processes.
*   **L2 (Advanced):** Consistent use of security tools across most repositories.
*   **L3 (Mature):** Fully integrated security with automated gates and centralized governance.
*   **L4 (Optimized):** Continuous improvement and proactive security measures.

## Key Features & Value
### 1. Unified Organization Analysis
Instead of looking at repos one by one, you can run a **Unified Analysis**. This aggregates data from every project, providing a single "Maturity Score" (out of 100) for the whole company.

### 2. Practice Detection
The system automatically identifies the tools you are currently using:
*   **SAST (Static Analysis):** Tools like CodeQL, SonarQube, or Snyk.
*   **SCA (Dependency Audit):** Tools that check for vulnerable libraries (Dependabot, OWASP Dependency-Check).
*   **Secret Scanning:** Detecting leaked passwords and tokens (Gitleaks, TruffleHog).
*   **DAST (Dynamic Analysis) & Container Scanning:** Checking running apps and Docker images.

### 3. AI-Powered Insights ("Ask AI")
Integrated directly into the dashboard is a **Chat Modal**. You can ask the AI questions like:
*   "Why is my Implementation score low?"
*   "How can I reach Level 3 in Build & Deployment?"
*   "Summarize the most critical policy gaps in the 'Marketing' folder."

## Comparison with Existing Tools
Traditional security tools (like GitHub's built-in alerts) focus on **Findings** (the "what"). Workspace Intelligence focuses on **Maturity** (the "how"). 

While GitHub tells you that you have a vulnerable library, WithOps Workspace Intelligence tells you that *60% of your repositories are completely missing dependency scanning tools*, providing a roadmap for systemic improvement rather than just a list of fires to put out.

## Benefits
*   **Visibility:** Stop guessing about your security posture. Know exactly where you stand.
*   **Roadmap:** Use DSOMM levels to set clear, achievable security goals for the next quarter.
*   **Compliance:** Automatically check for repo policies like branch protection and code reviews that are required by SOC2 or ISO 27001.
*   **Efficiency:** Identify centralized workflows to reduce duplication and improve security consistency across teams.
