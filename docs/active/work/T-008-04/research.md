# Research — T-008-04: Level Softlock Detection

## Objective

Run robotic player strategies against real stage data and verify each level is completable
with its design-intended strategy. Detect structural blockages where ALL strategies fail.

## Relevant Files

### Test Harness (tests/harness.py)
- `run_on_stage(stage_name, strategy, frames)` — loads real stage, runs from player_start
- `run_scenario(tile_lookup, start_x, start_y, strategy, frames)` — core simulation loop
- `ScenarioResult.max_x` — maximum X position reached across all frames
- `ScenarioResult.stuck_at(tolerance, window)` — sliding-window stuck detection
- Strategies: `idle()`, `hold_right()`, `hold_right_jump()`, `spindash_right()`, `scripted()`
- All Pyxel-free — calls `player_update(player, inp, tile_lookup)` each frame

### Stage Loading (speednik/level.py)
- `load_stage(stage_name)` → `StageData` with tile_lookup, entities, player_start, etc.
- Three stages registered: "hillside", "pipeworks", "skybridge"
- `StageData.entities` — raw entity list (dicts with "type", "x", "y" keys)
- No `get_goal_x()` helper exists yet — must extract from entities

### Stage Data (speednik/stages/*/meta.json + entities.json)

| Stage     | Start          | Goal           | Size         | Key Entities                    |
|-----------|---------------|----------------|--------------|--------------------------------|
| hillside  | (64, 610)     | (4758, 642)    | 4800×720     | rings, springs_up, enemies     |
| pipeworks | (200, 510)    | (5558, 782)    | 5600×1024    | pipes, liquid_triggers, springs |
| skybridge | (64, 490)     | (5158, 482)    | 5200×896     | rings, springs_up, enemies     |

### Physics (speednik/player.py, speednik/physics.py)
- `player_update()` is the complete frame update — no objects/springs/pipes handled
- The harness does NOT process springs, pipes, liquid zones, or enemies
- `PlayerState`: STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD
- Constants: TOP_SPEED=6.0, JUMP_FORCE=6.5, GRAVITY=0.21875

### Object Interaction (speednik/objects.py)
- `check_spring_collision()` — applies velocity override
- `update_pipe_travel()` — handles pipe entry/travel/exit
- `update_liquid_zones()` — rising liquid damage
- `check_goal_collision(player, goal_x, goal_y)` — distance-based (radius=24)
- None of these are called by the harness's `run_on_stage()`

### Existing Integration Tests (tests/test_hillside_integration.py)
- Tests validate tile properties: ramp angles, loop solidity, ground continuity
- Uses `load_stage("hillside")` directly
- Defines region constants for loop geometry
- Does NOT run player simulations

### Existing Harness Tests (tests/test_harness.py)
- Tests `run_scenario` with synthetic flat ground
- Tests `ScenarioResult` helper methods
- Tests each strategy factory's input generation
- Uses `flat_ground_lookup()` helper (width=30 tiles)

## Key Constraints and Observations

### 1. Harness is physics-only
The harness calls `player_update()` which handles terrain collision, but does NOT call
any object interaction functions (springs, pipes, goals). For level completion testing,
we need to compare max_x against goal_x — we cannot rely on GoalEvent.REACHED.

### 2. Springs and pipes matter for pipeworks
Pipeworks has springs and launch pipes. Without processing these, a player running
`hold_right_jump` may not actually reach the goal. However, the ticket's acceptance
criteria say `hold_right_jump` should reach the goal. This implies either:
- The level is designed so terrain alone is sufficient with jumping, OR
- We need to add spring/pipe processing to the simulation

Looking at the harness design: it deliberately only uses controls a real player has.
Springs and pipes are terrain features that respond to player position — they should
be processed. But the current harness doesn't do this.

**Decision needed**: Do we extend the harness, or test with physics-only and adjust
expectations? The ticket says test at `tests/test_levels.py` and uses `run_on_stage`.

### 3. Goal check is distance-based
`GOAL_ACTIVATION_RADIUS = 24`. Rather than checking GoalEvent, we can compare
`result.max_x >= goal_x` which is a simpler and sufficient proxy.

### 4. Frame counts
- 3600 frames = 60 seconds at 60fps — generous for hillside (4800px wide)
- 5400 frames for skybridge — extra time for spindash cycling
- At TOP_SPEED=6.0: 3600 frames × 6 px/frame = 21,600px (well over any stage width)
- At walking speed: slower acceleration means ~2-3x longer

### 5. S-007 dependency
Hillside's `hold_right` test should be `xfail` until S-007 loop ramps land.
S-007 story status needs checking but the ticket explicitly says to use xfail.

### 6. Stall detection already exists
`ScenarioResult.stuck_at(tolerance=2.0, window=30)` is ideal for identifying WHERE
a player gets stuck. The ticket wants stall X in failure messages.

### 7. No existing tests/test_levels.py
This file does not exist yet — it's entirely new.

## Patterns from Existing Tests

- Module-level cached stage loading (`_stage = None; def _get_stage()`)
- `from speednik.level import load_stage` for stage access
- `from tests.harness import run_on_stage, hold_right, ...` for strategies
- No Pyxel imports in any test file
- Descriptive assertion messages with coordinates
- Class-based test grouping (TestRampTilesExist, TestLoopTileType, etc.)
