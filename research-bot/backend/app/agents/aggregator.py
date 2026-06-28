# Final report builder
from backend.app.llm import llm2
from backend.app.graph.state import ResearchState
from langchain_core.messages import SystemMessage, HumanMessage


def aggregator_node(state: ResearchState) -> dict:
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
            "Guidelines:\n"
            "1. **Relevance**: Make sure the report directly answers the User Query.\n"
            "2. **Structure**: Include an Executive Summary, Key Findings (detailed with supporting evidence), and a Future Outlook/Conclusion.\n"
            "3. **Markdown**: Use professional typography with headers, bullet points, bold text for key metrics/terms, and blockquotes if appropriate.\n"
            "4. **Citations**: Weave the provided source URLs naturally into the content using markdown links (e.g. `[Source Name](URL)`) where they back up specific claims. Do not invent links."
        )),

        HumanMessage(content=f"User Query: {state['query']}\n\nResearch sections:\n\n{combined}\n\nWrite the final markdown report.")
    ]

    final = llm2.invoke(messages)
    
    #update the state with the final answer and set status to completed
    return {"final_answer": final.content, "citations": citations,"status": "completed"}