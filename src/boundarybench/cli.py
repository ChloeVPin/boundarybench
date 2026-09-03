"""Command-line interface for BoundaryBench.

The CLI is intentionally a thin adapter around scenario loading, the runner,
and result aggregation. Research behavior belongs in those modules so that
library users and experiments do not depend on command-line parsing.
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _scenario_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() in {".yaml", ".yml"}
        )
    raise FileNotFoundError(f"scenario path does not exist: {path}")


def _load_scenario(path: Path) -> Any:
    from . import scenarios

    loader = getattr(scenarios, "load_scenario", None)
    if loader is not None:
        return loader(path)
    scenario_type = getattr(scenarios, "Scenario", None)
    if scenario_type is not None and hasattr(scenario_type, "from_file"):
        return scenario_type.from_file(path)
    raise RuntimeError("scenario module does not expose load_scenario or Scenario.from_file")


def _load_script(path: Path) -> Any:
    """Load a local JSON/YAML scripted-agent response specification."""

    try:
        import yaml

        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"could not read script {path}: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"could not parse script {path}: {exc}") from exc
    if not isinstance(value, (list, dict)):
        raise ValueError("script must be a YAML sequence or mapping")
    return value


def _as_mapping(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_as_mapping(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return _as_mapping(value.to_dict())
    if dataclasses.is_dataclass(value):
        return _as_mapping(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _as_mapping(item) for key, item in value.items()}
    return value


def _call_supported(function: Callable[..., Any], **kwargs: Any) -> Any:
    """Call a public helper without making optional runner arguments mandatory."""

    try:
        parameters = inspect.signature(function).parameters
    except (TypeError, ValueError):
        return function(**kwargs)
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return function(**kwargs)
    accepted = {name for name in parameters if name != "self"}
    return function(**{name: value for name, value in kwargs.items() if name in accepted})


def _cmd_validate(path: Path) -> int:
    files = _scenario_files(path)
    if not files:
        print(f"no YAML scenarios found under {path}", file=sys.stderr)
        return 1
    failed = False
    for scenario_path in files:
        try:
            scenario = _load_scenario(scenario_path)
            scenario_id = getattr(scenario, "id", scenario_path.stem)
            print(f"valid: {scenario_path} ({scenario_id})")
        except Exception as exc:  # CLI boundary: preserve useful validation text and exit cleanly.
            failed = True
            print(f"invalid: {scenario_path}: {exc}", file=sys.stderr)
    return 1 if failed else 0


def _cmd_inspect(path: Path) -> int:
    try:
        scenario = _load_scenario(path)
    except Exception as exc:
        print(f"unable to inspect {path}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(_as_mapping(scenario), indent=2, sort_keys=True, default=str))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from . import runner

    run_function = getattr(runner, "run_scenario", None)
    if run_function is None:
        print("runner does not expose run_scenario", file=sys.stderr)
        return 1
    try:
        script = _load_script(args.script) if args.script is not None else None
        result = _call_supported(
            run_function,
            scenario_path=args.scenario,
            scenario=args.scenario,
            output_root=args.output_root,
            trials=args.trials,
            model=args.model,
            model_name=args.model,
            seed=args.seed,
            mitigation=args.mitigation,
            attack_variant=args.attack_variant,
            attack_position=args.attack_position,
            script=script,
        )
    except Exception as exc:
        print(f"benchmark run failed: {exc}", file=sys.stderr)
        return 1
    output = _as_mapping(result)
    if output is not None:
        print(json.dumps(output, indent=2, sort_keys=True, default=str))
    return 0


def _cmd_report(path: Path, output_format: str = "json") -> int:
    from . import results

    if output_format == "csv":
        report_function = getattr(results, "aggregate_runs", None)
    else:
        report_function = getattr(results, "summarize_runs", None)
    if report_function is None:
        report_function = getattr(results, "aggregate_runs", None)
    if report_function is None:
        report_function = getattr(results, "aggregate_results", None)
    if report_function is None:
        print("results module does not expose an aggregation function", file=sys.stderr)
        return 1
    try:
        report = _call_supported(report_function, path=path, run_path=path, root=path)
    except Exception as exc:
        print(f"report failed: {exc}", file=sys.stderr)
        return 1
    if output_format == "csv" and hasattr(report, "to_csv"):
        print(report.to_csv(), end="")
    else:
        print(json.dumps(_as_mapping(report), indent=2, sort_keys=True, default=str))
    return 0


def _cmd_suite(args: argparse.Namespace) -> int:
    from .suite import run_reference_suite

    try:
        result = run_reference_suite(
            args.scenarios,
            args.script,
            args.output_root,
            include_negative_controls=not args.primary_only,
        )
        summary = result.to_dict()
        rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
        if args.summary is not None:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0 if result.passed else 1
    except Exception as exc:
        print(f"reference suite failed: {exc}", file=sys.stderr)
        return 1


def _cmd_stress(args: argparse.Namespace) -> int:
    from .stress import run_authorization_decay_surface

    try:
        agent = None
        script = args.script
        if args.provider == "openai":
            from .openai_adapter import OpenAIResponsesAgent

            agent = OpenAIResponsesAgent(
                args.model,
                reasoning_effort=args.reasoning_effort,
                max_output_tokens=args.max_output_tokens,
                max_tool_rounds=args.max_tool_rounds,
                mitigation=args.mitigation,
            )
            script = None
        result = run_authorization_decay_surface(
            args.scenarios,
            script,
            args.output_root,
            trials=args.trials,
            seed=args.seed,
            positions=args.positions,
            pressure_levels=args.pressure_levels,
            provenance_modes=args.provenance_modes,
            agent=agent,
            model=args.model,
            mitigation=args.mitigation if args.mitigation != "none" else None,
        )
        rendered = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
        if args.summary is not None:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0 if result.passed else 1
    except Exception as exc:
        print(f"authorization decay experiment failed: {exc}", file=sys.stderr)
        return 1


def _cmd_plan(args: argparse.Namespace) -> int:
    from .study import compile_study_plan, write_study_plan

    try:
        plan = (
            write_study_plan(args.study, args.output)
            if args.output is not None
            else compile_study_plan(args.study)
        )
    except Exception as exc:
        print(f"study planning failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0 if plan["resource_plan"]["within_funding_cap"] else 1


def _cmd_compare_mitigation(args: argparse.Namespace) -> int:
    from .stress import compare_mitigation_runs

    try:
        report = compare_mitigation_runs(
            args.baseline,
            args.intervention,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
        )
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.summary is not None:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
    except Exception as exc:
        print(f"mitigation comparison failed: {exc}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="boundarybench",
        description="Run reproducible authorization-preservation benchmark experiments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="validate one scenario or a directory of scenarios"
    )
    validate.add_argument("path", type=Path)
    validate.set_defaults(handler=lambda args: _cmd_validate(args.path))

    inspect_parser = subparsers.add_parser("inspect", help="print a normalized scenario")
    inspect_parser.add_argument("path", type=Path)
    inspect_parser.set_defaults(handler=lambda args: _cmd_inspect(args.path))

    run = subparsers.add_parser("run", help="execute one scenario or repeated trials")
    run.add_argument("scenario", type=Path)
    run.add_argument("--trials", type=int, default=1)
    run.add_argument("--model", default="scripted")
    run.add_argument("--output-root", type=Path, default=Path("runs"))
    run.add_argument("--seed", type=int)
    run.add_argument("--mitigation")
    run.add_argument("--attack-variant")
    run.add_argument("--attack-position", type=int)
    run.add_argument(
        "--script",
        type=Path,
        help="local YAML/JSON scripted-agent response specification",
    )
    run.set_defaults(handler=_cmd_run)

    suite = subparsers.add_parser("suite", help="run the complete deterministic reference suite")
    suite.add_argument("--scenarios", type=Path, default=Path("scenarios"))
    suite.add_argument("--script", type=Path, default=Path("examples/reference-suite.yaml"))
    suite.add_argument("--output-root", type=Path, default=Path("runs/reference-suite"))
    suite.add_argument("--summary", type=Path)
    suite.add_argument("--primary-only", action="store_true")
    suite.set_defaults(handler=_cmd_suite)

    stress = subparsers.add_parser(
        "stress", help="measure authorization decay across controlled trajectories"
    )
    stress.add_argument("--scenarios", type=Path, default=Path("scenarios"))
    stress.add_argument("--script", type=Path, default=Path("examples/reference-suite.yaml"))
    stress.add_argument("--provider", choices=("scripted", "openai"), default="scripted")
    stress.add_argument("--model", default="scripted-reference")
    stress.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        default="medium",
    )
    stress.add_argument("--max-output-tokens", type=int, default=1500)
    stress.add_argument("--max-tool-rounds", type=int, default=8)
    stress.add_argument("--mitigation", choices=("none", "authority-checkpoint"), default="none")
    stress.add_argument(
        "--output-root", type=Path, default=Path("runs/authorization-decay-surface")
    )
    stress.add_argument("--summary", type=Path)
    stress.add_argument("--trials", type=int, default=1)
    stress.add_argument("--seed", type=int, default=0)
    stress.add_argument(
        "--positions",
        nargs="+",
        choices=("early", "middle", "late"),
        default=("early", "middle", "late"),
    )
    stress.add_argument(
        "--pressure-levels", nargs="+", type=int, choices=(1, 3, 5), default=(1, 3, 5)
    )
    stress.add_argument(
        "--provenance-modes",
        nargs="+",
        choices=("explicit", "source_only", "flattened"),
        default=("explicit", "source_only", "flattened"),
    )
    stress.set_defaults(handler=_cmd_stress)

    plan = subparsers.add_parser("plan", help="compile and lock a preregistered model study")
    plan.add_argument("study", type=Path)
    plan.add_argument("--output", type=Path)
    plan.set_defaults(handler=_cmd_plan)

    compare = subparsers.add_parser(
        "compare-mitigation",
        help="compare matched baseline and mitigation run collections",
    )
    compare.add_argument("baseline", type=Path)
    compare.add_argument("intervention", type=Path)
    compare.add_argument("--bootstrap-samples", type=int, default=2000)
    compare.add_argument("--seed", type=int, default=0)
    compare.add_argument("--summary", type=Path)
    compare.set_defaults(handler=_cmd_compare_mitigation)

    report = subparsers.add_parser("report", help="aggregate structured run results")
    report.add_argument("path", type=Path)
    report.add_argument("--format", choices=("json", "csv"), default="json")
    report.set_defaults(handler=lambda args: _cmd_report(args.path, args.format))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
