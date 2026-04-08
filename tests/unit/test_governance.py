import pytest
from src.normalization.mapper import CandidateMemory
from src.governance.rules import (
    MinimumConfidenceRule,
    MinimumMaturityRule,
    NoContradictionsRule,
    MinimumClaimsRule,
)
from src.governance.promotion import PromotionEngine


def make_memory(**kwargs):
    defaults = {
        "memory_type": "fact",
        "content": "Some fact about the world.",
        "confidence": 0.8,
        "maturity": 3,
        "claim_ids": ["claim-1"],
    }
    defaults.update(kwargs)
    return CandidateMemory(**defaults)


class TestPromotionRules:
    def test_minimum_confidence_rule_passes(self):
        rule = MinimumConfidenceRule(min_confidence=0.5)
        mem = make_memory(confidence=0.8)
        ok, msg = rule.check(mem)
        assert ok

    def test_minimum_confidence_rule_fails(self):
        rule = MinimumConfidenceRule(min_confidence=0.9)
        mem = make_memory(confidence=0.5)
        ok, msg = rule.check(mem)
        assert not ok
        assert "confidence" in msg

    def test_minimum_maturity_rule_passes(self):
        rule = MinimumMaturityRule(min_maturity=2)
        mem = make_memory(maturity=3)
        ok, msg = rule.check(mem)
        assert ok

    def test_minimum_maturity_rule_fails(self):
        rule = MinimumMaturityRule(min_maturity=5)
        mem = make_memory(maturity=1)
        ok, msg = rule.check(mem)
        assert not ok

    def test_contradiction_gating_no_contradictions(self):
        rule = NoContradictionsRule()
        mem = make_memory()
        ok, msg = rule.check(mem, context={})
        assert ok

    def test_contradiction_gating_with_contradictions(self):
        rule = NoContradictionsRule()
        mem = make_memory()
        ok, msg = rule.check(mem, context={"contradictions": ["memory-x"]})
        assert not ok

    def test_minimum_claims_rule(self):
        rule = MinimumClaimsRule(min_claims=2)
        mem_ok = make_memory(claim_ids=["c1", "c2"])
        mem_fail = make_memory(claim_ids=["c1"])
        ok, _ = rule.check(mem_ok)
        assert ok
        ok, _ = rule.check(mem_fail)
        assert not ok

    def test_promotion_eligibility(self):
        engine = PromotionEngine(rules=[MinimumConfidenceRule(0.5), MinimumMaturityRule(2)])
        mem = make_memory(confidence=0.9, maturity=3)
        result = engine.promote(mem)
        assert result.eligible
        assert result.promoted

    def test_promotion_ineligible(self):
        engine = PromotionEngine(rules=[MinimumConfidenceRule(0.9)])
        mem = make_memory(confidence=0.3)
        result = engine.promote(mem)
        assert not result.eligible
        assert not result.promoted
        assert len(result.reasons) > 0
