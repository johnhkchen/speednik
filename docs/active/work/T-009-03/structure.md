# T-009-03 Structure — Dev Park Stages

## Files Modified

### `tests/grids.py`
- Change all 5 public builder return types from `TileLookup` to
  `tuple[dict[tuple[int,int], Tile], TileLookup]`.
- Each builder returns `(tiles, _wrap(tiles))` instead of `_wrap(tiles)`.

### `tests/test_elementals.py`
- Update all calls to builders: destructure `_, lookup = build_*()`.

### `tests/test_grids.py`
- Update all calls: destructure `tiles_dict, lookup = build_*()` or `_, lookup`.

### `speednik/devpark.py`
- Add module-level state: sub_state, selected_index, active_bots, frame_counter,
  stage_defs list, current_stage_index, scenario_variant.
- Add `DevParkStage` dataclass: name, init_fn, readout_fn.
- Add `STAGES` list with 5 stage definitions.
- Add `init()` — reset to menu state.
- Add `update()` — dispatch to menu or running update.
- Add `draw()` — dispatch to menu or running draw.
- Add `_update_menu()` — UP/DOWN/Z/X navigation.
- Add `_draw_menu()` — render stage list with cursor.
- Add `_update_running()` — update all bots, check completion, handle X exit.
- Add `_draw_running()` — draw bots, labels, readouts, debug HUD.
- Add 5 init functions: `_init_ramp_walker`, `_init_speed_gate`, `_init_loop_lab`,
  `_init_gap_jump`, `_init_hillside_bot`.
- Add 5 readout functions: `_readout_ramp_walker`, `_readout_speed_gate`,
  `_readout_loop_lab`, `_readout_gap_jump`, `_readout_hillside_bot`.

### `speednik/renderer.py`
- Add `"devpark"` entry to `STAGE_PALETTES` dict.

### `speednik/main.py`
- Replace `_update_dev_park` / `_draw_dev_park` methods to delegate to
  `devpark.init()` / `devpark.update()` / `devpark.draw()`.
- Call `devpark.init()` when entering dev_park state.
- Handle return-to-stage-select: devpark.update() returns a signal or sets a flag
  when X is pressed in menu.

### `tests/test_devpark.py`
- Add tests for menu navigation (state transitions).
- Add tests for each stage init (creates correct number of bots with correct labels).
- Add tests for stage completion behavior.

## Module Boundaries

### devpark.py public interface
```
init() -> None                  # Reset to menu, called when entering dev_park state
update() -> str | None          # Returns "exit" when user backs out to stage select
draw() -> None                  # Render current sub-state
```

### Grid builders new return type
```
build_flat(...) -> tuple[dict, TileLookup]
build_gap(...)  -> tuple[dict, TileLookup]
build_slope(...) -> tuple[dict, TileLookup]
build_ramp(...) -> tuple[dict, TileLookup]
build_loop(...) -> tuple[dict, TileLookup]
```

## Component Organization

```
devpark.py
├── DevParkStage dataclass
├── Module state (sub_state, selected_idx, bots, etc.)
├── STAGES list (5 DevParkStage entries)
├── Public API: init(), update(), draw()
├── Menu: _update_menu(), _draw_menu()
├── Running: _update_running(), _draw_running()
├── Stage inits: _init_ramp_walker, _init_speed_gate, ...
└── Readouts: _readout_ramp_walker, _readout_speed_gate, ...
```

## Ordering Constraints

1. Grid builder return type change must come first (tests/grids.py + test updates).
2. Palette entry in renderer.py can be done independently.
3. devpark.py stage definitions depend on grid builder changes.
4. main.py delegation depends on devpark.py public API being defined.
5. devpark tests depend on all the above.
