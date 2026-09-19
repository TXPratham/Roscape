"""Local blockage detection with expiring peer observations."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

Cell = tuple[int, int]


@dataclass
class BlockageTracker:
    ttl: float = 30.0
    wait_threshold: int = 5
    clock: Callable[[], float] = time.monotonic
    _blocked: dict[Cell, float] = field(default_factory=dict)
    _last_cell: Cell | None = None
    _wait_steps: int = 0

    def observe_wait(self, cell: Cell) -> bool:
        """Record a wait and return True when the cell becomes blocked."""

        cell = tuple(cell)
        if cell == self._last_cell:
            self._wait_steps += 1
        else:
            self._last_cell = cell
            self._wait_steps = 1
        if self._wait_steps > self.wait_threshold:
            self.mark(cell)
            return True
        return False

    def observe_move(self, cell: Cell) -> None:
        self._last_cell = tuple(cell)
        self._wait_steps = 0

    def mark(self, cell: Cell, *, now: float | None = None) -> None:
        now = self.clock() if now is None else now
        self._blocked[tuple(cell)] = now + self.ttl

    def update_from_peer(self, cells: list[Cell], *, now: float | None = None) -> None:
        for cell in cells:
            self.mark(tuple(cell), now=now)

    def expire(self, *, now: float | None = None) -> None:
        now = self.clock() if now is None else now
        self._blocked = {cell: expiry for cell, expiry in self._blocked.items() if expiry > now}

    @property
    def blocked_cells(self) -> set[Cell]:
        self.expire()
        return set(self._blocked)

    def message_cells(self) -> list[list[int]]:
        return [list(cell) for cell in sorted(self.blocked_cells)]
