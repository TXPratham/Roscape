# Interfaces (DO NOT CHANGE without updating all agents)

## Message schema (`comms/message.py`)

```python
{
  "robot_id": str,
  "timestamp": float,
  "position": [int, int],
  "velocity": [int, int],
  "path": [[int, int], ...],       # planned cells
  "goal": [int, int],
  "battery": float,                # 0..100
  "task_id": str | None,
  "status": "idle" | "moving" | "waiting" | "blocked",
  "blocked_cells": [[int, int], ...]
}
```

## Robot API (`sim/robot.py`)

```python
class Robot:
    id: str
    pos: tuple[int, int]
    battery: float
    task_id: str | None
    path: list[tuple[int, int]]
    status: str

    def step(self, env): ...
    def set_path(self, path): ...
    def get_state(self) -> dict: ...
```

## Environment API (`sim/environment.py`)

```python
class Environment:
    grid: np.ndarray          # 0=free, 1=obstacle, 2=pickup, 3=dropoff
    robots: dict[str, Robot]
    tasks: list[Task]

    def is_free(self, cell) -> bool: ...
    def neighbors(self, cell) -> list[tuple[int, int]]: ...
    def reserve(self, robot_id, cell, t) -> bool: ...
    def step(self): ...
```

## Planner API (`planning/`)

```python
def astar(env, start, goal, blocked=set()) -> list[tuple[int, int]]: ...
def reserve_path(res_table, robot_id, path, t0) -> bool: ...
def resolve_conflict(a_state, b_state, res_table) -> dict: ...
def break_deadlock(wait_graph) -> str: ...  # returns robot_id to replan
```

## Task API (`tasks/`)

```python
class Task:
    id: str
    pickup: tuple[int, int]
    dropoff: tuple[int, int]
    priority: int
    assigned_to: str | None

def auction(robots, task) -> str: ...       # winning robot_id
def reroute(robot, env, blocked_cells): ...
```

## Dashboard API

WebSocket endpoint: `ws://localhost:8000/ws`

Broadcast JSON every 100ms:

```json
{
  "robots": [{"state": "..."}],
  "tasks": [{"task": "..."}],
  "blocked_cells": [[0, 0]],
  "metrics": {"collisions": 0, "deadlocks": 0, "completed": 12}
}
```
