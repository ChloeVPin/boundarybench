## Summary

Describe the exact behavior, scenario, or documentation change.

## Verification

List the commands run and their results.

```text
python -m pytest
ruff check .
ruff format --check .
boundarybench validate scenarios
boundarybench suite
python -m build
```

## Boundary review

- [ ] Authority and provenance remain separate.
- [ ] Fixtures contain synthetic data only.
- [ ] New scenarios include an executable negative control.
- [ ] Oracles are deterministic and inspect exact state or traces.
- [ ] Documentation and result claims match committed evidence.
