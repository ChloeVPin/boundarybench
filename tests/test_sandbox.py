from __future__ import annotations

import pytest

from boundarybench.sandbox import (
    ResourceDeclaration,
    Sandbox,
    SandboxPathError,
    SecretMaterialError,
)


def test_setup_reset_and_area_containment(tmp_path):
    sandbox = Sandbox(
        {
            "scenario_id": "s1",
            "resources": [
                {"area": "workspace", "path": "notes/a.txt", "content": "hello"},
                ResourceDeclaration("protected", "policy.txt", "SYNTHETIC_SECRET=fixture"),
                {"area": "external", "path": "docs/readme.txt", "content": "external"},
            ],
        },
        root=tmp_path / "sandbox",
    )
    assert sandbox.scenario_id == "s1"
    assert sandbox.read_text("workspace", "notes/a.txt") == "hello"
    assert sandbox.list_names("workspace", "notes") == ["a.txt"]
    sandbox.reset()
    assert sandbox.list_names("workspace") == []
    sandbox.close()


@pytest.mark.parametrize(
    "path", ["../outside", "nested/../../outside", "/tmp/host", "C:\\host\\file"]
)
def test_rejects_traversal_and_absolute_paths(path):
    with Sandbox() as sandbox:
        with pytest.raises(SandboxPathError):
            sandbox.resolve("workspace", path)


def test_symlink_to_other_area_cannot_escape(tmp_path):
    with Sandbox(root=tmp_path / "sandbox") as sandbox:
        sandbox.write_bytes("protected", "secret.txt", b"SYNTHETIC_SECRET=fixture")
        (sandbox.paths.workspace / "link").symlink_to(sandbox.paths.protected / "secret.txt")
        with pytest.raises(SandboxPathError):
            sandbox.resolve("workspace", "link")


def test_symlink_inside_one_area_is_not_an_authorization_alias(tmp_path):
    with Sandbox(root=tmp_path / "sandbox") as sandbox:
        sandbox.write_bytes("workspace", "allowed.txt", b"fixture")
        (sandbox.paths.workspace / "alias").symlink_to(sandbox.paths.workspace / "allowed.txt")
        with pytest.raises(SandboxPathError):
            sandbox.resolve("workspace", "alias")


def test_synthetic_only_secret_gate():
    with Sandbox() as sandbox:
        sandbox.write_bytes("workspace", "fixture.txt", b"SYNTHETIC_SECRET=fixture")
        assert sandbox.read_bytes("workspace", "fixture.txt") == b"SYNTHETIC_SECRET=fixture"
        with pytest.raises(SecretMaterialError):
            sandbox.write_bytes("workspace", "bad.txt", b"API_KEY=real-host-key")
        with pytest.raises(SecretMaterialError):
            sandbox.write_bytes("workspace", "lookalike.txt", b"API_KEY=latest-key")
