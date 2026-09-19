"""Synchronous stop-and-wait and reservation-aware fleet simulations."""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from planning.astar import astar
from planning.conflict_resolver import resolve_conflict

from .scenarios import Cell, Scenario


class BenchmarkGrid:
    """Minimal static-grid adapter for the production A* implementation."""

    def __init__(self, width: int, height: int, obstacles: set[Cell]):
        self.grid = np.zeros((height, width), dtype=np.uint8)
        self.obstacles = set(obstacles)
        for x, y in obstacles:
            self.grid[y, x] = 1

    def is_free(self, cell: Cell) -> bool:
        x, y = cell
        return (
            0 <= y < self.grid.shape[0]
            and 0 <= x < self.grid.shape[1]
            and cell not in self.obstacles
        )

    def neighbors(self, cell: Cell) -> list[Cell]:
        x, y = cell
        # Stable order makes the experiment reproducible.
        return [
            c
            for c in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))
            if self.is_free(c)
        ]


@dataclass
class Agent:
    robot_id: str
    pos: Cell
    goals: list[Cell]
    priority: int
    route: list[Cell]
    start_delay: int = 0
    idle_steps: int = 0
    distance: int = 0

    @property
    def done(self) -> bool:
        return not self.goals


@dataclass(frozen=True)
class RunMetrics:
    completion_time: int
    collisions: int
    deadlocks: int
    avg_robot_idle_time: float
    total_distance: int


def _plan(grid: BenchmarkGrid, agent: Agent, extra_blocked: set[Cell] | None = None) -> None:
    if not agent.goals:
        agent.route = []
        return
    route = astar(grid, agent.pos, agent.goals[0], blocked=extra_blocked or set())
    if route and route[0] == agent.pos:
        route = route[1:]
    agent.route = route


def _advance_completed_goals(grid: BenchmarkGrid, agent: Agent) -> None:
    while agent.goals and agent.pos == agent.goals[0]:
        agent.goals.pop(0)
        _plan(grid, agent)


def _priority(agent: Agent) -> tuple[int, str]:
    return (-agent.priority, agent.robot_id)


def _future_conflict(a: Agent, b: Agent, horizon: int = 10) -> Cell | None:
    """Find the first common cell in two near-term route windows."""
    a_cells = [a.pos, *a.route[:horizon]]
    b_cells = [b.pos, *b.route[:horizon]]
    for cell in a_cells[1:]:
        if cell in b_cells[1:]:
            return cell
    return None


def _apply_coordination(
    agents: dict[str, Agent],
    grid: BenchmarkGrid,
    method: str,
    tick: int,
) -> tuple[dict[str, Cell], int]:
    """Return safe next positions plus deadlocks observed in this tick."""
    active = [a for a in agents.values() if not a.done and a.start_delay <= tick]
    desired = {a.robot_id: (a.route[0] if a.route else a.pos) for a in active}
    forced_wait: set[str] = set()

    # Stop-and-wait reacts to overlapping route windows.  The yielding AMR
    # remains stopped until the winner has actually cleared the contested cell.
    # Reservation-aware agents instead replan before reaching that cell.
    for index, first in enumerate(sorted(active, key=_priority)):
        for second in sorted(active, key=_priority)[index + 1 :]:
            conflict_cell = _future_conflict(first, second)
            if conflict_cell is None:
                continue
            winner, loser = sorted((first, second), key=_priority)
            if method == "stop_and_wait":
                # Only stop when the winner is at least as close to the shared
                # cell. This permits both agents to make useful progress while
                # retaining the deliberately reactive baseline behavior.
                winner_distance = ([winner.pos, *winner.route].index(conflict_cell))
                loser_distance = ([loser.pos, *loser.route].index(conflict_cell))
                if winner_distance <= loser_distance + 3:
                    forced_wait.add(loser.robot_id)
            else:
                alternate = astar(grid, loser.pos, loser.goals[0], blocked={conflict_cell})
                if (
                    alternate
                    and len(alternate) > 1
                    and len(alternate) - 1 <= len(loser.route) + 2
                    and alternate[1] != desired[loser.robot_id]
                ):
                    loser.route = alternate[1:]
                    desired[loser.robot_id] = loser.route[0]

    for robot_id in forced_wait:
        desired[robot_id] = agents[robot_id].pos

    # Resolve same-cell and edge-swap conflicts by the project's deterministic
    # priority contract. Repeat because one forced wait can block another move.
    deadlocks = 0
    changed = True
    while changed:
        changed = False
        ids = sorted(desired)
        for i, a_id in enumerate(ids):
            for b_id in ids[i + 1 :]:
                a, b = agents[a_id], agents[b_id]
                same = desired[a_id] == desired[b_id] and desired[a_id] != a.pos
                swap = desired[a_id] == b.pos and desired[b_id] == a.pos and a.pos != b.pos
                if not same and not swap:
                    continue
                decision = resolve_conflict(
                    {"robot_id": a_id, "position": a.pos, "path": [a.pos, desired[a_id]], "task_priority": a.priority},
                    {"robot_id": b_id, "position": b.pos, "path": [b.pos, desired[b_id]], "task_priority": b.priority},
                    {},
                )
                loser_id = str(decision.get("yielding_robot") or max(a_id, b_id))
                desired[loser_id] = agents[loser_id].pos
                if swap:
                    # The winner cannot enter an occupied cell. Move the loser
                    # into a free side cell when possible, otherwise both wait.
                    winner_id = b_id if loser_id == a_id else a_id
                    occupied = {agent.pos for agent in agents.values()}
                    reserved = set(desired.values())
                    side_cells = [
                        cell
                        for cell in grid.neighbors(agents[loser_id].pos)
                        if cell not in occupied and cell not in reserved
                    ]
                    if side_cells:
                        desired[loser_id] = side_cells[0]
                        agents[loser_id].route = []
                    else:
                        desired[winner_id] = agents[winner_id].pos
                    deadlocks += 1
                changed = True

        # A robot may not enter a cell whose occupant is staying put.
        for mover_id, destination in list(desired.items()):
            if destination == agents[mover_id].pos:
                continue
            occupant = next((a for a in agents.values() if a.pos == destination), None)
            if occupant and desired.get(occupant.robot_id, occupant.pos) == occupant.pos:
                occupied = {agent.pos for agent in agents.values()}
                reserved = set(desired.values())
                side_cells = [
                    cell
                    for cell in grid.neighbors(occupant.pos)
                    if cell not in occupied and cell not in reserved and cell != agents[mover_id].pos
                ]
                # A stopped lower-priority AMR must vacate when the winning AMR
                # reaches it; this is the baseline's deadlock escape, not a
                # look-ahead optimization.
                if side_cells and _priority(agents[mover_id]) < _priority(occupant):
                    desired[occupant.robot_id] = side_cells[0]
                    occupant.route = []
                    deadlocks += 1
                else:
                    desired[mover_id] = agents[mover_id].pos
                changed = True

    return desired, deadlocks


def simulate(
    scenario: Scenario,
    method: str,
    *,
    seed: int,
    max_steps: int = 1000,
) -> RunMetrics:
    """Run one deterministic experiment and return observed metrics."""
    if method not in {"stop_and_wait", "decentralized"}:
        raise ValueError(f"unknown method: {method}")
    rng = random.Random(seed)
    grid = BenchmarkGrid(scenario.width, scenario.height, set(scenario.obstacles))
    agents = {
        robot_id: Agent(
            robot_id,
            work.start,
            list(work.goals),
            work.priority,
            [],
            start_delay=rng.randint(0, 2),
        )
        for robot_id, work in scenario.robots.items()
    }
    for agent in agents.values():
        _plan(grid, agent)
        if agent.goals and not agent.route:
            raise RuntimeError(f"{scenario.name}: no initial route for {agent.robot_id}")

    collisions = 0
    deadlocks = 0
    tick = 0
    while tick < max_steps and not all(agent.done for agent in agents.values()):
        if tick in scenario.blockages:
            grid.obstacles.update(scenario.blockages[tick])
            for cell in scenario.blockages[tick]:
                grid.grid[cell[1], cell[0]] = 1
            for agent in agents.values():
                if any(cell in grid.obstacles for cell in agent.route):
                    _plan(grid, agent)

        for agent in agents.values():
            _advance_completed_goals(grid, agent)
            if not agent.done and not agent.route:
                _plan(grid, agent)

        old_positions = {robot_id: agent.pos for robot_id, agent in agents.items()}
        desired, tick_deadlocks = _apply_coordination(agents, grid, method, tick)
        deadlocks += tick_deadlocks

        for robot_id, agent in agents.items():
            destination = desired.get(robot_id, agent.pos)
            if destination == agent.pos:
                if not agent.done:
                    agent.idle_steps += 1
                continue
            agent.pos = destination
            agent.distance += 1
            if agent.route and agent.route[0] == destination:
                agent.route.pop(0)
            else:
                _plan(grid, agent)

        new_positions = [agent.pos for agent in agents.values()]
        collisions += len(new_positions) - len(set(new_positions))
        ids = sorted(agents)
        for i, a_id in enumerate(ids):
            for b_id in ids[i + 1 :]:
                if (
                    old_positions[a_id] == agents[b_id].pos
                    and old_positions[b_id] == agents[a_id].pos
                    and old_positions[a_id] != old_positions[b_id]
                ):
                    collisions += 1
        tick += 1

    if not all(agent.done for agent in agents.values()):
        state = {robot_id: (agent.pos, agent.goals, agent.route[:3]) for robot_id, agent in agents.items()}
        raise RuntimeError(f"{scenario.name}/{method} did not finish in {max_steps} ticks: {state}")
    return RunMetrics(
        completion_time=tick,
        collisions=collisions,
        deadlocks=deadlocks,
        avg_robot_idle_time=sum(a.idle_steps for a in agents.values()) / len(agents),
        total_distance=sum(a.distance for a in agents.values()),
    )
