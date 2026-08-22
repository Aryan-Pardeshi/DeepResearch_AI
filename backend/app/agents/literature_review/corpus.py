"""Corpus creation and workspace retrieval module for Literature Review.
"""

from __future__ import annotations

import uuid
import time
import logging
from typing import Any, Dict, List, Optional

from backend.app.models.paper import PaperRecord
from backend.app.models.corpus import LiteratureCorpus
from backend.app.tools.academic_router import DomainProfile
from backend.app.storage.corpus_repository import get_corpus_repository

logger = logging.getLogger(__name__)


async def create_literature_corpus(
    query: str,
    papers: List[PaperRecord],
    domain_profile: DomainProfile
) -> LiteratureCorpus:
    """Initialize persistent LiteratureCorpus workspace in SQLite."""
    corpus_id = f"corp_{uuid.uuid4().hex[:12]}"
    paper_ids = [p.paper_id for p in papers]

    corpus = LiteratureCorpus(
        corpus_id=corpus_id,
        query=query,
        domain_profile=domain_profile.model_dump(),
        paper_ids=paper_ids,
        included_paper_ids=paper_ids,  # Default: all returned papers included initially
        excluded_paper_ids=[],
        exclusion_reasons={},
        evidence_ids=[],
        matrix_id=None,
        synthesis_id=None,
        created_at=time.time(),
        updated_at=time.time(),
    )

    repo = get_corpus_repository()
    await repo.save_papers(papers)
    await repo.save_corpus(corpus)
    logger.info(f"Created LiteratureCorpus '{corpus_id}' with {len(papers)} papers.")
    return corpus


async def get_literature_corpus_workspace(corpus_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete LiteratureCorpus workspace state including papers, matrix, and synthesis."""
    repo = get_corpus_repository()
    corpus = await repo.get_corpus(corpus_id)
    if not corpus:
        return None

    papers = await repo.get_papers(corpus.paper_ids)
    evidence = await repo.get_evidence_records_by_corpus(corpus_id)
    matrix = await repo.get_evidence_matrix(corpus_id)
    synthesis = await repo.get_synthesis_result(corpus_id)
    review = await repo.get_compiled_review(corpus_id)

    # Build screening summary stats
    included_count = len(corpus.included_paper_ids)
    excluded_count = len(corpus.excluded_paper_ids)
    source_dist: Dict[str, int] = {}
    year_dist: Dict[str, int] = {}

    for p in papers:
        src = p.retrieval_source
        source_dist[src] = source_dist.get(src, 0) + 1
        yr = p.year or "n.d."
        year_dist[yr] = year_dist.get(yr, 0) + 1

    return {
        "corpus": corpus.model_dump(),
        "papers": [p.model_dump() for p in papers],
        "evidence_count": len(evidence),
        "matrix": matrix.model_dump() if matrix else None,
        "synthesis": synthesis.model_dump() if synthesis else None,
        "review": review.model_dump() if review else None,
        "stats": {
            "total_found": len(papers),
            "included": included_count,
            "excluded": excluded_count,
            "source_distribution": source_dist,
            "year_distribution": year_dist,
        }
    }
