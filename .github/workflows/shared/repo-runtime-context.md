# Repository Runtime Context

Use the checked-in repository assets as the source of truth for trainer
execution instead of inventing parallel copies inside the workflow.

- **Agents**: `.github/agents/` contains the trainer agents (trainer,
  researcher, engineer, judge, teacher, student, adversary, conservator).
  These are overlaid from the upstream `copilot-auto-training` repository
  at workflow runtime by `copilot-setup-steps.yml` and are NOT committed
  to this repository.
- **MCP servers**: `shared/agent-skills-runtime.md` configures the
  `agent-skills` MCP server; its implementation lives under
  `tools/agent-skills-mcp/`.  The Python source (`agent_skills_mcp.py`,
  `server.py`) is overlaid from upstream at runtime; the `pyproject.toml`
  is repo-specific and committed.
- **Skills**: canonical skill content lives under `skills/` and
  `.agents/skills/`. This repository's six skills are:
  `memorize`, `recall`, `infer`, `reflect`, `discover`, `speculate`.
- **Source**: the Python implementation lives under `src/` and provides
  `MemoryManager`, `MutationPipeline`, `RetrievalComposer`,
  `TerminusMemoryRepository`, and `ManifoldRankingService`.
- **Documentation**: `docs/SKILLS_USAGE.md` and `README.md` describe the
  speculative knowledge architecture; prefer these over inferred context.

Treat the current repository checkout (with runtime overlays applied) as
the execution environment.  Reuse the existing agents, MCP server
configuration, skills, and hooks from the repository instead of creating
substitute workflow-local versions.
