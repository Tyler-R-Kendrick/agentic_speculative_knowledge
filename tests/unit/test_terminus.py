import pytest
from src.terminus.adapter import TerminusMemoryRepository
from src.terminus.branch_manager import session_branch_name, feature_branch_name
from src.terminus.schema import encode_document, decode_document
from src.normalization.mapper import CandidateMemory


class TestTerminusAdapter:
    def test_graceful_failure_on_no_connection(self):
        repo = TerminusMemoryRepository(url="http://localhost:9999")
        assert not repo.is_available()

    def test_insert_fails_gracefully(self):
        repo = TerminusMemoryRepository(url="http://localhost:9999")
        memory = CandidateMemory(memory_type="fact", content="test")
        result = repo.insert_memory(memory)
        assert result is False

    def test_get_fails_gracefully(self):
        repo = TerminusMemoryRepository(url="http://localhost:9999")
        result = repo.get_memory("some-id")
        assert result is None

    def test_query_fails_gracefully(self):
        repo = TerminusMemoryRepository(url="http://localhost:9999")
        result = repo.query_memories()
        assert result == []

    def test_schema_mapping(self):
        from src.terminus.schema import MEMORY_SCHEMA, CLAIM_SCHEMA
        assert MEMORY_SCHEMA["@id"] == "Memory"
        assert CLAIM_SCHEMA["@id"] == "Claim"

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


class TestBranchManager:
    def test_branch_naming_rules_session(self):
        name = session_branch_name("abc-123")
        assert name.startswith("session-")
        assert "abc" in name

    def test_branch_naming_rules_feature(self):
        name = feature_branch_name("my-feature")
        assert name.startswith("feature/")
        assert "my-feature" in name

    def test_branch_name_sanitization(self):
        name = session_branch_name("abc@def#xyz")
        assert "@" not in name
        assert "#" not in name
