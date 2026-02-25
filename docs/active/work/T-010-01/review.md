# Review — T-010-01: SimState and create_sim

## Summary of Changes

### Files Created
- **`speednik/simulation.py`** (133 lines) — New module. Contains event dataclasses, `SimState` dataclass, and `create_sim()` factory.
- **`tests/test_simulation.py`** (148 lines) — 10 test functions covering all acceptance criteria.

### Files Modified
None.

## Acceptance Criteria Coverage

| Criterion | Status | Evidence |
|-----------|--------|----------|
| SimState dataclass with all fields from spec | Done | All 18 fields present, types match spec |
| `create_sim("hillside")` returns populated SimState | Done | `test_create_sim_hillside` verifies all fields |
| `create_sim("pipeworks")` and `create_sim("skybridge")` work | Done | Dedicated tests for each |
| Goal position correctly extracted | Done | Tests verify exact coordinates (4758/642, 5558/782, 5158/482) |
| Stage 3 boss entity injected | Done | `test_skybridge_boss_injection` confirms egg_piston present |
| All entity lists populated | Done | `test_hillside_entity_lists` checks rings, springs, checkpoints, enemies |
| Event types defined | Done | Six dataclass events + union type |
| No Pyxel imports | Done | `test_no_pyxel_import` source scan |
| `uv run pytest tests/ -x` passes | Done | 821 passed, 5 xfailed, 0 failures |

## Test Coverage

- **10 tests**, all passing.
- **Integration coverage**: All three stages loaded end-to-end through the JSON pipeline.
- **Contract test**: Source-level Pyxel import check.
- **Boundary test**: Boss injection only on skybridge (verified hillside and pipeworks have zero boss enemies).

### What's NOT tested (by design — out of scope for this ticket):
- `sim_step` behavior (T-010-02)
- Actual physics simulation through SimState (T-010-02)
- Mutation of metric fields during gameplay (T-010-02)

## Design Decisions Made

1. **Event types as dataclasses** (per ticket spec) — parallel to existing enum events in `objects.py`/`enemies.py`. T-010-02 will handle mapping between the two systems.
2. **Boss injection via name matching** (`stage_name == "skybridge"`) — simple, no coupling to stage numbering.
3. **Goal default (0.0, 0.0)** — matches `main.py` behavior for stages without goal entities.

## Open Concerns

1. **Event type duplication**: There are now two parallel event systems — the existing enums (`RingEvent`, `SpringEvent`, etc.) used by `objects.py`/`enemies.py`, and the new dataclass events. T-010-02 must bridge them. This is intentional per the ticket spec.
2. **`tiles_dict` not in SimState**: Deliberately excluded (rendering only). If any future simulation code needs raw tile data, it would need to be added. Currently no use case.
3. **Boss injection hardcoded to "skybridge"**: If stage names change or new boss stages are added, this must be updated. This matches the existing `main.py` pattern (`stage_num == 3`).

## No Critical Issues

Nothing requires human intervention. The implementation is straightforward, follows the ticket and spec exactly, and all tests pass with zero regressions.
