"""Deterministic priority-based path conflict resolution."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

Cell = tuple[int, int]


def _robot_id(state: Mapping[str, Any]) -> str:
    return str(state.get("robot_id", state.get("id", "")))


def priority_key(state: Mapping[str, Any]) -> tuple[float, float, str]:
    """Sort key where the lexicographically smallest robot has highest priority."""
    task = state.get("task")
    task_priority = state.get("task_priority", state.get("priority", 0))
    if isinstance(task, Mapping):
        task_priority = task.get("priority", task_priority)
    return (-float(task_priority or 0), float(state.get("battery", 100)), _robot_id(state))


def _timed_path(state: Mapping[str, Any]) -> tuple[int, list[Cell]]:
    start_time = int(state.get("path_start_time", state.get("t0", 0)))
    raw_path: Sequence[Sequence[int]] = state.get("path") or [state.get("position", (0, 0))]
    path = [tuple(cell) for cell in raw_path]
    position = state.get("position")
    if position is not None and (not path or path[0] != tuple(position)):
        path.insert(0, tuple(position))
    return start_time, path


def detect_conflict(
    a_state: Mapping[str, Any], b_state: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Return the earliest vertex or opposing-edge conflict between two plans."""
    a_t0, a_path = _timed_path(a_state)
    b_t0, b_path = _timed_path(b_state)
    if not a_path or not b_path:
        return None

    a_at = {a_t0 + i: cell for i, cell in enumerate(a_path)}
    b_at = {b_t0 + i: cell for i, cell in enumerate(b_path)}
    common_times = sorted(set(a_at) & set(b_at))
    candidates: list[dict[str, Any]] = []
    for time in common_times:
        if a_at[time] == b_at[time]:
            candidates.append({"type": "vertex", "time": time, "cell": a_at[time]})
        if time - 1 in a_at and time - 1 in b_at:
            if a_at[time - 1] == b_at[time] and a_at[time] == b_at[time - 1]:
                candidates.append(
                    {
                        "type": "edge",
                        "time": time,
                        "edge": (a_at[time - 1], a_at[time]),
                        "cell": a_at[time],
                    }
                )
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item["time"], item["type"] != "vertex"))


def resolve_conflict(
    a_state: Mapping[str, Any],
    b_state: Mapping[str, Any],
    res_table: object,
) -> dict[str, Any]:
    """Choose a winner and issue a temporary-block replanning directive.

    The return value is deliberately data-only so each decentralized robot can
    invoke its local A* implementation without sharing an environment object.
    """
    conflict = detect_conflict(a_state, b_state)
    if conflict is None:
        return {"conflict": False, "action": "none"}

    winner, yielding = sorted((a_state, b_state), key=priority_key)
    winner_id, yielding_id = _robot_id(winner), _robot_id(yielding)
    blocked_cell = conflict["cell"]
    if conflict["type"] == "edge":
        # The yielding robot must not enter the winner's departure cell.
        blocked_cell = tuple(
            conflict["edge"][0] if winner_id == _robot_id(a_state) else conflict["edge"][1]
        )

    return {
        "conflict": True,
        "type": conflict["type"],
        "time": conflict["time"],
        "cell": conflict["cell"],
        "winner": winner_id,
        "yielding_robot": yielding_id,
        "replan_robot": yielding_id,
        "blocked_cells": [blocked_cell],
        "action": "replan",
    }
