import os
import re
import json
import asyncio
import logging
import httpx
import feedparser
from typing import List, Dict, Any, Optional, Tuple
from backend.app.llm import get_llm

logger = logging.getLogger(__name__)

# Strict 5 second HTTP timeout to prevent hanging
HTTP_TIMEOUT = 5.0

# Corpus limits for the screening stage
MAX_SEARCH_KEYWORDS = 8      # keywords queried against every index
SCREEN_THRESHOLD = 30        # corpus sizes at or below this skip screening entirely
SCREEN_CANDIDATES = 60       # papers sent to the LLM relevance scorer
SCREEN_KEEP = 30             # papers retained for synthesis
SCREEN_BATCH_SIZE = 15       # papers per LLM scoring call
SCREEN_CONCURRENCY = 2       # scoring calls in flight at once

def _reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    word_pos = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_pos.append((pos, word))
    word_pos.sort(key=lambda x: x[0])
    return " ".join(wp[1] for wp in word_pos)

def _normalize_doi(doi: Optional[str]) -> str:
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi.strip()


def _normalize_title(title: Optional[str]) -> str:
    if not title:
        return ""
    return re.sub(r"\W+", "", title.lower())

async def fetch_openalex_papers(client: httpx.AsyncClient, keyword: str, max_results: int = 50) -> List[Dict[str, Any]]:
    papers = []
    try:
        url = "https://api.openalex.org/works"
        params = {
            "search": keyword,
            "sort": "cited_by_count:desc",
            "per_page": min(max_results, 50)
        }
        email = os.getenv("OPENALEX_EMAIL")
        if email and email != "your_email@example.com":
            params["mailto"] = email

        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("results", []):
                title = item.get("title") or ""
                if not title:
                    continue
                abstract = _reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
                authors = []

                for auth in item.get("authorships") or []:
                    if isinstance(auth, dict):
                        auth_obj = auth.get("author") or {}
                        name = auth_obj.get("display_name")
                        if name:
                            authors.append(name)
                year = item.get("publication_year")
                doi = _normalize_doi(item.get("doi"))
                landing_page = item.get("doi") or (item.get("primary_location") or {}).get("landing_page_url") or ""
                oa_info = item.get("open_access") or {}
                best_oa = item.get("best_oa_location") or {}
                pdf_url = oa_info.get("oa_url") or best_oa.get("pdf_url") or ""

                
                papers.append({
                    "title": title.strip(),
                    "abstract": abstract.strip(),
                    "authors": authors,
                    "year": year or "n.d.",
                    "doi": doi,
                    "url": landing_page,
                    "pdf_url": pdf_url,
                    "source": "openalex",
                    "citation_count": item.get("cited_by_count", 0)
                })
    except Exception as e:
        logger.warning(f"OpenAlex search skipped for '{keyword}': {e}")
    return papers

async def fetch_semantic_scholar_papers(client: httpx.AsyncClient, keyword: str, max_results: int = 50) -> List[Dict[str, Any]]:
    papers = []
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": keyword,
            "limit": min(max_results, 50),
            "fields": "paperId,title,abstract,authors,year,citationCount,externalIds,openAccessPdf"
        }
        headers = {}
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key

        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code == 429:
            logger.warning(f"Semantic Scholar 429 rate limit hit for '{keyword}', retrying in 1.0s...")
            await asyncio.sleep(1.0)
            resp = await client.get(url, params=params, headers=headers)

        if resp.status_code == 200:

            data = resp.json()
            for item in data.get("data", []):
                title = item.get("title") or ""
                if not title:
                    continue
                abstract = item.get("abstract") or ""
                authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
                year = item.get("year")
                ext_ids = item.get("externalIds") or {}
                doi = _normalize_doi(ext_ids.get("DOI"))
                pdf_url = (item.get("openAccessPdf") or {}).get("url")
                paper_url = pdf_url or (f"https://doi.org/{doi}" if doi else f"https://www.semanticscholar.org/paper/{item.get('paperId')}")

                papers.append({
                    "title": title.strip(),
                    "abstract": abstract.strip(),
                    "authors": authors,
                    "year": year or "n.d.",
                    "doi": doi,
                    "url": paper_url,
                    "pdf_url": pdf_url or "",
                    "source": "semantic_scholar",
                    "citation_count": item.get("citationCount", 0)
                })
    except Exception as e:
        logger.warning(f"Semantic Scholar search skipped for '{keyword}': {e}")
    return papers

async def fetch_arxiv_papers(client: httpx.AsyncClient, keyword: str, max_results: int = 50) -> List[Dict[str, Any]]:
    papers = []
    try:
        clean_kw = re.sub(r'[^\w\s]', '', keyword).strip()
        url = f"http://export.arxiv.org/api/query?search_query=all:{clean_kw}&start=0&max_results={min(max_results, 50)}&sortBy=relevance"
        
        resp = await client.get(url)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                title = entry.get("title", "").replace("\n", " ").strip()
                if not title:
                    continue
                abstract = entry.get("summary", "").replace("\n", " ").strip()
                authors = [a.get("name", "") for a in entry.get("authors", []) if a.get("name")]
                published = entry.get("published", "")
                year = published[:4] if len(published) >= 4 else "n.d."
                arxiv_id = entry.get("id", "")
                doi = _normalize_doi(entry.get("arxiv_doi"))

                papers.append({
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "year": year,
                    "doi": doi or arxiv_id.split("/")[-1],
                    "url": arxiv_id,
                    "pdf_url": arxiv_id.replace("/abs/", "/pdf/") if arxiv_id else "",
                    "source": "arxiv",
                    "citation_count": 0
                })

    except Exception as e:
        logger.warning(f"ArXiv search skipped for '{keyword}': {e}")
    return papers

async def fetch_tavily_web_papers(keyword: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """LAST RESORT FALLBACK: Fetches web articles via Tavily when academic database indexes return insufficient literature."""
    papers = []
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return papers
        from tavily import TavilyClient
        logger.info(f"Triggering LAST RESORT Tavily web search fallback for keyword: '{keyword}'")
        tavily = TavilyClient(api_key=api_key)
        res = tavily.search(query=f"academic research paper {keyword}", max_results=max_results, search_depth="basic")
        results = res.get("results", []) if isinstance(res, dict) else []
        for r in results:
            title = r.get("title", "").strip()
            content = r.get("content", "").strip()
            url = r.get("url", "").strip()
            if not title or not content:
                continue
            papers.append({
                "title": title,
                "abstract": content,
                "authors": ["Web Source"],
                "year": "2026",
                "doi": "",
                "url": url,
                "pdf_url": url if url.lower().endswith(".pdf") else "",
                "source": "tavily_web_fallback",
                "citation_count": 0
            })
    except Exception as e:
        logger.warning(f"Tavily web fallback search skipped for '{keyword}': {e}")
    return papers

async def search_academic_papers(keywords: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Searches OpenAlex, Semantic Scholar, and ArXiv concurrently with strict timeouts and deduplication.

    Equipped with Tavily web search as a LAST RESORT fallback if academic indexes return < 5 papers.
    """
    # All extracted keywords are queried; every request runs concurrently on one client
    selected_keywords = keywords[:MAX_SEARCH_KEYWORDS] if keywords else ["research"]
    
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        tasks = []
        for kw in selected_keywords:
            tasks.append(fetch_openalex_papers(client, kw))
            tasks.append(fetch_semantic_scholar_papers(client, kw))
            tasks.append(fetch_arxiv_papers(client, kw))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        combined: List[Dict[str, Any]] = []
        for res in results_list:
            if isinstance(res, list):
                combined.extend(res)

    # Deduplicate by DOI and normalized title
    seen_dois = set()
    seen_titles = set()
    deduped = []

    for paper in combined:
        doi = paper.get("doi")
        norm_title = _normalize_title(paper.get("title"))

        if doi and doi in seen_dois:
            continue
        if norm_title in seen_titles:
            continue

        if doi:
            seen_dois.add(doi)
        if norm_title:
            seen_titles.add(norm_title)

        deduped.append(paper)

    # LAST RESORT FALLBACK: If academic indexes returned fewer than 5 papers, trigger Tavily web search
    if len(deduped) < 5 and selected_keywords:
        logger.warning(f"Academic database search yield low ({len(deduped)} papers). Invoking LAST RESORT Tavily web search fallback...")
        tavily_tasks = [fetch_tavily_web_papers(kw, max_results=5) for kw in selected_keywords[:3]]
        tavily_results = await asyncio.gather(*tavily_tasks, return_exceptions=True)
        for res in tavily_results:
            if isinstance(res, list):
                for paper in res:
                    norm_title = _normalize_title(paper.get("title"))
                    if norm_title and norm_title not in seen_titles:
                        seen_titles.add(norm_title)
                        combined.append(paper)
                        deduped.append(paper)

    stats = {"retrieved": len(combined), "after_dedup": len(deduped)}
    logger.info(f"Academic search retrieved {len(combined)} raw papers, {len(deduped)} after deduplication.")
    return deduped, stats

def _select_candidates(papers: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """Picks the candidate pool for screening, round-robin across sources.

    Citation count alone would erase ArXiv (preprints report 0 citations), so each
    index contributes its most-cited papers in turn until the pool is full.
    """
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for paper in papers:
        by_source.setdefault(paper.get("source", "unknown"), []).append(paper)

    for bucket in by_source.values():
        bucket.sort(key=lambda p: p.get("citation_count", 0) or 0, reverse=True)

    candidates: List[Dict[str, Any]] = []
    buckets = list(by_source.values())
    idx = 0
    while len(candidates) < limit and any(idx < len(b) for b in buckets):
        for bucket in buckets:
            if idx < len(bucket):
                candidates.append(bucket[idx])
                if len(candidates) >= limit:
                    break
        idx += 1
    return candidates


async def _score_batch(
    llm,
    batch: List[Dict[str, Any]],
    problem_statement: str,
    objectives_str: str,
    semaphore: asyncio.Semaphore
) -> List[Dict[str, Any]]:
    """Scores one batch of papers 1-10 for relevance. Falls back to a neutral 5 on failure."""
    prompt = f"""Problem Statement:
{problem_statement}

Research Objectives:
{objectives_str}

Evaluate the following candidate papers for relevance to the Problem Statement and Objectives.
For each paper, return a score from 1 to 10 (10 = highly relevant, 1 = irrelevant).

Papers:
"""
    for idx, p in enumerate(batch):
        prompt += f"\n[{idx+1}] Title: {p.get('title', '')}\nAbstract snippet: {(p.get('abstract') or '')[:300]}\n"

    prompt += """\nReturn ONLY a JSON array of objects with fields 'id' (1-based index) and 'score' (1-10). Example:
[{"id": 1, "score": 9}, {"id": 2, "score": 4}]"""

    score_map: Dict[int, int] = {}
    async with semaphore:
        try:
            res = await asyncio.wait_for(llm.ainvoke(prompt), timeout=20.0)
            raw = str(res.content).strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            scores = json.loads(raw.strip())
            score_map = {
                item["id"]: item.get("score", 5)
                for item in scores
                if isinstance(item, dict) and "id" in item
            }
        except Exception as e:
            logger.warning(
                f"Screening batch failed or timed out, defaulting to neutral scores "
                f"[{type(e).__name__}]: {e!r}"
            )

    scored = []
    for idx, p in enumerate(batch):
        p_copy = dict(p)
        p_copy["relevance_score"] = score_map.get(idx + 1, 5)
        scored.append(p_copy)
    return scored


async def screen_papers(
    papers: List[Dict[str, Any]],
    problem_statement: str,
    objectives: List[str],
    model: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Screens the corpus for relevance to the problem statement.

    Batches are scored concurrently (bounded by SCREEN_CONCURRENCY) so a large corpus
    costs a few seconds rather than a serial call per batch.
    """
    if len(papers) <= SCREEN_THRESHOLD:
        return papers, {"screened": len(papers), "included": len(papers)}

    candidates = _select_candidates(papers, SCREEN_CANDIDATES)
    logger.info(
        f"Corpus size {len(papers)} > {SCREEN_THRESHOLD}. "
        f"Screening {len(candidates)} candidates for relevance..."
    )

    llm = get_llm(model=model, role="researcher")
    objectives_str = "\n".join(f"- {obj}" for obj in objectives)
    semaphore = asyncio.Semaphore(SCREEN_CONCURRENCY)

    batches = [
        candidates[i:i + SCREEN_BATCH_SIZE]
        for i in range(0, len(candidates), SCREEN_BATCH_SIZE)
    ]
    results = await asyncio.gather(
        *(_score_batch(llm, b, problem_statement, objectives_str, semaphore) for b in batches),
        return_exceptions=True
    )

    scored_papers: List[Dict[str, Any]] = []
    for res in results:
        if isinstance(res, list):
            scored_papers.extend(res)
        else:
            logger.warning(f"Screening batch raised: {res}")

    if not scored_papers:
        scored_papers = candidates

    scored_papers.sort(
        key=lambda p: (p.get("relevance_score", 0), p.get("citation_count", 0) or 0),
        reverse=True
    )
    screened = scored_papers[:SCREEN_KEEP]
    stats = {"screened": len(candidates), "included": len(screened)}
    logger.info(f"Screening complete. Selected top {len(screened)} papers.")
    return screened, stats

def format_apa(paper: Dict[str, Any]) -> str:
    """Formats paper metadata into APA 7th edition citation string."""
    authors = paper.get("authors") or []
    if not authors:
        author_str = "Anonymous"
    elif len(authors) == 1:
        author_str = authors[0]
    elif len(authors) == 2:
        author_str = f"{authors[0]} & {authors[1]}"
    elif len(authors) <= 7:
        author_str = ", ".join(authors[:-1]) + f", & {authors[-1]}"
    else:
        author_str = ", ".join(authors[:6]) + f", et al."

    year = paper.get("year", "n.d.")
    title = paper.get("title", "").strip().rstrip(".")
    doi = paper.get("doi")
    url = paper.get("url")

    source = paper.get("source", "").title()
    link = f"https://doi.org/{doi}" if doi else (url or "")

    apa_str = f"{author_str} ({year}). {title}."
    if source:
        apa_str += f" {source}."
    if link:
        apa_str += f" {link}"

    return apa_str.strip()
