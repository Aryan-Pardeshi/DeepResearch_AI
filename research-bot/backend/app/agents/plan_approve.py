#Plan Approval Agent

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
from backend.app.llm import llm1
from langgraph.types import interrupt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = ("Treat Problem statement based changes and plan based changes as same. Based on the User Response you must decide if the plan has to be approved or revised. You must respond in JSON format, setting the key 'plan_approved' to true if approved, or false if rejected/revisions are requested.")

class PlanState(BaseModel):
    plan_approved: bool = Field(description="Whether the plan is approved or not")

def plan_approval(state: ResearchState)->dict:
    # Pause execution to wait for user approval/feedback message
    user_response = interrupt("Waiting for plan approval/feedback")
    
    # Extract the message from the resume payload (could be dict or string)
    feedback = user_response.get("message", "") if isinstance(user_response, dict) else str(user_response)
    
    # Classify the feedback using structured output LLM (with json_mode for DeepSeek compatibility)
    approval_llm = llm1.with_structured_output(PlanState, method="json_mode")
    
    user_content = f"User feedback: {feedback}\nPrevious ps: {state.get('ps', '')}\nPrevious plan: {state.get('plan', [])}"

    prompt = ChatPromptTemplate([("system", SYSTEM_PROMPT), ("user", user_content)])
    messages = prompt.format_messages()
    result = approval_llm.invoke(messages)
    
    logger.info(f"Plan approval result: {result.plan_approved}")
    logger.info(f"User feedback: {feedback}")
    
    status = "researching" if result.plan_approved else "planning"
    return {"plan_approved": result.plan_approved, "user_feedback": feedback, "status": status}