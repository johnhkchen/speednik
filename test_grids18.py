import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from tests.test_loop_audit import TestSyntheticLoopTraversal
runner = TestSyntheticLoopTraversal()
runner.RADIUS = 96
result, start, end = runner._build_and_run(96)

for snap in result.snaps[:120]:
    if snap.x >= 250:
        print(f"f={snap.frame:3d} x={snap.x:6.1f} y={snap.y:6.1f} q={snap.quadrant} a={snap.angle:3d} gs={snap.ground_speed:6.1f} og={snap.on_ground} st={snap.state}")
