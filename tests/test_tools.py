"""Tests for MCP tool definitions."""

import pytest
import respx
from httpx import Response

import point_mcp.server as server
from point_mcp.api_client import PointAPIClient

from conftest import (
    SEARCH_RESPONSE,
    TOC_RESPONSE,
    SECTIONS_RESPONSE,
    COLLECTIONS_RESPONSE,
    DISCOVER_RESPONSE,
    DOCUMENT_FULL_RESPONSE,
)


@pytest.fixture(autouse=True)
def patch_client(api_client):
    """Replace the global client with our test client."""
    server._client = api_client
    yield
    server._client = None


class TestSearchTool:
    async def test_search_returns_formatted_results(self, mock_api):
        result = await server.search("OAuth PKCE flow")
        assert "Found 1 result" in result
        assert "RFC 7636, Section 1 (2015)" in result
        assert "chunk-abc-001" in result
        assert "PKCE" in result

    async def test_search_no_results(self, mock_api):
        mock_api.routes.clear()
        mock_api.post("/v1/search").mock(return_value=Response(200, json={
            "query": "nonsense", "results": [], "context": "",
            "pipeline": {"search_ms": 5, "total_ms": 5}, "facets": {},
        }))
        result = await server.search("nonsense")
        assert "No results found" in result

    async def test_search_includes_context(self, mock_api):
        result = await server.search("OAuth PKCE flow")
        assert "Context (ready for prompt use)" in result
        assert "According to RFC 7636" in result

    async def test_search_includes_sibling_headings(self, mock_api):
        result = await server.search("OAuth PKCE flow")
        assert "Other sections in this doc" in result
        assert "Terminology" in result

    async def test_search_api_error(self):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.post("/v1/search").mock(
                return_value=Response(401, json={"detail": "Invalid API key"})
            )
            result = await server.search("test")
            assert "Authentication failed" in result
            assert "POINT_API_KEY" in result


class TestGetDocumentTocTool:
    async def test_toc_returns_structure(self, mock_api):
        result = await server.get_document_toc("rfc-7636")
        assert "Proof Key for Code Exchange" in result
        assert "chunk-abc-001" in result
        assert "Introduction" in result
        assert "Protocol" in result
        assert "Total sections: 3" in result

    async def test_toc_shows_indentation(self, mock_api):
        result = await server.get_document_toc("rfc-7636")
        assert "  - [chunk-abc-002]" in result

    async def test_toc_not_found(self):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/documents/bad-id/toc").mock(
                return_value=Response(404, json={"detail": "Document not found"})
            )
            result = await server.get_document_toc("bad-id")
            assert "Not found" in result


class TestGetSectionsTool:
    async def test_sections_returns_text(self, mock_api):
        result = await server.get_sections(["chunk-abc-001"])
        assert "Loaded 1 sections" in result
        assert "~156 tokens" in result
        assert "PKCE is an extension" in result
        assert "RFC 7636, Section 1 (2015)" in result

    async def test_sections_rejects_over_50(self):
        ids = [f"chunk-{i}" for i in range(51)]
        result = await server.get_sections(ids)
        assert "Maximum 50" in result

    async def test_sections_rejects_empty(self):
        result = await server.get_sections([])
        assert "at least one" in result


class TestListCollectionsTool:
    async def test_list_all(self, mock_api):
        result = await server.list_collections()
        assert "Available collections (2)" in result
        assert "IETF RFCs" in result
        assert "rfc-ietf" in result
        assert "AWS Documentation" in result

    async def test_list_with_query(self, mock_api):
        result = await server.list_collections(query="machine learning")
        assert "matching 'machine learning'" in result
        assert "PyTorch Documentation" in result
        assert "87.4%" in result

    async def test_list_api_error(self):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/collections").mock(
                return_value=Response(503, json={"detail": "Service unavailable"})
            )
            result = await server.list_collections()
            assert "temporarily unavailable" in result


class TestGetDocumentFullTool:
    async def test_full_returns_markdown(self, mock_api):
        result = await server.get_document_full("rfc-7636")
        assert "Proof Key for Code Exchange" in result
        assert "Version: 1.0" in result
        assert "PKCE is an extension" in result

    async def test_full_includes_token_estimate(self, mock_api):
        result = await server.get_document_full("rfc-7636")
        assert "tokens" in result

    async def test_full_withdrawn(self):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/documents/gone-doc/full").mock(
                return_value=Response(410, json={
                    "detail": {"error": "content_withdrawn"}
                })
            )
            result = await server.get_document_full("gone-doc")
            assert "withdrawn" in result
