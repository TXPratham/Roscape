"""Time-indexed cell and directed-edge reservations."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping
from dataclasses import dataclass

Cell = tuple[int, int]
ReservationKey = tuple[Cell, int]


@dataclass(frozen=True)
class ReservationConflict:
    kind: str
    robot_id: str
    other_robot_id: str
    time: int
    cell: Cell | None = None
    edge: tuple[Cell, Cell] | None = None


class ReservationTable(MutableMapping[ReservationKey, str]):
    """Reservation table with atomic path insertion and a finite horizon."""

    def __init__(self, horizon: int = 20) -> None:
        if horizon < 1:
            raise ValueError("horizon must be positive")
        self.horizon = horizon
        self._cells: dict[ReservationKey, str] = {}
        self._edges: dict[tuple[Cell, Cell, int], str] = {}
        self.last_conflict: ReservationConflict | None = None

    def __getitem__(self, key: ReservationKey) -> str:
        return self._cells[key]

    def __setitem__(self, key: ReservationKey, value: str) -> None:
        self._cells[key] = value

    def __delitem__(self, key: ReservationKey) -> None:
        del self._cells[key]

    def __iter__(self) -> Iterator[ReservationKey]:
        return iter(self._cells)

    def __len__(self) -> int:
        return len(self._cells)

    def clear_robot(self, robot_id: str, from_time: int | None = None) -> None:
        """Remove a robot's reservations, optionally only from ``from_time``."""
        cutoff = float("-inf") if from_time is None else from_time
        self._cells = {
            key: owner
            for key, owner in self._cells.items()
            if not (owner == robot_id and key[1] >= cutoff)
        }
        self._edges = {
            key: owner
            for key, owner in self._edges.items()
            if not (owner == robot_id and key[2] >= cutoff)
        }

    def prune(self, before_time: int) -> None:
        self._cells = {key: value for key, value in self._cells.items() if key[1] >= before_time}
        self._edges = {key: value for key, value in self._edges.items() if key[2] >= before_time}

    def reserve_path(self, robot_id: str, path: Iterable[Cell], t0: int) -> bool:
        cells = [tuple(cell) for cell in path]
        cells = cells[: self.horizon]
        self.last_conflict = None

        for offset, cell in enumerate(cells):
            time = t0 + offset
            owner = self._cells.get((cell, time))
            if owner is not None and owner != robot_id:
                self.last_conflict = ReservationConflict(
                    "vertex", robot_id, owner, time, cell=cell
                )
                return False
            if offset:
                previous = cells[offset - 1]
                owner = self._edges.get((cell, previous, time))
                if owner is not None and owner != robot_id:
                    self.last_conflict = ReservationConflict(
                        "edge", robot_id, owner, time, edge=(previous, cell)
                    )
                    return False

        # Commit only after validating the entire path.
        for offset, cell in enumerate(cells):
            time = t0 + offset
            self._cells[(cell, time)] = robot_id
            if offset:
                self._edges[(cells[offset - 1], cell, time)] = robot_id
        return True


def reserve_path(
    res_table: ReservationTable | MutableMapping[ReservationKey, str],
    robot_id: str,
    path: Iterable[Cell],
    t0: int,
) -> bool:
    """Reserve a path using either ``ReservationTable`` or a plain mapping."""
    if isinstance(res_table, ReservationTable):
        return res_table.reserve_path(robot_id, path, t0)

    cells = [tuple(cell) for cell in path][:20]
    pending = [((cell, t0 + offset), robot_id) for offset, cell in enumerate(cells)]
    if any(key in res_table and res_table[key] != robot_id for key, _ in pending):
        return False
    res_table.update(pending)
    return True
