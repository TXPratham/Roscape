"""Command-line entry point for the reproducible AMR fleet benchmark."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from benchmark.plots import generate_plots
    from benchmark.scenarios import all_scenarios
    from benchmark.stop_and_wait import simulate
else:
    from .plots import generate_plots
    from .scenarios import all_scenarios
    from .stop_and_wait import simulate


FIELDS = (
    "scenario",
    "method",
    "run",
    "seed",
    "completion_time",
    "collisions",
    "deadlocks",
    "avg_robot_idle_time",
    "total_distance",
)


def run_benchmark(runs: int = 20, output_dir: Path | None = None) -> dict[str, float]:
    if runs < 1:
        raise ValueError("runs must be positive")
    output_dir = output_dir or Path(__file__).with_name("results")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for scenario_index, scenario in enumerate(all_scenarios()):
        for run_number in range(1, runs + 1):
            seed = 10_000 * (scenario_index + 1) + run_number
            for method in ("stop_and_wait", "decentralized"):
                result = simulate(scenario, method, seed=seed)
                rows.append(
                    {
                        "scenario": scenario.name,
                        "method": method,
                        "run": run_number,
                        "seed": seed,
                        **result.__dict__,
                    }
                )

    csv_path = output_dir / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    means = {
        method: sum(float(row["completion_time"]) for row in rows if row["method"] == method)
        / sum(1 for row in rows if row["method"] == method)
        for method in ("stop_and_wait", "decentralized")
    }
    improvement = (means["stop_and_wait"] - means["decentralized"]) / means["stop_and_wait"] * 100
    collisions = int(sum(int(row["collisions"]) for row in rows))
    plots = generate_plots(rows, output_dir)

    per_scenario = []
    for scenario in all_scenarios():
        baseline = sum(float(r["completion_time"]) for r in rows if r["scenario"] == scenario.name and r["method"] == "stop_and_wait") / runs
        decentralized = sum(float(r["completion_time"]) for r in rows if r["scenario"] == scenario.name and r["method"] == "decentralized") / runs
        gain = (baseline - decentralized) / baseline * 100
        per_scenario.append(f"| {scenario.name} | {baseline:.2f} | {decentralized:.2f} | {gain:.1f}% |")

    status = "PASS" if improvement >= 20 and collisions == 0 else "FAIL"
    summary = "\n".join(
        [
            "# AMR Fleet Benchmark Summary",
            "",
            f"**Result: {status}**",
            "",
            f"- Runs per scenario and method: {runs}",
            f"- Stop-and-wait mean completion time: {means['stop_and_wait']:.2f} ticks",
            f"- Decentralized mean completion time: {means['decentralized']:.2f} ticks",
            f"- Completion-time improvement: {improvement:.1f}%",
            f"- Total collisions: {collisions}",
            "",
            "| Scenario | Stop-and-wait | Decentralized | Improvement |",
            "|---|---:|---:|---:|",
            *per_scenario,
            "",
            "Metrics are measured from synchronous grid simulation. Each paired run uses the same seeded startup delays. "
            "A collision includes vertex co-occupancy or an opposing-edge swap.",
            "",
            "Plots: " + ", ".join(path.name for path in plots),
        ]
    )
    (output_dir / "summary.md").write_text(summary + "\n", encoding="utf-8")
    print(summary)
    if collisions != 0:
        raise AssertionError(f"benchmark recorded {collisions} collisions")
    if runs >= 20 and improvement < 20:
        raise AssertionError(f"completion-time improvement {improvement:.1f}% is below 20%")
    return {"baseline_mean": means["stop_and_wait"], "decentralized_mean": means["decentralized"], "improvement": improvement, "collisions": collisions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=20, help="runs per scenario and method (default: 20)")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    run_benchmark(args.runs, args.output_dir)


if __name__ == "__main__":
    main()

