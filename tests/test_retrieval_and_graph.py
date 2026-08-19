"""Unit tests for Stage 6: Multi-Source Retrieval Tools and Deduplication."""

import pytest
from backend.app.models.evidence import PaperRecord, PRISMATracker
from backend.app.tools.crossref_search import search_crossref, _clean_abstract
from backend.app.tools.opencitations_search import _clean_doi
from backend.app.tools.academic_search import (
    _normalize_doi,
    _normalize_title,
    _select_candidates,
    format_apa,
)


def test_clean_abstract_and_doi():
    """Test XML stripping in Crossref abstract and DOI canonicalization."""
    raw_jats = "<jats:p>We propose a new <jats:bold>deep learning</jats:bold> framework.</jats:p>"
    clean = _clean_abstract(raw_jats)
    assert clean == "We propose a new deep learning framework."

    doi1 = _normalize_doi("https://doi.org/10.1038/s41586-021-03819-2")
    doi2 = _normalize_doi("doi:10.1038/s41586-021-03819-2")
    assert doi1 == "10.1038/s41586-021-03819-2"
    assert doi1 == doi2
    assert _clean_doi("http://doi.org/10.1234/test") == "10.1234/test"


def test_normalize_title():
    """Test title normalization ignores punctuation, whitespace, and case."""
    t1 = _normalize_title("Deep Learning in 2026: A Survey!")
    t2 = _normalize_title("deep learning in 2026 a survey")
    assert t1 == t2
    assert t1 == "deeplearningin2026asurvey"


def test_select_candidates_round_robin():
    """Test round-robin candidate pool selection across sources."""
    papers = [
        PaperRecord(paper_id=f"oa_{i}", title=f"OA Paper {i}", retrieval_source="openalex", citation_count=100 - i)
        for i in range(10)
    ] + [
        PaperRecord(paper_id=f"ax_{i}", title=f"ArXiv Paper {i}", retrieval_source="arxiv", citation_count=0)
        for i in range(10)
    ]
    candidates = _select_candidates(papers, limit=6)
    assert len(candidates) == 6
    sources = [c.retrieval_source for c in candidates]
    assert "openalex" in sources
    assert "arxiv" in sources


def test_format_apa():
    """Test APA 7th edition citation formatting."""
    paper = {
        "title": "Attention Is All You Need",
        "authors": ["Vaswani, A.", "Shazeer, N.", "Parmar, N."],
        "year": "2017",
        "doi": "10.48550/arXiv.1706.03762",
        "venue": "Advances in Neural Information Processing Systems",
    }
    apa = format_apa(paper)
    assert "Vaswani, A., Shazeer, N., & Parmar, N. (2017). Attention Is All You Need." in apa
    assert "https://doi.org/10.48550/arXiv.1706.03762" in apa
