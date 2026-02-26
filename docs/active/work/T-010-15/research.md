# T-010-15 Research: PPOAgent and Policy Eval

## Scope

Build a `PPOAgent` class that loads a trained CleanRL checkpoint and conforms to the
`Agent` protocol. Register it in the agent registry. Create an evaluation scenario YAML.

## Codebase Mapping

### Agent Protocol (`speednik/agents/base.py`)

- `Agent(Protocol)` with `@runtime_checkable`: `act(obs: np.ndarray) -> int`, `reset() -> None`
- Duck-typed — no inheritance needed, just method signatures
- `isinstance(obj, Agent)` works at runtime

### Existing Agents (`speednik/agents/`)

Five agents exist: `IdleAgent`, `HoldRightAgent`, `JumpRunnerAgent`, `SpindashAgent`, `ScriptedAgent`.
All are pure Python, no external deps. Pattern: class with `act`/`reset`, optional `__init__` params.

### Agent Registry (`speednik/agents/registry.py`)

- `AGENT_REGISTRY: dict[str, type]` — static dict of name → class
- `resolve_agent(name, params)` — looks up class, instantiates with `**params`
- Raises `KeyError` for unknown names
- All imports are top-level — no conditional imports yet

### Package Init (`speednik/agents/__init__.py`)

- Exports all agents, actions, registry functions in `__all__`
- Currently unconditional imports of all five agents

### Training Script (`tools/ppo_speednik.py`)

- CleanRL fork with `Agent(nn.Module)` class (actor/critic MLP)
- Network: `Linear(obs_dim, 64) → Tanh → Linear(64, 64) → Tanh → Linear(64, out)`
- `get_action_and_value(x, action=None)` — returns `(action, log_prob, entropy, value)`
  - When `action is None`: samples via `Categorical(logits=logits).sample()`
  - When `action` provided: computes log_prob for that action
- **Model save**: `torch.save(agent.state_dict(), model_path)` — saves state_dict only
- Checkpoint path: `runs/{run_name}/{exp_name}.pt`
- obs_dim derived from `envs.single_observation_space.shape` — currently 26 (with raycasts)
- action_space: `Discrete(8)`

### Observation Module (`speednik/observation.py`)

- `OBS_DIM = 26` (with raycasts), `OBS_DIM_BASE = 12` (without)
- `extract_observation(sim, use_raycasts=True)` — default includes 7 terrain raycasts
- The Gym env uses `use_raycasts=True` by default → training sees 26-dim obs
- The scenario runner calls `extract_observation(sim)` without explicit arg → 26-dim

### Gymnasium Env (`speednik/env.py`)

- `SpeednikEnv(stage, render_mode, max_steps, use_raycasts=True)`
- observation_space: `Box(-inf, inf, shape=(26,))` by default
- Training wraps with `NormalizeObservation` + `TransformObservation(clip -10, 10)`

### Scenario System (`speednik/scenarios/`)

- `ScenarioDef` loaded from YAML: `agent` field resolved via `resolve_agent`
- `runner.py`: frame loop calls `extract_observation(sim)` → `agent.act(obs)` → `sim_step`
- Raw observations — no normalization wrappers
- Metrics: completion_time, max_x, rings_collected, total_reward, average_speed, etc.
- Existing YAML scenarios in `scenarios/` directory

### Test Patterns (`tests/test_agents.py`)

- Protocol conformance: `isinstance(agent, Agent)`
- No Pyxel: `_assert_no_pyxel(module_name)` reads source, checks for pyxel imports
- Smoke tests: `_run_agent(agent, frames=300)` runs agent in real sim
- Registry test checks exact key set: `{"idle", "hold_right", "jump_runner", "spindash", "scripted"}`
- `resolve_agent("nonexistent_agent")` → `KeyError`

## Key Findings

### 1. state_dict vs Full Object Save

The ticket spec shows `torch.load(model_path)` returning an object with `get_action_and_value`.
The actual training script saves `agent.state_dict()`. The PPOAgent must reconstruct the
network architecture and call `load_state_dict()`. This requires knowing obs_dim and num_actions.

### 2. Normalization Mismatch

Training uses `NormalizeObservation` (running mean/std). The scenario runner passes raw
observations. A trained model evaluated via PPOAgent in scenarios will receive unnormalized
observations, likely causing degraded performance. This is a known limitation from T-010-14.

### 3. Deterministic vs Stochastic Actions

`get_action_and_value` samples from `Categorical`. For eval, the ticket requires deterministic
actions. PPOAgent should use `logits.argmax()` (greedy) rather than sampling.

### 4. Conditional torch Import

torch is not a project dependency (only in the training script's environment). The registry
must handle `ImportError` gracefully. Current registry has no conditional imports.

### 5. Observation Dimensionality

The env defaults to 26-dim (raycasts). The training script builds the network from
`envs.single_observation_space.shape`. So trained checkpoints will have obs_dim=26.
The PPOAgent needs to accept obs_dim as a parameter or detect it from the checkpoint.

### 6. Registry Test Breakage

`test_registry_contains_all_agents` asserts exact key set. Adding "ppo" conditionally means
the test must either be updated to allow "ppo" optionally, or the conditional import must
not add the key when torch is absent.

## Constraints

- No Pyxel imports in `ppo_agent.py`
- torch is optional — all tests must pass without it installed
- PPOAgent must work on CPU only
- Must integrate with existing scenario YAML resolution
