# Contributing to BoundaryBench

Contributions should make authorization preservation easier to measure, reproduce, and challenge. The repository includes a complete offline reference path and a provider neutral adapter contract.

## Adding a scenario

1. Read [the scenario specification](docs/scenario-specification.md), [the threat model](docs/threat-model.md), and [the methodology](docs/methodology.md).
2. Choose one category directory: `repository`, `filesystem`, `tools`, or `controls`.
3. Use a stable identifier with the category prefix (`BB-REPO`, `BB-FS`, `BB-TOOL`, or `BB-CTRL`) and a semantic scenario version.
4. State the authority grant and denial set independently from input provenance.
5. Describe the attacker entry point, strategy, goal, and payload without relying on a hidden runner behavior.
6. Make the fixture resettable and the oracle deterministic. Prefer exact paths, exact file contents, and exact tool-call records over judging prose.
7. Add an executable negative control that changes only the attack relevant condition and states the expected clean outcome.
8. Add or update documentation when the common schema changes. Do not add scenario-specific runner code.

## Review expectations

Reviewers should check that a scenario has a plausible authorization boundary, a meaningful authorized task, an untrusted input that is clearly labeled, and an observable violation. They should look for accidental dependence on a particular model or system prompt, ambiguous path matching, hidden nondeterminism, and excessive fixture realism that could expose personal data.

Claims about model behavior, statistics, or citations must match committed evidence. New aggregate results belong in a separately identified result artifact with its run manifest and provenance.

## Local checks

Run the complete local verification set before submitting a change:

```bash
python -m pytest --cov=boundarybench --cov-fail-under=80
ruff check .
ruff format --check .
boundarybench validate scenarios
boundarybench suite
boundarybench stress --summary /tmp/authorization-decay-surface-v0.2.json
boundarybench plan experiments/openai-researcher-access-v0.3.yaml \
  --output /tmp/openai-researcher-access-plan-v0.3.json
python -m build
```

Inspect the final diff for credentials, personal data, unsupported claims, and accidental changes outside the contribution scope. The pull request template records this review.
