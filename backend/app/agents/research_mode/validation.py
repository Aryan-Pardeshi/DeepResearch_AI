"""Phase 5 Deterministic Citation & Claim Validation Pipeline for Research Mode.

Enforces academic integrity gates, provenance verification, and PRISMA consistency.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Set, Tuple

from backend.app.models.evidence import ValidationReport, PRISMATracker, PaperRecord

logger = logging.getLogger(__name__)

# Regular expressions for identifying in-text APA citations
CITATION_PATTERN = re.compile(
    r"\(([A-Za-z\s\-&.,]+?),\s*(19\d\d|20\d\d)\)"
)

METRIC_KEYWORD_PATTERN = re.compile(
    r"(?:\b\d+\.?\d*|\d+)\s*(?:%|percent\b|BLEU\b|F1\b|accuracy\b|points\b|ms\b|seconds\b|x\b|fold\b)",
    re.IGNORECASE
)


def extract_numerical_claims(text: str) -> List[str]:
    """Extract individual sentences containing quantitative metrics or numerical performance claims."""
    if not text:
        return []
    sentences = re.split(r"(?<=[.?!])\s+", text)
    return [s.strip() for s in sentences if METRIC_KEYWORD_PATTERN.search(s)]


def validate_citations_in_text(
    text: str,
    paper_records: List[Dict[str, Any]]
) -> Tuple[int, int, List[str], List[str]]:
    """Validate all inline citations against the PaperRecord store."""
    if not text:
        return 0, 0, [], []

    # Build lookup index of (normalized_author, year) from paper records
    known_papers: Set[Tuple[str, str]] = set()
    for p in paper_records:
        year = str(p.get("year", "n.d."))
        authors = p.get("authors") or []
        for a in authors:
            if not a or not str(a).strip():
                continue
            tokens = str(a).split(",")[0].strip().split()
            if tokens:
                surname = tokens[-1].lower().strip()
                if len(surname) > 1:
                    known_papers.add((surname, year))

    matches = CITATION_PATTERN.findall(text)
    total_citations = len(matches)
    verified = 0
    unverified: List[str] = []

    # Shortest surname in the corpus: a citation surname shorter than this cannot
    # match any known record, so it must never be accepted on a year match alone.
    min_known_surname_len = min((len(k[0]) for k in known_papers), default=0)

    for author_str, year in matches:
        # Split on "and" only as a standalone word so surnames such as Rand,
        # Chandra, and Hollande survive intact.
        first_author = re.split(r"\band\b", author_str.split("&")[0])[0]
        first_author = first_author.replace("et al.", "").replace("et al", "").strip()
        tokens = first_author.split()
        if not tokens:
            unverified.append(f"({author_str}, {year})")
            continue
        surname = tokens[-1].lower().strip()

        # Require an exact (surname, year) match. The previous substring test
        # verified any citation whose surname merely contained (or was contained
        # by) a known surname with the same year.
        if len(surname) >= min_known_surname_len and (surname, year) in known_papers:
            verified += 1
        else:
            unverified.append(f"({author_str}, {year})")

    # Check for orphan references (papers never cited)
    orphan_references: List[str] = []
    text_lower = text.lower()
    for p in paper_records:
        authors = p.get("authors") or []
        if authors and authors[0] and str(authors[0]).strip():
            tokens = str(authors[0]).split(",")[0].strip().split()
            if tokens:
                surname = tokens[-1].lower().strip()
                if len(surname) > 2 and surname not in text_lower:
                    orphan_references.append(p.get("title", "Untitled"))

    return total_citations, verified, unverified, orphan_references


async def citation_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validator 1: Verifies all inline citations and flags orphan references."""
    papers = state.get("paper_records") or state.get("screened_papers") or []
    all_prose = " ".join([
        str(state.get("literature_review") or ""),
        str(state.get("results") or ""),
        str(state.get("discussion") or ""),
        str(state.get("introduction") or "")
    ])

    total, verified, unverified, orphans = validate_citations_in_text(all_prose, papers)
    logger.info(f"citation_validator: {verified}/{total} citations verified. {len(unverified)} unverified.")

    return {
        "unverified_citations": unverified,
    }


def _number_matches(claimed: float, expected: float, unit_or_scale: str = "") -> bool:
    """Compare a sentence number against an evidence value with scale tolerance.

    Accepts a direct match within a small relative tolerance, and also accepts
    percentage/fraction restatements (e.g. 0.942 reported as 94.2%) when the
    metric's unit or scale indicates a percentage.
    """
    candidates = [expected]
    unit = (unit_or_scale or "").lower()
    is_pct = "%" in unit or "percent" in unit
    if is_pct or 0 < abs(expected) <= 1:
        candidates.append(expected * 100.0)
    if is_pct or abs(expected) > 1:
        candidates.append(expected / 100.0)

    for cand in candidates:
        tolerance = max(abs(cand) * 0.01, 0.005)
        if abs(claimed - cand) <= tolerance:
            return True
    return False


def _mentions_metric(sentence_lower: str, metric_name: str) -> bool:
    """Check whether a sentence references the evidence metric by name."""
    metric = (metric_name or "").strip().lower()
    if not metric:
        return False
    if metric in sentence_lower:
        return True
    # Fall back to matching the metric's significant word tokens.
    tokens = [t for t in re.findall(r"[a-z0-9]+", metric) if len(t) > 2]
    return bool(tokens) and all(t in sentence_lower for t in tokens)


async def claim_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validator 2: Audits quantitative sentences against EvidenceRecord values."""
    ev_dicts = state.get("evidence_records") or []
    results_text = str(state.get("results") or "")

    # Metric-scoped expectations: a number is only grounded when the sentence
    # names the metric AND the number matches that metric's reported/baseline value.
    metric_expectations: List[Tuple[str, float, str]] = []
    for e in ev_dicts:
        metric_name = str(e.get("metric_name") or "").strip()
        if not metric_name:
            continue
        unit = str(e.get("unit_or_scale") or "")
        for field in ("reported_value", "baseline_value"):
            v = e.get(field)
            if v is None:
                continue
            try:
                metric_expectations.append((metric_name, float(v), unit))
            except (ValueError, TypeError):
                pass

    numerical_sentences = extract_numerical_claims(results_text)
    unsupported = []
    grounded_count = 0

    for sent in numerical_sentences:
        sent_lower = sent.lower()
        nums = []
        for n in re.findall(r"\b\d+\.?\d*\b", sent):
            try:
                nums.append(float(n))
            except (ValueError, TypeError):
                pass

        is_grounded = any(
            _mentions_metric(sent_lower, metric_name) and _number_matches(n, expected, unit)
            for metric_name, expected, unit in metric_expectations
            for n in nums
        )

        if is_grounded:
            grounded_count += 1
        else:
            unsupported.append(sent.strip())

    logger.info(f"claim_validator: {grounded_count}/{len(numerical_sentences)} numerical claims grounded.")
    return {
        "unsupported_numerical_claims": unsupported,
        "grounded_claims_count": grounded_count
    }


async def integrity_auditor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validator 3: Overall research integrity audit and PRISMA invariant verification."""
    raw_tr = state.get("prisma_tracker") or {}
    valid_keys = set(PRISMATracker.model_fields.keys())
    filtered_tr = {k: v for k, v in raw_tr.items() if k in valid_keys} if isinstance(raw_tr, dict) else {}
    tracker = PRISMATracker(**filtered_tr) if filtered_tr else PRISMATracker()
    prisma_errors = tracker.validate_invariants()

    papers = state.get("paper_records") or state.get("screened_papers") or []
    all_prose = " ".join([
        str(state.get("literature_review") or ""),
        str(state.get("results") or ""),
        str(state.get("discussion") or ""),
        str(state.get("introduction") or "")
    ])

    total_cites, verified_cites, unverified_cites, orphans = validate_citations_in_text(all_prose, papers)
    unsupported_claims = state.get("unsupported_numerical_claims") or []

    flags: List[str] = []
    if prisma_errors:
        flags.extend(prisma_errors)
    if unverified_cites:
        flags.append(f"{len(unverified_cites)} unverified inline citations found.")
    if unsupported_claims:
        flags.append(f"{len(unsupported_claims)} unsupported numerical claims flagged.")

    report = ValidationReport(
        total_inline_citations=total_cites,
        verified_citations=verified_cites,
        unverified_citations=unverified_cites,
        unsupported_claims=unsupported_claims,
        orphan_references=orphans[:10],
        prisma_invariants_valid=len(prisma_errors) == 0,
        integrity_flags=flags,
        passed_all_gates=len(flags) == 0
    )

    logger.info(f"integrity_auditor_node complete. Invariants valid: {report.prisma_invariants_valid}")
    return {
        "validation_report": report.model_dump()
    }
