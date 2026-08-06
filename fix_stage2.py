import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))
from speednik.grids import build_loop

TILE_MAP_PATH = 'speednik/stages/hillside/tile_map.json'
COLLISION_PATH = 'speednik/stages/hillside/collision.json'
ENTITIES_PATH = 'speednik/stages/hillside/entities.json'

def fix():
    with open(TILE_MAP_PATH) as f:
        tile_map = json.load(f)
    with open(COLLISION_PATH) as f:
        collision = json.load(f)

    for r in range(20, 45):
        for c in range(214, 246):
            tile_map[r][c] = None
            collision[r][c] = 0

    tiles_dict, _ = build_loop(approach_tiles=219, radius=64, ground_row=39, ramp_radius=32)

    for (tx, ty), tile in tiles_dict.items():
        if 219 <= tx <= 245 and 0 <= ty < 45:
            tile_map[ty][tx] = {
                "height_array": tile.height_array,
                "angle": tile.angle,
                "type": getattr(tile, 'tile_type', 0)
            }
            collision[ty][tx] = tile.solidity

    # DO NOT FILL GAPS HERE

    with open(TILE_MAP_PATH, 'w') as f:
        json.dump(tile_map, f, separators=(',', ':'))
    with open(COLLISION_PATH, 'w') as f:
        json.dump(collision, f, separators=(',', ':'))
    
    # Fix goal entity
    with open(ENTITIES_PATH) as f:
        entities = json.load(f)
    for e in entities:
        if e["type"] == "goal":
            e["y"] = 624
    with open(ENTITIES_PATH, 'w') as f:
        json.dump(entities, f, indent=2)

if __name__ == "__main__":
    fix()
