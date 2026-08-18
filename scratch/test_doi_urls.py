import asyncio
import httpx

async def test_doi_urls():
    email = "researcher@academic-lab.org"
    dois = [
        "10.1002/wps.20311",
        "10.1007/s12160-016-9830-8",
        "10.1136/qshc.2005.015842",
        "10.1136/bjsports-2019-100715",
        "10.1016/j.smrv.2021.101556"
    ]
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for doi in dois:
            print(f"\n--- DOI: {doi} ---")
            # Unpaywall
            unpay_resp = await client.get(f"https://api.unpaywall.org/v2/{doi}?email={email}")
            if unpay_resp.status_code == 200:
                data = unpay_resp.json()
                print("Unpaywall oa_locations:")
                for loc in data.get("oa_locations", []):
                    print("  - host_type:", loc.get("host_type"), "| url_for_pdf:", loc.get("url_for_pdf"), "| url:", loc.get("url"))
            
            # Europe PMC
            epmc_resp = await client.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={"query": f'DOI:"{doi}"', "format": "json", "resultType": "core"})
            if epmc_resp.status_code == 200:
                results = epmc_resp.json().get("resultList", {}).get("result", [])
                if results:
                    r = results[0]
                    print("Europe PMC:")
                    print("  - pmcid:", r.get("pmcid"), "| isOpenAccess:", r.get("isOpenAccess"), "| fullTextUrlList:", r.get("fullTextUrlList"))

if __name__ == "__main__":
    asyncio.run(test_doi_urls())
