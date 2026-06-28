# Planner agent
import sys
from pathlib import Path
# Add workspace root to sys.path so 'backend' is importable
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import logging
from langchain_core.prompts import ChatPromptTemplate
from backend.app.graph.state import ResearchState
from typing import List
from pydantic import BaseModel, Field
from backend.app.llm import llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a strategic research planner. Break down the given query into at most 5 independent sub-tasks. "
    "Each sub-task must:\n"
    "- Cover a distinct aspect of the query\n"
    "- Be self-contained (a researcher can work on it without the others)\n"
    "- Be concise: under 20 words\n"
    "If you are given user feedback on a previous plan, revise the plan accordingly.\n"
    "Respond in JSON with key 'sub_tasks' as a list of strings."
)

class ResearchPlan(BaseModel):
    sub_tasks: List[str] = Field(
        description="Ordered list of independent research sub-tasks",
        min_length=1,
        max_length=5
    )

def planner_node(state: ResearchState) -> dict:
    planner_llm = llm.with_structured_output(ResearchPlan, method="json_mode")

    user_content = f"Create a research plan for: {state['query']}"
    if state.get("user_feedback"):
        user_content += f"\n\nUser feedback on previous plan: {state['user_feedback']}\nPrevious plan: {state.get('plan', [])}"

    prompt = ChatPromptTemplate([
        ("system", SYSTEM_PROMPT),
        ("user", user_content)
    ])
    messages = prompt.format_messages()
    result = planner_llm.invoke(messages)

    logger.info(f"Planner generated {len(result.sub_tasks)} sub-tasks for query: {state['query']}")
    return {"plan": result.sub_tasks, "status": "awaiting_approval"}



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