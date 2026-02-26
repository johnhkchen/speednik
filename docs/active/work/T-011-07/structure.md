# T-011-07 Structure: CI Pytest Gate

## File Changes

### New Files

#### `.github/workflows/test.yml`

GitHub Actions workflow definition.

```
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.13"
      - run: uv sync
      - run: uv run pytest tests/ -x --tb=short
```

Single job, four steps. No matrix, no caching config (setup-uv handles it), no artifacts.

### Modified Files

#### `pyproject.toml`

Add pytest configuration section after the existing `[dependency-groups]` block:

```toml
[tool.pytest.ini_options]
markers = [
    "smoke: walkthrough smoke tests (fast, catch gross regressions)",
    "regression: full regression suite (medium, the main gate)",
    "slow: benchmarks or exhaustive tests (optional in CI)",
]
```

No other changes to pyproject.toml. No testpaths or other pytest options — default discovery works.

#### `tests/test_regression.py`

Add `@pytest.mark.regression` decorator to all 5 test functions:
- `test_invariants`
- `test_camera_no_oscillation`
- `test_forward_progress`
- `test_deaths_within_bounds`
- `test_results_logged`

These are all parametrized over `(stage, strategy)` — the marker goes on the function, covering all 45 parametrized cases.

Import: `import pytest` (already imported for parametrize).

#### `tests/test_walkthrough.py`

Add `@pytest.mark.smoke` decorator to all test functions in this module.

Import: `import pytest` (need to verify if already imported).

### Unchanged Files

Everything else. No conftest.py needed. No changes to source code. No changes to justfile (could add `test` recipe but out of scope).

## Module Boundaries

No new modules. The workflow file is standalone YAML. Marker decorators are pure metadata — no runtime behavior change.

## Interface

After this change:
- `uv run pytest tests/` — runs all 1,298 tests (unchanged).
- `uv run pytest tests/ -m smoke` — runs only smoke-marked walkthrough tests.
- `uv run pytest tests/ -m regression` — runs only regression-marked tests (45).
- `uv run pytest tests/ -m "not slow"` — runs everything except slow (same as all, currently).
- GitHub Actions runs all tests on push/PR.

## Ordering

1. pyproject.toml marker config (must exist before markers are used, to avoid warnings).
2. Test file marker decorators (references the registered markers).
3. Workflow file (independent of markers — runs all tests regardless).

Order 1→2 matters for clean pytest output. Step 3 is independent.
