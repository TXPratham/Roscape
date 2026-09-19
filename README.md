# AMR Fleet

Working reference implementation of an edge-native, decentralized fleet
coordination system for autonomous mobile robots in smart warehouses.

The repository includes a 30x20 simulator, UDP multicast peer discovery, A*
planning with time reservations and deadlock breaking, distributed task
allocation, a live FastAPI dashboard, a reproducible benchmark, and Docker
deployment definitions for three robot nodes.

The dashboard presents the grid simulation as an isometric 3D warehouse digital
twin: tall storage racks, pallets, AMR chassis, LED guidance paths, and live
operational telemetry. The underlying planner intentionally remains a discrete
2D occupancy grid, which keeps collision checks deterministic and suitable for
edge hardware; the 3D view is the real-time operational visualization.

## Requirements

- Windows, macOS, or Linux
- Python 3.11 or newer (ensure `python --version` works in your terminal)
- Docker Desktop or Docker Engine only if you want to run the containers

## Run locally

Open a PowerShell terminal in the project folder:

```powershell
cd "C:\Hackathon\SIH 2026\amr-fleet"
```

Create the environment and install dependencies once:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `python` is not recognized, install Python 3.11+ from
[python.org](https://www.python.org/downloads/) and reopen PowerShell.

### 1. Verify every module

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### 2. Run the simulator

Headless mode is useful for a quick terminal-only smoke test:

```powershell
.\.venv\Scripts\python.exe -m sim.main --headless --steps 100
```

For the standalone Pygame grid window:

```powershell
.\.venv\Scripts\python.exe -m sim.main
```

### 3. Run the 3D operations dashboard

```powershell
.\.venv\Scripts\python.exe -m uvicorn dashboard.server:app --port 8000
```

Keep that terminal running, then open <http://localhost:8000>. The browser
receives a fresh fleet snapshot every 100 ms.

### 4. Run the full benchmark

```powershell
.\.venv\Scripts\python.exe benchmark\run.py --runs 20
```

Results are written to [`benchmark/results/`](benchmark/results/). The current
measured result is 21.5% lower mean completion time with zero collisions.

For containers and ARM deployment, see [`deploy/README.md`](deploy/README.md).

## Run with Docker

With Docker installed and running:

```powershell
cd "C:\Hackathon\SIH 2026\amr-fleet\deploy"
docker compose up --build
```

Open <http://localhost:8000>. Stop the stack with `Ctrl+C`. For multicast
networking notes on Docker Desktop, Raspberry Pi, and Jetson, use
[`deploy/README.md`](deploy/README.md).

## Documents

- [`PROBLEM.md`](PROBLEM.md) - problem statement and success criteria
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - system modules and data flow
- [`INTERFACES.md`](INTERFACES.md) - shared cross-module contracts
- [`TASKS.md`](TASKS.md) - phased implementation checklist
- [`MASTER_PROMPT.md`](MASTER_PROMPT.md) - lead-agent orchestration prompt
- [`AGENT_PROMPTS/`](AGENT_PROMPTS/) - scoped prompts for all seven agents

## Development workflow

1. Give `MASTER_PROMPT.md` to the lead agent.
2. Complete and approve one phase at a time, beginning with Phase 1.
3. Run the relevant pytest suite after every phase.
4. At the end, run `.\.venv\Scripts\python.exe benchmark\run.py --runs 20` and the final acceptance check.

After Phase 1 passes, use:

```text
Phase 1 approved. Proceed to Phase 2 using AGENT_PROMPTS/02_comms_agent.md.
```

Repeat for each phase. Record demo video and screenshots after the full build.

## Final acceptance prompt

```text
Run the final acceptance check:
1. All pytest suites pass.
2. `.\.venv\Scripts\python.exe benchmark\run.py --runs 20` completes without collisions.
3. summary.md shows >= 20% completion-time improvement.
4. dashboard loads and shows live fleet.
5. Docker compose up works.
Report PASS/FAIL for each, with logs.
```
