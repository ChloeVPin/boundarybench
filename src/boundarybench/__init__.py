"""Public BoundaryBench interfaces."""

from ._version import __version__
from .agents import AgentRequest, AgentResponse, ScriptedAgent, ScriptedStep
from .evaluation import EvaluationMetrics, EvaluationResult, Evaluator
from .instrumentation import EventLogger, EventRecord
from .policy import (
    AuthorizationRule,
    Decision,
    Effect,
    Operation,
    Policy,
    canonicalize_destination,
    canonicalize_path,
)
from .runner import BenchmarkRunner, run_scenario
from .sandbox import Sandbox, SandboxPathError
from .scenarios import (
    SUPPORTED_SCENARIO_VERSIONS,
    SUPPORTED_VERSION,
    Authority,
    AuthorityEntry,
    Scenario,
    ScenarioParseError,
    ScenarioValidationError,
    ValidationIssue,
    load_scenario,
    negative_control_variant,
    parse_scenario,
)
from .stress import (
    AuthorizationDecaySurfaceResult,
    StressObservation,
    analyze_authorization_decay,
    run_authorization_decay_surface,
)
from .suite import SuiteResult, run_reference_suite
from .tools import ControlledTools, StubCallRecord

__all__ = [
    "__version__",
    "AuthorizationRule",
    "AgentRequest",
    "AgentResponse",
    "BenchmarkRunner",
    "ControlledTools",
    "EvaluationMetrics",
    "EvaluationResult",
    "Evaluator",
    "EventLogger",
    "EventRecord",
    "Authority",
    "AuthorityEntry",
    "AuthorizationDecaySurfaceResult",
    "Decision",
    "Effect",
    "Operation",
    "Policy",
    "Scenario",
    "ScenarioParseError",
    "ScenarioValidationError",
    "Sandbox",
    "SandboxPathError",
    "ScriptedAgent",
    "ScriptedStep",
    "SuiteResult",
    "StubCallRecord",
    "StressObservation",
    "SUPPORTED_VERSION",
    "SUPPORTED_SCENARIO_VERSIONS",
    "ValidationIssue",
    "canonicalize_destination",
    "canonicalize_path",
    "analyze_authorization_decay",
    "load_scenario",
    "negative_control_variant",
    "parse_scenario",
    "run_scenario",
    "run_reference_suite",
    "run_authorization_decay_surface",
]
