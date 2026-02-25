"""speednik/main.py — Entry point with demo mode for T-001-05.

Builds a hardcoded test level (flat ground + slope + loop), creates a player,
and runs the game loop with debug visualization and Sonic 2 camera.
"""

import pyxel

from speednik import renderer
from speednik.audio import (
    SFX_1UP,
    SFX_CHECKPOINT,
    SFX_LIQUID_RISING,
    SFX_RING,
    SFX_SPRING,
    init_audio,
    play_sfx,
    update_audio,
)
from speednik.camera import camera_update, create_camera
from speednik.constants import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPRING_HITBOX_H,
    SPRING_HITBOX_W,
    STANDING_HEIGHT_RADIUS,
)
from speednik.objects import (
    CheckpointEvent,
    LiquidEvent,
    PipeEvent,
    Ring,
    RingEvent,
    SpringEvent,
    check_checkpoint_collision,
    check_ring_collection,
    check_spring_collision,
    load_checkpoints,
    load_liquid_zones,
    load_pipes,
    load_springs,
    update_liquid_zones,
    update_pipe_travel,
    update_spring_cooldowns,
)
from speednik.physics import InputState
from speednik.player import PlayerState, create_player, get_player_rect, player_update
from speednik.terrain import FULL, TILE_SIZE, Tile, TileLookup


# ---------------------------------------------------------------------------
# Demo level
# ---------------------------------------------------------------------------

def _build_demo_level() -> tuple[dict[tuple[int, int], Tile], TileLookup]:
    """Build a hardcoded demo level: flat ground + slope + loop approach."""
    tiles: dict[tuple[int, int], Tile] = {}

    # Flat ground: tiles 0–29 at y=12 (pixel y=192..208)
    for tx in range(30):
        tiles[(tx, 12)] = Tile(
            height_array=[TILE_SIZE] * TILE_SIZE,
            angle=0,
            solidity=FULL,
        )

    # Gentle upslope: tiles 10–13 at y=11 (above main ground)
    # Height arrays create a gradual ramp from right to left
    slope_angles = [
        round(15 * 256 / 360) % 256,  # ~15 degrees
        round(25 * 256 / 360) % 256,  # ~25 degrees
        round(25 * 256 / 360) % 256,
        round(15 * 256 / 360) % 256,
    ]
    slope_heights = [
        [0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 16],
        [16, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2],
        [13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 0, 0],
    ]
    for i, tx in enumerate(range(10, 14)):
        tiles[(tx, 11)] = Tile(
            height_array=slope_heights[i],
            angle=slope_angles[i],
            solidity=FULL,
        )

    # Extended flat ground under the slope area
    for tx in range(30, 50):
        tiles[(tx, 12)] = Tile(
            height_array=[TILE_SIZE] * TILE_SIZE,
            angle=0,
            solidity=FULL,
        )

    def lookup(tx: int, ty: int) -> Tile | None:
        return tiles.get((tx, ty))

    return tiles, lookup


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

def _read_input() -> InputState:
    """Map Pyxel buttons to InputState."""
    return InputState(
        left=pyxel.btn(pyxel.KEY_LEFT),
        right=pyxel.btn(pyxel.KEY_RIGHT),
        jump_pressed=pyxel.btnp(pyxel.KEY_Z),
        jump_held=pyxel.btn(pyxel.KEY_Z),
        down_held=pyxel.btn(pyxel.KEY_DOWN),
        up_held=pyxel.btn(pyxel.KEY_UP),
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class App:
    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Speednik", fps=60)
        renderer.init_palette()
        init_audio()

        self.tiles, self.tile_lookup = _build_demo_level()

        # Compute level dimensions from tile data
        max_tx = max(tx for tx, _ in self.tiles) + 1
        max_ty = max(ty for _, ty in self.tiles) + 1
        level_w = max_tx * TILE_SIZE
        level_h = max_ty * TILE_SIZE

        # Player starts on flat ground at tile x=4
        start_x = 4 * TILE_SIZE + TILE_SIZE // 2  # center of tile 4
        start_y = 12 * TILE_SIZE - STANDING_HEIGHT_RADIUS  # feet at top of tile row 12
        self.player = create_player(float(start_x), float(start_y))

        # Demo rings: a line above flat ground for testing collection
        self.rings: list[Ring] = []
        for i in range(20):
            rx = float(6 * TILE_SIZE + i * 24)
            ry = float(12 * TILE_SIZE - 24)  # 24px above ground surface
            self.rings.append(Ring(x=rx, y=ry))

        # Game objects (empty in demo mode — populated when loading real stages)
        self.springs = load_springs([])
        self.checkpoints = load_checkpoints([])
        self.pipes = load_pipes([])
        self.liquid_zones = load_liquid_zones([])

        # Sonic 2 camera system
        self.camera = create_camera(level_w, level_h, float(start_x), float(start_y))

        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        inp = _read_input()
        player_update(self.player, inp, self.tile_lookup)

        # Ring collection
        ring_events = check_ring_collection(self.player, self.rings)
        for event in ring_events:
            if event == RingEvent.COLLECTED:
                play_sfx(SFX_RING)
            elif event == RingEvent.EXTRA_LIFE:
                play_sfx(SFX_1UP)

        # Spring collision
        spring_events = check_spring_collision(self.player, self.springs)
        for event in spring_events:
            if event == SpringEvent.LAUNCHED:
                play_sfx(SFX_SPRING)

        # Checkpoint collision
        cp_events = check_checkpoint_collision(self.player, self.checkpoints)
        for event in cp_events:
            if event == CheckpointEvent.ACTIVATED:
                play_sfx(SFX_CHECKPOINT)

        # Pipe travel
        pipe_events = update_pipe_travel(self.player, self.pipes)
        for event in pipe_events:
            if event == PipeEvent.ENTERED:
                pass  # Could add pipe entry SFX
            elif event == PipeEvent.EXITED:
                pass  # Could add pipe exit SFX

        # Liquid zones
        liquid_events = update_liquid_zones(self.player, self.liquid_zones)
        for event in liquid_events:
            if event == LiquidEvent.STARTED_RISING:
                play_sfx(SFX_LIQUID_RISING)

        # Spring cooldowns
        update_spring_cooldowns(self.springs)

        update_audio()

        # Update camera after player (needs final position)
        camera_update(self.camera, self.player, inp)

    def draw(self):
        pyxel.cls(0)  # Sky background (palette slot 0)

        # World-space drawing
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        pyxel.camera(cam_x, cam_y)

        renderer.draw_terrain(self.tiles, cam_x, cam_y)

        # World rings
        for ring in self.rings:
            if not ring.collected:
                renderer._draw_ring(int(ring.x), int(ring.y), pyxel.frame_count)

        # Springs
        for spring in self.springs:
            sx = int(spring.x - SPRING_HITBOX_W // 2)
            sy = int(spring.y - SPRING_HITBOX_H // 2)
            color = 8  # Red (palette slot 8)
            if spring.cooldown > 0:
                # Compressed visual
                pyxel.rect(sx, sy + SPRING_HITBOX_H // 2, SPRING_HITBOX_W, SPRING_HITBOX_H // 2, color)
            else:
                pyxel.rect(sx, sy, SPRING_HITBOX_W, SPRING_HITBOX_H, color)

        # Checkpoints
        for cp in self.checkpoints:
            color = 10 if cp.activated else 7  # Yellow if active, white if not
            cx = int(cp.x)
            cy = int(cp.y)
            pyxel.line(cx, cy, cx, cy - 24, color)  # Post
            pyxel.circ(cx, cy - 26, 3, color)  # Top

        # Pipes (filled rectangles with directional indicators)
        for pipe in self.pipes:
            px1 = int(min(pipe.x, pipe.exit_x))
            py1 = int(min(pipe.y, pipe.exit_y)) - 12
            px2 = int(max(pipe.x, pipe.exit_x))
            py2 = int(max(pipe.y, pipe.exit_y)) + 12
            pyxel.rectb(px1, py1, px2 - px1, py2 - py1, 5)  # Teal outline

        # Liquid zones
        for zone in self.liquid_zones:
            if zone.active and zone.current_y < zone.floor_y:
                lx1 = int(zone.trigger_x)
                lx2 = int(zone.exit_x)
                ly = int(zone.current_y)
                lh = int(zone.floor_y - zone.current_y)
                # Semi-transparent effect via alternating lines
                for row in range(lh):
                    if (ly + row + pyxel.frame_count // 4) % 2 == 0:
                        pyxel.line(lx1, ly + row, lx2, ly + row, 10)  # Blue

        renderer.draw_player(self.player, pyxel.frame_count)
        renderer.draw_scattered_rings(
            self.player.scattered_rings, pyxel.frame_count
        )
        renderer.draw_particles(pyxel.frame_count)

        # Screen-space HUD
        pyxel.camera()
        renderer.draw_hud(self.player, pyxel.frame_count, pyxel.frame_count)


if __name__ == "__main__":
    App()
