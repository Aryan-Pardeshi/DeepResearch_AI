import asyncio
import httpx
from backend.app.tools.fulltext_fetcher import _download_and_extract

async def test_pmc_pdf_urls():
    user_agent = "ResearchBot/1.0 (mailto:researcher@academic-lab.org)"
    test_cases = [
        ("Understanding burnout", "https://pmc.ncbi.nlm.nih.gov/articles/PMC4911781/pdf/"),
        ("Just-in-Time Adaptive Interventions", "https://pmc.ncbi.nlm.nih.gov/articles/PMC5364076/pdf/"),
        ("Improving sleep quality", "https://pmc.ncbi.nlm.nih.gov/articles/PMC8651630/pdf/"),
        ("SEIPS model", "https://pmc.ncbi.nlm.nih.gov/articles/PMC2464868/pdf/"),
    ]
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers={"User-Agent": user_agent}) as client:
        for title, url in test_cases:
            res = await _download_and_extract(client, url, title)
            if res:
                print(f"SUCCESS for '{title}': extracted {len(res)} chars from {url}")
            else:
                print(f"FAILED for '{title}' from {url}")

if __name__ == "__main__":
    asyncio.run(test_pmc_pdf_urls())
