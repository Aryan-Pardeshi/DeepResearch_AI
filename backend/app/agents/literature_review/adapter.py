"""ResearchModeImportAdapter: Bridges LiteratureReview workspace into ResearchModeState.

Decouples Literature Review from Research Mode graph internals by translating
LiteratureCorpus, included papers, and evidence records into a ResearchModeState dict.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.app.storage.corpus_repository import get_corpus_repository
from backend.app.models.evidence import PRISMATracker

logger = logging.getLogger(__name__)


async def bridge_corpus_to_research_mode(corpus_id: str) -> Dict[str, Any]:
    """Export screened LiteratureCorpus and evidence into ResearchModeState initialization dictionary."""
    repo = get_corpus_repository()
    corpus = await repo.get_corpus(corpus_id)
    if not corpus:
        raise ValueError(f"Corpus '{corpus_id}' not found.")

    included_papers = await repo.get_papers(corpus.included_paper_ids)
    all_papers = await repo.get_papers(corpus.paper_ids)
    evidence = await repo.get_evidence_records_by_corpus(corpus_id)
    synthesis = await repo.get_synthesis_result(corpus_id)

    paper_records_dump = [p.model_dump() for p in included_papers]
    evidence_records_dump = [e.model_dump() for e in evidence]

    # Build initial PRISMA tracker state for Research Mode
    records_by_source: Dict[str, int] = {}
    for p in all_papers:
        src = p.retrieval_source
        records_by_source[src] = records_by_source.get(src, 0) + 1

    prisma = PRISMATracker(
        records_identified=len(all_papers),
        records_by_source=records_by_source,
        duplicates_removed=0,
        records_after_dedup=len(all_papers),
        records_screened=len(all_papers),
        excluded_title_abstract=len(corpus.excluded_paper_ids),
        full_text_requested=len(included_papers),
        full_text_assessed=len(included_papers),
        excluded_full_text=0,
        studies_included=len(included_papers),
    )

    initial_rm_state: Dict[str, Any] = {
        "problem_statement": corpus.query,
        "research_objectives": [f"Systematic review of {corpus.query}"],
        "keywords": corpus.domain_profile.get("detected_topics", [corpus.query]),
        "paper_records": paper_records_dump,
        "screened_papers": paper_records_dump,
        "evidence_records": evidence_records_dump,
        "prisma_tracker": prisma.model_dump(),
        "taxonomy": {"themes": synthesis.themes} if synthesis else {},
        "research_gaps_structured": synthesis.research_gaps if synthesis else [],
        "synthesis_comparisons": synthesis.contradictions if synthesis else [],
        "status": "awaiting_approval",
        "hitl_checkpoint": "checkpoint_1_approved",  # Seeding directly into approved search protocol
    }

    logger.info(f"Bridged corpus '{corpus_id}' into ResearchModeState with {len(included_papers)} papers and {len(evidence)} evidence records.")
    return initial_rm_state
