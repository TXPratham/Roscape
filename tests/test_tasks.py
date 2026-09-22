from dataclasses import dataclass

from tasks.auction import auction, calculate_bid
from tasks.blockage import BlockageTracker
from tasks.reroute import reroute


@dataclass
class Robot:
    id: str
    pos: tuple[int, int]
    battery: float = 100
    task_id: str | None = None
    current_load: int = 0
    path: list[tuple[int, int]] | None = None
    goal: tuple[int, int] | None = None
    status: str = "moving"

    def set_path(self, path):
        self.path = path


@dataclass
class Task:
    pickup: tuple[int, int]
    assigned_to: str | None = None


def test_closest_robot_wins_auction():
    robots = [Robot("far", (9, 9)), Robot("near", (1, 2))]
    task = Task((2, 2))
    assert calculate_bid(robots[1], task) < calculate_bid(robots[0], task)
    assert auction(robots, task) == "near"
    assert task.assigned_to == "near"


def test_empty_auction_leaves_task_unassigned():
    task = Task((2, 2))
    assert auction([], task) is None
    assert task.assigned_to is None


def test_blockage_detection_and_ttl():
    now = [0.0]
    tracker = BlockageTracker(ttl=30, clock=lambda: now[0])
    for _ in range(5):
        assert not tracker.observe_wait((3, 4))
    assert tracker.observe_wait((3, 4))
    assert (3, 4) in tracker.blocked_cells
    now[0] = 31
    assert not tracker.blocked_cells


def test_blocked_next_cell_reroutes():
    robot = Robot("r1", (0, 0), path=[(1, 0), (2, 0)], goal=(2, 0))
    route = reroute(robot, object(), {(1, 0)}, planner=lambda *a, **k: [(0, 1), (1, 1), (2, 1), (2, 0)])
    assert route[0] == (0, 1)
    assert robot.path == route


def test_no_route_drops_task_and_broadcasts():
    sent = []
    robot = Robot("r1", (0, 0), task_id="t1", path=[(1, 0)], goal=(2, 0))
    assert reroute(robot, object(), {(1, 0)}, planner=lambda *a, **k: [], broadcast=sent.append) == []
    assert robot.task_id is None
    assert robot.status == "blocked"
    assert sent == [{(1, 0)}]
