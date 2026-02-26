# Plan — T-012-02: Hillside Behavior Audit

## Step 1: Create bug ticket T-012-02-BUG-01

Wall at x≈601 — tile (37,38) has angle=64 (wall) instead of gentle slope (~2).

File: `docs/active/tickets/T-012-02-BUG-01.md`
Verify: File exists with correct YAML frontmatter.

## Step 2: Create bug ticket T-012-02-BUG-02

No right boundary clamp — Jumper exits level at x=34023 past level_width=4800.

File: `docs/active/tickets/T-012-02-BUG-02.md`
Verify: File exists with correct YAML frontmatter.

## Step 3: Create bug ticket T-012-02-BUG-03

No left boundary clamp — Chaos reaches x=-49488.

File: `docs/active/tickets/T-012-02-BUG-03.md`
Verify: File exists with correct YAML frontmatter.

## Step 4: Write test file

Create `tests/test_audit_hillside.py` with:
- 6 expectation constants matching the ticket's table
- 6 test functions, each calling `run_audit("hillside", ..., ...)`
- xfail markers on Walker (BUG-01), Jumper (BUG-02), Cautious (BUG-01),
  Wall Hugger (BUG-01), Chaos (BUG-03)
- Speed Demon test without xfail (should pass)

Verify: `uv run pytest tests/test_audit_hillside.py -v` runs cleanly (xfails expected, no
unexpected failures).

## Step 5: Verify full test suite

Run `uv run pytest tests/test_audit_hillside.py -v` and confirm:
- Speed Demon: PASSED
- Walker, Cautious, Wall Hugger: XFAIL (wall at x≈601)
- Jumper: XFAIL (boundary clamp)
- Chaos: XFAIL (boundary clamp + insufficient drift)
- No unexpected failures (XPASS or ERROR)

## Testing Strategy

- **Unit test scope:** Each test exercises `run_audit` end-to-end on the real "hillside" stage.
- **No mocking:** Tests use real stage data, real physics, real invariant checker.
- **Determinism:** Chaos uses seed=42. All other archetypes are deterministic by construction.
- **xfail semantics:** `strict=True` on xfails so an XPASS (unexpected pass) also fails the
  test — this catches when a bug is silently fixed without updating the test.
- **Verification criteria:** `uv run pytest tests/test_audit_hillside.py -v` exits 0 with
  1 PASSED and 5 XFAIL.
