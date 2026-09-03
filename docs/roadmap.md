# Roadmap

This roadmap is a proposal. It records intended research work, not completed work.

## v0.1, current artifact

- Define the versioned YAML scenario contract.
- Publish the initial synthetic scenario corpus across repository, filesystem,
  tool, and control boundaries.
- Document threat model, methodology, evaluation, ethics, limitations, and experimental ABS.
- Provide the offline scripted-agent runner, controlled filesystem sandbox,
  instrumented local tools, deterministic core oracles, and JSON/JSONL run
  records.

## Candidate v0.2 work

- Extend the reference harness with additional isolated tool stubs and complete
  evaluation for the corpus's interface-specific oracles.
- Add machine-readable schema validation and fixture checks without embedding runner logic in scenario files.
- Expand independently authored scenarios and test inter-rater review of authority and provenance labels.
- Standardize attempt-trace events and partial/inconclusive run reporting.

## Candidate pilot work

- Pre-register scenario selection, weights, models, prompts, and stopping rules before execution.
- Run the negative controls and attack variants from clean resets.
- Inspect failure traces manually and publish exclusions with reasons.
- Test whether the data distinguish authorization decay from simpler explanations such as over-refusal, fixture confusion, or tool-interface errors.

## Longer-term questions

- How well do results transfer across harnesses and agent architectures?
- Which interventions preserve useful work without increasing unauthorized attempts?
- Can severity-aware reporting complement a single scalar without obscuring rare high-impact failures?

No pilot result or statistic is implied by this roadmap.
