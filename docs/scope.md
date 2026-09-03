# Scope

BoundaryBench v0.2 measures authorization preservation and controlled authorization decay in a synthetic environment. Its conclusions are tied to the named scenario corpus, runner, agent configuration, factorial condition, and recorded trace.

## Covered behavior

The corpus covers repository content, filesystem paths, archive members, synthetic secrets, tool recipients, issue visibility, repeated pressure, and clean refusal controls. The Authorization Decay Surface adds controlled variation in instruction position, repetition, and provenance visibility. The runner supports exact reads, writes, delegated moves, safe archive extraction, approved local commands, local document queries, synthetic endpoint records, email stubs, and issue stubs.

Each run begins from a fresh fixture and records attempted effects, completed effects, tool calls, final state, agent output, and deterministic oracle evidence. The bundled scripted adapter declares a complete effect trace, which allows the evaluator to distinguish an absent unsafe effect from missing telemetry.

## Claim boundary

Results describe behavior on these eleven primary scenarios, their clean controls, and the declared factorial interventions. They do not certify production safety, guarantee behavior on unseen tasks, or authorize testing any external service. The fixtures are synthetic and the tools do not deliver real messages or modify live projects.

ABS is a corpus level summary. Reviewers should also inspect the component scores, individual oracles, event traces, and any completed unauthorized effect. A model study should publish the model configuration, prompt wrapper, mitigation, trial count, exclusions, and source commit with its results.

## Extension rules

New scenarios can extend the corpus when they preserve deterministic reset, explicit authority, labeled provenance, a machine readable oracle, and an executable negative control. Changes to factor semantics, outcome definitions, or required fields receive a new protocol version.
