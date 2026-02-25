# Design — T-010-01: SimState and create_sim

## Decision 1: Event type representation

### Option A: New dataclass events (per ticket)

Define new `@dataclass` event types (`RingCollectedEvent`, `DamageEvent`, etc.) with a union type.
These are distinct from existing `RingEvent`, `SpringEvent`, etc. enums.

**Pros**: Clean separation; dataclass events can carry payload later (e.g., `RingCollectedEvent(x, y)`).
**Cons**: Dual event systems; `sim_step` (T-010-02) would need to map existing enum events → new dataclass events.

### Option B: Reuse existing enum events

`sim_step` directly returns `list[RingEvent | SpringEvent | GoalEvent | ...]`.
The spec's `sim_step` example already uses `RingEvent.COLLECTED`, `GoalEvent.REACHED`.

**Pros**: Zero duplication; existing events are already Pyxel-free.
**Cons**: No payload. But payloads aren't needed for T-010-01 scope.

### Option C: Define dataclass events but make them thin wrappers (hybrid)

Define the dataclass events as specified in the ticket. T-010-02 will decide mapping strategy.
This lets us follow the ticket spec now and defer the integration decision.

**Decision**: **Option C**. The ticket explicitly lists the dataclass event types as acceptance criteria.
Define them exactly as specified. They cost nearly nothing and give T-010-02 a clean interface.
The existing enum events continue to be used internally by `objects.py`/`enemies.py`.

## Decision 2: Boss injection trigger

### Option A: Name matching

`if stage_name == "skybridge": inject boss`. Simple string comparison.

### Option B: Accept optional stage_num parameter

`create_sim(stage_name, stage_num=None)`. Boss injected when `stage_num == 3`.

### Option C: Maintain a name → stage_num mapping

Mirror `_STAGE_LOADER_NAMES` from `main.py` in reverse.

**Decision**: **Option A**. The API is `create_sim(stage_name: str)`. The stage name → boss
mapping is a fixed property of the game design. Direct name check is the simplest and
avoids introducing coupling to `main.py`'s stage numbering. If more stages are added, this
mapping will need updating regardless of approach.

## Decision 3: SimState field set

The ticket and spec define identical fields. Review against `main.py:App` state:

| App field | SimState equivalent | Include? |
|-----------|-------------------|----------|
| `player` | `player: Player` | Yes |
| `tile_lookup` | `tile_lookup: TileLookup` | Yes |
| `tiles_dict` | — | No (rendering only) |
| `rings` | `rings: list[Ring]` | Yes |
| `springs` | `springs: list[Spring]` | Yes |
| `checkpoints` | `checkpoints: list[Checkpoint]` | Yes |
| `pipes` | `pipes: list[LaunchPipe]` | Yes |
| `liquid_zones` | `liquid_zones: list[LiquidZone]` | Yes |
| `enemies` | `enemies: list[Enemy]` | Yes |
| `goal_x`, `goal_y` | `goal_x: float`, `goal_y: float` | Yes |
| `active_stage` | — | No (UI state) |
| `timer_frames` | `frame: int` | Yes (renamed) |
| `camera` | — | No (rendering only) |
| `lives` | — | No (lives tracked on Player) |
| `death_timer` | — | No (respawn is UI-level) |
| `boss_music_started` | — | No (audio state) |
| `boss_defeated` | — | No (derived from enemy alive state) |
| — | `level_width`, `level_height` | Yes (for observation normalization) |
| — | `max_x_reached: float` | Yes (metric) |
| — | `rings_collected: int` | Yes (metric) |
| — | `deaths: int` | Yes (metric) |
| — | `goal_reached: bool` | Yes (terminal flag) |
| — | `player_dead: bool` | Yes (terminal flag) |

This matches the ticket spec exactly. No fields to add or remove.

## Decision 4: Default goal position when no goal entity exists

Current `main.py` initializes `goal_x = 0.0, goal_y = 0.0` and overwrites if goal found.
All three stages have goal entities. But robustness matters.

**Decision**: Match `main.py` behavior — default to `(0.0, 0.0)`. A stage without a goal
entity simply means the goal can never be reached (distance from player to (0,0) will
exceed `GOAL_ACTIVATION_RADIUS` unless player is at origin, which is off-map).

## Decision 5: Test strategy

Tests go in a new file `tests/test_simulation.py`.

Core test cases:
1. `create_sim("hillside")` succeeds and populates all fields.
2. `create_sim("pipeworks")` and `create_sim("skybridge")` succeed.
3. Goal position matches known values from entity data.
4. Stage 3 (skybridge) has boss enemy in enemy list.
5. Entity lists are non-empty where expected (hillside has rings, springs, enemies).
6. Event types are importable and instantiable.
7. `simulation.py` does not import Pyxel.

## Rejected alternatives

- **Putting SimState in `level.py`**: SimState is simulation-layer, not loading-layer. Keeps boundaries clean.
- **Making create_sim load from stage_num**: Ticket API says `stage_name: str`. Converting to numbers adds coupling.
- **Omitting event types from this ticket**: Ticket AC explicitly requires them.
- **Making SimState frozen**: It's mutated by `sim_step` (T-010-02). Must be mutable.
