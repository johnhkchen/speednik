import re
with open("speednik/grids.py", "r") as f:
    text = f.read()

text = text.replace("    FILL_DEPTH = 3\n    for ty in range", "    for ty in range")
if "FILL_DEPTH" not in text[:500]: # it might have been at the top of the file or class? wait, just inject it into the function start
    text = text.replace("    fill_rows: set[tuple[int, int]] = set()", "    fill_rows: set[tuple[int, int]] = set()\n    FILL_DEPTH = 3")

with open("speednik/grids.py", "w") as f:
    f.write(text)
