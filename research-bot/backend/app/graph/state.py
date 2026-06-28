from typing import List, TypedDict, Annotated, Literal, Optional

import operator

class ResearchState(TypedDict):
    """State for the research assistant graph."""

    query: str 
    plan: List[str]
    plan_approved: bool
    user_feedback: Optional[str]
    status: Literal["planning", "awaiting_approval", "researching", "reviewing", "completed", "error"]
    results: Annotated[List[str], operator.add] 
    final_answer: Optional[str]
    citations: Annotated[List[str], operator.add]
    
    
