# Task 2 Report: Lazy Async Graph Compiler and FastAPI Lifespan Checkpointer Wiring

**Status:** Completed  
**Timestamp:** 2026-08-09T20:06:30+05:30  
**Target Python Executable:** `.venv\Scripts\python.exe`  

---

## 1. Executive Summary

Task 2 of the implementation plan `docs/superpowers/plans/2026-08-09-durable-session-state-and-llm-cache.md` has been successfully implemented and verified. The graph builders (`research_mode_builder.py` and `builder.py`) now support lazy graph access and checkpointer injection (`set_checkpointer`), and FastAPI (`main.py`) manages an `AsyncSqliteSaver` instance via `@asynccontextmanager async def lifespan(app: FastAPI)` pointing to `RESEARCH_DB_PATH` (default `./data/research_state.db`).

---

## 2. File Changes

### 1. `research-bot/backend/app/graph/research_mode_builder.py`
- Removed static `research_mode_graph = builder.compile(checkpointer=MemorySaver())`.
- Added module-level state `_checkpointer = MemorySaver()` and `_compiled_graph = None`.
- Implemented `set_checkpointer(checkpointer)` to set active checkpointer and re-compile `_compiled_graph`.
- Implemented `get_research_mode_graph()` to return compiled graph (compiling lazily if `None`).
- Added module-level `__getattr__(name)` fallback for `research_mode_graph` for backwards compatibility.

### 2. `research-bot/backend/app/graph/builder.py`
- Removed static `research_graph = builder.compile(checkpointer=MemorySaver())`.
- Added module-level state `_checkpointer = MemorySaver()` and `_compiled_graph = None`.
- Implemented `set_checkpointer(checkpointer)` to set active checkpointer and re-compile `_compiled_graph`.
- Implemented `get_research_graph()` to return compiled graph (compiling lazily if `None`).
- Added module-level `__getattr__(name)` fallback for `research_graph` for backwards compatibility.

### 3. `research-bot/backend/app/main.py`
- Imported `asynccontextmanager` from `contextlib` and `AsyncSqliteSaver` from `langgraph.checkpoint.sqlite.aio`.
- Imported `set_checkpointer as set_rm_checkpointer` from `backend.app.graph.research_mode_builder`.
- Imported `set_checkpointer as set_ds_checkpointer` from `backend.app.graph.builder`.
- Implemented `@asynccontextmanager async def lifespan(app: FastAPI)`:
  - Reads `RESEARCH_DB_PATH` env var (default `./data/research_state.db`).
  - Auto-creates parent directory `Path(db_path).parent.mkdir(parents=True, exist_ok=True)`.
  - Initializes `AsyncSqliteSaver.from_conn_string(str(db_path))`.
  - Runs `await checkpointer.setup()`.
  - Registers checkpointer via `set_rm_checkpointer(checkpointer)` and `set_ds_checkpointer(checkpointer)`.
- Initialized FastAPI app with `lifespan=lifespan`: `app = FastAPI(title="AI Research Assistant Bot", lifespan=lifespan)`.

---

## 3. Verification & Testing

### Verification 1: SQLite Checkpointer & Research Mode Graph Compilation
```powershell
.\.venv\Scripts\python.exe -c "import sys, asyncio, os; from pathlib import Path; sys.path.insert(0, 'research-bot'); from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver; from backend.app.graph.research_mode_builder import set_checkpointer, get_research_mode_graph

async def test():
    Path('./data').mkdir(exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string('./data/test_state.db') as saver:
        await saver.setup()
        set_checkpointer(saver)
        graph = get_research_mode_graph()
        print('Graph compiled successfully:', graph is not None)

asyncio.run(test())"
```
**Output:** `Graph compiled successfully: True`

### Verification 2: SQLite Checkpointer & DeepSearch Graph Compilation
```powershell
.\.venv\Scripts\python.exe -c "import sys, asyncio, os; from pathlib import Path; sys.path.insert(0, 'research-bot'); from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver; from backend.app.graph.builder import set_checkpointer, get_research_graph

async def test():
    Path('./data').mkdir(exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string('./data/test_state.db') as saver:
        await saver.setup()
        set_checkpointer(saver)
        graph = get_research_graph()
        print('DeepSearch Graph compiled successfully:', graph is not None)

asyncio.run(test())"
```
**Output:** `DeepSearch Graph compiled successfully: True`

### Verification 3: Main App Lifespan Import & Initialization
```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'research-bot'); from backend.app.main import app; print('Main FastAPI app initialized with title:', app.title)"
```
**Output:** `Main FastAPI app initialized with title: AI Research Assistant Bot`

---

## 4. Git Commit Notice

Per task requirements, git changes were NOT committed automatically. The task report has been saved to `.superpowers/sdd/2026-08-09-durable-session-state-and-llm-cache/task-2-report.md`.
