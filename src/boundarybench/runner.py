"""Offline benchmark execution and durable per-trial run directories."""

from __future__ import annotations

import fnmatch
import hashlib
import inspect
import json
import platform
import re
import sys
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Any


def _value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _scenario_mapping(scenario: Any) -> Mapping[str, Any]:
    if isinstance(scenario, Mapping):
        return scenario
    method = getattr(scenario, "to_mapping", None)
    if callable(method):
        value = method()
        if isinstance(value, Mapping):
            return value
    return {}


def _fixture_mapping(scenario: Any) -> Mapping[str, Any]:
    value = _value(scenario, "fixture")
    return value if isinstance(value, Mapping) else {}


def _fixture_location(path: str) -> tuple[str, str]:
    """Translate a synthetic absolute fixture path into a sandbox area/path."""

    if not isinstance(path, str) or not path:
        raise ValueError("fixture resource path must be a non-empty string")
    normalized = path.rstrip("/") or "/"
    prefixes = (
        ("/workspace/private", "protected"),
        ("/workspace/external", "external"),
        ("/workspace", "workspace"),
        ("/protected", "protected"),
        ("/external", "external"),
    )
    for prefix, area in prefixes:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            # Keep the logical ``private``/``external`` segment in the
            # relative path even when the physical area is isolated.  This
            # lets final-state evidence use the same synthetic path that the
            # scenario authority declares.
            base = (
                "/workspace/" if prefix in {"/workspace/private", "/workspace/external"} else prefix
            )
            relative = normalized[len(base) :].lstrip("/") or "."
            return area, relative
    raise ValueError(
        f"fixture path {path!r} is outside the synthetic namespace; "
        "expected /workspace, /protected, or /external"
    )


def _fixture_setup(
    scenario: Any,
) -> tuple[
    list[Any],
    list[tuple[str, str, str, str]],
    dict[str, str],
    dict[str, Any],
    dict[str, str],
]:
    """Extract declarative fixture files, links, documents, and stub state."""

    from .sandbox import ResourceDeclaration

    fixture = _fixture_mapping(scenario)
    declarations: list[ResourceDeclaration] = []
    links: list[tuple[str, str, str, str]] = []
    documents: dict[str, str] = {}
    tool_state: dict[str, Any] = {}
    initial_files: dict[str, str] = {}
    resources = fixture.get("resources", ())
    if not isinstance(resources, list):
        raise ValueError("fixture.resources must be a list")
    for resource in resources:
        if not isinstance(resource, Mapping):
            raise ValueError("each fixture resource must be a mapping")
        state = resource.get("state", {})
        if not isinstance(state, Mapping):
            raise ValueError("fixture resource state must be a mapping")
        raw_files = state.get("files")
        if raw_files is not None:
            if not isinstance(raw_files, list):
                raise ValueError("fixture resource state.files must be a list")
            for item in raw_files:
                if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                    raise ValueError("fixture files require a synthetic path")
                area, relative = _fixture_location(item["path"])
                content = item.get("content", "")
                if not isinstance(content, (str, bytes)):
                    raise ValueError(f"fixture file {item['path']!r} content must be text or bytes")
                declarations.append(ResourceDeclaration(area, relative, content))
                initial_files[item["path"]] = (
                    content.decode("utf-8", errors="replace")
                    if isinstance(content, bytes)
                    else content
                )
        raw_directories = state.get("directories")
        if raw_directories is not None:
            if not isinstance(raw_directories, list):
                raise ValueError("fixture resource state.directories must be a list")
            for item in raw_directories:
                raw_path = item.get("path") if isinstance(item, Mapping) else item
                area, relative = _fixture_location(raw_path)
                declarations.append(ResourceDeclaration(area, relative, is_dir=True))
        raw_links = state.get("links")
        if raw_links is not None:
            if not isinstance(raw_links, list):
                raise ValueError("fixture resource state.links must be a list")
            for item in raw_links:
                if not isinstance(item, Mapping):
                    raise ValueError("fixture links must be mappings")
                source = item.get("path")
                target = item.get("target")
                if not isinstance(source, str) or not isinstance(target, str):
                    raise ValueError("fixture links require synthetic path and target")
                source_area, source_relative = _fixture_location(source)
                target_area, target_relative = _fixture_location(target)
                links.append((source_area, source_relative, target_area, target_relative))
        for key in ("documents", "query_documents"):
            values = state.get(key)
            if isinstance(values, Mapping):
                for endpoint, document in values.items():
                    if not isinstance(endpoint, str) or not isinstance(document, str):
                        raise ValueError("stub documents require string endpoints and content")
                    documents[endpoint] = document
        stubs = state.get("tool_stubs")
        if isinstance(stubs, Mapping):
            tool_state.update(stubs)
        if resource.get("kind") == "tool_stubs":
            tool_state.update(state)
    return declarations, links, documents, tool_state, initial_files


def _materialize_links(sandbox: Any, links: list[tuple[str, str, str, str]]) -> None:
    for source_area, source_relative, target_area, target_relative in links:
        source = sandbox.resolve(source_area, source_relative)
        target = sandbox.resolve(target_area, target_relative, must_exist=True)
        if source.exists() or source.is_symlink():
            raise ValueError(f"fixture link source already exists: {source_relative}")
        source.parent.mkdir(parents=True, exist_ok=True)
        source.symlink_to(target, target.is_dir())


def _scenario_tool_policy(scenario: Any, tool_state: Mapping[str, Any]) -> Any:
    from .policy import Effect, Operation
    from .sandbox import AREAS
    from .tools import AuthorizationPolicy

    boundary = _value(scenario, "policy")
    rules = getattr(boundary, "rules", ()) if boundary is not None else ()
    allow_read = any(
        rule.effect is Effect.ALLOW and rule.operation is Operation.READ for rule in rules
    )
    allow_write = any(
        rule.effect is Effect.ALLOW and rule.operation is Operation.WRITE for rule in rules
    )
    allow_execute = any(
        rule.effect is Effect.ALLOW and rule.operation is Operation.EXECUTE for rule in rules
    )
    approved_commands: set[tuple[str, ...]] = set()
    for raw in tool_state.get("approved_commands", ()):
        if isinstance(raw, str):
            import shlex

            approved_commands.add(tuple(shlex.split(raw)))
        elif isinstance(raw, (list, tuple)) and all(isinstance(item, str) for item in raw):
            approved_commands.add(tuple(raw))
    query_endpoints = set(tool_state.get("query_endpoints", ()))
    send_endpoints = set(tool_state.get("send_endpoints", ()))
    query_endpoints.update(
        tool_state.get("documents", {}).keys()
        if isinstance(tool_state.get("documents"), Mapping)
        else ()
    )
    return AuthorizationPolicy(
        read_areas=frozenset(AREAS if allow_read else ()),
        write_areas=frozenset(AREAS if allow_write else ()),
        list_areas=frozenset(AREAS if allow_read else ()),
        approved_commands=frozenset(approved_commands if allow_execute else ()),
        query_endpoints=frozenset(str(item) for item in query_endpoints),
        send_endpoints=frozenset(str(item) for item in send_endpoints),
    )


def _normalize_tool_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(arguments)
    raw_path = normalized.get("path")
    if isinstance(raw_path, str) and raw_path.startswith(("/workspace", "/protected", "/external")):
        area, relative = _fixture_location(raw_path)
        normalized["area"] = area
        normalized["path"] = relative
    if "content" in normalized and "data" not in normalized:
        normalized["data"] = normalized.pop("content")
    if "payload" in normalized and "data" not in normalized:
        normalized["data"] = normalized.pop("payload")
    return normalized


def _response_value(response: Any, key: str, default: Any = None) -> Any:
    if isinstance(response, Mapping):
        return response.get(key, default)
    return getattr(response, key, default)


class BenchmarkRunner:
    """Run one scenario once or repeatedly using a provider-neutral agent."""

    def __init__(
        self,
        agent: Any,
        output_dir: str | Path,
        *,
        scenario_path: str | Path | None = None,
    ) -> None:
        self.agent = agent
        self.output_dir = Path(output_dir)
        self.scenario_path = Path(scenario_path) if scenario_path is not None else None

    def run(
        self,
        scenario: Any,
        *,
        trials: int = 1,
        seed: int = 0,
        model: str = "scripted",
        mitigation: str | None = None,
        attack_variant: str | None = None,
        position: str | int | None = None,
    ) -> list[Any]:
        if trials < 1:
            raise ValueError("trials must be at least 1")
        return [
            self.run_trial(
                scenario,
                trial=trial,
                seed=seed + trial,
                model=model,
                mitigation=mitigation,
                attack_variant=attack_variant,
                position=position,
            )
            for trial in range(trials)
        ]

    def run_scenario(self, scenario: Any, **kwargs: Any) -> list[Any]:
        """Alias for callers that prefer the explicit scenario terminology."""

        return self.run(scenario, **kwargs)

    def run_trial(
        self,
        scenario: Any,
        *,
        trial: int = 0,
        seed: int = 0,
        model: str = "scripted",
        mitigation: str | None = None,
        attack_variant: str | None = None,
        position: str | int | None = None,
    ) -> Any:
        # Local imports keep the runner usable as a small library and avoid
        # making scenario validation depend on execution concerns.
        from .agents import AgentRequest
        from .evaluation import Evaluator
        from .instrumentation import EventLogger
        from .results import RunResult
        from .sandbox import Sandbox
        from .tools import ControlledTools

        scenario_id = self._scenario_id(scenario)
        run_id = self._run_id(scenario_id, trial, seed, model, mitigation, attack_variant, position)
        run_dir = self._new_run_dir(run_id)
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        sandbox_dir = run_dir / "sandbox"
        started_at = datetime.now(UTC).isoformat()
        scenario_value = _scenario_mapping(scenario)
        if self.scenario_path is not None:
            scenario_hash = hashlib.sha256(self.scenario_path.read_bytes()).hexdigest()
        else:
            scenario_hash = hashlib.sha256(
                json.dumps(self._json_safe(scenario_value), sort_keys=True).encode("utf-8")
            ).hexdigest()
        tool_state: dict[str, Any] = {}
        logger = EventLogger(run_id=run_id, scenario_id=scenario_id)
        logger.record(
            event_type="run_started",
            operation="run",
            target=scenario_id,
            authorization_decision="not_applicable",
            outcome="started",
            data_flow={"sandbox_root": str(sandbox_dir)},
        )
        request = AgentRequest(
            scenario_id=scenario_id,
            prompt=self._scenario_prompt(scenario),
            seed=seed,
            model=model,
            mitigation=mitigation,
            attack_variant=attack_variant,
            position=position,
            trial=trial,
            metadata={
                "tool_names": [
                    "read",
                    "write",
                    "list",
                    "run_approved_command",
                    "query_doc",
                    "send_synthetic_data",
                    "send_email",
                    "create_issue",
                    "set_visibility",
                    "invite_member",
                    "pin_issue",
                ],
                "sandbox_root": str(sandbox_dir),
            },
        )
        manifest = {
            "boundarybench_version": "0.1.0",
            "run_id": run_id,
            "scenario_id": scenario_id,
            "scenario_version": _value(scenario, "version"),
            "schema_version": _value(scenario, "schema_version"),
            "scenario_hash": scenario_hash,
            "scenario_path": str(self.scenario_path) if self.scenario_path is not None else None,
            "trial": trial,
            "seed": seed,
            "model": model,
            "model_parameters": {},
            "provider": getattr(
                self.agent,
                "provider",
                "local-scripted" if model == "scripted" else "unregistered",
            ),
            "mitigation": mitigation,
            "mitigation_configuration": mitigation,
            "attack_variant": attack_variant,
            "position": position,
            "agent": getattr(self.agent, "name", type(self.agent).__name__),
            "agent_implementation": (
                f"{type(self.agent).__module__}.{type(self.agent).__qualname__}"
            ),
            "tool_configuration": {
                "network": "controlled endpoint records only",
                "approved_commands": tool_state.get("approved_commands", []),
            },
            "environment": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
            },
            "token_usage": None,
            "estimated_cost": None,
            "request": request.to_dict(),
            "started_at": started_at,
        }
        self._write_json(run_dir / "manifest.json", manifest)

        events: list[Mapping[str, Any]] = []
        errors: list[Mapping[str, Any]] = []
        response: Any = None
        evaluation_result: Any = None
        status = "error"
        sandbox: Any = None
        tools: Any = None
        try:
            declarations, links, documents, tool_state, initial_files = _fixture_setup(scenario)
            sandbox = Sandbox(
                {"scenario_id": scenario_id, "resources": declarations},
                root=sandbox_dir,
            )
            _materialize_links(sandbox, links)
            if documents:
                tool_state.setdefault("documents", documents)
            tools = ControlledTools(
                sandbox,
                logger=logger,
                policy=_scenario_tool_policy(scenario, tool_state),
                boundary_policy=_value(scenario, "policy"),
                documents=documents,
                stub_state=tool_state,
                run_id=run_id,
                scenario_id=scenario_id,
            )
            manifest["tool_configuration"]["approved_commands"] = tool_state.get(
                "approved_commands", []
            )
            manifest["tool_configuration"]["stubs"] = self._json_safe(tool_state)
            self._write_json(run_dir / "manifest.json", manifest)
            logger.record(
                event_type="message_sent",
                operation="agent",
                target=scenario_id,
                authorization_decision="not_applicable",
                outcome="sent",
                data_flow={"prompt": request.prompt},
            )
            response = self._invoke_agent(request, tools)
            logger.record(
                event_type="message_received",
                operation="agent",
                target=scenario_id,
                authorization_decision="not_applicable",
                outcome="received",
                data_flow={"completed": _response_value(response, "completed")},
            )
            raw_events = [
                self._event_mapping(event) for event in self._response_instrumentation(response)
            ]
            agent_event_types: set[str] = set()
            for raw_event in raw_events:
                events.append(raw_event)
                if self._is_tool_call(raw_event):
                    self._execute_tool_call(raw_event, tools, logger, errors)
                else:
                    agent_event_types.add(
                        str(
                            raw_event.get(
                                "type", raw_event.get("event", raw_event.get("kind", "agent_event"))
                            )
                        )
                    )
                    self._record_agent_event(raw_event, logger)
            events.extend(
                event.as_dict()
                for event in logger.events
                if event.event_type not in agent_event_types
            )
            self._write_artifacts(artifacts_dir, self._response_artifacts(response))
            oracle_result = self._evaluate_oracle(scenario, sandbox, tools, events, initial_files)
            declaration = self._scenario_declaration(scenario, request, response, events)
            if oracle_result["supported"]:
                if isinstance(declaration, Mapping):
                    declaration_mapping = dict(declaration)
                elif hasattr(declaration, "to_dict"):
                    declaration_mapping = declaration.to_dict()
                else:
                    declaration_mapping = {}
                if "task_completed" not in declaration_mapping:
                    observed_completion = bool(_response_value(response, "completed")) or any(
                        str(event.get("type", event.get("event", "")))
                        in {"task_completed", "task_complete", "completion"}
                        for event in events
                    )
                    declaration_mapping["task_completed"] = bool(
                        observed_completion and oracle_result["passed"]
                    )
                declaration = declaration_mapping
            semantic = (
                scenario.get("semantic_evaluator")
                if isinstance(scenario, Mapping)
                else getattr(scenario, "semantic_evaluator", None)
            )
            evaluation_result = Evaluator(semantic).evaluate(
                events,
                declaration,
                response=response,
            )
            evaluation_result = type(evaluation_result)(
                metrics=evaluation_result.metrics,
                evidence={
                    **evaluation_result.evidence,
                    "oracle": oracle_result,
                },
                semantic=evaluation_result.semantic,
                errors=evaluation_result.errors,
            )
            errors.extend(evaluation_result.errors)
            status = "error" if errors else "completed"
        except Exception as exc:
            errors.append(self._error_record("run", exc))
            logger.record(
                event_type="run_failed",
                operation="run",
                target=scenario_id,
                authorization_decision="not_applicable",
                outcome="failed",
                data_flow={"error_type": type(exc).__name__, "message": str(exc)},
            )
        finally:
            for error in errors:
                logger.record(
                    event_type="run_error",
                    operation="runner",
                    target=scenario_id,
                    authorization_decision="not_applicable",
                    outcome="error",
                    data_flow=error,
                )
            logger.record(
                event_type="run_finished",
                operation="run",
                target=scenario_id,
                authorization_decision="not_applicable",
                outcome="finished" if status == "completed" else "failed",
                data_flow={"status": status},
            )
            self._write_events(
                run_dir / "events.jsonl",
                [event.as_dict() for event in logger.events],
                [],
            )
        metrics = (
            evaluation_result.metrics if evaluation_result is not None else self._unknown_metrics()
        )
        result = RunResult(
            run_id=run_id,
            scenario_id=scenario_id,
            trial=trial,
            seed=seed,
            model=model,
            mitigation=mitigation,
            attack_variant=attack_variant,
            position=position,
            status=status,
            metrics=metrics,
            response=self._response_dict(response),
            errors=errors,
            evaluation={} if evaluation_result is None else evaluation_result.to_dict(),
        )
        response_metadata = _response_value(response, "metadata", {})
        if isinstance(response_metadata, Mapping):
            manifest["token_usage"] = response_metadata.get("token_usage")
            manifest["estimated_cost"] = response_metadata.get("estimated_cost")
        manifest["ended_at"] = datetime.now(UTC).isoformat()
        manifest["status"] = status
        manifest["outcome"] = result.to_dict()
        self._write_json(run_dir / "manifest.json", manifest)
        self._write_json(run_dir / "result.json", result.to_dict())
        return result

    def _invoke_agent(self, request: Any, tools: Any) -> Any:
        """Invoke an adapter, passing controlled tools only when supported."""

        run = getattr(self.agent, "run", None)
        if not callable(run):
            raise TypeError("agent must expose a callable run(request) method")
        try:
            parameters = inspect.signature(run).parameters.values()
            accepts_tools = any(
                parameter.name == "tools" or parameter.kind is parameter.VAR_KEYWORD
                for parameter in parameters
            )
        except (TypeError, ValueError):
            accepts_tools = False
        return run(request, tools=tools) if accepts_tools else run(request)

    @staticmethod
    def _is_tool_call(event: Mapping[str, Any]) -> bool:
        event_type = str(event.get("type", event.get("event", event.get("kind", "")))).lower()
        return event_type in {"tool_call", "tool_request", "tool_requested", "call_tool"} or any(
            key in event for key in ("tool", "tool_name")
        )

    @staticmethod
    def _record_agent_event(event: Mapping[str, Any], logger: Any) -> None:
        event_type = str(event.get("type", event.get("event", event.get("kind", "agent_event"))))
        normalized_type = event_type or "agent_event"
        if normalized_type in {"task_completed", "task_complete", "completion"}:
            outcome = "completed"
        elif normalized_type in {"run_failed", "failed"}:
            outcome = "failed"
        else:
            outcome = "observed"
        decision = str(
            event.get("authorization_decision", event.get("authorization", "not_applicable"))
        )
        if normalized_type in {"violation", "policy_violation", "authorization_violation"}:
            decision = "deny"
        reserved = {"type", "event", "kind", "target", "authorization_decision", "authorization"}
        data_flow = {key: value for key, value in event.items() if key not in reserved}
        logger.record(
            event_type=normalized_type,
            operation="agent",
            target=str(event.get("target", "trajectory")),
            authorization_decision=decision,
            outcome=outcome,
            data_flow=data_flow,
        )

    @staticmethod
    def _execute_tool_call(
        event: Mapping[str, Any],
        tools: Any,
        logger: Any,
        errors: list[Mapping[str, Any]],
    ) -> Any:
        from .sandbox import SandboxPathError, SecretMaterialError
        from .tools import AuthorizationDenied, ToolError

        tool_name = str(event.get("tool", event.get("tool_name", "")))
        arguments = event.get("arguments", event.get("args", {}))
        if not isinstance(arguments, Mapping):
            error = ValueError("tool call arguments must be a mapping")
            errors.append(BenchmarkRunner._error_record("tool_call", error))
            logger.record(
                event_type="agent.tool_result",
                operation="tool_call",
                target=tool_name or "unknown",
                authorization_decision="deny",
                outcome="invalid",
                data_flow={"error_type": type(error).__name__},
            )
            return None
        try:
            normalized = _normalize_tool_arguments(arguments)
        except Exception as exc:
            errors.append(BenchmarkRunner._error_record("tool_call", exc))
            logger.record(
                event_type="agent.tool_result",
                operation="tool_call",
                target=tool_name or "unknown",
                authorization_decision="deny",
                outcome="invalid",
                data_flow={"error_type": type(exc).__name__, "message": str(exc)},
            )
            return None
        methods = {
            "read": tools.read,
            "read_file": tools.read_file,
            "write": tools.write,
            "write_file": tools.write_file,
            "list": tools.list,
            "list_files": tools.list_files,
            "run_approved_command": tools.run_approved_command,
            "approved_command": tools.approved_command,
            "query_doc": tools.query_doc,
            "query_document": tools.query_document,
            "send_synthetic_data": tools.send_synthetic_data,
            "send_data": tools.send_data,
            "send_email": tools.send_email,
            "create_issue": tools.create_issue,
            "set_visibility": tools.set_visibility,
            "invite_member": tools.invite_member,
            "pin_issue": tools.pin_issue,
        }
        logger.record(
            event_type="agent.tool_requested",
            operation="tool_call",
            target=tool_name or "unknown",
            authorization_decision="pending",
            outcome="requested",
            data_flow={"arguments": normalized},
        )
        method = methods.get(tool_name)
        if method is None:
            error = ToolError(f"unsupported controlled tool: {tool_name!r}")
            errors.append(BenchmarkRunner._error_record("tool_call", error))
            logger.record(
                event_type="agent.tool_result",
                operation="tool_call",
                target=tool_name or "unknown",
                authorization_decision="deny",
                outcome="unsupported",
                data_flow={"error_type": type(error).__name__},
            )
            return None
        try:
            result = method(**normalized)
        except (
            AuthorizationDenied,
            ToolError,
            PermissionError,
            SandboxPathError,
            SecretMaterialError,
        ) as exc:
            # A denied or unsafe operation is evidence in the trace, not a
            # runner crash.  The tool has already emitted its terminal event.
            logger.record(
                event_type="agent.tool_result",
                operation=tool_name,
                target=tool_name,
                authorization_decision="deny",
                outcome="blocked",
                data_flow={"error_type": type(exc).__name__, "message": str(exc)},
            )
            return None
        except (OSError, ValueError) as exc:
            errors.append(BenchmarkRunner._error_record("tool_call", exc))
            logger.record(
                event_type="agent.tool_result",
                operation=tool_name,
                target=tool_name,
                authorization_decision="allow",
                outcome="failed",
                data_flow={"error_type": type(exc).__name__, "message": str(exc)},
            )
            return None
        logger.record(
            event_type="agent.tool_result",
            operation=tool_name,
            target=tool_name,
            authorization_decision="allow",
            outcome="completed",
            data_flow={"result": BenchmarkRunner._json_safe(result)},
        )
        return result

    @staticmethod
    def _synthetic_target(target: str) -> str:
        if target.startswith("workspace:"):
            return "/workspace/" + target.split(":", 1)[1].lstrip("/")
        if target.startswith("protected:"):
            return "/workspace/" + target.split(":", 1)[1].lstrip("/")
        if target.startswith("external:"):
            return "/external/" + target.split(":", 1)[1].lstrip("/")
        return target

    @staticmethod
    def _final_files(sandbox: Any) -> dict[str, str]:
        files: dict[str, str] = {}
        for area in ("workspace", "protected", "external"):
            root = sandbox.paths.for_area(area)
            prefix = "/external/" if area == "external" else "/workspace/"
            for path in root.rglob("*"):
                if path.is_symlink() or not path.is_file():
                    continue
                relative = path.relative_to(root).as_posix()
                files[prefix + relative] = path.read_text(encoding="utf-8", errors="replace")
        return files

    @staticmethod
    def _oracle_content(expected: Any) -> Any:
        if isinstance(expected, Mapping) and "content" in expected:
            return expected["content"]
        return expected

    @staticmethod
    def _completed_effect_targets(events: list[Mapping[str, Any]]) -> list[str]:
        targets: list[str] = []
        for event in events:
            event_type = str(event.get("event_type", event.get("type", event.get("event", ""))))
            outcome = str(event.get("outcome", "")).lower()
            if event_type == "tool.executed" and outcome in {"executed", "completed", "success"}:
                targets.append(BenchmarkRunner._synthetic_target(str(event.get("target", ""))))
        return targets

    def _evaluate_oracle(
        self,
        scenario: Any,
        sandbox: Any,
        tools: Any,
        events: list[Mapping[str, Any]],
        initial_files: Mapping[str, str],
    ) -> dict[str, Any]:
        evaluation = _value(scenario, "evaluation", {})
        oracle = evaluation.get("oracle") if isinstance(evaluation, Mapping) else None
        if not isinstance(oracle, list):
            return {"status": "unsupported", "supported": False, "passed": False, "assertions": []}
        final_files = self._final_files(sandbox)
        completed_targets = self._completed_effect_targets(events)
        assertions: list[dict[str, Any]] = []
        for assertion in oracle:
            if not isinstance(assertion, Mapping):
                assertions.append(
                    {
                        "id": "<invalid>",
                        "kind": "unknown",
                        "supported": False,
                        "passed": False,
                        "error": "oracle assertion must be a mapping",
                    }
                )
                continue
            assertion_id = str(assertion.get("id", "<missing-id>"))
            kind = str(assertion.get("kind", ""))
            target = str(assertion.get("target", ""))
            expected = assertion.get("expected", {})
            actual: Any = None
            supported = True
            passed = False
            error: str | None = None
            try:
                if kind in {"file_content", "file_unchanged"}:
                    actual = final_files.get(target)
                    expected_content = self._oracle_content(expected)
                    passed = actual == expected_content
                    if kind == "file_unchanged":
                        passed = passed and initial_files.get(target) == expected_content
                elif kind == "file_absent":
                    actual = target in final_files
                    expected_absent = (
                        expected.get("absent", True) if isinstance(expected, Mapping) else True
                    )
                    passed = actual == (not bool(expected_absent))
                elif kind == "effect_count":
                    expected_count = (
                        expected.get("completed") if isinstance(expected, Mapping) else expected
                    )
                    actual = sum(
                        fnmatch.fnmatchcase(effect_target, target)
                        for effect_target in completed_targets
                    )
                    passed = actual == expected_count
                elif kind == "repository_diff":
                    changed = sorted(
                        path
                        for path in set(initial_files) | set(final_files)
                        if initial_files.get(path) != final_files.get(path)
                    )
                    expected_changed = (
                        sorted(expected.get("changed_paths", []))
                        if isinstance(expected, Mapping)
                        else []
                    )
                    expected_unchanged = (
                        expected.get("unchanged_paths", []) if isinstance(expected, Mapping) else []
                    )
                    actual = {"changed_paths": changed}
                    unchanged = all(
                        final_files.get(path) == initial_files.get(path)
                        for path in expected_unchanged
                    )
                    passed = changed == expected_changed and unchanged
                elif kind == "tool_trace":
                    expected_calls = (
                        expected.get("calls") if isinstance(expected, Mapping) else None
                    )
                    expected_state = (
                        expected.get("final_state") if isinstance(expected, Mapping) else None
                    )
                    actual_call_records = [call.to_dict() for call in tools.stub_calls]
                    actual = {"calls": actual_call_records}
                    passed = True
                    if expected_calls is not None:
                        passed = actual_call_records == expected_calls
                    if expected_state is not None:
                        actual_state = {key: tools.stub_runtime.get(key) for key in expected_state}
                        actual["final_state"] = actual_state
                        passed = passed and actual_state == expected_state
                else:
                    supported = False
                    error = f"unsupported oracle kind: {kind!r}"
            except (OSError, TypeError, ValueError) as exc:
                error = str(exc)
                passed = False
            record = {
                "id": assertion_id,
                "kind": kind,
                "target": target,
                "supported": supported,
                "passed": passed,
                "expected": self._json_safe(expected),
                "actual": self._json_safe(actual),
            }
            if error:
                record["error"] = error
            assertions.append(record)
        supported = all(assertion["supported"] for assertion in assertions)
        passed = supported and all(assertion["passed"] for assertion in assertions)
        status = "passed" if passed else "failed" if supported else "unsupported"
        return {
            "status": status,
            "supported": supported,
            "passed": passed,
            "assertions": assertions,
        }

    def _new_run_dir(self, run_id: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        candidate = self.output_dir / run_id
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
        suffix = 1
        while True:
            alternate = self.output_dir / f"{run_id}-{suffix}"
            if not alternate.exists():
                alternate.mkdir(parents=True)
                return alternate
            suffix += 1

    @staticmethod
    def _scenario_id(scenario: Any) -> str:
        value = getattr(scenario, "id", None) or getattr(scenario, "scenario_id", None)
        if value is None and isinstance(scenario, Mapping):
            value = scenario.get("id", scenario.get("scenario_id"))
        return str(value or type(scenario).__name__)

    @staticmethod
    def _scenario_prompt(scenario: Any) -> str:
        if isinstance(scenario, Mapping):
            value = scenario.get("prompt", scenario.get("task", scenario.get("instruction", "")))
        else:
            value = getattr(scenario, "prompt", None)
            if value is None:
                task = getattr(scenario, "task", None)
                value = task.get("request", task) if isinstance(task, Mapping) else task
            if value is None:
                value = getattr(scenario, "instruction", "")
        if isinstance(value, Mapping):
            value = value.get("request", value.get("prompt", ""))
        return str(value() if callable(value) else value)

    @staticmethod
    def _scenario_declaration(
        scenario: Any, request: Any, response: Any, events: list[Mapping[str, Any]]
    ) -> Any:
        value = None
        if isinstance(scenario, Mapping):
            value = scenario.get(
                "evaluation_declaration", scenario.get("declaration", scenario.get("evaluation"))
            )
        else:
            value = getattr(
                scenario, "evaluation_declaration", getattr(scenario, "declaration", None)
            )
            if value is None:
                extensions = getattr(scenario, "extensions", {})
                if isinstance(extensions, Mapping):
                    value = extensions.get("evaluation")
        if callable(value):
            try:
                return value(request, response, events)
            except TypeError:
                return value()
        return value

    @staticmethod
    def _run_id(
        scenario_id: str,
        trial: int,
        seed: int,
        model: str,
        mitigation: str | None,
        attack_variant: str | None,
        position: str | int | None,
    ) -> str:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", scenario_id).strip("-") or "scenario"
        configuration = json.dumps(
            [scenario_id, trial, seed, model, mitigation, attack_variant, position],
            sort_keys=True,
            default=str,
        )
        digest = hashlib.sha256(configuration.encode("utf-8")).hexdigest()[:10]
        return f"{safe_id}-trial-{trial:04d}-{digest}"

    @staticmethod
    def _error_record(stage: str, exc: Exception) -> dict[str, str]:
        return {"stage": stage, "type": type(exc).__name__, "message": str(exc)}

    @staticmethod
    def _unknown_metrics() -> Any:
        from .evaluation import EvaluationMetrics

        return EvaluationMetrics()

    @staticmethod
    def _response_dict(response: Any) -> Mapping[str, Any] | None:
        if response is None:
            return None
        if hasattr(response, "to_dict"):
            return response.to_dict()
        if isinstance(response, Mapping):
            return dict(response)
        return {"text": str(response)}

    @staticmethod
    def _response_instrumentation(response: Any) -> list[Any]:
        if isinstance(response, Mapping):
            return list(response.get("instrumentation", response.get("events", [])) or [])
        return list(getattr(response, "instrumentation", []) or [])

    @staticmethod
    def _response_artifacts(response: Any) -> Mapping[str, Any]:
        if isinstance(response, Mapping):
            return response.get("artifacts", {}) or {}
        return getattr(response, "artifacts", {}) or {}

    @staticmethod
    def _event_mapping(event: Any) -> Mapping[str, Any]:
        if isinstance(event, Mapping):
            return dict(event)
        for method_name in ("as_dict", "to_dict"):
            method = getattr(event, method_name, None)
            if callable(method):
                value = method()
                if isinstance(value, Mapping):
                    return dict(value)
        raise TypeError("instrumentation events must be mappings or expose as_dict()/to_dict()")

    @staticmethod
    def _write_events(
        path: Path, events: list[Mapping[str, Any]], errors: list[Mapping[str, Any]]
    ) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(
                    json.dumps(BenchmarkRunner._json_safe(dict(event)), sort_keys=True) + "\n"
                )
            for error in errors:
                safe_error = BenchmarkRunner._json_safe(dict(error))
                handle.write(
                    json.dumps(
                        {
                            "type": "error",
                            "error_type": safe_error.get("type"),
                            **{key: value for key, value in safe_error.items() if key != "type"},
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(BenchmarkRunner._json_safe(value), handle, indent=2, sort_keys=True)
            handle.write("\n")

    @staticmethod
    def _write_artifacts(directory: Path, artifacts: Mapping[str, Any]) -> None:
        for name, value in artifacts.items():
            relative = Path(str(name))
            windows_relative = PureWindowsPath(str(name))
            if (
                relative.is_absolute()
                or windows_relative.is_absolute()
                or windows_relative.drive
                or ".." in relative.parts
                or ".." in windows_relative.parts
            ):
                raise ValueError(f"artifact path escapes artifacts directory: {name}")
            destination = directory / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(value, bytes):
                destination.write_bytes(value)
            elif isinstance(value, str):
                destination.write_text(value, encoding="utf-8")
            else:
                BenchmarkRunner._write_json(destination, value)

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None or isinstance(value, (int, float, bool)):
            return value
        if isinstance(value, str):
            from .instrumentation import redact_value

            return redact_value(value)
        if isinstance(value, bytes):
            from .instrumentation import redact_value

            text = value.decode("utf-8", errors="replace")
            safe_text = redact_value(text)
            return {
                "encoding": "utf-8",
                "data": safe_text,
            }
        if is_dataclass(value):
            return BenchmarkRunner._json_safe(asdict(value))
        if isinstance(value, Mapping):
            return {str(key): BenchmarkRunner._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [BenchmarkRunner._json_safe(item) for item in value]
        if hasattr(value, "to_dict"):
            return BenchmarkRunner._json_safe(value.to_dict())
        return str(value)


def run_scenario(
    scenario: Any = None,
    *,
    scenario_path: str | Path | None = None,
    output_root: str | Path = "runs",
    trials: int = 1,
    model: str = "scripted",
    model_name: str | None = None,
    seed: int | None = 0,
    mitigation: str | None = None,
    attack_variant: str | None = None,
    attack_position: str | int | None = None,
    position: str | int | None = None,
    script: Any = None,
    agent: Any = None,
) -> list[Any]:
    """Small library hook for integrations such as the optional CLI.

    Loading a scenario is deliberately lazy.  If no agent is supplied, the
    local scripted adapter is the only bundled execution path.  Without a
    script it emits no events, producing unknown metrics rather than pretending
    that a model ran.
    """

    source_path: Path | None = None
    if scenario is None or isinstance(scenario, (str, Path)):
        path = scenario_path or scenario
        if path is None:
            raise ValueError("scenario or scenario_path is required")
        source_path = Path(path)
        from . import scenarios

        scenario = scenarios.load_scenario(source_path)
    selected_model = model_name or model
    if agent is None:
        from .agents import ScriptedAgent

        if selected_model != "scripted":
            raise ValueError(
                f"model {selected_model!r} is not implemented; use model='scripted' "
                "or supply an Agent adapter"
            )
        agent = ScriptedAgent([] if script is None else script)
    selected_position = position if position is not None else attack_position
    return BenchmarkRunner(agent, output_root, scenario_path=source_path).run(
        scenario,
        trials=trials,
        seed=0 if seed is None else seed,
        model=selected_model,
        mitigation=mitigation,
        attack_variant=attack_variant,
        position=selected_position,
    )


__all__ = ["BenchmarkRunner", "run_scenario"]
