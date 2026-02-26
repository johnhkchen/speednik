# Plan: T-012-08 — loop-traversal-audit

## Step 1: Create `tests/test_loop_audit.py`

Write the complete audit test file with:

### Infrastructure (top of file)

1. Module docstring with test table
2. Imports: `speednik.grids`, `speednik.simulation`, `speednik.terrain`,
   `speednik.physics`, `speednik.player`, `pytest`
3. Constants: `GROUND_ROW = 20`, `GROUND_Y = GROUND_ROW * TILE_SIZE - 20`
4. `LoopAuditSnap` dataclass (frame, x, y, ground_speed, on_ground, quadrant,
   angle, state)
5. `LoopAuditResult` dataclass with helper properties
6. `format_loop_diagnostic()` function
7. `_spindash_strategy()` — returns strategy function
8. `_hold_right_strategy()` — simple hold-right for speed sweep tests
9. `_run_loop_audit(sim, strategy, frames)` → `LoopAuditResult`

### Test class: TestSyntheticLoopTraversal

Parameterized by radius [32, 48, 64, 96].

- `_build_and_run(radius)`: builds loop, creates sim, runs audit
- `test_all_quadrants_grounded(radius)`: asserts `grounded_quadrants == {0,1,2,3}`
  - r=32: `xfail(strict=True, reason="T-012-06-BUG-01: r=32 too small...")`
  - r=48, 64, 96: no xfail (expected to pass)
- `test_exit_positive_speed(radius)`: asserts positive ground_speed past loop
  - r=32, 48: no xfail
  - r=64, 96: `xfail(strict=True, reason="T-012-06-BUG-02: large-radius exit")`
- `test_exit_on_ground(radius)`: asserts on_ground past loop exit
  - r=32, 48: no xfail
  - r=64, 96: `xfail(strict=True, reason="T-012-06-BUG-02...")`

### Test class: TestSyntheticLoopSpeedSweep

Parameterized by speed [4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
at fixed radius=48.

- Uses direct speed injection: `sim.player.physics.ground_speed = speed`,
  `sim.player.physics.x_vel = speed`
- Hold-right strategy (no spindash — we're testing the speed itself)
- Asserts `grounded_quadrants == {0, 1, 2, 3}`
- xfail for speeds that don't complete: 4.0, 6.0, 7.0, 9.0, 10.0, 11.0, 12.0
  (only 5.0 and 8.0 pass based on research)
- xfail reason: documents the speed sensitivity characteristic

### Test class: TestHillsideLoopTraversal

- `test_hillside_loop_all_quadrants_grounded()`:
  - `create_sim("hillside")`, set x=3100, y=610
  - Spindash strategy, 600 frames
  - Assert `grounded_quadrants == {0, 1, 2, 3}`
  - xfail: `T-012-08-BUG-01: hillside loop geometry traps player in Q1`

- `test_hillside_loop_exits()`:
  - Same setup
  - Assert `max_x > 3744` (past loop region)
  - xfail: `T-012-08-BUG-01`

### Verification

```bash
uv run pytest tests/test_loop_audit.py -v
```

Expected: All tests either pass or xfail. No unexpected failures.

## Step 2: Create bug ticket `T-012-08-BUG-01`

File: `docs/active/tickets/T-012-08-BUG-01.md`

Content:
- YAML frontmatter: id, story, title, type=bug, status=open, priority=high,
  phase=ready, depends_on=[]
- Summary: hillside loop not traversable — player stuck in Q1 oscillation
- Diagnostic evidence from audit test output
- Probable cause: hand-placed tile geometry has non-smooth angle transitions

## Step 3: Run full test suite verification

```bash
uv run pytest tests/test_loop_audit.py tests/test_mechanic_probes.py -v
```

Verify no conflicts between audit tests and mechanic probes.

## Testing Strategy

### Test categories

| Category | File | Method |
|----------|------|--------|
| Synthetic traversal | test_loop_audit.py | Grounded quadrant assertion |
| Speed sweep | test_loop_audit.py | Direct speed injection |
| Real stage | test_loop_audit.py | Hillside loop probe |

### Pass/fail expectations

| Test | Expected |
|------|----------|
| synthetic r=32 traversal | XFAIL |
| synthetic r=48 traversal | PASS |
| synthetic r=64 traversal | PASS |
| synthetic r=96 traversal | PASS |
| synthetic r=32,48 exit | PASS |
| synthetic r=64,96 exit | XFAIL |
| speed sweep 5.0 | PASS |
| speed sweep 8.0 | PASS |
| speed sweep others | XFAIL |
| hillside traversal | XFAIL |
| hillside exit | XFAIL |

## Commit Plan

Single commit: add `tests/test_loop_audit.py` + bug ticket
