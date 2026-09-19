# Role: dashboard-agent

Build the fleet dashboard in `dashboard/`.

## Deliverables

- `dashboard/server.py` - FastAPI + WebSocket
- `dashboard/static/index.html` - UI shell
- `dashboard/static/app.js` - Canvas renderer
- `dashboard/static/style.css`
- `tests/test_dashboard.py`

## Requirements

- WS endpoint `ws://localhost:8000/ws`
- Broadcast fleet JSON every 100ms (see `INTERFACES.md`)
- UI shows:
  - Grid with obstacles, pickups, dropoffs
  - Robots (colored circles) with id label
  - Planned paths (dashed lines)
  - Blocked cells (red overlay)
  - Battery bars per robot
  - Metrics: collisions, deadlocks, tasks completed, avg completion time
- Dark theme, minimal deps (no React)

## Definition of done

- Open browser, see live movement when sim runs
- Page loads under 200ms
- `pytest tests/test_dashboard.py` passes
