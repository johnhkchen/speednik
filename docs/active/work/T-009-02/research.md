# Research — T-009-02: live-bot-runner

## Scope

Build the `LiveBot` adapter that runs robotic player strategies live in the game loop,
one `player_update` per frame, renderable by Pyxel. This bridges the headless test harness
(strategies + `run_scenario`) and the visual game (renderer + camera).

---

## Existing Subsystems

### 1. Strategy system (`tests/harness.py`)

- **Type alias:** `Strategy = Callable[[int, Player], InputState]`
- **Factories:** `idle()`, `hold_right()`, `hold_right_jump()`, `spindash_right()`, `scripted()`
  - Each returns a `Strategy` — a closure that takes `(frame: int, player: Player)` and returns `InputState`.
- **Runners:** `run_scenario(tile_lookup, start_x, start_y, strategy, frames=600)` → `ScenarioResult`
  - Headless loop: creates player, feeds inputs frame-by-frame, captures snapshots.
  - `run_on_stage(stage_name, strategy, frames)` — loads a real stage, delegates to `run_scenario`.
- **Key insight:** `run_scenario` creates its own `Player` internally. The LiveBot must do the same but
  persist the player across frames (one update per game frame rather than batch).

### 2. Player (`speednik/player.py`)

- `create_player(x, y) -> Player` — factory placing player at pixel coords, on_ground=True.
- `player_update(player, inp, tile_lookup)` — full frame update (input → physics → collision → state sync).
  Mutates player in-place.
- `Player` dataclass: `physics: PhysicsState`, `state: PlayerState`, `rings`, `lives`, etc.
- `get_player_rect(player) -> (x, y, w, h)` — rendering helper.

### 3. Camera (`speednik/camera.py`)

- `create_camera(level_width, level_height, start_x, start_y) -> Camera` — factory, centers on start.
- `camera_update(camera, player, inp)` — updates horizontal, vertical, look offset, clamps to bounds.
- `Camera` dataclass: `x, y: float`, `look_offset: float`, `level_width, level_height: int`.
- **Requires `inp: InputState`** for look up/down. The LiveBot's strategy already produces this.

### 4. Renderer (`speednik/renderer.py`)

- `draw_terrain(tiles: dict, camera_x: int, camera_y: int)` — draws tiles in camera viewport.
  - **Takes `dict` (tiles_dict)**, not `TileLookup`. This is critical — we need the underlying dict
    for rendering, not just the callable.
- `draw_player(player, frame_count: int)` — draws player based on state/animation.
- `draw_debug_hud(player, frame_counter)` — debug overlay (guarded by `DEBUG`).

### 5. Terrain (`speednik/terrain.py`)

- `TileLookup = Callable[[int, int], Optional[Tile]]` — callable returning Tile or None.
- `Tile` dataclass: `height_array`, `angle`, `solidity`, `tile_type`.
- Used by `player_update` (via `resolve_collision`) for physics.
- Used by `draw_terrain` as a dict, not callable.

### 6. Level loader (`speednik/level.py`)

- `load_stage(stage_name) -> StageData`
- `StageData`: `tile_lookup`, `tiles_dict`, `entities`, `player_start: (float, float)`, `level_width`, `level_height`.
- Returns BOTH `tile_lookup` (callable) and `tiles_dict` (the underlying dict).
- **For real stages, both are available.** For synthetic grids, only `TileLookup` is returned by
  the builders — the underlying dict is internal.

### 7. Synthetic grids (`tests/grids.py`)

- Builders: `build_flat()`, `build_gap()`, `build_slope()`, `build_ramp()`, `build_loop()`.
- Each returns `TileLookup` via `_wrap(tiles)` — wraps a dict as callable.
- **The underlying dict is not exposed.** The `_wrap` function captures it in a closure.
- For `draw_terrain`, we'd need either:
  - (a) Expose the dict from grid builders (add a return value or helper).
  - (b) Build a tiles_dict separately when constructing grid-based bots.
  - (c) Modify `draw_terrain` to accept `TileLookup` (too invasive).

### 8. Debug flag (`speednik/debug.py`)

- `DEBUG = os.environ.get("SPEEDNIK_DEBUG", "") == "1"`
- Imported as `from speednik.debug import DEBUG`.
- T-009-01 is done: DEBUG flag, debug HUD, dev_park placeholder state all exist in main.py.

### 9. Main game loop (`speednik/main.py`)

- `App` class with state machine: title, stage_select, gameplay, results, game_over, dev_park.
- **Dev park state is placeholder**: shows "DEV PARK" text, returns on Z press.
- `_update_gameplay()` and `_draw_gameplay()` show the pattern for per-frame update + render.
- The dev_park state will be replaced/enhanced in T-009-03 and T-009-04. This ticket just provides
  the `LiveBot` class and factories — it does NOT modify main.py's dev_park state.

---

## Key Interface Mismatch: tiles_dict vs TileLookup

**Problem:** `draw_terrain` requires `tiles: dict` but grid builders return `TileLookup` (callable).

For `make_bots_for_stage`, `StageData` provides both `tile_lookup` and `tiles_dict` — no issue.

For `make_bots_for_grid`, the caller passes a `TileLookup` but we have no `tiles_dict`. Options:
1. **Have grid builders also return the dict.** Not in scope for this ticket.
2. **Accept both `tile_lookup` and `tiles_dict` in `make_bot`.** The LiveBot stores both.
3. **Make `tiles_dict` optional in LiveBot.** If None, `draw()` skips terrain.
4. **Extract dict from closure.** Fragile, not recommended.

Option 2 or 3 is cleanest. Since the ticket specifies a `tile_lookup` field on LiveBot,
adding a separate `tiles_dict` field for rendering is the right approach.

---

## Completion Detection

The ticket mentions `max_frames` and `goal_x` for finish conditions. These are NOT on the
ticket's `LiveBot` dataclass sketch but are described in "Completion detection" section.
Need to add `max_frames: int` and `goal_x: float | None` fields.

---

## Import Path: tests/ → game package

The ticket explicitly states importing strategies from `tests/harness.py` is acceptable since
it's gated by DEBUG. This is a dev-only path.

```python
from tests.harness import idle, hold_right, hold_right_jump, spindash_right
```

This import works because tests/ is on the Python path when running with `uv run`.

---

## Dependencies

- T-009-01 (done): DEBUG flag, debug HUD, dev_park placeholder — all available.
- S-008 / T-008-01 (done): strategies exist in `tests/harness.py`.
- S-008 / T-008-02 (done): grid builders exist in `tests/grids.py`.
