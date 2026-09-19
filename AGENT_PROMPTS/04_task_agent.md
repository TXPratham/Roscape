# Role: task-agent

Build task allocation + rerouting in `tasks/`.

## Deliverables

- `tasks/auction.py` - Decentralized auction allocator
- `tasks/reroute.py` - Reroute on blockage
- `tasks/blockage.py` - Track blocked cells, broadcast
- `tests/test_tasks.py`

## Requirements

### Auction

- Bid = `w1 * manhattan_dist + w2 * (100 - battery) + w3 * current_load`
- `w1=1.0`, `w2=0.5`, `w3=2.0`
- Highest bid wins; ties broken by `robot_id`
- If no bid within 500ms, task stays unassigned

### Reroute

- If next cell on path is blocked, replan with A*
- If no path exists, drop task and broadcast blockage

### Blockage

- Robot that has waited > 5 steps on same cell marks it blocked
- Broadcast to peers; peers add to their blocked set with TTL = 30s

## Definition of done

- Test: 2 robots, 1 task -> closest wins auction
- Test: blocked aisle -> robot reroutes and completes
- `pytest tests/test_tasks.py` passes
