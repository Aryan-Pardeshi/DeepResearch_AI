"""Thematic clustering, contradiction analysis, and research gap identification module.
"""

from __future__ import annotations

import uuid
import time
import json
import logging
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage

from backend.app.models.review import SynthesisResult
from backend.app.storage.corpus_repository import get_corpus_repository
from backend.app.llm import get_llm

logger = logging.getLogger(__name__)


async def generate_thematic_synthesis(corpus_id: str) -> SynthesisResult:
    """Group papers into themes, detect explicit contradictions, and identify research gaps."""
    repo = get_corpus_repository()
    corpus = await repo.get_corpus(corpus_id)
    if not corpus:
        raise ValueError(f"Corpus '{corpus_id}' not found.")

    papers = await repo.get_papers(corpus.included_paper_ids)
    evidence = await repo.get_evidence_records_by_corpus(corpus_id)

    if not papers:
        synthesis_id = corpus.synthesis_id or f"syn_{uuid.uuid4().hex[:12]}"
        res = SynthesisResult(synthesis_id=synthesis_id, corpus_id=corpus_id, themes=[], contradictions=[], research_gaps=[])
        await repo.save_synthesis_result(res)
        corpus.synthesis_id = synthesis_id
        corpus.updated_at = time.time()
        await repo.save_corpus(corpus)
        return res

    llm = get_llm(role="planner", temperature=0.2)

    paper_list_str = "\n".join(
        f"[{p.paper_id}] '{p.title}' ({p.year}) - Abstract: {p.abstract[:250]}"
        for p in papers[:15]
    )
    ev_list_str = "\n".join(
        f"[{e.evidence_id} from {e.paper_id}] Claim: {e.claim_summary} (Quote: {e.exact_quote or 'N/A'})"
        for e in evidence[:20]
    )

    prompt = f"""Research Query: {corpus.query}

Included Papers:
{paper_list_str}

Extracted Evidence:
{ev_list_str}

Analyze the literature and extract:
1. "themes": 3-5 major thematic clusters with theme_name, description, paper_ids, evidence_ids.
2. "contradictions": 1-3 explicit contradictions or moderating conditions (e.g. Paper A vs Paper B under setting X vs Y) with topic, paper_a_id, claim_a, paper_b_id, claim_b, moderator_explanation.
3. "research_gaps": 2-4 open research gaps grounded in the corpus with gap_title, description, supporting_evidence_ids.

Return ONLY a valid JSON object with keys "themes", "contradictions", "research_gaps".
"""

    themes: List[Dict[str, Any]] = []
    contradictions: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []

    try:
        res = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = str(res.content).strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        themes = data.get("themes", [])
        contradictions = data.get("contradictions", [])
        gaps = data.get("research_gaps", [])
    except Exception as e:
        logger.warning(f"Synthesis LLM generation defaulted: {e}")
        # Fallback theme grouping
        themes = [{
            "theme_name": "General Literature Overview",
            "description": f"Retrieved literature discussing {corpus.query}",
            "paper_ids": corpus.included_paper_ids,
            "evidence_ids": corpus.evidence_ids
        }]

    synthesis_id = corpus.synthesis_id or f"syn_{uuid.uuid4().hex[:12]}"
    result = SynthesisResult(
        synthesis_id=synthesis_id,
        corpus_id=corpus_id,
        themes=themes,
        contradictions=contradictions,
        research_gaps=gaps,
        created_at=time.time()
    )

    await repo.save_synthesis_result(result)
    corpus.synthesis_id = synthesis_id
    await repo.save_corpus(corpus)

    logger.info(f"Generated SynthesisResult '{synthesis_id}' with {len(themes)} themes, {len(contradictions)} contradictions, {len(gaps)} gaps.")
    return result
