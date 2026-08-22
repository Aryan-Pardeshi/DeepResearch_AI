"""Multi-provider academic search execution and deduplication for Literature Review mode.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Literal, Tuple
import httpx

from backend.app.models.paper import PaperRecord, make_paper_id
from backend.app.tools.academic_router import route_query_to_domain, DomainProfile, DiscoveryConfig
from backend.app.tools.academic_search import (
    fetch_openalex_papers,
    fetch_semantic_scholar_papers,
    fetch_arxiv_papers,
    _normalize_title,
    _normalize_doi
)
from backend.app.tools.crossref_search import search_crossref
from backend.app.tools.pubmed_search import search_pubmed
from backend.app.tools.openaire_search import search_openaire
from backend.app.tools.doaj_search import search_doaj
from backend.app.tools.datacite_search import search_datacite_metadata
from backend.app.tools.orcid_resolver import enrich_paper_authors_with_orcid

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 8.0


async def execute_literature_search(
    query: str,
    mode: Literal["quick", "standard", "deep"] = "standard"
) -> Tuple[List[PaperRecord], DomainProfile, Dict[str, int]]:
    """Execute domain-routed multi-provider discovery and deduplication."""
    domain_profile, config = route_query_to_domain(query, mode=mode)
    logger.info(f"Routed query '{query}' to domain '{domain_profile.primary_domain}' with providers: {domain_profile.recommended_providers}")

    per_provider_limit = max(10, config.max_candidates // len(domain_profile.recommended_providers))
    tasks = []
    records_by_source: Dict[str, int] = {}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        for provider in domain_profile.recommended_providers:
            if provider == "openalex":
                tasks.append(fetch_openalex_papers(client, query, max_results=per_provider_limit))
            elif provider == "semantic_scholar":
                tasks.append(fetch_semantic_scholar_papers(client, query, max_results=per_provider_limit))
            elif provider == "crossref":
                tasks.append(search_crossref(query, limit=per_provider_limit))
            elif provider == "openaire":
                tasks.append(search_openaire(query, limit=per_provider_limit, client=client))
            elif provider == "doaj":
                tasks.append(search_doaj(query, limit=per_provider_limit, client=client))
            elif provider == "pubmed":
                tasks.append(search_pubmed(query, limit=per_provider_limit))
            elif provider == "arxiv":
                tasks.append(fetch_arxiv_papers(client, query, max_results=per_provider_limit))
            elif provider == "datacite":
                tasks.append(search_datacite_metadata(query, limit=per_provider_limit, client=client))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        combined: List[PaperRecord] = []
        provider_errors: Dict[str, str] = {}

        for idx, res in enumerate(results_list):
            provider_name = domain_profile.recommended_providers[idx] if idx < len(domain_profile.recommended_providers) else f"provider_{idx}"
            if isinstance(res, Exception):
                provider_errors[provider_name] = str(res)
                logger.warning(f"Provider '{provider_name}' failed during literature search: {res}")
            elif isinstance(res, list):
                for p in res:
                    if isinstance(p, PaperRecord):
                        combined.append(p)
                        src = p.retrieval_source
                        records_by_source[src] = records_by_source.get(src, 0) + 1

        if not combined and provider_errors:
            logger.error(f"All academic providers failed for query '{query}': {provider_errors}")

        if provider_errors:
            records_by_source["_provider_errors"] = str(provider_errors)

    # Deduplication Priority: DOI -> PMID -> arXiv ID -> Provider ID -> Title + Year
    seen_dois: Dict[str, PaperRecord] = {}
    seen_pmids: Dict[str, PaperRecord] = {}
    seen_arxivs: Dict[str, PaperRecord] = {}
    seen_title_years: Dict[str, PaperRecord] = {}
    seen_paper_ids: Dict[str, PaperRecord] = {}
    deduped: List[PaperRecord] = []

    for p in combined:
        doi = _normalize_doi(p.doi)
        pmid = p.pmid
        arxiv_id = p.arxiv_id
        norm_title = _normalize_title(p.title)
        title_year_key = f"{norm_title}:{p.year or 'nd'}" if norm_title else None
        pid = p.paper_id

        canonical = (
            seen_paper_ids.get(pid) or
            (seen_dois.get(doi) if doi else None) or
            (seen_pmids.get(pmid) if pmid else None) or
            (seen_arxivs.get(arxiv_id) if arxiv_id else None) or
            (seen_title_years.get(title_year_key) if title_year_key else None)
        )

        if canonical:
            # Merge duplicate retrieval source into retained canonical record
            prov = getattr(canonical, "provenance", {}) or {}
            disc_via = prov.get("discovered_via", [canonical.retrieval_source])
            if p.retrieval_source not in disc_via:
                disc_via.append(p.retrieval_source)
            prov["discovered_via"] = disc_via
            canonical.provenance = prov
            continue

        p.provenance = {
            "discovered_via": [p.retrieval_source],
            "metadata_source": p.retrieval_source,
            "abstract_source": p.retrieval_source,
        }

        seen_paper_ids[pid] = p
        if doi:
            seen_dois[doi] = p
        if pmid:
            seen_pmids[pmid] = p
        if arxiv_id:
            seen_arxivs[arxiv_id] = p
        if title_year_key:
            seen_title_years[title_year_key] = p

        deduped.append(p)

    retained = deduped[:config.max_candidates]
    logger.info(f"Literature search complete: {len(combined)} retrieved, {len(retained)} retained after deduplication.")
    return retained, domain_profile, records_by_source
