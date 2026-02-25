"""speednik/stages/pipeworks.py — Stage 2: Pipe Works loader.

Loads pipeline-generated JSON data and exposes it to the engine via a
TileLookup callable and entity/metadata accessors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from speednik.stages.hillside import StageData
from speednik.terrain import Tile

_DATA_DIR = Path(__file__).parent / "pipeworks"


def load() -> StageData:
    """Load Pipe Works stage data from pipeline JSON output."""
    tile_map = _read_json("tile_map.json")
    collision = _read_json("collision.json")
    entities = _read_json("entities.json")
    meta = _read_json("meta.json")

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


def _read_json(filename: str) -> any:
    with open(_DATA_DIR / filename) as f:
        return json.load(f)
