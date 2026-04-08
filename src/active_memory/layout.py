import pathlib
from src.active_memory.atomic_write import atomic_write_text


DEFAULT_ROOT = pathlib.Path(".agent-memory")


def initialize_layout(root: pathlib.Path = DEFAULT_ROOT) -> pathlib.Path:
    root = pathlib.Path(root)

    dirs = [
        root / "active" / "entities",
        root / "active" / "tasks",
        root / "active" / "observations",
        root / "active" / "claims",
        root / "active" / "procedures",
        root / "active" / "summaries",
        root / "journal",
        root / "checkpoints",
        root / "config",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    session_yaml = root / "active" / "session.yaml"
    if not session_yaml.exists():
        atomic_write_text(session_yaml, "# session placeholder\n")

    working_set = root / "active" / "working-set.jsonl"
    if not working_set.exists():
        atomic_write_text(working_set, "")

    extracted_claims = root / "active" / "claims" / "extracted.jsonl"
    if not extracted_claims.exists():
        atomic_write_text(extracted_claims, "")

    memory_policy = root / "config" / "memory-policy.yaml"
    if not memory_policy.exists():
        atomic_write_text(memory_policy, "# memory policy\nmin_confidence: 0.5\nmin_maturity: 2\n")

    schema_version = root / "config" / "schema-version.yaml"
    if not schema_version.exists():
        atomic_write_text(schema_version, "schema_version: '0.1.0'\n")

    return root
