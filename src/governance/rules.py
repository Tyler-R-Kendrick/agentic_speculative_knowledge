from typing import Any
from src.normalization.mapper import CandidateMemory


class PromotionRule:
    name: str = "base"

    def check(self, memory: CandidateMemory, context: dict = None) -> tuple[bool, str]:
        raise NotImplementedError


class MinimumConfidenceRule(PromotionRule):
    name = "minimum_confidence"

    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence

    def check(self, memory: CandidateMemory, context: dict = None) -> tuple[bool, str]:
        if memory.confidence >= self.min_confidence:
            return True, ""
        return False, f"confidence {memory.confidence} < minimum {self.min_confidence}"


class MinimumMaturityRule(PromotionRule):
    name = "minimum_maturity"

    def __init__(self, min_maturity: int = 2):
        self.min_maturity = min_maturity

    def check(self, memory: CandidateMemory, context: dict = None) -> tuple[bool, str]:
        if memory.maturity >= self.min_maturity:
            return True, ""
        return False, f"maturity {memory.maturity} < minimum {self.min_maturity}"


class NoContradictionsRule(PromotionRule):
    name = "no_contradictions"

    def check(self, memory: CandidateMemory, context: dict = None) -> tuple[bool, str]:
        context = context or {}
        contradictions = context.get("contradictions", [])
        if not contradictions:
            return True, ""
        return False, f"memory has {len(contradictions)} contradictions"


class MinimumClaimsRule(PromotionRule):
    name = "minimum_claims"

    def __init__(self, min_claims: int = 1):
        self.min_claims = min_claims

    def check(self, memory: CandidateMemory, context: dict = None) -> tuple[bool, str]:
        if len(memory.claim_ids) >= self.min_claims:
            return True, ""
        return False, f"claim_ids count {len(memory.claim_ids)} < minimum {self.min_claims}"


DEFAULT_RULES = [
    MinimumConfidenceRule(),
    MinimumMaturityRule(),
    NoContradictionsRule(),
    MinimumClaimsRule(),
]
