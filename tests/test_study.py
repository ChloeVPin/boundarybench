from __future__ import annotations

import json

import jsonschema
import yaml

from boundarybench.cli import main
from boundarybench.study import compile_study_plan

STUDY_PATH = "experiments/openai-researcher-access-v0.3.yaml"


def test_preregistered_study_matches_schema_and_compiles_deterministically():
    specification = yaml.safe_load(open(STUDY_PATH, encoding="utf-8"))
    schema = json.load(open("schemas/study.schema.json", encoding="utf-8"))
    jsonschema.validate(specification, schema)

    first = compile_study_plan(STUDY_PATH)
    second = compile_study_plan(STUDY_PATH)

    assert first == second
    assert first["design"] == {
        "primary_scenarios": 11,
        "paired_clean_controls": 11,
        "factorial_cells": 27,
        "trials_per_cell": 10,
        "models": 3,
        "model_ids": ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"],
        "arms": 2,
        "arm_ids": ["baseline", "authority-checkpoint"],
        "cases_per_model_arm": 5940,
        "total_cases": 35640,
        "seed": 20260903,
    }
    assert first["resource_plan"]["base_estimated_cost_usd"] == "812.59"
    assert first["resource_plan"]["planned_cost_usd"] == "999.49"
    assert first["resource_plan"]["requested_credits_usd"] == "1000.00"
    assert first["resource_plan"]["within_funding_cap"] is True
    assert first["randomization"]["block_order"] == [
        "gpt-5.6-sol|baseline",
        "gpt-5.6-sol|authority-checkpoint",
        "gpt-5.6-terra|baseline",
        "gpt-5.6-terra|authority-checkpoint",
        "gpt-5.6-luna|baseline",
        "gpt-5.6-luna|authority-checkpoint",
    ]
    assert all(
        job.startswith("gpt-5.6-sol|baseline|") for job in first["randomization"]["first_jobs"]
    )
    assert len(first["inputs"]["scenario_manifest"]) == 11
    assert len(first["protocol_lock_sha256"]) == 64


def test_study_rejects_declared_case_count_that_disagrees_with_design(tmp_path):
    specification = yaml.safe_load(open(STUDY_PATH, encoding="utf-8"))
    specification["design"]["scenario_root"] = str((tmp_path.cwd() / "scenarios").resolve())
    specification["stopping_rule"]["planned_cases"] = 1
    path = tmp_path / "invalid-study.yaml"
    path.write_text(yaml.safe_dump(specification, sort_keys=False), encoding="utf-8")

    try:
        compile_study_plan(path)
    except ValueError as exc:
        assert "compiles to 35640 cases" in str(exc)
    else:
        raise AssertionError("expected inconsistent planned case count to fail")


def test_cli_writes_canonical_study_plan(tmp_path, capsys):
    output = tmp_path / "study-plan.json"

    assert main(["plan", STUDY_PATH, "--output", str(output)]) == 0
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert printed == written
    assert written["artifact_type"] == "boundarybench_preregistered_study_plan"
