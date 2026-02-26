# Plan — T-012-03-BUG-01: pipeworks-slope-wall-blocks-progress

## Step 1: Fix tile_map.json

**Action**: Edit `speednik/stages/pipeworks/tile_map.json`. Change the `"angle"`
field from 64 to 0 for four tiles:
- Row 13, column 32
- Row 14, column 32
- Row 15, column 32
- Row 16, column 32

**Verification**: Run a Python snippet to reload the JSON and confirm
`tile_map[row][32]["angle"] == 0` for rows 13–16. Confirm rows 10–12 still
have angle=64.

**Commit**: `fix: correct angle=64→0 for pipeworks tiles (32,13-16) [T-012-03-BUG-01]`

## Step 2: Add regression test — tile angles

**Action**: Add `test_pipeworks_col32_underground_not_wall_angle` to
`tests/test_terrain.py`.

```python
def test_pipeworks_col32_underground_not_wall_angle():
    """Fully-solid tiles at col 32, rows 13-16 must not have wall angle (T-012-03-BUG-01)."""
    from speednik.simulation import create_sim
    sim = create_sim("pipeworks")
    for row in [13, 14, 15, 16]:
        tile = sim.tile_lookup(32, row)
        assert tile is not None, f"Tile (32, {row}) must exist"
        assert tile.angle <= 5, (
            f"Tile (32, {row}): expected floor angle <=5, got {tile.angle}"
        )
```

**Verification**: `uv run pytest tests/test_terrain.py::test_pipeworks_col32_underground_not_wall_angle -v`

## Step 3: Add integration test — jumper passes slope

**Action**: Add `test_pipeworks_jumper_passes_slope_wall` to
`tests/test_simulation.py`.

```python
def test_pipeworks_jumper_passes_slope_wall():
    """Jumper must pass x=520 on pipeworks (formerly blocked by wall-angle tiles)."""
    from speednik.qa import make_jumper
    sim = create_sim("pipeworks")
    strategy = make_jumper()
    for frame in range(900):
        inp = strategy(sim)
        sim_step(sim, inp)
    assert sim.max_x_reached > 600, (
        f"Jumper max_x={sim.max_x_reached:.1f}, should pass 600"
    )
```

**Verification**: `uv run pytest tests/test_simulation.py::test_pipeworks_jumper_passes_slope_wall -v`

## Step 4: Evaluate audit xfail annotations

**Action**: Run the four BUG-01-related audit tests without xfail to see if
they now pass or still fail for different reasons:

```bash
uv run pytest tests/test_audit_pipeworks.py::test_pipeworks_jumper \
  tests/test_audit_pipeworks.py::test_pipeworks_speed_demon \
  tests/test_audit_pipeworks.py::test_pipeworks_cautious \
  tests/test_audit_pipeworks.py::test_pipeworks_chaos -v --no-header 2>&1
```

Possible outcomes:
- **Still xfail (fail)**: Tests still fail — archetypes hit other downstream
  obstacles. Update xfail reason text to reference the new blocker, not BUG-01.
- **Now pass**: Remove xfail. This means fixing the slope wall was sufficient.
- **Partial**: Some pass, some fail for new reasons. Handle individually.

Update `tests/test_audit_pipeworks.py` accordingly.

## Step 5: Run full test suite

**Action**: `uv run pytest tests/ -x -q`

**Verification**: All tests pass. No regressions. Any xfail tests should still
be strict (expected to fail, and do fail). Any tests that are now unexpectedly
passing (xpass) need xfail removed.

## Step 6: Commit tests

**Commit**: `test: add regression tests for pipeworks slope wall fix [T-012-03-BUG-01]`

## Testing Strategy

| Test | Type | Verifies |
|------|------|----------|
| `test_pipeworks_col32_underground_not_wall_angle` | Unit | Data fix persists |
| `test_pipeworks_jumper_passes_slope_wall` | Integration | Player traversal unblocked |
| `test_pipeworks_jumper` (audit) | E2E | Full archetype behavior |
| Existing `test_create_sim_pipeworks` | Smoke | Stage still loads |
| Full suite | Regression | No breakage |

## Rollback

If the fix causes unexpected issues:
- Revert tile_map.json (angle back to 64 for rows 13–16).
- The new regression tests would fail, correctly signaling the revert.
