from fastapi import FastAPI
from backend.app.graph.builder import research_graph
import uuid
from pydantic import BaseModel

class ResearchStartRequest(BaseModel):
    query: str


app = FastAPI()

@app.post("/research/start")
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

    return {
    "thread_id": id,
    "plan": plan,
    "status": status
}
