# Edge-AI Based Distributed Fleet Coordination for AMRs in Smart Warehouses

## Background

Smart warehouses use fleets of Autonomous Mobile Robots (AMRs). Cloud-based
coordination suffers from latency, Wi-Fi dead zones, and single-point-of-failure.
We need decentralized, edge-native coordination.

## Objective

Design a decentralized coordination and collision-avoidance framework for
at least 3 AMRs running on edge hardware (Raspberry Pi / Jetson Nano).

Must handle:

1. Decentralized peer-to-peer communication (no central server)
2. Dynamic multi-agent conflict resolution (deadlocks, narrow intersections)
3. Task allocation and re-routing when aisles are blocked

## Expected Solution

A multi-robot simulation with:

- Decentralized network stack (P2P localization sharing)
- Multi-agent path planning for edge hardware
- Fleet dashboard (positions + battery)

## Success Criteria

- ZERO inter-robot collisions
- >= 20% reduction in task completion time vs stop-and-wait baseline
  when paths overlap
