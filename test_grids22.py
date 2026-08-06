import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from tests.test_loop_audit import TestSyntheticLoopTraversal

result, start, end = TestSyntheticLoopTraversal._build_and_run(96)
print(f"START={start}, END={end}")
for s in result.snaps[:20]:
    print(s)
