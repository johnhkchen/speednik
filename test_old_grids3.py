import sys
import os

sys.path.insert(0, os.path.abspath('.'))
import old_grids

tiles, wrap = old_grids.build_loop(approach_tiles=15, radius=96, ground_row=20, ramp_radius=48)

print("Entry Ramp tiles:")
for tx in range(15, 15 + 3):
    if (tx, 20) in tiles:
        print(f"tx={tx} ang={tiles[tx,20].angle} ha={tiles[tx,20].height_array}")
    elif (tx, 20) not in tiles:
        print(f"tx={tx} ty=20 EMPTY")

print("Exit Ramp tiles:")
cx = 15*16 + 48 + 96
loop_end = 15*16 + 48 + 2*96
for tx in range(loop_end//16, loop_end//16 + 3):
    if (tx, 20) in tiles:
        print(f"tx={tx} ang={tiles[tx,20].angle} ha={tiles[tx,20].height_array}")
    elif (tx, 20) not in tiles:
        print(f"tx={tx} ty=20 EMPTY")

