from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.app.graph.builder import research_graph
import uuid
from pydantic import BaseModel
import json
import asyncio

from langgraph.types import Command

class ResearchStartRequest(BaseModel):
    query: str


class ResearchApproveRequest(BaseModel):
    thread_id: str
    message: str


router = APIRouter()

@router.post("/research/start")
async def run_research(request: ResearchStartRequest):
    id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": id}}
    
    # Run the graph stream. Since astream is an async generator, we consume it directly.
    # The graph will run until it hits the interrupt/pause state.
    async for event in research_graph.astream({"query": request.query}, config=config):
        pass
        
    # Reads the persisted snapshot from MemorySaver for that thread_id.
    state = research_graph.get_state(config)

    # Values from current state (not yet persisted)
    plan = state.values.get("plan")
    status = state.values.get("status")
    ps = state.values.get("ps")

    return {"thread_id": id, "ps": ps, "plan": plan, "status": status}

#SSE
@router.post("/research/approve")
async def approve_plan(request: ResearchApproveRequest):
    config = {"configurable": {"thread_id": request.thread_id}}

    async def event_generator():
        try:
            #for allowing frontend to know what is happening
            yield f"data: {json.dumps({'event': 'resume', 'thread_id': request.thread_id})}\n\n"
            #This is a workaround for SSE over HTTP
            await asyncio.sleep(0.01)
            
            researcher_count = 0
            #Stream the graph
            async for event in research_graph.astream(
                Command(resume={"message": request.message}),
                config=config,
                stream_mode="updates",
            ):
                for node_name, node_update in event.items():
                    #to filter garbage events like __start, __end etc
                    if node_name.startswith("__"):
                        continue
                    current_node_name = node_name
                    #to count researchers and give them names
                    if node_name == "researcher":
                        researcher_count += 1
                        current_node_name = f"researcher_{researcher_count}"
                    #prepare payload
                    payload = {
                        "event": "node_update",
                        "node": current_node_name,
                        "data": node_update,
                    }
                    #for giving data to frontend
                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(0.01)

            # Reads the state after resumption / planning execution loop
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
            yield f"data: {json.dumps(final_payload)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
