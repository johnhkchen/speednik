# T-010-05 Progress: Programmed Agents

## Completed

- [x] Step 1: IdleAgent and HoldRightAgent created
- [x] Step 2: JumpRunnerAgent created (landing-based jump detection)
- [x] Step 3: SpindashAgent created (4-phase state machine)
- [x] Step 4: ScriptedAgent created (frame-indexed timeline)
- [x] Step 5: Registry created (dict + resolve_agent factory)
- [x] Step 6: Package init updated with all new exports
- [x] Step 7: Tests written (50 tests in test_agents.py)
- [x] Step 8: Full test suite passes (904 passed, 5 xfailed)

## Deviations from Plan

None. All steps executed as planned.

## Test Results

```
904 passed, 5 xfailed in 2.00s
```

All 50 agent tests passed including:
- 5 protocol conformance tests
- 14 behavioral correctness tests
- 5 registry tests
- 4 smoke tests (integration with real simulation)
- 8 no-Pyxel import checks
- 14 existing action/protocol tests (unchanged, still passing)
