---
name: Daily Feature Extraction
description: |
  Runs the repository's extraction pipeline over recent repository activity and
  publishes a daily feature report as a GitHub issue.
on:
  schedule: daily
  workflow_dispatch:

engine: copilot

permissions:
  contents: read
  issues: read
  pull-requests: read

network:
  allowed:
    - defaults
    - python

tools:
  github:
    toolsets: [default]
    lockdown: false
    min-integrity: none
  bash: true

timeout-minutes: 20

safe-outputs:
  mentions: false
  allowed-github-references: []
  create-issue:
    title-prefix: "[feature-extraction] "
    close-older-issues: true
---

# Daily Feature Extraction

Run this repository's claim and inference extraction pipeline on the most relevant repository activity from the last 24 hours, then publish a short report as a GitHub issue.

## Repository-specific pipeline

Use the project's existing Python modules instead of inventing a new extraction flow:

- `src.claims.extractor.ClaimExtractor`
- `src.persistence.pipeline.MutationPipeline`
- `src.manifold_sidecar.ManifoldRankingService`
- `src.terminus.adapter.TerminusMemoryRepository`

If TerminusDB credentials or a reachable TerminusDB instance are unavailable, let the repository's built-in fallback behavior run and continue the extraction.

## Inputs to extract from

Build the extraction input from the last 24 hours of repository activity:

1. Recent merged pull requests.
2. Recent commits on the default branch.
3. `README.md` for architectural context.
4. Any changed markdown or Python files that look directly relevant to project behavior.

Ignore purely mechanical changes if they do not add meaningful project signal.

## Process

1. Use GitHub tools to gather the recent pull requests and commits.
2. Read the relevant files in the repository to understand what changed.
3. Build a concise input bundle at `/tmp/daily-feature-extraction/input.txt`.
4. Install project dependencies if needed:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e '.[dev]'
   ```

5. Run the repository pipeline with bash using a command like this:

   ```bash
   mkdir -p /tmp/daily-feature-extraction
   python - <<'PY'
   import json
   import os
   import pathlib

   from src.active_memory.models import WorkingItem
   from src.manifold_sidecar import ManifoldRankingService
   from src.persistence.pipeline import MutationPipeline
   from src.terminus.adapter import TerminusMemoryRepository

   input_path = pathlib.Path("/tmp/daily-feature-extraction/input.txt")
   root_dir = pathlib.Path("/tmp/daily-feature-extraction/state")
   root_dir.mkdir(parents=True, exist_ok=True)

   repo = TerminusMemoryRepository(
       url=os.getenv("TERMINUSDB_URL", "http://127.0.0.1:6363"),
       team=os.getenv("TERMINUSDB_TEAM", "admin"),
       db=os.getenv("TERMINUSDB_DB", "agent_memory"),
       user=os.getenv("TERMINUSDB_USER"),
       password=os.getenv("TERMINUSDB_PASSWORD"),
   )

   pipeline = MutationPipeline(
       root_dir,
       enable_terminus=True,
       terminus_repo=repo,
       manifold_service=ManifoldRankingService(),
       enable_inference=True,
   )

   result = pipeline.run(
       WorkingItem(
           item_type="observation",
           content=input_path.read_text(),
           session_id="daily-feature-extraction",
           metadata={"source": "daily-agentic-workflow"},
       ),
       session_id="daily-feature-extraction",
   )

   claims_path = root_dir / "active" / "claims" / "extracted.jsonl"
   claims = claims_path.read_text().strip().splitlines() if claims_path.exists() else []
   payload = {
       "success": result.success,
       "claims_extracted": result.claims_extracted,
       "terminus_written": result.terminus_written,
       "inference_candidates": result.inference_candidates,
       "ranked_inference_candidates": result.ranked_inference_candidates,
       "facet_relations_written": result.facet_relations_written,
       "inference_branch": result.inference_branch,
       "errors": result.errors,
       "claim_rows": [json.loads(row) for row in claims[:5]],
   }
   result_path = pathlib.Path("/tmp/daily-feature-extraction/result.json")
   result_path.write_text(json.dumps(payload, indent=2))
   print(result_path.read_text())
   PY
   ```

6. Read `/tmp/daily-feature-extraction/result.json` and summarize the outcome.

## Output requirements

If there was no meaningful recent activity or the extraction produced no useful signal, exit without creating an issue.

Otherwise, create a GitHub issue that includes:

- The time window you analyzed.
- The pull requests or commits used as source material.
- Pipeline counts for claims, inference candidates, ranked inference candidates, and facet relations.
- Up to five representative extracted claims.
- Any pipeline errors or TerminusDB fallback notes.

Keep the report concise and factual.
