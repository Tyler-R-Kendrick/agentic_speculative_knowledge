from __future__ import annotations

import os

from agent_skills_mcp import build_mcp


def main() -> None:
    # The server rereads skills from disk on each tool or resource call so edits hotload without a watcher.
    # Set MCP_TRANSPORT=sse to run as an HTTP/SSE server (MCP_HOST/MCP_PORT control bind address).
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    kwargs: dict = {}
    if transport != "stdio":
        kwargs["host"] = os.environ.get("MCP_HOST", "0.0.0.0")
        kwargs["port"] = int(os.environ.get("MCP_PORT", "3002"))
    build_mcp(**kwargs).run(transport=transport)


if __name__ == "__main__":
    main()
