"""Literature Review modular agent subsystem.
"""

from backend.app.agents.literature_review.search import execute_literature_search
from backend.app.agents.literature_review.corpus import create_literature_corpus, get_literature_corpus_workspace
from backend.app.agents.literature_review.screening import update_paper_screening
from backend.app.agents.literature_review.extraction import extract_corpus_evidence
from backend.app.agents.literature_review.matrix import generate_evidence_matrix, update_matrix_cell
from backend.app.agents.literature_review.synthesis import generate_thematic_synthesis
from backend.app.agents.literature_review.qa import ask_corpus_grounded
from backend.app.agents.literature_review.compilation import compile_literature_review_document
from backend.app.agents.literature_review.consistency import audit_review_consistency
from backend.app.agents.literature_review.adapter import bridge_corpus_to_research_mode

__all__ = [
    "execute_literature_search",
    "create_literature_corpus",
    "get_literature_corpus_workspace",
    "update_paper_screening",
    "extract_corpus_evidence",
    "generate_evidence_matrix",
    "update_matrix_cell",
    "generate_thematic_synthesis",
    "ask_corpus_grounded",
    "compile_literature_review_document",
    "audit_review_consistency",
    "bridge_corpus_to_research_mode",
]
