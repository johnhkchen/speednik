"""speednik/renderer.py — Code-generated geometric art renderer.

All visuals drawn with Pyxel primitives — no .pyxres sprite sheets.
Implements specification §5: player, terrain, enemies, objects, HUD, particles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pyxel

from speednik.constants import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from speednik.terrain import TILE_SIZE

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

# Fixed palette slots (set once at init)
_BASE_PALETTE = {
    0: 0x2090D0,   # Sky blue (background / cls color)
    4: 0x3050D0,   # Player body (blue)
    5: 0xD03030,   # Player accent (red, shoes)
    6: 0xC04040,   # Enemy primary
    7: 0xF0D000,   # Ring yellow
    8: 0xE02020,   # Spring red
    9: 0xE08020,   # Hazard orange
    10: 0x2060E0,  # Water / liquid blue
    11: 0xFFFFFF,  # UI white
    12: 0x202020,  # UI dark
}

# Per-stage terrain colors (slots 1–3 terrain shades, 13–15 stage accents)
STAGE_PALETTES: dict[str, dict[int, int]] = {
    "hillside": {
        1: 0x1B8C00,   # Dark green (earth)
        2: 0x30C010,   # Mid green (surface)
        3: 0x50E830,   # Light green (highlight)
        13: 0x8B5E3C,  # Brown accent
        14: 0xC49A6C,  # Light brown
        15: 0x6B3A1E,  # Dark brown
    },
    "pipeworks": {
        1: 0x1A5C5C,   # Dark teal
        2: 0x2A8C8C,   # Mid teal
        3: 0x40B0B0,   # Light teal
        13: 0x505050,  # Dark gray
        14: 0x808080,  # Mid gray
        15: 0xA0A0A0,  # Light gray
    },
    "skybridge": {
        1: 0x6090C0,   # Sky blue
        2: 0x90B8E0,   # Light sky
        3: 0xC0D8F0,   # Near-white blue
        13: 0xC0C0C0,  # Light gray
        14: 0xE0E0E0,  # Near-white
        15: 0xFFFFFF,  # White
    },
}


def init_palette() -> None:
    """Set the base palette colors. Call after pyxel.init()."""
    for slot, color in _BASE_PALETTE.items():
        pyxel.colors[slot] = color
    # Default to hillside terrain
    set_stage_palette("hillside")


def set_stage_palette(stage_name: str) -> None:
    """Swap terrain palette slots for the given stage."""
    palette = STAGE_PALETTES.get(stage_name)
    if palette is None:
        return
    for slot, color in palette.items():
        pyxel.colors[slot] = color


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------

def draw_terrain(
    tiles: dict,
    camera_x: int,
    camera_y: int,
) -> None:
    """Draw visible tiles with height profiles and surface lines.

    tiles: dict mapping (tx, ty) -> Tile
    camera_x, camera_y: viewport offset in world pixels
    """
    for (tx, ty), tile in tiles.items():
        wx = tx * TILE_SIZE
        wy = ty * TILE_SIZE
        # Viewport culling
        if wx + TILE_SIZE < camera_x or wx > camera_x + SCREEN_WIDTH:
            continue
        if wy + TILE_SIZE < camera_y or wy > camera_y + SCREEN_HEIGHT:
            continue
        _draw_tile(wx, wy, tile)


def _draw_tile(wx: int, wy: int, tile) -> None:
    """Draw a single tile at world position (wx, wy)."""
    prev_top = -1
    for col in range(TILE_SIZE):
        h = tile.height_array[col]
        if h <= 0:
            prev_top = -1
            continue
        x = wx + col
        y_top = wy + (TILE_SIZE - h)
        y_bot = wy + TILE_SIZE - 1
        # Fill column with dark terrain color
        pyxel.line(x, y_top, x, y_bot, 1)
        # Surface pixel (top) with highlight color
        pyxel.pset(x, y_top, 3)
        # Surface line connecting to previous column
        if prev_top >= 0:
            pyxel.line(x - 1, prev_top, x, y_top, 2)
        prev_top = y_top


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

def draw_player(player, frame_count: int) -> None:
    """Draw the player character based on state and animation."""
    # Invulnerability flicker
    if player.invulnerability_timer > 0 and frame_count % 4 < 2:
        return

    p = player.physics
    cx = int(p.x)
    cy = int(p.y)
    right = p.facing_right

    anim = player.anim_name
    if anim == "idle":
        _draw_player_idle(cx, cy, right)
    elif anim == "running":
        _draw_player_running(cx, cy, right, player.anim_frame)
    elif anim == "rolling":
        _draw_player_rolling(cx, cy, frame_count)
    elif anim == "spindash":
        _draw_player_rolling(cx, cy, frame_count)
        # Dust lines behind player during spindash
        dust_dir = 1 if right else -1
        for i in range(3):
            dx = -dust_dir * (8 + i * 4)
            dy = 8 - i * 2
            if frame_count % 3 != i:
                pyxel.pset(cx + dx, cy + dy, 11)
    elif anim == "hurt":
        _draw_player_hurt(cx, cy, right)
    elif anim == "dead":
        _draw_player_hurt(cx, cy, right)


def _draw_player_idle(cx: int, cy: int, right: bool) -> None:
    """Standing pose: body ellipse, limbs, circle head, dot eyes."""
    d = 1 if right else -1

    # Body (torso ellipse) — elli uses top-left + full size
    pyxel.elli(cx - 5, cy - 4, 10, 12, 4)

    # Head
    pyxel.circ(cx, cy - 9, 3, 4)

    # Eyes (2px dots)
    pyxel.pset(cx + d * 1, cy - 10, 11)
    pyxel.pset(cx + d * 2, cy - 10, 11)

    # Arms (hanging)
    pyxel.line(cx - 5, cy - 2, cx - 7, cy + 5, 4)
    pyxel.line(cx + 5, cy - 2, cx + 7, cy + 5, 4)

    # Legs (standing straight)
    pyxel.line(cx - 2, cy + 8, cx - 3, cy + 14, 4)
    pyxel.line(cx + 2, cy + 8, cx + 3, cy + 14, 4)

    # Shoes
    pyxel.pset(cx - 3, cy + 14, 5)
    pyxel.pset(cx + 3, cy + 14, 5)


def _draw_player_running(cx: int, cy: int, right: bool, frame: int) -> None:
    """Running with 4-frame limb animation."""
    d = 1 if right else -1

    # Body
    pyxel.elli(cx - 5, cy - 4, 10, 12, 4)

    # Head (slightly forward)
    pyxel.circ(cx + d * 2, cy - 9, 3, 4)

    # Eyes
    pyxel.pset(cx + d * 3, cy - 10, 11)
    pyxel.pset(cx + d * 4, cy - 10, 11)

    # Leg animation: x-offsets from center for front/back foot
    leg_offsets = [
        (-6, 5),   # frame 0: wide stride
        (-2, 2),   # frame 1: legs passing
        (5, -6),   # frame 2: wide stride (swapped)
        (2, -2),   # frame 3: legs passing (swapped)
    ]
    front_dx, back_dx = leg_offsets[frame % 4]

    # Legs
    pyxel.line(cx, cy + 8, cx + front_dx, cy + 14, 4)
    pyxel.line(cx, cy + 8, cx + back_dx, cy + 14, 4)

    # Shoes at foot positions
    pyxel.pset(cx + front_dx, cy + 14, 5)
    pyxel.pset(cx + back_dx, cy + 14, 5)

    # Arms swing opposite to legs
    arm_dx_front = -back_dx  # opposite of back leg
    arm_dx_back = -front_dx
    pyxel.line(cx, cy - 2, cx + arm_dx_front * 0.6, cy + 3, 4)
    pyxel.line(cx, cy - 2, cx + arm_dx_back * 0.6, cy + 3, 4)


def _draw_player_rolling(cx: int, cy: int, frame_count: int) -> None:
    """Spinning ball for rolling/jumping/spindash."""
    # Main ball
    pyxel.circ(cx, cy, 7, 4)

    # Rotating accent line
    angle = (frame_count * 15) % 360
    rad = math.radians(angle)
    lx = int(5 * math.cos(rad))
    ly = int(5 * math.sin(rad))
    pyxel.line(cx - lx, cy - ly, cx + lx, cy + ly, 5)


def _draw_player_hurt(cx: int, cy: int, right: bool) -> None:
    """Knocked-back pose."""
    d = 1 if right else -1

    # Body
    pyxel.elli(cx - 5, cy - 4, 10, 12, 4)

    # Head (tilted back)
    pyxel.circ(cx - d * 2, cy - 9, 3, 4)

    # Eyes (X marks)
    pyxel.pset(cx - d * 1, cy - 10, 5)
    pyxel.pset(cx - d * 3, cy - 10, 5)

    # Arms flung out
    pyxel.line(cx - 5, cy - 2, cx - 10, cy - 6, 4)
    pyxel.line(cx + 5, cy - 2, cx + 10, cy - 6, 4)

    # Legs splayed
    pyxel.line(cx - 2, cy + 8, cx - 6, cy + 14, 4)
    pyxel.line(cx + 2, cy + 8, cx + 6, cy + 14, 4)


# ---------------------------------------------------------------------------
# Enemies
# ---------------------------------------------------------------------------

def _draw_enemy_crab(x: int, y: int, frame_count: int) -> None:
    """Crab: wide ellipse + animated line claws + legs."""
    # Body
    pyxel.elli(x - 8, y - 5, 16, 10, 6)

    # Eyes
    pyxel.pset(x - 3, y - 4, 11)
    pyxel.pset(x + 3, y - 4, 11)

    # Claws (open/close animation)
    claw_open = frame_count % 30 < 15
    if claw_open:
        # Open claws
        pyxel.line(x - 8, y - 2, x - 13, y - 5, 6)
        pyxel.line(x - 13, y - 5, x - 11, y - 8, 6)
        pyxel.line(x + 8, y - 2, x + 13, y - 5, 6)
        pyxel.line(x + 13, y - 5, x + 11, y - 8, 6)
    else:
        # Closed claws
        pyxel.line(x - 8, y - 2, x - 13, y - 4, 6)
        pyxel.line(x - 13, y - 4, x - 12, y - 6, 6)
        pyxel.line(x + 8, y - 2, x + 13, y - 4, 6)
        pyxel.line(x + 13, y - 4, x + 12, y - 6, 6)

    # Legs
    for dx in (-5, -2, 2, 5):
        pyxel.line(x + dx, y + 5, x + dx, y + 8, 6)


def _draw_enemy_buzzer(x: int, y: int, frame_count: int) -> None:
    """Buzzer: circle body + flapping triangle wings + stinger."""
    # Body
    pyxel.circ(x, y, 5, 6)

    # Eyes
    pyxel.pset(x - 2, y - 1, 11)
    pyxel.pset(x + 2, y - 1, 11)

    # Wings (flap animation)
    wing_up = frame_count % 20 < 10
    wy = y - 8 if wing_up else y - 4
    pyxel.tri(x - 5, y - 3, x - 12, wy, x - 5, y, 9)
    pyxel.tri(x + 5, y - 3, x + 12, wy, x + 5, y, 9)

    # Stinger
    pyxel.line(x, y + 5, x, y + 9, 9)
    pyxel.pset(x, y + 9, 8)


def _draw_enemy_chopper(x: int, y: int, frame_count: int) -> None:
    """Chopper: elongated ellipse + mouth animation."""
    # Body
    pyxel.elli(x - 4, y - 8, 8, 16, 6)

    # Eyes
    pyxel.pset(x - 2, y - 4, 11)
    pyxel.pset(x + 2, y - 4, 11)

    # Mouth (open/close)
    mouth_open = frame_count % 24 < 12
    if mouth_open:
        pyxel.line(x - 3, y, x + 3, y, 12)
    else:
        pyxel.pset(x, y, 12)


def _draw_enemy_guardian(x: int, y: int, frame_count: int) -> None:
    """Guardian: large shielded rectangle."""
    # Shield (outer)
    pyxel.rectb(x - 12, y - 14, 24, 28, 9)

    # Body
    pyxel.rect(x - 10, y - 12, 20, 24, 6)

    # Eyes
    pyxel.pset(x - 3, y - 6, 11)
    pyxel.pset(x + 3, y - 6, 11)

    # Shield flash
    if frame_count % 40 < 5:
        pyxel.rectb(x - 12, y - 14, 24, 28, 11)


def _draw_enemy_egg_piston(x: int, y: int, frame_count: int) -> None:
    """Egg Piston boss: cockpit + armor + piston."""
    # Piston base
    pyxel.rect(x - 8, y + 6, 16, 10, 12)

    # Armor body
    pyxel.rect(x - 10, y - 8, 20, 16, 6)

    # Cockpit (dome)
    pyxel.elli(x - 6, y - 14, 12, 8, 9)

    # Cockpit glass
    pyxel.elli(x - 4, y - 12, 8, 5, 10)

    # Eyes inside cockpit
    pyxel.pset(x - 2, y - 10, 12)
    pyxel.pset(x + 2, y - 10, 12)

    # Piston detail lines
    pyxel.line(x - 6, y + 8, x - 6, y + 14, 11)
    pyxel.line(x + 6, y + 8, x + 6, y + 14, 11)


def draw_boss_indicator(x: int, ground_y: int, frame_count: int) -> None:
    """Draw targeting indicator where boss will land (flashing dashed line)."""
    if frame_count % 8 < 4:
        return  # Flash off
    # Dashed vertical line from 40px above ground to ground
    for dy in range(0, 40, 4):
        if dy % 8 < 4:
            pyxel.pset(x, ground_y - dy, 9)  # Hazard orange
    # Crosshair on ground
    pyxel.line(x - 4, ground_y, x + 4, ground_y, 9)


# Entity type → draw function mapping
_ENTITY_DRAWERS: dict[str, callable] = {
    "enemy_crab": _draw_enemy_crab,
    "enemy_buzzer": _draw_enemy_buzzer,
    "enemy_chopper": _draw_enemy_chopper,
    "enemy_guardian": _draw_enemy_guardian,
    "enemy_egg_piston": _draw_enemy_egg_piston,
}


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------

def _draw_ring(x: int, y: int, frame_count: int) -> None:
    """Ring: yellow circle with rotating highlight."""
    pyxel.circ(x, y, 3, 7)
    # Rotating highlight line
    angle = (frame_count * 8) % 360
    rad = math.radians(angle)
    lx = int(2 * math.cos(rad))
    ly = int(2 * math.sin(rad))
    pyxel.line(x - lx, y - ly, x + lx, y + ly, 11)


def _draw_spring(x: int, y: int, frame_count: int) -> None:
    """Spring: red rectangle with top plate."""
    # Base
    pyxel.rect(x - 4, y - 4, 8, 12, 8)
    # Top plate (wider)
    pyxel.rect(x - 6, y - 6, 12, 3, 8)
    # Coil lines
    pyxel.line(x - 3, y, x + 3, y, 9)
    pyxel.line(x - 3, y + 3, x + 3, y + 3, 9)
    # Arrow on top
    pyxel.tri(x, y - 8, x - 3, y - 5, x + 3, y - 5, 11)


def _draw_pipe(x: int, y: int, frame_count: int) -> None:
    """Launch pipe: filled rectangle with arrow."""
    pyxel.rect(x - 8, y - 6, 16, 12, 12)
    pyxel.rectb(x - 8, y - 6, 16, 12, 11)
    # Arrow pointing right
    pyxel.tri(x + 2, y, x - 2, y - 3, x - 2, y + 3, 11)


def _draw_checkpoint(x: int, y: int, frame_count: int) -> None:
    """Checkpoint: post with rotating top."""
    # Post
    pyxel.line(x, y, x, y - 20, 13)
    # Rotating top (diamond that spins)
    angle = (frame_count * 6) % 360
    rad = math.radians(angle)
    half_w = max(1, int(abs(4 * math.cos(rad))))
    pyxel.elli(x - half_w, y - 24, half_w * 2, 6, 7)


def _draw_goal(x: int, y: int, frame_count: int) -> None:
    """Goal post: tall post with spinning sign."""
    # Post
    pyxel.line(x, y, x, y - 32, 11)
    # Spinning sign (compress width to simulate rotation)
    angle = (frame_count * 4) % 360
    half_w = max(1, int(abs(8 * math.cos(math.radians(angle)))))
    pyxel.rect(x - half_w, y - 32, half_w * 2, 8, 7)
    pyxel.rectb(x - half_w, y - 32, half_w * 2, 8, 12)


# Object type → draw function mapping
_OBJECT_DRAWERS: dict[str, callable] = {
    "ring": _draw_ring,
    "spring_up": _draw_spring,
    "spring_right": _draw_spring,
    "pipe_h": _draw_pipe,
    "pipe_v": _draw_pipe,
    "checkpoint": _draw_checkpoint,
    "goal": _draw_goal,
}


# ---------------------------------------------------------------------------
# Entity dispatch
# ---------------------------------------------------------------------------

def draw_entities(entities: list[dict], frame_count: int) -> None:
    """Draw all entities from the stage entity list."""
    for ent in entities:
        etype = ent.get("type", "")
        x = int(ent.get("x", 0))
        y = int(ent.get("y", 0))
        drawer = _ENTITY_DRAWERS.get(etype) or _OBJECT_DRAWERS.get(etype)
        if drawer is not None:
            drawer(x, y, frame_count)


# ---------------------------------------------------------------------------
# Scattered rings
# ---------------------------------------------------------------------------

def draw_scattered_rings(rings: list, frame_count: int) -> None:
    """Draw scattered ring particles with fade effect."""
    for ring in rings:
        # Fade to darker color when nearly expired
        col = 7 if ring.timer > 60 else 9
        pyxel.circ(int(ring.x), int(ring.y), 2, col)
        # Small highlight
        if ring.timer > 60:
            pyxel.pset(int(ring.x), int(ring.y) - 1, 11)


# ---------------------------------------------------------------------------
# Particles (enemy destroy sparkle)
# ---------------------------------------------------------------------------

@dataclass
class _Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


_particles: list[_Particle] = []


def spawn_destroy_particles(x: float, y: float) -> None:
    """Spawn sparkle particles at the given position."""
    for i in range(6):
        angle = i * 60
        rad = math.radians(angle)
        speed = 1.5
        _particles.append(_Particle(
            x=x, y=y,
            vx=speed * math.cos(rad),
            vy=speed * math.sin(rad),
            color=11 if i % 2 == 0 else 7,
            life=15,
        ))


def clear_particles() -> None:
    """Remove all active particles. Call between stage loads."""
    _particles.clear()


def draw_particles(frame_count: int) -> None:
    """Update and draw all active particles."""
    alive = []
    for p in _particles:
        p.x += p.vx
        p.y += p.vy
        p.life -= 1
        if p.life > 0:
            pyxel.pset(int(p.x), int(p.y), p.color)
            alive.append(p)
    _particles.clear()
    _particles.extend(alive)


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

def draw_hud(player, timer_frames: int, frame_count: int) -> None:
    """Draw HUD overlay in screen space. Call after pyxel.camera() reset."""
    # Ring count
    ring_label_col = 7
    if player.rings == 0 and frame_count % 60 < 30:
        ring_label_col = 9  # Flash orange when 0 rings
    pyxel.text(4, 4, f"RINGS: {player.rings}", ring_label_col)

    # Timer
    total_seconds = timer_frames // 60
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    pyxel.text(90, 4, f"TIME: {minutes}:{seconds:02d}", 11)

    # Lives
    pyxel.text(200, 4, f"x{player.lives}", 11)
