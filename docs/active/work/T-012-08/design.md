# Design: T-012-08 — loop-traversal-audit

## Decision: Test Architecture

### Option A: Extend existing test_mechanic_probes.py

Add grounded-quadrant assertions to existing `TestLoopEntry` in mechanic probes.

**Rejected**: Ticket explicitly specifies `tests/test_loop_audit.py` as the target
file. Mixing audit tests with mechanic probes conflates "does the mechanic work?"
(probes) with "does the loop work end-to-end?" (audit). The probe tests check
individual mechanics; the audit tests check the full loop experience including
diagnostics.

### Option B: Extend test_geometry_probes.py

Add grounded-quadrant tests to the geometry probes alongside hillside tests.

**Rejected**: Geometry probes test real stage geometry. The audit covers both
synthetic and real stages. Also, test_geometry_probes.py has a pre-existing
`pytest` import bug making it uncollectable.

### Option C: New `tests/test_loop_audit.py` (chosen)

New file with both synthetic and real-stage loop audit tests. Self-contained,
with its own runner infrastructure, diagnostic formatting, and bug ticket xfails.

**Rationale**: Matches ticket specification exactly. Clean separation of concerns.
Audit tests are QA artifacts — they describe what SHOULD work and document WHY
it doesn't when it fails.

## Decision: Runner Infrastructure

### Option A: Use `strategies.py` `run_scenario()` for everything

**Rejected**: `run_scenario()` uses `player_update()` directly, which skips
entity processing. Hillside tests need `sim_step()` for full fidelity (springs,
rings, etc. near the loop could affect behavior).

### Option B: Use `simulation.py` `sim_step()` for everything (chosen)

Use `create_sim_from_lookup()` for synthetic tests and `create_sim("hillside")`
for real-stage tests. Both go through `sim_step()`. Consistent code path.

**Rationale**: The mechanic probes already use this pattern. `sim_step()` is
the canonical simulation function. Using the same path for both synthetic and
real-stage tests means any bug we find in the audit is representative of actual
gameplay.

### Option C: Write a new runner just for the audit

**Rejected**: Over-engineered. The existing `sim_step()` path works fine.

## Decision: Test Parameterization

### Radius sweep

Test radii: 32, 48, 64, 96 (as specified in ticket).

Expected results from research:
- r=32: FAIL (grounded {0,1}). xfail: tile resolution too coarse.
- r=48: PASS (grounded {0,1,2,3}).
- r=64: PASS for traversal, FAIL for exit (BUG-02).
- r=96: PASS for traversal, FAIL for exit (BUG-02).

### Speed sweep

Test speeds: 4.0 to 12.0 in steps of 1.0 (as specified in ticket).

From research, only narrow speed windows work for r=48. We'll test with
spindash strategy (not direct speed injection) because the ticket says
"spindash speed" is the reference. For the speed sweep, we'll directly set
`ground_speed` and `x_vel` to test the minimum traversal speed.

### Hillside real-stage test

Single test: spindash from x=3100, y=610 through the hillside loop.
Expected: FAIL (grounded {0,1}, stuck in Q1). xfail with bug reference.

## Decision: Diagnostic Output

The ticket requests rich diagnostic output when tests fail. Approach:

1. Build a `format_loop_diagnostic()` function that takes the frame snapshots,
   loop region bounds, and test parameters, and returns a multi-line string.

2. Include in assertion messages via `pytest.fail()` or assertion message strings.

3. Diagnostic includes:
   - Grounded vs all quadrants
   - Per-frame trajectory through loop region
   - Frame where ground contact was lost (if applicable)
   - Entry speed at loop entry
   - Probable cause heuristics

## Decision: Bug Ticket Filing

Based on research findings:

### T-012-08-BUG-01: Hillside loop not traversable

The hand-placed hillside loop geometry traps the player in Q1 oscillation.
The player enters the loop ramp, reaches Q1 angles, but bounces between
tiles around x=3445–3449 with decaying speed. Never reaches Q2.

Root cause: hillside loop tile angles and height arrays don't produce smooth
enough transitions for the sensor system to advance through the loop. Unlike
the synthetic `build_loop()` which uses angular sampling, the hillside tiles
are hand-placed with potentially non-smooth angle progressions.

### Speed sensitivity (documented, not a separate bug)

The narrow speed windows for loop traversal are a physics engine characteristic,
not a bug per se. The engine doesn't have centripetal force — it relies on
sensor snapping. If the player moves too fast, they overshoot the sensor snap
distance; too slow, gravity pulls them off. This is documented in the test
file as a known limitation.

## Decision: xfail Strategy

- r=32 synthetic: xfail with reason "tile resolution too coarse" (BUG-01 from
  T-012-06-BUG-01, already documented)
- r=64/96 exit tests: xfail with reason "BUG-02" (T-012-06-BUG-02)
- Hillside loop: xfail with reason from T-012-08-BUG-01
- Speed sweep failures: document as expected behavior (not xfail — just
  parametrize and let the test show which speeds work)
