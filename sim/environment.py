"""Discrete warehouse grid, robots, task generation, and reservations."""

from __future__ import annotations

import random
from collections.abc import Iterable

import numpy as np

from .robot import Robot
from .task import Task


class Environment:
    FREE = 0
    OBSTACLE = 1
    PICKUP = 2
    DROPOFF = 3

    def __init__(
        self,
        width: int = 30,
        height: int = 20,
        *,
        shelf_density: float = 0.20,
        robot_count: int = 3,
        task_interval_steps: int = 50,
        seed: int | None = None,
    ) -> None:
        if width < 8 or height < 8:
            raise ValueError("warehouse dimensions must both be at least 8")
        if robot_count < 0:
            raise ValueError("robot_count cannot be negative")
        if not 0 <= shelf_density <= 1:
            raise ValueError("shelf_density must be between 0 and 1")

        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.grid = np.zeros((height, width), dtype=np.uint8)
        self.robots: dict[str, Robot] = {}
        self.tasks: list[Task] = []
        self.reservations: dict[tuple[tuple[int, int], int], str] = {}
        self.time = 0
        self.task_interval_steps = max(1, task_interval_steps)
        self._next_task_id = 1

        self._build_warehouse(shelf_density)
        self._spawn_robots(robot_count)

    def _build_warehouse(self, density: float) -> None:
        self.grid[0, :] = self.OBSTACLE
        self.grid[-1, :] = self.OBSTACLE
        self.grid[:, 0] = self.OBSTACLE
        self.grid[:, -1] = self.OBSTACLE

        # A two-cell-wide cross remains open and connects every warehouse area.
        corridor_rows = {self.height // 2 - 1, self.height // 2}
        corridor_cols = {self.width // 2 - 1, self.width // 2}
        protected = {
            (x, y)
            for y in corridor_rows
            for x in range(1, self.width - 1)
        } | {
            (x, y)
            for x in corridor_cols
            for y in range(1, self.height - 1)
        }

        candidates = [
            (x, y)
            for y in range(2, self.height - 2)
            for x in range(2, self.width - 2)
            if (x, y) not in protected
        ]
        shelf_count = round(len(candidates) * density)
        for x, y in self.rng.sample(candidates, shelf_count):
            self.grid[y, x] = self.OBSTACLE

        # Loading zones are kept near opposite corners and remain traversable.
        self.pickup_cells = [(1, 1), (2, 1), (1, 2)]
        self.dropoff_cells = [
            (self.width - 2, self.height - 2),
            (self.width - 3, self.height - 2),
            (self.width - 2, self.height - 3),
        ]
        for x, y in self.pickup_cells:
            self.grid[y, x] = self.PICKUP
        for x, y in self.dropoff_cells:
            self.grid[y, x] = self.DROPOFF

    def _spawn_robots(self, count: int) -> None:
        free_cells = [
            (x, y)
            for y in range(1, self.height - 1)
            for x in range(1, self.width - 1)
            if self.grid[y, x] != self.OBSTACLE
        ]
        if count > len(free_cells):
            raise ValueError("not enough free cells to spawn requested robots")
        for index, pos in enumerate(self.rng.sample(free_cells, count), start=1):
            robot_id = f"robot-{index}"
            self.robots[robot_id] = Robot(robot_id, pos, rng=self.rng)

    def in_bounds(self, cell: tuple[int, int]) -> bool:
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def is_free(
        self, cell: tuple[int, int], *, ignore_robot: str | None = None
    ) -> bool:
        if not self.in_bounds(cell):
            return False
        x, y = cell
        if self.grid[y, x] == self.OBSTACLE:
            return False
        return all(
            robot.id == ignore_robot or robot.pos != cell
            for robot in self.robots.values()
        )

    def neighbors(self, cell: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = cell
        return [
            candidate
            for candidate in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if self.is_free(candidate)
        ]

    def reserve(self, robot_id: str, cell: tuple[int, int], t: int) -> bool:
        if not self.in_bounds(cell) or self.grid[cell[1], cell[0]] == self.OBSTACLE:
            return False
        key = (tuple(cell), int(t))
        owner = self.reservations.get(key)
        if owner is not None and owner != robot_id:
            return False
        self.reservations[key] = robot_id
        return True

    def generate_task(self) -> Task:
        pickup = self.rng.choice(self.pickup_cells)
        dropoff = self.rng.choice(self.dropoff_cells)
        task = Task(
            id=f"task-{self._next_task_id}",
            pickup=pickup,
            dropoff=dropoff,
            priority=self.rng.randint(1, 3),
        )
        self._next_task_id += 1
        self.tasks.append(task)
        return task

    def add_blockages(self, cells: Iterable[tuple[int, int]]) -> None:
        """Mark free cells as obstacles; useful for later rerouting phases."""
        for cell in cells:
            if self.in_bounds(cell):
                x, y = cell
                if self.grid[y, x] == self.FREE:
                    self.grid[y, x] = self.OBSTACLE

    def add_robot(
        self,
        model: str = "ATR-400",
        pos: tuple[int, int] | None = None,
        battery: float = 100.0,
        robot_id: str | None = None,
    ) -> Robot:
        if robot_id is None:
            existing_indices = []
            for rid in self.robots:
                if rid.startswith("robot-"):
                    try:
                        existing_indices.append(int(rid.split("-")[1]))
                    except (ValueError, IndexError):
                        pass
            next_idx = (max(existing_indices) + 1) if existing_indices else (len(self.robots) + 1)
            robot_id = f"robot-{next_idx}"

        if pos is None:
            free_cells = [
                (x, y)
                for y in range(1, self.height - 1)
                for x in range(1, self.width - 1)
                if self.is_free((x, y))
            ]
            if not free_cells:
                raise ValueError("No free cells available to spawn robot")
            pos = self.rng.choice(free_cells)
        else:
            pos = (int(pos[0]), int(pos[1]))
            if not self.in_bounds(pos) or self.grid[pos[1], pos[0]] == self.OBSTACLE:
                free_cells = [
                    (x, y)
                    for y in range(1, self.height - 1)
                    for x in range(1, self.width - 1)
                    if self.is_free((x, y))
                ]
                if free_cells:
                    pos = min(free_cells, key=lambda c: abs(c[0] - pos[0]) + abs(c[1] - pos[1]))

        cargo_name = "TOTE-B5" if model == "ATR-600" else "AMZ-BOX-A12"
        robot = Robot(
            robot_id,
            pos,
            battery=battery,
            model=model,
            cargo_name=cargo_name,
            rng=self.rng,
        )
        self.robots[robot_id] = robot
        return robot

    def remove_robot(self, robot_id: str) -> bool:
        if robot_id in self.robots:
            del self.robots[robot_id]
            self.reservations = {
                k: v for k, v in self.reservations.items() if v != robot_id
            }
            for task in self.tasks:
                if task.assigned_to == robot_id:
                    task.assigned_to = None
            return True
        return False

    def add_custom_task(
        self,
        pickup: tuple[int, int],
        dropoff: tuple[int, int],
        priority: int = 1,
        item_name: str = "AMZ-BOX-A12",
        assigned_to: str | None = None,
    ) -> Task:
        pickup_pos = (int(pickup[0]), int(pickup[1]))
        dropoff_pos = (int(dropoff[0]), int(dropoff[1]))
        task = Task(
            id=f"task-{self._next_task_id}",
            pickup=pickup_pos,
            dropoff=dropoff_pos,
            priority=priority,
            assigned_to=assigned_to,
            item_name=item_name,
        )
        self._next_task_id += 1

        if assigned_to and assigned_to in self.robots:
            robot = self.robots[assigned_to]
            robot.task_id = task.id
            robot.cargo_name = item_name

        self.tasks.append(task)
        return task

    def remove_task(self, task_id: str) -> bool:
        for idx, t in enumerate(self.tasks):
            if t.id == task_id:
                self.tasks.pop(idx)
                for r in self.robots.values():
                    if r.task_id == task_id:
                        r.task_id = None
                return True
        return False

    def step(self) -> None:
        for robot in self.robots.values():
            robot.step(self)
        self.time += 1
        if self.time % self.task_interval_steps == 0:
            self.generate_task()
        self.reservations = {
            key: owner for key, owner in self.reservations.items() if key[1] >= self.time
        }
