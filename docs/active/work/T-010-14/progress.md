# T-010-14 Progress — CleanRL PPO Fork

## Step 1: Add Training Dependency Group ✅

Added `train` group to `pyproject.toml`:
```toml
train = ["torch>=2.0", "tyro", "wandb", "tensorboard"]
```

`uv sync --group train` installed torch 2.10.0, tyro 1.0.8, wandb 0.25.0,
tensorboard 2.20.0.

## Step 2: Create `tools/ppo_speednik.py` ✅

Created forked CleanRL `ppo.py` with four changes from upstream:
1. Added `import speednik.env_registration` at top
2. Changed `Args.env_id` default to `"speednik/Hillside-v0"`
3. Replaced `make_env` wrapper stack with NormalizeObservation,
   NormalizeReward, and clip transforms
4. Added `torch.save(agent.state_dict(), model_path)` before `envs.close()`

Comment header documents all changes from upstream.

## Step 3: Verify Existing Tests Pass ✅

```
1135 passed, 16 skipped, 5 xfailed, 9 warnings in 3.93s
```

No regressions from adding training deps or the new script.

## Step 4: Smoke Test — Hillside ✅

```bash
uv run python tools/ppo_speednik.py \
    --env-id speednik/Hillside-v0 \
    --total-timesteps 10000 --num-envs 4 --num-steps 128
```

Results:
- No crashes
- 19 iterations completed
- SPS: 4359 → 9273 (stabilized ~9K steps/sec)
- Losses all finite:
  - value_loss: [0.0075, 2.5381]
  - policy_loss: [-0.0084, -0.0001]
  - entropy: [2.0761, 2.0791]
- Model saved: `runs/.../ppo_speednik.pt` (47KB)
- TensorBoard events logged

No episodic_return logged — expected: 10K total steps across 4 envs with
3600 max_steps/episode means no episode completed fully. This is fine for
a smoke test.

## Step 5: Cross-Stage — Pipeworks ✅

```bash
uv run python tools/ppo_speednik.py \
    --env-id speednik/Pipeworks-v0 \
    --total-timesteps 10000 --num-envs 4 --num-steps 128
```

Results: same success profile. SPS ~8K, finite losses, model saved.

## Step 6: Clean Up ✅

- Removed `runs/` directory from smoke tests
- Added `runs/` and `videos/` to `.gitignore`

## Deviations from Plan

1. Added `tyro` to train dependencies (not in original ticket, but required
   by CleanRL's argument parsing — identified in research phase)
2. Added `runs/` and `videos/` to `.gitignore` (not in plan but necessary
   to prevent training artifacts from being committed)
3. No episodic_return/episodic_length in stdout for 10K smoke test — episodes
   are too long (3600 steps) to complete in 10K total timesteps. This is
   expected behavior, not a bug. A longer run (>50K steps) would show episodes.
