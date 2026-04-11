# Skills usage guide

This guide explains how to use the six agent skills exposed by the repository. Each skill maps to a specific cognitive action and calls the Python APIs implemented in `src/`.

## Installing skills and agents

- The canonical skill definitions live in the repository root under `skills/`.
- If your local agent tooling looks for user-installed skills in `~/skills/`, copy or symlink each skill directory there.
- The repository also includes `.agents/skills/` symlinks that point back to `../../skills/<name>` for agent tooling that looks under `.agents/`.

| Skill | Cognitive action | Primary entry point |
|---|---|---|
| **memorize** | Store new knowledge | `MemoryManager` |
| **recall** | Retrieve past knowledge | `RetrievalComposer`, `JournalAppender` |
| **infer** | Generate speculative candidates | `MutationPipeline`, `InferenceGenerator` |
| **reflect** | Persist to the temporal graph | `TerminusMemoryRepository` |
| **discover** | Find connections and rank candidates | `ManifoldRankingService`, `InferenceGenerator` |
| **speculate** | Package critique-ready speculation with reasoning traces | `MemoryManager`, `MutationPipeline`, `RetrievalComposer`, `ManifoldRankingService` |

---

## memorize

Store observations, entities, tasks, and claims into the filesystem-backed active memory.

```python
import pathlib
from src.api.memory_manager import MemoryManager

mgr = MemoryManager(root_dir=pathlib.Path(".agent-memory"))

session = mgr.start_session(current_goal="investigate auth failures")

mgr.add_working_item(
    item_type="observation",
    content="The auth service returned 401 after cert rotation.",
)

mgr.add_entity(name="auth-service", entity_type="service")
mgr.add_task(title="Check certificate expiry dates", priority=1)

claims = mgr.extract_claims(
    text="The auth service failed after a certificate rotation.",
    source_ref="incident-42",
)

results = mgr.promote_memories()
mgr.end_session()
```

### Key classes

- `src.api.memory_manager.MemoryManager` — high-level orchestration
- `src.active_memory.session_manager.SessionManager` — session lifecycle
- `src.claims.extractor.ClaimExtractor` — claim extraction
- `src.governance.promotion.PromotionEngine` — promotion governance

---

## recall

Retrieve composed context from active memory, trusted Terminus graphs, and optional speculative branches.

```python
import pathlib
from datetime import date
from src.api.memory_manager import MemoryManager
from src.retrieval.composer import RetrievalComposer
from src.journal.appender import JournalAppender

root = pathlib.Path(".agent-memory")
mgr = MemoryManager(root_dir=root)

# Active-only context
context = mgr.retrieve_context(include_terminus=False)

# Full context with Terminus and speculative layers
full = mgr.retrieve_context(
    include_terminus=True,
    include_speculative=True,
    inference_branch="inference/sess-1",
)

# Journal history
appender = JournalAppender(root)
events = appender.read_day(date.today())
```

### Key classes

- `src.retrieval.composer.RetrievalComposer` — multi-layer composed retrieval
- `src.journal.appender.JournalAppender` — journal mutation history
- `src.retrieval.active_retriever.ActiveRetriever` — filesystem reader

---

## infer

Generate speculative inference candidates from claims and run the full mutation pipeline.

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
print(result.inference_candidates, result.ranked_inference_candidates)
```

### Using InferenceGenerator directly

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
```

### Key classes

- `src.persistence.pipeline.MutationPipeline` — end-to-end pipeline
- `src.inference.generator.InferenceGenerator` — candidate generation

---

## reflect

Persist memories, claims, and inference nodes into the TerminusDB temporal graph.

```python
from src.terminus.adapter import TerminusMemoryRepository
from src.terminus.branch_manager import session_branch_name, inference_branch_name
from src.claims.models import Claim
from src.normalization.mapper import ClaimToMemoryMapper

repo = TerminusMemoryRepository(url="http://localhost:6363")

# Create a session branch and write data
branch = repo.ensure_branch(session_branch_name("sess-1"))

claim = Claim(claim_text="Cert rotation caused auth failures.", claim_type="observation")
repo.write_claim(branch, claim)

mapper = ClaimToMemoryMapper()
memories = mapper.map_many([claim], session_id="sess-1")
for m in memories:
    m.source_branch = branch
    repo.write_memory(branch, m)

# Query trusted memories
trusted = repo.query_memories(branch="session/sess-1")

# Query speculative inference nodes
inf_br = repo.ensure_branch(inference_branch_name("sess-1"))
nodes = repo.query_inference_nodes(inf_br)
```

### Key classes

- `src.terminus.adapter.TerminusMemoryRepository` — Terminus adapter with fallback
- `src.terminus.branch_manager.BranchManager` — branch lifecycle helpers

---

## discover

Find connections between claims through facet relations and rank candidates using manifold geometry.

### Facet generation

```python
from src.inference.generator import InferenceGenerator
from src.claims.extractor import ClaimExtractor

extractor = ClaimExtractor()
claims = extractor.extract(
    text="The auth service failed. The API returned 401 errors.",
    source_ref="incident-42",
)

generator = InferenceGenerator()
facets = generator.generate_facet_candidates(
    claims,
    provenance_commit="journal-event-abc",
    source_branch="inference/sess-1",
)
```

### Manifold ranking

```python
from src.manifold_sidecar import ManifoldRankingService, ManifoldRankingRequest

svc = ManifoldRankingService()

ranking = svc.rank_inference_candidates(
    ManifoldRankingRequest(
        branch_name="inference/sess-1",
        ranking_mode="inference_candidate_ranking",
        seed_context={"session_id": "sess-1"},
        candidates=candidates,
    )
)
for c in ranking.candidates:
    print(c.ranking_score, c.relatedness_score, c.uncertainty)
```

### Discovery retrieval

```python
import pathlib
from src.retrieval.composer import RetrievalComposer
from src.terminus.adapter import TerminusMemoryRepository

root = pathlib.Path(".agent-memory")
repo = TerminusMemoryRepository(url="http://localhost:6363")
composer = RetrievalComposer(root, terminus_repo=repo)

result = composer.retrieve(
    include_terminus=True,
    include_speculative=True,
    inference_branch="inference/sess-1",
)
```

### Key classes

- `src.manifold_sidecar.service.ManifoldRankingService` — scoring service
- `src.inference.generator.InferenceGenerator` — facet generation
- `src.retrieval.composer.RetrievalComposer` — composed retrieval

---

## speculate

Orchestrate the other skills into a critique-ready speculative packet that exposes reasoning traces, assumptions, supports, ranking metadata, and justifications.

```python
import pathlib
from src.api.memory_manager import MemoryManager
from src.active_memory.models import WorkingItem
from src.persistence.pipeline import MutationPipeline
from src.retrieval.composer import RetrievalComposer
from src.terminus.adapter import TerminusMemoryRepository
from src.manifold_sidecar import ManifoldRankingService

root = pathlib.Path(".agent-memory")
mgr = MemoryManager(root_dir=root)
session = mgr.start_session(current_goal="speculate about auth failures")

observation = "The auth service returned 401 after a certificate rotation."
mgr.add_working_item(item_type="observation", content=observation)
claims = mgr.extract_claims(text=observation, source_ref="incident-42")

repo = TerminusMemoryRepository(url="http://localhost:6363")
ranker = ManifoldRankingService()
pipeline = MutationPipeline(
    root,
    enable_terminus=True,
    terminus_repo=repo,
    manifold_service=ranker,
    enable_inference=True,
)
result = pipeline.run(
    WorkingItem(item_type="observation", content=observation, session_id=session.session_id),
    session_id=session.session_id,
)

composer = RetrievalComposer(root, terminus_repo=repo)
context = composer.retrieve(
    include_terminus=True,
    include_speculative=True,
    inference_branch=result.inference_branch,
)

claim_index = {claim["claim_id"]: claim for claim in context["claims"]}
for node in context["speculative_inference"]:
    trace = {
        "candidate": node["text"],
        "supports": [
            claim_index.get(claim_id, {"claim_text": claim_id})["claim_text"]
            for claim_id in node.get("generated_from_nodes", [])
        ],
        "assumptions": node.get("assumptions", []),
        "ranking_score": node.get("ranking_score"),
        "uncertainty": node.get("uncertainty"),
        "justification": "Critique this candidate using its supporting claims and ranking signals.",
    }
    print(trace)

for relation in context["facet_relations"]:
    print(relation.get("facet_type"), relation.get("shared_core_claim"), relation.get("facet_strength"))

mgr.end_session()
```

### Key classes

- `src.api.memory_manager.MemoryManager` — seeds speculation with observations and claims
- `src.persistence.pipeline.MutationPipeline` — generates and persists speculative candidates
- `src.retrieval.composer.RetrievalComposer` — assembles critique packets across memory layers
- `src.manifold_sidecar.service.ManifoldRankingService` — adds ranking metadata for review priority
- `src.terminus.adapter.TerminusMemoryRepository` — stores and queries speculative graph data

---

## End-to-end workflow

The six skills form a cognitive loop. A typical end-to-end session looks like this:

```python
import pathlib
from src.api.memory_manager import MemoryManager
from src.persistence.pipeline import MutationPipeline
from src.terminus.adapter import TerminusMemoryRepository
from src.manifold_sidecar import ManifoldRankingService
from src.active_memory.models import WorkingItem

root = pathlib.Path(".agent-memory")
mgr = MemoryManager(root_dir=root)
repo = TerminusMemoryRepository(url="http://localhost:6363")
ranker = ManifoldRankingService()

# 1. MEMORIZE — start a session and record observations
session = mgr.start_session(current_goal="investigate auth failures")
mgr.add_working_item(item_type="observation", content="Auth returned 401 after cert rotation.")
claims = mgr.extract_claims(text="The auth service failed after a certificate rotation.")

# 2. INFER — run the mutation pipeline to generate speculative candidates
pipeline = MutationPipeline(
    root, enable_terminus=True, terminus_repo=repo,
    manifold_service=ranker, enable_inference=True,
)
item = WorkingItem(item_type="observation", content="Auth returned 401.", session_id=session.session_id)
result = pipeline.run(item, session_id=session.session_id)

# 3. RECALL — retrieve composed context
context = mgr.retrieve_context(
    include_terminus=True, include_speculative=True,
    inference_branch=result.inference_branch,
)

# 4. DISCOVER — inspect ranked discovery signals
from src.inference.generator import InferenceGenerator
generator = InferenceGenerator()
facets = generator.generate_facet_candidates(
    claims, provenance_commit="evt-1", source_branch=result.inference_branch,
)

# 5. SPECULATE — package reasoning traces for critique
claim_index = {claim["claim_id"]: claim for claim in context["claims"]}
for node in context["speculative_inference"]:
    print(
        {
            "candidate": node["text"],
            "supports": [
                claim_index.get(claim_id, {"claim_text": claim_id})["claim_text"]
                for claim_id in node.get("generated_from_nodes", [])
            ],
            "assumptions": node.get("assumptions", []),
            "ranking_score": node.get("ranking_score"),
            "uncertainty": node.get("uncertainty"),
        }
    )

# 6. REFLECT — persist trusted knowledge to the temporal graph
from src.terminus.branch_manager import session_branch_name
branch = repo.ensure_branch(session_branch_name(session.session_id))
for claim in claims:
    repo.write_claim(branch, claim)

# Close the session
mgr.end_session()
```

### Loop summary

| Step | Skill | What happens |
|---|---|---|
| 1 | **memorize** | Record observations, entities, tasks, and extract claims |
| 2 | **infer** | Generate speculative inference candidates and rank them |
| 3 | **recall** | Retrieve composed context across all memory layers |
| 4 | **discover** | Find connections through facets and geometric ranking |
| 5 | **speculate** | Present candidates with reasoning traces and critique-ready justifications |
| 6 | **reflect** | Persist trusted knowledge to the temporal graph |

See the individual skill files under `skills/` or the mirrored `.agents/skills/` symlinks for detailed API tables and working rules.
