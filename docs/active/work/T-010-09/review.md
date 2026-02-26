# T-010-09 Review: Scenario YAML Format and Loader

## Summary of Changes

### New Files (9)

| File | Purpose |
|------|---------|
| `speednik/scenarios/__init__.py` | Package init, re-exports public API |
| `speednik/scenarios/conditions.py` | Condition dataclasses + valid type sets |
| `speednik/scenarios/loader.py` | ScenarioDef dataclass, load_scenario, load_scenarios |
| `scenarios/hillside_complete.yaml` | Spindash agent, goal_reached |
| `scenarios/hillside_hold_right.yaml` | Hold-right agent baseline |
| `scenarios/hillside_loop.yaml` | Loop section test with compound failure + start_override |
| `scenarios/pipeworks_jump.yaml` | Jump-runner on pipeworks |
| `scenarios/gap_jump.yaml` | Scripted agent with timeline |
| `tests/test_scenarios.py` | 31 tests for loader |

### Modified Files (1)

| File | Change |
|------|--------|
| `pyproject.toml` | Added `pyyaml` to dependencies |

## Acceptance Criteria Evaluation

| Criterion | Status |
|-----------|--------|
| pyyaml added as dependency | Done |
| ScenarioDef dataclass with all fields | Done |
| SuccessCondition and FailureCondition dataclasses | Done |
| load_scenario(path) parses YAML into ScenarioDef | Done |
| load_scenarios(run_all=True) finds all YAML in scenarios/ | Done |
| All 8 condition types parseable | Done (5 success + 3 failure) |
| Compound `any` with nested sub-conditions | Done |
| start_override optional field parsed | Done |
| agent_params optional dict parsed | Done |
| 3-5 starter scenario YAML files | Done (5 files) |
| Round-trip test: load scenario, verify fields | Done |
| No Pyxel imports | Done (guarded by test) |
| uv run pytest tests/ -x passes | Done (966 passed) |

## Test Coverage

- **31 tests** in `tests/test_scenarios.py`.
- **Real file round-trips**: All 5 YAML scenarios load and verify correctly.
- **Type coverage**: Each of 5 success types and 3 failure types tested individually.
- **Edge cases**: Missing optional fields default correctly, missing required fields
  raise KeyError, invalid condition types raise ValueError.
- **Compound conditions**: Recursive `any` failure with nested sub-conditions verified.
- **Import guard**: Source-level check that scenarios package never imports Pyxel.
- **Full suite**: 966 passed, 5 xfailed, 0 failures — no regressions.

## Architecture Notes

The scenarios package is a pure data layer with zero dependencies on game code:
```
scenarios/conditions.py  →  stdlib only (dataclasses)
scenarios/loader.py      →  yaml + conditions.py
```

This enables the runner (future ticket) to import ScenarioDef and connect it to
the simulation + agent layers without any coupling in the data definitions.

## Open Concerns

1. **Scenario file discovery path**: `load_scenarios(run_all=True)` defaults to
   `Path("scenarios")` which assumes CWD is the project root. This matches how
   pytest and uv run operate, but a future CLI tool may need to set the base path
   explicitly. The `base` parameter supports this.

2. **No `any` nesting validation**: The parser allows `any` inside `any`. There's no
   practical use case, but it doesn't cause harm either. Could add a depth limit
   later if needed.

3. **Stage name validation**: The loader doesn't validate that `stage` matches a real
   stage (hillside, pipeworks, skybridge). That validation belongs in the runner when
   it calls `create_sim(scenario.stage)`.

4. **Agent name validation**: Similarly, `agent` is not validated against the agent
   registry at load time. The runner will get a clear `KeyError` from `resolve_agent`
   if the name is wrong.

## No Known Issues

All acceptance criteria met. No deviations from the plan. Ready for human review.
