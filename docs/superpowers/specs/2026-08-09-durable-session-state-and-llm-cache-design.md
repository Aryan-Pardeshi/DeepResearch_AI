# Technical Design Specification: Durable Session State, LLM Response Cache, and SSE Reconnect

## Overview & Goals
In Research Mode, a single pipeline run executes 20+ agent nodes and 4 HITL checkpoints, taking several minutes and invoking multiple LLM calls. If a network drop or process crash occurs, in-memory state is lost, forcing complete re-execution and re-billing of LLM calls.

This specification addresses these issues by introducing:
1. **SQLite-Backed Graph Checkpointer**: Replaces `MemorySaver` with `AsyncSqliteSaver` from `langgraph-checkpoint-sqlite.aio`, persisting graph state to SQLite so threads resume at the exact node where they stopped.
2. **Persistent LLM Response Cache**: Enables `LoggingSQLiteCache` (subclass of `SQLiteCache` from `langchain_community.cache`) in `llm.py` with explicit `[LLM CACHE HIT]` log logging.
3. **Resumable E2E CLI Test Script**: Updates test tooling to persist `thread_id` and accept `--resume <thread_id>` flag.
4. **Frontend Session Persistence & Resume**: Stores `thread_id` and `state.rm` in `localStorage`, extended `GET /research-mode/result/{thread_id}` endpoint with status/next metadata, and auto-rehydrates the UI with a "Resume Session" banner.
5. **SSE Reconnect with Per-Thread Event Buffer**: Decouples graph execution from HTTP stream disconnects, buffering node-level events with sequence IDs so reconnecting clients replay missed events without duplicating graph execution or losing state.

---

## 1. Durable SQLite Checkpointer & Lazy Graph Access

### Architecture
- **Package**: `langgraph-checkpoint-sqlite` added to `research-bot/requirements.txt`.
- **Database Path**: Configurable via `RESEARCH_DB_PATH` (default `./data/research_state.db`). Auto-creates parent directories.
- **Lifespan Connection & Lazy Access**:
  - `AsyncSqliteSaver.from_conn_string(db_path)` is an async context manager managed during FastAPI startup/shutdown in `main.py`'s `lifespan`.
  - In `research_mode_builder.py`, `builder` state graph is exported uncompiled or compiled lazily via `async def get_research_mode_graph()`.
  - `main.py` initializes the connection on startup and sets the active saver instance into `research_mode_builder`.
  - `research_mode.py` uses `await get_research_mode_graph()` lazily rather than importing a module-level compiled instance.
- **Async State Retrieval**:
  - All calls to `research_mode_graph.get_state(config)` in `research_mode.py` are converted to `await graph.aget_state(config)`.

---

## 2. Persistent LLM Response Cache & Verification

### Architecture
- **Cache Engine**: `LoggingSQLiteCache` extending `langchain_community.cache.SQLiteCache`.
- **Location**: `research-bot/backend/app/llm.py`.
- **Database Path**: `LLM_CACHE_PATH` (default `./data/llm_cache.db`).
- **Hit Verification**:
  ```python
  class LoggingSQLiteCache(SQLiteCache):
      def lookup(self, prompt: str, llm_string: str):
          res = super().lookup(prompt, llm_string)
          if res:
              logger.info(f"[LLM CACHE HIT] Prompt prefix: {prompt[:50]!r}")
          else:
              logger.info(f"[LLM CACHE MISS] Prompt prefix: {prompt[:50]!r}")
          return res
  ```
- Wired at startup via `set_llm_cache(LoggingSQLiteCache(database_path=cache_path))`.

---

## 3. SSE Reconnect Engine with Per-Thread Event Buffer

### Architecture
- **Background Execution**: When `/research-mode/approve` is called, a background task executes the graph run if not already active.
- **Event Buffer**:
  - Per-thread append-only list `thread_buffers[thread_id] = {"events": [], "task": task, "updated_at": timestamp}`.
  - Node-level events (`node_start`, `node_update`, `checkpoint`, `completed`, `error`, `resume`) are assigned an incrementing sequence integer `seq` and appended to `events`.
  - `token_stream` events are streamed live to active connections but **NEVER** stored in the persistent buffer to preserve memory.
- **Reconnection Cursor**:
  - SSE client passes `Last-Event-ID` header or `from_seq` parameter in `/research-mode/approve`.
  - Upon connection, the SSE stream replays buffered events with `seq > from_seq`, then continues live.
- **Task Cleanup & Reconcilation**:
  - Integrates directly with `active_research_tasks`.
  - Upon completion or error, buffers and tasks are marked with TTL (1 hour) and cleaned up.

---

## 4. Endpoint Extension & Frontend Session Resume

### Backend API Updates (`research_mode.py`)
- `GET /research-mode/result/{thread_id}`:
  - Fetches state via `await graph.aget_state(config)`.
  - If state is missing or empty `values`, returns `HTTPException(404, "Research Mode thread not found")`.
  - Returns extended payload:
    ```json
    {
      "values": { ... },
      "next": state.next,
      "is_checkpoint": bool(state.next),
      "is_completed": not bool(state.next) and values.get("status") == "completed",
      "hitl_checkpoint": values.get("hitl_checkpoint"),
      "status": values.get("status")
    }
    ```

### Frontend Updates (`app.js`)
- `localStorage` key `'rm_session'` holds `{ threadId, rmState, lastSeq }`.
- Saved on `node_update`, `checkpoint`, `completed`, and start responses.
- On page load (`DOMContentLoaded`):
  - Calls `GET /research-mode/result/{thread_id}`.
  - On 404: clears `localStorage` session.
  - On 200: rehydrates UI, shows "Resume Session" banner, restores pipeline progress grid and appropriate HITL form or PDF export view.
  - Cleared on "New Research" button click.

---

## 5. CLI Resumable Test Script (`research-bot/test_research_mode.py`)

- End-to-end test runner for Research Mode.
- Persists `thread_id` to `./data/latest_thread_id.txt`.
- Flag `--resume [thread_id]`:
  - Reattaches to existing `thread_id`.
  - Queries `await graph.aget_state(config)`.
  - Logs resumed node/stage.
  - Continues graph execution using `Command(resume=...)`.

---

## 6. Housekeeping & DeepSearch Mode Assessment

- **Dependencies**: Add `langgraph-checkpoint-sqlite` to `research-bot/requirements.txt`.
- **Git Ignore**: Add `data/*.db` and `data/` to `.gitignore`.
- **Environment Variables**: `RESEARCH_DB_PATH` and `LLM_CACHE_PATH` for container volume mounts.
- **DeepSearch (`builder.py`) Assessment**: `builder.py` also uses `MemorySaver()`. To maintain consistency across the codebase, we will apply the same lazy async checkpointer pattern to `builder.py` so DeepSearch mode also benefits from SQLite persistence.
