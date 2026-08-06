import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from speednik.grids import build_loop

tiles, wrap = build_loop(approach_tiles=15, radius=96, ground_row=20, ramp_radius=32)
# Replicate test radius: in test test_all_quadrants_grounded[r96], wait.
# The test calls self._build_and_run(radius) which sets ramp_radius = max(16, radius // 2) = 48
# Let me just check the whole top row:
cy = 320 - 96
top_ty = (cy - 96) // 16
cx = (15 * 16) + 48 + 96 # Wait! ramp_radius is 48! so approach_px + r_ramp + radius
# loop_start = 240 + 48 = 288. cx = 288 + 96 = 384. tx=24.
for ty in range(top_ty - 1, top_ty + 3):
    for tx in range(21, 27):
        if (tx, ty) in tiles:
            print(f"({tx},{ty}) ang={tiles[tx,ty].angle} ha={tiles[tx,ty].height_array}")
