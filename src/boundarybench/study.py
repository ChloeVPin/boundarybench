"""Deterministic preregistration and resource planning for model studies."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import product
from pathlib import Path
from typing import Any

import yaml

from ._version import __version__
from .scenarios import load_scenario
from .trajectory import (
    POSITIONS,
    PRESSURE_LEVELS,
    PROVENANCE_MODES,
    TrajectoryCondition,
    authorization_decay_order_key,
)

_CENT = Decimal("0.01")
_MILLION = Decimal("1000000")


def _money(value: Decimal) -> str:
    return str(value.quantize(_CENT, rounding=ROUND_HALF_UP))


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    return value


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _decimal(value: Any, name: str, *, minimum: Decimal = Decimal("0")) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{name} must be a decimal number") from exc
    if not parsed.is_finite() or parsed < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return parsed


@dataclass(frozen=True, slots=True)
class StudyModel:
    id: str
    input_per_million_usd: Decimal
    output_per_million_usd: Decimal


@dataclass(frozen=True, slots=True)
class StudyArm:
    id: str
    description: str
    adapter_mitigation: str


@dataclass(frozen=True, slots=True)
class StudySpecification:
    path: Path
    raw: Mapping[str, Any]
    title: str
    scenario_root: Path
    paired_clean_controls: bool
    positions: tuple[str, ...]
    pressure_levels: tuple[int, ...]
    provenance_modes: tuple[str, ...]
    trials_per_cell: int
    seed: int
    arms: tuple[StudyArm, ...]
    models: tuple[StudyModel, ...]
    input_tokens_per_case: int
    output_tokens_per_case: int
    reserve_fraction: Decimal
    funding_cap_usd: Decimal


def load_study(path: str | Path) -> StudySpecification:
    """Load and validate one machine-readable confirmatory study specification."""

    selected = Path(path)
    try:
        raw = yaml.safe_load(selected.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"could not read study specification {selected}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"could not parse study specification {selected}: {exc}") from exc
    root = _mapping(raw, "study specification")
    for field in (
        "study_version",
        "status",
        "title",
        "price_basis_date",
        "funding_cap_usd",
        "replication_reserve_fraction",
        "research_questions",
        "hypotheses",
        "design",
        "arms",
        "models",
        "token_budget_per_case",
        "analysis",
        "exclusions",
        "stopping_rule",
        "responsible_research",
    ):
        if field not in root:
            raise ValueError(f"study specification is missing required field: {field}")
    if root["status"] != "preregistered":
        raise ValueError("study status must be 'preregistered'")
    title = root["title"]
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")
    try:
        date.fromisoformat(str(root["price_basis_date"]))
    except ValueError as exc:
        raise ValueError("price_basis_date must be an ISO 8601 date") from exc
    questions = _sequence(root["research_questions"], "research_questions")
    if not all(isinstance(item, str) and item.strip() for item in questions):
        raise ValueError("research_questions must contain non-empty strings")
    hypotheses = _sequence(root["hypotheses"], "hypotheses")
    hypothesis_ids = []
    for index, value in enumerate(hypotheses):
        item = _mapping(value, f"hypotheses[{index}]")
        if not all(
            isinstance(item.get(field), str) and item[field].strip()
            for field in (
                "id",
                "statement",
                "estimand",
                "direction",
            )
        ):
            raise ValueError(f"hypotheses[{index}] requires non-empty string fields")
        hypothesis_ids.append(item["id"])
    _reject_duplicate_ids(hypothesis_ids, "hypotheses")
    _mapping(root["analysis"], "analysis")
    _sequence(root["exclusions"], "exclusions")
    _mapping(root["stopping_rule"], "stopping_rule")
    _mapping(root["responsible_research"], "responsible_research")

    design = _mapping(root["design"], "design")
    raw_scenario_root = design.get("scenario_root")
    if not isinstance(raw_scenario_root, str) or not raw_scenario_root:
        raise ValueError("design.scenario_root must be a non-empty path")
    scenario_root = (selected.parent / raw_scenario_root).resolve()
    positions = tuple(_sequence(design.get("positions"), "design.positions"))
    pressures = tuple(_sequence(design.get("pressure_levels"), "design.pressure_levels"))
    provenance = tuple(_sequence(design.get("provenance_modes"), "design.provenance_modes"))
    _validate_levels(positions, POSITIONS, "design.positions")
    _validate_levels(pressures, PRESSURE_LEVELS, "design.pressure_levels")
    _validate_levels(provenance, PROVENANCE_MODES, "design.provenance_modes")
    trials = _positive_int(design.get("trials_per_cell"), "design.trials_per_cell")
    seed = design.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("design.seed must be an integer")
    paired = design.get("paired_clean_controls")
    if paired is not True:
        raise ValueError("design.paired_clean_controls must be true")

    arms = tuple(_load_arms(_sequence(root["arms"], "arms")))
    models = tuple(_load_models(_sequence(root["models"], "models")))
    token_budget = _mapping(root["token_budget_per_case"], "token_budget_per_case")
    input_tokens = _positive_int(
        token_budget.get("input_tokens"), "token_budget_per_case.input_tokens"
    )
    output_tokens = _positive_int(
        token_budget.get("output_tokens"), "token_budget_per_case.output_tokens"
    )
    reserve = _decimal(root.get("replication_reserve_fraction"), "replication_reserve_fraction")
    if reserve > 1:
        raise ValueError("replication_reserve_fraction cannot exceed 1")
    funding_cap = _decimal(root.get("funding_cap_usd"), "funding_cap_usd", minimum=_CENT)
    return StudySpecification(
        path=selected,
        raw=root,
        title=title,
        scenario_root=scenario_root,
        paired_clean_controls=paired,
        positions=positions,
        pressure_levels=pressures,
        provenance_modes=provenance,
        trials_per_cell=trials,
        seed=seed,
        arms=arms,
        models=models,
        input_tokens_per_case=input_tokens,
        output_tokens_per_case=output_tokens,
        reserve_fraction=reserve,
        funding_cap_usd=funding_cap,
    )


def _validate_levels(values: Sequence[Any], allowed: Sequence[Any], name: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{name} cannot contain duplicate values")
    invalid = [value for value in values if value not in allowed]
    if invalid:
        raise ValueError(f"{name} contains unsupported values: {invalid}")


def _load_arms(values: Sequence[Any]) -> list[StudyArm]:
    arms: list[StudyArm] = []
    for index, value in enumerate(values):
        item = _mapping(value, f"arms[{index}]")
        arm_id = item.get("id")
        description = item.get("description")
        mitigation = item.get("adapter_mitigation")
        if not isinstance(arm_id, str) or not arm_id.strip():
            raise ValueError(f"arms[{index}].id must be a non-empty string")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"arms[{index}].description must be a non-empty string")
        if mitigation not in {"none", "authority-checkpoint"}:
            raise ValueError(
                f"arms[{index}].adapter_mitigation must be 'none' or 'authority-checkpoint'"
            )
        arms.append(StudyArm(arm_id, description, mitigation))
    _reject_duplicate_ids([arm.id for arm in arms], "arms")
    return arms


def _load_models(values: Sequence[Any]) -> list[StudyModel]:
    models: list[StudyModel] = []
    for index, value in enumerate(values):
        item = _mapping(value, f"models[{index}]")
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError(f"models[{index}].id must be a non-empty string")
        models.append(
            StudyModel(
                model_id,
                _decimal(
                    item.get("input_per_million_usd"),
                    f"models[{index}].input_per_million_usd",
                ),
                _decimal(
                    item.get("output_per_million_usd"),
                    f"models[{index}].output_per_million_usd",
                ),
            )
        )
    _reject_duplicate_ids([model.id for model in models], "models")
    return models


def _reject_duplicate_ids(values: Sequence[str], name: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{name} cannot contain duplicate ids")


def compile_study_plan(path: str | Path) -> dict[str, Any]:
    """Compile a study specification into a deterministic protocol lock."""

    study = load_study(path)
    scenario_files = sorted(study.scenario_root.rglob("*.yaml"))
    if not scenario_files:
        raise ValueError(f"no scenarios found under {study.scenario_root}")
    scenarios: list[dict[str, str]] = []
    for scenario_path in scenario_files:
        scenario = load_scenario(scenario_path)
        scenarios.append(
            {
                "id": scenario.id,
                "version": scenario.version,
                "path": scenario_path.relative_to(study.scenario_root.parent).as_posix(),
                "sha256": hashlib.sha256(scenario_path.read_bytes()).hexdigest(),
            }
        )
    scenario_ids = [item["id"] for item in scenarios]
    _reject_duplicate_ids(scenario_ids, "scenarios")

    conditions = tuple(
        TrajectoryCondition(position, pressure, provenance)
        for position, pressure, provenance in product(
            study.positions, study.pressure_levels, study.provenance_modes
        )
    )
    control_values = (False, True) if study.paired_clean_controls else (False,)
    jobs: list[tuple[str, str, str, bool, str, int]] = []
    block_order: list[str] = []
    for model in study.models:
        for arm in study.arms:
            block_order.append(f"{model.id}|{arm.id}")
            block_jobs = [
                (
                    model.id,
                    arm.id,
                    scenario_id,
                    control,
                    condition.id,
                    trial,
                )
                for scenario_id in scenario_ids
                for control in control_values
                for condition in conditions
                for trial in range(study.trials_per_cell)
            ]
            block_jobs.sort(
                key=lambda job: authorization_decay_order_key(
                    study.seed,
                    f"{job[2]}{'-NC' if job[3] else ''}",
                    job[3],
                    job[4],
                    job[5],
                )
            )
            jobs.extend(block_jobs)
    job_ids = ["|".join(map(str, job)) for job in jobs]
    schedule_digest = hashlib.sha256("\n".join(job_ids).encode()).hexdigest()
    stopping_rule = _mapping(study.raw["stopping_rule"], "stopping_rule")
    declared_cases = stopping_rule.get("planned_cases")
    if declared_cases != len(jobs):
        raise ValueError(
            f"stopping_rule.planned_cases is {declared_cases}, but the design compiles to "
            f"{len(jobs)} cases"
        )

    cases_per_model = len(jobs) // len(study.models)
    model_costs: list[dict[str, Any]] = []
    base_cost = Decimal("0")
    for model in study.models:
        input_tokens = cases_per_model * study.input_tokens_per_case
        output_tokens = cases_per_model * study.output_tokens_per_case
        cost = (
            Decimal(input_tokens) * model.input_per_million_usd
            + Decimal(output_tokens) * model.output_per_million_usd
        ) / _MILLION
        base_cost += cost
        model_costs.append(
            {
                "model": model.id,
                "cases": cases_per_model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_per_million_usd": _money(model.input_per_million_usd),
                "output_per_million_usd": _money(model.output_per_million_usd),
                "estimated_cost_usd": _money(cost),
            }
        )
    reserve_cost = base_cost * study.reserve_fraction
    planned_cost = base_cost + reserve_cost
    requested_credits = Decimal(math.ceil(planned_cost))
    within_cap = requested_credits <= study.funding_cap_usd

    config_hash = hashlib.sha256(study.path.read_bytes()).hexdigest()
    lock_material = {
        "study_specification_sha256": config_hash,
        "scenario_manifest": scenarios,
        "schedule_sha256": schedule_digest,
        "job_count": len(jobs),
    }
    return {
        "artifact_type": "boundarybench_preregistered_study_plan",
        "boundarybench_version": __version__,
        "study_version": str(study.raw["study_version"]),
        "status": "preregistered",
        "title": study.title,
        "protocol_lock_sha256": _digest(lock_material),
        "inputs": lock_material,
        "design": {
            "primary_scenarios": len(scenarios),
            "paired_clean_controls": len(scenarios),
            "factorial_cells": len(conditions),
            "trials_per_cell": study.trials_per_cell,
            "models": len(study.models),
            "model_ids": [model.id for model in study.models],
            "arms": len(study.arms),
            "arm_ids": [arm.id for arm in study.arms],
            "cases_per_model_arm": len(scenarios)
            * len(control_values)
            * len(conditions)
            * study.trials_per_cell,
            "total_cases": len(jobs),
            "seed": study.seed,
        },
        "randomization": {
            "method": (
                "Declared model-arm blocks with SHA256 ordering over the seed and case "
                "identity inside each block"
            ),
            "block_order": block_order,
            "schedule_sha256": schedule_digest,
            "first_jobs": job_ids[:10],
        },
        "resource_plan": {
            "price_basis_date": str(study.raw.get("price_basis_date")),
            "token_budget_per_case": {
                "input_tokens": study.input_tokens_per_case,
                "output_tokens": study.output_tokens_per_case,
            },
            "models": model_costs,
            "base_estimated_cost_usd": _money(base_cost),
            "replication_reserve_fraction": str(study.reserve_fraction),
            "replication_reserve_usd": _money(reserve_cost),
            "planned_cost_usd": _money(planned_cost),
            "requested_credits_usd": _money(requested_credits),
            "funding_cap_usd": _money(study.funding_cap_usd),
            "within_funding_cap": within_cap,
            "headroom_usd": _money(study.funding_cap_usd - requested_credits),
        },
        "commitments": {
            "research_questions": list(study.raw["research_questions"]),
            "hypotheses": list(study.raw["hypotheses"]),
            "analysis": dict(study.raw["analysis"]),
            "exclusions": list(study.raw["exclusions"]),
            "stopping_rule": dict(stopping_rule),
            "responsible_research": dict(study.raw["responsible_research"]),
        },
    }


def write_study_plan(path: str | Path, output: str | Path) -> dict[str, Any]:
    """Compile and write a canonical JSON study plan."""

    plan = compile_study_plan(path)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return plan


__all__ = ["StudySpecification", "compile_study_plan", "load_study", "write_study_plan"]
