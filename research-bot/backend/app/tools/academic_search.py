import os
import re
import asyncio
import logging
import httpx
import feedparser
from typing import List, Dict, Any, Optional
from backend.app.llm import get_llm

logger = logging.getLogger(__name__)

# Timeout for HTTP requests
HTTP_TIMEOUT = 30.0

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
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi

def _normalize_title(title: Optional[str]) -> str:
    if not title:
        return ""
    return re.sub(r"\W+", "", title.lower())

async def fetch_openalex_papers(keyword: str, max_results: int = 100) -> List[Dict[str, Any]]:
    papers = []
    try:
        url = "https://api.openalex.org/works"
        params = {
            "search": keyword,
            "sort": "cited_by_count:desc",
            "per_page": min(max_results, 100)
        }
        email = os.getenv("OPENALEX_EMAIL")
        if email and email != "your_email@example.com":
            params["mailto"] = email

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    title = item.get("title") or ""
                    if not title:
                        continue
                    abstract = _reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
                    authors = [
                        auth.get("author", {}).get("display_name", "")
                        for auth in item.get("authorships", [])
                        if auth.get("author", {}).get("display_name")
                    ]
                    year = item.get("publication_year")
                    doi = _normalize_doi(item.get("doi"))
                    landing_page = item.get("doi") or (item.get("primary_location") or {}).get("landing_page_url") or ""
                    
                    papers.append({
                        "title": title.strip(),
                        "abstract": abstract.strip(),
                        "authors": authors,
                        "year": year or "n.d.",
                        "doi": doi,
                        "url": landing_page,
                        "source": "openalex",
                        "citation_count": item.get("cited_by_count", 0)
                    })
    except Exception as e:
        logger.warning(f"OpenAlex search failed for '{keyword}': {e}")
    return papers

async def fetch_semantic_scholar_papers(keyword: str, max_results: int = 100) -> List[Dict[str, Any]]:
    papers = []
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": keyword,
            "limit": min(max_results, 100),
            "fields": "paperId,title,abstract,authors,year,citationCount,externalIds,openAccessPdf"
        }
        headers = {}
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
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
                        "source": "semantic_scholar",
                        "citation_count": item.get("citationCount", 0)
                    })
    except Exception as e:
        logger.warning(f"Semantic Scholar search failed for '{keyword}': {e}")
    return papers

async def fetch_arxiv_papers(keyword: str, max_results: int = 100) -> List[Dict[str, Any]]:
    papers = []
    try:
        clean_kw = re.sub(r'[^\w\s]', '', keyword).strip()
        url = f"http://export.arxiv.org/api/query?search_query=all:{clean_kw}&start=0&max_results={min(max_results, 100)}&sortBy=relevance"
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
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
                        "source": "arxiv",
                        "citation_count": 0
                    })
    except Exception as e:
        logger.warning(f"ArXiv search failed for '{keyword}': {e}")
    return papers

async def search_academic_papers(keywords: List[str]) -> List[Dict[str, Any]]:
    """Searches OpenAlex, Semantic Scholar, and ArXiv in parallel across all keywords and deduplicates results."""
    tasks = []
    for kw in keywords[:10]:  # Cap at 10 keywords
        tasks.append(fetch_openalex_papers(kw))
        tasks.append(fetch_semantic_scholar_papers(kw))
        tasks.append(fetch_arxiv_papers(kw))

    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    combined: List[Dict[str, Any]] = []
    for res in results_list:
        if isinstance(res, list):
            combined.extend(res)

    # Deduplicate by DOI first, then by normalized title
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

    logger.info(f"Academic search retrieved {len(combined)} raw papers, {len(deduped)} after deduplication.")
    return deduped

async def screen_papers(
    papers: List[Dict[str, Any]],
    problem_statement: str,
    objectives: List[str]
) -> List[Dict[str, Any]]:
    """Screens papers based on relevance if total corpus > 50."""
    if len(papers) <= 50:
        return papers

    logger.info(f"Corpus size {len(papers)} > 50. Screening papers using LLM...")
    llm = get_llm(role="researcher")
    
    scored_papers = []
    batch_size = 20
    
    objectives_str = "\n".join(f"- {obj}" for obj in objectives)

    for i in range(0, len(papers), batch_size):
        batch = papers[i:i + batch_size]
        prompt = f"""Problem Statement:
{problem_statement}

Research Objectives:
{objectives_str}

Evaluate the following candidate papers for relevance to the Problem Statement and Objectives.
For each paper, return a score from 1 to 10 (10 = highly relevant, 1 = irrelevant).

Papers:
"""
        for idx, p in enumerate(batch):
            title = p.get("title", "")
            abstract = p.get("abstract", "")[:300]
            prompt += f"\n[{idx+1}] Title: {title}\nAbstract snippet: {abstract}\n"

        prompt += """\nReturn ONLY a JSON array of objects with fields 'id' (1-based index) and 'score' (1-10). Example:
[{"id": 1, "score": 9}, {"id": 2, "score": 4}]"""

        try:
            res = await llm.ainvoke(prompt)
            import json
            raw = res.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            scores = json.loads(raw)
            score_map = {item["id"]: item.get("score", 5) for item in scores if isinstance(item, dict)}
            
            for idx, p in enumerate(batch):
                score = score_map.get(idx + 1, 5)
                p_copy = dict(p)
                p_copy["relevance_score"] = score
                scored_papers.append(p_copy)
        except Exception as e:
            logger.warning(f"Error scoring batch {i}: {e}")
            for p in batch:
                p_copy = dict(p)
                p_copy["relevance_score"] = 5
                scored_papers.append(p_copy)

    # Sort by relevance score descending and keep top 40
    scored_papers.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    screened = scored_papers[:40]
    logger.info(f"Screening complete. Selected top {len(screened)} papers.")
    return screened

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
