# T-010-14 Research — CleanRL PPO Fork

## Scope

Fork CleanRL's `ppo.py` into `tools/ppo_speednik.py` with exactly two changes,
add training dependencies as optional, verify with a smoke test.

---

## Existing Codebase

### Environment Registration (`speednik/env_registration.py`)

Three environments registered via `gymnasium.register()`:
- `speednik/Hillside-v0` — 3600 max steps
- `speednik/Pipeworks-v0` — 5400 max steps
- `speednik/Skybridge-v0` — 7200 max steps

All share `SpeednikEnv` entry point with stage/max_steps kwargs. The module
must be imported to trigger registration — this is the purpose of Change 1.

### Gymnasium Environment (`speednik/env.py`)

`SpeednikEnv` implements the standard Gymnasium interface:
- **Observation**: `Box(shape=(12,), dtype=float32)` — position, velocity, ground
  state, facing, progress, goal distance, time
- **Action**: `Discrete(8)` — NOOP, LEFT, RIGHT, JUMP, LEFT+JUMP, RIGHT+JUMP,
  DOWN (spindash), DOWN+JUMP (charge)
- **Reward signal**: progress delta × 10, speed bonus, goal completion bonus,
  death penalty, ring bonus, time penalty
- **Info dict**: frame, x, y, max_x, rings, deaths, goal_reached

CleanRL PPO expects `Discrete` action + `Box` observation → exact match.

### Project Dependencies (`pyproject.toml`)

Current structure:
```toml
dependencies = ["pyxel", "numpy", "gymnasium>=1.2.3", "pyyaml"]
[project.optional-dependencies]
dev = ["pytest"]
[dependency-groups]
dev = ["librosa>=0.11.0", "pytest>=9.0.2"]
```

No `train` group exists yet. The project uses `uv` for dependency management.
`[dependency-groups]` is PEP 735 (uv-native); `[project.optional-dependencies]`
is PEP 621 (pip-compatible). Both are valid — the project already uses both.

### Tools Directory (`tools/`)

Contains: `analyze_mp3s.py`, `profile2stage.py`, `svg2stage.py`. Training script
will live here as `ppo_speednik.py`.

### Spec Requirements (`docs/specs/scenario-testing-system.md` §8)

§8.1: Two changes only — registration import + default env_id.
§8.2: Wrapper stack — RecordEpisodeStatistics, NormalizeObservation,
TransformObservation (clip ±10), NormalizeReward (gamma=0.99),
TransformReward (clip ±10).
§8.3: Training invocation via `uv run python tools/ppo_speednik.py`.
§8.4: Post-training, model loads via PPOAgent (future ticket scope).

### CleanRL Upstream (`ppo.py`)

~230 lines. Uses `tyro` for CLI args, `torch` for training, `tensorboard`
for logging, optional `wandb` for tracking. Key components:
- `Args` dataclass — all hyperparameters with `tyro.cli()` parsing
- `make_env()` — creates environments with optional video recording
- `Agent(nn.Module)` — 64-unit MLP actor-critic
- Main loop — PPO with GAE, clipped surrogate loss, value clipping

Dependencies: `torch`, `tyro`, `gymnasium`, `numpy`, `tensorboard`.
Optional: `wandb` (imported lazily when `--track` is set).

### Test Suite

39 test files under `tests/`. Tests use `pytest`, no torch dependency.
Acceptance criterion: `uv run pytest tests/ -x` must pass without training
dependencies installed. This means `tools/ppo_speednik.py` must not be
imported by any test.

---

## Constraints & Boundaries

1. **Fork discipline**: Only 2 lines changed from upstream. The wrapper stack
   change is larger but is part of the existing `make_env` function.
2. **No Pyxel in training**: Environment is headless; `env.py` never imports
   Pyxel. Training script has no Pyxel dependency.
3. **Optional deps**: `torch`, `wandb`, `tensorboard`, `tyro` are training-only.
   Must not break base install or test suite.
4. **Model saving**: CleanRL saves to `runs/{run_name}/` by default. No custom
   checkpoint logic needed for this ticket.
5. **Video capture**: CleanRL supports `--capture-video` but SpeednikEnv only
   supports `render_mode="human"/"rgb_array"` in metadata — video recording
   may not work without a render implementation. Not required by acceptance
   criteria.

---

## Open Questions

- `tyro` is a CleanRL dependency not currently in the project. Must be added
  to the train dependency group.
- The upstream `ppo.py` uses `gymnasium` (not `gym`) — matches our project.
- `NormalizeObservation` / `NormalizeReward` maintain running statistics. These
  are not saved with the model by default — future concern for PPOAgent, not
  this ticket.
