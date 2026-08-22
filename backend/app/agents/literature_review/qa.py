"""Grounded Corpus Q&A interface with claim validation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage

from backend.app.models.evidence import ReviewClaim, make_claim_id
from backend.app.storage.corpus_repository import get_corpus_repository
from backend.app.agents.research_mode.validation import validate_citations_in_text
from backend.app.llm import get_llm

logger = logging.getLogger(__name__)


async def ask_corpus_grounded(
    corpus_id: str,
    question: str
) -> Dict[str, Any]:
    """Execute grounded RAG over corpus EvidenceRecords with citation & claim validation."""
    repo = get_corpus_repository()
    corpus = await repo.get_corpus(corpus_id)
    if not corpus:
        raise ValueError(f"Corpus '{corpus_id}' not found.")

    papers = await repo.get_papers(corpus.included_paper_ids)
    evidence = await repo.get_evidence_records_by_corpus(corpus_id)

    paper_dicts = [p.model_dump() for p in papers]

    # Build context from extracted evidence and paper abstracts
    ev_context_lines = []
    for ev in evidence[:25]:
        p = next((paper for paper in papers if paper.paper_id == ev.paper_id), None)
        author_lead = p.authors[0] if (p and p.authors) else "Unknown"
        year = p.year if p else "n.d."
        ev_context_lines.append(
            f"[{ev.evidence_id}] ({author_lead}, {year}) - Claim: {ev.claim_summary} "
            f"| Quote: '{ev.exact_quote or ''}'"
        )

    context_str = "\n".join(ev_context_lines)
    llm = get_llm(role="researcher", temperature=0.1)

    prompt = f"""Question: {question}

Corpus Grounding Context (Use ONLY this context to answer):
{context_str}

Instructions:
1. Answer the question directly and concisely based strictly on the provided evidence context.
2. Cite sources using (Author, Year) format matching the context.
3. If the context does not contain sufficient evidence, state clearly what is missing.

Answer:
"""

    answer_text = ""
    try:
        res = await llm.ainvoke([HumanMessage(content=prompt)])
        answer_text = str(res.content).strip()
    except Exception as e:
        logger.warning(f"Corpus Q&A LLM invocation defaulted: {e}")
        answer_text = f"Could not generate grounded answer due to error: {e}"

    # Validate citations against paper records
    total_c, verified_c, unverified_c, _ = validate_citations_in_text(answer_text, paper_dicts)

    # Convert sentences into ReviewClaims
    sentences = [s.strip() for s in answer_text.split(".") if len(s.strip()) > 10]
    claims: List[ReviewClaim] = []
    for idx, stmt in enumerate(sentences[:10]):
        cid = make_claim_id("qa", idx + 1)
        stmt_tot, stmt_ver, stmt_unver, _ = validate_citations_in_text(stmt, paper_dicts)
        matched_ev = [ev.evidence_id for ev in evidence if any(w in stmt.lower() for w in (ev.task_or_domain or "").lower().split() if len(w) > 4)]
        is_verified = stmt_ver > 0 and len(matched_ev) > 0 and stmt_unver == 0
        claims.append(ReviewClaim(
            claim_id=cid,
            claim_text=stmt + ".",
            target_section="qa",
            supporting_evidence_ids=matched_ev[:3],
            validation_status="verified" if is_verified else "pending"
        ))

    return {
        "corpus_id": corpus_id,
        "question": question,
        "answer": answer_text,
        "claims": [c.model_dump() for c in claims],
        "validation": {
            "total_citations": total_c,
            "verified_citations": verified_c,
            "unverified_citations": unverified_c,
            "is_grounded": verified_c > 0
        }
    }
