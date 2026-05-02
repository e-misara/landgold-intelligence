from __future__ import annotations
from typing import Any


class MessageBus:
    """Single shared queue for all inter-agent messages.

    Class-level _queue means every instance shares the same log,
    so agents can be instantiated independently and still see each other's messages.
    """

    _queue: list[dict[str, Any]] = []

    # ── Write ──────────────────────────────────────────────────────────────

    def publish(self, message: dict[str, Any]) -> None:
        """Append a fully-formed message dict to the shared queue."""
        self._queue.append(message)

    # ── Read ───────────────────────────────────────────────────────────────

    def subscribe(self, agent_name: str) -> list[dict[str, Any]]:
        """Return all messages addressed to *agent_name* (or broadcast '*')."""
        return [
            m for m in self._queue
            if m.get("to") in (agent_name, "*")
        ]

    def get_all(self) -> list[dict[str, Any]]:
        """Return the full message log in insertion order."""
        return list(self._queue)

    # ── Utility ────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Flush the queue (useful between test runs)."""
        self._queue.clear()

    def __len__(self) -> int:
        return len(self._queue)
