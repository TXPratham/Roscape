# Role: deploy-agent

Containerize for edge deployment in `deploy/`.

## Deliverables

- `deploy/Dockerfile.robot`
- `deploy/Dockerfile.dashboard`
- `deploy/docker-compose.yml`
- `deploy/README.md`
- `deploy/.env.example`

## Requirements

- Base image: `python:3.11-slim` (or arm64v8 variant)
- Robot container runs one AMR process, takes `ROBOT_ID` env var
- Dashboard container exposes port 8000
- docker-compose spins up:
  - `amr-1`, `amr-2`, `amr-3` (network: `amr-net`)
  - `dashboard`
- Multicast must work across containers (use host network or macvlan)
- Document how to run on Raspberry Pi 4 and Jetson Nano

## Definition of done

- `docker compose up` starts all services
- Dashboard reachable at localhost:8000
- README tested on x86 and ARM
