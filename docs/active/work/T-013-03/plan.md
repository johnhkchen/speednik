# T-013-03 Plan — Re-run Skybridge Audit

## Step 1: Create bug ticket T-013-03-BUG-01

File: `docs/active/tickets/T-013-03-BUG-01.md`

Terrain pocket trap on Skybridge at x≈413, y≈620. Walker and Wall Hugger get stuck in
FULL-solidity tiles (col 26-28, rows 38-41) after spring launch from x=304. They oscillate
between on_ground states and can never escape because the terrain forms a closed pocket.

Verification: File exists with correct YAML frontmatter.

## Step 2: Create bug ticket T-013-03-BUG-02

File: `docs/active/tickets/T-013-03-BUG-02.md`

No respawn in audit framework after pit death. `run_audit()` continues simulating dead
players for thousands of frames. More critically, single-death archetypes (Speed Demon,
Jumper) can never recover because the audit doesn't respawn them. This suppresses their
true x-progress potential.

Verification: File exists with correct YAML frontmatter.

## Step 3: Create bug ticket T-013-03-BUG-03

File: `docs/active/tickets/T-013-03-BUG-03.md`

Speed Demon spindash launches off slopes into bottomless pits. On Skybridge, the spindash
+ slope interaction at x≈467 sends the player airborne on a trajectory that ends in pit
death at x≈691. The player needs either better slope adhesion or the stage needs recovery
springs in these zones.

Verification: File exists with correct YAML frontmatter.

## Step 4: Update test expectations

File: `tests/test_audit_skybridge.py`

Changes:
- Add `import pytest` at top
- SKYBRIDGE_CAUTIOUS: min_x_progress=250
- SKYBRIDGE_CHAOS: min_x_progress=250

Verification: `uv run python -c "import tests.test_audit_skybridge"` succeeds.

## Step 5: Add xfail markers to 4 test functions

File: `tests/test_audit_skybridge.py`

Add `@pytest.mark.xfail(reason=..., strict=True)` to:
- test_skybridge_walker — reason references T-013-03-BUG-01
- test_skybridge_jumper — reason references T-013-03-BUG-02
- test_skybridge_speed_demon — reason references T-013-03-BUG-02, T-013-03-BUG-03
- test_skybridge_wall_hugger — reason references T-013-03-BUG-01

Leave test_skybridge_cautious and test_skybridge_chaos without xfail.

Verification: `uv run pytest tests/test_audit_skybridge.py -v` shows 2 passed + 4 xfailed.

## Step 6: Run full test suite

Command: `uv run pytest tests/test_audit_skybridge.py -v`

Expected: 2 passed, 4 xfailed, 0 failed, 0 errors.

Verify acceptance criteria:
- At least 2 of 6 pass without xfail: cautious + chaos = 2 ✓
- All xfails reference specific documented bug tickets ✓
- No archetype falls through x≈170 gap ✓ (verified in research)
- Boss arena reachability tested for Speed Demon ✓ (require_goal=True in expectation)

## Testing Strategy

- **Primary verification**: `uv run pytest tests/test_audit_skybridge.py -v` — 2 pass, 4 xfail
- **Regression check**: No other test files modified, so no regression risk
- **Acceptance criteria check**: Manual verification against ticket requirements
