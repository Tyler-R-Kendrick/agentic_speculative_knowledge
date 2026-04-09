# Adaptive Speculative Knowledge

This repo implements an agentic memory system for knowledge and discovery.

- **filesystem active memory** for mutable working cognition as a MEMORY.md and jsonl "journal".
- **TerminusDB temporal graph storage** for canonical persistent memory with time-travel and temporal reasoning.
- **knowledge facet generation** for speculative inference from the existing knowledge graph of memories.
- **a manifold ranking sidecar** for geometric scoring of inference candidates and knowledge facets to inform steering and discovery.

## Core architectural approach

### 1. Active memory stays in the filesystem and is used to augment current context with fast lookup and RAG.

This layer is intentionally:

- human-readable
- Git-diffable
- fast to update
- easy to recover from files and history

### 2. Persistent memory lives in temporal graphs

TerminusDB is the canonical store for trusted long-term knowledge and branch-local speculative knowledge. Importantly, it models diffs over time for historical queries. This is used for longer-term recall and advanced RAG scenarios.

The graph stores explicit structures such as:

- claims
- memories
- sessions
- tasks
- observations
- working-memory events and snapshots
- inference nodes
- facet relations
- provenance metadata
- temporal scope
- validation state
- branch lineage

### 3. Runtime inference is isolated in separate inference meta-graphs

Runtime-derived knowledge is not written directly into trusted memory.

Instead, this system uses branch-local speculative graph layers such as:

- `session/<session-id>` for candidate memory
- `inference/<session-id>` for speculative inference nodes and ranked facet relations
- `verification/<run-id>` for proof, checking, and validation artifacts
- `reflection/<task-id>` for consolidation outputs

This keeps trusted memory separate from runtime exploration and preserves clear trust boundaries between:

- **trusted**
- **candidate**
- **speculative**

### 4. Knowledge facets are modeled as relations

The system models facets as qualified relations between knowledge nodes rather than as standalone concept nodes.

That allows the graph to represent things like:

- paraphrases
- abstractions
- reframings
- decompositions
- scope differences
- timeframe differences

Each facet relation can carry ranking and uncertainty metadata without replacing explicit graph semantics.

### 5. Manifolds model rich geometric inference space

The manifold sidecar is used to score and rank candidates in a richer geometric space than the graph alone provides.

It improves:

- inference candidate ranking
- facet strength estimation
- bridge discovery between sparse subgraphs
- neighborhood expansion
- latent relatedness scoring

It does **not** replace the graph and it is **not** the source of truth.

Its outputs are advisory metadata such as:

- ranking score
- relatedness score
- distance score
- uncertainty
- geometry version
- ranking model id
- ranking run id

Those outputs are written back into TerminusDB so ranking decisions remain auditable.

## Why this is not a vector-database-first system

Vector infrastructure can be useful, but it is not the canonical knowledge layer here.

If a vector-serving layer such as **Qdrant** is used, it should be treated as:

- an auxiliary retrieval or embedding cache
- a serving layer for learned ranking representations
- a reusable store for neighborhood embeddings or candidate encodings

It should **not** become:

- the only store for claims or inferences
- the source of truth for trusted memory
- the only place provenance or validation state exists

In this architecture:

- **TerminusDB remains canonical**
- **vector infrastructure is optional and supporting**
- **manifold ranking remains advisory**

## Verification and formal reasoning layers

The architecture also leaves room for explicit verification layers.

Verification artifacts should live in graph-aware flows and branches such as `verification/<run-id>`, where the system can track:

- verifier identity
- verification run id
- proof attempts
- contradiction checks
- validation outcomes
- promotion decisions

Where useful, graph content can be mapped into more formal verification systems such as:

- rule engines
- symbolic validators
- logic programming systems
- SMT or theorem-proving workflows

Those formal solvers should validate or refute candidates; they should not replace the graph as the durable memory record.

## Current implementation direction

The repository currently implements the core shape of this architecture:

- filesystem-backed active memory
- Terminus-oriented schema and branch management
- `InferenceNode` as the single speculative proposition type
- facet relations with ranking metadata
- a formalized manifold ranking service API
- branch-aware speculative persistence
- retrieval that suppresses speculative results by default

## Design principles

- **Graph-first:** graph semantics, provenance, temporality, and validation state are authoritative.
- **Filesystem-first for working state:** active memory remains easy to inspect and edit.
- **Inference is separate from truth:** speculative runtime knowledge is isolated from validated memory.
- **Ranking is advisory:** manifold geometry influences prioritization, not truth status.
- **Auditability matters:** every inference and ranking signal should be traceable to its source and run metadata.

## Development container

The repository includes a `.devcontainer/` setup for VS Code Dev Containers and GitHub Codespaces.

It provisions:

- a Python 3.12 workspace container
- editable installation of the package with `.[dev]`
- a colocated TerminusDB service on `http://terminusdb:6363`
- forwarded access to TerminusDB on local port `6363`

Default development credentials inside the container are:

- user: `admin`
- password: `root`
- team: `admin`
- database: `agent_memory`

Open the repository in a dev container to have the Python environment and TerminusDB service configured automatically.

## Repository focus

This project is aimed at building an agent memory stack where:

- active memory supports immediate cognition
- persistent memory is explicit and temporal
- inference meta-graphs support runtime knowledge discovery
- manifold geometry improves discovery quality without collapsing trust boundaries

## Notebook demos

The repository includes a focused set of simple Python notebooks under `notebooks/` that showcase the repo’s main capabilities and value proposition:

- `01_active_memory_basics.ipynb` — starts a session, writes working memory, stores entity/task cards, extracts claims, and retrieves the active context.
- `02_speculative_inference_and_facets.ipynb` — runs the mutation pipeline, generates speculative inference candidates, ranks them, and inspects facet relations.
- `03_historical_recall.ipynb` — shows branch-local recall across sessions and the journal-backed history of memory mutations.
- `04_terminus_temporal_graph_memory.ipynb` — demonstrates persistent branch-local Terminus memory, session/inference separation, and temporal recall across graph branches.
- `05_knowledge_discovery_through_facets.ipynb` — demonstrates knowledge discovery through ranked facet relations that connect related claims through scope and timeframe differences.
- `06_manifold_mapping_for_discovery.ipynb` — demonstrates manifold-guided discovery, including inference/facet ranking metadata, relatedness, distance, and steering signals.

Each notebook is designed to run locally with the repository code only. The Terminus examples intentionally point at an unused local URL so `TerminusMemoryRepository` falls back to its in-process store, which means the notebooks do not require a live TerminusDB server.

## Agent skills

The repository now exposes its main workflows as project agent skills under `.github/skills/`.

- `/active-memory-basics`
- `/speculative-inference-and-facets`
- `/historical-recall`
- `/terminus-temporal-graph-memory`
- `/knowledge-discovery-through-facets`
- `/manifold-mapping-for-discovery`

Each skill is grounded in the existing implementation and points back to the most relevant source files, tests, and demo notebook for that workflow so agents can extend the repo without inventing parallel abstractions.
