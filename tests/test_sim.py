import numpy as np

from sim.environment import Environment
from sim.robot import Robot
from sim.task import Task


def test_default_grid_and_borders() -> None:
    env = Environment(seed=7)
    assert env.grid.shape == (20, 30)
    assert np.all(env.grid[0, :] == env.OBSTACLE)
    assert np.all(env.grid[-1, :] == env.OBSTACLE)
    assert np.all(env.grid[:, 0] == env.OBSTACLE)
    assert np.all(env.grid[:, -1] == env.OBSTACLE)


def test_two_cell_corridors_are_always_clear() -> None:
    env = Environment(seed=9, shelf_density=1.0, robot_count=0)
    rows = (env.height // 2 - 1, env.height // 2)
    cols = (env.width // 2 - 1, env.width // 2)
    assert np.all(env.grid[list(rows), 1:-1] != env.OBSTACLE)
    assert np.all(env.grid[1:-1, list(cols)] != env.OBSTACLE)


def test_robots_spawn_on_distinct_free_cells() -> None:
    env = Environment(seed=1, robot_count=5)
    positions = [robot.pos for robot in env.robots.values()]
    assert len(positions) == len(set(positions)) == 5
    assert all(env.grid[y, x] != env.OBSTACLE for x, y in positions)


def test_neighbors_are_cardinal_free_cells() -> None:
    env = Environment(seed=1, robot_count=0, shelf_density=0)
    neighbors = env.neighbors((10, 10))
    assert set(neighbors) == {(9, 10), (11, 10), (10, 9), (10, 11)}


def test_reservations_are_exclusive_per_cell_and_time() -> None:
    env = Environment(seed=2, robot_count=0)
    assert env.reserve("a", (10, 10), 4)
    assert env.reserve("a", (10, 10), 4)
    assert not env.reserve("b", (10, 10), 4)
    assert env.reserve("b", (10, 10), 5)
    assert not env.reserve("a", (0, 0), 5)


def test_robot_follows_path_and_drains_moving_battery() -> None:
    env = Environment(seed=3, robot_count=0, shelf_density=0)
    robot = Robot("test", (5, 5))
    env.robots[robot.id] = robot
    robot.set_path([(5, 5), (6, 5)])
    robot.step(env)
    assert robot.pos == (6, 5)
    assert robot.velocity == (1, 0)
    assert abs(robot.battery - 99.9) < 1e-9


def test_blocked_robot_waits_and_drains_idle_battery() -> None:
    env = Environment(seed=3, robot_count=0, shelf_density=0)
    robot = Robot("test", (5, 5))
    blocker = Robot("blocker", (6, 5))
    env.robots = {robot.id: robot, blocker.id: blocker}
    robot.set_path([(6, 5)])
    robot.step(env)
    assert robot.pos == (5, 5)
    assert robot.status == "waiting"
    assert abs(robot.battery - 99.98) < 1e-9


def test_robot_state_matches_message_contract() -> None:
    robot = Robot("r1", (2, 3))
    state = robot.get_state()
    assert {
        "robot_id", "timestamp", "position", "velocity", "path", "goal",
        "battery", "task_id", "status", "blocked_cells",
    }.issubset(state)
    assert {"model", "heading_degrees", "speed_mps", "payload_kg", "task_stage"}.issubset(state)
    assert state["position"] == [2, 3]


def test_task_generation_and_periodic_step() -> None:
    env = Environment(seed=4, robot_count=0, task_interval_steps=2)
    env.step()
    assert env.tasks == []
    env.step()
    assert len(env.tasks) == 1
    assert isinstance(env.tasks[0], Task)
    assert env.tasks[0].pickup in env.pickup_cells
    assert env.tasks[0].dropoff in env.dropoff_cells


def test_random_movement_never_collides_or_enters_obstacle() -> None:
    env = Environment(seed=12, robot_count=6)
    for _ in range(100):
        env.step()
        positions = [robot.pos for robot in env.robots.values()]
        assert len(positions) == len(set(positions))
        assert all(env.grid[y, x] != env.OBSTACLE for x, y in positions)
