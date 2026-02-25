# T-009-03 Design — Dev Park Stages

## Key Design Decisions

### 1. Grid Builder tiles_dict Access

**Problem**: Grid builders return `TileLookup` (a closure over a dict), but `make_bot`
needs the raw `tiles_dict` for rendering.

**Options**:
A. Modify grid builders to return `(tiles_dict, TileLookup)` tuples.
B. Add parallel `build_*_with_dict()` variants.
C. Add a wrapper in devpark.py that builds tiles_dict and wraps it.

**Decision**: Option A. Change return type of all builders to
`tuple[dict, TileLookup]`. This is the cleanest approach — callers that only need
`TileLookup` destructure `_, lookup = build_flat(...)`. The existing elemental tests
and test_grids need updating but it's a mechanical change. The alternative of duplicating
builders is worse long-term.

### 2. Dev Park State Machine Architecture

**Problem**: The dev park needs a sub-menu plus 5 individual stage screens, all within
the `"dev_park"` game state.

**Decision**: Internal sub-state within devpark.py. The main game state stays `"dev_park"`,
and devpark.py manages its own sub-states:

- `"menu"` — stage list with UP/DOWN/Z/X navigation
- `"running"` — active stage with bot(s) running

The App class delegates to devpark module functions:
```python
def _update_dev_park(self):
    devpark.update()
def _draw_dev_park(self):
    devpark.draw()
```

devpark.py holds module-level state for the current sub-state, selected index, active
bots, and frame counter. This keeps all dev park logic contained in one module.

### 3. Stage Definition Pattern

**Decision**: Each elemental stage is defined as a dataclass or dict containing:
- `name: str` — display name
- `init: Callable` — creates bots and returns them
- `readout: Callable` — draws scenario-specific HUD text

A list of stage definitions drives both the menu and the runtime. The init function
returns a list of `LiveBot`s. The readout function receives the bot list and draws
scenario text (angle, speed, position).

### 4. SPEED GATE — Two Bots on Same Grid

**Problem**: Need walk vs spindash comparison. Options: split screen or Y-stagger.

**Decision**: Y-stagger. Build two copies of the same ramp grid at different Y offsets
(e.g., 64px apart). Each bot gets its own Y start. Camera follows a virtual midpoint
between the two bots. This is simpler than split-screen rendering and shows both bots
in the same viewport.

Actually, simpler: build a single grid, spawn both bots at the same start. They share
tiles_dict and tile_lookup. Camera follows the lead bot (or the first bot). The second
bot will stall behind. This works because both bots have independent Player objects.

### 5. LOOP LAB — Sequential Scenarios

**Problem**: Show loop-with-ramps (success) and loop-without-ramps (failure).

**Decision**: Run one scenario at a time. Start with loop+ramps. When the bot finishes
(max_frames or goal_x), show result text, then auto-switch to loop-without-ramps after
a brief pause. Or: let the user press Z to toggle between scenarios. Simpler: just show
"phase 1" and "phase 2" labels and auto-advance.

Simplest: two bots on the same screen with different grid data. But LiveBot.draw()
renders its own tiles_dict, so two bots with different tile data would overdraw each
other. Sequential is cleaner.

**Final decision**: Single scenario at a time with Z to cycle. Label shows which variant.

### 6. Palette

**Decision**: Monochrome green-on-black. Override slots:
- 0: 0x000000 (black background)
- 1: 0x003300 (dark green terrain fill)
- 2: 0x00AA00 (mid green surface line)
- 3: 0x00FF00 (bright green highlight)
- 4: 0x00CC00 (player body — green)
- 11: 0x00FF00 (UI text — bright green)

Add `"devpark"` to `STAGE_PALETTES` dict.

### 7. Camera Following

**Decision**: Use the first bot's camera for the viewport. In multi-bot scenarios,
only the primary bot's camera tracks. The secondary bot may scroll off screen if it
falls behind — that's acceptable and even desirable (shows the contrast).

### 8. Exit and Summary

**Decision**: X key returns to dev park menu from any stage. When a bot finishes, show
a summary line at the bottom: "STALLED AT X=1234" or "COMPLETED IN 456 FRAMES". The
stage keeps running (drawing the frozen bot) until X is pressed.

### 9. Test Strategy

Tests for dev park stages must work without Pyxel. Test that:
- Menu navigation works (state transitions)
- Stage init creates correct bots
- Bot update/completion works
- No Pyxel imports at test time (all drawing is skipped)

Since the draw path uses pyxel.* calls, tests only verify the data/logic layer.

## Rejected Approaches

- **Split-screen rendering**: Too complex for SPEED GATE. Would require two camera
  passes and viewport clipping. Y-stagger or same-start achieves the comparison with
  simpler code.
- **Extracting strategies to a shared module**: The ticket doesn't require it, and the
  current import-from-tests pattern works fine for DEBUG-only code.
- **Building a generic "scenario runner" framework**: Over-engineering. Each stage has
  unique init logic; a shared framework adds abstraction without simplifying much.
