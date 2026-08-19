from backend.app.agents.research_mode.validation import (
    validate_citations_in_text,
    extract_numerical_claims,
    CITATION_PATTERN,
)
from backend.app.models.evidence import PaperRecord, ValidationReport, PRISMATracker


def test_citation_pattern_regex():
    """Verify APA citation regex matches standard academic formats."""
    text = "Recent advances in transformers (Vaswani et al., 2017) and protein folding (Jumper & Hassabis, 2021) demonstrate scaling."
    matches = CITATION_PATTERN.findall(text)
    assert len(matches) == 2
    assert matches[0] == ("Vaswani et al.", "2017")
    assert matches[1] == ("Jumper & Hassabis", "2021")


def test_validate_citations_in_text():
    """Verify citation matcher correctly validates known papers and flags fake citations."""
    papers = [
        {"authors": ["Vaswani, A.", "Shazeer, N."], "year": "2017", "title": "Attention Is All You Need"},
        {"authors": ["Devlin, J.", "Chang, M."], "year": "2018", "title": "BERT"},
        {"authors": ["Orphan, X."], "year": "2020", "title": "Unused Reference Paper"}
    ]
    prose = "As demonstrated by (Vaswani et al., 2017) and verified by (Devlin et al., 2018), scaling works. However, (FakeAuthor et al., 2026) claimed otherwise."

    total, verified, unverified, orphans = validate_citations_in_text(prose, papers)
    assert total == 3
    assert verified == 2
    assert len(unverified) == 1
    assert "(FakeAuthor et al., 2026)" in unverified[0]
    assert len(orphans) == 1
    assert "Unused Reference Paper" in orphans[0]


def test_numerical_claim_regex():
    """Verify quantitative sentence extractor matches percentage and benchmark sentences."""
    text = "Our model achieves 94.2% accuracy on ImageNet. Previous approaches scored 88.5 BLEU. Qualitative behavior is sound."
    sentences = extract_numerical_claims(text)
    assert len(sentences) == 2
    assert "94.2% accuracy" in sentences[0]
    assert "88.5 BLEU" in sentences[1]
