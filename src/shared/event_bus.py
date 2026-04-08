from typing import Callable, Any
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[dict], Any]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event_type: str, payload: dict) -> None:
        for handler in self._handlers.get(event_type, []):
            handler(payload)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
