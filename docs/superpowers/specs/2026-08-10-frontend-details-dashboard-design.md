# Frontend Academic Research Dashboard & Paper Deep-Dive Inspector

## Design Spec

### Overview
This design enhances the Research Mode frontend UI (`index.html`, `styles.css`, `app.js`) to provide an interactive, detailed academic research dashboard. It adds real-time execution timing metrics, a live event log stream drawer, corpus breakdown cards, interactive PRISMA diagram display, hypothesis-to-evidence matrix, and a full-text paper excerpt inspector drawer.

---

### Key Components & Layout

#### 1. Live Pipeline & Execution Metrics Bar
- **Node Execution Timers**: Real-time counter per graph node (showing duration in seconds upon completion, e.g. `literature_review (21.0s)`).
- **Corpus Summary Badges**: Metric cards displayed at the top of the research dashboard:
  - `Retrieved` (total raw papers from search)
  - `Deduplicated` (unique papers after deduplication)
  - `Screened` (evaluated for inclusion)
  - `Included` (passed relevance threshold)
  - `Full-Text Fetched` (extracted PDF text count)
- **Live Event Log Stream Drawer**: A collapsible terminal console displaying live SSE events (`node_start`, `node_update`, `token_stream`, OA resolver status, rate limit retries) with timestamped log lines and a clear log button.

#### 2. Interactive PRISMA & Open-Access Rescue Tab / Card
- **Embedded PRISMA Flowchart**: Displays the generated PRISMA diagram (`figures.prisma`) with click-to-zoom modal view.
- **OA Resolver Breakdown Card**: Visual list showing open-access full-text rescue metrics (Direct PDF vs Unpaywall vs Europe PMC vs CORE) with links to rescued PDF URLs.

#### 3. Hypothesis & Evidence Matrix Viewer
- **Interactive Evidence Table**: Structured matrix mapping included papers to research hypotheses ($H_1, H_2, \dots$) with color-coded status badges:
  - `Supported` (emerald green badge)
  - `Partial` (amber badge)
  - `Refuted` (rose red badge)
  - `Not Addressed` (slate gray badge)
- Filter papers by hypothesis alignment or relevance score.

#### 4. Paper Deep-Dive Inspector (Modal / Slide-Over)
- **Paper Detail Drawer**: Clicking any paper row in the screened paper list or evidence matrix opens a detail inspector slide-over panel featuring:
  - Paper Title, Authors, Venue, Year, DOI link, and PDF download button.
  - LLM Screener relevance score and inclusion/exclusion reasoning.
  - Tabbed full-text excerpt viewer showing extracted text snippets (Introduction, Methodology, Results, Discussion).

---

### Data Contracts & SSE Event Additions

1. **State Payload (`/research-mode/approve`, SSE `node_update`, SSE `completed`)**:
   Ensure `state` emitted via SSE includes:
   - `corpus_stats`: `{"retrieved": int, "after_dedup": int, "screened": int, "included": int, "fulltext_fetched": int}`
   - `figures`: `{"prisma": str, "evidence": str}`
   - `screened_papers`: List of paper dicts containing `title`, `authors`, `year`, `doi`, `pdf_url`, `relevance_score`, `inclusion_reason`, `hypothesis_support`, `fulltext_excerpt`.
   - `node_timings`: Dict mapping node name to duration in seconds.

2. **Frontend State & DOM Elements**:
   - `index.html`: Update `#rm-pipeline-steps-grid` and add `#rm-corpus-stats-bar`, `#rm-log-drawer`, `#rm-prisma-container`, `#rm-evidence-table-container`, and `#paper-detail-modal`.
   - `styles.css`: Add styles for metric cards, terminal log drawer, evidence matrix, badges, and slide-over paper inspector drawer.
   - `app.js`: Update SSE event listener to render timers, populate log stream, render PRISMA image, generate evidence table, and handle paper modal clicks.
