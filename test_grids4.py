import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from speednik.grids import build_loop

tiles, wrap = build_loop(approach_tiles=15, radius=48, ground_row=20, ramp_radius=16)
for y in range(16, 21):
    for x in range(19, 23):
        if (x, y) in tiles:
            print(f"({x},{y}) ang={tiles[x,y].angle} ha={tiles[x,y].height_array}")
