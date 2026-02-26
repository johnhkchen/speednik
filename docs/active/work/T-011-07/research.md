# T-011-07 Research: CI Pytest Gate

## Current State

### Test Suite

36 test modules, 1,298 total tests. Local run: **1,277 passed, 16 skipped, 5 xfailed in 10.87s**.

| Category | Files | Tests | Example |
|----------|-------|-------|---------|
| Core simulation | test_simulation, test_physics, test_terrain | ~111 | sim_step, collision |
| Player/enemies | test_player, test_enemies, test_rings | ~107 | movement, AI |
| Stage-specific | test_hillside, test_pipeworks, test_skybridge | ~75 | per-stage validation |
| Integration | test_integration, test_hillside_integration | ~47 | full-loop runs |
| Regression (T-011-06) | test_regression | 45 | 3 stages × 3 strategies × 5 checks |
| Gymnasium/RL | test_env, test_observation, test_agents | ~136 | SpeednikEnv, obs |
| Scenarios | test_scenarios, test_walkthrough | ~106 | YAML scenario runner |
| Camera | test_camera, test_camera_stability | ~53 | tracking, oscillation |
| Build tools | test_svg2stage, test_profile2stage | ~182 | SVG→stage pipeline |
| Framework | test_invariants, test_qa_framework, test_grids | ~70 | physics validation |
| Presentation | test_renderer, test_audio, test_devpark, test_debug | ~93 | render/audio stubs |
| Misc | test_harness, test_game_state, test_levels, test_web_export | ~73 | helpers, game FSM |

### Pyxel Import Safety

**Architecture enforces clean separation:**

- **Layers 1-4** (physics, simulation, agents, RL framework): Zero pyxel imports.
- **Layer 5** (main.py, renderer.py, audio.py, devpark.py): Import pyxel.

Tests only exercise Layers 1-4. A few tests (test_audio, test_renderer, test_devpark) import Layer 5 modules, but those modules only call pyxel at runtime (inside `draw()`, `update()`, `play_sound()` callbacks), never at module import time. Since pyxel is a core project dependency, it will be installed in CI — no import errors.

**Verified:** `grep -rE "^import pyxel|^from pyxel" tests/` returns zero matches.

### CI Configuration

- **No `.github/` directory exists** — no workflows, no CI at all.
- **No pytest configuration** in pyproject.toml (no `[tool.pytest.ini_options]`).
- **No conftest.py** in tests/.
- **No custom markers** registered.

### pyproject.toml Dependencies

```toml
dependencies = ["pyxel", "numpy", "gymnasium>=1.2.3", "pyyaml"]

[dependency-groups]
dev = ["librosa>=0.11.0", "pytest>=9.0.2"]
train = ["torch>=2.0", "tyro", "wandb", "tensorboard"]
```

CI needs only the default + dev groups. The `train` group (torch, wandb) is not needed for tests.

### justfile

No test recipe. Only `up` (build/serve) and `debug` (build with debug HUD). Could add a `test` recipe but not required for this ticket.

### Existing Markers in Use

- `@pytest.mark.parametrize` — 16 uses across test files.
- `@pytest.mark.xfail` — 5 uses (expected failures in test_levels.py).
- `@pytest.mark.skipif` — 1 use.
- No custom markers (`smoke`, `regression`, `slow`) defined anywhere.

### Performance Profile

- Full suite: **~11s local** (Apple Silicon). CI (ubuntu-latest) typically 1.5-3x slower → ~16-30s.
- Regression suite alone: < 2s (sim runs at ~20K+ updates/sec).
- Well within the 60s CI requirement.

### Determinism

Physics engine is fully deterministic: same inputs → same outputs. No randomness, no floating-point non-determinism (integer physics). All assertions are exact value checks.

### Key Files

| Path | Role |
|------|------|
| `tests/test_regression.py` | Crown jewel — 45-test regression gate |
| `tests/test_walkthrough.py` | Smoke-level walkthrough tests |
| `pyproject.toml` | Needs pytest marker config |
| `.github/workflows/test.yml` | Needs to be created |

### Constraints

1. Pyxel requires system-level libs on Linux (SDL2, etc.). The `pyxel` pip package bundles these, but CI may need them. `astral-sh/setup-uv` handles Python; pyxel's manylinux wheel should work on ubuntu-latest without extra apt packages.
2. The `librosa` dev dependency pulls in large audio processing libs — acceptable for CI but adds to install time.
3. No secrets or env vars needed for tests.
4. All test data (stages, YAML scenarios) is committed to the repo.
