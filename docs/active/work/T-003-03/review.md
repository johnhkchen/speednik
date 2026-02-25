# T-003-03 Review: Enemy Types

## Summary of Changes

### Files Created
- **`speednik/enemies.py`** (~170 lines) — New module containing Enemy dataclass, EnemyEvent enum, loading, per-frame behavior updates, and collision detection. Pyxel-free, event-driven pattern matching objects.py.
- **`tests/test_enemies.py`** (~290 lines) — 36 unit tests across 7 test classes covering all enemy types, behaviors, and collision outcomes.
- **`docs/active/work/T-003-03/`** — RDSPI artifacts (research, design, structure, plan, progress).

### Files Modified
- **`speednik/constants.py`** — Added 15 enemy constants: bounce velocity, crab patrol speed/range, chopper jump interval/velocity, spindash kill threshold, and hitbox dimensions for all 4 types.
- **`speednik/main.py`** — Integrated enemy system: imports, demo enemy entities (crab + buzzer), update/collision calls in game loop with event→SFX mapping, enemy drawing in render pass.

### Files NOT Modified
- `speednik/renderer.py` — Enemy draw functions already existed from T-004-01.
- `speednik/player.py` — `damage_player()` and `get_player_rect()` used as-is.
- `speednik/objects.py` — `aabb_overlap()` reused for enemy collision.
- `speednik/physics.py` — No changes needed.

## Acceptance Criteria Coverage

| Criterion | Status | Implementation |
|-----------|--------|---------------|
| Base: jump/roll on top → destroy + bounce + SFX 4 | ✅ | `_check_single_enemy()`: player_center_y < enemy_center_y + (rolling or y_vel>0) |
| Base: side/below + not rolling → damage | ✅ | Falls through to `damage_player()` call |
| Base: spindash (rolling + ground_speed ≥ 8) → destroy, no bounce | ✅ | Checked first, before bounce logic |
| Base: destroy particle effect | ✅ | `spawn_destroy_particles()` called from main.py on DESTROYED event |
| Crab: patrol 64px, reverse at edges | ✅ | `_update_crab()`: ±32px from origin_x |
| Buzzer: hover in place, stationary | ✅ | No update function needed — stays at spawn position |
| Chopper: jump every ~90 frames | ✅ | `_update_chopper()`: timer countdown → velocity → gravity → base_y reset |
| Guardian: shield blocks front, spindash ≥ 8 breaks | ✅ | Shield check before other collision logic |
| Bounce physics: y_vel enables next platform | ✅ | ENEMY_BOUNCE_VELOCITY = -6.5 (same as JUMP_FORCE, ~96px reach) |
| Loaded from entities.json by type | ✅ | `load_enemies()` filters `enemy_` prefix types |
| Tests: bounce, side damage, spindash, guardian | ✅ | 36 tests, all passing |

## Test Coverage

**36 tests, all passing.** Full test suite: 445 tests, 0 failures.

| Test Class | Count | What it covers |
|-----------|-------|---------------|
| TestLoadEnemies | 7 | Entity filtering, type preservation, shielded/timer initialization |
| TestCrabPatrol | 6 | Movement, direction reversal, full cycle, dead enemy skip |
| TestChopperJump | 4 | Jump trigger, waiting, air physics, base_y reset |
| TestBounceKill | 4 | From-above destruction, velocity set, rolling variant, dead skip |
| TestSpindashKill | 4 | Threshold kill, no bounce, negative speed, below threshold |
| TestSideDamage | 6 | Damage, invulnerability, dead/hurt skip, no overlap, death at 0 rings |
| TestGuardian | 5 | Shield blocks, spindash kills, shield break event, invulnerable, below threshold |

## Architecture Decisions

1. **Flat dataclass** — Single Enemy dataclass with type-specific fields. 4 enemy types don't warrant subclass polymorphism. Follows Ring pattern.
2. **Separate module** — `enemies.py` per specification layout. Keeps objects.py focused on static entities.
3. **AABB + vertical check** — AABB overlap for contact detection, player_center_y vs enemy_center_y for attack direction determination.
4. **Spindash checked first** — Ensures spindash always kills regardless of relative position, matching Sonic 2 behavior.
5. **Guardian instant kill** — Spec says "breaks through shield and destroys it" — single spindash action, not two-phase.

## Open Concerns

1. **Particle spawning in main.py event loop** — Currently iterates all enemies to find dead ones when DESTROYED fires. Works but O(n) per destroy event. Could be improved by returning enemy position with the event. Low priority given small enemy counts.

2. **Demo enemies only** — main.py has hardcoded demo enemies. Real stage loading will replace this when stage loaders wire entities.json data. The `load_enemies()` function is ready for that integration.

3. **No enemy respawn** — Destroyed enemies stay dead (alive=False) permanently. No respawn on death/checkpoint. This matches classic Sonic 2 behavior but may need revisiting if stages require it.

4. **Chopper underwater hitbox** — Chopper at base_y (liquid surface) may interact oddly with liquid damage zones if both are active. The player would take damage from liquid before reaching the chopper. Stage design should account for this.

5. **Guardian physical blocking** — The Guardian doesn't physically obstruct player movement (no tile collision). It damages on contact, which effectively blocks progress since the player bounces back. Real physical blocking would require terrain integration. Current behavior matches the design intent.
