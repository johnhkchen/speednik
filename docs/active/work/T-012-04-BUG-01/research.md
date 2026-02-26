# Research — T-012-04-BUG-01: skybridge-bottomless-pit-at-x170

## Bug Summary

All 6 player archetypes fall into a bottomless pit at x~170 in Skybridge Gauntlet.
Tile column 11 (px 176-192) at row 31 has no collision or tile_map data, creating a
gap in the walking surface. The player falls below the world.

## Two Compounding Issues

### Issue 1: Missing collision tile at column 11

The skybridge walking surface starts at row 31 with solid tiles from col 0-10.
Column 11 has `None` in `tile_map.json` and `0` in `collision.json` for ALL 56 rows.

Surrounding pattern at row 31:
- Col 10: collision=2(FULL), angle=192, heights=[12,0,0,...,0] — trailing slope edge
- Col 11: collision=0, tile_map=None — **gap**
- Col 12: collision=1(TOP_ONLY), angle=64, heights=all 12 — leading slope edge

The trailing/leading edge pair (angle 192→64) around col 11 matches the pattern at
every other gap in the stage (cols 19, 27-28, 36-38, etc.), suggesting col 11 was
intended as a gap/pit, not a missing tile error.

However, col 11's gap is unique: it is bottomless (no floor in rows 32-55) and has
no recovery mechanism. Gaps at cols 19 and 27-28 have floors at row 38.

### Issue 2: No pit death mechanism (ALREADY FIXED)

T-013-01 added pit death logic to `simulation.py` lines 246-252:
```python
if p.y > sim.level_height + PIT_DEATH_MARGIN:
    if sim.player.state != PlayerState.DEAD:
        sim.player.state = PlayerState.DEAD
        sim.player.physics.on_ground = False
        sim.deaths += 1
        events.append(DeathEvent())
```

`PIT_DEATH_MARGIN = 32` in `constants.py` line 111. Level height for skybridge is
896px (meta.json). Death triggers at y > 928.

This means the "never dies" aspect of the bug is now resolved. Players falling through
the gap will die at y=928. However, they still fall, die, and the audit still fails
because the walker dies at x~170 instead of progressing to x=2500+.

## File Inventory

| File | Role |
|------|------|
| `speednik/stages/skybridge/collision.json` | 56x325 solidity grid; col 11 all zeros |
| `speednik/stages/skybridge/tile_map.json` | 56x325 tile data; col 11 all None |
| `speednik/stages/skybridge/entities.json` | Entities; no springs exist in this stage |
| `speednik/stages/skybridge/meta.json` | Dimensions 5200x896, player_start (64,490) |
| `speednik/simulation.py` | sim_step() with pit death (lines 246-252) |
| `speednik/constants.py` | PIT_DEATH_MARGIN=32 (line 111) |
| `speednik/level.py` | _build_tiles() skips None tile_map cells (line 105) |
| `speednik/terrain.py` | resolve_collision() detaches when no floor found |
| `tests/test_audit_skybridge.py` | 6 tests, all xfail ref T-012-04-BUG-01 |

## Gap Analysis: All Skybridge Row 31 Gaps

| Cols | Px Range | Width | Depth | Recovery |
|------|----------|-------|-------|----------|
| 11 | 176-192 | 1 tile | Bottomless | **None** |
| 19 | 304-320 | 1 tile | Row 38 | Floor below |
| 27-28 | 432-464 | 2 tiles | Row 38 | Floor below |
| 36-38 | 576-624 | 3 tiles | ? | ? |
| 52-71 | 832-1152 | 20 tiles | ? | Alt path |
| 73-76 | 1168-1232 | 4 tiles | ? | ? |
| 102-119 | 1632-1920 | 18 tiles | ? | Alt path |
| 123-128 | 1968-2064 | 6 tiles | ? | ? |
| 152-168 | 2432-2704 | 17 tiles | ? | Alt path |
| 173-180 | 2768-2896 | 8 tiles | ? | ? |

The first gap at col 11 is the earliest obstacle in the stage. Without a floor below
or recovery mechanism, it is an immediate death trap that stops all progress.

## Trailing Edge Problem

Col 10 has heights=[12,0,0,...,0] with angle=192. This means only the first pixel
column (x=160) within tile col 10 is solid. Pixels x=161-175 within col 10 have
height 0. Combined with the missing col 11, the effective gap runs from x=161 to
x=191 (31 pixels).

The floor sensors are at x-9 and x+9 from player center. When center reaches ~x=170:
- Sensor A (x=161): tile col 10, pixel offset 1 → height=0, no surface
- Sensor B (x=179): tile col 11 → None, no surface
Both sensors fail → player detaches from ground → falls.

## Test Status

`tests/test_audit_skybridge.py`: All 6 tests xfailed with `strict=True`. They
reference `T-012-04-BUG-01` as the reason. These xfails should be removed once the
collision gap is fixed.

## Constraints

- No springs exist in skybridge at all — the stage uses gaps as pits, with lower
  platform paths as recovery, not springs
- The stage already has pit death via T-013-01, so falling = death + respawn
- The fix must ensure the initial walking surface (cols 0-11) is traversable
- Other intentional gaps must remain as designed pit hazards
