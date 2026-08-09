import io
import logging
import asyncio
import httpx
import pypdf

logger = logging.getLogger(__name__)

FULLTEXT_TOP_N = 10            # only the N highest-ranked papers get fetched
FULLTEXT_CHAR_BUDGET = 1500    # extracted characters kept per paper
FULLTEXT_FETCH_TIMEOUT = 8.0   # seconds, per PDF download
FULLTEXT_MAX_PDF_BYTES = 8 * 1024 * 1024   # 8MB cap, abort larger downloads
FULLTEXT_CONCURRENCY = 4       # concurrent downloads
FULLTEXT_TOTAL_BUDGET_SECONDS = 25.0   # whole-batch ceiling


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

            excerpt = full_text[:FULLTEXT_CHAR_BUDGET]
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

