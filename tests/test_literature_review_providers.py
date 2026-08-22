"""Unit tests for expanded academic providers and academic_router.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.tools.academic_router import route_query_to_domain, DomainProfile, DiscoveryConfig
from backend.app.tools.openaire_search import search_openaire
from backend.app.tools.doaj_search import search_doaj
from backend.app.tools.datacite_search import search_datacite_metadata
from backend.app.tools.orcid_resolver import resolve_author_orcid


def test_academic_router_biomedical():
    profile, config = route_query_to_domain("CRISPR gene editing oncology trial", mode="standard")
    assert profile.primary_domain == "biomedical"
    assert "pubmed" in profile.recommended_providers
    assert config.max_candidates == 100


def test_academic_router_computer_science():
    profile, config = route_query_to_domain("Transformer neural network LLM latency benchmark", mode="quick")
    assert profile.primary_domain == "computer_science"
    assert "arxiv" in profile.recommended_providers
    assert config.max_candidates == 50


def test_academic_router_deep_mode():
    profile, config = route_query_to_domain("general research query", mode="deep")
    assert config.max_candidates == 250
    assert config.max_fulltext == 100


@pytest.mark.asyncio
async def test_openaire_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "header": {"dri:objIdentifier": "openaire_001"},
                "metadata": {
                    "oaf:entity": {
                        "oaf:result": {
                            "title": {"content": "OpenAIRE Test Publication"},
                            "creator": [{"content": "Alice Smith"}],
                            "dateofacceptance": {"content": "2023-05-12"},
                            "pid": [{"classid": "doi", "content": "10.1000/openaire.test"}]
                        }
                    }
                }
            }
        ]
    }
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    records = await search_openaire("medical image segmentation", limit=5, client=mock_client)
    assert isinstance(records, list)
    assert len(records) == 1
    assert records[0].title == "OpenAIRE Test Publication"
    assert records[0].doi == "10.1000/openaire.test"
    # Verify outgoing request used 'search' parameter
    mock_client.get.assert_called_once()
    _, kwargs = mock_client.get.call_args
    assert kwargs["params"]["search"] == "medical image segmentation"


@pytest.mark.asyncio
async def test_doaj_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "bibjson": {
                    "title": "DOAJ Open Access Article",
                    "author": [{"name": "Bob Jones"}],
                    "year": "2024",
                    "identifier": [{"type": "doi", "id": "10.1000/doaj.test"}]
                }
            }
        ]
    }
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    records = await search_doaj("open access biology", limit=5, client=mock_client)
    assert isinstance(records, list)
    assert len(records) == 1
    assert records[0].title == "DOAJ Open Access Article"


@pytest.mark.asyncio
async def test_datacite_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "10.1000/datacite.test",
                "attributes": {
                    "doi": "10.1000/datacite.test",
                    "titles": [{"title": "DataCite Dataset Output"}],
                    "creators": [{"name": "Charlie Brown"}],
                    "publicationYear": 2023,
                    "publisher": "Zenodo"
                }
            }
        ]
    }
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    records = await search_datacite_metadata("climate dataset", limit=5, client=mock_client)
    assert isinstance(records, list)
    assert len(records) == 1
    assert records[0].title == "DataCite Dataset Output"
