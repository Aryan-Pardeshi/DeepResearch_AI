# Final report builder
import logging
from backend.app.llm import llm_pro
from backend.app.graph.state import ResearchState
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


async def aggregator_node(state: ResearchState) -> dict:
    # Combine the results of all the sub-agents
    combined = "\n\n".join(
        f"Research Section {i+1}:\n{result}" 
        for i, result in enumerate(state["results"])
    )

    # Combine and deduplicate the citations
    citations = list(dict.fromkeys(state.get("citations", [])))

    messages = [
        SystemMessage(content=(
            "You are a Principal Research Analyst and Writer.\n\n"
            "Your task is to synthesize the provided raw research findings into a cohesive, publication-ready research report in markdown format.\n\n"
            "Structure requirements:\n"
            "- Use a single, clean markdown title for the report.\n"
            "- Provide a clear Executive Summary / Overview at the beginning.\n"
            "- Organically group the findings into logical sections based on the research content. Do not create an excessive number of short sections; keep it concise, flow naturally, and focus on details and facts.\n"
            "- Incorporate the Problem Statement naturally into the intro/executive summary section.\n"
            "- List all the provided source URLs cleanly under a 'Sources & References' section at the end.\n\n"
            "Guidelines:\n"
            "- Keep the tone formal, objective, and analytical.\n"
            "- Present data in well-formatted markdown tables or bullet points where appropriate.\n"
            "- Strictly stick to the facts provided. Do not extrapolate, invent metrics, or fabricate URLs."
        )),

        HumanMessage(content=(
            f"User Query: {state['query']}\n"
            f"Problem Statement (ps): {state.get('ps', '')}\n\n"
            f"Research Sections:\n{combined}\n\n"
            f"Citations:\n" + "\n".join(f"- {url}" for url in citations) + "\n\n"
            "Write the final synthesized markdown report."
        ))
    ]

    try:
        response = await llm_pro.ainvoke(messages)
        final_content = response.content
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error in aggregator: {e}", exc_info=True)
        if any(kw in error_msg for kw in ["api key", "authentication", "unauthorized", "401", "403", "invalid key", "missing credentials", "not set"]):
            return {"status": "error", "error": "API key is missing or invalid. Open settings to configure your API keys."}
        return {"status": "error", "error": f"Synthesis failed: {str(e)}"}
    
    # Update the state with the final answer and set status to completed
    return {"final_answer": final_content, "status": "completed"}