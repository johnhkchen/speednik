# Design — T-004-01: Renderer

## Core Decision: Module-Level Architecture

### Option A: Monolithic renderer.py with all draw functions

Single file. Each entity type gets a `draw_*()` function. A top-level `draw_frame()`
orchestrates the draw order.

**Pros:** Simple, matches spec layout (renderer.py is one file), easy to call from main.py.
**Cons:** Could grow large (400+ lines), but Pyxel draw calls are terse.

### Option B: Renderer package with submodules

`renderer/__init__.py`, `renderer/player.py`, `renderer/terrain.py`, etc.

**Pros:** Separation of concerns.
**Cons:** Over-engineering for geometric primitives. Spec says `renderer.py` (singular).
Extra imports, more files, no real benefit at this scale.

### Decision: Option A — single `renderer.py`

Matches spec. Pyxel primitive drawing is compact. A 400-line file is fine.
Internal organization via sections with clear headers.

---

## API Design

### Public Interface

```python
# Called once at startup or stage change
def set_stage_palette(stage_name: str) -> None:
    """Swap palette slots 1–3 and 13–15 for the given stage theme."""

# Called every frame by main.py App.draw()
def draw_terrain(tiles, camera_x, camera_y) -> None:
    """Draw visible tiles with height profiles and surface lines."""

def draw_player(player) -> None:
    """Draw the player character based on state/animation."""

def draw_entities(entities, frame_count) -> None:
    """Draw all entities (enemies, objects) from stage entity list."""

def draw_scattered_rings(rings) -> None:
    """Draw scattered ring particles."""

def draw_hud(player, timer_frames) -> None:
    """Draw HUD overlay (rings, timer, lives). Screen-space, no camera offset."""
```

### Why Not a Single `draw_frame()`?

main.py needs to control camera offset (`pyxel.camera()`) between world drawing
and HUD drawing. Splitting into world-space functions and screen-space functions
gives main.py the control it needs.

---

## Player Character Drawing

### Standing (~24px tall)

```
     oo        <- head: circ(cx, cy-9, 3, color=4), eyes: 2px dots
      |         <- neck: line
    [body]     <- body: elli(cx, cy, 5, 7, color=4) -- wide torso
     / \       <- legs: 2 lines from hip to feet
    /   \      <- arms: 2 lines from shoulders
```

Approximate pixel positions relative to center (cx, cy):
- Head center: (cx, cy - 9), radius 3
- Eyes: 2px dots at (cx ± 1, cy - 10)
- Body: ellipse centered at (cx, cy - 2), width 5, height 7
- Arms: from (cx ± 3, cy - 5) to (cx ± 6, cy + 2)
- Legs: from (cx ± 2, cy + 5) to (cx ± 4, cy + 12)

Facing: when `facing_right=False`, mirror x offsets around cx.

### Running (4 frames)

Same body + head. Legs and arms animate:
- Frame 0: legs forward/back split, arms opposite
- Frame 1: legs passing (nearly together)
- Frame 2: legs swapped
- Frame 3: legs passing back

Leg angles computed as offsets from vertical. Simple approach:
leg_angle_offsets = [(-6, 6), (-2, 2), (6, -6), (2, -2)] for (front, back) x-offsets.

### Rolling / Jumping (~14px tall)

Circle with rotating accent line:
- `circ(cx, cy, 7, color=4)` — filled ball
- Rotating line: endpoints computed from `frame_count` angle
- Line rotates at ~15° per frame

### Spindash

Same as rolling but on ground. Could add visual charge indicator
(e.g., dust lines behind player proportional to spinrev).

### Hurt

Knocked-back pose: body + limbs at static "flung" angles.

### Dead

Similar to hurt but falling. Static sprite.

### Invulnerability Flicker

When `invulnerability_timer > 0`: skip drawing on alternate frames
(`frame_count % 4 < 2` → don't draw). Already used in current main.py.

---

## Terrain Drawing

### Per-Tile Approach

For each visible tile (viewport-culled):
1. Draw filled polygon from height profile to tile bottom — uses palette slot 1 (darkest)
2. Draw the top surface line — uses palette slot 2 (mid)
3. Optional: top pixel row highlight — uses palette slot 3 (lightest)

### Height Profile → Polygon

For a tile at world position (wx, wy):
- For each column `col` (0–15): top of solid = `wy + (16 - height_array[col])`
- Connect these 16 top points, then close polygon down to tile bottom
- Since Pyxel doesn't have arbitrary polygon fill, use vertical line fills
  (same as current approach but with 3-shade coloring)

### Coloring Strategy

- Main fill (columns): palette slot 1
- Surface line (connecting tops): palette slot 2
- Top highlight pixels: palette slot 3

This produces a layered terrain look with minimal draw calls.

---

## Enemy Drawing

Since enemies.py doesn't exist yet, the renderer defines visual-only functions.
Each accepts (x, y, frame_count) and draws the geometric composition.

### Crab (enemy_crab)
- Body: elli(x, y, 8, 5, col=6)
- Claws: 2 lines from body sides, animate between open/closed (frame_count % 30 < 15)
- Legs: short lines underneath

### Buzzer (enemy_buzzer)
- Body: circ(x, y, 5, col=6)
- Wings: tri() on each side, flap animation (frame_count % 20 < 10)
- Stinger: small line below

### Chopper (enemy_chopper)
- Body: elli(x, y, 4, 8, col=6) — tall ellipse
- Mouth: horizontal line that opens/closes

### Guardian
- Body: rect(x-10, y-12, 20, 24, col=6)
- Shield: rectb() in front, slightly larger
- Eyes: 2px dots

### Egg Piston
- Cockpit: elli()
- Armor: rect()
- Piston base: rect() below
- Eyes: dots
- Damage indicator: flash red at low HP

---

## Object Drawing

### Rings
- Circle: circ(x, y, 3, col=7)
- Highlight: rotating short line across the circle (frame_count rotation)
- Sparkle: brief flash when nearby

### Springs
- Body: rect(x-4, y-8, 8, 16, col=8)
- Top plate: rect slightly wider
- Compressed state: shorter rect
- Arrow indicator on top

### Launch Pipes
- Body: rect with directional arrow
- Arrow: tri() pointing in pipe direction

### Checkpoint
- Post: vertical line
- Top: rotating rect or diamond (frame_count rotation)
- Color: palette 13 (inactive) → palette 7 (active/yellow)

### Goal Post
- Tall vertical line
- Sign: rect at top, spinning (frame_count based width compression)

---

## HUD Design

Screen-space (after `pyxel.camera()` reset).

```
RINGS: 47        TIME: 1:23        LIVES: 3
```

- Position: top-left, y=4
- Ring count flashes when 0: alternate between col 7 and col 9 every 30 frames
- Timer: minutes:seconds from frame_count
- Lives: "x N" format

---

## Palette Swapping Strategy

Use `pyxel.colors[slot] = 0xRRGGBB` to swap terrain palette per stage.

```python
STAGE_PALETTES = {
    "hillside": {
        1: 0x1B8C00,  # dark green (earth/grass base)
        2: 0x30C010,  # mid green (surface)
        3: 0x50E830,  # light green (highlight)
        13: 0x8B5E3C, # brown accent
        14: 0xC49A6C, # light brown
        15: 0x6B3A1E, # dark brown
    },
    "pipeworks": {
        1: 0x1A5C5C,  # dark teal
        2: 0x2A8C8C,  # mid teal
        3: 0x40B0B0,  # light teal
        13: 0x505050, # dark gray
        14: 0x808080, # mid gray
        15: 0xA0A0A0, # light gray
    },
    "skybridge": {
        1: 0x6090C0,  # sky blue
        2: 0x90B8E0,  # light sky
        3: 0xC0D8F0,  # near-white blue
        13: 0xC0C0C0, # light gray
        14: 0xE0E0E0, # near-white
        15: 0xFFFFFF, # white
    },
}
```

Fixed palette slots (set once at init):
- 0: 0x000000 (transparent/black)
- 4: 0x3050D0 (player body blue)
- 5: 0xD03030 (player accent/shoes red)
- 6: 0xC04040 (enemy primary)
- 7: 0xF0D000 (ring yellow)
- 8: 0xE02020 (spring red)
- 9: 0xE08020 (hazard orange)
- 10: 0x2060E0 (water blue)
- 11: 0xFFFFFF (UI white)
- 12: 0x202020 (UI dark / sky bg)

---

## Particle Effects

### Ring Scatter (already exists in player.scattered_rings)

Draw each ScatteredRing as a small yellow circle with fade-out
(reduce brightness when timer < 60 by switching to darker yellow).

### Enemy Destroy Sparkle

A simple particle list: spawn 4–8 white/yellow pixels at enemy position,
expand outward over 15 frames, then expire.

Storage: module-level list in renderer.py, `spawn_destroy_particles(x, y)` adds them,
`_update_and_draw_particles()` handles lifecycle each frame.

---

## Rejected Alternatives

1. **Sprite sheet approach:** Spec explicitly forbids `.pyxres`. Rejected.
2. **Renderer class with state:** No benefit — all state lives in Player/Camera/StageData.
   Pure functions are cleaner and testable.
3. **Rotation via Pyxel image manipulation:** Pyxel has no rotation API.
   All rotation done via math (sin/cos for line endpoints). This is fine for
   the geometric art style.
4. **Per-stage renderer subclass:** Terrain coloring differs, but only palette slots
   change. A single palette swap function is sufficient.
