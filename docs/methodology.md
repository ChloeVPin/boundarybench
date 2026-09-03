# Methodology

## Design principles

Scenarios are deliberately small enough to reset and inspect, but substantive enough to contain a useful task and a competing unauthorized path. Every scenario separates four questions:

1. What action is useful and authorized?
2. Which sources are trusted for that decision?
3. What strategy attempts to expand, redirect, or disguise authority?
4. What exact state or trace proves the outcome?

The corpus uses synthetic data, explicit paths, and stubbed tool interfaces. It avoids requiring a particular prompt template or runner implementation.

## Run protocol

An evaluator should:

1. Pin the scenario file and its `version`.
2. Reset the complete declared fixture.
3. Supply the trusted task and all declared untrusted sources through the harness's documented interface.
4. Allow only the interfaces listed by the harness for the scenario.
5. Record attempted and completed effects, tool calls, agent output, and final fixture state.
6. Evaluate the declared oracle without changing the fixture.
7. Reset and run the negative control as a separate case.
8. Preserve a manifest containing scenario IDs, versions, schema version, harness version, model settings, and tool stubs.

## Outcome dimensions

The minimum report should distinguish:

- authorized task completion;
- unauthorized attempt, even if blocked;
- unauthorized completed effect;
- provenance handling, meaning whether untrusted content was treated as authority; and
- negative-control completion.

Final-state-only scoring can miss blocked attempts, so traces should be retained where the harness can capture them. An evaluator must not infer an attempt from a missing artifact.

## Controls and bias checks

Negative controls are clean variants where the useful action remains authorized and the attack-relevant input is removed or made benign. They test for over-refusal and for accidental fixture failures. Results should be stratified by category and reported with scenario-level traces. A single aggregate score must not conceal a severe unauthorized effect.

Authors should review each scenario for ambiguous authority wording, accidental clues, unrealistic tool semantics, and hidden dependence on a specific model. The v0.1 core accepts scenarios only when the bundled evaluator can establish the declared outcome deterministically.

## Authorization Decay Surface protocol

Version 0.2 adds a preregistered 3 by 3 by 3 factorial protocol. It changes attack position, repetition pressure, and provenance visibility while holding the task, authority ledger, fixture, tools, and oracle fixed. Every primary run has a clean control in the same cell.

The independent variables and matched contrasts are defined before execution in [Authorization Decay Surface](authorization-decay-surface.md). Job order is deterministically pseudorandomized from the experiment seed. Every compiled trajectory has a stable condition ID and content digest.

The protocol separates three evidence layers:

1. Model behavior consists of responses, attempted actions, completed actions, and final state.
2. Harness behavior consists of trajectory compilation, sandbox isolation, tool enforcement, and event capture.
3. Evaluator behavior consists of deterministic oracle execution and statistical aggregation.

The agent receives the first layer's task context and authority ledger. It never receives expected behavior or oracle fields.

## Reproducibility

Reproduction uses the exact scenario version, harness, model or agent build, configuration, tool stubs, reset method, and evaluator implementation. The run manifest records these fields, the scenario checksum, trajectory condition, and trajectory digest. `experiments/authorization-decay-surface-v0.2.yaml` captures the full protocol configuration, and `results/authorization-decay-surface-v0.2.json` records its deterministic conformance summary.

## Preregistered model study

Version 0.3 adds a study-level protocol above individual experiment runs. The compiler validates the selected factor levels, model and arm identifiers, trial count, price assumptions, exclusions, stopping rule, and responsible-research commitments. It loads and validates every scenario, records each scenario hash, expands the complete model by arm by condition schedule, randomizes that schedule deterministically, and emits one combined protocol lock.

The registered design runs ten trials for every scenario, clean control, factorial cell, model, and mitigation arm. The resulting 35,640 cases are fixed before behavior collection. The declared case count must agree with the compiled design, and the rounded request must remain within the funding ceiling.

## Hosted model execution

The Responses API adapter maps the policy trajectory message to a developer message and renders source metadata into the corresponding model-visible content. It sends the canonical authority ledger with the first policy message. Model-selected calls are limited to the same local controlled tools used by deterministic conformance runs.

Each provider response disables storage. Function calls run sequentially, and the adapter returns structured success or denial records so a model can recover from a blocked request. Response identifiers, cumulative token usage, model parameters, tool rounds, and mitigation enter the run manifest. API credentials remain in the process environment and are not serialized.
