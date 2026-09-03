"""Typed scenario loading for BoundaryBench v0.1.

Scenarios are deliberately data-only.  The ``task`` and unknown fields are
preserved as mappings so a runner can add task types without adding parser
branches here.  The parser accepts PyYAML when installed and includes a small
safe fallback for the ordinary YAML subset used by local scenario files.
"""

from __future__ import annotations

import ast
import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .policy import (
    AuthorizationRule,
    Effect,
    Operation,
    Policy,
    canonicalize_destination,
    canonicalize_path,
)

SUPPORTED_VERSION = "0.1"
SUPPORTED_SCENARIO_VERSIONS = frozenset({"0.1", "0.1.0"})


@dataclass(frozen=True)
class ValidationIssue:
    """One validation problem, with a stable field path for tooling."""

    path: str
    message: str


class ScenarioValidationError(ValueError):
    """Raised when a scenario document is syntactically valid but invalid."""

    def __init__(
        self, message: str | None = None, *, issues: Sequence[ValidationIssue] = ()
    ) -> None:
        self.issues = tuple(issues)
        if message is None:
            message = "scenario validation failed"
        if self.issues:
            message = (
                message
                + ": "
                + "; ".join(f"{issue.path}: {issue.message}" for issue in self.issues)
            )
        super().__init__(message)


class ScenarioParseError(ScenarioValidationError):
    """Raised when a YAML scenario cannot be decoded."""


class _MiniYamlError(ValueError):
    pass


def _strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote:
            if quote == '"' and escaped:
                escaped = False
            elif quote == '"' and char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _split_inline(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote:
            if quote == '"' and escaped:
                escaped = False
            elif quote == '"' and char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    if quote or depth != 0:
        raise _MiniYamlError("unterminated quoted or inline value")
    parts.append(value[start:].strip())
    return parts


def _mini_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [_mini_scalar(item) for item in _split_inline(inner)]
    if value.startswith("{") and value.endswith("}"):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise _MiniYamlError("inline mappings must use JSON syntax") from exc
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value[:1] in {"'", '"'}:
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise _MiniYamlError("invalid quoted scalar") from exc
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _mini_yaml_load(text: str) -> Any:
    """Decode the small, safe YAML subset needed when PyYAML is absent."""

    rows: list[tuple[int, str, int]] = []
    for line_number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise _MiniYamlError(f"line {line_number}: tabs are not supported")
        content = _strip_yaml_comment(raw)
        if not content.strip():
            continue
        indent = len(content) - len(content.lstrip(" "))
        rows.append((indent, content.strip(), line_number))
    if not rows:
        return None

    def parse_block(position: int, indent: int) -> tuple[Any, int]:
        if position >= len(rows) or rows[position][0] != indent:
            raise _MiniYamlError("invalid indentation")
        is_list = rows[position][1].startswith("-")
        result: list[Any] = []
        mapping: dict[str, Any] = {}
        while position < len(rows):
            row_indent, content, line_number = rows[position]
            if row_indent < indent:
                break
            if row_indent != indent:
                raise _MiniYamlError(f"line {line_number}: inconsistent indentation")
            if is_list:
                if not content.startswith("-"):
                    raise _MiniYamlError(f"line {line_number}: expected list item")
                remainder = content[1:].strip()
                position += 1
                if not remainder:
                    if position >= len(rows) or rows[position][0] <= indent:
                        raise _MiniYamlError(f"line {line_number}: empty list item")
                    item, position = parse_block(position, rows[position][0])
                elif ":" in remainder and not remainder.startswith(("'", '"')):
                    key, raw_value = remainder.split(":", 1)
                    if not key.strip():
                        raise _MiniYamlError(f"line {line_number}: empty mapping key")
                    item = (
                        {key.strip(): _mini_scalar(raw_value)}
                        if raw_value.strip()
                        else {key.strip(): None}
                    )
                    if position < len(rows) and rows[position][0] > indent:
                        extra, position = parse_block(position, rows[position][0])
                        if not isinstance(extra, dict):
                            raise _MiniYamlError(
                                f"line {line_number}: list mapping continuation must be a mapping"
                            )
                        item.update(extra)
                else:
                    item = _mini_scalar(remainder)
                result.append(item)
            else:
                if content.startswith("-") or ":" not in content:
                    raise _MiniYamlError(f"line {line_number}: expected mapping entry")
                key, raw_value = content.split(":", 1)
                key = key.strip()
                if not key or key in mapping:
                    raise _MiniYamlError(f"line {line_number}: invalid or duplicate mapping key")
                position += 1
                if raw_value.strip():
                    mapping[key] = _mini_scalar(raw_value)
                elif position < len(rows) and rows[position][0] > indent:
                    child, position = parse_block(position, rows[position][0])
                    mapping[key] = child
                else:
                    mapping[key] = None
        return (result if is_list else mapping), position

    parsed, position = parse_block(0, rows[0][0])
    if position != len(rows):
        raise _MiniYamlError("trailing YAML content")
    return parsed


def _decode_yaml(text: str, source_name: str) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        try:
            return _mini_yaml_load(text)
        except (ValueError, TypeError) as exc:
            raise ScenarioParseError(
                f"could not parse YAML from {source_name}",
                issues=(ValidationIssue("$", str(exc)),),
            ) from exc
    try:
        return yaml.safe_load(text)
    except Exception as exc:  # PyYAML exposes several parser exception classes.
        raise ScenarioParseError(
            f"could not parse YAML from {source_name}",
            issues=(ValidationIssue("$", str(exc)),),
        ) from exc


def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _version(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    result = str(value).strip()
    return result or None


def _path(path: str, suffix: str) -> str:
    return f"{path}.{suffix}" if path else suffix


@dataclass(frozen=True)
class AuthorityEntry:
    """One declarative authority grant or denial."""

    action: str
    resource: str
    conditions: tuple[str, ...] = ()
    extensions: Mapping[str, Any] = field(default_factory=dict)

    def to_mapping(self) -> dict[str, Any]:
        result = {
            **_copy_mapping(self.extensions),
            "action": self.action,
            "resource": self.resource,
        }
        if self.conditions:
            result["conditions"] = list(self.conditions)
        return result


@dataclass(frozen=True)
class Authority:
    """Trusted grants and denials declared by a scenario."""

    principal: str
    grants: tuple[AuthorityEntry, ...]
    denials: tuple[AuthorityEntry, ...]
    decision_rule: str
    extensions: Mapping[str, Any] = field(default_factory=dict)

    def to_mapping(self) -> dict[str, Any]:
        return {
            **_copy_mapping(self.extensions),
            "principal": self.principal,
            "grants": [entry.to_mapping() for entry in self.grants],
            "denials": [entry.to_mapping() for entry in self.denials],
            "decision_rule": self.decision_rule,
        }


@dataclass(frozen=True)
class Scenario:
    """A validated, runner-independent benchmark scenario."""

    version: str
    id: str
    policy: Policy
    schema_version: str = SUPPORTED_VERSION
    name: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    difficulty: str | None = None
    summary: str | None = None
    authority: Authority | None = None
    provenance: Mapping[str, Any] | None = None
    attacker: Mapping[str, Any] | None = None
    fixture: Mapping[str, Any] | None = None
    task: Mapping[str, Any] | None = None
    expected_behavior: Mapping[str, Any] | None = None
    evaluation: Mapping[str, Any] | None = None
    negative_control: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    extensions: Mapping[str, Any] = field(default_factory=dict)

    def to_mapping(self) -> dict[str, Any]:
        """Return a JSON/YAML-friendly copy of the scenario."""

        result: dict[str, Any] = {
            **_copy_mapping(self.extensions),
            "version": self.version,
            "id": self.id,
            "policy": self.policy.to_mapping(),
        }
        if self.schema_version:
            result["schema_version"] = self.schema_version
        if self.name is not None:
            result["name"] = self.name
        for key in ("title", "category", "difficulty", "summary"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        if self.description is not None:
            result["description"] = self.description
        if self.authority is not None:
            result["authority"] = self.authority.to_mapping()
        for key in (
            "provenance",
            "attacker",
            "fixture",
            "task",
            "expected_behavior",
            "evaluation",
            "negative_control",
        ):
            value = getattr(self, key)
            if value is not None:
                result[key] = _copy_mapping(value)
        if self.metadata:
            result["metadata"] = _copy_mapping(self.metadata)
        return result

    @property
    def scenario_id(self) -> str:
        """Compatibility name used by sandbox adapters."""

        return self.id

    @property
    def prompt(self) -> str:
        """Return the declarative task request for provider-neutral runners."""

        return str(self.task.get("request", "")) if self.task else ""

    to_dict = to_mapping


def _parse_rules(
    value: Any,
    path: str,
    issues: list[ValidationIssue],
    *,
    default_effect: str | None = None,
    id_offset: int = 0,
) -> list[AuthorizationRule]:
    if not isinstance(value, list):
        issues.append(ValidationIssue(path, "must be a list of rule objects"))
        return []
    rules: list[AuthorizationRule] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, Mapping):
            issues.append(ValidationIssue(item_path, "must be a mapping"))
            continue
        raw = dict(item)
        effect = raw.pop("effect", default_effect)
        operation = raw.pop("operation", None)
        target_value = raw.pop("targets", raw.pop("target", None))
        if not _text(effect):
            issues.append(ValidationIssue(_path(item_path, "effect"), "must be 'allow' or 'deny'"))
        if not _text(operation) or operation not in {"read", "write", "execute", "network"}:
            issues.append(
                ValidationIssue(
                    _path(item_path, "operation"), "must be read, write, execute, or network"
                )
            )
        if isinstance(target_value, str):
            targets = [target_value]
        elif isinstance(target_value, list) and all(
            isinstance(target, str) for target in target_value
        ):
            targets = target_value
        else:
            targets = []
            issues.append(
                ValidationIssue(
                    _path(item_path, "targets"), "must be a non-empty string or list of strings"
                )
            )
        if not targets:
            issues.append(ValidationIssue(_path(item_path, "targets"), "must not be empty"))
        canonical_targets: list[str] = []
        for target_index, target in enumerate(targets):
            try:
                canonical_targets.append(
                    canonicalize_destination(target)
                    if operation == "network"
                    else canonicalize_path(target, pattern=True)
                )
            except ValueError as exc:
                issues.append(ValidationIssue(f"{item_path}.targets[{target_index}]", str(exc)))
        rule_id = raw.pop("id", None)
        if rule_id is not None and not _text(rule_id):
            issues.append(ValidationIssue(_path(item_path, "id"), "must be a non-empty string"))
        if (
            _text(effect)
            and effect in {"allow", "deny"}
            and _text(operation)
            and operation in {"read", "write", "execute", "network"}
            and canonical_targets
        ):
            rules.append(
                AuthorizationRule(
                    id=rule_id or f"rule-{id_offset + index + 1}",
                    effect=Effect(effect),
                    operation=Operation(operation),
                    targets=tuple(canonical_targets),
                    extensions=raw,
                )
            )
    return rules


def _parse_shorthand(
    value: Any, effect: str, path: str, issues: list[ValidationIssue], start_index: int
) -> list[AuthorizationRule]:
    if not isinstance(value, Mapping):
        issues.append(ValidationIssue(path, "must map operations to targets"))
        return []
    rules: list[AuthorizationRule] = []
    for operation, targets_value in value.items():
        operation_path = f"{path}.{operation}"
        if operation not in {"read", "write", "execute", "network"}:
            issues.append(ValidationIssue(operation_path, "unknown operation"))
            continue
        if isinstance(targets_value, Mapping):
            target_value = targets_value.get(
                "destinations" if operation == "network" else "paths",
                targets_value.get("targets", targets_value.get("target")),
            )
        else:
            target_value = targets_value
        rules.extend(
            _parse_rules(
                [{"effect": effect, "operation": operation, "targets": target_value}],
                operation_path,
                issues,
                default_effect=effect,
                id_offset=start_index,
            )
        )
    return rules


def _parse_authority(value: Any, issues: list[ValidationIssue]) -> Authority | None:
    if not isinstance(value, Mapping):
        issues.append(ValidationIssue("authority", "must be a mapping"))
        return None
    data = dict(value)
    principal = data.pop("principal", None)
    decision_rule = data.pop("decision_rule", None)
    if not _text(principal):
        issues.append(ValidationIssue("authority.principal", "must be a non-empty string"))
    if decision_rule != "trusted_grants_only":
        issues.append(
            ValidationIssue("authority.decision_rule", "must be 'trusted_grants_only' in v0.1")
        )

    def entries(name: str) -> tuple[AuthorityEntry, ...]:
        raw_entries = data.pop(name, None)
        if not isinstance(raw_entries, list) or not raw_entries:
            issues.append(ValidationIssue(f"authority.{name}", "must be a non-empty list"))
            return ()
        parsed: list[AuthorityEntry] = []
        for index, raw_entry in enumerate(raw_entries):
            entry_path = f"authority.{name}[{index}]"
            if not isinstance(raw_entry, Mapping):
                issues.append(ValidationIssue(entry_path, "must be a mapping"))
                continue
            entry = dict(raw_entry)
            action = entry.pop("action", None)
            resource = entry.pop("resource", None)
            conditions = entry.pop("conditions", ())
            if not _text(action):
                issues.append(ValidationIssue(f"{entry_path}.action", "must be a non-empty string"))
            if not _text(resource):
                issues.append(
                    ValidationIssue(f"{entry_path}.resource", "must be a non-empty string")
                )
            if not isinstance(conditions, list) or not all(_text(item) for item in conditions):
                issues.append(
                    ValidationIssue(
                        f"{entry_path}.conditions", "must be a list of non-empty strings"
                    )
                )
                conditions = ()
            if _text(action) and _text(resource):
                parsed.append(AuthorityEntry(action, resource, tuple(conditions), entry))
        return tuple(parsed)

    grants = entries("grants")
    denials = entries("denials")
    return Authority(principal or "", grants, denials, decision_rule or "", data)


def _validate_mapping_section(
    data: dict[str, Any], name: str, issues: list[ValidationIssue], *, required: bool
) -> Mapping[str, Any] | None:
    value = data.pop(name, None)
    if value is None:
        if required:
            issues.append(ValidationIssue(name, "is required and must be a mapping"))
        return None
    if not isinstance(value, Mapping):
        issues.append(ValidationIssue(name, "must be a mapping"))
        return None
    return _copy_mapping(value)


def _validate_scenario_sections(
    *,
    provenance: Mapping[str, Any] | None,
    attacker: Mapping[str, Any] | None,
    fixture: Mapping[str, Any] | None,
    task: Mapping[str, Any] | None,
    expected_behavior: Mapping[str, Any] | None,
    evaluation: Mapping[str, Any] | None,
    negative_control: Mapping[str, Any] | None,
    issues: list[ValidationIssue],
) -> None:
    """Validate stable declarative fields without interpreting task kinds."""

    if provenance is not None:
        for key in ("trusted_sources", "untrusted_sources"):
            sources = provenance.get(key)
            if not isinstance(sources, list):
                issues.append(ValidationIssue(f"provenance.{key}", "must be a list"))
            else:
                for index, source in enumerate(sources):
                    source_path = f"provenance.{key}[{index}]"
                    if not isinstance(source, Mapping):
                        issues.append(ValidationIssue(source_path, "must be a mapping"))
                        continue
                    for field_name in ("id", "kind", "description"):
                        if not _text(source.get(field_name)):
                            issues.append(
                                ValidationIssue(
                                    f"{source_path}.{field_name}", "must be a non-empty string"
                                )
                            )
                    if key == "untrusted_sources" and "payload" not in source:
                        issues.append(ValidationIssue(f"{source_path}.payload", "is required"))
        if provenance.get("precedence") != "trusted_authority_over_untrusted_content":
            issues.append(
                ValidationIssue(
                    "provenance.precedence", "must be trusted_authority_over_untrusted_content"
                )
            )

    if attacker is not None:
        for field_name in ("strategy", "entrypoint", "goal", "payload_source"):
            if not _text(attacker.get(field_name)):
                issues.append(
                    ValidationIssue(f"attacker.{field_name}", "must be a non-empty string")
                )
        untrusted = provenance.get("untrusted_sources", ()) if provenance else ()
        source_ids = {source.get("id") for source in untrusted if isinstance(source, Mapping)}
        if _text(attacker.get("payload_source")) and attacker["payload_source"] not in source_ids:
            issues.append(
                ValidationIssue("attacker.payload_source", "must refer to an untrusted source id")
            )

    if fixture is not None:
        if fixture.get("reset_policy") != "reset_before_each_run":
            issues.append(ValidationIssue("fixture.reset_policy", "must be reset_before_each_run"))
        if not isinstance(fixture.get("resources"), list):
            issues.append(ValidationIssue("fixture.resources", "must be a list"))

    if task is not None:
        if not _text(task.get("request")):
            issues.append(ValidationIssue("task.request", "must be a non-empty string"))
        for field_name in ("inputs", "allowed_interfaces"):
            value = task.get(field_name)
            if not isinstance(value, list) or not all(_text(item) for item in value):
                issues.append(
                    ValidationIssue(f"task.{field_name}", "must be a list of non-empty strings")
                )

    if expected_behavior is not None:
        if expected_behavior.get("decision") not in {"allow", "allow_and_constrain", "deny"}:
            issues.append(
                ValidationIssue(
                    "expected_behavior.decision", "must be allow, allow_and_constrain, or deny"
                )
            )
        for field_name in ("authorized_effects", "forbidden_effects", "explanation_requirements"):
            if not isinstance(expected_behavior.get(field_name), list):
                issues.append(ValidationIssue(f"expected_behavior.{field_name}", "must be a list"))

    if evaluation is not None:
        if evaluation.get("deterministic") is not True:
            issues.append(ValidationIssue("evaluation.deterministic", "must be true in v0.1"))
        if not isinstance(evaluation.get("oracle"), list):
            issues.append(ValidationIssue("evaluation.oracle", "must be a list"))
        record = evaluation.get("record")
        required_record = {
            "attempted_effects",
            "completed_effects",
            "tool_calls",
            "final_state",
            "agent_output",
        }
        if not isinstance(record, list) or not required_record.issubset(record):
            issues.append(
                ValidationIssue(
                    "evaluation.record",
                    "must include attempted_effects, completed_effects, tool_calls, "
                    "final_state, and agent_output",
                )
            )

    if negative_control is not None:
        for field_name in ("id", "input_change", "expected_behavior"):
            if not _text(negative_control.get(field_name)):
                issues.append(
                    ValidationIssue(f"negative_control.{field_name}", "must be a non-empty string")
                )
        if not isinstance(negative_control.get("oracle"), list):
            issues.append(ValidationIssue("negative_control.oracle", "must be a list"))


def parse_scenario(source: str | Mapping[str, Any], *, source_name: str = "<string>") -> Scenario:
    """Parse and validate one YAML document or already-decoded mapping."""

    document = _decode_yaml(source, source_name) if isinstance(source, str) else source
    issues: list[ValidationIssue] = []
    if not isinstance(document, Mapping):
        raise ScenarioValidationError(issues=(ValidationIssue("$", "scenario must be a mapping"),))
    data = dict(document)
    schema_version = _version(data.pop("schema_version", None))
    version_value = data.pop("version", None)
    version = _version(version_value)
    scenario_id = data.pop("id", None)
    policy_data = data.pop("policy", data.pop("authorization", None))
    canonical_form = isinstance(policy_data, Mapping) and schema_version is None
    if schema_version is None:
        if canonical_form and version in SUPPORTED_SCENARIO_VERSIONS:
            schema_version = SUPPORTED_VERSION
        else:
            issues.append(ValidationIssue("schema_version", "is required and must be '0.1'"))
    elif schema_version != SUPPORTED_VERSION:
        issues.append(
            ValidationIssue(
                "schema_version",
                f"unsupported schema version {schema_version!r}; expected {SUPPORTED_VERSION!r}",
            )
        )
    if version is None:
        issues.append(
            ValidationIssue("version", "is required and must be a non-empty string or number")
        )
    elif version not in SUPPORTED_SCENARIO_VERSIONS:
        issues.append(
            ValidationIssue(
                "version", f"unsupported scenario version {version!r}; expected 0.1 or 0.1.0"
            )
        )
    if not _text(scenario_id):
        issues.append(ValidationIssue("id", "is required and must be a non-empty string"))
    if version == SUPPORTED_VERSION and canonical_form:
        # In the compact form, ``version`` is the schema version itself.
        version = SUPPORTED_VERSION

    policy: Policy | None = None
    if isinstance(policy_data, Mapping):
        policy = _parse_policy(policy_data, issues)
    elif policy_data is not None:
        issues.append(ValidationIssue("policy", "must be a mapping"))

    authority_value = data.pop("authority", None)
    authority = _parse_authority(authority_value, issues) if authority_value is not None else None
    if policy is None and authority is not None:
        try:
            policy = Policy.from_authority(authority)
        except ValueError as exc:
            issues.append(ValidationIssue("authority", str(exc)))
    if policy is None and not canonical_form:
        issues.append(ValidationIssue("policy", "or authority is required"))

    required_sections = not canonical_form
    provenance = _validate_mapping_section(data, "provenance", issues, required=required_sections)
    attacker = _validate_mapping_section(data, "attacker", issues, required=required_sections)
    fixture = _validate_mapping_section(data, "fixture", issues, required=required_sections)
    task = _validate_mapping_section(data, "task", issues, required=required_sections)
    expected_behavior = _validate_mapping_section(
        data, "expected_behavior", issues, required=required_sections
    )
    evaluation = _validate_mapping_section(data, "evaluation", issues, required=required_sections)
    negative_control = _validate_mapping_section(
        data, "negative_control", issues, required=required_sections
    )
    if required_sections:
        for _section_name, section_value in (
            ("provenance", provenance),
            ("attacker", attacker),
            ("fixture", fixture),
            ("task", task),
            ("expected_behavior", expected_behavior),
            ("evaluation", evaluation),
            ("negative_control", negative_control),
        ):
            if section_value is None:
                continue
        title = data.pop("title", None)
        category = data.pop("category", None)
        difficulty = data.pop("difficulty", None)
        summary = data.pop("summary", None)
        for name, value in (
            ("title", title),
            ("category", category),
            ("difficulty", difficulty),
            ("summary", summary),
        ):
            if not _text(value):
                issues.append(ValidationIssue(name, "is required and must be a non-empty string"))
        if category not in {"repository", "filesystem", "tools", "controls"}:
            issues.append(
                ValidationIssue("category", "must be repository, filesystem, tools, or controls")
            )
        if difficulty not in {"basic", "intermediate", "advanced"}:
            issues.append(ValidationIssue("difficulty", "must be basic, intermediate, or advanced"))
    else:
        title = data.pop("title", None)
        category = data.pop("category", None)
        difficulty = data.pop("difficulty", None)
        summary = data.pop("summary", None)

    name = data.pop("name", None)
    description = data.pop("description", None)
    metadata = data.pop("metadata", {})
    if name is not None and not isinstance(name, str):
        issues.append(ValidationIssue("name", "must be a string"))
    if description is not None and not isinstance(description, str):
        issues.append(ValidationIssue("description", "must be a string"))
    if not isinstance(metadata, Mapping):
        issues.append(ValidationIssue("metadata", "must be a mapping when provided"))
    if required_sections:
        _validate_scenario_sections(
            provenance=provenance,
            attacker=attacker,
            fixture=fixture,
            task=task,
            expected_behavior=expected_behavior,
            evaluation=evaluation,
            negative_control=negative_control,
            issues=issues,
        )

    if issues:
        raise ScenarioValidationError(issues=issues)
    assert policy is not None and schema_version is not None and version is not None
    return Scenario(
        version=version,
        id=scenario_id,
        policy=policy,
        schema_version=schema_version,
        name=name,
        title=title,
        description=description,
        category=category,
        difficulty=difficulty,
        summary=summary,
        authority=authority,
        provenance=provenance,
        attacker=attacker,
        fixture=fixture,
        task=_copy_mapping(task) if isinstance(task, Mapping) else None,
        expected_behavior=expected_behavior,
        evaluation=evaluation,
        negative_control=negative_control,
        metadata=_copy_mapping(metadata),
        extensions=data,
    )


def load_scenario(path: str | Path) -> Scenario:
    """Read one local UTF-8 YAML scenario and validate it."""

    scenario_path = Path(path)
    try:
        text = scenario_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScenarioParseError(
            f"could not read scenario {scenario_path}",
            issues=(ValidationIssue("$", str(exc)),),
        ) from exc
    return parse_scenario(text, source_name=str(scenario_path))


def _parse_policy(data: Mapping[str, Any], issues: list[ValidationIssue]) -> Policy:
    raw = dict(data)
    rules: list[AuthorizationRule] = []
    explicit_rules = raw.pop("rules", None)
    if explicit_rules is not None:
        rules.extend(_parse_rules(explicit_rules, "policy.rules", issues))
    for effect in ("allow", "deny"):
        shorthand = raw.pop(effect, None)
        if shorthand is not None:
            rules.extend(
                _parse_shorthand(shorthand, effect, f"policy.{effect}", issues, len(rules))
            )
    seen: set[str] = set()
    for index, rule in enumerate(rules):
        if rule.id in seen:
            issues.append(
                ValidationIssue(f"policy.rules[{index}].id", f"duplicate rule id {rule.id!r}")
            )
        seen.add(rule.id)
    return Policy(rules=tuple(rules), extensions=raw)
