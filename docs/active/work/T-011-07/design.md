# T-011-07 Design: CI Pytest Gate

## Decision 1: CI Platform

**Chosen: GitHub Actions**

The ticket specifies GitHub Actions. No alternatives considered.

## Decision 2: Workflow Trigger Events

**Chosen: `on: [push, pull_request]`**

Matches the ticket's specification. Runs on every push (catches broken commits on any branch) and every PR (gates merges). No branch filtering needed — the repo is small and tests are fast (~11s local).

**Rejected:**
- `on: pull_request` only — misses broken pushes to main.
- Adding `workflow_dispatch` — unnecessary complexity for a test gate.

## Decision 3: UV Setup Strategy

**Chosen: `astral-sh/setup-uv@v4` + `uv sync`**

The ticket provides this exact pattern. `setup-uv` installs uv, then `uv sync` installs all default + dev dependencies (pytest, librosa). This is the canonical uv-in-CI approach.

**Rejected:**
- `pip install` — would require maintaining a separate requirements.txt.
- `uv sync --group dev` — `uv sync` already includes the default dev group. Explicit `--group dev` is redundant with uv's default behavior (dev dependencies are included by default).
- `uv sync --no-group train` — train group isn't synced by default (only dev is), so this is unnecessary.

## Decision 4: Python Version Strategy

**Chosen: Single version, `python-version: "3.13"`**

The project requires `>=3.10` per pyproject.toml. Testing a single version keeps CI fast and simple. 3.13 matches local development (the git status shows Python 3.13.0). Matrix testing across 3.10-3.13 is unnecessary overhead for a game project.

**Rejected:**
- Matrix `[3.10, 3.11, 3.12, 3.13]` — adds 3x CI time for minimal benefit. A game isn't a library.
- No `python-version` at all (use system default) — less reproducible.

## Decision 5: Pytest Invocation

**Chosen: `uv run pytest tests/ -x --tb=short`**

Per the ticket. `-x` stops at first failure (fail fast). `--tb=short` keeps CI logs readable.

**Enhancement:** Add `-q` for quieter output? No — `--tb=short` is sufficient, and verbose test names help debug CI failures.

## Decision 6: Pytest Markers (Stretch Goal)

**Chosen: Implement markers**

Three custom markers as specified in the ticket:

| Marker | Targets | Purpose |
|--------|---------|---------|
| `@pytest.mark.smoke` | test_walkthrough.py tests | Fast smoke tests (~1s) |
| `@pytest.mark.regression` | test_regression.py tests | Full regression gate (~2s) |
| `@pytest.mark.slow` | None currently; reserved | Future benchmarks |

**Rationale:** Low cost (a few lines in pyproject.toml + a few decorators). Enables selective test runs: `pytest -m smoke` for fast feedback, `pytest -m regression` for the gate.

**CI does NOT filter by marker** — it runs all tests. Markers are for developer convenience and future CI matrix splits.

**Registration:** Add `[tool.pytest.ini_options]` to pyproject.toml with `markers` list. This suppresses pytest's `PytestUnknownMarkWarning`.

## Decision 7: Pyxel in CI

**Chosen: Install pyxel normally, rely on architecture**

Pyxel is a core dependency. The manylinux wheel includes bundled SDL2/etc. Tests don't call pyxel rendering functions. No special handling needed.

**Rejected:**
- Mocking pyxel — unnecessary, it imports fine.
- Excluding pyxel from CI deps — would break imports of modules that `import pyxel` at top level (audio, renderer).
- Adding `--no-header` or pyxel-specific CI flags — not needed.

## Decision 8: Caching

**Chosen: Enable uv cache via `setup-uv`'s built-in caching**

`astral-sh/setup-uv@v4` caches the uv tool and dependency downloads by default. No additional `actions/cache` step needed. This keeps dependency installation fast on subsequent runs.

## Decision 9: Workflow Structure

**Chosen: Single job, single step for tests**

The test suite is fast enough (~11s) that splitting into parallel jobs is unnecessary. One job:

```
checkout → setup-uv → uv sync → pytest
```

**Rejected:**
- Separate jobs for smoke/regression/full — adds queue overhead, not worth it for an 11s suite.
- Separate lint job — no linter configured in the project.
- Upload test results as artifacts — overkill for now.

## Design Summary

Minimal, focused CI configuration:

1. **New file:** `.github/workflows/test.yml` — 4-step workflow.
2. **Modify:** `pyproject.toml` — add `[tool.pytest.ini_options]` with marker definitions.
3. **Modify:** `tests/test_regression.py` — add `@pytest.mark.regression` to test functions.
4. **Modify:** `tests/test_walkthrough.py` — add `@pytest.mark.smoke` to test functions.
5. **Verify:** Run full suite locally to confirm no regressions.
