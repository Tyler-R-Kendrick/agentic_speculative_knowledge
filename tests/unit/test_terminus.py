import pytest
from collections import defaultdict
from src.terminus.adapter import TerminusMemoryRepository
from src.terminus.branch_manager import (
    session_branch_name,
    inference_branch_name,
    verification_branch_name,
    reflection_branch_name,
)
from src.terminus.schema import (
    encode_document,
    decode_document,
    CLAIM_SCHEMA,
    FACET_RELATION_SCHEMA,
    INFERENCE_NODE_SCHEMA,
    MEMORY_SCHEMA,
)
from src.normalization.mapper import CandidateMemory
from src.inference.models import FacetRelation, InferenceNode


class FakeTerminusClient:
    def __init__(self, fail_inserts: bool = False):
        self.fail_inserts = fail_inserts
        self.current_branch = "main"
        self.branches = defaultdict(list)

    def create_branch(self, branch: str):
        self.branches[branch]

    def checkout(self, branch: str):
        self.current_branch = branch

    def insert_document(self, doc: dict, graph_type: str = "instance", commit_msg: str = ""):
        if self.fail_inserts:
            raise RuntimeError("insert failed")
        self.branches[self.current_branch].append(dict(doc))

    def get_all_documents(self, graph_type: str = "instance", as_list: bool = True):
        return list(self.branches[self.current_branch])

    def get_document(self, document_id: str):
        document_type, _, document_key = document_id.partition("/")
        for doc in self.branches[self.current_branch]:
            if doc.get("@type") == document_type and doc.get(f"{document_type.lower()}_id") == document_key:
                return doc
        raise KeyError(document_id)


class TestTerminusAdapter:
    UNAVAILABLE_URL = "http://localhost:9999"

    def test_graceful_failure_on_no_connection(self):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL)
        assert not repo.is_available()

    def test_insert_fails_gracefully(self):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL)
        memory = CandidateMemory(memory_type="fact", content="test")
        result = repo.insert_memory(memory)
        assert result is False

    def test_get_fails_gracefully(self):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL)
        result = repo.get_memory("some-id")
        assert result is None

    def test_query_fails_gracefully(self):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL)
        result = repo.query_memories()
        assert result == []

    def test_schema_mapping(self):
        assert MEMORY_SCHEMA["@id"] == "Memory"
        assert CLAIM_SCHEMA["@id"] == "Claim"
        assert INFERENCE_NODE_SCHEMA["@id"] == "InferenceNode"
        assert FACET_RELATION_SCHEMA["@id"] == "FacetRelation"
        assert MEMORY_SCHEMA["claim_ids"]["@class"]["@type"] == "List"

    def test_document_encoding(self):
        data = {"key": "value", "number": 42, "none_val": None}
        encoded = encode_document(data)
        assert "none_val" not in encoded
        assert encoded["key"] == "value"

    def test_document_decoding(self):
        doc = {"@type": "Memory", "@id": "Memory/123", "content": "hello"}
        decoded = decode_document(doc)
        assert "content" in decoded
        assert "@type" not in decoded

    def test_branch_local_inference_storage(self):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL)
        branch = "inference/sess-123"
        node = InferenceNode(
            text="The deployment issue may be caused by stale credentials.",
            inference_mode="abductive",
            generated_from_nodes=["claim-1"],
            generated_from_edges=["supports:claim-1"],
            source_branch=branch,
            source_commit="abc123",
            ranking_model_id="sidecar-v1",
            ranking_run_id="run-1",
            ranking_score=0.81,
            prompt_template_id="tmpl-1",
            policy_version="policy-v1",
        )

        assert repo.write_inference_node(branch, node)
        stored = repo.query_inference_nodes(branch)
        assert len(stored) == 1
        assert stored[0]["text"] == node.text
        assert repo.query_memories(branch="main") == []

    def test_branch_local_facet_storage(self):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL)
        branch = "inference/sess-123"
        relation = FacetRelation(
            source_node_id="claim-1",
            target_node_id="claim-2",
            facet_type="paraphrase_of",
            provenance_commit="abc123",
            ranking_model_id="sidecar-v1",
            ranking_run_id="run-1",
            relatedness_score=0.88,
            distance_score=0.12,
            facet_strength=0.91,
        )

        assert repo.write_facet_relation(branch, relation)
        stored = repo.query_facet_relations(branch)
        assert len(stored) == 1
        assert stored[0]["facet_type"] == "paraphrase_of"

    def test_local_fallback_data_does_not_mark_remote_available(self):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL)
        branch = "inference/sess-123"
        node = InferenceNode(
            text="The deployment issue may be caused by stale credentials.",
            inference_mode="abductive",
            generated_from_nodes=["claim-1"],
            generated_from_edges=["supports:claim-1"],
            source_branch=branch,
            source_commit="abc123",
            ranking_model_id="sidecar-v1",
            ranking_run_id="run-1",
            ranking_score=0.81,
            prompt_template_id="tmpl-1",
            policy_version="policy-v1",
        )

        assert repo.write_inference_node(branch, node) is False
        assert repo.has_local_data() is True
        assert repo.is_available() is False

    def test_remote_writes_and_queries_are_branch_scoped(self, monkeypatch):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL, user="user", password="pass")
        client = FakeTerminusClient()
        monkeypatch.setattr(repo, "_get_client", lambda: client)
        repo._connected = True

        session_memory = CandidateMemory(memory_type="fact", content="session memory")
        inference_memory = CandidateMemory(memory_type="fact", content="inference memory")

        assert repo.write_memory("session/sess-1", session_memory) is True
        assert repo.write_memory("inference/sess-1", inference_memory) is True

        session_results = repo.query_memories(branch="session/sess-1")
        inference_results = repo.query_memories(branch="inference/sess-1")

        assert [memory["content"] for memory in session_results] == ["session memory"]
        assert [memory["content"] for memory in inference_results] == ["inference memory"]

    def test_write_memory_returns_false_when_remote_insert_fails(self, monkeypatch):
        repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL, user="user", password="pass")
        client = FakeTerminusClient(fail_inserts=True)
        monkeypatch.setattr(repo, "_get_client", lambda: client)
        repo._connected = True

        memory = CandidateMemory(memory_type="fact", content="fallback only")

        assert repo.write_memory("session/sess-1", memory) is False
        assert repo.query_memories(branch="session/sess-1")[0]["content"] == "fallback only"

    def test_remote_queries_support_claims_inference_and_facets(self, monkeypatch):
        writer_repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL, user="user", password="pass")
        reader_repo = TerminusMemoryRepository(url=self.UNAVAILABLE_URL, user="user", password="pass")
        client = FakeTerminusClient()
        monkeypatch.setattr(writer_repo, "_get_client", lambda: client)
        monkeypatch.setattr(reader_repo, "_get_client", lambda: client)
        writer_repo._connected = True
        reader_repo._connected = True

        branch = "inference/sess-99"
        claim_branch = "session/sess-99"

        claim = Claim(claim_text="The service recovered after restart.")
        node = InferenceNode(
            text="The restart may have flushed a stale cache entry.",
            inference_mode="abductive",
            generated_from_nodes=[claim.claim_id],
            generated_from_edges=["supports:claim-1"],
            source_branch=branch,
            source_commit="abc123",
            ranking_model_id="sidecar-v1",
            ranking_run_id="run-1",
            ranking_score=0.75,
            prompt_template_id="tmpl-1",
            policy_version="policy-v1",
        )
        relation = FacetRelation(
            source_node_id="claim-1",
            target_node_id="claim-2",
            facet_type="paraphrase_of",
            provenance_commit="abc123",
            ranking_model_id="sidecar-v1",
            ranking_run_id="run-1",
            relatedness_score=0.88,
            distance_score=0.12,
            facet_strength=0.91,
        )

        assert writer_repo.write_claim(claim_branch, claim) is True
        assert writer_repo.write_inference_node(branch, node) is True
        assert writer_repo.write_facet_relation(branch, relation) is True

        assert reader_repo.query_claims(claim_branch)[0]["claim_text"] == claim.claim_text
        assert reader_repo.query_inference_nodes(branch)[0]["text"] == node.text
        assert reader_repo.query_facet_relations(branch)[0]["facet_type"] == relation.facet_type


class TestBranchManager:
    def test_branch_naming_rules_session(self):
        name = session_branch_name("abc-123")
        assert name.startswith("session/")
        assert "abc" in name

    def test_branch_naming_rules_inference(self):
        name = inference_branch_name("my session")
        assert name == "inference/my-session"

    def test_branch_naming_rules_verification(self):
        name = verification_branch_name("run@1")
        assert name == "verification/run-1"

    def test_branch_naming_rules_reflection(self):
        name = reflection_branch_name("task/42")
        assert name == "reflection/task/42"

    def test_branch_name_sanitization(self):
        name = session_branch_name("abc@def#xyz")
        assert "@" not in name
        assert "#" not in name
