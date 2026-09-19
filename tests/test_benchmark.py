from __future__ import annotations

import csv

from benchmark.run import run_benchmark
from benchmark.scenarios import all_scenarios
from benchmark.stop_and_wait import simulate


def test_five_required_scenarios_are_defined():
    scenarios = all_scenarios()
    assert len(scenarios) == 5
    assert {scenario.name for scenario in scenarios} == {
        "head_on_collision_course",
        "narrow_intersection_three_robots",
        "overlapping_pickup_dropoff_paths",
        "blocked_aisle_mid_run",
        "random_five_tasks_three_robots",
    }


def test_methods_are_deterministic_and_collision_free():
    scenario = all_scenarios()[0]
    for method in ("stop_and_wait", "decentralized"):
        first = simulate(scenario, method, seed=42)
        second = simulate(scenario, method, seed=42)
        assert first == second
        assert first.collisions == 0
        assert first.completion_time > 0


def test_harness_writes_csv_summary_and_plots(tmp_path):
    result = run_benchmark(runs=2, output_dir=tmp_path)
    rows = list(csv.DictReader((tmp_path / "results.csv").open(encoding="utf-8")))
    assert len(rows) == 5 * 2 * 2
    assert set(rows[0]) >= {"scenario", "method", "completion_time", "collisions"}
    assert result["collisions"] == 0
    assert (tmp_path / "summary.md").is_file()
    assert (tmp_path / "completion_time.png").stat().st_size > 0
    assert (tmp_path / "fleet_metrics.png").stat().st_size > 0


def test_twenty_run_acceptance_target_is_measured_not_stubbed():
    baseline_times = []
    decentralized_times = []
    collisions = 0
    for scenario_index, scenario in enumerate(all_scenarios()):
        for run_number in range(1, 21):
            seed = 10_000 * (scenario_index + 1) + run_number
            baseline = simulate(scenario, "stop_and_wait", seed=seed)
            decentralized = simulate(scenario, "decentralized", seed=seed)
            baseline_times.append(baseline.completion_time)
            decentralized_times.append(decentralized.completion_time)
            collisions += baseline.collisions + decentralized.collisions

    baseline_mean = sum(baseline_times) / len(baseline_times)
    decentralized_mean = sum(decentralized_times) / len(decentralized_times)
    measured_improvement = (baseline_mean - decentralized_mean) / baseline_mean
    assert collisions == 0
    assert measured_improvement >= 0.20
