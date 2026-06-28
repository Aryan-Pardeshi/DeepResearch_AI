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

#state = memory
def approval_interrupt(state: ResearchState):
    # If already approved, skip the interrupt
    if state.get("plan_approved"):
        return state
        
    # When resumed, user_response receives the value sent during resume.
    #i.e. the value passed in Command(resume={}) Dict
    user_response = interrupt("Waiting for human approval")
    
    approved = user_response.get("approved", False)
    feedback = user_response.get("feedback", "")
    
    if approved:
        return {
            "plan_approved": True,
            "status": "researching"
        }
    else:
        return {
        "plan_approved": False,
        "user_feedback": feedback,
        "status": "planning"
        }



builder = StateGraph(ResearchState)

#nodes
builder.add_node("planner", planner_node)
builder.add_node("approval", approval_interrupt)

#Connect nodes
builder.add_edge(START, "planner")
builder.add_edge("planner", "approval")
builder.add_edge("approval", END)


checkpointer = MemorySaver()

#build graph
research_graph = builder.compile(
    checkpointer=checkpointer
)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "test_thread_1"}}
    
    print("--- Running graph (Starting Planner) ---")
    # This will run until it hits the 'approval' node's interrupt
    for event in research_graph.stream(
        {"query": "Recent breakthroughs in Quantum Computing in 2026"},
        config=config
    ):
        print("Event:", event)
        
    # Inspect the state after interrupt
    state = research_graph.get_state(config)
    print("\n--- Paused State ---")
    print("Next step:", state.next)
    print("Current Plan:", state.values.get("plan"))
    
    # Resume the graph by passing the resume value wrapped in Command
    print("\n--- Resuming from Interrupt (Approving) ---")
    for event in research_graph.stream(Command(resume={"approved": True, "feedback": "Approved"}), config=config):
        print("Event:", event)
        
    # Check final state
    final_state = research_graph.get_state(config)
    print("\n--- Completed State ---")
    print("Next step:", final_state.next)
    print("Plan Approved:", final_state.values.get("plan_approved"))
    print("User Feedback:", final_state.values.get("user_feedback"))