from src.claims.models import Claim

VALID_CLAIM_TYPES = {"factual", "prescriptive", "procedural", "relational", "temporal", "causal"}


class ClaimValidator:
    def validate(self, claim: Claim) -> tuple[bool, list[str]]:
        errors = []
        if not claim.claim_text or not claim.claim_text.strip():
            errors.append("claim_text must not be empty")
        if not (0.0 <= claim.confidence <= 1.0):
            errors.append(f"confidence must be in [0, 1], got {claim.confidence}")
        if claim.claim_type not in VALID_CLAIM_TYPES:
            errors.append(f"claim_type '{claim.claim_type}' is not valid; must be one of {VALID_CLAIM_TYPES}")
        return len(errors) == 0, errors

    def validate_many(self, claims: list[Claim]) -> list[tuple[Claim, bool, list[str]]]:
        return [(c, *self.validate(c)) for c in claims]
