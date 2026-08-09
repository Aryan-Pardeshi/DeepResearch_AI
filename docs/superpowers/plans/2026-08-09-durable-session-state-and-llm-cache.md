# Durable Session State and LLM Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement durable session state using SQLite-backed LangGraph checkpointers (`AsyncSqliteSaver`), persistent LLM caching with `LoggingSQLiteCache`, an SSE reconnection engine with per-thread event buffering, frontend session resume, and CLI test resume capabilities.

**Architecture:**
- **Backend Graph & Checkpointer:** `research_mode_builder.py` and `builder.py` compile graphs lazily with an active `AsyncSqliteSaver` instance initialized in FastAPI's `lifespan` handler using `RESEARCH_DB_PATH` env var (default `./data/research_state.db`). All state calls in `research_mode.py` use `await graph.aget_state(config)`.
- **LLM Caching:** `llm.py` initializes `LoggingSQLiteCache` (subclass of `langchain_community.cache.SQLiteCache`) pointing to `LLM_CACHE_PATH` (default `./data/llm_cache.db`) and logs `[LLM CACHE HIT]` or `[LLM CACHE MISS]`.
- **SSE Reconnect:** `research_mode.py` uses per-thread append-only event buffers with sequence IDs for node-level events and cursor support (`Last-Event-ID` / `from_seq`), along with background task completion cleanup.
- **Frontend & CLI:** `app.js` persists session state to `localStorage` and restores via extended `GET /research-mode/result/{thread_id}`. `research-bot/test_research_mode.py` provides a resumable E2E CLI test runner.

**Tech Stack:** Python 3.13, FastAPI, LangChain, LangGraph, `langgraph-checkpoint-sqlite`, SQLite, Vanilla JS (HTML5 `localStorage`).

## Global Constraints
- Target python executable: `.venv\Scripts\python.exe`.
- Environment variable defaults: `RESEARCH_DB_PATH` -> `./data/research_state.db`, `LLM_CACHE_PATH` -> `./data/llm_cache.db`.
- Database directory `Path(...).parent.mkdir(parents=True, exist_ok=True)` must be auto-created.
- Do NOT delete or simplify existing graph/agent functionality.
- Do NOT rewrite whole files; make targeted, minimal edits.
- Add `data/*.db` and `data/` to `.gitignore`.
- Add `langgraph-checkpoint-sqlite` to `research-bot/requirements.txt` and install into `.venv`.
- Output proof (`git log --oneline -3` and command output) before declaring tasks completed or committed.

---

### Task 1: Requirements, Git Ignore, and LLM Response Cache with Hit Logging

**Files:**
- Create: `data/.gitkeep`
- Modify: `research-bot/requirements.txt`
- Modify: `.gitignore`
- Modify: `research-bot/backend/app/llm.py`

**Interfaces:**
- `llm.py` exports `set_llm_cache(LoggingSQLiteCache(database_path=...))` initialized on import or explicit call.
- `LoggingSQLiteCache.lookup(prompt, llm_string)` logs `[LLM CACHE HIT]` or `[LLM CACHE MISS]`.

- [ ] **Step 1: Install dependency and update requirements.txt and .gitignore**

Run:
```powershell
.venv\Scripts\python.exe -m pip install langgraph-checkpoint-sqlite
```
Add `langgraph-checkpoint-sqlite` to `research-bot/requirements.txt`.
Add `data/` and `data/*.db` to `.gitignore`.

- [ ] **Step 2: Implement LoggingSQLiteCache in llm.py**

Modify `research-bot/backend/app/llm.py`:
```python
import os
import logging
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class LoggingSQLiteCache(SQLiteCache):
    def lookup(self, prompt: str, llm_string: str):
        result = super().lookup(prompt, llm_string)
        prefix = (prompt[:50] + "...") if len(prompt) > 50 else prompt
        if result is not None:
            logger.info(f"[LLM CACHE HIT] Prompt: {prefix!r}")
        else:
            logger.info(f"[LLM CACHE MISS] Prompt: {prefix!r}")
        return result

def init_llm_cache():
    cache_path_str = os.getenv("LLM_CACHE_PATH", "./data/llm_cache.db")
    cache_path = Path(cache_path_str).resolve()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    set_llm_cache(LoggingSQLiteCache(database_path=str(cache_path)))
    logger.info(f"LLM cache initialized at {cache_path}")

init_llm_cache()
```

- [ ] **Step 3: Test LLM Cache with Hit Logging**

Run a quick python check to verify cache initialization and hit logging:
```powershell
.venv\Scripts\python.exe -c "from backend.app.llm import get_llm; print('LLM cache loaded successfully')"
```

- [ ] **Step 4: Commit Task 1**

```powershell
git add research-bot/requirements.txt .gitignore research-bot/backend/app/llm.py
git commit -m "feat: add langgraph-checkpoint-sqlite dependency and persistent LLM cache with hit logging"
```

---

### Task 2: Lazy Async Graph Compiler and FastAPI Lifespan Checkpointer Wiring

**Files:**
- Modify: `research-bot/backend/app/graph/research_mode_builder.py`
- Modify: `research-bot/backend/app/graph/builder.py`
- Modify: `research-bot/backend/app/main.py`

**Interfaces:**
- `research_mode_builder.py` exports `set_checkpointer(checkpointer)` and `get_research_mode_graph()`.
- `builder.py` exports `set_checkpointer(checkpointer)` and `get_research_graph()`.
- `main.py` manages `AsyncSqliteSaver` in `@asynccontextmanager async def lifespan(app: FastAPI)` using `RESEARCH_DB_PATH` env var (default `./data/research_state.db`).

- [ ] **Step 1: Update research_mode_builder.py for lazy graph accessor**

In `research-bot/backend/app/graph/research_mode_builder.py`:
Replace:
```python
checkpointer = MemorySaver()
research_mode_graph = builder.compile(checkpointer=checkpointer)
```
With:
```python
_checkpointer = MemorySaver()
_compiled_graph = None

def set_checkpointer(checkpointer):
    global _checkpointer, _compiled_graph
    _checkpointer = checkpointer
    _compiled_graph = builder.compile(checkpointer=_checkpointer)
    logger.info(f"Research Mode graph compiled with checkpointer: {type(checkpointer).__name__}")

def get_research_mode_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = builder.compile(checkpointer=_checkpointer)
    return _compiled_graph

# For backwards compatibility/fallback
research_mode_graph = get_research_mode_graph()
```

- [ ] **Step 2: Update builder.py (DeepSearch mode) for consistency**

In `research-bot/backend/app/graph/builder.py`:
Apply the same lazy accessor pattern with `set_checkpointer(checkpointer)` and `get_research_graph()`.

- [ ] **Step 3: Wire AsyncSqliteSaver in FastAPI Lifespan (main.py)**

In `research-bot/backend/app/main.py`:
Add:
```python
from contextlib import asynccontextmanager
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from backend.app.graph.research_mode_builder import set_checkpointer as set_rm_checkpointer
from backend.app.graph.builder import set_checkpointer as set_ds_checkpointer

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path_str = os.getenv("RESEARCH_DB_PATH", "./data/research_state.db")
    db_path = Path(db_path_str).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        await checkpointer.setup()
        set_rm_checkpointer(checkpointer)
        set_ds_checkpointer(checkpointer)
        yield

app = FastAPI(title="AI Research Assistant Bot", lifespan=lifespan)
```

- [ ] **Step 4: Verify lifespan initialization and SQLite checkpointer creation**

Run python script to test SQLite checkpointer creation and graph compilation:
```powershell
.venv\Scripts\python.exe -c "import asyncio, os; from pathlib import Path; from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver; from backend.app.graph.research_mode_builder import set_checkpointer, get_research_mode_graph; async def test(): Path('./data').mkdir(exist_ok=True); async with AsyncSqliteSaver.from_conn_string('./data/test_state.db') as saver: await saver.setup(); set_checkpointer(saver); graph = get_research_mode_graph(); print('Graph compiled:', graph is not None); asyncio.run(test())"
```

- [ ] **Step 5: Commit Task 2**

```powershell
git add research-bot/backend/app/graph/research_mode_builder.py research-bot/backend/app/graph/builder.py research-bot/backend/app/main.py
git commit -m "feat: wire SQLite AsyncSqliteSaver checkpointer via FastAPI lifespan and lazy graph accessors"
```

---

### Task 3: Async State Resolution, Extended Result Endpoint, and SSE Reconnect Engine with Buffer & Cursor

**Files:**
- Modify: `research-bot/backend/app/api/research_mode.py`

**Interfaces:**
- `GET /research-mode/result/{thread_id}`: Returns extended state dictionary with `next`, `is_checkpoint`, `is_completed`, `hitl_checkpoint`, `status`. Returns 404 for unknown threads. Uses `await graph.aget_state(config)`.
- `POST /research-mode/start`: Uses `await graph.aget_state(config)`.
- `POST /research-mode/approve`: Accepts optional `from_seq` in request body or `Last-Event-ID` header. Uses per-thread event buffer `thread_buffers[thread_id]`. Replays missed events for `seq > from_seq`, streams new events live, and retains active tasks with TTL cleanup.

- [ ] **Step 1: Replace synchronous get_state calls with await aget_state**

In `research-bot/backend/app/api/research_mode.py`:
Replace `from backend.app.graph.research_mode_builder import research_mode_graph` with `from backend.app.graph.research_mode_builder import get_research_mode_graph`.
Update graph access in endpoints:
```python
graph = get_research_mode_graph()
state = await graph.aget_state(config)
```

- [ ] **Step 2: Extend /research-mode/result/{thread_id} endpoint**

In `research-bot/backend/app/api/research_mode.py`:
```python
@router.get("/research-mode/result/{thread_id}")
@router.get("/research/mode/result/{thread_id}")
async def get_research_mode_result(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_research_mode_graph()
    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Research Mode thread not found")
    
    values = state.values
    is_checkpoint = bool(state.next)
    is_completed = not bool(state.next) and values.get("status") == "completed"
    
    return {
        "values": values,
        "next": list(state.next) if state.next else [],
        "is_checkpoint": is_checkpoint,
        "is_completed": is_completed,
        "hitl_checkpoint": values.get("hitl_checkpoint"),
        "status": values.get("status")
    }
```

- [ ] **Step 3: Implement Per-Thread Event Buffer & SSE Cursor Replay**

In `research-bot/backend/app/api/research_mode.py`:
- Add `thread_buffers: Dict[str, Dict[str, Any]] = {}` to track events (`List[Dict]`), task, and timestamp per thread.
- Modify `ResearchModeApproveRequest` to accept `from_seq: Optional[int] = None`.
- In `approve_research_mode`:
  - Fetch `from_seq` from request or `Last-Event-ID` header.
  - Spawn background execution task if not already running for `thread_id`.
  - Replay buffered node events with `seq > from_seq`.
  - Stream live events as node execution updates.
  - Implement task TTL cleanup upon graph completion or error.

- [ ] **Step 4: Verify async state retrieval and 404 response**

Run backend server or test script to verify `GET /research-mode/result/{thread_id}` returns 404 for nonexistent thread and returns extended dictionary for valid state.

- [ ] **Step 5: Commit Task 3**

```powershell
git add research-bot/backend/app/api/research_mode.py
git commit -m "feat: implement async state resolution, extended result endpoint, and SSE reconnect event buffer"
```

---

### Task 4: Frontend Session Resume and localStorage State Persistence

**Files:**
- Modify: `research-bot/frontend/app.js`

**Interfaces:**
- `saveRMSession()`: Stores `{ threadId: state.rm.threadId, rmState: state.rm, lastSeq }` into `localStorage.setItem('rm_session', ...)`.
- `restoreRMSession()`: Called on `DOMContentLoaded`. If `rm_session` exists, queries `/research-mode/result/{thread_id}`. On 404, clears `localStorage`. On 200, rehydrates state, renders "Resume Session" banner, and restores view.
- `clearRMSession()`: Clears `localStorage.removeItem('rm_session')`.

- [ ] **Step 1: Add save, restore, and clear session helpers in app.js**

In `research-bot/frontend/app.js`:
```javascript
function saveRMSession() {
    if (!state.rm.threadId) return;
    try {
        const sessionData = {
            threadId: state.rm.threadId,
            rmState: state.rm,
            timestamp: Date.now()
        };
        localStorage.setItem('rm_session', JSON.stringify(sessionData));
    } catch (e) {
        console.warn('Failed to save RM session:', e);
    }
}

function clearRMSession() {
    try {
        localStorage.removeItem('rm_session');
    } catch (e) {
        console.warn('Failed to clear RM session:', e);
    }
}

async function restoreRMSessionOnLoad() {
    try {
        const raw = localStorage.getItem('rm_session');
        if (!raw) return;
        const session = JSON.parse(raw);
        if (!session || !session.threadId) return;

        const res = await fetch(`${API_BASE_URL}/research-mode/result/${session.threadId}`);
        if (!res.ok) {
            if (res.status === 404) {
                clearRMSession();
            }
            return;
        }
        const data = await res.json();
        const values = data.values || {};
        
        state.rm.threadId = session.threadId;
        applyRMStatePayload(values);
        if (data.hitl_checkpoint) state.rm.hitlCheckpoint = data.hitl_checkpoint;
        if (data.status) state.rm.status = data.status;

        // Switch UI to Research Mode tab & show Resume Banner
        switchMode('researchmode');
        showResumeBanner(data);
    } catch (e) {
        console.warn('Error restoring session on load:', e);
    }
}
```

- [ ] **Step 2: Wire saveRMSession into node_update, checkpoint, and start handlers**

In `app.js`:
Call `saveRMSession()` inside:
- `startResearchMode` upon receiving initial `thread_id`
- SSE `node_update` handler
- SSE `checkpoint` handler
- SSE `completed` handler
Call `clearRMSession()` inside `resetResearchModeForm` / New Research button listener.

- [ ] **Step 3: Add "Resume Session" UI Banner component in app.js**

Add helper `showResumeBanner(data)` to render a clean notification banner giving the user immediate context that their session was restored, showing current checkpoint or completed paper with option to resume or start fresh.

- [ ] **Step 4: Commit Task 4**

```powershell
git add research-bot/frontend/app.js
git commit -m "feat: implement frontend localStorage persistence and session rehydration on page load"
```

---

### Task 5: Resumable CLI Test Script

**Files:**
- Create: `research-bot/test_research_mode.py`

**Interfaces:**
- Supports command line execution:
  `python research-bot/test_research_mode.py [--problem "..." | --resume [thread_id]]`
- Persists active `thread_id` to `./data/latest_thread_id.txt`.
- Prints resumed node/stage on `--resume`.

- [ ] **Step 1: Write test_research_mode.py**

Create `research-bot/test_research_mode.py`:
```python
import sys
import os
import argparse
import asyncio
from pathlib import Path

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from backend.app.graph.research_mode_builder import set_checkpointer, get_research_mode_graph

THREAD_FILE = Path("./data/latest_thread_id.txt")

async def run_pipeline(problem: str, resume_thread_id: str | None = None):
    db_path_str = os.getenv("RESEARCH_DB_PATH", "./data/research_state.db")
    db_path = Path(db_path_str).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        await saver.setup()
        set_checkpointer(saver)
        graph = get_research_mode_graph()

        if resume_thread_id:
            thread_id = resume_thread_id
            print(f"Attaching to existing thread: {thread_id}")
        elif THREAD_FILE.exists() and not problem:
            thread_id = THREAD_FILE.read_text().strip()
            print(f"Reading saved thread_id from file: {thread_id}")
        else:
            import uuid
            thread_id = str(uuid.uuid4())
            THREAD_FILE.write_text(thread_id)
            print(f"Started new thread: {thread_id}")

        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.aget_state(config)

        if state and state.next:
            print(f"[RESUME] Resuming thread {thread_id} at stage: {list(state.next)}")
            input_val = Command(resume={"message": "approve"})
        else:
            print(f"[START] Initializing new pipeline run...")
            input_val = {
                "thread_id": thread_id,
                "problem_statement": problem or "Impact of AI on Healthcare 2026",
                "research_objectives": [],
                "research_questions": [],
                "keywords": [],
                "raw_papers": [],
                "screened_papers": [],
                "status": "initializing"
            }

        async for event in graph.astream(input_val, config=config):
            print(f"Event: {list(event.keys())}")

        updated_state = await graph.aget_state(config)
        print(f"Paused state next: {list(updated_state.next) if updated_state else 'END'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", type=str, default="")
    parser.add_argument("--resume", type=str, nargs="?", const="latest", default="")
    args = parser.parse_args()

    resume_id = None
    if args.resume:
        if args.resume != "latest":
            resume_id = args.resume
        elif THREAD_FILE.exists():
            resume_id = THREAD_FILE.read_text().strip()

    asyncio.run(run_pipeline(problem=args.problem, resume_thread_id=resume_id))
```

- [ ] **Step 2: Commit Task 5**

```powershell
git add research-bot/test_research_mode.py
git commit -m "feat: add resumable CLI test script test_research_mode.py"
```

---

### Task 6: End-to-End Verification & Demonstration (Acceptance Criteria)

**Verification Checklist:**
- [ ] **Acceptance a**: Start run, kill process mid-pipeline after synthesis node, restart, resume same thread_id, confirm continuation from exact paused node.
- [ ] **Acceptance b**: Show LLM cache hits in backend log (`[LLM CACHE HIT]`) on resumed run.
- [ ] **Acceptance c**: Reload browser page mid-run, confirm UI rehydrates state and restores correct checkpoint/paper.
- [ ] **Acceptance d**: Run full end-to-end pipeline with a *brand new, fresh problem statement* never used before, confirming all 20 sections populate and PDF exports.

- [ ] **Step 1: Execute acceptance tests and capture real output**
- [ ] **Step 2: Verify git status and commit log**
