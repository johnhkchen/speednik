# Design — T-004-03: Game State Machine

## Approach Options

### Option A: Monolithic Rewrite of main.py

Replace `App.__init__`/`update`/`draw` with a state machine using string state and dispatch. All state logic lives in main.py methods. Stage loading, menu rendering, transitions — everything in one file.

Pros: Simple, self-contained. No new modules. All game flow visible in one file.
Cons: main.py grows large (~500+ lines). Mixing UI rendering with game logic.

### Option B: Separate State Classes

Create a `GameState` base class and subclasses (TitleState, StageSelectState, etc.) each with `update()` and `draw()`. App dispatches to the active state object.

Pros: Clean separation. Easy to test individual states.
Cons: Over-engineered for 5 states with simple logic. Adds class hierarchy complexity. State transitions need shared mutable context (lives, unlocked stages, selected stage).

### Option C: State Machine in main.py with Helpers

Keep the state machine routing in main.py but extract reusable helpers (goal check in objects.py, StageData extension) to existing modules. Main.py owns the state transitions and rendering dispatch. Helper functions handle the mechanics.

Pros: Balances cohesion and separation. Keeps game flow readable. Leverages existing module boundaries. Minimal new abstractions.
Cons: main.py still substantial, but manageable.

## Decision: Option C

Option C is the right fit. The game has 5 states, each with ~20 lines of update logic and ~20 lines of draw logic. That doesn't justify a class hierarchy. The state machine is simple enough to read in one file, and the mechanical helpers (goal collision, stage loading) belong in their existing modules.

Option A was close but puts too much rendering detail in main.py. Option B introduces unnecessary abstraction for a game this size.

## Design Details

### State Machine States

```
TITLE → STAGE_SELECT → GAMEPLAY → RESULTS → STAGE_SELECT
                                          → GAME_OVER → TITLE
```

String enum: `"title"`, `"stage_select"`, `"gameplay"`, `"results"`, `"game_over"`.

### Shared Context (App attributes)

- `state: str` — current state
- `lives: int` — starts at 3, persists across stages, resets on game over
- `unlocked_stages: int` — 1..3, incremented on stage completion
- `selected_stage: int` — cursor position in stage select
- `active_stage: int` — which stage is loaded (1, 2, 3)
- `timer_frames: int` — gameplay timer, reset per stage
- `results_timer: int` — countdown in results screen
- `death_timer: int` — delay after death before respawn/game over

### Gameplay State Fields (populated on stage load)

- `player: Player`
- `camera: Camera`
- `tile_lookup: TileLookup`
- `tiles_dict: dict` — for renderer
- `rings, springs, checkpoints, pipes, liquid_zones, enemies` — loaded objects
- `goal_x, goal_y: float` — extracted from entities
- `boss_defeated: bool` — tracks whether Stage 3 boss is dead

### State Transitions

**TITLE:**
- Any button press (Z, Return, arrow) → play SFX_MENU_CONFIRM → STAGE_SELECT
- Music: MUSIC_TITLE (looping)

**STAGE_SELECT:**
- Up/Down arrows → change `selected_stage` within 1..`unlocked_stages`, play SFX_MENU_SELECT
- Z or Return → load selected stage → GAMEPLAY
- Music: MUSIC_TITLE continues

**GAMEPLAY:**
- Goal collision → stop music → play SFX_STAGE_CLEAR → RESULTS
- Player DEAD state detected → death_timer countdown → if lives > 0: respawn, else GAME_OVER
- ESC → pause overlay (stretch goal, not in AC — skip for now)
- Boss defeated event → stop stage music → play MUSIC_CLEAR (handled in results transition)
- Music: stage-specific (HILLSIDE/PIPEWORKS/SKYBRIDGE), switch to BOSS when boss fight starts

**RESULTS:**
- Display time, ring count, score
- Music: MUSIC_CLEAR
- Auto-advance after ~300 frames (5 seconds) → unlock next stage → STAGE_SELECT

**GAME_OVER:**
- Music: MUSIC_GAMEOVER
- After jingle finishes + delay → TITLE
- Reset lives to 3, keep unlocked_stages

### Death and Respawn

When `player.state == PlayerState.DEAD`:
1. Start `death_timer` (120 frames = 2 seconds)
2. When timer expires:
   - If `lives > 0`: decrement lives, respawn at `respawn_x/y` with `respawn_rings`, reset physics
   - If `lives == 0`: transition to GAME_OVER

Respawn resets: player position to respawn point, player state to STANDING, physics to ground state, rings to respawn_rings. Does NOT reset enemies, checkpoints, or timer.

### Stage Loading

A `_load_stage(stage_num)` method on App:
1. Import the correct stage module
2. Call `.load()` to get `StageData` (now including `tiles_dict`)
3. Create player at `player_start`
4. Load all objects from `entities`
5. Extract goal position
6. For Stage 3: inject boss entity
7. Reset timer, set palette, start stage music
8. Set camera

### Goal Collision

Add `check_goal_collision(player, goal_x, goal_y)` to `objects.py`. Simple radius check — player within ~24px of goal → return True. Reuse existing `CHECKPOINT_ACTIVATION_RADIUS` or define `GOAL_ACTIVATION_RADIUS`.

### StageData Extension

Add `tiles_dict: dict[tuple[int, int], Tile]` to `StageData` in `hillside.py`. Update all three loaders to populate it. This is a 1-line change per file.

### Skybridge Cleanup

`skybridge.py` duplicates `StageData`. Change it to import from `hillside` like `pipeworks.py` already does.

### Boss Injection for Stage 3

After loading skybridge entities and enemies, append a synthetic boss entity dict:
```python
{"type": "enemy_egg_piston", "x": 4800, "y": 480}
```
Position based on boss arena section (roughly x=4600-5000, ground at y~480). The `load_enemies()` function will handle the rest — initializing boss state machine fields.

### Boss Music Transition

During GAMEPLAY, when entering the boss arena area (player x > boss_arena_start), switch from stage music to MUSIC_BOSS. Track with a `boss_music_started` flag to avoid re-triggering.

### Rendering per State

| State | Draws |
|-------|-------|
| TITLE | Sky background, game title text, "PRESS START" flashing text |
| STAGE_SELECT | Stage list with cursor, lock indicators |
| GAMEPLAY | Full game (terrain, objects, player, enemies, HUD) |
| RESULTS | Results overlay (time, rings, score) |
| GAME_OVER | "GAME OVER" text, "Press any key" after delay |

### Rejected Alternatives

- **Separate renderer for menus:** Not needed. Title/select/results are 5-10 `pyxel.text()` calls each. Adding a new module for this is overhead with no benefit.
- **Persistent game state object:** A separate `GameSession` dataclass to hold lives/unlocked stages. Over-abstraction for 3 fields. App attributes suffice.
- **Event bus for state transitions:** Unnecessary complexity. Direct assignment (`self.state = "results"`) is clear and traceable.
