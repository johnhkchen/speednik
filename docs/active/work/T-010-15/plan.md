# T-010-15 Plan: PPOAgent and Policy Eval

## Step 1: Create `speednik/agents/ppo_agent.py`

Implement `_layer_init`, `_PPONetwork(nn.Module)`, and `PPOAgent`.

- `_PPONetwork`: actor/critic MLP mirroring `tools/ppo_speednik.py:Agent`
- `PPOAgent.__init__`: build network, load state_dict, set eval mode
- `PPOAgent.act`: `torch.no_grad()`, tensor conversion, actor forward, argmax
- `PPOAgent.reset`: pass

Verification: module imports cleanly when torch is available.

## Step 2: Update `speednik/agents/registry.py`

- Add try/except import of PPOAgent
- On success: add `"ppo"` to `AGENT_REGISTRY`
- On failure: don't register
- Modify `resolve_agent` to give a clear error when "ppo" requested but torch missing

Verification: `resolve_agent("ppo", ...)` works with torch; raises clear error without.

## Step 3: Update `speednik/agents/__init__.py`

- Add conditional PPOAgent import
- Add to `__all__` conditionally

Verification: `from speednik.agents import PPOAgent` works with torch, doesn't break without.

## Step 4: Create `scenarios/hillside_ppo_eval.yaml`

Write the evaluation scenario YAML per the ticket spec:
- agent: ppo, model_path param
- success: goal_reached, failure: player_dead
- metrics: completion_time, max_x, rings_collected, total_reward, average_speed

Verification: YAML parses correctly via the scenario loader.

## Step 5: Update `tests/test_agents.py`

Add PPOAgent tests (all behind `pytest.importorskip("torch")`):

1. **Protocol conformance**: `isinstance(PPOAgent(...), Agent)`
2. **No Pyxel import**: `_assert_no_pyxel("ppo_agent")`
3. **Deterministic actions**: same obs → same action across multiple calls
4. **Action range**: output is int in [0, num_actions)
5. **Registry presence**: "ppo" in AGENT_REGISTRY (when torch available)
6. **Registry resolve**: `resolve_agent("ppo", {"model_path": ...})` returns PPOAgent

Update existing test:
- `test_registry_contains_all_agents`: allow "ppo" key optionally based on torch availability

For tests that need a model checkpoint: create a small helper that builds a
`_PPONetwork`, saves its state_dict to a temp file, and returns the path.

Verification: `uv run pytest tests/test_agents.py -x` passes.

## Step 6: Run full test suite

`uv run pytest tests/ -x` — verify nothing is broken.

## Testing Strategy

- **Unit tests**: PPOAgent protocol conformance, deterministic action, action range
- **Integration test**: Registry resolve with PPOAgent, scenario YAML loading
- **Skip pattern**: All PPO tests use `pytest.importorskip("torch")` so suite passes without torch
- **Mock checkpoint**: Tests create a temporary checkpoint via `_PPONetwork` + `torch.save(state_dict)`
- **No Pyxel check**: Source file scan for pyxel imports
- **Existing test update**: Registry key set test accounts for optional "ppo" entry
