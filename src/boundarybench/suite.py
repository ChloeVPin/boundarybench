"""Run the complete deterministic BoundaryBench reference suite."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .agents import ScriptedAgent
from .results import RunResult, compute_agent_boundary_score
from .runner import BenchmarkRunner
from .scenarios import load_scenario, negative_control_variant


@dataclass(frozen=True)
class SuiteResult:
    """A compact deterministic summary plus the individual run records."""

    results: tuple[RunResult, ...]

    @property
    def passed(self) -> bool:
        return all(
            result.status == "completed"
            and result.evaluation.get("evidence", {}).get("oracle", {}).get("passed") is True
            for result in self.results
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "reference_harness_conformance",
            "boundarybench_version": "0.1.0",
            "suite": "BoundaryBench v0.1",
            "agent": "deterministic scripted reference",
            "cases": len(self.results),
            "primary_scenarios": sum(not item.scenario_id.endswith("-NC") for item in self.results),
            "negative_controls": sum(item.scenario_id.endswith("-NC") for item in self.results),
            "passed": sum(
                item.evaluation.get("evidence", {}).get("oracle", {}).get("passed") is True
                for item in self.results
            ),
            "failed": sum(
                item.evaluation.get("evidence", {}).get("oracle", {}).get("passed") is not True
                for item in self.results
            ),
            "all_oracles_passed": self.passed,
            "agent_boundary_score": compute_agent_boundary_score(self.results),
            "scenario_results": [
                {
                    "scenario_id": item.scenario_id,
                    "status": item.status,
                    "oracle": item.evaluation.get("evidence", {})
                    .get("oracle", {})
                    .get("status", "missing"),
                }
                for item in self.results
            ],
        }


def load_reference_script(path: str | Path) -> Mapping[str, Any]:
    """Load a scenario keyed local script document."""

    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("reference script must be a scenario keyed mapping")
    return value


def run_reference_suite(
    scenario_root: str | Path,
    script_path: str | Path,
    output_dir: str | Path,
    *,
    include_negative_controls: bool = True,
) -> SuiteResult:
    """Execute each corpus scenario and its declared clean comparison."""

    root = Path(scenario_root)
    files = sorted(path for path in root.rglob("*.yaml") if path.is_file())
    if not files:
        raise ValueError(f"no scenarios found under {root}")
    agent = ScriptedAgent(load_reference_script(script_path), name="reference-scripted-agent")
    results: list[RunResult] = []
    for scenario_path in files:
        scenario = load_scenario(scenario_path)
        runner = BenchmarkRunner(agent, output_dir, scenario_path=scenario_path)
        results.extend(runner.run(scenario, seed=0, model="scripted-reference"))
        if include_negative_controls:
            results.extend(
                runner.run(
                    negative_control_variant(scenario),
                    seed=0,
                    model="scripted-reference",
                    attack_variant="negative-control",
                )
            )
    return SuiteResult(tuple(results))


__all__ = ["SuiteResult", "load_reference_script", "run_reference_suite"]
