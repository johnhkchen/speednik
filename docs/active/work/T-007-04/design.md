# T-007-04 Design: Regenerate Hillside & Verify Loop

## Problem

This is an integration verification ticket. The work (ramp generation + physics exemption)
is already done in T-007-01/02/03. T-007-04 must regenerate stage data, validate outputs,
run the full test suite, and confirm no integration gaps exist.

---

## Approach Options

### Option A: Regenerate and Accept Current Warnings

Regenerate the hillside stage data, run the full test suite, inspect the validation report,
and document the existing warnings (impassable gaps, accidental walls) as expected artifacts
that don't affect gameplay. No code changes.

**Pros:** Fastest path. The dependency tickets' reviews already explain why the warnings are
harmless. The physics system (angle gate + loop exemption) handles these cases correctly.

**Cons:** Acceptance criteria literally says "zero impassable gap errors." Leaving warnings
that say "Impassable gap" in the report creates ambiguity about whether the criteria are met.

### Option B: Regenerate, Fix Validator to Exclude Overlapping Surfaces

Modify the Validator to suppress impassable gap and accidental wall warnings in regions where
ramp tiles overlap with ground polygon tiles (a known artifact). This requires understanding
exactly when these false positives arise and filtering them.

**Pros:** Clean validation report. Unambiguous acceptance criteria satisfaction.

**Cons:** Validator changes are non-trivial and could mask real issues. This is scope creep
beyond what T-007-04 requests — the ticket says "regenerate and verify," not "fix validator."

### Option C: Regenerate, Run Full Verification, Add Integration Test

Regenerate stage data, run the test suite, and add a targeted integration test that loads the
actual hillside stage data and verifies the loop region properties: ramp tile existence, angle
progression, no true impassable geometry, and tile_type propagation through the full chain.

**Pros:** Strongest verification. Catches future regressions in the full pipeline. Addresses
the spirit of the acceptance criteria (verify the loop is traversable) rather than the letter
(zero warning strings in a report).

**Cons:** Adds test code. But this is an integration verification ticket — adding an
integration test is precisely the right scope.

---

## Decision: Option C

**Rationale:**

1. The ticket's purpose is integration verification. An integration test that exercises the
   full chain (SVG → tile data → physics-level tile properties) is the most valuable artifact
   this ticket can produce.

2. The existing validation report warnings are false positives caused by overlapping surfaces.
   The impassable gap check finds gaps between a ramp surface tile and a ground polygon tile
   in the same column, but both tiles provide valid ground — the player will land on whichever
   is higher. The accidental wall check finds steep ramp tiles, but the wall angle gate
   already prevents these from blocking the player.

3. Rather than modifying the validator (Option B, scope creep), or merely documenting warnings
   (Option A, weak), we'll:
   - Regenerate stage data (required by all options)
   - Run and pass the full test suite
   - Add an integration test that loads hillside stage data and verifies loop region properties
   - Document the validation warnings with explanations in the review

4. The integration test will verify:
   - Ramp tiles exist at expected columns with SOLID surface type
   - Loop tiles exist with LOOP surface type
   - tile_type is correctly set to SURFACE_LOOP (5) for loop tiles in the loaded Tile objects
   - Angle progression is smooth across ramp tiles
   - No true impassable geometry exists (contiguous ground surface through the loop region)
   - Upper loop tiles have TOP_ONLY solidity, lower loop tiles have FULL solidity

---

## What Was Rejected

**Option A (accept warnings):** Too weak for a verification ticket. The ticket exists
specifically to catch integration issues; merely re-running the pipeline and saying
"looks fine" doesn't add lasting value.

**Option B (fix validator):** Scope creep. Validator improvements are a separate concern.
The validator's job is to flag things that *might* be problems; the integration test's job
is to verify they *aren't* problems. Both can coexist.

---

## Risk Assessment

**Low risk:** This ticket doesn't change any game logic or physics. It regenerates data
(which should be identical to the current committed data if T-007-01 already regenerated)
and adds a read-only integration test.

**Manual playtest:** The acceptance criteria include a manual playtest. This can't be
automated in a headless context. The integration test is the best automated proxy. The
review artifact will note that manual playtest verification is deferred to the developer.
