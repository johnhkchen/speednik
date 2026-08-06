import json

with open('speednik/stages/hillside/tile_map.json') as f:
    tile_map = json.load(f)

print("Columns and their ground rows (38-40):")
for c in range(4, 298):
    rows = []
    for r in range(35, 42):
        if tile_map[r][c] and max(tile_map[r][c].get("height_array", [0]*16)) > 0:
            rows.append(r)
    if not rows:
        print(f"[{c}]: GAP")
    # else:
    #     print(f"[{c}]: {rows}")
