# Final report builder
import logging
from backend.app.llm import llm_pro
from backend.app.graph.state import ResearchState
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


async def aggregator_node(state: ResearchState) -> dict:
    #combine the results of all the sub agents
    combined = "\n\n".join(
        f"Research Section {i+1}:\n{result}" 
        for i, result in enumerate(state["results"])
    )

    #combine the citations
    # citations is already a flat List[str] — no flattening needed
    citations = list(dict.fromkeys(state.get("citations", [])))  # deduplicate, preserve order

    messages = [
        SystemMessage(content=(
            "You are a Principal Research Analyst and Writer.\n\n"
            "Your task is to synthesize the provided raw research sections into a cohesive, publication-ready markdown report.\n"
            "You MUST structure the final report with the following exact markdown headers:\n"
            "1. **Problem Statement**: Directly incorporate the provided Problem Statement (ps).\n"
            "2. **Aim**: Outline the main target/objective of the research based on the User Query.\n"
            "3. **Overview**: Provide a high-level summary overview of the findings.\n"
            "4. **Detailed Findings** (use custom section & sub-section headers based on the query): Divide this into various sections and small sub-sections as needed to thoroughly explain the topic.\n"
            "5. **Sources**: List the provided source URLs cleanly at the bottom as references.\n\n"
            "Guidelines:\n"
            "- Use professional typography, bullet points, and bold text for key metrics.\n"
            "- Do not invent any facts or source links. Only use what is present in the research sections."
        )),

        HumanMessage(content=(
            f"User Query: {state['query']}\n"
            f"Problem Statement (ps): {state.get('ps', '')}\n\n"
            f"Research Sections:\n{combined}\n\n"
            f"Citations:\n" + "\n".join(f"- {url}" for url in citations) + "\n\n"
            "Write the final structured markdown report."
        ))
    ]

    try:
        final = await llm_pro.ainvoke(messages)
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error in aggregator: {e}", exc_info=True)
        if any(kw in error_msg for kw in ["api key", "authentication", "unauthorized", "401", "403", "invalid key", "missing credentials", "not set"]):
            return {"status": "error", "error": "API key is missing or invalid. Open settings to configure your API keys."}
        return {"status": "error", "error": f"Synthesis failed: {str(e)}"}
    
    #update the state with the final answer and set status to completed (do not return citations to avoid duplicating them via the operator.add reducer)
    return {"final_answer": final.content, "status": "completed"}