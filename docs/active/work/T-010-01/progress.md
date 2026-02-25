# Progress — T-010-01: SimState and create_sim

## Completed

### Step 1–3: Create `speednik/simulation.py`
- Created `speednik/simulation.py` with:
  - Six event dataclasses: `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`, `GoalReachedEvent`, `CheckpointEvent`
  - `Event` union type alias
  - `SimState` dataclass with all 18 fields from ticket spec
  - `create_sim(stage_name: str) -> SimState` factory mirroring `main.py:_load_stage()`
  - Boss injection for skybridge stage
  - No Pyxel imports

### Step 4: Write `tests/test_simulation.py`
- 10 test functions covering:
  - `create_sim` for all three stages (hillside, pipeworks, skybridge)
  - Goal position verification against known entity data
  - Boss injection for skybridge only
  - Entity list population checks
  - Event type instantiation
  - No-Pyxel-import contract test
  - SimState default values

### Step 5: Full test suite
- `uv run pytest tests/ -x`: 821 passed, 5 xfailed, 0 failures.
- No regressions.

## Deviations from Plan

None. Implementation followed plan exactly.
