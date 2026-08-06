import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import speednik.terrain as terrain
from speednik.physics import PhysicsState

from speednik.grids import build_loop

tiles, wrap = build_loop(approach_tiles=15, radius=48, ground_row=20, ramp_radius=16)

# Provide a mock lookup
def tile_lookup(tx, ty):
    return tiles.get((tx, ty))

# Set up state for frame 51: x=349.9, y=293.0, gs=6.1, a=14
state = PhysicsState(
    x=349.9,
    y=293.0,
    x_vel=6.1,
    y_vel=0.0,
    ground_speed=6.1,
    angle=14,
    on_ground=True,
    is_rolling=False
)

res = terrain.find_floor(state, tile_lookup)
print(f"find_floor: f={res.found} d={res.distance} ang={res.tile_angle}")

w_rad, h_rad = terrain._get_radii(state)
print(f"w_rad={w_rad} h_rad={h_rad}")

a_x = state.x - w_rad
a_y = state.y + h_rad
b_x = state.x + w_rad
b_y = state.y + h_rad

print(f"Sensor A: x={a_x} y={a_y}")
res_A = terrain._sensor_cast(a_x, a_y, terrain.DOWN, tile_lookup, terrain._floor_solidity_filter(state.y_vel))
print(f"  A -> f={res_A.found} d={res_A.distance} ang={res_A.tile_angle}")

print(f"Sensor B: x={b_x} y={b_y}")
res_B = terrain._sensor_cast(b_x, b_y, terrain.DOWN, tile_lookup, terrain._floor_solidity_filter(state.y_vel))
print(f"  B -> f={res_B.found} d={res_B.distance} ang={res_B.tile_angle}")

