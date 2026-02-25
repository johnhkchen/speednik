# Plan — T-001-01: Project Scaffolding

## Step 1: Create .gitignore

Create `.gitignore` at repo root with Python/uv patterns.

**Files:** `.gitignore` (new)
**Verify:** File exists, `git status` no longer shows `__pycache__/` etc.
**Commit:** Yes — "Add .gitignore for Python/uv project"

## Step 2: Create pyproject.toml

Write `pyproject.toml` with PEP 621 metadata: name=speednik, version=0.1.0,
requires-python>=3.10, dependencies=["pyxel"], hatchling build backend.

**Files:** `pyproject.toml` (new)
**Verify:** `uv sync` succeeds (downloads pyxel, creates .venv and uv.lock)
**Commit:** Yes — "Add pyproject.toml with uv and pyxel dependency"
**Note:** uv.lock should be committed (it pins dependency versions for reproducibility).

## Step 3: Create package directory structure

Create directories and empty files:
- `speednik/__init__.py`
- `speednik/constants.py`
- `speednik/stages/__init__.py`
- `tools/.gitkeep`

**Files:** 4 new files, 2 new directories
**Verify:** `python -c "import speednik"` works from project root (after uv sync)
**Commit:** Yes — "Add speednik package structure and tools directory"

## Step 4: Create speednik/main.py

Write the minimal Pyxel app:

```python
import pyxel


class App:
    def __init__(self):
        pyxel.init(256, 224, title="Speednik", fps=60)
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

    def draw(self):
        pyxel.cls(1)
        pyxel.text(112, 109, "Speednik", 7)


if __name__ == "__main__":
    App()
```

**Files:** `speednik/main.py` (new)
**Verify:** `uv run python -m speednik.main` opens a 256x224 window with dark blue
background and white "Speednik" text. Press Q to quit.
**Commit:** Yes — "Add minimal Pyxel app in speednik/main.py"

## Step 5: Update CLAUDE.md

Add project description and Build & Run section.

**Files:** `CLAUDE.md` (modified)
**Verify:** Content is correct, instructions work.
**Commit:** Yes — "Update CLAUDE.md with project description and build/run commands"

## Step 6: Final verification

Run through all acceptance criteria:
1. `pyproject.toml` — uv, speednik, python>=3.10, pyxel ✓
2. `speednik/__init__.py` exists ✓
3. `speednik/main.py` — 256x224, 60fps, clears screen, "Speednik" text ✓
4. `speednik/constants.py` — empty stub ✓
5. `speednik/stages/__init__.py` exists ✓
6. `tools/` directory exists ✓
7. `uv run python -m speednik.main` launches ✓
8. CLAUDE.md updated ✓

**Verify:** Run `uv run python -m speednik.main` one final time.
**Commit:** No additional commit needed unless fixes are required.

## Testing Strategy

This ticket has no unit tests — it's pure scaffolding. The verification is:

1. **Structural:** All required files and directories exist
2. **Functional:** `uv sync` succeeds (dependency resolution works)
3. **Functional:** `uv run python -m speednik.main` opens the Pyxel window
4. **Visual:** Window is 256x224, dark background, "Speednik" text visible
5. **Interactive:** Pressing Q quits the application

Future tickets (T-001-02+) will add pytest and unit tests. This ticket does not
introduce pytest because it's not in the acceptance criteria and would be
over-engineering.

## Risk Mitigation

- **Pyxel install failure:** If the wheel isn't available for the platform, `uv sync`
  will fail. Fallback: check `uv pip install pyxel` error message, may need to
  install SDL2 system dependency. On macOS ARM64 this should not be an issue.
- **Headless environment:** If no display is available, Pyxel will crash on
  `pyxel.init()`. This is expected — AC requires window launch. No mitigation needed.
- **uv version compatibility:** uv 0.10.5 is installed. PEP 621 pyproject.toml is
  stable across uv versions. No risk.
