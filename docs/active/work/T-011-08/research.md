# T-011-08 Research: Extract Shared Code from Tests

## Problem

`speednik/devpark.py` imports from `tests.grids` and `tests.harness` at 10 call sites via
lazy (in-function) imports. This works under pytest because pytest adds the project root to
`sys.path`, but crashes with `ModuleNotFoundError: No module named 'tests'` when running
normally (`uv run python -m speednik.main`) or in web builds.

## Current File Map

### `tests/grids.py` (380 lines)

Synthetic tile-grid builders for physics tests. No Pyxel imports.

**Imports from speednik:** `speednik.terrain` (FULL, SURFACE_LOOP, TILE_SIZE, TOP_ONLY, Tile, TileLookup)

**Constants:**
- `FILL_DEPTH = 4`

**Internal helpers (4):**
- `_wrap(tiles)` → wraps dict as TileLookup callable
- `_flat_tile(angle, solidity, tile_type)` → creates flat Tile
- `_fill_below(tiles, tx, ground_row)` → adds solid fill rows below surface
- `_slope_height_array(angle_byte, col_offset)` → 16-element height array from angle

**Public builders (5):**
- `build_flat(width_tiles, ground_row)` → flat ground
- `build_gap(approach_tiles, gap_tiles, landing_tiles, ground_row)` → approach + gap + landing
- `build_slope(approach_tiles, slope_tiles, angle, ground_row)` → flat + constant-angle slope
- `build_ramp(approach_tiles, ramp_tiles, start_angle, end_angle, ground_row)` → interpolated ramp
- `build_loop(approach_tiles, radius, ground_row, ramp_radius)` → full 360° loop

All builders return `tuple[dict[tuple[int,int], Tile], TileLookup]`.

### `tests/harness.py` (271 lines)

Scenario runner and strategy primitives. No Pyxel imports.

**Imports from speednik:** `speednik.level`, `speednik.physics`, `speednik.player`, `speednik.terrain`

**Type alias:**
- `Strategy = Callable[[int, Player], InputState]`

**Dataclasses (2):**
- `FrameSnapshot` — per-frame player state capture (11 fields)
- `ScenarioResult` — list of snapshots + final player, with properties: `final`, `max_x`,
  `quadrants_visited`, and `stuck_at()` method

**Internal helper:**
- `_capture_snapshot(frame, player)` → FrameSnapshot

**Runner functions (2):**
- `run_scenario(tile_lookup, start_x, start_y, strategy, frames, on_ground)` → ScenarioResult
- `run_on_stage(stage_name, strategy, frames)` → ScenarioResult (loads real stage)

**Strategy factories (6):**
- `idle()` — do nothing
- `hold_right()` — hold right
- `hold_left()` — hold left
- `hold_right_jump()` — hold right + spam jump (closure state)
- `spindash_right(charge_frames, redash_threshold)` — 4-phase state machine (closure state)
- `scripted(timeline)` — frame-windowed input playback

## Import Sites in `speednik/devpark.py`

All imports are lazy (inside functions):

| Line | Function | Import |
|------|----------|--------|
| 116 | `make_bots_for_stage` | `from tests.harness import hold_right, hold_right_jump, idle, spindash_right` |
| 169 | `_init_ramp_walker` | `from tests.grids import build_ramp` |
| 170 | `_init_ramp_walker` | `from tests.harness import hold_right, spindash_right` |
| 187 | `_init_speed_gate` | `from tests.grids import build_ramp` |
| 188 | `_init_speed_gate` | `from tests.harness import hold_right, spindash_right` |
| 205 | `_init_loop_lab_with_ramps` | `from tests.grids import build_loop` |
| 206 | `_init_loop_lab_with_ramps` | `from tests.harness import spindash_right` |
| 221 | `_init_loop_lab_no_ramps` | `from tests.grids import build_loop` |
| 222 | `_init_loop_lab_no_ramps` | `from tests.harness import spindash_right` |
| 241 | `_init_gap_jump` | `from tests.grids import build_gap` |
| 242 | `_init_gap_jump` | `from tests.harness import hold_right_jump` |
| 259 | `_init_hillside_bot` | `from tests.harness import hold_right` |
| 280 | `_init_boundary_patrol` | `from tests.harness import hold_left, hold_right` |

**Used from tests.grids:** `build_ramp`, `build_loop`, `build_gap` (3 of 5 builders)
**Used from tests.harness:** `idle`, `hold_right`, `hold_left`, `hold_right_jump`, `spindash_right` (5 of 6 strategies)

## Test Files Importing from `tests.grids` / `tests.harness`

| File | From `tests.grids` | From `tests.harness` |
|------|--------------------|-----------------------|
| `tests/test_grids.py` | FILL_DEPTH, build_flat, build_gap, build_loop, build_ramp, build_slope | — |
| `tests/test_harness.py` | — | FrameSnapshot, ScenarioResult, hold_right, hold_right_jump, idle, run_scenario, scripted, spindash_right |
| `tests/test_elementals.py` | build_flat, build_gap, build_loop, build_slope | ScenarioResult, hold_right, hold_right_jump, idle, run_scenario, spindash_right |
| `tests/test_levels.py` | — | ScenarioResult, hold_left, hold_right, hold_right_jump, idle, run_on_stage, spindash_right |
| `tests/test_simulation.py` | build_flat | hold_right, idle, run_scenario, spindash_right |
| `tests/test_camera_stability.py` | — | Strategy, hold_right, spindash_right |
| `tests/test_invariants.py` | — | FrameSnapshot |
| `tests/test_devpark.py` | — | hold_right, idle |

8 test files total with 40+ import references.

## `speednik/agents/` — Overlap Analysis

The agents package (S-010) defines observation-based agents: `act(obs: np.ndarray) -> int`.
Strategies are frame-based: `(frame: int, player: Player) -> InputState`.

**Functional overlaps (same behavior logic, different interface):**
- `IdleAgent` ↔ `idle()` strategy
- `HoldRightAgent` ↔ `hold_right()` strategy
- `JumpRunnerAgent` ↔ `hold_right_jump()` strategy
- `SpindashAgent` ↔ `spindash_right()` strategy
- `ScriptedAgent` ↔ `scripted()` strategy

Agents work with observation vectors and return action indices. Strategies work with Player
objects and return InputState. The interfaces are fundamentally different — no code sharing
is practical between them. No conflict to resolve.

## `tests/__init__.py`

Empty file (1 line, blank). Makes `tests/` a proper Python package but doesn't export anything.

## Key Observations

1. **Neither `tests/grids.py` nor `tests/harness.py` import Pyxel** — they are pure
   simulation code and belong in the `speednik/` package.
2. **`speednik/grids.py` and `speednik/strategies.py` do not exist yet** — clean namespace.
3. All devpark imports are lazy (inside functions), so moving them to top-level imports in
   the new locations won't change initialization order.
4. The agent/strategy overlap is by design — agents are the RL interface, strategies are
   the direct-control interface. Both are needed.
