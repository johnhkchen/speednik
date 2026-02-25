# T-003-03 Design: Enemy Types

## Decision 1: Where does enemy logic live?

### Option A: Add to objects.py alongside rings/springs
- Pro: Single import, existing pattern
- Con: objects.py is already 441 lines; enemy behavior (patrol, jumping, shield state) is fundamentally different from static objects

### Option B: New enemies.py module
- Pro: Specification lists `enemies.py` in the package layout (§1). Separates behavioral entities from static objects. Each module stays focused.
- Con: One more file

**Decision: Option B.** The spec explicitly names `enemies.py`. Enemies have per-frame update logic (patrol, jumping, shield transitions) that static objects don't. Follows existing architecture — objects.py handles rings/springs/pipes, enemies.py handles behavioral entities.

## Decision 2: Enemy data model

### Option A: Single Enemy dataclass with type-specific fields
```python
@dataclass
class Enemy:
    x: float; y: float; enemy_type: str
    alive: bool = True
    origin_x: float = 0.0       # crab patrol
    facing_right: bool = True    # crab direction
    jump_timer: int = 0          # chopper
    shielded: bool = False       # guardian
```
- Pro: Simple, one list to iterate
- Con: Wasted fields per type, unclear which fields apply to which type

### Option B: Base dataclass + subclasses per type
- Pro: Type-safe, no wasted fields
- Con: More boilerplate, polymorphic dispatch needed, load function becomes complex

### Option C: Single dataclass with a state dict for type-specific data
```python
@dataclass
class Enemy:
    x: float; y: float; enemy_type: str; alive: bool = True
    origin_x: float = 0.0  # set at load from x
    patrol_dir: int = 1     # crab only
    jump_timer: int = 0     # chopper only
    base_y: float = 0.0     # chopper only
    shielded: bool = True   # guardian only
```
- Pro: Single type, single list, simple iteration; a few unused fields per type are cheap
- Con: Slightly loose

**Decision: Option C (flat dataclass).** With only 4 enemy types and ~5 type-specific fields, subclass polymorphism is overengineering. The ring system uses a flat Ring dataclass. Follow the same pattern. Unused fields cost nothing at this scale. Update logic dispatches on `enemy_type` string.

## Decision 3: Collision detection approach

### Option A: Circular radius (like rings)
- Pro: Simple
- Con: Enemies have rectangular visuals; circle collision doesn't match

### Option B: AABB (like springs/pipes)
- Pro: Matches rectangular enemy shapes, `aabb_overlap()` already exists
- Con: Need hitbox dimensions per enemy type

### Option C: Hybrid — AABB for detection, then vertical position check for bounce vs damage
- Pro: AABB overlap detects contact; player-center-y vs enemy-center-y determines attack direction

**Decision: Option C.** AABB detects overlap. Then determine outcome:
- Player center above enemy center AND (player is_rolling OR y_vel > 0 descending) → **bounce kill**
- Player is_rolling AND abs(ground_speed) ≥ SPINDASH_BASE_SPEED (8) → **spindash kill** (regardless of vertical position)
- Otherwise → **damage** (unless invulnerable)

For Guardian: spindash kill requirement applies to breaking shield; front-check uses player facing vs guardian position.

## Decision 4: Hitbox sizes

Derive from renderer visual bounds with slight padding:

| Type | Width | Height | Notes |
|------|-------|--------|-------|
| Crab | 16 | 14 | Body ellipse only (exclude claws for fair gameplay) |
| Buzzer | 12 | 12 | Circle body + partial wing area |
| Chopper | 8 | 16 | Elongated body |
| Guardian | 24 | 28 | Full shield rectangle |

These will be constants in constants.py.

## Decision 5: Enemy bounce velocity

Ticket says: "y_vel set to a consistent upward value that enables reaching the next platform." Stage 3 rhythm loops place platforms ~48-64px above enemies. At GRAVITY = 0.21875, to reach height h: v = sqrt(2 * g * h).

- h=48: v = sqrt(2 * 0.21875 * 48) ≈ 4.58
- h=64: v = sqrt(2 * 0.21875 * 64) ≈ 5.29
- JUMP_FORCE = 6.5 (covers ~96px)

**Decision: ENEMY_BOUNCE_VELOCITY = -6.5** (same as JUMP_FORCE). This provides comfortable height to reach next platforms. Using the same value as jump makes the mechanic feel consistent.

## Decision 6: Crab patrol speed

Spec doesn't define. Player TOP_SPEED = 6.0. Crab should be slow enough to easily react to.

**Decision: CRAB_PATROL_SPEED = 0.5 px/frame.** At 60fps, covers 64px patrol range in ~2 seconds round-trip. Visually readable, non-threatening speed.

## Decision 7: Chopper jump parameters

Spec says "every ~90 frames" and "reaches a fixed height."

**Decision:**
- CHOPPER_JUMP_INTERVAL = 90 frames (1.5 seconds)
- CHOPPER_JUMP_VELOCITY = -5.0 (reaches ~57px above surface, enough to threaten platform players)
- Uses GRAVITY for descent naturally

## Decision 8: Event types for enemy interactions

Follow the event pattern from objects.py:

```python
class EnemyEvent(Enum):
    DESTROYED = "destroyed"      # enemy killed (any method)
    BOUNCE = "bounce"            # player bounced off enemy
    PLAYER_DAMAGED = "player_damaged"
    SHIELD_BREAK = "shield_break"  # guardian shield broken
```

main.py maps: DESTROYED → SFX_ENEMY_DESTROY + particles, BOUNCE → SFX_ENEMY_BOUNCE, PLAYER_DAMAGED → SFX_HURT, SHIELD_BREAK → SFX_BOSS_HIT.

## Decision 9: Guardian shield-break vs destroy

Two-phase: spindash ≥ 8 from behind/side → shield breaks (SHIELD_BREAK event). Guardian becomes a normal enemy. Then any normal attack destroys it. This matches the spec: "breaks through shield and destroys it." Reading more carefully — "Spindash at ground_speed >= 8 breaks through shield and destroys it" — single action. So spindash ≥ 8 both breaks shield AND destroys in one hit.

**Decision:** Spindash ≥ 8 is an instant kill on Guardian regardless of shield. Other attacks from front are blocked (no damage to player, but no kill either — player just stops). Other attacks from above bounce as normal if shield is already broken... but since spindash destroys immediately, the only other scenario is: player jumps on top without spindash, which should be blocked by the shield.

Simplified: Guardian with shield → only spindash ≥ 8 kills. All other contact blocks/damages. Simple boolean check.

## Rejected approaches

1. **ECS (Entity Component System)**: Way too heavy for 4 enemy types with straightforward behavior. Would require component registry, system dispatcher, etc. Not worth it.

2. **Enemies inside objects.py**: Violates the spec's module layout and would bloat an already substantial file.

3. **Per-type subclasses**: Adds boilerplate without meaningful safety given the small type count and simple dispatch.

4. **Distance-based collision**: AABB better matches rectangular enemy shapes and is already the pattern used for springs/pipes.
