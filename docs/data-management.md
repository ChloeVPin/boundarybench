# Data management

## Data classes

BoundaryBench produces four classes of research data:

| Class | Contents | Canonical format |
| --- | --- | --- |
| Protocol | Study configuration, scenario versions, hashes, randomization | YAML and JSON |
| Raw behavior | Model response, tool events, errors, final synthetic state | JSON and JSONL |
| Derived results | Per-case metrics, matched effects, confidence intervals | JSON |
| Human-readable record | Methods, interpretation, limitations, release notes | Markdown |

No real credentials, personal data, customer records, private repositories, or production endpoints belong in any class.

## Collection

Each case receives a new run directory with `manifest.json`, `events.jsonl`, `result.json`, and an `artifacts` directory. The manifest binds the observation to the scenario hash, model, provider, adapter, parameters, mitigation, seed, trajectory digest, environment, response identifiers, token usage, source fingerprint, and outcome. Runs from a Git checkout also record the repository revision.

API credentials remain in the process environment. They are neither passed through command arguments nor serialized by BoundaryBench.

## Integrity

The preregistration compiler hashes the study source and every scenario, derives a deterministic schedule, and emits a combined protocol lock. Raw cases remain immutable after collection. Corrections create a new derived artifact with documented code and provenance rather than rewriting the raw record.

Interrupted and excluded cases remain present. Unknown measurements remain null. A complete release includes the exact repository commit, a deterministic SHA256 fingerprint of all package source files, and the protocol lock digest. The source fingerprint remains available when the benchmark runs from an installed wheel without Git metadata.

## Retention and release

Synthetic raw traces, manifests, and derived tables can be released with the research artifact. Before publication, an automated secret scan and a manual review confirm that no local environment value, API credential, personal identifier, or provider dashboard detail entered the package.

Safety or security findings that could materially enable misuse are withheld from the public artifact until the applicable coordinated disclosure process permits release. Public results disclose enough method, configuration, and aggregate evidence for independent reproduction without exposing operational vulnerabilities.

## Authorship and AI assistance

Publications identify the human authors who take responsibility for the work. Any material role of AI in code, analysis, or drafting is disclosed accurately. Model outputs used as observations are labeled as such and remain separate from authored interpretation.
