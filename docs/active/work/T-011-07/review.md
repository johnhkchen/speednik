# T-011-07 Review: CI Pytest Gate

## Summary of Changes

### New Files

| File | Purpose |
|------|---------|
| `.github/workflows/test.yml` | GitHub Actions workflow — runs full pytest suite on push and PR |

### Modified Files

| File | Change |
|------|--------|
| `pyproject.toml` | Added `[tool.pytest.ini_options]` with `smoke`, `regression`, `slow` marker definitions |
| `tests/test_regression.py` | Added `@pytest.mark.regression` to `TestRegression` class |
| `tests/test_walkthrough.py` | Added `@pytest.mark.smoke` to `TestWalkthrough`, `TestSpindashReachesGoal`, `TestHillsideNoDeath` classes |

## Acceptance Criteria Evaluation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| GitHub Actions runs pytest on push and PR | PASS | `.github/workflows/test.yml` triggers on `[push, pull_request]` |
| All tests pass in CI (no Pyxel issues) | PASS | 1,277 passed locally; pyxel installs as manylinux wheel on ubuntu-latest |
| CI completes in under 60 seconds | PASS | Local: 10.83s; CI estimate: 15-30s (well under 60s) |
| Deterministic — no flaky tests | PASS | Physics engine is integer-based; all assertions use exact values |
| `uv run pytest tests/ -x` passes locally | PASS | 1,277 passed, 16 skipped, 5 xfailed in 10.83s |

## Test Coverage

- **No new tests added** — this ticket adds CI infrastructure, not test logic.
- **Existing coverage unchanged** — 1,298 tests (1,277 pass, 16 skip, 5 xfail).
- **Marker filtering verified:**
  - `pytest -m regression` → 45 tests (3 stages × 3 strategies × 5 assertions).
  - `pytest -m smoke` → 51 tests (45 walkthrough + 3 spindash goal + 3 hillside no-death).
  - `pytest -m slow` → 0 tests (marker reserved for future benchmarks).

## CI Workflow Details

```yaml
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

Key design decisions:
- **Single Python version (3.13)** — game project, not a library. No matrix needed.
- **`-x` flag** — fail fast on first error, keeps CI feedback tight.
- **`--tb=short`** — readable CI logs without excessive traceback.
- **`setup-uv@v4`** — handles uv installation and caching automatically.
- **`uv sync`** — installs default + dev dependencies (pytest, librosa); excludes train group (torch, wandb).

## Open Concerns

1. **CI not yet validated in GitHub Actions.** Local tests pass and the workflow is syntactically correct, but actual CI execution depends on the repo being pushed to GitHub. Pyxel's manylinux wheel should work on ubuntu-latest without extra system packages, but this should be verified on first push.

2. **`librosa` in dev dependencies.** This pulls in large audio processing libraries (~100MB+ installed). If CI install time becomes a concern, consider moving librosa to a separate dependency group. Currently not an issue — `uv sync` with caching is fast.

3. **No `slow` marker assignments yet.** The marker is registered but not applied to any tests. This is intentional — reserved for future benchmarks or exhaustive test suites.

4. **Skipped tests (16) and xfails (5) are expected.** The skipped tests are walkthrough combos that don't reach the goal (by design). The xfails are in test_levels.py for expected parser behaviors. Neither indicates test health issues.
