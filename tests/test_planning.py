from __future__ import annotations

import numpy as np

from planning.astar import astar
from planning.conflict_resolver import detect_conflict, resolve_conflict
from planning.deadlock import WaitForGraph, break_deadlock, deadlock_resolution, find_cycle
from planning.reservation import ReservationTable, reserve_path


class GridEnvironment:
    def __init__(self, grid):
        self.grid = np.asarray(grid)

    def is_free(self, cell):
        x, y = cell
        return 0 <= y < self.grid.shape[0] and 0 <= x < self.grid.shape[1] and self.grid[y, x] != 1

    def neighbors(self, cell):
        x, y = cell
        return [candidate for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)) if self.is_free(candidate)]


def test_astar_avoids_obstacles_and_dynamic_blockages():
    env = GridEnvironment([[0, 0, 0], [0, 1, 0], [0, 0, 0]])
    path = astar(env, (0, 1), (2, 1), blocked={(0, 2)})
    assert path[0] == (0, 1) and path[-1] == (2, 1)
    assert (1, 1) not in path and (0, 2) not in path
    assert len(path) == 5


def test_astar_returns_empty_when_goal_is_unreachable():
    env = GridEnvironment([[0, 1, 0], [0, 1, 0], [0, 1, 0]])
    assert astar(env, (0, 0), (2, 0)) == []


def test_reservations_are_atomic_horizon_limited_and_detect_swaps():
    table = ReservationTable(horizon=20)
    assert reserve_path(table, "a", [(i, 0) for i in range(25)], 0)
    assert len(table) == 20
    before = dict(table)
    assert not reserve_path(table, "b", [(19, 0), (18, 0)], 18)
    assert table.last_conflict.kind == "edge"
    assert dict(table) == before


def test_two_robots_head_on_lower_priority_replans():
    a = {"robot_id": "a", "path": [(0, 0), (1, 0)], "task_priority": 5, "battery": 80}
    b = {"robot_id": "b", "path": [(1, 0), (0, 0)], "task_priority": 1, "battery": 20}
    assert detect_conflict(a, b)["type"] == "edge"
    result = resolve_conflict(a, b, ReservationTable())
    assert result["winner"] == "a"
    assert result["replan_robot"] == "b"
    assert result["blocked_cells"] == [(0, 0)]

    # The blocked cell is oriented to the winning path, even when B wins.
    reverse = resolve_conflict(
        {**a, "task_priority": 0}, {**b, "task_priority": 9}, ReservationTable()
    )
    assert reverse["winner"] == "b"
    assert reverse["blocked_cells"] == [(1, 0)]


def test_priority_uses_lower_battery_then_robot_id():
    path = [(0, 0), (1, 0)]
    low_battery = {"robot_id": "z", "path": path, "task_priority": 2, "battery": 20}
    high_battery = {"robot_id": "a", "path": path, "task_priority": 2, "battery": 90}
    assert resolve_conflict(low_battery, high_battery, {})["winner"] == "z"
    first_id = {"robot_id": "a", "path": path, "task_priority": 2, "battery": 20}
    assert resolve_conflict(low_battery, first_id, {})["winner"] == "a"


def test_three_robot_cycle_deadlock_breaks_lowest_priority_robot():
    graph = WaitForGraph()
    graph.add_wait("r1", "r2")
    graph.add_wait("r2", "r3")
    graph.add_wait("r3", "r1")
    graph.add_state("r1", {"robot_id": "r1", "task_priority": 5, "battery": 80})
    graph.add_state("r2", {"robot_id": "r2", "task_priority": 3, "battery": 50})
    graph.add_state("r3", {"robot_id": "r3", "task_priority": 1, "battery": 10})

    assert set(find_cycle(graph)) == {"r1", "r2", "r3"}
    assert break_deadlock(graph) == "r3"
    assert deadlock_resolution(graph, safe_cell=(4, 4)) == {
        "deadlock": True,
        "robot_id": "r3",
        "action": "yield_and_replan",
        "safe_cell": (4, 4),
        "wait_steps": 3,
    }


def test_acyclic_wait_graph_has_no_breaker():
    graph = {"r1": {"r2"}, "r2": {"r3"}, "r3": set()}
    assert find_cycle(graph) == []
    assert break_deadlock(graph) == ""
