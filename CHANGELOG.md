# Changelog

## 0.1.0 (2026-03-28)

Initial release.

- 5 MCP tools: `search`, `get_document_toc`, `get_sections`, `list_collections`, `get_document_full`
- stdio transport (works with Claude Code, Cursor, Windsurf, VS Code)
- API key authentication via `POINT_API_KEY` environment variable
- Retry logic with exponential backoff for transient errors (429, 502, 503, 504)
- User-friendly error messages for all failure modes
