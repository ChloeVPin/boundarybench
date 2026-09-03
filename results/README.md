# Results

This directory contains versioned result summaries that can be reproduced from committed experiment configurations.

`authorization-decay-surface-v0.2.json` is the deterministic conformance result for `experiments/authorization-decay-surface-v0.2.yaml`. It records 594 passing cases, all 27 factorial cells, the Authorization Decay Fingerprint, Wilson rate intervals, clustered effect intervals, and scenario-level primary and clean-control summaries.

`reference-suite-v0.1.json` is the deterministic harness conformance result for `experiments/reference-suite-v0.1.yaml`. It records all eleven primary scenarios, all eleven negative controls, every pair score, and the aggregate Agent Boundary Score.

Model evaluation bundles use the same result contract and identify the repository commit, scenario versions, harness version, model configuration, tool stubs, reset policy, exclusions, and per scenario oracle evidence. The command below creates descriptive JSON grouped by scenario, attack variant, model, and trajectory position.

The committed conformance artifacts describe deterministic harness behavior. Model result bundles should use a distinct filename and identify the model adapter in the artifact.

```bash
boundarybench report RUN_ROOT
```

Use `--format csv` for one row per metric. Nullable metrics remain null in aggregate calculations.
