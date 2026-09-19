"""Thread-safe table of recently heard peer robots."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable

from .message import Message


@dataclass(frozen=True, slots=True)
class NeighborEntry:
    message: Message
    received_at: float


class NeighborTable:
    """Store the latest update for each peer and expire silent peers."""

    def __init__(
        self,
        ttl: float = 1.0,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.ttl = float(ttl)
        self._clock = clock
        self._entries: dict[str, NeighborEntry] = {}
        self._lock = threading.RLock()

    def update(self, message: Message) -> None:
        """Record a peer update using local receipt time for TTL accounting."""

        with self._lock:
            self._entries[message.robot_id] = NeighborEntry(message, self._clock())

    def prune(self) -> list[str]:
        """Remove expired peers and return their robot IDs."""

        now = self._clock()
        with self._lock:
            expired = [
                robot_id
                for robot_id, entry in self._entries.items()
                if now - entry.received_at >= self.ttl
            ]
            for robot_id in expired:
                del self._entries[robot_id]
        return expired

    def get(self, robot_id: str) -> Message | None:
        self.prune()
        with self._lock:
            entry = self._entries.get(robot_id)
            return entry.message if entry else None

    def snapshot(self) -> dict[str, Message]:
        """Return the active peers as an independent dictionary."""

        self.prune()
        with self._lock:
            return {
                robot_id: entry.message for robot_id, entry in self._entries.items()
            }

    def __contains__(self, robot_id: object) -> bool:
        return isinstance(robot_id, str) and self.get(robot_id) is not None

    def __len__(self) -> int:
        return len(self.snapshot())
