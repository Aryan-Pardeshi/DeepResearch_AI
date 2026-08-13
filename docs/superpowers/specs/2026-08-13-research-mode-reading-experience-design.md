# Research Mode reading experience — design spec

Date: 2026-08-13
Scope: `research-bot/frontend` (Research Mode workspace only — checkpoint panels, live paper view). DeepSearch mode and landing pages are explicitly out of scope; they were reworked earlier in this session and the user confirmed they don't need another pass.

## Problem

Three related complaints about the Research Mode workspace:

1. **No sources shown.** The backend fetches, screens, and scores real papers (title, authors, year, DOI, relevance score, full-text excerpt) but the frontend only ever surfaces counts (`rawPapersCount`, `screenedPapersCount`). The actual paper objects are discarded on arrival. There's an unwired paper-detail modal (`openPaperInspector` / `#paper-detail-modal` in `app.js`/`index.html`) already built for this and never called anywhere.
2. **Checkpoint panels are "boring" / walls of text.** At checkpoint 2, `researchGap` and `conceptualFramework` render in full — observed at ~2500 words visible at once in a live test run. Only `literatureReview` is truncated (hard cut at 400 chars, no expand). Body text also uses `--text-secondary` (`rgb(161,161,170)`), which the user found too dim to read comfortably.
3. **The live/final paper view has no typography at all.** `.paper-render-container` (`#rm-paper-output`) has zero CSS rules. `marked.parse()` output renders with pure browser UA defaults — no heading hierarchy, no paragraph spacing, no distinction between a section heading and body text. This is the app's primary deliverable and it currently reads as an undifferentiated wall of white text.

## Non-goals

- DeepSearch mode's workspace (worker cards, report view) — not touched.
- Landing pages — not touched.
- Guaranteeing 100% accurate inline citation matching — best-effort only (see Component 5).
- Redesigning the HITL approve/revise interaction model itself — only how the *content inside* the panels reads.

## Components

### 1. Data layer: capture paper objects from SSE

`applyRMStatePayload` currently drops `raw_papers` / `screened_papers` on purpose (this was fixed earlier this session specifically to stop them from bloating `localStorage`). That constraint stays — the fix is to capture them into a **non-persisted** field:

- Add `state.rm.screenedPapers` (array, default `[]`), populated from `node_update` payloads when `data.screened_papers` (or `raw_papers` before screening completes) is present.
- `saveRMSession()` must continue to exclude this field from the localStorage blob — it stays in-memory only.
- On page reload, `restoreRMSessionOnLoad()`'s existing background sync to `/research-mode/result/{thread_id}` already returns the full arrays in `values` — wire that same field through there too, so a reload doesn't lose the paper list.

### 2. Checkpoint 2: "Evidence used" strip

Checkpoint 1 happens before `paper_fetcher` runs — there are no papers yet, so no sources UI there (confirmed with the user; the original ask conflated 1 and 2, corrected during clarification).

At checkpoint 2, add a compact section above or alongside the existing Literature Review / Research Gap / Framework blocks:

- Reuse the existing corpus-stats-bar visual style (retrieved → deduplicated → screened → included → full-text) — already built, already wired to `updateCorpusStats()`, just needs to be visible/repeated in this panel context if not already in view.
- A scrollable list of the top ~10 screened papers by relevance score: title (truncated), year, source badge (OpenAlex/Semantic Scholar/arXiv — reuse the index-mark assets already added to the landing page), relevance score. Each row is clickable.
- Click → `openPaperInspector(paper)` using the existing modal (now wired: currently `dom.modalCloseBtn` click handler exists per this session's earlier fix, but nothing ever calls `openPaperInspector`).

### 3. Dedicated sources/library panel

A new collapsible section in `#rm-workspace-panel`, sibling to the pipeline tracker card, available throughout the run and after completion (not gated behind a checkpoint):

- Card grid of all `state.rm.screenedPapers`, each showing title, authors, year, source, relevance score.
- Same click → `openPaperInspector(paper)` wiring as Component 2.
- Empty state before any papers exist ("Papers will appear here once corpus retrieval starts").
- No filtering/sorting UI in v1 — YAGNI; papers are already relevance-sorted by the backend. Revisit only if the user asks after seeing it with real data.

### 4. Wall-of-text fix in checkpoint 2

Apply the same truncate-with-expand pattern to `researchGap` and `conceptualFramework` that `literatureReview` already has (currently just `.slice(0, 400)` with no way to see more — that half of the fix is also missing today):

- Cap each block's initial rendered height (character-based cap, ~400 chars, matching the existing literature review behavior) with a "Show full text" / "Show less" toggle button.
- Applies to `renderRMHitlPanel()`'s checkpoint_2 branch only — checkpoint_3 (hypotheses, already itemized as H1-H5 cards) and checkpoint_4 (research design/data collection/data analysis, shorter blocks in practice) are not in scope unless real content later proves otherwise.

### 5. Inline citations in the live/final paper (best-effort)

- Regex match citation-like patterns — `(Lastname et al., YYYY)` and `(Lastname, YYYY)` — against `state.rm.screenedPapers`' `authors[0]` last name + `year`.
- On match, wrap in an `<a>` that opens the paper inspector modal (not an external link — keeps the reader in the app).
- No match → leave as plain text, unchanged from today. This is explicitly best-effort: the model's citation text won't always map cleanly to a specific screened paper (paraphrased names, multi-author "et al." collisions, references not in the screened set). No attempt to guarantee coverage.
- Runs client-side at render time in `renderRMPaperLive()` / `renderRMPaperFinal()`, not stored in state.

### 6. Paper typography (`.paper-render-container`)

Currently has zero CSS rules. Add a proper reading-optimized style pass:

- `h1` (paper title): large, bold, distinct from body.
- `h2` (section headings — "1. Introduction", "2. Literature Review", etc.): clear visual break from surrounding paragraphs — size, weight, top margin, maybe a subtle rule/border.
- `h3` (subsections, e.g. "8.1 Research Design"): one step down from h2.
- `p`: comfortable line-height and paragraph spacing, readable max-width (avoid full-bleed line lengths on wide viewports).
- `strong` / `em`: visually distinct from body weight/style — currently likely invisible against plain white-on-dark if unstyled.
- `ul` / `ol`: proper indentation and item spacing (hypotheses list, references list, future scope list all render as markdown lists).
- Body text color: bump from the complaint ("too made white text no formatting") — this component addresses the *formatting* half; Component 4's color bump addresses checkpoint-panel body text specifically. The paper view's own text color should be reviewed as part of this pass for the same "not too dim, not glaring white" balance.

## Data flow summary

```
SSE node_update (paper_fetcher / paper_screener)
  → data.data.screened_papers (or raw_papers)
  → state.rm.screenedPapers (in-memory, NOT persisted)
  → consumed by:
      - Checkpoint 2 "Evidence used" strip (Component 2)
      - Sources/library panel (Component 3)
      - Inline citation matching in renderRMPaperLive/Final (Component 5)
  → click on any paper row/citation → openPaperInspector(paper) → existing #paper-detail-modal
```

## Testing

- Live run against the real backend (as done earlier this session) verifying: papers appear in the checkpoint 2 strip and library panel as they're screened; clicking one opens the modal with real data; reload mid-run doesn't lose the paper list; a completed paper's inline citations link out where a match exists and stay plain text where they don't.
- Visual check of checkpoint 2 with a real long `researchGap`/`conceptualFramework` (this session's test thread has both, saved server-side) confirming truncate/expand behaves correctly at the boundary.
- Visual check of the full paper view's heading hierarchy against a real completed paper (same test thread) — confirm h1/h2/h3/lists/emphasis are all visually distinct.
