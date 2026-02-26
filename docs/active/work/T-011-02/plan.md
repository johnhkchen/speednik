# T-011-02 Plan: physics-invariant-checker

## Step 1: Create `speednik/invariants.py` with Violation and Protocol

- Define `Violation` dataclass
- Define `SnapshotLike` Protocol
- Define module-level constants (MAX_VEL, SPIKE_THRESHOLD, POSITION_MARGIN)
- Stub `check_invariants()` that returns empty list

Verify: module imports without error, no Pyxel.

## Step 2: Implement position bound checks

- `_check_position_bounds(sim, snapshots)` — x<0, y>level_height+64, x>level_width+64

Verify: unit tests for each boundary violation + clean case.

## Step 3: Implement solid tile check

- `_check_inside_solid(sim, snapshots)` — player center inside FULL tile

Verify: unit test with synthetic tile_lookup that returns a FULL tile at known position.

## Step 4: Implement velocity limit checks

- `_check_velocity_limits(snapshots)` — |x_vel|>20, |y_vel|>20

Verify: unit tests with extreme velocities + normal velocities.

## Step 5: Implement velocity spike checks

- `_check_velocity_spikes(snapshots, events_per_frame)` — delta > 12.0/axis
- Excusal logic: SpringEvent in events, or prev state=="spindash" and curr!="spindash"

Verify: tests for unexcused spike, spring-excused spike, spindash-excused spike, gradual.

## Step 6: Implement ground consistency check

- `_check_ground_consistency(sim, snapshots)` — on_ground with no tile below

Verify: unit test with on_ground=True over empty space, and over solid tile.

## Step 7: Implement quadrant jump check

- `_check_quadrant_jumps(snapshots)` — diagonal quadrant changes (diff==2 mod 4)

Verify: unit tests for 0→2, 1→3, 0→1 (ok), same (ok).

## Step 8: Wire all checks into check_invariants

- `check_invariants` calls all private checkers, concatenates results, returns sorted by frame

Verify: integration test with a clean trajectory → 0 violations.

## Step 9: Write clean trajectory integration test

- Build a short trajectory on a flat grid using run_scenario or manual sim_step loop
- Assert `len(check_invariants(...)) == 0`

## Step 10: No-Pyxel import test

- Inspect source of `speednik.invariants`, assert no "import pyxel" or "from pyxel"

## Step 11: Run full test suite

- `uv run pytest tests/test_invariants.py -x`
- Fix any failures

## Testing strategy

- All tests use synthetic FrameSnapshots with known values — no stage loading needed
- `make_snap()` helper with defaults for a normal standing player at (100, 400)
- `make_sim()` helper wrapping `create_sim_from_lookup` with a trivial tile_lookup
- Each invariant category has at least one "violation detected" and one "clean" test
- One integration test with a multi-frame clean trajectory
