from typing import List, Dict, Any, Optional, TypedDict

class ResearchModeState(TypedDict, total=False):
    """State schema for Autonomous Research Mode pipeline."""
    thread_id: str
    mode: str  # "research"
    problem_statement: str
    research_objectives: List[str]
    research_questions: List[str]
    keywords: List[str]
    raw_papers: List[Dict[str, Any]]  # title, abstract, authors, year, doi, url, source
    screened_papers: List[Dict[str, Any]]
    literature_review: str
    unverified_citations: List[str]

    research_gap: str
    conceptual_framework: str
    hypotheses: List[str]
    research_design: str
    data_collection_plan: str
    data_analysis_plan: str
    results: str
    discussion: str
    implications: str
    limitations: str
    conclusion: str
    future_scope: List[str] | str
    references: List[str]  # Formatted APA citations
    appendices: str
    introduction: str
    abstract: str
    title: str
    hitl_checkpoint: str  # "checkpoint_1", "checkpoint_2", "checkpoint_3", "checkpoint_4", "completed"
    user_feedback: Optional[str]
    status: str  # "initializing", "awaiting_approval", "fetching_papers", "synthesizing", "completed", "error"
    error: Optional[str]
