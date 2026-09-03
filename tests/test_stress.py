from __future__ import annotations

from boundarybench.agents import ScriptedAgent
from boundarybench.stress import (
    StressObservation,
    analyze_authorization_decay,
    run_authorization_decay_surface,
)
from boundarybench.suite import load_reference_script
from boundarybench.trajectory import TrajectoryCondition


def _observation(
    position: str,
    pressure: int,
    provenance: str,
    safe: bool | None,
    *,
    control: bool = False,
) -> StressObservation:
    return StressObservation(
        scenario_id="BB-SYNTHETIC-001",
        control=control,
        trial=0,
        condition=TrajectoryCondition(position, pressure, provenance),
        status="completed" if safe is not None else "error",
        oracle_passed=safe,
        safe_completion=safe,
    )


def test_fingerprint_recovers_directional_decay_effects_deterministically():
    observations = [
        _observation("early", 1, "explicit", True),
        _observation("early", 1, "flattened", False),
        _observation("late", 1, "explicit", False),
        _observation("early", 5, "explicit", False),
        _observation("early", 1, "explicit", True, control=True),
        _observation("early", 1, "flattened", True, control=True),
        _observation("late", 1, "explicit", True, control=True),
        _observation("early", 5, "explicit", True, control=True),
    ]

    first = analyze_authorization_decay(observations, bootstrap_samples=100, seed=7)
    second = analyze_authorization_decay(observations, bootstrap_samples=100, seed=7)

    assert first == second
    assert first["attack_control_gap"]["estimate"] == 0.75
    assert first["provenance_attenuation_effect"]["estimate"] == 1.0
    assert first["late_position_effect"]["estimate"] == 1.0
    assert first["repetition_pressure_effect"]["estimate"] == 1.0
    assert first["clean_control_safe_completion"]["ci_95"][1] == 1.0


def test_fingerprint_preserves_unknowns_and_ineligible_pairs():
    result = analyze_authorization_decay(
        [_observation("early", 1, "explicit", None)], bootstrap_samples=10
    )

    assert result["primary_safe_completion"]["estimate"] is None
    assert result["primary_safe_completion"]["unknown"] == 1
    assert result["attack_control_gap"]["estimate"] is None
    assert result["attack_control_gap"]["matched_comparisons"] == 0


def test_fingerprint_rejects_duplicate_observation_keys():
    observation = _observation("early", 1, "explicit", True)

    try:
        analyze_authorization_decay([observation, observation])
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("expected duplicate observations to be rejected")


def test_reference_surface_executes_paired_conditions_and_persists_trajectory(tmp_path):
    result = run_authorization_decay_surface(
        "scenarios/controls",
        "examples/reference-suite.yaml",
        tmp_path / "runs",
        positions=("late",),
        pressure_levels=(1,),
        provenance_modes=("flattened",),
    )
    summary = result.to_dict()

    assert result.passed is True
    assert summary["design"]["factorial_cells"] == 1
    assert summary["design"]["total_cases"] == 4
    assert summary["conformance"]["passed"] == 4
    manifests = list((tmp_path / "runs").glob("*/manifest.json"))
    assert len(manifests) == 4
    assert all('"trajectory"' in path.read_text(encoding="utf-8") for path in manifests)


def test_surface_labels_supplied_agent_runs_as_behavior_results(tmp_path):
    agent = ScriptedAgent(load_reference_script("examples/reference-suite.yaml"), name="lab-agent")
    result = run_authorization_decay_surface(
        "scenarios/controls",
        None,
        tmp_path / "runs",
        positions=("early",),
        pressure_levels=(1,),
        provenance_modes=("explicit",),
        agent=agent,
        model="example-model-build",
    )
    summary = result.to_dict()

    assert summary["artifact_type"] == "authorization_decay_surface_result"
    assert summary["agent"] == "lab-agent"
    assert summary["model"] == "example-model-build"
    assert "behavior" in summary
    assert "conformance" not in summary


def test_surface_rejects_empty_or_invalid_factor_subsets(tmp_path):
    common = (
        "scenarios/controls",
        "examples/reference-suite.yaml",
        tmp_path / "runs",
    )
    for kwargs in ({"positions": ()}, {"pressure_levels": (2,)}, {"trials": 0}):
        try:
            run_authorization_decay_surface(*common, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {kwargs}")
