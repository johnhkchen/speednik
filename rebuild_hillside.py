"""Rebuild hillside loop: replace only the broken hand-placed loop tiles with
synthetic build_loop() geometry, preserving all surrounding terrain.

Run: uv run python rebuild_hillside.py
"""

import json
from pathlib import Path

from speednik.grids import build_loop, _flat_tile, FILL_DEPTH
from speednik.terrain import TILE_SIZE, FULL, SURFACE_LOOP

STAGE_DIR = Path("speednik/stages/hillside")

# ---------------------------------------------------------------------------
# Load current data
# ---------------------------------------------------------------------------

with open(STAGE_DIR / "tile_map.json") as f:
    tile_map = json.load(f)

with open(STAGE_DIR / "collision.json") as f:
    collision = json.load(f)

with open(STAGE_DIR / "entities.json") as f:
    entities = json.load(f)

ROWS = len(tile_map)
COLS = len(tile_map[0])
print(f"Grid: {COLS}×{ROWS}")

# ---------------------------------------------------------------------------
# Loop parameters — match the old loop center
# ---------------------------------------------------------------------------

RADIUS = 64
RAMP_RADIUS = 32
GROUND_ROW = 39  # ground surface row at the loop location

# Place loop center at old center (cx=3584, col 224)
APPROACH_TILES = 218

# Derived geometry
approach_px = APPROACH_TILES * TILE_SIZE       # 3488
ramp_entry_start = approach_px                  # 3488
loop_start_px = approach_px + RAMP_RADIUS       # 3520
loop_end_px = loop_start_px + 2 * RADIUS        # 3648
ramp_exit_end_px = loop_end_px + RAMP_RADIUS    # 3680
cx = loop_start_px + RADIUS                     # 3584
cy = GROUND_ROW * TILE_SIZE - RADIUS            # 560

ramp_entry_start_col = ramp_entry_start // TILE_SIZE  # 218
loop_start_col = loop_start_px // TILE_SIZE           # 220
loop_end_col = (loop_end_px - 1) // TILE_SIZE         # 227
ramp_exit_end_col = (ramp_exit_end_px - 1) // TILE_SIZE + 1  # 230

print(f"Loop center: ({cx}, {cy})")
print(f"Entry ramp cols: {ramp_entry_start_col}–{loop_start_col - 1}")
print(f"Loop body cols: {loop_start_col}–{loop_end_col}")
print(f"Exit ramp cols: {loop_end_col + 1}–{ramp_exit_end_col - 1}")

# ---------------------------------------------------------------------------
# Step 1: Clear ONLY the old loop tiles
# ---------------------------------------------------------------------------
# The old hand-placed loop occupies cols 220-228, rows 31-38 (type=5 tiles)
# plus some non-loop tiles at those cols. We also clear the gap (214-218)
# and the exit tiles at 219, 229 since build_loop will regenerate those.
#
# Be surgical: only clear what we're going to replace.

CLEAR_COL_START = 214  # gap between approach ramp and old loop entry
CLEAR_COL_END = 230    # through exit tile (exclusive: clear up to 229)
CLEAR_ROW_START = 28
CLEAR_ROW_END = 39     # don't clear ground_row or below — only above

cleared = 0
for row in range(CLEAR_ROW_START, CLEAR_ROW_END):
    for col in range(CLEAR_COL_START, CLEAR_COL_END):
        if tile_map[row][col] is not None:
            tile_map[row][col] = None
            collision[row][col] = 0
            cleared += 1

# Also clear the entry/exit tiles at ground_row (will be regenerated)
for col in range(CLEAR_COL_START, CLEAR_COL_END):
    if tile_map[GROUND_ROW][col] is not None:
        old_type = tile_map[GROUND_ROW][col].get("type", 0)
        # Only clear tiles that were part of the old loop infrastructure
        # (type=5 loop tiles, or type=0 flat fill tiles placed by old pipeline)
        if old_type in (0, 5):
            tile_map[GROUND_ROW][col] = None
            collision[GROUND_ROW][col] = 0
            cleared += 1

print(f"Cleared {cleared} tiles in old loop region")

# ---------------------------------------------------------------------------
# Step 2: Generate synthetic loop
# ---------------------------------------------------------------------------

tiles_dict, _ = build_loop(
    approach_tiles=APPROACH_TILES,
    radius=RADIUS,
    ground_row=GROUND_ROW,
    ramp_radius=RAMP_RADIUS,
)

print(f"build_loop() generated {len(tiles_dict)} tiles total")

# ---------------------------------------------------------------------------
# Step 3: Merge synthetic loop tiles — only in the loop/ramp region
# ---------------------------------------------------------------------------
# We only merge tiles from the entry ramp through the exit ramp.
# We do NOT merge the flat approach (cols 0-217) or the flat exit (cols 230+),
# because the stage has its own terrain there.

MERGE_COL_START = CLEAR_COL_START  # 214
MERGE_COL_END = CLEAR_COL_END     # 230

# However, we also need flat exit tiles for a few columns past the exit ramp
# to bridge to the existing stage terrain at col 230+.
# The existing stage already has flat tiles at cols 230+, so we just need to
# make sure the exit ramp connects.
EXIT_BRIDGE_END = 230  # merge up to here

merged = 0
for (tx, ty), tile in tiles_dict.items():
    if tx < MERGE_COL_START or tx >= EXIT_BRIDGE_END:
        continue
    if ty < 0 or ty >= ROWS:
        continue

    cell = {
        "height_array": tile.height_array,
        "angle": tile.angle,
        "type": tile.tile_type,
    }
    tile_map[ty][tx] = cell
    collision[ty][tx] = tile.solidity
    merged += 1

print(f"Merged {merged} synthetic tiles (cols {MERGE_COL_START}–{EXIT_BRIDGE_END - 1})")

# ---------------------------------------------------------------------------
# Step 4: Bridge the gap between approach ramp and entry ramp
# ---------------------------------------------------------------------------
# The existing approach ramp at cols 209-213 ends at surface_y≈608.
# The entry ramp from build_loop starts at col 218.
# Cols 214-217 need transitional ground tiles.
#
# We fill these with flat tiles at the same height as the surrounding terrain.
# The approach ramp ends at row 38 (col 213), so we use row 39 flat tiles
# to match the existing terrain at the entry/exit (surface_y=624).

bridge_filled = 0
for col in range(214, ramp_entry_start_col):  # cols 214-217
    if tile_map[GROUND_ROW][col] is None:
        flat = _flat_tile()
        tile_map[GROUND_ROW][col] = {
            "height_array": flat.height_array,
            "angle": flat.angle,
            "type": flat.tile_type,
        }
        collision[GROUND_ROW][col] = flat.solidity
        bridge_filled += 1
        # Fill below
        for fill_row in range(GROUND_ROW + 1, min(GROUND_ROW + 1 + FILL_DEPTH, ROWS)):
            if tile_map[fill_row][col] is None:
                tile_map[fill_row][col] = {
                    "height_array": flat.height_array,
                    "angle": flat.angle,
                    "type": flat.tile_type,
                }
                collision[fill_row][col] = flat.solidity

print(f"Bridged {bridge_filled} gap columns (214-{ramp_entry_start_col - 1})")

# ---------------------------------------------------------------------------
# Step 5: Ensure ground continuity under the loop
# ---------------------------------------------------------------------------
# build_loop() may not generate tiles at ground_row for every column in the
# loop body (the bottom of the circle doesn't always land at exactly ground_row).
# Fill any remaining gaps at ground_row between entry and exit.

ground_gaps_filled = 0
for col in range(MERGE_COL_START, EXIT_BRIDGE_END):
    if tile_map[GROUND_ROW][col] is None:
        flat = _flat_tile()
        tile_map[GROUND_ROW][col] = {
            "height_array": flat.height_array,
            "angle": flat.angle,
            "type": flat.tile_type,
        }
        collision[GROUND_ROW][col] = flat.solidity
        ground_gaps_filled += 1
        # Fill below
        for fill_row in range(GROUND_ROW + 1, min(GROUND_ROW + 1 + FILL_DEPTH, ROWS)):
            if tile_map[fill_row][col] is None:
                tile_map[fill_row][col] = {
                    "height_array": flat.height_array,
                    "angle": flat.angle,
                    "type": flat.tile_type,
                }
                collision[fill_row][col] = flat.solidity

print(f"Filled {ground_gaps_filled} ground-row gaps under loop")

# ---------------------------------------------------------------------------
# Step 6: Fix goal position
# ---------------------------------------------------------------------------
# The goal at (4758, 642) is underground. Place it at y=610 to match
# the player_start convention (player center sits at y=610 on flat ground).

for entity in entities:
    if entity["type"] == "goal":
        old_y = entity["y"]
        entity["y"] = 610
        print(f"Goal: y={old_y} -> y={entity['y']}")

# ---------------------------------------------------------------------------
# Verify: no terrain damage outside the loop region
# ---------------------------------------------------------------------------
# Spot-check that the hillside terrain is intact outside the loop.
# Cols 37-213 should be untouched (original hills).
damage = 0
for col in range(37, 214):
    found = False
    for row in range(ROWS):
        cell = tile_map[row][col]
        if cell is not None and max(cell["height_array"]) > 0:
            found = True
            break
    if not found:
        damage += 1
        print(f"  WARNING: col {col} has no ground tile!")

if damage == 0:
    print("Terrain integrity check: OK (all approach columns have ground)")
else:
    print(f"Terrain integrity check: FAILED ({damage} columns lost)")

# ---------------------------------------------------------------------------
# Write back
# ---------------------------------------------------------------------------

with open(STAGE_DIR / "tile_map.json", "w") as f:
    json.dump(tile_map, f, separators=(",", ":"))

with open(STAGE_DIR / "collision.json", "w") as f:
    json.dump(collision, f, separators=(",", ":"))

with open(STAGE_DIR / "entities.json", "w") as f:
    json.dump(entities, f, indent=2)

print("\nDone! Stage files updated.")
