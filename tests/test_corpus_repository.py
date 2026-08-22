"""Unit tests for CorpusRepository SQLite DAO.
"""

import pytest
import tempfile
import os
from backend.app.models.paper import PaperRecord
from backend.app.models.corpus import LiteratureCorpus, EvidenceMatrix, MatrixCell
from backend.app.models.evidence import EvidenceRecord
from backend.app.storage.corpus_repository import CorpusRepository


@pytest.mark.asyncio
async def test_corpus_repository_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_research_state.db")
        repo = CorpusRepository(db_path=db_path)
        await repo.initialize()

        paper = PaperRecord(
            paper_id="paper_test_001",
            doi="10.1000/test.doi",
            title="Test Paper Title",
            authors=["Author One", "Author Two"],
            year="2024",
            venue="Test Journal",
            abstract="Abstract of test paper.",
            retrieval_source="openalex"
        )
        await repo.save_papers([paper])

        fetched_papers = await repo.get_papers(["paper_test_001"])
        assert len(fetched_papers) == 1
        assert fetched_papers[0].title == "Test Paper Title"

        corpus = LiteratureCorpus(
            corpus_id="corp_test_001",
            query="Test research query",
            domain_profile={"primary_domain": "computer_science"},
            paper_ids=["paper_test_001"],
            included_paper_ids=["paper_test_001"],
            excluded_paper_ids=[],
            exclusion_reasons={}
        )
        await repo.save_corpus(corpus)

        fetched_corpus = await repo.get_corpus("corp_test_001")
        assert fetched_corpus is not None
        assert fetched_corpus.query == "Test research query"
        assert fetched_corpus.included_paper_ids == ["paper_test_001"]

        # Test EvidenceMatrix CRUD
        matrix = EvidenceMatrix(
            matrix_id="mat_test_001",
            corpus_id="corp_test_001",
            columns=[{"key": "model", "label": "Model"}],
            rows={
                "paper_test_001": {
                    "model": MatrixCell(cell_value="Transformer", origin="ai", validation_status="source_supported")
                }
            }
        )
        await repo.save_evidence_matrix(matrix)

        fetched_matrix = await repo.get_evidence_matrix("corp_test_001")
        assert fetched_matrix is not None
        assert fetched_matrix.rows["paper_test_001"]["model"].cell_value == "Transformer"
