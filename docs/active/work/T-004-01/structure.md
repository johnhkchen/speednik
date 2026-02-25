# Structure — T-004-01: Renderer

## Files Modified

### `speednik/renderer.py` — NEW

The sole new file. Contains all drawing logic. ~350–400 lines.

#### Internal Organization

```
Section: Module docstring, imports
Section: Palette constants and stage palettes
Section: Palette initialization
Section: Terrain drawing
Section: Player drawing (idle, running, rolling, hurt, dead)
Section: Enemy drawing (crab, buzzer, chopper, guardian, egg_piston)
Section: Object drawing (ring, spring, pipe, checkpoint, goal)
Section: Particle effects (destroy sparkle)
Section: HUD drawing
```

#### Public Interface

```python
# Palette
def init_palette() -> None
def set_stage_palette(stage_name: str) -> None

# World-space drawing (call between pyxel.camera(x,y) and pyxel.camera())
def draw_terrain(tiles: dict | Iterable, camera_x: int, camera_y: int) -> None
def draw_player(player: Player, frame_count: int) -> None
def draw_entities(entities: list[dict], frame_count: int) -> None
def draw_scattered_rings(rings: list[ScatteredRing], frame_count: int) -> None
def draw_particles(frame_count: int) -> None

# Screen-space drawing (call after pyxel.camera() reset)
def draw_hud(player: Player, timer_frames: int, frame_count: int) -> None

# Particle management
def spawn_destroy_particles(x: float, y: float) -> None
```

#### Internal Functions

```python
# Player sub-drawers
_draw_player_idle(cx, cy, facing_right)
_draw_player_running(cx, cy, facing_right, anim_frame)
_draw_player_rolling(cx, cy, frame_count)
_draw_player_hurt(cx, cy, facing_right)

# Entity sub-drawers
_draw_ring(x, y, frame_count)
_draw_enemy_crab(x, y, frame_count)
_draw_enemy_buzzer(x, y, frame_count)
_draw_enemy_chopper(x, y, frame_count)
_draw_enemy_guardian(x, y, frame_count)
_draw_enemy_egg_piston(x, y, frame_count)
_draw_spring(x, y, direction, compressed)
_draw_pipe(x, y, direction)
_draw_checkpoint(x, y, activated, frame_count)
_draw_goal(x, y, frame_count)

# Particle system
_update_particles()
_draw_particle_list()
```

#### Module-level State

```python
_particles: list[_Particle] = []  # Active destroy sparkle particles
```

Minimal — only the particle list. Everything else is passed as arguments.

---

### `speednik/main.py` — MODIFIED

Replace the inline `draw()` body with calls to renderer functions.

#### Changes

**Imports:** Add `from speednik import renderer`

**`__init__`:** Add `renderer.init_palette()` call after `pyxel.init()`.

**`draw()` method:** Replace lines 127–174 with:

```python
def draw(self):
    pyxel.cls(0)  # Sky/transparent (palette slot 0)
    pyxel.camera(int(self.camera.x), int(self.camera.y))

    renderer.draw_terrain(self.tiles, int(self.camera.x), int(self.camera.y))
    renderer.draw_player(self.player, pyxel.frame_count)
    renderer.draw_scattered_rings(self.player.scattered_rings, pyxel.frame_count)
    renderer.draw_particles(pyxel.frame_count)

    pyxel.camera()
    renderer.draw_hud(self.player, pyxel.frame_count, pyxel.frame_count)
```

This is a ~30-line net reduction from the current draw method.

---

### `speednik/constants.py` — NO CHANGES

All needed constants (SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, hitbox radii) are
already defined. TILE_SIZE is in terrain.py. No new constants needed — palette
values are renderer-internal.

---

### `tests/test_renderer.py` — NEW

Unit tests for the renderer. Since Pyxel drawing calls require a running Pyxel
instance, tests focus on:

1. **Palette configuration:** Verify `STAGE_PALETTES` dict has correct keys/structure
2. **Player draw dispatch:** Verify the correct sub-drawer is called for each state
3. **Terrain culling:** Verify tiles outside viewport are skipped
4. **Particle lifecycle:** Verify particles spawn, age, and expire correctly
5. **HUD formatting:** Verify timer format, ring flash logic

Mock `pyxel` for draw calls — verify correct primitives are called with correct args.

---

## Module Boundaries

### renderer.py reads from (never writes to):
- `player.Player` — state, physics, animation, rings, lives
- `player.ScatteredRing` — x, y, timer
- `terrain.Tile` — height_array, angle, solidity
- `terrain.TILE_SIZE` — 16
- `constants.SCREEN_WIDTH`, `SCREEN_HEIGHT`

### renderer.py owns:
- All palette color values (hex constants)
- Stage palette mapping
- Particle effect state and lifecycle
- All draw function implementations

### main.py orchestrates:
- Camera offset before/after world drawing
- Frame clearing
- Call order of renderer functions
- Passing frame_count to renderer

---

## Ordering Constraints

1. `init_palette()` must be called after `pyxel.init()` but before first `draw()`
2. `set_stage_palette()` must be called before drawing terrain for that stage
3. World-space draws must happen between `pyxel.camera(x,y)` and `pyxel.camera()`
4. `draw_hud()` must happen after `pyxel.camera()` (screen-space)
5. Draw order: terrain → entities → player → particles → HUD (back to front)

---

## Integration with Demo Level

The current demo level uses `self.tiles` as `dict[tuple[int,int], Tile]`.
`draw_terrain()` accepts this dict and iterates it with viewport culling,
identical to the current pattern but with proper 3-shade rendering.

Future StageData integration: `draw_terrain()` will accept either the dict
directly or a tile_lookup callable. For now, dict iteration matches the demo.
