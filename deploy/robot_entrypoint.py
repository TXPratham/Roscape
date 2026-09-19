"""Run one headless AMR simulation and multicast its state to its peers."""

from __future__ import annotations

import logging
import os
import signal
import threading
import time

from comms.udp_node import UDPNode
from sim.environment import Environment
from sim.robot import Robot


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} must be set to a non-empty value")
    return value


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    robot_id = _required_env("ROBOT_ID")
    seed = int(os.getenv("SIM_SEED", "2026"))
    tick_seconds = float(os.getenv("TICK_SECONDS", "0.1"))
    if tick_seconds <= 0:
        raise SystemExit("TICK_SECONDS must be greater than zero")

    # Each container owns exactly one robot. A stable ID-derived offset keeps
    # the demo nodes from starting in the same cell while preserving repeatability.
    env = Environment(robot_count=0, seed=seed)
    free_cells = [
        (x, y)
        for y in range(1, env.height - 1)
        for x in range(1, env.width - 1)
        if env.grid[y, x] != env.OBSTACLE
    ]
    start = free_cells[sum(robot_id.encode("utf-8")) % len(free_cells)]
    robot = Robot(robot_id, start, rng=env.rng)
    env.robots[robot_id] = robot

    stop = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    node = UDPNode(
        robot_id,
        robot.get_state,
        group=os.getenv("MULTICAST_GROUP", UDPNode.MULTICAST_GROUP),
        port=int(os.getenv("MULTICAST_PORT", str(UDPNode.PORT))),
        interface=os.getenv("MULTICAST_INTERFACE", "0.0.0.0"),
    )
    logging.getLogger(__name__).info(
        "starting %s at %s using multicast %s:%s",
        robot_id,
        start,
        node.group,
        node.port,
    )
    with node:
        next_tick = time.monotonic()
        next_peer_log = next_tick + 5.0
        while not stop.is_set():
            env.step()
            now = time.monotonic()
            if now >= next_peer_log:
                logging.getLogger(__name__).info(
                    "%s peers=%s",
                    robot_id,
                    sorted(node.neighbors.snapshot()),
                )
                next_peer_log = now + 5.0
            next_tick += tick_seconds
            stop.wait(max(0.0, next_tick - now))


if __name__ == "__main__":
    main()
