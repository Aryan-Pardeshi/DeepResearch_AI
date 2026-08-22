"""Structured PaperRecord and AuthorIdentity data models.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


def make_paper_id(doi: Optional[str], title: str, year: Optional[str] = None) -> str:
    """Generate a deterministic 16-character SHA-256 hash paper ID.
    
    DOI is canonical; normalized title is used as fallback.
    """
    if doi and doi.strip():
        doi_clean = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi.strip(), flags=re.IGNORECASE).strip().lower()
        key = f"doi:{doi_clean}"
    else:
        cleaned = re.sub(r"\s+", " ", (title or "").lower().strip())
        normalized = re.sub(r"[^\w\s]", "", cleaned, flags=re.UNICODE).strip()
        key = f"title:{normalized}:{year or 'nd'}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class AuthorIdentity(BaseModel):
    """Structured representation of an author with ORCID and affiliation."""
    
    name: str
    orcid: Optional[str] = None
    orcid_uri: Optional[str] = None
    affiliation: Optional[str] = None


class PaperRecord(BaseModel):
    """Structured representation of an academic paper retrieved during search."""
    
    paper_id: str = Field(
        ...,
        description="Deterministic 16-hex hash of DOI or normalized title"
    )
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    author_identities: List[AuthorIdentity] = Field(default_factory=list)
    year: str = "n.d."
    venue: Optional[str] = None
    abstract: str = ""
    source_url: str = ""
    pdf_url: Optional[str] = None
    fulltext_excerpt: Optional[str] = None
    open_access_status: Optional[str] = None
    retrieval_source: str = "unknown"
    external_ids: Dict[str, str] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Lineage dictionary: discovered_via, metadata_source, abstract_source, etc."
    )
    citation_count: int = 0
    relevance_score: Optional[float] = None
    study_type: Optional[Literal["empirical", "benchmark", "review", "theoretical", "survey", "meta-analysis", "other"]] = "empirical"
    quality_rating: Optional[Literal["High", "Medium", "Low", "Unclear"]] = "Unclear"
    quality_rubric: Optional[Dict[str, Any]] = None
    screening_status: Literal["retrieved", "screened", "included", "excluded"] = "retrieved"
    exclusion_reason: Optional[str] = None
    hypothesis_support: Dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PaperRecord:
        """Create a PaperRecord from raw paper dictionary with auto-generated paper_id."""
        d = dict(data)
        if "paper_id" not in d or not d["paper_id"]:
            d["paper_id"] = make_paper_id(d.get("doi"), d.get("title", ""), d.get("year"))
        return cls(**d)
