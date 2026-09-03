"""Authorization primitives for BoundaryBench.

Policy evaluation is fail-closed: an operation is allowed only when an allow
rule matches, and any matching deny rule takes precedence.  File targets are
relative canonical POSIX paths.  Network targets are exact normalized
destinations; this intentionally does not infer subdomains or default ports.
"""

from __future__ import annotations

import fnmatch
import ipaddress
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit


class Operation(StrEnum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"


class Effect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


_DRIVE_PATH = re.compile(r"^[A-Za-z]:")
_GLOB_CHARS = frozenset("*?[")


def canonicalize_path(value: str, *, pattern: bool = False) -> str:
    """Canonicalize a relative path, rejecting traversal and absolute forms.

    ``pattern=True`` permits ``*`` and ``**`` path-segment globs for policy
    rules.  Request targets are always concrete paths and must use the default
    ``pattern=False`` behavior.
    """

    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a non-empty string")
    path = value.strip()
    if "\x00" in path:
        raise ValueError("path must not contain NUL")
    if "\\" in path or path.startswith("/") or path.startswith("~") or _DRIVE_PATH.match(path):
        raise ValueError("path must be relative and use POSIX separators")
    segments = path.split("/")
    if any(segment == ".." for segment in segments):
        raise ValueError("path traversal '..' is not allowed")
    if not pattern and any(char in path for char in _GLOB_CHARS):
        raise ValueError("request path must be concrete")
    normalized = [segment for segment in segments if segment not in {"", "."}]
    if not normalized or any(segment == ".." for segment in normalized):
        raise ValueError("path must identify a relative location")
    return "/".join(normalized)


def _normalize_host(host: str) -> str:
    host = host.strip().lower().rstrip(".")
    if not host:
        raise ValueError("network destination must include a host")
    if any(char.isspace() for char in host) or "@" in host:
        raise ValueError("network destination host is invalid")
    if host.startswith("[") and host.endswith("]"):
        try:
            return f"[{ipaddress.IPv6Address(host[1:-1])}]"
        except ValueError as exc:
            raise ValueError("network destination contains an invalid IPv6 host") from exc
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        if ":" in host or "/" in host or "*" in host:
            raise ValueError("network destination host is invalid") from None
        labels = host.split(".")
        if any(
            not label
            or not re.fullmatch(r"[a-z0-9-]+", label)
            or label.startswith("-")
            or label.endswith("-")
            for label in labels
        ):
            raise ValueError("network destination host is invalid") from None
        try:
            return host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("network destination host is invalid") from exc


def canonicalize_destination(value: str) -> str:
    """Normalize an exact ``host[:port]`` or ``scheme://host[:port]`` target."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("network destination must be a non-empty string")
    destination = value.strip()
    if any(char in destination for char in "*?[]"):
        raise ValueError("network destination matching is exact; wildcards are not allowed")
    if "\x00" in destination or any(char.isspace() for char in destination):
        raise ValueError("network destination must not contain whitespace or NUL")
    has_scheme = "://" in destination
    if has_scheme:
        parsed = urlsplit(destination)
        if (
            not parsed.scheme
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError(
                "network destination must contain only scheme, host, and optional port"
            )
        scheme = parsed.scheme.lower()
        authority = parsed.netloc
    else:
        scheme = ""
        authority = destination
    if not authority:
        raise ValueError("network destination must include a host")
    try:
        host = parsed.hostname if has_scheme else None
        port = parsed.port if has_scheme else None
    except ValueError as exc:
        raise ValueError("network destination port is invalid") from exc
    if not has_scheme:
        if authority.startswith("["):
            closing = authority.find("]")
            if closing < 0:
                raise ValueError("network destination IPv6 host is invalid")
            host = authority[1:closing]
            suffix = authority[closing + 1 :]
            if suffix:
                if not suffix.startswith(":") or not suffix[1:].isdigit():
                    raise ValueError("network destination port is invalid")
                port = int(suffix[1:])
        elif authority.count(":") == 1:
            possible_host, possible_port = authority.rsplit(":", 1)
            if possible_port.isdigit():
                host, port = possible_host, int(possible_port)
            else:
                raise ValueError("network destination port is invalid")
        else:
            host = authority
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("network destination port must be between 1 and 65535")
    normalized = _normalize_host(host or "")
    prefix = f"{scheme}://" if scheme else ""
    port_suffix = f":{port}" if port is not None else ""
    return f"{prefix}{normalized}{port_suffix}"


def _path_pattern_matches(pattern: str, target: str) -> bool:
    pattern_parts = pattern.split("/")
    target_parts = target.split("/")

    def match(pattern_index: int, target_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return target_index == len(target_parts)
        part = pattern_parts[pattern_index]
        if part == "**":
            return match(pattern_index + 1, target_index) or (
                target_index < len(target_parts) and match(pattern_index, target_index + 1)
            )
        return (
            target_index < len(target_parts)
            and fnmatch.fnmatchcase(target_parts[target_index], part)
            and match(pattern_index + 1, target_index + 1)
        )

    return match(0, 0)


@dataclass(frozen=True)
class AuthorizationRule:
    """One allow or deny rule over one operation and one or more targets."""

    id: str
    effect: Effect
    operation: Operation
    targets: tuple[str, ...]
    extensions: Mapping[str, Any] = field(default_factory=dict)

    def matches(self, operation: Operation, canonical_target: str) -> bool:
        if self.operation is not operation:
            return False
        if operation is Operation.NETWORK:
            return canonical_target in self.targets
        return any(_path_pattern_matches(pattern, canonical_target) for pattern in self.targets)

    def to_mapping(self) -> dict[str, Any]:
        return {
            **dict(self.extensions),
            "id": self.id,
            "effect": self.effect.value,
            "operation": self.operation.value,
            "targets": list(self.targets),
        }


@dataclass(frozen=True)
class Decision:
    """An immutable authorization result suitable for instrumentation."""

    allowed: bool
    operation: Operation
    target: str
    canonical_target: str | None
    effect: Effect
    reason: str
    matched_rule_id: str | None = None
    matched_rule_ids: tuple[str, ...] = ()

    @property
    def authorized(self) -> bool:
        return self.allowed

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "authorized": self.authorized,
            "operation": self.operation.value,
            "target": self.target,
            "canonical_target": self.canonical_target,
            "effect": self.effect.value,
            "reason": self.reason,
            "matched_rule_id": self.matched_rule_id,
            "matched_rule_ids": list(self.matched_rule_ids),
        }


@dataclass(frozen=True)
class Policy:
    """Fail-closed policy with explicit deny precedence."""

    rules: tuple[AuthorizationRule, ...] = ()
    extensions: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_authority(cls, authority: Any) -> Policy:
        """Build core-operation rules from a declarative authority section.

        The scenario corpus uses synthetic ``/workspace/...`` resources.  The
        policy model stores the relative portion so it can apply the same
        canonical path checks as sandbox requests.  Authority actions outside
        read/write/execute/network (for example ``disclose``) remain valid
        scenario metadata but are not silently treated as filesystem access.
        """

        def value(name: str) -> Any:
            if isinstance(authority, Mapping):
                return authority.get(name, ())
            return getattr(authority, name, ())

        rules: list[AuthorizationRule] = []
        for effect_name, section_name in ((Effect.ALLOW, "grants"), (Effect.DENY, "denials")):
            for index, grant in enumerate(value(section_name) or ()):
                action = (
                    grant.get("action")
                    if isinstance(grant, Mapping)
                    else getattr(grant, "action", None)
                )
                resource = (
                    grant.get("resource")
                    if isinstance(grant, Mapping)
                    else getattr(grant, "resource", None)
                )
                if action not in {item.value for item in Operation}:
                    continue
                if not isinstance(resource, str):
                    raise ValueError(f"authority.{section_name}[{index}].resource must be a string")
                target = resource
                if action != Operation.NETWORK.value and target.startswith("/workspace/"):
                    target = target[len("/workspace/") :]
                canonical = (
                    canonicalize_destination(target)
                    if action == Operation.NETWORK.value
                    else canonicalize_path(target, pattern=True)
                )
                rules.append(
                    AuthorizationRule(
                        id=f"{section_name[:-1]}-{index + 1}",
                        effect=effect_name,
                        operation=Operation(action),
                        targets=(canonical,),
                    )
                )
        return cls(rules=tuple(rules))

    def decide(self, operation: Operation | str, target: str) -> Decision:
        """Return a decision without performing the requested operation."""

        operation = Operation(operation)
        try:
            canonical_target = (
                canonicalize_destination(target)
                if operation is Operation.NETWORK
                else canonicalize_path(target)
            )
        except ValueError as exc:
            return Decision(False, operation, target, None, Effect.DENY, f"invalid target: {exc}")
        matching = tuple(rule for rule in self.rules if rule.matches(operation, canonical_target))
        denies = tuple(rule for rule in matching if rule.effect is Effect.DENY)
        if denies:
            return Decision(
                False,
                operation,
                target,
                canonical_target,
                Effect.DENY,
                f"explicit deny rule {denies[0].id!r} matched",
                denies[0].id,
                tuple(rule.id for rule in matching),
            )
        allows = tuple(rule for rule in matching if rule.effect is Effect.ALLOW)
        if allows:
            return Decision(
                True,
                operation,
                target,
                canonical_target,
                Effect.ALLOW,
                f"explicit allow rule {allows[0].id!r} matched",
                allows[0].id,
                tuple(rule.id for rule in matching),
            )
        return Decision(
            False, operation, target, canonical_target, Effect.DENY, "no matching allow rule"
        )

    authorize = decide

    def to_mapping(self) -> dict[str, Any]:
        return {**dict(self.extensions), "rules": [rule.to_mapping() for rule in self.rules]}
