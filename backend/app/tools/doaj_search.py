"""DOAJ (Directory of Open Access Journals) API integration for pure OA literature discovery.

Queries DOAJ v2 REST API (https://doaj.org/api/v2/search/articles/).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from backend.app.models.evidence import PaperRecord, make_paper_id

logger = logging.getLogger(__name__)

DOAJ_API_URL = "https://doaj.org/api/v2/search/articles"
DOAJ_TIMEOUT = 8.0


async def search_doaj(
    query: str,
    limit: int = 15,
    client: Optional[httpx.AsyncClient] = None
) -> List[PaperRecord]:
    """Search DOAJ API for open-access journal articles."""
    url = f"{DOAJ_API_URL}/{query}"
    params = {
        "page": 1,
        "pageSize": min(limit, 50)
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=DOAJ_TIMEOUT, follow_redirects=True)
        should_close = True

    try:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            logger.warning(f"DOAJ search returned status {resp.status_code} for query: {query[:40]!r}")
            return []

        data = resp.json()
        results = data.get("results", [])
        records: List[PaperRecord] = []

        for item in results:
            bib = item.get("bibjson", {})
            title = bib.get("title", "").strip().rstrip(".")
            if not title:
                continue

            # Authors
            authors = []
            for a in bib.get("author", []):
                name = a.get("name", "").strip()
                if name:
                    authors.append(name)

            # Year
            year = str(bib.get("year") or "n.d.")

            # Journal / Venue
            journal = bib.get("journal", {})
            venue = journal.get("title")

            # Abstract
            abstract = bib.get("abstract", "").strip()

            # Identifiers (DOI, PII)
            doi = None
            for identifier in bib.get("identifier", []):
                if identifier.get("type") == "doi":
                    doi = identifier.get("id", "").strip()
                    break

            # Links / Full-text PDF
            pdf_url = None
            source_url = f"https://doi.org/{doi}" if doi else ""
            for link in bib.get("link", []):
                l_type = link.get("type", "")
                l_url = link.get("url", "")
                if l_type == "fulltext" or l_url.lower().endswith(".pdf"):
                    pdf_url = l_url
                if not source_url and l_url:
                    source_url = l_url

            paper_id = make_paper_id(doi=doi, title=title, year=year)

            record = PaperRecord(
                paper_id=paper_id,
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                abstract=abstract,
                source_url=source_url,
                pdf_url=pdf_url,
                retrieval_source="doaj",
                citation_count=0,
                screening_status="retrieved",
            )
            records.append(record)

        logger.info(f"DOAJ returned {len(records)} papers for: {query[:40]!r}")
        return records

    except Exception as e:
        logger.warning(f"DOAJ search failed for {query[:40]!r}: {e}")
        return []
    finally:
        if should_close:
            await client.aclose()
