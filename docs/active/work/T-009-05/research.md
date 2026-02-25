# Research — T-009-05 boundary-escape-detection

## Problem

The player can walk/roll/fall off any level edge and continue indefinitely.
The camera clamps to level boundaries (camera.py:164-169) but the player has
zero boundary enforcement. This creates a soft-lock: the player sails past the
visible area with no way to die or recover.

## Codebase Map

### Player position handling — `speednik/player.py`

- `create_player(x, y)` initializes physics at given position (line 99-102)
- `player_update()` orchestrates movement + collision but **never validates
  position against level bounds** (lines 109-145)
- Position modified via `apply_movement()` in physics.py (lines 262-270)
  and terrain collision resolution — no clamping at any layer

### Camera clamping — `speednik/camera.py:164-169`

```python
def _clamp_to_bounds(camera: Camera) -> None:
    max_x = max(0, camera.level_width - SCREEN_WIDTH)
    max_y = max(0, camera.level_height - SCREEN_HEIGHT)
    camera.x = max(0.0, min(camera.x, float(max_x)))
    camera.y = max(0.0, min(camera.y, float(max_y)))
```

Camera IS bounded. Player IS NOT. This is the gap.

### Level dimensions — `speednik/level.py`

- `StageData` dataclass (lines 22-32) stores `level_width` and `level_height`
- Loaded from `meta.json` per stage (line 88-89): `width_px`, `height_px`
- Three stages: hillside (4800×720), pipeworks, skybridge
- `load_stage()` returns StageData with all fields populated

### Test infrastructure — `tests/harness.py`

- `FrameSnapshot` (lines 30-40): per-frame x, y, velocities, state
- `ScenarioResult` (lines 44-72): snapshots list, `max_x`, `stuck_at()`
- `run_scenario()` (lines 99-131): physics-only loop, no Pyxel
- `run_on_stage()` (lines 134-151): loads stage, runs from player_start
- Strategies: `idle()`, `hold_right()`, `hold_right_jump()`, `spindash_right()`
- **No `hold_left` strategy exists** — needed for left-edge testing

### Existing tests — `tests/test_levels.py`

- Uses `_get_stage()` cached loader, `get_goal_x()`, STRATEGIES dict
- Test classes per stage: TestHillside, TestPipeworks, TestSkybridge
- Tests check goal completion and stall detection
- **No boundary escape tests exist** — this is what T-009-05 adds
- Pattern: `@pytest.mark.xfail(reason="...")` for expected failures

### Dev park — `speednik/devpark.py`

- `LiveBot` dataclass (lines 31-64): player + strategy + camera per bot
- `make_bot()` factory (lines 84-107): creates from tile data + strategy
- `make_bots_for_stage()` (lines 110-129): 4 strategies for a real stage
- 6 stages in STAGES list (line 389-396): RAMP WALKER, SPEED GATE,
  LOOP LAB, GAP JUMP, HILLSIDE BOT, MULTI-VIEW
- Pattern: `_init_*()` → list[LiveBot], `_readout_*()` → HUD text
- `_compute_level_bounds()` (lines 71-77): derives bounds from tiles_dict
- `_draw_running()` (lines 521-567): renders primary bot camera + all bots

### Debug — `speednik/debug.py`

- Single `DEBUG` flag from `SPEEDNIK_DEBUG` env var
- Used in main.py to toggle dev park menu visibility
- No debug rendering infrastructure beyond flag

### Renderer — `speednik/renderer.py`

- `draw_terrain()` (lines 99-138): world-space tile rendering with viewport culling
- `draw_player()` (lines 145-176): draws at physics.x, physics.y
- All drawing in world coordinates with camera offset via `pyxel.camera()`
- Palette: slot 8 = spring red (0xE02020), slot 9 = hazard orange (0xE08020)
- No boundary line drawing exists

## Key Observations

1. **Level bounds are available** via StageData.level_width/level_height
2. **Snapshots already capture x, y every frame** — boundary checks are trivial
3. **No `hold_left` strategy** exists in harness.py — must be added
4. **Dev park pattern is clear**: init_fn + readout_fn + add to STAGES list
5. **Boundary lines are world-space pyxel.line()** calls with camera offset
6. **Camera.level_width/height** available in LiveBot.camera for rendering
7. **Stage boundaries from meta.json** differ from computed bounds in devpark
   (`_compute_level_bounds` scans tiles_dict; meta.json has canonical values)
   — for real stages we should use load_stage() meta values

## Constraints

- No Pyxel imports in test files
- Tests must use physics-only harness
- xfail tests document the known defect (no fix in this ticket)
- Dev park rendering uses pyxel — separate from test infrastructure
- Boundary rendering should work in both devpark and DEBUG modes

## Open Questions for Design

- Should boundary lines render via renderer.py (new function) or inline in devpark.py?
- For bottom-edge tests, what Y threshold? Ticket says `level_height + 64` grace
- Should `hold_left` strategy also be added as a general harness strategy?
