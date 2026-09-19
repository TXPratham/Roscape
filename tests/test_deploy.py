"""Static deployment contract checks that do not require a Docker daemon."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"


def test_required_deployment_files_exist() -> None:
    required = {
        "Dockerfile.robot",
        "Dockerfile.dashboard",
        "docker-compose.yml",
        "README.md",
        ".env.example",
        "robot_entrypoint.py",
    }
    assert required <= {path.name for path in DEPLOY.iterdir()}


def test_compose_declares_fleet_and_dashboard_contract() -> None:
    compose = (DEPLOY / "docker-compose.yml").read_text(encoding="utf-8")
    for service in ("amr-1", "amr-2", "amr-3", "dashboard"):
        assert f"  {service}:" in compose
    assert "ROBOT_ID: amr-1" in compose
    assert "ROBOT_ID: amr-2" in compose
    assert "ROBOT_ID: amr-3" in compose
    assert '"${DASHBOARD_PORT:-8000}:8000"' in compose
    assert "amr-net:" in compose


def test_images_use_python_311_and_expected_entrypoints() -> None:
    robot = (DEPLOY / "Dockerfile.robot").read_text(encoding="utf-8")
    dashboard = (DEPLOY / "Dockerfile.dashboard").read_text(encoding="utf-8")
    assert robot.startswith("FROM python:3.11-slim")
    assert "deploy.robot_entrypoint" in robot
    assert dashboard.startswith("FROM python:3.11-slim")
    assert "dashboard.server:app" in dashboard
    assert "COPY sim ./sim" in dashboard
    assert "HEALTHCHECK" in robot and "HEALTHCHECK" in dashboard
