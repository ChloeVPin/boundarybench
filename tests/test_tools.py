from __future__ import annotations

import pytest

from boundarybench.instrumentation import EventLogger
from boundarybench.sandbox import Sandbox, SandboxPathError, SecretMaterialError
from boundarybench.tools import (
    AuthorizationDenied,
    AuthorizationPolicy,
    ControlledTools,
    EndpointDenied,
)


def test_unauthorized_write_is_not_performed_and_is_fully_logged():
    with Sandbox() as sandbox:
        logger = EventLogger(run_id="r1", scenario_id="s1")
        tools = ControlledTools(sandbox, logger=logger)
        with pytest.raises(AuthorizationDenied):
            tools.write("protected.txt", "blocked", area="protected")
        assert not (sandbox.paths.protected / "protected.txt").exists()
        assert [event.event_type for event in logger.events] == ["tool.requested", "tool.denied"]
        assert logger.events[-1].outcome == "unauthorized"


def test_secret_detection_denies_write_before_filesystem_change():
    with Sandbox() as sandbox:
        tools = ControlledTools(sandbox)
        with pytest.raises(SecretMaterialError):
            tools.write("credentials.txt", "TOKEN=real-token")
        assert not (sandbox.paths.workspace / "credentials.txt").exists()
        assert logger_events(tools) == ["tool.requested", "tool.denied"]
        assert tools.logger.events[-1].outcome == "secret_rejected"


def test_approved_command_is_allowlisted_and_network_is_not_available():
    policy = AuthorizationPolicy(approved_commands=frozenset({("printf", "ok")}))
    with Sandbox() as sandbox:
        tools = ControlledTools(sandbox, policy=policy)
        result = tools.run_approved_command(("printf", "ok"))
        assert result.stdout == "ok"
        with pytest.raises(AuthorizationDenied):
            tools.run_approved_command(("curl", "https://example.invalid"))

        network_capable = AuthorizationPolicy(approved_commands=frozenset({("git", "fetch")}))
        restricted = ControlledTools(sandbox, policy=network_capable)
        with pytest.raises(AuthorizationDenied):
            restricted.run_approved_command(("git", "fetch"))

        host_reader = AuthorizationPolicy(
            approved_commands=frozenset({("grep", "x", "/etc/passwd")})
        )
        restricted = ControlledTools(sandbox, policy=host_reader)
        with pytest.raises(SandboxPathError):
            restricted.run_approved_command(("grep", "x", "/etc/passwd"))


def test_controlled_endpoints_record_without_network_calls():
    policy = AuthorizationPolicy(
        query_endpoints=frozenset({"docs://local"}),
        send_endpoints=frozenset({"sink://test"}),
    )
    with Sandbox() as sandbox:
        tools = ControlledTools(
            sandbox,
            policy=policy,
            documents={"docs://local": "alpha\nbeta"},
        )
        result = tools.query_doc("docs://local", "alp")
        sent = tools.send_synthetic_data("sink://test", {"value": "SYNTHETIC_SECRET=test"})
        assert result.matches == ("alpha",)
        assert sent.endpoint == "sink://test"
        assert [record.operation for record in tools.endpoint_records] == ["query", "send"]
        assert len(tools.logger.events) == 4
        with pytest.raises(EndpointDenied):
            tools.send_synthetic_data("https://unapproved.invalid", {"value": "x"})
        assert len(tools.endpoint_records) == 2


def test_structured_endpoint_payload_rejects_non_synthetic_secret():
    policy = AuthorizationPolicy(send_endpoints=frozenset({"sink://test"}))
    with Sandbox() as sandbox:
        tools = ControlledTools(sandbox, policy=policy)
        with pytest.raises(SecretMaterialError):
            tools.send_synthetic_data("sink://test", {"token": "real-token"})
        assert tools.endpoint_records == []


def test_move_requires_the_exact_delegated_pair():
    policy = AuthorizationPolicy(
        approved_moves=frozenset(
            {("/workspace/project/README.md", "/workspace/project/README-old.md")}
        )
    )
    with Sandbox(
        [{"area": "workspace", "path": "project/README.md", "content": "readme"}]
    ) as sandbox:
        tools = ControlledTools(sandbox, policy=policy)
        tools.move("/workspace/project/README.md", "/workspace/project/README-old.md")
        assert sandbox.read_text("workspace", "project/README-old.md") == "readme"
        with pytest.raises(AuthorizationDenied):
            tools.move("/workspace/project/README-old.md", "/workspace/private/README.md")


def test_archive_extraction_rejects_posix_and_windows_traversal():
    archive = "/workspace/uploads/input.tar"
    destination = "/workspace/uploads/extracted"
    policy = AuthorizationPolicy(
        approved_extractions=frozenset({(archive, destination)}),
        archive_members={
            archive: (
                {"name": "docs/readme.txt", "content": "safe\n"},
                {"name": "../../outside.txt", "content": "blocked\n"},
                {"name": "..\\outside.txt", "content": "blocked\n"},
            )
        },
    )
    with Sandbox(
        [{"area": "workspace", "path": "uploads/input.tar", "content": "archive"}]
    ) as sandbox:
        tools = ControlledTools(sandbox, policy=policy)
        result = tools.extract_archive(archive, destination)
        assert result == {
            "extracted": ["docs/readme.txt"],
            "rejected": ["../../outside.txt", "..\\outside.txt"],
        }
        assert sandbox.read_text("workspace", "uploads/extracted/docs/readme.txt") == "safe\n"
        assert not (sandbox.paths.workspace / "outside.txt").exists()


def logger_events(tools: ControlledTools) -> list[str]:
    return [event.event_type for event in tools.logger.events]
