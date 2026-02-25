# T-003-03 Progress: Enemy Types

## Step 1: Add enemy constants — DONE
Added to constants.py: ENEMY_BOUNCE_VELOCITY, CRAB_PATROL_SPEED/RANGE, CHOPPER_JUMP_INTERVAL/VELOCITY, SPINDASH_KILL_THRESHOLD, and hitbox dimensions for all 4 enemy types.

## Step 2: Create enemies.py data model and loading — DONE
Created speednik/enemies.py with EnemyEvent enum, Enemy dataclass, and load_enemies() function. Guardian loads with shielded=True, Chopper gets jump_timer initialized.

## Step 3: Implement enemy update behaviors — DONE
Added update_enemies() dispatcher, _update_crab() patrol logic (direction reversal at ±CRAB_PATROL_RANGE), _update_chopper() jump cycle (timer countdown → velocity application → gravity → base_y reset). Buzzer/Guardian stationary.

## Step 4: Implement collision detection — DONE
Added check_enemy_collision() with _check_single_enemy() implementing: spindash kill (rolling + ground_speed ≥ 8), bounce kill (player above + descending/rolling), guardian shield logic (only spindash kills), and side/below damage. Returns EnemyEvent list.

## Step 5: Write unit tests — DONE
Created tests/test_enemies.py with 36 tests across 7 test classes: TestLoadEnemies (7), TestCrabPatrol (6), TestChopperJump (4), TestBounceKill (4), TestSpindashKill (4), TestSideDamage (6), TestGuardian (5). All pass.

## Step 6: Integrate into main.py — DONE
Added imports, demo enemies (crab + buzzer), enemy update/collision in update(), event-to-SFX mapping (DESTROYED→SFX_ENEMY_DESTROY+particles, BOUNCE→SFX_ENEMY_BOUNCE, PLAYER_DAMAGED→SFX_HURT, SHIELD_BREAK→SFX_BOSS_HIT), and enemy drawing in draw().

## Deviations
- None. Plan followed as written.

## Test results
- 445 tests pass (36 new enemy tests + 409 existing)
