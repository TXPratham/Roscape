from __future__ import annotations

import socket
import time

import pytest

from comms.message import Message
from comms.neighbor_table import NeighborTable
from comms.udp_node import UDPNode


def state(robot_id: str) -> Message:
    return Message(
        robot_id=robot_id,
        timestamp=time.time(),
        position=(1, 2),
        velocity=(0, 1),
        path=[(1, 3), (1, 4)],
        goal=(1, 4),
        battery=92.5,
        task_id=None,
        status="moving",
        blocked_cells=[],
    )


def eventually(predicate, timeout: float = 4.0, interval: float = 0.025) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


def unused_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


def multicast_interface() -> str:
    """Find the default IPv4 interface without sending network traffic.

    Windows does not route IPv4 multicast over its loopback adapter, while
    Linux commonly does. Connecting a UDP socket only performs local route
    selection and therefore gives the portable interface choice we need.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("192.0.2.1", 9))
            return sock.getsockname()[0]
        except OSError:
            try:
                return socket.gethostbyname(socket.gethostname())
            except OSError:
                return "0.0.0.0"


def test_message_json_round_trip_and_unknown_fields() -> None:
    original = state("r1")
    wire = original.to_dict()
    wire["future_schema_field"] = {"safe": True}

    restored = Message.from_dict(wire)

    assert restored == original
    assert Message.from_json(original.to_json()) == original
    with pytest.raises(ValueError):
        Message.from_json(b"{not-json")


def test_neighbor_table_expires_by_receipt_time() -> None:
    now = [10.0]
    table = NeighborTable(ttl=1.0, clock=lambda: now[0])
    old_timestamp = state("old-clock")
    old_timestamp.timestamp = -1_000_000.0
    table.update(old_timestamp)

    now[0] = 10.999
    assert "old-clock" in table
    now[0] = 11.0
    assert table.prune() == ["old-clock"]
    assert len(table) == 0


def test_three_multicast_nodes_discover_peers_and_expire_stopped_node() -> None:
    port = unused_udp_port()
    interface = multicast_interface()
    nodes = [
        UDPNode(
            robot_id,
            lambda robot_id=robot_id: state(robot_id),
            port=port,
            interface=interface,
            neighbor_ttl=1.0,
            test_mode=True,
        )
        for robot_id in ("r1", "r2", "r3")
    ]
    started: list[UDPNode] = []
    try:
        for node in nodes:
            try:
                node.start()
            except OSError as exc:
                pytest.skip(f"loopback multicast unavailable: {exc}")
            started.append(node)

        assert eventually(
            lambda: all(len(node.neighbors) == 2 for node in nodes), timeout=5.0
        ), [set(node.neighbors.snapshot()) for node in nodes]

        nodes[2].stop()
        assert eventually(
            lambda: all("r3" not in node.neighbors for node in nodes[:2]),
            timeout=2.5,
        )
        assert all("r2" in node.neighbors for node in nodes[:1])
        assert "r1" in nodes[1].neighbors
    finally:
        for node in started:
            node.stop()
