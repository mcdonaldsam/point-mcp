"""Tests for the Point API client."""

import pytest
import respx
from httpx import Response

from point_mcp.api_client import PointAPIClient, PointAPIError

from conftest import (
    SEARCH_RESPONSE,
    TOC_RESPONSE,
    SECTIONS_RESPONSE,
    COLLECTIONS_RESPONSE,
    DISCOVER_RESPONSE,
    DOCUMENT_FULL_RESPONSE,
)


class TestAPIClientInit:
    def test_requires_api_key(self):
        import os
        env_key = os.environ.pop("POINT_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="POINT_API_KEY"):
                PointAPIClient(api_key="")
        finally:
            if env_key:
                os.environ["POINT_API_KEY"] = env_key

    def test_accepts_explicit_key(self):
        client = PointAPIClient(api_key="my-key")
        assert client.api_key == "my-key"

    def test_custom_base_url(self):
        client = PointAPIClient(api_key="key", base_url="http://localhost:8000")
        assert client.base_url == "http://localhost:8000"

    def test_default_base_url(self):
        client = PointAPIClient(api_key="key")
        assert client.base_url == "https://point-api.pinchpoint.dev"


class TestAPIClientSearch:
    async def test_search_basic(self, api_client, mock_api):
        result = await api_client.search("OAuth PKCE flow")
        assert result["query"] == "OAuth PKCE flow"
        assert len(result["results"]) == 1

    async def test_search_with_filters(self, api_client, mock_api):
        await api_client.search("test", collection="rfc-ietf", doc_type="rfc", limit=5)
        request = mock_api.calls[0].request
        import json
        body = json.loads(request.content)
        assert body["collection"] == "rfc-ietf"
        assert body["doc_type"] == "rfc"
        assert body["limit"] == 5


class TestAPIClientDocuments:
    async def test_get_toc(self, api_client, mock_api):
        result = await api_client.get_document_toc("rfc-7636")
        assert result["doc_id"] == "rfc-7636"
        assert len(result["sections"]) == 3

    async def test_get_full(self, api_client, mock_api):
        result = await api_client.get_document_full("rfc-7636")
        assert "markdown" in result
        assert result["doc_id"] == "rfc-7636"


class TestAPIClientSections:
    async def test_get_sections(self, api_client, mock_api):
        result = await api_client.get_sections(["chunk-abc-001"])
        assert len(result["results"]) == 1
        assert result["total_tokens_approx"] == 156


class TestAPIClientCollections:
    async def test_list_collections(self, api_client, mock_api):
        result = await api_client.list_collections()
        assert len(result) == 2
        assert result[0]["id"] == "rfc-ietf"

    async def test_discover_collections(self, api_client, mock_api):
        result = await api_client.discover_collections("machine learning")
        assert len(result["results"]) == 1


class TestAPIClientErrors:
    async def test_401_no_retry(self, api_client):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/collections").mock(
                return_value=Response(401, json={"detail": "Invalid API key"})
            )
            with pytest.raises(PointAPIError) as exc_info:
                await api_client.list_collections()
            assert exc_info.value.status_code == 401
            assert len(mock.calls) == 1

    async def test_404_no_retry(self, api_client):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/documents/nonexistent/toc").mock(
                return_value=Response(404, json={"detail": "Document not found"})
            )
            with pytest.raises(PointAPIError) as exc_info:
                await api_client.get_document_toc("nonexistent")
            assert exc_info.value.status_code == 404

    async def test_429_retries(self, api_client):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/collections").mock(
                side_effect=[
                    Response(429, json={"detail": "Rate limited"}),
                    Response(200, json=[]),
                ]
            )
            result = await api_client.list_collections()
            assert result == []
            assert len(mock.calls) == 2

    async def test_503_retries_then_fails(self, api_client):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/collections").mock(
                return_value=Response(503, json={"detail": "Service unavailable"})
            )
            with pytest.raises(PointAPIError) as exc_info:
                await api_client.list_collections()
            assert exc_info.value.status_code == 503
            assert len(mock.calls) == 3

    async def test_timeout_retries(self, api_client):
        import httpx as httpx_lib
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/collections").mock(
                side_effect=[
                    httpx_lib.TimeoutException("timed out"),
                    Response(200, json=[]),
                ]
            )
            result = await api_client.list_collections()
            assert result == []

    async def test_410_withdrawn(self, api_client):
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/documents/withdrawn-doc/toc").mock(
                return_value=Response(410, json={
                    "detail": {
                        "error": "content_withdrawn",
                        "reason": "content_review_rejected",
                        "collection_id": "test-coll",
                        "alternatives": "/v1/collections/test-coll/documents",
                    }
                })
            )
            with pytest.raises(PointAPIError) as exc_info:
                await api_client.get_document_toc("withdrawn-doc")
            assert exc_info.value.status_code == 410
            assert "content_withdrawn" in exc_info.value.detail

    async def test_connect_error_retries(self, api_client):
        """ConnectError triggers retry and succeeds on recovery."""
        import httpx as httpx_lib
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/collections").mock(
                side_effect=[
                    httpx_lib.ConnectError("connection refused"),
                    Response(200, json=[]),
                ]
            )
            result = await api_client.list_collections()
            assert result == []

    async def test_429_respects_retry_after_header(self, api_client):
        """429 with Retry-After header respects the value."""
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/collections").mock(
                side_effect=[
                    Response(429, headers={"Retry-After": "1"}, json={"detail": "Rate limited"}),
                    Response(200, json=[]),
                ]
            )
            result = await api_client.list_collections()
            assert result == []
            assert len(mock.calls) == 2


class TestAPIClientValidation:
    """Test API key validation."""

    async def test_validate_api_key_success(self, api_client, mock_api):
        """Valid API key returns True."""
        result = await api_client.validate_api_key()
        assert result is True

    async def test_validate_api_key_401(self, api_client):
        """Invalid API key raises PointAPIError with helpful message."""
        with respx.mock(base_url="https://point-api.pinchpoint.dev") as mock:
            mock.get("/v1/collections").mock(
                return_value=Response(401, json={"detail": "Invalid API key"})
            )
            with pytest.raises(PointAPIError) as exc_info:
                await api_client.validate_api_key()
            assert exc_info.value.status_code == 401
            assert "POINT_API_KEY" in exc_info.value.detail
