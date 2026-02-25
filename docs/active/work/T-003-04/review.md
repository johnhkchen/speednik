# Review — T-003-04: Egg Piston Boss

## Summary of Changes

### Files Modified (5)

| File | Lines Changed | Description |
|------|--------------|-------------|
| `speednik/constants.py` | +15 | 14 boss constants (HP, durations, speeds, hitbox, invulnerability, arena bounds) |
| `speednik/enemies.py` | +130 | Boss fields on Enemy, BOSS_HIT/BOSS_DEFEATED events, loading, state machine, collision |
| `speednik/renderer.py` | +12 | `draw_boss_indicator()` — flashing crosshair at landing target |
| `speednik/main.py` | +14 | Event→SFX wiring (BOSS_HIT→SFX 11, BOSS_DEFEATED→SFX 10), indicator rendering |
| `tests/test_enemies.py` | +245 | 34 new tests across 7 test classes |

### Files Created (5)

| File | Description |
|------|-------------|
| `docs/active/work/T-003-04/research.md` | Codebase mapping for boss implementation |
| `docs/active/work/T-003-04/design.md` | Design decisions, approach selection, state machine spec |
| `docs/active/work/T-003-04/structure.md` | File-level change blueprint |
| `docs/active/work/T-003-04/plan.md` | Step-by-step implementation sequence |
| `docs/active/work/T-003-04/progress.md` | Implementation tracking |

## Acceptance Criteria Verification

- [x] **Boss state machine with 4 states**: IDLE (120f), DESCEND (60f), VULNERABLE (90→60f), ASCEND (60f) — implemented in `_update_egg_piston()` with per-state functions.
- [x] **Damage: only spindash (ground_speed >= 8)**: `_check_boss_collision()` checks `is_spindash_kill` flag. Regular jumps bounce off armor.
- [x] **SFX slot 11 on hit**: `BOSS_HIT` event maps to `SFX_BOSS_HIT` (slot 11) in main.py.
- [x] **HP: 8 hits total**: `BOSS_HP = 8`, decremented in collision handler.
- [x] **Escalation at 4 hits**: `BOSS_ESCALATION_HP = 4`. When HP drops to 4: VULNERABLE window shrinks to 60f, IDLE speed doubles to 2.0 px/frame.
- [x] **Targeting indicator**: `draw_boss_indicator()` renders flashing crosshair at `boss_target_x`. Target selected 60 frames before descent.
- [x] **Boss defeat triggers stage clear**: `BOSS_DEFEATED` event maps to `SFX_STAGE_CLEAR` (slot 10).
- [x] **Unit tests**: 34 tests covering state transitions, spindash-only damage, escalation trigger, invulnerability during non-VULNERABLE states.

## Test Coverage

| Test Class | Tests | Coverage Area |
|-----------|-------|---------------|
| TestEggPistonLoading | 3 | Boss field initialization from entity data |
| TestEggPistonStateTransitions | 8 | All 4 state transitions, full cycle, timer behavior, dead boss skip |
| TestEggPistonMovement | 8 | Patrol, edge reversal, escalated speed, hover/descend/ascend interpolation |
| TestEggPistonDamage | 5 | Spindash damage, hit invulnerability, armor bounce, side damage |
| TestEggPistonEscalation | 3 | Trigger at threshold, no premature escalation, persistence |
| TestEggPistonDefeat | 2 | Death at 0 HP, event ordering |
| TestEggPistonNonVulnerableDamage | 5 | IDLE/DESCEND/ASCEND crush, invulnerable player, spindash blocked |
| **Total** | **34** | |

All 479 tests pass (36 existing enemy + 34 new boss + 409 other).

## Design Decisions

1. **Extended Enemy dataclass** rather than creating a separate Boss class. This follows the established pattern (crab, buzzer, chopper, guardian all share the same struct). Boss fields default to zero/empty, so existing enemies are unaffected.

2. **State stored as string** (`"idle"`, `"descend"`, etc.) rather than an enum. Matches the codebase's existing string-based type dispatch pattern. Keeps it simple.

3. **Boss hit invulnerability** (30 frames) prevents multiple hits from a single spindash pass. Without this, a fast spindash could register several overlapping collision frames.

4. **Target selection at BOSS_INDICATOR_LEAD** (60 frames before descent) clamps to current x position within arena bounds. This gives the player 1 second of visual warning before the boss lands.

## Open Concerns

1. **No stage clear sequence yet**: `BOSS_DEFEATED` plays SFX slot 10 but doesn't trigger a gameplay transition (results screen, credits, etc.). That's likely a separate ticket for the game state machine.

2. **Boss music not triggered**: The boss theme (`MUSIC_BOSS`, track 4) exists in audio.py but nothing starts it when the boss fight begins. The main loop would need stage/boss awareness to switch music.

3. **Rendering is state-unaware**: The `_draw_enemy_egg_piston()` renderer draws the same static pose in all states. The vulnerable state cockpit exposure is conceptual only — the same visual is used. A future polish pass could add visual differentiation (e.g., cockpit glow during VULNERABLE, armor flash during hit invulnerability).

4. **Arena bounds are computed from spawn position**: `boss_left_x/right_x = spawn ± 128px`. This works if the boss entity is placed at the center of the arena. If stage data places it off-center, the patrol bounds could extend outside the arena walls.

5. **No boss health bar HUD**: The player has no visual indication of boss HP or escalation state. This could be a separate HUD ticket.

None of these are blockers — they represent polish and integration work outside the scope of T-003-04.
