# Structure — T-004-03: Game State Machine

## Files Modified

### 1. `speednik/stages/hillside.py`

- Add `tiles_dict: dict[tuple[int, int], Tile]` field to `StageData` dataclass
- Populate `tiles_dict` in `load()` by passing the `tiles` dict already built

```
@dataclass
class StageData:
    tile_lookup: TileLookup
    tiles_dict: dict              # NEW
    entities: list[dict]
    player_start: tuple[float, float]
    checkpoints: list[dict]
    level_width: int
    level_height: int
```

### 2. `speednik/stages/pipeworks.py`

- Update `load()` to pass `tiles_dict=tiles` in StageData constructor
- No import changes needed (already imports StageData from hillside)

### 3. `speednik/stages/skybridge.py`

- Remove duplicated `StageData` class
- Import `StageData` from `speednik.stages.hillside`
- Remove unused imports (`FULL`, `NOT_SOLID`, `TOP_ONLY`, `TileLookup`, `dataclass`)
- Update `load()` to pass `tiles_dict=tiles`

### 4. `speednik/constants.py`

- Add `GOAL_ACTIVATION_RADIUS = 24`
- Add `DEATH_DELAY_FRAMES = 120` (2 seconds at 60fps)
- Add `RESULTS_DURATION = 300` (5 seconds at 60fps)
- Add `GAMEOVER_DELAY = 360` (6 seconds — enough for jingle + pause)
- Add `BOSS_ARENA_START_X = 4000` (x threshold for boss music)
- Add `BOSS_SPAWN_X = 4800` (boss spawn position for Stage 3)
- Add `BOSS_SPAWN_Y = 480` (boss ground level)

### 5. `speednik/objects.py`

- Add `GoalEvent` enum with `REACHED` value
- Add `check_goal_collision(player, goal_x, goal_y)` → `GoalEvent | None`
  - Skip if player dead/hurt
  - Radius check using `GOAL_ACTIVATION_RADIUS`
  - Returns `GoalEvent.REACHED` on contact

### 6. `speednik/renderer.py`

- Add `clear_particles()` public function wrapping `_particles.clear()`

### 7. `speednik/main.py` — Complete Rewrite

Remove: `_build_demo_level()`, existing `App` class with demo state.
Keep: `_read_input()` function.

New `App` class structure:

```
class App:
    # --- Init ---
    __init__(self)
        - pyxel.init, palette, audio
        - State machine fields: state, lives, unlocked_stages, selected_stage
        - Gameplay fields: all None/empty initially
        - Start title music, pyxel.run

    # --- State dispatch ---
    update(self)
        - Route to _update_{state}
    draw(self)
        - Route to _draw_{state}

    # --- TITLE ---
    _update_title(self)
        - Any button → SFX_MENU_CONFIRM → state = "stage_select"
    _draw_title(self)
        - Game title, "PRESS START" flashing

    # --- STAGE_SELECT ---
    _update_stage_select(self)
        - Up/Down → navigate (clamped to unlocked)
        - Confirm → _load_stage → state = "gameplay"
    _draw_stage_select(self)
        - Stage names, cursor, lock icons

    # --- GAMEPLAY ---
    _update_gameplay(self)
        - Handle death timer (if player dead)
        - Normal frame: input → player_update → object checks → enemy checks → goal check
        - Boss music trigger (Stage 3)
        - Update audio, camera
    _draw_gameplay(self)
        - Full world render (terrain, objects, enemies, player, particles, HUD)

    # --- RESULTS ---
    _update_results(self)
        - Decrement results_timer → unlock next stage → state = "stage_select"
    _draw_results(self)
        - Time, rings, score display

    # --- GAME_OVER ---
    _update_game_over(self)
        - Decrement timer → reset lives → state = "title", play title music
    _draw_game_over(self)
        - "GAME OVER" text

    # --- Stage loading ---
    _load_stage(self, stage_num)
        - Load stage module, create player, load objects, inject boss for Stage 3
        - Set palette, start music, reset timer

    # --- Respawn ---
    _respawn_player(self)
        - Reset player position/state/rings to checkpoint data
        - Decrement lives
```

## Module Boundaries

- `main.py` owns: state machine routing, state transitions, stage loading orchestration, rendering dispatch, input handling for menus
- `objects.py` owns: goal collision detection (new)
- `renderer.py` owns: all drawing (existing + particle cleanup)
- Stage loaders own: data loading + tiles dict exposure (extended)
- `audio.py`, `player.py`, `enemies.py`, `camera.py`, `constants.py`, `physics.py`, `terrain.py`: no interface changes (constants.py gets new constants only)

## Ordering Constraints

1. Stage loaders (hillside → pipeworks → skybridge) must be updated first — main.py depends on `tiles_dict`
2. `constants.py` can be updated independently
3. `objects.py` goal check can be added independently
4. `renderer.py` clear helper can be added independently
5. `main.py` rewrite comes last — depends on all other changes

## Data Flow

```
Stage module.load() → StageData(tiles_dict, tile_lookup, entities, ...)
                          ↓
App._load_stage() → creates Player, Camera, loads objects, extracts goal
                          ↓
App._update_gameplay() → player_update(player, input, tile_lookup)
                       → check_ring/spring/checkpoint/pipe/liquid/enemy/goal
                       → camera_update
                          ↓
App._draw_gameplay() → renderer.draw_terrain(tiles_dict, cam_x, cam_y)
                     → draw objects, enemies, player, HUD
```

## No Files Created

All changes fit within existing files. No new modules needed.
