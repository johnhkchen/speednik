# Design — T-012-07: svg2stage angle fix and regenerate

## Decision: Post-rasterization angle smoothing + validator enhancement

### Approach chosen: Single-pass neighbor smoothing

After rasterization completes and before validation runs, scan the entire grid for
isolated steep tiles and replace their angles with the average of non-steep horizontal
neighbors.

### Why this approach

1. **Minimal invasiveness**: No changes to the rasterizer itself. The "last write wins"
   behavior is correct for most tiles — the problem only manifests at polygon edge
   boundaries where a degenerate segment crosses a tile.

2. **Conservative**: Only modifies tiles that are (a) steep, (b) not loop tiles, and
   (c) have at least one non-steep horizontal neighbor. Legitimate wall geometry (where
   both neighbors are also steep) is untouched.

3. **Matches the ticket's pseudocode**: The ticket provides a reference implementation
   that is well-reasoned. Adopt it with minor adjustments.

### Alternatives considered

**A. Fix angle computation in the rasterizer (per-tile angle averaging)**
- Accumulate multiple angles per tile from overlapping segments, take circular mean.
- Pro: Fixes the root cause at the source.
- Con: Significantly more complex. Requires tracking per-tile angle history. The
  "last write wins" model works for height arrays (max is taken), but angle averaging
  during rasterization would need weighted means based on segment length within the tile.
  Over-engineering for what is essentially a rare boundary artifact.
- Rejected: Too complex for the problem scope.

**B. Increase `MAX_STEEP_RUN` threshold and live with it**
- Con: Doesn't fix the bug, just hides the validator warning.
- Rejected: Not a fix.

**C. Pre-filter degenerate segments before rasterization**
- Skip or clamp segments shorter than some threshold.
- Con: Short segments can be legitimate (e.g., tight curves). Hard to distinguish
  degenerate from intentional. Risk of dropping valid geometry.
- Rejected: Unsafe heuristic.

### Smoothing algorithm detail

```
for each tile (tx, ty) in grid:
    skip if tile is None
    skip if tile.is_loop_upper
    skip if tile is not steep (_is_steep returns False)

    collect non-steep horizontal neighbors at (tx-1, ty) and (tx+1, ty)
    if at least 1 non-steep neighbor exists:
        replace tile.angle with circular_mean(neighbor angles) mod 256
```

**Circular mean for byte angles**: For non-steep neighbors (angles in floor quadrant:
0-32 or 224-255), simple arithmetic average mod 256 can fail at the wrap boundary.
Example: angles 2 and 254 should average to 0, not 128. Use the circular mean:

```python
sin_sum = sum(sin(a * 2π/256) for a in neighbor_angles)
cos_sum = sum(cos(a * 2π/256) for a in neighbor_angles)
mean = round(atan2(sin_sum, cos_sum) * 256 / (2π)) % 256
```

This handles wraparound correctly at negligible cost.

### Validator enhancement

Extend `_check_accidental_walls` to also flag isolated steep tiles (run lengths 1-3)
when surrounded by non-steep neighbors. Since the smoothing pass runs before validation,
these should no longer appear. The validator serves as a safety net: if the smoothing
pass misses something, the validator catches it.

Specifically: change the threshold from `run_count > MAX_STEEP_RUN` to also flag runs
of length 1 where at least one horizontal neighbor is non-steep and non-loop. This
makes the validator consistent with the smoothing pass's logic.

### Integration into main()

Current flow: parse → rasterize → validate → write
New flow:     parse → rasterize → **smooth** → validate → write

The smoothing function is a module-level function `_smooth_accidental_walls(grid)` called
in `main()` between rasterization and validation. It logs how many tiles were smoothed.

### Regeneration

Run the pipeline for all 3 stages:
```
uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/
uv run python tools/svg2stage.py stages/pipe_works.svg speednik/stages/pipeworks/
uv run python tools/svg2stage.py stages/skybridge_gauntlet.svg speednik/stages/skybridge/
```

### Test changes

**Hillside**: Remove xfail markers from `test_hillside_walker`, `test_hillside_cautious`,
`test_hillside_wall_hugger` IF they pass after regeneration. These are the BUG-01 tests.
Speed demon and chaos xfails stay (separate bugs).

**Pipeworks**: BUG-01 already fixed in comments. No xfail changes expected. The slope
difficulty xfails (jumper, speed_demon, cautious, chaos) are gameplay issues, not pipeline
bugs.

**Skybridge**: All xfails are for bottomless pit BUG-01 (T-012-04-BUG-01), unrelated.
Regeneration must not break them. Verify they still xfail cleanly.

### Risk assessment

- **Low risk**: The smoothing is conservative (only isolated steep with non-steep
  neighbors). Legitimate walls are preserved.
- **Loop safety**: Explicitly skips `is_loop_upper` tiles.
- **Regression risk**: Regenerating all 3 stages changes tile data. Tests must pass.
  Skybridge may have angle changes but the bottomless pit bug is structural (missing
  collision data), not angle-related.
