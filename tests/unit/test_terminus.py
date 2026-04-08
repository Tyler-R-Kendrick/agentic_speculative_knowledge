import pytest
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
