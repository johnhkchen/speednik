"""speednik/main.py — Entry point with demo mode for T-001-05.

Builds a hardcoded test level (flat ground + slope + loop), creates a player,
and runs the game loop with debug visualization and Sonic 2 camera.
"""

import pyxel

from speednik.audio import init_audio, update_audio
from speednik.camera import camera_update, create_camera
from speednik.constants import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STANDING_HEIGHT_RADIUS,
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

        # Sonic 2 camera system
        self.camera = create_camera(level_w, level_h, float(start_x), float(start_y))

        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        inp = _read_input()
        player_update(self.player, inp, self.tile_lookup)
        update_audio()

        # Update camera after player (needs final position)
        camera_update(self.camera, self.player, inp)

    def draw(self):
        pyxel.cls(12)  # Light blue sky

        # Set viewport offset for world drawing
        pyxel.camera(int(self.camera.x), int(self.camera.y))

        # Draw tiles (in world coordinates)
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        for (tx, ty), tile in self.tiles.items():
            world_x = tx * TILE_SIZE
            world_y = ty * TILE_SIZE
            # Cull tiles outside viewport
            if world_x + TILE_SIZE < cam_x or world_x > cam_x + SCREEN_WIDTH:
                continue
            if world_y + TILE_SIZE < cam_y or world_y > cam_y + SCREEN_HEIGHT:
                continue
            for col in range(TILE_SIZE):
                h = tile.height_array[col]
                if h > 0:
                    x = world_x + col
                    y_top = world_y + (TILE_SIZE - h)
                    pyxel.line(x, y_top, x, world_y + TILE_SIZE - 1, 3)  # Green

        # Draw player as colored rectangle (world coordinates)
        px, py, pw, ph = get_player_rect(self.player)
        color = 8 if self.player.state == PlayerState.HURT else 4
        if self.player.invulnerability_timer > 0 and pyxel.frame_count % 4 < 2:
            color = 0
        pyxel.rect(int(px), int(py), pw, ph, color)

        # Draw scattered rings (world coordinates)
        for ring in self.player.scattered_rings:
            pyxel.circ(int(ring.x), int(ring.y), 2, 10)

        # Reset camera for HUD (screen-relative)
        pyxel.camera()

        # Debug HUD
        p = self.player.physics
        pyxel.text(4, 4, f"State: {self.player.state.value}", 7)
        pyxel.text(4, 12, f"GndSpd: {p.ground_speed:.2f}", 7)
        pyxel.text(4, 20, f"Pos: ({p.x:.0f}, {p.y:.0f})", 7)
        pyxel.text(4, 28, f"Rings: {self.player.rings}", 7)
        pyxel.text(4, 36, f"Angle: {p.angle}", 7)
        pyxel.text(4, 44, f"OnGnd: {p.on_ground}", 7)

        # Controls help
        pyxel.text(4, SCREEN_HEIGHT - 10, "Arrows+Z:jump  Up/Down:look  Q:quit", 7)


if __name__ == "__main__":
    App()
