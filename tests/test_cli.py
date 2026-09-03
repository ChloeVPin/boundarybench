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
