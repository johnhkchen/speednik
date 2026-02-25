# Design — T-001-01: Project Scaffolding

## Decision 1: pyproject.toml Configuration

### Option A: `uv init` then modify

Run `uv init --name speednik`, then edit the generated `pyproject.toml` to add pyxel
and adjust settings.

**Pros:** Gets uv boilerplate for free.
**Cons:** `uv init` creates files we don't want (e.g., `hello.py`, `README.md`), uses
its own layout conventions, and may conflict with our existing repo structure. More
work to clean up than to write from scratch.

### Option B: Hand-craft pyproject.toml (chosen)

Write `pyproject.toml` directly with exactly the fields we need.

**Pros:** Full control, no cleanup needed, matches spec layout exactly.
**Cons:** Must know the correct PEP 621 / uv fields. Trivial for this scope.

**Decision:** Option B. The file is ~20 lines. `uv init` adds unnecessary friction for
an existing repo.

### pyproject.toml Content

```toml
[project]
name = "speednik"
version = "0.1.0"
description = "A Sonic 2 homage built with Pyxel"
requires-python = ">=3.10"
dependencies = ["pyxel"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- **Build system:** hatchling is the default for uv-managed projects and is lightweight.
  We're not publishing to PyPI, so this is just for `uv run` / `uv sync` to work.
- **Version:** 0.1.0 — standard starting version for a new project.
- **No pinned pyxel version:** Let uv resolve the latest. Pyxel 2.x is stable and
  backward-compatible within major versions. A lockfile (`uv.lock`) will pin the
  exact version after first sync.

## Decision 2: Minimal Pyxel App Structure

### Option A: Class-based App

```python
class App:
    def __init__(self):
        pyxel.init(256, 224, title="Speednik", fps=60)
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

    def draw(self):
        pyxel.cls(1)
        pyxel.text(100, 104, "Speednik", 7)
```

**Pros:** Encapsulated state, extensible pattern for future game state machine.
Matches the spec's description of `main.py` as the "game state machine" entry point.
**Cons:** Slightly more code than bare functions.

### Option B: Module-level functions

```python
def update():
    if pyxel.btnp(pyxel.KEY_Q):
        pyxel.quit()

def draw():
    pyxel.cls(1)
    pyxel.text(100, 104, "Speednik", 7)

pyxel.init(256, 224, title="Speednik", fps=60)
pyxel.run(update, draw)
```

**Pros:** Minimal, flat.
**Cons:** No encapsulation. Future tickets (T-001-04 player module, game state machine)
will need to refactor to a class or global state. Creates unnecessary churn.

### Decision: Option A (class-based)

The spec says `main.py` is the game state machine entry point. A class is the natural
structure for that. Starting with a class avoids a refactor in T-001-04. The extra
code is 3 lines.

The class will be instantiated via `if __name__ == "__main__"` and also via a
`__main__.py`-style entry for `python -m speednik.main`.

## Decision 3: Screen Clear Color and Text Position

- **Clear color:** `1` (dark blue, Pyxel default palette). Visible, neutral.
- **Text color:** `7` (white). High contrast on dark blue.
- **Text position:** Centered horizontally. "Speednik" is 8 characters × 4px wide
  (Pyxel's built-in font) = 32px. Screen is 256px wide. x = (256 - 32) / 2 = 112.
  y = (224 - 6) / 2 ≈ 109 for vertical center (text height is ~6px).

## Decision 4: .gitignore

Not in AC but necessary for project hygiene. Include standard Python ignores plus
uv-specific patterns:

```
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
.DS_Store
```

## Decision 5: CLAUDE.md Updates

Add a section with build/run commands:

```markdown
## Build & Run

- **Install dependencies:** `uv sync`
- **Run the game:** `uv run python -m speednik.main`
- **Add a dependency:** `uv add <package>`
```

Keep it minimal. Future tickets will add test commands, lint config, etc.

## Decision 6: Empty Stubs

- `speednik/__init__.py` — empty file (standard package marker)
- `speednik/constants.py` — empty file (T-001-02 populates it)
- `speednik/stages/__init__.py` — empty file (future stage data)
- `tools/` — empty directory. Git doesn't track empty directories, so add a
  `.gitkeep` file.

## Rejected Alternatives

- **src/ layout:** PEP 621 supports `src/speednik/` but the spec explicitly shows
  `speednik/` at repo root. Follow the spec.
- **setuptools:** hatchling is simpler for uv projects and doesn't need `setup.cfg`.
- **Pyxel resource file (.pyxres):** Spec says "no .pyxres sprite sheets — all visuals
  drawn with Pyxel primitives." Not needed.
- **pytest/ruff in this ticket:** Not in AC. Future tickets can add dev dependencies.
