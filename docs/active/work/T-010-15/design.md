# T-010-15 Design: PPOAgent and Policy Eval

## Problem

Need a PPOAgent class that loads CleanRL checkpoints, conforms to the Agent protocol,
integrates into the scenario system via registry, and handles the case where torch is
not installed.

## Approaches Considered

### A. Full Object Save/Load

Change `tools/ppo_speednik.py` to use `torch.save(agent, path)` instead of `state_dict()`.
Then PPOAgent just does `torch.load(path)` and calls `model.get_action_and_value()`.

**Pros**: Matches ticket spec exactly. Simple PPOAgent code.
**Cons**: Full object pickle is fragile — breaks if Agent class moves or changes.
Pickle-based loading is a known security concern. Larger checkpoint files.

**Rejected**: state_dict is the standard PyTorch practice. Changing the training script
to use full object save creates fragility.

### B. Reconstruct Network in PPOAgent (Selected)

PPOAgent knows the network architecture (same as `tools/ppo_speednik.py`). Loads
`state_dict()`, reconstructs the network, calls `load_state_dict()`. Uses `actor`
head directly for greedy action selection.

**Pros**: Standard PyTorch pattern. state_dict checkpoints are portable and smaller.
Network architecture is documented and stable. Allows greedy (deterministic) eval
without the Categorical sampling path.
**Cons**: Architecture must be kept in sync between training and inference. If the
network changes, PPOAgent must update.

**Selected**: This is the canonical PyTorch approach. The architecture is simple (2-layer
MLP) and unlikely to change frequently. We can detect dimension mismatches at load time.

### C. Registry Stub with Lazy Import

Register a factory function instead of the class, so `resolve_agent("ppo")` triggers
the import lazily.

**Rejected**: Overengineered. A simple try/except at module level is the established
pattern for optional deps. The registry just needs a clear error message.

## Design Decisions

### 1. Network Architecture in PPOAgent

Duplicate the actor/critic network from `tools/ppo_speednik.py` inside `ppo_agent.py`.
Accept `obs_dim` and `num_actions` as constructor parameters with defaults matching
the current env (26, 8). Use `layer_init` from the training script for weight init
(needed for state_dict shape compatibility).

On `__init__`: build network, load state_dict, set `eval()` mode.

### 2. Deterministic Action Selection

PPOAgent.act() will:
1. Convert obs to tensor
2. Forward through actor network to get logits
3. Return `logits.argmax(-1).item()` — greedy, no sampling

This satisfies the "deterministic actions, no sampling" requirement.

### 3. Conditional Registration

In `registry.py`, wrap the PPOAgent import in try/except:

```python
try:
    from speednik.agents.ppo_agent import PPOAgent
    AGENT_REGISTRY["ppo"] = PPOAgent
except ImportError:
    pass
```

For the clear error message requirement: override `resolve_agent` to check if the name
is "ppo" and torch isn't available, raising a descriptive error. Simpler approach:
just check if "ppo" is missing and the name was "ppo", raise a custom error.

### 4. Observation Normalization

Known limitation: the scenario runner passes raw observations while training uses
NormalizeObservation. We will NOT solve this in T-010-15 — it's flagged as a known
concern. Future work could save normalization stats alongside the checkpoint.

### 5. Constructor API

```python
PPOAgent(
    model_path: str,
    device: str = "cpu",
    obs_dim: int = 26,
    num_actions: int = 8,
)
```

- `model_path`: path to `.pt` state_dict file
- `device`: torch device string
- `obs_dim`: observation dimension (must match checkpoint)
- `num_actions`: action space size (must match checkpoint)

### 6. Registry Test Update

The existing test `test_registry_contains_all_agents` checks exact key set.
It needs to be updated to include "ppo" conditionally. Since torch may or may not
be installed, the test should check that "ppo" is present iff torch is importable.

### 7. Evaluation Scenario YAML

Create `scenarios/hillside_ppo_eval.yaml` matching the ticket spec. The scenario
references `agent: ppo` with `agent_params.model_path`. This exercises the full
pipeline: YAML → loader → registry → PPOAgent → scenario runner.

## Risk: Architecture Drift

The network in PPOAgent must match the training script. If someone changes the training
architecture without updating PPOAgent, checkpoints will fail to load. Mitigation:
`load_state_dict(strict=True)` (default) will raise an error on shape mismatch.
