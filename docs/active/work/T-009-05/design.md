# Design — T-009-05 boundary-escape-detection

## Decision 1: Test Structure

### Options

**A. One test class per stage (TestHillsideBoundary, etc.)**
Follows existing test_levels.py pattern. 3 classes × 4 edge tests = 12 tests.
Verbose but clear. Allows per-stage xfail reasons.

**B. Parametrized test across all stages**
`@pytest.mark.parametrize("stage_name", ["hillside", "pipeworks", "skybridge"])`
with strategy × edge combinations. Compact, DRY.

**C. Single TestBoundaryEscape class with per-direction methods**
One class, methods like `test_right_edge`, `test_left_edge`, `test_bottom_edge`.
Each method iterates stages internally.

**Decision: C — Single TestBoundaryEscape class.**
Rationale: The ticket groups tests by escape direction, not by stage. A single
class with directional methods reads naturally and matches the ticket structure.
Each method iterates all three stages and all relevant strategies. The xfail
decorator goes on the class or individual methods. Error messages include
stage name + strategy name + frame + position as ticket requires.

### Options for xfail placement

**A. Mark entire class xfail** — all boundary tests expected to fail
**B. Mark individual methods xfail** — granular control

**Decision: B — Individual method xfail.**
Rationale: Some directions may actually pass (e.g., top edge might never be
reachable). Per-method xfail with `strict=False` lets us capture which specific
vectors currently fail without masking accidental passes.

## Decision 2: hold_left Strategy

### Options

**A. Add hold_left to harness.py as a general strategy**
Alongside hold_right, hold_right_jump, etc. Reusable.

**B. Define hold_left inline in test file**
Keeps test self-contained but duplicates pattern.

**Decision: A — Add to harness.py.**
Rationale: It's the mirror of hold_right, fits the strategy factory pattern,
and will be needed by devpark too. Avoids duplication.

## Decision 3: Boundary Line Rendering

### Options

**A. New function in renderer.py: `draw_level_bounds()`**
Reusable by both devpark and main game (when DEBUG active).
Takes level_width, level_height, camera_x, camera_y.

**B. Inline in devpark.py only**
Simpler, no cross-module dependency.

**C. In devpark.py with a helper, extend to renderer.py later**
Ship it in devpark first, move if DEBUG rendering is requested.

**Decision: A — New function in renderer.py.**
Rationale: The ticket explicitly says "when in dev park or when DEBUG is active"
— both need the same rendering. A renderer.py function is the natural home and
keeps devpark.py focused on bot orchestration. Uses pyxel.line() in world space
with camera offset, matching existing terrain rendering pattern. Color: slot 8
(red, 0xE02020) which is bright against all stage palettes.

## Decision 4: Dev Park Stage Design

### Options

**A. One stage with hold_right + hold_left on hillside only**
Simple, demonstrates the bug.

**B. One stage per real stage (3 stages)**
Thorough but clutters the dev park menu.

**C. One BOUNDARY PATROL stage that cycles through all real stages**
Z key cycles stage (like GAP JUMP cycles gap width). Each stage runs
hold_right and hold_left bots simultaneously.

**Decision: C — Single stage with Z-to-cycle.**
Rationale: Matches the GAP JUMP pattern (Z cycles variants). Shows all stages
in one menu entry. Two bots visible: hold_right approaching right edge and
hold_left approaching left edge. Z cycles through hillside → pipeworks →
skybridge. Readout shows stage name, bot positions, and whether they've
escaped bounds.

## Decision 5: Camera Behavior for Escape Visualization

### Options

**A. Use existing camera clamping (camera stops at edge, player disappears)**
Shows the problem as-is — player vanishes while camera stays.

**B. Disable camera clamping in boundary patrol**
Camera follows player past the edge, showing them in void.

**C. Use two cameras — one for hold_right bot, one for hold_left bot,
quad-split view**
Full visibility for both edges simultaneously.

**Decision: A — Use existing camera.**
Rationale: The point is to visualize the *problem*, and the problem IS that the
camera stops while the player keeps going. The boundary lines rendered at the
edges make the escape visible even after the player leaves view (the red line
is the last thing visible as the bot approaches the edge). The readout HUD
shows bot X/Y so escape is numerically tracked even when visually lost.

## Summary

| Decision | Choice | Key Rationale |
|----------|--------|--------------|
| Test structure | Single TestBoundaryEscape class | Matches ticket's directional grouping |
| xfail | Per-method | Granular, allows partial pass |
| hold_left | In harness.py | Reusable, mirrors hold_right pattern |
| Boundary rendering | renderer.py function | Shared by devpark + DEBUG mode |
| Dev park stage | One stage, Z-cycles stages | Matches GAP JUMP pattern |
| Camera | Existing clamped camera | Shows the actual problem |
