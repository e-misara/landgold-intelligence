from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable
from core.message_bus import MessageBus
from core.logger import get_logger

VALID_PRIORITIES = ("low", "normal", "high", "critical")
VALID_TYPES      = ("task", "report", "alert", "info")


class BaseAgent(ABC):

    def __init__(
        self,
        name: str,
        role: str,
        ceo_callback: Callable[[dict], None] | None = None,
    ) -> None:
        self.name         = name
        self.role         = role
        self.ceo_callback = ceo_callback
        self._bus         = MessageBus()
        self._outbox:  list[dict[str, Any]] = []
        self._inbox:   list[dict[str, Any]] = []
        self._logger = get_logger(name)

    # ── Core API ───────────────────────────────────────────────────────────

    def send_message(
        self,
        to: str,
        content: dict[str, Any],
        priority: str = "normal",
        msg_type: str = "info",
    ) -> dict[str, Any]:
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {VALID_PRIORITIES}")
        if msg_type not in VALID_TYPES:
            raise ValueError(f"type must be one of {VALID_TYPES}")

        message: dict[str, Any] = {
            "from":      self.name,
            "to":        to,
            "priority":  priority,
            "type":      msg_type,
            "content":   content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._outbox.append(message)
        self._bus.publish(message)
        self.log(f"→ {to} [{priority}] {msg_type}: {list(content.keys())}")
        return message

    def receive_message(self, message: dict[str, Any]) -> None:
        self._inbox.append(message)
        sender   = message.get("from", "?")
        priority = message.get("priority", "normal")
        msg_type = message.get("type", "info")
        self.log(f"← {sender} [{priority}] {msg_type}")

        if priority == "critical":
            self.log(f"CRITICAL message from {sender} — handling immediately")
            self._handle_critical(message)

    def report_to_ceo(self, summary: dict[str, Any]) -> None:
        report: dict[str, Any] = {
            "agent":     self.name,
            "role":      self.role,
            "summary":   summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self.ceo_callback:
            self.ceo_callback(report)
        else:
            self.send_message(
                to="ceo",
                content=report,
                priority="normal",
                msg_type="report",
            )

    def log(self, text: str) -> None:
        ts  = datetime.now(timezone.utc).strftime("%H:%M:%S")
        msg = f"[{ts}] [{self.name.upper()}] {text}"
        self._logger.info(msg)

    # ── Abstract ───────────────────────────────────────────────────────────

    @abstractmethod
    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute an assigned task and return a result dict."""

    # ── Helpers ────────────────────────────────────────────────────────────

    def fetch_inbox(self) -> list[dict[str, Any]]:
        """Pull new messages from the bus addressed to this agent."""
        new = [m for m in self._bus.subscribe(self.name) if m not in self._inbox]
        for m in new:
            self.receive_message(m)
        return new

    def _handle_critical(self, message: dict[str, Any]) -> None:
        """Override in subclasses to add critical-priority handling."""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} role={self.role!r}>"
