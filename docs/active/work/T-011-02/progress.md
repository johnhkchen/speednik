# T-011-02 Progress: physics-invariant-checker

## Completed

1. Created `speednik/invariants.py` with:
   - `Violation` dataclass (frame, invariant, details, severity)
   - `SnapshotLike` Protocol for duck-typed snapshot acceptance
   - `check_invariants()` public API
   - Six private checker functions covering all invariant categories

2. Created `tests/test_invariants.py` with:
   - 22 tests across 8 test classes
   - Covers all invariant categories (position, solid tile, velocity, spikes, ground, quadrants)
   - Clean trajectory integration test
   - No-Pyxel-import test
   - Helper factories: `make_snap()`, `make_sim()`, tile lookup builders

3. All 22 tests pass: `uv run pytest tests/test_invariants.py -x` → 22 passed in 0.02s

## Deviations from plan

- None. Plan followed step by step.

## Remaining

- None. All implementation complete.
