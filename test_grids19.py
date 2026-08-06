import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import speednik.grids as new_grids
import old_grids

from tests.test_loop_audit import TestSyntheticLoopTraversal

def run_with(builder):
    new_grids.build_loop = builder
    runner = TestSyntheticLoopTraversal()
    runner.RADIUS = 96
    result, start, end = runner._build_and_run(96)
    return result

res_old = run_with(old_grids.build_loop)
print("OLD GRIDS:")
for snap in res_old.snaps:
    if 240 <= snap.x <= 320:
        print(f"f={snap.frame:3d} x={snap.x:6.1f} y={snap.y:6.1f} q={snap.quadrant} a={snap.angle:3d} gs={snap.ground_speed:6.1f} og={snap.on_ground}")

