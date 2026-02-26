# T-010-05 Review: Programmed Agents

## Summary

Implemented 5 observation-based agents conforming to the `Agent` protocol, plus a
registry for scenario YAML resolution. All agents read only the observation vector —
no direct `Player` access, no Pyxel imports.

## Files Created

| File | Lines | Description |
|------|-------|-------------|
| `speednik/agents/idle.py` | 18 | IdleAgent — always ACTION_NOOP |
| `speednik/agents/hold_right.py` | 18 | HoldRightAgent — always ACTION_RIGHT |
| `speednik/agents/jump_runner.py` | 40 | JumpRunnerAgent — run right, jump on landing |
| `speednik/agents/spindash.py` | 53 | SpindashAgent — CROUCH→CHARGE→RELEASE→RUN cycle |
| `speednik/agents/scripted.py` | 28 | ScriptedAgent — frame-indexed timeline playback |
| `speednik/agents/registry.py` | 35 | AGENT_REGISTRY dict + resolve_agent factory |

## Files Modified

| File | Change |
|------|--------|
| `speednik/agents/__init__.py` | Added imports/exports for 5 agents + registry |
| `tests/test_agents.py` | Extended from 196 → ~310 lines with 36 new tests |

## Acceptance Criteria Coverage

| Criterion | Status | Test |
|-----------|--------|------|
| HoldRightAgent conforms to Agent protocol | Pass | test_hold_right_agent_protocol |
| JumpRunnerAgent conforms to Agent protocol | Pass | test_jump_runner_agent_protocol |
| SpindashAgent conforms to Agent protocol | Pass | test_spindash_agent_protocol |
| ScriptedAgent conforms to Agent protocol | Pass | test_scripted_agent_protocol |
| IdleAgent conforms to Agent protocol | Pass | test_idle_agent_protocol |
| All pass isinstance(agent, Agent) | Pass | All 5 protocol tests |
| resolve_agent("hold_right") works | Pass | test_resolve_agent_hold_right |
| resolve_agent("spindash", {"charge_frames": 5}) works | Pass | test_resolve_agent_with_params |
| Smoke: HoldRight x increases over 300 frames | Pass | test_smoke_hold_right_moves_right |
| Smoke: Spindash reaches higher x than HoldRight | Pass | test_smoke_spindash_beats_hold_right |
| No Pyxel imports | Pass | 8 no-pyxel tests |
| uv run pytest tests/ -x passes | Pass | 904 passed, 5 xfailed |

## Test Coverage

**50 tests total** in `tests/test_agents.py`:
- 14 existing tests (T-010-04, unchanged, still passing)
- 5 protocol conformance (isinstance checks)
- 14 behavioral correctness (action returns, phase transitions, reset, timeline)
- 5 registry tests (lookup, params, scripted, unknown name)
- 4 smoke tests (agents driving real hillside simulation for 300 frames)
- 8 no-Pyxel source inspection checks

All existing tests in other files (test_simulation.py, test_observation.py, etc.)
continue to pass — no regressions.

## Design Decisions

1. **JumpRunnerAgent uses landing detection, not raycasts.** The current 12-dim
   observation lacks terrain raycasts (obs[18] from spec). Agent jumps on first frame
   and after every landing, matching the harness `hold_right_jump()` strategy. Can be
   extended when raycasts arrive in T-010-16/17.

2. **SpindashAgent uses is_rolling as SPINDASH proxy.** The observation doesn't expose
   PlayerState. `obs[6] > 0.5` (is_rolling) prevents re-dashing during active spindash,
   which is a reasonable approximation.

3. **SpindashAgent redash_speed defaults to 0.125.** Harness uses raw threshold 2.0;
   normalized: 2.0/16.0 = 0.125. Keeps the interface in observation units.

4. **ScriptedAgent uses action ints, not InputState.** Consistent with the agent
   protocol which returns action ints. The harness scripted strategy uses InputState
   because it operates at a different interface level.

## Open Concerns

- **JumpRunnerAgent without raycasts is limited.** It cannot detect obstacles ahead,
  only react to landings. This is the expected initial behavior per the ticket, but
  should be enhanced when T-010-16/17 adds terrain raycasts to the observation vector.

- **SpindashAgent rolling heuristic may differ on steep terrain.** Downhill sections
  can set is_rolling without an active spindash, which would prevent re-dashing. In
  practice this is rare and the ticket acknowledges "similar (not identical) behavior."

## No Issues Requiring Human Attention

All acceptance criteria met. All tests pass. No blocking concerns.
