# Limitations

## Synthetic environments

BoundaryBench favors exact attribution over production realism. Its files, secrets, recipients, endpoints, and project objects are synthetic. Real integrations add identity systems, network behavior, user interfaces, latency, retries, and provider policies that can change agent behavior.

## Corpus coverage

The current corpus contains eleven primary scenarios across repository, filesystem, tool, and control categories. The Authorization Decay Surface creates controlled variants of those scenarios, but additional cells do not create additional base tasks. Reported effects therefore describe this corpus.

## Trajectory abstraction

Early, middle, and late positions use four neutral checkpoints. They isolate recency and placement cleanly, but they are shorter than many production trajectories. They do not reproduce context summarization, multi-agent delegation, memory retrieval, or hundreds of stateful actions.

## Provider and adapter effects

Model providers differ in message roles, tool schemas, tokenization, safety layers, and sampling controls. An adapter's translation of the model visible trajectory can affect results. Research reports must identify the adapter commit and the exact model build.

## Nondeterminism and cost

Hosted models may vary across repeated calls and silent provider revisions. One trial is useful for harness conformance but weak evidence for model comparison. Model studies should choose repeated trials before execution and preserve failed or interrupted runs. Trial count may be constrained by cost and rate limits.

## Evaluator boundaries

Deterministic oracles are strong for exact state and tool effects. They can miss unsafe reasoning that never becomes an observable action. Semantic judgments are kept separate because judge prompts and judge models introduce another source of error.

## Attribution

A failed run can arise from model reasoning, adapter translation, tool semantics, fixture setup, policy matching, provider behavior, or incomplete telemetry. BoundaryBench preserves these layers so researchers can diagnose them, but an aggregate number alone cannot identify the cause.

## Contamination and gaming

Public scenarios may enter model training data. An agent can also learn stable checkpoint wording, condition identifiers, or reference scripts. Held-out scenarios, alternate neutral checkpoints, and private replication sets are appropriate for confirmatory studies. The model visible trajectory excludes oracle and expected behavior fields to reduce direct grader gaming.

## Statistical interpretation

Wilson and clustered bootstrap intervals quantify uncertainty in observed rates and matched corpus effects. The scenarios are designed cases rather than a random sample from all agent tasks. These intervals do not justify population-wide safety claims.
