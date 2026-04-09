---
name: historical-recall
description: Guide for the historical-recall capability. Use when asked to inspect journal-backed history, branch-local recall, or retrieval flows that summarize past working-memory changes.
---

# Historical recall

Use the existing journal and retrieval composition layers to answer recall questions, not custom history files or one-off readers.

## Grounding
- `src/journal/appender.py`
- `src/retrieval/composer.py`
- `tests/integration/test_retrieval.py`
- `notebooks/03_historical_recall.ipynb`

## Use this skill when
- a task needs journal-backed reconstruction of recent work
- a task changes retrieval defaults or branch-aware recall behavior
- a task needs to keep speculative results hidden unless explicitly requested

## Working rules
1. Treat `src/journal/appender.py` as the source for mutation history and changed-file lineage.
2. Use `src/retrieval/composer.py` to compose active, trusted, and optional speculative context instead of hand-merging sources.
3. Preserve the default behavior that suppresses speculative inference unless callers explicitly opt in.
4. Validate retrieval behavior with `tests/integration/test_retrieval.py` and the walkthrough in `notebooks/03_historical_recall.ipynb`.
