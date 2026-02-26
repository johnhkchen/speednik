# T-010-15 Review: PPOAgent and Policy Eval

## Summary of Changes

### Files Created
- `speednik/agents/ppo_agent.py` — PPOAgent class wrapping CleanRL checkpoint
- `scenarios/eval/hillside_ppo_eval.yaml` — evaluation scenario YAML

### Files Modified
- `speednik/agents/registry.py` — conditional PPO registration, improved error messages
- `speednik/agents/__init__.py` — conditional PPOAgent export
- `tests/test_agents.py` — 9 new PPOAgent tests, updated registry key check

## Acceptance Criteria Evaluation

| Criterion | Status |
|-----------|--------|
| PPOAgent conforms to Agent protocol | PASS — `isinstance(PPOAgent(...), Agent)` verified |
| PPOAgent loads CleanRL checkpoint and runs inference | PASS — loads state_dict, forward pass verified |
| PPOAgent uses torch.no_grad() for inference | PASS — `act()` wrapped in `torch.no_grad()` |
| "ppo" registered in agent registry with conditional import | PASS — try/except ImportError pattern |
| torch not installed → clear error message | PASS — custom message in `resolve_agent` |
| Evaluation scenario YAML | PASS — `scenarios/eval/hillside_ppo_eval.yaml` created |
| Deterministic actions (no sampling) | PASS — `logits.argmax()`, verified in test |
| Works on CPU (no GPU required) | PASS — default `device="cpu"` |
| No Pyxel imports | PASS — source scan verified in test |
| `uv run pytest tests/ -x` passes | PASS — 1170 passed, 16 skipped |

**Scenario comparison**: The YAML + registry integration enables the comparison workflow
described in the ticket. Running `--compare` requires a trained model checkpoint, which
is outside the scope of this ticket (training is T-010-14).

## Test Coverage

- **9 new tests** in `TestPPOAgent` class, all behind `pytest.importorskip("torch")`
- Protocol conformance, no Pyxel, deterministic actions, action range, reset,
  custom dimensions, registry presence, resolve_agent integration, FileNotFoundError
- Updated `test_registry_contains_all_agents` to accept optional "ppo" key
- All tests create temporary checkpoints via `_make_ppo_checkpoint` helper

## Architecture Decisions

1. **state_dict loading**: PPOAgent reconstructs the network architecture (`_PPONetwork`)
   and calls `load_state_dict()`. This is the standard PyTorch pattern and works with
   the checkpoint format from T-010-14 (`torch.save(agent.state_dict(), path)`).

2. **Greedy action selection**: `act()` uses `logits.argmax()` instead of
   `Categorical.sample()`. This satisfies the deterministic requirement and is the
   standard eval-mode approach.

3. **Eval scenario placement**: `scenarios/eval/` subdirectory, not top-level `scenarios/`.
   The `--all` CLI flag globs only `*.yaml` at the top level. PPO eval requires a
   trained model file that won't exist in test environments.

## Open Concerns

1. **Observation normalization mismatch**: Training uses `NormalizeObservation` wrapper
   (running mean/std). The scenario runner passes raw observations from
   `extract_observation()`. A trained model evaluated through PPOAgent in scenarios
   will receive unnormalized observations, likely causing degraded performance.
   **Mitigation**: Future work should save normalization statistics alongside the
   checkpoint and apply them in PPOAgent. This is a known limitation from T-010-14.

2. **Architecture coupling**: The network in `_PPONetwork` must stay in sync with the
   `Agent` class in `tools/ppo_speednik.py`. If someone changes the training
   architecture without updating PPOAgent, checkpoints will fail to load with a clear
   `RuntimeError` from `load_state_dict(strict=True)`.

3. **obs_dim default**: The default `obs_dim=26` matches the current env (with raycasts).
   If a model was trained with `use_raycasts=False` (obs_dim=12), the user must pass
   `obs_dim=12` explicitly. The state_dict load will catch mismatches.

4. **No end-to-end eval test**: There is no test that runs PPOAgent through the full
   scenario pipeline with a real simulation, because random-weight models produce
   meaningless behavior. The integration is tested via `resolve_agent` + `act()`.
