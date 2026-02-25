# T-009-03 Research — Dev Park Stages

## Current State

### Dev Park Entry Point (`speednik/main.py`)

The main game already has a `"dev_park"` state in its state machine (lines 169-188).
Stage select shows "DEV PARK" when `DEBUG=True` (line 255-260). Selecting it sets
`self.state = "dev_park"` (line 235). Currently the dev park is a placeholder that shows
"DEV PARK" text and returns to stage select on Z press (lines 266-279).

The existing state machine routes `"dev_park"` to `_update_dev_park` / `_draw_dev_park`.

### LiveBot System (`speednik/devpark.py`)

T-009-02 delivered a complete LiveBot system:

- **`LiveBot` dataclass** (line 29): player, strategy, tile_lookup, tiles_dict, camera,
  label, max_frames, goal_x, frame counter, finished flag.
- **`LiveBot.update()`** (line 43): strategy → player_update → camera_update per frame.
  Stops when finished (max_frames or goal_x reached).
- **`LiveBot.draw()`** (line 56): sets pyxel.camera, calls draw_terrain + draw_player.
- **`make_bot()`** (line 82): factory from tiles_dict + tile_lookup + position + strategy.
- **`make_bots_for_stage()`** (line 108): creates 4 bots for a real stage.
- **`make_bots_for_grid()`** (line 130): creates bots for synthetic grid + strategies list.

### Synthetic Grid Builders (`tests/grids.py`)

T-008-02 builders are in `tests/grids.py`:

- **`build_flat(width, ground_row)`** — flat ground, returns TileLookup.
- **`build_gap(approach, gap, landing, ground_row)`** — flat + gap + flat.
- **`build_slope(approach, slope_tiles, angle, ground_row)`** — flat + constant-angle slope.
- **`build_ramp(approach, ramp_tiles, start_angle, end_angle, ground_row)`** — flat +
  linearly interpolated angle ramp.
- **`build_loop(approach, radius, ground_row, ramp_radius=None)`** — flat + full 360° loop.

All return `TileLookup` (callable). None return `tiles_dict` directly — they use `_wrap()`
which captures the dict in a closure. This is a gap: LiveBot needs both `tiles_dict` (for
rendering) and `tile_lookup` (for physics). The builders need to be extended or wrapped.

### Strategy Factories (`tests/harness.py`)

Available strategies:
- `idle()` — no input
- `hold_right()` — right every frame
- `hold_right_jump()` — right + spam jump
- `spindash_right(charge_frames=3, redash_threshold=2.0)` — spindash state machine

### Renderer Palette (`speednik/renderer.py`)

`STAGE_PALETTES` dict (line 39) has entries for "hillside", "pipeworks", "skybridge".
No "devpark" entry yet. `set_stage_palette()` (line 76) reads from this dict; returns
silently if key not found.

### Debug HUD (`speednik/renderer.py`)

`draw_debug_hud(player, frame_counter)` (line 573) draws F/X/Y/GS/A/Q/STATE/GND in the
top-right. Called from `_draw_gameplay` when `DEBUG=True`.

### Camera System (`speednik/camera.py`)

`create_camera(level_width, level_height, start_x, start_y)` and `camera_update(camera,
player, inp)`. Camera needs an InputState for look up/down — the dev park bots already
pass strategy output through camera_update.

### Screen Dimensions

256×224 (`SCREEN_WIDTH`, `SCREEN_HEIGHT`). TILE_SIZE = 16.

## Gaps and Constraints

1. **Grid builders return TileLookup, not tiles_dict**: `make_bot` needs `tiles_dict` for
   rendering. Need to either (a) modify grid builders to return both, or (b) add a wrapper
   that captures the tiles dict before wrapping.

2. **Dev park has no sub-menu**: Current placeholder just shows text. Need a menu state
   machine within the dev_park state.

3. **No devpark palette**: Need to add to `STAGE_PALETTES`.

4. **Bot labels not rendered**: `LiveBot.draw()` draws terrain + player but not the label.
   Label rendering needs to be added.

5. **No scenario-specific readouts**: Angle readout (RAMP WALKER), speed comparison, etc.
   are not in the current draw path.

6. **HILLSIDE BOT needs stage loading**: `load_stage("hillside")` returns `StageData` with
   `tiles_dict` and `tile_lookup` — this works directly with `make_bot`.

7. **SPEED GATE needs two bots vertically separated**: Either split view or Y-stagger.
   The simpler approach is Y-stagger on the same grid.

8. **LOOP LAB needs two scenarios**: Loop with ramps (success) and without (failure).
   Could be sequential (restart scenario) or side-by-side.

## Dependency Status

- **T-009-01** (debug flag + HUD): Done. `DEBUG` flag, `draw_debug_hud`, stage select gate
  all present and working.
- **T-009-02** (live bot runner): Done. `LiveBot`, `make_bot`, `make_bots_for_grid`,
  `make_bots_for_stage` all present and tested.
- **T-008-02** (grid builders): Present in `tests/grids.py`. All five builders available.

## Existing Tests

- `tests/test_devpark.py` — Tests LiveBot update, make_bot, make_bots_for_stage,
  make_bots_for_grid. All pass headlessly (no Pyxel required for update).
- `tests/test_elementals.py` — Tests elemental scenarios on synthetic grids. Uses
  `run_scenario` from harness, not LiveBot.
