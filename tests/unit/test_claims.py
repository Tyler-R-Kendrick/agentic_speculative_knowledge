import pytest
from src.claims.models import Claim
from src.claims.extractor import ClaimExtractor
from src.claims.validator import ClaimValidator


class TestClaimExtractor:
    def setup_method(self):
        self.extractor = ClaimExtractor()

    def test_extraction_basic(self):
        text = "Python is a popular programming language. It was created by Guido van Rossum."
        claims = self.extractor.extract(text, source_ref="test")
        assert len(claims) >= 1
        assert all(isinstance(c, Claim) for c in claims)

    def test_empty_text(self):
        claims = self.extractor.extract("")
        assert claims == []

    def test_whitespace_only(self):
        claims = self.extractor.extract("   \n  ")
        assert claims == []

    def test_question_filtered_out(self):
        claims = self.extractor.extract("What is the capital of France?")
        assert len(claims) == 0

    def test_decontextualization(self):
        text = "The system stores memories persistently using a file-based approach."
        claims = self.extractor.extract(text)
        for c in claims:
            assert c.decontextualized is True

    def test_category_classification(self):
        text = "The agent should always validate its inputs before processing them."
        claims = self.extractor.extract(text)
        types = [c.claim_type for c in claims]
        assert any(t in ("prescriptive", "factual") for t in types)

    def test_ambiguity_flagging(self):
        text = "The system processes data and it stores the results automatically."
        claims = self.extractor.extract(text)
        pronoun_flagged = [c for c in claims if c.ambiguity_flag]
        # Any claim containing a pronoun should have ambiguity_flag=True
        for claim in claims:
            import re
            has_pronoun = bool(re.search(r"\b(it|they|them|their|this|that|these|those|he|she|him|her)\b", claim.claim_text, re.IGNORECASE))
            if has_pronoun:
                assert claim.ambiguity_flag is True

    def test_confidence_range(self):
        text = "The agent typically processes information and stores relevant data points."
        claims = self.extractor.extract(text)
        for c in claims:
            assert 0.0 <= c.confidence <= 1.0

    def test_short_text_no_claims(self):
        claims = self.extractor.extract("Yes.")
        assert len(claims) == 0


class TestClaimValidator:
    def setup_method(self):
        self.validator = ClaimValidator()

    def test_valid_claim(self):
        claim = Claim(claim_text="Python is a programming language.", confidence=0.9)
        ok, errors = self.validator.validate(claim)
        assert ok
        assert errors == []

    def test_invalid_confidence_high(self):
        claim = Claim(claim_text="Valid text", confidence=1.5)
        ok, errors = self.validator.validate(claim)
        assert not ok
        assert any("confidence" in e for e in errors)

    def test_invalid_confidence_low(self):
        claim = Claim(claim_text="Valid text", confidence=-0.1)
        ok, errors = self.validator.validate(claim)
        assert not ok

    def test_empty_claim_text(self):
        claim = Claim(claim_text="", confidence=0.9)
        ok, errors = self.validator.validate(claim)
        assert not ok
        assert any("claim_text" in e for e in errors)

    def test_invalid_claim_type(self):
        claim = Claim(claim_text="Some text", claim_type="invalid_type")
        ok, errors = self.validator.validate(claim)
        assert not ok
        assert any("claim_type" in e for e in errors)
