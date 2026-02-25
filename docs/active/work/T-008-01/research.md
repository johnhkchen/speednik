# Research — T-008-01: scenario-runner-and-strategies

## Relevant Modules & Key Types

### Player system (`speednik/player.py`)
- `Player` dataclass: top-level game object. Contains nested `PhysicsState`, plus
  `state: PlayerState`, rings, lives, invulnerability, animation, scattered rings,
  pipe/respawn state, and `_prev_jump_held` for release detection.
- `PlayerState` enum: STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD.
- `create_player(x, y) -> Player`: factory. Sets `on_ground=True`, stores respawn pos.
- `player_update(player, inp, tile_lookup) -> None`: the single per-frame entry point.
  Mutates player in place. Sequence: early-exit for DEAD/pipe → `_pre_physics` (state
  transitions) → physics steps 1-4 (skip input if HURT) → `resolve_collision` →
  slip timer → `_post_physics` (state sync) → subsystems (invulnerability, scattered
  rings, ring collection, animation) → track `_prev_jump_held`.

### Physics engine (`speednik/physics.py`)
- `InputState` dataclass: `left`, `right`, `jump_pressed`, `jump_held`, `down_held`,
  `up_held`. All bool, all default False. Fully Pyxel-free.
- `PhysicsState` dataclass: `x`, `y`, `x_vel`, `y_vel`, `ground_speed`, `angle` (byte
  0-255), `on_ground`, `is_rolling`, `facing_right`, `spinrev`, `is_charging_spindash`,
  `slip_timer`.
- Spindash mechanics: enter via `down_held` when standing/slow → SPINDASH state. Charge
  with `jump_pressed` while `down_held` (increments `spinrev` by 2.0, cap 8.0). Decay
  per frame while holding. Release on `down_held=False` → converts to ROLLING with
  `ground_speed = SPINDASH_BASE_SPEED(8) + floor(spinrev/2)`. Max possible speed: 12.
- Jump mechanics: `jump_pressed` on ground → `apply_jump` (angle-aware launch, clears
  `on_ground`). Variable height: releasing `jump_held` mid-air caps `y_vel` at -4.0.
  `_prev_jump_held` tracks previous frame for release detection.

### Terrain & collision (`speednik/terrain.py`)
- `TileLookup = Callable[[int, int], Optional[Tile]]` — grid coords → Tile or None.
- `Tile` dataclass: `height_array` (16 ints), `angle` (byte), `solidity` (0-3),
  `tile_type` (0=normal, 5=loop).
- `get_quadrant(angle) -> int`: maps byte angle to quadrant 0-3.
- `resolve_collision(state, tile_lookup)`: full collision resolution (floor/wall/ceiling).
- Constants: `TILE_SIZE=16`, `FULL=2`, `NOT_SOLID=0`, `TOP_ONLY=1`.

### Stage loading (`speednik/level.py`)
- `StageData` dataclass: `tile_lookup`, `tiles_dict`, `entities`, `player_start` (tuple
  x,y), `checkpoints`, `level_width`, `level_height`.
- `load_stage(stage_name) -> StageData`: loads from `speednik/stages/{name}/` JSON files.
  Valid names: "hillside", "pipeworks", "skybridge".
- No Pyxel dependency — pure file I/O + dict construction.

### Pyxel boundary
Only 3 files import pyxel: `main.py`, `renderer.py`, `audio.py`. All physics, player,
terrain, and level modules are Pyxel-free. The scenario runner can import freely from
`player`, `physics`, `terrain`, `level` without any pyxel dependency.

## Existing Test Patterns (`tests/test_player.py`)

- Helper: `flat_tile(angle=0, solidity=FULL)` → Tile with `[16]*16` height array.
- Helper: `make_tile_lookup(tiles_dict)` → closure-based TileLookup.
- Helper: `flat_ground_lookup()` → 30-tile flat ground at tile_y=12 (pixel y=192).
- Helper: `empty_lookup()` → no tiles.
- Player placed at y=172.0 (20px above tile top at y=192) for ground tests.
- Standard pattern: create player, build lookup, run `player_update` in a loop, assert.
- No conftest.py — all helpers are module-local.

## Access Patterns for FrameSnapshot Fields

The ticket's `FrameSnapshot` needs: `frame`, `x`, `y`, `x_vel`, `y_vel`,
`ground_speed`, `angle`, `on_ground`, `quadrant`, `state`.

| Field          | Source                                |
|----------------|---------------------------------------|
| frame          | loop counter                          |
| x              | `player.physics.x`                    |
| y              | `player.physics.y`                    |
| x_vel          | `player.physics.x_vel`                |
| y_vel          | `player.physics.y_vel`                |
| ground_speed   | `player.physics.ground_speed`         |
| angle          | `player.physics.angle`                |
| on_ground      | `player.physics.on_ground`            |
| quadrant       | `get_quadrant(player.physics.angle)`  |
| state          | `player.state.value` (string)         |

## Spindash Strategy Nuances

The `spindash_right` strategy must model: (1) crouch: set `down_held=True` while
standing still → enters SPINDASH; (2) charge: pulse `jump_pressed=True` with
`down_held=True` for N frames; (3) release: set `down_held=False` → converts to
ROLLING; (4) hold right while rolling; (5) detect speed drop → re-spindash.

Key constants: `MIN_ROLL_SPEED=0.5`, `SPINDASH_BASE_SPEED=8.0`,
`SPINDASH_CHARGE_INCREMENT=2.0`, `SPINDASH_MAX_CHARGE=8.0`.

State detection: `player.state == PlayerState.SPINDASH` during charge,
`player.state == PlayerState.ROLLING` after release, speed available via
`player.physics.ground_speed`.

## hold_right_jump Strategy Nuances

Must track whether player has landed to re-press jump. `jump_pressed` should be True
only on the first frame (and re-pressed after landing). Detection: when
`player.physics.on_ground` transitions from False→True, set `jump_pressed=True` on
the next input. Need internal state (closure or class) to track `was_airborne`.

## Constraints and Boundaries

- `tests/harness.py` is the target file — not a test file, just a module imported by
  tests. No `test_` prefix.
- The runner must not import pyxel.
- `run_on_stage` is a convenience helper that calls `load_stage` + `run_scenario`.
- `stuck_at` needs to detect when X position hasn't changed meaningfully over many
  frames — scan snapshots for extended periods where `max_x - min_x < tolerance`.
