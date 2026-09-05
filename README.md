# BoundaryBench

A reproducible research harness for studying whether tool-using agents preserve authorization when context, repetition, and source provenance change.

## Research record

The repository contains two different kinds of evidence:

- The deterministic conformance harness runs 594 isolated cases across primary and clean-control scenarios.
- A locked v0.3 study plan describes 35,640 proposed model cases across three model tiers and two intervention arms. This checkout does not contain those model observations.

Read the research record in RESEARCH.md, the study brief in docs/researcher-access-brief.md, and the compiled plan in results/openai-researcher-access-plan-v0.3.json before interpreting a result.

## Start here

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

boundarybench validate scenarios
boundarybench stress   --output-root runs/authorization-decay-surface   --summary results/local-authorization-decay.json
```

Each stress case gets a fresh sandbox and a manifest, event stream, artifacts, oracle evidence, and final state. Hosted model collection is optional and requires provider credentials and review of the adapter contract.

## Explore and report

```sh
boundarybench inspect scenarios/filesystem/BB-FS-003-archive-traversal.yaml
boundarybench run scenarios/controls/BB-CTRL-002-benign-same-scope.yaml   --script examples/smoke-script.yaml   --output-root runs
boundarybench report runs
```

The analysis keeps task completion, authorization violations, matched controls, unknown observations, and mitigation effects separate. Unknown values are not treated as failures or successes.

## Development

```sh
pytest
```

See docs/ for the protocol, evidence standard, and collection limits.

## License

MIT. See LICENSE.
