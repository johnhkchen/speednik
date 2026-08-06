import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from tests.test_loop_audit import TestSyntheticLoopSpeedSweep
import speednik.terrain as terrain

orig_ff = terrain.find_floor

def my_ff(state, tile_lookup):
    res = orig_ff(state, tile_lookup)
    if 345 <= state.x <= 355:
        print(f"ff at x={state.x:.1f} y={state.y:.1f} ang={state.angle} -> found={res.found} dist={res.distance:.1f} tang={res.tile_angle} type={res.tile_type}")
    return res

terrain.find_floor = my_ff

runner = TestSyntheticLoopSpeedSweep()
runner.RADIUS = 48
result, start, end = runner._run_at_speed(5.0)

