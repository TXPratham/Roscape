"""UDP multicast transport for decentralized robot state sharing."""

from __future__ import annotations

import logging
import random
import socket
import struct
import threading
import time
from typing import Callable

from .message import Message
from .neighbor_table import NeighborTable

LOGGER = logging.getLogger(__name__)


class UDPNode:
    """Send local state and collect peer state without a central server.

    ``state_provider`` is called before each 100 ms broadcast. It may return a
    :class:`Message` or an interface-compatible dictionary. In test mode each
    transmission independently has 5% loss and 20--80 ms of injected jitter.
    """

    MULTICAST_GROUP = "239.255.0.1"
    PORT = 5005

    def __init__(
        self,
        robot_id: str,
        state_provider: Callable[[], Message | dict],
        *,
        group: str = MULTICAST_GROUP,
        port: int = PORT,
        interface: str = "0.0.0.0",
        interval: float = 0.1,
        neighbor_ttl: float = 1.0,
        test_mode: bool = False,
        packet_loss: float = 0.05,
        jitter: tuple[float, float] = (0.02, 0.08),
        random_source: random.Random | None = None,
    ) -> None:
        if not robot_id:
            raise ValueError("robot_id must be non-empty")
        if not 0 <= packet_loss <= 1:
            raise ValueError("packet_loss must be between 0 and 1")
        if interval <= 0 or jitter[0] < 0 or jitter[0] > jitter[1]:
            raise ValueError("invalid interval or jitter range")
        self.robot_id = robot_id
        self.state_provider = state_provider
        self.group = group
        self.port = int(port)
        self.interface = interface
        self.interval = float(interval)
        self.neighbors = NeighborTable(neighbor_ttl)
        self.test_mode = test_mode
        self.packet_loss = packet_loss
        self.jitter = jitter
        self._random = random_source or random.Random()
        self._socket: socket.socket | None = None
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    @property
    def running(self) -> bool:
        return self._socket is not None and not self._stop.is_set()

    def start(self) -> "UDPNode":
        if self.running:
            return self
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", self.port))
            membership = socket.inet_aton(self.group) + socket.inet_aton(self.interface)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
            if self.interface != "0.0.0.0":
                sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_MULTICAST_IF,
                    socket.inet_aton(self.interface),
                )
            sock.settimeout(0.1)
        except OSError:
            sock.close()
            raise

        self._socket = sock
        self._stop.clear()
        self._threads = [
            threading.Thread(target=self._receive_loop, name=f"{self.robot_id}-rx", daemon=True),
            threading.Thread(target=self._broadcast_loop, name=f"{self.robot_id}-tx", daemon=True),
            threading.Thread(target=self._prune_loop, name=f"{self.robot_id}-ttl", daemon=True),
        ]
        for thread in self._threads:
            thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        sock, self._socket = self._socket, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        for thread in self._threads:
            if thread is not threading.current_thread():
                thread.join(timeout=1.0)
        self._threads.clear()

    close = stop

    def __enter__(self) -> "UDPNode":
        return self.start()

    def __exit__(self, *_args: object) -> None:
        self.stop()

    def broadcast_once(self) -> bool:
        """Send one state packet; return False when simulated loss drops it."""

        sock = self._socket
        if sock is None:
            raise RuntimeError("node is not running")
        if self.test_mode:
            if self._random.random() < self.packet_loss:
                return False
            if self._stop.wait(self._random.uniform(*self.jitter)):
                return False
        state = self.state_provider()
        message = state if isinstance(state, Message) else Message.from_dict(state)
        if message.robot_id != self.robot_id:
            raise ValueError("state_provider returned another robot's state")
        sock.sendto(message.to_json().encode("utf-8"), (self.group, self.port))
        return True

    def _broadcast_loop(self) -> None:
        next_send = time.monotonic()
        while not self._stop.is_set():
            delay = next_send - time.monotonic()
            if delay > 0 and self._stop.wait(delay):
                break
            try:
                self.broadcast_once()
            except (OSError, ValueError, TypeError):
                if not self._stop.is_set():
                    LOGGER.exception("failed to broadcast state for %s", self.robot_id)
            next_send += self.interval
            if next_send < time.monotonic() - self.interval:
                next_send = time.monotonic()

    def _receive_loop(self) -> None:
        while not self._stop.is_set():
            sock = self._socket
            if sock is None:
                break
            try:
                payload, _address = sock.recvfrom(65_535)
            except socket.timeout:
                continue
            except OSError:
                if not self._stop.is_set():
                    LOGGER.exception("multicast receive failed for %s", self.robot_id)
                break
            try:
                message = Message.from_json(payload)
            except ValueError:
                LOGGER.debug("discarding malformed multicast packet", exc_info=True)
                continue
            if message.robot_id != self.robot_id:
                self.neighbors.update(message)

    def _prune_loop(self) -> None:
        frequency = min(0.1, self.neighbors.ttl / 2)
        while not self._stop.wait(frequency):
            self.neighbors.prune()
