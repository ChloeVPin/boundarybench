"""Filesystem isolation primitives used by BoundaryBench scenarios.

The sandbox intentionally uses a small, explicit API.  Callers select one of
three areas and provide a path relative to that area; host paths are never
accepted as scenario resources or tool targets.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Literal

Area = Literal["workspace", "protected", "external"]
AREAS: tuple[Area, ...] = ("workspace", "protected", "external")


class SandboxError(RuntimeError):
    """Base class for sandbox setup and access errors."""


class SandboxPathError(SandboxError, ValueError):
    """Raised when a path is absolute, traverses an area, or escapes by link."""


class SecretMaterialError(SandboxError, ValueError):
    """Raised when non-synthetic secret material reaches the sandbox boundary."""


@dataclass(frozen=True, slots=True)
class ResourceDeclaration:
    """A file or directory that is created during scenario setup."""

    area: Area
    path: str
    content: str | bytes = ""
    is_dir: bool = False


@dataclass(frozen=True, slots=True)
class Scenario:
    """Minimal scenario shape consumed by :class:`Sandbox`."""

    scenario_id: str
    resources: tuple[ResourceDeclaration, ...] = ()


@dataclass(frozen=True, slots=True)
class SandboxPaths:
    """Absolute roots for the isolated areas."""

    root: Path
    workspace: Path
    protected: Path
    external: Path

    def for_area(self, area: Area) -> Path:
        if area not in AREAS:
            raise ValueError(f"unknown sandbox area: {area!r}")
        return getattr(self, area)


# These are deliberately conservative.  The benchmark may carry fixtures such
# as ``SYNTHETIC_SECRET=...`` but must not carry credentials from a real host.
_SECRET_ASSIGNMENT = re.compile(
    r"(?ix)((?:synthetic[_-]?)?(?:api[_-]?key|access[_-]?token|"
    r"auth(?:entication)?[_-]?token|password|passwd|private[_-]?key|"
    r"secret|token|bearer))[\"']?\s*[:=]\s*[\"']?([^\s,;\"'}]+)"
)
_KNOWN_SECRET = re.compile(
    r"(?x)(?:AKIA[0-9A-Z]{16}|(?:sk|rk)_live_[A-Za-z0-9]{12,}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{15,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
_SYNTHETIC_MARKERS = ("synthetic", "fake", "dummy", "test", "example", "boundarybench")


def is_synthetic_secret(value: str) -> bool:
    """Return whether a secret-shaped value is explicitly marked synthetic."""

    lowered = value.lower()
    words = set(re.findall(r"[a-z0-9]+", lowered))
    return bool(words.intersection(_SYNTHETIC_MARKERS))


def contains_non_synthetic_secret(value: Any) -> bool:
    """Detect credential-shaped values without inspecting host data.

    Tool payloads are often structured mappings rather than shell-style text.
    Secret-shaped keys are therefore inspected recursively while scalar text
    retains the assignment and known-token checks used for fixture content.
    """

    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if _SECRET_ASSIGNMENT.search(f"{key_text}={item}"):
                if not is_synthetic_secret(key_text) and not is_synthetic_secret(str(item)):
                    return True
            if contains_non_synthetic_secret(item):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(contains_non_synthetic_secret(item) for item in value)
    if not isinstance(value, (str, bytes)):
        return False
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
    for match in _SECRET_ASSIGNMENT.finditer(text):
        key, secret = match.groups()
        if "synthetic" not in key.lower() and not is_synthetic_secret(secret):
            return True
    return bool(_KNOWN_SECRET.search(text))


def ensure_synthetic_only(value: Any, *, field: str = "data") -> None:
    """Reject data containing a secret that is not explicitly synthetic."""

    if contains_non_synthetic_secret(value):
        raise SecretMaterialError(f"{field} contains non-synthetic secret material")


def _coerce_declaration(raw: ResourceDeclaration | Mapping[str, Any]) -> ResourceDeclaration:
    if isinstance(raw, ResourceDeclaration):
        declaration = raw
    elif isinstance(raw, Mapping):
        try:
            declaration = ResourceDeclaration(
                area=raw["area"],
                path=raw["path"],
                content=raw.get("content", ""),
                is_dir=raw.get("is_dir", False),
            )
        except KeyError as exc:
            raise SandboxError(f"resource declaration is missing {exc.args[0]!r}") from exc
    else:
        raise TypeError("resources must be ResourceDeclaration instances or mappings")
    if declaration.area not in AREAS:
        raise SandboxError(f"unknown resource area: {declaration.area!r}")
    if not isinstance(declaration.path, str):
        raise TypeError("resource path must be a string")
    if not isinstance(declaration.content, (str, bytes)):
        raise TypeError("resource content must be str or bytes")
    return declaration


def _contains_symlink_component(root: Path, candidate: Path) -> bool:
    """Return whether an existing component between root and candidate is a link."""

    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return True
    current = root
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            return True
    return False


class Sandbox:
    """Deterministic, temporary three-area filesystem sandbox.

    ``reset`` removes only children of the three directories owned by this
    instance.  A caller-provided root is supported for repeatable tests, while
    the default root is a private temporary directory.
    """

    def __init__(
        self,
        scenario: (
            Scenario | Mapping[str, Any] | Iterable[ResourceDeclaration | Mapping[str, Any]] | None
        ) = None,
        *,
        root: str | os.PathLike[str] | None = None,
        scenario_id: str | None = None,
    ) -> None:
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        if root is None:
            self._temporary_directory = tempfile.TemporaryDirectory(prefix="boundarybench-")
            root_path = Path(self._temporary_directory.name)
        else:
            root_path = Path(root).absolute()
            if root_path.exists() and root_path.is_symlink():
                raise SandboxPathError("sandbox root cannot be a symlink")
            root_path.mkdir(parents=True, exist_ok=True)
        self.paths = SandboxPaths(
            root=root_path,
            workspace=root_path / "workspace",
            protected=root_path / "protected",
            external=root_path / "external",
        )
        self.scenario_id = scenario_id or self._scenario_id(scenario)
        self._prepare_area_roots()
        self.setup(scenario)

    @staticmethod
    def _scenario_id(scenario: Any) -> str:
        if isinstance(scenario, Scenario):
            return scenario.scenario_id
        if isinstance(scenario, Mapping) and scenario.get("scenario_id"):
            return str(scenario["scenario_id"])
        return "scenario"

    def _prepare_area_roots(self) -> None:
        for area in AREAS:
            area_root = self.paths.for_area(area)
            if area_root.exists() and area_root.is_symlink():
                raise SandboxPathError(f"sandbox area cannot be a symlink: {area}")
            area_root.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> Sandbox:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None

    @property
    def root(self) -> Path:
        return self.paths.root

    def area_root(self, area: Area) -> Path:
        """Return an area root without accepting a host path."""

        return self.paths.for_area(area)

    def reset(self) -> None:
        """Clear all area contents and recreate the area roots."""

        self._prepare_area_roots()
        for area in AREAS:
            area_root = self.paths.for_area(area)
            for child in area_root.iterdir():
                # Never recurse through a symlink while clearing the sandbox.
                if child.is_symlink() or not child.is_dir():
                    child.unlink()
                else:
                    shutil.rmtree(child)

    def setup(
        self,
        scenario: (
            Scenario | Mapping[str, Any] | Iterable[ResourceDeclaration | Mapping[str, Any]] | None
        ),
    ) -> None:
        """Reset the sandbox and materialize scenario resource declarations."""

        self.reset()
        if scenario is None:
            return
        if isinstance(scenario, Scenario):
            resources: Iterable[ResourceDeclaration | Mapping[str, Any]] = scenario.resources
            self.scenario_id = scenario.scenario_id
        elif isinstance(scenario, Mapping):
            resources = scenario.get("resources", ())
            if scenario.get("scenario_id"):
                self.scenario_id = str(scenario["scenario_id"])
        else:
            resources = scenario
        for raw in resources:
            declaration = _coerce_declaration(raw)
            if declaration.is_dir:
                self.resolve(declaration.area, declaration.path).mkdir(parents=True, exist_ok=True)
                continue
            target = self.resolve(declaration.area, declaration.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            ensure_synthetic_only(declaration.content, field=f"resource {declaration.path!r}")
            target.write_bytes(
                declaration.content.encode("utf-8")
                if isinstance(declaration.content, str)
                else declaration.content
            )

    def resolve(
        self,
        area: Area,
        relative_path: str | os.PathLike[str],
        *,
        must_exist: bool = False,
    ) -> Path:
        """Resolve a relative path and verify containment without following links."""

        area_root = self.paths.for_area(area)
        raw = os.fspath(relative_path)
        if "\x00" in raw:
            raise SandboxPathError("path contains a NUL byte")
        if os.path.isabs(raw) or PureWindowsPath(raw).is_absolute() or PureWindowsPath(raw).drive:
            raise SandboxPathError("absolute paths are not allowed")
        # Check both path syntaxes so Windows traversal strings are rejected on
        # POSIX hosts too.  A literal backslash is not a useful fixture name.
        if any(part == ".." for part in Path(raw).parts) or any(
            part == ".." for part in PureWindowsPath(raw.replace("/", "\\")).parts
        ):
            raise SandboxPathError("parent traversal is not allowed")
        candidate = area_root / Path(raw)
        if _contains_symlink_component(area_root, candidate):
            raise SandboxPathError("symlink path components are not allowed")
        resolved_root = area_root.resolve(strict=True)
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise SandboxPathError("path escapes its sandbox area") from exc
        if must_exist and not candidate.exists():
            raise FileNotFoundError(candidate)
        return candidate

    def read_bytes(self, area: Area, path: str | os.PathLike[str]) -> bytes:
        target = self.resolve(area, path, must_exist=True)
        return target.read_bytes()

    def read_text(self, area: Area, path: str | os.PathLike[str]) -> str:
        return self.read_bytes(area, path).decode("utf-8")

    def write_bytes(self, area: Area, path: str | os.PathLike[str], content: bytes) -> None:
        target = self.resolve(area, path)
        ensure_synthetic_only(content, field=f"write {path!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Re-check after parent creation in case a symlink was introduced in a
        # parent component during setup of a custom-root test.
        self.resolve(area, path)
        target.write_bytes(content)

    def list_names(self, area: Area, path: str | os.PathLike[str] = "") -> list[str]:
        target = self.resolve(area, path, must_exist=True)
        if not target.is_dir():
            raise NotADirectoryError(target)
        return sorted(child.name for child in target.iterdir())


__all__ = [
    "AREAS",
    "Area",
    "ResourceDeclaration",
    "Sandbox",
    "SandboxError",
    "SandboxPathError",
    "SandboxPaths",
    "Scenario",
    "SecretMaterialError",
    "contains_non_synthetic_secret",
    "ensure_synthetic_only",
    "is_synthetic_secret",
]
