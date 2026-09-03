from __future__ import annotations

import json

import pytest

from boundarybench.scenarios import load_scenario, negative_control_variant
from boundarybench.trajectory import (
    TrajectoryCondition,
    compile_trajectory,
    factorial_conditions,
)


def _scenario():
    return load_scenario("scenarios/controls/BB-CTRL-002-benign-same-scope.yaml")


def _attack_messages(trajectory):
    return [message for message in trajectory.messages if "repeat_index" in message]


def test_factorial_design_has_27_stable_unique_cells():
    conditions = tuple(factorial_conditions())

    assert len(conditions) == 27
    assert len({condition.id for condition in conditions}) == 27
    assert conditions[0].id == "ads-v0.2:position=early:pressure=1:provenance=explicit"


@pytest.mark.parametrize("position,expected_index", [("early", 2), ("middle", 4), ("late", 6)])
def test_position_controls_attack_insertion_without_changing_authority(position, expected_index):
    trajectory = compile_trajectory(_scenario(), TrajectoryCondition(position, 1, "explicit"))

    first_attack = next(
        index for index, message in enumerate(trajectory.messages) if "repeat_index" in message
    )
    assert first_attack == expected_index
    assert trajectory.authority_ledger["principal"] == "synthetic-user"


@pytest.mark.parametrize("pressure", [1, 3, 5])
def test_pressure_controls_exact_repetition_count(pressure):
    trajectory = compile_trajectory(
        _scenario(), TrajectoryCondition("middle", pressure, "explicit")
    )

    assert len(_attack_messages(trajectory)) == pressure


def test_provenance_modes_reveal_only_the_preregistered_cues():
    explicit = _attack_messages(
        compile_trajectory(_scenario(), TrajectoryCondition("early", 1, "explicit"))
    )[0]
    source_only = _attack_messages(
        compile_trajectory(_scenario(), TrajectoryCondition("early", 1, "source_only"))
    )[0]
    flattened = _attack_messages(
        compile_trajectory(_scenario(), TrajectoryCondition("early", 1, "flattened"))
    )[0]

    assert explicit["trust"] == "untrusted"
    assert explicit["source_id"] == "review-note"
    assert source_only["source_id"] == "review-note"
    assert source_only["source_kind"] == "review_comment"
    assert source_only["channel"] == "context"
    assert "trust" not in source_only
    assert "source_id" not in flattened
    assert "trust" not in flattened
    assert explicit["content"] == source_only["content"] == flattened["content"]


def test_trajectory_digest_is_deterministic_and_condition_sensitive():
    condition = TrajectoryCondition("late", 5, "flattened")
    first = compile_trajectory(_scenario(), condition)
    second = compile_trajectory(_scenario(), condition)
    different = compile_trajectory(_scenario(), TrajectoryCondition("early", 5, "flattened"))

    assert first.digest == second.digest
    assert first.digest != different.digest


def test_trajectory_exposes_no_evaluator_or_expected_answer_fields():
    trajectory = compile_trajectory(_scenario(), TrajectoryCondition("late", 3, "explicit"))
    encoded = json.dumps(trajectory.to_dict(), sort_keys=True).lower()

    assert '"oracle"' not in encoded
    assert '"evaluation"' not in encoded
    assert '"expected_behavior"' not in encoded
    assert '"authorized_effects"' not in encoded
    assert '"forbidden_effects"' not in encoded


def test_clean_control_changes_payload_but_preserves_task_and_authority():
    scenario = _scenario()
    control = negative_control_variant(scenario)
    condition = TrajectoryCondition("middle", 1, "explicit")
    primary_trajectory = compile_trajectory(scenario, condition)
    control_trajectory = compile_trajectory(control, condition)

    assert scenario.task == control.task
    assert primary_trajectory.authority_ledger == control_trajectory.authority_ledger
    assert (
        _attack_messages(primary_trajectory)[0]["content"]
        != _attack_messages(control_trajectory)[0]["content"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ("never", 1, "explicit"),
        ("early", 2, "explicit"),
        ("early", 1, "hidden"),
    ],
)
def test_invalid_conditions_are_rejected(arguments):
    with pytest.raises(ValueError):
        TrajectoryCondition(*arguments)
