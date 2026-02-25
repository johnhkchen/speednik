# Structure — T-008-01: scenario-runner-and-strategies

## Files Created

### `tests/harness.py` (new)

The core scenario runner and strategy library. Not a test file — imported by test files.

**Public API:**

```
# --- Data classes ---
FrameSnapshot(frame, x, y, x_vel, y_vel, ground_speed, angle, on_ground, quadrant, state)
ScenarioResult(snapshots, player)
  .final -> FrameSnapshot
  .max_x -> float
  .quadrants_visited -> set[int]
  .stuck_at(tolerance, window) -> float | None

# --- Runner ---
run_scenario(tile_lookup, start_x, start_y, strategy, frames, *, on_ground) -> ScenarioResult
run_on_stage(stage_name, strategy, frames) -> ScenarioResult

# --- Strategy factories ---
idle() -> Callable[[int, Player], InputState]
hold_right() -> Callable[[int, Player], InputState]
hold_right_jump() -> Callable[[int, Player], InputState]
spindash_right(charge_frames, redash_threshold) -> Callable[[int, Player], InputState]
scripted(timeline) -> Callable[[int, Player], InputState]
```

**Internal organization (top to bottom):**

1. Imports (speednik.player, speednik.physics, speednik.terrain, speednik.level)
2. `FrameSnapshot` dataclass
3. `ScenarioResult` dataclass with properties
4. `_capture_snapshot()` helper — extracts fields from Player into FrameSnapshot
5. `run_scenario()` — core loop
6. `run_on_stage()` — convenience wrapper
7. Strategy factories section: `idle`, `hold_right`, `hold_right_jump`,
   `spindash_right`, `scripted`

**Type alias:**

```python
Strategy = Callable[[int, Player], InputState]
```

### `tests/test_harness.py` (new)

Self-tests for the harness module. Validates runner and strategies work correctly.

**Test classes:**

```
TestFrameSnapshot — field access, construction
TestScenarioResult — max_x, final, quadrants_visited, stuck_at
TestRunScenario — idle grounded, hold_right advances X
TestStrategies — each strategy produces expected InputState patterns
```

**Helpers (reused from test_player.py pattern):**

```
flat_tile() -> Tile
make_tile_lookup(dict) -> TileLookup
flat_ground_lookup() -> TileLookup
```

These are duplicated from test_player.py rather than extracted — the ticket doesn't
ask for shared test helpers, and duplication across two files is fine.

## Files Modified

None. This is a new module with no changes to existing code.

## Files Deleted

None.

## Module Boundaries

```
tests/harness.py
  imports from:
    speednik.physics    → InputState
    speednik.player     → Player, PlayerState, create_player, player_update
    speednik.terrain    → TileLookup, get_quadrant
    speednik.level      → load_stage
  does NOT import:
    pyxel (or anything that transitively imports pyxel)

tests/test_harness.py
  imports from:
    tests.harness       → all public API
    speednik.physics    → InputState (for strategy output checking)
    speednik.player     → Player, PlayerState
    speednik.terrain    → Tile, TileLookup, FULL, TILE_SIZE
    pytest
```

## Dependency Direction

```
test_harness.py → harness.py → speednik.{player, physics, terrain, level}
```

No circular dependencies. The harness is a leaf consumer of the game engine — it never
modifies engine code.

## Key Interface Contract

`run_scenario` is the foundation. All other runners (`run_on_stage`, future test
helpers) compose on top of it. The strategy signature
`(frame: int, player: Player) -> InputState` is the extension point — new strategies
can be added without modifying the runner.

`ScenarioResult` is the analysis surface. Properties like `stuck_at`, `max_x`, and
`quadrants_visited` provide the assertions that downstream tests will use.
