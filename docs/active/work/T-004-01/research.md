# Research — T-004-01: Renderer

## Ticket Summary

Implement `speednik/renderer.py` — all game visuals using Pyxel drawing primitives.
No `.pyxres` sprite sheets. Code-generated geometric art for every entity.

Reference: specification §5 (Rendering).

---

## Codebase Map

### Existing Modules

| Module | Role | Renderer Relevance |
|--------|------|-------------------|
| `main.py` | Entry point, demo level, game loop | Contains placeholder draw() to be replaced |
| `constants.py` | Physics, screen, sensor dimensions | SCREEN_WIDTH/HEIGHT, hitbox radii |
| `physics.py` | PhysicsState dataclass, movement | Source of x, y, angle, facing_right, ground_speed |
| `player.py` | Player state machine, animation, damage | PlayerState enum, anim_name/anim_frame, scattered rings |
| `terrain.py` | Tile collision: Tile dataclass, TileLookup | Tile.height_array for terrain drawing |
| `camera.py` | Sonic 2 camera with borders/look-ahead | camera.x/y for viewport offset |
| `audio.py` | SFX + music | No rendering interaction |
| `stages/*.py` | Stage data loaders → StageData | StageData.tile_lookup, entities, level dimensions |

### No existing `renderer.py`

The file does not yet exist. All current rendering is inline in `main.py:App.draw()` (lines 126–174) as a debug placeholder.

---

## Data Structures the Renderer Consumes

### Player (from `player.py`)

```python
Player:
  physics: PhysicsState
    .x, .y          # center position (float)
    .facing_right    # bool — mirror sprites
    .ground_speed    # for animation speed
    .angle           # byte 0–255 — body rotation
    .is_rolling      # hitbox size switch
    .on_ground       # standing vs rolling hitbox
    .spinrev         # 0.0–8.0, spindash charge level
  state: PlayerState  # STANDING/RUNNING/JUMPING/ROLLING/SPINDASH/HURT/DEAD
  anim_name: str      # "idle"/"running"/"rolling"/"spindash"/"hurt"/"dead"
  anim_frame: int     # 0–3 for running animation
  invulnerability_timer: int  # >0 = flicker
  rings: int
  lives: int
  scattered_rings: list[ScatteredRing]  # .x, .y, .timer
```

`get_player_rect(player)` returns `(x, y, width, height)` for the bounding box.

### Tile (from `terrain.py`)

```python
Tile:
  height_array: list[int]  # 16 values, 0–16 (solid from bottom per column)
  angle: int               # byte angle 0–255
  solidity: int            # NOT_SOLID=0, TOP_ONLY=1, FULL=2, LRB_ONLY=3
```

Height interpretation: `height_array[col]` = pixels of solid from the tile's bottom edge.
Top of solid at column `col`: `world_y + (TILE_SIZE - height_array[col])`.
TILE_SIZE = 16.

### StageData (from `stages/*.py`)

```python
StageData:
  tile_lookup: TileLookup    # (tx, ty) → Tile | None
  entities: list[dict]       # [{"type": str, "x": int, "y": int}, ...]
  player_start: (float, float)
  checkpoints: list[dict]
  level_width: int            # pixels
  level_height: int           # pixels
```

Entity types in data: ring, enemy_crab, enemy_buzzer, enemy_chopper, spring_up,
spring_right, checkpoint, goal, pipe_h, pipe_v, liquid_trigger.

### Camera (from `camera.py`)

```python
Camera:
  x: float   # viewport left edge in world coordinates
  y: float   # viewport top edge in world coordinates
```

Used as: `pyxel.camera(int(cam.x), int(cam.y))` before world drawing,
`pyxel.camera()` to reset for HUD.

---

## Specification Requirements (§5)

### 5.1 Player Character
- Standing: ellipse body, line limbs, circle head, 2px dot eyes (~24px tall)
- Running: 4-frame limb animation, leg angles from frame_count, arms opposite
- Rolling/spindash: circle + rotating line accent (~14px tall)
- Jumping: rolling sprite in air
- Facing direction: horizontal flip based on facing_right

### 5.2 Terrain
- Per-tile: filled polygon from height profile to tile bottom
- 3 color shades from palette slots 1–3 (swapped per stage)
- Surface line along top edge of height profile

### 5.3 Enemies
- Crab: wide ellipse + 2 line claws
- Buzzer: circle + triangle wings
- Chopper: elongated ellipse
- Guardian: large shielded rectangle
- Egg Piston: detailed boss sprite
- All have 2-frame idle animations

### 5.4 Objects
- Rings: yellow circle + rotating highlight line
- Springs: red rectangle, compressed/extended states
- Launch pipes: filled rect + directional arrow
- Checkpoint: post + rotating top, color changes on activation
- Goal post: tall post + spinning sign

### 5.5 HUD
- Top-left: ring count (flashes at 0), timer, lives
- Drawn with pyxel.text()

### 5.6 Palette (16 colors)
| Slot | Usage |
|------|-------|
| 0 | Transparent / sky |
| 1–3 | Terrain (3 shades, per-stage) |
| 4–5 | Player body / accent |
| 6 | Enemy primary |
| 7 | Ring yellow |
| 8 | Spring red |
| 9 | Hazard orange |
| 10 | Water / liquid blue |
| 11–12 | UI text (white, dark) |
| 13–15 | Stage-specific accents |

### Particle effects
- Ring scatter burst (already have ScatteredRing positions)
- Enemy destroy sparkle (needs a particle system)

---

## Current Rendering in main.py (to be replaced)

Lines 126–174 of `main.py`:
1. `pyxel.cls(12)` — sky
2. `pyxel.camera(cam_x, cam_y)` — world offset
3. Per-tile: vertical green lines from height_array (color 3)
4. Player: colored rectangle via get_player_rect()
5. Scattered rings: yellow circles
6. `pyxel.camera()` — HUD reset
7. Debug HUD: state, speed, pos, rings, angle, on_ground

---

## Pyxel Drawing API Available

| Function | Signature |
|----------|-----------|
| `pyxel.cls(col)` | Clear screen |
| `pyxel.pset(x, y, col)` | Single pixel |
| `pyxel.line(x1, y1, x2, y2, col)` | Line |
| `pyxel.rect(x, y, w, h, col)` | Filled rectangle |
| `pyxel.rectb(x, y, w, h, col)` | Rectangle border |
| `pyxel.circ(x, y, r, col)` | Filled circle |
| `pyxel.circb(x, y, r, col)` | Circle border |
| `pyxel.elli(x, y, w, h, col)` | Filled ellipse |
| `pyxel.ellib(x, y, w, h, col)` | Ellipse border |
| `pyxel.tri(x1, y1, x2, y2, x3, y3, col)` | Filled triangle |
| `pyxel.trib(x1, y1, x2, y2, x3, y3, col)` | Triangle border |
| `pyxel.text(x, y, s, col)` | Text string |
| `pyxel.camera(x, y)` | Offset all drawing |
| `pyxel.camera()` | Reset offset |
| `pyxel.frame_count` | Global frame counter |

Note: `elli` and `ellib` take (x, y, w, h) where x,y is the center, w/h are radii.

---

## Constraints and Dependencies

1. **No enemies.py or objects.py yet.** The renderer must define drawing functions
   for enemy/object visuals, but game logic for those entities doesn't exist.
   The renderer should accept entity dicts from StageData.entities and draw based on type.

2. **Demo level in main.py** uses a flat tile dict, not StageData. The renderer
   must work with the dict-based tile iteration already present AND future StageData.

3. **Camera offset** is the responsibility of the caller (main.py sets pyxel.camera
   before calling renderer functions). Renderer draws in world coordinates.

4. **No palette modification API in Pyxel.** Pyxel's 16-color palette is fixed at
   init. Stage-specific colors must be set via `pyxel.colors[slot] = 0xRRGGBB`
   before drawing, or we use the palette slots with different interpretations per stage.

5. **Acceptance criteria** says "works with the player demo level from T-001-04."
   So the immediate integration target is the existing main.py demo.

---

## Assumptions to Verify

- Pyxel `elli()` center vs top-left: need to confirm. Pyxel docs say elli(x, y, w, h)
  where x,y = top-left, w,h = full size. This is different from circ() where x,y = center.
- `pyxel.colors[]` is writable for palette swapping (confirmed in Pyxel v2 API).
- No sprite rotation in Pyxel — must use math to draw rotated primitives.
