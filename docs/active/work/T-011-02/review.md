# T-011-02 Review: physics-invariant-checker

## Summary of changes

### Files created

| File | Lines | Purpose |
|------|-------|---------|
| `speednik/invariants.py` | ~190 | Physics invariant checker library |
| `tests/test_invariants.py` | ~210 | Unit tests for the checker |

### Files modified

None.

## Architecture

`speednik/invariants.py` exports two public symbols:

- **`Violation`** — dataclass with `frame`, `invariant`, `details`, `severity`
- **`check_invariants(sim, snapshots, events_per_frame) -> list[Violation]`**

Internally, six private functions each check one invariant category and return
`list[Violation]`. The public function calls all six, concatenates, and sorts by frame.

A `SnapshotLike` Protocol allows the checker to accept any object with the right
attributes — both `tests.harness.FrameSnapshot` and `speednik.scenarios.runner.FrameRecord`
satisfy it automatically without import coupling.

## Acceptance criteria coverage

| Criterion | Status |
|-----------|--------|
| `Violation` dataclass with frame, invariant name, details, severity | Done |
| `check_invariants` detects player out of bounds (X and Y) | Done — 3 tests |
| `check_invariants` detects velocity spikes | Done — 4 tests |
| `check_invariants` detects player inside solid tile | Done — 2 tests |
| `check_invariants` detects impossible quadrant jumps | Done — 4 tests |
| Unit tests with synthetic violations (crafted FrameSnapshots) | Done — 15 violation tests |
| Unit tests with clean trajectories (assert 0 violations) | Done — 1 integration test |
| No Pyxel imports | Done — verified by test |
| `uv run pytest tests/test_invariants.py -x` passes | Done — 22/22 pass |

## Test coverage

22 tests across 8 test classes:

- `TestViolationDataclass` — 1 test: field access
- `TestPositionInvariants` — 4 tests: x<0, y>height+64, x>width+64, clean
- `TestSolidTileInvariant` — 2 tests: inside solid, above solid
- `TestVelocityInvariants` — 3 tests: x exceeds max, y exceeds max, normal
- `TestVelocitySpikes` — 4 tests: unexcused spike, spring excused, spindash excused, gradual
- `TestGroundConsistency` — 2 tests: no tile at feet, tile present
- `TestQuadrantJumps` — 4 tests: 0→2, 1→3, adjacent (clean), same (clean)
- `TestCleanTrajectory` — 1 test: 60-frame walk on flat ground → 0 violations
- `TestNoPyxelImport` — 1 test: source inspection

## Design decisions

1. **SnapshotLike Protocol** instead of importing `FrameSnapshot` from tests/ — keeps
   the package→test import boundary clean.

2. **Velocity spike excusal** via `SpringEvent` or spindash release (prev state was
   "spindash", current is not). Threshold: 12.0 per axis.

3. **Ground consistency** uses a lightweight check (tile at feet position) rather than
   reimplementing full sensor cast logic. Flagged as warning, not error.

4. **Dead state + rings check** omitted — `FrameSnapshot` doesn't carry ring count,
   making retroactive ring-at-damage validation impossible from snapshots alone. This
   is a known limitation documented in design.md.

## Open concerns

1. **Ground consistency false positives** — The lightweight feet-tile check may flag
   warnings during slope transitions or at tile boundaries where the real sensor logic
   finds a surface but our simplified check doesn't. These are warnings (not errors)
   so they won't break CI, but could be noisy. Monitor when integrated with scenario
   sweeps (T-011-06).

2. **Quadrant jump at 3→0 wrapping** — The `diff == 2` check handles the diagonal case
   correctly (|0-2|=2, |1-3|=2), but the wrap-around case (quadrant 3→1 via |3-1|=2)
   is also caught. The 3→0 transition (|3-0|=3) is NOT flagged as a diagonal jump,
   which is correct since 3→0 is adjacent on the cyclic ring. However, this doesn't
   handle three-step jumps like 0→3 (|0-3|=3), which could also indicate a glitch.
   In practice, such jumps are extremely rare and would be caught by other invariants.

3. **SnapshotLike and FrameRecord compatibility** — `FrameRecord` in
   `speednik/scenarios/runner.py` has matching field names (`x`, `y`, `x_vel`, etc.)
   and should satisfy the protocol, but this hasn't been explicitly tested. Will be
   validated when T-011-06 integrates the checker with scenario runs.
