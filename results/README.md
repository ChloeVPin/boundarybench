# Results directory

No pilot or benchmark results are included in this repository. This directory documents the expected reporting location for future, separately generated artifacts.

A result bundle should identify the repository commit, scenario IDs and versions, schema version, harness and evaluator versions, model configuration, tool stubs, reset policy, exclusions, and per-scenario oracle evidence. Aggregate values such as ABS are uninterpretable without that manifest and must not be backfilled from missing runs.

The reference `boundarybench report RUN_ROOT` command emits descriptive JSON
for the overall set and breakdowns by scenario, attack variant, model, and
trajectory position. It preserves nullable metrics and does not run
significance tests.
