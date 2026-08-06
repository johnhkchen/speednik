import json
import os
import sys
import math

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

    # Manual slope from col 213 (row 38, y=608) to col 218 (row 39, y=624)
    # 4 tiles of slope from 214 to 217
    # angle for drop of 16px over 64px = 1/4
    angle = round(-math.atan2(-0.25, 1.0) * 256 / (2*math.pi)) % 256
    for idx, col in enumerate(range(214, 218)):
        ha = []
        for c in range(16):
            px = idx * 16 + c
            # At px=0, h=16. At px=64, h=0.
            h = 16 - int(px * 16 / 64)
            h = max(0, min(16, h))
            ha.append(h)
        tile_map[38][col] = {"height_array": ha, "angle": angle, "type": 0}
        collision[38][col] = 2
        for r in range(39, 45):
            tile_map[r][col] = {"height_array": [16]*16, "angle": 0, "type": 0}
            collision[r][col] = 2

    # Col 218 is flat at row 39
    col = 218
    tile_map[39][col] = {"height_array": [16]*16, "angle": 0, "type": 0}
    collision[39][col] = 2
    for r in range(40, 45):
        tile_map[r][col] = {"height_array": [16]*16, "angle": 0, "type": 0}
        collision[r][col] = 2

    # Fix gaps overall (checking current ground row to continue it)
    # The gaps could be ANY row.
    loop_interior = range(221, 229)
    # Find last ground row
    last_ground_row = 38
    for col in range(4, 298):
        if col in loop_interior:
            continue
            
        has_ground = False
        for row in range(35, 42):
            if tile_map[row][col] is not None and max(tile_map[row][col].get("height_array", [0]*16)) > 0:
                has_ground = True
                last_ground_row = row
                # We break, but we want the highest ground tile (lowest row index)
                # Since we iterate 35 to 41, the first one we hit is the topmost terrain!
                break
        
        if not has_ground:
            # Fill gap at last_ground_row
            tile_map[last_ground_row][col] = {"height_array": [16]*16, "angle": 0, "type": 0}
            collision[last_ground_row][col] = 2
            for r in range(last_ground_row + 1, 45):
                tile_map[r][col] = {"height_array": [16]*16, "angle": 0, "type": 0}
                collision[r][col] = 2

    with open(TILE_MAP_PATH, 'w') as f:
        json.dump(tile_map, f, separators=(',', ':'))
    with open(COLLISION_PATH, 'w') as f:
        json.dump(collision, f, separators=(',', ':'))
        
    with open(ENTITIES_PATH) as f:
        entities = json.load(f)
    for e in entities:
        if e["type"] == "goal":
            e["y"] = 624
    with open(ENTITIES_PATH, 'w') as f:
        json.dump(entities, f, indent=2)

if __name__ == "__main__":
    fix()
