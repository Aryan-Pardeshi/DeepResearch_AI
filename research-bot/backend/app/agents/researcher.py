# Worker agent (reused for each sub-question)
import logging
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from backend.app.graph.state import ResearchState
from typing import List
from pydantic import BaseModel, Field
from backend.app.llm import llm
from backend.app.tools.tavily_search import search_web

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert research analyst with access to web search.

Your workflow:
1. Read the research task carefully.
2. Identify 1-3 precise search queries that will best answer the task.
3. Use the search_web tool. Use time_range when the task involves recent or time-sensitive topics:
   - "day"   → news from the last 24 hours
   - "week"  → last 7 days
   - "month" → last 30 days
   - "year"  → last 12 months
4. Critically evaluate the search results. If the results are insufficient or not relevant, search again with a refined query.
5. After gathering enough information, stop searching.

Output constraints:
- Your final summary must be factual and grounded in the search results.
- Keep it under 500 tokens.
- Always extract and include source URLs as citations.
"""

SYNTHESIS_PROMPT = """Using all search results gathered above, write your final research report.

You MUST respond in valid JSON with this exact schema:
{{
  "result": "<comprehensive research summary based only on search results>",
  "citations": ["<url1>", "<url2>", ...]
}}

Only include URLs that appeared in the search results."""


class ResearchResult(BaseModel):
    result: str = Field(description="Comprehensive research summary based on search results")
    citations: List[str] = Field(description="List of source URLs from search results")


def researcher_node(state: ResearchState) -> dict:
    query = state["query"]
    logger.info(f"Researcher starting for query: {query}")

    # Single agent: same LLM instance used for both tool calling and synthesis
    agent = llm.bind_tools([search_web])

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Research Task: {query}")
    ]

    max_steps = 10
    search_count = 0

    for step in range(max_steps):
        response = agent.invoke(messages)
        messages.append(response)

        # No tool calls → LLM is done searching, move to synthesis
        if not response.tool_calls:
            logger.info(f"Researcher completed search in {step + 1} steps with {search_count} searches")
            break

        # Execute each requested tool call
        for tool_call in response.tool_calls:
            if tool_call["name"] == "search_web":
                args = tool_call["args"]
                logger.info(f"Executing search: query='{args.get('query')}', time_range={args.get('time_range')}")

                try:
                    tool_output = search_web.invoke(args)
                    search_count += 1
                except Exception as e:
                    tool_output = f"Search failed: {str(e)}"
                    logger.warning(f"Search failed: {e}")

                messages.append(
                    ToolMessage(
                        content=str(tool_output),
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"]
                    )
                )
            else:
                logger.warning(f"Unknown tool call: {tool_call['name']}")
                messages.append(ToolMessage(content=f"Unknown tool {tool_call['name']}", tool_call_id=tool_call["id"]))

    # Synthesis step: ask the same agent to produce structured JSON (no tools needed now)
    messages.append(HumanMessage(content=SYNTHESIS_PROMPT))
    final_response = agent.invoke(messages)

    try:
        import json
        raw = final_response.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        final_result = ResearchResult(**data)
    except Exception as e:
        logger.error(f"Structured output parsing failed: {e}")
        return {"results": [final_response.content], "citations": []}

    logger.info(f"Researcher completed. Citations: {len(final_result.citations)}")
    return {
        "results": [final_result.result],
        "citations": final_result.citations
    }

