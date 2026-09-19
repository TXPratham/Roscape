# Role: planner-agent

Build path planning + conflict resolution in `planning/`.

## Deliverables

- `planning/astar.py` - A* on grid (4-connected), returns list of cells
- `planning/reservation.py` - Reservation table: `(cell, t) -> robot_id`
- `planning/conflict_resolver.py` - Priority-based resolution
- `planning/deadlock.py` - Wait-for graph + cycle breaker
- `tests/test_planning.py`

## Requirements

- A* must avoid obstacle cells and `blocked_cells`
- Reservation table supports horizon of 20 steps
- Priority = higher task priority, then lower battery, then robot_id tie-break
- Conflict types: vertex (same cell, same time), edge (swap)
- Resolution: lower priority robot replans with the conflicting cell temporarily blocked
- Deadlock detection: build wait-for graph from robots waiting on each other's reserved cells; if cycle found, force lowest-priority robot to yield (replan to safe cell + wait 3 steps)

## Definition of done

- Test: two robots head-on, resolver avoids collision
- Test: 3-robot cycle deadlock, breaker resolves it
- `pytest tests/test_planning.py` passes
