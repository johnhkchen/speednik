# Speednik — Game Specification

A Sonic 2 homage built with Pyxel, managed by uv, developed via lisa.

## 1. Project Structure & Tooling

**Resolution:** 256x224 @ 60fps (Genesis-native)
**Engine:** Pyxel (Python retro game engine, 16-color palette, 4-channel audio)
**Package manager:** uv
**Development orchestration:** lisa (RDSPI workflow, concurrent ticket execution)

### Python Package Layout

```
pyproject.toml
assets/                     # Reference MP3 tracks (not shipped in game)
  MAIN_MENU_Genesis_of_Glory.mp3
  LV1_Pixel_Pursuit.mp3
  LV2_Chrome_Citadel.mp3
  LV3_Genesis_Gauntlet.mp3
tools/
  svg2stage.py              # SVG-to-stage pipeline CLI
speednik/
  __init__.py
  main.py                   # Entry point, game state machine
  constants.py              # All physics constants, screen dimensions
  physics.py                # Sonic 2 ground/air/slope physics engine
  player.py                 # Player state, animation frames, input handling
  camera.py                 # Sonic 2 camera with borders & look-ahead
  terrain.py                # Tile collision: height arrays, angles, sensors
  level.py                  # Level loading from pipeline output, tile layout
  enemies.py                # Enemy types, behaviors, bounce physics
  objects.py                # Rings, springs, launch pipes, checkpoints, liquid
  renderer.py               # Code-generated geometric art (all visuals)
  audio.py                  # Pyxel 4-channel SFX + chiptune music
  stages/
    __init__.py
    hillside.py             # Stage 1 data
    pipeworks.py            # Stage 2 data
    skybridge.py            # Stage 3 data
```

### Game State Machine

Title Screen → Stage Select → Gameplay → Results → (next stage or credits)

---

## 2. Physics Engine

Faithful Sonic 2 physics. All values in pixels/frame at 60fps.

### 2.1 Ground Movement

| Constant | Value | Notes |
|----------|-------|-------|
| Acceleration | 0.046875 | Applied when pressing movement direction |
| Deceleration | 0.5 | Applied when pressing opposite of movement |
| Friction | 0.046875 | Applied when no directional input (same value as acceleration) |
| Top speed | 6.0 | Acceleration not applied above this; momentum from slopes can exceed it |
| Rolling friction | 0.0234375 | Exactly half of standing friction |
| Rolling deceleration | 0.125 | Braking while rolling |
| Min roll speed | 0.5 | Below this threshold, unroll to standing |
| Max X speed | 16.0 | Hard cap, both directions |

Player cannot accelerate while rolling — only friction and slope factor apply.

### 2.2 Air Movement

| Constant | Value |
|----------|-------|
| Gravity | 0.21875 |
| Jump force | 6.5 |
| Air acceleration | 0.09375 |

**Variable jump height:** When the jump button is **released** AND `y_vel < 0` (player is still moving upward), set `y_vel = max(y_vel, -4.0)`. If `y_vel >= 0` (already falling), do nothing. The cap only truncates upward momentum.

**Jump launch formula (angle-aware):**
```
x_speed -= jump_force * sin(ground_angle)
y_speed -= jump_force * cos(ground_angle)
```

### 2.3 Slope Physics

| Constant | Value |
|----------|-------|
| Slope factor (running) | 0.125 |
| Slope factor (rolling uphill) | 0.078125 |
| Slope factor (rolling downhill) | 0.3125 |

Applied each frame on ground: `ground_speed -= slope_factor * sin(angle)`

**Velocity decomposition:**
```
x_vel = ground_speed * cos(angle)
y_vel = ground_speed * -sin(angle)
```

**Slipping:** When `|ground_speed| < 2.5` on slopes steeper than 46°, directional input is ignored for 30 frames. Angles between 46° and 315° trigger detachment from the surface.

**Landing from air:** Snap player angle to the landed tile's stored angle value immediately. Do not carry air angle (0°) into ground state. Ground speed is recalculated from X/Y velocity based on impact angle:
- Flat (339°–23°): `ground_speed = x_speed`
- Slope (316°–45°): `ground_speed = y_speed * 0.5 * -sign(sin(angle))`
- Steep (outside slope range): `ground_speed = y_speed * -sign(sin(angle))`

### 2.4 Spindash

- Initiate: press down while standing still, then press jump to charge
- Each jump press adds +2.0 to `spinrev` (max 8.0)
- Decay per frame **while holding charge only**: `spinrev -= spinrev / 32.0`
- Release (let go of down): `ground_speed = 8 + floor(spinrev / 2)`
- Theoretical max launch speed: 12.0 (when spinrev = 8)

Note: reaching max charge is nearly impossible without a turbo controller due to exponential decay at high spinrev values. This is by design.

### 2.5 Frame Update Order

This order is not negotiable — deviations produce physics that feel subtly broken in ways that are difficult to trace.

1. Apply input (acceleration, deceleration, jump initiation)
2. Apply slope factor (if on ground)
3. Apply gravity (if airborne)
4. Move player by velocity
5. Run sensors (floor, ceiling, wall)
6. Resolve collision (push out of solids, snap to surfaces)
7. Update angle (from tile data at sensor contact point)

---

## 3. Collision System

### 3.1 Tile Format

Each solid tile is a 16x16 block storing:
- **Height array:** 16 values (one per column), each 0–16, indicating solid height from the bottom
- **Angle:** 0–255 mapped to 0°–360°. Value 255 = use nearest 90° cardinal direction
- **Solidity flag:** not solid / top-only / full / left-right-bottom only

**Top-only tile behavior:** Ignore the tile when `y_vel < 0` (player rising). Collide only when `y_vel >= 0` and player is approaching from above. This enables jump-through platforms.

### 3.2 Sensor Layout

**Standing (width_radius=9, height_radius=20):**
```
        C       D          <- ceiling sensors (push up)
        |       |
   E -- + ----- + -- F     <- wall sensors (push sideways, at center Y)
        |       |
        A       B          <- floor sensors (push down)

   A/B spread by width_radius (9px) at player's feet
   C/D spread by width_radius at player's head
   E/F extend ±10px horizontally from player center
```

**Rolling/jumping (width_radius=7, height_radius=14):**
- Hitbox shrinks — shorter and narrower
- E/F wall sensors shift inward with the reduced width_radius
- This is why rolling through tight gaps works

### 3.3 Floor Sensor Operation (A/B)

1. Each sensor casts downward from the player's foot position
2. Check the tile at the sensor's position — read height array at the sensor's X within the tile
3. If height = 0 (empty at this column), check the tile **one block below** (extension)
4. If height = 16 (full column), check the tile **one block above** (regression)
5. Return the distance from sensor to the detected surface
6. **Use the sensor (A or B) that returns the shorter distance** — this is how the player straddles tile boundaries without clipping
7. **Tiebreaker: when A and B return equal distances, prefer sensor A.** This must be deterministic.

Sensor range: current tile + one adjacent tile (32px). Distances beyond 32px are rejected as "no block found."

### 3.4 The Tile-Boundary Crossing Problem

When the player moves at high speed (up to 16px/frame), they can cross an entire tile in one frame. Always check both sensors A and B independently each frame and snap to the closer surface. When sensor A is on tile N and sensor B is on tile N+1, each reads its own tile's height array. The "winning" sensor switches from A to B as the player crosses the boundary, producing smooth transitions. Bugs occur when implementations only check one sensor or average them.

### 3.5 Wall Sensors (E/F)

1. Cast horizontally from player center
2. Read the **width array** (height array rotated 90°) at the sensor tip's tile
3. If a wall is detected within push distance, push the player outward
4. Wall sensors are **disabled** when the player is moving away from the wall (prevents sticky walls)
5. Wall sensors use the **current width_radius** — rolling narrows detection

### 3.6 Ceiling Sensors (C/D)

Mirror of A/B but casting upward. When the player hits a ceiling while on a steep slope (going through a loop), ceiling sensors **become floor sensors**. The mode switch is based on the player's current angle quadrant.

### 3.7 Angle Quadrant Mode Switching

| Player angle | Floor sensors | Ceiling sensors | Wall sensors |
|-------------|--------------|----------------|-------------|
| 0°–45°, 316°–360° | A/B point down | C/D point up | E/F horizontal |
| 46°–134° | A/B point right | C/D point left | E/F vertical |
| 135°–225° | A/B point up | C/D point down | E/F horizontal |
| 226°–315° | A/B point left | C/D point right | E/F vertical |

This rotation is how the player runs along walls and through loops using the exact same sensor code — the sensors rotate with the angle.

---

## 4. SVG-to-Stage Pipeline

A build tool that converts designer-drawn SVG files into playable level data. Lives at `tools/svg2stage.py`.

### 4.1 SVG Drawing Conventions

**Terrain:** Closed polygons or polylines with stroke color indicating surface type:
| Stroke color | Surface type |
|-------------|-------------|
| `#00AA00` | Solid ground |
| `#0000FF` | Top-only platform |
| `#FF8800` | Slope surface |
| `#FF0000` | Hazard/death tile |

Fill color is ignored — only stroke color and path geometry matter.

**Loops:** Circles or ellipses with terrain stroke color. The pipeline recognizes closed elliptical paths and generates curved tile sequences with correct angle values around the perimeter.

**Entities:** SVG `<circle>` or `<rect>` elements with `id` attribute indicating type:
- `id="player_start"` — single circle, player spawn point
- `id="ring"` — ring placement
- `id="enemy_crab"`, `id="enemy_buzzer"`, `id="enemy_chopper"` — enemy types
- `id="spring_up"`, `id="spring_right"` — directional springs
- `id="goal"` — stage end
- `id="checkpoint"` — mid-stage checkpoint
- `id="pipe_h"`, `id="pipe_v"` — launch pipes (horizontal/vertical)
- `id="liquid_trigger"` — liquid rise zone boundary

Position is taken from the element's center point.

**ViewBox:** Maps directly to world pixel space at 1:1 scale. A 4800x720 viewBox = 4800x720 world pixels.

### 4.2 Pipeline Output

Per stage, the pipeline outputs:

**Tile map:** 2D array where each cell contains:
```json
{
  "type": 1,
  "height_array": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
  "angle": 32
}
```

**Collision layer:** Solidity flags per tile derived from the stroke color of the generating SVG path.

**Entity list:** Flat JSON array:
```json
[
  {"type": "ring", "x": 400, "y": 320},
  {"type": "enemy_crab", "x": 800, "y": 640},
  {"type": "player_start", "x": 64, "y": 600}
]
```

**Metadata:** Stage width, height, player start position, named zones/checkpoints.

### 4.3 Rasterization Logic

**Straight segments:** Rasterize into the tile grid. Assign angle values based on segment slope angle converted to 0–255 format.

**Curved paths:** Sample at 16px intervals, compute tangent angle at each sample, assign to the corresponding tile.

**Loops:** Walk the ellipse perimeter at 16px intervals, assign angles continuously, flag upper-half tiles as requiring angle quadrant mode switching.

**Height arrays:** Computed by determining how much of each tile column the SVG geometry occupies. A 45° diagonal produces a linearly increasing array from 0 to 16 across 16 columns.

### 4.4 Validation

The pipeline runs these checks before outputting and produces a validation report:

1. **Angle consistency:** Flag any tile whose angle differs from its neighbors by > ~30° (likely SVG geometry error causing player snap/jitter)
2. **Impassable gaps:** Flag terrain gaps narrower than 18px (player width_radius × 2) that aren't top-only platforms
3. **Accidental walls:** Flag slope sequences exceeding 45° per tile for > 3 consecutive tiles without a loop flag

---

## 5. Rendering

All visuals drawn with Pyxel primitives — no .pyxres sprite sheets. Distinctive geometric art style.

### 5.1 Player Character

- **Standing:** Body as filled ellipse, limbs as lines, head as circle, eyes as 2px dots. ~24px tall.
- **Running:** 4-frame limb animation, leg angles computed from `frame_count`. Arms swing opposite legs.
- **Rolling/spindash:** Single circle with a rotating line accent. ~14px tall (matches rolling hitbox).
- **Jumping:** Rolling sprite used in air.

### 5.2 Terrain

- Rendered per-tile: filled polygon from height profile to tile bottom
- Color varies by stage theme (3 shades per stage from the palette)
- Surface line drawn along the top edge of the height profile

**Stage palettes:**
- Hillside Rush: greens (grass) + browns (earth) + blue sky
- Pipe Works: teals + grays + dark blue (interior)
- Skybridge Gauntlet: sky blue + white + light gray

### 5.3 Enemies

Simple geometric compositions, 2-frame idle animations:
- **Crab:** Wide ellipse body + 2 line claws, walks short patrol
- **Buzzer:** Circle body + triangle wings, hovers in place
- **Chopper:** Elongated ellipse, jumps vertically from liquid
- **Guardian (Stage 3 mini-boss):** Large shielded rectangle, blocks bridge
- **Egg Piston (Stage 3 boss):** see Stage 3 boss spec in Section 7.3

### 5.4 Objects

- **Rings:** Small yellow circles with rotating highlight line
- **Springs:** Red rectangle, compressed/extended animation on trigger
- **Launch pipes:** Filled rectangles with directional arrow markers
- **Checkpoint:** Post with rotating top, color changes when activated
- **Goal post:** Tall post with spinning sign

### 5.5 HUD

- Top-left: ring count (flashes at 0), timer, lives count
- Drawn with `pyxel.text()`

### 5.6 Palette Allocation (16 colors)

| Slot | Usage |
|------|-------|
| 0 | Transparent / sky background |
| 1–3 | Terrain (3 shades, swapped per stage) |
| 4–5 | Player body / accent |
| 6 | Enemy primary |
| 7 | Ring yellow |
| 8 | Spring red |
| 9 | Hazard orange |
| 10 | Water / liquid blue |
| 11–12 | UI / text (white, dark) |
| 13–15 | Stage-specific accents |

---

## 6. Audio

All audio through Pyxel's native 4-channel chiptune engine. MP3 assets in `assets/` are reference tracks for composition — not shipped in the game.

### 6.1 Channel Allocation

| Channel | Role |
|---------|------|
| 0 | Music: melody / lead |
| 1 | Music: bass / harmony |
| 2 | Music: percussion / rhythm |
| 3 | SFX (preempts; channel 2 ducks during SFX) |

### 6.2 Sound Effects

| `sounds[]` slot | SFX | Description |
|----------------|-----|-------------|
| 0 | Ring collect | Short ascending arpeggio, ~4 frames |
| 1 | Jump | Quick rising tone |
| 2 | Spindash charge | Ascending buzz, retriggered each press |
| 3 | Spindash release | Sharp burst |
| 4 | Enemy destroy | Pop + descending sparkle |
| 5 | Enemy bounce | Higher-pitched jump variant |
| 6 | Spring | Sine wave pitch bend (boing) |
| 7 | Ring loss | Scatter sound, descending |
| 8 | Hurt / death | Harsh descending tone |
| 9 | Checkpoint | Two-tone chime |
| 10 | Stage clear | Ascending fanfare, longer |
| 11 | Boss hit | Metallic impact |
| 12 | Liquid rising | Low rumble loop |
| 13 | Menu select | Click |
| 14 | Menu confirm | Chime |
| 15 | 1-up | Classic jingle |

### 6.3 Music Tracks

| `musics[]` slot | Reference MP3 | Usage |
|----------------|--------------|-------|
| 0 | `MAIN_MENU_Genesis_of_Glory.mp3` | Title screen, stage select |
| 1 | `LV1_Pixel_Pursuit.mp3` | Stage 1: Hillside Rush |
| 2 | `LV2_Chrome_Citadel.mp3` | Stage 2: Pipe Works |
| 3 | `LV3_Genesis_Gauntlet.mp3` | Stage 3: Skybridge Gauntlet |
| 4 | (composed in-engine) | Boss theme |
| 5 | (composed in-engine) | Stage clear jingle |
| 6 | (composed in-engine) | Game over |
| 7 | (reserved) | Future use |

**Composition approach:** Transcribe melodic/rhythmic contour of each reference MP3 into MML strings. Each track = 3 sound sequences (melody, bass, percussion) combined into a `musics[]` entry. Tempo and key matched to reference feel. Tracks loop via `playm(track, loop=True)`.

**SFX priority:** SFX on channel 3 preempts immediately. Channel 2 (percussion) mutes for SFX duration, then resumes.

---

## 7. Stage Designs

All stages share the same tile format and entity system. Dimensions in world pixels; SVG viewBox matches directly.

### 7.1 Stage 1 — Hillside Rush

**Theme:** Green hillside, open sky. Teaching momentum.
**Dimensions:** ~4800x720 (300x45 tiles)
**Route:** Single path, left to right.

**Section 1 — Flat runway (0–600px):**
Player start at x=64. Flat ground, rings in an arc. Orient the player, establish controls.

**Section 2 — Gentle slopes (600–1600px):**
Undulating terrain — convex hills at ~25° into concave valleys. Rings along slope contours. 2–3 stationary crab enemies on flat sections between slopes. Teaches that slopes affect speed naturally.

**Section 3 — Half-pipe valley (1600–2400px):**
3 connected U-shaped valleys with increasing depth. Rings at crests. Visual spindash tutorial cue before the first pipe. Players who spindash at the crest gain significantly more speed. Introduces spindash as momentum amplifier.

**Section 4 — Acceleration runway (2400–3200px):**
Long flat/slight downhill. Continuous ring line. No enemies. Rewards speed built in section 3.

**Section 5 — The loop (3200–4000px):**
Full 360° loop, radius ~128px (diameter 256px = 16 tiles). Flat approach runway. Rings trace inside of loop. Speed < ~6 at entry → stall and slide back. Speed ≥ 6 → clean pass. No punishment for stalling. Momentum checkpoint — validates the player learned to maintain speed.

**Section 6 — Goal run (4000–4800px):**
Gentle downhill, scattered rings, one final enemy, goal post.

**Geometry primitives:** Convex/concave slopes at 25° and 45°, full loop (r=128), flat runways.
**Enemies:** Crab (stationary/patrol), Buzzer (hover obstacles). **Objects:** ~200 rings, 1 spring (half-pipe exit safety net), checkpoint at section 3, goal post.

### 7.2 Stage 2 — Pipe Works

**Theme:** Industrial interior, teal/gray. Teaching routing.
**Dimensions:** ~5600x1024 (350x64 tiles)
**Routes:** Three horizontal paths (low/mid/high).

**Vertical structure:**
- Low route: y=768–1024 (bottom 256px)
- Mid route: y=384–640
- High route: y=0–256 (top 256px)
- Connecting shafts at specific x positions

**Section 1 — Entry hall (0–800px):**
All three routes visible. Player starts on mid. Drop down → low (easy/default). Spindash off slope → high (skilled). Forward → continue mid. Presents routing choice immediately.

**Section 2 — Diverged paths (800–2800px):**

*Low route:* Straightforward flat platforming with enemies. Top-only platforms over liquid (liquid at y=960). Slow but safe. More enemies, fewer rings.

*Mid route:* Requires basic spindash to cross gaps. Horizontal launch pipes connect platforms. Pipe mechanic: enter trigger zone → launch at fixed velocity → exit at pipe end, resume normal physics. Moderate enemies and rings.

*High route:* Requires chained spindash off 45° slope at entry. Once reached, nearly unobstructed fast path. Few enemies, dense rings (reward). One-way drop-down shortcuts to mid at 2 points (safety valves).

**Section 3 — Liquid rise zone (2800–3800px):**
Routes converge into a single tall room. Liquid rises from bottom at 1px/frame when player enters zone (x > 2800). Stops when player exits (x > 3800). Liquid deals damage on contact (ring loss, not instant death). New players escape by moving forward. Fast players outrun it entirely.

**Section 4 — Reconvergence (3800–4800px):**
Routes rejoin. Downhill with slopes. Final enemy cluster.

**Section 5 — Goal (4800–5600px):**
Flat approach, goal post. Checkpoint at section 3 entry.

**Unique systems:**
- **Liquid rise:** Trigger-based, 1px/frame, y=1024→384
- **Launch pipes:** Rectangular triggers, overwrite velocity to fixed vector (e.g. `(10, 0)`), player invulnerable during travel
- **One-way drop-downs:** Top-only tiles

**Enemies:** Crab (patrol), Buzzer (mid-route gaps), Chopper (liquid zone). **Objects:** ~300 rings, springs at route transitions, 4 launch pipes, 2 checkpoints.

### 7.3 Stage 3 — Skybridge Gauntlet

**Theme:** Elevated sky platforms, white/blue. Synthesis under pressure.
**Dimensions:** ~5200x896 (325x56 tiles)
**Structure:** Build → launch → clear → ascend rhythm, repeated with escalation.

**Section 1 — Opening bridges (0–800px):**
Narrow platforms with gaps (32px → 48px → 64px). Enemies on bridges that cannot be avoided by waiting. Establishes that momentum is harder to maintain here.

**Section 2 — Rhythm loop ×1 (800–1600px):**
BUILD: Downhill slope, gain speed. LAUNCH: 30° ramp, airborne over 80px gap. CLEAR: Land on platform with 2 crab enemies, spindash through them. ASCEND: Bounce off second enemy upward to higher platform.

**Section 3 — Rhythm loop ×2 (1600–2400px):**
Same pattern, escalated. 112px gap. 3 enemies (crab, buzzer, crab). 35° ramp. Narrower landing.

**Section 4 — Rhythm loop ×3 (2400–3200px):**
144px gap. 4 mixed enemies. 40° ramp. Requires spindash before ramp for enough launch speed.

**Section 5 — Path split: the guardian (3200–4000px):**
Large shielded enemy blocks a narrow bridge.
- *Low path:* Detour under the bridge. Slow, narrow platforming over pits.
- *Fast path:* Spindash through at ground_speed ≥ 8 to break the shield.

Forces the player to use spindash as a deliberate tool.

**Section 6 — Boss arena (4000–5200px):**
Flat enclosed arena. 20 rings.

**Boss: Egg Piston** — state machine:
| State | Duration | Behavior |
|-------|----------|----------|
| IDLE | 2.0s | Hovers at top, slow left/right movement |
| DESCEND | 1.0s | Drops to ground. Targeting indicator appears 1s before |
| VULNERABLE | 1.5s (→1.0s after 4 hits) | Sits on ground, cockpit exposed |
| ASCEND | 1.0s | Rises. Damages player if underneath |

- **Damage condition:** Only spindash (ground_speed ≥ 8) deals damage. Regular jumps bounce off armor.
- **HP:** 8 hits.
- **Escalation:** After 4 hits, VULNERABLE shrinks to 1.0s, IDLE movement speed doubles.
- **Design purpose:** Stationary charge-and-release spindash timing. Stages 1–2 taught momentum; this stage's boss requires controlled bursts.

**Enemies:** Crab, Buzzer, Guardian (mini-boss), Egg Piston (boss). **Objects:** ~250 rings, springs under gaps, 2 checkpoints (before rhythm ×1, before boss).

---

## 8. Game Systems Summary

### Ring System
- Collecting a ring: +1 to ring count, play SFX slot 0
- Taking damage with rings > 0: scatter rings outward (up to 32), brief invulnerability, play SFX slot 7
- Taking damage with rings = 0: death, play SFX slot 8
- Scattered rings can be recollected for ~3 seconds, then disappear

### Lives and Game Over
- Start with 3 lives
- 100 rings = extra life
- Death → restart from last checkpoint (or stage start)
- 0 lives → game over screen → return to title

### Checkpoint System
- Activating a checkpoint saves position + ring count
- Visual: post with rotating top, color change on activation
- Play SFX slot 9 on activation
