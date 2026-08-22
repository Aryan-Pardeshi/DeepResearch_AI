"""DataCite REST API integration for research-output metadata enrichment and non-traditional outputs.

Queries DataCite REST API (https://api.datacite.org/dois).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from backend.app.models.evidence import PaperRecord, make_paper_id

logger = logging.getLogger(__name__)

DATACITE_API_URL = "https://api.datacite.org/dois"
DATACITE_TIMEOUT = 8.0


async def search_datacite_metadata(
    query: str,
    limit: int = 15,
    client: Optional[httpx.AsyncClient] = None
) -> List[PaperRecord]:
    """Search DataCite REST API for non-traditional research outputs, datasets, software, and DOI metadata."""
    params = {
        "query": query,
        "page[size]": min(limit, 50),
        "page[number]": 1
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=DATACITE_TIMEOUT, follow_redirects=True)
        should_close = True

    try:
        resp = await client.get(DATACITE_API_URL, params=params)
        if resp.status_code != 200:
            logger.warning(f"DataCite search returned status {resp.status_code} for query: {query[:40]!r}")
            return []

        data = resp.json()
        results = data.get("data", [])
        records: List[PaperRecord] = []

        for item in results:
            attrs = item.get("attributes", {})
            doi = attrs.get("doi")
            
            # Titles
            titles = attrs.get("titles", [])
            title = titles[0].get("title", "").strip() if titles else ""
            if not title:
                continue

            # Authors / Creators
            authors = []
            for c in attrs.get("creators", []):
                name = c.get("name") or f"{c.get('familyName', '')}, {c.get('givenName', '')}".strip(", ")
                if name:
                    authors.append(name.strip())

            # Publication Year
            year = str(attrs.get("publicationYear") or "n.d.")

            # Descriptions / Abstract
            descriptions = attrs.get("descriptions", [])
            abstract = descriptions[0].get("description", "").strip() if descriptions else ""
            abstract = re.sub(r"<[^>]+>", " ", abstract).strip()

            # Resource Type / Venue
            types = attrs.get("types", {})
            resource_type = types.get("resourceTypeGeneral") or types.get("resourceType") or "ResearchOutput"
            url = attrs.get("url") or (f"https://doi.org/{doi}" if doi else "")

            paper_id = make_paper_id(doi=doi, title=title, year=year)

            record = PaperRecord(
                paper_id=paper_id,
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                venue=f"DataCite [{resource_type}]",
                abstract=abstract,
                source_url=url,
                retrieval_source="datacite",
                citation_count=int(attrs.get("citationCount", 0) or 0),
                screening_status="retrieved",
            )
            records.append(record)

        logger.info(f"DataCite returned {len(records)} research outputs for: {query[:40]!r}")
        return records

    except Exception as e:
        logger.warning(f"DataCite search failed for {query[:40]!r}: {e}")
        return []
    finally:
        if should_close:
            await client.aclose()


async def enrich_doi_metadata_with_datacite(
    doi: str,
    client: Optional[httpx.AsyncClient] = None
) -> Optional[Dict[str, Any]]:
    """Fetch rich metadata for a single DOI from DataCite API."""
    if not doi:
        return None
    
    clean_doi = doi.strip().lower()
    clean_doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", clean_doi)
    url = f"{DATACITE_API_URL}/{clean_doi}"

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=DATACITE_TIMEOUT, follow_redirects=True)
        should_close = True

    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            attrs = data.get("data", {}).get("attributes", {})
            return {
                "datacite_doi": attrs.get("doi"),
                "creators": attrs.get("creators", []),
                "publicationYear": attrs.get("publicationYear"),
                "resourceType": attrs.get("types", {}).get("resourceTypeGeneral"),
                "rightsList": attrs.get("rightsList", []),
                "relatedIdentifiers": attrs.get("relatedIdentifiers", []),
            }
    except Exception as e:
        logger.debug(f"DataCite DOI lookup skipped for {doi}: {e}")
    finally:
        if should_close:
            await client.aclose()
    return None
