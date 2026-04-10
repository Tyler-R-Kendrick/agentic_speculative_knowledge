---
name: infer
description: >-
  Use the infer skill to generate speculative inference candidates from
  claims, persist them on branch-local inference graphs, and run the full
  mutation pipeline that coordinates active memory, claims, Terminus
  persistence, and speculative ranking.
---

# Infer

Generate speculative knowledge from existing claims and persist it on
isolated inference branches.

## When to use

- Running the mutation pipeline end-to-end on new observations
- Generating inference candidates (abductive, heuristic, predictive, etc.)
- Producing facet relation candidates between claims
- Persisting ranked speculative output to a Terminus inference branch

## Quick start

```python
import pathlib
from src.active_memory.models import WorkingItem
from src.persistence.pipeline import MutationPipeline
from src.terminus.adapter import TerminusMemoryRepository
from src.manifold_sidecar import ManifoldRankingService

root = pathlib.Path(".agent-memory")
repo = TerminusMemoryRepository(url="http://localhost:6363")
ranker = ManifoldRankingService()

pipeline = MutationPipeline(
    root,
    enable_terminus=True,
    terminus_repo=repo,
    manifold_service=ranker,
    enable_inference=True,
)

item = WorkingItem(
    item_type="observation",
    content="The auth service failed after a certificate rotation.",
    session_id="sess-1",
)

result = pipeline.run(item, session_id="sess-1")

print(result.inference_candidates)        # number of candidates generated
print(result.ranked_inference_candidates)  # number ranked by manifold sidecar
print(result.inference_branch)             # e.g. "inference/sess-1"
```

### Using the generator directly

```python
from src.inference.generator import InferenceGenerator
from src.claims.extractor import ClaimExtractor

extractor = ClaimExtractor()
claims = extractor.extract(text="The API started returning 401 errors.")

generator = InferenceGenerator()
candidates = generator.generate_from_claims(
    claims,
    source_branch="inference/sess-1",
    source_commit="journal-event-abc",
    session_id="sess-1",
)
facets = generator.generate_facet_candidates(
    claims,
    provenance_commit="journal-event-abc",
    source_branch="inference/sess-1",
)
```

## Key APIs

| Class | Method | Purpose |
|---|---|---|
| `MutationPipeline` | `run()` | Full pipeline: active write → journal → claims → Terminus → inference → ranking |
| `InferenceGenerator` | `generate_from_claims()` | Produce `InferenceNode` candidates from a list of claims |
| `InferenceGenerator` | `generate_facet_candidates()` | Produce `FacetRelation` candidates between adjacent claims |

## Grounding

- `src/persistence/pipeline.py` — mutation pipeline orchestration
- `src/inference/generator.py` — rule-based inference and facet generation
- `src/inference/models.py` — `InferenceNode` and `FacetRelation` schemas
- `src/claims/extractor.py` — upstream claim extraction
- `tests/integration/test_inference_flow.py` — integration coverage
- `notebooks/02_speculative_inference_and_facets.ipynb` — executable walkthrough

## Rules

1. Route orchestration through `MutationPipeline` in `src/persistence/pipeline.py` so all pipeline steps stay synchronized.
2. Reuse `InferenceGenerator` from `src/inference/generator.py` for candidate creation.
3. Speculative output must stay on `inference/*` branches; never write directly to trusted memory.
4. Validate with `tests/integration/test_inference_flow.py`.
