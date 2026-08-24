# <img src="frontend/assets/logo.png" width="32" height="32" style="vertical-align: middle; border-radius: 7px;"> DeepResearch

An AI-powered multi-agent research workspace with **two modes**: fast web research that returns a cited report, and a full evidence-grounded academic pipeline that writes complete, citation-verified research papers with human-in-the-loop quality gates.

**🔗 Live demo → [deep-research-ai-xi.vercel.app](https://deep-research-ai-xi.vercel.app/)**

---

## Two Modes

| | **DeepSearch** | **Research Mode (Evidence-First)** |
|---|---|---|
| **Goal** | Answer a question from the live web | Write a full, evidence-grounded academic paper |
| **Sources** | Tavily web search | OpenAlex · Semantic Scholar · Crossref · PubMed · arXiv · OpenCitations |
| **Agents** | 5 (fan-out parallel researchers) | 25 specialized agents across 5 evidence phases |
| **HITL Checkpoints** | 1 (plan approval) | 3 Quality Gates (Protocol, Evidence Corpus, Hypotheses) |
| **Data Invariant** | LLM web summary | Deterministic `EvidenceRecord` store (quotes, metrics, baselines) |
| **PRISMA Tracking** | N/A | Deterministic PRISMA 2020 flow counts & assertions |
| **Integrity Audit** | Citation regex | Automated citation & numerical claim grounding verification |
| **Runtime** | ~1-2 min | ~5-15 min |
| **Output** | Structured markdown report | Full paper + PRISMA flow chart + evidence mapping matrix |
| **Export** | `.md` | `.pdf` · `.docx` |

---

## Architecture

Both modes run as separate LangGraph state machines behind one FastAPI backend, sharing the LLM layer, checkpointer, and SSE streaming transport.

```mermaid
flowchart TB
    UI["🖥️ Frontend<br/>Vanilla JS · Swiss Modernism 2.0"]
    API["⚡ FastAPI<br/>SSE streaming & Heartbeats"]

    UI <-->|"Server-Sent<br/>Events"| API

    API --> DS["🔎 DeepSearch<br/>Graph"]
    API --> RM["📚 Research Mode<br/>25-Agent Graph"]

    DS --> TAV["🌐 Tavily<br/>Web Search"]
    RM --> ACAD["🎓 Multi-Source Academic APIs<br/>OpenAlex · Semantic Scholar · Crossref<br/>PubMed · arXiv · OpenCitations"]

    DS --> LLM["🧠 LLM Layer<br/>Structured JSON Outputs"]
    RM --> LLM
    LLM --> CACHE[("💾 SQLite<br/>response cache")]

    DS --> CP[("🔁 Checkpointer<br/>resumable state")]
    RM --> CP

    style UI fill:#4f46e5,stroke:#3730a3,color:#fff
    style API fill:#4f46e5,stroke:#3730a3,color:#fff
    style DS fill:#0891b2,stroke:#0e7490,color:#fff
    style RM fill:#0891b2,stroke:#0e7490,color:#fff
    style TAV fill:#ea580c,stroke:#c2410c,color:#fff
    style ACAD fill:#ea580c,stroke:#c2410c,color:#fff
    style LLM fill:#db2777,stroke:#be185d,color:#fff
    style CACHE fill:#475569,stroke:#334155,color:#fff
    style CP fill:#475569,stroke:#334155,color:#fff
```

---

## 25-Agent Evidence-First Research Pipeline

```mermaid
flowchart TB
    subgraph P1 ["Phase 1: Planning & Protocol"]
        direction LR
        START(["Problem Statement"]) --> SCOPE["<b>1. scope_definition</b><br/>PICOC Scoping"]
        SCOPE --> PROT["<b>2. protocol_agent</b><br/>Search Protocol"]
        PROT --> KW["<b>3. keyword_extractor</b><br/>Boolean Search Strings"]
        KW --> G1{"🧑 Gate 1<br/>Protocol Review"}
        G1 -.->|"revise"| REVISER["scope_reviser"]
        REVISER -.-> G1
    end

    subgraph P2 ["Phase 2: Multi-Source Retrieval & Screening"]
        direction LR
        FETCH["<b>4. paper_fetcher</b><br/>OpenAlex · S2 · Crossref · PubMed · arXiv"] --> CITE["<b>5. citation_expander</b><br/>OpenCitations 1-Hop Graph"]
        CITE --> META["<b>6. metadata_validator</b><br/>DOI Dedup & Normalization"]
        META --> SCREEN["<b>7. paper_screener</b><br/>Title/Abstract Scored Filter"]
        SCREEN --> FULL["<b>8. fulltext_eligibility</b><br/>OA Full-Text PDF Ingestion"]
        FULL --> QUAL["<b>9. quality_appraisal</b><br/>Methodological Rigor"]
    end

    subgraph P3 ["Phase 3: Structured Evidence Extraction"]
        direction LR
        EX_FIND["<b>10. evidence_extractor</b><br/>Qualitative Findings"] --> EX_QUANT["<b>11. quantitative_extractor</b><br/>Metrics & Baselines"]
        EX_QUANT --> EX_METH["<b>12. methodology_extractor</b><br/>Design & Sample Sizes"]
        EX_METH --> EX_LIM["<b>13. limitation_extractor</b><br/>Reported Constraints"]
        EX_LIM --> PROV["<b>14. provenance_agent</b><br/>Deterministic ID Anchoring"]
        PROV --> G2{"🧑 Gate 2<br/>Evidence Review"}
    end

    subgraph P4 ["Phase 4: Theoretical Framing & Synthesis"]
        direction LR
        TAX["<b>15. taxonomy_agent</b><br/>Thematic Clustering"] --> GAP["<b>16. gap_analysis</b><br/>Contradictions & Open Questions"]
        GAP --> FRAME["<b>17. conceptual_framework</b><br/>Theoretical Paradigm"]
        FRAME --> HYP["<b>18. hypotheses</b><br/>Directional Hypotheses H1..H5"]
        HYP --> G3{"🧑 Gate 3<br/>Hypotheses Review"}
    end

    subgraph P5A ["Phase 5A: Methodology & Section Drafting"]
        direction LR
        M_DES["<b>19. research_design</b>"] --> M_COL["<b>20. data_collection</b>"]
        M_COL --> M_ANA["<b>21. data_analysis</b>"]
        M_ANA --> W_REV["<b>Literature Review</b>"]
        W_REV --> W_RES["<b>22. results</b><br/>(Empirical Matrix)"]
        W_RES --> W_DISC["<b>23. discussion</b>"]
        W_DISC --> W_LIM["<b>24. limitations</b>"]
        W_LIM --> W_CONC["<b>25. conclusion</b>"]
    end

    subgraph P5B ["Phase 5B: Verification, Figures & Delivery"]
        direction LR
        W_REF["<b>References & Citations</b>"] --> V_CITE["🔍 citation_validator"]
        V_CITE --> V_CLAIM["🔍 claim_validator"]
        V_CLAIM --> V_AUDIT["🛡️ integrity_auditor"]
        V_AUDIT --> FIGS["📊 figures_node<br/>PRISMA + Evidence Matrix"]
        FIGS --> APPS["Appendices & Audit Protocol"]
        APPS --> END_NODE(["📄 Complete Publication-Grade Paper (PDF / DOCX)"])
    end

    G1 -->|"approved"| FETCH
    QUAL --> EX_FIND
    G2 -->|"approved"| TAX
    G3 -->|"approved"| M_DES
    W_CONC --> W_REF

    style START fill:#6366f1,stroke:#4338ca,color:#fff
    style G1 fill:#f59e0b,stroke:#b45309,color:#fff
    style G2 fill:#f59e0b,stroke:#b45309,color:#fff
    style G3 fill:#f59e0b,stroke:#b45309,color:#fff
    style END_NODE fill:#10b981,stroke:#047857,color:#fff
    style P1 fill:none,stroke:#64748b,stroke-width:1px,stroke-dasharray: 4 4
    style P2 fill:none,stroke:#64748b,stroke-width:1px,stroke-dasharray: 4 4
    style P3 fill:none,stroke:#64748b,stroke-width:1px,stroke-dasharray: 4 4
    style P4 fill:none,stroke:#64748b,stroke-width:1px,stroke-dasharray: 4 4
    style P5A fill:none,stroke:#64748b,stroke-width:1px,stroke-dasharray: 4 4
    style P5B fill:none,stroke:#64748b,stroke-width:1px,stroke-dasharray: 4 4
```

---

## 3 Human-in-the-Loop Quality Gates

Each gate genuinely pauses graph execution via LangGraph `interrupt()`, allowing the author to approve or request targeted revisions in natural language:

| Gate | Phase | Review Artifacts | Guarantees |
|---|---|---|---|
| **Gate 1: Planning & Protocol** | Phase 1 | PICOC Protocol, Objectives, Research Questions, Boolean Keywords | Prevents query divergence before initiating multi-source retrieval |
| **Gate 2: Evidence & Corpus** | Phase 3 | PRISMA Flow Tracker, Screened Literature, Extracted Evidence Records | Verifies empirical grounding before theoretical synthesis begins |
| **Gate 3: Hypotheses & Framework** | Phase 4 | Conceptual Framework, Research Gaps, Formulated Hypotheses (H1..H5) | Confirms theoretical validity before committing to full paper generation |

---

## Academic Integrity & Research Invariants

1. **Deterministic Flow-Tracking State Machine (PRISMA 2020-aligned)**:
   `PRISMATracker.validate_invariants()` asserts these *internal* conservation relations:
   $$\text{records\_identified} - \text{duplicates\_removed} = \text{records\_after\_dedup}$$
   $$\text{records\_screened} - \text{excluded\_title\_abstract} = \text{full\_text\_requested}$$
   $$\text{full\_text\_assessed} - \text{excluded\_full\_text} = \text{studies\_included}$$
   `full_text_requested` is the tracker's internal shortcut for PRISMA's *reports sought for retrieval*. The distinct PRISMA stages *reports not retrieved* (`full_text_unavailable`) and *reports assessed for eligibility* (`full_text_assessed`) are tracked as separate fields, but the hand-off between them is not asserted—so the equations above are internal invariants rather than the complete PRISMA 2020 flow. Every count is tracked deterministically in code—never generated or estimated by an LLM.

2. **Immutable Evidence Store**:
   - `PaperRecord.paper_id`: first 16 hex characters of a SHA-256 digest (a truncated representation, not the full digest) computed over a source-qualified key: `doi:<canonicalized DOI>` when a DOI is available, otherwise `title:<normalized title>:<year>`. Normalized titles are not assumed unique, so the fallback key also folds in the publication year (`nd` when unknown).
   - `EvidenceRecord.evidence_id`: deterministic composite identifier `{paper_id}_ev001` (the composite is not itself hashed) anchoring exact quote, metric, baseline value, and effect direction.
   - `ReviewClaim.claim_id`: deterministic composite identifier `{section}_cl001` (section slug truncated to 8 characters) linking paper claims to supporting evidence IDs.

3. **Deterministic Validation Pipeline**:
   - `citation_validator`: Audits every in-text citation against known `PaperRecord` metadata; flags unverified or hallucinated citations.
   - `claim_validator`: Audits quantitative sentences against extracted `EvidenceRecord` benchmark metrics.
   - `integrity_auditor`: Validates PRISMA invariants and issues comprehensive `ValidationReport`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph (StateGraph, `interrupt()` HITL, `Send()` fan-out, SQLite persistence) |
| **Structured LLM** | Pydantic v2 schemas + `ainvoke_structured_with_retry` |
| **Academic Sources** | OpenAlex, Semantic Scholar, Crossref, PubMed, arXiv, OpenCitations |
| **Full-Text Ingestion** | Unpaywall → Europe PMC → CORE fallback chain |
| **Backend API** | FastAPI + Server-Sent Events (SSE) with keep-alive heartbeats |
| **Frontend UI/UX** | Vanilla JS + CSS (Swiss Modernism 2.0, zero-build, responsive) |
| **Figures & Charts** | matplotlib (PRISMA 2020 Flowchart, Hypothesis Evidence Matrix) |
| **Document Export** | FPDF2 (`.pdf` with hanging APA indents) · python-docx (`.docx`) |

---

## Getting Started

### 1. Clone & Configure

```bash
git clone https://github.com/Aryan-Pardeshi/DeepResearch_AI.git
cd DeepResearch_AI
cp .env.example .env
```

Minimum `.env` configuration:

```bash
LLM_API_KEY="your_api_key_here"
LLM_BASE_URL="https://api.deepseek.com"
TAVILY_API_KEY="your_tavily_key_here"
OPENALEX_EMAIL="you@example.com"
```

### 2. Run with Docker

```bash
docker compose up -d --build
```

Access the UI at **[http://localhost:8000](http://localhost:8000)**.

### 3. Local Development

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows (or source .venv/bin/activate on Unix)
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

---

## Author

Built by [Aryan Pardeshi](https://github.com/Aryan-Pardeshi) — open to AI/ML internship opportunities.

Connect: [LinkedIn](https://linkedin.com/in/aryan-pardeshi-dev) · [GitHub](https://github.com/Aryan-Pardeshi)
