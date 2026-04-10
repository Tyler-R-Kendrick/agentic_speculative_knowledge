---
name: reflect
description: >-
  Use the reflect skill to persist memories, claims, and inference nodes
  into the TerminusDB temporal graph. Covers branch lifecycle, trusted
  session writes, temporal recall, and the separation between session and
  inference branches.
---

# Reflect

Persist and reason over long-term knowledge in the temporal graph.

## When to use

- Writing memories or claims to a persistent Terminus branch
- Creating or managing session and inference branches
- Querying the temporal graph for trusted or branch-local data
- Verifying the separation between trusted and speculative branches

## Quick start

```python
from src.terminus.adapter import TerminusMemoryRepository
from src.terminus.branch_manager import (
    BranchManager,
    session_branch_name,
    inference_branch_name,
)

repo = TerminusMemoryRepository(url="http://localhost:6363")

# Create a session branch
branch = repo.ensure_branch(session_branch_name("sess-1"))

# Write a claim to the session branch
from src.claims.models import Claim
claim = Claim(claim_text="Cert rotation caused auth failures.", claim_type="observation")
repo.write_claim(branch, claim)

# Write a memory
from src.normalization.mapper import ClaimToMemoryMapper
mapper = ClaimToMemoryMapper()
memories = mapper.map_many([claim], session_id="sess-1")
for m in memories:
    m.source_branch = branch
    repo.write_memory(branch, m)

# Query trusted memories
trusted = repo.query_memories(branch="session/sess-1")

# Query inference nodes on a speculative branch
inference_br = repo.ensure_branch(inference_branch_name("sess-1"))
nodes = repo.query_inference_nodes(inference_br)
```

### Branch manager helpers

```python
from src.terminus.branch_manager import session_branch_name, inference_branch_name

session_branch_name("sess-1")    # → "session/sess-1"
inference_branch_name("sess-1")  # → "inference/sess-1"
```

## Key APIs

| Class | Method | Purpose |
|---|---|---|
| `TerminusMemoryRepository` | `ensure_branch()` | Create a branch if it does not exist |
| `TerminusMemoryRepository` | `write_memory()` | Persist a `CandidateMemory` to a branch |
| `TerminusMemoryRepository` | `write_claim()` | Persist a `Claim` to a branch |
| `TerminusMemoryRepository` | `write_inference_node()` | Persist an `InferenceNode` to a branch |
| `TerminusMemoryRepository` | `write_facet_relation()` | Persist a `FacetRelation` to a branch |
| `TerminusMemoryRepository` | `query_memories()` | Read memories from a branch |
| `TerminusMemoryRepository` | `query_inference_nodes()` | Read inference nodes from a branch |
| `TerminusMemoryRepository` | `query_facet_relations()` | Read facet relations from a branch |
| `session_branch_name()` | — | `"session/{id}"` naming helper |
| `inference_branch_name()` | — | `"inference/{id}"` naming helper |
| `BranchManager` | `create_session_branch()` / `create_inference_branch()` | High-level branch creation |

## Grounding

- `src/terminus/adapter.py` — Terminus persistence adapter with fallback store
- `src/terminus/branch_manager.py` — branch naming and lifecycle helpers
- `src/terminus/schema.py` — document encoding/decoding for Terminus
- `tests/unit/test_terminus.py` — unit coverage
- `notebooks/04_terminus_temporal_graph_memory.ipynb` — executable walkthrough

## Rules

1. Use `TerminusMemoryRepository` from `src/terminus/adapter.py` for all graph writes and reads.
2. Reuse `session_branch_name()` and `inference_branch_name()` from `src/terminus/branch_manager.py` for branch naming.
3. Keep trusted data on `session/*` branches and speculative data on `inference/*` branches; never mix them.
4. The adapter falls back to an in-process store when Terminus is unreachable — keep both paths aligned.
5. Validate with `tests/unit/test_terminus.py`.
