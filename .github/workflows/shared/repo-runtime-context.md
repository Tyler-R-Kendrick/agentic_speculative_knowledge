# Repository Runtime Context

Use the checked-in repository assets as the source of truth for trainer
execution instead of inventing parallel copies inside the workflow.

- **Agents**: `.github/agents/` contains the imported `trainer.agent.md`
  orchestrator plus sibling handoff agents (`researcher`, `engineer`, `judge`,
  `teacher`, `student`, `adversary`, `conservator`).
- **MCP servers**: `shared/agent-skills-runtime.md` configures the
  `agent-skills` MCP server; its implementation lives under
  `tools/agent-skills-mcp/`.
- **Skills**: canonical skill content lives under `skills/` and
  `.agents/skills/`. This repository's six skills are:
  `memorize`, `recall`, `infer`, `reflect`, `discover`, `speculate`.
- **Source**: the Python implementation lives under `src/` and provides
  `MemoryManager`, `MutationPipeline`, `RetrievalComposer`,
  `TerminusMemoryRepository`, and `ManifoldRankingService`.
- **Documentation**: `docs/SKILLS_USAGE.md` and `README.md` describe the
  speculative knowledge architecture; prefer these over inferred context.

Treat the current repository checkout as the execution environment for these
assets. Reuse the existing agents, MCP server configuration, skills, and hooks
from the repository instead of creating substitute workflow-local versions.
