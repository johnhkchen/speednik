"""speednik/main.py — Game state machine and entry point.

Manages five game states: TITLE, STAGE_SELECT, GAMEPLAY, RESULTS, GAME_OVER.
Loads real stages from pipeline data. Handles lives, death, respawn, and
stage progression.
"""

import pyxel

from speednik import renderer
from speednik.debug import DEBUG
from speednik.audio import (
    MUSIC_BOSS,
    MUSIC_CLEAR,
    MUSIC_GAMEOVER,
    MUSIC_HILLSIDE,
    MUSIC_PIPEWORKS,
    MUSIC_SKYBRIDGE,
    MUSIC_TITLE,
    SFX_1UP,
    SFX_BOSS_HIT,
    SFX_CHECKPOINT,
    SFX_ENEMY_BOUNCE,
    SFX_ENEMY_DESTROY,
    SFX_HURT,
    SFX_LIQUID_RISING,
    SFX_MENU_CONFIRM,
    SFX_MENU_SELECT,
    SFX_RING,
    SFX_SPRING,
    SFX_STAGE_CLEAR,
    init_audio,
    play_music,
    play_sfx,
    stop_music,
    update_audio,
)
from speednik.camera import camera_update, create_camera
from speednik.constants import (
    BOSS_ARENA_START_X,
    BOSS_SPAWN_X,
    BOSS_SPAWN_Y,
    DEATH_DELAY_FRAMES,
    GAMEOVER_DELAY,
    RESULTS_DURATION,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPRING_HITBOX_H,
    SPRING_HITBOX_W,
    STANDING_HEIGHT_RADIUS,
)
from speednik.enemies import (
    EnemyEvent,
    check_enemy_collision,
    load_enemies,
    update_enemies,
)
from speednik.objects import (
    CheckpointEvent,
    GoalEvent,
    LiquidEvent,
    PipeEvent,
    Ring,
    RingEvent,
    SpringEvent,
    check_checkpoint_collision,
    check_goal_collision,
    check_ring_collection,
    check_spring_collision,
    load_checkpoints,
    load_liquid_zones,
    load_pipes,
    load_rings,
    load_springs,
    update_liquid_zones,
    update_pipe_travel,
    update_spring_cooldowns,
)
from speednik.level import load_stage
from speednik.physics import InputState
from speednik.player import Player, PlayerState, create_player, get_player_rect, player_update

# ---------------------------------------------------------------------------
# Stage configuration
# ---------------------------------------------------------------------------

_STAGE_LOADER_NAMES = {1: "hillside", 2: "pipeworks", 3: "skybridge"}
_STAGE_NAMES = {1: "HILLSIDE RUSH", 2: "PIPE WORKS", 3: "SKYBRIDGE GAUNTLET"}
_STAGE_MUSIC = {1: MUSIC_HILLSIDE, 2: MUSIC_PIPEWORKS, 3: MUSIC_SKYBRIDGE}
_STAGE_PALETTE = {1: "hillside", 2: "pipeworks", 3: "skybridge"}
_NUM_STAGES = 3
_DEV_PARK_STAGE = 0


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

        # State machine
        self.state = "title"
        self.lives = 3
        self.unlocked_stages = 1
        self.selected_stage = 1

        # Gameplay fields (populated by _load_stage)
        self.player: Player | None = None
        self.camera = None
        self.tiles_dict: dict | None = None
        self.tile_lookup = None
        self.rings: list = []
        self.springs: list = []
        self.checkpoints: list = []
        self.pipes: list = []
        self.liquid_zones: list = []
        self.enemies: list = []
        self.goal_x = 0.0
        self.goal_y = 0.0
        self.active_stage = 0
        self.timer_frames = 0
        self.death_timer = 0
        self.results_timer = 0
        self.gameover_timer = 0
        self.boss_music_started = False
        self.boss_defeated = False
        self.dev_park_bots: list | None = None

        play_music(MUSIC_TITLE)
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if self.state == "title":
            self._update_title()
        elif self.state == "stage_select":
            self._update_stage_select()
        elif self.state == "gameplay":
            self._update_gameplay()
        elif self.state == "results":
            self._update_results()
        elif self.state == "game_over":
            self._update_game_over()
        elif self.state == "dev_park":
            self._update_dev_park()

        update_audio()

    def draw(self):
        pyxel.cls(0)

        if self.state == "title":
            self._draw_title()
        elif self.state == "stage_select":
            self._draw_stage_select()
        elif self.state == "gameplay":
            self._draw_gameplay()
        elif self.state == "results":
            self._draw_results()
        elif self.state == "game_over":
            self._draw_game_over()
        elif self.state == "dev_park":
            self._draw_dev_park()

    # ------------------------------------------------------------------
    # TITLE
    # ------------------------------------------------------------------

    def _update_title(self):
        if (pyxel.btnp(pyxel.KEY_Z)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_SPACE)):
            play_sfx(SFX_MENU_CONFIRM)
            self.state = "stage_select"

    def _draw_title(self):
        # Title
        pyxel.text(SCREEN_WIDTH // 2 - 28, 60, "S P E E D N I K", 7)

        # Subtitle
        pyxel.text(SCREEN_WIDTH // 2 - 32, 80, "A Sonic 2 Homage", 11)

        # Flashing prompt
        if pyxel.frame_count % 60 < 40:
            pyxel.text(SCREEN_WIDTH // 2 - 24, 140, "PRESS  START", 11)

    # ------------------------------------------------------------------
    # STAGE SELECT
    # ------------------------------------------------------------------

    def _update_stage_select(self):
        if pyxel.btnp(pyxel.KEY_UP):
            if self.selected_stage == _DEV_PARK_STAGE:
                self.selected_stage = self.unlocked_stages
                play_sfx(SFX_MENU_SELECT)
            elif self.selected_stage > 1:
                self.selected_stage -= 1
                play_sfx(SFX_MENU_SELECT)
        elif pyxel.btnp(pyxel.KEY_DOWN):
            if self.selected_stage < self.unlocked_stages:
                self.selected_stage += 1
                play_sfx(SFX_MENU_SELECT)
            elif self.selected_stage == self.unlocked_stages and DEBUG:
                self.selected_stage = _DEV_PARK_STAGE
                play_sfx(SFX_MENU_SELECT)

        if pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_RETURN):
            play_sfx(SFX_MENU_CONFIRM)
            if self.selected_stage == _DEV_PARK_STAGE:
                self._init_dev_park()
                self.state = "dev_park"
            else:
                self._load_stage(self.selected_stage)
                self.state = "gameplay"

    def _draw_stage_select(self):
        pyxel.text(SCREEN_WIDTH // 2 - 28, 30, "SELECT  STAGE", 11)

        for i in range(1, _NUM_STAGES + 1):
            y = 60 + (i - 1) * 24
            name = _STAGE_NAMES[i]
            if i <= self.unlocked_stages:
                color = 11 if i == self.selected_stage else 7
                prefix = "> " if i == self.selected_stage else "  "
            else:
                color = 12
                name = "???"
                prefix = "  "
            pyxel.text(60, y, f"{prefix}{i}. {name}", color)

        if DEBUG:
            y = 60 + _NUM_STAGES * 24
            selected = self.selected_stage == _DEV_PARK_STAGE
            color = 11 if selected else 7
            prefix = "> " if selected else "  "
            pyxel.text(60, y, f"{prefix}D. DEV PARK", color)

    # ------------------------------------------------------------------
    # DEV PARK
    # ------------------------------------------------------------------

    def _init_dev_park(self):
        from speednik import devpark
        devpark.init()

    def _update_dev_park(self):
        from speednik import devpark
        result = devpark.update()
        if result == "exit":
            self.selected_stage = 1
            self.state = "stage_select"

    def _draw_dev_park(self):
        from speednik import devpark
        devpark.draw()

    # ------------------------------------------------------------------
    # Stage loading
    # ------------------------------------------------------------------

    def _load_stage(self, stage_num: int):
        stage_name = _STAGE_LOADER_NAMES[stage_num]
        stage = load_stage(stage_name)

        self.active_stage = stage_num
        self.tiles_dict = stage.tiles_dict
        self.tile_lookup = stage.tile_lookup

        # Player
        sx, sy = stage.player_start
        self.player = create_player(float(sx), float(sy))
        self.player.lives = self.lives

        # Camera
        self.camera = create_camera(
            stage.level_width, stage.level_height, float(sx), float(sy)
        )

        # Objects
        self.rings = load_rings(stage.entities)
        self.springs = load_springs(stage.entities)
        self.checkpoints = load_checkpoints(stage.entities)
        self.pipes = load_pipes(stage.entities)
        self.liquid_zones = load_liquid_zones(stage.entities)
        self.enemies = load_enemies(stage.entities)

        # Goal
        self.goal_x = 0.0
        self.goal_y = 0.0
        for e in stage.entities:
            if e.get("type") == "goal":
                self.goal_x = float(e["x"])
                self.goal_y = float(e["y"])
                break

        # Stage 3: inject boss
        if stage_num == 3:
            boss_entities = [
                {"type": "enemy_egg_piston", "x": BOSS_SPAWN_X, "y": BOSS_SPAWN_Y}
            ]
            self.enemies.extend(load_enemies(boss_entities))

        # Reset state
        self.timer_frames = 0
        self.death_timer = 0
        self.boss_music_started = False
        self.boss_defeated = False
        renderer.clear_particles()
        renderer.set_stage_palette(_STAGE_PALETTE[stage_num])
        stop_music()
        play_music(_STAGE_MUSIC[stage_num])

    # ------------------------------------------------------------------
    # GAMEPLAY
    # ------------------------------------------------------------------

    def _update_gameplay(self):
        # --- Death handling ---
        if self.player.state == PlayerState.DEAD:
            self.death_timer += 1
            if self.death_timer >= DEATH_DELAY_FRAMES:
                if self.lives > 1:
                    self.lives -= 1
                    self._respawn_player()
                else:
                    self.lives = 0
                    stop_music()
                    play_music(MUSIC_GAMEOVER)
                    self.gameover_timer = GAMEOVER_DELAY
                    self.state = "game_over"
            return

        # --- Normal gameplay frame ---
        inp = _read_input()
        player_update(self.player, inp, self.tile_lookup)
        self.timer_frames += 1

        # Ring collection
        ring_events = check_ring_collection(self.player, self.rings)
        for event in ring_events:
            if event == RingEvent.COLLECTED:
                play_sfx(SFX_RING)
            elif event == RingEvent.EXTRA_LIFE:
                play_sfx(SFX_1UP)
                self.lives += 1

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
        update_pipe_travel(self.player, self.pipes)

        # Liquid zones
        liquid_events = update_liquid_zones(self.player, self.liquid_zones)
        for event in liquid_events:
            if event == LiquidEvent.STARTED_RISING:
                play_sfx(SFX_LIQUID_RISING)

        # Enemy update and collision
        update_enemies(self.enemies)
        enemy_events = check_enemy_collision(self.player, self.enemies)
        for event in enemy_events:
            if event == EnemyEvent.DESTROYED:
                play_sfx(SFX_ENEMY_DESTROY)
                for enemy in self.enemies:
                    if not enemy.alive:
                        renderer.spawn_destroy_particles(enemy.x, enemy.y)
            elif event == EnemyEvent.BOUNCE:
                play_sfx(SFX_ENEMY_BOUNCE)
            elif event == EnemyEvent.PLAYER_DAMAGED:
                play_sfx(SFX_HURT)
                if self.player.state == PlayerState.DEAD:
                    self.death_timer = 0
            elif event == EnemyEvent.SHIELD_BREAK:
                play_sfx(SFX_BOSS_HIT)
            elif event == EnemyEvent.BOSS_HIT:
                play_sfx(SFX_BOSS_HIT)
            elif event == EnemyEvent.BOSS_DEFEATED:
                play_sfx(SFX_STAGE_CLEAR)
                self.boss_defeated = True

        # Spring cooldowns
        update_spring_cooldowns(self.springs)

        # Boss music trigger (Stage 3)
        if (self.active_stage == 3
                and not self.boss_music_started
                and not self.boss_defeated
                and self.player.physics.x >= BOSS_ARENA_START_X):
            self.boss_music_started = True
            stop_music()
            play_music(MUSIC_BOSS)

        # Goal collision
        goal = check_goal_collision(self.player, self.goal_x, self.goal_y)
        if goal == GoalEvent.REACHED:
            stop_music()
            play_music(MUSIC_CLEAR)
            self.results_timer = RESULTS_DURATION
            self.state = "results"
            return

        # Sync lives between player and app
        self.lives = self.player.lives

        # Camera
        camera_update(self.camera, self.player, inp)

    def _draw_gameplay(self):
        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        pyxel.camera(cam_x, cam_y)

        renderer.draw_terrain(self.tiles_dict, cam_x, cam_y)

        # Rings
        for ring in self.rings:
            if not ring.collected:
                renderer._draw_ring(int(ring.x), int(ring.y), pyxel.frame_count)

        # Springs
        for spring in self.springs:
            sx = int(spring.x - SPRING_HITBOX_W // 2)
            sy = int(spring.y - SPRING_HITBOX_H // 2)
            color = 8
            if spring.cooldown > 0:
                pyxel.rect(sx, sy + SPRING_HITBOX_H // 2, SPRING_HITBOX_W, SPRING_HITBOX_H // 2, color)
            else:
                pyxel.rect(sx, sy, SPRING_HITBOX_W, SPRING_HITBOX_H, color)

        # Checkpoints
        for cp in self.checkpoints:
            color = 10 if cp.activated else 7
            cx = int(cp.x)
            cy = int(cp.y)
            pyxel.line(cx, cy, cx, cy - 24, color)
            pyxel.circ(cx, cy - 26, 3, color)

        # Pipes
        for pipe in self.pipes:
            px1 = int(min(pipe.x, pipe.exit_x))
            py1 = int(min(pipe.y, pipe.exit_y)) - 12
            px2 = int(max(pipe.x, pipe.exit_x))
            py2 = int(max(pipe.y, pipe.exit_y)) + 12
            pyxel.rectb(px1, py1, px2 - px1, py2 - py1, 5)

        # Liquid zones
        for zone in self.liquid_zones:
            if zone.active and zone.current_y < zone.floor_y:
                lx1 = int(zone.trigger_x)
                lx2 = int(zone.exit_x)
                ly = int(zone.current_y)
                lh = int(zone.floor_y - zone.current_y)
                for row in range(lh):
                    if (ly + row + pyxel.frame_count // 4) % 2 == 0:
                        pyxel.line(lx1, ly + row, lx2, ly + row, 10)

        # Goal post
        if self.goal_x > 0:
            renderer._draw_goal(int(self.goal_x), int(self.goal_y), pyxel.frame_count)

        # Boss targeting indicator
        for enemy in self.enemies:
            if (enemy.alive and enemy.enemy_type == "enemy_egg_piston"
                    and enemy.boss_state in ("idle", "descend")
                    and enemy.boss_timer <= 60):
                renderer.draw_boss_indicator(
                    int(enemy.boss_target_x),
                    int(enemy.boss_ground_y),
                    pyxel.frame_count,
                )

        # Enemies
        for enemy in self.enemies:
            if enemy.alive:
                drawer = renderer._ENTITY_DRAWERS.get(enemy.enemy_type)
                if drawer:
                    drawer(int(enemy.x), int(enemy.y), pyxel.frame_count)

        renderer.draw_player(self.player, pyxel.frame_count)
        renderer.draw_scattered_rings(
            self.player.scattered_rings, pyxel.frame_count
        )
        renderer.draw_particles(pyxel.frame_count)

        # HUD (screen space)
        pyxel.camera()
        renderer.draw_hud(self.player, self.timer_frames, pyxel.frame_count)
        if DEBUG:
            renderer.draw_debug_hud(self.player, self.timer_frames)

    # ------------------------------------------------------------------
    # Respawn
    # ------------------------------------------------------------------

    def _respawn_player(self):
        rx = self.player.respawn_x
        ry = self.player.respawn_y
        rr = self.player.respawn_rings

        self.player = create_player(rx, ry)
        self.player.lives = self.lives
        self.player.rings = rr
        self.player.respawn_x = rx
        self.player.respawn_y = ry
        self.player.respawn_rings = rr

        self.death_timer = 0

        # Reset camera to respawn position
        self.camera = create_camera(
            self.camera.level_width, self.camera.level_height, rx, ry
        )

    # ------------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------------

    def _update_results(self):
        self.results_timer -= 1
        if self.results_timer <= 0:
            # Unlock next stage
            if self.active_stage < _NUM_STAGES:
                self.unlocked_stages = max(
                    self.unlocked_stages, self.active_stage + 1
                )
            self.state = "stage_select"
            stop_music()
            play_music(MUSIC_TITLE)

    def _draw_results(self):
        name = _STAGE_NAMES.get(self.active_stage, "STAGE")
        pyxel.text(SCREEN_WIDTH // 2 - 30, 40, f"{name}", 7)
        pyxel.text(SCREEN_WIDTH // 2 - 28, 55, "S T A G E  C L E A R", 11)

        # Time
        total_seconds = self.timer_frames // 60
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        pyxel.text(80, 90, f"TIME:   {minutes}:{seconds:02d}", 11)

        # Rings
        rings = self.player.rings if self.player else 0
        pyxel.text(80, 106, f"RINGS:  {rings}", 7)

        # Score (time bonus + ring bonus)
        time_bonus = max(0, 600 - total_seconds) * 10
        ring_bonus = rings * 100
        pyxel.text(80, 122, f"TIME BONUS:  {time_bonus}", 11)
        pyxel.text(80, 138, f"RING BONUS:  {ring_bonus}", 11)
        pyxel.text(80, 158, f"TOTAL: {time_bonus + ring_bonus}", 7)

    # ------------------------------------------------------------------
    # GAME OVER
    # ------------------------------------------------------------------

    def _update_game_over(self):
        self.gameover_timer -= 1
        if self.gameover_timer <= 0:
            self.lives = 3
            self.state = "title"
            stop_music()
            play_music(MUSIC_TITLE)

    def _draw_game_over(self):
        pyxel.text(SCREEN_WIDTH // 2 - 24, SCREEN_HEIGHT // 2 - 8, "GAME  OVER", 8)

        if self.gameover_timer < GAMEOVER_DELAY - 120:
            if pyxel.frame_count % 60 < 40:
                pyxel.text(SCREEN_WIDTH // 2 - 28, SCREEN_HEIGHT // 2 + 16, "PRESS  START", 11)


if __name__ == "__main__":
    App()
