---
name: terminus-temporal-graph-memory
description: Guide for the terminus-temporal-graph-memory capability. Use when asked to work on branch-aware Terminus persistence, temporal graph memory, or persistent trusted memory behavior.
---

# Terminus temporal graph memory

Extend the existing Terminus adapter and branch conventions instead of adding a second persistence abstraction.

## Grounding
- `src/terminus/adapter.py`
- `src/terminus/branch_manager.py`
- `tests/unit/test_terminus.py`
- `notebooks/04_terminus_temporal_graph_memory.ipynb`

## Use this skill when
- a task changes branch creation or naming for session or inference graphs
- a task updates trusted memory writes or branch-local reads
- a task needs temporal-memory behavior that stays compatible with the fallback in-process store

## Working rules
1. Reuse `src/terminus/branch_manager.py` helpers for branch names and lifecycle rules.
2. Keep persistence changes inside `src/terminus/adapter.py` so the live Terminus path and fallback store remain behaviorally aligned.
3. Preserve the separation between trusted session branches and speculative inference branches.
4. Validate with `tests/unit/test_terminus.py` and the end-to-end example in `notebooks/04_terminus_temporal_graph_memory.ipynb`.
