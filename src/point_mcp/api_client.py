"""HTTP client for the Point Knowledge API."""

from __future__ import annotations

import asyncio
import os

import httpx

from point_mcp import __version__

# Retry config
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


class PointAPIError(Exception):
    """Raised when the Point API returns an error."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Point API error {status_code}: {detail}")


class PointAPIClient:
    """Async HTTP client for point-api.pinchpoint.dev."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = (api_key or os.environ.get("POINT_API_KEY", "")).strip()
        self.base_url = base_url or os.environ.get(
            "POINT_API_URL", "https://point-api.pinchpoint.dev"
        )
        if not self.api_key:
            raise ValueError(
                "POINT_API_KEY environment variable is required. "
                "Get one at https://pinchpoint.dev/point/keys"
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "X-API-Key": self.api_key,
                    "User-Agent": f"point-mcp/{__version__}",
                },
                timeout=30.0,
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict | list:
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.request(
                    method, path, json=json, params=params
                )

                if response.status_code < 400:
                    return response.json()

                # Parse error detail
                detail = response.text
                try:
                    body = response.json()
                    detail = body.get("detail", detail)
                    if isinstance(detail, dict):
                        detail = detail.get("error", str(detail))
                except Exception:
                    pass

                # Non-retryable client errors
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    raise PointAPIError(response.status_code, str(detail))

                # Retryable error — backoff and retry
                last_error = PointAPIError(response.status_code, str(detail))

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        delay = min(float(retry_after), 30.0)
                    else:
                        delay = RETRY_BASE_DELAY * (2 ** attempt)
                else:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)

                await asyncio.sleep(delay)

            except httpx.TimeoutException:
                last_error = PointAPIError(
                    408, f"Request timed out after 30s: {method} {path}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))

            except httpx.ConnectError:
                last_error = PointAPIError(
                    503, f"Cannot connect to Point API at {self.base_url}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))

        raise last_error or PointAPIError(500, "Unknown error after retries")

    async def validate_api_key(self) -> bool:
        """Check if the configured API key is valid."""
        try:
            await self._request("GET", "/v1/collections")
            return True
        except PointAPIError as e:
            if e.status_code == 401:
                raise PointAPIError(
                    401,
                    "Invalid API key. Check your POINT_API_KEY environment variable. "
                    "Get a key at https://pinchpoint.dev/point/keys",
                )
            raise

    async def search(
        self,
        query: str,
        collection: str | None = None,
        doc_type: str | None = None,
        limit: int = 10,
    ) -> dict:
        """POST /v1/search — hybrid search with citations."""
        body: dict = {"query": query, "limit": limit}
        if collection:
            body["collection"] = collection
        if doc_type:
            body["doc_type"] = doc_type
        return await self._request("POST", "/v1/search", json=body)

    async def get_document_toc(self, doc_id: str) -> dict:
        """GET /v1/documents/{doc_id}/toc — lightweight TOC."""
        return await self._request("GET", f"/v1/documents/{doc_id}/toc")

    async def get_sections(self, chunk_ids: list[str]) -> dict:
        """POST /v1/sections/batch — load specific sections by chunk ID."""
        return await self._request(
            "POST", "/v1/sections/batch", json={"chunk_ids": chunk_ids}
        )

    async def list_collections(self) -> list[dict]:
        """GET /v1/collections — list all collections."""
        return await self._request("GET", "/v1/collections")

    async def discover_collections(self, query: str, limit: int = 10) -> dict:
        """GET /v1/collections/discover — semantic search over collections."""
        return await self._request(
            "GET",
            "/v1/collections/discover",
            params={"q": query, "limit": limit},
        )

    async def get_document_full(self, doc_id: str) -> dict:
        """GET /v1/documents/{doc_id}/full — full markdown content."""
        return await self._request("GET", f"/v1/documents/{doc_id}/full")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
