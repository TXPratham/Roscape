"""Repeatable benchmark scenario definitions.

Coordinates are ``(x, y)``.  Scenario runs vary only their small, seeded
startup delays; maps, work, and dynamic blockages remain directly comparable
between the two coordination methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Cell = tuple[int, int]


@dataclass(frozen=True)
class RobotWork:
    start: Cell
    goals: tuple[Cell, ...]
    priority: int = 1


@dataclass(frozen=True)
class Scenario:
    name: str
    width: int
    height: int
    robots: dict[str, RobotWork]
    obstacles: frozenset[Cell] = frozenset()
    blockages: dict[int, frozenset[Cell]] = field(default_factory=dict)


def _border(width: int, height: int) -> set[Cell]:
    return (
        {(x, 0) for x in range(width)}
        | {(x, height - 1) for x in range(width)}
        | {(0, y) for y in range(height)}
        | {(width - 1, y) for y in range(height)}
    )


def all_scenarios() -> list[Scenario]:
    """Return the five acceptance scenarios in stable order."""
    scenarios: list[Scenario] = []

    scenarios.append(
        Scenario(
            "head_on_collision_course",
            13,
            7,
            {
                "r1": RobotWork((1, 3), ((11, 3), (1, 2)), 3),
                "r2": RobotWork((11, 3), ((1, 3), (11, 4)), 2),
            },
            frozenset(_border(13, 7)),
        )
    )

    # Four approach lanes meet in a roomy 3x3 crossing.  Three robots each
    # traverse the crossing twice, stressing look-ahead conflict handling.
    intersection_free = {
        (x, y)
        for x in range(6, 9)
        for y in range(1, 14)
    } | {
        (x, y)
        for x in range(1, 14)
        for y in range(6, 9)
    }
    intersection_obstacles = {
        (x, y) for x in range(15) for y in range(15)
    } - intersection_free
    scenarios.append(
        Scenario(
            "narrow_intersection_three_robots",
            15,
            15,
            {
                "r1": RobotWork((1, 7), ((13, 7), (1, 6)), 3),
                "r2": RobotWork((7, 1), ((7, 13), (6, 1)), 2),
                "r3": RobotWork((13, 8), ((1, 8), (13, 8)), 1),
            },
            frozenset(intersection_obstacles),
        )
    )

    scenarios.append(
        Scenario(
            "overlapping_pickup_dropoff_paths",
            17,
            9,
            {
                "r1": RobotWork((1, 2), ((8, 4), (15, 6), (1, 2)), 3),
                "r2": RobotWork((15, 2), ((8, 4), (1, 6), (15, 2)), 2),
                "r3": RobotWork((8, 7), ((8, 4), (8, 1), (8, 7)), 1),
            },
            frozenset(_border(17, 9)),
        )
    )

    # The middle opening closes after launch; the upper and lower openings
    # remain available and force an observable online reroute.
    wall = {(9, y) for y in range(1, 10) if y not in {2, 5, 8}}
    scenarios.append(
        Scenario(
            "blocked_aisle_mid_run",
            19,
            11,
            {
                "r1": RobotWork((1, 5), ((17, 5), (1, 6)), 3),
                "r2": RobotWork((17, 4), ((1, 4), (17, 3)), 2),
                "r3": RobotWork((2, 8), ((16, 2), (2, 9)), 1),
            },
            frozenset(_border(19, 11) | wall),
            {4: frozenset({(9, 5)})},
        )
    )

    shelves = {
        (x, y)
        for x in (4, 8, 12, 16)
        for y in range(2, 11)
        if y not in (4, 8)
    }
    scenarios.append(
        Scenario(
            "random_five_tasks_three_robots",
            21,
            13,
            {
                # Five fixed seeded jobs (pickup then drop-off), distributed
                # across three edge agents as an auction would assign them.
                "r1": RobotWork((1, 1), ((6, 4), (19, 11), (2, 8), (18, 2)), 3),
                "r2": RobotWork((19, 1), ((14, 8), (1, 11), (10, 4), (2, 10)), 2),
                "r3": RobotWork((10, 11), ((2, 4), (10, 10)), 1),
            },
            frozenset(_border(21, 13) | shelves),
        )
    )
    return scenarios
