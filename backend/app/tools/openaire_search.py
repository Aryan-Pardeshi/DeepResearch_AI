"""OpenAIRE Graph API v3 integration for European OA and institutional repository research products.

Uses OpenAIRE Graph API v3 endpoints (https://api.openaire.eu/graph/v3/research-products).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from backend.app.models.evidence import PaperRecord, make_paper_id

logger = logging.getLogger(__name__)

OPENAIRE_GRAPH_API_URL = "https://api.openaire.eu/graph/v3/research-products"
OPENAIRE_TIMEOUT = 8.0


async def search_openaire(
    query: str,
    limit: int = 15,
    client: Optional[httpx.AsyncClient] = None
) -> List[PaperRecord]:
    """Search OpenAIRE Graph API v3 for academic publications and research products."""
    params = {
        "search": query,
        "pageSize": min(limit, 50),
        "page": 1,
        "format": "json"
    }
    user_email = os.getenv("OPENALEX_EMAIL") or "researcher@example.com"
    headers = {
        "User-Agent": f"DeepResearchAssistant/2.0 (mailto:{user_email})"
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=OPENAIRE_TIMEOUT, follow_redirects=True)
        should_close = True

    try:
        resp = await client.get(OPENAIRE_GRAPH_API_URL, params=params, headers=headers)
        if resp.status_code != 200:
            logger.warning(f"OpenAIRE Graph API returned status {resp.status_code} for: {query[:40]!r}")
            return []

        data = resp.json()
        results = data.get("results", []) or data.get("response", {}).get("results", {}).get("result", [])
        records: List[PaperRecord] = []

        for item in results:
            header = item.get("header", {}) or item
            metadata = item.get("metadata", {}).get("oaf:entity", {}).get("oaf:result", {}) or item

            # Title
            title_obj = metadata.get("title") or metadata.get("maintitle") or {}
            if isinstance(title_obj, list) and title_obj:
                title_obj = title_obj[0]
            if isinstance(title_obj, dict):
                title = title_obj.get("content") or title_obj.get("value") or ""
            else:
                title = str(title_obj)

            title = title.strip()
            if not title:
                continue

            # Authors
            author_objs = metadata.get("author") or metadata.get("creator") or []
            if isinstance(author_objs, dict):
                author_objs = [author_objs]
            authors = []
            for a in author_objs:
                if isinstance(a, dict):
                    name = a.get("content") or a.get("fullname") or a.get("value") or ""
                    if name:
                        authors.append(name.strip())
                elif isinstance(a, str):
                    authors.append(a.strip())

            # Publication Year
            date = metadata.get("dateofacceptance") or metadata.get("resultdate") or metadata.get("publicationdate") or ""
            if isinstance(date, dict):
                date = date.get("content") or date.get("value") or ""
            year_match = re.search(r"\b(19\d\d|20\d\d)\b", str(date))
            year = year_match.group(1) if year_match else "n.d."

            # DOI & External IDs
            doi = None
            pid_objs = metadata.get("pid") or metadata.get("identifier") or []
            if isinstance(pid_objs, dict):
                pid_objs = [pid_objs]
            for pid in pid_objs:
                if isinstance(pid, dict):
                    scheme = (pid.get("classid") or pid.get("scheme") or "").lower()
                    val = pid.get("content") or pid.get("value") or ""
                    if scheme == "doi" or val.startswith("10."):
                        doi = val.strip()
                        break

            # Abstract
            description = metadata.get("description") or ""
            if isinstance(description, list) and description:
                description = description[0]
            if isinstance(description, dict):
                description = description.get("content") or description.get("value") or ""
            abstract = re.sub(r"<[^>]+>", " ", str(description)).strip()

            # Venue / Journal
            journal = metadata.get("journal") or {}
            venue = journal.get("name") if isinstance(journal, dict) else None

            # Open Access Status & PDF
            oa_status = "unknown"
            best_license = metadata.get("bestaccessright") or {}
            if isinstance(best_license, dict):
                oa_status = best_license.get("classid", "open").lower()

            url = f"https://doi.org/{doi}" if doi else (item.get("url") or f"https://explore.openaire.eu/search/publication?articleId={header.get('dri:objIdentifier', '')}")

            paper_id = make_paper_id(doi=doi, title=title, year=year)

            record = PaperRecord(
                paper_id=paper_id,
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                abstract=abstract,
                source_url=url,
                open_access_status=oa_status,
                retrieval_source="openaire",
                citation_count=0,
                screening_status="retrieved",
            )
            records.append(record)

        logger.info(f"OpenAIRE Graph API v3 returned {len(records)} papers for: {query[:40]!r}")
        return records

    except Exception as e:
        logger.warning(f"OpenAIRE Graph API search failed for {query[:40]!r}: {e}")
        return []
    finally:
        if should_close:
            await client.aclose()
