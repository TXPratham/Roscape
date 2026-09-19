"""Plotting helpers for benchmark results."""

from __future__ import annotations

from pathlib import Path


def generate_plots(rows: list[dict[str, object]], output_dir: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = list(dict.fromkeys(str(row["scenario"]) for row in rows))
    methods = ("stop_and_wait", "decentralized")
    labels = ("Stop-and-wait", "Decentralized")

    completion = {
        method: [
            sum(float(r["completion_time"]) for r in rows if r["scenario"] == scenario and r["method"] == method)
            / sum(1 for r in rows if r["scenario"] == scenario and r["method"] == method)
            for scenario in scenarios
        ]
        for method in methods
    }
    x = list(range(len(scenarios)))
    width = 0.38
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar([v - width / 2 for v in x], completion[methods[0]], width, label=labels[0])
    ax.bar([v + width / 2 for v in x], completion[methods[1]], width, label=labels[1])
    ax.set_ylabel("Mean completion time (ticks)")
    ax.set_xticks(x, [s.replace("_", "\n") for s in scenarios], fontsize=8)
    ax.set_title("Fleet completion time by scenario")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    completion_path = output_dir / "completion_time.png"
    fig.savefig(completion_path, dpi=150)
    plt.close(fig)

    metric_names = ("avg_robot_idle_time", "total_distance", "deadlocks")
    titles = ("Idle time", "Distance travelled", "Deadlocks encountered")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, metric, title in zip(axes, metric_names, titles):
        values = [
            sum(float(r[metric]) for r in rows if r["method"] == method)
            / sum(1 for r in rows if r["method"] == method)
            for method in methods
        ]
        ax.bar(labels, values, color=("#777777", "#2878b5"))
        ax.set_title(title)
        ax.tick_params(axis="x", labelrotation=15)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    metrics_path = output_dir / "fleet_metrics.png"
    fig.savefig(metrics_path, dpi=150)
    plt.close(fig)
    return [completion_path, metrics_path]

