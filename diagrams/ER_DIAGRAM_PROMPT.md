# ER Diagram Prompt — Copy & Paste

Copy the prompt below and paste it into ChatGPT (GPT-4o), Gemini, or any AI diagram tool.

---

## Prompt

Create a comprehensive **Entity-Relationship (ER) Diagram** using **standard Chen Notation** for a **DevSecOps Intelligence Platform** called **WithOps**. The system manages GitHub CI/CD workflow security analysis, threat modeling, and vulnerability scanning.

**Use standard Chen notation with:**

- **Rectangles** for Entities
- **Ovals** for Attributes (underline Primary Keys, italicize Foreign Keys)
- **Diamonds** for Relationships
- **Cardinality notation** (1, N, M) on connecting lines

---

### Entities and Attributes

**1. USERS**

- ~~id~~ (PK, UUID)
- auth_user_id (String)
- email (String)
- name (String)
- github_username (String)
- is_active (Boolean)
- created_at (Timestamp)

**2. ORGANIZATIONS**

- ~~id~~ (PK, UUID)
- github_org_id (Integer)
- login (String)
- name (String)
- type (String)

**3. ORGANIZATION_INSTALLATIONS** _(Associative Entity)_

- ~~id~~ (PK, UUID)
- _user_id_ (FK → USERS)
- _organization_id_ (FK → ORGANIZATIONS)
- github_installation_id (Integer)
- status (String)

**4. REPOSITORIES**

- ~~id~~ (PK, UUID)
- _installation_id_ (FK → ORGANIZATION_INSTALLATIONS)
- github_repo_id (Integer)
- full_name (String)
- language (String)
- default_branch (String)

**5. WORKFLOWS**

- ~~id~~ (PK, UUID)
- _repository_id_ (FK → REPOSITORIES)
- name (String)
- path (String)
- content (Text)
- state (String)

**6. THREAT_MODELS**

- ~~id~~ (PK, UUID)
- _user_id_ (FK → USERS)
- _organization_id_ (FK → ORGANIZATIONS)
- name (String)
- methodology (String)
- status (String)
- canvas_data (JSON)

**7. THREAT_ASSESSMENTS**

- ~~id~~ (PK, UUID)
- _threat_model_id_ (FK → THREAT_MODELS)
- threat_category (String)
- impact_level (String)
- risk_level (String)
- ai_generated (Boolean)

**8. SECURITY_SCANS**

- ~~id~~ (PK, UUID)
- _repository_id_ (FK → REPOSITORIES)
- _scan_initiator_ (FK → USERS)
- scan_type (String)
- risk_score (Float)
- status (String)

**9. SECURITY_VULNERABILITIES**

- ~~id~~ (PK, UUID)
- _scan_id_ (FK → SECURITY_SCANS)
- vulnerability_type (String)
- severity (String)
- title (String)
- status (String)

**10. PROJECT_ANALYSES**

- ~~id~~ (PK, UUID)
- _user_id_ (FK → USERS)
- analysis_scope (String)
- maturity_score (Float)
- status (String)
- total_repositories (Integer)

**11. CHAT_CONVERSATIONS**

- ~~id~~ (PK, UUID)
- _user_id_ (FK → USERS)
- title (String)
- analysis_scope (String)
- message_count (Integer)

---

### Relationships

| #   | Relationship | Entity 1       | Entity 2                 | Cardinality | Label                                         |
| --- | ------------ | -------------- | ------------------------ | ----------- | --------------------------------------------- |
| R1  | Belongs To   | USERS          | ORGANIZATIONS            | N : M       | "Belongs To" (via ORGANIZATION_INSTALLATIONS) |
| R2  | Contains     | ORGANIZATIONS  | REPOSITORIES             | 1 : N       | "Contains" (via installations)                |
| R3  | Has          | REPOSITORIES   | WORKFLOWS                | 1 : N       | "Has"                                         |
| R4  | Creates      | USERS          | THREAT_MODELS            | 1 : N       | "Creates"                                     |
| R5  | Contains     | THREAT_MODELS  | THREAT_ASSESSMENTS       | 1 : N       | "Contains"                                    |
| R6  | Scans        | REPOSITORIES   | SECURITY_SCANS           | 1 : N       | "Scans"                                       |
| R7  | Discovers    | SECURITY_SCANS | SECURITY_VULNERABILITIES | 1 : N       | "Discovers"                                   |
| R8  | Runs         | USERS          | PROJECT_ANALYSES         | 1 : N       | "Runs"                                        |
| R9  | Initiates    | USERS          | CHAT_CONVERSATIONS       | 1 : N       | "Initiates"                                   |

---

### Design Requirements

- Use **color-coded entity groups**:
  - **Blue** = Core Domain (Users, Organizations, Repositories, Workflows)
  - **Green** = Threat Modeling (Threat Models, Threat Assessments)
  - **Orange** = Security Scanning (Security Scans, Security Vulnerabilities)
  - **Purple** = Workspace Intelligence (Project Analyses)
  - **Red** = AI Chat (Chat Conversations)
- Primary Key attributes should be **underlined and bold**
- Foreign Key attributes should be in **italics**
- Relationship diamonds should be **yellow/amber** colored
- All text must be **clearly readable** with large font sizes
- Include **cardinality labels** (1, N, M) on every relationship line
- Use a **clean white background** with professional styling
- Title: **"Figure 5.3 — Entity-Relationship Diagram"**
- Subtitle: **"WithOps DevSecOps Intelligence Platform · Supabase PostgreSQL 15"**
- The diagram should be suitable for an academic report (PUSL3190 Interim Report)
