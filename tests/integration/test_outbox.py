import pytest
from src.journal.models import JournalEvent
from src.journal.outbox import RetryableOutbox


class TestOutboxFlow:
    def test_full_delivery_flow(self, tmp_path):
        outbox = RetryableOutbox(tmp_path)
        events = [JournalEvent(session_id="s1", mutation_kind=f"kind_{i}") for i in range(3)]
        for e in events:
            outbox.enqueue(e)
        delivered = []
        def handler(event):
            delivered.append(event)
            return True
        results = outbox.deliver_all(handler)
        assert results["delivered"] == 3
        assert len(delivered) == 3

    def test_partial_failure(self, tmp_path):
        outbox = RetryableOutbox(tmp_path, max_retries=2)
        events = [JournalEvent(session_id="s1", mutation_kind="add") for _ in range(4)]
        for e in events:
            outbox.enqueue(e)
        call_count = [0]
        def handler(event):
            call_count[0] += 1
            return call_count[0] % 2 == 0  # alternating success/fail
        results = outbox.deliver_all(handler)
        assert results["delivered"] + results["failed"] == 4
