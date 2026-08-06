import sys
import os

sys.path.insert(0, os.path.abspath('.'))
import old_grids
import tests.test_loop_audit as test_module

test_module.build_loop = old_grids.build_loop
runner = test_module.TestSyntheticLoopTraversal()
runner.RADIUS = 96
result, start, end = runner._build_and_run(96)

print(f"Old Grids: Start={start}, End={end}")
if result.snaps:
    print(f"First snap: x={result.snaps[0].x}, y={result.snaps[0].y}")
else:
    print("No snaps!")
