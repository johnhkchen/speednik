import re
with open("debug_grids.py", "r") as f:
    text = f.read()

text = text.replace(
    "tile.angle = mid[2]",
    "tile.angle = mid[2]\n        if key == (21, 17):\n            print(f'Populated {key} with {pixels}')\n            print(f'Result harr: {tile.height_array}')"
)

with open("debug_grids.py", "w") as f:
    f.write(text)
