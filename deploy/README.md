# Edge deployment

The Compose stack starts three independent AMR processes and the fleet
dashboard. Each robot owns one simulation state, broadcasts it over UDP
multicast, and identifies itself with `ROBOT_ID`.

## Run locally

From the repository root:

```sh
cp deploy/.env.example deploy/.env
docker compose -f deploy/docker-compose.yml up --build
```

Open <http://localhost:8000>. Stop the stack with:

```sh
docker compose -f deploy/docker-compose.yml down
```

The default `amr-net` user-defined bridge is the most portable development
setup and normally forwards multicast among Linux containers. Confirm peer
discovery in the robot logs rather than assuming it on a new Docker host:

```sh
docker compose -f deploy/docker-compose.yml logs -f amr-1 amr-2 amr-3
```

## Multicast networking tradeoffs

- **Native Linux:** a Docker bridge generally carries container-to-container
  multicast and keeps the dashboard port mapping simple. If the host firewall,
  bridge multicast snooping, or Docker version prevents discovery, use host
  networking for the three robots (`network_mode: host`, remove their
  `networks` entries). Host mode gives the multicast sockets the host network
  directly, but removes network isolation and prevents scaling services that
  bind the same unicast port. The dashboard can remain on `amr-net`.
- **Docker Desktop on Windows/macOS:** containers run inside a VM; host mode and
  LAN multicast behavior differ from native Linux and may not cross the VM
  boundary. The default bridge supports an all-container demo, but physical
  robots may not be discoverable. Run the robot process natively, or deploy the
  containers to a Linux edge host, for LAN multicast.
- **Physical robots on one LAN:** macvlan gives every robot container its own
  LAN address and is the most faithful container deployment. It requires a
  Linux parent interface, a site-specific subnet/gateway, and usually a macvlan
  shim for host-to-container traffic. It is not supported consistently through
  Docker Desktop Wi-Fi. Do not copy example subnets blindly; have the network
  administrator allocate them.

The multicast group (`239.255.0.1`) is administratively scoped and TTL is one,
so packets remain on the local network segment.

## Raspberry Pi 4 (64-bit Raspberry Pi OS)

Install the current 64-bit Raspberry Pi OS and Docker Engine with the Compose
plugin. The official `python:3.11-slim` image is multi-architecture, so no
Dockerfile change is needed on an ARM64 Pi:

```sh
uname -m                 # expected: aarch64
docker buildx imagetools inspect python:3.11-slim
docker compose -f deploy/docker-compose.yml build
docker compose -f deploy/docker-compose.yml up -d
```

For a remote multi-platform build from an x86 workstation:

```sh
docker buildx build --platform linux/arm64 -f deploy/Dockerfile.robot .
docker buildx build --platform linux/arm64 -f deploy/Dockerfile.dashboard .
```

## Jetson Nano

Use a 64-bit JetPack release with a Docker version that supports Compose v2.
Jetson Nano storage and memory are constrained; enable swap for image builds or
build ARM64 images on another machine and push them to a registry. The software
does not require CUDA, so the standard ARM64 Python base is intentional. Check
that the chosen JetPack/Docker combination can run current OCI ARM64 images,
then use the same Compose commands as the Pi. Do not add the NVIDIA runtime
unless a future module actually uses CUDA.

## Verification

```sh
docker compose -f deploy/docker-compose.yml config --quiet
docker compose -f deploy/docker-compose.yml ps
curl --fail http://localhost:8000/
```

All four services should be `running` (and eventually `healthy`). The image
definitions are architecture-neutral; an ARM build must still be exercised on
the exact Pi/Jetson OS image before production use.
