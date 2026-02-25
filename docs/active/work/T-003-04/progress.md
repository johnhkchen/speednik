# Progress — T-003-04: Egg Piston Boss

## Completed

### Step 1: Boss Constants
- Added 14 constants to `speednik/constants.py`: HP, durations, speeds, hitbox, invulnerability, arena bounds.

### Step 2: Enemy Dataclass and Events
- Added 10 boss fields to `Enemy` dataclass (all with defaults, existing enemies unaffected).
- Added `BOSS_HIT` and `BOSS_DEFEATED` to `EnemyEvent` enum.
- Added `"enemy_egg_piston"` to `_HITBOX_SIZES`.
- Imported all new constants.
- All 36 existing tests pass.

### Step 3: Boss Loading
- Added egg_piston initialization in `load_enemies()`: sets boss_state="idle", HP, timer, hover/ground positions, arena bounds.

### Step 4: Boss Update Logic
- Added `_update_egg_piston()` with state machine dispatch.
- Added `_boss_idle()`: patrol, target selection, transition to descend.
- Added `_boss_descend()`: y interpolation hover→ground, transition to vulnerable.
- Added `_boss_vulnerable()`: timer countdown, transition to ascend.
- Added `_boss_ascend()`: y interpolation ground→hover, transition to idle.
- Wired into `update_enemies()` dispatch.

### Step 5: Boss Collision Logic
- Added `_check_boss_collision()` function.
- Vulnerable: spindash → BOSS_HIT (+ BOSS_DEFEATED at 0 HP), jump → BOUNCE, side → PLAYER_DAMAGED.
- Non-vulnerable: all contact → PLAYER_DAMAGED.
- Respects boss_hit_timer for invulnerability between hits.
- Escalation at BOSS_ESCALATION_HP.

### Step 6: Boss Tests
- 34 new tests across 7 test classes.
- All 70 enemy tests pass (36 existing + 34 new).

### Step 7: Renderer Indicator
- Added `draw_boss_indicator()` to renderer.py — flashing dashed line with crosshair.

### Step 8: Main Loop Integration
- Added BOSS_HIT → SFX_BOSS_HIT and BOSS_DEFEATED → SFX_STAGE_CLEAR event handling.
- Added boss targeting indicator rendering before enemy draw pass.

### Step 9: Full Verification
- All 479 tests pass across entire test suite.
- No import cycles.
- No existing behavior changed.

## Deviations from Plan

None. All steps executed as planned.
