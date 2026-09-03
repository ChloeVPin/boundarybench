"""Public BoundaryBench interfaces."""

from ._version import __version__
from .agents import AgentRequest, AgentResponse, ScriptedAgent, ScriptedStep
from .evaluation import EvaluationMetrics, EvaluationResult, Evaluator
from .instrumentation import EventLogger, EventRecord
from .openai_adapter import OpenAIResponsesAgent
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
    analyze_mitigation_effect,
    compare_mitigation_runs,
    run_authorization_decay_surface,
)
from .study import StudySpecification, compile_study_plan, load_study, write_study_plan
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
    "OpenAIResponsesAgent",
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
    "StudySpecification",
    "SUPPORTED_VERSION",
    "SUPPORTED_SCENARIO_VERSIONS",
    "ValidationIssue",
    "canonicalize_destination",
    "canonicalize_path",
    "analyze_authorization_decay",
    "analyze_mitigation_effect",
    "compare_mitigation_runs",
    "compile_study_plan",
    "load_scenario",
    "load_study",
    "negative_control_variant",
    "parse_scenario",
    "run_scenario",
    "run_reference_suite",
    "run_authorization_decay_surface",
    "write_study_plan",
]
