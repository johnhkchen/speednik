# Plan: T-005-02 hillside-loop-collision-fix

## Step 1: Edit SVG — fix loop circle center

File: `stages/hillside_rush.svg`, line 233.

Change `cy="380"` to `cy="508"`. Update Section 5 comments (lines 222–223) to
reflect new geometry: center at (3600, 508), bottom at y=636, top at y=380.

**Verify**: grep for `cy="508"` in the circle element.

## Step 2: Edit SVG — flatten approach polygon

File: `stages/hillside_rush.svg`, lines 226–230.

Replace the sloping approach polygon with a flat rectangle:
```xml
<!-- Approach ground: flat at y=636 -->
<polygon points="
  3200,636 3472,636
  3472,720 3200,720
" stroke="#00AA00" fill="none"/>
```

**Verify**: no Y values between 508 and 635 in the approach polygon.

## Step 3: Edit SVG — flatten exit polygon

File: `stages/hillside_rush.svg`, lines 235–239.

Replace the sloping exit polygon with a flat rectangle:
```xml
<!-- Exit ground: flat at y=636 -->
<polygon points="
  3728,636 4000,636
  4000,720 3728,720
" stroke="#00AA00" fill="none"/>
```

**Verify**: no Y values between 508 and 635 in the exit polygon.

## Step 4: Edit SVG — delete ground-beneath-loop polygon

File: `stages/hillside_rush.svg`, lines 241–244.

Delete the 4 lines (comment + polygon element). This polygon was filling the gap
that no longer exists.

**Verify**: no polygon with points `3472,508 3728,508` remains in the file.

## Step 5: Edit SVG — shift loop ring positions

File: `stages/hillside_rush.svg`, lines 247–266.

For each of ring_131 through ring_150, add 128 to the `cy` attribute value.
This keeps the rings centered on the new loop center (3600, 508).

20 edits total. Each is a simple cy value replacement.

**Verify**: all 20 ring cy values are 128 higher than before.

## Step 6: Edit SVG — flatten approach ring positions

File: `stages/hillside_rush.svg`, lines 268–272.

Set all 5 approach rings (ring_151–155) to cy="622" since the approach is now flat.
ring_151 is already at 622; ring_152–155 need adjustment.

**Verify**: all 5 approach rings have cy="622".

## Step 7: Regenerate stage data

Run:
```
uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/
```

**Verify**:
- Command exits 0
- `speednik/stages/hillside/validation_report.txt` has fewer warnings than before
- No 12px impassable gaps at y=496
- entities.json ring positions match SVG changes

## Step 8: Update tests

File: `tests/test_hillside.py`, lines 106–128.

Update `TestLoopGeometry`:
- `test_loop_tiles_exist`: change ty range from (15, 33) to (23, 41),
  update docstring to reference center (3600, 508)
- `test_loop_has_varied_angles`: change ty range from (15, 33) to (23, 41)

## Step 9: Run tests

Run:
```
uv run pytest tests/test_hillside.py -v
```

**Verify**: all tests pass. Focus on `TestLoopGeometry` tests.

## Testing Strategy

- **Existing tests**: `tests/test_hillside.py` covers entity counts, player start,
  dimensions, and loop geometry. All should pass after updates.
- **Manual verification**: inspect `validation_report.txt` for reduction in
  loop-zone warnings.
- **No new tests needed**: the existing loop geometry tests cover the relevant
  assertions (tiles exist, varied angles). The fix is data-only.
