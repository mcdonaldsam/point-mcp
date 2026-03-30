"""Point MCP Server — verified knowledge for AI systems.

Provides 5 tools for searching and retrieving curated knowledge:
- search: Hybrid search with citations
- get_document_toc: Lightweight document structure
- get_sections: Batch load specific sections
- list_collections: Browse available knowledge
- get_document_full: Full markdown when needed
"""

from __future__ import annotations

from fastmcp import FastMCP

from point_mcp.api_client import PointAPIClient, PointAPIError

mcp = FastMCP(
    "Point Knowledge API",
    instructions=(
        "Point is a verified knowledge API. Use these tools to find authoritative, "
        "citable information. Recommended workflow: (1) search or list_collections to "
        "find relevant content, (2) get_document_toc for structure, (3) get_sections "
        "for specific passages. Use get_document_full only when you need the complete text."
    ),
)

_client: PointAPIClient | None = None


def _get_client() -> PointAPIClient:
    global _client
    if _client is None:
        _client = PointAPIClient()
    return _client


def _format_error(e: PointAPIError) -> str:
    """Convert API errors to user-friendly messages."""
    error_messages = {
        401: (
            "Authentication failed. Your POINT_API_KEY may be invalid or expired. "
            "Get a new key at https://pinchpoint.dev/point/keys"
        ),
        403: "Access denied. Your API key may not have permission for this resource.",
        404: "Not found. The document or collection ID may be incorrect.",
        408: "Request timed out. The Point API may be temporarily slow. Try again.",
        410: "This content has been withdrawn by its publisher.",
        429: (
            "Rate limit exceeded. The Point API allows 60 searches per minute. "
            "Wait a moment and try again."
        ),
        503: (
            "Point API is temporarily unavailable. "
            "Check https://status.pinchpoint.dev or try again in a minute."
        ),
    }
    return error_messages.get(e.status_code, f"API error ({e.status_code}): {e.detail}")


@mcp.tool()
async def search(
    query: str,
    collection: str | None = None,
    doc_type: str | None = None,
    limit: int = 10,
) -> str:
    """Search Point's verified knowledge base using hybrid search (BM25 + vector).

    Returns ranked results with relevance scores, text excerpts, and citations.
    Each result includes a pre-formatted citation you can use directly.

    Args:
        query: Natural language search query (e.g. "how does OAuth 2.0 PKCE work")
        collection: Optional collection ID to search within (e.g. "rfc-ietf").
                    Omit to search all collections.
        doc_type: Optional document type filter (e.g. "rfc", "standard", "guide")
        limit: Max results to return (1-50, default 10). Use 3-5 for focused queries.
    """
    try:
        client = _get_client()
        data = await client.search(
            query=query,
            collection=collection,
            doc_type=doc_type,
            limit=limit,
        )
    except PointAPIError as e:
        return _format_error(e)

    results = data.get("results", [])
    if not results:
        return f"No results found for: {query}"

    count = len(results)
    lines = [f"Found {count} {'result' if count == 1 else 'results'} for: {query}\n"]
    for i, r in enumerate(results, 1):
        citation = r.get("citation", {})
        score = r.get("relevance_score", 0)
        lines.append(f"--- Result {i} (score: {score}%) ---")
        lines.append(f"Citation: {citation.get('formatted', 'N/A')}")
        lines.append(f"Doc: {citation.get('doc_id', '')} | "
                     f"Collection: {citation.get('collection', '')}")
        if citation.get("heading_path"):
            lines.append(f"Section: {' > '.join(citation['heading_path'])}")
        lines.append(f"Chunk ID: {r.get('chunk_id', '')}")
        lines.append(f"Text: {r.get('text', '')}")

        doc_ctx = r.get("document_context")
        if doc_ctx and doc_ctx.get("sibling_headings"):
            siblings = doc_ctx["sibling_headings"][:5]
            lines.append(f"Other sections in this doc: {', '.join(siblings)}")

        lines.append("")

    context = data.get("context", "")
    if context:
        lines.append("--- Context (ready for prompt use) ---")
        lines.append(context)

    return "\n".join(lines)


@mcp.tool()
async def get_document_toc(doc_id: str) -> str:
    """Get a lightweight table of contents for a document (~50 tokens).

    Use this to understand document structure before loading specific sections.
    Returns chunk IDs that you can pass to get_sections.

    Args:
        doc_id: Document ID (from search results or collection listings)
    """
    try:
        client = _get_client()
        data = await client.get_document_toc(doc_id)
    except PointAPIError as e:
        return _format_error(e)

    lines = [
        f"# {data.get('title', 'Untitled')}",
        f"Type: {data.get('doc_type', '')} | Collection: {data.get('collection', '')}",
        f"Version: {data.get('version', '')} | Date: {data.get('effective_date', '')}",
        f"Total sections: {data.get('total_chunks', 0)}",
        "",
    ]
    for entry in data.get("sections", []):
        indent = "  " * (entry.get("level", 1) - 1)
        heading = " > ".join(entry.get("heading_path", []))
        words = entry.get("word_count", 0)
        chunk_id = entry.get("chunk_id", "")
        lines.append(f"{indent}- [{chunk_id}] {heading} ({words} words)")

    return "\n".join(lines)


@mcp.tool()
async def get_sections(chunk_ids: list[str]) -> str:
    """Load specific document sections by their chunk IDs (max 50 per request).

    Use after search or get_document_toc to retrieve full text of specific passages.
    Each section includes its text, heading path, word count, and citation.

    Args:
        chunk_ids: List of chunk IDs to load (get these from search results or TOC).
                   Max 50 per request.
    """
    if len(chunk_ids) > 50:
        return "Error: Maximum 50 chunk IDs per request. Split into multiple calls."
    if not chunk_ids:
        return "Error: Provide at least one chunk ID."

    try:
        client = _get_client()
        data = await client.get_sections(chunk_ids)
    except PointAPIError as e:
        return _format_error(e)

    results = data.get("results", [])
    tokens = data.get("total_tokens_approx", 0)
    lines = [f"Loaded {len(results)} sections (~{tokens} tokens)\n"]

    for section in results:
        citation = section.get("citation", {})
        heading = " > ".join(section.get("heading_path", []))
        lines.append(f"--- [{section.get('chunk_id', '')}] {heading} ---")
        lines.append(f"Citation: {citation.get('formatted', '')}")
        lines.append(f"Words: {section.get('word_count', 0)}")
        lines.append(section.get("text", ""))
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def list_collections(query: str | None = None) -> str:
    """Browse or search available knowledge collections.

    Without a query, lists all collections with document counts.
    With a query, performs semantic search to find relevant collections.

    Args:
        query: Optional search query to find relevant collections
               (e.g. "machine learning frameworks"). Omit to list all.
    """
    try:
        client = _get_client()
        if query:
            data = await client.discover_collections(query)
            collections = data.get("results", [])
            lines = [f"Collections matching '{query}':\n"]
            for c in collections:
                score = c.get("similarity_score", 0)
                lines.append(f"- **{c.get('name', '')}** (id: {c.get('collection_id', '')})")
                lines.append(f"  {c.get('description', 'No description')}")
                lines.append(f"  Docs: {c.get('document_count', 0)} | "
                             f"Relevance: {round(score * 100, 1)}% | "
                             f"Tier: {c.get('publisher_tier', 'community')}")
                lines.append("")
        else:
            collections = await client.list_collections()
            lines = [f"Available collections ({len(collections)}):\n"]
            for c in collections:
                lines.append(f"- **{c.get('name', '')}** (id: {c.get('id', '')})")
                lines.append(f"  {c.get('description', 'No description')}")
                lines.append(f"  Documents: {c.get('document_count', 0)}")
                lines.append("")
    except PointAPIError as e:
        return _format_error(e)

    return "\n".join(lines)


@mcp.tool()
async def get_document_full(doc_id: str) -> str:
    """Get the full markdown content of a document.

    WARNING: This can be large (thousands of tokens). Prefer get_document_toc +
    get_sections for targeted retrieval. Use this only when you need the complete text.

    Args:
        doc_id: Document ID (from search results or collection listings)
    """
    try:
        client = _get_client()
        data = await client.get_document_full(doc_id)
    except PointAPIError as e:
        return _format_error(e)

    title = data.get("title", "Untitled")
    version = data.get("version", "")
    eff_date = data.get("effective_date", "")
    markdown = data.get("markdown", "")

    word_count = len(markdown.split())
    token_estimate = int(word_count * 1.3)

    lines = [
        f"# {title}",
        f"Version: {version} | Date: {eff_date} | ~{token_estimate} tokens",
        "",
        markdown,
    ]
    return "\n".join(lines)


def main():
    """Entry point for the point-mcp CLI command."""
    import sys

    if "--version" in sys.argv or "-v" in sys.argv:
        from point_mcp import __version__
        print(f"point-mcp {__version__}")
        sys.exit(0)

    if "--help" in sys.argv or "-h" in sys.argv:
        print("Point MCP Server — verified knowledge for AI systems")
        print()
        print("Usage: point-mcp")
        print()
        print("Environment variables:")
        print("  POINT_API_KEY    (required) Your Point API key")
        print("  POINT_API_URL    (optional) API base URL (default: https://point-api.pinchpoint.dev)")
        print()
        print("Options:")
        print("  --version, -v    Show version and exit")
        print("  --help, -h       Show this help and exit")
        sys.exit(0)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
