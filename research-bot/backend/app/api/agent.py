from typing import List, Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.app.graph.builder import research_graph
import uuid
from pydantic import BaseModel
import json
import asyncio

from langgraph.types import Command

class ResearchStartRequest(BaseModel):
    query: str
    search_topic: List[Literal["all", "news", "academic", "finance", "patent"]] = ["all"]


class ResearchApproveRequest(BaseModel):
    thread_id: str
    message: str


router = APIRouter()

@router.post("/research/start")
async def run_research(request: ResearchStartRequest):
    id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": id}}

    try:
        # Run the graph stream. Since astream is an async generator, we consume it directly.
        # The graph will run until it hits the interrupt/pause state.
        async for event in research_graph.astream(
            {"query": request.query, "search_topic": request.search_topic}, config=config
        ):
            pass

        # Reads the persisted snapshot from MemorySaver for that thread_id.
        state = research_graph.get_state(config)

        # Values from current state (not yet persisted)
        plan = state.values.get("plan")
        status = state.values.get("status")
        ps = state.values.get("ps")
        error = state.values.get("error")

        return {"thread_id": id, "ps": ps, "plan": plan, "status": status, "error": error}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error during run_research: {e}", exc_info=True)
        return {"thread_id": id, "ps": None, "plan": None, "status": "error", "error": f"Failed to start research: {str(e)}"}


# SSE
@router.post("/research/approve")
async def approve_plan(request: ResearchApproveRequest):
    config = {"configurable": {"thread_id": request.thread_id}}

    async def event_generator():
        try:
            # 1. Notify the frontend immediately that we are resuming graph execution for this thread
            yield f"data: {json.dumps({'event': 'resume', 'thread_id': request.thread_id})}\n\n"
            # This is a workaround for SSE over HTTP
            await asyncio.sleep(0.01)
            
            researcher_tasks = {}
            researcher_count = 0
            
            # 2. # Stream the graph events using the astream_events engine
            #For aggrigator node streaming
            # We use `astream_events(version="v2")` to capture both LLM token streams and node completions.
            async for event in research_graph.astream_events(
                Command(resume={"message": request.message}),
                config=config,
                version="v2",
            ):
                event_type = event["event"]
                
                # 0. Capture when any node starts running
                if event_type == "on_chain_start":
                    node_name = event.get("metadata", {}).get("langgraph_node")
                    if node_name and event.get("name") == node_name and not node_name.startswith("__"):
                        current_node_name = node_name
                        # If it is a researcher node, assign it a number
                        if node_name == "researcher":
                            query = event["data"].get("input", {}).get("query")
                            if query not in researcher_tasks:
                                researcher_count += 1
                                researcher_tasks[query] = f"researcher_{researcher_count}"
                            current_node_name = researcher_tasks[query]
                            
                        payload = {
                            "event": "node_start",
                            "node": current_node_name,
                        }
                        if node_name == "researcher":
                            payload["task"] = event["data"].get("input", {}).get("query")
                        yield f"data: {json.dumps(payload)}\n\n"
                        await asyncio.sleep(0.01)
                
                # Stream individual LLM tokens 
                elif event_type == "on_chat_model_stream":
                    metadata = event.get("metadata", {})
                    
                    if metadata.get("langgraph_node") == "aggregator":
                        chunk = event["data"].get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            payload = {
                                "event": "aggregator_token",
                                "token": chunk.content,
                            }
                            yield f"data: {json.dumps(payload)}\n\n"
                            # Small sleep to prevent network congestion
                            await asyncio.sleep(0.001)
                            
                # Capture node completion updates 
                elif event_type == "on_chain_end":
                    node_name = event.get("metadata", {}).get("langgraph_node")
                    # In v2, the top-level node completion matches the node's name in the event
                    if node_name and event.get("name") == node_name:
                        # Skip LangGraph's internal/helper nodes (which start with double underscores)
                        if node_name.startswith("__"):
                            continue
                        
                        current_node_name = node_name
                        
                        if node_name == "researcher":
                            query = event["data"].get("input", {}).get("query")
                            if query in researcher_tasks:
                                current_node_name = researcher_tasks[query]
                            else:
                                researcher_count += 1
                                researcher_tasks[query] = f"researcher_{researcher_count}"
                                current_node_name = researcher_tasks[query]
                        
                        node_output = event["data"].get("output")
                        payload = {
                            "event": "node_update",
                            "node": current_node_name,
                            "data": node_output,
                        }
                        # Attach the matching sub-task query to the end event
                        if node_name == "researcher":
                            payload["task"] = event["data"].get("input", {}).get("query")
                            
                        yield f"data: {json.dumps(payload)}\n\n"
                        await asyncio.sleep(0.01)

            # 3. Graph execution is finished. Retrieve the final state snapshot to send the final report/citations.
            state = research_graph.get_state(config)

            final_payload = {
                "event": (
                    "completed"
                    if state.values.get("status") == "completed"
                    else "awaiting_approval"
                ),
                "thread_id": request.thread_id,
                "plan_approved": state.values.get("plan_approved"),
                "status": state.values.get("status"),
                "ps": state.values.get("ps"),
                "plan": state.values.get("plan"),
                "final_answer": state.values.get("final_answer"),
                "citations": state.values.get("citations"),
            }
            # Send the complete final state payload to mark completion
            yield f"data: {json.dumps(final_payload)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/research/result/{thread_id}")
async def get_result(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = research_graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {
        "ps": state.values.get("ps"),
        "final_answer": state.values.get("final_answer"),
        "citations": state.values.get("citations"),
        "status": state.values.get("status"),
    }
