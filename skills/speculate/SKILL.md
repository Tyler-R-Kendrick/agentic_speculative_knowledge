---
name: speculate
description: >-
  Use the speculate skill when you need critique-ready hypotheses from new
  observations: recall context, run the mutation pipeline on a fresh
  observation, retrieve ranked inference and facet results from an
  inference/* branch, and present candidate text, provenance, assumptions,
  uncertainty, and review priority without promoting anything to trusted
  memory.
---

# Speculate

Turn new observations into critique-ready speculative packets by chaining the repository's existing memory, inference, retrieval, and ranking APIs.

## Trigger when

- The user asks “what might explain this?”, “what could this imply?”, or “generate hypotheses”
- You need candidate explanations before trusting or reflecting them
- You need a review packet with provenance, assumptions, uncertainty, and ranking metadata
- You want to compare multiple speculative candidates or alternate framings
- You need to surface facet relations that reveal scope, timeframe, or reframing differences

Do **not** use this skill to promote conclusions to trusted memory. Speculation stays on `inference/*` branches until a reviewer explicitly decides to reflect it.

## Repository-grounded workflow

1. **Recall first** with `MemoryManager.retrieve_context()` or `RetrievalComposer.retrieve()`.
2. **Start a session** with `MemoryManager.start_session()`.
3. **Run one fresh observation through `MutationPipeline.run()`**.  
   This already writes the working item, appends a journal event, extracts claims, optionally writes trusted memories, and generates speculative outputs.  
   Do **not** call `add_working_item()` for the same observation first unless you intentionally want duplicate active-memory entries.
4. **Retrieve speculative results** with:
   - `include_terminus=True`
   - `include_speculative=True`
   - `inference_branch=result.inference_branch`
5. **Assemble a critique packet** from:
   - `context["claims"]`
   - `context["speculative_inference"]`
   - `context["facet_relations"]`
6. **Keep everything speculative** on the `inference/*` branch until reviewed.

## Quick start — end-to-end critique packet

```python
import pathlib
from src.api.memory_manager import MemoryManager
from src.active_memory.models import WorkingItem
from src.persistence.pipeline import MutationPipeline
from src.retrieval.composer import RetrievalComposer
from src.terminus.adapter import TerminusMemoryRepository
from src.manifold_sidecar import ManifoldRankingService

root = pathlib.Path(".agent-memory")
mgr = MemoryManager(root_dir=root)
session = mgr.start_session(current_goal="speculate about auth regression")

# Shared capitalized entity "Auth" helps the current facet generator emit a relation.
observation = (
    "The service Auth failed after a certificate rotation. "
    "The API for Auth started returning 401 errors."
)

baseline = mgr.retrieve_context(include_terminus=False)

repo = TerminusMemoryRepository(url="http://localhost:6363")
pipeline = MutationPipeline(
    root,
    enable_terminus=True,
    terminus_repo=repo,
    manifold_service=ManifoldRankingService(),
    enable_inference=True,
)

result = pipeline.run(
    WorkingItem(
        item_type="observation",
        content=observation,
        session_id=session.session_id,
    ),
    session_id=session.session_id,
)

composer = RetrievalComposer(root, terminus_repo=repo)
context = composer.retrieve(
    include_terminus=True,
    include_speculative=True,
    inference_branch=result.inference_branch,
)

claims_by_id = {claim["claim_id"]: claim for claim in context["claims"]}

critique_packet = {
    "session_id": session.session_id,
    "inference_branch": result.inference_branch,
    "baseline_claim_count": len(baseline["claims"]),
    "claims": context["claims"],
    "candidates": [],
    "facets": [],
}

for node in context["speculative_inference"]:
    critique_packet["candidates"].append(
        {
            "candidate": node["text"],
            "provenance_claim_ids": node.get("generated_from_nodes", []),
            "provenance_claims": [
                claims_by_id[claim_id]["claim_text"]
                for claim_id in node.get("generated_from_nodes", [])
                if claim_id in claims_by_id
            ],
            "assumptions": node.get("assumptions", []),
            "confidence": node.get("confidence"),
            "uncertainty": node.get("uncertainty"),
            "review_priority": node.get("ranking_score"),
            "ranking": {
                "ranking_score": node.get("ranking_score"),
                "relatedness_score": node.get("relatedness_score"),
                "distance_score": node.get("distance_score"),
                "ranking_model_id": node.get("ranking_model_id"),
                "ranking_run_id": node.get("ranking_run_id"),
            },
            "justification": (
                "Review this candidate because it is traceable to extracted claims "
                "and remains explicitly unverified."
            ),
        }
    )

for relation in context["facet_relations"]:
    critique_packet["facets"].append(
        {
            "facet_type": relation.get("facet_type"),
            "source_claim": claims_by_id.get(relation.get("source_node_id"), {}).get("claim_text"),
            "target_claim": claims_by_id.get(relation.get("target_node_id"), {}).get("claim_text"),
            "shared_core_claim": relation.get("shared_core_claim"),
            "differences": relation.get("differences", []),
            "facet_strength": relation.get("facet_strength"),
            "relatedness_score": relation.get("relatedness_score"),
            "distance_score": relation.get("distance_score"),
            "uncertainty": relation.get("uncertainty"),
            "why_it_matters": "Use facet relations to compare alternate framings during critique.",
        }
    )

print(critique_packet)
mgr.end_session()
```

## What a good critique packet must include

For each speculative candidate, include:

1. **Candidate text** — `node["text"]`
2. **Traceable provenance** — use `generated_from_nodes` as the primary link back to extracted claims
3. **Human-readable support** — resolve those claim IDs to `context["claims"]`
4. **Assumptions** — `node["assumptions"]`
5. **Confidence and uncertainty** — `confidence`, `uncertainty`
6. **Ranking metadata** — `ranking_score`, `relatedness_score`, `distance_score`, `ranking_model_id`
7. **Status framing** — keep it clearly speculative/unverified
8. **Short justification** — why this candidate deserves human critique now

For nearby facet relations, include:

1. `facet_type`
2. source/target claim text
3. `shared_core_claim`
4. `differences`
5. `facet_strength`
6. a one-line explanation of why the alternate framing matters

## Practical notes from actual pipeline behavior

- `MutationPipeline.run()` is the safest orchestration entry point: it performs active-memory write, journaling, claim extraction, optional Terminus writes, inference generation, and ranking in one path.
- `RetrievalComposer.retrieve()` only returns speculative results when **all three** are set:
  - `include_terminus=True`
  - `include_speculative=True`
  - `inference_branch=...`
- `TerminusMemoryRepository` falls back to an in-process store when Terminus is unreachable, so the same retrieval flow still works in tests and local no-Terminus runs.
- The current rule-based generator uses `generated_from_nodes` / `generated_from_edges` as reliable provenance. The `supports` field may be empty.
- The current facet generator only emits relations between **adjacent extracted claims that share extracted entities**. If you want facet output, use multi-sentence observations with a shared capitalized entity.
- If manifold ranking fails, inference nodes are still written, but ranking fields may be `None` and `result.ranked_inference_candidates` may stay `0`. Treat provenance-bearing candidates as reviewable even without scores.
- Ranking requires an `inference/*` or `verification/*` branch. Let the pipeline create the `inference/*` branch for you.

## Key APIs

| Class | Method | Purpose |
|---|---|---|
| `MemoryManager` | `start_session()` / `end_session()` | Session lifecycle around speculative work |
| `MemoryManager` | `retrieve_context()` | Convenient recall wrapper before or after speculation |
| `MutationPipeline` | `run()` | Single entry point for write → extract → persist → infer → rank |
| `RetrievalComposer` | `retrieve()` | Compose active, trusted, and speculative layers into one packet |
| `ManifoldRankingService` | `rank_inference_candidates()` / `rank_facet_candidates()` | Supply review-priority metadata |
| `TerminusMemoryRepository` | `ensure_branch()` / `query_inference_nodes()` / `query_facet_relations()` | Direct speculative branch access when needed |

## Grounding

- `src/api/memory_manager.py` — session lifecycle and recall wrapper
- `src/persistence/pipeline.py` — end-to-end mutation pipeline
- `src/retrieval/composer.py` — composed retrieval rules for speculative data
- `src/inference/generator.py` — current rule-based inference and facet generation behavior
- `src/inference/models.py` — `InferenceNode` and `FacetRelation` fields
- `src/manifold_sidecar/service.py` — branch-gated ranking and metadata population
- `src/terminus/adapter.py` — Terminus adapter with fallback local store
- `tests/integration/test_inference_flow.py` — inference persistence and retrieval behavior
- `tests/integration/test_retrieval.py` — base retrieval behavior
- `docs/SKILLS_USAGE.md` — end-to-end skill usage guide

## Rules

1. Use the existing Python APIs in `src/`; do not build a parallel speculation stack.
2. Prefer `MutationPipeline.run()` over hand-stitching pipeline steps.
3. Keep speculative output on `inference/*` branches until review explicitly chooses reflection.
4. Always show provenance, assumptions, and ranking/uncertainty metadata in the critique packet.
5. Use `RetrievalComposer` or `MemoryManager.retrieve_context()` to assemble packets instead of manually merging files and graph queries.
6. Validate any code changes with `python -m pytest`; for behavior checks, `tests/integration/test_inference_flow.py` is the most directly relevant.
