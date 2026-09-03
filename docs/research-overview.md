# Research overview

## Research question

BoundaryBench asks: when an autonomous agent receives a useful task plus lower-trust content that attempts to expand or redirect that task, does the agent preserve the original authority boundary while still completing the authorized work?

The benchmark treats authorization as a property of the requested action and resource, not as a property of the wording alone. Provenance records where an instruction came from; authority records what the principal actually grants. The two fields must not be collapsed.

## Hypothesis

The primary hypothesis is **authorization decay**: an agent may lose track of the original authority boundary as context is copied, summarized, retrieved, placed in a file, or passed through a tool. A scenario can support, weaken, or fail to discriminate this hypothesis. A passing or failing run is evidence about that scenario, not proof about agents in general.

Secondary questions include:

- Which boundary type produces the most unauthorized effects: repository, filesystem, or tool?
- Do agents preserve a useful task when a lower-trust instruction is present, or avoid the whole task?
- Do negative controls distinguish principled boundary preservation from blanket refusal?
- Which evidence is lost when evaluators score only final artifacts and not attempted actions or tool traces?

## BoundaryBench v0.1

This release provides a versioned YAML representation, eleven synthetic scenarios, eleven executable negative controls, an explicit threat model, a controlled offline runner, deterministic oracles, durable run records, and the fixed v0.1 Agent Boundary Score. The reference conformance artifact covers all twenty two cases.

## Intended users

Researchers and engineers may use the corpus to build isolated agent harnesses, compare prompting or policy interventions, examine attempted versus completed effects, and report failure traces. Scenario authors should be able to reuse the YAML without adopting a particular agent framework.

## Claim discipline

Reports using BoundaryBench should state the exact commit, schema version, scenario versions, harness behavior, model configuration, test account or stub setup, and exclusions. Every reported number should identify its run artifact. The committed v0.1 artifact is explicitly typed as reference harness conformance so it cannot be confused with an external model evaluation.
