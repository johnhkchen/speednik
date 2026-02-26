# T-011-07 Plan: CI Pytest Gate

## Step 1: Add pytest marker configuration to pyproject.toml

Add `[tool.pytest.ini_options]` section with three marker definitions: `smoke`, `regression`, `slow`.

**Verify:** `uv run pytest --markers` shows the three custom markers without warnings.

## Step 2: Add `@pytest.mark.regression` to test_regression.py

Read test_regression.py, identify all test functions, add the decorator to each.

**Verify:** `uv run pytest tests/test_regression.py -m regression --collect-only` collects exactly 45 tests.

## Step 3: Add `@pytest.mark.smoke` to test_walkthrough.py

Read test_walkthrough.py, identify all test functions, add the decorator to each.

**Verify:** `uv run pytest tests/test_walkthrough.py -m smoke --collect-only` collects the expected smoke tests.

## Step 4: Create `.github/workflows/test.yml`

Create the directory structure and workflow file per the ticket spec.

**Verify:** YAML is syntactically valid. `python -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))"` succeeds.

## Step 5: Run full test suite locally

Execute `uv run pytest tests/ -x --tb=short` — the exact command CI will run.

**Verify:** All tests pass. No new warnings from markers. Total time < 30s.

## Step 6: Verify marker filtering works

- `uv run pytest -m smoke --collect-only` — shows only smoke tests.
- `uv run pytest -m regression --collect-only` — shows only regression tests (45).
- `uv run pytest -m "not slow" --collect-only` — shows all tests (none are marked slow).

**Verify:** Counts match expectations.

## Testing Strategy

- **No new test files.** This ticket adds CI infrastructure and markers, not new test logic.
- **Verification is the test:** The full suite passing locally with `pytest tests/ -x --tb=short` proves the CI command will work.
- **Marker verification:** `--collect-only` confirms markers filter correctly.
- **Determinism check:** Run the suite twice; results must be identical.
