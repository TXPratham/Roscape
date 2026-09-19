"""Path rerouting helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any


def reroute(
    robot: Any,
    env: Any,
    blocked_cells: Iterable[tuple[int, int]],
    *,
    planner: Callable[..., list[tuple[int, int]]] | None = None,
    broadcast: Callable[[set[tuple[int, int]]], None] | None = None,
) -> list[tuple[int, int]]:
    """Replan when the robot's next cell is blocked.

    If no route exists, the current task is released and the blockage set is
    published through the optional callback.
    """

    blocked = {tuple(cell) for cell in blocked_cells}
    path = list(getattr(robot, "path", []))
    if not path or tuple(path[0]) not in blocked:
        return path
    if planner is None:
        from planning.astar import astar

        planner = astar
    goal = getattr(robot, "goal", None) or (path[-1] if path else None)
    new_path = planner(env, tuple(robot.pos), tuple(goal), blocked=blocked) if goal else []
    if new_path:
        if hasattr(robot, "set_path"):
            robot.set_path(new_path)
        else:
            robot.path = new_path
        robot.status = "moving"
        return new_path
    robot.task_id = None
    robot.status = "blocked"
    if broadcast:
        broadcast(blocked)
    return []
