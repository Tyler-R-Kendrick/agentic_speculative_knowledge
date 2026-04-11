---
name: speculate
description: >-
  Use the speculate skill to orchestrate recall, memorize, infer, discover,
  and reflect into a critique-friendly workflow that generates new knowledge
  candidates and displays reasoning traces, assumptions, evidence, ranking
  metadata, and justifications for review.
---

# Speculate

Generate critique-ready speculative knowledge by chaining the repository's
existing memory, inference, retrieval, and discovery APIs.

## When to use

- Exploring hypotheses from fresh observations without promoting them to trusted knowledge yet
- Packaging speculative candidates so another reviewer can critique the reasoning trace
- Showing which claims, assumptions, supports, facets, and ranking signals produced a candidate
- Comparing multiple candidate explanations before deciding what should be reflected into trusted memory

## Quick start — produce a critique packet

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
session = mgr.start_session(current_goal="speculate about auth failures")

observation = "The auth service returned 401 after a certificate rotation."
mgr.add_working_item(item_type="observation", content=observation)
claims = mgr.extract_claims(text=observation, source_ref="incident-42")

repo = TerminusMemoryRepository(url="http://localhost:6363")
ranker = ManifoldRankingService()
pipeline = MutationPipeline(
    root,
    enable_terminus=True,
    terminus_repo=repo,
    manifold_service=ranker,
    enable_inference=True,
)

result = pipeline.run(
    WorkingItem(item_type="observation", content=observation, session_id=session.session_id),
    session_id=session.session_id,
)

composer = RetrievalComposer(root, terminus_repo=repo)
context = composer.retrieve(
    include_terminus=True,
    include_speculative=True,
    inference_branch=result.inference_branch,
)

claim_index = {claim["claim_id"]: claim for claim in context["claims"]}

for node in context["speculative_inference"]:
    trace = {
        "candidate": node["text"],
        "supports": [
            claim_index.get(claim_id, {"claim_text": claim_id})["claim_text"]
            for claim_id in node.get("generated_from_nodes", [])
        ],
        "assumptions": node.get("assumptions", []),
        "confidence": node.get("confidence"),
        "ranking_score": node.get("ranking_score"),
        "relatedness_score": node.get("relatedness_score"),
        "uncertainty": node.get("uncertainty"),
        "justification": (
            "Review because the candidate is derived from explicit claims and "
            "includes manifold ranking metadata for critique."
        ),
    }
    print(trace)

for relation in context["facet_relations"]:
    print(
        {
            "facet_type": relation.get("facet_type"),
            "shared_core_claim": relation.get("shared_core_claim"),
            "differences": relation.get("differences", []),
            "facet_strength": relation.get("facet_strength"),
            "why_it_matters": "Facet relations expose alternate framings to critique.",
        }
    )

mgr.end_session()
```

## Reasoning-trace checklist

For each speculative candidate, display:

1. The candidate text itself
2. The supporting claim IDs or claim texts from `generated_from_nodes`
3. Assumptions from `assumptions`
4. Confidence and uncertainty values
5. Ranking metadata such as `ranking_score`, `relatedness_score`, and `distance_score`
6. Nearby facet relations that show alternate scope, timeframe, or framing
7. A short human-readable justification explaining why the candidate is worth critique

## Key APIs

| Class | Method | Purpose |
|---|---|---|
| `MemoryManager` | `start_session()` / `add_working_item()` / `extract_claims()` | Capture the observation that seeds speculation |
| `MutationPipeline` | `run()` | Generate and persist speculative candidates on an `inference/*` branch |
| `RetrievalComposer` | `retrieve()` | Recover claims, inference nodes, and facet relations into one critique packet |
| `ManifoldRankingService` | `rank_inference_candidates()` / `rank_facet_candidates()` | Supply ranking signals that justify review priority |
| `TerminusMemoryRepository` | `query_inference_nodes()` / `query_facet_relations()` | Read speculative graph data directly when needed |

## Grounding

- `src/api/memory_manager.py` — session, working memory, and claim extraction entry point
- `src/persistence/pipeline.py` — mutation pipeline orchestration
- `src/retrieval/composer.py` — composed retrieval of active, trusted, and speculative layers
- `src/inference/generator.py` — inference and facet generation logic
- `src/manifold_sidecar/service.py` — ranking metadata and manifold scoring
- `src/terminus/adapter.py` — speculative graph persistence and query access
- `tests/integration/test_inference_flow.py` — inference and discovery integration coverage
- `tests/integration/test_retrieval.py` — retrieval integration coverage
- `notebooks/02_speculative_inference_and_facets.ipynb` — pipeline and candidate generation walkthrough
- `notebooks/03_historical_recall.ipynb` — composed recall walkthrough
- `notebooks/05_knowledge_discovery_through_facets.ipynb` — facet discovery walkthrough
- `notebooks/06_manifold_mapping_for_discovery.ipynb` — manifold ranking walkthrough

## Rules

1. Orchestrate speculation with the existing APIs in `src/`; do not invent a parallel speculation stack.
2. Use `MutationPipeline` from `src/persistence/pipeline.py` to keep claim extraction, speculative writes, and ranking aligned.
3. Use `RetrievalComposer` from `src/retrieval/composer.py` to assemble critique packets instead of hand-merging files and graph queries.
4. Keep speculative output on `inference/*` branches until a reviewer explicitly chooses to reflect trusted conclusions.
5. Every displayed candidate should include traceable provenance, assumptions, and justification so other agents can accurately critique it.
