"""Deterministic decentralized task auction."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


DISTANCE_WEIGHT = 1.0
BATTERY_WEIGHT = 0.5
LOAD_WEIGHT = 2.0


def _value(item: Any, name: str, default: Any = None) -> Any:
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def calculate_bid(robot: Any, task: Any) -> float:
    """Return the weighted service cost advertised by *robot* for *task*.

    A lower numeric cost is a better bid. This interpretation makes distance,
    depleted battery, and current load penalties behave consistently.
    """

    position = _value(robot, "pos", _value(robot, "position"))
    pickup = _value(task, "pickup")
    if position is None or pickup is None:
        raise ValueError("robot position and task pickup are required")
    distance = abs(position[0] - pickup[0]) + abs(position[1] - pickup[1])
    battery = float(_value(robot, "battery", 100.0))
    load = float(_value(robot, "current_load", 1 if _value(robot, "task_id") else 0))
    return (
        DISTANCE_WEIGHT * distance
        + BATTERY_WEIGHT * (100.0 - battery)
        + LOAD_WEIGHT * load
    )


def auction(robots: Iterable[Any], task: Any, timeout_ms: int = 500) -> str | None:
    """Select the lowest-cost bid, breaking ties by robot id.

    ``timeout_ms`` is part of the distributed API. This pure selection function
    assumes the caller passes bids received within that window; an empty set
    therefore represents a timeout and leaves the task unassigned.
    """

    del timeout_ms
    candidates = []
    for robot in robots:
        robot_id = str(_value(robot, "id", _value(robot, "robot_id", "")))
        if robot_id:
            candidates.append((calculate_bid(robot, task), robot_id))
    if not candidates:
        return None
    winner = min(candidates, key=lambda bid: (bid[0], bid[1]))[1]
    if hasattr(task, "assigned_to"):
        task.assigned_to = winner
    elif isinstance(task, dict):
        task["assigned_to"] = winner
    return winner
