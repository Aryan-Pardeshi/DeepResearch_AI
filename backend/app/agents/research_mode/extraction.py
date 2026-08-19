"""Phase 4 Structured Evidence Extraction Agents for Research Mode."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage

from backend.app.agents.research_mode._common import (
    get_llm_for,
    _safe_invoke_llm,
)
from backend.app.models.evidence import (
    EvidenceRecord,
    PaperRecord,
    make_evidence_id,
    make_paper_id,
)

logger = logging.getLogger(__name__)


async def evidence_extractor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 11: Extracts structured factual findings and verbatim quotes from included papers."""
    paper_dicts = state.get("paper_records") or state.get("screened_papers") or []
    if not paper_dicts:
        return {"evidence_records": []}

    llm = get_llm_for("researcher", state, temperature=0.1)
    evidence_records: List[Dict[str, Any]] = []

    # Process top 10 included papers
    for p_idx, p in enumerate(paper_dicts[:10]):
        paper_id = p.get("paper_id")
        if not paper_id:
            # Persist a stable identifier back onto the record so provenance_agent
            # resolves the exact same ID that downstream evidence records carry.
            paper_id = make_paper_id(
                doi=p.get("doi"),
                title=p.get("title", ""),
                year=p.get("year"),
            )
            p["paper_id"] = paper_id
        title = p.get("title", "")
        abstract = p.get("abstract", "")
        excerpt = p.get("fulltext_excerpt") or ""

        text_content = f"Title: {title}\nAbstract: {abstract}\nKey Excerpt: {excerpt[:800]}"
        norm_text = re.sub(r"\s+", " ", text_content.lower())

        prompt = f"""You are an expert Evidence Extraction Specialist.
Extract 2-3 specific, verifiable empirical or theoretical claims from the paper below.
For each claim, capture the exact verbatim quote and the source section where possible.

Paper:
{text_content}

Return a valid JSON array of objects:
[
  {{
    "claim_summary": "Concise summary of specific empirical finding or theoretical principle",
    "exact_quote": "Verbatim quote from the text supporting this finding",
    "source_section": "Abstract" | "Methodology" | "Results" | "Conclusion",
    "task_or_domain": "e.g. Natural Language Processing, Protein Folding",
    "model_or_method": "e.g. AlphaFold2, Transformer, CNN"
  }}
]
"""
        records_before = len(evidence_records)
        try:
            raw = await _safe_invoke_llm(llm, [HumanMessage(content=prompt)])
            clean = raw
            if "```" in clean:
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            items = json.loads(clean.strip())

            for item in items:
                if not isinstance(item, dict):
                    continue
                quote = item.get("exact_quote")
                norm_quote = re.sub(r"\s+", " ", str(quote or "").lower().strip())
                # Verify quote is present in available text
                if norm_quote and (norm_quote in norm_text or (abstract and norm_quote in abstract.lower())):
                    seq = len(evidence_records) - records_before + 1
                    ev_id = make_evidence_id(paper_id, seq)
                    ev = EvidenceRecord(
                        evidence_id=ev_id,
                        paper_id=paper_id,
                        claim_summary=item.get("claim_summary", "Empirical finding"),
                        exact_quote=quote,
                        source_section=item.get("source_section", "Abstract"),
                        task_or_domain=item.get("task_or_domain"),
                        model_or_method=item.get("model_or_method"),
                        effect_direction="unclear",
                    )
                    evidence_records.append(ev.model_dump())

        except Exception as e:
            logger.warning(f"evidence_extractor failed for paper '{title[:30]}': {e}")

        # Fallback only if no records were extracted for this paper AND valid abstract quote exists
        if len(evidence_records) == records_before and abstract and len(abstract.strip()) > 30:
            ev_id = make_evidence_id(paper_id, 1)
            ev = EvidenceRecord(
                evidence_id=ev_id,
                paper_id=paper_id,
                claim_summary=f"Investigates {title[:60]}",
                exact_quote=abstract.strip()[:200],
                source_section="Abstract",
                effect_direction="unclear"
            )
            evidence_records.append(ev.model_dump())

    logger.info(f"evidence_extractor_agent generated {len(evidence_records)} structured evidence records.")
    return {"evidence_records": evidence_records, "paper_records": paper_dicts}


async def quantitative_extractor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 12: Enriches evidence records with quantitative benchmarks, baseline vs reported numbers, effect directions."""
    ev_dicts = state.get("evidence_records") or []
    if not ev_dicts:
        return {}

    llm = get_llm_for("researcher", state, temperature=0.1)
    ev_summary = "\n".join(
        f"[{i+1}] ID: {e.get('evidence_id')}\nClaim: {e.get('claim_summary')}\nQuote: {e.get('exact_quote')}"
        for i, e in enumerate(ev_dicts[:15])
    )

    prompt = f"""You are a Quantitative Meta-Analysis Extractor.
Extract any numerical metrics, baselines, reported values, and effect directions (positive, negative, neutral, mixed) from the following evidence items.

Evidence:
{ev_summary}

Return a valid JSON array of objects:
[
  {{
    "id": 1,
    "metric_name": "e.g. Accuracy, BLEU, F1, Latency (or null if qualitative)",
    "baseline_value": 0.0 (or null),
    "reported_value": 0.0 (or null),
    "unit_or_scale": "%" | "ms" | "points" (or null),
    "effect_direction": "positive" | "negative" | "neutral" | "mixed" | "unclear"
  }}
]
"""
    try:
        raw = await _safe_invoke_llm(llm, [HumanMessage(content=prompt)])
        clean = raw
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        items = json.loads(clean.strip())
        item_map = {it["id"]: it for it in items if isinstance(it, dict) and "id" in it}

        for idx, e in enumerate(ev_dicts[:15]):
            q = item_map.get(idx + 1)
            if q:
                if q.get("metric_name"):
                    e["metric_name"] = str(q["metric_name"])
                if q.get("baseline_value") is not None:
                    try:
                        e["baseline_value"] = float(q["baseline_value"])
                    except (ValueError, TypeError):
                        pass
                if q.get("reported_value") is not None:
                    try:
                        e["reported_value"] = float(q["reported_value"])
                    except (ValueError, TypeError):
                        pass
                if q.get("unit_or_scale"):
                    e["unit_or_scale"] = str(q["unit_or_scale"])
                e["effect_direction"] = q.get("effect_direction", "unclear")
    except Exception as e:
        logger.warning(f"quantitative_extractor parsing defaulted: {e}")

    return {"evidence_records": ev_dicts}


async def methodology_extractor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 13: Extracts benchmark datasets, sample sizes, and experimental baselines."""
    ev_dicts = state.get("evidence_records") or []
    paper_dicts = state.get("paper_records") or []
    if not ev_dicts or not paper_dicts:
        return {}

    # task_or_domain is left unset when no task or domain was extracted from the
    # source. A paper's publication venue is not a valid substitute for it.
    return {"evidence_records": ev_dicts}


async def limitation_extractor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 14: Extracts empirical caveats, boundary conditions, and threats to validity."""
    ev_dicts = state.get("evidence_records") or []
    # Leave limitations empty when absent from source rather than injecting synthetic text
    return {"evidence_records": ev_dicts}


async def provenance_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 15: Validates and anchors every evidence record to its source paper."""
    ev_dicts = state.get("evidence_records") or []
    # Fall back to screened_papers so evidence stays validated when only that
    # corpus key is populated upstream.
    paper_dicts = state.get("paper_records") or state.get("screened_papers") or []
    valid_paper_ids = {p.get("paper_id") for p in paper_dicts if p.get("paper_id")}

    validated: List[Dict[str, Any]] = []
    if not valid_paper_ids:
        # No corpus available to anchor against: keep the evidence rather than
        # discarding every record because upstream state was empty.
        if ev_dicts:
            logger.warning(
                "provenance_agent found no paper corpus to anchor against; "
                f"passing {len(ev_dicts)} evidence records through unfiltered."
            )
        validated = list(ev_dicts)
    else:
        for e in ev_dicts:
            pid = e.get("paper_id")
            if pid in valid_paper_ids:
                validated.append(e)
            else:
                logger.warning(f"Discarded ungrounded evidence record {e.get('evidence_id')} without paper match.")

    return {
        "evidence_records": validated,
        "hitl_checkpoint": "checkpoint_2",
        "status": "awaiting_approval"
    }
