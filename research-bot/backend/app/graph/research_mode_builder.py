import sys
import logging
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from backend.app.graph.research_mode_state import ResearchModeState
from backend.app.agents.research_mode.agents import (
    keyword_extractor_agent,
    paper_fetcher_agent,
    paper_screener_agent,
    literature_review_agent,
    gap_analysis_agent,
    framework_agent,
    hypotheses_agent,
    methodology_agent,
    results_agent,
    discussion_agent,
    implications_agent,
    limitations_agent,
    conclusion_agent,
    future_scope_agent,
    references_agent,
    introduction_agent,
    abstract_agent,
    title_agent,
)
from backend.app.llm import get_llm

logger = logging.getLogger(__name__)


# Checkpoint wrapper nodes with HITL interrupt

async def checkpoint_1_node(state: ResearchModeState) -> dict:
    """Checkpoint 1: Review Problem Statement, Objectives, RQs, Keywords."""
    logger.info("Executing Checkpoint 1 HITL interrupt...")
    user_input = interrupt({
        "checkpoint": "checkpoint_1",
        "message": "Review Problem Statement, Objectives, and Keywords before paper fetching.",
        "keywords": state.get("keywords", []),
        "problem_statement": state.get("problem_statement", ""),
        "research_objectives": state.get("research_objectives", []),
        "research_questions": state.get("research_questions", [])
    })

    message = user_input.get("message", "") if isinstance(user_input, dict) else str(user_input)
    
    if message and message.strip().lower() not in ["approve", "approved", "ok", "yes", "looks good", "continue"]:
        logger.info(f"Checkpoint 1 revision requested: {message}")
        llm = get_llm(role="planner")
        prompt = f"""Original Problem Statement: {state.get('problem_statement')}
Original Objectives: {state.get('research_objectives')}
Original Keywords: {state.get('keywords')}

User Revision Request: {message}

Update the keywords and objectives based on user feedback.
Return JSON with keys: "keywords" (list of strings), "research_objectives" (list of strings)."""
        try:
            res = await llm.ainvoke(prompt)
            import json
            raw = res.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            revised = json.loads(raw)
            return {
                "keywords": revised.get("keywords", state.get("keywords")),
                "research_objectives": revised.get("research_objectives", state.get("research_objectives")),
                "user_feedback": message,
                "hitl_checkpoint": "checkpoint_1_approved",
                "status": "fetching_papers"
            }
        except Exception as e:
            logger.warning(f"Error processing Checkpoint 1 feedback: {e}")

    return {
        "hitl_checkpoint": "checkpoint_1_approved",
        "status": "fetching_papers"
    }


async def checkpoint_2_node(state: ResearchModeState) -> dict:
    """Checkpoint 2: Review Literature Review, Gap, and Conceptual Framework."""
    logger.info("Executing Checkpoint 2 HITL interrupt...")
    user_input = interrupt({
        "checkpoint": "checkpoint_2",
        "message": "Review Literature Review, Research Gap, and Conceptual Framework before generating hypotheses.",
        "literature_review": state.get("literature_review", ""),
        "research_gap": state.get("research_gap", ""),
        "conceptual_framework": state.get("conceptual_framework", "")
    })

    message = user_input.get("message", "") if isinstance(user_input, dict) else str(user_input)
    
    if message and message.strip().lower() not in ["approve", "approved", "ok", "yes", "looks good", "continue"]:
        logger.info(f"Checkpoint 2 revision requested: {message}")
        llm = get_llm(role="planner")
        prompt = f"""Original Conceptual Framework: {state.get('conceptual_framework')}
Original Research Gap: {state.get('research_gap')}

User Revision Request: {message}

Revise the Conceptual Framework based on user feedback.
Return JSON with keys: "conceptual_framework" (string), "research_gap" (string)."""
        try:
            res = await llm.ainvoke(prompt)
            import json
            raw = res.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            revised = json.loads(raw)
            return {
                "conceptual_framework": revised.get("conceptual_framework", state.get("conceptual_framework")),
                "research_gap": revised.get("research_gap", state.get("research_gap")),
                "user_feedback": message,
                "hitl_checkpoint": "checkpoint_2_approved"
            }
        except Exception as e:
            logger.warning(f"Error processing Checkpoint 2 feedback: {e}")

    return {"hitl_checkpoint": "checkpoint_2_approved"}


async def checkpoint_3_node(state: ResearchModeState) -> dict:
    """Checkpoint 3: Review / Edit Hypotheses."""
    logger.info("Executing Checkpoint 3 HITL interrupt...")
    user_input = interrupt({
        "checkpoint": "checkpoint_3",
        "message": "Review and edit proposed Hypotheses before methodology formulation.",
        "hypotheses": state.get("hypotheses", [])
    })

    message = user_input.get("message", "") if isinstance(user_input, dict) else str(user_input)
    
    if message and message.strip().lower() not in ["approve", "approved", "ok", "yes", "looks good", "continue"]:
        logger.info(f"Checkpoint 3 revision requested: {message}")
        llm = get_llm(role="planner")
        prompt = f"""Original Hypotheses: {state.get('hypotheses')}

User Revision Request: {message}

Revise or refine the hypotheses list.
Return ONLY a JSON array of hypothesis strings."""
        try:
            res = await llm.ainvoke(prompt)
            import json
            raw = res.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            revised = json.loads(raw)
            if isinstance(revised, list):
                return {
                    "hypotheses": revised,
                    "user_feedback": message,
                    "hitl_checkpoint": "checkpoint_3_approved"
                }
        except Exception as e:
            logger.warning(f"Error processing Checkpoint 3 feedback: {e}")

    return {"hitl_checkpoint": "checkpoint_3_approved"}


async def checkpoint_4_node(state: ResearchModeState) -> dict:
    """Checkpoint 4: Review Methodology."""
    logger.info("Executing Checkpoint 4 HITL interrupt...")
    user_input = interrupt({
        "checkpoint": "checkpoint_4",
        "message": "Review Research Design and Methodology before running synthesis.",
        "research_design": state.get("research_design", ""),
        "data_collection_plan": state.get("data_collection_plan", ""),
        "data_analysis_plan": state.get("data_analysis_plan", "")
    })

    message = user_input.get("message", "") if isinstance(user_input, dict) else str(user_input)
    
    if message and message.strip().lower() not in ["approve", "approved", "ok", "yes", "looks good", "continue"]:
        logger.info(f"Checkpoint 4 revision requested: {message}")
        llm = get_llm(role="planner")
        prompt = f"""Original Research Design: {state.get('research_design')}
Original Data Collection: {state.get('data_collection_plan')}
Original Data Analysis: {state.get('data_analysis_plan')}

User Revision Request: {message}

Revise the methodology components based on user feedback.
Return JSON with keys: "research_design", "data_collection_plan", "data_analysis_plan"."""
        try:
            res = await llm.ainvoke(prompt)
            import json
            raw = res.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            revised = json.loads(raw)
            return {
                "research_design": revised.get("research_design", state.get("research_design")),
                "data_collection_plan": revised.get("data_collection_plan", state.get("data_collection_plan")),
                "data_analysis_plan": revised.get("data_analysis_plan", state.get("data_analysis_plan")),
                "user_feedback": message,
                "hitl_checkpoint": "checkpoint_4_approved",
                "status": "synthesizing"
            }
        except Exception as e:
            logger.warning(f"Error processing Checkpoint 4 feedback: {e}")

    return {
        "hitl_checkpoint": "checkpoint_4_approved",
        "status": "synthesizing"
    }


# Build StateGraph
builder = StateGraph(ResearchModeState)

# Add Nodes
builder.add_node("keyword_extractor", keyword_extractor_agent)
builder.add_node("checkpoint_1", checkpoint_1_node)
builder.add_node("paper_fetcher", paper_fetcher_agent)
builder.add_node("paper_screener", paper_screener_agent)
builder.add_node("literature_review", literature_review_agent)
builder.add_node("gap_analysis", gap_analysis_agent)
builder.add_node("framework", framework_agent)
builder.add_node("checkpoint_2", checkpoint_2_node)
builder.add_node("hypotheses", hypotheses_agent)
builder.add_node("checkpoint_3", checkpoint_3_node)
builder.add_node("methodology", methodology_agent)
builder.add_node("checkpoint_4", checkpoint_4_node)
builder.add_node("results", results_agent)
builder.add_node("discussion", discussion_agent)
builder.add_node("implications", implications_agent)
builder.add_node("limitations", limitations_agent)
builder.add_node("conclusion", conclusion_agent)
builder.add_node("future_scope", future_scope_agent)
builder.add_node("references", references_agent)
builder.add_node("introduction", introduction_agent)
builder.add_node("abstract", abstract_agent)
builder.add_node("title", title_agent)

# Edges
builder.add_edge(START, "keyword_extractor")
builder.add_edge("keyword_extractor", "checkpoint_1")
builder.add_edge("checkpoint_1", "paper_fetcher")
builder.add_edge("paper_fetcher", "paper_screener")
builder.add_edge("paper_screener", "literature_review")
builder.add_edge("literature_review", "gap_analysis")
builder.add_edge("gap_analysis", "framework")
builder.add_edge("framework", "checkpoint_2")
builder.add_edge("checkpoint_2", "hypotheses")
builder.add_edge("hypotheses", "checkpoint_3")
builder.add_edge("checkpoint_3", "methodology")
builder.add_edge("methodology", "checkpoint_4")
builder.add_edge("checkpoint_4", "results")
builder.add_edge("results", "discussion")
builder.add_edge("discussion", "implications")
builder.add_edge("implications", "limitations")
builder.add_edge("limitations", "conclusion")
builder.add_edge("conclusion", "future_scope")
builder.add_edge("future_scope", "references")
builder.add_edge("references", "introduction")
builder.add_edge("introduction", "abstract")
builder.add_edge("abstract", "title")
builder.add_edge("title", END)

checkpointer = MemorySaver()
research_mode_graph = builder.compile(checkpointer=checkpointer)
