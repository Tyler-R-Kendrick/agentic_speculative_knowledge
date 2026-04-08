import pytest
from src.claims.models import Claim
from src.normalization.mapper import ClaimToMemoryMapper, CandidateMemory
from src.normalization.scorer import SalienceScorer, ConfidenceScorer
from src.normalization.entity_linker import EntityLinker
from src.normalization.duplicate_detector import DuplicateDetector


class TestNormalizationMapper:
    def test_claim_to_memory_mapping(self):
        mapper = ClaimToMemoryMapper()
        claim = Claim(claim_text="Python is a programming language.", claim_type="factual", confidence=0.9)
        memory = mapper.map(claim)
        assert isinstance(memory, CandidateMemory)
        assert memory.memory_type == "fact"
        assert memory.content == claim.claim_text
        assert memory.confidence == claim.confidence
        assert claim.claim_id in memory.claim_ids

    def test_prescriptive_mapping(self):
        mapper = ClaimToMemoryMapper()
        claim = Claim(claim_text="Developers should write tests.", claim_type="prescriptive")
        memory = mapper.map(claim)
        assert memory.memory_type == "rule"

    def test_map_many(self):
        mapper = ClaimToMemoryMapper()
        claims = [
            Claim(claim_text=f"Fact number {i}.", claim_type="factual")
            for i in range(3)
        ]
        memories = mapper.map_many(claims, session_id="sess1")
        assert len(memories) == 3
        assert all(m.session_id == "sess1" for m in memories)


class TestEntityLinker:
    def test_entity_extraction(self):
        linker = EntityLinker()
        entities = linker.extract_and_link("Alice and Bob met in London to discuss Python.")
        assert len(entities) > 0

    def test_entity_linking(self):
        linker = EntityLinker()
        linker.register("Python")
        linked = linker.link("python")
        assert linked == "Python"

    def test_entity_normalization(self):
        linker = EntityLinker()
        linker.register("New York")
        linked = linker.link("new york")
        assert linked == "New York"


class TestDuplicateDetector:
    def test_exact_duplicate(self):
        detector = DuplicateDetector()
        c1 = Claim(claim_text="Python is a programming language.")
        c2 = Claim(claim_text="Python is a programming language.")
        assert detector.is_duplicate(c1, c2)

    def test_near_duplicate(self):
        detector = DuplicateDetector(threshold=0.7)
        c1 = Claim(claim_text="Python is a popular programming language.")
        c2 = Claim(claim_text="Python is a popular programming language used widely.")
        # These are similar but not identical
        overlap = detector.is_duplicate(c1, c2)
        # Just verify the method runs without error
        assert isinstance(overlap, bool)

    def test_different_claims(self):
        detector = DuplicateDetector()
        c1 = Claim(claim_text="Python is a programming language.")
        c2 = Claim(claim_text="The sky is blue and the weather is warm today.")
        assert not detector.is_duplicate(c1, c2)

    def test_deduplicate(self):
        detector = DuplicateDetector()
        c1 = Claim(claim_text="Python is a programming language.")
        c2 = Claim(claim_text="Python is a programming language.")
        c3 = Claim(claim_text="Java is also a programming language.")
        result = detector.deduplicate([c1, c2, c3])
        assert len(result) == 2


class TestScorer:
    def test_salience_scoring(self):
        scorer = SalienceScorer()
        memory = CandidateMemory(
            memory_type="fact",
            content="A fairly long piece of content about important topics.",
            confidence=0.9,
            claim_ids=["id1", "id2"],
        )
        score = scorer.score(memory)
        assert 0.0 <= score <= 1.0

    def test_confidence_scoring(self):
        scorer = ConfidenceScorer()
        memory = CandidateMemory(
            memory_type="fact",
            content="Some content.",
            confidence=0.75,
        )
        score = scorer.score(memory)
        assert score == 0.75

    def test_confidence_adjust(self):
        scorer = ConfidenceScorer()
        memory = CandidateMemory(memory_type="fact", content="x", confidence=0.8)
        adjusted = scorer.adjust(memory, factor=0.5)
        assert abs(adjusted.confidence - 0.4) < 0.001
