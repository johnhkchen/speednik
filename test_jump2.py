import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from tests.test_loop_audit import TestSyntheticLoopSpeedSweep
from speednik.grids import build_loop
from speednik.terrain import get_quadrant

runner = TestSyntheticLoopSpeedSweep()
runner.RADIUS = 48
result, start, end = runner._run_at_speed(5.0)

for snap in result.snaps:
    if snap.x >= 280 and snap.x <= 360:
        tx = int(snap.x) // 16
        ty = int(snap.y) // 16
        print(f"f={snap.frame:3d} x={snap.x:6.1f} y={snap.y:6.1f} tile=({tx},{ty}) q={snap.quadrant} a={snap.angle:3d} gs={snap.ground_speed:6.1f} og={snap.on_ground}")
