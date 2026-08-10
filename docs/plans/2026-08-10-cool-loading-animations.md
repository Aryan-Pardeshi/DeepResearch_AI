# Cool Loading Animations & Response Generation UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add modern CSS animations, glowing quantum loaders, skeleton shimmers, live streaming typewriter cursors, and active node flow effects to the frontend UI.

**Architecture:** Add keyframe animations and utility classes to `style.css`, insert wave visualizers and skeleton templates in `index.html`, and update `app.js` to render live streaming cursors and active pulse states.

**Tech Stack:** HTML5, CSS3 Keyframes & Glassmorphism, Vanilla JS.

---

### Task 1: Add Keyframe Animations & Glass Styling to `style.css`

**Files:**
- Modify: `research-bot/frontend/style.css`

**Interfaces:**
- Consumes: CSS custom properties (`--academic-blue`, `--violet-pulse`, `--bg-dark`)
- Produces: CSS animation classes `.orbital-loader`, `.skeleton-shimmer`, `.typing-cursor`, `.ai-wave-bar`, `.active-node-glow`

- [ ] **Step 1: Define Keyframes for Orbital Spinner, Skeleton Shimmer, Wave Bars, and Cursor Glow**

```css
@keyframes orbitalRotate {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes skeletonShimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

@keyframes cursorBlink {
    0%, 100% { opacity: 1; text-shadow: 0 0 8px #38bdf8; }
    50% { opacity: 0; text-shadow: none; }
}

@keyframes wavePulse {
    0%, 100% { height: 4px; }
    50% { height: 16px; }
}

@keyframes nodeGlowPulse {
    0%, 100% { box-shadow: 0 0 8px rgba(56, 189, 248, 0.3), inset 0 0 12px rgba(56, 189, 248, 0.2); }
    50% { box-shadow: 0 0 20px rgba(56, 189, 248, 0.7), inset 0 0 20px rgba(56, 189, 248, 0.4); }
}
```

- [ ] **Step 2: Add Component Styles for Loaders and Live Typing Cursor**

```css
.orbital-loader-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2.5rem 1.5rem;
}
.orbital-ring {
    width: 50px;
    height: 50px;
    border: 3px solid transparent;
    border-top-color: var(--academic-blue);
    border-right-color: var(--violet-pulse);
    border-radius: 50%;
    animation: orbitalRotate 1s linear infinite;
}
.skeleton-line {
    height: 14px;
    border-radius: 4px;
    background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.05) 75%);
    background-size: 200% 100%;
    animation: skeletonShimmer 1.5s infinite;
    margin-bottom: 0.75rem;
}
.typing-cursor {
    display: inline-block;
    width: 8px;
    height: 1.1em;
    background: var(--academic-blue);
    margin-left: 2px;
    vertical-align: middle;
    animation: cursorBlink 0.8s infinite;
}
.ai-wave-container {
    display: inline-flex;
    align-items: flex-end;
    gap: 3px;
    height: 18px;
    margin-left: 8px;
    vertical-align: middle;
}
.ai-wave-bar {
    width: 3px;
    background: var(--academic-blue);
    border-radius: 2px;
    animation: wavePulse 1s ease-in-out infinite;
}
.ai-wave-bar:nth-child(2) { animation-delay: 0.2s; }
.ai-wave-bar:nth-child(3) { animation-delay: 0.4s; }
.ai-wave-bar:nth-child(4) { animation-delay: 0.6s; }
```

- [ ] **Step 3: Commit CSS Keyframe & Animation Styles**

```bash
git add research-bot/frontend/style.css
git commit -m "feat(frontend): add CSS keyframe animations, orbital loader, skeleton shimmer, and typewriter cursor"
```

---

### Task 2: Update HTML Templates for Animated Indicators in `index.html`

**Files:**
- Modify: `research-bot/frontend/index.html`

- [ ] **Step 1: Replace Default Spinner with Orbital Loader and Skeleton Preview**

```html
<div class="paper-placeholder-state" id="rm-paper-placeholder">
    <div class="orbital-loader-container">
        <div class="orbital-ring"></div>
        <p style="margin-top: 1rem; color: var(--text-secondary); font-weight: 500;">
            Autonomous Academic Pipeline Active
            <span class="ai-wave-container">
                <span class="ai-wave-bar"></span>
                <span class="ai-wave-bar"></span>
                <span class="ai-wave-bar"></span>
                <span class="ai-wave-bar"></span>
            </span>
        </p>
    </div>
    <div class="skeleton-preview" style="width: 100%; max-width: 650px; margin-top: 1rem;">
        <div class="skeleton-line" style="width: 70%; height: 22px;"></div>
        <div class="skeleton-line" style="width: 95%;"></div>
        <div class="skeleton-line" style="width: 88%;"></div>
        <div class="skeleton-line" style="width: 92%;"></div>
    </div>
</div>
```

- [ ] **Step 2: Commit HTML updates**

```bash
git add research-bot/frontend/index.html
git commit -m "feat(frontend): update index.html with orbital progress loader and skeleton placeholder"
```

---

### Task 3: JS Streaming Cursor & Active Node Glow in `app.js`

**Files:**
- Modify: `research-bot/frontend/app.js`

- [ ] **Step 1: Add Typing Cursor during Live SSE Streaming**

```javascript
function renderRMPaperLive(isStreaming = false) {
    if (dom.rmPaperTitle) dom.rmPaperTitle.textContent = state.rm.title || 'Synthesizing Academic Paper...';
    if (dom.rmPaperOutput) {
        let content = marked.parse(getPaperMarkdown());
        if (isStreaming) {
            content += '<span class="typing-cursor"></span>';
        }
        dom.rmPaperOutput.innerHTML = content;
    }
}
```

- [ ] **Step 2: Handle `on_chat_model_stream` or live node updates with typing cursor**

```javascript
// Append typing cursor to processRMSEEvent during live node updates
if (data.event === 'token_stream' || data.event === 'node_update') {
    renderRMPaperLive(true);
}
```

- [ ] **Step 3: Test and commit app.js changes**

```bash
git add research-bot/frontend/app.js
git commit -m "feat(frontend): implement live streaming typewriter cursor and active glowing node status in app.js"
```
