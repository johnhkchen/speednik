# T-003-01 Research — Ring System

## Scope

Implement the ring collection, scatter, and recollection system — the core pickup mechanic and damage buffer. This ticket covers: world ring entities loaded from stage data, collection detection, SFX triggers, 100-ring extra life, HUD ring counter with flash-at-zero, and unit tests.

## Existing Ring Infrastructure

### Already implemented in `player.py`

The player module (T-001-04) already contains significant ring-related logic:

1. **`ScatteredRing` dataclass** (line 63): `x, y, vx, vy, timer` — represents a ring ejected on damage. Timer defaults to `SCATTER_RING_LIFETIME` (180 frames = 3 seconds).

2. **`Player` dataclass** (line 73): Has `rings: int = 0`, `lives: int = 3`, `scattered_rings: list[ScatteredRing]`.

3. **`damage_player()`** (line 241): Checks invulnerability, then either scatters rings (if rings > 0) or kills player (if rings == 0). Sets HURT state, knockback, invulnerability timer.

4. **`_scatter_rings()`** (line 267): Creates up to `MAX_SCATTER_RINGS` (32) ScatteredRing objects in a fan pattern with alternating angles and varying speeds.

5. **`_update_scattered_rings()`** (line 286): Applies gravity and movement to scattered rings, removes expired ones (timer <= 0).

6. **`_check_ring_collection()`** (line 299): Checks distance from player center to each scattered ring. Collection radius is 16px. Increments `player.rings` on collection.

7. **Frame update order** in `player_update()` (line 102): Subsystem updates run after physics/collision: `_update_invulnerability` → `_update_scattered_rings` → `_check_ring_collection` → `_update_animation`.

### What is NOT implemented

- **World ring entities**: No `Ring` dataclass for level-placed rings
- **World ring collection**: No detection of player overlap with level rings
- **SFX triggers**: `damage_player()` doesn't call `play_sfx(SFX_RING_LOSS)` or `play_sfx(SFX_HURT)`; ring collection doesn't call `play_sfx(SFX_RING)`
- **100-ring extra life**: No logic to award a life at 100 rings
- **HUD ring counter**: `main.py` shows `Rings: {player.rings}` in debug text but no proper HUD with flash-at-zero
- **Ring rendering**: No rendering of world rings (scattered rings are drawn as circles in main.py)

## Audio System

`audio.py` defines all SFX constants and the playback API:

- `SFX_RING = 0` — ring collect sound (bright ascending arpeggio)
- `SFX_RING_LOSS = 7` — scatter sound (descending)
- `SFX_HURT = 8` — death sound (harsh descending)
- `SFX_1UP = 15` — extra life jingle
- `play_sfx(sfx_id: int)` — plays on channel 3 with percussion ducking

The audio module depends on `pyxel` being initialized. Game logic modules (player.py) currently don't import audio — they are Pyxel-free for testability.

## Stage/Entity System

### Stage loader pattern (`stages/hillside.py`)

`StageData` dataclass holds: `tile_lookup`, `entities: list[dict]`, `player_start`, `checkpoints`, `level_width`, `level_height`.

Entities are loaded from `entities.json` as raw dicts with `type`, `x`, `y` keys. Ring entities have `"type": "ring"`.

### Current main.py integration

`main.py` builds a hardcoded demo level (`_build_demo_level()`), not using stage loaders yet. The draw method renders:
- Tiles via column-by-column height rendering
- Player as a colored rectangle
- Scattered rings as small circles (color 10 = yellow)
- Debug HUD text (state, speed, position, rings, angle, on-ground)

## Test Patterns

`tests/test_player.py` establishes the testing pattern:
- Helper functions: `flat_tile()`, `make_tile_lookup()`, `flat_ground_lookup()`, `empty_lookup()`
- Test classes organized by feature: `TestCreatePlayer`, `TestStateTransitions`, `TestSpindashFlow`, etc.
- Tests are Pyxel-free — they operate on dataclasses and functions only
- `pytest.approx()` for float comparisons

Existing damage tests cover: scatter with rings, death without rings, invulnerability prevention, scatter expiry, dead state stops updates, max scatter cap.

## Constants

All ring-related constants are in `constants.py`:
- `INVULNERABILITY_DURATION = 120` (2 seconds)
- `MAX_SCATTER_RINGS = 32`
- `SCATTER_RING_LIFETIME = 180` (3 seconds)
- `HURT_KNOCKBACK_X = 2.0`, `HURT_KNOCKBACK_Y = -4.0`

Missing: `RING_COLLECTION_RADIUS` (currently hardcoded as `16` in `_check_ring_collection`), `EXTRA_LIFE_THRESHOLD` (100).

## Specification Requirements (§5.4, §5.5, §8)

- **Rings**: Small yellow circles with rotating highlight line (color 7 = ring yellow)
- **HUD**: Top-left: ring count (flashes at 0), timer, lives count. Drawn with `pyxel.text()`
- **Ring system**: +1 on collect, SFX 0; scatter on damage with rings, SFX 7; death on damage without rings, SFX 8
- **Extra life**: 100 rings = +1 life, SFX 15
- **Scattered rings**: Recollectable for ~3 seconds, then disappear

## Architectural Constraints

1. **Pyxel-free game logic**: The `player.py` pattern keeps game logic testable without Pyxel. Ring entity logic should follow this pattern.
2. **Dataclass + functions**: No methods on mutable state. Pure data + pure functions.
3. **Audio coupling**: SFX calls require Pyxel. Ring collection logic needs to signal "a ring was collected" without directly calling `play_sfx()`. Options: return value, callback, or event list.
4. **Entity ownership**: World rings belong to the level/stage, not the player. They need their own data structure and update cycle, separate from `scattered_rings` (which belong to the player).

## Key Files

| File | Relevance |
|------|-----------|
| `speednik/player.py` | Has scattered ring logic; needs world ring collection and extra-life logic |
| `speednik/constants.py` | Needs RING_COLLECTION_RADIUS and EXTRA_LIFE_THRESHOLD constants |
| `speednik/audio.py` | SFX API; not directly imported by game logic modules |
| `speednik/main.py` | Integration point; needs ring rendering and HUD updates |
| `speednik/stages/hillside.py` | Stage loader pattern; entities include ring positions |
| `tests/test_player.py` | Existing damage/ring tests; new ring tests go in new file |
| `docs/specification.md` | §5.4, §5.5, §8 define ring visuals, HUD, and mechanics |
