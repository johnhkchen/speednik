# T-011-07 Progress: CI Pytest Gate

## Completed Steps

### Step 1: Add pytest marker configuration to pyproject.toml
- Added `[tool.pytest.ini_options]` with `smoke`, `regression`, `slow` markers.
- No deviations from plan.

### Step 2: Add `@pytest.mark.regression` to test_regression.py
- Added marker to `TestRegression` class (covers all 45 parametrized tests).
- Verified: `pytest -m regression --collect-only` → 45 tests collected.

### Step 3: Add `@pytest.mark.smoke` to test_walkthrough.py
- Added marker to `TestWalkthrough`, `TestSpindashReachesGoal`, `TestHillsideNoDeath`.
- Verified: `pytest -m smoke --collect-only` → 51 tests collected.

### Step 4: Create `.github/workflows/test.yml`
- Created `.github/workflows/` directory.
- Workflow: checkout → setup-uv (python 3.13) → uv sync → pytest -x --tb=short.
- YAML validated with `yaml.safe_load()`.

### Step 5: Run full test suite
- `uv run pytest tests/ -x --tb=short` → **1,277 passed, 16 skipped, 5 xfailed in 10.83s**.
- Identical results to pre-change baseline. No regressions.

### Step 6: Verify marker filtering
- `pytest -m regression` → 45 tests (correct).
- `pytest -m smoke` → 51 tests (correct).

## Remaining Steps

None. All steps complete.
