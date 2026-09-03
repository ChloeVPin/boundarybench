"""Agent interfaces and the deterministic local scripted adapter.

The benchmark intentionally knows nothing about model providers.  Providers can
implement :class:`Agent`; the scripted adapter is the only implementation
included in the core package.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AgentRequest:
    """The complete, provider-neutral input for one benchmark trial."""

    scenario_id: str
    prompt: str = ""
    seed: int = 0
    model: str = "scripted"
    mitigation: str | None = None
    attack_variant: str | None = None
    position: str | int | None = None
    trial: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "prompt": self.prompt,
            "seed": self.seed,
            "model": self.model,
            "mitigation": self.mitigation,
            "attack_variant": self.attack_variant,
            "position": self.position,
            "trial": self.trial,
            "metadata": dict(self.metadata),
        }


@dataclass
class AgentResponse:
    """Provider output plus locally captured instrumentation and artifacts."""

    text: str = ""
    instrumentation: list[Mapping[str, Any]] = field(default_factory=list)
    completed: bool | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "instrumentation": [self._event_dict(event) for event in self.instrumentation],
            "completed": self.completed,
            "artifacts": dict(self.artifacts),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def _event_dict(event: Any) -> dict[str, Any]:
        if isinstance(event, Mapping):
            return dict(event)
        for method_name in ("as_dict", "to_dict"):
            method = getattr(event, method_name, None)
            if callable(method):
                value = method()
                if isinstance(value, Mapping):
                    return dict(value)
        raise TypeError("instrumentation events must be mappings or expose as_dict()/to_dict()")


class Agent(Protocol):
    """Minimal adapter contract for a future local or hosted model provider."""

    @property
    def name(self) -> str: ...

    def run(self, request: AgentRequest) -> AgentResponse: ...


@dataclass(frozen=True)
class ScriptedStep:
    """One deterministic instrumentation event emitted by ``ScriptedAgent``."""

    event: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self, *, step: int) -> dict[str, Any]:
        value = dict(self.data)
        value.setdefault("type", self.event)
        value.setdefault("step", step)
        return value


class ScriptedAgent:
    """A deterministic, offline agent useful for fixtures and smoke tests.

    ``script`` is normally a sequence of event mappings, for example
    ``[{"type": "task_completed"}, {"type": "protected_resource_access",
    "authorized": False}]``.  A mapping may instead select a script by
    scenario id, attack variant, or ``"default"``.  A mapping containing
    ``events`` is treated as a response specification and may also provide
    ``text``, ``completed``, ``artifacts``, and ``metadata``.
    """

    def __init__(
        self,
        script: Sequence[Mapping[str, Any] | ScriptedStep] | Mapping[str, Any],
        *,
        name: str = "scripted",
        text: str = "",
        completed: bool | None = None,
        artifacts: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self._script = script
        self._name = name
        self._text = text
        self._completed = completed
        self._artifacts = dict(artifacts or {})
        self._metadata = dict(metadata or {})

    @property
    def name(self) -> str:
        return self._name

    def run(self, request: AgentRequest) -> AgentResponse:
        selected = self._select_script(request)
        response_options: Mapping[str, Any] = {}
        events_source: Any = selected
        if isinstance(selected, Mapping) and (
            "events" in selected
            or any(key in selected for key in ("text", "completed", "artifacts", "metadata"))
        ):
            response_options = selected
            events_source = selected.get("events", [])

        events = [self._event_dict(event, index) for index, event in enumerate(events_source)]
        return AgentResponse(
            text=str(response_options.get("text", self._text)),
            instrumentation=events,
            completed=response_options.get("completed", self._completed),
            artifacts={**self._artifacts, **dict(response_options.get("artifacts", {}))},
            metadata={**self._metadata, **dict(response_options.get("metadata", {}))},
        )

    def _select_script(self, request: AgentRequest) -> Any:
        if not isinstance(self._script, Mapping):
            return self._script
        if any(
            key in self._script for key in ("events", "text", "completed", "artifacts", "metadata")
        ):
            return self._script
        for key in (request.scenario_id, request.attack_variant, "default"):
            if key is not None and key in self._script:
                return self._script[key]
        return []

    @staticmethod
    def _event_dict(event: Mapping[str, Any] | ScriptedStep, index: int) -> dict[str, Any]:
        if isinstance(event, ScriptedStep):
            return event.to_dict(step=index)
        value = dict(event)
        if "type" not in value:
            if "event" in value:
                value["type"] = value["event"]
            elif "kind" in value:
                value["type"] = value["kind"]
        value.setdefault("step", index)
        return value


__all__ = ["Agent", "AgentRequest", "AgentResponse", "ScriptedAgent", "ScriptedStep"]
