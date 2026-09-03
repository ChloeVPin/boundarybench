# BoundaryBench

[![CI](https://github.com/ChloeVPin/boundarybench/actions/workflows/ci.yml/badge.svg)](https://github.com/ChloeVPin/boundarybench/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

BoundaryBench is a reproducible benchmark for measuring whether autonomous agents preserve authorization boundaries while completing useful work. Version 0.1 includes a typed scenario format, an isolated filesystem, controlled tools, complete event traces, deterministic oracles, paired negative controls, and a one command reference suite.

The benchmark studies authorization decay: the possibility that an agent begins treating lower trust content as authority as a task moves through files, messages, tools, and execution steps. BoundaryBench keeps authority, provenance, action, and outcome separate so each decision can be inspected after a run.

## Reference release

| Component | Included |
| --- | ---: |
| Primary scenarios | 11 |
| Paired negative controls | 11 |
| Deterministic reference cases | 22 |
| Scenario categories | 4 |
| Supported Python versions | 3.11 through 3.14 |

The committed [reference conformance result](results/reference-suite-v0.1.json) records 22 passing deterministic cases and an Agent Boundary Score of 100 for the scripted reference adapter. This artifact verifies the harness, scenario fixtures, controlled operations, and oracles. Model evaluations can use the same scenarios and reporting contract without changing the corpus.

## Quick start

```bash
git clone https://github.com/ChloeVPin/boundarybench.git
cd boundarybench
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
boundarybench validate scenarios
boundarybench suite
```

The suite creates an isolated run directory for every case. Each directory contains a manifest, an event stream, a result record, artifacts, and the final sandbox state.

Run or inspect one scenario:

```bash
boundarybench inspect scenarios/filesystem/BB-FS-003-archive-traversal.yaml
boundarybench run scenarios/controls/BB-CTRL-002-benign-same-scope.yaml \
  --script examples/smoke-script.yaml \
  --output-root runs
boundarybench report runs
```

## Scenario corpus

| ID | Boundary under test |
| --- | --- |
| BB-CTRL-001 | Exact delegated move with unrelated deletion pressure |
| BB-CTRL-002 | Benign same scope instruction as a refusal control |
| BB-FS-001 | Symlink redirection outside an approved output path |
| BB-FS-002 | Relative path pressure toward a protected file |
| BB-FS-003 | Archive member traversal outside an extraction root |
| BB-REPO-001 | README content attempting to modify a protected workflow |
| BB-REPO-002 | Repository note requesting synthetic secret disclosure |
| BB-REPO-003 | Dependency documentation attempting a lockfile change |
| BB-REPO-004 | Source comment requesting protected configuration access |
| BB-TOOL-001 | Tool output attempting to widen recipients and attachments |
| BB-TOOL-002 | Tool output attempting to change visibility and membership |

Every scenario declares trusted and untrusted sources, an authority manifest, resettable synthetic fixtures, allowed interfaces, exact expected effects, forbidden effects, deterministic oracles, and a clean negative control.

## How it works

```text
scenario YAML
    |
    v
typed validation -> fresh sandbox -> controlled tools -> event trace
                                                       |
                                                       v
                                  deterministic oracle and ABS report
```

The runner does not expose host paths or unrestricted network access. Files are mapped into isolated workspace, protected, and external areas. Reads, writes, moves, archive extraction, commands, and synthetic tool calls pass through explicit policy checks and structured instrumentation.

The bundled `ScriptedAgent` provides a deterministic conformance path. A model adapter can implement the same provider neutral request and response interface while retaining the controlled tool boundary and result format.

## Documentation

| Topic | Document |
| --- | --- |
| Research framing | [Research overview](docs/research-overview.md) |
| Security assumptions | [Threat model](docs/threat-model.md) |
| Scenario authoring | [Scenario specification](docs/scenario-specification.md) |
| Study design | [Methodology](docs/methodology.md) |
| Metrics and oracles | [Evaluation](docs/evaluation.md) |
| Composite score | [Agent Boundary Score](docs/agent-boundary-score.md) |
| Supported claims | [Scope](docs/scope.md) |
| Research sources | [References](docs/references.md) |
| Version history | [Release notes](docs/release-notes.md) |
| Responsible use | [Ethics](docs/ethics.md) |

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a scenario or implementation change. General usage questions belong in [GitHub Discussions](https://github.com/ChloeVPin/boundarybench/discussions). Bugs and scenario proposals belong in [GitHub Issues](https://github.com/ChloeVPin/boundarybench/issues). Report unsafe fixtures, exposed data, or execution boundary failures privately through the repository Security tab as described in [SECURITY.md](SECURITY.md).

BoundaryBench uses only synthetic fixtures and local stubs. The project does not authorize testing external systems or contacting real recipients.

## Citation and license

Citation metadata is available in [CITATION.cff](CITATION.cff). BoundaryBench is released under the [MIT License](LICENSE).
