import sys
import os

sys.path.insert(0, os.path.abspath('.'))
import speednik.grids
import old_grids

speednik.grids.build_loop = old_grids.build_loop

import tests.test_loop_audit as test_module
test_module.build_loop = old_grids.build_loop

runner = test_module.TestSyntheticLoopTraversal()
result, start, end = runner._build_and_run(96)

print(f"Start: {start} End: {end}")
for snap in result.snaps[:10]:
    print(f"f={snap.frame:3d} x={snap.x:6.1f} y={snap.y:6.1f} q={snap.quadrant} a={snap.angle:3d} gs={snap.ground_speed:6.1f} og={snap.on_ground}")
