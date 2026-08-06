import json

with open('speednik/stages/hillside/tile_map.json') as f:
    t = json.load(f)

print("   " + "".join(f"{c // 10 % 10} " for c in range(210, 246)))
print("   " + "".join(f"{c % 10} " for c in range(210, 246)))

for row in range(30, 42):
    line = []
    for col in range(210, 246):
        tile = t[row][col]
        if tile is None:
            line.append("  ")
        else:
            ha = tile.get("height_array", [0]*16)
            m = max(ha)
            prefix = ""
            if tile.get("type", 0) == 5:
                prefix = "L"
            elif m == 16:
                prefix = "F"
            elif m == 0:
                prefix = "."
            else:
                prefix = "S"
            line.append(prefix + str(tile.get("angle", 0) % 10))
    print(f"{row:2d} " + "".join(line))
