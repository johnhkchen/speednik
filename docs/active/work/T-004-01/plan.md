# Plan — T-004-01: Renderer

## Step 1: Palette System

**Create `speednik/renderer.py`** with palette constants and initialization.

Contents:
- Module docstring and imports (pyxel, math, constants, player types, terrain types)
- `_BASE_PALETTE` dict: fixed color slots (0, 4–12)
- `STAGE_PALETTES` dict: per-stage terrain colors (slots 1–3, 13–15)
- `init_palette()` — writes `_BASE_PALETTE` to `pyxel.colors[]`
- `set_stage_palette(stage_name)` — writes stage-specific slots to `pyxel.colors[]`

**Verify:** Import renderer in a test, confirm palette dicts have expected keys.

**Commit:** "Add renderer palette system (T-004-01 step 1)"

---

## Step 2: Terrain Drawing

Add `draw_terrain()` to renderer.py.

Contents:
- Accept `tiles: dict`, `camera_x: int`, `camera_y: int`
- Viewport culling (same logic as current main.py)
- Per-tile drawing:
  - Fill columns with palette slot 1 (dark shade)
  - Surface line connecting height tops with palette slot 2
  - Top-pixel highlight with palette slot 3

**Verify:** Replace terrain drawing in main.py draw() with `renderer.draw_terrain()`.
Run the game, confirm terrain renders with 3 shades instead of single green.

**Commit:** "Add terrain drawing with 3-shade coloring (T-004-01 step 2)"

---

## Step 3: Player Drawing

Add player drawing functions to renderer.py.

Contents:
- `draw_player(player, frame_count)` — dispatch based on anim_name
- `_draw_player_idle(cx, cy, facing_right)` — standing pose
- `_draw_player_running(cx, cy, facing_right, anim_frame)` — 4-frame animation
- `_draw_player_rolling(cx, cy, frame_count)` — spinning ball
- `_draw_player_hurt(cx, cy, facing_right)` — knockback pose
- Invulnerability flicker: skip draw when timer > 0 and frame_count % 4 < 2

**Verify:** Replace player rectangle in main.py with `renderer.draw_player()`.
Run the game. Player should appear as geometric character, animate when running,
become ball when rolling/jumping, flicker when hurt.

**Commit:** "Add geometric player character drawing (T-004-01 step 3)"

---

## Step 4: Object Drawing (Rings, Springs, Pipes, Checkpoints, Goal)

Add object drawing functions to renderer.py.

Contents:
- `_draw_ring(x, y, frame_count)` — yellow circle + rotating highlight
- `_draw_spring(x, y, direction, compressed)` — red rect + states
- `_draw_pipe(x, y, direction)` — rect + arrow
- `_draw_checkpoint(x, y, activated, frame_count)` — post + rotating top
- `_draw_goal(x, y, frame_count)` — tall post + spinning sign
- `draw_scattered_rings(rings, frame_count)` — scattered ring particles

**Verify:** Scattered rings should render as proper ring sprites instead of plain circles.
Object functions verified visually when entities exist (no entity system yet).

**Commit:** "Add object drawing functions (T-004-01 step 4)"

---

## Step 5: Enemy Drawing

Add enemy drawing functions to renderer.py.

Contents:
- `_draw_enemy_crab(x, y, frame_count)` — ellipse + animated claws
- `_draw_enemy_buzzer(x, y, frame_count)` — circle + flapping wings
- `_draw_enemy_chopper(x, y, frame_count)` — elongated ellipse + mouth
- `_draw_enemy_guardian(x, y, frame_count)` — shielded rectangle
- `_draw_enemy_egg_piston(x, y, frame_count)` — boss composite
- `draw_entities(entities, frame_count)` — dispatch by entity type string

**Verify:** Unit test that draw_entities dispatches to correct sub-function per type.

**Commit:** "Add enemy drawing functions (T-004-01 step 5)"

---

## Step 6: Particle Effects

Add particle system to renderer.py.

Contents:
- `_Particle` dataclass: x, y, vx, vy, color, lifetime
- `_particles: list[_Particle]` module-level list
- `spawn_destroy_particles(x, y)` — create 6 sparkle particles
- `draw_particles(frame_count)` — update positions, draw, remove expired

**Verify:** Unit test particle spawn/expire lifecycle.

**Commit:** "Add particle effect system (T-004-01 step 6)"

---

## Step 7: HUD Drawing

Add `draw_hud()` to renderer.py.

Contents:
- Ring count display with flash at 0 (alternate colors every 30 frames)
- Timer display: frame_count → minutes:seconds format
- Lives count display
- All positioned at top-left, drawn with pyxel.text()

**Verify:** Replace debug HUD in main.py with `renderer.draw_hud()`.
Run game, confirm HUD shows ring count, timer, lives in clean format.

**Commit:** "Add HUD drawing (T-004-01 step 7)"

---

## Step 8: Integration — Replace main.py draw()

Finalize main.py integration.

Contents:
- Add `from speednik import renderer` import
- Add `renderer.init_palette()` in `__init__`
- Replace entire `draw()` body with renderer calls
- Remove old inline drawing code
- Keep draw order: cls → camera → terrain → entities → player → scattered_rings → particles → camera_reset → hud

**Verify:** Run the game end-to-end. All visuals should work:
- Terrain with 3-shade coloring
- Player with geometric character sprites
- Scattered rings as ring sprites
- HUD with ring count, timer, lives

**Commit:** "Integrate renderer into main.py game loop (T-004-01 step 8)"

---

## Step 9: Tests

Create `tests/test_renderer.py`.

Contents:
- Test palette dict structure (all stage names, correct slot keys)
- Test player draw dispatch (mock pyxel, verify correct sub-drawer called per state)
- Test terrain viewport culling (tiles outside viewport not drawn)
- Test particle lifecycle (spawn, tick, expire)
- Test HUD formatting (timer display, ring flash logic)
- Test entity dispatch (each type routes to correct draw function)

**Verify:** `uv run python -m pytest tests/test_renderer.py -v` — all pass.

**Commit:** "Add renderer unit tests (T-004-01 step 9)"

---

## Testing Strategy

| What | How | Type |
|------|-----|------|
| Palette structure | Assert dict keys/value types | Unit |
| Draw dispatch | Mock pyxel, check function routing | Unit |
| Viewport culling | Provide tiles in/out of viewport, count draws | Unit |
| Particle lifecycle | Spawn, tick N frames, assert count | Unit |
| HUD format | Check timer string, flash color logic | Unit |
| Visual correctness | Run game, observe manually | Manual |
| Demo integration | Run `uv run python -m speednik.main`, play | Integration |
