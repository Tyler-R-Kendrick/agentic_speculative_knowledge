import re
from src.claims.models import Claim


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _word_overlap(a: str, b: str) -> float:
    words_a = set(_normalize_text(a).split())
    words_b = set(_normalize_text(b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


class DuplicateDetector:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def is_duplicate(self, claim_a: Claim, claim_b: Claim) -> bool:
        if claim_a.claim_id == claim_b.claim_id:
            return True
        norm_a = _normalize_text(claim_a.claim_text)
        norm_b = _normalize_text(claim_b.claim_text)
        if norm_a == norm_b:
            return True
        return _word_overlap(claim_a.claim_text, claim_b.claim_text) >= self.threshold

    def find_duplicates(self, claims: list[Claim]) -> list[tuple[Claim, Claim]]:
        duplicates = []
        for i, c1 in enumerate(claims):
            for c2 in claims[i+1:]:
                if self.is_duplicate(c1, c2):
                    duplicates.append((c1, c2))
        return duplicates

    def deduplicate(self, claims: list[Claim]) -> list[Claim]:
        result = []
        seen_ids: set[str] = set()
        for claim in claims:
            is_dup = False
            for existing in result:
                if self.is_duplicate(claim, existing):
                    is_dup = True
                    break
            if not is_dup:
                result.append(claim)
                seen_ids.add(claim.claim_id)
        return result
