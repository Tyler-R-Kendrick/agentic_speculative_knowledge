---
name: active-memory-basics
description: Guide for the active-memory-basics capability. Use when asked to start sessions, manage active memory, extract claims, retrieve context, or promote memory candidates in this repository.
---

# Active memory basics

Prefer the existing filesystem-backed APIs over ad hoc file handling or new abstractions.

## Grounding
- `README.md`
- `src/api/memory_manager.py`
- `tests/unit/test_active_memory.py`
- `notebooks/01_active_memory_basics.ipynb`

## Use this skill when
- a task needs a new active-memory workflow
- a change touches sessions, working items, entity cards, task cards, or claim extraction
- you need to retrieve composed active context before making other changes

## Working rules
1. Start from `src/api/memory_manager.py` and reuse `MemoryManager` methods before adding new entry points.
2. Preserve the filesystem-first layout used by the active-memory modules and their serializers.
3. Keep claim extraction and promotion flows aligned with the existing manager API instead of duplicating orchestration logic.
4. Validate behavior with `tests/unit/test_active_memory.py` and the executable example in `notebooks/01_active_memory_basics.ipynb`.
