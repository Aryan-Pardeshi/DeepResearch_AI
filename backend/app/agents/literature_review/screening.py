"""Paper screening and inclusion/exclusion management module.
"""

from __future__ import annotations

import time
import logging
from typing import Optional

from backend.app.models.corpus import LiteratureCorpus
from backend.app.storage.corpus_repository import get_corpus_repository

logger = logging.getLogger(__name__)


async def update_paper_screening(
    corpus_id: str,
    paper_id: str,
    status: str,  # "included" or "excluded"
    exclusion_reason: Optional[str] = None
) -> LiteratureCorpus:
    """Update paper inclusion/exclusion status and reason in SQLite."""
    repo = get_corpus_repository()
    corpus = await repo.get_corpus(corpus_id)
    if not corpus:
        raise ValueError(f"Corpus '{corpus_id}' not found.")

    if paper_id not in corpus.paper_ids:
        raise ValueError(f"Paper '{paper_id}' not present in corpus '{corpus_id}'.")

    if status == "included":
        if paper_id not in corpus.included_paper_ids:
            corpus.included_paper_ids.append(paper_id)
        if paper_id in corpus.excluded_paper_ids:
            corpus.excluded_paper_ids.remove(paper_id)
        corpus.exclusion_reasons.pop(paper_id, None)
    elif status == "excluded":
        if paper_id not in corpus.excluded_paper_ids:
            corpus.excluded_paper_ids.append(paper_id)
        if paper_id in corpus.included_paper_ids:
            corpus.included_paper_ids.remove(paper_id)
        if exclusion_reason:
            corpus.exclusion_reasons[paper_id] = exclusion_reason
    else:
        raise ValueError(f"Invalid status '{status}'. Must be 'included' or 'excluded'.")

    corpus.updated_at = time.time()
    await repo.save_corpus(corpus)
    logger.info(f"Updated paper '{paper_id}' in corpus '{corpus_id}' to status '{status}'.")
    return corpus
