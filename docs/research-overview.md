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

## BoundaryBench v0.2

This release adds the Authorization Decay Surface to the versioned scenario corpus and controlled runtime. The protocol turns every scenario into 27 matched conditions spanning position, repetition pressure, and provenance visibility. Eleven primary scenarios and eleven clean controls produce 594 isolated cases per trial.

The central output is a fingerprint rather than one rank. It reports attack-control, provenance, position, and repetition effects alongside utility, worst-cell behavior, uncertainty intervals, and complete scenario evidence. The v0.1 Agent Boundary Score remains available as a compact baseline.

## BoundaryBench v0.3

Version 0.3 makes the model study executable and preregistered. The Responses API adapter preserves trajectory order, attaches the authority ledger, disables provider storage, and exposes only the benchmark's local controlled tools. A deterministic compiler locks the study source, scenario corpus, 35,640-case randomization schedule, hypotheses, exclusions, stopping rule, and $1,000 resource plan.

The registered comparison spans three model capability tiers and two arms. The authority-checkpoint arm repeats the fact that authority has not changed at neutral trajectory checkpoints. Mitigation analysis reports the attack benefit, clean-control utility effect, and matched difference in differences separately.

## Intended users

Researchers and engineers may use the corpus to run isolated model studies, compare prompting or policy interventions, examine attempted versus completed effects, and report failure traces. Scenario authors can reuse the YAML without adopting a particular agent framework.

## Claim discipline

Reports using BoundaryBench should state the exact commit, schema version, scenario versions, harness behavior, model configuration, test account or stub setup, and exclusions. Every reported number should identify its run artifact. Committed artifacts are explicitly typed as reference harness conformance so they cannot be confused with an external model evaluation.
