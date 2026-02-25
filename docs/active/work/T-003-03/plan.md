# T-003-03 Plan: Enemy Types

## Step 1: Add enemy constants to constants.py

Add all enemy-related constants: hitbox dimensions, patrol speed/range, chopper jump parameters, bounce velocity, spindash kill threshold.

**Verify:** Constants importable without error.

## Step 2: Create enemies.py with data model and loading

Create `speednik/enemies.py` with:
- `EnemyEvent` enum (DESTROYED, BOUNCE, PLAYER_DAMAGED, SHIELD_BREAK)
- `Enemy` dataclass with all fields
- `load_enemies()` function that filters entity dicts by `enemy_` prefix
- Sets `origin_x = x`, `base_y = y` at load time
- Sets `shielded = True` for guardian type

**Verify:** Import succeeds, load_enemies filters correctly.

## Step 3: Implement enemy update behaviors

Add to `enemies.py`:
- `update_enemies(enemies)` dispatcher
- `_update_crab(enemy)` — patrol movement with direction reversal
- `_update_chopper(enemy)` — jump timer countdown, velocity application, gravity, base_y reset
- Buzzer and Guardian: no update needed (stationary)
- `_get_enemy_hitbox(enemy)` helper returning AABB tuple

**Verify:** Crab patrols correctly, Chopper jumps and falls.

## Step 4: Implement collision detection

Add to `enemies.py`:
- `check_enemy_collision(player, enemies)` iterating all alive enemies
- `_check_single_enemy(player, enemy)` with logic:
  1. Skip dead enemies and DEAD/HURT players
  2. AABB overlap check
  3. Spindash kill check (rolling + ground_speed ≥ 8)
  4. Guardian shield check (only spindash kills)
  5. Bounce kill check (player above + descending or rolling)
  6. Damage check (remaining contact → damage_player)
- Returns list of EnemyEvent

**Verify:** All collision outcomes produce correct events and state mutations.

## Step 5: Write unit tests

Create `tests/test_enemies.py` with:
- Test helpers (create_player, position setup)
- TestLoadEnemies: loading, filtering, type preservation
- TestCrabPatrol: movement, reversal, range
- TestChopperJump: interval, gravity, reset
- TestBounceKill: from above, velocity set, enemy destroyed, event
- TestSpindashKill: through enemy, no bounce, below threshold
- TestSideDamage: damages player, invulnerable skip, dead skip
- TestGuardian: blocks normal, spindash kills, shield break event

**Verify:** `uv run pytest tests/test_enemies.py -v` all pass.

## Step 6: Integrate into main.py

Add to main.py:
- Import enemies module
- Load enemies in `__init__` (demo enemies for now since no stage loader yet)
- Call `update_enemies()` in `update()` after `player_update()`
- Call `check_enemy_collision()` and map events to SFX + particles
- Draw alive enemies in `draw()` using renderer entity drawers

**Verify:** Game runs, demo enemies visible and interactive.

## Testing strategy

- **Unit tests** (step 5): All 4 enemy types, all collision outcomes, patrol/jump behavior
- **Integration check** (step 6): Visual verification that enemies render, patrol, and respond to player interaction
- Tests are Pyxel-free (game logic only)
- Each step is independently committable

## Commit sequence

1. Constants + enemies.py data model + loading
2. Enemy update behaviors
3. Collision detection
4. Unit tests
5. main.py integration
