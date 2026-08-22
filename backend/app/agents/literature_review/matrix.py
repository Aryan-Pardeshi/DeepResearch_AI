"""Dynamic Evidence Matrix extraction and cell provenance management module.
"""

from __future__ import annotations

import uuid
import time
import logging
from typing import Any, Dict, List, Optional

from backend.app.models.corpus import EvidenceMatrix, MatrixCell
from backend.app.storage.corpus_repository import get_corpus_repository
from backend.app.llm import get_llm

logger = logging.getLogger(__name__)

# Standard domain schema templates
MATRIX_TEMPLATES = {
    "computer_science": [
        {"key": "model", "label": "Model / Method", "description": "Architecture or algorithm proposed"},
        {"key": "dataset", "label": "Dataset / Benchmark", "description": "Evaluation dataset used"},
        {"key": "metric", "label": "Primary Metric", "description": "Accuracy, F1, BLEU, Latency, etc."},
        {"key": "baseline", "label": "Baseline Comparison", "description": "Previous SOTA baseline"},
        {"key": "result", "label": "Reported Result", "description": "Key numerical or qualitative result"},
        {"key": "limitations", "label": "Limitations", "description": "Stated weaknesses or bounds"},
    ],
    "biomedical": [
        {"key": "sample_size", "label": "Sample Size / Population", "description": "N count, organism, or cohort"},
        {"key": "intervention", "label": "Intervention / Exposure", "description": "Treatment, dose, or genetic variant"},
        {"key": "comparator", "label": "Comparator / Control", "description": "Control group or baseline"},
        {"key": "outcome", "label": "Primary Outcome", "description": "Measured clinical or molecular effect"},
        {"key": "effect_size", "label": "Effect Size / P-value", "description": "OR, HR, RR, or p-value"},
        {"key": "risk_of_bias", "label": "Risk of Bias", "description": "Blinding, randomization, or confounders"},
    ],
    "general": [
        {"key": "core_finding", "label": "Core Finding", "description": "Main discovery or thesis"},
        {"key": "methodology", "label": "Methodology", "description": "Study design or theoretical framework"},
        {"key": "sample_data", "label": "Dataset / Sample", "description": "Data sources or sample studied"},
        {"key": "key_result", "label": "Key Result", "description": "Primary quantitative/qualitative result"},
        {"key": "limitations", "label": "Limitations", "description": "Study limitations"},
    ]
}


async def generate_evidence_matrix(
    corpus_id: str,
    custom_columns: Optional[List[Dict[str, str]]] = None
) -> EvidenceMatrix:
    """Generate dynamic evidence matrix schema and populate cells from EvidenceRecords."""
    repo = get_corpus_repository()
    corpus = await repo.get_corpus(corpus_id)
    if not corpus:
        raise ValueError(f"Corpus '{corpus_id}' not found.")

    papers = await repo.get_papers(corpus.included_paper_ids)
    evidence = await repo.get_evidence_records_by_corpus(corpus_id)

    # Determine column schema
    if custom_columns:
        columns = custom_columns
    else:
        domain = (corpus.domain_profile or {}).get("primary_domain", "general")
        columns = MATRIX_TEMPLATES.get(domain, MATRIX_TEMPLATES["general"])

    ev_by_paper: Dict[str, List[Any]] = {}
    for ev in evidence:
        ev_by_paper.setdefault(ev.paper_id, []).append(ev)

    matrix_rows: Dict[str, Dict[str, MatrixCell]] = {}

    for paper in papers:
        pid = paper.paper_id
        paper_ev = ev_by_paper.get(pid, [])
        ev_ids = [e.evidence_id for e in paper_ev]
        row_cells: Dict[str, MatrixCell] = {}

        for col in columns:
            col_key = col["key"]
            val = None
            matching_ev_ids: List[str] = []

            # Matching from EvidenceRecord fields
            for ev in paper_ev:
                matched = False
                if col_key == "model" and ev.model_or_method:
                    val = ev.model_or_method
                    matched = True
                elif col_key == "dataset" and ev.dataset:
                    val = ev.dataset
                    matched = True
                elif col_key == "metric" and ev.metric_name:
                    val = f"{ev.metric_name}: {ev.reported_value or ''}"
                    matched = True
                elif col_key in ("sample_size", "sample_data") and ev.sample_size:
                    val = ev.sample_size
                    matched = True
                elif col_key in ("key_result", "core_finding") and ev.claim_summary:
                    val = ev.claim_summary
                    matched = True
                elif col_key == "limitations" and ev.limitations:
                    val = ev.limitations
                    matched = True

                if matched:
                    matching_ev_ids.append(ev.evidence_id)

            if val and matching_ev_ids:
                status = "source_supported"
                src_ids = matching_ev_ids
            else:
                val = paper.abstract[:150] + "..." if paper.abstract else "Not specified"
                status = "unverified"
                src_ids = []

            row_cells[col_key] = MatrixCell(
                cell_value=val,
                source_evidence_ids=src_ids,
                origin="ai",
                validation_status=status
            )

        matrix_rows[pid] = row_cells

    matrix_id = corpus.matrix_id or f"mat_{uuid.uuid4().hex[:12]}"
    matrix = EvidenceMatrix(
        matrix_id=matrix_id,
        corpus_id=corpus_id,
        columns=columns,
        rows=matrix_rows
    )

    await repo.save_evidence_matrix(matrix)
    corpus.matrix_id = matrix_id
    corpus.updated_at = time.time()
    await repo.save_corpus(corpus)

    logger.info(f"Generated EvidenceMatrix '{matrix_id}' with {len(columns)} columns across {len(papers)} papers.")
    return matrix


async def update_matrix_cell(
    corpus_id: str,
    paper_id: str,
    column_key: str,
    new_value: Any
) -> EvidenceMatrix:
    """Update a matrix cell value and tag origin as 'human' with status 'human_edited'."""
    repo = get_corpus_repository()
    matrix = await repo.get_evidence_matrix(corpus_id)
    if not matrix:
        raise ValueError(f"Evidence matrix for corpus '{corpus_id}' not found.")

    if paper_id not in matrix.rows:
        raise ValueError(f"Invalid paper_id '{paper_id}' for matrix.")

    valid_col_keys = [col["key"] if isinstance(col, dict) else col for col in matrix.columns]
    if column_key not in valid_col_keys:
        raise ValueError(f"Invalid column_key '{column_key}' for matrix schema.")

    existing_cell = matrix.rows[paper_id].get(column_key)
    source_ids = existing_cell.source_evidence_ids if existing_cell else []

    matrix.rows[paper_id][column_key] = MatrixCell(
        cell_value=new_value,
        source_evidence_ids=source_ids,
        origin="human",
        validation_status="human_edited"
    )

    await repo.save_evidence_matrix(matrix)
    logger.info(f"Updated cell ({paper_id}, {column_key}) in matrix '{matrix.matrix_id}' (origin: human).")
    return matrix
