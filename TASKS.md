# Tasks

## Phase 1 - Simulation skeleton [sim-agent]

- [x] Grid warehouse 30x20 with shelves, pickup, dropoff zones
- [x] Robot class with pos, battery, task, path, status
- [x] Task generator
- [x] Pygame visualizer
- [x] Main loop at 10 Hz

## Phase 2 - Decentralized comms [comms-agent]

- [x] UDP multicast node
- [x] Message schema (see `INTERFACES.md`)
- [x] Neighbor table with TTL
- [x] Simulated packet loss + delay

## Phase 3 - Planning + conflict [planner-agent]

- [x] A* on grid
- [x] Reservation table `(cell, time) -> robot_id`
- [x] Priority-based conflict resolution
- [x] Deadlock detection via wait-for graph
- [x] Deadlock breaker

## Phase 4 - Task allocation [task-agent]

- [x] Auction: bid = f(distance, battery, load)
- [x] Reroute on blockage
- [x] Blockage broadcast

## Phase 5 - Dashboard [dashboard-agent]

- [x] FastAPI + WebSocket
- [x] Canvas rendering of grid, robots, tasks
- [x] Battery bars + metrics panel

## Phase 6 - Benchmark [benchmark-agent]

- [x] Stop-and-wait baseline
- [x] Decentralized run
- [x] CSV + plots
- [x] Assert >= 20% improvement, zero collisions

## Phase 7 - Deploy [deploy-agent]

- [x] Dockerfile for robot node
- [x] docker-compose with 3 robots + dashboard
- [ ] ARM build tested
