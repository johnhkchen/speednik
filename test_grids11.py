import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import speednik.terrain as terrain

orig_sc_down = terrain._sensor_cast_down

def my_sc_down(sensor_x, sensor_y, tile_lookup, solidity_filter):
    res = orig_sc_down(sensor_x, sensor_y, tile_lookup, solidity_filter)
    if terrain.DEBUG_ON and 345 <= sensor_x <= 355:
        tx = int(sensor_x) // 16
        ty = int(sensor_y) // 16
        print(f"[SC_DOWN] sx={sensor_x:.1f} sy={sensor_y:.1f} tile=({tx},{ty}) -> {res.found} d={res.distance:.1f} a={res.tile_angle} type={res.tile_type}")
    return res

terrain._sensor_cast_down = my_sc_down

terrain.DEBUG_ON = False
from tests.test_loop_audit import TestSyntheticLoopSpeedSweep
runner = TestSyntheticLoopSpeedSweep()
runner.RADIUS = 48
terrain.DEBUG_ON = True
result, start, end = runner._run_at_speed(5.0)

