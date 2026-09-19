"""A lightweight robot model independent of any path planner."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .environment import Environment


class Robot:
    """An AMR which follows a path or explores a random free neighbor."""

    def __init__(
        self,
        robot_id: str,
        pos: tuple[int, int],
        *,
        battery: float = 100.0,
        model: str | None = None,
        cargo_name: str | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.id = robot_id
        self.pos = tuple(pos)
        self.battery = float(battery)
        self.task_id: str | None = None
        self.path: list[tuple[int, int]] = []
        self.status = "idle"
        self.velocity = (0, 0)
        self._rng = rng or random.Random()
        if model:
            self.model = model
        else:
            self.model = "ATR-600" if robot_id.endswith(("2", "4", "6", "8")) else "ATR-400"
        self.payload_kg = round(self._rng.uniform(3.5, 18.0), 1)
        self.heading_degrees = 0
        self.cargo_name = cargo_name or ("TOTE-B5" if self.model == "ATR-600" else "AMZ-BOX-A12")
        self.arm_state = "idle"

    def set_path(self, path: Iterable[tuple[int, int]]) -> None:
        self.path = [tuple(cell) for cell in path]
        if self.path and self.path[0] == self.pos:
            self.path.pop(0)
        self.status = "moving" if self.path else "idle"

    def step(self, env: "Environment") -> None:
        old_pos = self.pos
        destination: tuple[int, int] | None = None

        if self.battery > 0 and self.path:
            candidate = self.path[0]
            if env.is_free(candidate, ignore_robot=self.id):
                destination = candidate
                self.path.pop(0)
            else:
                self.status = "waiting"
        elif self.battery > 0:
            candidates = env.neighbors(self.pos)
            if candidates:
                destination = self._rng.choice(candidates)

        if destination is not None:
            self.pos = destination
            self.velocity = (
                destination[0] - old_pos[0],
                destination[1] - old_pos[1],
            )
            headings = {(1, 0): 0, (0, 1): 90, (-1, 0): 180, (0, -1): 270}
            self.heading_degrees = headings.get(self.velocity, self.heading_degrees)
            self.battery = max(0.0, self.battery - 0.1)
            self.status = "moving"
        else:
            self.velocity = (0, 0)
            self.battery = max(0.0, self.battery - 0.02)
            if self.status != "waiting":
                self.status = "idle"

        if not self.path and self.status == "moving" and self.task_id is None:
            # Random exploration is movement, but the robot has no active route.
            self.status = "moving"

    def get_state(self) -> dict[str, object]:
        return {
            "robot_id": self.id,
            "timestamp": time.time(),
            "position": list(self.pos),
            "velocity": list(self.velocity),
            "path": [list(cell) for cell in self.path],
            "goal": list(self.path[-1]) if self.path else list(self.pos),
            "battery": self.battery,
            "task_id": self.task_id,
            "status": self.status,
            "blocked_cells": [],
            "model": self.model,
            "heading_degrees": self.heading_degrees,
            "speed_mps": 1.2 if self.velocity != (0, 0) else 0.0,
            "payload_kg": self.payload_kg if self.status == "moving" else 0.0,
            "cargo_name": self.cargo_name,
            "arm_state": "carrying" if (self.model == "ATR-600" and self.status == "moving") else "idle",
            "task_stage": "transporting" if self.task_id else "patrol" if self.status == "moving" else self.status,
        }
