"""Four-connected A* for the warehouse grid."""

from __future__ import annotations

import heapq
from itertools import count
from typing import Iterable

Cell = tuple[int, int]


def _cell(value: Iterable[int]) -> Cell:
    x, y = value
    return int(x), int(y)


def _neighbors(env: object, cell: Cell) -> Iterable[Cell]:
    """Use the environment API, with a grid fallback for lightweight callers."""
    neighbors = getattr(env, "neighbors", None)
    if callable(neighbors):
        yield from (_cell(candidate) for candidate in neighbors(cell))
        return

    grid = getattr(env, "grid")
    height, width = grid.shape[:2]
    x, y = cell
    for candidate in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        cx, cy = candidate
        if 0 <= cx < width and 0 <= cy < height:
            yield candidate


def _is_free(env: object, cell: Cell) -> bool:
    is_free = getattr(env, "is_free", None)
    if callable(is_free):
        return bool(is_free(cell))
    x, y = cell
    return int(getattr(env, "grid")[y, x]) != 1


def astar(
    env: object,
    start: Cell,
    goal: Cell,
    blocked: Iterable[Cell] | None = None,
) -> list[Cell]:
    """Return a shortest path from ``start`` to ``goal``, including both.

    An empty list means no path exists.  ``blocked`` is copied, so callers may
    safely mutate their blockage set while another plan is being calculated.
    The start cell remains usable (a robot can replan while standing in a cell),
    while a blocked goal is unreachable unless it is also the start.
    """
    start, goal = _cell(start), _cell(goal)
    blocked_cells = {_cell(cell) for cell in (blocked or ())}
    if start == goal:
        return [start]
    if goal in blocked_cells or not _is_free(env, start) or not _is_free(env, goal):
        return []

    def heuristic(cell: Cell) -> int:
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    serial = count()
    frontier: list[tuple[int, int, int, Cell]] = [(heuristic(start), 0, next(serial), start)]
    came_from: dict[Cell, Cell] = {}
    best_cost: dict[Cell, int] = {start: 0}

    while frontier:
        _, cost, _, current = heapq.heappop(frontier)
        if cost != best_cost.get(current):
            continue
        if current == goal:
            path = [current]
            while current != start:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in _neighbors(env, current):
            if neighbor in blocked_cells or not _is_free(env, neighbor):
                continue
            new_cost = cost + 1
            if new_cost < best_cost.get(neighbor, float("inf")):
                best_cost[neighbor] = new_cost
                came_from[neighbor] = current
                heapq.heappush(
                    frontier,
                    (new_cost + heuristic(neighbor), new_cost, next(serial), neighbor),
                )
    return []
