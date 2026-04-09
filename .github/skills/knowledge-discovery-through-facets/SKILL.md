---
name: knowledge-discovery-through-facets
description: Guide for the knowledge-discovery-through-facets capability. Use when asked to model or retrieve facet relations that connect related claims through paraphrase, abstraction, scope, or timeframe differences.
---

# Knowledge discovery through facets

Use the repository's facet relation models and retrieval surfaces so discovery features stay aligned with the graph-first design.

## Grounding
- `src/inference/models.py`
- `src/retrieval/composer.py`
- `tests/integration/test_inference_flow.py`
- `notebooks/05_knowledge_discovery_through_facets.ipynb`

## Use this skill when
- a task changes facet relation structure or metadata
- a task exposes discovery results through retrieval
- a task needs to preserve claim-to-claim relationships without collapsing them into standalone concept nodes

## Working rules
1. Reuse the facet relation types in `src/inference/models.py` for schema changes and validation rules.
2. Surface facet results through `src/retrieval/composer.py` so discovery stays consistent with other retrieval paths.
3. Preserve ranking and uncertainty metadata on relations without treating facets as trusted canonical replacements for claims.
4. Validate against `tests/integration/test_inference_flow.py` and the narrative example in `notebooks/05_knowledge_discovery_through_facets.ipynb`.
