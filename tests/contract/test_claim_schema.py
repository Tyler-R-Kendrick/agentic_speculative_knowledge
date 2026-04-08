import pytest
from src.claims.models import Claim
from src.claims.extractor import ClaimExtractor
from src.claims.validator import ClaimValidator


class TestClaimSchema:
    def test_claim_required_fields(self):
        claim = Claim(claim_text="Python is a programming language.")
        assert claim.claim_id
        assert claim.claim_text
        assert claim.claim_type
        assert claim.extracted_at
        assert isinstance(claim.confidence, float)
        assert isinstance(claim.entities, list)
        assert isinstance(claim.decontextualized, bool)
        assert isinstance(claim.ambiguity_flag, bool)

    def test_extracted_claims_have_source_ref(self):
        extractor = ClaimExtractor()
        claims = extractor.extract(
            "Python is a popular programming language created in the early 1990s.",
            source_ref="test-doc",
            source_file="test.txt",
        )
        for claim in claims:
            assert claim.source_ref == "test-doc"
            assert claim.source_file == "test.txt"

    def test_claim_confidence_bounds(self):
        validator = ClaimValidator()
        claim_low = Claim(claim_text="test", confidence=-0.1)
        claim_high = Claim(claim_text="test", confidence=1.1)
        claim_valid = Claim(claim_text="some valid content here", confidence=0.5)
        ok_low, _ = validator.validate(claim_low)
        ok_high, _ = validator.validate(claim_high)
        ok_valid, _ = validator.validate(claim_valid)
        assert not ok_low
        assert not ok_high
        assert ok_valid

    def test_claim_type_validation(self):
        validator = ClaimValidator()
        valid_types = ["factual", "prescriptive", "procedural", "relational", "temporal", "causal"]
        for ct in valid_types:
            claim = Claim(claim_text="Some text content here", claim_type=ct)
            ok, errors = validator.validate(claim)
            assert ok, f"Expected valid for type {ct}, got errors: {errors}"
