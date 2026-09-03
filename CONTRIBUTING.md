# Contributing to BoundaryBench

Contributions should make authorization preservation easier to measure, reproduce, and challenge. The repository includes a small offline reference runner, but it is not a provider-specific autonomous-agent runtime.

## Adding a scenario

1. Read [the scenario specification](docs/scenario-specification.md), [the threat model](docs/threat-model.md), and [the methodology](docs/methodology.md).
2. Choose one category directory: `repository`, `filesystem`, `tools`, or `controls`.
3. Use a stable identifier with the category prefix (`BB-REPO`, `BB-FS`, `BB-TOOL`, or `BB-CTRL`) and a semantic scenario version.
4. State the authority grant and denial set independently from input provenance.
5. Describe the attacker entry point, strategy, goal, and payload without relying on a hidden runner behavior.
6. Make the fixture resettable and the oracle deterministic. Prefer exact paths, exact file contents, and exact tool-call records over judging prose.
7. Add a negative control that changes only the attack-relevant condition and states the expected clean outcome.
8. Add or update documentation when the common schema changes. Do not add scenario-specific runner code.

## Review expectations

Reviewers should check that a scenario has a plausible authorization boundary, a meaningful authorized task, an untrusted input that is clearly labeled, and an observable violation. They should look for accidental dependence on a particular model or system prompt, ambiguous path matching, hidden nondeterminism, and excessive fixture realism that could expose personal data.

Changes must not claim pilot results, model behavior, statistics, or citations that are not present in the repository's evidence. New aggregate results belong in a separately identified results artifact with its run manifest and provenance.

## Local checks

Scenario authors do not need a package manager or a particular runtime. Before submitting a change:

- parse every `scenarios/**/*.yaml` file with a YAML 1.2-compatible parser;
- check that every scenario has the required keys, a valid category/id prefix, and `schema_version: "0.1"`;
- check that every scenario has `evaluation.deterministic: true` and a `negative_control`; and
- inspect the diff for secrets, real personal data, fabricated results, or out-of-scope runner code.
- run `python -m pytest` and `boundarybench validate scenarios/` when changing
  the reference implementation or scenario corpus.
