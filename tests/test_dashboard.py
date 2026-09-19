import time

from fastapi.testclient import TestClient

from dashboard.server import create_app
from sim.environment import Environment


def make_client(*, autostart: bool = False) -> TestClient:
    env = Environment(width=10, height=8, robot_count=2, seed=3)
    return TestClient(create_app(env, autostart=autostart))


def test_dashboard_page_and_static_assets_load() -> None:
    with make_client() as client:
        started = time.perf_counter()
        response = client.get("/")
        assert response.status_code == 200
        assert time.perf_counter() - started < 0.2
        assert "fleet-canvas" in response.text
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/style.css").status_code == 200


def test_state_api_matches_dashboard_contract() -> None:
    with make_client() as client:
        state = client.get("/api/state").json()
    assert set(state) >= {"robots", "tasks", "blocked_cells", "metrics", "grid"}
    assert state["grid"]["width"] == 10
    assert state["grid"]["height"] == 8
    assert len(state["grid"]["cells"]) == 8
    assert len(state["robots"]) == 2
    assert set(state["metrics"]) == {
        "collisions", "deadlocks", "completed", "avg_completion_time"
    }


def test_websocket_broadcasts_fleet_json() -> None:
    with make_client() as client:
        with client.websocket_connect("/ws") as websocket:
            state = websocket.receive_json()
            assert len(state["robots"]) == 2
            assert state["robots"][0]["robot_id"].startswith("robot-")
            assert "battery" in state["robots"][0]


def test_websocket_broadcast_interval_is_about_100ms() -> None:
    with make_client() as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            started = time.perf_counter()
            websocket.receive_json()
            elapsed = time.perf_counter() - started
    assert 0.06 <= elapsed < 0.3


def test_external_snapshot_can_feed_dashboard() -> None:
    app = create_app(autostart=False)
    supplied = {
        "grid": {"width": 2, "height": 2, "cells": [[0, 2], [1, 3]]},
        "robots": [],
        "tasks": [],
        "blocked_cells": [[1, 0]],
        "metrics": {
            "collisions": 1,
            "deadlocks": 2,
            "completed": 3,
            "avg_completion_time": 4.5,
        },
    }
    app.state.fleet_state.publish(supplied)
    supplied["metrics"]["completed"] = 99
    with TestClient(app) as client:
        assert client.get("/api/state").json()["metrics"]["completed"] == 3


def test_completion_metric_maintains_running_average() -> None:
    app = create_app(autostart=False)
    app.state.fleet_state.record_completion(2.0)
    app.state.fleet_state.record_completion(4.0)
    with TestClient(app) as client:
        metrics = client.get("/api/state").json()["metrics"]
    assert metrics["completed"] == 2
    assert metrics["avg_completion_time"] == 3.0


def test_add_and_remove_robot_api() -> None:
    with make_client() as client:
        # Add a custom ATR-600 robot
        res = client.post("/api/robots", json={"model": "ATR-600", "battery": 95.0, "pos": [3, 4]})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        robot = data["robot"]
        assert robot["model"] == "ATR-600"
        assert robot["battery"] == 95.0
        robot_id = robot["robot_id"]

        state = client.get("/api/state").json()
        assert any(r["robot_id"] == robot_id for r in state["robots"])

        # Remove the robot
        del_res = client.delete(f"/api/robots/{robot_id}")
        assert del_res.status_code == 200
        assert del_res.json()["removed"] is True

        state_after = client.get("/api/state").json()
        assert not any(r["robot_id"] == robot_id for r in state_after["robots"])


def test_add_and_remove_task_api() -> None:
    with make_client() as client:
        res = client.post(
            "/api/tasks",
            json={
                "pickup": [1, 1],
                "dropoff": [8, 6],
                "priority": 2,
                "item_name": "GEAR-UNIT X1",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        task = data["task"]
        assert task["item_name"] == "GEAR-UNIT X1"
        assert task["priority"] == 2
        task_id = task["id"]

        state = client.get("/api/state").json()
        assert any(t["id"] == task_id for t in state["tasks"])

        # Remove task
        del_res = client.delete(f"/api/tasks/{task_id}")
        assert del_res.status_code == 200
        assert del_res.json()["removed"] is True


def test_simulation_control_api() -> None:
    with make_client() as client:
        res = client.post("/api/simulation/control", json={"action": "pause"})
        assert res.status_code == 200
        assert res.json()["paused"] is True

        res = client.post("/api/simulation/control", json={"action": "speed", "speed": 2.5})
        assert res.status_code == 200
        assert res.json()["speed"] == 2.5

        res = client.post("/api/simulation/control", json={"action": "resume"})
        assert res.status_code == 200
        assert res.json()["paused"] is False
