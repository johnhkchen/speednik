# T-010-15 Progress: PPOAgent and Policy Eval

## Completed

### Step 1: Create `speednik/agents/ppo_agent.py`
- Implemented `_layer_init`, `_PPONetwork(nn.Module)`, `PPOAgent`
- Network architecture mirrors `tools/ppo_speednik.py:Agent` exactly
- Loads `state_dict` checkpoint with `weights_only=True`
- Greedy action selection via `logits.argmax()` (deterministic, no sampling)
- Uses `torch.no_grad()` for inference efficiency
- Default `obs_dim=26` (matches current env with raycasts), `num_actions=8`

### Step 2: Update `speednik/agents/registry.py`
- Added conditional import of PPOAgent (try/except ImportError)
- On success: `"ppo"` added to `AGENT_REGISTRY`
- Modified `resolve_agent` with clear error messages:
  - If "ppo" requested but torch missing: descriptive message about installing torch
  - For other unknown agents: lists available agents

### Step 3: Update `speednik/agents/__init__.py`
- Added conditional PPOAgent import
- Added "PPOAgent" to `__all__` conditionally

### Step 4: Create scenario YAML
- Created `scenarios/eval/hillside_ppo_eval.yaml`
- Placed in `eval/` subdirectory to avoid `--all` glob (which only picks up top-level)
- This avoids breaking the existing `test_cli_all_flag` test (which runs all scenarios
  and would fail on a missing model file)

### Step 5: Update tests
- Updated `test_registry_contains_all_agents` to accept optional "ppo" key
- Added `TestPPOAgent` class with 9 tests (all behind `pytest.importorskip("torch")`):
  - Protocol conformance, no Pyxel, deterministic actions, action range,
    reset noop, custom dims, registry presence, resolve agent, file not found
- All tests use temporary checkpoints created via `_make_ppo_checkpoint` helper

### Step 6: Full test suite
- 1170 passed, 16 skipped, 5 xfailed — all green

## Deviations from Plan

1. **Scenario YAML location**: Moved from `scenarios/hillside_ppo_eval.yaml` to
   `scenarios/eval/hillside_ppo_eval.yaml`. The `--all` CLI flag globs `*.yaml` at
   the top level, and the PPO eval scenario requires a trained model file that won't
   exist in test/CI environments.

2. **No smoke test with real simulation**: The plan mentioned running PPOAgent through
   the simulation. Since the model weights are random in tests, this would be meaningless.
   Tests verify protocol conformance, deterministic behavior, and action range instead.
