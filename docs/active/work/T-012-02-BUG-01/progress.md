# Progress — T-012-02-BUG-01: hillside-wall-at-x601

## Completed Steps

### Step 1: Fix tile_map.json ✓

Changed `speednik/stages/hillside/tile_map.json[38][37]["angle"]` from 64 to 2.

Verified:
- `tile_map[38][37]["angle"] == 2` after write
- Neighboring tiles (36, 38, 39) unchanged
- Height array unchanged: `[4,4,4,4,4,4,4,4,4,5,5,5,5,5,5,5]`

### Step 2: Add regression test — tile angle ✓

Added `test_hillside_tile_37_38_not_wall_angle` to `tests/test_terrain.py`.
Loads hillside via `create_sim`, inspects tile (37, 38), asserts `angle <= 5`.

Result: PASSED

### Step 3: Add integration test — walker passes x=601 ✓

Added `test_hillside_walker_passes_x601` to `tests/test_simulation.py`.
Runs hold-right for 600 frames, asserts `max_x_reached > 650`.

Result: PASSED (max_x_reached ≈ 838.9)

### Step 4: Full test suite ✓

- `uv run pytest tests/ -q` (excluding pre-existing failures in
  `test_walkthrough.py` and `test_audit_hillside.py`)
- **1244 passed, 0 failed, 5 xfailed**
- No regressions introduced

## Pre-existing Failures (not related to this ticket)

- `test_walkthrough.py::TestSpindashReachesGoal::test_hillside` — spindash
  strategy times out. Pre-existing: this test file is part of uncommitted
  work and was failing before this change.
- `test_audit_hillside.py::test_hillside_speed_demon` — boundary clamping
  bugs (T-012-02-BUG-02, T-012-02-BUG-03). Pre-existing.

## Deviations from Plan

- Integration test uses `max_x_reached` instead of current `player.physics.x`
  because the player can bounce back from enemy collisions. The metric correctly
  tracks whether the player *ever* passed x=650, which is the intent.

## Remaining

- Step 5 (commit) — deferred until review phase is written.
