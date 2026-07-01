# query validator node
import logging
from backend.app.graph.state import ResearchState

logger = logging.getLogger(__name__)

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from backend.app.llm import llm_fast

# System prompt for query validation
VALIDATOR_SYSTEM_PROMPT = """You are an input validation assistant for a specialized Research Bot.
Your task is to analyze the user's input query and determine if it is a valid, substantive research topic.

Criteria for a VALID research query:
- It asks to research, explain, analyze, or gather info on a specific topic (e.g., "Recent breakthroughs in Quantum Computing in 2026", "Impact of microplastics on marine life").
- Even if it starts with polite greetings or conversational filler (e.g., "Hello, can you please research...", "Hi, tell me about..."), it is VALID as long as it contains a specific subject of research.

Criteria for an INVALID query:
- It is just conversational greeting/filler (e.g., "hello", "hi there", "greetings").
- It is a general query about you or the bot (e.g., "who are you", "what is your name", "what can you do").
- It is a generic command without any topic (e.g., "do some research for me", "search something", "please start").
- It is empty, gibberish, or completely lacks any researchable subject.

You MUST respond in JSON matching this schema:
{{
  "is_valid": true or false,
  "error_message": "your error message here, or null if is_valid is true"
}}
"""

class QueryValidation(BaseModel):
    is_valid: bool = Field(
        description="True if the input query contains a specific research topic. False if it is just a greeting, chatbot meta-question, or generic conversational filler without a topic."
    )
    error_message: Optional[str] = Field(
        default=None,
        description="If is_valid is False, provide a friendly error message explaining why and asking the user to provide a specific research topic. Otherwise, leave empty."
    )

def query_validator(state: ResearchState) -> dict:
    query = state.get("query", "").strip()
    logger.info(f"Validating query: '{query}'")
    
    if not query:
        return {"status": "error", "error": "Please provide a specific research topic."}
        
    # Pre-filter very short queries (less than 3 words) to save API tokens
    words = query.split()
    if len(words) < 3:
        return {"status": "error", "error": "Not a valid research query. Please provide a specific research topic."}
        
    try:
        validator_llm = llm_fast.with_structured_output(QueryValidation, method="json_mode")
        prompt = ChatPromptTemplate([
            ("system", VALIDATOR_SYSTEM_PROMPT),
            ("user", f"Input Query: {query}")
        ])
        messages = prompt.format_messages()
        validation = validator_llm.invoke(messages)
        
        if not validation.is_valid:
            error_msg = validation.error_message or "Not a valid research query. Please provide a specific research topic."
            return {"status": "error", "error": error_msg}
            
    except Exception as e:
        logger.error(f"Error during query validation LLM call: {e}")
        # Fallback to a basic check if the LLM call fails
        words = query.split()
        if len(words) < 5:
            return {"status": "error", "error": "Not a valid research query. Please provide a specific research topic."}
            
    return {}