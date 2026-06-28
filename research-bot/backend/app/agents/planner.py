# Planner agent
import sys
from pathlib import Path
# Add workspace root to sys.path so 'backend' is importable
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from langchain_core.prompts import ChatPromptTemplate
from backend.app.graph.state import ResearchState
from typing import List
from pydantic import BaseModel, Field
from backend.app.llm import llm

class ResearchPlan(BaseModel):
    sub_tasks: List[str] = Field(description="List of sub-tasks for the research plan")

def planner_node(state: ResearchState) -> dict:
    planner_llm = llm.with_structured_output(ResearchPlan, method="json_mode")
    prompt = ChatPromptTemplate([("system","You are a planner agent specialized in breaking down complex research queries into smaller tasks. You must return your response in JSON format with a single key 'sub_tasks' containing a list of strings representing the sub-tasks (at most 5). Keep each task description short and under 20 words. Each task should be independent and cover different aspects of the research query."),
    ("user", f"Create a research plan for {state['query']}")])
    messages = prompt.format_messages()
    result = planner_llm.invoke(messages)
    return {"plan": result.sub_tasks, "status":"awaiting_approval"}



if __name__ == "__main__":
    test_state = {
        "query": "Recent advances in room-temperature superconductivity in 2026",
        "plan": [],
        "plan_approved": False,
        "user_feedback": None,
        "status": "planning",
        "results": [],
        "final_answer": None,
        "citations": []
    }
    print("Testing planner_node...")
    output = planner_node(test_state)
    print("Output:", output)





