# AMR Fleet Benchmark Summary

**Result: PASS**

- Runs per scenario and method: 20
- Stop-and-wait mean completion time: 56.72 ticks
- Decentralized mean completion time: 44.52 ticks
- Completion-time improvement: 21.5%
- Total collisions: 0

| Scenario | Stop-and-wait | Decentralized | Improvement |
|---|---:|---:|---:|
| head_on_collision_course | 43.05 | 27.65 | 35.8% |
| narrow_intersection_three_robots | 39.05 | 29.85 | 23.6% |
| overlapping_pickup_dropoff_paths | 61.00 | 46.90 | 23.1% |
| blocked_aisle_mid_run | 55.55 | 45.00 | 19.0% |
| random_five_tasks_three_robots | 84.95 | 73.20 | 13.8% |

Metrics are measured from synchronous grid simulation. Each paired run uses the same seeded startup delays. A collision includes vertex co-occupancy or an opposing-edge swap.

Plots: completion_time.png, fleet_metrics.png
