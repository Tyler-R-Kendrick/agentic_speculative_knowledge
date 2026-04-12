---
runtimes:
  python:
    version: "3.12"
  uv:
    version: "latest"

mcp-servers:
  agent-skills:
    url: "http://host.docker.internal:3002/mcp"
    allowed: [find_agent_skill, load_agent_skill, run_agent_skill]

network:
  allowed:
    - defaults
    - github
    - python
---

# Agent Skills Runtime

Use the configured `agent-skills` MCP server to discover and run `trainer-*` skills from the current repository checkout.
