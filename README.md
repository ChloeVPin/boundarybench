# BoundaryBench

[![CI](https://github.com/ChloeVPin/boundarybench/actions/workflows/ci.yml/badge.svg)](https://github.com/ChloeVPin/boundarybench/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)
[![Research protocol](https://img.shields.io/badge/protocol-Authorization_Decay_Surface-6f42c1)](docs/authorization-decay-surface.md)
[![Preregistered study](https://img.shields.io/badge/study-35%2C640_cases-0b7285)](docs/preregistered-study.md)

BoundaryBench is a reproducible research instrument for measuring whether autonomous agents preserve authorization while context, pressure, and provenance change around them.

The project has a public research studio at [`site/`](site/) designed to make the research question, method, and evidence legible before a reader enters the repository. See the [brand charter](docs/brand-charter.md) for the public identity and editorial commitments.

Version 0.3 turns that instrument into a complete model-study package. It adds a Responses API adapter restricted to local synthetic tools, a preregistration compiler that locks every research decision before collection, a matched mitigation analysis, and a $1,000 resource plan for 35,640 cases across three model tiers and two intervention arms.

[Read the research record](RESEARCH.md) or open the [Researcher Access study brief](docs/researcher-access-brief.md).

## Research at a glance

| Question | Design answer |
| --- | --- |
| What fails? | Task completion and authorization violations are measured independently |
| Where does robustness change? | Position, repetition, and provenance vary in a 3 by 3 by 3 factorial design |
| Is refusal mistaken for safety? | Every attack condition has a matched clean control |
| Can the failure be mitigated? | Baseline and authority-checkpoint arms use a matched difference in differences |
| Can another lab reproduce it? | Scenarios, schedule, adapter settings, and analysis commitments are hashed |
| Is collection bounded? | Synthetic tools, fixed stopping rules, usage accounting, and a $1,000 ceiling |

## The research contribution

Most prompt injection evaluations ask whether an attack worked. BoundaryBench asks a more diagnostic question: under which controlled context changes does authorization preservation weaken?

| Factor | Levels |
| --- | --- |
| Injection position | early, middle, late |
| Repetition pressure | 1, 3, 5 |
| Provenance visibility | explicit, source only, flattened |

The full design contains 27 matched conditions for every scenario. Across eleven primary scenarios and eleven clean controls, one trial produces 594 isolated cases.

The resulting Authorization Decay Fingerprint reports:

* attack versus clean control gap
* provenance attenuation effect
* late position effect
* repetition pressure effect
* worst cell safe completion
* Wilson intervals for rates
* scenario clustered bootstrap intervals for matched effects

Positive effects indicate lower safe completion under stronger stress. Unknown observations remain null and never become implicit failures or successes.

## Run it

```bash
git clone https://github.com/ChloeVPin/boundarybench.git
cd boundarybench
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

boundarybench validate scenarios
boundarybench plan experiments/openai-researcher-access-v0.3.yaml \
  --output results/local-study-plan.json
boundarybench stress \
  --output-root runs/authorization-decay-surface \
  --summary results/local-authorization-decay.json
```

The stress command creates a fresh sandbox for every case and preserves its manifest, model visible trajectory, event stream, artifacts, oracle evidence, and final state.

Run the compact v0.1 reference suite or inspect one scenario:

```bash
boundarybench suite
boundarybench inspect scenarios/filesystem/BB-FS-003-archive-traversal.yaml
boundarybench run scenarios/controls/BB-CTRL-002-benign-same-scope.yaml \
  --script examples/smoke-script.yaml \
  --output-root runs
boundarybench report runs
```

Run a hosted model through the same isolated tools:

```bash
python -m pip install -e ".[dev,openai]"
export OPENAI_API_KEY="your-project-key"
boundarybench stress \
  --provider openai \
  --model gpt-5.6-luna \
  --reasoning-effort medium \
  --max-output-tokens 1500 \
  --max-tool-rounds 8 \
  --output-root runs/gpt-5.6-luna
```

The key remains in the environment. The adapter sets `store=False`, exposes no web or computer tool, and routes every requested effect through a fresh synthetic sandbox. See the [adapter contract](docs/openai-responses-adapter.md) before collection.

Compare completed baseline and authority-checkpoint collections without custom analysis code:

```bash
boundarybench compare-mitigation \
  runs/gpt-5.6-luna/baseline \
  runs/gpt-5.6-luna/authority-checkpoint \
  --seed 20260903 \
  --summary results/gpt-5.6-luna-mitigation-comparison.json
```

## Verified release

| Component | Included |
| --- | ---: |
| Primary scenarios | 11 |
| Paired clean controls | 11 |
| Factorial conditions per scenario | 27 |
| Authorization Decay Surface cases | 594 |
| Deterministic oracle passes | 594 |
| Preregistered model-study cases | 35,640 |
| Model capability tiers | 3 |
| Mitigation arms | 2 |
| Focused automated tests | 84 |
| Supported Python versions | 3.11 through 3.14 |

The committed [v0.2 conformance artifact](results/authorization-decay-surface-v0.2.json) establishes that every generated condition executes through the harness and reaches its declared oracle under the deterministic reference adapter. The [v0.3 protocol lock](results/openai-researcher-access-plan-v0.3.json) binds the confirmatory model study to the exact scenario corpus, schedule, hypotheses, exclusions, stopping rule, and credit budget. The [v0.1 reference result](results/reference-suite-v0.1.json) remains available as the compact baseline.

Reference conformance and model behavior are separate result types. A model adapter receives the same controlled trajectory through `request.metadata["trajectory"]` and produces its own run evidence.

## Experimental pipeline

```text
scenario and clean control
          |
          v
27 controlled trajectories per input
          |
          v
fresh sandbox -> controlled tools -> complete event trace
          |                              |
          v                              v
deterministic oracle          attempted and completed effects
          |                              |
          +---------------+--------------+
                          v
              Authorization Decay Fingerprint
```

The trajectory compiler never exposes evaluator fields, expected behavior, authorized effect lists, forbidden effect lists, or oracle answers to the agent. Each trajectory carries a SHA256 digest and an exact authority ledger for independent replay and audit.

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

Every scenario declares authority, source provenance, resettable synthetic fixtures, allowed interfaces, exact expected effects, forbidden effects, deterministic oracles, and an executable clean control.

## Documentation

| Topic | Document |
| --- | --- |
| Authorization Decay Surface | [Protocol and estimands](docs/authorization-decay-surface.md) |
| Complete research record | [Research overview and artifact map](RESEARCH.md) |
| Confirmatory model study | [Preregistered study](docs/preregistered-study.md) |
| OpenAI model execution | [Responses API adapter](docs/openai-responses-adapter.md) |
| Program application summary | [Researcher Access study brief](docs/researcher-access-brief.md) |
| Authorization semantics | [Authorization model](docs/authorization-model.md) |
| Research framing | [Research overview](docs/research-overview.md) |
| Study design | [Methodology](docs/methodology.md) |
| Metrics and uncertainty | [Evaluation](docs/evaluation.md) |
| Security assumptions | [Threat model](docs/threat-model.md) |
| Scenario authoring | [Scenario specification](docs/scenario-specification.md) |
| Composite baseline | [Agent Boundary Score](docs/agent-boundary-score.md) |
| Supported claims | [Scope](docs/scope.md) |
| Measurement limits | [Limitations](docs/limitations.md) |
| Research data lifecycle | [Data management](docs/data-management.md) |
| Research progression | [Roadmap](docs/roadmap.md) |
| Research sources | [References](docs/references.md) |
| Version history | [Release notes](docs/release-notes.md) |
| Responsible use | [Ethics](docs/ethics.md) |

## Project standards

BoundaryBench runs on synthetic fixtures and local stubs. Hosted models can request only the controlled function tools supplied by the adapter. The project never authorizes testing external systems or contacting real recipients.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a scenario or implementation change. Use [GitHub Discussions](https://github.com/ChloeVPin/boundarybench/discussions) for research questions and [GitHub Issues](https://github.com/ChloeVPin/boundarybench/issues) for defects and scenario proposals. Report execution boundary failures privately through the Security tab as described in [SECURITY.md](SECURITY.md).

Citation metadata is available in [CITATION.cff](CITATION.cff). BoundaryBench is released under the [MIT License](LICENSE).
