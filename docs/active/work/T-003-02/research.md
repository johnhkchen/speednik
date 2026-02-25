# Research — T-003-02: Game Objects

## Scope

Springs, checkpoints, launch pipes, and liquid rise mechanic. Reference: specification §7.2 (pipe/liquid), §8 (ring/checkpoint systems), §5.4 (visual descriptions).

---

## Existing Architecture

### objects.py (current state)

`speednik/objects.py` implements rings only. Established patterns:

- **Dataclass entities:** `Ring(x, y, collected)` — pure data, no methods.
- **Loader function:** `load_rings(entities: list[dict]) -> list[Ring]` — filters entity dicts by `type` field.
- **Event enum:** `RingEvent(COLLECTED, EXTRA_LIFE)` — returned by collision checks for the main loop to map to SFX.
- **Collision function:** `check_ring_collection(player, rings) -> list[RingEvent]` — distance-based, Pyxel-free for testability.

The module imports `Player` and `PlayerState` from `player.py` but does **not** mutate physics state directly — it only sets `player.rings` and `player.lives`. The physics module is not imported.

### player.py

- `Player` dataclass holds `physics: PhysicsState`, `state: PlayerState`, `rings`, `lives`, `invulnerability_timer`.
- `damage_player(player)` is the damage API — checks invulnerability, scatters rings or kills.
- `player_update()` runs the full frame: pre-physics state machine → physics steps 1–4 → collision → post-physics sync → subsystems.
- Player states: STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD.

### physics.py / PhysicsState

Key fields for object interactions:
- `x, y` — world position (center of player)
- `x_vel, y_vel` — cartesian velocity
- `ground_speed` — tangential speed on ground
- `on_ground` — grounded flag
- `angle` — byte angle (0–255)
- `is_rolling` — rolling state flag

Velocity override pattern (from `apply_jump`):
```python
state.x_vel = ...
state.y_vel = ...
state.on_ground = False
state.angle = 0
state.ground_speed = 0.0
```

This is the pattern springs and pipes should follow.

### constants.py

Relevant existing constants:
- `RING_COLLECTION_RADIUS = 16` — distance-based collision radius
- SFX slots already defined in `audio.py`: `SFX_SPRING = 6`, `SFX_CHECKPOINT = 9`, `SFX_LIQUID_RISING = 12`

### Stage entity data

Entity JSON format: `{"type": "spring_up", "x": 2380, "y": 612}`

**Existing entity types in stage data:**
- `spring_up` — hillside (1), pipeworks (3), skybridge (8)
- `spring_right` — pipeworks (1)
- `checkpoint` — hillside (1), pipeworks (2), skybridge (2)
- `pipe_h`, `pipe_v` — **not present in any stage data yet** (spec mentions them for pipeworks)
- `liquid_trigger` — **not present in any stage data yet** (spec describes for pipeworks §7.2)
- `goal` — all stages (1 each)

### main.py integration

Currently hardcoded demo level. Ring objects created manually. The update loop calls `check_ring_collection()` then maps events to `play_sfx()`. Same pattern will be used for springs, checkpoints, pipes.

### Test patterns (test_rings.py)

- Helper functions: `flat_tile()`, `flat_ground_lookup()` for creating test terrain.
- Test classes grouped by feature: `TestLoadRings`, `TestRingCollection`, `TestExtraLife`, `TestRecollectionTimer`.
- Players created via `create_player(x, y)` with state/rings set directly for test conditions.
- Distance-based assertions with boundary tests.

---

## Entity Behavior Analysis

### Springs (spec §5.4, §7.1, §7.2, §7.3)

- **Trigger:** Player contact (bounding-box or distance overlap).
- **Effect:** Override velocity in spring direction. Up springs set `y_vel` to fixed upward value. Right springs set `x_vel`.
- **Visual states:** Compressed (during contact frame), extended (after launch).
- **SFX:** Slot 6 (`SFX_SPRING`).
- **Cooldown needed?** Yes — prevent re-triggering during the same contact (spring needs "armed" state that resets when player leaves).
- **Spring entities in data:** Only `spring_up` and `spring_right` exist. No `spring_left` or `spring_down` in current data.

### Checkpoints (spec §8)

- **Trigger:** First player contact only (one-shot activation).
- **Effect:** Save `(x, y)` position + ring count as respawn point.
- **Visual:** Post with rotating top, color change on activation.
- **SFX:** Slot 9 (`SFX_CHECKPOINT`).
- **Player respawn data:** Not currently stored on Player. Needs a `respawn_x`, `respawn_y`, `respawn_rings` or similar.

### Launch Pipes (spec §7.2)

- **Trigger:** Rectangular trigger zone — player enters zone.
- **Effect:** Override velocity to fixed vector (e.g. `(10, 0)` for horizontal), player invulnerable during travel, exit at pipe end, resume normal physics.
- **Visual:** Filled rectangle with directional arrows.
- **Key complexity:** Need entry point, exit point, and travel duration/path. Entity data needs more than just `(x, y)` — needs exit coordinates or pipe length.
- **No entities in data yet** — will need to add `pipe_h` entries to pipeworks entities.json.

### Liquid Rise (spec §7.2)

- **Trigger:** Player crosses `liquid_trigger` x-position (x > 2800 in pipeworks).
- **Effect:** Liquid y rises at 1px/frame from bottom toward ceiling. Stops when player exits zone (x > 3800). Contact = damage (ring loss).
- **Not an entity per-se** — more of a zone/global state machine. Could be a single trigger entity or stage metadata.
- **No entities in data yet** — will need `liquid_trigger` in pipeworks entities.json.

---

## Constraints and Boundaries

1. **objects.py must remain Pyxel-free** — all game logic testable without Pyxel import.
2. **Event-based coupling** — objects return events, main.py maps to SFX/visuals.
3. **Consistent with ring pattern** — dataclass + loader + collision/update function.
4. **PhysicsState mutation** — springs and pipes need to directly set velocity fields on `player.physics`. This means objects.py will need to import `PhysicsState` (or accept it as a parameter). Currently it imports `Player` which has `.physics`.
5. **Missing entity data** — pipes and liquid triggers need entities added to pipeworks stage data.
6. **Respawn system** — checkpoint save/restore requires storing respawn state somewhere accessible. Could be on Player or a separate game-state struct.

---

## Open Questions

- **Pipe entity format:** Need entry (x, y) + exit (x, y) + launch velocity. Single entity point is insufficient. Options: two entities (entry/exit pair), or single entity with extra fields (`exit_x`, `exit_y`, `vel_x`, `vel_y`).
- **Liquid zone bounds:** Should be defined by x-range + starting y + ceiling y. Could be stage metadata or a specialized entity.
- **Collision model for springs/checkpoints:** Distance-based (like rings) or AABB overlap? Springs have a physical surface — AABB is more appropriate.
