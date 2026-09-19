# Role: comms-agent

Build the decentralized P2P comms layer in `comms/`.

## Deliverables

- `comms/message.py` - Message dataclass + to/from JSON
- `comms/udp_node.py` - UDP multicast sender/receiver
- `comms/neighbor_table.py` - Peers keyed by id, TTL expiry
- `tests/test_comms.py`

## Requirements

- Multicast group: 239.255.0.1, port 5005
- Each robot has its own socket bound to receive on the multicast group
- Broadcast every 100ms with state per `INTERFACES.md`
- Neighbor entries expire after 1s without update
- Simulate 5% packet loss and 20-80ms jitter in test mode
- Robust to JSON parse errors and unknown fields

## Definition of done

- Test: spawn 3 nodes in-process, verify each sees the other two
- Test: kill one node, verify its entry disappears after TTL
- `pytest tests/test_comms.py` passes
