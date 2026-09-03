from boundarybench.suite import run_reference_suite


def test_reference_suite_passes_all_primary_and_negative_control_oracles(tmp_path):
    result = run_reference_suite(
        "scenarios",
        "examples/reference-suite.yaml",
        tmp_path / "runs",
    )
    summary = result.to_dict()
    assert result.passed is True
    assert summary["cases"] == 22
    assert summary["passed"] == 22
    assert summary["failed"] == 0
    assert summary["agent_boundary_score"]["score"] == 100.0
