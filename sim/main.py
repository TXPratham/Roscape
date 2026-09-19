"""Run the Phase 1 simulation at ten updates per second."""

from __future__ import annotations

import argparse
import time

from .environment import Environment
from .visualize import Visualizer


def run(
    *,
    headless: bool = False,
    steps: int | None = None,
    seed: int | None = None,
    screenshot: str | None = None,
) -> Environment:
    env = Environment(seed=seed)
    visualizer = None if headless else Visualizer(env)
    count = 0
    running = True
    try:
        while running and (steps is None or count < steps):
            started = time.perf_counter()
            if visualizer is not None:
                running = visualizer.process_events()
            if not running:
                break
            env.step()
            count += 1
            if visualizer is not None:
                visualizer.draw()
            delay = 0.1 - (time.perf_counter() - started)
            if delay > 0:
                time.sleep(delay)
        if visualizer is not None and screenshot:
            visualizer.save(screenshot)
    finally:
        if visualizer is not None:
            visualizer.close()
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="disable Pygame")
    parser.add_argument("--steps", type=int, help="stop after this many updates")
    parser.add_argument("--seed", type=int, help="random seed")
    parser.add_argument("--screenshot", help="save the final rendered frame")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        headless=args.headless,
        steps=args.steps,
        seed=args.seed,
        screenshot=args.screenshot,
    )
