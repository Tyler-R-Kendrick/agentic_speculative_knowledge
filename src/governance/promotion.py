from dataclasses import dataclass, field
from typing import Optional
from src.normalization.mapper import CandidateMemory
from src.governance.rules import PromotionRule, DEFAULT_RULES


@dataclass
class PromotionResult:
    eligible: bool
    memory_id: str
    reasons: list[str] = field(default_factory=list)
    promoted: bool = False


class PromotionEngine:
    def __init__(self, rules: Optional[list[PromotionRule]] = None):
        self.rules = rules if rules is not None else DEFAULT_RULES

    def check_eligibility(self, memory: CandidateMemory, context: dict = None) -> tuple[bool, list[str]]:
        failures = []
        for rule in self.rules:
            ok, msg = rule.check(memory, context=context)
            if not ok:
                failures.append(f"{rule.name}: {msg}")
        return len(failures) == 0, failures

    def promote(self, memory: CandidateMemory, context: dict = None) -> PromotionResult:
        eligible, failures = self.check_eligibility(memory, context=context)
        result = PromotionResult(
            eligible=eligible,
            memory_id=memory.memory_id,
            reasons=failures,
        )
        if eligible:
            result.promoted = True
        return result
