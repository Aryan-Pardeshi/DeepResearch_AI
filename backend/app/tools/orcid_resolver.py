"""ORCID Public API integration for author identity resolution and profile enrichment.

Queries ORCID v3.0 Public API (https://pub.orcid.org/v3.0).
Used post-discovery to enrich author metadata and disambiguate author profiles.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

ORCID_BASE_URL = "https://pub.orcid.org/v3.0"
ORCID_TIMEOUT = 6.0


async def resolve_author_orcid(
    author_name: str,
    affiliation_hint: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None
) -> Optional[Dict[str, str]]:
    """Query ORCID Public API to resolve an author's ORCID identifier and profile details."""
    if not author_name or len(author_name.strip()) < 3:
        return None

    clean_name = re.sub(r"[^\w\s]", "", author_name).strip()
    name_parts = clean_name.split()
    if len(name_parts) >= 2:
        given = name_parts[0]
        family = " ".join(name_parts[1:])
        name_query = f'given-names:"{given}" AND family-name:"{family}"'
    else:
        name_query = f'credit-name:"{clean_name}"'

    query = name_query
    if affiliation_hint:
        clean_aff = re.sub(r"[^\w\s]", "", affiliation_hint).strip()
        if clean_aff:
            query = f'({name_query}) AND affiliation-org-name:"{clean_aff}"'

    url = f"{ORCID_BASE_URL}/search"
    params = {"q": query, "rows": 1}
    headers = {"Accept": "application/json"}

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=ORCID_TIMEOUT, follow_redirects=True)
        should_close = True

    try:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("result", [])
            if results:
                orcid_id = results[0].get("orcid-identifier", {}).get("path")
                # Require explicit affiliation match or structured given/family match before assigning verified ORCID
                if orcid_id and (affiliation_hint or len(name_parts) >= 2):
                    return {
                        "name": author_name,
                        "orcid": orcid_id,
                        "orcid_uri": f"https://orcid.org/{orcid_id}"
                    }
    except Exception as e:
        logger.debug(f"ORCID resolution skipped for '{author_name}': {e}")
    finally:
        if should_close:
            await client.aclose()
    return None


async def enrich_paper_authors_with_orcid(
    authors: List[str],
    venue_or_affil: Optional[str] = None,
    max_authors_to_resolve: int = 3
) -> List[Dict[str, str]]:
    """Enrich a list of author name strings with resolved ORCID records for top N authors."""
    enriched = []
    async with httpx.AsyncClient(timeout=ORCID_TIMEOUT, follow_redirects=True) as client:
        for idx, author in enumerate(authors):
            author_dict = {"name": author, "orcid": ""}
            if idx < max_authors_to_resolve:
                orcid_info = await resolve_author_orcid(author, affiliation_hint=venue_or_affil, client=client)
                if orcid_info:
                    author_dict["orcid"] = orcid_info["orcid"]
                    author_dict["orcid_uri"] = orcid_info["orcid_uri"]
            enriched.append(author_dict)
    return enriched
