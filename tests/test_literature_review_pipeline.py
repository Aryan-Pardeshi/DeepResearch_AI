"""End-to-end integration tests for Literature Review pipeline.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.models.paper import PaperRecord
from backend.app.models.corpus import EvidenceMatrix, MatrixCell
from backend.app.tools.academic_router import DomainProfile
from backend.app.storage.corpus_repository import get_corpus_repository
from backend.app.agents.literature_review import (
    create_literature_corpus,
    get_literature_corpus_workspace,
    update_paper_screening,
    generate_evidence_matrix,
    update_matrix_cell,
    generate_thematic_synthesis,
    ask_corpus_grounded,
    compile_literature_review_document,
    audit_review_consistency,
    bridge_corpus_to_research_mode
)


@pytest.mark.asyncio
async def test_literature_review_pipeline_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_lr_pipeline.db")
        repo = get_corpus_repository(db_path=db_path)
        await repo.initialize()

        p1 = PaperRecord(
            paper_id="paper_1",
            doi="10.1000/p1",
            title="Transformer Networks for Medical Image Segmentation",
            authors=["Smith, J.", "Doe, A."],
            year="2023",
            venue="Medical Physics",
            abstract="We evaluate vision transformers on medical image segmentation, achieving 94.2% Dice score.",
            retrieval_source="openalex"
        )
        p2 = PaperRecord(
            paper_id="paper_2",
            doi="10.1000/p2",
            title="CNN Baseline Comparison in Radiomics",
            authors=["Johnson, M."],
            year="2022",
            venue="Radiology AI",
            abstract="Convolutional neural networks achieve 89.1% Dice score under noisy dataset conditions.",
            retrieval_source="pubmed"
        )

        dp = DomainProfile(primary_domain="biomedical", recommended_providers=["pubmed", "openalex"])
        corpus = await create_literature_corpus("Medical image segmentation transformers", [p1, p2], dp)
        assert corpus.corpus_id.startswith("corp_")

        # 1. Test workspace fetch
        workspace = await get_literature_corpus_workspace(corpus.corpus_id)
        assert workspace is not None
        assert workspace["stats"]["total_found"] == 2

        # 2. Test screening update
        updated_corpus = await update_paper_screening(corpus.corpus_id, "paper_2", "excluded", "Outdated methodology")
        assert "paper_2" in updated_corpus.excluded_paper_ids

        # 3. Test Evidence Matrix generation & cell edit provenance
        matrix = await generate_evidence_matrix(corpus.corpus_id)
        assert matrix.matrix_id is not None
        assert "paper_1" in matrix.rows

        # Edit cell and verify provenance tag turns into 'human' and rejects invalid paper_id / col_key
        updated_matrix = await update_matrix_cell(corpus.corpus_id, "paper_1", "outcome", "Edited 96.5% Dice Score")
        assert updated_matrix.rows["paper_1"]["outcome"].origin == "human"
        assert updated_matrix.rows["paper_1"]["outcome"].validation_status == "human_edited"

        with pytest.raises(ValueError, match="Invalid paper_id"):
            await update_matrix_cell(corpus.corpus_id, "invalid_paper_id", "outcome", "test")

        with pytest.raises(ValueError, match="Invalid column_key"):
            await update_matrix_cell(corpus.corpus_id, "paper_1", "invalid_col_key", "test")

        # 4. Test Synthesis Engine (with distinct mock response)
        syn_mock_resp = MagicMock()
        syn_mock_resp.content = '{"themes": [{"theme_name": "Vision Transformers", "description": "High segmentation accuracy.", "paper_ids": ["paper_1"]}], "contradictions": [], "research_gaps": []}'
        syn_llm = MagicMock()
        syn_llm.ainvoke = AsyncMock(return_value=syn_mock_resp)

        with patch("backend.app.agents.literature_review.synthesis.get_llm", return_value=syn_llm):
            synthesis = await generate_thematic_synthesis(corpus.corpus_id)
            assert synthesis.synthesis_id is not None
            assert len(synthesis.themes) == 1

        # 5. Test Grounded Q&A (with grounded citation answer fixture)
        qa_mock_resp = MagicMock()
        qa_mock_resp.content = "Vision transformers achieved a 94.2% Dice score on medical image segmentation tasks (Smith et al., 2023)."
        qa_llm = MagicMock()
        qa_llm.ainvoke = AsyncMock(return_value=qa_mock_resp)

        with patch("backend.app.agents.literature_review.qa.get_llm", return_value=qa_llm):
            qa_res = await ask_corpus_grounded(corpus.corpus_id, "What Dice score did transformers achieve?")
            assert qa_res["corpus_id"] == corpus.corpus_id
            assert "Smith et al., 2023" in qa_res["answer"]
            assert qa_res["validation"]["verified_citations"] > 0
            assert qa_res["validation"]["is_grounded"] is True

        # 6. Test Review Compilation & Consistency Auditor (with section prose fixture)
        comp_mock_resp = MagicMock()
        comp_mock_resp.content = "Vision transformers significantly outperform legacy baselines (Smith et al., 2023). Empirical evaluation demonstrates robust performance across benchmark datasets."
        comp_llm = MagicMock()
        comp_llm.ainvoke = AsyncMock(return_value=comp_mock_resp)

        with patch("backend.app.agents.literature_review.compilation.get_llm", return_value=comp_llm):
            review = await compile_literature_review_document(corpus.corpus_id)
            assert review.review_id.startswith("rev_")
            assert len(review.sections) == 5
            audit = audit_review_consistency(review, [p1], [])
            assert audit["is_consistent"] is True

        # 7. Test Bridge to Research Mode Adapter
        rm_state = await bridge_corpus_to_research_mode(corpus.corpus_id)
        assert rm_state["problem_statement"] == "Medical image segmentation transformers"
        assert len(rm_state["paper_records"]) == 1  # Only included paper p1
        assert rm_state["hitl_checkpoint"] == "checkpoint_1_approved"
