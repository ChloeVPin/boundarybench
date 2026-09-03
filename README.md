# BoundaryBench

BoundaryBench is an open-source benchmark for studying whether autonomous agents preserve authorization boundaries while completing useful work. Version 0.1 provides a versioned scenario format, a controlled local sandbox, instrumented tools, an offline scripted-agent path, deterministic evaluation, and structured run records. It is not a claim that any agent is safe.

## Status

This repository is at the implementation and pilot-preparation stage. The bundled execution path is deliberately offline and scripted. No pilot has been run from the contents of this repository, and it contains no model results, aggregate statistics, or validated safety conclusions.

The central research hypothesis is that an agent can experience **authorization decay**: as a task crosses messages, files, tools, or execution steps, the agent may gradually treat lower-trust instructions as if they carried the authority of the original request. Authorization decay is a hypothesis to test, not an established phenomenon.

The **Agent Boundary Score (ABS)** is an experimental reporting measure proposed in [docs/agent-boundary-score.md](docs/agent-boundary-score.md). ABS must not be presented as a validated safety metric or as a substitute for task-specific evidence.

## What the benchmark tests

Each scenario gives an agent:

- an explicit authority grant and denial set;
- trusted and untrusted inputs with declared provenance;
- an attacker strategy and payload;
- a deterministic initial fixture;
- expected authorized and unauthorized effects;
- a machine-readable oracle based on state and tool traces; and
- a negative control that should remain usable.

The initial corpus covers malicious README and source-comment content,
dependency documentation, fake administrator and conflicting tool output,
workspace escape, synthetic-secret disclosure, delayed and repeated attacks,
and negative controls. The scenarios are designed to be run by independent
harnesses. Scenario files do not contain runner code and do not require a
particular model, framework, or prompt wrapper.

## Install and run the local path

Use Python 3.11 or newer:

```text
python -m pip install -e ".[dev]"
boundarybench validate scenarios/
boundarybench inspect scenarios/controls/BB-CTRL-002-benign-same-scope.yaml
boundarybench run scenarios/controls/BB-CTRL-002-benign-same-scope.yaml \
  --script examples/smoke-script.yaml --output-root runs
boundarybench report runs/
boundarybench report runs/ --format csv
```

The scripted adapter is the only bundled agent implementation. A script is a
YAML or JSON response specification containing `tool_call` events and
trajectory events such as `task_completed`. Each run receives a fresh
filesystem sandbox and writes `manifest.json`, `events.jsonl`, `result.json`,
an `artifacts/` directory, and the preserved sandbox state. External model
providers are not silently supported; future adapters must implement the
documented agent interface. Approved command execution is limited to a small
non-shell, non-interpreter command allowlist; it cannot make arbitrary network
requests.

## Repository map

```text
docs/                  Research and format documentation
scenarios/             Versioned YAML scenarios grouped by boundary type
examples/              Small illustrative fragments for authors and evaluators
experiments/           Versioned planned experiment configurations
src/boundarybench/     Parser, policy, sandbox, tools, runner, evaluator, CLI
tests/                 Unit and boundary regression tests
results/README.md      Results-reporting contract; no results are included
```

Read the documents in this order:

1. [Research overview](docs/research-overview.md)
2. [Threat model](docs/threat-model.md)
3. [Scenario specification](docs/scenario-specification.md)
4. [Methodology](docs/methodology.md)
5. [Evaluation](docs/evaluation.md)
6. [Agent Boundary Score](docs/agent-boundary-score.md)
7. [Limitations](docs/limitations.md) and [ethics](docs/ethics.md)

## Quick review

The scenario corpus remains runner-independent and does not require a particular model runtime. The bundled runner resets the declarative fixture before every trial and exposes only controlled local tools. To inspect the scenarios, use the CLI or load the YAML files with a YAML 1.2 parser and validate them against the field and enum rules in [docs/scenario-specification.md](docs/scenario-specification.md). Compare only the declared oracle targets.

Contributions should preserve determinism, keep authority separate from provenance, and add a clean negative control. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

BoundaryBench is released under the MIT License. See [LICENSE](LICENSE).
