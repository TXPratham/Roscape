# Architecture

## High-level

Each AMR is an autonomous node. No central planner. Robots:

- perceive their own state
- plan locally
- broadcast intent to peers over UDP multicast
- resolve conflicts via reservation tables + priorities
- re-plan on blockages
- bid for tasks via auction

## Modules

1. `sim/` - Grid warehouse, robots, tasks, Pygame visualizer
2. `comms/` - UDP multicast node, message schema, neighbor table
3. `planning/` - A*, reservation table, conflict resolver, deadlock breaker
4. `tasks/` - Auction allocator, reroute on blockage
5. `dashboard/` - FastAPI + WebSocket UI
6. `benchmark/` - Stop-and-wait vs decentralized comparison
7. `deploy/` - Docker + docker-compose for edge nodes

## Data flow

Robot loop (10 Hz):

```text
sense -> share state -> receive peer states -> plan A*
-> reserve cells -> detect conflict -> resolve -> act
-> detect blockage -> reroute/broadcast
-> bid on tasks -> update dashboard
```

## Assumptions

- Discrete 2D grid warehouse (e.g. 30x20)
- Discrete time steps
- Symmetric Wi-Fi (UDP multicast reachable)
- Cells are single-occupancy
