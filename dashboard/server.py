"""FastAPI server and live WebSocket feed for the fleet dashboard."""

from __future__ import annotations

import asyncio
import contextlib
import copy
import threading
import time
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from sim.environment import Environment


STATIC_DIR = Path(__file__).with_name("static")
INDEX_HTML = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
BROADCAST_INTERVAL_SECONDS = 0.1


class FleetState:
    """Thread-safe adapter between the simulator and JSON dashboard clients."""

    def __init__(self, environment: Environment | None = None) -> None:
        self.environment = environment or Environment(seed=7)
        self.blocked_cells: set[tuple[int, int]] = set()
        self.metrics: dict[str, int | float] = {
            "collisions": 0,
            "deadlocks": 0,
            "completed": 0,
            "avg_completion_time": 0.0,
        }
        self.paused: bool = False
        self.speed: float = 1.0
        self._external_snapshot: dict[str, Any] | None = None
        self._lock = threading.RLock()

    def step(self) -> None:
        """Advance the built-in demo simulation unless an external feed is active or paused."""
        with self._lock:
            if self._external_snapshot is None and not self.paused:
                self.environment.step()

    def toggle_pause(self, paused: bool | None = None) -> bool:
        with self._lock:
            self.paused = (not self.paused) if paused is None else bool(paused)
            return self.paused

    def set_speed(self, speed: float) -> float:
        with self._lock:
            self.speed = max(0.1, min(10.0, float(speed)))
            return self.speed

    def add_robot(
        self,
        model: str = "ATR-400",
        pos: tuple[int, int] | None = None,
        battery: float = 100.0,
        robot_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            robot = self.environment.add_robot(
                model=model,
                pos=pos,
                battery=battery,
                robot_id=robot_id,
            )
            return robot.get_state()

    def remove_robot(self, robot_id: str) -> bool:
        with self._lock:
            return self.environment.remove_robot(robot_id)

    def add_task(
        self,
        pickup: tuple[int, int],
        dropoff: tuple[int, int],
        priority: int = 1,
        item_name: str = "AMZ-BOX-A12",
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            task = self.environment.add_custom_task(
                pickup=pickup,
                dropoff=dropoff,
                priority=priority,
                item_name=item_name,
                assigned_to=assigned_to,
            )
            return task.to_dict()

    def remove_task(self, task_id: str) -> bool:
        with self._lock:
            return self.environment.remove_task(task_id)

    def publish(self, state: Mapping[str, Any]) -> None:
        """Publish a complete snapshot from a separately running simulator."""
        with self._lock:
            self._external_snapshot = copy.deepcopy(dict(state))

    def use_environment(self) -> None:
        """Resume snapshots from the built-in environment after external publishing."""
        with self._lock:
            self._external_snapshot = None

    def set_blocked_cells(self, cells: list[tuple[int, int]]) -> None:
        with self._lock:
            self.blocked_cells = {tuple(cell) for cell in cells}

    def record_completion(self, completion_seconds: float) -> None:
        with self._lock:
            count = int(self.metrics["completed"])
            average = float(self.metrics["avg_completion_time"])
            self.metrics["completed"] = count + 1
            self.metrics["avg_completion_time"] = round(
                (average * count + max(0.0, completion_seconds)) / (count + 1), 3
            )

    def snapshot(self) -> dict[str, Any]:
        """Return an independent, JSON-serializable fleet snapshot."""
        with self._lock:
            if self._external_snapshot is not None:
                return copy.deepcopy(self._external_snapshot)

            env = self.environment
            return {
                "timestamp": time.time(),
                "grid": {
                    "width": env.width,
                    "height": env.height,
                    "cells": env.grid.tolist(),
                },
                "robots": [robot.get_state() for robot in env.robots.values()],
                "tasks": [task.to_dict() for task in env.tasks],
                "blocked_cells": [list(cell) for cell in sorted(self.blocked_cells)],
                "metrics": dict(self.metrics),
                "paused": self.paused,
                "speed": self.speed,
            }


def create_app(
    environment: Environment | None = None, *, autostart: bool = True
) -> FastAPI:
    fleet_state = FleetState(environment)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        runner: asyncio.Task[None] | None = None
        if autostart:
            runner = asyncio.create_task(_simulation_loop(fleet_state))
        try:
            yield
        finally:
            if runner is not None:
                runner.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runner

    application = FastAPI(title="AMR Fleet Dashboard", lifespan=lifespan)
    application.state.fleet_state = fleet_state
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/", include_in_schema=False)
    async def index() -> HTMLResponse:
        content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(content)

    @application.get("/api/state")
    async def current_state() -> dict[str, Any]:
        return fleet_state.snapshot()

    @application.post("/api/robots")
    async def add_robot(payload: dict[str, Any]) -> dict[str, Any]:
        model = payload.get("model", "ATR-400")
        pos = payload.get("pos") or payload.get("position")
        if pos is not None and isinstance(pos, (list, tuple)) and len(pos) >= 2:
            pos = (int(pos[0]), int(pos[1]))
        else:
            pos = None
        battery = float(payload.get("battery", 100.0))
        robot_id = payload.get("id") or payload.get("robot_id")
        robot_state = fleet_state.add_robot(
            model=model, pos=pos, battery=battery, robot_id=robot_id
        )
        return {"status": "ok", "robot": robot_state}

    @application.delete("/api/robots/{robot_id}")
    async def remove_robot(robot_id: str) -> dict[str, Any]:
        success = fleet_state.remove_robot(robot_id)
        return {"status": "ok" if success else "not_found", "removed": success}

    @application.post("/api/tasks")
    async def add_task(payload: dict[str, Any]) -> dict[str, Any]:
        pickup = payload.get("pickup", (1, 1))
        dropoff = payload.get("dropoff", (28, 18))
        priority = int(payload.get("priority", 1))
        item_name = str(payload.get("item_name", "AMZ-BOX-A12"))
        assigned_to = payload.get("assigned_to")
        task_data = fleet_state.add_task(
            pickup=tuple(pickup),
            dropoff=tuple(dropoff),
            priority=priority,
            item_name=item_name,
            assigned_to=assigned_to,
        )
        return {"status": "ok", "task": task_data}

    @application.delete("/api/tasks/{task_id}")
    async def remove_task(task_id: str) -> dict[str, Any]:
        success = fleet_state.remove_task(task_id)
        return {"status": "ok" if success else "not_found", "removed": success}

    @application.post("/api/simulation/control")
    async def control_simulation(payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action", "")
        if action == "pause":
            fleet_state.toggle_pause(True)
        elif action == "resume":
            fleet_state.toggle_pause(False)
        elif action == "toggle":
            fleet_state.toggle_pause()
        elif action == "speed":
            speed = float(payload.get("speed", 1.0))
            fleet_state.set_speed(speed)
        elif action == "step":
            fleet_state.step()
        elif action == "random_task":
            t = fleet_state.environment.generate_task()
            return {"status": "ok", "task": t.to_dict()}
        return {
            "status": "ok",
            "paused": fleet_state.paused,
            "speed": fleet_state.speed,
        }

    @application.websocket("/ws")
    async def fleet_websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(fleet_state.snapshot())
                delay = max(0.02, BROADCAST_INTERVAL_SECONDS / max(0.1, fleet_state.speed))
                await asyncio.sleep(delay)
        except (WebSocketDisconnect, RuntimeError):
            return

    return application


async def _simulation_loop(fleet_state: FleetState) -> None:
    while True:
        started = time.monotonic()
        fleet_state.step()
        base_delay = BROADCAST_INTERVAL_SECONDS / max(0.1, fleet_state.speed)
        delay = base_delay - (time.monotonic() - started)
        await asyncio.sleep(max(0.01, delay))


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dashboard.server:app", host="0.0.0.0", port=8000, reload=False)
