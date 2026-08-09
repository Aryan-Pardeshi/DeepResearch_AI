# Implementation Plan - OA Resolvers, PRISMA Flow Diagram, and Per-Run Model Selection

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance Research Mode by resolving legal open-access PDFs when publisher URLs 403, generating PRISMA flow diagrams and evidence tables embedded into PDF reports, and enabling per-run LLM model selection across Planner, Researcher, and Aggregator roles.

**Architecture:** 
1. New `oa_resolver.py` module with Unpaywall, Europe PMC, and CORE v3 fallback logic integrated into `fulltext_fetcher.py`.
2. Pipeline metrics captured in `ResearchModeState["corpus_stats"]`, plotted via headless matplotlib in `figures.py` inside a new `figures_agent` graph node, and embedded in `pdf_generator.py`.
3. Per-run model overrides passed via API/UI payload into `ResearchModeState["model_overrides"]` and resolved by a helper `get_llm_for(state, role)` across all agent nodes.

**Tech Stack:** Python 3.11+, LangGraph, FastAPI, httpx, matplotlib, fpdf2, HTML5/JS.

## Global Constraints

- Do not rewrite `academic_search.py`, `agents.py`, `pdf_generator.py`, or `research_mode_builder.py` wholesale.
- Preserve existing `_text_belongs_to_paper` guard, cover-page skip, concurrent screening, Checkpoint 1 revision loop, SQLite checkpointer, LLM cache, and preprint PDF layout.
- All new network calls must be individually timeout-bounded and never raise exceptions into the graph.

---

### Task 1: Rescue Full-Text Yield with OA Resolvers

**Files:**
- Create: `research-bot/backend/app/tools/oa_resolver.py`
- Modify: `research-bot/backend/app/tools/fulltext_fetcher.py`
- Create Test: `research-bot/tests/test_oa_resolver.py`

- [ ] **Step 1: Write unit tests for `oa_resolver.py`**
- [ ] **Step 2: Create `oa_resolver.py` with `resolve_unpaywall`, `resolve_europe_pmc`, `resolve_core`, and `resolve_oa_pdf_url`**
- [ ] **Step 3: Integrate `resolve_oa_pdf_url` into `fulltext_fetcher.py` with retry logic and custom User-Agent**
- [ ] **Step 4: Run tests to verify `oa_resolver` functionality**

### Task 2: PRISMA Flow Diagram & Evidence Table

**Files:**
- Modify: `research-bot/backend/app/graph/research_mode_state.py`
- Modify: `research-bot/backend/app/tools/academic_search.py`
- Create: `research-bot/backend/app/tools/figures.py`
- Modify: `research-bot/backend/app/agents/research_mode/agents.py`
- Modify: `research-bot/backend/app/graph/research_mode_builder.py`
- Modify: `research-bot/backend/app/tools/pdf_generator.py`
- Create Test: `research-bot/tests/test_figures.py`

- [ ] **Step 1: Update `ResearchModeState` schema with `corpus_stats`, `figures`, and `model_overrides`**
- [ ] **Step 2: Update `search_academic_papers` and `screen_papers` to return counts/stats**
- [ ] **Step 3: Create `figures.py` with `render_prisma_diagram` and `render_evidence_table`**
- [ ] **Step 4: Add `figures_agent` in `agents.py` and wire it into `research_mode_builder.py`**
- [ ] **Step 5: Embed figures into `pdf_generator.py` after Methodology (Section 8) and Results (Section 9)**
- [ ] **Step 6: Run tests for figures rendering and state tracking**

### Task 3: Per-Run Model Selection in Frontend & Backend

**Files:**
- Modify: `research-bot/backend/app/agents/research_mode/agents.py`
- Modify: `research-bot/backend/app/tools/academic_search.py`
- Modify: `research-bot/backend/app/api/research_mode.py`
- Modify: `research-bot/frontend/index.html`
- Modify: `research-bot/frontend/app.js`

- [ ] **Step 1: Add `get_llm_for(state, role)` in `agents.py` and replace all 19 `get_llm` calls**
- [ ] **Step 2: Add `models: Dict[str, str] = {}` to `ResearchModeStartRequest` in `research_mode.py` and pass `model_overrides` into state**
- [ ] **Step 3: Update `index.html` to add model override inputs in the advanced panel**
- [ ] **Step 4: Update `app.js` to collect model choices and send them in `handleRMStart`**
- [ ] **Step 5: Test model selection override handling**

### Task 4: Verification & Acceptance Tests

- [ ] **Step 1: Execute test suite and verify test pass status**
- [ ] **Step 2: Perform live search test on non-arXiv topic to verify OA resolvers full-text yield rescue**
- [ ] **Step 3: Verify PRISMA figure numbers match backend logs**
- [ ] **Step 4: Verify exported PDF page metrics (612x792pt, 1in margin, body 10pt, no title page)**
- [ ] **Step 5: Perform live run with different models per role and verify log outputs**
- [ ] **Step 6: Perform complete end-to-end run on new problem statement and capture timing, warnings/errors, and PDF metrics**
