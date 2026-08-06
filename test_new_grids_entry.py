import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import speednik.grids as new_grids

tiles, wrap = new_grids.build_loop(approach_tiles=15, radius=96, ground_row=20, ramp_radius=48)

for ty in range(19, 22):
    for tx in range(17, 26):
        if (tx, ty) in tiles:
            print(f"tx={tx} ty={ty} ang={tiles[tx,ty].angle} ha={tiles[tx,ty].height_array}")
        else:
            print(f"tx={tx} ty={ty} -- empty")
