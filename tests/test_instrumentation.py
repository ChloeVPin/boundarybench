from __future__ import annotations

import json
from datetime import UTC, datetime

from boundarybench.instrumentation import EventLogger


def test_jsonl_schema_sequence_and_stable_timestamp(tmp_path):
    log_path = tmp_path / "events.jsonl"
    logger = EventLogger(
        log_path,
        run_id="run-1",
        scenario_id="scenario-1",
        clock=lambda: datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=UTC),
    )
    logger.record(
        event_type="tool.requested",
        operation="write",
        target="workspace:a.txt",
        authorization_decision="allow",
        outcome="requested",
        data_flow={"source": "agent", "destination": "workspace:a.txt"},
    )
    logger.record(
        event_type="tool.executed",
        operation="write",
        target="workspace:a.txt",
        authorization_decision="allow",
        outcome="executed",
    )
    lines = log_path.read_text().splitlines()
    assert [json.loads(line)["sequence"] for line in lines] == [1, 2]
    first = json.loads(lines[0])
    assert first["timestamp"] == "2026-01-02T03:04:05.678Z"
    assert first["run_id"] == "run-1"
    assert first["scenario_id"] == "scenario-1"
    assert set(first) == {
        "timestamp",
        "sequence",
        "run_id",
        "scenario_id",
        "event_type",
        "operation",
        "target",
        "authorization_decision",
        "outcome",
        "data_flow",
    }


def test_sensitive_event_metadata_is_redacted():
    logger = EventLogger(run_id="r", scenario_id="s")
    event = logger.record(
        event_type="tool.requested",
        operation="send",
        target="endpoint:test",
        authorization_decision="allow",
        outcome="requested",
        data_flow={"payload": "API_KEY=real-key", "safe": "SYNTHETIC_SECRET=fake"},
    )
    assert "real-key" not in event.to_json()
    assert "SYNTHETIC_SECRET=fake" in event.to_json()


def test_incidental_marker_text_does_not_disable_redaction():
    logger = EventLogger(run_id="r", scenario_id="s")
    event = logger.record(
        event_type="tool.requested",
        operation="send",
        target="endpoint:test",
        authorization_decision="allow",
        outcome="requested",
        data_flow={"payload": "API_KEY=latest-key"},
    )
    assert "latest-key" not in event.to_json()
