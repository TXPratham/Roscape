"""Wait-for graph construction, cycle detection, and deterministic breaking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .conflict_resolver import priority_key


@dataclass
class WaitForGraph:
    edges: dict[str, set[str]] = field(default_factory=dict)
    states: dict[str, Mapping[str, Any]] = field(default_factory=dict)

    def add_wait(self, waiting: str, holding: str) -> None:
        self.edges.setdefault(waiting, set()).add(holding)
        self.edges.setdefault(holding, set())

    def add_state(self, robot_id: str, state: Mapping[str, Any]) -> None:
        self.states[robot_id] = state
        self.edges.setdefault(robot_id, set())


def build_wait_graph(
    robot_states: Iterable[Mapping[str, Any]], reservations: Mapping[tuple, str]
) -> WaitForGraph:
    """Build edges for waiting robots whose next cells are owned by peers."""
    graph = WaitForGraph()
    for state in robot_states:
        robot_id = str(state.get("robot_id", state.get("id", "")))
        graph.add_state(robot_id, state)
        if state.get("status") != "waiting":
            continue
        path = state.get("path") or []
        position = tuple(state.get("position", ()))
        next_cell = None
        if path:
            normalized = [tuple(cell) for cell in path]
            next_cell = normalized[1] if normalized[0] == position and len(normalized) > 1 else normalized[0]
        if next_cell is None:
            continue
        time = int(state.get("waiting_for_time", state.get("time", 0) + 1))
        owner = reservations.get((next_cell, time))
        if owner is not None and owner != robot_id:
            graph.add_wait(robot_id, str(owner))
    return graph


def _edges(graph: WaitForGraph | Mapping[str, Iterable[str]]) -> Mapping[str, Iterable[str]]:
    return graph.edges if isinstance(graph, WaitForGraph) else graph


def find_cycle(graph: WaitForGraph | Mapping[str, Iterable[str]]) -> list[str]:
    """Return one cycle's nodes, or an empty list for an acyclic graph."""
    edges = _edges(graph)
    visited: set[str] = set()
    active: list[str] = []
    active_set: set[str] = set()

    def visit(node: str) -> list[str]:
        if node in active_set:
            return active[active.index(node) :]
        if node in visited:
            return []
        visited.add(node)
        active.append(node)
        active_set.add(node)
        for neighbor in sorted(edges.get(node, ())):
            cycle = visit(neighbor)
            if cycle:
                return cycle
        active.pop()
        active_set.remove(node)
        return []

    for node in sorted(edges):
        cycle = visit(node)
        if cycle:
            return cycle
    return []


def break_deadlock(wait_graph: WaitForGraph | Mapping[str, Iterable[str]]) -> str:
    """Return the lowest-priority robot in a cycle to replan and yield.

    If state metadata is unavailable, IDs provide the specified final tie-break:
    lexicographically larger IDs have lower priority.  An acyclic graph returns
    an empty string.
    """
    cycle = find_cycle(wait_graph)
    if not cycle:
        return ""
    states = wait_graph.states if isinstance(wait_graph, WaitForGraph) else {}
    return max(cycle, key=lambda robot_id: priority_key(states.get(robot_id, {"robot_id": robot_id})))


def deadlock_resolution(
    wait_graph: WaitForGraph | Mapping[str, Iterable[str]], safe_cell: tuple[int, int] | None = None
) -> dict[str, Any]:
    """Return the standard safe-cell and three-step wait directive."""
    robot_id = break_deadlock(wait_graph)
    if not robot_id:
        return {"deadlock": False, "action": "none"}
    return {
        "deadlock": True,
        "robot_id": robot_id,
        "action": "yield_and_replan",
        "safe_cell": safe_cell,
        "wait_steps": 3,
    }
