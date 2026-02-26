# Research — T-011-04: camera-stability-tests

## Camera module (`speednik/camera.py`)

### Data model

`Camera` dataclass: `x`, `y`, `look_offset` (floats), `level_width`, `level_height` (ints).
Created via `create_camera(level_width, level_height, start_x, start_y)` which places
camera so player appears at `CAMERA_LEFT_BORDER` horizontally, `CAMERA_FOCAL_Y` vertically,
then clamps to bounds.

### Update pipeline

`camera_update(camera, player, inp)` runs four steps in order:

1. **Horizontal** (`_update_horizontal`): Dead zone between `CAMERA_LEFT_BORDER` (144) and
   `CAMERA_RIGHT_BORDER` (160). Outside dead zone, scroll toward player capped at
   `CAMERA_H_SCROLL_CAP` (16 px/frame).

2. **Look offset** (`_update_look_offset`): Only when `on_ground and ground_speed == 0.0`.
   Shifts `look_offset` toward ±104/88 at 2 px/frame. Returns to 0 when moving.

3. **Vertical** (`_update_vertical`):
   - On ground: target_y = player_y − FOCAL_Y + look_offset. Capped at 6 px/frame (slow,
     |gs| < 8) or 16 px/frame (fast, |gs| >= 8).
   - Airborne: tolerance band ±32 around focal. Scroll only when player exits band, capped
     at 16 px/frame.

4. **Clamp** (`_clamp_to_bounds`): `x ∈ [0, level_width − SCREEN_WIDTH]`,
   `y ∈ [0, level_height − SCREEN_HEIGHT]`.

### Constants (from `speednik/constants.py`)

| Constant | Value | Role |
|---|---|---|
| SCREEN_WIDTH | 256 | Viewport width |
| SCREEN_HEIGHT | 224 | Viewport height |
| CAMERA_LEFT_BORDER | 144 | Dead zone left edge |
| CAMERA_RIGHT_BORDER | 160 | Dead zone right edge |
| CAMERA_H_SCROLL_CAP | 16 | Max horizontal scroll per frame |
| CAMERA_FOCAL_Y | 96 | Vertical focal point |
| CAMERA_AIR_BORDER | 32 | Airborne tolerance band |
| CAMERA_V_SCROLL_GROUND_SLOW | 6 | Vertical cap, slow ground |
| CAMERA_V_SCROLL_GROUND_FAST | 16 | Vertical cap, fast ground |
| CAMERA_V_SCROLL_AIR | 16 | Vertical cap, airborne |
| CAMERA_GROUND_SPEED_THRESHOLD | 8.0 | Fast/slow boundary |

## Simulation module (`speednik/simulation.py`)

`SimState` holds complete headless game state. `create_sim(stage_name)` loads a real stage
("hillside", "pipeworks", "skybridge") with entities. `sim_step(sim, inp)` advances one
frame — updates player physics, rings, springs, checkpoints, pipes, liquids, enemies, goal.

Camera is NOT updated by `sim_step`. The ticket confirms this — tests must call
`camera_update` separately after each `sim_step`, matching `main.py`'s `_update_gameplay`.

## Existing test patterns

### `tests/harness.py`

`Strategy = Callable[[int, Player], InputState]`. Built-in strategies:
- `hold_right()` — hold right every frame
- `hold_left()` — hold left every frame
- `hold_right_jump()` — right + spam jump
- `spindash_right(charge_frames=3, redash_threshold=2.0)` — spindash then run
- `idle()` — do nothing
- `scripted(timeline)` — windowed input playback

`run_on_stage(stage_name, strategy, frames)` loads a stage and runs the scenario.
Returns `ScenarioResult` with `snapshots: list[FrameSnapshot]`.

### `tests/test_walkthrough.py`

Uses the `speednik.scenarios` module (different from `tests/harness.py`). Runs 3 stages ×
3 strategies, checks forward progress, rings, deaths, frame budget. Uses outcome caching.

Stage dimensions: hillside=4800, pipeworks=5600, skybridge=5200 (widths). Max frames:
4000/5000/6000.

### `tests/test_camera.py`

Unit tests for camera functions — dead zone, scroll capping, vertical tracking, look
up/down, boundary clamping. Uses `make_player()` and `make_camera()` helpers. Does NOT
test camera + real simulation together.

## Stages

Three stages loaded via `load_stage()`:
- **hillside**: width 4800, simplest terrain, 0 deaths expected
- **pipeworks**: width 5600, pipes and liquid hazards
- **skybridge**: width 5200, springs that launch off-map, boss fight

Heights are loaded from `meta.json` per stage. Level heights are needed for camera bounds
but available from `SimState.level_height`.

## Gap analysis

Existing `test_camera.py` covers unit-level behavior. No test currently:
- Creates a Camera alongside SimState and runs multi-frame sim
- Checks for oscillation (sign-flip detection)
- Verifies camera deltas stay within scroll caps on real stages
- Verifies camera bounds on real stages
- Verifies player visibility on-screen during gameplay

The ticket fills this gap: integration-level camera stability on real stages with real
player trajectories.
