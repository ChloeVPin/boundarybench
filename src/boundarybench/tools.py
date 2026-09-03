"""Authorization-preserving, non-networking tools for benchmark agents."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .instrumentation import EventLogger
from .sandbox import (
    AREAS,
    Area,
    Sandbox,
    SandboxPathError,
    SecretMaterialError,
    ensure_synthetic_only,
)


class ToolError(RuntimeError):
    """Base class for controlled tool failures."""


class AuthorizationDenied(ToolError, PermissionError):
    """Raised when a tool operation is not authorized by its policy."""


class EndpointDenied(AuthorizationDenied):
    """Raised when a query or send target is not allowlisted."""


@dataclass(frozen=True, slots=True)
class AuthorizationPolicy:
    """Explicit allowlists for filesystem areas, commands, and endpoints."""

    read_areas: frozenset[Area] = frozenset({"workspace"})
    write_areas: frozenset[Area] = frozenset({"workspace"})
    list_areas: frozenset[Area] = frozenset({"workspace"})
    approved_commands: frozenset[tuple[str, ...]] = frozenset()
    query_endpoints: frozenset[str] = frozenset()
    send_endpoints: frozenset[str] = frozenset()
    approved_moves: frozenset[tuple[str, str]] = frozenset()
    approved_extractions: frozenset[tuple[str, str]] = frozenset()
    archive_members: Mapping[str, tuple[Mapping[str, Any], ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("read_areas", "write_areas", "list_areas"):
            areas = getattr(self, name)
            if not set(areas).issubset(AREAS):
                raise ValueError(f"{name} contains an unknown sandbox area")

    @classmethod
    def allow_protected(cls) -> AuthorizationPolicy:
        return cls(
            read_areas=frozenset({"workspace", "protected"}),
            write_areas=frozenset({"workspace", "protected"}),
            list_areas=frozenset({"workspace", "protected"}),
        )


@dataclass(frozen=True, slots=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class DocumentQueryResult:
    endpoint: str
    query: str
    matches: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EndpointRecord:
    operation: str
    endpoint: str
    payload: Mapping[str, Any]
    synthetic_only: bool = True


@dataclass(frozen=True, slots=True)
class StubCallRecord:
    """One accepted or blocked call against a local tool stub."""

    interface: str
    arguments: Mapping[str, Any]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "interface": self.interface,
            "arguments": dict(self.arguments),
            "status": self.status,
        }


class ControlledTools:
    """Small tool facade that emits request and terminal events for every call."""

    _NETWORK_COMMANDS = frozenset({"curl", "wget", "nc", "ncat", "netcat", "ftp", "telnet", "ssh"})
    _INTERPRETERS = frozenset(
        {"bash", "env", "node", "perl", "python", "python3", "ruby", "sh", "zsh"}
    )
    _SAFE_COMMANDS = frozenset(
        {
            "cat",
            "cp",
            "diff",
            "echo",
            "false",
            "grep",
            "head",
            "ls",
            "mv",
            "printf",
            "pwd",
            "sed",
            "tail",
            "true",
            "wc",
        }
    )
    _FILESYSTEM_COMMANDS = _SAFE_COMMANDS

    def __init__(
        self,
        sandbox: Sandbox,
        *,
        logger: EventLogger | None = None,
        policy: AuthorizationPolicy | None = None,
        boundary_policy: Any | None = None,
        logical_roots: Mapping[Area, str] | None = None,
        documents: Mapping[str, str] | None = None,
        stub_state: Mapping[str, Any] | None = None,
        run_id: str = "run",
        scenario_id: str | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.logger = logger or EventLogger(
            run_id=run_id,
            scenario_id=scenario_id or sandbox.scenario_id,
        )
        self.policy = policy or AuthorizationPolicy()
        self.boundary_policy = boundary_policy
        self.logical_roots = {
            "workspace": "",
            "protected": "",
            "external": "",
            **dict(logical_roots or {}),
        }
        if set(self.logical_roots) - set(AREAS):
            raise ValueError("logical_roots contains an unknown sandbox area")
        self.documents = dict(documents or {})
        for endpoint, document in self.documents.items():
            ensure_synthetic_only(document, field=f"document {endpoint!r}")
        self.endpoint_records: list[EndpointRecord] = []
        self.stub_state = dict(stub_state or {})
        self.stub_calls: list[StubCallRecord] = []
        self.stub_runtime: dict[str, Any] = {
            "visibility": self.stub_state.get("initial_visibility"),
            "issue_count": self.stub_state.get("issue_count", 0),
            "invited_members": [],
            "pinned_issues": [],
        }

    def _logical_target(self, area: Area, path: str) -> str:
        root = self.logical_roots[area].strip("/")
        relative = str(path).strip("/")
        return "/".join(part for part in (root, relative) if part)

    @staticmethod
    def _synthetic_location(path: str) -> tuple[Area, str]:
        prefixes: tuple[tuple[str, Area], ...] = (
            ("/workspace/private", "protected"),
            ("/workspace/external", "external"),
            ("/workspace", "workspace"),
            ("/protected", "protected"),
            ("/external", "external"),
        )
        normalized = path.rstrip("/") or "/"
        for prefix, area in prefixes:
            if normalized == prefix or normalized.startswith(prefix + "/"):
                base = (
                    "/workspace/"
                    if prefix in {"/workspace/private", "/workspace/external"}
                    else prefix
                )
                return area, normalized[len(base) :].lstrip("/") or "."
        raise SandboxPathError(f"synthetic path is outside the sandbox namespace: {path!r}")

    def _boundary_allowed(
        self,
        operation: str,
        target: str,
        fallback: bool,
        *,
        area: Area | None = None,
    ) -> bool:
        """Apply the scenario policy when it explicitly models an operation."""

        if not fallback or self.boundary_policy is None:
            return fallback
        rules = getattr(self.boundary_policy, "rules", ())
        operation_value = getattr(operation, "value", operation)
        modeled = any(
            getattr(getattr(rule, "operation", None), "value", getattr(rule, "operation", None))
            == operation_value
            for rule in rules
        )
        if not modeled:
            return fallback
        logical_target = self._logical_target(area, target) if area is not None else target
        try:
            decision = self.boundary_policy.decide(operation_value, logical_target)
        except (TypeError, ValueError):
            return False
        return bool(getattr(decision, "allowed", False))

    def _request(
        self,
        operation: str,
        target: str,
        allowed: bool,
        data_flow: Mapping[str, Any] | None = None,
    ) -> None:
        self.logger.record(
            event_type="tool.requested",
            operation=operation,
            target=target,
            authorization_decision="allow" if allowed else "deny",
            outcome="requested",
            data_flow=data_flow,
        )

    def _denied(
        self,
        operation: str,
        target: str,
        outcome: str,
        data_flow: Mapping[str, Any] | None = None,
    ) -> None:
        self.logger.record(
            event_type="tool.denied",
            operation=operation,
            target=target,
            authorization_decision="deny",
            outcome=outcome,
            data_flow=data_flow,
        )

    def _executed(
        self,
        operation: str,
        target: str,
        data_flow: Mapping[str, Any] | None = None,
    ) -> None:
        self.logger.record(
            event_type="tool.executed",
            operation=operation,
            target=target,
            authorization_decision="allow",
            outcome="executed",
            data_flow=data_flow,
        )

    def _failed(
        self,
        operation: str,
        target: str,
        error: Exception,
        data_flow: Mapping[str, Any] | None = None,
    ) -> None:
        metadata = dict(data_flow or {})
        metadata["error_type"] = type(error).__name__
        self.logger.record(
            event_type="tool.failed",
            operation=operation,
            target=target,
            authorization_decision="allow",
            outcome="failed",
            data_flow=metadata,
        )

    @staticmethod
    def _area_target(area: Area, path: str) -> str:
        return f"{area}:{path or '.'}"

    def read(self, path: str, *, area: Area = "workspace") -> str:
        target = self._area_target(area, path)
        allowed = self._boundary_allowed("read", path, area in self.policy.read_areas, area=area)
        self._request("read", target, allowed)
        if not allowed:
            self._denied("read", target, "unauthorized")
            raise AuthorizationDenied(f"read is not authorized for {area}")
        try:
            value = self.sandbox.read_text(area, path)
            ensure_synthetic_only(value, field=f"read {path!r}")
        except SecretMaterialError:
            self._denied("read", target, "secret_rejected")
            raise
        except SandboxPathError:
            self._denied("read", target, "unsafe_path")
            raise
        except Exception as exc:
            self._failed("read", target, exc)
            raise
        self._executed(
            "read",
            target,
            {"source": target, "destination": "agent", "bytes": len(value.encode())},
        )
        return value

    def write(self, path: str, data: str | bytes, *, area: Area = "workspace") -> None:
        target = self._area_target(area, path)
        size = len(data.encode("utf-8") if isinstance(data, str) else data)
        allowed = self._boundary_allowed("write", path, area in self.policy.write_areas, area=area)
        self._request(
            "write",
            target,
            allowed,
            {"source": "agent", "destination": target, "bytes": size},
        )
        if not allowed:
            self._denied(
                "write", target, "unauthorized", {"source": "agent", "destination": target}
            )
            raise AuthorizationDenied(f"write is not authorized for {area}")
        try:
            ensure_synthetic_only(data, field=f"write {path!r}")
            content = data.encode("utf-8") if isinstance(data, str) else data
            self.sandbox.write_bytes(area, path, content)
        except SecretMaterialError:
            self._denied(
                "write", target, "secret_rejected", {"source": "agent", "destination": target}
            )
            raise
        except SandboxPathError:
            self._denied("write", target, "unsafe_path", {"source": "agent", "destination": target})
            raise
        except Exception as exc:
            self._failed("write", target, exc, {"source": "agent", "destination": target})
            raise
        self._executed("write", target, {"source": "agent", "destination": target, "bytes": size})

    def move(self, source: str, destination: str) -> None:
        """Move one file only when the exact synthetic path pair is delegated."""

        pair = (source, destination)
        target = f"{source} -> {destination}"
        allowed = pair in self.policy.approved_moves
        self._request("move", target, allowed, {"source": source, "destination": destination})
        if not allowed:
            self._denied("move", target, "unauthorized")
            raise AuthorizationDenied("move does not match the delegated path pair")
        try:
            source_area, source_relative = self._synthetic_location(source)
            destination_area, destination_relative = self._synthetic_location(destination)
            if source_area != destination_area:
                raise SandboxPathError("moves between sandbox areas are not allowed")
            source_path = self.sandbox.resolve(source_area, source_relative, must_exist=True)
            destination_path = self.sandbox.resolve(destination_area, destination_relative)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            self.sandbox.resolve(destination_area, destination_relative)
            shutil.move(source_path, destination_path)
        except SandboxPathError:
            self._denied("move", target, "unsafe_path")
            raise
        except Exception as exc:
            self._failed("move", target, exc)
            raise
        self._executed("move", target, {"source": source, "destination": destination})

    def extract_archive(self, archive: str, destination: str) -> Mapping[str, Any]:
        """Extract declarative archive members while rejecting unsafe member names."""

        pair = (archive, destination)
        target = f"{archive} -> {destination}"
        allowed = pair in self.policy.approved_extractions
        self._request(
            "extract_archive",
            target,
            allowed,
            {"source": archive, "destination": destination},
        )
        if not allowed:
            self._denied("extract_archive", target, "unauthorized")
            raise AuthorizationDenied("archive extraction does not match the approved path pair")
        extracted: list[str] = []
        rejected: list[str] = []
        try:
            archive_area, archive_relative = self._synthetic_location(archive)
            destination_area, destination_relative = self._synthetic_location(destination)
            self.sandbox.resolve(archive_area, archive_relative, must_exist=True)
            for member in self.policy.archive_members.get(archive, ()):
                name = member.get("name")
                content = member.get("content", "")
                if not isinstance(name, str) or not isinstance(content, (str, bytes)):
                    raise ValueError(
                        "archive members require string names and text or bytes content"
                    )
                member_path = PurePosixPath(name)
                windows_path = PureWindowsPath(name)
                if (
                    not name
                    or "\\" in name
                    or member_path.is_absolute()
                    or windows_path.is_absolute()
                    or windows_path.drive
                    or ".." in member_path.parts
                ):
                    rejected.append(name)
                    continue
                relative = str(PurePosixPath(destination_relative) / member_path)
                self.sandbox.write_bytes(
                    destination_area,
                    relative,
                    content.encode("utf-8") if isinstance(content, str) else content,
                )
                extracted.append(name)
        except (SandboxPathError, SecretMaterialError):
            self._denied("extract_archive", target, "unsafe_archive")
            raise
        except Exception as exc:
            self._failed("extract_archive", target, exc)
            raise
        result = {"extracted": extracted, "rejected": rejected}
        self._executed("extract_archive", target, result)
        return result

    def list(self, path: str = "", *, area: Area = "workspace") -> list[str]:
        target = self._area_target(area, path)
        allowed = self._boundary_allowed("read", path, area in self.policy.list_areas, area=area)
        self._request("list", target, allowed)
        if not allowed:
            self._denied("list", target, "unauthorized")
            raise AuthorizationDenied(f"list is not authorized for {area}")
        try:
            result = self.sandbox.list_names(area, path)
        except SandboxPathError:
            self._denied("list", target, "unsafe_path")
            raise
        except Exception as exc:
            self._failed("list", target, exc)
            raise
        self._executed(
            "list", target, {"source": target, "destination": "agent", "items": len(result)}
        )
        return result

    def run_approved_command(
        self,
        command: str | Sequence[str],
        *,
        cwd: str = "",
        timeout: float = 5.0,
    ) -> CommandResult:
        raw_command = command if isinstance(command, str) else " ".join(map(str, command))
        try:
            argv = tuple(shlex.split(command) if isinstance(command, str) else command)
        except ValueError:
            target = "command:" + raw_command
            self._request(
                "command", target, False, {"source": "agent", "destination": "sandbox-process"}
            )
            self._denied("command", target, "invalid_command")
            raise
        if not argv or not all(isinstance(item, str) and item for item in argv):
            target = "command:" + raw_command
            self._request(
                "command", target, False, {"source": "agent", "destination": "sandbox-process"}
            )
            self._denied("command", target, "invalid_command")
            raise ValueError("command must contain at least one non-empty argument")
        target = "command:" + " ".join(argv)
        command_name = argv[0].rsplit("/", 1)[-1]
        allowed = (
            argv in self.policy.approved_commands
            and command_name in self._SAFE_COMMANDS
            and "/" not in argv[0]
            and "\\" not in argv[0]
            and command_name not in self._NETWORK_COMMANDS
            and command_name not in self._INTERPRETERS
            and not Path(argv[0]).is_absolute()
            and not PureWindowsPath(argv[0]).is_absolute()
        )
        if allowed and self.boundary_policy is not None:
            rules = getattr(self.boundary_policy, "rules", ())
            if any(
                getattr(getattr(rule, "operation", None), "value", getattr(rule, "operation", None))
                == "execute"
                for rule in rules
            ):
                allowed = self._boundary_allowed(
                    "execute", cwd or "workspace", True, area="workspace"
                )
        self._request(
            "command", target, allowed, {"source": "agent", "destination": "sandbox-process"}
        )
        if not allowed:
            self._denied("command", target, "unauthorized")
            raise AuthorizationDenied("command is not approved or is network-capable")
        try:
            workdir = self.sandbox.resolve("workspace", cwd, must_exist=True)
            if not workdir.is_dir():
                raise NotADirectoryError(workdir)
            if command_name in self._FILESYSTEM_COMMANDS:
                for argument in argv[1:]:
                    if argument.startswith("-"):
                        option_value = argument.partition("=")[2]
                        if option_value and (
                            Path(option_value).is_absolute()
                            or PureWindowsPath(option_value).is_absolute()
                            or PureWindowsPath(option_value).drive
                        ):
                            raise SandboxPathError("command option refers to an absolute path")
                        continue
                    relative = str(Path(cwd) / argument) if cwd else argument
                    self.sandbox.resolve("workspace", relative)
            result = subprocess.run(
                argv,
                cwd=workdir,
                env={"PATH": "/usr/bin:/bin", "BOUNDARYBENCH_SANDBOX": "1"},
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
            ensure_synthetic_only(result.stdout, field="command stdout")
            ensure_synthetic_only(result.stderr, field="command stderr")
        except SecretMaterialError:
            self._denied(
                "command",
                target,
                "secret_rejected",
                {"source": "sandbox-process", "destination": "agent"},
            )
            raise
        except SandboxPathError:
            self._denied("command", target, "unsafe_path")
            raise
        except Exception as exc:
            self._failed("command", target, exc)
            raise
        self._executed("command", target, {"source": "sandbox-process", "destination": "agent"})
        return CommandResult(argv, result.returncode, result.stdout, result.stderr)

    def query_doc(self, endpoint: str, query: str = "") -> DocumentQueryResult:
        allowed = endpoint in self.policy.query_endpoints
        allowed = self._boundary_allowed("network", endpoint, allowed)
        target = f"endpoint:{endpoint}"
        self._request("query", target, allowed, {"source": "agent", "destination": endpoint})
        if not allowed:
            self._denied(
                "query", target, "unauthorized", {"source": "agent", "destination": endpoint}
            )
            raise EndpointDenied(f"query endpoint is not approved: {endpoint}")
        try:
            document = self.documents[endpoint]
            ensure_synthetic_only(query, field="document query")
            lines = tuple(line for line in document.splitlines() if not query or query in line)
            self.endpoint_records.append(EndpointRecord("query", endpoint, {"query": query}))
        except SecretMaterialError:
            self._denied(
                "query", target, "secret_rejected", {"source": "agent", "destination": endpoint}
            )
            raise
        except Exception as exc:
            self._failed("query", target, exc)
            raise
        self._executed(
            "query", target, {"source": endpoint, "destination": "agent", "matches": len(lines)}
        )
        return DocumentQueryResult(endpoint, query, lines)

    def send_synthetic_data(self, endpoint: str, payload: Mapping[str, Any]) -> EndpointRecord:
        allowed = endpoint in self.policy.send_endpoints
        allowed = self._boundary_allowed("network", endpoint, allowed)
        target = f"endpoint:{endpoint}"
        self._request("send", target, allowed, {"source": "agent", "destination": endpoint})
        if not allowed:
            self._denied(
                "send", target, "unauthorized", {"source": "agent", "destination": endpoint}
            )
            raise EndpointDenied(f"send endpoint is not approved: {endpoint}")
        try:
            ensure_synthetic_only(payload, field="endpoint payload")
            record = EndpointRecord("send", endpoint, dict(payload))
            self.endpoint_records.append(record)
        except SecretMaterialError:
            self._denied(
                "send", target, "secret_rejected", {"source": "agent", "destination": endpoint}
            )
            raise
        except Exception as exc:
            self._failed("send", target, exc)
            raise
        self._executed(
            "send",
            target,
            {"source": "agent", "destination": endpoint, "synthetic_only": True},
        )
        return record

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Sequence[str] | None = None,
    ) -> Mapping[str, Any]:
        """Record an email-like stub call without delivering anything."""

        arguments = {
            "to": to,
            "subject": subject,
            "body": body,
            "attachments": list(attachments or []),
        }
        configuration = self.stub_state.get("send_email", {})
        accepted = (
            isinstance(configuration, Mapping)
            and to == configuration.get("accepted_recipient")
            and subject == configuration.get("accepted_subject")
            and body == configuration.get("accepted_body")
            and arguments["attachments"] == list(configuration.get("accepted_attachments", []))
        )
        target = str(to)
        self._request("send_email", target, accepted, {"arguments": arguments})
        status = "accepted" if accepted else "denied"
        self.stub_calls.append(StubCallRecord("tools.send_email", arguments, status))
        if not accepted:
            self._denied("send_email", target, "unauthorized", {"arguments": arguments})
            raise AuthorizationDenied("email call does not match the synthetic stub allowlist")
        try:
            ensure_synthetic_only(arguments, field="email payload")
        except SecretMaterialError:
            self._denied("send_email", target, "secret_rejected", {"arguments": arguments})
            self.stub_calls[-1] = StubCallRecord("tools.send_email", arguments, "secret_rejected")
            raise
        self._executed("send_email", target, {"arguments": arguments, "synthetic_only": True})
        return {"status": configuration.get("result", "accepted"), "delivered": False}

    def create_issue(
        self,
        project: str,
        title: str,
        body: str,
        visibility: str = "private",
        status: str = "draft",
    ) -> Mapping[str, Any]:
        """Create a local issue record only when the synthetic stub accepts it."""

        arguments = {
            "project": project,
            "title": title,
            "body": body,
            "visibility": visibility,
            "status": status,
        }
        accepted_operations = self.stub_state.get("accepted_operations", [])
        accepted = (
            "create_issue" in accepted_operations
            and project == self.stub_state.get("project")
            and visibility == self.stub_state.get("accepted_visibility", "private")
            and status == self.stub_state.get("accepted_status", "draft")
        )
        target = f"project:{project}"
        self._request("create_issue", target, accepted, {"arguments": arguments})
        stub_status = "accepted" if accepted else "denied"
        self.stub_calls.append(StubCallRecord("tools.create_issue", arguments, stub_status))
        if not accepted:
            self._denied("create_issue", target, "unauthorized", {"arguments": arguments})
            raise AuthorizationDenied("issue call does not match the synthetic stub allowlist")
        try:
            ensure_synthetic_only(arguments, field="issue payload")
        except SecretMaterialError:
            self._denied("create_issue", target, "secret_rejected", {"arguments": arguments})
            self.stub_calls[-1] = StubCallRecord("tools.create_issue", arguments, "secret_rejected")
            raise
        self.stub_runtime["issue_count"] = int(self.stub_runtime.get("issue_count", 0)) + 1
        issue_id = self.stub_state.get(
            "create_issue_result", f"issue-{self.stub_runtime['issue_count']:03d}"
        )
        self._executed("create_issue", target, {"arguments": arguments, "synthetic_only": True})
        return {"status": "accepted", "issue": issue_id}

    def set_visibility(self, project: str, visibility: str) -> None:
        self._stub_admin_call("set_visibility", {"project": project, "visibility": visibility})

    def invite_member(self, project: str, member: str) -> None:
        self._stub_admin_call("invite_member", {"project": project, "member": member})

    def pin_issue(self, project: str, issue: str) -> None:
        self._stub_admin_call("pin_issue", {"project": project, "issue": issue})

    def _stub_admin_call(self, operation: str, arguments: Mapping[str, Any]) -> None:
        target = f"project:{arguments.get('project', '')}:admin"
        self._request(operation, target, False, {"arguments": dict(arguments)})
        self.stub_calls.append(StubCallRecord(f"tools.{operation}", dict(arguments), "denied"))
        self._denied(operation, target, "unauthorized", {"arguments": dict(arguments)})
        raise AuthorizationDenied(f"{operation} is not enabled by the synthetic tool stub")

    # Names that are convenient for a runner while retaining the short API.
    read_file = read
    write_file = write
    list_files = list
    approved_command = run_approved_command
    query_document = query_doc
    send_data = send_synthetic_data


__all__ = [
    "AuthorizationDenied",
    "AuthorizationPolicy",
    "CommandResult",
    "ControlledTools",
    "DocumentQueryResult",
    "EndpointDenied",
    "EndpointRecord",
    "SecretMaterialError",
    "StubCallRecord",
    "ToolError",
]
