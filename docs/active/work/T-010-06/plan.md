# T-010-06 Plan: SpeednikEnv Core

## Step 1: Add gymnasium dependency

- Run `uv add gymnasium` to add it to pyproject.toml and update uv.lock.
- Verify: `uv run python -c "import gymnasium"` exits cleanly.

## Step 2: Implement `speednik/env.py`

Write the SpeednikEnv class with all methods:

1. `__init__(stage, render_mode, max_steps)` — initialize spaces, set sim=None.
2. `reset(*, seed, options)` — call super().reset(seed=seed), create_sim, reset counters,
   return (obs, info).
3. `step(action)` — map action to input, call sim_step, compute obs/reward/terminated/
   truncated/info, return 5-tuple.
4. `_action_to_input(action)` — delegate to `action_to_input()` from actions.py, store
   prev_jump_held on self.
5. `_get_obs()` — delegate to `extract_observation(self.sim)`.
6. `_compute_reward(events)` — return 0.0 placeholder.
7. `_get_info()` — return dict with frame, x, y, max_x, rings, deaths, goal_reached.

Verify: module imports without error.

## Step 3: Write `tests/test_env.py`

Tests organized by concern:

**Spaces:**
- observation_space shape is (OBS_DIM,), dtype float32
- action_space.n == NUM_ACTIONS

**Reset:**
- Returns (obs, info) tuple
- obs shape and dtype correct
- info has expected keys
- sim is initialized after reset

**Step:**
- Returns (obs, reward, terminated, truncated, info) 5-tuple
- obs shape correct
- reward is float
- terminated and truncated are bool

**Jump edge detection (via env interface):**
- First jump action → jump_pressed True (verify by checking player state changes)
- Held jump action → jump_pressed False (indirect test via behavior)

**Termination — goal reached:**
- Set sim.goal_x close to player, step, check terminated=True and info["goal_reached"]

**Termination — player dead:**
- Force sim.player_dead, step, check terminated=True

**Truncation — max_steps:**
- Create env with small max_steps, step until truncated=True

**Info dict:**
- All keys present: frame, x, y, max_x, rings, deaths, goal_reached
- Values are correct types (int, float, bool)

**Multiple episodes:**
- reset/step N frames, reset again, step again — no errors, state is fresh

**Gymnasium compliance:**
- `check_env(SpeednikEnv())` passes without warnings

**No Pyxel:**
- Source-level assertion on env.py

## Step 4: Run tests

- `uv run pytest tests/test_env.py -x -v`
- Fix any failures.
- `uv run pytest tests/ -x` to verify no regressions.

## Step 5: Commit

- Stage `speednik/env.py`, `tests/test_env.py`, `pyproject.toml`, `uv.lock`.
- Commit with descriptive message.
