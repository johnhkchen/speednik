import sys
import os

sys.path.insert(0, os.path.abspath('.'))
import speednik.grids
import old_grids
import tests.test_loop_audit as test_module

# correctly patch the imported build_loop reference
test_module.build_loop = old_grids.build_loop

runner = test_module.TestSyntheticLoopTraversal()
runner.RADIUS = 96
result, start, end = runner._build_and_run(96)

print(f"Old Grids: Start={start}, End={end}")
if result.snaps:
    print(f"First snap: x={result.snaps[0].x}, y={result.snaps[0].y}")
else:
    print("No snaps!")

for snap in result.snaps:
    if 240 <= snap.x <= 320:
        print(f"f={snap.frame:3d} x={snap.x:6.1f} y={snap.y:6.1f} q={snap.quadrant} a={snap.angle:3d} gs={snap.ground_speed:6.1f} og={snap.on_ground}")
