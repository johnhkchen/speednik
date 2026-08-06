import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import speednik.terrain as terrain

orig_sn = terrain.find_floor

def my_sn(state, tile_lookup):
    import speednik.terrain as terr
    res = orig_sn(state, tile_lookup)
    if getattr(terr, 'DEBUG_ON', False) and 345 <= state.x <= 355:
        print(f"[FF] x={state.x:.1f} y={state.y:.1f} y_vel={state.y_vel:.1f} -> {res.found} d={res.distance:.1f} ang={res.tile_angle}")
    return res

terrain.find_floor = my_sn

from tests.test_loop_audit import TestSyntheticLoopSpeedSweep
runner = TestSyntheticLoopSpeedSweep()
runner.RADIUS = 48
terrain.DEBUG_ON = True
result, start, end = runner._run_at_speed(5.0)

