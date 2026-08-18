import asyncio
import os
import logging
import httpx
from backend.app.tools.academic_search import search_academic_papers
from backend.app.tools.fulltext_fetcher import _download_and_extract
from backend.app.tools.oa_resolver import resolve_unpaywall, resolve_europe_pmc, resolve_core, resolve_oa_pdf_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test_a():
    # Set a valid email so Unpaywall is active
    os.environ["OPENALEX_EMAIL"] = "researcher@academic-lab.org"

    keywords = ["cognitive behavioral therapy healthcare worker burnout", "psychological interventions nursing stress"]
    print("--- Searching academic papers for clinical/social science topic ---")
    papers, stats = await search_academic_papers(keywords)
    print(f"Retrieved: {stats['retrieved']}, After Dedup: {stats['after_dedup']}")

    top_10 = papers[:10]
    print(f"\nEvaluating top {len(top_10)} papers:")

    # Test 1: Direct fetch only (without OA resolvers)
    print("\n--- Test 1: Direct pdf_url fetch only ---")
    direct_success = 0
    direct_results = {}
    user_agent = "ResearchBot/1.0 (mailto:researcher@academic-lab.org)"
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers={"User-Agent": user_agent}) as client:
        for idx, p in enumerate(top_10):
            url = p.get("pdf_url")
            if url:
                res = await _download_and_extract(client, url, p["title"])
                if res:
                    direct_success += 1
                    direct_results[p["title"]] = True
                    print(f"  [{idx+1}] DIRECT SUCCESS: '{p['title'][:40]}...'")
                else:
                    direct_results[p["title"]] = False
                    print(f"  [{idx+1}] DIRECT FAILED (HTTP 403 or parse error): '{p['title'][:40]}...' from {url}")
            else:
                direct_results[p["title"]] = False
                print(f"  [{idx+1}] NO INITIAL PDF URL: '{p['title'][:40]}...'")

    print(f"\nDirect fetch yield: {direct_success}/{len(top_10)}")

    # Test 2: With OA Resolvers
    print("\n--- Test 2: Evaluating OA Resolvers (Unpaywall, Europe PMC, CORE) ---")
    unpaywall_rescued = 0
    europe_pmc_rescued = 0
    core_rescued = 0
    total_with_oa = 0

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers={"User-Agent": user_agent}) as client:
        for idx, p in enumerate(top_10):
            title = p["title"]
            initial_url = p.get("pdf_url")
            
            # If direct succeeded, keep it
            if direct_results.get(title):
                total_with_oa += 1
                continue

            print(f"\nAttempting OA resolution for [{idx+1}] '{title[:50]}...' (DOI: {p.get('doi')})")

            paper_no_url = dict(p)
            paper_no_url["pdf_url"] = ""

            # Try Unpaywall
            unpay_url = await resolve_unpaywall(client, paper_no_url)
            print(f"  -> Unpaywall resolved URL: {unpay_url}")
            if unpay_url and unpay_url != initial_url:
                ex = await _download_and_extract(client, unpay_url, title)
                if ex:
                    unpaywall_rescued += 1
                    total_with_oa += 1
                    print(f"  [RESCUED BY UNPAYWALL] '{title[:40]}...' -> {unpay_url}")
                    continue
                else:
                    print(f"  Unpaywall URL download failed or text mismatch: {unpay_url}")

            # Try Europe PMC
            epmc_url = await resolve_europe_pmc(client, paper_no_url)
            print(f"  -> Europe PMC resolved URL: {epmc_url}")
            if epmc_url and epmc_url != initial_url:
                ex = await _download_and_extract(client, epmc_url, title)
                if ex:
                    europe_pmc_rescued += 1
                    total_with_oa += 1
                    print(f"  [RESCUED BY EUROPE PMC] '{title[:40]}...' -> {epmc_url}")
                    continue
                else:
                    print(f"  Europe PMC URL download failed or text mismatch: {epmc_url}")

            # Try CORE
            core_url = await resolve_core(client, paper_no_url)
            print(f"  -> CORE resolved URL: {core_url}")
            if core_url and core_url != initial_url:
                ex = await _download_and_extract(client, core_url, title)
                if ex:
                    core_rescued += 1
                    total_with_oa += 1
                    print(f"  [RESCUED BY CORE] '{title[:40]}...' -> {core_url}")
                    continue
                else:
                    print(f"  CORE URL download failed or text mismatch: {core_url}")

    print(f"\nSummary:")
    print(f"Full-text yield BEFORE OA resolvers: {direct_success}/{len(top_10)}")
    print(f"Full-text yield AFTER OA resolvers:  {total_with_oa}/{len(top_10)}")
    print(f"Rescued by Unpaywall:  {unpaywall_rescued}")
    print(f"Rescued by Europe PMC: {europe_pmc_rescued}")
    print(f"Rescued by CORE:       {core_rescued}")

if __name__ == "__main__":
    asyncio.run(run_test_a())
