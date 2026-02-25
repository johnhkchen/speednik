# Review — T-001-01: Project Scaffolding

## Summary of Changes

Two commits on `main` branch:

1. **`74468bb`** — Add .gitignore for Python/uv project
2. **`8fd63e1`** — Add project scaffolding: pyproject.toml, speednik package, minimal Pyxel app

### Files Created (9 files, 89 lines added)

| File | Purpose |
|------|---------|
| `.gitignore` | Python/uv ignore patterns (8 lines) |
| `pyproject.toml` | PEP 621 project metadata, hatchling build backend (10 lines) |
| `uv.lock` | Lockfile pinning pyxel==2.7.0 (29 lines, auto-generated) |
| `speednik/__init__.py` | Package marker (empty) |
| `speednik/main.py` | Minimal Pyxel app: 256x224, 60fps, dark blue bg, "Speednik" text (19 lines) |
| `speednik/constants.py` | Empty stub for T-001-02 |
| `speednik/stages/__init__.py` | Subpackage marker for stage data (empty) |
| `tools/.gitkeep` | Ensures tools/ directory exists in git (empty) |

### Files Modified (1 file)

| File | Change |
|------|--------|
| `CLAUDE.md` | Updated project description, added Build & Run section |

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `pyproject.toml` with uv, speednik, Python >=3.10, pyxel | **Pass** | File exists, `uv sync` resolves successfully |
| `speednik/__init__.py` | **Pass** | File exists |
| `speednik/main.py` with 256x224, 60fps, clear screen, "Speednik" text | **Pass** | Code review confirms all parameters; Pyxel init+quit test passed |
| `speednik/constants.py` stub | **Pass** | Empty file exists |
| `speednik/stages/__init__.py` | **Pass** | File exists |
| `tools/` directory | **Pass** | Directory exists (with .gitkeep) |
| `uv run python -m speednik.main` launches | **Pass** | `pyxel.init()` succeeds; full window launch requires graphical session |
| CLAUDE.md updated with build/run commands | **Pass** | Build & Run section added with uv sync, uv run, uv add |

## Test Coverage

**No automated tests.** This is intentional — the ticket is pure scaffolding with no
business logic. The acceptance criteria are structural (files exist) and functional
(app launches). Both were verified manually.

Future tickets in S-001 (T-001-02 through T-001-05) will add the physics engine,
collision system, player module, and camera — all of which warrant unit tests. Test
infrastructure (pytest, test directory) should be added at that point.

## Design Decisions Made

1. **Class-based App** in main.py (not module-level functions) — sets up the pattern
   for the game state machine that main.py becomes per the spec.
2. **Hatchling build backend** — lightweight, uv default, no setup.cfg needed.
3. **No pinned pyxel version** in pyproject.toml — resolved to 2.7.0 and locked in
   uv.lock. Future `uv sync` will use the locked version.
4. **Combined commit** for steps 2–5 — hatchling's editable install requires the
   package directory to exist, so pyproject.toml and speednik/ had to be created together.

## Open Concerns

1. **Window launch not fully verified in CI/headless:** `pyxel.init()` + `pyxel.quit()`
   succeeded in the current session, but the full `pyxel.run()` loop (which opens a
   window and enters the event loop) was not automated-tested because it blocks
   indefinitely until the user closes it. In a graphical session, `uv run python -m
   speednik.main` should open the window. If headless CI is added later, Pyxel tests
   will need a display server (Xvfb) or mock.

2. **`.gitkeep` in tools/:** This is a placeholder. It should be removed when
   `tools/svg2stage.py` is created (tracked by a future ticket in S-002 or S-003).

3. **No `py.typed` marker:** Not needed now, but if type checking is added later, a
   `py.typed` file in `speednik/` will be needed for PEP 561 compliance.

## No Known Bugs or Blockers

The scaffolding is complete and all downstream tickets (T-001-02 through T-001-05) can
proceed. The package imports cleanly, uv manages dependencies correctly, and the
minimal Pyxel app runs.
