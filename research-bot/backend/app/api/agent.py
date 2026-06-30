from fastapi import APIRouter
from backend.app.graph.builder import research_graph
import uuid
from pydantic import BaseModel

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
    async for event in research_graph.astream(
        {"query": request.query}, config=config
    ):
        pass
    
    # Reads the persisted snapshot from MemorySaver for that thread_id.
    state = research_graph.get_state(config)
    
    # Values from current state (not yet persisted)
    plan = state.values.get("plan")
    status = state.values.get("status")
    ps = state.values.get("ps")

    return {
        "thread_id": id,
        "ps": ps,
        "plan": plan,
        "status": status
    }


@router.post("/research/approve")
async def approve_plan(request: ResearchApproveRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    
    #resume the graph that was paused due to interrupt()
    #it also updates the graph values 
    async for chunk,event in research_graph.astream(
        Command(resume={"message": request.message}), config=config,
        stream_mode=["updates"]
    ):
        if chunk["type"] == "updates":
            for aggregator_node, state in chunk["data"].items():
                print(f"Node {aggregator_node} updated: {state}")
        # elif chunk["type"] == "custom":
        #     print(f"Status: {chunk['data']['status']}")
    
    # Reads the state after resumption / planning execution loop
    state = research_graph.get_state(config)
    
    return {
        "thread_id": request.thread_id,
        "plan_approved": state.values.get("plan_approved"),
        "status": state.values.get("status"),
        "ps": state.values.get("ps"),
        "plan": state.values.get("plan")
    }

