# Final report builder
from backend.app.llm import llm2
from backend.app.graph.state import ResearchState
from langchain_core.messages import SystemMessage, HumanMessage


def aggregator_node(state: ResearchState) -> dict:
    combined = "\n\n".join(
        f"Research Section {i+1}:\n{result}" 
        for i, result in enumerate(state["results"])
    )

    # citations is already a flat List[str] — no flattening needed
    citations = list(dict.fromkeys(state.get("citations", [])))  # deduplicate, preserve order

    messages = [
        SystemMessage(content=(
            "You are a senior research report writer. Synthesize the provided research sections "
            "into a single, well-structured markdown report. Include an executive summary, "
            "key findings with supporting evidence, and a conclusion. Be objective and factual."
        )),
        HumanMessage(content=f"Research sections:\n\n{combined}\n\nWrite the final markdown report.")
    ]

    final = llm2.invoke(messages)
    return {"final_answer": final.content, "citations": citations,"status": "completed"}