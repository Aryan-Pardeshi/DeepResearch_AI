"""Typed data models and deterministic evidence store for AI Research Assistant.

These Pydantic models form the single source of truth for the research pipeline,
guaranteeing mathematical PRISMA tracking, provenance anchoring for every claim,
and strict separation between literature review findings and proposed future research.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


from backend.app.models.paper import PaperRecord, AuthorIdentity, make_paper_id


def make_evidence_id(paper_id: str, claim_index: int) -> str:
    """Generate a scoped evidence ID: paper_id prefix + sequential claim index."""
    return f"{paper_id}_ev{claim_index:03d}"


def make_claim_id(section: str, claim_index: int) -> str:
    """Generate a section-scoped review claim ID."""
    clean_sec = re.sub(r"[^a-z0-9]", "", (section or "sec").lower())[:8]
    return f"{clean_sec}_cl{claim_index:03d}"



class EvidenceRecord(BaseModel):
    """Structured, verifiable unit of empirical or theoretical evidence from a paper."""
    
    evidence_id: str = Field(
        ...,
        description="Scoped identifier in format {paper_id}_ev001"
    )
    paper_id: str = Field(
        ...,
        description="Foreign key to PaperRecord.paper_id"
    )
    claim_summary: str = Field(
        ...,
        description="Concise description of the specific factual claim or finding"
    )
    exact_quote: Optional[str] = Field(
        None,
        description="Verbatim text from the source paper demonstrating provenance"
    )
    source_section: Optional[str] = Field(
        None,
        description="Section of source paper: 'Abstract', 'Section 4.2', 'Table 1', etc."
    )
    task_or_domain: Optional[str] = None
    dataset: Optional[str] = None
    model_or_method: Optional[str] = None
    sample_size: Optional[str] = None
    metric_name: Optional[str] = None
    baseline_value: Optional[float] = None
    reported_value: Optional[float] = None
    unit_or_scale: Optional[str] = None
    effect_direction: Optional[Literal["positive", "negative", "neutral", "mixed", "unclear"]] = "unclear"
    confidence_interval_or_p: Optional[str] = None
    limitations: Optional[str] = None
    reproducibility_available: bool = False
    hypothesis_relevance: Dict[str, Literal["Supports", "Refutes", "Neutral", "Partial", "Not Applicable"]] = Field(
        default_factory=dict
    )


class ReviewClaim(BaseModel):
    """A claim generated in the paper prose with links to supporting evidence."""
    
    claim_id: str = Field(
        ...,
        description="Identifier in format {section}_cl001"
    )
    claim_text: str = Field(
        ...,
        description="The written sentence or thesis in the paper"
    )
    target_section: str = Field(
        ...,
        description="Target section: 'literature_review', 'results', 'discussion', etc."
    )
    supporting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="List of EvidenceRecord.evidence_id grounding this claim"
    )
    is_quantitative: bool = False
    quantitative_metric: Optional[str] = None
    quantitative_value: Optional[float] = None
    validation_status: Literal["verified", "unsupported", "flagged", "pending"] = "pending"
    integrity_notes: Optional[str] = None


class PRISMATracker(BaseModel):
    """Deterministic PRISMA 2020 flow tracker with mathematical invariants."""
    
    records_identified: int = 0
    records_by_source: Dict[str, int] = Field(default_factory=dict)
    duplicates_removed: int = 0
    records_after_dedup: int = 0
    records_screened: int = 0
    excluded_title_abstract: int = 0
    full_text_requested: int = 0
    full_text_unavailable: int = 0
    full_text_assessed: int = 0
    excluded_full_text: int = 0
    studies_included: int = 0
    exclusion_reasons: Dict[str, int] = Field(default_factory=dict)

    def validate_invariants(self) -> List[str]:
        """Validate mathematical conservation laws of the PRISMA flowchart."""
        errors = []
        if self.records_identified - self.duplicates_removed != self.records_after_dedup:
            errors.append(
                f"PRISMA Invariant Broken: identified ({self.records_identified}) - "
                f"duplicates ({self.duplicates_removed}) != after_dedup ({self.records_after_dedup})"
            )
        expected_screened_excluded = self.records_screened - self.excluded_title_abstract
        if self.full_text_requested > 0 and self.full_text_requested != expected_screened_excluded:
            errors.append(
                f"PRISMA Invariant Broken: screened ({self.records_screened}) - "
                f"excluded_title_abstract ({self.excluded_title_abstract}) != full_text_requested ({self.full_text_requested})"
            )
        if self.full_text_assessed > 0:
            expected_included = self.full_text_assessed - self.excluded_full_text
            if self.studies_included != expected_included:
                errors.append(
                    f"PRISMA Invariant Broken: full_text_assessed ({self.full_text_assessed}) - "
                    f"excluded_full_text ({self.excluded_full_text}) != studies_included ({self.studies_included})"
                )
        return errors


class SearchProtocol(BaseModel):
    """PICOC research scope and Boolean search protocol."""
    
    population: str = ""
    intervention: str = ""
    comparison: str = ""
    outcomes: List[str] = Field(default_factory=list)
    context: str = ""
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)
    boolean_queries: List[str] = Field(default_factory=list)
    search_keywords: List[str] = Field(default_factory=list)


class TaxonomyTheme(BaseModel):
    """A theme or category in the synthesized literature taxonomy."""
    
    theme_id: str
    theme_name: str
    description: str
    paper_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    subthemes: List[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Audit report generated by the deterministic validation pipeline."""
    
    total_inline_citations: int = 0
    verified_citations: int = 0
    unverified_citations: List[str] = Field(default_factory=list)
    orphan_references: List[str] = Field(default_factory=list)
    total_quantitative_claims: int = 0
    grounded_quantitative_claims: int = 0
    unsupported_quantitative_claims: List[str] = Field(default_factory=list)
    integrity_flags: List[str] = Field(default_factory=list)
    prisma_invariants_valid: bool = True
    passed_all_gates: bool = True
