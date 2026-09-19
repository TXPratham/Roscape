# Role: sim-agent

Build the warehouse simulator in `sim/`.

## Deliverables

- `sim/environment.py` - grid, obstacles, pickup/dropoff, reservations
- `sim/robot.py` - Robot class per `INTERFACES.md`
- `sim/task.py` - Task dataclass
- `sim/visualize.py` - Pygame renderer
- `sim/main.py` - loop at 10 Hz
- `tests/test_sim.py` - unit tests

## Requirements

- Grid: 30x20, borders = obstacles
- Random shelves in aisles (density 20%), but always leave >= 2 wide corridors
- 3+ robots spawn at distinct free cells
- Random pickup/dropoff task generator (new task every ~5s)
- Battery drains 0.1%/step when moving, 0.02% idle
- Pygame shows: grid, robots (colored), paths, tasks, battery bars
- Support headless mode (`--headless`) for benchmarking

## Definition of done

- Robots move randomly (no planner yet) without crashing
- `pytest tests/test_sim.py` passes
- Screenshot / GIF attached
