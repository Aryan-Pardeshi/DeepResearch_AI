# Ultra-Cool Homepage UI & Plasma Backlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add floating plasma gradient orbs, animated glowing gradient borders, a hero metrics strip, and typewriter placeholder animations to the homepage.

**Architecture:** Update HTML in `index.html`, define plasma animations and gradient border utility classes in `style.css`, and add typewriter placeholder cycling logic in `app.js`.

**Tech Stack:** HTML5, CSS3 Glassmorphism & Keyframes, Vanilla JS.

---

### Task 1: Add Plasma Keyframes & Gradient Border Styles in `style.css`

**Files:**
- Modify: `research-bot/frontend/style.css`

- [ ] **Step 1: Add Plasma Keyframes & Gradient Border utilities**

```css
@keyframes plasmaFloat1 {
    0%, 100% { transform: translate(-30%, -30%) rotate(0deg) scale(1); }
    50% { transform: translate(-10%, -45%) rotate(180deg) scale(1.2); }
}
@keyframes plasmaFloat2 {
    0%, 100% { transform: translate(20%, -20%) rotate(0deg) scale(1); }
    50% { transform: translate(35%, -40%) rotate(-180deg) scale(1.25); }
}

.hero-plasma-container {
    position: absolute;
    top: 20%;
    left: 50%;
    transform: translateX(-50%);
    width: 800px;
    height: 450px;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
}

.plasma-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.45;
}
.plasma-orb-1 {
    width: 450px;
    height: 450px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.4), rgba(168, 85, 247, 0.2), transparent 70%);
    top: 0;
    left: 10%;
    animation: plasmaFloat1 12s ease-in-out infinite;
}
.plasma-orb-2 {
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(56, 189, 248, 0.35), rgba(236, 72, 153, 0.2), transparent 70%);
    top: 10%;
    right: 10%;
    animation: plasmaFloat2 15s ease-in-out infinite;
}

.hero-card-gradient-border {
    position: relative;
    border-radius: var(--radius-lg);
    padding: 2px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.6), rgba(236, 72, 153, 0.4), rgba(56, 189, 248, 0.6));
    box-shadow: 0 10px 35px rgba(99, 102, 241, 0.25);
    transition: all 0.35s ease;
}

.hero-card-gradient-border:hover,
.hero-card-gradient-border:focus-within {
    box-shadow: 0 0 35px rgba(99, 102, 241, 0.5), 0 0 70px rgba(168, 85, 247, 0.3);
}

.hero-metrics-strip {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    flex-wrap: wrap;
    margin-top: 2rem;
    padding: 0.85rem 1.5rem;
    background: rgba(18, 18, 24, 0.5);
    border: 1px solid var(--card-border);
    border-radius: 50px;
    backdrop-filter: blur(12px);
}
.hero-metric-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.82rem;
    color: var(--text-secondary);
}
.hero-metric-item strong {
    color: #ffffff;
    font-size: 0.9rem;
}
```

- [ ] **Step 2: Commit CSS updates**

```bash
git add research-bot/frontend/style.css
git commit -m "feat(frontend): add plasma background orbs, gradient border cards, and hero metrics strip styles"
```

---

### Task 2: Update HTML in `index.html`

**Files:**
- Modify: `research-bot/frontend/index.html`

- [ ] **Step 1: Add plasma container, gradient card wrapper, and metrics strip to index.html**

```html
<!-- Inside #landing-panel and #rm-input-panel -->
<div class="hero-plasma-container">
    <div class="plasma-orb plasma-orb-1"></div>
    <div class="plasma-orb plasma-orb-2"></div>
</div>

<div class="hero-metrics-strip">
    <div class="hero-metric-item"><span>🤖</span> <strong>20+</strong> Autonomous Agents</div>
    <div class="hero-metric-item"><span>📚</span> <strong>3</strong> Academic API Indexes</div>
    <div class="hero-metric-item"><span>🛡️</span> <strong>100%</strong> Local Privacy (.env)</div>
    <div class="hero-metric-item"><span>⚡</span> <strong>Real-Time</strong> SSE Token Stream</div>
</div>
```

- [ ] **Step 2: Commit HTML updates**

```bash
git add research-bot/frontend/index.html
git commit -m "feat(frontend): add plasma orbs, hero card gradient borders, and metrics strip to index.html"
```

---

### Task 3: Add Typewriter Placeholder Cycling in `app.js`

**Files:**
- Modify: `research-bot/frontend/app.js`

- [ ] **Step 1: Implement animated typewriter placeholder cycler**

```javascript
function initTypewriterPlaceholders() {
    const inputs = [dom.rmPsInput, document.getElementById('query-input')].filter(Boolean);
    const prompts = [
        "Efficacy of cognitive behavioral therapy for healthcare worker burnout...",
        "Impact of generative AI code assistants on software developer productivity...",
        "Macroeconomic predictors of digital health platform adoption in rural systems...",
        "Comparative analysis of transformer architectures for time-series forecasting..."
    ];
    let promptIdx = 0;
    
    setInterval(() => {
        inputs.forEach(input => {
            if (input && document.activeElement !== input && !input.value) {
                promptIdx = (promptIdx + 1) % prompts.length;
                input.placeholder = prompts[promptIdx];
            }
        });
    }, 4500);
}
```

- [ ] **Step 2: Commit app.js changes**

```bash
git add research-bot/frontend/app.js
git commit -m "feat(frontend): add typewriter placeholder cycling to input textareas in app.js"
```
