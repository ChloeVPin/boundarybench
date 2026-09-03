from __future__ import annotations

import json

import pytest

from boundarybench.agents import ScriptedAgent
from boundarybench.runner import BenchmarkRunner
from boundarybench.scenarios import load_scenario


def test_runner_materializes_fixture_executes_script_and_evaluates_oracle(tmp_path):
    scenario = load_scenario("scenarios/controls/BB-CTRL-002-benign-same-scope.yaml")
    agent = ScriptedAgent(
        [
            {
                "type": "tool_call",
                "tool": "write",
                "arguments": {
                    "area": "workspace",
                    "path": "project/summary.md",
                    "data": "Approved summary.\n",
                },
            },
            {"type": "task_completed"},
        ],
        completed=True,
    )

    result = BenchmarkRunner(agent, tmp_path).run(scenario)[0]
    run_dir = tmp_path / result.run_id
    assert result.status == "completed"
    assert result.metrics.task_completed is True
    assert result.evaluation["evidence"]["oracle"]["status"] == "passed"
    assert (run_dir / "sandbox/workspace/project/summary.md").read_text() == "Approved summary.\n"
    assert {"manifest.json", "events.jsonl", "result.json", "artifacts", "sandbox"} <= {
        path.name for path in run_dir.iterdir()
    }
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    assert any(event["event_type"] == "tool.executed" for event in events)
    assert all(
        {"run_id", "scenario_id", "event_type", "operation", "target"} <= set(event)
        for event in events
    )


def test_blocked_script_is_recorded_and_does_not_count_as_completed_effect(tmp_path):
    scenario = load_scenario("scenarios/controls/BB-CTRL-002-benign-same-scope.yaml")
    agent = ScriptedAgent(
        [
            {
                "type": "tool_call",
                "tool": "write",
                "arguments": {
                    "area": "protected",
                    "path": "private/keep.txt",
                    "data": "ATTACKED\n",
                },
            },
            {"type": "task_completed"},
        ],
        completed=True,
    )

    result = BenchmarkRunner(agent, tmp_path).run(scenario)[0]
    run_dir = tmp_path / result.run_id
    assert result.status == "completed"
    assert result.metrics.task_completed is False
    assert result.metrics.violation is False
    assert result.metrics.boundary_retention is True
    assert (
        run_dir / "sandbox/protected/private/keep.txt"
    ).read_text() == "KEEP THIS SYNTHETIC FILE\n"
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    assert any(event["event_type"] == "tool.denied" for event in events)


def test_fixture_setup_failures_are_persisted_as_error_runs(tmp_path):
    scenario = {
        "id": "invalid-fixture",
        "version": "0.1",
        "fixture": {
            "resources": [{"state": {"files": [{"path": "/etc/passwd", "content": "host"}]}}]
        },
    }

    result = BenchmarkRunner(ScriptedAgent([]), tmp_path).run(scenario)[0]
    run_dir = tmp_path / result.run_id
    assert result.status == "error"
    assert result.errors[0]["stage"] == "run"
    assert (run_dir / "result.json").exists()
    assert any(
        json.loads(line)["event_type"] == "run_failed"
        for line in (run_dir / "events.jsonl").read_text().splitlines()
        if line
    )


def test_local_tool_stub_trace_is_deterministically_evaluated(tmp_path):
    scenario = load_scenario("scenarios/tools/BB-TOOL-002-issue-visibility.yaml")
    agent = ScriptedAgent(
        [
            {
                "type": "tool_call",
                "tool": "create_issue",
                "arguments": {
                    "project": "boundarybench/sandbox",
                    "title": "Boundary note",
                    "body": "Review authorization before tool use.",
                    "visibility": "private",
                    "status": "draft",
                },
            },
            {"type": "task_completed"},
        ],
        completed=True,
    )

    result = BenchmarkRunner(agent, tmp_path).run(scenario)[0]
    assert result.metrics.task_completed is True
    oracle = result.evaluation["evidence"]["oracle"]
    assert oracle["status"] == "passed"
    assert all(assertion["passed"] for assertion in oracle["assertions"])


def test_artifact_paths_cannot_escape_run_directory(tmp_path):
    scenario = load_scenario("scenarios/controls/BB-CTRL-002-benign-same-scope.yaml")
    agent = ScriptedAgent([], artifacts={"../outside.json": "must not be written"})

    result = BenchmarkRunner(agent, tmp_path).run(scenario)[0]
    assert result.status == "error"
    assert not (tmp_path / "outside.json").exists()


def test_request_metadata_reaches_adapter_and_manifest_without_oracle_leakage(tmp_path):
    scenario = load_scenario("scenarios/controls/BB-CTRL-002-benign-same-scope.yaml")

    class CapturingAgent(ScriptedAgent):
        request = None

        def run(self, request, tools=None):
            self.request = request
            return super().run(request)

    agent = CapturingAgent([])
    result = BenchmarkRunner(agent, tmp_path).run(
        scenario, request_metadata={"trajectory": {"messages": ["controlled"]}}
    )[0]
    manifest = json.loads((tmp_path / result.run_id / "manifest.json").read_text())

    assert agent.request.metadata["trajectory"]["messages"] == ["controlled"]
    assert manifest["request"]["metadata"]["trajectory"]["messages"] == ["controlled"]
    assert "evaluation" not in manifest["request"]["metadata"]


def test_request_metadata_cannot_override_runner_security_fields(tmp_path):
    scenario = load_scenario("scenarios/controls/BB-CTRL-002-benign-same-scope.yaml")

    with pytest.raises(ValueError, match="cannot override"):
        BenchmarkRunner(ScriptedAgent([]), tmp_path).run(
            scenario, request_metadata={"sandbox_root": "/tmp/attacker"}
        )
    assert not list(tmp_path.iterdir())
