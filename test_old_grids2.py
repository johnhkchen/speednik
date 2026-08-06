import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import old_grids

tiles, wrap = old_grids.build_loop(approach_tiles=15, radius=96, ground_row=20, ramp_radius=48)

for ty in range(0, 25):
    if (18, ty) in tiles:
        print(f"tx=18 ty={ty} ang={tiles[18,ty].angle} ha={tiles[18,ty].height_array}")
    else:
        print(f"tx=18 ty={ty} -- empty")
