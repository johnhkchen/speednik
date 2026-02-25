# Progress — T-004-01: Renderer

## Completed

### Step 1: Palette System
- Created `speednik/renderer.py` with `_BASE_PALETTE` and `STAGE_PALETTES`
- `init_palette()` and `set_stage_palette()` write to `pyxel.colors[]`
- Three stage themes: hillside (greens), pipeworks (teals), skybridge (blues)

### Step 2: Terrain Drawing
- `draw_terrain()` with viewport culling
- 3-shade rendering: fill (slot 1), surface line (slot 2), highlight (slot 3)
- Per-column vertical fill + connecting surface line between columns

### Step 3: Player Drawing
- `draw_player()` dispatches by `anim_name`
- Idle: ellipse body, circle head, line limbs, dot eyes, shoes
- Running: 4-frame leg animation with arm swing, head lean
- Rolling/jumping: spinning circle with rotating accent line
- Spindash: rolling sprite + dust particles behind player
- Hurt/dead: flung-back pose with X eyes
- Invulnerability flicker: skip draw on `frame_count % 4 < 2`
- Facing direction: eye/head position mirrors based on `facing_right`

### Step 4: Object Drawing
- `_draw_ring()`: yellow circle + rotating highlight line
- `_draw_spring()`: red rect with top plate, coil lines, arrow
- `_draw_pipe()`: rect with border and directional arrow
- `_draw_checkpoint()`: post line + rotating ellipse top
- `_draw_goal()`: tall post + width-compressing sign (spin effect)
- `draw_scattered_rings()`: yellow/orange fade based on timer

### Step 5: Enemy Drawing
- `_draw_enemy_crab()`: wide ellipse + animated claws + legs
- `_draw_enemy_buzzer()`: circle + flapping triangle wings + stinger
- `_draw_enemy_chopper()`: elongated ellipse + mouth open/close
- `_draw_enemy_guardian()`: shielded rectangle + flash effect
- `_draw_enemy_egg_piston()`: cockpit dome + armor + piston base
- `draw_entities()`: dispatches by entity type string

### Step 6: Particle Effects
- `_Particle` dataclass with position, velocity, color, lifetime
- `spawn_destroy_particles()`: 6 particles in radial pattern
- `draw_particles()`: update positions, draw, expire dead particles

### Step 7: HUD Drawing
- `draw_hud()`: ring count (flashes orange at 0), timer (M:SS), lives
- Screen-space rendering (called after camera reset)

### Step 8: Integration
- Added `from speednik import renderer` to main.py
- Added `renderer.init_palette()` in `App.__init__`
- Replaced entire `App.draw()` body with renderer calls
- World rings drawn with `_draw_ring()` instead of plain circles
- Draw order: cls → camera → terrain → rings → player → scattered → particles → HUD

### Step 9: Tests
- 34 tests in `tests/test_renderer.py`
- Palette structure, player dispatch, terrain culling, particles, HUD, entities, facing
- All 366 tests pass (332 existing + 34 new)

## Deviations from Plan

- Pyxel `elli()` confirmed to use top-left + full dimensions (not center), adjusted
  all ellipse calls accordingly
- main.py had evolved since initial research (objects.py, Ring class now exists),
  adapted integration to draw world rings using renderer's `_draw_ring()` function
- Combined steps 1–9 into a single implementation pass (all code written to
  renderer.py at once, then tests, then integrated) rather than individual commits
  per step — more efficient given no inter-step blocking dependencies
