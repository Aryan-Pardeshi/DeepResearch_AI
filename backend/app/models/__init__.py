"""Models package for AI Research Assistant."""

from backend.app.models.paper import (
    PaperRecord,
    AuthorIdentity,
    make_paper_id,
)
from backend.app.models.evidence import (
    EvidenceRecord,
    ReviewClaim,
    PRISMATracker,
    SearchProtocol,
    TaxonomyTheme,
    ValidationReport,
    make_evidence_id,
    make_claim_id,
)
from backend.app.models.corpus import (
    LiteratureCorpus,
    MatrixCell,
    EvidenceMatrix,
)
from backend.app.models.review import (
    SynthesisResult,
    CompiledReview,
)

__all__ = [
    "PaperRecord",
    "AuthorIdentity",
    "make_paper_id",
    "EvidenceRecord",
    "ReviewClaim",
    "PRISMATracker",
    "SearchProtocol",
    "TaxonomyTheme",
    "ValidationReport",
    "make_evidence_id",
    "make_claim_id",
    "LiteratureCorpus",
    "MatrixCell",
    "EvidenceMatrix",
    "SynthesisResult",
    "CompiledReview",
]
