# Plan — T-004-03: Game State Machine

## Step 1: Add Constants

File: `speednik/constants.py`

Add goal/game-state constants at end of file:
- `GOAL_ACTIVATION_RADIUS = 24`
- `DEATH_DELAY_FRAMES = 120`
- `RESULTS_DURATION = 300`
- `GAMEOVER_DELAY = 360`
- `BOSS_ARENA_START_X = 4000`
- `BOSS_SPAWN_X = 4800`
- `BOSS_SPAWN_Y = 480`

Verification: import succeeds, no test regressions.

## Step 2: Extend StageData and Fix Loaders

### 2a: `speednik/stages/hillside.py`
- Add `tiles_dict: dict` field to `StageData` (after `tile_lookup`)
- In `load()`, pass `tiles_dict=tiles` to constructor

### 2b: `speednik/stages/pipeworks.py`
- In `load()`, pass `tiles_dict=tiles` to constructor

### 2c: `speednik/stages/skybridge.py`
- Remove duplicate `StageData` class and associated imports
- Add `from speednik.stages.hillside import StageData`
- In `load()`, pass `tiles_dict=tiles` to constructor

Verification: each loader's `load()` returns StageData with `tiles_dict` populated. Existing tests still pass.

## Step 3: Add Goal Collision to objects.py

File: `speednik/objects.py`

- Add import: `GOAL_ACTIVATION_RADIUS` from constants
- Add `GoalEvent` enum with `REACHED`
- Add `check_goal_collision(player, goal_x, goal_y) -> GoalEvent | None`
  - If player dead/hurt: return None
  - Compute distance squared from player to goal
  - If within radius: return GoalEvent.REACHED
  - Else: return None

Verification: unit test — player near goal returns REACHED, far away returns None.

## Step 4: Add Particle Cleanup to renderer.py

File: `speednik/renderer.py`

- Add `clear_particles()` function: `_particles.clear()`

Verification: function exists and clears the list.

## Step 5: Rewrite main.py

File: `speednik/main.py`

Complete replacement. The new file:

### 5a: Imports
- All existing imports plus: stage modules, GoalEvent, new constants, play_music/stop_music, clear_particles

### 5b: _read_input() — keep as-is

### 5c: Stage configuration
```python
_STAGE_NAMES = {1: "HILLSIDE RUSH", 2: "PIPE WORKS", 3: "SKYBRIDGE GAUNTLET"}
_STAGE_MUSIC = {1: MUSIC_HILLSIDE, 2: MUSIC_PIPEWORKS, 3: MUSIC_SKYBRIDGE}
_STAGE_PALETTE = {1: "hillside", 2: "pipeworks", 3: "skybridge"}
```

### 5d: App.__init__
- pyxel.init, renderer.init_palette(), init_audio()
- State machine: state="title", lives=3, unlocked_stages=1, selected_stage=1
- Gameplay fields: player=None, camera=None, tiles_dict=None, tile_lookup=None, rings=[], springs=[], checkpoints=[], pipes=[], liquid_zones=[], enemies=[], goal_x=0, goal_y=0, active_stage=0, timer_frames=0, death_timer=0, results_timer=0, gameover_timer=0, boss_music_started=False, boss_defeated=False
- play_music(MUSIC_TITLE)
- pyxel.run(self.update, self.draw)

### 5e: update() and draw() dispatch
- Route based on self.state string

### 5f: _update_title / _draw_title
- update: check btnp for Z, Return, Space, or any arrow → switch to stage_select + SFX
- draw: centered title text, flashing "PRESS START"

### 5g: _update_stage_select / _draw_stage_select
- update: UP/DOWN navigate, Z/Return confirm → _load_stage → gameplay
- draw: list stages, cursor indicator, locked stages grayed out

### 5h: _load_stage(stage_num)
- Import and call correct stage module's load()
- Build all game objects from stage data
- Create player, camera
- Extract goal from entities
- Stage 3: inject boss entity into enemies
- Reset timer, particles, death_timer
- Set palette, start music

### 5i: _update_gameplay / _draw_gameplay
- If player dead: handle death_timer → respawn or game_over
- Normal: input → player_update → all collision checks → goal check → enemy update → audio → camera
- Boss music trigger for Stage 3
- Draw: camera, terrain, objects, enemies, player, particles, HUD

### 5j: _respawn_player()
- Create new player at respawn point with respawn_rings
- Reset camera to new position
- Preserve enemies/checkpoints/timer state

### 5k: _update_results / _draw_results
- Timer countdown → unlock next stage → stage_select + title music
- Draw: centered results (stage name, time, rings)

### 5l: _update_game_over / _draw_game_over
- Timer countdown → reset lives → title + title music
- Draw: centered "GAME OVER" text

Verification: manual play test — navigate all states. Automated: test_game_state.py for state transitions.

## Step 6: Write Tests

File: `tests/test_game_state.py`

Test goal collision:
- Player at goal position → REACHED
- Player far from goal → None
- Player dead → None

Test state transition logic (if extractable):
- Death with lives > 0 → respawn
- Death with 0 lives → game over

Existing test files should still pass unchanged.

## Commit Strategy

1. Commit: constants + stage loaders + objects.py + renderer.py (infrastructure)
2. Commit: main.py rewrite (state machine)
3. Commit: tests
