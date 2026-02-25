# Review — T-004-01: Renderer

## Summary of Changes

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `speednik/renderer.py` | ~380 | All drawing functions for the game |
| `tests/test_renderer.py` | ~280 | 34 unit tests covering all renderer subsystems |
| `docs/active/work/T-004-01/research.md` | ~150 | Codebase mapping for renderer context |
| `docs/active/work/T-004-01/design.md` | ~180 | Architecture decisions and visual specifications |
| `docs/active/work/T-004-01/structure.md` | ~120 | File-level change blueprint |
| `docs/active/work/T-004-01/plan.md` | ~120 | Implementation step sequence |
| `docs/active/work/T-004-01/progress.md` | ~80 | Implementation tracking |

### Files Modified

| File | Nature of Change |
|------|-----------------|
| `speednik/main.py` | Replaced inline draw() with renderer calls, added `renderer.init_palette()`, added `from speednik import renderer` |

---

## Acceptance Criteria Coverage

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| Player standing sprite | Done | `_draw_player_idle()` — ellipse body, line limbs, circle head, 2px dot eyes |
| Player running animation | Done | `_draw_player_running()` — 4-frame leg offsets, arm swing, head lean |
| Player rolling/spindash | Done | `_draw_player_rolling()` — circle + rotating accent line |
| Player jumping | Done | Routes to rolling sprite (same as spec) |
| Facing direction | Done | Eye/head position mirrors based on `facing_right` |
| Terrain per-tile polygon | Done | `_draw_tile()` — column fill + surface line + highlight |
| Terrain 3-shade coloring | Done | Palette slots 1 (fill), 2 (surface), 3 (highlight) |
| Enemy crab | Done | `_draw_enemy_crab()` — ellipse + animated claws + legs |
| Enemy buzzer | Done | `_draw_enemy_buzzer()` — circle + flapping triangle wings + stinger |
| Enemy chopper | Done | `_draw_enemy_chopper()` — elongated ellipse + mouth animation |
| Enemy guardian | Done | `_draw_enemy_guardian()` — shielded rect + flash |
| Enemy egg piston | Done | `_draw_enemy_egg_piston()` — cockpit + armor + piston base |
| Rings | Done | `_draw_ring()` — yellow circle + rotating highlight |
| Springs | Done | `_draw_spring()` — red rect + top plate + coil lines + arrow |
| Pipes | Done | `_draw_pipe()` — rect + border + arrow |
| Checkpoint | Done | `_draw_checkpoint()` — post + rotating ellipse top |
| Goal post | Done | `_draw_goal()` — tall post + spinning sign |
| HUD ring count (flash at 0) | Done | `draw_hud()` — flashes orange when 0 rings |
| HUD timer | Done | `draw_hud()` — frame count → M:SS format |
| HUD lives | Done | `draw_hud()` — "xN" display |
| 16-color palette per spec | Done | `_BASE_PALETTE` + `STAGE_PALETTES` cover all 16 slots |
| Palette swap per stage | Done | `set_stage_palette()` writes terrain slots 1–3, accent slots 13–15 |
| Camera offset respected | Done | main.py sets `pyxel.camera()` before calling renderer functions |
| Particle effects: ring scatter | Done | `draw_scattered_rings()` with color fade near expiry |
| Particle effects: enemy sparkle | Done | `spawn_destroy_particles()` + `draw_particles()` lifecycle |
| Works with demo level | Done | Integrated in main.py, replaces all inline drawing |

---

## Test Coverage

34 tests across 8 test classes:

| Class | Tests | Coverage Area |
|-------|-------|---------------|
| TestPalette | 4 | Palette dict structure, slot presence, value types |
| TestPlayerDrawDispatch | 7 | All animation states, flicker skip/show, spindash dust |
| TestTerrainCulling | 2 | Off-screen tiles skipped, visible tiles drawn |
| TestParticles | 4 | Spawn count, velocity, lifetime expiry, survival during life |
| TestHUD | 5 | Ring count text, flash color at 0, normal color, timer format, lives |
| TestEntityDispatch | 7 | Ring, crab, buzzer, unknown skip, checkpoint, goal, multiple |
| TestScatteredRings | 3 | Draw count, fade color, bright color |
| TestFacingDirection | 2 | Right-facing eye position, left-facing eye position |

All 366 tests pass (332 existing + 34 new). No regressions.

### Test gaps

- No test for individual enemy drawing details (specific pixel positions). Covered
  by dispatch tests + manual visual verification.
- No test for `init_palette()` or `set_stage_palette()` — these require a running
  Pyxel instance to write `pyxel.colors[]`. Covered by palette structure tests.
- Spring compressed/extended state not tested — the `_draw_spring` function currently
  draws a static state. Spring state animations depend on gameplay triggers from
  objects.py (not yet wired).

---

## Open Concerns

1. **`_draw_ring` called as `renderer._draw_ring()` from main.py.** This is a
   private function accessed externally. When objects.py/enemies.py integrate fully,
   world rings should be drawn via `draw_entities()` instead. Current usage is a
   bridge for the demo level which places rings directly. Low priority — will
   resolve when full level loading is implemented.

2. **Spring/checkpoint/goal state awareness.** The current draw functions don't
   accept state parameters (compressed, activated). When objects.py evolves to
   track these states, the draw functions will need additional parameters. The
   current signatures accept `(x, y, frame_count)` which is sufficient for
   animation but not for state-dependent rendering. This is expected — tracked
   as future work when game objects gain state.

3. **No Pyxel `elli()` confirmation in tests.** The `elli(x, y, w, h)` function
   was confirmed via documentation to use top-left + full dimensions. The player
   body ellipse uses this convention. If Pyxel's behavior differs from docs,
   player body will be offset. Mitigated by visual testing.

4. **Palette slot 0 is now sky blue** (0x2090D0) and used as cls() color. The
   original code used `pyxel.cls(12)` which was palette slot 12. The new code
   uses `pyxel.cls(0)` to match the palette-managed background color. This
   means the sky color is configurable via palette swap if needed.

---

## Architecture Notes

- **Pure functions, no class.** All renderer functions are stateless (except the
  module-level `_particles` list). This makes them easy to test via mock injection
  and avoids unnecessary coupling.

- **Entity dispatch pattern.** `draw_entities()` uses `_ENTITY_DRAWERS` and
  `_OBJECT_DRAWERS` dicts for O(1) lookup by type string. New entity types are
  added by adding an entry to the dict + implementing the draw function.

- **main.py is thinner.** The draw method went from ~50 lines of inline rendering
  to ~15 lines of renderer calls. Clear separation between game loop orchestration
  and visual rendering.
