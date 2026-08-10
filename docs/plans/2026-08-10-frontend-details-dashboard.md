# Frontend Academic Dashboard & Paper Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the frontend UI to display live execution metrics, a terminal event log stream, corpus summary cards, an interactive PRISMA diagram viewer, a hypothesis evidence matrix, and a full-text paper excerpt inspector.

**Architecture:** Update HTML structure in `index.html`, add component styles in `styles.css`, and handle dynamic rendering, SSE event processing, and modal interactions in `app.js`.

**Tech Stack:** HTML5, CSS3 (Vanilla), JavaScript (ES6+), Lucide Icons.

---

### Task 1: Add HTML Structure & Components for Dashboard Details

**Files:**
- Modify: `research-bot/frontend/index.html:350-420`

**Interfaces:**
- Consumes: Existing Research Mode section container `#section-research-mode`
- Produces: HTML elements `#rm-corpus-stats-bar`, `#rm-log-drawer`, `#rm-prisma-card`, `#rm-evidence-table-card`, and `#paper-detail-modal`

- [ ] **Step 1: Update index.html to add Corpus Stats Bar & Live Log Drawer**

```html
<div class="rm-corpus-stats" id="rm-corpus-stats-bar" style="display: none;">
    <div class="stat-card"><span class="stat-num" id="stat-retrieved">0</span><span class="stat-lbl">Retrieved</span></div>
    <div class="stat-card"><span class="stat-num" id="stat-dedup">0</span><span class="stat-lbl">Deduplicated</span></div>
    <div class="stat-card"><span class="stat-num" id="stat-screened">0</span><span class="stat-lbl">Screened</span></div>
    <div class="stat-card"><span class="stat-num" id="stat-included">0</span><span class="stat-lbl">Included</span></div>
    <div class="stat-card"><span class="stat-num" id="stat-fulltext">0</span><span class="stat-lbl">Full-Text Fetched</span></div>
</div>
```

- [ ] **Step 2: Add Live Log Console Drawer in index.html**

```html
<details class="rm-log-console" id="rm-log-drawer">
    <summary class="rm-log-summary">
        <i data-lucide="terminal"></i> Live Execution Log & SSE Event Console
        <span class="badge" id="rm-log-count">0 events</span>
    </summary>
    <div class="rm-log-body" id="rm-log-body">
        <div class="rm-log-line info">[System] Log console initialized. Awaiting pipeline execution...</div>
    </div>
</details>
```

- [ ] **Step 3: Add PRISMA Card, Evidence Matrix, and Paper Detail Modal in index.html**

```html
<div class="modal-overlay" id="paper-detail-modal" style="display: none;">
    <div class="modal-card modal-lg">
        <div class="modal-header">
            <h3 id="modal-paper-title">Paper Details</h3>
            <button class="btn-icon" id="modal-close-btn">&times;</button>
        </div>
        <div class="modal-body" id="modal-paper-body"></div>
    </div>
</div>
```

- [ ] **Step 4: Commit HTML structural updates**

```bash
git add research-bot/frontend/index.html
git commit -m "feat(frontend): add HTML containers for stats, log drawer, and paper detail modal"
```

---

### Task 2: CSS Styling for Dashboard Components, Matrix, and Inspector

**Files:**
- Modify: `research-bot/frontend/styles.css`

**Interfaces:**
- Consumes: Class selectors defined in Task 1
- Produces: CSS rules for `.rm-corpus-stats`, `.stat-card`, `.rm-log-console`, `.rm-log-body`, `.evidence-matrix`, and `.modal-overlay`

- [ ] **Step 1: Add styling rules to styles.css for stats bar and cards**

```css
.rm-corpus-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1.25rem;
}
.stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 0.75rem;
    text-align: center;
}
.stat-num {
    display: block;
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--primary-color);
}
.stat-lbl {
    font-size: 0.75rem;
    color: var(--text-muted);
}
```

- [ ] **Step 2: Add styling rules for live terminal log console**

```css
.rm-log-console {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f8fafc;
    margin-top: 1rem;
    font-family: monospace;
    font-size: 0.82rem;
}
.rm-log-summary {
    padding: 0.6rem 1rem;
    cursor: pointer;
    user-select: none;
    font-weight: 600;
}
.rm-log-body {
    max-height: 200px;
    overflow-y: auto;
    padding: 0.75rem 1rem;
    border-top: 1px solid #334155;
}
.rm-log-line { margin-bottom: 0.25rem; }
.rm-log-line.info { color: #38bdf8; }
.rm-log-line.warn { color: #fbbf24; }
.rm-log-line.success { color: #34d399; }
```

- [ ] **Step 3: Add styling rules for hypothesis evidence matrix badges and modal**

```css
.badge-supported { background: #d1fae5; color: #065f46; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.badge-partial { background: #fef3c7; color: #92400e; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.badge-refuted { background: #fee2e2; color: #991b1b; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.badge-none { background: #f1f5f9; color: #64748b; padding: 2px 8px; border-radius: 4px; }
```

- [ ] **Step 4: Commit CSS styling updates**

```bash
git add research-bot/frontend/styles.css
git commit -m "feat(frontend): add CSS styles for stats bar, log drawer, evidence matrix, and inspector modal"
```

---

### Task 3: JavaScript Logic for Live Metrics, PRISMA Image, Evidence Table, and Paper Inspector

**Files:**
- Modify: `research-bot/frontend/app.js`

**Interfaces:**
- Consumes: DOM elements from Task 1, SSE events from `/research-mode/stream`
- Produces: Live SSE event logging, PRISMA render update, hypothesis matrix table render, paper modal open/close handling.

- [ ] **Step 1: Update DOM cache and add helper state in app.js**

```javascript
// Add DOM refs for stat elements, log drawer, prisma, evidence matrix, and paper modal
dom.statRetrieved = document.getElementById('stat-retrieved');
dom.statDedup = document.getElementById('stat-dedup');
dom.statScreened = document.getElementById('stat-screened');
dom.statIncluded = document.getElementById('stat-included');
dom.statFulltext = document.getElementById('stat-fulltext');
dom.rmCorpusStatsBar = document.getElementById('rm-corpus-stats-bar');
dom.rmLogDrawer = document.getElementById('rm-log-drawer');
dom.rmLogBody = document.getElementById('rm-log-body');
dom.rmLogCount = document.getElementById('rm-log-count');
dom.paperDetailModal = document.getElementById('paper-detail-modal');
dom.modalPaperTitle = document.getElementById('modal-paper-title');
dom.modalPaperBody = document.getElementById('modal-paper-body');
dom.modalCloseBtn = document.getElementById('modal-close-btn');
```

- [ ] **Step 2: Update SSE message handler to append to log console and update node timers**

```javascript
function appendLogLine(msg, level = 'info') {
    if (!dom.rmLogBody) return;
    const timeStr = new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.className = `rm-log-line ${level}`;
    div.textContent = `[${timeStr}] ${msg}`;
    dom.rmLogBody.appendChild(div);
    dom.rmLogBody.scrollTop = dom.rmLogBody.scrollHeight;
    
    const count = dom.rmLogBody.children.length;
    if (dom.rmLogCount) dom.rmLogCount.textContent = `${count} events`;
}
```

- [ ] **Step 3: Add functions for rendering Evidence Table and handling Paper Modal inspector**

```javascript
function openPaperInspector(paper) {
    if (!paper) return;
    dom.modalPaperTitle.textContent = paper.title || 'Paper Details';
    dom.modalPaperBody.innerHTML = `
        <p><strong>Authors:</strong> ${(paper.authors || []).join(', ') || 'N/A'}</p>
        <p><strong>Journal/Year:</strong> ${paper.venue || 'N/A'} (${paper.year || 'N/A'})</p>
        <p><strong>DOI:</strong> ${paper.doi ? `<a href="https://doi.org/${paper.doi}" target="_blank">${paper.doi}</a>` : 'N/A'}</p>
        <p><strong>Relevance Score:</strong> ${paper.relevance_score || 'N/A'}/10</p>
        <p><strong>Inclusion Rationale:</strong> ${paper.inclusion_reason || 'N/A'}</p>
        <hr/>
        <h4>Full-Text Excerpt:</h4>
        <pre style="white-space: pre-wrap; font-size: 0.85rem; background: #f8fafc; padding: 0.5rem;">${paper.fulltext_excerpt || 'No full-text PDF extracted for this paper.'}</pre>
    `;
    dom.paperDetailModal.style.display = 'flex';
}
```

- [ ] **Step 4: Connect modal close button listener**

```javascript
if (dom.modalCloseBtn) {
    dom.modalCloseBtn.onclick = () => {
        if (dom.paperDetailModal) dom.paperDetailModal.style.display = 'none';
    };
}
```

- [ ] **Step 5: Test frontend rendering and commit app.js changes**

```bash
git add research-bot/frontend/app.js
git commit -m "feat(frontend): implement JS event logging, metrics update, evidence table, and paper inspector modal"
```
