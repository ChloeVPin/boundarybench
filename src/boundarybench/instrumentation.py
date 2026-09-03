"""Stable, append-only JSONL instrumentation for BoundaryBench tool calls."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REDACTED = "[REDACTED]"
_SECRET_ASSIGNMENT = re.compile(
    r"(?ix)((?:synthetic[_-]?)?(?:api[_-]?key|access[_-]?token|"
    r"auth(?:entication)?[_-]?token|password|passwd|private[_-]?key|"
    r"secret|token|bearer)[\"']?\s*[:=]\s*[\"']?)"
    r"([^\s,;\"'}]+)"
)
_SECRET_KEY = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|auth(?:entication)?[_-]?token|"
    r"password|passwd|private[_-]?key|secret|token|bearer)"
)
_SYNTHETIC_MARKER = re.compile(
    r"(?i)(?<![a-z0-9])(?:synthetic|fake|dummy|test|example|boundarybench)(?![a-z0-9])"
)


def _redact(value: Any) -> Any:
    if isinstance(value, str):

        def replace_secret(match: re.Match[str]) -> str:
            secret_value = match.group(2)
            if "synthetic" in match.group(1).lower() or _SYNTHETIC_MARKER.search(secret_value):
                return match.group(0)
            return match.group(1) + _REDACTED

        value = _SECRET_ASSIGNMENT.sub(replace_secret, value)
        if "-----BEGIN " in value and "PRIVATE KEY-----" in value:
            return _REDACTED
        return value
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            redacted[key_text] = _REDACTED if _SECRET_KEY.fullmatch(key_text) else _redact(item)
        return redacted
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def redact_value(value: Any) -> Any:
    """Return a storage-safe copy with credential-shaped values redacted."""

    return _redact(value)


def _timestamp(clock: Callable[[], datetime | str] | None) -> str:
    if clock is None:
        current = datetime.now(UTC)
    else:
        current = clock()
    if isinstance(current, str):
        return current
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class EventRecord:
    timestamp: str
    sequence: int
    run_id: str
    scenario_id: str
    event_type: str
    operation: str
    target: str
    authorization_decision: str
    outcome: str
    data_flow: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "event_type": self.event_type,
            "operation": self.operation,
            "target": self.target,
            "authorization_decision": self.authorization_decision,
            "outcome": self.outcome,
            "data_flow": dict(self.data_flow),
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EventLogger:
    """Collect events in memory and optionally append one stable JSON object per line."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        run_id: str = "run",
        scenario_id: str = "scenario",
        clock: Callable[[], datetime | str] | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.run_id = run_id
        self.scenario_id = scenario_id
        self._clock = clock
        self._sequence = 0
        self._events: list[EventRecord] = []
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch(exist_ok=True)

    @property
    def events(self) -> tuple[EventRecord, ...]:
        return tuple(self._events)

    def record(
        self,
        *,
        event_type: str,
        operation: str,
        target: str,
        authorization_decision: str,
        outcome: str,
        data_flow: Mapping[str, Any] | None = None,
    ) -> EventRecord:
        if not all(
            isinstance(value, str) and value
            for value in (event_type, operation, target, authorization_decision, outcome)
        ):
            raise ValueError("event fields must be non-empty strings")
        self._sequence += 1
        event = EventRecord(
            timestamp=_timestamp(self._clock),
            sequence=self._sequence,
            run_id=self.run_id,
            scenario_id=self.scenario_id,
            event_type=event_type,
            operation=operation,
            target=_redact(target),
            authorization_decision=authorization_decision,
            outcome=outcome,
            data_flow=_redact(data_flow or {}),
        )
        self._events.append(event)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(event.to_json() + "\n")
        return event

    def to_jsonl(self) -> str:
        return "".join(event.to_json() + "\n" for event in self._events)

    def write_jsonl(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.to_jsonl(), encoding="utf-8")


__all__ = ["EventLogger", "EventRecord", "redact_value"]
