"""speednik/devpark.py — Live bot runner and dev park stage menu.

Runs robotic player strategies live in the game loop, one player_update per
frame, renderable by Pyxel. Bridges the headless test harness (strategies)
and the visual game (renderer + camera).

Also provides the dev park sub-menu and 5 elemental stage definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pyxel

from speednik import renderer
from speednik.camera import Camera, camera_update, create_camera
from speednik.constants import SCREEN_HEIGHT, SCREEN_WIDTH, STANDING_HEIGHT_RADIUS
from speednik.level import load_stage
from speednik.physics import InputState
from speednik.player import Player, create_player, player_update
from speednik.terrain import TILE_SIZE, TileLookup


# ---------------------------------------------------------------------------
# LiveBot
# ---------------------------------------------------------------------------

@dataclass
class LiveBot:
    """A bot that runs a strategy live in the game loop."""

    player: Player
    strategy: Callable[[int, Player], InputState]
    tile_lookup: TileLookup
    tiles_dict: dict
    camera: Camera
    label: str
    max_frames: int = 600
    goal_x: float | None = None
    frame: int = 0
    finished: bool = False

    def update(self) -> None:
        """Advance one frame: strategy → player_update → camera_update."""
        if self.finished:
            return
        inp = self.strategy(self.frame, self.player)
        player_update(self.player, inp, self.tile_lookup)
        camera_update(self.camera, self.player, inp)
        self.frame += 1
        if self.frame >= self.max_frames:
            self.finished = True
        elif self.goal_x is not None and self.player.physics.x >= self.goal_x:
            self.finished = True

    def draw(self) -> None:
        """Draw terrain + player using this bot's camera."""
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        pyxel.camera(cam_x, cam_y)
        renderer.draw_terrain(self.tiles_dict, cam_x, cam_y)
        renderer.draw_player(self.player, self.frame)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_level_bounds(tiles_dict: dict) -> tuple[int, int]:
    """Compute (width_px, height_px) from a tiles dictionary."""
    if not tiles_dict:
        return (TILE_SIZE, TILE_SIZE)
    max_tx = max(tx for tx, ty in tiles_dict)
    max_ty = max(ty for tx, ty in tiles_dict)
    return ((max_tx + 1) * TILE_SIZE, (max_ty + 1) * TILE_SIZE)


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def make_bot(
    tiles_dict: dict,
    tile_lookup: TileLookup,
    start_x: float,
    start_y: float,
    strategy: Callable[[int, Player], InputState],
    label: str,
    max_frames: int = 600,
    goal_x: float | None = None,
) -> LiveBot:
    """Create a LiveBot from tile data, start position, and strategy."""
    player = create_player(start_x, start_y)
    width, height = _compute_level_bounds(tiles_dict)
    camera = create_camera(width, height, start_x, start_y)
    return LiveBot(
        player=player,
        strategy=strategy,
        tile_lookup=tile_lookup,
        tiles_dict=tiles_dict,
        camera=camera,
        label=label,
        max_frames=max_frames,
        goal_x=goal_x,
    )


def make_bots_for_stage(
    stage_name: str,
    max_frames: int = 600,
) -> list[LiveBot]:
    """Create one bot per strategy for a real stage."""
    # Lazy import: strategies live in tests/ — only used in dev context.
    from tests.harness import hold_right, hold_right_jump, idle, spindash_right

    stage = load_stage(stage_name)
    sx, sy = stage.player_start
    strategies = [
        (idle(), "IDLE"),
        (hold_right(), "HOLD_RIGHT"),
        (hold_right_jump(), "JUMP"),
        (spindash_right(), "SPINDASH"),
    ]
    return [
        make_bot(stage.tiles_dict, stage.tile_lookup, sx, sy, strat, label, max_frames)
        for strat, label in strategies
    ]


def make_bots_for_grid(
    tiles_dict: dict,
    tile_lookup: TileLookup,
    start_x: float,
    start_y: float,
    strategies: list[tuple[Callable[[int, Player], InputState], str]],
    max_frames: int = 600,
    goal_x: float | None = None,
) -> list[LiveBot]:
    """Create bots for a synthetic grid scenario."""
    return [
        make_bot(tiles_dict, tile_lookup, start_x, start_y, strat, label, max_frames, goal_x)
        for strat, label in strategies
    ]


# ---------------------------------------------------------------------------
# Dev Park Stage Definitions
# ---------------------------------------------------------------------------

GROUND_ROW = 10
LOOP_GROUND_ROW = 40
MAX_FRAMES = 900


def _start_y(ground_row: int) -> float:
    """Player start Y on a ground row."""
    return float(ground_row * TILE_SIZE) - STANDING_HEIGHT_RADIUS


def _deg_to_byte(deg: float) -> int:
    """Convert degrees to byte angle (0-255)."""
    return round(deg * 256 / 360) % 256


def _init_ramp_walker() -> list[LiveBot]:
    """RAMP WALKER: hold_right on progressive ramp, plus spindash comparison."""
    from tests.grids import build_ramp
    from tests.harness import hold_right, spindash_right

    tiles_dict, tile_lookup = build_ramp(
        approach_tiles=10, ramp_tiles=30,
        start_angle=0, end_angle=_deg_to_byte(60),
        ground_row=GROUND_ROW,
    )
    sx = 48.0
    sy = _start_y(GROUND_ROW)
    return [
        make_bot(tiles_dict, tile_lookup, sx, sy, hold_right(), "HOLD_RIGHT", MAX_FRAMES),
        make_bot(tiles_dict, tile_lookup, sx, sy, spindash_right(), "SPINDASH", MAX_FRAMES),
    ]


def _init_speed_gate() -> list[LiveBot]:
    """SPEED GATE: walk vs spindash on a steep obstacle."""
    from tests.grids import build_ramp
    from tests.harness import hold_right, spindash_right

    tiles_dict, tile_lookup = build_ramp(
        approach_tiles=10, ramp_tiles=15,
        start_angle=0, end_angle=_deg_to_byte(60),
        ground_row=GROUND_ROW,
    )
    sx = 48.0
    sy = _start_y(GROUND_ROW)
    return [
        make_bot(tiles_dict, tile_lookup, sx, sy, hold_right(), "WALK", MAX_FRAMES),
        make_bot(tiles_dict, tile_lookup, sx, sy, spindash_right(), "SPINDASH", MAX_FRAMES),
    ]


def _init_loop_lab_with_ramps() -> list[LiveBot]:
    """LOOP LAB variant 1: loop with entry ramps (should succeed)."""
    from tests.grids import build_loop
    from tests.harness import spindash_right

    tiles_dict, tile_lookup = build_loop(
        approach_tiles=10, radius=128,
        ground_row=LOOP_GROUND_ROW, ramp_radius=128,
    )
    sx = 48.0
    sy = _start_y(LOOP_GROUND_ROW)
    return [
        make_bot(tiles_dict, tile_lookup, sx, sy, spindash_right(), "WITH RAMPS", MAX_FRAMES),
    ]


def _init_loop_lab_no_ramps() -> list[LiveBot]:
    """LOOP LAB variant 2: loop without ramps (should fail)."""
    from tests.grids import build_loop
    from tests.harness import spindash_right

    tiles_dict, tile_lookup = build_loop(
        approach_tiles=10, radius=128,
        ground_row=LOOP_GROUND_ROW, ramp_radius=None,
    )
    sx = 48.0
    sy = _start_y(LOOP_GROUND_ROW)
    return [
        make_bot(tiles_dict, tile_lookup, sx, sy, spindash_right(), "NO RAMPS", MAX_FRAMES),
    ]


# Gap widths for progressive challenge
_GAP_WIDTHS = [3, 5, 8, 12, 20]


def _init_gap_jump(gap_index: int = 0) -> list[LiveBot]:
    """GAP JUMP: hold_right_jump across a gap of given width."""
    from tests.grids import build_gap
    from tests.harness import hold_right_jump

    gap_tiles = _GAP_WIDTHS[gap_index % len(_GAP_WIDTHS)]
    tiles_dict, tile_lookup = build_gap(
        approach_tiles=30, gap_tiles=gap_tiles,
        landing_tiles=15, ground_row=GROUND_ROW,
    )
    sx = 48.0
    sy = _start_y(GROUND_ROW)
    return [
        make_bot(tiles_dict, tile_lookup, sx, sy, hold_right_jump(),
                 f"GAP={gap_tiles}", MAX_FRAMES),
    ]


def _init_hillside_bot() -> list[LiveBot]:
    """HILLSIDE BOT: hold_right on the real hillside stage."""
    from tests.harness import hold_right

    stage = load_stage("hillside")
    sx, sy = stage.player_start
    return [
        make_bot(stage.tiles_dict, stage.tile_lookup, float(sx), float(sy),
                 hold_right(), "HOLD_RIGHT", MAX_FRAMES),
    ]


def _init_multi_view_hillside() -> list[LiveBot]:
    """MULTI-VIEW: HILLSIDE — 4 strategies on hillside for quad-split."""
    return make_bots_for_stage("hillside", max_frames=36000)


# Stages available for boundary patrol cycling
_BOUNDARY_STAGES = ["hillside", "pipeworks", "skybridge"]


def _init_boundary_patrol(stage_index: int = 0) -> list[LiveBot]:
    """BOUNDARY PATROL: hold_right and hold_left on a real stage."""
    from tests.harness import hold_left, hold_right

    name = _BOUNDARY_STAGES[stage_index % len(_BOUNDARY_STAGES)]
    stage = load_stage(name)
    sx, sy = stage.player_start
    return [
        make_bot(stage.tiles_dict, stage.tile_lookup, float(sx), float(sy),
                 hold_right(), "RIGHT->", 3600),
        make_bot(stage.tiles_dict, stage.tile_lookup, float(sx), float(sy),
                 hold_left(), "<-LEFT", 3600),
    ]


# ---------------------------------------------------------------------------
# Readout functions (draw scenario-specific HUD text)
# ---------------------------------------------------------------------------

def _readout_ramp_walker(bots: list[LiveBot]) -> None:
    """Draw angle readout for the primary bot."""
    bot = bots[0]
    p = bot.player.physics
    angle = p.angle
    on_ground = "Y" if p.on_ground else "N"
    status = "STALLED" if bot.finished and p.ground_speed < 0.5 else ""
    pyxel.text(4, SCREEN_HEIGHT - 16, f"ANGLE:{angle}  GND:{on_ground}  {status}", 11)
    if len(bots) > 1:
        b2 = bots[1]
        pyxel.text(4, SCREEN_HEIGHT - 8,
                   f"SPINDASH X:{b2.player.physics.x:.0f}", 11)


def _readout_speed_gate(bots: list[LiveBot]) -> None:
    """Draw walk vs spindash comparison."""
    for i, bot in enumerate(bots):
        stuck = bot.finished and abs(bot.player.physics.ground_speed) < 0.5
        label = "BLOCKED" if stuck else f"X:{bot.player.physics.x:.0f}"
        pyxel.text(4, SCREEN_HEIGHT - 16 + i * 8, f"{bot.label}: {label}", 11)


def _readout_loop_lab(bots: list[LiveBot]) -> None:
    """Draw loop lab variant info."""
    bot = bots[0]
    p = bot.player.physics
    q = p.angle // 64
    pyxel.text(4, SCREEN_HEIGHT - 16,
               f"{bot.label}  X:{p.x:.0f}  Q:{q}", 11)
    pyxel.text(4, SCREEN_HEIGHT - 8, "Z=TOGGLE VARIANT  X=BACK", 11)


def _readout_gap_jump(bots: list[LiveBot]) -> None:
    """Draw gap jump status."""
    bot = bots[0]
    p = bot.player.physics
    landed = p.on_ground and p.x > 30 * TILE_SIZE  # past approach
    status = "CLEARED" if landed else "JUMPING..."
    if bot.finished and not landed:
        status = "FELL"
    pyxel.text(4, SCREEN_HEIGHT - 16,
               f"{bot.label}  {status}  X:{p.x:.0f}", 11)
    pyxel.text(4, SCREEN_HEIGHT - 8, "Z=NEXT GAP  X=BACK", 11)


def _readout_boundary_patrol(bots: list[LiveBot]) -> None:
    """Draw boundary patrol status: stage name, bot positions, escape flag."""
    stage_name = _BOUNDARY_STAGES[_boundary_stage_index].upper()
    pyxel.text(4, SCREEN_HEIGHT - 24, f"STAGE: {stage_name}", 11)
    for i, bot in enumerate(bots):
        p = bot.player.physics
        lw = bot.camera.level_width
        escaped = p.x < 0 or p.x > lw
        tag = " ESCAPED!" if escaped else ""
        pyxel.text(4, SCREEN_HEIGHT - 16 + i * 8,
                   f"{bot.label} X:{p.x:.0f}{tag}", 8 if escaped else 11)
    pyxel.text(136, SCREEN_HEIGHT - 8, "Z=NEXT STAGE  X=BACK", 11)


def _readout_hillside_bot(bots: list[LiveBot]) -> None:
    """Draw hillside bot position info."""
    bot = bots[0]
    p = bot.player.physics
    pyxel.text(4, SCREEN_HEIGHT - 16,
               f"X:{p.x:.0f}  Y:{p.y:.0f}  GS:{p.ground_speed:.1f}", 11)
    pyxel.text(4, SCREEN_HEIGHT - 8,
               f"ANGLE:{p.angle}  F:{bot.frame}", 11)


# ---------------------------------------------------------------------------
# Quad-split renderer
# ---------------------------------------------------------------------------

QUADRANTS: list[tuple[int, int, int, int]] = [
    (0,   0,   128, 112),   # top-left
    (128, 0,   128, 112),   # top-right
    (0,   112, 128, 112),   # bottom-left
    (128, 112, 128, 112),   # bottom-right
]


def draw_quad_split(bots: list[LiveBot], frame_count: int) -> None:
    """Render up to 4 bots in a quad-split security-camera view.

    Each bot gets a 128x112 quadrant with independent camera and clipping.
    Strategy labels and X-position readouts are drawn in each corner.
    """
    for (qx, qy, qw, qh), bot in zip(QUADRANTS, bots):
        pyxel.clip(qx, qy, qw, qh)

        # Camera offset: map world camera into this quadrant's screen rect
        cam_x = int(bot.camera.x)
        cam_y = int(bot.camera.y)
        pyxel.camera(cam_x - qx, cam_y - qy)

        renderer.draw_terrain(bot.tiles_dict, cam_x, cam_y)
        renderer.draw_player(bot.player, frame_count)

        # Labels in screen space
        pyxel.camera()
        pyxel.text(qx + 2, qy + 2, bot.label, 7)
        pyxel.text(qx + 2, qy + qh - 8, f"X:{bot.player.physics.x:.0f}", 7)

    # Reset clip and draw dividers
    pyxel.clip()
    pyxel.line(SCREEN_WIDTH // 2, 0, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 1, 11)
    pyxel.line(0, SCREEN_HEIGHT // 2, SCREEN_WIDTH - 1, SCREEN_HEIGHT // 2, 11)


def _readout_multi_view(_bots: list[LiveBot]) -> None:
    """No extra readout for quad-split — labels are drawn by draw_quad_split."""


# ---------------------------------------------------------------------------
# Stage Definition Table
# ---------------------------------------------------------------------------

@dataclass
class DevParkStage:
    """Definition of a dev park elemental stage."""
    name: str
    init_fn: Callable[[], list[LiveBot]]
    readout_fn: Callable[[list[LiveBot]], None]


STAGES: list[DevParkStage] = [
    DevParkStage("RAMP WALKER", _init_ramp_walker, _readout_ramp_walker),
    DevParkStage("SPEED GATE", _init_speed_gate, _readout_speed_gate),
    DevParkStage("LOOP LAB", _init_loop_lab_with_ramps, _readout_loop_lab),
    DevParkStage("GAP JUMP", lambda: _init_gap_jump(0), _readout_gap_jump),
    DevParkStage("HILLSIDE BOT", _init_hillside_bot, _readout_hillside_bot),
    DevParkStage("MULTI-VIEW", _init_multi_view_hillside, _readout_multi_view),
    DevParkStage("BOUNDARY PATROL", _init_boundary_patrol, _readout_boundary_patrol),
]


# ---------------------------------------------------------------------------
# Module State
# ---------------------------------------------------------------------------

_sub_state: str = "menu"  # "menu" | "running"
_selected_index: int = 0
_active_bots: list[LiveBot] = []
_current_stage_index: int = 0
_loop_variant: int = 0  # 0=with ramps, 1=no ramps (for LOOP LAB)
_gap_index: int = 0  # current gap width index (for GAP JUMP)
_boundary_stage_index: int = 0  # current stage for BOUNDARY PATROL


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init() -> None:
    """Reset to menu state. Called when entering dev_park from stage select."""
    global _sub_state, _selected_index, _active_bots
    global _loop_variant, _gap_index, _boundary_stage_index
    _sub_state = "menu"
    _selected_index = 0
    _active_bots = []
    _loop_variant = 0
    _gap_index = 0
    _boundary_stage_index = 0
    renderer.set_stage_palette("devpark")


def update() -> str | None:
    """Update dev park state. Returns 'exit' when user backs out to stage select."""
    if _sub_state == "menu":
        return _update_menu()
    elif _sub_state == "running":
        return _update_running()
    return None


def draw() -> None:
    """Draw dev park current sub-state."""
    if _sub_state == "menu":
        _draw_menu()
    elif _sub_state == "running":
        _draw_running()


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

def _update_menu() -> str | None:
    """Handle menu navigation. Returns 'exit' when X is pressed."""
    global _selected_index, _sub_state, _active_bots, _current_stage_index

    if pyxel.btnp(pyxel.KEY_UP):
        _selected_index = (_selected_index - 1) % len(STAGES)
    elif pyxel.btnp(pyxel.KEY_DOWN):
        _selected_index = (_selected_index + 1) % len(STAGES)

    if pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_RETURN):
        _current_stage_index = _selected_index
        _active_bots = STAGES[_selected_index].init_fn()
        _sub_state = "running"
        return None

    if pyxel.btnp(pyxel.KEY_X):
        return "exit"

    return None


def _draw_menu() -> None:
    """Render the dev park stage list."""
    pyxel.text(SCREEN_WIDTH // 2 - 20, 20, "DEV PARK", 11)
    pyxel.text(SCREEN_WIDTH // 2 - 20, 30, "--------", 11)

    for i, stage in enumerate(STAGES):
        y = 50 + i * 14
        if i == _selected_index:
            prefix = "> "
            color = 11
        else:
            prefix = "  "
            color = 3  # mid green in devpark palette
        pyxel.text(60, y, f"{prefix}{stage.name}", color)

    pyxel.text(60, SCREEN_HEIGHT - 16, "Z=SELECT  X=BACK", 11)


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def _update_running() -> str | None:
    """Update active stage bots. X returns to menu."""
    global _sub_state, _active_bots, _loop_variant, _gap_index

    # X key: back to menu
    if pyxel.btnp(pyxel.KEY_X):
        _active_bots = []
        _sub_state = "menu"
        return None

    # Z key: stage-specific actions
    if pyxel.btnp(pyxel.KEY_Z):
        stage = STAGES[_current_stage_index]
        if stage.name == "LOOP LAB":
            _loop_variant = 1 - _loop_variant
            if _loop_variant == 0:
                _active_bots = _init_loop_lab_with_ramps()
            else:
                _active_bots = _init_loop_lab_no_ramps()
        elif stage.name == "GAP JUMP":
            _gap_index = (_gap_index + 1) % len(_GAP_WIDTHS)
            _active_bots = _init_gap_jump(_gap_index)
        elif stage.name == "BOUNDARY PATROL":
            _boundary_stage_index = (_boundary_stage_index + 1) % len(_BOUNDARY_STAGES)
            _active_bots = _init_boundary_patrol(_boundary_stage_index)

    # Update all bots
    for bot in _active_bots:
        bot.update()

    return None


def _draw_running() -> None:
    """Draw active stage: bots, labels, readout, debug HUD."""
    if not _active_bots:
        return

    stage = STAGES[_current_stage_index]

    # Quad-split stages use their own rendering path
    if stage.name == "MULTI-VIEW":
        draw_quad_split(_active_bots, pyxel.frame_count)
        return

    # Use the first bot's camera for the viewport
    primary = _active_bots[0]
    cam_x = int(primary.camera.x)
    cam_y = int(primary.camera.y)
    pyxel.camera(cam_x, cam_y)

    # Draw terrain from primary bot
    renderer.draw_terrain(primary.tiles_dict, cam_x, cam_y)

    # Draw level boundary lines for BOUNDARY PATROL
    if stage.name == "BOUNDARY PATROL":
        renderer.draw_level_bounds(
            primary.camera.level_width, primary.camera.level_height,
            cam_x, cam_y,
        )

    # Draw all bots' players
    for bot in _active_bots:
        renderer.draw_player(bot.player, bot.frame)

    # Labels in world space (near each bot)
    for bot in _active_bots:
        lx = int(bot.player.physics.x) - 12
        ly = int(bot.player.physics.y) - 30
        pyxel.text(lx, ly, bot.label, 11)

    # HUD in screen space
    pyxel.camera()

    # Stage name
    pyxel.text(4, 4, stage.name, 11)

    # Debug HUD for primary bot
    p = primary.player.physics
    q = p.angle // 64
    gnd = "Y" if p.on_ground else "N"
    pyxel.text(136, 4, f"F:{primary.frame}  X:{p.x:.1f}  Y:{p.y:.1f}", 11)
    pyxel.text(136, 12, f"GS:{p.ground_speed:.2f}  A:{p.angle}  Q:{q}", 11)
    pyxel.text(136, 20, f"GND:{gnd}", 11)

    # Scenario-specific readout
    stage.readout_fn(_active_bots)
