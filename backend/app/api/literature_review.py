"""FastAPI endpoints for Literature Review Mode.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.agents.literature_review import (
    execute_literature_search,
    create_literature_corpus,
    get_literature_corpus_workspace,
    update_paper_screening,
    extract_corpus_evidence,
    generate_evidence_matrix,
    update_matrix_cell,
    generate_thematic_synthesis,
    ask_corpus_grounded,
    compile_literature_review_document,
    audit_review_consistency,
    bridge_corpus_to_research_mode,
)
from backend.app.models.paper import PaperRecord
from backend.app.storage.corpus_repository import get_corpus_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/literature-review", tags=["Literature Review"])


class SearchRequest(BaseModel):
    query: str
    mode: str = "standard"  # quick, standard, deep


class CreateCorpusRequest(BaseModel):
    query: str
    domain_profile: Dict[str, Any]
    papers: List[Dict[str, Any]]


class ScreenPaperRequest(BaseModel):
    paper_id: str
    status: str  # "included" or "excluded"
    exclusion_reason: Optional[str] = None


class MatrixCellUpdateRequest(BaseModel):
    paper_id: str
    column_key: str
    new_value: Any


class AskCorpusRequest(BaseModel):
    question: str


@router.post("/search")
async def search_literature(req: SearchRequest):
    """Execute multi-provider discovery and deduplication."""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        papers, profile, stats = await execute_literature_search(req.query.strip(), mode=req.mode)
        return {
            "query": req.query,
            "domain_profile": profile.model_dump(),
            "papers": [p.model_dump() for p in papers],
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Literature search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corpus")
async def initialize_corpus(req: CreateCorpusRequest):
    """Initialize a persistent LiteratureCorpus workspace in SQLite."""
    try:
        paper_records = [PaperRecord.from_dict(p) for p in req.papers]
        from backend.app.tools.academic_router import DomainProfile
        dp = DomainProfile(**req.domain_profile) if req.domain_profile else DomainProfile()
        corpus = await create_literature_corpus(req.query, paper_records, dp)
        return corpus.model_dump()
    except Exception as e:
        logger.error(f"Corpus initialization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corpus/{corpus_id}")
async def fetch_corpus(corpus_id: str):
    """Fetch literature review corpus workspace state."""
    workspace = await get_literature_corpus_workspace(corpus_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Corpus '{corpus_id}' not found.")
    return workspace


@router.post("/corpus/{corpus_id}/screen")
async def screen_paper(corpus_id: str, req: ScreenPaperRequest):
    """Update paper inclusion/exclusion status with structured reason."""
    try:
        corpus = await update_paper_screening(
            corpus_id, req.paper_id, req.status, exclusion_reason=req.exclusion_reason
        )
        return corpus.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Screening error for corpus '{corpus_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corpus/{corpus_id}/extract")
async def extract_evidence(corpus_id: str):
    """Extract structured EvidenceRecords for included papers."""
    try:
        records = await extract_corpus_evidence(corpus_id)
        return {"corpus_id": corpus_id, "evidence_records": [r.model_dump() for r in records]}
    except ValueError as e:
        if "not found" in str(e).lower() or "corpus" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Extraction error for corpus '{corpus_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corpus/{corpus_id}/matrix")
async def generate_matrix(corpus_id: str, custom_columns: Optional[List[Dict[str, str]]] = None):
    """Generate dynamic evidence matrix schema and populate cells."""
    try:
        matrix = await generate_evidence_matrix(corpus_id, custom_columns=custom_columns)
        return matrix.model_dump()
    except ValueError as e:
        if "not found" in str(e).lower() or "corpus" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Matrix generation error for corpus '{corpus_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corpus/{corpus_id}/matrix/cell")
async def update_cell(corpus_id: str, req: MatrixCellUpdateRequest):
    """Update matrix cell value and tag origin as 'human'."""
    try:
        matrix = await update_matrix_cell(corpus_id, req.paper_id, req.column_key, req.new_value)
        return matrix.model_dump()
    except ValueError as e:
        if "not found" in str(e).lower() or "corpus" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Matrix cell update error for corpus '{corpus_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corpus/{corpus_id}/ask")
async def ask_corpus(corpus_id: str, req: AskCorpusRequest):
    """Grounded Q&A over corpus evidence with validated inline citations."""
    try:
        result = await ask_corpus_grounded(corpus_id, req.question)
        return result
    except ValueError as e:
        if "not found" in str(e).lower() or "corpus" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ask corpus error for '{corpus_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corpus/{corpus_id}/synthesis")
async def synthesis_literature(corpus_id: str):
    """Run thematic clustering, explicit contradiction detection, and research gap extraction."""
    try:
        synthesis = await generate_thematic_synthesis(corpus_id)
        return synthesis.model_dump()
    except ValueError as e:
        if "not found" in str(e).lower() or "corpus" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Synthesis error for corpus '{corpus_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corpus/{corpus_id}/generate")
async def generate_review(corpus_id: str):
    """Compile structured section-by-section literature review document with consistency audit."""
    try:
        review = await compile_literature_review_document(corpus_id)
        repo = get_corpus_repository()
        papers = await repo.get_papers(review.corpus_id) # wait, get_papers needs paper_ids
        corpus = await repo.get_corpus(corpus_id)
        p_records = await repo.get_papers(corpus.included_paper_ids) if corpus else []
        ev_records = await repo.get_evidence_records_by_corpus(corpus_id)
        audit = audit_review_consistency(review, p_records, ev_records)
        review.consistency_audit = audit
        await repo.save_compiled_review(review)
        return review.model_dump()
    except ValueError as e:
        if "not found" in str(e).lower() or "corpus" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Review compilation error for corpus '{corpus_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corpus/{corpus_id}/bridge-to-research")
async def bridge_to_research_mode(corpus_id: str):
    """Bridge LiteratureCorpus into ResearchModeState dictionary for seamless handover."""
    try:
        rm_state = await bridge_corpus_to_research_mode(corpus_id)
        return rm_state
    except ValueError as e:
        if "not found" in str(e).lower() or "corpus" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Bridge to research error for corpus '{corpus_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
