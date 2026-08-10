# Research Mode Ambient Backlight & Glow Effects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the ambient backlight glow aura from DeepSearch to Research Mode input containers, pipeline trackers, checkpoint review cards, and output panels.

**Architecture:** Add ambient spotlight elements to `index.html`, define glow keyframes and box-shadow backlight utilities in `style.css`, and update `app.js` to toggle backlight glow during pipeline execution.

**Tech Stack:** HTML5, CSS3 Radial Gradients & Glow Shadows, Vanilla JS.

---

### Task 1: Add Ambient Backlight CSS & Glow Utilities in `style.css`

**Files:**
- Modify: `research-bot/frontend/style.css`

- [ ] **Step 1: Add Ambient Backlight Keyframes & Card Glow Classes**

```css
@keyframes ambientPulse {
    0%, 100% {
        opacity: 0.45;
        transform: translate(-50%, -50%) scale(1);
    }
    50% {
        opacity: 0.7;
        transform: translate(-50%, -50%) scale(1.1);
    }
}

.rm-ambient-aura {
    position: absolute;
    top: 30%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 600px;
    height: 350px;
    background: radial-gradient(ellipse at center, rgba(56, 189, 248, 0.15), rgba(99, 102, 241, 0.1), transparent 70%);
    filter: blur(60px);
    pointer-events: none;
    z-index: 0;
    animation: ambientPulse 6s ease-in-out infinite;
}

.rm-glow-card {
    position: relative;
    z-index: 1;
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.rm-glow-card:focus-within,
.rm-glow-card.active-execution {
    border-color: rgba(56, 189, 248, 0.6) !important;
    box-shadow: 0 0 25px rgba(56, 189, 248, 0.3), 0 0 50px rgba(99, 102, 241, 0.2), inset 0 0 15px rgba(56, 189, 248, 0.08) !important;
}
```

- [ ] **Step 2: Commit CSS updates**

```bash
git add research-bot/frontend/style.css
git commit -m "feat(frontend): add CSS backlight aura keyframes and glowing card utilities"
```

---

### Task 2: Insert Ambient Backlight Containers in `index.html`

**Files:**
- Modify: `research-bot/frontend/index.html`

- [ ] **Step 1: Add `.rm-ambient-aura` to Research Mode panels in index.html**

```html
<section id="rm-landing-panel" class="panel" style="position: relative;">
    <div class="rm-ambient-aura"></div>
    ...
```

- [ ] **Step 2: Commit index.html changes**

```bash
git add research-bot/frontend/index.html
git commit -m "feat(frontend): add ambient aura backlight elements to Research Mode panels in index.html"
```

---

### Task 3: Toggle Active Execution Glow in `app.js`

**Files:**
- Modify: `research-bot/frontend/app.js`

- [ ] **Step 1: Add `.active-execution` toggle during active SSE stream**

```javascript
// Toggle .active-execution on pipeline-tracker-container and rm-paper-card during execution
```

- [ ] **Step 2: Commit app.js updates**

```bash
git add research-bot/frontend/app.js
git commit -m "feat(frontend): toggle active backlight glow on cards during pipeline execution in app.js"
```
