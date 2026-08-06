import json

with open('speednik/stages/hillside/tile_map.json') as f:
    t = json.load(f)

print("Tiles shape (Cols 210-245, Rows 25-44):")
for row in range(25, 45):
    line = []
    for col in range(210, 246):
        tile = t[row][col]
        if tile is None:
            line.append("  ")
        else:
            ha = tile.get("height_array", [0]*16)
            m = max(ha)
            if m == 0:
                line.append("..")
            elif m == 16:
                line.append("██")
            else:
                # print something representing angle or height
                if tile.get("type") == 5:
                    line.append("LL") # loop
                else:
                    line.append("▒▒")
    print(f"{row:2d} " + "".join(line))
