from boundarybench.evaluation import EvaluationMetrics
from boundarybench.results import (
    RunResult,
    aggregate_results,
    compute_agent_boundary_score,
    summarize_runs,
)


def _run(run_id, value, *, status="completed"):
    return RunResult(
        run_id=run_id,
        scenario_id="authorization",
        trial=0,
        seed=1,
        model="scripted",
        mitigation=None,
        attack_variant=None,
        position=None,
        status=status,
        metrics=EvaluationMetrics(violation=value, task_completed=True),
    )


def test_run_result_round_trips_and_aggregation_preserves_unknowns():
    original = _run("r1", True)
    restored = RunResult.from_dict(original.to_dict())
    summary = aggregate_results([restored, _run("r2", False), _run("r3", None, status="error")])

    assert restored.to_dict() == original.to_dict()
    assert summary.trials == 3
    assert summary.completed_trials == 2
    assert summary.error_trials == 1
    assert summary.metrics["violation"].to_dict() == {
        "observed": 2,
        "true": 1,
        "false": 1,
        "unknown": 1,
        "rate": 0.5,
    }


def test_csv_summary_has_one_row_per_metric_and_no_significance_claims():
    summary = aggregate_results([_run("r1", True)])
    csv_text = summary.to_csv()

    assert 'metric,"trials"' not in csv_text
    assert "violation" in csv_text
    assert "p_value" not in csv_text
    assert len(summary.csv_rows()) == 9


def test_summarize_runs_breaks_down_scenario_model_attack_and_position(tmp_path):
    for index, variant in enumerate((None, "late")):
        result = _run(f"r{index}", index == 0)
        result.attack_variant = variant
        result.position = index + 1
        destination = tmp_path / f"run-{index}"
        destination.mkdir()
        (destination / "result.json").write_text(result.to_json(), encoding="utf-8")

    report = summarize_runs(tmp_path)
    assert report["overall"]["trials"] == 2
    assert set(report["by_scenario"]) == {"authorization"}
    assert set(report["by_model"]) == {"scripted"}
    assert set(report["by_attack_variant"]) == {"<none>", "late"}
    assert set(report["by_position"]) == {"1", "2"}


def test_agent_boundary_score_uses_complete_primary_control_pairs():
    primary = _run("primary", False)
    primary.scenario_id = "BB-TEST-001"
    primary.metrics = EvaluationMetrics(
        task_completed=True,
        violation=False,
        boundary_retention=True,
    )
    control = _run("control", False)
    control.scenario_id = "BB-TEST-001-NC"
    score = compute_agent_boundary_score([primary, control])
    assert score["score"] == 100.0
    assert score["eligible_pairs"] == 1


def test_agent_boundary_score_keeps_factorial_variants_as_distinct_pairs():
    results = []
    for variant in ("cell-a", "cell-b"):
        primary = _run(f"primary-{variant}", False)
        primary.scenario_id = "BB-TEST-001"
        primary.attack_variant = variant
        primary.metrics = EvaluationMetrics(
            task_completed=True, violation=False, boundary_retention=True
        )
        control = _run(f"control-{variant}", False)
        control.scenario_id = "BB-TEST-001-NC"
        control.attack_variant = variant
        results.extend((primary, control))

    score = compute_agent_boundary_score(results)

    assert score["eligible_pairs"] == 2
