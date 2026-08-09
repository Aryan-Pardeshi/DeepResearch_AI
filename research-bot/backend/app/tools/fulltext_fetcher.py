import io
import re
import logging
import asyncio
import httpx
import pypdf

logger = logging.getLogger(__name__)

# Open-access URLs are not always trustworthy: OpenAlex oa_url in particular can
# resolve to a proceedings volume or an unrelated record. Text that does not look
# like the paper it is attached to is worse than no text at all, because it grounds
# the literature review in a source the citation does not name.
TITLE_MATCH_THRESHOLD = 0.4    # fraction of title words that must appear up front
TITLE_MATCH_WINDOW = 4000      # characters searched for them; repository deposits
                               # (HAL, institutional archives) prepend a cover sheet
                               # before the paper itself begins

FULLTEXT_TOP_N = 10            # only the N highest-ranked papers get fetched
FULLTEXT_CHAR_BUDGET = 1500    # extracted characters kept per paper
FULLTEXT_FETCH_TIMEOUT = 8.0   # seconds, per PDF download
FULLTEXT_MAX_PDF_BYTES = 16 * 1024 * 1024  # 16MB cap, abort larger downloads

FULLTEXT_CONCURRENCY = 4       # concurrent downloads
FULLTEXT_TOTAL_BUDGET_SECONDS = 25.0   # whole-batch ceiling


def _significant_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower())}


def _text_belongs_to_paper(title: str, text: str) -> bool:
    """Checks the extracted PDF text really is the paper it claims to be.

    A paper's own title appears near the front of its PDF, so most title words
    should turn up in the opening window. When they do not, the URL resolved to a
    different document entirely.
    """
    title_words = _significant_words(title)
    if not title_words:
        return True  # nothing to check against; do not discard on a missing title
    head_words = _significant_words(text[:TITLE_MATCH_WINDOW])
    overlap = len(title_words & head_words) / len(title_words)
    return overlap >= TITLE_MATCH_THRESHOLD


def _skip_cover_page(title: str, text: str) -> str:
    """Drops repository boilerplate preceding the paper.

    HAL and similar archives prepend a deposit cover sheet; starting the excerpt at
    the paper's own title spends the character budget on content instead of
    submission metadata.
    """
    words = [w for w in re.findall(r"[a-z]{4,}", (title or "").lower())][:4]
    if len(words) < 3:
        return text
    # Allow short connecting words between the significant ones: "Applied to Document"
    pattern = r".{0,30}?".join(re.escape(w) for w in words)
    match = re.search(pattern, text[:TITLE_MATCH_WINDOW], re.IGNORECASE | re.DOTALL)
    return text[match.start():] if match else text


async def _fetch_single_pdf(paper: dict, semaphore: asyncio.Semaphore) -> tuple[str, str | None]:
    title = paper.get("title", "")
    pdf_url = paper.get("pdf_url", "")
    if not pdf_url:
        return (title, None)

    async with semaphore:
        try:
            async with httpx.AsyncClient(timeout=FULLTEXT_FETCH_TIMEOUT, follow_redirects=True) as client:
                async with client.stream("GET", pdf_url) as resp:
                    if resp.status_code != 200:
                        logger.warning(f"HTTP {resp.status_code} fetching PDF for '{title}' from {pdf_url}")
                        return (title, None)

                    cl = resp.headers.get("Content-Length")
                    if cl and cl.isdigit() and int(cl) > FULLTEXT_MAX_PDF_BYTES:
                        logger.warning(
                            f"Aborting fetch for '{title}': Content-Length {cl} exceeds {FULLTEXT_MAX_PDF_BYTES} bytes cap."
                        )
                        return (title, None)

                    chunks = []
                    downloaded = 0
                    async for chunk in resp.aiter_bytes():
                        downloaded += len(chunk)
                        if downloaded > FULLTEXT_MAX_PDF_BYTES:
                            logger.warning(
                                f"Aborting fetch for '{title}': Downloaded size exceeded {FULLTEXT_MAX_PDF_BYTES} bytes cap."
                            )
                            return (title, None)
                        chunks.append(chunk)
                    pdf_bytes = b"".join(chunks)

            if not pdf_bytes:
                logger.warning(f"Empty PDF content received for '{title}'")
                return (title, None)

            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            pages_text = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    pages_text.append(txt)

            full_text = " ".join(" ".join(pages_text).split())
            if not full_text:
                logger.warning(f"No text extracted from PDF for '{title}'")
                return (title, None)

            if not _text_belongs_to_paper(title, full_text):
                logger.warning(
                    f"Discarding full text for '{title}': extracted content does not match "
                    f"the paper title (URL likely resolved to a different document)."
                )
                return (title, None)

            excerpt = _skip_cover_page(title, full_text)[:FULLTEXT_CHAR_BUDGET]
            return (title, excerpt)
        except Exception as e:
            logger.warning(f"Failed to fetch/extract fulltext PDF for '{title}': {e}")
            return (title, None)


async def fetch_fulltext_excerpts(papers: list[dict]) -> dict[str, str]:
    """Fetches PDF full-text excerpts concurrently for the top FULLTEXT_TOP_N papers."""
    top_selected = papers[:FULLTEXT_TOP_N]
    papers_to_fetch = [p for p in top_selected if p.get("pdf_url")]

    results: dict[str, str] = {}
    if not papers_to_fetch:
        logger.info(f"fetched full text for 0/{FULLTEXT_TOP_N} papers")
        return results

    semaphore = asyncio.Semaphore(FULLTEXT_CONCURRENCY)
    tasks = [asyncio.create_task(_fetch_single_pdf(p, semaphore)) for p in papers_to_fetch]

    try:
        raw_results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=FULLTEXT_TOTAL_BUDGET_SECONDS
        )
        for res in raw_results:
            if isinstance(res, tuple) and res[1] is not None:
                title, excerpt = res
                results[title] = excerpt
    except (asyncio.TimeoutError, asyncio.CancelledError):
        logger.warning(f"Batch full-text fetch timed out or cancelled after {FULLTEXT_TOTAL_BUDGET_SECONDS}s")
        for t in tasks:
            if not t.done():
                t.cancel()
            else:
                try:
                    if not t.cancelled():
                        res = t.result()
                        if isinstance(res, tuple) and res[1] is not None:
                            results[res[0]] = res[1]
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Error in fetch_fulltext_excerpts batch: {e}")

    logger.info(f"fetched full text for {len(results)}/{FULLTEXT_TOP_N} papers")
    return results

