# Role: benchmark-agent

Build the benchmarking harness in `benchmark/`.

## Deliverables

- `benchmark/run.py` - Entry point
- `benchmark/stop_and_wait.py` - Baseline
- `benchmark/scenarios.py` - Test scenarios
- `benchmark/plots.py` - Matplotlib plots
- `benchmark/results/` - CSV output
- `tests/test_benchmark.py`

## Scenarios (each >= 20 runs)

1. Head-on collision course
2. Narrow intersection with 3 robots
3. Overlapping pickup/dropoff paths
4. Blocked aisle mid-run
5. Random 5 tasks, 3 robots

## Metrics per run

- Total completion time (last task done)
- Collisions (must be 0)
- Deadlocks encountered
- Avg robot idle time
- Total distance traveled

## Baseline: stop-and-wait

When two robots conflict, lower-priority robot stops until the other clears the cell.

## Output

- `benchmark/results/results.csv`
- `benchmark/results/summary.md` with:
  - Mean completion time for both methods
  - % improvement (must be >= 20%)
  - Collision count (must be 0)

## Definition of done

- `python benchmark/run.py` runs all scenarios headless
- `summary.md` shows >= 20% improvement and 0 collisions
- Plots generated
