"""Domain-aware query router and provider capability mapping.

Classifies academic queries into DomainProfiles using deterministic heuristics
and selects optimal provider subsets and DiscoveryConfig limits.
"""

from __future__ import annotations

import re
from typing import Dict, List, Literal, Tuple
from pydantic import BaseModel, Field


class DomainProfile(BaseModel):
    """Domain profile returned by query router."""
    
    primary_domain: str = "general"
    secondary_domains: List[str] = Field(default_factory=list)
    detected_topics: List[str] = Field(default_factory=list)
    recommended_providers: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class DiscoveryConfig(BaseModel):
    """Configurable candidate retrieval and deep extraction thresholds."""
    
    mode: Literal["quick", "standard", "deep"] = "standard"
    max_candidates: int = 100
    max_fulltext: int = 50
    max_deep_extract: int = 50


# Provider subsets by domain
PROVIDER_SUBSETS = {
    "biomedical": ["pubmed", "europe_pmc", "openalex", "semantic_scholar", "openaire"],
    "computer_science": ["arxiv", "semantic_scholar", "crossref", "openalex", "doaj"],
    "physics_math": ["arxiv", "semantic_scholar", "crossref", "openalex"],
    "open_access": ["doaj", "openaire", "unpaywall", "core", "openalex"],
    "general": ["openalex", "semantic_scholar", "crossref", "openaire", "doaj"]
}

# Domain keyword markers
BIOMEDICAL_KEYWORDS = {
    "cancer", "tumor", "gene", "protein", "dna", "rna", "clinical", "patient", "disease",
    "drug", "therapy", "cell", "mutation", "virus", "infection", "vaccine", "antibody",
    "pharmacology", "neuron", "brain", "cardiac", "immunology", "oncology", "pathology",
    "CRISPR", "assay", "in vitro", "in vivo", "biomarker", "trial", "pubmed", "genomic"
}

CS_KEYWORDS = {
    "algorithm", "neural network", "transformer", "llm", "machine learning", "deep learning",
    "ai", "artificial intelligence", "convolutional", "nlp", "computer vision", "gpu",
    "reinforcement learning", "benchmark", "dataset", "dataset", "framework", "architecture",
    "optimization", "loss function", "latency", "throughput", "cybersecurity", "quantum"
}

PHYSICS_MATH_KEYWORDS = {
    "quantum", "relativity", "particle", "gravity", "spin", "string theory", "equation",
    "theorem", "proof", "topology", "manifold", "algebra", "calculus", "thermodynamics",
    "cosmology", "astrophysics", "boson", "fermion", "arxiv"
}


def route_query_to_domain(
    query: str,
    mode: Literal["quick", "standard", "deep"] = "standard"
) -> Tuple[DomainProfile, DiscoveryConfig]:
    """Route query using deterministic keyword matching + capability matrix."""
    clean_q = (query or "").lower().strip()
    words = set(re.findall(r"\b[a-z0-9-]+\b", clean_q))

    def calculate_domain_score(keyword_set: set) -> int:
        score = 0
        for kw in keyword_set:
            kw_clean = kw.lower().strip()
            if " " in kw_clean or "-" in kw_clean:
                if kw_clean in clean_q:
                    score += 2
            else:
                if kw_clean in words:
                    score += 1
        return score

    bio_score = calculate_domain_score(BIOMEDICAL_KEYWORDS)
    cs_score = calculate_domain_score(CS_KEYWORDS)
    phys_score = calculate_domain_score(PHYSICS_MATH_KEYWORDS)

    # Secondary multi-word phrase bonuses
    if any(phrase in clean_q for phrase in ["drug discovery", "clinical trial", "gene editing", "cell line", "in vitro"]):
        bio_score += 3
    if any(phrase in clean_q for phrase in ["large language model", "neural network", "deep learning", "computer vision"]):
        cs_score += 3
    if any(phrase in clean_q for phrase in ["quantum computing", "general relativity", "particle physics", "string theory"]):
        phys_score += 3

    domain_scores = [
        ("biomedical", bio_score),
        ("computer_science", cs_score),
        ("physics_math", phys_score)
    ]
    domain_scores.sort(key=lambda x: x[1], reverse=True)

    top_domain, top_score = domain_scores[0]
    if top_score == 0:
        primary_domain = "general"
        secondary_domains = []
    else:
        primary_domain = top_domain
        secondary_domains = [d for d, s in domain_scores[1:] if s > 0]

    recommended_providers = PROVIDER_SUBSETS.get(primary_domain, PROVIDER_SUBSETS["general"])

    # Configure limits based on mode
    if mode == "quick":
        config = DiscoveryConfig(mode="quick", max_candidates=50, max_fulltext=25, max_deep_extract=25)
    elif mode == "deep":
        config = DiscoveryConfig(mode="deep", max_candidates=250, max_fulltext=100, max_deep_extract=100)
    else:
        config = DiscoveryConfig(mode="standard", max_candidates=100, max_fulltext=50, max_deep_extract=50)

    profile = DomainProfile(
        primary_domain=primary_domain,
        secondary_domains=secondary_domains,
        detected_topics=sorted(list(words))[:8],
        recommended_providers=recommended_providers,
        confidence=min(1.0, 0.5 + (top_score * 0.15))
    )

    return profile, config
