---
name: discover
description: >-
  Use the discover skill to find connections between claims through facet
  relations and to rank inference and facet candidates using manifold
  geometry. Covers facet modeling, manifold scoring, relatedness,
  distance, uncertainty, and retrieval of discovery results.
---

# Discover

Find new connections across knowledge through facets and geometric ranking.

## When to use

- Generating facet relations between related claims (paraphrase, abstraction, scope, timeframe)
- Ranking inference or facet candidates with the manifold sidecar
- Retrieving discovery results including ranked speculative inference and facet relations
- Inspecting ranking metadata (relatedness, distance, uncertainty, facet strength)

## Quick start — facet generation

```python
from src.inference.generator import InferenceGenerator
from src.claims.extractor import ClaimExtractor

extractor = ClaimExtractor()
claims = extractor.extract(
    text="The auth service failed. The API returned 401 errors.",
    source_ref="incident-42",
)

generator = InferenceGenerator()
facets = generator.generate_facet_candidates(
    claims,
    provenance_commit="journal-event-abc",
    source_branch="inference/sess-1",
)

for f in facets:
    print(f.facet_type, f.shared_core_claim, f.differences)
```

## Quick start — manifold ranking

```python
from src.manifold_sidecar import ManifoldRankingService, ManifoldRankingRequest
from src.inference.generator import InferenceGenerator
from src.claims.extractor import ClaimExtractor

extractor = ClaimExtractor()
claims = extractor.extract(text="Database writes slowed after index rebuild.")

generator = InferenceGenerator()
candidates = generator.generate_from_claims(
    claims,
    source_branch="inference/sess-1",
    source_commit="evt-1",
    session_id="sess-1",
)
facets = generator.generate_facet_candidates(
    claims,
    provenance_commit="evt-1",
    source_branch="inference/sess-1",
)

svc = ManifoldRankingService()

# Rank inference candidates
inference_ranking = svc.rank_inference_candidates(
    ManifoldRankingRequest(
        branch_name="inference/sess-1",
        ranking_mode="inference_candidate_ranking",
        seed_context={"session_id": "sess-1"},
        candidates=candidates,
    )
)
for c in inference_ranking.candidates:
    print(c.ranking_score, c.relatedness_score, c.uncertainty)

# Rank facet candidates
facet_ranking = svc.rank_facet_candidates(
    ManifoldRankingRequest(
        branch_name="inference/sess-1",
        ranking_mode="facet_candidate_ranking",
        seed_context={"session_id": "sess-1"},
        candidates=facets,
    )
)
for f in facet_ranking.candidates:
    print(f.facet_strength, f.relatedness_score, f.distance_score)
```

## Quick start — discovery retrieval

```python
import pathlib
from src.retrieval.composer import RetrievalComposer
from src.terminus.adapter import TerminusMemoryRepository

root = pathlib.Path(".agent-memory")
repo = TerminusMemoryRepository(url="http://localhost:6363")
composer = RetrievalComposer(root, terminus_repo=repo)

result = composer.retrieve(
    include_terminus=True,
    include_speculative=True,
    inference_branch="inference/sess-1",
)

for node in result["speculative_inference"]:
    print(node.get("ranking_score"), node.get("text"))
for rel in result["facet_relations"]:
    print(rel.get("facet_type"), rel.get("facet_strength"))
```

## Key APIs

| Class | Method | Purpose |
|---|---|---|
| `InferenceGenerator` | `generate_facet_candidates()` | Produce `FacetRelation` candidates between claims |
| `ManifoldRankingService` | `rank_inference_candidates()` | Score and sort `InferenceNode` candidates |
| `ManifoldRankingService` | `rank_facet_candidates()` | Score and sort `FacetRelation` candidates |
| `ManifoldRankingService` | `get_current_model_metadata()` | Inspect active model, geometry, and feature list |
| `RetrievalComposer` | `retrieve()` | Compose context including speculative and facet results |

## Grounding

- `src/inference/models.py` — `InferenceNode` and `FacetRelation` schemas
- `src/inference/generator.py` — facet generation logic
- `src/manifold_sidecar/service.py` — manifold ranking service
- `src/manifold_sidecar/models.py` — ranking request/response models
- `src/retrieval/composer.py` — composed retrieval with discovery layers
- `tests/integration/test_inference_flow.py` — integration coverage
- `notebooks/05_knowledge_discovery_through_facets.ipynb` — facet discovery walkthrough
- `notebooks/06_manifold_mapping_for_discovery.ipynb` — manifold ranking walkthrough

## Rules

1. Use `InferenceGenerator` from `src/inference/generator.py` for facet candidate creation.
2. Use `ManifoldRankingService` from `src/manifold_sidecar/service.py` for all scoring — never hard-code scores outside the sidecar.
3. Manifold ranking requires `inference/*` or `verification/*` branch context; a `ManifoldBranchContextError` is raised otherwise.
4. Ranking metadata is advisory; it does not change trust status. Facets remain speculative until explicitly promoted.
5. Validate with `tests/integration/test_inference_flow.py`.
