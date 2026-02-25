# Progress — T-001-01: Project Scaffolding

## Completed

### Step 1: .gitignore
- Created `.gitignore` with Python/uv patterns
- Committed: `74468bb` — "Add .gitignore for Python/uv project"

### Step 2–5: pyproject.toml, package structure, main.py, CLAUDE.md
- Created `pyproject.toml` (speednik, Python >=3.10, pyxel dep, hatchling backend)
- Created `speednik/__init__.py` (empty)
- Created `speednik/constants.py` (empty stub)
- Created `speednik/stages/__init__.py` (empty)
- Created `speednik/main.py` (class App, 256x224 @ 60fps, dark blue bg, "Speednik" text)
- Created `tools/.gitkeep`
- Ran `uv sync` — pyxel 2.7.0 installed, uv.lock generated
- Updated `CLAUDE.md` with project description and Build & Run section
- Committed: `8fd63e1` — "Add project scaffolding: pyproject.toml, speednik package, minimal Pyxel app"

### Deviation from plan
- Plan called for 4 separate commits (steps 2–5). Combined into one commit because
  hatchling requires the package directory to exist before `uv sync` can build the
  editable install. Creating pyproject.toml and the package separately caused a build
  failure. This is a non-issue — the atomic commit is actually cleaner.

## Verification

- `uv sync` — succeeds, pyxel 2.7.0 installed ✓
- `uv run python -c "import speednik"` — imports OK ✓
- `uv run python -c "import pyxel; pyxel.init(256, 224, title='Speednik', fps=60); pyxel.quit()"` — init+quit clean ✓
- `speednik/main.py` code review: 256x224, 60fps, cls(1), text "Speednik" centered, Q to quit ✓

## Remaining

Nothing. All acceptance criteria addressed.
