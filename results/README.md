# Results

This directory contains versioned result summaries that can be reproduced from committed experiment configurations.

`reference-suite-v0.1.json` is the deterministic harness conformance result for `experiments/reference-suite-v0.1.yaml`. It records all eleven primary scenarios, all eleven negative controls, every pair score, and the aggregate Agent Boundary Score.

Model evaluation bundles use the same result contract and identify the repository commit, scenario versions, harness version, model configuration, tool stubs, reset policy, exclusions, and per scenario oracle evidence. The command below creates descriptive JSON grouped by scenario, attack variant, model, and trajectory position.

```bash
boundarybench report RUN_ROOT
```

Use `--format csv` for one row per metric. Nullable metrics remain null in aggregate calculations.
