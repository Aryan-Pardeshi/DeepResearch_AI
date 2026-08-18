import asyncio
import logging
import uuid
from backend.app.graph.research_mode_builder import get_research_mode_graph
from backend.app.agents.research_mode.agents import get_llm_for, ResearchModeState

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

async def test_model_overrides():
    state: ResearchModeState = {
        "thread_id": str(uuid.uuid4()),
        "problem_statement": "Evaluating LLM performance under constrained memory budgets.",
        "model_overrides": {
            "planner": "deepseek-chat",
            "researcher": "gpt-4o-mini",
            "aggregator": "deepseek-reasoner"
        }
    }

    print("\n--- Testing get_llm_for with per-role overrides ---")
    llm_p = get_llm_for(state, role="planner")
    llm_r = get_llm_for(state, role="researcher")
    llm_a = get_llm_for(state, role="aggregator")

    print("\n--- Model Resolution Results ---")
    print(f"Role 'planner'    -> Resolved Model: {llm_p.model_name}")
    print(f"Role 'researcher' -> Resolved Model: {llm_r.model_name}")
    print(f"Role 'aggregator' -> Resolved Model: {llm_a.model_name}")

    assert llm_p.model_name == "deepseek-chat"
    assert llm_r.model_name == "gpt-4o-mini"
    assert llm_a.model_name == "deepseek-reasoner"
    print("\nPASS: Three distinct model overrides resolved successfully in one state payload!")

if __name__ == "__main__":
    asyncio.run(test_model_overrides())
