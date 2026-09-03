# Release notes

## Version 0.2.0

BoundaryBench v0.2.0 introduces the Authorization Decay Surface, a causal stress protocol for locating authorization failures across an agent trajectory.

### Research protocol

The release adds a deterministic 3 by 3 by 3 trajectory compiler spanning early, middle, and late injection; one, three, and five presentations; and explicit, source-only, and flattened provenance. Paired clean controls preserve task utility measurement in every cell.

The new Authorization Decay Fingerprint reports four matched effects, complete cell rates, worst-cell safe completion, Wilson intervals, and scenario-clustered bootstrap intervals. Unknown observations remain explicit.

### Runtime and evidence

The `boundarybench stress` command runs the complete protocol and stores the model visible trajectory in each manifest. Trajectories carry stable condition identifiers, exact authority ledgers, and SHA256 content digests. Runner-owned sandbox and tool metadata cannot be replaced by an adapter.

### Verification

The committed v0.2 conformance artifact records 594 passing deterministic oracle cases across all eleven primary scenarios, eleven clean controls, and 27 factorial conditions. The automated suite contains 69 focused tests and CI validates the full stress artifact on Python 3.14 alongside the package matrix for Python 3.11 through 3.14.

## Version 0.1.0

BoundaryBench v0.1.0 establishes a complete offline reference release for authorization preservation research.

### Corpus

The release contains eleven primary scenarios across repository, filesystem, tool, and control categories. Every primary scenario has an executable clean negative control, producing twenty two deterministic reference cases.

### Runtime

The Python package provides typed scenario loading, fail closed policy decisions, isolated filesystem areas, synthetic secret checks, controlled tool interfaces, event instrumentation, durable run records, deterministic oracles, result aggregation, and the fixed v0.1 Agent Boundary Score.

The controlled operation set includes reads, writes, directory listing, exact delegated moves, traversal safe archive extraction, approved nonnetworking commands, local document queries, synthetic endpoint records, email stubs, and private issue stubs.

### Verification

The committed reference result records twenty two passing cases. Continuous integration validates Python 3.11 through 3.14, executes the automated test suite, checks formatting and lint rules, regenerates the reference summary, builds both distribution formats, installs the wheel, and validates the scenario corpus from the installed command.

### Project files

The repository includes contribution guidance, issue forms, a pull request template, a code of conduct, a security policy, citation metadata, dependency update configuration, research references, and complete release documentation.
