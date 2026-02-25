# Design — T-003-04: Egg Piston Boss

## Approach Options

### Option A: Extend Enemy Dataclass

Add boss-specific fields (`boss_state`, `boss_hp`, `boss_timer`, `target_x`, `escalated`) directly to the existing `Enemy` dataclass. Boss logic lives in `enemies.py` alongside all other enemy types.

**Pros:** Consistent with existing patterns. No new modules. Loading, update, collision, and rendering all follow established dispatch paths. Tests follow existing patterns exactly.

**Cons:** Enemy dataclass grows with more type-specific fields. `_check_single_enemy` gets another special case branch.

### Option B: Separate Boss Module

Create `speednik/boss.py` with a dedicated `Boss` dataclass and its own update/collision functions. Main loop calls boss update separately.

**Pros:** Cleaner separation. Boss complexity doesn't pollute the basic enemy module.

**Cons:** Duplicates patterns (AABB collision, player interaction, event dispatch). Main loop needs additional integration. Renderer still needs to know about boss states. Two different entity systems to maintain.

### Option C: Entity Component System

Refactor all enemies into a component-based architecture. Boss is just another entity with a state-machine component.

**Cons:** Massive scope creep. Overkill for 5 enemy types. Rejects the established pattern.

## Decision: Option A — Extend Enemy Dataclass

The codebase uses a flat dataclass with type-based dispatch throughout. The guardian already demonstrates how to add special-case collision handling. Adding 5 fields to Enemy is a smaller change than introducing a parallel entity system. The `enemy_type` dispatch pattern in `update_enemies` and `_check_single_enemy` is proven and tested.

Option B was rejected because it would create parallel infrastructure (loading, collision, events) for a single entity that fundamentally works the same way as other enemies — it has a position, hitbox, alive state, and interacts with the player through AABB overlap.

## State Machine Design

```
IDLE (120f) → DESCEND (60f) → VULNERABLE (90/60f) → ASCEND (60f) → IDLE ...
```

State stored as string field `boss_state` on Enemy. Timer stored as `boss_timer` (int, counts down each frame). Transitions happen when timer hits 0.

### IDLE State
- Boss hovers at `boss_hover_y` (set during loading, top of arena area).
- Moves left/right between `boss_left_x` and `boss_right_x` at `BOSS_IDLE_SPEED` (1.0 px/frame, doubles to 2.0 after escalation).
- At `boss_timer == 60` (1s before DESCEND), pick a target x-position for landing and store in `boss_target_x`. This is where the targeting indicator appears.
- Transition: timer expires → DESCEND.

### DESCEND State
- Boss moves linearly from `boss_hover_y` to `boss_ground_y` over 60 frames.
- X position moves toward `boss_target_x` (may already be there from IDLE).
- Player can be crushed during descent (damage if overlapping).
- Transition: timer expires → VULNERABLE.

### VULNERABLE State
- Boss sits at `boss_ground_y`. No movement.
- Duration: 90 frames (pre-escalation) or 60 frames (post-escalation).
- Spindash at ground_speed >= 8 deals 1 HP damage. Boss stays in VULNERABLE after hit (can be hit again if player repositions fast enough, but invulnerability frames on boss prevent double-hits in same charge).
- Regular jump on top: player bounces off armor (gets ENEMY_BOUNCE_VELOCITY), no damage to boss.
- Side contact: damages player (like other enemies).
- Transition: timer expires → ASCEND.

### ASCEND State
- Boss rises from `boss_ground_y` to `boss_hover_y` over 60 frames.
- Damages player if overlapping (upward crush).
- Transition: timer expires → IDLE.

### Escalation
At 4 hits (`boss_hp` drops from 8 to 4):
- `boss_escalated = True`
- VULNERABLE duration changes from 90 to 60 frames.
- IDLE movement speed doubles (handled by checking escalated flag during IDLE update).

### Defeat
At 0 HP:
- `alive = False`
- Return new event `BOSS_DEFEATED` (or `STAGE_CLEAR`).
- Main loop plays `SFX_STAGE_CLEAR` (slot 10).

## New Enemy Fields

```python
# Boss state machine
boss_state: str = ""          # "idle", "descend", "vulnerable", "ascend", "" for non-boss
boss_timer: int = 0           # Countdown timer for current state
boss_hp: int = 0              # Health points (8 for egg piston)
boss_escalated: bool = False  # True after 4 hits
boss_target_x: float = 0.0   # X position where boss will land
boss_hover_y: float = 0.0    # Y position at top of arena
boss_ground_y: float = 0.0   # Y position on ground
boss_hit_timer: int = 0       # Invulnerability after being hit (prevents multi-hit per charge)
```

## New Constants

```python
BOSS_HP = 8
BOSS_ESCALATION_THRESHOLD = 4  # hits remaining when escalation triggers
BOSS_IDLE_DURATION = 120       # 2.0s at 60fps
BOSS_DESCEND_DURATION = 60     # 1.0s
BOSS_VULNERABLE_DURATION = 90  # 1.5s
BOSS_VULNERABLE_DURATION_ESCALATED = 60  # 1.0s
BOSS_ASCEND_DURATION = 60      # 1.0s
BOSS_IDLE_SPEED = 1.0          # px/frame
BOSS_IDLE_SPEED_ESCALATED = 2.0
BOSS_INDICATOR_LEAD = 60       # frames before descend when indicator appears
BOSS_HITBOX_W = 24
BOSS_HITBOX_H = 32
BOSS_HIT_INVULNERABILITY = 30  # frames after taking damage
```

## New Events

Add to `EnemyEvent`:
- `BOSS_HIT` — spindash damage dealt (triggers SFX slot 11)
- `BOSS_DEFEATED` — boss HP reaches 0 (triggers SFX slot 10, stage clear sequence)

The existing `SHIELD_BREAK` event currently maps to SFX_BOSS_HIT in main.py. For the boss, `BOSS_HIT` is more semantically correct and maps to the same SFX. `SHIELD_BREAK` stays for guardian.

## Collision Design

Boss collision is state-dependent:
- **IDLE / ASCEND**: Contact damages player. No damage to boss possible.
- **DESCEND**: Contact damages player (crush). No damage to boss.
- **VULNERABLE**: Spindash (rolling + ground_speed >= 8) → BOSS_HIT event, decrement HP, set boss_hit_timer. Regular jump from above → BOUNCE (player bounces, boss undamaged). Side/below contact → PLAYER_DAMAGED.

## Renderer Updates

The existing `_draw_enemy_egg_piston` draws a static boss. For state awareness:
- Pass boss state info through the existing `frame_count` parameter pattern (renderer reads enemy state from global or passed reference).
- Alternative: renderer receives the Enemy object and checks `boss_state` field.
- Decision: Keep existing drawer as base, add a separate `draw_boss_indicator()` for the targeting marker. The main loop will need to pass boss state to the renderer for the indicator. Since the existing pattern passes only `(x, y, frame_count)` to drawers, we'll add a small wrapper in main.py that draws the indicator before the enemy draw pass.

## Testing Strategy

All boss logic testable without Pyxel:
1. State transitions — construct boss Enemy, call update, verify state/timer changes
2. Collision — construct player + boss in each state, verify correct events
3. Damage — only spindash deals damage, verify HP decrements
4. Escalation — verify at exactly 4 hits remaining
5. Defeat — verify alive=False and BOSS_DEFEATED event at 0 HP
6. Armor bounce — verify jump bounces without dealing damage
7. ASCEND/DESCEND crush damage — verify player damaged on overlap
