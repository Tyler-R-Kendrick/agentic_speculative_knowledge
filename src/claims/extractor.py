import re
from datetime import datetime
from typing import Optional, Callable
from src.claims.models import Claim

PRONOUN_RE = re.compile(r"\b(it|they|them|their|this|that|these|those|he|she|him|her)\b", re.IGNORECASE)
QUESTION_RE = re.compile(r"^\s*\w.*\?$")


class ClaimExtractor:
    def __init__(self, llm_fn: Optional[Callable[[str], str]] = None):
        self.llm_fn = llm_fn

    def extract(
        self,
        text: str,
        source_ref: Optional[str] = None,
        source_file: Optional[str] = None,
        source_commit: Optional[str] = None,
        observed_at: Optional[datetime] = None,
    ) -> list[Claim]:
        if not text or not text.strip():
            return []

        sentences = self._select_sentences(text)
        sentences = self._disambiguate(sentences)
        sentences = self._decompose(sentences)
        sentences = self._decontextualize(sentences)
        sentences = self._validate(sentences)

        claims = []
        for s in sentences:
            claim = Claim(
                claim_text=s.strip(),
                source_ref=source_ref,
                source_file=source_file,
                source_commit=source_commit,
                observed_at=observed_at,
                decontextualized=True,
                ambiguity_flag=bool(PRONOUN_RE.search(s)),
                claim_type=self._classify(s),
                confidence=self._score_confidence(s),
                entities=self._extract_entities(s),
            )
            claims.append(claim)
        return claims

    def _select_sentences(self, text: str) -> list[str]:
        raw = re.split(r"(?<=[.!?])\s+", text.strip())
        selected = []
        for s in raw:
            s = s.strip()
            if not s:
                continue
            # Must have at least 5 words
            words = s.split()
            if len(words) < 5:
                continue
            # Not a question
            if QUESTION_RE.match(s):
                continue
            selected.append(s)
        return selected

    def _disambiguate(self, sentences: list[str]) -> list[str]:
        # Simple rule-based: flag sentences with unresolved pronouns
        return sentences

    def _decompose(self, sentences: list[str]) -> list[str]:
        result = []
        split_pattern = re.compile(r"\s+(?:and|but|however|also)\s+(?=[A-Z])", re.IGNORECASE)
        for s in sentences:
            parts = split_pattern.split(s)
            if len(parts) > 1:
                for p in parts:
                    p = p.strip().rstrip(",")
                    if p:
                        result.append(p)
            else:
                result.append(s)
        return result

    def _decontextualize(self, sentences: list[str]) -> list[str]:
        result = []
        for s in sentences:
            # Ensure sentence ends with period
            s = s.strip()
            if s and not s.endswith((".", "!", "?")):
                s += "."
            result.append(s)
        return result

    def _validate(self, sentences: list[str]) -> list[str]:
        valid = []
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            words = s.split()
            if len(words) < 4:
                continue
            if QUESTION_RE.match(s):
                continue
            valid.append(s)
        return valid

    def _classify(self, text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["should", "must", "need to", "requires", "recommend"]):
            return "prescriptive"
        if any(w in lower for w in ["is", "are", "was", "were", "has", "have", "had"]):
            return "factual"
        return "factual"

    def _score_confidence(self, text: str) -> float:
        lower = text.lower()
        if any(w in lower for w in ["always", "never", "definitely", "certainly"]):
            return 0.95
        if any(w in lower for w in ["usually", "often", "typically", "generally"]):
            return 0.8
        if any(w in lower for w in ["sometimes", "may", "might", "could", "possibly"]):
            return 0.6
        return 0.85

    def _extract_entities(self, text: str) -> list[str]:
        # Simple: find capitalized words that aren't at the start
        words = text.split()
        entities = []
        for i, w in enumerate(words):
            clean = re.sub(r"[^\w]", "", w)
            if i > 0 and clean and clean[0].isupper() and len(clean) > 1:
                entities.append(clean)
        return list(dict.fromkeys(entities))  # dedupe preserving order
