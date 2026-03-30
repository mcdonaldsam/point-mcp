"""Shared fixtures for Point MCP tests."""

import pytest
import respx

from point_mcp.api_client import PointAPIClient


SEARCH_RESPONSE = {
    "query": "OAuth PKCE flow",
    "results": [
        {
            "chunk_id": "chunk-abc-001",
            "relevance_score": 87.3,
            "text": "PKCE (Proof Key for Code Exchange) is an extension to the authorization code flow...",
            "citation": {
                "formatted": "RFC 7636, Section 1 (2015)",
                "doc_id": "rfc-7636",
                "doc_type": "rfc",
                "title": "Proof Key for Code Exchange by OAuth Public Clients",
                "section_id": "sec-1",
                "heading_path": ["Introduction"],
                "source_url": "https://datatracker.ietf.org/doc/html/rfc7636",
                "effective_date": "2015-09-01",
                "collection": "rfc-ietf",
            },
            "document_context": {
                "doc_id": "rfc-7636",
                "title": "Proof Key for Code Exchange by OAuth Public Clients",
                "total_sections": 12,
                "sibling_headings": ["Terminology", "Protocol", "Security Considerations"],
            },
            "publisher_tier": "verified",
            "word_count": 45,
            "token_estimate": 58,
            "collection_star_count": 12,
            "is_bookmarked": False,
            "category": "technology/security/oauth",
            "provenance": "official",
            "quality": "reviewed",
        }
    ],
    "context": "According to RFC 7636, Section 1 (2015): PKCE (Proof Key for Code Exchange) is an extension to the authorization code flow...",
    "pipeline": {"search_ms": 42, "rerank_ms": 0, "total_ms": 42},
    "facets": {"provenance": {"official": 1}, "quality": {"reviewed": 1}, "category": {"technology": 1}},
}

TOC_RESPONSE = {
    "doc_id": "rfc-7636",
    "title": "Proof Key for Code Exchange by OAuth Public Clients",
    "doc_type": "rfc",
    "collection": "rfc-ietf",
    "doc_group": "rfc",
    "version": "1.0",
    "effective_date": "2015-09-01",
    "total_chunks": 3,
    "sections": [
        {"chunk_id": "chunk-abc-001", "heading_path": ["Introduction"], "level": 1, "word_count": 120},
        {"chunk_id": "chunk-abc-002", "heading_path": ["Introduction", "Terminology"], "level": 2, "word_count": 80},
        {"chunk_id": "chunk-abc-003", "heading_path": ["Protocol"], "level": 1, "word_count": 350},
    ],
}

SECTIONS_RESPONSE = {
    "results": [
        {
            "chunk_id": "chunk-abc-001",
            "text": "PKCE is an extension to the authorization code flow...",
            "heading_path": ["Introduction"],
            "word_count": 120,
            "citation": {
                "formatted": "RFC 7636, Section 1 (2015)",
                "doc_id": "rfc-7636",
                "doc_type": "rfc",
                "title": "Proof Key for Code Exchange by OAuth Public Clients",
                "section_id": "sec-1",
                "heading_path": ["Introduction"],
                "source_url": "https://datatracker.ietf.org/doc/html/rfc7636",
                "effective_date": "2015-09-01",
                "collection": "rfc-ietf",
            },
        }
    ],
    "total_tokens_approx": 156,
}

COLLECTIONS_RESPONSE = [
    {"id": "rfc-ietf", "name": "IETF RFCs", "description": "Internet Engineering Task Force standards", "document_count": 42},
    {"id": "aws-docs", "name": "AWS Documentation", "description": "Amazon Web Services official docs", "document_count": 156},
]

DISCOVER_RESPONSE = {
    "query": "machine learning",
    "results": [
        {
            "collection_id": "pytorch-docs",
            "name": "PyTorch Documentation",
            "description": "Official PyTorch framework docs",
            "star_count": 8,
            "publisher_tier": "verified",
            "similarity_score": 0.8742,
            "document_count": 34,
        }
    ],
}

DOCUMENT_FULL_RESPONSE = {
    "doc_id": "rfc-7636",
    "title": "Proof Key for Code Exchange by OAuth Public Clients",
    "version": "1.0",
    "effective_date": "2015-09-01",
    "markdown": "# Proof Key for Code Exchange\n\n## Introduction\n\nPKCE is an extension...",
}


@pytest.fixture
def api_client():
    """Create a PointAPIClient with a test key."""
    return PointAPIClient(api_key="test-key-123", base_url="https://point-api.pinchpoint.dev")


@pytest.fixture
def mock_api():
    """Mock all Point API endpoints with sample responses."""
    with respx.mock(base_url="https://point-api.pinchpoint.dev", assert_all_called=False) as mock:
        mock.post("/v1/search").mock(return_value=respx.MockResponse(200, json=SEARCH_RESPONSE))
        mock.get("/v1/documents/rfc-7636/toc").mock(return_value=respx.MockResponse(200, json=TOC_RESPONSE))
        mock.post("/v1/sections/batch").mock(return_value=respx.MockResponse(200, json=SECTIONS_RESPONSE))
        mock.get("/v1/collections").mock(return_value=respx.MockResponse(200, json=COLLECTIONS_RESPONSE))
        mock.get("/v1/collections/discover").mock(return_value=respx.MockResponse(200, json=DISCOVER_RESPONSE))
        mock.get("/v1/documents/rfc-7636/full").mock(return_value=respx.MockResponse(200, json=DOCUMENT_FULL_RESPONSE))
        yield mock
