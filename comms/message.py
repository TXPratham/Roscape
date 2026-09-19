"""Wire message schema shared by AMR peers."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
import json
from typing import Any, ClassVar, Mapping


@dataclass(slots=True)
class Message:
    """A robot state update sent over the multicast channel.

    Coordinates are represented as tuples in Python and become JSON arrays on
    the wire.  ``from_dict`` deliberately ignores extra keys so a newer peer
    can talk to an older one without breaking it.
    """

    robot_id: str
    timestamp: float
    position: tuple[int, int]
    velocity: tuple[int, int]
    path: list[tuple[int, int]]
    goal: tuple[int, int]
    battery: float
    task_id: str | None
    status: str
    blocked_cells: list[tuple[int, int]] = field(default_factory=list)

    VALID_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {"idle", "moving", "waiting", "blocked"}
    )

    def __post_init__(self) -> None:
        if not isinstance(self.robot_id, str) or not self.robot_id:
            raise ValueError("robot_id must be a non-empty string")
        self.timestamp = float(self.timestamp)
        self.position = self._coordinate(self.position, "position")
        self.velocity = self._coordinate(self.velocity, "velocity")
        self.path = [self._coordinate(cell, "path cell") for cell in self.path]
        self.goal = self._coordinate(self.goal, "goal")
        self.battery = float(self.battery)
        if not 0.0 <= self.battery <= 100.0:
            raise ValueError("battery must be between 0 and 100")
        if self.task_id is not None and not isinstance(self.task_id, str):
            raise ValueError("task_id must be a string or None")
        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"invalid robot status: {self.status!r}")
        self.blocked_cells = [
            self._coordinate(cell, "blocked cell") for cell in self.blocked_cells
        ]

    @staticmethod
    def _coordinate(value: Any, name: str) -> tuple[int, int]:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(f"{name} must contain exactly two coordinates")
        if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
            raise ValueError(f"{name} coordinates must be integers")
        return value[0], value[1]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation of the message."""

        return {
            "robot_id": self.robot_id,
            "timestamp": self.timestamp,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "path": [list(cell) for cell in self.path],
            "goal": list(self.goal),
            "battery": self.battery,
            "task_id": self.task_id,
            "status": self.status,
            "blocked_cells": [list(cell) for cell in self.blocked_cells],
        }

    def to_json(self) -> str:
        """Serialize the message using compact UTF-8-safe JSON."""

        return json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Message":
        """Build a message, ignoring fields unknown to this schema version."""

        if not isinstance(payload, Mapping):
            raise ValueError("message payload must be a JSON object")
        known = {item.name for item in fields(cls)}
        filtered = {key: value for key, value in payload.items() if key in known}
        try:
            return cls(**filtered)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"invalid message payload: {exc}") from exc

    @classmethod
    def from_json(cls, payload: str | bytes | bytearray) -> "Message":
        """Deserialize and validate a JSON message."""

        try:
            decoded = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
            raise ValueError("invalid message JSON") from exc
        return cls.from_dict(decoded)
