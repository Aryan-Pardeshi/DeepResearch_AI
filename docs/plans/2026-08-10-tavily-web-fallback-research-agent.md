# Tavily Web Search Last-Resort Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Tavily web search into the academic literature retrieval pipeline as a last-resort fallback and update research agent system prompts.

**Architecture:** Add `fetch_tavily_web_papers` fallback in `academic_search.py`, update `search_academic_papers` low-yield check, and update system prompts in `agents.py` and `researcher.py`.

**Tech Stack:** Python 3.13, Tavily API, Asyncio, Pytest.

---

### Task 1: Add `fetch_tavily_web_papers` Fallback in `academic_search.py`

**Files:**
- Modify: `research-bot/backend/app/tools/academic_search.py`
- Modify: `research-bot/tests/test_oa_resolver.py`

- [ ] **Step 1: Implement `fetch_tavily_web_papers` and low-yield fallback in `search_academic_papers`**

```python
async def fetch_tavily_web_papers(keyword: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """LAST RESORT FALLBACK: Fetches web articles via Tavily when academic database indexes return insufficient literature."""
    papers = []
    try:
        from backend.app.tools.tavily_search import search_web
        res = search_web(query=f"academic research paper {keyword}", max_results=max_results)
        results = res.get("results", []) if isinstance(res, dict) else []
        for r in results:
            title = r.get("title", "").strip()
            content = r.get("content", "").strip()
            url = r.get("url", "").strip()
            if not title or not content:
                continue
            papers.append({
                "title": title,
                "abstract": content,
                "authors": ["Web Source"],
                "year": "2026",
                "doi": "",
                "url": url,
                "pdf_url": url if url.lower().endswith(".pdf") else "",
                "source": "tavily_web_fallback",
                "citation_count": 0
            })
    except Exception as e:
        logger.warning(f"Tavily web fallback search skipped for '{keyword}': {e}")
    return papers
```

- [ ] **Step 2: Commit academic_search.py updates**

```bash
git add research-bot/backend/app/tools/academic_search.py
git commit -m "feat(backend): add Tavily web search fallback when academic index yield is low"
```

---

### Task 2: Update Research Agent System Prompts in `agents.py`

**Files:**
- Modify: `research-bot/backend/app/agents/research_mode/agents.py`

- [ ] **Step 1: Update keyword extractor / paper fetcher agent prompts with last-resort Tavily web search instructions**

```python
# System prompt instruction:
# LAST RESORT WEB SEARCH: Academic database indexes (OpenAlex, Semantic Scholar, ArXiv) are primary. Tavily Web Search is equipped ONLY as a last resort when academic indexes fail to return sufficient papers.
```

- [ ] **Step 2: Commit system prompt changes**

```bash
git add research-bot/backend/app/agents/research_mode/agents.py
git commit -m "docs(prompts): add explicit last-resort Tavily web search policy to research agent prompts"
```

---

### Task 3: Test and Verify with Pytest

- [ ] **Step 1: Run pytest test suite**

```powershell
$env:PYTHONPATH="research-bot"; .venv\Scripts\python.exe -m pytest research-bot/tests
```
