from src.normalization.mapper import CandidateMemory


class SalienceScorer:
    def score(self, memory: CandidateMemory) -> float:
        score = memory.confidence * 0.5
        entity_boost = min(len(memory.claim_ids) * 0.05, 0.2)
        text_len = len(memory.content)
        length_boost = min(text_len / 500.0, 0.3)
        return min(score + entity_boost + length_boost, 1.0)


class ConfidenceScorer:
    def score(self, memory: CandidateMemory) -> float:
        return memory.confidence

    def adjust(self, memory: CandidateMemory, factor: float) -> CandidateMemory:
        new_conf = max(0.0, min(1.0, memory.confidence * factor))
        return memory.model_copy(update={"confidence": new_conf})
