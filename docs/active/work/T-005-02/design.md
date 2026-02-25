# Design: T-005-02 hillside-loop-collision-fix

## Problem

Loop circle cy=380 places loop bottom at y=508. Ground level is y=636. The 128px
gap is currently filled by a rectangular ground polygon and sloping approach/exit
polygons, but this makes the loop unreachable (player walks over the gap fill instead
of entering the loop).

## Approach A: Move circle center down (chosen)

Change `cy="380"` to `cy="508"`. This places:
- Loop bottom: y = 508 + 128 = 636 (ground level)
- Loop top: y = 508 − 128 = 380
- Left/right edges unchanged: x = 3472, x = 3728

**Advantages:**
- Loop bottom aligns with ground level — player runs straight into it
- No gap fill needed; the ground-beneath-loop polygon is deleted
- Approach and exit polygons simplify to flat ground at y=636
- The loop top stays at y=380 (same as current), so the visible loop arc is the
  same height, just shifted so the bottom meets the ground

**Disadvantages:**
- Ring positions (ring_131–150) must all shift down by 128px
- Approach rings (ring_151–155) change from sloped to flat
- Tests hardcode the old loop center; need updates

## Approach B: Raise the ground to meet the loop

Keep the circle where it is and raise the ground level to y=508 in the loop zone.

**Rejected because:**
- Creates a 128px step-up before the loop, which is worse for gameplay
- Contradicts the ticket's explicit direction
- Would require more complex approach/exit polygons with steep slopes

## Approach C: Increase loop radius

Keep cy=380 but increase radius to 256 so the bottom reaches y=636.

**Rejected because:**
- A 256-radius loop would extend from y=124 to y=636 — far too tall
- Would extend horizontally from x=3344 to x=3856, overlapping adjacent sections
- Changes the intended loop design dramatically

## Chosen Approach: A — Move circle center down

### SVG Changes

1. **Circle element** (line 233): `cy="380"` → `cy="508"`
2. **Delete ground-beneath-loop polygon** (lines 241–244): no longer needed
3. **Flatten approach polygon** (lines 227–230): all points at y=636, connecting
   left edge at x=3200 to loop entry at x=3472
4. **Flatten exit polygon** (lines 236–239): all points at y=636, connecting
   loop exit at x=3728 to right edge at x=4000
5. **Shift loop rings +128 in Y** (lines 247–266): ring_131–ring_150, each cy += 128
6. **Flatten approach rings** (lines 268–272): ring_151–155, adjust Y to ~622
   (near ground level, since approach is now flat)

### Ring Adjustment Detail

Loop rings are arranged in a circle around center (3600, 380). Shifting the center
to (3600, 508) means adding 128 to each ring's cy. This preserves the circular
pattern relative to the new loop center.

Approach rings currently slope from 622 to 540. With a flat approach at y=636,
these should sit slightly above ground, e.g., at y=622 uniformly (or removed, but
keeping them for gameplay value makes sense). Since the approach is now flat, we
can place them at consistent height above ground: y ≈ 620–622.

### Test Changes

`TestLoopGeometry` scans ty=15–32 (y=240–512). After the fix, the loop spans
y=380–636, which is ty=23–39. The scan range needs updating:
- ty range: 23 to 40 (y=368 to y=640)
- tx range: 218 to 234 (unchanged, loop X is the same)

The docstring referencing "Loop center at (3600, 380)" needs updating to (3600, 508).

### Pipeline

After SVG edits, regenerate stage data:
```
uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/
```

Verify `validation_report.txt` for improvement — the 12px gaps at y=496 and the
angle inconsistencies at rows 30–31 should disappear since the ground-fill rectangle
and sloped approach are eliminated.

## Risk Assessment

- **Low risk**: changes are confined to one SVG section and its generated output
- **No code changes**: `svg2stage.py` and game engine are untouched
- **Mechanical ring shifts**: each ring gets +128 to cy, straightforward
- **Test updates**: ranges shift by predictable offset, easy to verify
