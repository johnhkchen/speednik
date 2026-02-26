# Plan — T-013-03-BUG-03: Speed Demon Pit Death on Skybridge

## Step 1: Fix collision.json solidity mismatches

Write a Python script to:
1. Load collision.json and tile_map.json
2. For each of the three transition regions (cols 50-55, 100-107, 150-157; rows 31-39):
   - Where collision=2 (FULL) and tile_map type=1 (TOP_ONLY), set collision to 1
3. Write the updated collision.json

Verification: Diff the file to confirm only the expected cells changed.

## Step 2: Add recovery spring to entities.json

Add a `spring_up` entity at x=1190, y=608 to `entities.json`.

Insert after the existing spring at x=592 (the third spring in the list) to maintain
ascending x-order in the entities file.

Verification: Count springs — should be 8 (was 7).

## Step 3: Run speed demon audit to verify fix

Run the speed demon audit:
```python
from speednik.qa import run_audit, BehaviorExpectation, make_speed_demon
exp = BehaviorExpectation(
    name="test", stage="skybridge", archetype="speed_demon",
    min_x_progress=5000, max_deaths=1, require_goal=True,
    max_frames=6000, invariant_errors_ok=0,
)
findings, result = run_audit("skybridge", make_speed_demon(), exp)
```

Success criteria:
- max_x > 4800 (reaches boss arena)
- deaths ≤ 1
- No invariant errors (or documented known issues)

## Step 4: Run existing tests to check for regressions

```bash
uv run python -m pytest tests/ -x -q
```

Focus on:
- `test_audit_skybridge.py` — all archetype audits
- `test_hillside_integration.py` — unrelated stage, should not regress

## Testing Strategy

- **Primary**: Speed demon audit run showing the player traverses past x=1600
- **Secondary**: Other archetype audits (walker, jumper, etc.) should not regress
- **Regression**: Full test suite pass
