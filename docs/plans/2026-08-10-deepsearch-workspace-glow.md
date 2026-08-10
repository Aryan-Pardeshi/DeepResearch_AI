# DeepSearch Approval & Workspace Backlight Glow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add plasma backlight orbs, glowing card borders, and active execution glows to DeepSearch Approval and Workspace panels.

**Architecture:** Update HTML in `index.html`, ensure CSS card glow selectors cover DeepSearch panels in `style.css`, and toggle active execution glow in `app.js`.

**Tech Stack:** HTML5, CSS3 Glassmorphism & Keyframes, Vanilla JS.

---

### Task 1: Update HTML in `index.html`

**Files:**
- Modify: `research-bot/frontend/index.html`

- [ ] **Step 1: Add plasma backdrop and rm-glow-card classes to DeepSearch Approval & Workspace panels in index.html**

```html
<!-- Approval Panel -->
<section id="approval-panel" class="panel" style="position: relative;">
    <div class="hero-plasma-container">
        <div class="plasma-orb plasma-orb-1"></div>
        <div class="plasma-orb plasma-orb-2"></div>
    </div>
    ...

<!-- Workspace Panel -->
<section id="workspace-panel" class="panel" style="position: relative;">
    <div class="hero-plasma-container">
        <div class="plasma-orb plasma-orb-1"></div>
        <div class="plasma-orb plasma-orb-2"></div>
    </div>
    <aside class="workers-sidebar card rm-glow-card">...</aside>
    <article class="report-workspace card rm-glow-card">...</article>
</section>
```

- [ ] **Step 2: Commit HTML updates**

```bash
git add research-bot/frontend/index.html
git commit -m "feat(frontend): add plasma orbs and rm-glow-card classes to DeepSearch approval and workspace panels"
```

---

### Task 2: Toggle Active Execution Glow in `app.js`

**Files:**
- Modify: `research-bot/frontend/app.js`

- [ ] **Step 1: Toggle active execution glow during DeepSearch streaming**

```javascript
// Toggle .active-execution on .report-workspace and .workers-sidebar during DeepSearch run
```

- [ ] **Step 2: Commit app.js changes**

```bash
git add research-bot/frontend/app.js
git commit -m "feat(frontend): toggle active-execution glow on DeepSearch workspace during report synthesis"
```
