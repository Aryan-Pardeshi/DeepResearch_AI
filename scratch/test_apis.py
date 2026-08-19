import asyncio
import logging
from backend.app.tools.crossref_search import search_crossref
from backend.app.tools.pubmed_search import search_pubmed
from backend.app.tools.opencitations_search import expand_citation_graph
from backend.app.tools.academic_search import search_academic_papers_structured

logging.basicConfig(level=logging.INFO)

async def test():
    print("--- Testing Crossref Search ---")
    try:
        cr_papers = await search_crossref("machine learning protein folding", limit=5)
        print(f"Crossref result count: {len(cr_papers)}")
        for p in cr_papers[:2]:
            print(f"  [Crossref] {p.title} ({p.year}) - DOI: {p.doi} - Source: {p.retrieval_source}")
    except Exception as e:
        print(f"Crossref error: {e}")

    print("\n--- Testing PubMed Search ---")
    try:
        pm_papers = await search_pubmed("crispr gene editing clinical trial", limit=5)
        print(f"PubMed result count: {len(pm_papers)}")
        for p in pm_papers[:2]:
            print(f"  [PubMed] {p.title} ({p.year}) - DOI: {p.doi} - Source: {p.retrieval_source}")
    except Exception as e:
        print(f"PubMed error: {e}")

    print("\n--- Testing OpenCitations ---")
    try:
        seed_dois = ["10.1038/s41586-021-03819-2"]  # AlphaFold Nature paper
        expanded = await expand_citation_graph(seed_dois, max_expansion=5)
        print(f"OpenCitations expanded DOIs count: {len(expanded)}")
        print(f"  [OpenCitations] DOIs: {list(expanded)[:3]}")
    except Exception as e:
        print(f"OpenCitations error: {e}")

    print("\n--- Testing Full Structured Academic Search ---")
    try:
        records, tracker = await search_academic_papers_structured(["deep learning biomedical vision"])
        print(f"Total records retrieved: {len(records)}")
        print(f"Records by source in PRISMA tracker: {tracker.records_by_source}")
    except Exception as e:
        print(f"Full search error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
