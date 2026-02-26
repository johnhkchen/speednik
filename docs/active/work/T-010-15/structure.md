# T-010-15 Structure: PPOAgent and Policy Eval

## Files Created

### `speednik/agents/ppo_agent.py`

New module containing:

- `_layer_init(layer, std, bias_const)` — weight initialization (mirrors training script)
- `_PPONetwork(nn.Module)` — actor/critic MLP matching `tools/ppo_speednik.py` architecture
  - `__init__(self, obs_dim: int, num_actions: int)`
  - `actor`: Sequential(Linear(obs_dim,64), Tanh, Linear(64,64), Tanh, Linear(64,num_actions))
  - `critic`: Sequential(Linear(obs_dim,64), Tanh, Linear(64,64), Tanh, Linear(64,1))
  - `get_action_and_value(self, x, action=None)` — same interface as training Agent
- `PPOAgent` — wraps `_PPONetwork` behind the Agent protocol
  - `__init__(self, model_path: str, device: str = "cpu", obs_dim: int = 26, num_actions: int = 8)`
  - `act(self, obs: np.ndarray) -> int` — greedy action from actor logits
  - `reset(self) -> None` — no-op

Module-level: `import torch` at top. This file is only importable when torch is installed.
The registry handles the conditional import.

### `scenarios/hillside_ppo_eval.yaml`

Evaluation scenario YAML as specified in the ticket.

## Files Modified

### `speednik/agents/registry.py`

- Add conditional import of PPOAgent wrapped in try/except ImportError
- If import succeeds: add `"ppo": PPOAgent` to `AGENT_REGISTRY`
- If import fails: register nothing (key absent)
- Modify `resolve_agent` to check for `"ppo"` specifically when KeyError is raised,
  and provide a clear error message about installing torch

### `speednik/agents/__init__.py`

- Add conditional import of `PPOAgent` (try/except)
- Add `"PPOAgent"` to `__all__` conditionally (only if import succeeds)

### `tests/test_agents.py`

- Update `test_registry_contains_all_agents` to accept "ppo" key optionally
- Add PPOAgent-specific tests behind `pytest.importorskip("torch")`:
  - Protocol conformance
  - No Pyxel import check
  - Greedy action selection (deterministic)
  - Constructor parameter validation
  - Registry integration: `resolve_agent("ppo", {"model_path": ...})`
  - Registry error: clear message when torch not installed

## Module Boundaries

```
speednik/agents/ppo_agent.py  ← depends on torch (optional), numpy
speednik/agents/registry.py   ← imports ppo_agent conditionally
speednik/agents/__init__.py   ← imports ppo_agent conditionally
tests/test_agents.py          ← PPO tests skip without torch
```

The PPOAgent module has NO dependency on:
- pyxel
- speednik.simulation
- speednik.observation
- gymnasium

It only depends on torch and numpy. The scenario runner feeds it observations;
it returns action integers.

## Interface Contracts

### PPOAgent Constructor

```python
PPOAgent(model_path="path/to/model.pt", device="cpu", obs_dim=26, num_actions=8)
```

Raises `FileNotFoundError` if model_path doesn't exist.
Raises `RuntimeError` if state_dict doesn't match network architecture.

### PPOAgent.act

```python
agent.act(obs)  # obs: np.ndarray shape (obs_dim,) → int in [0, num_actions)
```

Deterministic (greedy argmax). Uses `torch.no_grad()`.

### Registry Integration

```python
resolve_agent("ppo", {"model_path": "models/ppo.pt"})  # → PPOAgent instance
resolve_agent("ppo", {"model_path": "models/ppo.pt", "obs_dim": 12})  # custom dims
```

When torch not installed:
```python
resolve_agent("ppo", ...)  # → KeyError with message mentioning torch
```
