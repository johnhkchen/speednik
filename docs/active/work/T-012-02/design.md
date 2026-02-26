# Design — T-012-02: Hillside Behavior Audit

## Decision: Test Structure

### Option A: One test per archetype (chosen)

Six individual test functions: `test_hillside_walker`, `test_hillside_jumper`, etc. Each calls
`run_audit("hillside", make_<archetype>(), expectation)` and asserts on findings.

**Pros:** Clear per-archetype failure reporting. Easy to mark individual tests as xfail.
**Cons:** Some boilerplate.

### Option B: Parametrized single test

`@pytest.mark.parametrize` over archetype/expectation pairs.

**Rejected:** xfail reasons differ per archetype. Parametrized xfail with `pytest.param(...,
marks=pytest.mark.xfail(reason="..."))` works but makes the test harder to read and modify.
The ticket says "6 archetype tests" — individual functions are clearest.

## Decision: Expectation Values

Use the ticket's aspirational expectations exactly:

| Archetype    | min_x  | max_deaths | goal? | max_frames | inv_errors_ok |
|--------------|--------|------------|-------|------------|---------------|
| Walker       | 4700   | 0          | yes   | 3600       | 0             |
| Jumper       | 4700   | 0          | yes   | 3600       | 0             |
| Speed Demon  | 4700   | 0          | yes   | 3600       | 0             |
| Cautious     | 2400   | 0          | no    | 3600       | 0             |
| Wall Hugger  | 2400   | 0          | no    | 3600       | 0             |
| Chaos        | 1200   | 2          | no    | 3600       | 0             |

`max_frames=3600` (60 seconds at 60fps) is generous for a tutorial level. `invariant_errors_ok=0`
is strict — any physics violation is a finding.

## Decision: xfail Strategy

Research shows these bugs:

1. **Wall at x≈601** — Tile (37,38) angle=64. Blocks Walker, Cautious, Wall Hugger. Prevents
   them from reaching min_x or goal. → xfail for Walker, Cautious, Wall Hugger.

2. **No boundary clamping** — Jumper reaches x=34023 (past level_width=4800), generating 5444
   position_x_beyond_right errors. Chaos reaches x=-49488, generating 10526 position_x_negative
   errors. → xfail for Jumper (invariant errors), Chaos (invariant errors + min_x).

3. **Speed Demon goal detection** — Speed Demon reaches goal at frame 737 (max_x=4738.2 <
   4700 threshold for goal_x=4758). If the sim correctly registers goal_reached=True, the
   min_x check might show max_x < 4700 depending on exact stopping position. Research shows
   Speed Demon *does* reach goal, so this should pass. 3 warnings won't count against 0
   invariant_errors_ok (only errors count). → expect PASS.

### xfail mapping:

| Archetype    | Expected result | xfail reason                                     |
|--------------|-----------------|--------------------------------------------------|
| Walker       | XFAIL           | BUG-01: wall at x≈601 blocks progress            |
| Jumper       | XFAIL           | BUG-02: no right boundary clamp → invariant flood |
| Speed Demon  | PASS            | —                                                |
| Cautious     | XFAIL           | BUG-01: wall at x≈601 blocks progress            |
| Wall Hugger  | XFAIL           | BUG-01: wall at x≈601 blocks progress            |
| Chaos        | XFAIL           | BUG-03: no left boundary clamp + insufficient drift |

## Decision: Bug Tickets

Create three bug tickets:

- **T-012-02-BUG-01** — Tile (37,38) has angle=64 (wall) where it should be a gentle slope (~2).
  Blocks Walker/Cautious/Wall Hugger at x≈601.
- **T-012-02-BUG-02** — No right boundary clamp. Jumper reaches x=34023 past level_width=4800.
- **T-012-02-BUG-03** — No left boundary clamp. Chaos reaches x=-49488.

## Decision: Assertion Style

Each test follows this pattern:
```python
findings, result = run_audit("hillside", archetype_fn, expectation)
bugs = [f for f in findings if f.severity == "bug"]
assert len(bugs) == 0, format_findings(findings)
```

The `format_findings()` output serves as the assertion message — exactly per the ticket's
acceptance criteria. This gives maximum diagnostic info on failure.

## Decision: Test File Organization

Single file `tests/test_audit_hillside.py` with:
1. Module-level expectation constants (one per archetype)
2. Six test functions in table order
3. No helper classes needed — `run_audit` handles everything

## Decision: Chaos Seed

Use seed=42 for deterministic reproducibility, matching the exploratory run. This ensures test
stability across runs.
