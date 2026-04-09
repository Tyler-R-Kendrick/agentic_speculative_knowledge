---
name: manifold-mapping-for-discovery
description: Guide for the manifold-mapping-for-discovery capability. Use when asked to rank inference or facet candidates with manifold geometry, relatedness, distance, or uncertainty signals.
---

# Manifold mapping for discovery

Treat manifold ranking as advisory metadata layered on top of graph semantics, and reuse the current sidecar service instead of replacing core memory logic.

## Grounding
- `src/manifold_sidecar/service.py`
- `src/persistence/pipeline.py`
- `tests/unit/test_inference.py`
- `notebooks/06_manifold_mapping_for_discovery.ipynb`

## Use this skill when
- a task changes scoring, ranking metadata, or branch validation for manifold operations
- a task needs geometric ranking for inference or facet candidates
- a task must preserve the rule that ranking only runs in speculative branch contexts

## Working rules
1. Implement scoring changes inside `src/manifold_sidecar/service.py` so ranking metadata stays centralized and auditable.
2. Keep pipeline integration inside `src/persistence/pipeline.py` so manifold ranking remains an optional advisory step.
3. Preserve branch checks that require `inference/*` or `verification/*` contexts for ranking operations.
4. Validate ranking behavior with `tests/unit/test_inference.py` and the discovery scenario in `notebooks/06_manifold_mapping_for_discovery.ipynb`.
