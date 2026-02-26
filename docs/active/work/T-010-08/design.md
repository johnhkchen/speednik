# T-010-08 Design: env-registration-and-validation

## Problem

SpeednikEnv works when directly instantiated but isn't discoverable through Gymnasium's standard `gym.make()` interface. RL training frameworks (CleanRL, SB3) expect registered environments.

## Options Considered

### Option A: Register in `speednik/__init__.py`

Put `gym.register()` calls in the package init so registration happens on any import of `speednik`.

**Pros:** Automatic — any `import speednik` triggers registration.
**Cons:** Couples registration to all imports. Anyone importing `speednik.main` (the Pyxel game) would also trigger Gymnasium import. Adds gymnasium as a hard import for the game itself.

**Rejected:** The game runtime should not require gymnasium. Registration should be opt-in.

### Option B: Separate `speednik/env_registration.py` module (chosen)

Dedicated module containing only `gym.register()` calls. Consumers do `import speednik.env_registration` to trigger registration.

**Pros:**
- Opt-in: only RL code imports it
- Matches ticket specification and spec §3.4
- No import side effects on the game
- Clear, single-responsibility module
- Standard pattern in gymnasium ecosystem

**Cons:** Requires explicit import before `gym.make()`.

**Chosen** because it matches the ticket, the spec, and gymnasium conventions.

### Option C: Entry points in pyproject.toml

Use `[project.entry-points."gymnasium.envs"]` for automatic discovery.

**Pros:** No explicit import needed.
**Cons:** Requires build/install step. `uv run` development flow may not pick it up reliably. More complex. Not specified in ticket.

**Rejected:** Over-engineered for current needs.

## Design Decision

### Registration Module

`speednik/env_registration.py` — a module-level script with three `gym.register()` calls:

```python
gym.register(
    id="speednik/Hillside-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "hillside"},
    max_episode_steps=3600,
)
```

Same pattern for Pipeworks (5400) and Skybridge (7200).

No functions, no classes — just top-level registration calls executed on import.

### Double-Truncation Handling

`gym.make()` wraps the env in `TimeLimit(max_episode_steps=N)`. The inner `SpeednikEnv` also has `max_steps` which defaults to 3600.

Two approaches:
1. **Pass a very large `max_steps` via kwargs** so the inner truncation never fires
2. **Leave it as-is** and accept that both can truncate

Decision: **Leave as-is.** The `kwargs` in `gym.register` only passes `stage`. The `SpeednikEnv.__init__` default of `max_steps=3600` means for Hillside both will truncate at 3600. For Pipeworks/Skybridge, the `TimeLimit` wrapper truncates first (at 5400/7200) while the inner env has a higher default. Actually — the inner default is 3600 for all stages, so for Pipeworks the inner truncation would fire at 3600 while `TimeLimit` is set to 5400.

**Revised decision:** Pass `max_steps` in kwargs to match `max_episode_steps`, so the inner env doesn't truncate before the wrapper:

```python
kwargs={"stage": "hillside", "max_steps": 3600},
kwargs={"stage": "pipeworks", "max_steps": 5400},
kwargs={"stage": "skybridge", "max_steps": 7200},
```

This ensures consistent behavior whether the env is used directly or via `gym.make()`.

### Test Strategy

Add to `tests/test_env.py`:

1. **Registration tests** — import module, verify `gym.make()` works for all three IDs
2. **check_env via registry** — `gym.make()` then `check_env(env.unwrapped)` for all three stages
3. **Random action loop** — 100 steps with random actions, verify obs shape, reward type, finite values
4. **Reset after termination** — drive to termination, reset, verify clean state
5. **Finite observations** — no NaN/Inf during random play

### No-Pyxel Guard

`env_registration.py` imports only `gymnasium` — no Pyxel. Add import guard test.

## Key Constraints

- Tests that use `gym.make()` must import `speednik.env_registration` first
- `check_env` should be called on `.unwrapped` to test the raw env
- All stages must be tested (hillside, pipeworks, skybridge)
- Observations must be finite (no NaN/Inf) during random play
