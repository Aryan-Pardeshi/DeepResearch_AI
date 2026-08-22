"""Structured evidence extraction module for Literature Review mode.
"""

from __future__ import annotations

import logging
from typing import List

from backend.app.models.evidence import EvidenceRecord
from backend.app.storage.corpus_repository import get_corpus_repository
from backend.app.tools.fulltext_fetcher import fetch_fulltexts
from backend.app.agents.research_mode.extraction import evidence_extractor_agent

logger = logging.getLogger(__name__)


async def extract_corpus_evidence(corpus_id: str) -> List[EvidenceRecord]:
    """Fetch full-texts for included papers and extract structured EvidenceRecords."""
    repo = get_corpus_repository()
    corpus = await repo.get_corpus(corpus_id)
    if not corpus:
        raise ValueError(f"Corpus '{corpus_id}' not found.")

    if not corpus.included_paper_ids:
        logger.info(f"No included papers in corpus '{corpus_id}' to extract evidence from.")
        return []

    papers = await repo.get_papers(corpus.included_paper_ids)
    paper_dicts = [p.model_dump() for p in papers]

    # Fetch full-texts for top papers if needed
    enriched_paper_dicts = await fetch_fulltexts(paper_dicts)

    # Run structured extraction agent
    state = {"paper_records": enriched_paper_dicts, "research_query": corpus.query}
    result_state = await evidence_extractor_agent(state)
    raw_evidence = result_state.get("evidence_records", [])

    evidence_records: List[EvidenceRecord] = []
    evidence_ids: List[str] = []

    for r_dict in raw_evidence:
        if isinstance(r_dict, dict):
            ev = EvidenceRecord(**r_dict)
            evidence_records.append(ev)
            evidence_ids.append(ev.evidence_id)

    # Save extracted evidence & update corpus in SQLite
    await repo.save_evidence_records(corpus_id, evidence_records)
    corpus.evidence_ids = list(set(corpus.evidence_ids + evidence_ids))
    corpus.updated_at = time.time()
    await repo.save_corpus(corpus)

    logger.info(f"Extracted {len(evidence_records)} evidence records for corpus '{corpus_id}'.")
    return evidence_records
