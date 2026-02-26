# T-010-08 Plan: env-registration-and-validation

## Step 1: Create `speednik/env_registration.py`

Create the registration module with three `gym.register()` calls.

```python
import gymnasium as gym

gym.register(
    id="speednik/Hillside-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "hillside", "max_steps": 3600},
    max_episode_steps=3600,
)

gym.register(
    id="speednik/Pipeworks-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "pipeworks", "max_steps": 5400},
    max_episode_steps=5400,
)

gym.register(
    id="speednik/Skybridge-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "skybridge", "max_steps": 7200},
    max_episode_steps=7200,
)
```

**Verify:** `python -c "import speednik.env_registration; import gymnasium; print(gymnasium.make('speednik/Hillside-v0'))"`

## Step 2: Add registration tests to `tests/test_env.py`

Append these test functions after existing tests:

### 2a: Registration smoke test

```python
def test_registration_creates_envs():
    import speednik.env_registration  # noqa: F401
    import gymnasium as gym
    for env_id in ["speednik/Hillside-v0", "speednik/Pipeworks-v0", "speednik/Skybridge-v0"]:
        env = gym.make(env_id)
        obs, info = env.reset()
        assert obs.shape == (OBS_DIM,)
        env.close()
```

### 2b: check_env for all three stages via registry

```python
def test_check_env_hillside_registered():
    import speednik.env_registration  # noqa: F401
    import gymnasium as gym
    from gymnasium.utils.env_checker import check_env
    env = gym.make("speednik/Hillside-v0")
    check_env(env.unwrapped)

# Same for pipeworks, skybridge
```

### 2c: Random action loop (100 steps)

```python
def test_random_actions_100_steps():
    env = SpeednikEnv(stage="hillside")
    obs, info = env.reset()
    for _ in range(100):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == (OBS_DIM,)
        assert isinstance(reward, float)
        if terminated or truncated:
            obs, info = env.reset()
```

### 2d: Finite observations check

```python
def test_observations_finite_during_random_play():
    env = SpeednikEnv(stage="hillside")
    obs, _ = env.reset()
    assert np.all(np.isfinite(obs))
    for _ in range(100):
        action = env.action_space.sample()
        obs, _, terminated, truncated, _ = env.step(action)
        assert np.all(np.isfinite(obs)), f"Non-finite obs: {obs}"
        if terminated or truncated:
            obs, _ = env.reset()
            assert np.all(np.isfinite(obs))
```

### 2e: Reset after termination

```python
def test_reset_after_termination():
    env = SpeednikEnv()
    env.reset()
    env.sim.player.state = PlayerState.DEAD
    _, _, terminated, _, _ = env.step(ACTION_NOOP)
    assert terminated
    obs, info = env.reset()
    assert obs.shape == (OBS_DIM,)
    assert info["frame"] == 0
```

### 2f: No-Pyxel guard for registration module

```python
def test_no_pyxel_import_env_registration():
    import speednik.env_registration as mod
    source = Path(inspect.getfile(mod)).read_text()
    assert "import pyxel" not in source
    assert "from pyxel" not in source
```

## Step 3: Run full test suite

```bash
uv run pytest tests/test_env.py -x -v
```

Verify all existing tests still pass and all new tests pass.

## Step 4: Run full project test suite

```bash
uv run pytest tests/ -x -v
```

Verify no regressions across the entire test suite.

## Testing Strategy

| Test | What it validates |
|------|-------------------|
| `test_registration_creates_envs` | `gym.make()` works for all 3 env IDs |
| `test_check_env_*_registered` | Gymnasium's own validator passes per stage |
| `test_random_actions_100_steps` | Stability under random input |
| `test_observations_finite_during_random_play` | No NaN/Inf values |
| `test_reset_after_termination` | Clean recovery after episode end |
| `test_no_pyxel_import_env_registration` | Headless safety |

## Commit Strategy

Single atomic commit: create `env_registration.py` + add tests. Small change set.
