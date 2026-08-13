# Research Mode Reading Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Research Mode's checkpoint panels and final paper a real reading experience — show the actual papers behind the synthesis, stop dumping walls of untruncated text, and style the paper output that currently has zero CSS.

**Architecture:** Pure frontend work (`research-bot/frontend/app.js`, `style.css`, `index.html`) except one backend touch to confirm field names (no backend code changes needed — the data already exists in SSE payloads, see Global Constraints). No test framework exists in this codebase; verification is `node --check` for syntax and live browser checks against the real backend using the `mcp__Claude_Browser__*` tools, the same approach used successfully throughout this session's bug-fixing work.

**Tech Stack:** Vanilla JS (no framework, no bundler), plain CSS with custom properties, `marked.js` (CDN) for markdown, FastAPI + LangGraph backend (unchanged), served via `python -m uvicorn backend.app.main:app` from `research-bot/` with the venv at repo root (`../.venv/Scripts/python.exe` from `research-bot/`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-13-research-mode-reading-experience-design.md`
- Scope is Research Mode workspace only (`#rm-input-panel`, `#rm-workspace-panel`) — do not touch DeepSearch mode (`#landing-panel`, `#approval-panel`, `#workspace-panel`) or any landing/hero markup.
- `state.rm.screenedPapers` must NEVER be written into `saveRMSession()`'s localStorage payload — this field is intentionally excluded (see `research-bot/frontend/app.js:712` `saveRMSession()`, which already has a comment explaining a prior localStorage-bloat bug from persisting raw/screened paper arrays).
- Backend node output keys (confirmed in `research-bot/backend/app/agents/research_mode/agents.py`): `paper_fetcher_agent` (line 225) returns `raw_papers`; `paper_screener_agent` (line 240) returns `screened_papers`; `fulltext_fetcher_agent` (line 259) returns `screened_papers` again (with `content_excerpt` added). No backend changes needed — these are already present in the SSE `node_update` event's `data.data`.
- Paper `source` field values (confirmed in `research-bot/backend/app/tools/academic_search.py`): `"openalex"`, `"semantic_scholar"`, `"arxiv"`, `"tavily_web_fallback"`.
- Source badge assets already exist at `research-bot/frontend/assets/openalex.png`, `assets/semantic-scholar.png`, `assets/arxiv.png`.
- After every `app.js`/`style.css`/`index.html` change, bump the cache-busting query strings in `research-bot/frontend/index.html` (`app.js?v=X.X.X`, `style.css?v=X.X.X`) — this session discovered the Browser tool's tab cache ignores plain reloads and serves stale JS/CSS unless the query string changes.
- CSS variables in use (from `:root` in `style.css`): `--text-primary`, `--text-secondary`, `--text-muted`, `--card-border`, `--accent-purple`, `--academic-blue`, `--accent-teal`, `--bg-card`. Light-mode overrides live under `:root.light-mode`.
- `dom.rmHitlBody` = `document.getElementById('rm-hitl-body')` (`app.js:406`). `.rm-workspace-body` (`index.html:377`) wraps the evidence card, HITL panel, and paper card in `#rm-workspace-panel`.

---

### Task 1: Capture paper data from SSE without persisting it

**Files:**
- Modify: `research-bot/frontend/app.js:31-75` (`state` object, inside `state.rm`)
- Modify: `research-bot/frontend/app.js:153-174` (`applyRMStatePayload`)
- Modify: `research-bot/frontend/app.js:712-720` (`saveRMSession`)
- Modify: `research-bot/frontend/app.js:735-798` (`restoreRMSessionOnLoad`, the background-sync block that calls `/research-mode/result/{thread_id}`)

**Interfaces:**
- Produces: `state.rm.screenedPapers` — `Array<{title, abstract, authors, year, doi, url, pdf_url, source, citation_count, relevance_score, content_excerpt, hypothesis_support}>`, default `[]`. This is the array every later task reads from.
- Produces: `getScreenedPapers()` — returns `state.rm.screenedPapers`, sorted by `relevance_score` descending (falls back to `0` if missing). Later tasks call this instead of touching `state.rm.screenedPapers` directly, so the sort logic lives in one place.

- [ ] **Step 1: Add the field to initial state**

In `state.rm` (around `app.js:73`, right after `activeStage: 'scope_definition',` and `completedStages: []`), add:

```js
        completedStages: [],
        screenedPapers: []
```

- [ ] **Step 2: Capture papers in `applyRMStatePayload`**

Find the function at `app.js:153`. After the existing `RM_PASSTHROUGH_KEYS.forEach(...)` block and before the `raw_papers_count`/`screened_papers_count` derivation lines, add:

```js
    // paper_fetcher sends raw_papers before screening; paper_screener and
    // fulltext_fetcher both send screened_papers (the latter adds
    // content_excerpt). Whichever arrives most recently wins — screened_papers
    // is always the more complete list once it exists.
    if (Array.isArray(payload.screened_papers)) {
        state.rm.screenedPapers = payload.screened_papers;
    } else if (Array.isArray(payload.raw_papers) && state.rm.screenedPapers.length === 0) {
        state.rm.screenedPapers = payload.raw_papers;
    }
```

Place this ABOVE the existing two lines:
```js
    if (Array.isArray(payload.raw_papers)) state.rm.rawPapersCount = payload.raw_papers.length;
    if (Array.isArray(payload.screened_papers)) state.rm.screenedPapersCount = payload.screened_papers.length;
```
(those two lines stay unchanged — they already exist and are correct, just keep counts in sync separately from the array capture above).

- [ ] **Step 3: Add the sorted-accessor helper**

Immediately after the `applyRMStatePayload` function closes (after its final `}`), add:

```js
// Papers arrive from the backend already relevance-ranked in practice, but
// don't rely on that — sort explicitly so the checkpoint strip and library
// panel always show the strongest matches first regardless of arrival order.
function getScreenedPapers() {
    return [...state.rm.screenedPapers].sort(
        (a, b) => (b.relevance_score || 0) - (a.relevance_score || 0)
    );
}
```

- [ ] **Step 4: Confirm `saveRMSession` still excludes it**

Read `app.js:712-720`. It builds `sessionData` from `state.rm.threadId`, `state.rm` (as `rmState`), `lastSeq`. Since `state.rm` is passed wholesale, `screenedPapers` WOULD be persisted as-is today. Change the function to shallow-copy `state.rm` and strip the field before saving:

```js
function saveRMSession() {
    if (!state.rm.threadId) return;
    try {
        const { screenedPapers, ...persistableRmState } = state.rm;
        const sessionData = {
            threadId: state.rm.threadId,
            rmState: persistableRmState,
            lastSeq: state.rm.lastSeq || 0,
            timestamp: Date.now()
        };
        localStorage.setItem('rm_session', JSON.stringify(sessionData));
    } catch (e) {
        console.warn('Failed to save RM session:', e);
    }
}
```

- [ ] **Step 5: Wire the background-sync restore path**

In `restoreRMSessionOnLoad` (`app.js:735`), find the background-sync block that does `applyRMStatePayload(data.values || {})` (inside the `try { const res = await fetch(...result/...)` block, around line 762-793 in the current file). `data.values` from `/research-mode/result/{thread_id}` already contains `screened_papers`/`raw_papers` in full (confirmed live this session via direct curl during testing) and `applyRMStatePayload` now captures them per Step 2 — no additional code needed here beyond what Step 2 already wired. Just verify: search for any place in this block that reads `data.values` and copies fields manually instead of calling `applyRMStatePayload` — there should be none (the file already calls `applyRMStatePayload(data.values || {})` once). If found, leave as-is; this step is a verification-only step, not a code change.

- [ ] **Step 6: Verify — syntax check**

```bash
cd research-bot/frontend && node --check app.js
```
Expected: no output (success).

- [ ] **Step 7: Verify — live capture via browser**

Start the backend (from `research-bot/`):
```bash
cd research-bot && ../.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Bump `app.js?v=2.4.0` in `index.html`, navigate the Browser tool to `http://127.0.0.1:8000/index.html?nocache=<random>`, start a Research Mode run, approve checkpoint 1, and once checkpoint 2 is reached, run via `javascript_tool`:
```js
JSON.stringify({ count: state.rm.screenedPapers.length, sample: state.rm.screenedPapers[0]?.title })
```
Expected: `count` > 0 and `sample` is a real paper title (not undefined).

Then reload the page (`navigate` with the same `?nocache=` URL again) and re-run the same check — `state.rm.screenedPapers.length` should still be > 0 (proves the background-sync restore path also populates it), while `localStorage.getItem('rm_session')` should NOT contain the string `"screenedPapers"` when inspected via `JSON.parse(localStorage.getItem('rm_session')).rmState.hasOwnProperty('screenedPapers')` → expect `false`.

- [ ] **Step 8: Commit**

```bash
git add research-bot/frontend/app.js research-bot/frontend/index.html
git commit -m "feat(rm): capture screened papers from SSE without persisting to localStorage"
```

---

### Task 2: Reusable helpers — source badge and truncate-with-expand

**Files:**
- Modify: `research-bot/frontend/app.js` (add two new functions near `escapeHtml`/`renderMarkdownSafe`, i.e. right after the `renderMarkdownSafe` function currently at `app.js:200`)
- Modify: `research-bot/frontend/style.css` (new rules, append near the existing `.index-mark` rules at `style.css:2487`)

**Interfaces:**
- Consumes: nothing external (pure functions operating on strings/objects passed in).
- Produces: `sourceBadgeHtml(source)` — returns an `<img>` HTML string for a given `source` string (`"openalex"` / `"semantic_scholar"` / `"arxiv"` / anything else). Used by Task 3 and Task 5.
- Produces: `renderTruncatable(text, opts)` — returns HTML string: a `<div class="truncatable">` wrapping the rendered markdown, capped visually via CSS `max-height` + a toggle `<button class="truncate-toggle" data-truncate-target="...">Show full text</button>` when `text` exceeds `opts.charLimit` (default 400). Used by Task 3.
- Produces: a single delegated click listener (added in `setupEventListeners()`) that toggles the `.expanded` class on `.truncatable` elements when their sibling `.truncate-toggle` button is clicked. Later tasks that call `renderTruncatable` don't need to add their own listeners.

- [ ] **Step 1: Add `sourceBadgeHtml`**

After the `renderMarkdownSafe` function (ends around `app.js:210`), add:

```js
const SOURCE_BADGE_MAP = {
    openalex: { src: 'assets/openalex.png', label: 'OpenAlex', cls: 'index-mark-openalex' },
    semantic_scholar: { src: 'assets/semantic-scholar.png', label: 'Semantic Scholar', cls: '' },
    arxiv: { src: 'assets/arxiv.png', label: 'arXiv', cls: '' }
};

// Reuses the same brand marks the landing page already downloaded (see
// assets/*.png) so a paper's origin index is visually recognizable instead
// of a plain text label like "openalex".
function sourceBadgeHtml(source) {
    const entry = SOURCE_BADGE_MAP[source];
    if (!entry) return '';
    return `<img class="source-badge ${entry.cls}" src="${entry.src}" alt="${entry.label}" title="${entry.label}" width="14" height="14" loading="lazy">`;
}
```

- [ ] **Step 2: Add `renderTruncatable`**

Immediately after `sourceBadgeHtml`, add:

```js
let truncatableIdCounter = 0;

// Checkpoint 2 was showing researchGap/conceptualFramework in full — observed
// at ~2500 words on screen in one live test run. literatureReview already had
// a hard 400-char cut with no way to read past it. This gives every long
// snippet the same collapsed-by-default treatment with an actual way out.
function renderTruncatable(text, opts = {}) {
    const charLimit = opts.charLimit || 400;
    const safeText = text || '';
    const id = `trunc-${++truncatableIdCounter}`;
    const rendered = renderMarkdownSafe(safeText);

    if (safeText.length <= charLimit) {
        return `<div class="problem-statement-text">${rendered}</div>`;
    }

    return `
        <div class="problem-statement-text truncatable" id="${id}">${rendered}</div>
        <button type="button" class="truncate-toggle" data-truncate-target="${id}">Show full text</button>
    `;
}
```

- [ ] **Step 3: Wire the delegated toggle listener**

In `setupEventListeners()`, find the existing delegated-click pattern for filter chips:
```js
dom.filterChips?.addEventListener('click', (e) => {
    if (e.target.classList.contains('chip')) {
```
Right after that whole block (before `dom.planResearchBtn?.addEventListener(...)`), add:

```js
    // Delegated so it works for truncatable blocks rendered at any point
    // after this listener is attached (checkpoint panels, library panel).
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.truncate-toggle');
        if (!btn) return;
        const target = document.getElementById(btn.dataset.truncateTarget);
        if (!target) return;
        const expanded = target.classList.toggle('expanded');
        btn.textContent = expanded ? 'Show less' : 'Show full text';
    });
```

- [ ] **Step 4: CSS for badges and truncation**

Append to `style.css`, near the existing `.index-mark` block (`style.css:2487`):

```css
/* Source badges — reused brand marks for individual paper rows (checkpoint
   2 evidence strip, sources library panel). Smaller than the landing page's
   .index-mark since these sit inline next to a paper title. */
.source-badge {
    width: 14px;
    height: 14px;
    object-fit: contain;
    flex-shrink: 0;
    vertical-align: middle;
}

/* Collapsed-by-default long-text blocks in checkpoint panels. */
.truncatable {
    max-height: 8.5em;
    overflow: hidden;
    position: relative;
    mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
    -webkit-mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
}
.truncatable.expanded {
    max-height: none;
    mask-image: none;
    -webkit-mask-image: none;
}
.truncate-toggle {
    display: block;
    margin: 0.4rem 0 1rem 0;
    padding: 0;
    background: none;
    border: none;
    color: var(--accent-purple);
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
}
.truncate-toggle:hover {
    text-decoration: underline;
}
```

- [ ] **Step 5: Verify — syntax + brace balance**

```bash
cd research-bot/frontend && node --check app.js
python -c "s=open('style.css',encoding='utf-8').read(); print(s.count('{')==s.count('}'))"
```
Expected: `node --check` silent success, Python prints `True`.

- [ ] **Step 6: Commit**

```bash
git add research-bot/frontend/app.js research-bot/frontend/style.css
git commit -m "feat(rm): add source badge and truncate-with-expand helpers"
```

---

### Task 3: Checkpoint 2 evidence strip + apply truncation to gap/framework

**Files:**
- Modify: `research-bot/frontend/app.js:1125-1142` (the `checkpoint_2` branch inside `renderRMHitlPanel`)

**Interfaces:**
- Consumes: `getScreenedPapers()` (Task 1), `sourceBadgeHtml()` and `renderTruncatable()` (Task 2), `openPaperInspector(paper)` (existing function at `app.js:1377`, unmodified signature — takes a single paper object).
- Produces: nothing new consumed by later tasks — this is a leaf UI change.

- [ ] **Step 1: Replace the checkpoint_2 branch**

Replace the block currently at `app.js:1125-1142`:

```js
    } else if (checkpoint === 'checkpoint_2') {
        dom.rmHitlTitle.textContent = 'Checkpoint 2: Literature Review & Framework Review';
        dom.rmHitlBadge.textContent = 'Checkpoint 2 of 4';

        dom.rmHitlBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">Synthesized Literature Review Snippet</label>
                <div class="problem-statement-text">${renderMarkdownSafe((state.rm.literatureReview || '').slice(0, 400))}...</div>
            </div>
            <div class="form-group">
                <label class="form-label">Identified Research Gap</label>
                <div class="problem-statement-text">${renderMarkdownSafe(state.rm.researchGap)}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Proposed Conceptual Framework</label>
                <div class="problem-statement-text">${renderMarkdownSafe(state.rm.conceptualFramework)}</div>
            </div>
        `;
```

with:

```js
    } else if (checkpoint === 'checkpoint_2') {
        dom.rmHitlTitle.textContent = 'Checkpoint 2: Literature Review & Framework Review';
        dom.rmHitlBadge.textContent = 'Checkpoint 2 of 4';

        const topPapers = getScreenedPapers().slice(0, 10);
        const evidenceRows = topPapers.map((p, i) => `
            <div class="evidence-row" data-paper-index="${i}">
                ${sourceBadgeHtml(p.source)}
                <span class="evidence-title">${escapeHtml(p.title || 'Untitled')}</span>
                <span class="evidence-year">${escapeHtml(String(p.year || ''))}</span>
                <span class="evidence-score">${p.relevance_score != null ? p.relevance_score + '/10' : ''}</span>
            </div>
        `).join('');

        dom.rmHitlBody.innerHTML = `
            ${topPapers.length ? `
            <div class="form-group">
                <label class="form-label">Evidence Used <span class="label-tag">${state.rm.screenedPapers.length} papers screened</span></label>
                <div class="evidence-list">${evidenceRows}</div>
            </div>
            ` : ''}
            <div class="form-group">
                <label class="form-label">Synthesized Literature Review Snippet</label>
                ${renderTruncatable(state.rm.literatureReview)}
            </div>
            <div class="form-group">
                <label class="form-label">Identified Research Gap</label>
                ${renderTruncatable(state.rm.researchGap)}
            </div>
            <div class="form-group">
                <label class="form-label">Proposed Conceptual Framework</label>
                ${renderTruncatable(state.rm.conceptualFramework)}
            </div>
        `;

        dom.rmHitlBody.querySelectorAll('.evidence-row').forEach((row) => {
            row.addEventListener('click', () => {
                const idx = parseInt(row.dataset.paperIndex, 10);
                openPaperInspector(topPapers[idx]);
            });
        });
```

Note: this changes `literatureReview` from a hard `.slice(0, 400) + '...'` (which cut mid-word/mid-sentence with no way to read on) to `renderTruncatable`'s CSS-based collapse (which shows the same rough amount visually but lets the user expand to the full text) — consistent with the fix now also applied to `researchGap`/`conceptualFramework`.

- [ ] **Step 2: CSS for the evidence list**

Append to `style.css`:

```css
/* Checkpoint 2 evidence strip */
.evidence-list {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    max-height: 220px;
    overflow-y: auto;
    margin-top: 0.5rem;
}
.evidence-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.6rem;
    border-radius: 6px;
    border: 1px solid var(--card-border);
    background: rgba(255, 255, 255, 0.02);
    cursor: pointer;
    transition: var(--transition-fast);
}
.evidence-row:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.12);
}
.evidence-title {
    flex: 1;
    font-size: 0.82rem;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.evidence-year {
    font-size: 0.75rem;
    color: var(--text-muted);
    flex-shrink: 0;
}
.evidence-score {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--academic-blue);
    flex-shrink: 0;
    min-width: 32px;
    text-align: right;
}
```

- [ ] **Step 3: Verify — syntax + brace balance**

```bash
cd research-bot/frontend && node --check app.js
python -c "s=open('style.css',encoding='utf-8').read(); print(s.count('{')==s.count('}'))"
```

- [ ] **Step 4: Verify — live**

Bump `app.js?v=2.4.1`, run a Research Mode session to checkpoint 2 (or reuse a thread already paused there), and check via `javascript_tool`:
```js
JSON.stringify({
  rows: document.querySelectorAll('.evidence-row').length,
  toggle: !!document.querySelector('.truncate-toggle'),
})
```
Expected: `rows` > 0, `toggle` is `true` (given `researchGap`/`conceptualFramework` are realistically always over 400 chars). Click a `.truncate-toggle` via `computer` click and confirm the corresponding `.truncatable` element gains `expanded` in its class list. Click an `.evidence-row` and confirm `#paper-detail-modal`'s `style.display` becomes `flex` with the correct paper's title in `#modal-paper-title`.

- [ ] **Step 5: Commit**

```bash
git add research-bot/frontend/app.js research-bot/frontend/style.css research-bot/frontend/index.html
git commit -m "feat(rm): add evidence strip and truncation to checkpoint 2 panel"
```

---

### Task 4: Dedicated sources/library panel

**Files:**
- Modify: `research-bot/frontend/index.html:377-460` (inside `.rm-workspace-body`, add a new section)
- Modify: `research-bot/frontend/app.js` (new render function + DOM cache entries + call sites)
- Modify: `research-bot/frontend/style.css` (new rules)

**Interfaces:**
- Consumes: `getScreenedPapers()` (Task 1), `sourceBadgeHtml()` (Task 2), `openPaperInspector(paper)` (existing, unmodified).
- Produces: `renderRMSourcesPanel()` — rebuilds the panel's contents from `state.rm.screenedPapers`. Called from `processRMSEEvent`'s `node_update` branch (already exists in the file) and from `restoreRMSessionOnLoad`'s post-sync block, so both live updates and page-reload restores populate it.

- [ ] **Step 1: Add the markup**

In `index.html`, inside `.rm-workspace-body` (`index.html:377`), insert a new section BEFORE the existing `<!-- HITL Review Panel -->` comment (i.e. before the `rm-hitl-panel` div, so it's visible above the checkpoint gate — it should be visible throughout the run, not just at checkpoints):

```html
                <!-- Sources Library: all screened papers, browsable throughout the run -->
                <details class="rm-sources-panel card" id="rm-sources-panel" style="display: none; margin-bottom: 1.5rem;">
                    <summary class="tracker-header">
                        <div class="tracker-title-group">
                            <i data-lucide="library" style="width: 18px; height: 18px; color: var(--academic-blue);"></i>
                            <h2 class="tracker-title">Sources</h2>
                            <span class="tracker-status-tag" id="rm-sources-count-tag">0 papers</span>
                        </div>
                        <div class="tracker-header-controls">
                            <span class="tracker-toggle-lbl" id="rm-sources-toggle-lbl">Expand</span>
                            <i data-lucide="chevron-down" class="tracker-chevron-icon" style="width: 15px; height: 15px;"></i>
                        </div>
                    </summary>
                    <div class="rm-sources-grid" id="rm-sources-grid"></div>
                </details>

```

This reuses the same `<details>` + `.card`/`.tracker-header` visual pattern as the existing pipeline tracker (`#rm-tracker-details`), so it matches the established look without inventing a new component style.

- [ ] **Step 2: Cache the new DOM elements**

In `cacheDomElements()` (`app.js:342`), near the other `rm*` entries (e.g. right after `rmEvidenceCard: document.getElementById('rm-evidence-card'),` at line 425), add:

```js
        rmSourcesPanel: document.getElementById('rm-sources-panel'),
        rmSourcesGrid: document.getElementById('rm-sources-grid'),
        rmSourcesCountTag: document.getElementById('rm-sources-count-tag'),
```

- [ ] **Step 3: Add the render function**

Add this function right after `renderRMPipelineTracker` (which starts at `app.js` — search for `function renderRMPipelineTracker`), or anywhere at top level after `getScreenedPapers` is defined:

```js
function renderRMSourcesPanel() {
    if (!dom.rmSourcesPanel) return;
    const papers = getScreenedPapers();

    if (papers.length === 0) {
        dom.rmSourcesPanel.style.display = 'none';
        return;
    }

    dom.rmSourcesPanel.style.display = 'block';
    if (dom.rmSourcesCountTag) {
        dom.rmSourcesCountTag.textContent = `${papers.length} papers`;
    }

    dom.rmSourcesGrid.innerHTML = papers.map((p, i) => `
        <div class="source-card-item" data-paper-index="${i}">
            <div class="source-card-header">
                ${sourceBadgeHtml(p.source)}
                <span class="source-card-score">${p.relevance_score != null ? p.relevance_score + '/10' : ''}</span>
            </div>
            <div class="source-card-title">${escapeHtml(p.title || 'Untitled')}</div>
            <div class="source-card-meta">${escapeHtml(String(p.year || ''))}${p.authors && p.authors.length ? ' · ' + escapeHtml(Array.isArray(p.authors) ? p.authors[0] : String(p.authors)) : ''}</div>
        </div>
    `).join('');

    dom.rmSourcesGrid.querySelectorAll('.source-card-item').forEach((card) => {
        card.addEventListener('click', () => {
            const idx = parseInt(card.dataset.paperIndex, 10);
            openPaperInspector(papers[idx]);
        });
    });

    refreshIcons();
}
```

- [ ] **Step 4: Call it from the live-update path**

Find `processRMSEEvent`'s `node_update` branch (search for `} else if (data.event === 'node_update') {`). It already calls `applyRMStatePayload(data.data || {})`, `appendLogLine(...)`, `updateCorpusStats(...)`, `renderRMPaperLive()`, `saveRMSession()`. Add `renderRMSourcesPanel();` right after `applyRMStatePayload(data.data || {});` in that branch (so the panel updates as soon as new papers arrive, regardless of which node sent them).

- [ ] **Step 5: Call it from the restore-on-load path**

In `restoreRMSessionOnLoad` (`app.js:735`), after the background-sync `applyRMStatePayload(data.values || {})` call (inside the `try` block reading from `/research-mode/result/...`), add `renderRMSourcesPanel();` on its own line right after it, so a page reload repopulates the panel too.

- [ ] **Step 6: CSS**

Append to `style.css`:

```css
/* Sources library panel */
.rm-sources-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.75rem;
    padding: 1rem 1.5rem 1.5rem;
}
.source-card-item {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 0.75rem;
    cursor: pointer;
    transition: var(--transition-fast);
}
.source-card-item:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.15);
    transform: translateY(-1px);
}
.source-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}
.source-card-score {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--academic-blue);
}
.source-card-title {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-primary);
    line-height: 1.4;
    margin-bottom: 0.35rem;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.source-card-meta {
    font-size: 0.72rem;
    color: var(--text-muted);
}
```

- [ ] **Step 7: Verify — syntax + brace balance**

```bash
cd research-bot/frontend && node --check app.js
python -c "s=open('style.css',encoding='utf-8').read(); print(s.count('{')==s.count('}'))"
```

- [ ] **Step 8: Verify — live**

Bump `app.js?v=2.4.2`, run to checkpoint 2 or later, check via `javascript_tool`:
```js
JSON.stringify({
  panelVisible: getComputedStyle(document.getElementById('rm-sources-panel')).display,
  cardCount: document.querySelectorAll('.source-card-item').length,
  countTag: document.getElementById('rm-sources-count-tag').textContent
})
```
Expected: `panelVisible` not `"none"`, `cardCount` > 0, `countTag` matches. Click a card, confirm the modal opens with matching data. Reload the page and re-check `cardCount` — should still be > 0.

- [ ] **Step 9: Commit**

```bash
git add research-bot/frontend/app.js research-bot/frontend/style.css research-bot/frontend/index.html
git commit -m "feat(rm): add dedicated sources library panel"
```

---

### Task 5: Best-effort inline citation linking in the paper view

**Files:**
- Modify: `research-bot/frontend/app.js:1473-1497` (`renderRMPaperLive`, `renderRMPaperFinal`)

**Interfaces:**
- Consumes: `getScreenedPapers()` (Task 1), `openPaperInspector(paper)` (existing).
- Produces: `linkCitations(html)` — takes already-rendered paper HTML (post-`renderMarkdown`), returns HTML with matched citations wrapped in clickable spans. Not consumed elsewhere — this is the final task in the citation feature.

- [ ] **Step 1: Add the citation-linking function**

Add this function right before `renderRMPaperLive` (`app.js:1473`):

```js
// Best-effort only: matches "(Lastname, YYYY)" and "(Lastname et al., YYYY)"
// against screened papers' first-author last name + year. Model-generated
// citation text won't always map cleanly to a specific screened paper
// (paraphrased names, multi-author collisions, references outside the
// screened set) — unmatched citations are left as plain text, unchanged
// from today's behavior.
function linkCitations(html) {
    const papers = getScreenedPapers();
    if (papers.length === 0) return html;

    const byLastNameYear = new Map();
    papers.forEach((p, idx) => {
        const firstAuthor = Array.isArray(p.authors) ? p.authors[0] : p.authors;
        if (!firstAuthor || !p.year) return;
        const lastName = String(firstAuthor).trim().split(/\s+/).pop();
        if (!lastName) return;
        const key = `${lastName.toLowerCase()}|${p.year}`;
        if (!byLastNameYear.has(key)) byLastNameYear.set(key, idx);
    });

    if (byLastNameYear.size === 0) return html;

    return html.replace(
        /\(([A-Z][a-zA-Z'-]+)(?:\s+et al\.)?,\s*(\d{4})\)/g,
        (match, lastName, year) => {
            const key = `${lastName.toLowerCase()}|${year}`;
            const paperIdx = byLastNameYear.get(key);
            if (paperIdx === undefined) return match;
            return `<a href="#" class="citation-link" data-paper-index="${paperIdx}">${match}</a>`;
        }
    );
}
```

- [ ] **Step 2: Apply it in `renderRMPaperLive`**

Find `renderRMPaperLive` (`app.js:1473-1490`). It currently does:
```js
        let content = renderMarkdown(getPaperMarkdown());
        if (isStreaming) {
            content += '<span class="typing-cursor"></span>';
        }
        scroller.innerHTML = content;
```
Change to:
```js
        let content = linkCitations(renderMarkdown(getPaperMarkdown()));
        if (isStreaming) {
            content += '<span class="typing-cursor"></span>';
        }
        scroller.innerHTML = content;
```

- [ ] **Step 3: Wire click handling for citation links**

`renderRMPaperLive` rebuilds `scroller.innerHTML` on every call, so per-element listeners would need re-attaching constantly. Use delegation instead — add this inside `renderRMPaperLive`, right after `scroller.innerHTML = content;` and before the scroll-position restore line:

```js
        scroller.querySelectorAll('.citation-link').forEach((link) => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const idx = parseInt(link.dataset.paperIndex, 10);
                const papers = getScreenedPapers();
                if (papers[idx]) openPaperInspector(papers[idx]);
            });
        });
```

- [ ] **Step 4: CSS for citation links**

Append to `style.css`:

```css
.citation-link {
    color: var(--academic-blue);
    text-decoration: none;
    border-bottom: 1px dotted var(--academic-blue);
}
.citation-link:hover {
    border-bottom-style: solid;
}
```

- [ ] **Step 5: Verify — syntax + brace balance**

```bash
cd research-bot/frontend && node --check app.js
python -c "s=open('style.css',encoding='utf-8').read(); print(s.count('{')==s.count('}'))"
```

- [ ] **Step 6: Verify — live**

Bump `app.js?v=2.4.3`. Against a completed paper (or one far enough along to have citations in `literatureReview`), check:
```js
JSON.stringify({ linkCount: document.querySelectorAll('.citation-link').length })
```
This may legitimately be `0` if the model's citation format doesn't match any screened paper's author/year — that's expected best-effort behavior per the spec, not a failure. If the test thread from this session's earlier run is still available (`6d6991dc-c74f-43b2-93c1-787024bdfe0e`), its literature review is known to contain citations like "(Page et al., 2021; Moher et al., 2009)" — reload that thread and check for at least a non-zero count, or manually confirm via console that `linkCitations` runs without throwing on real data.

- [ ] **Step 7: Commit**

```bash
git add research-bot/frontend/app.js research-bot/frontend/style.css
git commit -m "feat(rm): best-effort inline citation linking in paper view"
```

---

### Task 6: Paper typography

**Files:**
- Modify: `research-bot/frontend/style.css` (new rules — `.paper-render-container` currently has zero rules anywhere in the file, confirmed by grep during design)
- Modify: `research-bot/frontend/style.css` (checkpoint body text color — `.problem-statement-text` at `style.css:547`)

**Interfaces:**
- Consumes: nothing (pure CSS addition).
- Produces: nothing consumed by other tasks — this is the final leaf task.

- [ ] **Step 1: Add full typography for the paper render container**

Append to `style.css`:

```css
/* Paper typography. .paper-render-container had zero rules before this —
   marked.parse() output rendered with bare browser UA defaults: no heading
   hierarchy, no paragraph rhythm, emphasis invisible against body weight. */
.paper-render-container {
    color: var(--text-primary);
    font-size: 0.98rem;
    line-height: 1.75;
    max-width: 780px;
    margin: 0 auto;
}
.paper-render-container h1 {
    font-family: var(--font-outfit);
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.3;
    margin: 0 0 1.25rem 0;
    color: var(--text-primary);
}
.paper-render-container h2 {
    font-family: var(--font-outfit);
    font-size: 1.3rem;
    font-weight: 600;
    line-height: 1.35;
    margin: 2rem 0 0.85rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--card-border);
    color: var(--text-primary);
}
.paper-render-container h2:first-child {
    margin-top: 0;
}
.paper-render-container h3 {
    font-family: var(--font-outfit);
    font-size: 1.08rem;
    font-weight: 600;
    line-height: 1.4;
    margin: 1.5rem 0 0.6rem 0;
    color: var(--text-primary);
}
.paper-render-container p {
    margin: 0 0 1rem 0;
}
.paper-render-container p:last-child {
    margin-bottom: 0;
}
.paper-render-container strong {
    font-weight: 700;
    color: var(--text-primary);
}
.paper-render-container em {
    font-style: italic;
}
.paper-render-container ul,
.paper-render-container ol {
    margin: 0 0 1rem 0;
    padding-left: 1.5rem;
}
.paper-render-container li {
    margin-bottom: 0.4rem;
    line-height: 1.65;
}
.paper-render-container li:last-child {
    margin-bottom: 0;
}
.paper-render-container a {
    color: var(--academic-blue);
}
.paper-render-container hr {
    border: none;
    border-top: 1px solid var(--card-border);
    margin: 1.75rem 0;
}
```

- [ ] **Step 2: Lighten checkpoint body text**

Find `.problem-statement-text` at `style.css:547-551`:
```css
.problem-statement-text {
    font-size: 1rem;
    line-height: 1.6;
    color: var(--text-secondary);
}
```
Change `color: var(--text-secondary);` to `color: var(--text-primary);` — matches the user's explicit request ("not grey paragraphs, white text, maybe a lighter shade ok"). `--text-primary` is the same token used for the headings fixed earlier this session inside these exact containers, so headings and body text will now read consistently instead of the heading standing out sharply against dim body copy.

- [ ] **Step 3: Verify — brace balance**

```bash
cd research-bot/frontend && python -c "s=open('style.css',encoding='utf-8').read(); print(s.count('{')==s.count('}'))"
```

- [ ] **Step 4: Verify — live**

Bump `app.js?v=2.4.4` and `style.css?v=2.4.4` (this task changes CSS only, but bump both query strings for consistency with the rest of the plan's verification steps). Load a completed paper and check:
```js
(() => {
  const h2 = document.querySelector('#rm-paper-output h2');
  const p = document.querySelector('#rm-paper-output p');
  return JSON.stringify({
    h2Size: h2 ? getComputedStyle(h2).fontSize : null,
    h2Weight: h2 ? getComputedStyle(h2).fontWeight : null,
    pColor: p ? getComputedStyle(p).color : null,
    checkpointBodyColor: (() => {
      const el = document.querySelector('.problem-statement-text');
      return el ? getComputedStyle(el).color : null;
    })()
  });
})()
```
Expected: `h2Size` noticeably larger than the ~15.6px (0.98rem) body text (should read `~20.8px` for 1.3rem), `h2Weight` `"600"`, and `checkpointBodyColor` should now match `--text-primary`'s computed RGB (previously confirmed as `rgb(244, 244, 245)` during this session's live testing) rather than the dimmer `rgb(161, 161, 170)`.

- [ ] **Step 5: Commit**

```bash
git add research-bot/frontend/style.css research-bot/frontend/index.html
git commit -m "feat(rm): style paper render container and lighten checkpoint body text"
```

---

### Task 7: Full end-to-end verification

**Files:** none (verification-only task, no code changes)

**Interfaces:**
- Consumes: everything from Tasks 1-6.
- Produces: nothing — this is the plan's final gate.

- [ ] **Step 1: Start a completely fresh Research Mode run**

Follow the same live-run pattern used successfully earlier this session: start the backend, navigate the Browser tool to `index.html?nocache=<new random value>`, fill the Core Problem Statement field, click Launch, and step through all four checkpoints to completion.

- [ ] **Step 2: Confirm at checkpoint 2**

- `.evidence-row` elements are present and each opens the modal with correct data on click.
- `.truncate-toggle` buttons exist for research gap and conceptual framework (and literature review, now consistently truncated); clicking one expands its sibling `.truncatable` block.

- [ ] **Step 3: Confirm the sources panel throughout the run**

- `#rm-sources-panel` becomes visible once papers exist (around/after checkpoint 1 → paper_fetcher) and its card count matches `state.rm.screenedPapers.length` at every subsequent checkpoint.
- Reload the page mid-run (after checkpoint 2, before completion) and confirm the panel repopulates without needing to re-approve anything.

- [ ] **Step 4: Confirm the completed paper**

- Headings (`h1`/`h2`/`h3`) are visually distinct from body paragraphs (larger, bolder, `h2` has the bottom border).
- Any citation matching a screened paper's author/year is a clickable `.citation-link` that opens the correct paper in the modal.
- Export to PDF still works (`POST /research-mode/export/{thread_id}`) — this task didn't touch the backend, but confirm no regression: fetch the endpoint and check `res.ok` and `content-type: application/pdf`, same check used earlier this session.

- [ ] **Step 5: Regression check on DeepSearch mode**

Switch to DeepSearch mode (`#tab-deepsearch`) and confirm the landing page, query input, and mode-toggle pill still render and function normally — this plan's scope explicitly excludes DeepSearch, so this is a check that nothing leaked across.

- [ ] **Step 6: Stop the test backend**

```bash
taskkill //F //IM python.exe
```
(Or the platform-appropriate equivalent — only if a dev server was started for this verification and needs cleanup.)

- [ ] **Step 7: Final commit if any fixes were needed during verification**

If Steps 2-5 surfaced any issues, fix them in the relevant task's files and commit with a message describing the specific fix (not a generic "fix bugs" — name what broke and why, matching this session's established commit-message style).
