"""Task model used by the simulator and task-allocation layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Task:
    id: str
    pickup: tuple[int, int]
    dropoff: tuple[int, int]
    priority: int = 1
    assigned_to: str | None = None
    item_name: str = "AMZ-BOX-A12"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "pickup": list(self.pickup),
            "dropoff": list(self.dropoff),
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "item_name": self.item_name,
            "stage": "assigned" if self.assigned_to else "queued",
        }
