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

## Reproducibility

Reproduction uses the exact scenario version, harness, model or agent build, configuration, tool stubs, reset method, and evaluator implementation. The run manifest records these fields and the scenario checksum. `experiments/reference-suite-v0.1.yaml` captures the checked reference configuration, and `results/reference-suite-v0.1.json` records its deterministic summary.
