# Landing Page UI Elements & Research Templates Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive research template cards, engine capability pills, and a perspective grid background to the primary landing page.

**Architecture:** Update HTML in `index.html`, add component styles in `style.css`, and implement click-to-autofill template logic in `app.js`.

**Tech Stack:** HTML5, CSS3 Glassmorphism & Grid, Vanilla JS.

---

### Task 1: Add Component Styles in `style.css`

**Files:**
- Modify: `research-bot/frontend/style.css`

- [ ] **Step 1: Add CSS rules for template grid, template cards, capability pills, and grid overlay**

```css
.engine-capability-bar {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 1rem;
    margin-bottom: 1.75rem;
}

.capability-pill {
    background: rgba(99, 102, 241, 0.08);
    border: 1px solid rgba(99, 102, 241, 0.25);
    color: #c7d2fe;
    padding: 0.35rem 0.85rem;
    border-radius: 50px;
    font-size: 0.78rem;
    font-weight: 500;
    backdrop-filter: blur(8px);
}

.research-template-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.85rem;
    margin-top: 1.5rem;
    text-align: left;
}

.template-card {
    background: rgba(18, 18, 24, 0.6);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    padding: 0.85rem 1rem;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.template-card:hover {
    border-color: rgba(99, 102, 241, 0.6);
    background: rgba(30, 27, 75, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.2);
}

.template-icon { font-size: 1.2rem; }
.template-title { font-size: 0.85rem; font-weight: 600; color: var(--text-primary); }
.template-desc { font-size: 0.75rem; color: var(--text-muted); line-height: 1.3; }
```

- [ ] **Step 2: Commit CSS updates**

```bash
git add research-bot/frontend/style.css
git commit -m "feat(frontend): add CSS styles for research template cards and capability pills"
```

---

### Task 2: Insert Template Cards Grid & Capability Pills in `index.html`

**Files:**
- Modify: `research-bot/frontend/index.html`

- [ ] **Step 1: Update `#rm-input-panel` and `#landing-panel` in index.html with capability pills and template cards**

```html
<div class="engine-capability-bar">
    <span class="capability-pill">⚡ Real-Time SSE Token Stream</span>
    <span class="capability-pill">📚 Open-Access Resolvers</span>
    <span class="capability-pill">📊 Auto PRISMA Flow & Evidence Matrix</span>
    <span class="capability-pill">🤖 Per-Run Model Overrides</span>
</div>

<div class="research-template-grid">
    <div class="template-card" data-prompt="Efficacy of cognitive behavioral therapy interventions for healthcare worker burnout: a systematic review">
        <span class="template-icon">🧬</span>
        <span class="template-title">Clinical & Bio-Medical</span>
        <span class="template-desc">CBT interventions for healthcare worker burnout</span>
    </div>
    <div class="template-card" data-prompt="Impact of generative AI code assistants on software developer productivity and code vulnerability density">
        <span class="template-icon">🤖</span>
        <span class="template-title">AI & Software Security</span>
        <span class="template-desc">Generative AI code assistants & security risks</span>
    </div>
    <div class="template-card" data-prompt="Macroeconomic predictors and barrier factors influencing digital health platform adoption">
        <span class="template-icon">📈</span>
        <span class="template-title">Economic & Market Trends</span>
        <span class="template-desc">Predictors of digital health platform adoption</span>
    </div>
    <div class="template-card" data-prompt="Comparative analysis of transformer architectures for high-frequency financial time-series forecasting">
        <span class="template-icon">🔬</span>
        <span class="template-title">Systematic Literature Review</span>
        <span class="template-desc">Transformer architectures for financial forecasting</span>
    </div>
</div>
```

- [ ] **Step 2: Commit HTML updates**

```bash
git add research-bot/frontend/index.html
git commit -m "feat(frontend): add capability pills and template cards grid to index.html landing views"
```

---

### Task 3: Handle Template Card Click Auto-Fill in `app.js`

**Files:**
- Modify: `research-bot/frontend/app.js`

- [ ] **Step 1: Add click listener to template cards to auto-fill input fields**

```javascript
document.querySelectorAll('.template-card').forEach(card => {
    card.addEventListener('click', () => {
        const prompt = card.getAttribute('data-prompt');
        if (!prompt) return;
        
        // Auto-fill active landing input (Research Mode or DeepSearch)
        if (dom.rmPsInput) {
            dom.rmPsInput.value = prompt;
            dom.rmPsInput.focus();
        }
        const queryInput = document.getElementById('query-input');
        if (queryInput) queryInput.value = prompt;
        
        showToast('Template auto-filled into research prompt!', 'info');
    });
});
```

- [ ] **Step 2: Commit app.js changes**

```bash
git add research-bot/frontend/app.js
git commit -m "feat(frontend): implement click-to-autofill logic for research template cards in app.js"
```
