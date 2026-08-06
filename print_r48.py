import os
import sys

sys.path.insert(0, os.path.abspath('.'))
from speednik.grids import build_loop

tiles, _ = build_loop(approach_tiles=15, radius=48, ground_row=20, ramp_radius=16)

cx = 15*16 + 16 + 48
cy = 320 - 48

for ty in range(cy//16 - 2, cy//16 + 4):
    for tx in range(cx//16 + 1, cx//16 + 4):
        if (tx, ty) in tiles:
            print(f"({tx}, {ty}): maxh={max(tiles[tx,ty].height_array)} {tiles[tx,ty].height_array}")
