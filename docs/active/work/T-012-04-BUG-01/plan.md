# Plan — T-012-04-BUG-01: skybridge-bottomless-pit-at-x170

## Step 1: Fix skybridge tile_map.json

Modify `speednik/stages/skybridge/tile_map.json`:

1. Row 31, col 10: Change height_array to all 12s, angle to 0 (remove trailing edge)
2. Row 31, col 11: Replace `null` with `{"type":2, "height_array":[12x12], "angle":0}`
3. Row 32, col 10: Change height_array to all 16s, angle to 0 (remove trailing edge)
4. Row 32, col 11: Replace `null` with `{"type":2, "height_array":[16x16], "angle":0}`

Verification: Run a Python script to confirm tile_map[31][11] and [32][11] are not
None, and [31][10] and [32][10] have flat heights.

## Step 2: Fix skybridge collision.json

Modify `speednik/stages/skybridge/collision.json`:

1. Row 31, col 11: Change from `0` to `1` (TOP_ONLY)
2. Row 32, col 11: Change from `0` to `1` (TOP_ONLY)

Verification: Run a Python script to confirm collision[31][11] == 1 and
collision[32][11] == 1.

## Step 3: Remove xfail markers from test_audit_skybridge.py

Remove the `@pytest.mark.xfail(strict=True, reason="BUG: T-012-04-BUG-01 ...")`
decorator from all 6 test functions:
- test_skybridge_walker
- test_skybridge_jumper
- test_skybridge_speed_demon
- test_skybridge_cautious
- test_skybridge_wall_hugger
- test_skybridge_chaos

## Step 4: Verify the fix

1. Run a quick simulation to confirm the walker passes x=170 without falling:
   ```python
   from speednik.simulation import create_sim, sim_step
   from speednik.physics import InputState
   sim = create_sim("skybridge")
   for _ in range(400):
       inp = InputState(right_held=True)
       sim_step(sim, inp)
   assert sim.player.physics.y < 600  # not fallen
   assert sim.player.physics.x > 170  # passed the gap
   ```

2. Run `pytest tests/test_audit_skybridge.py` to see which tests pass/fail. Tests
   may still fail for unrelated reasons (other gaps, enemies, etc.), but they should
   no longer fail specifically because of the col 11 gap.

## Testing Strategy

- **Smoke test**: Quick simulation confirms player traverses x=170 on solid ground
- **Integration tests**: The existing `test_audit_skybridge.py` tests cover all 6
  archetypes; removing xfail lets them report real results
- **Regression**: No code changes to the engine means no risk to other stages; but
  verify hillside and pipeworks tests still pass as a sanity check
