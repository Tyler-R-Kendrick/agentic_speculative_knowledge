import pytest
from datetime import date, datetime
from src.journal.models import JournalEvent
from src.journal.appender import JournalAppender
from src.journal.outbox import RetryableOutbox


class TestJournalEvent:
    def test_event_schema_validation(self):
        event = JournalEvent(session_id="sess1", mutation_kind="add")
        assert event.event_id
        assert event.actor == "agent"
        assert event.persist_status == "pending"

    def test_append_ordering(self, tmp_path):
        appender = JournalAppender(tmp_path)
        today = date.today()
        event1 = JournalEvent(session_id="sess1", mutation_kind="add")
        event2 = JournalEvent(session_id="sess1", mutation_kind="update")
        appender.append(event1)
        appender.append(event2)
        events = appender.read_day(today)
        assert len(events) == 2
        assert events[0].event_id == event1.event_id
        assert events[1].event_id == event2.event_id

    def test_replay_parsing(self, tmp_path):
        appender = JournalAppender(tmp_path)
        today = date.today()
        for i in range(5):
            appender.append(JournalEvent(session_id="s", mutation_kind=f"kind_{i}"))
        events = appender.read_day(today)
        assert len(events) == 5
        for i, e in enumerate(events):
            assert e.mutation_kind == f"kind_{i}"


class TestRetryableOutbox:
    def test_enqueue_and_deliver(self, tmp_path):
        outbox = RetryableOutbox(tmp_path)
        event = JournalEvent(session_id="s1", mutation_kind="add")
        outbox.enqueue(event)
        results = outbox.deliver_all(lambda e: True)
        assert results["delivered"] == 1
        assert results["failed"] == 0

    def test_idempotency(self, tmp_path):
        outbox = RetryableOutbox(tmp_path)
        event = JournalEvent(session_id="s1", mutation_kind="add")
        outbox.enqueue(event)
        outbox.deliver_all(lambda e: True)
        # Enqueue same event again should be skipped via delivered tracking
        outbox.enqueue(event)
        results = outbox.deliver_all(lambda e: True)
        assert results["skipped"] == 1

    def test_retry_on_failure(self, tmp_path):
        outbox = RetryableOutbox(tmp_path, max_retries=3)
        event = JournalEvent(session_id="s1", mutation_kind="add")
        outbox.enqueue(event)
        results = outbox.deliver_all(lambda e: False)
        assert results["failed"] == 1
