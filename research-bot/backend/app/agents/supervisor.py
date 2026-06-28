# Supervisor + Send() logic
from langgraph.types import Send
from backend.app.graph.state import ResearchState


def dispatch_researchers(state: ResearchState):
    
    return [Send("researcher", {**state, "query": task}) for task in state["plan"][:5]]
    