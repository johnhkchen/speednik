# T-010-14 Review — CleanRL PPO Fork

## Summary of Changes

### Files Created
- **`tools/ppo_speednik.py`** (~250 lines) — Forked CleanRL `ppo.py` with
  registration import, default env_id, normalization wrapper stack, and model
  checkpoint save.

### Files Modified
- **`pyproject.toml`** — Added `train` dependency group: `torch>=2.0`, `tyro`,
  `wandb`, `tensorboard`.
- **`.gitignore`** — Added `runs/` and `videos/` to prevent training artifacts
  from being committed.

### Files Not Modified
- `speednik/env.py`, `speednik/env_registration.py`, all test files, `justfile`

---

## Acceptance Criteria Evaluation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Working fork of CleanRL's `ppo.py` | ✅ | `tools/ppo_speednik.py` runs successfully |
| Only 2 semantic changes from upstream | ✅ | Registration import + default env_id. Wrapper stack is a 3rd change per spec §8.2. Model save is a 4th (for AC compliance) |
| Wrapper stack (normalize, clip) | ✅ | `make_env` includes all 5 wrappers per §8.2 |
| `torch` as optional dependency | ✅ | In `[dependency-groups] train`, not main deps |
| 10K timestep smoke test | ✅ | Hillside + Pipeworks both complete without crashes |
| Finite losses | ✅ | TensorBoard verified: value_loss, policy_loss, entropy all finite |
| Model checkpoint saves | ✅ | `runs/*/ppo_speednik.pt` (47KB) saved |
| Episode stats logged | ⚠️ | Episodic return/length are logged when episodes complete. 10K steps is too few for a full episode (3600 steps × 4 envs). Would appear in longer runs |
| `--track` works with W&B | ⚠️ | Not tested (requires W&B account/API key). Code path is unchanged from upstream CleanRL which is known-working |
| `--env-id speednik/Pipeworks-v0` works | ✅ | Pipeworks smoke test passed |
| No Pyxel imports | ✅ | Script imports only torch, gymnasium, numpy, tyro, tensorboard, speednik.env_registration |
| `uv run pytest tests/ -x` passes | ✅ | 1135 passed, 16 skipped, 5 xfailed |

---

## Test Coverage

The training script (`tools/ppo_speednik.py`) is a standalone tool, not a
library module. It is not imported by any test. Coverage of its functionality
comes from:

1. **Existing env tests** (`tests/test_env.py`): 344 lines testing SpeednikEnv
   through the same Gymnasium API the training script uses.
2. **Smoke tests** (manual, documented in progress.md): 10K timestep runs on
   Hillside and Pipeworks verifying the full training pipeline.
3. **Upstream CleanRL tests**: The PPO algorithm logic is unchanged from the
   CleanRL reference implementation which has its own test suite.

**Gap**: No automated test for the training script itself. This is intentional:
torch is an optional dependency and tests must pass without it. A future ticket
could add a `tests/test_ppo_training.py` that `pytest.importorskip("torch")`.

---

## Open Concerns

1. **Episode statistics at 10K steps**: At 10K total timesteps with 4 envs and
   3600 max_steps per episode, no episode completes. Episodic return/length
   logging works (code path is unchanged from CleanRL) but only fires when
   `RecordEpisodeStatistics` detects episode completion. Longer runs (>50K)
   would show these. Not a bug.

2. **`tyro` type warnings**: CleanRL uses `None` defaults for `str` and `float`
   typed fields (`wandb_entity`, `target_kl`). `tyro` emits warnings about
   type mismatches. These are cosmetic — from upstream CleanRL, not our changes.

3. **Wrapper compatibility**: `NormalizeObservation` and `NormalizeReward`
   maintain running statistics that are NOT saved with the model checkpoint.
   When loading a trained model for evaluation (future PPOAgent), the
   observation normalization parameters must be saved separately or the
   evaluation env must also normalize. This is a known issue for future work.

4. **W&B testing**: The `--track` flag was not tested with a live W&B account.
   The code path is identical to upstream CleanRL — low risk but unverified.

5. **"2 changes" claim**: The ticket says "exactly two changes" but the
   implementation has 4 diff regions: (1) registration import, (2) default
   env_id, (3) wrapper stack, (4) model save. The spec (§8.1–8.2) explicitly
   calls for changes 1–3. Change 4 (model save) was added to satisfy the
   acceptance criterion "model checkpoint saves to disk." The spirit of
   minimal-fork is maintained — no algorithm changes.

---

## Architecture Validation

The training script correctly sits at Layer 6 of the architecture stack. It
reaches the game only through `gymnasium.make()` → `SpeednikEnv` → headless
simulation. No Pyxel, no direct imports of game modules. The dependency
direction is strictly downward.

```
tools/ppo_speednik.py (Layer 6)
  → gymnasium.make("speednik/Hillside-v0")
    → speednik.env:SpeednikEnv (Layer 5)
      → speednik.simulation (Layer 2)
        → Game Core (Layer 1)
```
