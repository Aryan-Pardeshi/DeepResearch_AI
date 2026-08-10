# Bring Your Own Key Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the header settings button in the frontend UI to display a key icon and the text "Bring your own key".

**Architecture:** Modify `index.html` header actions, add CSS rules for `.btn-byok` in `style.css`, and verify click listener in `app.js`.

**Tech Stack:** HTML5, CSS3, JavaScript (Vanilla), Lucide Icons.

## Global Constraints
- Target directory: `research-bot/frontend/`
- Key icon: `key`
- Button text: `Bring your own key`
- Button ID: `settings-btn`

---

### Task 1: Update HTML Header Settings Button

**Files:**
- Modify: `research-bot/frontend/index.html:46-48`

- [ ] **Step 1: Update settings button in index.html**

Replace lines 46-48 of `research-bot/frontend/index.html`:
```html
<button class="btn-secondary btn-byok" id="settings-btn" title="Configure API Keys">
    <i data-lucide="key" style="width: 15px; height: 15px;"></i>
    <span>Bring your own key</span>
</button>
```

- [ ] **Step 2: Commit**

```bash
git add research-bot/frontend/index.html
git commit -m "feat(frontend): update settings button to BYOK key button in index.html"
```

---

### Task 2: Add CSS Styling for `.btn-byok`

**Files:**
- Modify: `research-bot/frontend/style.css`

- [ ] **Step 1: Add .btn-byok styles in style.css**

Add to `research-bot/frontend/style.css`:
```css
.btn-byok {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.45rem 0.85rem;
    font-size: 0.825rem;
    font-weight: 600;
    border-radius: 50px;
    background: rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.3);
    color: #a5b4fc;
    transition: all 0.2s ease;
    cursor: pointer;
}

.btn-byok:hover {
    background: rgba(99, 102, 241, 0.25);
    color: #ffffff;
    border-color: rgba(99, 102, 241, 0.5);
    box-shadow: 0 0 12px rgba(99, 102, 241, 0.2);
}
```

- [ ] **Step 2: Commit**

```bash
git add research-bot/frontend/style.css
git commit -m "style(frontend): add .btn-byok pill styling with hover glow"
```
