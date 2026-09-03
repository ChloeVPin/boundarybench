from __future__ import annotations

from boundarybench.cli import main


def test_cli_validates_corpus_and_runs_scripted_path(tmp_path, capsys):
    assert main(["validate", "scenarios/controls"]) == 0
    assert "valid:" in capsys.readouterr().out

    assert (
        main(
            [
                "run",
                "scenarios/controls/BB-CTRL-002-benign-same-scope.yaml",
                "--script",
                "examples/smoke-script.yaml",
                "--output-root",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert '"task_completed": true' in capsys.readouterr().out


def test_cli_runs_complete_reference_suite(tmp_path, capsys):
    summary = tmp_path / "summary.json"
    assert (
        main(
            [
                "suite",
                "--output-root",
                str(tmp_path / "runs"),
                "--summary",
                str(summary),
            ]
        )
        == 0
    )
    assert '"all_oracles_passed": true' in capsys.readouterr().out
    assert summary.exists()


def test_cli_runs_authorization_decay_surface_subset(tmp_path, capsys):
    summary = tmp_path / "stress-summary.json"
    assert (
        main(
            [
                "stress",
                "--scenarios",
                "scenarios/controls",
                "--positions",
                "late",
                "--pressure-levels",
                "1",
                "--provenance-modes",
                "flattened",
                "--output-root",
                str(tmp_path / "stress-runs"),
                "--summary",
                str(summary),
            ]
        )
        == 0
    )
    assert '"protocol": "Authorization Decay Surface"' in capsys.readouterr().out
    assert summary.exists()
