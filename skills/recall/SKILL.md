---
name: recall
description: >-
  Use the recall skill to retrieve composed context from active memory,
  trusted Terminus graphs, and optional speculative branches. Also covers
  journal-backed history of past working-memory mutations.
---

# Recall

Retrieve past knowledge from the memory layers.

## When to use

- Fetching the current active context (session, working items, entities, tasks, claims)
- Querying journal history to see what changed and when
- Composing a unified context snapshot that merges active, trusted, and speculative layers
- Deciding whether to include speculative inference in the retrieved context

## Quick start

```python
import pathlib
from datetime import date
from src.api.memory_manager import MemoryManager
from src.retrieval.composer import RetrievalComposer
from src.journal.appender import JournalAppender

root = pathlib.Path(".agent-memory")

# High-level retrieval via MemoryManager
mgr = MemoryManager(root_dir=root)
context = mgr.retrieve_context(include_terminus=False)
# context keys: session, working_items, entities, tasks, claims,
#               terminus_memories, speculative_inference, facet_relations

# Include trusted Terminus memories and speculative inference
full = mgr.retrieve_context(
    include_terminus=True,
    include_speculative=True,
    inference_branch="inference/sess-1",
)

# Journal history for today
appender = JournalAppender(root)
events = appender.read_day(date.today())
for event in events:
    print(event.mutation_kind, event.changed_files)
```

### Direct composer usage

```python
from src.retrieval.composer import RetrievalComposer
from src.terminus.adapter import TerminusMemoryRepository

repo = TerminusMemoryRepository(url="http://localhost:6363")
composer = RetrievalComposer(root, terminus_repo=repo)

trusted = composer.retrieve(include_terminus=True)
exploratory = composer.retrieve(
    include_terminus=True,
    include_speculative=True,
    inference_branch="inference/sess-1",
)
```

## Key APIs

| Class | Method | Purpose |
|---|---|---|
| `MemoryManager` | `retrieve_context()` | High-level composed retrieval with opt-in layers |
| `RetrievalComposer` | `retrieve()` | Low-level retrieval combining active, Terminus, and speculative sources |
| `JournalAppender` | `read_day()` | Read mutation events for a specific date |
| `ActiveRetriever` | `get_session()` / `get_working_set()` / `get_entities()` / `get_tasks()` / `get_claims()` | Individual active-memory readers |

## Grounding

- `src/retrieval/composer.py` — composed retrieval from multiple layers
- `src/retrieval/active_retriever.py` — filesystem active-memory reader
- `src/retrieval/terminus_retriever.py` — Terminus trusted/speculative reader
- `src/journal/appender.py` — journal day-file reader
- `tests/integration/test_retrieval.py` — integration coverage
- `notebooks/03_historical_recall.ipynb` — executable walkthrough

## Rules

1. Use `RetrievalComposer` from `src/retrieval/composer.py` to merge context layers rather than hand-merging sources.
2. Treat `JournalAppender` in `src/journal/appender.py` as the source for mutation history.
3. Speculative inference is suppressed by default; callers must explicitly opt in via `include_speculative=True`.
4. Validate with `tests/integration/test_retrieval.py`.
