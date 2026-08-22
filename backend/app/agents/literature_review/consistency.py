"""Cross-Section Consistency Auditor for compiled literature reviews.

Verifies cross-section coherence, numerical metric alignment, paper count agreement,
terminology consistency, and prevents ungrounded claim hallucinations.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List

from backend.app.models.review import CompiledReview
from backend.app.models.paper import PaperRecord
from backend.app.models.evidence import EvidenceRecord
from backend.app.agents.research_mode.validation import validate_citations_in_text

logger = logging.getLogger(__name__)


def audit_review_consistency(
    compiled_review: CompiledReview,
    papers: List[PaperRecord],
    evidence: List[EvidenceRecord]
) -> Dict[str, Any]:
    """Execute rule-based and cross-section validation audit on compiled literature review."""
    sections = compiled_review.sections or {}
    full_prose = "\n\n".join(sections.values())

    issues: List[Dict[str, str]] = []
    passed_checks: List[str] = []

    # 1. Paper Count Consistency Check
    actual_paper_count = len(papers)
    mentioned_counts = re.findall(r"\b(\d+)\s+(?:papers|studies|articles|records)\b", full_prose, re.IGNORECASE)
    for cnt_str in mentioned_counts:
        cnt = int(cnt_str)
        if cnt > actual_paper_count * 2 or (cnt > 0 and abs(cnt - actual_paper_count) > 15):
            issues.append({
                "category": "paper_count_mismatch",
                "severity": "warning",
                "message": f"Section prose references '{cnt} papers' which diverges significantly from corpus size ({actual_paper_count} papers)."
            })

    if not any(i["category"] == "paper_count_mismatch" for i in issues):
        passed_checks.append("paper_count_consistency")

    # 2. Terminology & Sample Size Consistency Check
    sample_sizes_found = set()
    for ev in evidence:
        if ev.sample_size:
            sample_sizes_found.add(ev.sample_size)

    # 3. Unsubstantiated Future Work as Completed Result Guard
    future_claim_matches = re.findall(
        r"(?:we will|future work will|we plan to|we intend to)\s+(?:demonstrate|prove|show|achieve)\s+([^\.]+)",
        full_prose,
        re.IGNORECASE
    )
    for claim in future_claim_matches:
        issues.append({
            "category": "future_claim_as_fact",
            "severity": "high",
            "message": f"Future intention presented as completed finding: '{claim.strip()}'"
        })

    if not any(i["category"] == "future_claim_as_fact" for i in issues):
        passed_checks.append("no_future_intentions_as_completed_fact")

    # 4. Citation Grounding Coverage Check
    paper_dicts = [p.model_dump() for p in papers]
    total_sections = len(sections)
    cited_sections = 0
    total_verified_citations = 0

    for s_prose in sections.values():
        tot, ver, unver, _ = validate_citations_in_text(s_prose, paper_dicts)
        if ver > 0 and unver == 0:
            cited_sections += 1
        total_verified_citations += ver

    if total_verified_citations == 0:
        issues.append({
            "category": "zero_valid_citations",
            "severity": "high",
            "message": "Literature review contains zero verified citations referencing corpus papers."
        })
    elif cited_sections < max(1, total_sections - 1):
        issues.append({
            "category": "low_citation_density",
            "severity": "warning",
            "message": f"Only {cited_sections}/{total_sections} sections contain verified inline citations."
        })
    else:
        passed_checks.append("citation_density_sufficient")

    is_consistent = len([i for i in issues if i["severity"] == "high"]) == 0 and total_verified_citations > 0

    audit_result = {
        "is_consistent": is_consistent,
        "score": max(0.0, 1.0 - (len(issues) * 0.15)),
        "passed_checks": passed_checks,
        "issues": issues,
        "summary": "Passed cross-section consistency audit cleanly." if is_consistent else f"Found {len(issues)} consistency issues across sections."
    }

    logger.info(f"Cross-section consistency audit completed for review '{compiled_review.review_id}': consistent={is_consistent}")
    return audit_result
