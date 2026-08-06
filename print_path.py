from speednik.grids import build_loop
from speednik.qa import run_audit, make_walker, BehaviorExpectation

tiles, wrap = build_loop(approach_tiles=15, radius=48, ground_row=20, ramp_radius=16)

expectation = BehaviorExpectation(
    name="dbg",
    stage="hillside", 
    archetype="walker",
    min_x_progress=0, max_deaths=0, require_goal=False, max_frames=200, invariant_errors_ok=0
)

# wait I need to simulate it exactly like test_loop_audit does
