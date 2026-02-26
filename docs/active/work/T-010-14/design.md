# T-010-14 Design — CleanRL PPO Fork

## Decision: Minimal Fork with Wrapper Stack Override

### Approach

Copy CleanRL's `ppo.py` verbatim, then apply exactly two semantic changes
plus one structural change (wrapper stack in `make_env`). This follows the
spec's §8.1–8.2 design precisely.

---

## Change Analysis

### Change 1: Registration Import

Add at top of file:
```python
import speednik.env_registration  # noqa: F401  # triggers gym.register()
```

**Rationale**: Without this import, `gym.make("speednik/Hillside-v0")` raises
`NamespaceNotFound`. The import is side-effect only (hence `noqa: F401`).

### Change 2: Default env_id

In `Args` dataclass:
```python
env_id: str = "speednik/Hillside-v0"  # was "CartPole-v1"
```

**Rationale**: Makes the default behavior train on Speednik without needing
`--env-id` every time. Still overridable via CLI for other stages.

### Change 3: Wrapper Stack in `make_env`

Replace the simple `RecordEpisodeStatistics` wrapper with the full
normalization stack from §8.2:

```python
def make_env(env_id, idx, capture_video, run_name):
    def thunk():
        if capture_video and idx == 0:
            env = gym.make(env_id, render_mode="rgb_array")
            env = gym.wrappers.RecordVideo(env, f"videos/{run_name}")
        else:
            env = gym.make(env_id)
        env = gym.wrappers.RecordEpisodeStatistics(env)
        env = gym.wrappers.NormalizeObservation(env)
        env = gym.wrappers.TransformObservation(
            env, lambda obs: np.clip(obs, -10, 10),
            observation_space=env.observation_space,
        )
        env = gym.wrappers.NormalizeReward(env, gamma=0.99)
        env = gym.wrappers.TransformReward(env, lambda r: np.clip(r, -10, 10))
        return env
    return thunk
```

**Rationale**: Observation normalization stabilizes gradients for the 12-dim
observation vector (components have different scales — position in hundreds,
velocity in single digits, booleans 0/1). Reward normalization handles the
mixed-magnitude reward signal (progress delta ~0.001–0.01, goal bonus 10–15,
death penalty –5). Clipping at ±10 prevents outliers from destabilizing
training.

---

## Alternatives Considered

### A) Import CleanRL as library dependency
**Rejected.** CleanRL is designed for forking, not importing. The library API
changes frequently and adds unnecessary dependency weight. A single copied
file with 2 changes is simpler to maintain.

### B) Write PPO from scratch
**Rejected.** CleanRL's ppo.py is the reference implementation — well-tested,
well-documented, W&B integration included. Rewriting would add bugs and lose
the community's years of debugging.

### C) Use Stable Baselines 3
**Rejected.** SB3 adds a heavy framework dependency with abstraction layers
that obscure the training loop. CleanRL's single-file approach keeps everything
visible and modifiable.

### D) Skip wrapper stack, use raw env
**Rejected.** Raw observations span wildly different scales. Without
normalization, the MLP would need much longer to learn. The spec explicitly
requires this wrapper stack.

---

## Dependency Strategy

Use `[dependency-groups]` (PEP 735) for training deps:

```toml
[dependency-groups]
dev = ["librosa>=0.11.0", "pytest>=9.0.2"]
train = ["torch>=2.0", "tyro", "wandb", "tensorboard"]
```

**Why `dependency-groups` over `optional-dependencies`**:
- Project already uses `dependency-groups` for dev
- `uv sync --group train` installs them
- Training deps are never needed by the package itself
- Consistent with existing pattern

**tyro** is required: CleanRL uses `tyro.cli(Args)` for argument parsing.
Must be in the train group.

---

## Model Checkpoint Behavior

CleanRL does not save model checkpoints by default in the standard `ppo.py`.
The model architecture is defined inline (the `Agent` class). For this ticket,
we accept that behavior — model checkpoints are a future concern (PPOAgent
integration). TensorBoard logs in `runs/` provide training visibility.

Note: The acceptance criteria mention "model checkpoint saves to disk." We will
add a simple `torch.save()` at the end of training to satisfy this. This is a
small addition beyond the two core changes but is necessary for the AC.

---

## Risk Assessment

- **Low risk**: Fork is mechanically simple. Two line changes + wrapper stack.
- **Medium risk**: Gymnasium wrapper compatibility — `NormalizeObservation` and
  `NormalizeReward` must work with our env's spaces. Verified: both accept
  `Box` observation space (ours) and arbitrary reward signals.
- **Low risk**: Dependency isolation — training deps in optional group won't
  affect base install or test suite.
