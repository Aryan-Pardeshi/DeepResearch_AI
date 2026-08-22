"""LiteratureCorpus and EvidenceMatrix state models.

LiteratureCorpus maintains workspace IDs (paper_ids, included_paper_ids, evidence_ids)
to keep data normalized and decoupled from raw paper/evidence records.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class MatrixCell(BaseModel):
    """A cell in the dynamic evidence matrix tracking provenance and validation."""
    
    cell_value: Any = None
    source_evidence_ids: List[str] = Field(default_factory=list)
    origin: Literal["ai", "human"] = "ai"
    validation_status: Literal["source_supported", "human_edited", "unverified"] = "source_supported"


class EvidenceMatrix(BaseModel):
    """Dynamic evidence matrix schema and extracted cells."""
    
    matrix_id: str
    corpus_id: str
    columns: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of column definitions: [{'key': 'model', 'label': 'Model Name', 'description': '...'}]"
    )
    rows: Dict[str, Dict[str, MatrixCell]] = Field(
        default_factory=dict,
        description="Map of paper_id -> column_key -> MatrixCell"
    )


class LiteratureCorpus(BaseModel):
    """Persistent Literature Review corpus workspace container (ID references only)."""
    
    corpus_id: str
    query: str
    domain_profile: Dict[str, Any] = Field(default_factory=dict)
    paper_ids: List[str] = Field(default_factory=list)
    included_paper_ids: List[str] = Field(default_factory=list)
    excluded_paper_ids: List[str] = Field(default_factory=list)
    exclusion_reasons: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of paper_id -> exclusion reason string"
    )
    evidence_ids: List[str] = Field(default_factory=list)
    matrix_id: Optional[str] = None
    synthesis_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
