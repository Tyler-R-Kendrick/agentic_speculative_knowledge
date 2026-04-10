---
name: memorize
description: >-
  Use the memorize skill to store observations, entities, tasks, and claims
  into the filesystem-backed active memory. Covers session lifecycle,
  working-set writes, entity/task card creation, claim extraction, and
  candidate promotion.
---

# Memorize

Store new knowledge into the agent's active memory layer.

## When to use

- Starting or ending a working session
- Recording observations, notes, or decisions
- Registering entities or tasks encountered during work
- Extracting structured claims from unstructured text
- Promoting candidate memories to trusted status

## Quick start

```python
import pathlib
from src.api.memory_manager import MemoryManager

mgr = MemoryManager(root_dir=pathlib.Path(".agent-memory"))

# 1. Start a session
session = mgr.start_session(current_goal="investigate auth failures")

# 2. Record a working item
item = mgr.add_working_item(
    item_type="observation",
    content="The auth service returned 401 after cert rotation.",
)

# 3. Register an entity
entity = mgr.add_entity(
    name="auth-service",
    entity_type="service",
    description="Handles authentication and token issuance.",
)

# 4. Register a task
task = mgr.add_task(title="Check certificate expiry dates", priority=1)

# 5. Extract claims from text
claims = mgr.extract_claims(
    text="The auth service failed after a certificate rotation.",
    source_ref="incident-report-42",
)

# 6. Promote eligible memories
results = mgr.promote_memories()

# 7. Close the session
mgr.end_session()
```

## Key APIs

| Class | Method | Purpose |
|---|---|---|
| `MemoryManager` | `start_session()` | Open a new working session with an optional goal |
| `MemoryManager` | `end_session()` | Close the active session |
| `MemoryManager` | `add_working_item()` | Append an observation, note, or decision to the working set |
| `MemoryManager` | `add_entity()` | Write an entity card to active memory |
| `MemoryManager` | `add_task()` | Write a task card to active memory |
| `MemoryManager` | `extract_claims()` | Extract and persist structured claims from text |
| `MemoryManager` | `promote_memories()` | Run governance rules and promote eligible candidates |
| `SessionManager` | `create_session()` / `close_session()` | Low-level session lifecycle |

## Grounding

- `src/api/memory_manager.py` — high-level orchestration API
- `src/active_memory/session_manager.py` — session create / close / load
- `src/active_memory/working_set.py` — JSONL working-set appender
- `src/active_memory/entity_card.py` — entity card writer
- `src/active_memory/task_card.py` — task card writer
- `src/claims/extractor.py` — claim extraction from text
- `src/governance/promotion.py` — promotion eligibility engine
- `tests/unit/test_active_memory.py` — unit coverage
- `notebooks/01_active_memory_basics.ipynb` — executable walkthrough

## Rules

1. Always use `MemoryManager` from `src/api/memory_manager.py` as the entry point; do not bypass it with low-level appenders unless extending the API itself.
2. Preserve the filesystem-first layout: `active/`, `journal/`, `claims/` directories under the memory root.
3. Keep claim extraction aligned with the existing `ClaimExtractor` pipeline rather than duplicating extraction logic.
4. Validate changes with `tests/unit/test_active_memory.py`.
