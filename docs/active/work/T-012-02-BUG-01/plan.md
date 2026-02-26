# Plan — T-012-02-BUG-01: hillside-wall-at-x601

## Step 1: Fix tile_map.json

**Action**: Edit `speednik/stages/hillside/tile_map.json`, row 38, column 37.
Change the `"angle"` field from `64` to `2`.

**Verification**: Run a quick Python snippet to reload the JSON and confirm
`tile_map[38][37]["angle"] == 2`. Confirm neighboring tiles unchanged.

**Commit**: "fix: correct angle=64→2 for hillside tile (37,38) [T-012-02-BUG-01]"

## Step 2: Add regression test — tile angle

**Action**: Add `test_hillside_tile_37_38_not_wall_angle` to
`tests/test_terrain.py`.

```python
def test_hillside_tile_37_38_not_wall_angle():
    """Tile (37,38) must have a floor-range angle, not wall-range."""
    from speednik.simulation import create_sim
    sim = create_sim("hillside")
    tile = sim.tile_lookup(37, 38)
    assert tile is not None, "Tile (37, 38) must exist"
    assert tile.angle <= 5, f"Expected floor angle <=5, got {tile.angle}"
```

**Verification**: `uv run pytest tests/test_terrain.py::test_hillside_tile_37_38_not_wall_angle -v`

## Step 3: Add integration test — walker passes x=601

**Action**: Add `test_hillside_walker_passes_x601` to
`tests/test_simulation.py`.

```python
def test_hillside_walker_passes_x601():
    """Hold-right walker must pass x=601 (formerly blocked by wall-angle tile)."""
    sim = create_sim("hillside")
    inp = InputState(right=True)
    for _ in range(600):
        sim_step(sim, inp)
    assert sim.player.physics.x > 650, (
        f"Walker stuck at x={sim.player.physics.x:.1f}, should pass 650"
    )
```

**Verification**: `uv run pytest tests/test_simulation.py::test_hillside_walker_passes_x601 -v`

## Step 4: Run full test suite

**Action**: `uv run pytest tests/ -x -q`

**Verification**: All tests pass. No regressions.

## Step 5: Commit tests

**Commit**: "test: add regression tests for hillside tile (37,38) wall fix [T-012-02-BUG-01]"

## Testing Strategy

| Test                                           | Type        | Verifies                              |
|------------------------------------------------|-------------|---------------------------------------|
| `test_hillside_tile_37_38_not_wall_angle`      | Unit        | Data fix is correct and persists      |
| `test_hillside_walker_passes_x601`             | Integration | Player traversal no longer blocked    |
| Existing `test_create_sim_hillside`            | Smoke       | Stage still loads correctly           |
| Existing `test_sim_step_hold_right_smoke`      | Smoke       | Basic hold-right still works          |
| Existing `test_full_sim_ring_collection_hillside` | E2E      | Ring collection still functions       |

## Rollback

If the fix causes unexpected issues:
- Revert `tile_map.json` change (angle back to 64).
- The two new tests would then fail, correctly signaling the revert.
