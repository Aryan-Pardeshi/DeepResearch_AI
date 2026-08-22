"""SynthesisResult and CompiledReview models for literature reviews.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.models.evidence import ReviewClaim


class SynthesisResult(BaseModel):
    """Structured synthesis output (themes, contradictions, research gaps)."""
    
    synthesis_id: str
    corpus_id: str
    themes: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    research_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class CompiledReview(BaseModel):
    """Compiled literature review document with cross-section consistency audit."""
    
    review_id: str
    corpus_id: str
    title: str
    outline: List[str] = Field(default_factory=list)
    sections: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of section_title -> section_markdown_prose"
    )
    claims: List[ReviewClaim] = Field(default_factory=list)
    consistency_audit: Dict[str, Any] = Field(
        default_factory=dict,
        description="Results from Cross-Section Consistency Auditor"
    )
    created_at: float = Field(default_factory=time.time)
