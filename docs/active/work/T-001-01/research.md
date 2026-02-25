# Research — T-001-01: Project Scaffolding

## Current Repository State

The repo contains a single initial commit (`6039e00`) with no Python source code, no
`pyproject.toml`, and no `.gitignore`. The working tree has:

```
.claude/           # Claude Code config
.git/
.lisa/             # Lisa orchestration internals
.lisa.toml         # Lisa project config (v0.2.7)
.lisa-layout.kdl   # Lisa terminal layout
assets/            # 4 reference MP3 tracks (~740KB each)
CLAUDE.md          # Project instructions (needs update per AC)
docs/              # Ticket/story/work tree + specification.md
LICENSE            # MIT, Copyright 2026 John Chen
```

No `pyproject.toml`, no `speednik/` package, no `tools/` directory. This is a
greenfield scaffold.

## Specification Constraints

From `docs/specification.md`:

- **Resolution:** 256x224 @ 60fps (Genesis-native)
- **Engine:** Pyxel (Python retro game engine, 16-color palette)
- **Package manager:** uv
- **Python:** >=3.10 (implied by Pyxel requirements and spec tooling)
- **Package name:** `speednik`
- **Entry point:** `speednik/main.py` — game state machine

### Required Package Layout (from spec Section 1)

```
pyproject.toml
assets/                     # Already exists
tools/
  svg2stage.py              # Future — just create directory for now
speednik/
  __init__.py
  main.py
  constants.py
  physics.py                # Future (T-001-02+)
  player.py                 # Future
  camera.py                 # Future
  terrain.py                # Future
  level.py                  # Future
  enemies.py                # Future
  objects.py                # Future
  renderer.py               # Future
  audio.py                  # Future
  stages/
    __init__.py
    hillside.py             # Future
    pipeworks.py             # Future
    skybridge.py             # Future
```

Only files listed in acceptance criteria need to exist now. The rest are future tickets.

## Acceptance Criteria Analysis

1. **`pyproject.toml`** — uv-managed, name=speednik, python>=3.10, pyxel dep
2. **`speednik/__init__.py`** — package marker
3. **`speednik/main.py`** — minimal Pyxel app: 256x224, 60fps, clear screen, "Speednik" text
4. **`speednik/constants.py`** — stub (empty, populated by T-001-02)
5. **`speednik/stages/__init__.py`** — subpackage marker
6. **`tools/`** — directory created
7. **`uv run python -m speednik.main`** — launches Pyxel window
8. **CLAUDE.md** — updated with build/run commands

## Environment

- **macOS** Darwin 25.3.0 (Apple Silicon)
- **uv** 0.10.5 (Homebrew)
- **System Python:** 3.9.6 (too old — uv will manage a >=3.10 interpreter)
- **Pyxel compatibility:** Pyxel 2.x supports Python 3.8+ on macOS/Linux/Windows.
  Requires SDL2 which Pyxel bundles as a wheel dependency.

## Pyxel API (relevant subset)

```python
import pyxel

pyxel.init(256, 224, title="Speednik", fps=60)
pyxel.cls(0)           # Clear screen with color 0
pyxel.text(x, y, "Speednik", col)  # Draw text
pyxel.run(update, draw) # Main loop
```

`pyxel.init()` parameters: `width, height, title, fps, ...`
`pyxel.run(update_fn, draw_fn)` — takes two callables.

The minimal app structure is a class with `update` and `draw` methods, or two
standalone functions.

## Dependencies and Risks

- **Pyxel wheel availability:** Pyxel publishes wheels for macOS ARM64 (Apple
  Silicon) via PyPI. uv will download the correct wheel. No build-from-source needed.
- **SDL2 on headless:** If running in a headless/SSH environment, Pyxel will fail to
  open a window. For this ticket, we assume a graphical session is available. The AC
  says "launches the Pyxel window successfully."
- **uv project init vs manual:** uv supports `uv init` but also works with a
  hand-crafted `pyproject.toml`. Since we have an existing repo with specific
  structure requirements, hand-crafting is cleaner.
- **No .gitignore yet:** Need one to exclude `__pycache__/`, `.venv/`, `*.pyc`, etc.

## What Other Tickets Expect

- **T-001-02** (physics constants): Will populate `speednik/constants.py` — needs it
  to exist as an empty file.
- **T-001-03** through **T-001-05**: Will add more modules to `speednik/`. The package
  structure and `pyproject.toml` must be in place.
- All downstream tickets depend on `uv run python -m speednik.main` working.

## Key Observations

1. This is straightforward scaffolding — no architectural decisions with significant
   tradeoffs.
2. The spec already dictates the exact layout. The only design decision is the minimal
   app structure in `main.py`.
3. A `.gitignore` is not in the AC but is essential for a Python project. Should add it.
4. The `tools/` directory just needs to exist — no files required by this ticket.
5. CLAUDE.md needs build/run commands added — this is the handoff to future agents.
