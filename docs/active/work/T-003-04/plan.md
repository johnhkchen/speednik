# Plan — T-003-04: Egg Piston Boss

## Step 1: Add Boss Constants

**File:** `speednik/constants.py`

Add all boss-related constants after the enemy hitbox block. Values from spec: HP=8, escalation at 4 HP, durations in frames at 60fps.

**Verify:** Constants file imports cleanly (`python -c "from speednik.constants import BOSS_HP"`).

## Step 2: Extend Enemy Dataclass and Events

**File:** `speednik/enemies.py`

- Add 10 boss fields to `Enemy` dataclass (all with defaults so existing enemies unaffected).
- Add `BOSS_HIT` and `BOSS_DEFEATED` to `EnemyEvent` enum.
- Add `"enemy_egg_piston"` to `_HITBOX_SIZES` dict.
- Import new constants.

**Verify:** Existing tests still pass (`uv run pytest tests/test_enemies.py`).

## Step 3: Boss Loading

**File:** `speednik/enemies.py` — `load_enemies()` function

Add egg_piston initialization in the enemy loading loop: set boss_state="idle", boss_hp=BOSS_HP, boss_timer=BOSS_IDLE_DURATION, compute hover_y/ground_y/left_x/right_x from entity position.

**Verify:** Write loading test in step 6, verify manually that load_enemies handles egg_piston entity dicts.

## Step 4: Boss Update Logic

**File:** `speednik/enemies.py`

- Add `_update_egg_piston(enemy)` function with state machine:
  - IDLE: patrol, pick target, transition to DESCEND
  - DESCEND: interpolate y, transition to VULNERABLE
  - VULNERABLE: sit, transition to ASCEND
  - ASCEND: interpolate y, transition to IDLE
- Wire into `update_enemies()` dispatch.

**Verify:** Write state transition tests in step 6.

## Step 5: Boss Collision Logic

**File:** `speednik/enemies.py` — `_check_single_enemy()`

Add egg_piston branch:
- Non-vulnerable: damage player on contact
- Vulnerable: spindash → BOSS_HIT (+ BOSS_DEFEATED if HP=0), jump above → BOUNCE, side → PLAYER_DAMAGED
- Respect boss_hit_timer for invulnerability between hits

**Verify:** Write collision tests in step 6.

## Step 6: Write Boss Tests

**File:** `tests/test_enemies.py`

Add `TestEggPistonLoading`, `TestEggPistonStateTransitions`, `TestEggPistonDamage`, `TestEggPistonEscalation`, `TestEggPistonDefeat`, `TestEggPistonArmorBounce`, `TestEggPistonNonVulnerableDamage` test classes.

Test coverage:
- Loading initializes all boss fields correctly
- Full state cycle: idle(120f) → descend(60f) → vulnerable(90f) → ascend(60f) → idle
- Spindash deals damage, returns BOSS_HIT
- Non-spindash attacks don't deal damage (bounce or player damage)
- Escalation triggers at 4 HP: vulnerable duration changes, idle speed changes
- Defeat at 0 HP: alive=False, BOSS_DEFEATED event
- Boss hit invulnerability prevents double-hit
- Non-vulnerable state contact damages player
- Dead/hurt player skips collision (inherited behavior)
- Invulnerable player not damaged (inherited behavior)

**Verify:** `uv run pytest tests/test_enemies.py -v`

## Step 7: Renderer Indicator

**File:** `speednik/renderer.py`

Add `draw_boss_indicator(x, ground_y, frame_count)` — flashing vertical line/crosshair at target landing position. Simple implementation: alternating-frame vertical dashed line from ground to hover height.

**Verify:** Visual inspection (or just ensure no import errors).

## Step 8: Main Loop Integration

**File:** `speednik/main.py`

- Import new events `BOSS_HIT`, `BOSS_DEFEATED` from enemies.
- Import `SFX_STAGE_CLEAR` from audio.
- Add event handling: `BOSS_HIT` → `play_sfx(SFX_BOSS_HIT)`, `BOSS_DEFEATED` → `play_sfx(SFX_STAGE_CLEAR)`.
- Add boss indicator rendering in draw method: iterate enemies, find active egg_piston, draw indicator if in targeting window.

**Verify:** Full test suite passes. `uv run pytest`

## Step 9: Full Verification

- Run all tests: `uv run pytest`
- Verify no import cycles
- Verify existing enemy behavior is unchanged (TestCrabPatrol, TestChopperJump, TestBounceKill, TestSpindashKill, TestSideDamage, TestGuardian all green)

## Testing Strategy Summary

| Category | Tests | Purpose |
|----------|-------|---------|
| Loading | 3 | Boss fields initialized correctly |
| State transitions | 5 | Each transition fires correctly, timer resets |
| Damage | 4 | Spindash-only damage, HP decrement, hit invuln |
| Escalation | 3 | Triggers at 4 HP, changes duration + speed |
| Defeat | 2 | alive=False, BOSS_DEFEATED event |
| Armor bounce | 2 | Jump from above bounces without damage |
| Non-vulnerable damage | 3 | IDLE/DESCEND/ASCEND contact damages player |
| Edge cases | 3 | Dead player, invulnerable player, dead boss |
