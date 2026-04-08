import pytest
from src.claims.extractor import ClaimExtractor
from src.claims.writer import ClaimWriter
from src.claims.validator import ClaimValidator


class TestClaimExtractionFlow:
    def test_extract_write_read_flow(self, tmp_path):
        extractor = ClaimExtractor()
        writer = ClaimWriter(tmp_path)
        text = "Memory systems are essential for AI agents. They enable persistent knowledge storage."
        claims = extractor.extract(text, source_ref="test-source")
        writer.write_many(claims)
        all_claims = writer.read_all()
        assert len(all_claims) == len(claims)

    def test_validated_claims_only(self, tmp_path):
        from src.claims.models import Claim
        validator = ClaimValidator()
        writer = ClaimWriter(tmp_path)
        valid_claim = Claim(claim_text="Python is used for data science tasks.", confidence=0.9)
        invalid_claim = Claim(claim_text="", confidence=0.9)
        ok1, _ = validator.validate(valid_claim)
        ok2, _ = validator.validate(invalid_claim)
        assert ok1
        assert not ok2
        if ok1:
            writer.write(valid_claim)
        stored = writer.read_all()
        assert len(stored) == 1
        assert stored[0].claim_text == valid_claim.claim_text
