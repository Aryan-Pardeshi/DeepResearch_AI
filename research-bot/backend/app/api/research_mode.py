import sys
import uuid
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Set

from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from langgraph.types import Command
from backend.app.graph.research_mode_builder import get_research_mode_graph
from backend.app.tools.pdf_generator import generate_paper_pdf

logger = logging.getLogger(__name__)

router = APIRouter()

# Active streaming tasks per thread_id
active_research_tasks: Dict[str, asyncio.Task] = {}

# Per-thread event buffer for SSE reconnects
# Structure: {thread_id: {"events": [], "task": task, "updated_at": timestamp, "completed": bool, "listeners": set()}}
thread_buffers: Dict[str, Dict[str, Any]] = {}

BUFFER_TTL_SECONDS = 3600  # 1 hour TTL for inactive thread buffers


def prune_old_buffers():
    now = time.time()
    to_delete = []
    for tid, buf in list(thread_buffers.items()):
        task = buf.get("task")
        if (task is None or task.done()) and (now - buf.get("updated_at", 0) > BUFFER_TTL_SECONDS):
            to_delete.append(tid)
    for tid in to_delete:
        thread_buffers.pop(tid, None)
        active_research_tasks.pop(tid, None)


class ResearchModeStartRequest(BaseModel):
    problem_statement: str
    research_objectives: List[str] = []
    research_questions: List[str] = []


class ResearchModeApproveRequest(BaseModel):
    thread_id: str
    message: str = ""
    from_seq: Optional[int] = None


class ResearchModeCancelRequest(BaseModel):
    thread_id: str


async def _broadcast_event(thread_id: str, payload: Dict[str, Any], is_node_event: bool = True):
    buf = thread_buffers.get(thread_id)
    if not buf:
        return
    buf["updated_at"] = time.time()
    if is_node_event:
        seq = len(buf["events"]) + 1
        payload["seq"] = seq
        buf["events"].append(payload)

    # Broadcast copy to active listeners
    listeners = list(buf.get("listeners", set()))
    for q in listeners:
        try:
            q.put_nowait(payload)
        except Exception:
            pass


async def _execute_research_graph(thread_id: str, message: str):
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_research_mode_graph()
    buf = thread_buffers.get(thread_id)
    if buf:
        buf["completed"] = False

    try:
        resume_payload = {
            "event": "resume",
            "thread_id": thread_id
        }
        await _broadcast_event(thread_id, resume_payload, is_node_event=True)

        async for event in graph.astream_events(
            Command(resume={"message": message}),
            config=config,
            version="v2",
        ):
            event_type = event["event"]

            # Node execution starts
            if event_type == "on_chain_start":
                node_name = event.get("metadata", {}).get("langgraph_node")
                if node_name and event.get("name") == node_name and not node_name.startswith("__"):
                    payload = {
                        "event": "node_start",
                        "node": node_name,
                        "thread_id": thread_id
                    }
                    await _broadcast_event(thread_id, payload, is_node_event=True)

            # LLM token streaming (live only, NOT stored in buffer)
            elif event_type == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                node_name = event.get("metadata", {}).get("langgraph_node")
                if chunk and hasattr(chunk, "content") and chunk.content and node_name:
                    payload = {
                        "event": "token_stream",
                        "node": node_name,
                        "token": chunk.content
                    }
                    await _broadcast_event(thread_id, payload, is_node_event=False)

            # Node completion updates
            elif event_type == "on_chain_end":
                node_name = event.get("metadata", {}).get("langgraph_node")
                if node_name and event.get("name") == node_name and not node_name.startswith("__"):
                    node_output = event["data"].get("output")
                    payload = {
                        "event": "node_update",
                        "node": node_name,
                        "data": node_output
                    }
                    await _broadcast_event(thread_id, payload, is_node_event=True)

        # Retrieve state after stream pause / completion
        state = await graph.aget_state(config)
        values = state.values or {} if state else {}

        # Check if paused at next interrupt or finished
        is_completed = values.get("status") == "completed" or not (state and state.next)
        event_name = "completed" if is_completed else "checkpoint"

        final_payload = {
            "event": event_name,
            "thread_id": thread_id,
            "status": values.get("status"),
            "hitl_checkpoint": values.get("hitl_checkpoint"),
            "state": {
                "problem_statement": values.get("problem_statement"),
                "research_objectives": values.get("research_objectives"),
                "research_questions": values.get("research_questions"),
                "keywords": values.get("keywords"),
                "raw_papers_count": len(values.get("raw_papers", [])),
                "screened_papers_count": len(values.get("screened_papers", [])),
                "literature_review": values.get("literature_review"),
                "research_gap": values.get("research_gap"),
                "conceptual_framework": values.get("conceptual_framework"),
                "hypotheses": values.get("hypotheses"),
                "research_design": values.get("research_design"),
                "data_collection_plan": values.get("data_collection_plan"),
                "data_analysis_plan": values.get("data_analysis_plan"),
                "results": values.get("results"),
                "discussion": values.get("discussion"),
                "implications": values.get("implications"),
                "limitations": values.get("limitations"),
                "conclusion": values.get("conclusion"),
                "future_scope": values.get("future_scope"),
                "references": values.get("references"),
                "appendices": values.get("appendices"),
                "introduction": values.get("introduction"),
                "abstract": values.get("abstract"),
                "title": values.get("title")
            }
        }
        await _broadcast_event(thread_id, final_payload, is_node_event=True)
        if buf:
            buf["completed"] = True

    except Exception as e:
        logger.error(f"SSE Error in Research Mode approve: {e}", exc_info=True)
        error_payload = {
            "event": "error",
            "message": str(e)
        }
        await _broadcast_event(thread_id, error_payload, is_node_event=True)
        if buf:
            buf["completed"] = True
    finally:
        current_task = asyncio.current_task()
        if active_research_tasks.get(thread_id) == current_task:
            active_research_tasks.pop(thread_id, None)
        if buf:
            listeners = list(buf.get("listeners", set()))
            for q in listeners:
                try:
                    q.put_nowait(None)
                except Exception:
                    pass


@router.post("/research-mode/start")
@router.post("/research/mode/start")
async def start_research_mode(request: ResearchModeStartRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_research_mode_graph()

    initial_state = {
        "thread_id": thread_id,
        "mode": "research",
        "problem_statement": request.problem_statement,
        "research_objectives": request.research_objectives or [],
        "research_questions": request.research_questions or [],
        "keywords": [],
        "raw_papers": [],
        "screened_papers": [],
        "status": "initializing"
    }

    try:
        # Run graph until first interrupt (Checkpoint 1)
        async for event in graph.astream(initial_state, config=config):
            pass

        state = await graph.aget_state(config)
        values = state.values or {}

        return {
            "thread_id": thread_id,
            "problem_statement": values.get("problem_statement"),
            "research_objectives": values.get("research_objectives"),
            "research_questions": values.get("research_questions"),
            "keywords": values.get("keywords"),
            "hitl_checkpoint": values.get("hitl_checkpoint", "checkpoint_1"),
            "status": values.get("status", "awaiting_approval"),
            "error": values.get("error")
        }
    except Exception as e:
        logger.error(f"Error starting Research Mode: {e}", exc_info=True)
        return {
            "thread_id": thread_id,
            "status": "error",
            "error": f"Failed to start Research Mode: {str(e)}"
        }


@router.post("/research-mode/approve")
@router.post("/research/mode/approve")
async def approve_research_mode(
    request: ResearchModeApproveRequest,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID")
):
    prune_old_buffers()

    from_seq = request.from_seq
    if from_seq is None and last_event_id is not None:
        try:
            from_seq = int(last_event_id)
        except ValueError:
            pass

    thread_id = request.thread_id
    if thread_id not in thread_buffers:
        thread_buffers[thread_id] = {
            "events": [],
            "task": None,
            "updated_at": time.time(),
            "completed": False,
            "listeners": set()
        }

    buf = thread_buffers[thread_id]

    task = buf.get("task")
    need_new_task = False
    if task is None or task.done():
        events_count = len(buf.get("events", []))
        if not buf.get("completed") or from_seq is None or from_seq >= events_count:
            need_new_task = True

    if need_new_task:
        new_task = asyncio.create_task(_execute_research_graph(thread_id, request.message))
        buf["task"] = new_task
        active_research_tasks[thread_id] = new_task

    async def event_generator():
        listener_queue = asyncio.Queue()
        buf["listeners"].add(listener_queue)

        try:
            # Replay missed buffered events if from_seq is present
            if from_seq is not None:
                missed = [e for e in buf.get("events", []) if e.get("seq", 0) > from_seq]
                for evt in missed:
                    seq_str = f"id: {evt['seq']}\n" if "seq" in evt else ""
                    yield f"{seq_str}data: {json.dumps(evt)}\n\n"
                    await asyncio.sleep(0.001)

            # Stream live events
            task_ref = buf.get("task")
            while True:
                try:
                    evt = await asyncio.wait_for(listener_queue.get(), timeout=0.5)
                    if evt is None:
                        break
                    seq_str = f"id: {evt['seq']}\n" if "seq" in evt else ""
                    yield f"{seq_str}data: {json.dumps(evt)}\n\n"
                    await asyncio.sleep(0.001)
                except asyncio.TimeoutError:
                    if (task_ref is None or task_ref.done()) and listener_queue.empty():
                        break

        finally:
            buf["listeners"].discard(listener_queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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


@router.post("/research-mode/export/{thread_id}")
@router.post("/research/mode/export/{thread_id}")
async def export_research_mode_pdf(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_research_mode_graph()
    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Research Mode thread not found")

    temp_dir = Path(__file__).resolve().parent.parent / "static" / "exports"
    temp_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = temp_dir / f"paper_{thread_id}.pdf"

    try:
        generate_paper_pdf(state.values, str(pdf_path))
        return FileResponse(
            path=str(pdf_path),
            filename=f"research_paper_{thread_id[:8]}.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
