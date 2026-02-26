# T-013-05 Design: Loop and Slope Surface Adhesion

## Problem Recap

The engine unconditionally detaches the player when floor sensors can't find ground
within snap distance. The original Sonic 2 uses speed-based adhesion: high-speed players
stay attached through steep angles. Three fixes needed:

1. Speed-based adhesion to prevent detachment at high speeds on loops/steep surfaces
2. Slip-only detachment on steep slopes (not sensor-gap detachment)
3. Large loop exit handled by fixing traversal (Bug 2 is a consequence of Bug 1)

## Option A: Speed-Based Adhesion Guard in resolve_collision

Add a speed check before the detachment branch in `resolve_collision`. When on_ground
and floor sensor fails, check if `abs(ground_speed) >= FALL_SPEED_THRESHOLD` (2.5).
If speed is high enough, DON'T detach — instead, keep the player grounded and trust
that the next frame's sensor will find the surface.

**Pros**: Matches original Sonic 2 behavior exactly. Simple, localized change.
One `if` guard in the detachment path.

**Cons**: If the sensor genuinely can't find the floor (e.g., player ran off a cliff
at high speed), the player will float for one frame. Need an angle gate: only apply
adhesion when angle is in the steep range (quadrants 1-3).

## Option B: Increase Snap Distance at High Speeds

Scale `_GROUND_SNAP_DISTANCE` with speed: `min(abs(ground_speed) + 4, 14)` per SPG.
This gives sensors more reach when moving fast, reducing detachment at quadrant
transitions.

**Pros**: Also matches SPG. Addresses the sensor gap issue directly.

**Cons**: A larger snap distance can cause false landings on nearby surfaces. Also
doesn't fully solve the Q1→Q2 transition because the issue isn't snap distance — it's
that the sensor direction changes and may need to look in a completely different place.
Alone, this is insufficient.

## Option C: Retain Angle on Detachment + Immediate Re-Check

When the floor sensor fails, instead of immediately detaching, retain the current angle
and re-run the floor sensor with a slightly expanded search. If the surface is nearby
(within speed-scaled range), snap to it.

**Pros**: Could handle quadrant transitions more smoothly.

**Cons**: Complex, fragile, could cause oscillation. Not how original Sonic works.

## Decision: Option A (with angle gate)

Option A is the correct approach because it matches the original Sonic 2 specification:

> The player falls off when `abs(ground_speed) < 2.5` AND angle is in 46°-315°.
> At speeds ≥ 2.5, the player stays attached.

Implementation:

In `resolve_collision`, when `on_ground=True` and floor sensor fails:
1. Check if `abs(ground_speed) >= 2.5`
2. Check if angle is in the "steep" range (byte angles 33-223, i.e., quadrants 1-3)
3. If BOTH conditions met → **don't detach**, keep on_ground, preserve angle
4. If speed is below threshold OR angle is flat → detach normally

This means at spindash speed (8.0), the player stays attached through the entire loop
regardless of momentary sensor gaps at quadrant transitions. The slope factor and
friction naturally slow the player; when speed drops below 2.5 on a steep angle, the
existing slip system triggers and handles the detachment correctly.

### Slope Adhesion Fix (Bug 3)

The slope adhesion fix comes for free with Option A. Currently, the slip system causes
oscillating detach/reattach cycles. With the adhesion guard:

1. Player on steep slope, speed decays below 2.5
2. Slip activates (correct) — input locked
3. Speed continues to decay — angle is steep, speed < 2.5
4. **Fall condition**: `abs(ground_speed) < 2.5 AND angle in steep range`
5. Player detaches (correct behavior per Sonic 2 spec)

The key difference: with the adhesion guard, the player stays grounded as long as
speed ≥ 2.5, even on steep slopes. The oscillation only happens when speed drops
below the threshold, which is the correct Sonic 2 behavior. Players holding right
on a steep slope maintain enough speed through input acceleration to stay above 2.5.

### What About the Slip System?

The slip system currently triggers at SLIP_ANGLE_THRESHOLD=33 (~46°). With the
adhesion guard, the slip system only matters when speed is already below 2.5. The
slip timer (30 frames) and input lock are correct per Sonic 2. No changes needed
to the slip system itself.

### Detachment Logic Summary

After the fix, the detachment decision tree:

```
on_ground AND floor_sensor_fails:
  IF abs(ground_speed) >= 2.5 AND angle_in_steep_range:
    → STAY ATTACHED (speed-based adhesion)
  ELSE:
    → DETACH (original behavior)
```

The steep range check (quadrants 1-3) ensures that running off a flat cliff at
high speed still causes normal detachment. Only curved/steep surfaces get the
adhesion benefit.

## Rejected Approaches

- **Option B alone**: Insufficient for Q1→Q2 transition. The sensor direction
  completely changes; no amount of snap distance fixes finding a surface in the
  wrong direction.

- **Option C**: Over-engineered. The original Sonic 2 doesn't do retry logic —
  it simply doesn't detach at high speed.

- **Centripetal force simulation**: Some fan engines add a centripetal force term.
  Not necessary — the original Sonic 2 doesn't use this. Speed-based adhesion
  is sufficient.

- **Loop-specific lock**: Some implementations force `on_ground=True` for all
  SURFACE_LOOP tiles. This is fragile and doesn't fix the general slope case.

## New Constant

```python
FALL_SPEED_THRESHOLD = 2.5  # Min speed to stay attached on steep surfaces
```

This is the same value as `SLIP_SPEED_THRESHOLD`. In the original Sonic 2, these
are the same value. Keep them as separate constants for clarity (slip vs fall are
different mechanics that happen to share the threshold).

## Test Impact

- Loop traversal tests (TestLoopEntry): Should now pass for all radii
- Slope adhesion tests (TestSlopeAdhesion): Should now pass for angles 35-45
- Hillside loop tests: xfail markers should be removable
- Existing flat/ramp/gap/spring tests: Unaffected (angle is in Q0, adhesion guard
  doesn't activate)
