# Plan — T-012-02-BUG-02: hillside-no-right-boundary-clamp

## Step 1: Add right-boundary clamp in `sim_step()`

**File:** `speednik/simulation.py`

**Action:** Insert 2 lines after `player_update(sim.player, inp, sim.tile_lookup)`
(line 231), before the frame counter increment (line 234).

```python
    # 2a. Right-boundary clamp — prevents escaping level to the right
    if sim.player.physics.x > sim.level_width:
        sim.player.physics.x = float(sim.level_width)
```

**Verification:** Read the file after edit, confirm the clamp is in the correct
position in the sim_step flow.

## Step 2: Add test — immediate clamp from out-of-bounds position

**File:** `tests/test_simulation.py`

**Action:** Append a new test section at the end of the file.

```python
def test_right_boundary_clamp_immediate():
    """Player placed beyond level_width is clamped back on next step."""
    _, lookup = build_flat(40, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    lw = 600  # small level width for test
    sim = create_sim_from_lookup(lookup, START_X, sy, level_width=lw)

    # Teleport past boundary
    sim.player.physics.x = lw + 100.0
    sim_step(sim, InputState())

    assert sim.player.physics.x == float(lw), (
        f"Expected x={lw}, got x={sim.player.physics.x}"
    )
```

**Verification:** Run `uv run pytest tests/test_simulation.py::test_right_boundary_clamp_immediate -v`

## Step 3: Add test — running into boundary over many frames

**File:** `tests/test_simulation.py`

**Action:** Append another test after Step 2's test.

```python
def test_right_boundary_clamp_running():
    """Player running right never exceeds level_width."""
    _, lookup = build_flat(40, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    lw = 400  # small level width
    sim = create_sim_from_lookup(lookup, START_X, sy, level_width=lw)

    inp = InputState(right=True)
    for frame in range(600):
        sim_step(sim, inp)
        assert sim.player.physics.x <= lw, (
            f"Frame {frame}: x={sim.player.physics.x} exceeds level_width={lw}"
        )
```

**Verification:** Run `uv run pytest tests/test_simulation.py::test_right_boundary_clamp_running -v`

## Step 4: Run full test suite

**Action:** Run all simulation tests to ensure no regressions.

```
uv run pytest tests/test_simulation.py -v
```

**Pass criteria:** All tests pass, including the new boundary tests and all
existing parity/smoke/regression tests.

## Step 5: Verify invariant resolution

**Action:** Run the reproduction scenario from the ticket to confirm zero
`position_x_beyond_right` violations on hillside with the jumper archetype.

If the QA framework (`speednik.qa`) is available and functional, run:
```python
from speednik.qa import run_audit, format_findings, BehaviorExpectation, make_jumper
exp = BehaviorExpectation(
    name="hillside_jumper", stage="hillside", archetype="jumper",
    min_x_progress=4700, max_deaths=0, require_goal=True,
    max_frames=3600, invariant_errors_ok=0,
)
findings, result = run_audit("hillside", make_jumper(), exp)
```

If the QA framework is not runnable (e.g., missing strategy archetypes), verify
via a manual simulation loop with hold_right for 3600 frames on hillside and
assert the player never exceeds level_width.

## Commit Plan

Single atomic commit after all tests pass:
- `speednik/simulation.py` — boundary clamp
- `tests/test_simulation.py` — two new tests
