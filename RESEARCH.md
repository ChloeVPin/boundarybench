# BoundaryBench research record

## Abstract

Autonomous agents increasingly act across repositories, filesystems, tools, and external context. The information they encounter can be useful without carrying permission to change the task. BoundaryBench studies whether an agent can preserve that distinction.

The benchmark measures authorization preservation independently from task completion. Its Authorization Decay Surface holds the task, authority ledger, tools, fixture, and deterministic oracle constant while varying three properties of an untrusted instruction: position, repetition, and visible provenance. Every attack case has a matched clean control, so a system cannot appear safe merely by refusing useful work.

BoundaryBench v0.3 adds a complete model-study path. A Responses API adapter gives models access only to synthetic, locally enforced tools. A preregistration compiler locks the scenario corpus, experimental factors, trial count, randomized schedule, analysis commitments, and resource budget before model observations are collected. The registered study contains 35,640 cases across three model capability tiers and two mitigation arms within a $1,000 API credit request.

## Research question

When a tool-using language model receives untrusted information during a legitimate task, which changes in context cause it to lose the original authorization boundary, and can a lightweight authority checkpoint prevent that loss without reducing useful task completion?

## Contribution

BoundaryBench contributes a controlled way to localize authorization failures rather than treating prompt injection as one binary event.

| Research requirement | BoundaryBench mechanism |
| --- | --- |
| Separate capability from safety | Task completion and authorization violations are independent outcomes |
| Detect over-refusal | Every attack condition has a matched clean control |
| Attribute failure pressure | Position, repetition, and provenance vary independently |
| Observe actions | Controlled tools record attempted, denied, and completed effects |
| Avoid evaluator leakage | Model-visible trajectories exclude expected behavior and oracle fields |
| Preserve uncertainty | Unknown observations remain outside denominators |
| Support audit | Scenario, trajectory, schedule, source, and protocol digests are recorded |
| Bound research risk | Fixtures, secrets, endpoints, projects, and recipients are synthetic |

## Registered model study

The [study specification](experiments/openai-researcher-access-v0.3.yaml) commits to:

* eleven primary scenarios and eleven matched clean controls;
* twenty-seven factorial conditions per scenario;
* ten repeated trials per cell;
* three current OpenAI model capability tiers;
* baseline and authority-checkpoint arms;
* 35,640 isolated cases;
* scenario-clustered uncertainty estimates;
* explicit exclusions and stopping rules; and
* a $1,000 credit ceiling.

Compile the study before collection:

```bash
boundarybench plan experiments/openai-researcher-access-v0.3.yaml \
  --output results/openai-researcher-access-plan-v0.3.json
```

The compiled artifact records a protocol lock digest. Any change to the study file, scenario corpus, or randomized schedule produces a different digest.

## Evidence layers

BoundaryBench keeps four evidence layers separate:

1. Harness conformance establishes that isolation, controlled tools, trajectory construction, oracles, and aggregation behave as specified.
2. Model behavior records responses, tool requests, denied effects, completed effects, token use, and final state for a named model configuration.
3. Confirmatory analysis estimates the preregistered contrasts without altering exclusions after outcomes are observed.
4. External validity is addressed through held-out scenarios and independent replication rather than broad claims from a designed corpus.

The committed v0.2 result is a deterministic harness conformance artifact. The v0.3 protocol lock is the registered design for model behavior collection. These artifact types cannot be confused in the machine-readable output.

The `boundarybench compare-mitigation` command reconstructs both collection arms from their immutable manifests and results, rejects unmatched designs, and emits the registered arm fingerprints and mitigation estimands as one machine-readable artifact.

## Reproducibility package

| Artifact | Location |
| --- | --- |
| Research protocol | [Preregistered study](docs/preregistered-study.md) |
| Compiled protocol lock | [v0.3 study plan](results/openai-researcher-access-plan-v0.3.json) |
| Provider adapter | [Responses API adapter](docs/openai-responses-adapter.md) |
| Measurement model | [Evaluation](docs/evaluation.md) |
| Scenario schema | [Scenario specification](docs/scenario-specification.md) |
| Data handling | [Data management](docs/data-management.md) |
| Responsible use | [Ethics](docs/ethics.md) |
| Application summary | [Researcher Access study brief](docs/researcher-access-brief.md) |

## Research integrity

BoundaryBench does not infer safety from task completion, convert missing telemetry into success, treat designed scenarios as a population sample, or publish sensitive failure details before coordinated disclosure. Model identifiers, parameters, prompts, adapter revision, exclusions, usage, and funding are part of the research record.
