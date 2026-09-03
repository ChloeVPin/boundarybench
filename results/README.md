# Results

This directory contains versioned result summaries that can be reproduced from committed experiment configurations.

`openai-researcher-access-plan-v0.3.json` is the preregistered protocol lock for `experiments/openai-researcher-access-v0.3.yaml`. It records all 35,640 planned cases, the SHA256 of every scenario, the randomized schedule digest, confirmatory hypotheses, exclusions, stopping rule, responsible-research commitments, and the model-level API credit budget.

`authorization-decay-surface-v0.2.json` is the deterministic conformance result for `experiments/authorization-decay-surface-v0.2.yaml`. It records 594 passing cases, all 27 factorial cells, the Authorization Decay Fingerprint, Wilson rate intervals, clustered effect intervals, and scenario-level primary and clean-control summaries.

`reference-suite-v0.1.json` is the deterministic harness conformance result for `experiments/reference-suite-v0.1.yaml`. It records all eleven primary scenarios, all eleven negative controls, every pair score, and the aggregate Agent Boundary Score.

Model evaluation bundles use the same result contract and identify the repository commit, scenario versions, harness version, model configuration, tool stubs, reset policy, exclusions, and per scenario oracle evidence. The command below creates descriptive JSON grouped by scenario, attack variant, model, and trajectory position.

The committed conformance artifacts describe deterministic harness behavior. Model result bundles should use a distinct filename and identify the model adapter in the artifact.

Recompile and compare the v0.3 protocol lock:

```bash
boundarybench plan experiments/openai-researcher-access-v0.3.yaml \
  --output /tmp/openai-researcher-access-plan-v0.3.json
python -c "import json; from pathlib import Path; expected=json.loads(Path('results/openai-researcher-access-plan-v0.3.json').read_text()); actual=json.loads(Path('/tmp/openai-researcher-access-plan-v0.3.json').read_text()); assert actual == expected"
```

```bash
boundarybench report RUN_ROOT
```

Use `--format csv` for one row per metric. Nullable metrics remain null in aggregate calculations.
