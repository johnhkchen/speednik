import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from tests.test_loop_audit import TestSyntheticLoopSpeedSweep
from speednik import simulation

# Override sim_step to trace floor checks
orig_sim_step = simulation.sim_step

def my_sim_step(sim, inp):
    frame = getattr(sim, 'frame_count', 0)
    p = sim.player.physics
    px, py = p.x, p.y
    if 348 <= px <= 352 and 290 <= py <= 300:
        import speednik.terrain as terrain
        res = terrain.find_floor(p, sim.tile_lookup)
        print(f"[{frame}] px={px:.1f} py={py:.1f} floor={res.found} dist={res.distance:.1f} ang={res.tile_angle}")
    orig_sim_step(sim, inp)
    sim.frame_count = frame + 1

simulation.sim_step = my_sim_step

runner = TestSyntheticLoopSpeedSweep()
runner.RADIUS = 48
result, start, end = runner._run_at_speed(5.0)

for snap in result.snaps:
    if snap.x >= 345 and snap.x <= 355:
        print(f"f={snap.frame} x={snap.x:.1f} y={snap.y:.1f} q={snap.quadrant} gs={snap.ground_speed:.1f} a={snap.angle}")
