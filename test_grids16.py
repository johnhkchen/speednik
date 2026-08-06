import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from speednik.grids import build_loop

# test_all_quadrants_grounded sets ramp_radius = max(16, r//2) = 48
tiles, wrap = build_loop(approach_tiles=15, radius=96, ground_row=20, ramp_radius=48)

cy = 320 - 96
top_ty = (cy - 96) // 16
cx = 15 * 16 + 48 + 96
print(f"cx={cx} top_ty={top_ty}")
for ty in range(top_ty - 1, top_ty + 2):
    for tx in range(21, 27):
        if (tx, ty) in tiles:
            print(f"({tx},{ty}) ang={tiles[tx,ty].angle} ha={tiles[tx,ty].height_array}")
