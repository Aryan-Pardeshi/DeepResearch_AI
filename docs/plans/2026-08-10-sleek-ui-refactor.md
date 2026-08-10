# Sleek Vercel/Linear Style Minimalist UI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up visual clutter, remove heavy plasma orbs and multi-color borders, and establish a sleek, ultra-clean Vercel/Linear-style dark aesthetic across the entire app.

**Architecture:** Remove noisy HTML elements in `index.html`, simplify card/background CSS rules in `style.css`, and update prompt template chip listeners in `app.js`.

**Tech Stack:** HTML5, CSS3 Glassmorphism, Vanilla JS.

---

### Task 1: Clean Up HTML Noise in `index.html`

**Files:**
- Modify: `research-bot/frontend/index.html`

- [ ] **Step 1: Remove `.hero-plasma-container`, `.hero-metrics-strip`, `.engine-capability-bar`, `.hero-card-gradient-border`, and `.rm-ambient-aura` elements from index.html**
- [ ] **Step 2: Replace bulky template grid with streamlined prompt template pills**

```html
<div class="template-chips-container">
    <span class="template-chip" data-prompt="Efficacy of cognitive behavioral therapy for healthcare worker burnout...">🧬 Clinical CBT</span>
    <span class="template-chip" data-prompt="Impact of generative AI code assistants on software developer productivity...">🤖 GenAI Code Security</span>
    <span class="template-chip" data-prompt="Macroeconomic predictors of digital health platform adoption in rural systems...">📈 Digital Health Markets</span>
    <span class="template-chip" data-prompt="Comparative analysis of transformer architectures for time-series forecasting...">🔬 Time-Series Transformers</span>
</div>
```

- [ ] **Step 3: Commit HTML cleanup**

```bash
git add research-bot/frontend/index.html
git commit -m "refactor(frontend): clean up plasma containers, metrics strips, and convert template cards to sleek prompt chips"
```

---

### Task 2: Refine CSS Aesthetics in `style.css`

**Files:**
- Modify: `research-bot/frontend/style.css`

- [ ] **Step 1: Update body background and clean up glow keyframes / card styles in style.css**

```css
body {
    background: #09090b radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.12), transparent 45%) no-repeat;
    color: var(--text-primary);
    min-height: 100vh;
}

.search-box-container,
.rm-input-card,
.card {
    background: rgba(18, 18, 22, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: var(--radius-lg);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(12px);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-box-container:focus-within,
.rm-input-card:focus-within,
.card:focus-within {
    border-color: rgba(99, 102, 241, 0.4) !important;
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.15) !important;
}

.template-chips-container {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 1rem;
}

.template-chip {
    padding: 0.4rem 0.85rem;
    border-radius: 50px;
    background-color: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
}

.template-chip:hover {
    background-color: rgba(99, 102, 241, 0.15);
    border-color: rgba(99, 102, 241, 0.4);
    color: #ffffff;
}
```

- [ ] **Step 2: Commit CSS updates**

```bash
git add research-bot/frontend/style.css
git commit -m "refactor(frontend): streamline body background, input card borders, and template chip styling in style.css"
```

---

### Task 3: Update Event Listeners in `app.js`

**Files:**
- Modify: `research-bot/frontend/app.js`

- [ ] **Step 1: Update template chip event listener query selector**

```javascript
document.querySelectorAll('.template-chip').forEach(chip => { ... });
```

- [ ] **Step 2: Commit app.js changes**

```bash
git add research-bot/frontend/app.js
git commit -m "refactor(frontend): update click handler selector for template prompt chips in app.js"
```
