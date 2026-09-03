# Architecture decision 0001: deterministic trajectory compiler

Status: accepted

Date: 2026-09-03

## Context

BoundaryBench needed to measure authorization behavior across position, repetition, and provenance interventions without changing the underlying task or authority. The design also had to remain provider neutral, replayable, compact, and resistant to evaluator leakage.

## Decision

Generate experiment trajectories from the existing scenario corpus with a deterministic compiler.

The scenario YAML remains the authoritative source for task, authority, provenance, fixtures, and oracles. The compiler receives a validated scenario and one typed factorial condition. It emits only model visible messages, the authority ledger, condition metadata, and a digest.

The runner carries this object in request metadata and stores it in the run manifest. Provider adapters decide how to map the ordered messages into their native API without changing the experimental condition.

## Alternatives considered

### Duplicate every condition in YAML

This would create 297 primary scenario documents before controls or repeated trials. Duplication would make authority drift and inconsistent fixes likely. Reviewers would have to compare large files to establish that only one factor changed.

### Generate variants with a language model

Model generated transformations would add semantic drift, nondeterminism, and a second model dependency to the independent variable. Exact replay would become difficult and attack strength could change across cells.

### Embed evaluator fields in the adapter prompt

This would leak expected outcomes and create a grader gaming path. It would also entangle provider prompts with scenario internals.

## Consequences

The selected design gives every condition a stable identifier and content digest. A full experiment can be regenerated from eleven source scenarios. Automated checks can prove that authority is held constant and evaluator fields remain absent.

Provider adapters must explicitly consume the trajectory metadata. This keeps the core API backward compatible and makes adapter behavior visible in research reports.
