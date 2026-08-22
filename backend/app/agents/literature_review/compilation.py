"""Section-compiler literature review document generator.
"""

from __future__ import annotations

import uuid
import time
import json
import logging
from typing import Dict, List, Optional
from langchain_core.messages import HumanMessage

from backend.app.models.review import CompiledReview
from backend.app.models.evidence import ReviewClaim, make_claim_id
from backend.app.storage.corpus_repository import get_corpus_repository
from backend.app.agents.research_mode.validation import validate_citations_in_text
from backend.app.llm import get_llm

logger = logging.getLogger(__name__)


async def compile_literature_review_document(corpus_id: str) -> CompiledReview:
    """Compile structured literature review prose section by section."""
    repo = get_corpus_repository()
    corpus = await repo.get_corpus(corpus_id)
    if not corpus:
        raise ValueError(f"Corpus '{corpus_id}' not found.")

    papers = await repo.get_papers(corpus.included_paper_ids)
    evidence = await repo.get_evidence_records_by_corpus(corpus_id)
    synthesis = await repo.get_synthesis_result(corpus_id)

    paper_dicts = [p.model_dump() for p in papers]

    outline = [
        "1. Introduction & Research Scope",
        "2. Thematic Analysis of Literature",
        "3. Methodological Comparisons & Contradictions",
        "4. Identified Research Gaps & Future Directions",
        "5. Conclusion"
    ]

    llm = get_llm(role="planner", temperature=0.2)
    sections: Dict[str, str] = {}
    all_claims: List[ReviewClaim] = []

    # Build paper & evidence lookup dictionary for LLM context and claim validation
    ev_by_paper: Dict[str, List[EvidenceRecord]] = {}
    for ev in evidence:
        ev_by_paper.setdefault(ev.paper_id, []).append(ev)

    paper_dicts = [p.model_dump() for p in papers]

    # Format paper citation dictionary with evidence records for LLM context
    citation_lines = []
    for p in papers[:15]:
        p_evs = ev_by_paper.get(p.paper_id, [])
        ev_summaries = "; ".join(f"[{e.evidence_id}: {e.claim_summary}]" for e in p_evs[:3])
        citation_lines.append(
            f"- [{p.paper_id}] {p.authors[0] if p.authors else 'Anon'} et al. ({p.year}). '{p.title}' "
            f"| Findings: {ev_summaries if ev_summaries else p.abstract[:150]}"
        )
    citation_guide = "\n".join(citation_lines)

    for sec_idx, sec_title in enumerate(outline):
        prompt = f"""Target Section: {sec_title}
Research Query: {corpus.query}

Available Paper Citations & Evidence Findings:
{citation_guide}

Thematic Context:
{json.dumps(synthesis.themes if synthesis else [])[:500]}

Instructions:
Write 2-3 detailed, academic paragraphs for the '{sec_title}' section.
Cite source papers using (Author et al., Year) format matching the available citations above.
Ensure claims are grounded strictly in the provided evidence.

Section Content:
"""
        sec_prose = ""
        try:
            res = await llm.ainvoke([HumanMessage(content=prompt)])
            sec_prose = str(res.content).strip()
        except Exception as e:
            logger.warning(f"Section generation defaulted for '{sec_title}': {e}")
            sec_prose = f"Literature synthesis for {sec_title}."

        sections[sec_title] = sec_prose

        # Extract claims per section and validate evidence citation
        sentences = [s.strip() for s in sec_prose.split(".") if len(s.strip()) > 15]
        for c_idx, stmt in enumerate(sentences[:4]):
            cid = make_claim_id(f"sec{sec_idx+1}", c_idx + 1)
            tot_c, ver_c, unver_c, _ = validate_citations_in_text(stmt, paper_dicts)
            matched_ev_ids = [
                ev.evidence_id for ev in evidence
                if any(w in stmt.lower() for w in (ev.claim_summary or "").lower().split() if len(w) > 4)
            ]
            is_valid = ver_c > 0 and len(matched_ev_ids) > 0 and unver_c == 0
            all_claims.append(ReviewClaim(
                claim_id=cid,
                claim_text=stmt + ".",
                target_section=sec_title,
                supporting_evidence_ids=matched_ev_ids[:3],
                validation_status="verified" if is_valid else "pending"
            ))

    review_id = f"rev_{uuid.uuid4().hex[:12]}"
    review = CompiledReview(
        review_id=review_id,
        corpus_id=corpus_id,
        title=f"Literature Review: {corpus.query}",
        outline=outline,
        sections=sections,
        claims=all_claims,
        consistency_audit={},
        created_at=time.time()
    )

    await repo.save_compiled_review(review)
    logger.info(f"Compiled LiteratureReview '{review_id}' across {len(outline)} sections.")
    return review
