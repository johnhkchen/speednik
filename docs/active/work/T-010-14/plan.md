# T-010-14 Plan — CleanRL PPO Fork

## Step 1: Add Training Dependency Group

**File**: `pyproject.toml`

Add `train` to `[dependency-groups]`:
```toml
train = ["torch>=2.0", "tyro", "wandb", "tensorboard"]
```

**Verify**: `uv sync --group train` resolves and installs all training deps.

---

## Step 2: Create `tools/ppo_speednik.py`

**File**: `tools/ppo_speednik.py`

Copy CleanRL's `ppo.py` source and apply changes:

1. Add `import speednik.env_registration` after third-party imports
2. Change `Args.env_id` default to `"speednik/Hillside-v0"`
3. Replace `make_env` wrapper stack with normalize/clip wrappers
4. Add `torch.save(agent.state_dict(), model_path)` before `envs.close()`

**Verify**: File is syntactically valid (`python -c "import ast; ast.parse(open('tools/ppo_speednik.py').read())"`)

---

## Step 3: Verify Existing Tests Pass

**Command**: `uv run pytest tests/ -x`

Confirm that adding the training dependency group and new script does not
break any existing tests. The script is not imported anywhere, so this
should be trivially true.

---

## Step 4: Smoke Test (10K timesteps)

**Command**:
```bash
uv run python tools/ppo_speednik.py \
    --env-id speednik/Hillside-v0 \
    --total-timesteps 10000 \
    --num-envs 4 \
    --num-steps 128
```

**Verify**:
- [ ] No crashes during training
- [ ] Loss values printed are finite (not NaN/Inf)
- [ ] Episode statistics logged (episodic_return, episodic_length in stdout)
- [ ] Model checkpoint saved to `runs/*/ppo_speednik.pt`
- [ ] TensorBoard logs created in `runs/`
- [ ] SPS (steps per second) printed each iteration

---

## Step 5: Cross-Stage Verification

**Command**:
```bash
uv run python tools/ppo_speednik.py \
    --env-id speednik/Pipeworks-v0 \
    --total-timesteps 10000 \
    --num-envs 4 \
    --num-steps 128
```

**Verify**: Same criteria as Step 4 — confirms `--env-id` override works
and Pipeworks stage is functional for training.

---

## Step 6: Clean Up

- Remove `runs/` directory created by smoke tests (transient artifacts)
- Ensure `runs/` is in `.gitignore` (or document that it should be)

---

## Testing Strategy

**Unit tests**: None needed for this ticket. The script is a standalone tool,
not a library module. It exercises `SpeednikEnv` through the standard Gymnasium
API, which is already thoroughly tested in `tests/test_env.py`.

**Integration test**: The smoke test (Step 4) IS the integration test. It
validates the full stack: registration → env creation → wrapper stack →
vectorized env → PPO training loop → model save.

**Regression test**: Step 3 ensures existing tests still pass.

**Acceptance verification**: Steps 4–5 directly verify the acceptance criteria:
- Working fork: Steps 2, 4
- Two changes only: Step 2 (manual audit)
- Wrapper stack: Step 2 (code review)
- Optional dependency: Steps 1, 3
- Smoke test / finite losses / checkpoint / episode stats: Step 4
- Cross-stage: Step 5
- No Pyxel: Step 2 (no Pyxel import in script)
- Tests pass: Step 3
