# T-010-05 Plan: Programmed Agents

## Step 1: Create IdleAgent and HoldRightAgent

Create `speednik/agents/idle.py` and `speednik/agents/hold_right.py`. Both are
stateless, trivial implementations.

**Verify:** Import classes, call act() with a dummy obs, confirm correct action returned.

## Step 2: Create JumpRunnerAgent

Create `speednik/agents/jump_runner.py`. Stateful: tracks _was_airborne and
_first_call for landing detection.

**Verify:** Create agent, feed sequence of obs with on_ground transitions. Confirm
ACTION_RIGHT_JUMP on first call and after landing, ACTION_RIGHT otherwise.

## Step 3: Create SpindashAgent

Create `speednik/agents/spindash.py`. State machine with 4 phases. Parameterized
with charge_frames and redash_speed.

**Verify:** Create agent, step through phases with crafted obs vectors. Confirm
correct action sequence: DOWN → DOWN_JUMP × N → RIGHT → RIGHT (until re-dash).

## Step 4: Create ScriptedAgent

Create `speednik/agents/scripted.py`. Frame-indexed timeline playback with internal
frame counter.

**Verify:** Create agent with known timeline, call act() across frames, confirm
correct action at each frame boundary.

## Step 5: Create Registry

Create `speednik/agents/registry.py`. Dict mapping + resolve_agent factory.

**Verify:** resolve_agent returns correct agent types, kwargs pass through.

## Step 6: Update Package Init

Modify `speednik/agents/__init__.py` to import and re-export all new symbols.

**Verify:** All symbols importable from `speednik.agents`.

## Step 7: Write Tests

Add tests to `tests/test_agents.py` in clearly labeled sections:

1. **Protocol conformance** — isinstance(agent, Agent) for all 5 agents
2. **Behavioral** — correct action returns for each agent type
3. **Registry** — resolve_agent with and without params
4. **Smoke** — HoldRight 300 frames x increases; Spindash 300 frames beats HoldRight
5. **No-Pyxel** — source inspection for all 6 new modules

## Step 8: Run Full Test Suite

Run `uv run pytest tests/ -x` and fix any failures.

**Verify:** All tests pass including existing tests from T-010-02/03/04.

## Testing Strategy

- **Unit tests:** Each agent's act() with synthetic obs arrays
- **Integration tests:** Agent + sim_step + extract_observation for 300 frames
- **Regression tests:** Existing test_simulation.py and test_observation.py pass
- **No-Pyxel:** Source inspection of all new files
