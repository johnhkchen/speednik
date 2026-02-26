# T-010-09 Design: Scenario YAML Format and Loader

## Decision 1: YAML Parsing Library

### Option A: PyYAML (`pyyaml`)

- Industry standard for YAML in Python.
- `yaml.safe_load()` returns plain dicts/lists — exactly what we need.
- Ticket explicitly specifies PyYAML.
- Well-maintained, no security concerns with `safe_load`.

### Option B: stdlib `tomllib` with TOML format

- No extra dependency.
- But TOML is less natural for scenario definitions (nested conditions).
- Ticket says YAML, spec says YAML. Rejected.

### Option C: `ruamel.yaml`

- Preserves comments, round-trips. Over-engineered for read-only loading.
- Rejected: unnecessary complexity.

**Decision: PyYAML with `yaml.safe_load()`.**

## Decision 2: Dataclass Design

### Option A: Flat dataclasses matching ticket spec exactly

The ticket provides `SuccessCondition`, `FailureCondition`, `StartOverride`, `ScenarioDef`.
Use these as-is with `@dataclass`. Keep condition dataclasses in a separate
`conditions.py` module. Loader manually constructs dataclasses from parsed dicts.

### Option B: Single Condition dataclass for both success and failure

Both share `type` and `value` fields. Could unify into one `Condition` type.
But the ticket explicitly defines separate classes, and semantically they're different
(success vs failure). Rejected: deviates from spec without clear benefit.

### Option C: Use TypedDict instead of dataclasses

Lighter weight, but no `__init__`, no `__repr__`, no defaults. Dataclasses are the
standard pattern in this codebase. Rejected.

**Decision: Option A — separate dataclasses matching the ticket spec.** Condition types
stored as strings, validated against known sets at load time.

## Decision 3: Validation Strategy

### Option A: Validate at load time (fail fast)

Check condition type strings against known sets. Raise `ValueError` for unknowns.
Validate required fields are present. Ensures bad YAML fails immediately with
a clear error message, not later at runtime in the runner.

### Option B: No validation — trust the YAML

Simpler loader, but pushes errors to runtime. A typo like `type: goal_reched`
would silently pass through and fail cryptically in the runner.

### Option C: Schema validation with jsonschema or cerberus

Heavy dependency for a simple format. Overkill. Rejected.

**Decision: Option A — validate at load time.** Define `VALID_SUCCESS_TYPES` and
`VALID_FAILURE_TYPES` sets. Check membership during construction.

## Decision 4: Condition Construction

### Option A: Factory function per condition type

`parse_success_condition(data: dict) -> SuccessCondition`. Extracts fields from the
dict, validates type, returns dataclass.

### Option B: Dataclass `__post_init__` validation

Put validation inside the dataclass itself. Constructor does double duty.
Couples data definition with parsing logic. Rejected.

### Option C: classmethod `from_dict`

`SuccessCondition.from_dict(data)`. Clean, but the codebase doesn't use classmethods
for construction — it uses free functions (`create_sim`, `load_stage`).

**Decision: Option A — free `parse_*` functions in `loader.py`.** Matches codebase
conventions (factory functions).

## Decision 5: File Discovery for `load_scenarios(run_all=True)`

### Option A: Glob from CWD-relative `scenarios/`

`Path("scenarios").glob("*.yaml")`. Simple, works when run from project root.
This is how pytest and other tools work — assume CWD is project root.

### Option B: Glob relative to package location

`Path(__file__).parent.parent.parent / "scenarios"`. Brittle, breaks if package
is installed elsewhere.

### Option C: Configurable base path with default

`load_scenarios(base: Path | None = None, run_all=False)`. Default to
`Path("scenarios")` if base is None. Allows override for testing.

**Decision: Option C — configurable base with sensible default.** The function
signature becomes `load_scenarios(paths=None, run_all=False, base=Path("scenarios"))`.

## Decision 6: Compound `any` Condition Handling

The `any` failure condition contains nested sub-conditions:
```yaml
failure:
  type: any
  conditions:
    - type: player_dead
    - type: stuck
      tolerance: 2.0
      window: 30
```

Parse recursively: each item in `conditions` is parsed through the same
`parse_failure_condition()` function. Allow one level of nesting (no `any` inside
`any` — there's no use case and it complicates things). Validate this at parse time.

## Decision 7: Starter Scenario Files

The ticket requests 3-5 scenarios. Write all 5 specified:

1. `hillside_complete.yaml` — spindash, goal_reached / player_dead
2. `hillside_hold_right.yaml` — hold_right, goal_reached / player_dead
3. `hillside_loop.yaml` — hold_right, position_x_gte / stuck
4. `pipeworks_jump.yaml` — jump_runner, goal_reached / player_dead
5. `gap_jump.yaml` — scripted, position_x_gte / player_dead

Each scenario exercises a different agent type and condition combination, providing
good coverage for the loader's parsing logic.

## Design Summary

- Add `pyyaml` dependency.
- `speednik/scenarios/conditions.py`: `SuccessCondition`, `FailureCondition`,
  `StartOverride` dataclasses + `VALID_*_TYPES` sets.
- `speednik/scenarios/loader.py`: `ScenarioDef` dataclass, `load_scenario(path)`,
  `load_scenarios(paths, run_all, base)`, parse helpers.
- `speednik/scenarios/__init__.py`: re-exports.
- `scenarios/*.yaml`: 5 starter files.
- Tests: round-trip load, field validation, compound conditions, error cases.
