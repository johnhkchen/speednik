"""speednik/level.py — Level loading from pipeline output, tile layout.

Loads stage data from pipeline-generated JSON files (tile_map.json,
collision.json, entities.json, meta.json) and constructs the runtime level
representation. Unified loader for all stages.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from speednik.terrain import Tile, TileLookup


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class StageData:
    """All runtime data for a loaded stage."""

    tile_lookup: TileLookup
    tiles_dict: dict
    entities: list[dict]
    player_start: tuple[float, float]
    checkpoints: list[dict]
    level_width: int
    level_height: int


# ---------------------------------------------------------------------------
# Stage directory lookup
# ---------------------------------------------------------------------------

_STAGES_DIR = Path(__file__).parent / "stages"

_DATA_DIRS: dict[str, Path] = {
    "hillside": _STAGES_DIR / "hillside",
    "pipeworks": _STAGES_DIR / "pipeworks",
    "skybridge": _STAGES_DIR / "skybridge",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_stage(stage_name: str) -> StageData:
    """Load stage data from pipeline JSON output.

    Args:
        stage_name: One of "hillside", "pipeworks", "skybridge".

    Returns:
        StageData with tile lookup, entities, and metadata.

    Raises:
        ValueError: If stage_name is not recognized.
        FileNotFoundError: If stage data files are missing.
    """
    data_dir = _DATA_DIRS.get(stage_name)
    if data_dir is None:
        raise ValueError(f"Unknown stage: {stage_name!r}")

    tile_map = _read_json(data_dir / "tile_map.json")
    collision = _read_json(data_dir / "collision.json")
    entities = _read_json(data_dir / "entities.json")
    meta = _read_json(data_dir / "meta.json")

    tiles = _build_tiles(tile_map, collision)

    def tile_lookup(tx: int, ty: int) -> Optional[Tile]:
        return tiles.get((tx, ty))

    ps = meta["player_start"]
    player_start = (float(ps["x"]), float(ps["y"]))

    return StageData(
        tile_lookup=tile_lookup,
        tiles_dict=tiles,
        entities=entities,
        player_start=player_start,
        checkpoints=meta.get("checkpoints", []),
        level_width=meta["width_px"],
        level_height=meta["height_px"],
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tiles(
    tile_map: list[list],
    collision: list[list],
) -> dict[tuple[int, int], Tile]:
    """Build tile dictionary from tile_map and collision JSON arrays."""
    tiles: dict[tuple[int, int], Tile] = {}
    for ty, (tm_row, col_row) in enumerate(zip(tile_map, collision)):
        for tx, (cell, sol) in enumerate(zip(tm_row, col_row)):
            if cell is None:
                continue
            tiles[(tx, ty)] = Tile(
                height_array=cell["height_array"],
                angle=cell["angle"],
                solidity=sol,
            )
    return tiles


def _read_json(path: Path):
    """Read and parse a JSON file."""
    with open(path) as f:
        return json.load(f)
