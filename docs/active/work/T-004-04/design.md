# T-004-04 Design: Integration and Full Game Loop

## Problem Statement

The codebase needs a `level.py` module per the specification. Currently, stage loading is duplicated across three nearly-identical loader files, and `StageData` is defined in `hillside.py` (an odd location). Integration tests are needed to verify the full game loop works end-to-end with real stage data.

## Options Evaluated

### Option A: Create `level.py` as a thin dispatcher

`level.py` imports and delegates to stage-specific loaders. Moves `StageData` to `level.py`. Stage loaders remain but only contain the `_DATA_DIR` path and call shared code.

**Pros:** Minimal change to existing loaders, adds the spec-required module.
**Cons:** Doesn't eliminate duplication — three loaders still exist with nearly identical code.

### Option B: Create `level.py` as the unified loader (chosen)

`level.py` contains `StageData`, a `load_stage(stage_name: str)` function that takes a stage name, finds the data directory, and loads it. The three `stages/*.py` files become thin wrappers (their `load()` functions call `level.load_stage()`). `main.py` can call `level.load_stage()` directly.

**Pros:** Eliminates duplication. `StageData` lives in the logical module. Single place to maintain JSON loading code. Stage loaders become optional thin wrappers for backwards compatibility.
**Cons:** Slightly more change than Option A.

### Option C: Merge everything into `main.py`

**Rejected.** Violates spec module listing and makes testing harder.

## Decision: Option B

The loading logic is identical across all three stages — only the data directory differs. A single `load_stage(stage_name)` function with a path lookup is cleaner and matches the spec's intent for `level.py`.

### Design Details

#### `level.py` API

```python
@dataclass
class StageData:
    tile_lookup: TileLookup
    tiles_dict: dict
    entities: list[dict]
    player_start: tuple[float, float]
    checkpoints: list[dict]
    level_width: int
    level_height: int

def load_stage(stage_name: str) -> StageData:
    """Load stage data from pipeline JSON output.

    stage_name: "hillside", "pipeworks", or "skybridge"
    """
```

#### Stage directory resolution

`_DATA_DIRS` maps stage names to paths:
```python
_STAGES_DIR = Path(__file__).parent / "stages"
_DATA_DIRS = {
    "hillside": _STAGES_DIR / "hillside",
    "pipeworks": _STAGES_DIR / "pipeworks",
    "skybridge": _STAGES_DIR / "skybridge",
}
```

#### Backwards compatibility

Keep existing `stages/hillside.py`, `stages/pipeworks.py`, `stages/skybridge.py` but simplify them to delegate to `level.load_stage()`. This preserves any external code or tests that import from them.

#### `main.py` changes

Replace `_STAGE_MODULES` dict and per-module `.load()` calls with a `_STAGE_NAMES_MAP` and `level.load_stage()` call. Minimal change to `_load_stage()`.

### Integration Test Strategy

New test file: `tests/test_integration.py`

Tests to add:
1. **Stage loading**: Each stage loads without error, returns valid `StageData`
2. **Entity parsing**: Loaded entities contain expected types for each stage
3. **Full lifecycle**: Create player → simulate frames → verify state transitions
4. **Death/respawn**: Simulate damage → verify respawn from checkpoint
5. **100-ring extra life**: Collect 100 rings → verify life increment
6. **Boss fight**: Stage 3 boss injection, damage, defeat sequence
7. **Game state transitions**: title → stage_select → gameplay → results → stage_select
8. **Camera with real stage bounds**: Verify clamping works with actual level dimensions

All tests remain Pyxel-free — they test logic, not rendering.

### What We Won't Change

- Physics engine: stable, 494 tests passing
- Collision system: stable
- Audio definitions: stable
- Renderer: stable
- Enemy/object logic: stable
- Existing tests: must all still pass
