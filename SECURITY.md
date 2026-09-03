# Security policy

BoundaryBench is a research benchmark. Its scenarios use synthetic repositories, paths, and tool interfaces; they are not authorization to test any external service or to contact real recipients.

## Reporting a benchmark security issue

If you find a secret, real personal data, an unsafe executable fixture, or a scenario that could cause an evaluator to perform an unintended external action, do not reproduce it against a live target. Remove local copies where practical and report the issue privately to the repository maintainers through the project channel configured by the deployment using this corpus.

Include the affected file, the unsafe field or behavior, reproduction steps limited to the local fixture, and any suggested containment. Do not include live credentials or private data in a report.

## Scope boundaries

The benchmark does not authorize probing, exploitation, password testing, social engineering, data access, or tool calls against third-party systems. A harness must use isolated fixtures and test accounts or stubbed tools. External side effects should be disabled by default.
