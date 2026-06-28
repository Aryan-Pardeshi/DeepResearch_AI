# Tavily tool wrapper
from tavily import TavilyClient
from langchain_core.tools import tool
import os
from dotenv import load_dotenv
from typing import Optional, Literal

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def search_web(query: str, time_range: Optional[Literal["day", "month", "week", "year"]] = None) -> str:
    """Use Tavily search to search the web for the given query."""

    try:
        response = tavily_client.search(
            time_range=time_range,
            query=query,
            max_results=4,
            include_images=False,
            include_raw_content=False,
        )
        return str(response)

    except Exception as e:
        return f"Error using Tavily search: {str(e)}"
