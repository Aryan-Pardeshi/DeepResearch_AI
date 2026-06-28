import sys
from pathlib import Path

# Add workspace root to sys.path so 'backend' is importable
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# LangGraph graph definition
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from backend.app.graph.state import ResearchState
from backend.app.agents.planner import planner_node
from backend.app.agents.aggregator import aggregator_node
from backend.app.agents.supervisor import dispatch_researchers
from backend.app.agents.researcher import researcher_node


# state = memory
def approval_interrupt(state: ResearchState):
    # If already approved, skip the interrupt
    if state.get("plan_approved"):
        return state

    # When resumed, user_response receives the value sent during resume.
    # i.e. the value passed in Command(resume={}) Dict
    user_response = interrupt("Waiting for human approval")

    approved = user_response.get("approved", False)
    feedback = user_response.get("feedback", "")

    if approved:
        return {"plan_approved": True, "status": "researching"}
    else:
        return {"plan_approved": False, "user_feedback": feedback, "status": "planning"}


builder = StateGraph(ResearchState)

# nodes
builder.add_node("planner", planner_node)
builder.add_node("approval", approval_interrupt)
builder.add_node("researcher", researcher_node)
builder.add_node("aggregator", aggregator_node)

def route_after_approval(state: ResearchState):
    """Fan out to one researcher per sub-task if approved, otherwise loop back to planner."""
    #if plan approved
    if state["plan_approved"]:
        return dispatch_researchers(state)  # returns List[Send("researcher", ...)]
    return "planner"

# Connect nodes
builder.add_edge(START, "planner")
builder.add_edge("planner", "approval")
#conditional node because if approved it goes to aggregator and if not approved it goes back to planner
# Langchain dosnt allow list[Send()] from normal nodes only allows state to be returned
builder.add_conditional_edges("approval", route_after_approval, ["researcher", "planner"])

builder.add_edge("researcher", "aggregator")
builder.add_edge("aggregator", END)


checkpointer = MemorySaver()

# build graph
research_graph = builder.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    import sys
    # Force UTF-8 output on Windows consoles
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    config = {"configurable": {"thread_id": "test_thread_1"}}

    print("--- Running graph (Starting Planner) ---")
    for event in research_graph.stream(
        {"query": "Recent breakthroughs in Quantum Computing in 2026"}, config=config
    ):
        print("Event:", event)

    # Inspect the state after interrupt
    state = research_graph.get_state(config)
    print("\n--- Paused State ---")
    print("Next step:", state.next)
    print("Current Plan:", state.values.get("plan"))

    # Resume the graph by passing the resume value wrapped in Command
    print("\n--- Resuming from Interrupt (Approving) ---")
    for event in research_graph.stream(
        Command(resume={"approved": True, "feedback": "Approved"}), config=config
    ):
        print("Event:", event)

    # Check final state
    final_state = research_graph.get_state(config)
    print("\n--- Completed State ---")
    print("Next step:", final_state.next)
    print("Plan Approved:", final_state.values.get("plan_approved"))
    print("Final Answer (preview):", str(final_state.values.get("final_answer", ""))[:300])