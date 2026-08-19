"""Backward-compatibility module redirecting to modular agent packages."""

from backend.app.agents.research_mode import *
from backend.app.agents.research_mode._common import (
    get_llm_for,
    _safe_invoke_llm,
    _strip_preamble,
    EVIDENCE_BASIS_NOTE,
)
from backend.app.graph.research_mode_state import ResearchModeState
from backend.app.agents.research_mode.validation import validate_citations_in_text

# Alias for legacy test suites
verify_citations = validate_citations_in_text
