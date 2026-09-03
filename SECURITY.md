# Security policy

BoundaryBench is a research benchmark. Its scenarios use synthetic repositories, paths, and tool interfaces; they are not authorization to test any external service or to contact real recipients.

## Reporting a benchmark security issue

If you find a secret, real personal data, an unsafe executable fixture, or behavior that can escape the controlled environment, do not reproduce it against a live target. Report it privately through a [GitHub security advisory](https://github.com/ChloeVPin/boundarybench/security/advisories/new).

Include the affected version, file, unsafe field or behavior, local reproduction steps, impact, and suggested containment. Do not include live credentials or private data.

## Scope boundaries

The benchmark does not authorize probing, exploitation, password testing, social engineering, data access, or tool calls against third-party systems. A harness must use isolated fixtures and test accounts or stubbed tools. The bundled Responses API adapter exposes only local controlled functions and disables provider response storage.
