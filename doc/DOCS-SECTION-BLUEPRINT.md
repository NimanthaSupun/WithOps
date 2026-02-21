# WithOps Documentation Section — Full Blueprint & Continuation Guide

> **Purpose:** This document captures every design decision, implementation detail, file structure, theme system, and remaining work for the `/docs` documentation section of the WithOps DevSecOps Platform. It is designed so that any developer (or AI assistant in a new chat session) can pick up exactly where we left off.

---

## Table of Contents

1. [Project Context](#1-project-context)
2. [Design Philosophy](#2-design-philosophy)
3. [Key Design Decisions](#3-key-design-decisions)
4. [Tech Stack & Dependencies](#4-tech-stack--dependencies)
5. [File Inventory & Descriptions](#5-file-inventory--descriptions)
6. [Theme System & CSS Token Architecture](#6-theme-system--css-token-architecture)
7. [Layout Architecture](#7-layout-architecture)
8. [Navigation Structure](#8-navigation-structure)
9. [Component Patterns & Conventions](#9-component-patterns--conventions)
10. [Page Content Summary](#10-page-content-summary)
11. [What Is Complete](#11-what-is-complete)
12. [What Remains To Do](#12-what-remains-to-do)
13. [Known Issues](#13-known-issues)
14. [How To Continue This Work](#14-how-to-continue-this-work)
15. [Full Page Tree (Future Sections)](#15-full-page-tree-future-sections)

---

## 1. Project Context

**WithOps** is a DevSecOps platform with:

- **Frontend:** SvelteKit 2.16.0 + Svelte 5 + Tailwind CSS 4.0 + Vite 6.2.6
- **Backend:** Python FastAPI (`backend/main.py`)
- **9 Microservices:** ai-service (Claude 3/Llama 3), ai-rag-service, auth-service, github-service, threat-modeling-service, collaboration-service, workflow-orchestration-service, workspace-intelligence-service, events-hub (backend monolith)
- **Gateway:** Kong API Gateway
- **Auth:** Auth0 SPA SDK (OAuth 2.0 + PKCE)
- **Infrastructure:** Docker Compose, Kubernetes (k8s/), monitoring stack

The documentation section lives at route `/docs` and is accessible from the landing page's top navigation bar.

### Landing Page Nav Change

- **File:** `frontend/src/routes/+page.svelte` — line ~511
- **Change:** `<a href="#docs">` was changed to `<a href="/docs" class="nav-link">Documentation</a>`
- This routes users from the landing page to the dedicated docs section.

---

## 2. Design Philosophy

### "Sophisticated Notebook" Aesthetic

The docs section was designed with a **notebook/journal** visual metaphor:

- **Ruled-line background:** Faint horizontal lines spaced 1.5rem apart on main content area, mimicking notebook paper.
- **Binding margin:** A vertical colored line (accent color, low opacity) on the left edge of the content area, mimicking the red margin line in a notebook.
- **Serif headings:** `Source Serif 4` for page titles and section headings — gives an editorial/academic feel.
- **Sans-serif body text:** `Inter` for body text — clean and readable.
- **Monospace code:** `JetBrains Mono` for code blocks, inline code, and technical references.
- **Gentle entrance animations:** Pages fade-in with slight upward translation on mount.
- **Card system:** Content blocks use "notebook cards" with subtle shadows, rounded corners, and optional colored ribbons.

### Light & Dark Mode

Both themes are fully supported. The docs layout subscribes to the global `isDarkMode` store from `$lib/stores.js`. Theme class (`dark` / `light`) is applied to the `.docs-shell` wrapper, and all CSS tokens adapt accordingly.

---

## 3. Key Design Decisions

| Decision                   | Choice                                 | Rationale                                             |
| -------------------------- | -------------------------------------- | ----------------------------------------------------- |
| **Auth gate**              | Public (no login required)             | Docs should be freely accessible for adoption         |
| **Content authoring**      | Pure Svelte components (no mdsvex)     | Full control over layout; no extra dependency         |
| **API reference strategy** | Hybrid (auto-gen + manual) — for later | Auto-gen OpenAPI specs + hand-written guides          |
| **Versioning**             | None (single "latest" version)         | Platform is pre-1.0, versioning adds complexity       |
| **Search**                 | Client-side (Fuse.js) — for later      | No backend needed; fast for docs-sized content        |
| **Routing**                | SvelteKit file-based routing           | Each doc page = a `+page.svelte` under `routes/docs/` |

---

## 4. Tech Stack & Dependencies

### Already installed (no new packages needed)

```
SvelteKit      ^2.16.0
Svelte         ^5.0.0    (uses runes: $state, $derived, $effect, $props)
Tailwind CSS   ^4.0.0    (via @tailwindcss/vite plugin)
Vite           ^6.2.6
```

### Fonts (loaded via Google Fonts CDN in docs layout `<svelte:head>`)

```
Inter           — sans-serif body text (400, 500, 600, 700, 800)
JetBrains Mono  — monospace code blocks (400, 500, 600)
Source Serif 4  — serif headings (400, 600, 700, italic 400)
```

### NOT installed (considered but deferred)

- `mdsvex` — Markdown-in-Svelte preprocessor (not needed for current approach)
- `fuse.js` — Client-side fuzzy search (to be added when search is implemented)
- `shiki` / `prism` — Syntax highlighter (code blocks currently use styled `<pre><code>` with manual formatting)

---

## 5. File Inventory & Descriptions

All docs files live under: `frontend/src/routes/docs/`

| File                                                    | Lines | Purpose                                                                                                        |
| ------------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------- |
| `docs/+layout.svelte`                                   | ~866  | **Docs shell layout** — topbar, sidebar, TOC rail, prev/next nav, notebook background, all CSS tokens          |
| `docs/+page.svelte`                                     | 7     | **Root redirect** — redirects `/docs` → `/docs/getting-started`                                                |
| `docs/getting-started/+page.svelte`                     | ~835  | **Introduction page** — welcome card, 3-step overview, capabilities grid, prerequisites, architecture diagram  |
| `docs/getting-started/quick-start/+page.svelte`         | ~669  | **Quick Start** — Cloud vs Self-Hosted tab switcher, step-by-step instructions, code blocks with copy button   |
| `docs/getting-started/connecting-github/+page.svelte`   | ~680  | **Connecting GitHub** — OAuth vs GitHub App comparison, permission tables, troubleshooting FAQ                 |
| `docs/getting-started/first-security-scan/+page.svelte` | ~969  | **First Security Scan** — scan dimensions, progress animation, severity table, example finding, maturity score |

### Other files modified

| File                               | Change                                              |
| ---------------------------------- | --------------------------------------------------- |
| `frontend/src/routes/+page.svelte` | Line ~511: nav link changed from `#docs` to `/docs` |

---

## 6. Theme System & CSS Token Architecture

The docs layout defines custom CSS properties (tokens) inside `.docs-shell.dark` and `.docs-shell.light` selectors. This is independent of (but consistent with) the dashboard's token system.

### Color Tokens

```css
/* --- Dark mode --- */
.docs-shell.dark {
  --bg-page: #0f0f13; /* Page background */
  --bg-surface: #1a1a24; /* Card/panel background */
  --bg-surface-2: #22222e; /* Elevated surface */
  --bg-surface-3: #2a2a38; /* Hover/active surface */
  --border: #2d2d3d; /* Borders */
  --text-primary: #e8e8f0; /* Main text */
  --text-secondary: #a0a0b8; /* Supporting text */
  --text-muted: #6b6b82; /* Disabled/faded text */
  --accent: #a78bfa; /* Purple accent */
  --accent-hover: #b49bff;
  --accent-subtle: rgba(167, 139, 250, 0.1);
  --callout-info-bg: rgba(96, 165, 250, 0.08);
  --callout-info-border: rgba(96, 165, 250, 0.25);
  --callout-info-text: #93bbfc;
  --callout-tip-bg: rgba(52, 211, 153, 0.08);
  --callout-tip-border: rgba(52, 211, 153, 0.25);
  --callout-tip-text: #6ee7b7;
  --callout-warn-bg: rgba(251, 191, 36, 0.08);
  --callout-warn-border: rgba(251, 191, 36, 0.25);
  --callout-warn-text: #fcd34d;
  --notebook-line: rgba(255, 255, 255, 0.03);
  --notebook-margin: rgba(167, 139, 250, 0.15);
}

/* --- Light mode --- */
.docs-shell.light {
  --bg-page: #faf9f7;
  --bg-surface: #ffffff;
  --bg-surface-2: #f5f4f1;
  --bg-surface-3: #eeedea;
  --border: #e5e3df;
  --text-primary: #1a1a2e;
  --text-secondary: #5a5a72;
  --text-muted: #9a9ab0;
  --accent: #7c3aed;
  --accent-hover: #6d28d9;
  --accent-subtle: rgba(124, 58, 237, 0.08);
  --callout-info-bg: rgba(59, 130, 246, 0.06);
  --callout-info-border: rgba(59, 130, 246, 0.2);
  --callout-info-text: #2563eb;
  --callout-tip-bg: rgba(16, 185, 129, 0.06);
  --callout-tip-border: rgba(16, 185, 129, 0.2);
  --callout-tip-text: #059669;
  --callout-warn-bg: rgba(245, 158, 11, 0.06);
  --callout-warn-border: rgba(245, 158, 11, 0.2);
  --callout-warn-text: #d97706;
  --notebook-line: rgba(0, 0, 0, 0.04);
  --notebook-margin: rgba(124, 58, 237, 0.12);
}
```

### Font Tokens

```css
--font-sans: "Inter", system-ui, sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", monospace;
--font-serif: "Source Serif 4", "Georgia", serif;
```

### How Dark Mode Works (Global)

- **Store:** `$lib/stores.js` exports `isDarkMode` — a Svelte writable store with `.init()`, `.toggle()`, `.set()` methods.
- **Persistence:** localStorage key `darkMode`.
- **DOM:** Toggles `dark` class on `document.documentElement`.
- **Docs layout:** Subscribes to `isDarkMode` and applies class to `.docs-shell` wrapper.

---

## 7. Layout Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  TOPBAR (fixed)                                              │
│  [Logo WithOps] | [Docs label] | [Search bar] | [Dashboard] │
│  [Theme toggle] [GitHub icon] [Mobile menu btn]              │
├─────────┬──────────────────────────────────────┬─────────────┤
│ SIDEBAR │  MAIN CONTENT                        │  TOC RAIL   │
│ (240px) │  (notebook ruled background)         │  (200px)    │
│         │                                      │  Auto-gen   │
│ ▸ Getting│  ┌─ binding margin line             │  from h2/h3 │
│   Started│  │                                  │             │
│   ▹ Intro│  │  [Page Content]                  │  • Section1 │
│   ▹ Quick│  │  - breadcrumbs                   │  • Section2 │
│   ▹ GitHub│ │  - page title (serif)            │    • Sub2.1 │
│   ▹ Scan │  │  - body content                  │  • Section3 │
│         │  │  - cards, callouts, code blocks   │             │
│ ▸ Platform│ │                                  │             │
│   (muted)│  │                                  │             │
│ ▸ Features│ │  [Prev / Next navigation]        │             │
│   (muted)│  │                                  │             │
│ ▸ API    │  └──────────────────────────────────│             │
│   (muted)│                                      │             │
│ ▸ Deploy │                                      │             │
│   (muted)│                                      │             │
├─────────┴──────────────────────────────────────┴─────────────┤
│  (footer area is implicit in content scroll)                 │
└──────────────────────────────────────────────────────────────┘
```

### Key Structural CSS Classes

- `.docs-shell` — Root wrapper, applies theme
- `.docs-topbar` — Fixed header with 56px height
- `.docs-sidebar` — Left panel, 240px wide, fixed position, scrollable
- `.doc-content` — Main content area with notebook lines
- `.toc-rail` — Right side table of contents, hidden on small screens
- `.bottom-nav` — Previous/Next page navigation at bottom of content

### Responsive Behavior

- **Desktop (>1200px):** Full 3-column layout (sidebar + content + TOC)
- **Tablet (768-1200px):** Sidebar collapses, TOC hidden, hamburger menu appears
- **Mobile (<768px):** Full-screen mobile sidebar overlay, single-column content

---

## 8. Navigation Structure

### Currently Implemented (Getting Started section only)

```javascript
const navigation = [
  {
    title: "Getting Started",
    icon: "rocket",
    items: [
      { title: "Introduction", href: "/docs/getting-started" },
      { title: "Quick Start", href: "/docs/getting-started/quick-start" },
      {
        title: "Connecting GitHub",
        href: "/docs/getting-started/connecting-github",
      },
      {
        title: "First Security Scan",
        href: "/docs/getting-started/first-security-scan",
      },
    ],
  },
];
```

### Placeholder Sections (shown as muted/disabled in sidebar)

These sections appear in the sidebar with a "Coming Soon" state — they are visually present but not clickable:

- Platform Overview
- Features & Tools
- API Reference
- Deployment Guide

---

## 9. Component Patterns & Conventions

### Svelte 5 Runes Used

```javascript
let visible = $state(false);          // Reactive state
let { children } = $props();          // Component props
const currentPath = $derived(...);    // Derived values
$effect(() => { ... });               // Side effects
```

### Common UI Patterns Across Pages

#### Breadcrumbs

```html
<div class="breadcrumb">
  <span class="bc-muted">Docs</span>
  <span class="bc-sep">/</span>
  <span class="bc-muted">Getting Started</span>
  <span class="bc-sep">/</span>
  <span class="bc-current">Quick Start</span>
</div>
```

#### Page Header

```html
<h1 class="page-title" id="section-id">Page Title</h1>
<p class="page-lead">Subtitle / introductory paragraph.</p>
```

#### Notebook Card

```html
<div class="notebook-card">
  <div class="card-ribbon"></div>
  <!-- Optional colored left ribbon -->
  <div class="card-body">
    <!-- Content -->
  </div>
</div>
```

#### Callout Boxes

```html
<div class="callout info">
  <!-- or "tip" or "warn" -->
  <div class="callout-icon">💡</div>
  <div class="callout-content"><strong>Note:</strong> Callout text here</div>
</div>
```

#### Code Block with Copy Button

```html
<div class="code-block">
  <div class="code-header">
    <span class="code-lang">bash</span>
    <button class="copy-btn" onclick="{copyCode}">Copy</button>
  </div>
  <pre><code>command here</code></pre>
</div>
```

#### Next Step Card (bottom CTA)

```html
<div class="next-step-card">
  <div class="nsc-content">
    <p class="nsc-label">Next Step</p>
    <h3 class="nsc-title">Page Title →</h3>
    <p class="nsc-desc">Brief description of next page.</p>
  </div>
</div>
```

#### Page Entry Animation

```javascript
let visible = $state(false);
onMount(() => {
  setTimeout(() => (visible = true), 50);
});
```

```html
<div class="page-name {visible ? 'visible' : ''}"></div>
```

```css
.page-name {
  opacity: 0;
  transform: translateY(10px);
  transition: all 0.5s ease;
}
.page-name.visible {
  opacity: 1;
  transform: translateY(0);
}
```

---

## 10. Page Content Summary

### 10.1 Introduction (`/docs/getting-started`)

- Welcome card with ribbon and wave icon
- "What You'll Learn" — 3 step-preview cards (Quick Start, GitHub, Scan) linking to subpages
- Platform capabilities — 4-card grid (AI Security, Threat Modeling, GitHub Integration, Workflow Orchestration)
- Prerequisites checklist (GitHub account, supported browser, repository access)
- Architecture flow diagram (ASCII-style: Browser → Kong → Microservices → AI+Data layers)
- CTA to Quick Start page

### 10.2 Quick Start (`/docs/getting-started/quick-start`)

- Tab switcher: **Cloud** (hosted) vs **Self-Hosted** (Docker)
- Cloud path: Sign Up → Connect GitHub → Select Repo → Run Scan (4 numbered steps)
- Self-Hosted path: Prerequisites (Docker, RAM, Node, Python) → Clone → Configure `.env` → Docker Compose → Access
- Code blocks with copy buttons for all CLI commands
- Environment variable template
- Feature comparison table (Cloud vs Self-Hosted)

### 10.3 Connecting GitHub (`/docs/getting-started/connecting-github`)

- Two-column comparison: OAuth App vs GitHub App
- OAuth scope list: `read:org`, `read:user`, `repo`
- GitHub App permissions grid with Read/Write/Events badges
- Step-by-step connection flow for each method
- Troubleshooting FAQ (3 expandable items: "Not seeing repositories", "Permission errors", "Rate limiting")
- Security notes about token handling

### 10.4 First Security Scan (`/docs/getting-started/first-security-scan`)

- 5 scan dimension cards: SAST, Dependency Audit, Secret Detection, CI/CD Analysis, AI Threat Assessment
- Animated scan progress demo (5 stages with pulse animation for "active" stage)
- Severity classification table: Critical (CVSS 9.0-10.0), High (7.0-8.9), Medium (4.0-6.9), Low (0.1-3.9)
- Example finding card: SQL Injection vulnerability with code snippet + AI-generated fix suggestion
- DevSecOps maturity score breakdown (5 factors)
- Completion celebration card
- "Continue Learning" grid — links to future sections with "Coming Soon" badges

---

## 11. What Is Complete

- [x] Design philosophy and aesthetic defined
- [x] All key design decisions made
- [x] Docs layout shell (`+layout.svelte`) with topbar, sidebar, TOC, bottom nav
- [x] Full dark/light theme token system
- [x] Root redirect (`/docs` → `/docs/getting-started`)
- [x] Introduction page
- [x] Quick Start page (with Cloud/Self-Hosted tabs)
- [x] Connecting GitHub page (OAuth + GitHub App)
- [x] First Security Scan page (scan types, severity, example findings)
- [x] Landing page nav link updated (`/docs`)
- [x] Zero compile errors (validated with IDE error checking)

---

## 12. What Remains To Do

### High Priority (Next Steps)

1. **Run dev server and visually test** — A port issue (`EACCES: permission denied` on port 5173) was encountered. Try `npx vite dev --port 3000` or fix Windows port reservation (see Known Issues).
2. **Visual QA in browser** — Test all 4 pages in both light and dark mode. Check responsiveness at mobile, tablet, and desktop breakpoints.
3. **Fix any visual bugs** — Spacing, font loading, animation timing, responsive breakpoints.
4. **Verify the `brand-icon` image** — The topbar uses `/icons/excellence_17274210.png`. Confirm this file exists in `frontend/static/icons/`.

### Medium Priority (Enhancing Getting Started)

5. **Add real screenshots** — Replace placeholder descriptions with actual UI screenshots from the platform.
6. **Wire up search** — Install `fuse.js`, build a search index from page content, implement the search overlay (currently just a styled input with no functionality).
7. **Add syntax highlighting** — Install `shiki` or `prism` for proper code block syntax highlighting.
8. **Keyboard shortcut (⌘K / Ctrl+K)** — Bind keyboard shortcut to focus the search input.

### Lower Priority (New Sections — Expand Docs)

9. **Platform Overview section** — Architecture deep-dive, microservices explained.
10. **Features & Tools section** — AI analysis, threat modeling, collaboration features.
11. **API Reference section** — Auto-generate from OpenAPI specs + manual guides.
12. **Deployment Guide section** — Docker, Kubernetes, environment configuration.
13. **Contributing / Developer Guide** — Local development setup, code conventions.

### Nice-to-Have

14. **Print stylesheet** — Optimized CSS for printing documentation pages.
15. **Copy link to heading** — Click-to-copy anchor links on h2/h3 headings.
16. **Reading progress bar** — Scroll-based progress indicator in the topbar.
17. **Page last-updated timestamps** — Show when each doc was last modified.

---

## 13. Known Issues

### EACCES Port Permission Issue (Windows)

- **Error:** `Error: listen EACCES: permission denied ::1:5173`
- **Cause:** Windows Hyper-V / WinNAT reserves port ranges that can include 5173.
- **Diagnosis steps performed:**
  - `netstat -ano | findstr :5173` → Port NOT in use by any process
  - `npx vite dev --host 127.0.0.1` → Same EACCES error
  - Was about to check `netsh interface ipv4 show excludedportrange protocol=tcp` when cancelled
- **Solutions (try in order):**
  1. **Use different port:** `npx vite dev --port 3000` or add `server: { port: 3000 }` to `vite.config.js`
  2. **Restart WinNAT (as admin):** `net stop winnat` → `net start winnat` → retry
  3. **Check excluded ranges:** `netsh interface ipv4 show excludedportrange protocol=tcp` — if 5173 is in a range, either change port or reboot

### No mdsvex

- We chose pure Svelte components over mdsvex for full layout control.
- Tradeoff: Content is less portable (can't just write `.md` files), but gives access to Svelte reactivity, animations, and component composition.
- If content authoring becomes a bottleneck, consider adding mdsvex later and converting pages to `.md` with Svelte frontmatter.

---

## 14. How To Continue This Work

### For an AI assistant in a new chat session:

1. **Read this file** (`doc/DOCS-SECTION-BLUEPRINT.md`) — it contains everything you need.
2. **Read the existing files** to understand current state:
   - `frontend/src/routes/docs/+layout.svelte` (the layout shell — ~866 lines)
   - `frontend/src/routes/docs/getting-started/+page.svelte` (intro — ~835 lines)
   - `frontend/src/routes/docs/getting-started/quick-start/+page.svelte` (~669 lines)
   - `frontend/src/routes/docs/getting-started/connecting-github/+page.svelte` (~680 lines)
   - `frontend/src/routes/docs/getting-started/first-security-scan/+page.svelte` (~969 lines)
3. **Understand the theme system** — all CSS tokens are in `+layout.svelte`, not `app.css`. The dark/light class is on `.docs-shell`.
4. **Follow existing patterns** — use the same card, callout, code-block, breadcrumb, and animation patterns documented in Section 9.
5. **When adding a new section** (e.g., Platform Overview):
   - Create `frontend/src/routes/docs/platform-overview/+page.svelte`
   - Add the route to the `navigation` array in `+layout.svelte`
   - Remove the "Coming Soon" state from the sidebar for that section
   - Follow the same page structure (breadcrumbs → header → body → next-step-card)
6. **Global store:** `$lib/stores.js` has the `isDarkMode` store. Import it if needed.
7. **Svelte 5 runes:** Use `$state`, `$derived`, `$effect`, `$props` — NOT the legacy `let x; $: x = ...` syntax.

### For a human developer:

1. Clone the repo and run `cd frontend && npm install`.
2. Start the dev server: `npm run dev -- --port 3000` (port 3000 to avoid the Windows issue).
3. Navigate to `http://localhost:3000/docs`.
4. Use the theme toggle in the top-right to switch between light and dark mode.
5. All docs source is in `src/routes/docs/`. Edit any `+page.svelte` file to update content.
6. The layout shell is in `src/routes/docs/+layout.svelte` — modify this for structural changes (sidebar, topbar, TOC).

---

## 15. Full Page Tree (Future Sections)

This is the planned page tree. Only **Getting Started** is implemented. All other sections show as "Coming Soon" in the sidebar.

```
/docs
├── /getting-started                    ✅ DONE
│   ├── (Introduction)                  ✅ DONE
│   ├── /quick-start                    ✅ DONE
│   ├── /connecting-github              ✅ DONE
│   └── /first-security-scan            ✅ DONE
│
├── /platform-overview                  ⬜ TODO
│   ├── (Architecture)                  ⬜
│   ├── /microservices                  ⬜
│   ├── /ai-engine                      ⬜
│   └── /security-model                 ⬜
│
├── /features                           ⬜ TODO
│   ├── (Overview)                      ⬜
│   ├── /ai-security-analysis           ⬜
│   ├── /threat-modeling                 ⬜
│   ├── /github-integration             ⬜
│   ├── /collaboration                  ⬜
│   ├── /workflow-orchestration         ⬜
│   └── /workspace-intelligence         ⬜
│
├── /api-reference                      ⬜ TODO
│   ├── (Overview)                      ⬜
│   ├── /authentication                 ⬜
│   ├── /repositories                   ⬜
│   ├── /scans                          ⬜
│   ├── /threat-models                  ⬜
│   └── /webhooks                       ⬜
│
├── /deployment                         ⬜ TODO
│   ├── (Overview)                      ⬜
│   ├── /docker                         ⬜
│   ├── /kubernetes                     ⬜
│   ├── /environment-variables          ⬜
│   └── /monitoring                     ⬜
│
└── /contributing                       ⬜ TODO (optional)
    ├── (Developer Guide)               ⬜
    ├── /local-setup                    ⬜
    └── /code-conventions               ⬜
```

---

## Appendix A: Critical File Paths

| What                    | Path                                                                        |
| ----------------------- | --------------------------------------------------------------------------- |
| Docs layout shell       | `frontend/src/routes/docs/+layout.svelte`                                   |
| Docs root redirect      | `frontend/src/routes/docs/+page.svelte`                                     |
| Getting Started intro   | `frontend/src/routes/docs/getting-started/+page.svelte`                     |
| Quick Start             | `frontend/src/routes/docs/getting-started/quick-start/+page.svelte`         |
| Connecting GitHub       | `frontend/src/routes/docs/getting-started/connecting-github/+page.svelte`   |
| First Security Scan     | `frontend/src/routes/docs/getting-started/first-security-scan/+page.svelte` |
| Landing page (nav link) | `frontend/src/routes/+page.svelte` (~line 511)                              |
| Dark mode store         | `frontend/src/lib/stores.js`                                                |
| Root layout             | `frontend/src/routes/+layout.svelte`                                        |
| Vite config             | `frontend/vite.config.js`                                                   |
| Package.json            | `frontend/package.json`                                                     |
| Global CSS              | `frontend/src/app.css`                                                      |
| Project analysis        | `PROJECT_ANALYSIS.md` (root)                                                |

## Appendix B: Quick Reference — Vite Config

Current `vite.config.js` does NOT have a custom server port. To fix the EACCES issue, you can add:

```javascript
export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    port: 3000, // <-- Add this to avoid port 5173 conflict
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  // ... rest of config
});
```

---

_Last updated: February 20, 2026_
_Created to preserve context across AI assistant chat sessions._
