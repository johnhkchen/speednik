# T-013-02 Structure — skybridge-collision-gap-fix

## Files Modified

### 1. `speednik/stages/skybridge/collision.json`

**What changes:** Two integer values in a 56×325 2D JSON array.

```
collision[31][11]: 0 → 1  (NOT_SOLID → TOP_ONLY)
collision[32][11]: 0 → 1  (NOT_SOLID → TOP_ONLY)
```

**Format constraint:** The file must remain in its original multi-line format
(one value per line, matching the committed formatting). The working tree has
minified the file to one line — we must apply the fix to the committed format
instead.

**No other values change.** The rest of the 18,200 values remain identical.

### 2. `tests/test_audit_skybridge.py`

**What changes:** Remove `@pytest.mark.xfail` decorators from all 6 test
functions, if present. In the current working tree these are already removed.
If they are still present in the committed version, they need to be removed
so the tests actually assert the fix works.

**No other test changes.** The existing test assertions (`len(bugs) == 0`) are
the correct acceptance criteria. No new tests need to be written — the audit
framework already tests exactly what the ticket requires.

## Files NOT Modified

| File | Reason |
|------|--------|
| `speednik/stages/skybridge/tile_map.json` | Already correct at col 11 |
| `speednik/level.py` | No logic changes needed |
| `speednik/terrain.py` | No logic changes needed |
| `speednik/simulation.py` | Pit death is a separate ticket (T-013-01) |
| `speednik/constants.py` | No new constants needed |
| `stages/skybridge_gauntlet.svg` | SVG fix is out of scope |
| `tools/svg2stage.py` | Pipeline fix is out of scope |
| `speednik/stages/skybridge/entities.json` | No springs/entities to add |
| `speednik/stages/skybridge/meta.json` | No metadata changes |

## Module Boundaries

This fix is entirely within the data layer (collision.json). No Python code
changes are needed. The existing loading pipeline in `level.py:_build_tiles`
will automatically pick up the corrected solidity value. The terrain sensor
system in `terrain.py` will then recognize col 11 tiles as TOP_ONLY and
resolve collisions correctly.

Data flow: `collision.json` → `level.py:_build_tiles` → `Tile.solidity` →
`terrain.py` sensor checks → player stays on ground at col 11.

## Change Ordering

1. Fix collision.json (the data fix)
2. Update tests if needed (remove xfail markers)
3. Verify by running tests

Step 1 is the only essential change. Steps 2–3 are verification.

## Risk Assessment

- **Blast radius:** Two integer values in a data file. Zero risk of breaking
  other stages or game logic.
- **Regression surface:** Only skybridge collision at cols 10–12 is affected.
  Adjacent stages (hillside, pipeworks) are untouched.
- **Rollback:** Trivially reversible — set the two values back to 0.
