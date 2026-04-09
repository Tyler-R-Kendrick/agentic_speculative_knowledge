---
name: speculative-inference-and-facets
description: Guide for the speculative-inference-and-facets capability. Use when asked to generate speculative inference candidates, persist them on inference branches, or work on facet generation and ranking flows.
---

# Speculative inference and facets

Build on the existing mutation pipeline, inference generator, and integration coverage instead of creating a parallel inference flow.

## Grounding
- `src/persistence/pipeline.py`
- `src/inference/generator.py`
- `tests/integration/test_inference_flow.py`
- `notebooks/02_speculative_inference_and_facets.ipynb`

## Use this skill when
- a task adds or changes inference generation behavior
- a task needs branch-local speculative persistence
- a task touches ranked inference candidates or facet relations

## Working rules
1. Route orchestration changes through `src/persistence/pipeline.py` so active memory, claim extraction, Terminus persistence, and speculative ranking stay synchronized.
2. Reuse `src/inference/generator.py` for inference and facet creation rather than inventing new speculative data shapes.
3. Preserve the repository trust boundary: speculative outputs stay isolated from trusted memory until another workflow explicitly promotes them.
4. Validate with `tests/integration/test_inference_flow.py` and compare workflow expectations with `notebooks/02_speculative_inference_and_facets.ipynb`.
