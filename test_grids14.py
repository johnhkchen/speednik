import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from speednik.grids import build_loop

tiles, wrap = build_loop(approach_tiles=15, radius=96, ground_row=20, ramp_radius=48)
for ty in range(13, 16):
    for tx in range(22, 26):
        if (tx, ty) in tiles:
            print(f"({tx},{ty}) ang={tiles[tx,ty].angle} ha={tiles[tx,ty].height_array}")
