# Ethics

BoundaryBench is intended to improve understanding of authorization preservation without exposing people or systems to unnecessary risk.

## Safety commitments

- Use synthetic fixtures, local sandboxes, and stubbed tools by default.
- Do not place real secrets, personal data, customer records, or live credentials in a scenario.
- Disable network and external side effects unless a separately approved study requires them and uses test accounts.
- Keep attacker payloads bounded and focused on authorization confusion, not destructive behavior.
- Record only the telemetry needed to evaluate the declared oracle.
- Report failures privately when a fixture or harness could cause unintended real-world effects.

## Human subjects and model studies

An agent run is not automatically a human-subject study, but researchers remain responsible for their institutional and platform requirements. Do not collect personal information from participants merely to operate a benchmark. If human raters are used for supplemental analysis, obtain appropriate consent and keep their judgments separate from the deterministic core oracle.

## Responsible interpretation

A boundary failure is a property of a run in a controlled setup. It is not evidence that a model is malicious, and a pass is not evidence that the model is safe. Publish limitations, failed or incomplete runs, scenario selection rules, and any changes made after observing results. Do not optimize the corpus around a preferred model or suppress negative controls because they lower a headline score.
