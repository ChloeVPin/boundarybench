# Limitations

BoundaryBench v0.1 has material limitations:

- The corpus contains only eleven scenarios and cannot represent the space of authorization failures.
- Fixtures are synthetic and may not capture the ambiguity, incentives, or operational complexity of real systems.
- The common schema describes interfaces but does not standardize every harness detail, model configuration, or trace format.
- Deterministic final-state oracles can miss attempted actions, timing effects, hidden state, and side channels.
- Trace completeness depends on the harness. A missing trace is not evidence of no attempt.
- The bundled runner executes filesystem operations and a small set of local
  tool stubs; archive extraction, repository moves, and arbitrary provider
  adapters remain outside its v0.1 execution path.
- Negative controls reduce, but do not eliminate, the risk of measuring blanket refusal instead of boundary preservation.
- Scenario authors choose the authority boundary and payload; author judgment can introduce bias or accidental clues.
- ABS weights four components equally by default, although their importance may not be equal in every study.
- Results on this corpus do not establish generalization, causal explanations for authorization decay, or production safety.

These limitations are reasons to label conclusions narrowly, not reasons to invent precision. A future release should add independently authored scenarios, richer trace contracts, and documented pilot evidence before making stronger claims.
