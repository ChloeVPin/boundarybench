"""Structured run records and aggregation helpers."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .evaluation import METRIC_NAMES, EvaluationMetrics


@dataclass
class RunResult:
    run_id: str
    scenario_id: str
    trial: int
    seed: int
    model: str
    mitigation: str | None
    attack_variant: str | None
    position: str | int | None
    status: str
    metrics: EvaluationMetrics = field(default_factory=EvaluationMetrics)
    response: Mapping[str, Any] | None = None
    errors: list[Mapping[str, Any]] = field(default_factory=list)
    evaluation: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "trial": self.trial,
            "seed": self.seed,
            "model": self.model,
            "mitigation": self.mitigation,
            "attack_variant": self.attack_variant,
            "position": self.position,
            "status": self.status,
            "metrics": self.metrics.to_dict(),
            "response": None if self.response is None else dict(self.response),
            "errors": [dict(error) for error in self.errors],
            "evaluation": dict(self.evaluation),
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RunResult:
        metrics = EvaluationMetrics(
            **{name: value.get("metrics", {}).get(name) for name in METRIC_NAMES}
        )
        return cls(
            run_id=str(value["run_id"]),
            scenario_id=str(value["scenario_id"]),
            trial=int(value["trial"]),
            seed=int(value["seed"]),
            model=str(value["model"]),
            mitigation=value.get("mitigation"),
            attack_variant=value.get("attack_variant"),
            position=value.get("position"),
            status=str(value["status"]),
            metrics=metrics,
            response=value.get("response"),
            errors=list(value.get("errors", [])),
            evaluation=value.get("evaluation", {}),
        )


@dataclass(frozen=True)
class MetricAggregate:
    observed: int
    true: int
    false: int
    total: int

    @property
    def unknown(self) -> int:
        return self.total - self.observed

    @property
    def rate(self) -> float | None:
        return self.true / self.observed if self.observed else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed": self.observed,
            "true": self.true,
            "false": self.false,
            "unknown": self.unknown,
            "rate": self.rate,
        }


@dataclass(frozen=True)
class AggregatedResults:
    scenario_id: str | None
    trials: int
    completed_trials: int
    error_trials: int
    metrics: Mapping[str, MetricAggregate]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "trials": self.trials,
            "completed_trials": self.completed_trials,
            "error_trials": self.error_trials,
            "metrics": {name: metric.to_dict() for name, metric in self.metrics.items()},
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def csv_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name, metric in self.metrics.items():
            rows.append(
                {
                    "scenario_id": self.scenario_id,
                    "metric": name,
                    "trials": self.trials,
                    "completed_trials": self.completed_trials,
                    "error_trials": self.error_trials,
                    **metric.to_dict(),
                }
            )
        return rows

    def to_csv(self) -> str:
        rows = self.csv_rows()
        output = io.StringIO()
        fieldnames = [
            "scenario_id",
            "metric",
            "trials",
            "completed_trials",
            "error_trials",
            "observed",
            "true",
            "false",
            "unknown",
            "rate",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()


def aggregate_results(results: Iterable[RunResult | Mapping[str, Any]]) -> AggregatedResults:
    """Aggregate observed boolean metrics without statistical inference."""

    materialized = [
        result if isinstance(result, RunResult) else RunResult.from_dict(result)
        for result in results
    ]
    scenario_ids = {result.scenario_id for result in materialized}
    metrics: dict[str, MetricAggregate] = {}
    for name in METRIC_NAMES:
        observed = sum(getattr(result.metrics, name) is not None for result in materialized)
        true = sum(getattr(result.metrics, name) is True for result in materialized)
        false = sum(getattr(result.metrics, name) is False for result in materialized)
        metrics[name] = MetricAggregate(observed, true, false, len(materialized))
    return AggregatedResults(
        scenario_id=next(iter(scenario_ids)) if len(scenario_ids) == 1 else None,
        trials=len(materialized),
        completed_trials=sum(result.status == "completed" for result in materialized),
        error_trials=sum(result.status == "error" for result in materialized),
        metrics=metrics,
    )


aggregate = aggregate_results


def aggregate_runs(
    path: str | Any = ".", *, run_path: str | Any | None = None, root: str | Any | None = None
) -> AggregatedResults:
    """Load ``result.json`` files below a run directory and aggregate them."""

    return aggregate_results(_load_run_results(path, run_path=run_path, root=root))


def _load_run_results(
    path: str | Any = ".", *, run_path: str | Any | None = None, root: str | Any | None = None
) -> list[Mapping[str, Any]]:
    from pathlib import Path

    selected = run_path or root or path
    base = Path(selected)
    files = (
        [base]
        if base.is_file() and base.name == "result.json"
        else sorted(base.rglob("result.json"))
    )
    loaded: list[Mapping[str, Any]] = []
    for result_path in files:
        with result_path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        if isinstance(value, Mapping):
            loaded.append(value)
    return loaded


def summarize_runs(
    path: str | Any = ".", *, run_path: str | Any | None = None, root: str | Any | None = None
) -> dict[str, Any]:
    """Return descriptive overall and dimension-grouped summaries."""

    loaded = _load_run_results(path, run_path=run_path, root=root)
    materialized = [RunResult.from_dict(value) for value in loaded]
    report: dict[str, Any] = {"overall": aggregate_results(materialized).to_dict()}
    dimensions = {
        "by_scenario": "scenario_id",
        "by_attack_variant": "attack_variant",
        "by_model": "model",
        "by_position": "position",
    }
    for report_name, attribute in dimensions.items():
        groups: dict[str, list[RunResult]] = {}
        for result in materialized:
            key = getattr(result, attribute)
            label = "<none>" if key is None else str(key)
            groups.setdefault(label, []).append(result)
        report[report_name] = {
            label: aggregate_results(values).to_dict() for label, values in sorted(groups.items())
        }
    return report


__all__ = [
    "AggregatedResults",
    "MetricAggregate",
    "RunResult",
    "aggregate",
    "aggregate_results",
    "aggregate_runs",
    "summarize_runs",
]
