import sys
import uuid
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from langgraph.types import Command
from backend.app.graph.research_mode_builder import research_mode_graph
from backend.app.tools.pdf_generator import generate_paper_pdf

logger = logging.getLogger(__name__)

router = APIRouter()

# Active streaming tasks per thread_id
active_research_tasks: Dict[str, asyncio.Task] = {}


class ResearchModeStartRequest(BaseModel):
    problem_statement: str
    research_objectives: List[str] = []
    research_questions: List[str] = []


class ResearchModeApproveRequest(BaseModel):
    thread_id: str
    message: str = ""


class ResearchModeCancelRequest(BaseModel):
    thread_id: str


@router.post("/research-mode/start")
@router.post("/research/mode/start")
async def start_research_mode(request: ResearchModeStartRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "thread_id": thread_id,
        "mode": "research",
        "problem_statement": request.problem_statement,
        # Left empty on purpose: scope_definition_agent derives these from the
        # problem statement unless the author supplied them in the Advanced panel.
        "research_objectives": request.research_objectives or [],
        "research_questions": request.research_questions or [],
        "keywords": [],
        "raw_papers": [],
        "screened_papers": [],
        "status": "initializing"
    }

    try:
        # Run graph until first interrupt (Checkpoint 1)
        async for event in research_mode_graph.astream(initial_state, config=config):
            pass

        state = research_mode_graph.get_state(config)
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
async def approve_research_mode(request: ResearchModeApproveRequest):
    config = {"configurable": {"thread_id": request.thread_id}}

    async def event_generator():
        current_task = asyncio.current_task()
        active_research_tasks[request.thread_id] = current_task
        try:
            yield f"data: {json.dumps({'event': 'resume', 'thread_id': request.thread_id})}\n\n"
            await asyncio.sleep(0.01)

            async for event in research_mode_graph.astream_events(
                Command(resume={"message": request.message}),
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
                            "thread_id": request.thread_id
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                        await asyncio.sleep(0.01)

                # LLM token streaming (e.g., literature review, results, discussion)
                elif event_type == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    node_name = event.get("metadata", {}).get("langgraph_node")
                    if chunk and hasattr(chunk, "content") and chunk.content and node_name:
                        payload = {
                            "event": "token_stream",
                            "node": node_name,
                            "token": chunk.content
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                        await asyncio.sleep(0.001)

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
                        yield f"data: {json.dumps(payload)}\n\n"
                        await asyncio.sleep(0.01)

            # Retrieve state after stream pause / completion
            state = research_mode_graph.get_state(config)
            values = state.values or {}

            # Check if paused at next interrupt or finished
            is_completed = values.get("status") == "completed" or not state.next
            event_name = "completed" if is_completed else "checkpoint"

            final_payload = {
                "event": event_name,
                "thread_id": request.thread_id,
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
            yield f"data: {json.dumps(final_payload)}\n\n"

        except Exception as e:
            logger.error(f"SSE Error in Research Mode approve: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        finally:
            if active_research_tasks.get(request.thread_id) == current_task:
                active_research_tasks.pop(request.thread_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/research-mode/result/{thread_id}")
@router.get("/research/mode/result/{thread_id}")
async def get_research_mode_result(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = research_mode_graph.get_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Research Mode thread not found")
    return state.values


@router.post("/research-mode/export/{thread_id}")
@router.post("/research/mode/export/{thread_id}")
async def export_research_mode_pdf(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = research_mode_graph.get_state(config)
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
